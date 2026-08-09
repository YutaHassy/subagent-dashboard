#!/usr/bin/env python3
"""Subagent Dashboard — 配信サーバー

    python server.py                 既定ポート 3939 で起動（使用中なら +1 して再試行）
    python server.py --port 4000     ポート指定
    python server.py --open          起動後にブラウザを開く

1つのサーバーで全プロジェクトの記録を扱う。「いま稼働として映すチーム」は
サーバーが決める（稼働中のチーム全部 ＋ missions/.current が指すチーム＝teams）。
画面がそれを指定する手段は用意しない（?project= は無い）。

それとは別に、過去のミッション（missions/<slug>/history/<runId>/）も選んで見られる。
どれが選べるかは /api/state の tabs（軽い要約の一覧）で配り、選ばれた1件の完全な
状態は /api/run で1件ずつ返す。teams と tabs は役割が違うので混ぜない。

ルート:
    GET  /                    → public/index.html
    GET  /api/state          → 映すチームの状態（teams 配列。空なら待機画面）＋ タブ一覧（tabs）
    GET  /api/run            → 1件の完全な状態（?slug=&runId=。runId 省略で現在のミッション）
    GET  /api/projects       → 残っている記録の一覧（画面は使わない。CLI と診断用）
    GET  /api/env            → 実行環境（各種パス・プラットフォーム）
    POST /api/project/delete → 記録を削除（既定はゴミ箱へ移動）
    POST /api/history/delete → ミッションの記録を削除（必ずゴミ箱へ移動。完了したものだけ）
    GET  /*                  → public/ 配下の静的ファイル

破壊的な操作は POST でしか受け付けない。GET では絶対に消さない（ブラウザの先読み・
履歴・うっかり踏んだリンクで記録が消えることがないように）。

外部ライブラリは使いません（Python 標準ライブラリのみ）。
Windows / macOS / Linux で同じように動きます。
"""

from __future__ import annotations

import argparse
import errno
import json
import os
import sys
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePath
from urllib.parse import parse_qs, unquote, urlparse

import dashlib
from i18n import t
from dashlib import PUBLIC_DIR

dashlib.use_utf8_stdio()

# 初回実行時の自動セットアップ（人間が実行した場合はインタラクティブに確認）
try:
    import auto_setup
    auto_setup.check_and_setup(silent=False)
except Exception:
    pass  # セットアップに失敗しても本体の動作は続ける

# 本体を更新しても CLAUDE.md の運用ルールは古いまま残る。サーバーの起動は人間が画面を
# 見に来た瞬間なので、ここで気づけると手当てまで一続きになる。
# auto_setup と分けているのは、あちらが .vsix に同梱されない（＝配布先には無い）ため。
_stale = dashlib.stale_block_notice()
if _stale:
    print()
    print(_stale)
    print()

# 同じ理由で、セットアップのあとに別の CLI を入れた人もここで気づけるようにする。
# 何も書かれていない CLI からの起動は、画面に何も出ないだけでエラーにはならない
# ので、サーバー起動時のこの一瞬を逃すと気づく場所が無くなる。
_unwired = dashlib.unwired_agent_notice()
if _unwired:
    print()
    print(_unwired)
    print()

DEFAULT_PORT = 3939
PORT_RETRY = 10
MAX_BODY = 64 * 1024  # POST 本文の上限（削除要求は数十バイトで足りる）

MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".woff2": "font/woff2",
    ".ico": "image/x-icon",
}


def _note(message: str) -> None:
    """破壊的な操作の記録を1行出す。**書けなくても失敗にしない。**

    削除そのものは既に済んでいるので、ここで例外を漏らすと do_POST の except が
    それを 500 に変え、消えているのに「記録はそのまま残っています」と画面に出る。
    実際に起きる: VSCode 拡張はサーバーを stdio=pipe で起動するので、読み手が
    先に居なくなると print が OSError（Windows では Errno 22）を投げる。
    ログが書けないことと、操作が成功したかどうかは別の話。
    """
    try:
        print(message)
        sys.stdout.flush()
    except Exception:
        # OSError だけでなく全部握る。stdout が None や閉じた状態のときは
        # AttributeError / ValueError で来るので、型を絞ると同じ症状が別の顔で戻る。
        pass


def _safe_component(value) -> bool:
    """外から来た文字列が「パスの1階層」として使ってよい形かだけを見る構造チェック。

    dashlib の検証（is_valid_slug / is_valid_run_id）と併用する。区切り文字や
    .. を含む要求は、dashlib 側の実装がどうであれ、パスに触れる前に弾きたい。
    slug には日本語も空白も入りうるので文字種の許可リストは作れない。
    """
    if not isinstance(value, str) or not value or value in (".", ".."):
        return False
    if "\x00" in value or "/" in value or "\\" in value:
        return False
    return PurePath(value).name == value


def _ts(raw) -> float | None:
    """ISO8601 をエポック秒に。読めないものは None（並べ替えで末尾に回すため）。

    タイムゾーン付きと無しが混在しても比較できるよう、必ず float に落とす
    （aware と naive の datetime を直接比べると TypeError になる）。
    """
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def _tab_sort_key(tab: dict):
    """startedAt の降順に並べるための鍵。無い／壊れているものは末尾へ。

    (有効な startedAt を持つか, その値) の順にして reverse=True で使う。
    真偽を先頭に置くので、無効なものは reverse でも必ず後ろへ回る。
    """
    # 変数名を ts にしてあるのは、この module が文言の翻訳関数を t という名前で
    # import しているため。ここで t を作ると、あとでこの関数の中から翻訳を呼びたく
    # なったときに静かに数値を呼ぶことになる。
    ts = _ts(tab.get("startedAt"))
    return (ts is not None, ts or 0.0)


def _phase_of(value, fallback: str = "standby") -> str:
    return value if value in dashlib.PHASES else fallback


def _current_tab(slug: str, current: str | None) -> dict | None:
    """いま進行中のミッション（state.json）1件をタブ1つ分の軽い情報にする。

    build_state は使わない（孫の自己申告まで読む重い処理を、1秒ごとに全プロジェクト
    ぶん走らせることになる）。state.json を1回だけ読んで必要な項目だけ取り出す。

    state.json がまだ無いプロジェクトは「現在のミッション」が無いので None を返す。
    ただし .current が指しているものは teams 側にも出るので必ずタブを作る。
    """
    ok, value, err = dashlib.read_json_safe(dashlib.state_file(slug))
    if not ok:
        if dashlib.is_not_created(err) and slug != current:
            return None
        value = {}
    if not isinstance(value, dict):
        value = {}

    mission = value.get("mission") if isinstance(value.get("mission"), dict) else {}
    project = value.get("project") if isinstance(value.get("project"), dict) else {}
    agents = value.get("agents") if isinstance(value.get("agents"), list) else []

    # 指令塔は「サブエージェントの数」に含めない（CLI の summarize_project と同じ数え方）。
    # 孫の自己申告（agents/*.json）は数えない。1件ずつ開くと軽い一覧ではなくなる。
    workers = [
        a for a in agents
        if isinstance(a, dict) and dashlib.as_str(a.get("id")) and a.get("id") != dashlib.COMMAND_ID
    ]
    count = len(workers)
    # 締め忘れ（全員 done なのに phase が running）をタブに出すための数。
    # 数えられなかったときは 0 ではなく None を返す。0 は「1体も帰っていない」と
    # いう意味を持ってしまうので、「分からない」と区別できないと画面が嘘をつく。
    done_count = sum(1 for a in workers if a.get("status") == "done")
    if count == 0:
        done_count = None
        summary = mission.get("summary")
        if isinstance(summary, dict) and dashlib.as_num(summary.get("agentCount")) is not None:
            count = dashlib.as_num(summary.get("agentCount"))

    return {
        "slug": slug,
        "runId": None,  # None＝missions/<slug>/state.json（進行中のミッション）
        "title": dashlib.as_str(mission.get("title")) or t("(untitled mission)"),
        "phase": _phase_of(mission.get("phase")),
        "startedAt": dashlib.as_str(mission.get("startedAt")) or None,
        "finishedAt": dashlib.as_str(mission.get("finishedAt")) or None,
        "projectName": dashlib.as_str(project.get("name")) or slug,
        "agentCount": count,
        "doneCount": done_count,
        "isCurrent": slug == current,
    }


def _history_tabs(slug: str, project_name: str) -> list[dict]:
    """missions/<slug>/history/ の一覧をタブに変換する。

    dashlib.list_runs() は軽い一覧（build_state を使っていない）。ここで例外を
    漏らすと履歴1件の破損で /api/state が毎秒 500 になり、稼働中のチームまで
    画面から消えるので、プロジェクト単位で握って「履歴なし」に落とす。
    """
    try:
        runs = dashlib.list_runs(slug)
    except Exception:
        return []
    if not isinstance(runs, list):
        return []

    tabs: list[dict] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        run_id = dashlib.as_str(run.get("runId"))
        # /api/run と同じ検証をここでも通す。通らない runId をタブにすると、
        # 画面が押しても 400 しか返らないタブが並ぶことになる。
        if not run_id or not dashlib.is_valid_run_id(run_id):
            continue
        tabs.append({
            "slug": slug,
            "runId": run_id,
            "title": dashlib.as_str(run.get("title")) or t("(untitled mission)"),
            "phase": _phase_of(run.get("phase")),
            "startedAt": dashlib.as_str(run.get("startedAt")) or None,
            "finishedAt": dashlib.as_str(run.get("finishedAt")) or None,
            "projectName": project_name,
            "agentCount": dashlib.as_num(run.get("agentCount")),
            # 過去の記録に「未締め」の催促は出さない（もう締められない）。軽い一覧の
            # list_runs は各機体の状態まで持たないので、数えずに None を返す。
            "doneCount": None,
            "isCurrent": False,  # 過去の記録は「いま映すチーム」には決してならない
        })
    return tabs


def _is_unstarted_tab(tab: dict) -> bool:
    """まだ一度も start していない、器だけの「未開始」タブか。

    reset の直後や、名前だけ作られたプロジェクトがこれになる。判定にタイトルの
    文字列は使わない。state.json が読めないときの題は「（無題のミッション）」で、
    同じ未開始でも文字列が違うため取りこぼす（_current_tab の題のフォールバック）。

    phase を必ず見るのが要点。start 直後は指令塔しか居ないので agentCount は 0 に
    なるが、そちらは phase が running なので未開始とは別物である。
    """
    return (
        tab.get("runId") is None
        and tab.get("phase") == "standby"
        and not tab.get("agentCount")
    )


def drop_unstarted_tabs(tabs: list[dict]) -> tuple[list[dict], set[str]]:
    """未開始の器は「他に見るものが1件も無いとき」だけ残す。

    reset したプロジェクトの空タブは次の start まで消えないので、放っておくと
    「押しても何も出ないタブ」がタブ列に溜まり続ける。中身のあるタブが1件でも
    あれば降ろす。ただし全部降ろしてしまうと、まだ何も始めていない人の画面から
    プロジェクトの存在ごと消えるので、他に1件も無いときはそのまま残す。

    未開始どうしは「他のタブ」に数えない。数えると、未開始が2件あるだけで
    両方消えて tabs が空になり、画面が待機画面へ落ちてしまう。

    返り値の2つ目は降ろした器のスラッグ。呼び出し側が teams からも同じものを
    外すために使う。
    """
    real = [t for t in tabs if not _is_unstarted_tab(t)]
    if not real:
        return tabs, set()
    hidden = {dashlib.as_str(t.get("slug")) for t in tabs if _is_unstarted_tab(t)}
    return real, {s for s in hidden if s}


def build_tabs(current: str | None) -> list[dict]:
    """画面のタブ一覧。全プロジェクトの「進行中のミッション」と「history/」を全部並べる。

    1秒ごとに叩かれるので build_state は一切呼ばない。1プロジェクトあたり
    state.json 1回の読み込み ＋ list_runs()（軽い一覧）だけで組み立てる。

    current は呼び出し側が読んだものを受け取る。ここで read_current() を
    呼び直すと、その間に start が走ったとき teams と食い違う。
    """
    tabs: list[dict] = []
    for slug in dashlib.list_slugs():
        # 1プロジェクトの破損で他のプロジェクトのタブまで落とさない。
        # ここで例外を漏らすと /api/state が毎秒 500 になる。
        try:
            cur = _current_tab(slug, current)
        except Exception:
            cur = None
        name = cur["projectName"] if cur else slug
        if cur:
            tabs.append(cur)
        try:
            tabs.extend(_history_tabs(slug, name))
        except Exception:
            pass

    tabs.sort(key=_tab_sort_key, reverse=True)
    return tabs


def build_payload() -> dict:
    """画面が1リクエストで必要な情報をまとめて返す。

    複数チームが並行稼働することがあるため、稼働中とみなせるチームを
    resolve_visible_slugs() で全部集めて返す（どれを映すかは画面ではなく
    dashlib が決める。ここに「どのプロジェクトを見るか」という引数は無い）。
    表示対象が1つも無ければ teams は空配列＝待機画面。

    teams は従来どおり「稼働中の描画」用。tabs は「過去のぶんも含めて何が選べるか」の
    一覧で、中身は軽い要約だけ（完全な状態は /api/run で1件ずつ取る）。
    """
    # .current は1リクエストにつき1回だけ読む。2回読むと、その間に start が走った場合に
    # currentSlug と teams が食い違った応答を返してしまう。
    current = dashlib.read_current()
    teams = [dashlib.build_state(slug) for slug in dashlib.resolve_visible_slugs(current)]

    # tabs は「おまけ」。ここで例外を漏らすと稼働中のチームまで映らなくなるので、
    # 最後の受け皿を置いて空配列に落とす（原因は tabsError で見えるようにする）。
    tabs_error = None
    try:
        tabs, hidden = drop_unstarted_tabs(build_tabs(current))
    except Exception as e:
        tabs, hidden, tabs_error = [], set(), f"{type(e).__name__}: {e}"

    # タブから降ろした器は teams からも外す。画面側は毎秒「tabs に無いチームは片付ける」と
    # 「teams にあるチームは作る」の両方をやるので、ここが食い違うと同じチームの器を
    # 作っては壊すのを延々と繰り返す（.current が未開始のプロジェクトを指したまま、
    # 別のプロジェクトで作業を始めたときに起きる）。
    if hidden:
        teams = [
            ts for ts in teams
            if dashlib.as_str((ts.get("project") or {}).get("slug")) not in hidden
        ]

    payload = {
        "version": 2,
        "serverTime": dashlib.now_iso(),
        "currentSlug": current,
        "teams": teams,
        "tabs": tabs,
    }
    if tabs_error:
        payload["tabsError"] = tabs_error
    return payload


def env_info() -> dict:
    return {
        "platform": sys.platform,
        "python": sys.version.split()[0],
        "toolRoot": str(dashlib.TOOL_ROOT),
        "dataHome": str(dashlib.DATA_HOME),
        "missionsDir": str(dashlib.MISSIONS_DIR),
        "pythonCommand": dashlib.PY_CMD,
        "launcher": dashlib.LAUNCHER,
        "activeWindowSec": dashlib.active_window_sec(),
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentDashboard/3.0"
    protocol_version = "HTTP/1.1"  # keep-alive。Content-Length は必ず付ける

    def log_message(self, fmt, *args):
        # 1秒ごとのポーリングでログが溢れるので抑制する
        pass

    # --- レスポンス補助

    def _no_store(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")

    def _send_bytes(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._no_store()
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, code: int, obj) -> None:
        self._send_bytes(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), MIME[".json"])

    def _send_text(self, code: int, text: str) -> None:
        self._send_bytes(code, text.encode("utf-8"), "text/plain; charset=utf-8")

    def _send_method_not_allowed(self, path: str, allow: str) -> None:
        body = json.dumps(
            {"ok": False,
             "error": t("{path} accepts only {allow}").format(path=path, allow=allow)},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(405)
        self.send_header("Content-Type", MIME[".json"])
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Allow", allow)
        self._no_store()
        self.end_headers()
        self.wfile.write(body)

    def _same_origin(self) -> bool:
        """この画面自身から出た要求かを確かめる。

        Origin が無い要求（curl など）は素通しする。ローカル専用ツールなのでトークン方式は
        採らず、「他のサイトを開いていて勝手に消える」ことだけを防ぐ。
        """
        origin = self.headers.get("Origin")
        if not origin:
            return True
        try:
            origin_host = urlparse(origin).hostname or ""
            host = urlparse("//" + (self.headers.get("Host") or "")).hostname or ""
        except ValueError:
            return False
        local = {"127.0.0.1", "localhost", "::1"}
        return bool(origin_host) and (
            origin_host == host or (origin_host in local and host in local)
        )

    def _read_json_body(self) -> tuple[dict | None, str]:
        """POST 本文を読む。keep-alive を壊さないよう Content-Length ぶんを必ず読み切る。"""
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            # HTML の form は application/json を送れない。この1行で「他サイトの
            # 送信ボタンひとつで消える」経路が原理的に成立しなくなる。
            return None, t("Content-Type must be application/json")
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None, t("Content-Length is invalid")
        if length <= 0:
            return None, t("the request body is empty")
        if length > MAX_BODY:
            self.close_connection = True  # 読み捨てずに接続を切る
            return None, t("the request body is too large")
        raw = self.rfile.read(length)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, t("not readable as JSON ({err})").format(err=e)
        if not isinstance(value, dict):
            return None, t("please send a JSON object")
        return value, ""

    # --- ルーティング

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        # 言語設定を読み直す（変わっていたときだけ）。サーバーは何時間も同じプロセスで
        # 動くので、起動時に決めたままにすると dash lang で切り替えても画面側のフォール
        # バック文言（「（ミッション未開始）」など）が古い言語のまま出続ける。
        dashlib.refresh_lang()

        if path == "/api/state":
            # 映すチームはサーバーが決めるので、クエリでの指定は受け付けない。
            # ?t= のキャッシュ避けだけが付いてくる。
            try:
                self._send_json(200, build_payload())
            except Exception as e:  # 状態ファイルが想定外でも画面を落とさない
                self._send_json(500, {"error": f"{type(e).__name__}: {e}"})
            return

        if path == "/api/run":
            # 1件ぶんの完全な状態。slug に日本語や空白が入りうるので path ではなく
            # クエリで受ける（?slug=...&runId=...。URLエンコードされて届く）。
            self._handle_run(parsed.query)
            return

        if path == "/api/projects":
            # 画面は使わない。CLI と診断から「記録がどれだけ残っているか」を見るため。
            try:
                self._send_json(200, {"projects": dashlib.list_projects()})
            except Exception as e:
                self._send_json(500, {"error": f"{type(e).__name__}: {e}"})
            return

        if path == "/api/env":
            self._send_json(200, env_info())
            return

        if path.startswith("/api/project/") or path.startswith("/api/history/"):
            # 破壊的な操作は GET では受け付けない
            self._send_method_not_allowed(path, "POST")
            return

        self._serve_static(path)

    def _handle_run(self, query: str) -> None:
        """GET /api/run?slug=<slug>&runId=<runId>

        runId を省略したら現在のミッション（build_state）。返す形はどちらも同じ。
        """
        params = parse_qs(query)
        slug = (params.get("slug") or [""])[0]
        run_id = (params.get("runId") or [""])[0]

        # dashlib の検証に加えて構造チェックも通す。区切り文字や .. を含むものは
        # dashlib の実装がどうであれ、パスに触れる前に 400 で返したい。
        if not _safe_component(slug) or not dashlib.is_valid_slug(slug):
            self._send_json(400, {"ok": False, "error": t("specify a valid slug")})
            return

        if run_id:
            if not _safe_component(run_id) or not dashlib.is_valid_run_id(run_id):
                self._send_json(400, {"ok": False, "error": t("specify a valid runId")})
                return
            try:
                state = dashlib.read_run(slug, run_id)
            except FileNotFoundError:
                self._send_json(404, {"ok": False, "error":
                    t("{slug} has no record {run_id}").format(slug=slug, run_id=run_id)})
                return
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
                return
        else:
            # 記録そのものが無い slug は 404。build_state は空の状態を返してしまうので、
            # 「無いもの」が「未開始のもの」に見えないよう先に弾く。
            if slug not in dashlib.list_slugs():
                self._send_json(404, {"ok": False, "error":
                    t("{slug} has no records").format(slug=slug)})
                return
            try:
                state = dashlib.build_state(slug)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
                return

        if not isinstance(state, dict):
            self._send_json(500, {"ok": False,
                                  "error": t("the record is not in the expected shape")})
            return

        # 画面が「いまどれを表示しているか」を突き合わせられるように添える
        # （build_state と同じ形のまま、キーを1つ足すだけ）
        state = dict(state)
        state.setdefault("runId", run_id or None)
        self._send_json(200, state)

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path not in ("/api/project/delete", "/api/history/delete"):
            self._send_json(404, {"ok": False,
                                  "error": t("{path} does not accept POST").format(path=path)})
            return

        if not self._same_origin():
            self._send_json(403, {"ok": False,
                                  "error": t("requests from another origin are not accepted")})
            return

        body, err = self._read_json_body()
        if body is None:
            self._send_json(400, {"ok": False, "error": err})
            return

        try:
            if path == "/api/history/delete":
                self._delete_history(body)
            else:
                self._delete_project(body)
        except Exception as e:
            # 応答を返さずに例外で抜けると keep-alive の接続が切れるだけで画面に何も出ない
            self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})

    def _delete_project(self, body: dict) -> None:
        slug = body.get("slug")
        permanent = bool(body.get("permanent"))
        if not isinstance(slug, str) or not dashlib.is_valid_slug(slug):
            self._send_json(400, {"ok": False, "error": t("specify a valid slug")})
            return

        if slug not in dashlib.list_slugs():
            # すでに無い場合も「消えている」で構わない（連打・再送でエラーにしない）
            self._send_json(200, {
                "ok": True, "slug": slug, "permanent": permanent, "movedTo": None,
                "alreadyGone": True, "projects": dashlib.list_projects(),
            })
            return

        try:
            info = dashlib.delete_project(slug, permanent=permanent)
        except (OSError, ValueError) as e:
            self._send_json(500, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        # log_message は抑制しているので、破壊的な操作だけは自分で1行出す
        _note(
            t("  Deleted the record: {slug}").format(slug=slug)
            + (f" → {info['movedTo']}" if info["movedTo"]
               else t(" (deleted permanently)"))
        )

        self._send_json(200, {
            "ok": True, **info, "alreadyGone": False, "projects": dashlib.list_projects(),
        })

    def _history_targets(self, body: dict) -> tuple[list[tuple[str, str | None]], str]:
        """POST /api/history/delete の本文から「消す対象」を組み立てる。

        受ける形は2つだけ:
            {"runs": [{"slug": ..., "runId": ...}, ...]}
            {"phase": "done"}

        runId が None のものは history/ ではなく現在のミッション
        （missions/<slug>/state.json）を指す。history/ へ移されるのは次の start が
        走ったときだけなので、1度きりのミッションは完了しても state.json に残り続ける。
        画面で「完了」と出ているものを消せるように、ここでも対象に含める。
        ただし実際に消せるのは完了したものだけ（判定は dashlib 側で行う。要求を
        組み立ててから消すまでの間に start が走ることがあるので、消す直前に見る）。

        返り値: (対象の一覧, エラー説明)。エラー説明が空でなければ 400 で返す。
        """
        runs = body.get("runs")
        phase = body.get("phase")

        if runs is not None:
            if not isinstance(runs, list) or not runs:
                return [], t("runs must list at least one {slug, runId} entry")
            targets: list[tuple[str, str | None]] = []
            for i, item in enumerate(runs):
                if not isinstance(item, dict):
                    return [], t("runs[{i}] is not an object").format(i=i)
                slug = item.get("slug")
                run_id = item.get("runId")
                # 不正な指定は1件でもあれば何も消さずに 400。区切り文字や .. が
                # 混ざった要求は「一部失敗」ではなく要求そのものが間違っている。
                if not _safe_component(slug) or not dashlib.is_valid_slug(slug):
                    return [], t("runs[{i}].slug is invalid").format(i=i)
                if run_id is None:
                    targets.append((slug, None))  # 現在のミッション（state.json）
                    continue
                if not _safe_component(run_id) or not dashlib.is_valid_run_id(run_id):
                    return [], t("runs[{i}].runId is invalid").format(i=i)
                targets.append((slug, run_id))
            return targets, ""

        if phase is not None:
            if not isinstance(phase, str) or phase not in dashlib.PHASES:
                return [], t("phase must be one of {list}").format(
                    list=" / ".join(dashlib.PHASES))
            targets = []
            current = dashlib.read_current()
            for slug in dashlib.list_slugs():
                # 現在のミッションは画面のタブと同じ判定を通す（表示が「完了」なら
                # 一括削除にも入る、を一致させるため _current_tab を使い回す）。
                try:
                    cur = _current_tab(slug, current)
                except Exception:
                    cur = None  # 1プロジェクトの破損で他のプロジェクトを諦めない
                if cur and cur["phase"] == phase:
                    targets.append((slug, None))
                try:
                    listed = dashlib.list_runs(slug)
                except Exception:
                    continue
                for run in listed if isinstance(listed, list) else []:
                    if not isinstance(run, dict) or run.get("phase") != phase:
                        continue
                    run_id = dashlib.as_str(run.get("runId"))
                    if run_id and dashlib.is_valid_run_id(run_id):
                        targets.append((slug, run_id))
            return targets, ""

        return [], t("specify either runs or phase")

    def _delete_history(self, body: dict) -> None:
        """ミッションの記録を消す。必ずゴミ箱へ移すだけで、完全削除はしない。"""
        if body.get("permanent"):
            # 画面から押されるボタンに完全削除をさせない。permanent は受け付けない。
            self._send_json(400, {
                "ok": False,
                "error": t("permanent is not accepted "
                           "(records are always moved to the trash)"),
            })
            return

        targets, err = self._history_targets(body)
        if err:
            self._send_json(400, {"ok": False, "error": err})
            return

        moved: list[str] = []
        failed: list[dict] = []
        deleted = 0
        for slug, run_id in targets:
            try:
                # runId が無いものは現在のミッション（state.json）。完了していれば
                # 消せる。まだ終わっていなければ delete_current_run が断る。
                if run_id is None:
                    info = dashlib.delete_current_run(slug)
                else:
                    info = dashlib.delete_run(slug, run_id)
            except FileNotFoundError:
                failed.append({"slug": slug, "runId": run_id,
                               "error": t("no such record")})
                continue
            except ValueError as e:
                # 断られた理由（まだ完了していない等）はそのまま画面に出す。
                # 種類名を付けると人が読む文にならない。
                failed.append({"slug": slug, "runId": run_id, "error": str(e)})
                continue
            except Exception as e:
                # 1件失敗しても残りは進める（連続削除の途中で止まらないように）
                failed.append({"slug": slug, "runId": run_id, "error": f"{type(e).__name__}: {e}"})
                continue
            deleted += 1
            dest = info.get("movedTo") if isinstance(info, dict) else None
            if dest:
                moved.append(str(dest))

        # log_message は抑制しているので、破壊的な操作だけは自分で1行出す
        _note(t("  Deleted records: {n}").format(n=deleted)
              + (t(" ({n} failed)").format(n=len(failed)) if failed else ""))

        self._send_json(200, {
            "ok": True, "deleted": deleted, "movedTo": moved, "failed": failed,
        })

    def _serve_static(self, path: str) -> None:
        rel = unquote(path)
        if rel in ("", "/"):
            rel = "/index.html"

        target = (PUBLIC_DIR / rel.lstrip("/")).resolve()
        try:
            target.relative_to(PUBLIC_DIR)  # public/ の外を読ませない
        except ValueError:
            self._send_text(403, "forbidden")
            return

        if not target.is_file():
            self._send_text(404, t("404 — {path} was not found").format(path=rel))
            return

        try:
            if target.suffix.lower() == ".html":
                # 説明書などに書かれた {{TOOL_ROOT}} を実際のパスへ差し替える
                body = dashlib.render_template(target.read_text(encoding="utf-8")).encode("utf-8")
            else:
                body = target.read_bytes()
        except OSError as e:
            self._send_text(500, t("failed to read: {err}").format(err=e))
            return

        self._send_bytes(200, body, MIME.get(target.suffix.lower(), "application/octet-stream"))


class Dashboard(ThreadingHTTPServer):
    # Windows では SO_REUSEADDR が「使用中ポートへのバインド」まで許してしまうので無効化する。
    # POSIX では TIME_WAIT のポートをすぐ再利用するために有効にする。
    allow_reuse_address = sys.platform != "win32"
    daemon_threads = True


def serve(host: str = "127.0.0.1", port: int = DEFAULT_PORT, retry: int = PORT_RETRY,
          open_browser: bool = False) -> None:
    httpd = None
    for _ in range(retry + 1):
        try:
            httpd = Dashboard((host, port), Handler)
            break
        except OSError as e:
            if e.errno in (errno.EADDRINUSE, 10048):
                print(t("Port {port} is in use. Trying {next}…")
                      .format(port=port, next=port + 1))
                port += 1
                continue
            print(t("Failed to start: {err}").format(err=e), file=sys.stderr)
            sys.exit(1)

    if httpd is None:
        print(t("No free port was found. Use --port to choose another one."),
              file=sys.stderr)
        sys.exit(1)

    shown_host = "127.0.0.1" if host in ("", "0.0.0.0", "::") else host
    url = f"http://{shown_host}:{port}/"
    visible = dashlib.resolve_visible_slugs()  # 稼働中とみなせるチームは複数ありうる

    print()
    print(t("  Subagent Dashboard"))
    print("  ------------------------------------------------")
    print(t("  Screen        {url}").format(url=url))
    print(t("  Manual        {url}").format(url=url + "manual.html"))
    print(t("  Tool          {path}").format(path=dashlib.TOOL_ROOT))
    print(t("  Missions      {path}").format(path=dashlib.MISSIONS_DIR))
    if host not in ("127.0.0.1", "localhost"):
        print(t("  * Listening on {host}. Other machines on the same network "
                "can reach it.").format(host=host))
    if visible:
        label = {"standby": t("standby"), "running": t("running"), "done": t("done")}
        print(t("  Teams on screen  {n}").format(n=len(visible)))
        for slug in visible:
            p = dashlib.summarize_project(slug)
            phase_label = label.get(p["phase"], "?")
            print(t("    - {name} ({phase} / {done}/{total} done) {title}")
                  .format(name=p["name"], phase=phase_label, done=p["done"],
                          total=p["total"], title=p["title"]))
    else:
        print(t("  Teams on screen  none (standby screen)"))
        print(t("    → In your working folder, run  {cmd} update_state.py start")
              .format(cmd=dashlib.PY_CMD))
    print(t("  Stop          Ctrl+C"))
    print()
    sys.stdout.flush()

    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass  # 開けなくてもサーバーは動く

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n" + t("Stopped."))
    finally:
        httpd.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="server.py",
        description=t("The serving process for the Subagent Dashboard"),
    )
    parser.add_argument("--port", type=int, default=None,
                        help=t("port to listen on (default {port}; the PORT "
                               "environment variable also works)").format(port=DEFAULT_PORT))
    parser.add_argument("--host", default="127.0.0.1",
                        help=t("address to listen on (default 127.0.0.1; use 0.0.0.0 "
                               "only when you want it visible on the LAN)"))
    parser.add_argument("--open", action="store_true",
                        help=t("open a browser after starting"))
    parser.add_argument("--no-retry", action="store_true",
                        help=t("do not move to the next port when it is in use"))
    args = parser.parse_args()

    port = args.port if args.port is not None else int(os.environ.get("PORT", DEFAULT_PORT))
    serve(
        host=args.host,
        port=port,
        retry=0 if args.no_retry else PORT_RETRY,
        open_browser=args.open,
    )


if __name__ == "__main__":
    main()
