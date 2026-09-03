"""稼働中のサブエージェントを、Claude Code が書いている記録から実測で読む。

このダッシュボードの記録（state.json）は「起動直後」と「完了通知時」の2点でしか
更新されない。そのあいだ、機体が本当に動いているのか、詰まって止まっているのかは
記録からは分からなかった。

一方 Claude Code は、サブエージェント1体につき1本の JSONL を、稼働中にそのまま
追記し続けている。

    <claude設定>/projects/<slug>/<sessionId>/subagents/agent-<agentId>.jsonl
    <claude設定>/projects/<slug>/<sessionId>/subagents/agent-<agentId>.meta.json
    <claude設定>/projects/<slug>/<sessionId>/subagents/workflows/<runId>/  （Workflow 経由）

ツール呼び出し1件ごとに1行が増え、行には時刻・ツール名・引数・usage が入っている。
ここから読めるのは全部**実測値**で、推定は一切していない。これはこのプロジェクトの
「推測値を書かない」という方針を守るための前提条件である。

読み方の要点（すべて実データで検証した）:

- トークンは**累積合計ではなく、最後の assistant 行の
  input_tokens + cache_creation_input_tokens + cache_read_input_tokens**（＝そのときの
  コンテキスト長）。cache_creation は5分で失効する一時キャッシュなので、ツール実行が
  長引くと同じ文脈が何度も作り直され、単純合計は実際の 2.8〜45 倍に膨れる。
  この式は完了通知の値と n=8 で誤差 -0.002%（947,275 対 947,297）で一致した。
- ツール回数は jsonl 内の tool_use ブロック数と完全に一致する（288 対 288）。
- 所要秒は最初と最後の timestamp の差で、誤差 13ms 以内。

このモジュールは**読むだけ**で、何も書かない。失敗しても例外を外に出さない
（/api/state は毎秒叩かれるので、ここで throw すると無関係な稼働中のチームまで
画面から消える）。
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import dashlib


# ---------------------------------------------------------------- 設定

# 記録の読み先。既定は Claude の設定ディレクトリ配下（CLAUDE_CONFIG_DIR を尊重する
# dashlib.claude_config_dir() を通す）。試験のときだけ環境変数で差し替える。
ENV_LIVE_ROOT = "AGENT_DASHBOARD_LIVE_ROOT"

# 「静か」「無風」とみなすまでの秒数。長いツールを実行中は沈黙と見なさない
# （tool_use は出たのに tool_result が来ていない＝実行中だと分かるため）。
DEFAULT_IDLE_QUIET_SEC = 180
ENV_IDLE_QUIET = "AGENT_DASHBOARD_IDLE_QUIET"
DEFAULT_IDLE_STALLED_SEC = 600
ENV_IDLE_STALLED = "AGENT_DASHBOARD_IDLE_STALLED"

# ファイル列挙の使い回し秒数。/api/state は毎秒叩かれ、しかも1リクエストで
# 稼働中の全チームぶん build_state が走る。列挙をチームごとにやると N 倍払うので束ねる。
DEFAULT_ENUM_TTL_SEC = 2
ENV_ENUM_TTL = "AGENT_DASHBOARD_LIVE_ENUM_TTL"

# 記録の startedAt と実機の最初の行の時刻が、これ以上離れていたら別物とみなす。
# add は起動直後に打つ運用なので、実際の差は数秒に収まる。
DEFAULT_PAIR_WINDOW_SEC = 300
ENV_PAIR_WINDOW = "AGENT_DASHBOARD_LIVE_PAIR_WINDOW"

# ミッション開始より前に生まれた機体は候補にしない（前のミッションの残骸を拾わない）。
MISSION_SLACK_SEC = 120

# 1回の呼び出しで読む JSONL の上限。増分読みなので通常は届かないが、記録が壊れて
# 巨大な差分が出たときに毎秒それを読み続けないための蓋。
MAX_READ_BYTES = 8 * 1024 * 1024

# 1行がこれを超えたら、その行の中身は諦める。止まるよりましだから。
LINE_PARSE_CAP = 64 * 1024 * 1024

_LOCK = threading.RLock()

# path -> {"size", "mtime", "offset", "acc"}
_file_cache = {}
# {"at": float, "files": [...]}
_enum_cache = {"at": 0.0, "files": []}
# path -> 素性（cwd・モデル・説明）。生まれたあと変わらないので恒久的に持つ。
_describe_cache = {}
# slug -> {record_id: agent_id}  前回の対応。毎回ゼロから解き直すと数字が入れ替わるので保つ。
_sticky = {}
# 同じティックのあいだ、どの agentId がどの slug に取られたか（チーム横断の重複防止）
_ledger = {"at": 0.0, "taken": {}}


def _env_int(name: str, default: int) -> int:
    """正の整数として読めない値は既定にフォールバックする（dashlib の作法に合わせる）。"""
    raw = os.environ.get(name, "").strip()
    if raw:
        try:
            n = int(raw)
            if n > 0:
                return n
        except ValueError:
            pass
    return default


def idle_quiet_sec() -> int:
    return _env_int(ENV_IDLE_QUIET, DEFAULT_IDLE_QUIET_SEC)


def idle_stalled_sec() -> int:
    return _env_int(ENV_IDLE_STALLED, DEFAULT_IDLE_STALLED_SEC)


def pair_window_sec() -> int:
    return _env_int(ENV_PAIR_WINDOW, DEFAULT_PAIR_WINDOW_SEC)


def projects_root() -> Path:
    """サブエージェントの記録の置き場。

    既定は dashlib.claude_config_dir()/projects。CLAUDE_CONFIG_DIR を使っている環境でも
    正しい場所を見るように、ホームを自分で組み立てないこと。
    """
    raw = os.environ.get(ENV_LIVE_ROOT, "").strip()
    if raw:
        return Path(raw).expanduser()
    return dashlib.claude_config_dir() / "projects"


# ---------------------------------------------------------------- 小道具

def parse_ts(value):
    """JSONL の timestamp を UTC の epoch 秒にする。

    Claude Code が書くのは '2026-09-01T00:03:38.526Z' という末尾 Z 形式だが、
    datetime.fromisoformat が Z を受け付けるのは Python 3.11 以降。このツールは 3.9 を
    最低要件と宣言している（install.py）ので、自分で置き換えてから渡す。
    tz が付いていない値には UTC を補う。state.json 側は +09:00 の aware なので、
    naive と混ぜると比較で TypeError になる。
    """
    if not isinstance(value, str) or not value:
        return None
    s = value.strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


_SEP = re.compile(r"[\\/]+")


def norm_path(p) -> str:
    """パスの見た目の揺れを吸収して比べられる形にする。

    Windows では区切りもドライブレターの大小も安定しない。実測で、同じ場所が
    'C:\\...' と 'c:/...' の両方で記録に現れる。
    """
    if not isinstance(p, str) or not p:
        return ""
    return _SEP.sub("/", p.strip()).rstrip("/").lower()


# 記録側は "claude-sonnet-5"、実機の meta.json は "sonnet" と、同じモデルが別表記で入る。
# 突き合わせのために共通の呼び名へ落とす。知らない表記は "" にして門番に使わない。
_MODEL_KEYS = ("opus", "sonnet", "haiku", "fable")


def model_key(value) -> str:
    if not isinstance(value, str):
        return ""
    low = value.lower()
    for k in _MODEL_KEYS:
        if k in low:
            return k
    return ""


# ツールごとに「いま何をしているか」の1行を作る。ここに出すのは引数の実物であって、
# 説明のために言葉を足さない（足した瞬間に推測になる）。
_LABEL_KEYS = (
    "description",   # Bash / Agent / Task
    "file_path",     # Read / Write / Edit
    "pattern",       # Grep / Glob
    "command",       # Bash（description が無いとき）
    "query",         # WebSearch / ToolSearch
    "url",           # WebFetch
    "skill",         # Skill
    "prompt",        # Agent 系
    "path",
)

MAX_LABEL = 120


def tool_label(inp) -> str:
    if not isinstance(inp, dict):
        return ""
    for key in _LABEL_KEYS:
        v = inp.get(key)
        if isinstance(v, str) and v.strip():
            one = " ".join(v.split())
            if len(one) > MAX_LABEL:
                one = one[: MAX_LABEL - 1] + "…"
            return one
    return ""


# ---------------------------------------------------------------- 1本の JSONL を読む

# 子を起動するツールの名前。ここで拾った tool_use のIDが、生まれた子の
# meta.json の toolUseId と一致する＝親子が実測で決まる。
# 実測（手元の全記録）: spawnDepth>=2 の 15 体すべてが親のログの "Agent" 呼び出しに
# 解決した。"Task" は同じ役割の旧名なので併せて見る（外れても親が出ないだけで害はない）。
SPAWN_TOOLS = ("Agent", "Task")


def _new_acc() -> dict:
    return {
        "firstTs": None,
        "lastTs": None,
        "toolCalls": 0,
        "openTools": {},   # tool_use_id -> True（結果がまだ来ていない呼び出し）
        "lastTool": None,  # {"name", "label", "at"}
        "spawns": {},      # tool_use_id -> True（この機体が起動した子の呼び出し）
        "tokens": None,
        "lines": 0,
    }


def _feed(acc: dict, row: dict) -> None:
    ts = parse_ts(row.get("timestamp"))
    if ts is not None:
        if acc["firstTs"] is None:
            acc["firstTs"] = ts
        acc["lastTs"] = ts
    acc["lines"] += 1

    msg = row.get("message")
    if not isinstance(msg, dict):
        return

    usage = msg.get("usage")
    if msg.get("role") == "assistant" and isinstance(usage, dict):
        # 最後の assistant 行の値だけを使う。累積合計にしないこと（冒頭の説明を読むこと）。
        acc["tokens"] = (
            (usage.get("input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
        )

    content = msg.get("content")
    if not isinstance(content, list):
        return
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "tool_use":
            acc["toolCalls"] += 1
            name = dashlib.as_str(block.get("name")) or "?"
            acc["lastTool"] = {
                "name": name,
                "label": tool_label(block.get("input")),
                "at": ts,
            }
            bid = dashlib.as_str(block.get("id"))
            if bid:
                acc["openTools"][bid] = True
                if name in SPAWN_TOOLS:
                    acc["spawns"][bid] = True
        elif kind == "tool_result":
            bid = dashlib.as_str(block.get("tool_use_id"))
            if bid:
                acc["openTools"].pop(bid, None)


def read_agent_file(path: Path):
    """1本の agent-*.jsonl を増分で読む。

    毎秒呼ばれるので、前回読んだ続きだけをパースする。ファイルは追記のみなので、
    サイズが戻っていたら（作り直された）最初から読み直す。末尾が書きかけの行に
    なっていることがあるため、最後の改行までしか消費しない。
    """
    key = str(path)
    try:
        st = path.stat()
    except OSError:
        with _LOCK:
            _file_cache.pop(key, None)
        return None

    with _LOCK:
        cached = _file_cache.get(key)

    # 読み切っているときだけ、そのまま返す速い道を通る。
    # offset を見ずにサイズと更新時刻だけで判定すると、末尾に読み残し（書きかけの行や、
    # 窓より長い行）があるファイルで永久に読み進めなくなる。追記が続いているうちは
    # 毎回サイズが変わるので露見しないが、そこで書き込みが止まると、その機体は
    # 読み残したところまでの古い値を出したまま固まる。
    if (cached and cached["size"] == st.st_size and cached["mtime"] == st.st_mtime_ns
            and cached["offset"] >= st.st_size):
        return cached["acc"]

    if cached and st.st_size >= cached["offset"]:
        offset = cached["offset"]
        # キャッシュ済みの acc をそのまま育てないこと。server.py は
        # ThreadingHTTPServer で、/api/state と /api/run が別スレッドで並行に走る
        # （タブを1回押すだけで、動き続けているポーリングと確実に重なる）。
        # 同じ dict を2スレッドが育てると、同じ増分を二重に数えて toolCalls が水増しされる。
        # 複製してから育て、書き戻しは size/mtime/offset/acc の4つ揃いで行う。
        # 負けた側の組は丸ごと捨てられるだけなので、取りこぼしも二重読みも起きない。
        acc = dict(cached["acc"])
        acc["openTools"] = dict(acc["openTools"])   # _feed が中身を直接いじるので浅い複製では足りない
        acc["spawns"] = dict(acc["spawns"])         # 同上
    else:
        offset = 0
        acc = _new_acc()

    dropped = 0
    try:
        with path.open("rb") as fh:
            fh.seek(offset)
            chunk = fh.read(MAX_READ_BYTES)
            if len(chunk) >= MAX_READ_BYTES and chunk.rfind(b"\n") < 0:
                # 1行が読み取り窓より長い（1つの tool_result に画像が何枚も入るとありうる）。
                # ここで諦めると offset が永久に進まず、この機体の live が二度と更新
                # されない——消えるか、古い値のまま凍って「無風」と出る。改行まで読み進める。
                parts, total = [chunk], len(chunk)
                while total < LINE_PARSE_CAP:
                    nxt = fh.read(MAX_READ_BYTES)
                    if not nxt:
                        break               # まだ書きかけ。次のティックでやり直す
                    parts.append(nxt)
                    total += len(nxt)
                    if b"\n" in nxt:
                        break
                chunk = b"".join(parts)
                if chunk.rfind(b"\n") < 0 and total >= LINE_PARSE_CAP:
                    # 読み切れないほど長い1行。中身は諦めて、改行の次まで飛ばす。
                    # 数え落とすのはその1行だけ。推測では埋めない。
                    while True:
                        nxt = fh.read(MAX_READ_BYTES)
                        if not nxt:
                            chunk = b""     # 未完。今回は何もせず次のティックへ
                            break
                        k = nxt.find(b"\n")
                        total += len(nxt)
                        if k >= 0:
                            dropped = total - len(nxt) + k + 1
                            chunk = b""
                            break
    except OSError:
        # Windows では書き込み中のファイルが一瞬開けないことがある。次のティックで拾う。
        return acc if cached else None

    cut = chunk.rfind(b"\n")
    consumed = chunk[: cut + 1] if cut >= 0 else b""

    if consumed:
        for line in consumed.decode("utf-8", "replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                _feed(acc, row)

    with _LOCK:
        _file_cache[key] = {
            "size": st.st_size,
            "mtime": st.st_mtime_ns,
            "offset": offset + len(consumed) + dropped,
            "acc": acc,
        }
    return acc


def _read_meta(path: Path) -> dict:
    ok, value, _err = dashlib.read_json_safe(path)
    return value if ok and isinstance(value, dict) else {}


# 起動時の指示文をどれだけ覚えておくか。対応づけの手がかりに使うだけなので全文は要らないが、
# 短く切りすぎると危険：似た指示で起動した2体は先頭が丸ごと同じで、違いが末尾にしか無い
# ことがある（実測で、37,941 文字のうち先頭 37,772 文字が完全に一致した例がある）。
PROMPT_KEEP = 48 * 1024

# 指示文に含まれるかを見るとき、これより短い語は手がかりにしない。
# 「A」のような短い名前はどの指示文にも現れてしまう。
MIN_NEEDLE = 4


def _first_row(path: Path) -> dict:
    """1行目だけ読む。cwd と sessionId、そして起動時の指示文が入っている。

    上限に PROMPT_KEEP を使わないこと。PROMPT_KEEP は _prompt_of の切り詰めに使う
    **文字数**だが、readline に渡すのは **バイト数**で、日本語の指示文は JSON の
    エスケープ込みで1文字が 1.7 バイト前後になる（実測：37,941 文字の指示文で1行
    63,404 バイト、84,686 文字で 140,031 バイト）。バイト側を PROMPT_KEEP に合わせると
    行の途中で切れ、json.loads が必ず失敗して cwd・sessionId・指示文をまとめて失う。
    _belongs は実質 cwd だけで決まるので、失うと候補列挙ごと落ちて live も
    liveOrphans も出なくなる——画面には何も無かったことになり、欠落に気づけない。
    実測では 475 本中 37 本（7.8%）がこれに当たり、その全部が Workflow 経由だった。
    行は丸ごと読み、切り詰めは _prompt_of に任せる。
    """
    try:
        with path.open("rb") as fh:
            raw = fh.readline(MAX_READ_BYTES)
    except OSError:
        return {}
    try:
        row = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {}
    return row if isinstance(row, dict) else {}


def _prompt_of(row: dict) -> str:
    """1行目から、そのエージェントに渡された指示文を取り出す。"""
    msg = row.get("message")
    if not isinstance(msg, dict):
        return ""
    content = msg.get("content")
    if isinstance(content, str):
        return content[:PROMPT_KEEP]
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict) and isinstance(b.get("text"), str):
                out.append(b["text"])
        return "".join(out)[:PROMPT_KEEP]
    return ""


# ---------------------------------------------------------------- 候補の列挙

def enumerate_agents(now=None) -> list:
    """実機のファイル一覧。ここでは glob と stat しかしない。

    実測（461 ファイル）: glob 68.9ms + stat 30.9ms = 約100ms。これに対し、全ファイルの
    1行目と meta.json まで読むと 1082ms かかった。1秒ポーリングには重すぎるので、
    中身を見るのは mtime で絞ったあと（_describe）に回す。直近3時間に触られたファイルは
    実測で 14 件しかなく、その 1行目読みは 5.5ms で済む。
    """
    now = time.time() if now is None else now
    ttl = _env_int(ENV_ENUM_TTL, DEFAULT_ENUM_TTL_SEC)
    with _LOCK:
        if _enum_cache["files"] and (now - _enum_cache["at"]) < ttl:
            return _enum_cache["files"]

    root = projects_root()
    found = []
    try:
        paths = sorted(root.glob("*/*/subagents/**/agent-*.jsonl"))
    except OSError:
        paths = []

    for p in paths:
        stem = p.name[: -len(".jsonl")]
        agent_id = stem[len("agent-"):]
        if not agent_id:
            continue
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        # projects/<slug>/<sessionId>/subagents/... なので、subagents の2つ上が slug。
        parts = p.parts
        try:
            si = len(parts) - 1 - parts[::-1].index("subagents")
            slug, session_id = parts[si - 2], parts[si - 1]
        except (ValueError, IndexError):
            slug, session_id = "", ""
        found.append({
            "agentId": agent_id,
            "path": p,
            "mtime": mtime,
            "slug": slug,
            "sessionId": session_id,
            "workflow": "workflows" in parts,
        })

    with _LOCK:
        _enum_cache["at"] = now
        _enum_cache["files"] = found
        # 消えたファイルのぶんを捨てる。サーバーは何日も動かしっぱなしになるので、
        # ここを掃除しないと読み取り位置と素性のキャッシュが片道で増え続ける。
        alive = {str(e["path"]) for e in found}
        for cache in (_file_cache, _describe_cache):
            for k in [k for k in cache if k not in alive]:
                cache.pop(k, None)
    return found


def describe(entry: dict) -> dict:
    """その機体の素性（cwd・モデル・説明）を足す。

    1行目と meta.json は機体が生まれたときに書かれてから変わらないので、一度読んだら
    ずっと使い回してよい。ここを毎ティック読み直すと列挙が10倍遅くなる。
    """
    key = str(entry["path"])
    with _LOCK:
        got = _describe_cache.get(key)
    if got is not None:
        return got

    p = entry["path"]
    stem = p.name[: -len(".jsonl")]
    meta = _read_meta(p.with_name(stem + ".meta.json"))
    head = _first_row(p)
    out = dict(entry)
    out.update({
        "prompt": _prompt_of(head),
        "cwd": dashlib.as_str(head.get("cwd")),
        "sessionId": dashlib.as_str(head.get("sessionId")) or entry["sessionId"],
        "description": dashlib.as_str(meta.get("description")),
        # この機体を起動した Agent 呼び出しのID。親のログの tool_use と突き合わせる。
        "toolUseId": dashlib.as_str(meta.get("toolUseId")),
        # 親そのものが書かれている個体もある（実データで確認）。あればこちらが確実。
        "parentAgentId": dashlib.as_str(meta.get("parentAgentId")),
        "agentType": dashlib.as_str(meta.get("agentType")),
        "model": dashlib.as_str(meta.get("model")),
        "spawnDepth": dashlib.as_num(meta.get("spawnDepth")),
    })
    # 素性がまったく読めなかったもの（生まれかけ）は覚え込まない。次のティックで読み直す。
    if out["cwd"] or out["description"] or out["model"]:
        with _LOCK:
            _describe_cache[key] = out
    return out


# ---------------------------------------------------------------- 実測値の組み立て

def measure(cand: dict, now: float) -> dict:
    """1機体の実測値。読めなければ None を返す（0 で埋めない）。"""
    acc = read_agent_file(cand["path"])
    if not acc or acc["firstTs"] is None:
        return {}
    last = acc["lastTs"] or acc["firstTs"]
    busy = len(acc["openTools"]) > 0
    idle = max(0, int(now - last))
    if busy:
        state = "active"          # ツールの結果待ち。沈黙ではない。
    elif idle >= idle_stalled_sec():
        state = "stalled"
    elif idle >= idle_quiet_sec():
        state = "quiet"
    else:
        state = "active"
    tool = acc["lastTool"] or {}
    return {
        "tool": dashlib.as_str(tool.get("name")),
        "toolLabel": dashlib.as_str(tool.get("label")),
        "toolCalls": acc["toolCalls"],
        "tokens": acc["tokens"],
        "elapsedSec": max(0, int(last - acc["firstTs"])),
        "idleSec": idle,
        "busy": busy,
        "state": state,
        "agentId": cand["agentId"],
        "model": cand["model"],
        "agentType": cand["agentType"],
        "description": cand["description"],
        "workflow": bool(cand["workflow"]),
    }


# ---------------------------------------------------------------- 記録と実機の対応づけ

def _belongs(cand: dict, want_path: str, want_slug: str) -> bool:
    """その実機がこのプロジェクトのものか。

    スラッグも cwd も単独では当てにならない（実測：日本語のディレクトリ名は1文字1ハイフンに
    潰れるので別プロジェクトが同じスラッグになりうるし、同じスラッグの下に別プロジェクトの
    cwd が混ざっている例が実在する）。どちらか一方でも一致すれば候補には入れ、
    最終的な結びつけは下の一意性で決める。
    """
    if want_path and norm_path(cand["cwd"]) == want_path:
        return True
    if want_slug and cand["slug"].lower() == want_slug.lower():
        return True
    return False


_PEER_TTL = 5.0
_peer_cache = {"at": 0.0, "keys": {}}


def _peer_records(want_path: str, slug: str, now: float) -> list:
    """同じ場所で走っている、他のミッションの稼働中の記録。

    `--project` で名前を分けても、実際に動いている場所（cwd）は同じなので
    project.path が一致する。すると「このプロジェクトの機体」という絞り込みが
    両チームで同じ集合を指し、片方のカードにもう片方の実機が載りうる。
    運用ルールが正式に案内している使い方なので、想定外ではない。

    ここで集めた記録は「その実機を欲しがっている別の誰か」として使う。
    欲しがる相手がいる実機は、どちらのカードにも載せない。
    """
    if not want_path:
        return []
    with _LOCK:
        fresh = (now - _peer_cache["at"]) < _PEER_TTL and _peer_cache["keys"]
        if not fresh:
            keys = {}
            try:
                for s in dashlib.list_slugs():
                    ok, value, _err = dashlib.read_json_safe(dashlib.state_file(s))
                    if not ok or not isinstance(value, dict):
                        continue
                    m = value.get("mission")
                    if not isinstance(m, dict) or m.get("phase") != "running":
                        continue
                    p = value.get("project") if isinstance(value.get("project"), dict) else {}
                    recs = [a for a in (value.get("agents") or [])
                            if isinstance(a, dict) and a.get("status") == "running"]
                    keys[s] = (norm_path(dashlib.as_str(p.get("path"))), recs)
            except Exception:
                keys = {}
            _peer_cache["at"] = now
            _peer_cache["keys"] = keys
        keys = _peer_cache["keys"]
    out = []
    for s, (p, recs) in keys.items():
        if s == slug or p != want_path:
            continue
        out.extend(recs)
    return out


def _tick_taken(now: float) -> dict:
    """同じリクエストのあいだだけ有効な台帳。

    build_payload() は稼働中の全チームぶん build_state を直列に呼ぶ。--project で
    ミッションを分けて同じセッションから2本回すと、同じ agentId が両方のカードに
    出うるので、先に取ったチームのものとする。
    """
    with _LOCK:
        if now - _ledger["at"] > 1.5:
            _ledger["at"] = now
            _ledger["taken"] = {}
        return _ledger["taken"]


def assign_live(agents: list, project_path: str, mission: dict, slug: str = "") -> list:
    """稼働中の機体に live を載せ、記録に無い実機の一覧を返す。

    ここで載せるのは実測値だけで、推測はしない。対応づけに確信が持てない機体には
    live を載せない（別の機体の数字をカードに出すのが最悪の結果なので、
    「分からない」を「たぶんこれ」より優先する）。
    """
    for a in agents:
        a["live"] = None

    if not isinstance(mission, dict) or mission.get("phase") != "running":
        return []

    # **指令塔は外す。** 指令塔は主セッションであって、サブエージェントではない。
    # その記録は <slug>/<sessionId>.jsonl であって subagents/ の下には無いので、
    # agent-*.jsonl が指令塔であることは原理的にありえない。
    # 外さないと、残った候補が1つのときに規則4（双方向の一意）が成立して、
    # **別の機体の数字が指令塔のカードに載る**。実測（2026-09-02）: 下請けが自分で
    # 起動した孫が指令塔のカードに載った。孫の meta.json には model が無く
    # （実データで確認）、モデル一致の門は「両方に値があるときだけ」外すので素通りする。
    running = [a for a in agents
               if a.get("status") == "running"
               and dashlib.as_str(a.get("id")) != dashlib.COMMAND_ID]
    if not running:
        return []

    now = time.time()
    started = parse_ts(dashlib.as_str(mission.get("startedAt")))
    floor = (started - MISSION_SLACK_SEC) if started is not None else None

    want_path = norm_path(project_path)
    want_slug = dashlib.slug_for_path(Path(project_path)) if project_path else ""
    if not want_path and not want_slug:
        return []   # どのプロジェクトの記録かを確かめる手がかりが無い。何も出さない。

    taken = _tick_taken(now)
    cands = []
    known_desc = {}          # agentId -> description（候補に残らなかった機体も含む）
    for entry in enumerate_agents(now):
        if taken.get(entry["agentId"], slug) != slug:
            continue
        # 中身を見る前に mtime でふるいにかける。ミッションが始まる前で更新が止まっている
        # ファイルは、このミッションの機体ではありえない。
        if floor is not None and entry["mtime"] < floor:
            continue
        c = describe(entry)
        known_desc[c["agentId"]] = c["description"]
        if not _belongs(c, want_path, want_slug):
            continue
        m = measure(c, now)
        if not m:
            continue
        acc = read_agent_file(c["path"])
        if floor is not None and acc["firstTs"] < floor:
            continue
        # 対応づけにだけ使う手がかりは _ 始まりにして持ち回り、画面へ渡す前に落とす。
        m["_firstTs"] = acc["firstTs"]
        m["_prompt"] = c.get("prompt") or ""
        m["_toolUseId"] = c.get("toolUseId") or ""
        m["_parentAgentId"] = c.get("parentAgentId") or ""
        m["_spawns"] = list(acc["spawns"])
        cands.append(m)
    if not cands:
        return []

    window = pair_window_sec()

    def compatible(rec, cand) -> bool:
        rm, cm = model_key(rec.get("model")), model_key(cand["model"])
        if rm and cm and rm != cm:
            return False
        rs = parse_ts(dashlib.as_str(rec.get("startedAt")))
        if rs is not None and abs(cand["_firstTs"] - rs) > window:
            return False
        return True

    # 同じ場所で走っている別のミッションの記録。その実機を欲しがる相手がいるなら、
    # どちらのカードにも載せない。載せる側から見ると「候補が1つしか残っていないから
    # これだろう」に見えるが、その1つが隣のチームの機体でも同じように見える。
    peers = _peer_records(want_path, slug, now)

    by_id = {c["agentId"]: c for c in cands}
    pairs = {}   # record_id -> agentId
    used = set()
    # 前回の対応はミッションごとに持つ。slug だけで持つと、同じ記録IDを使い回した
    # 次のミッションが、前のミッションの無関係な機体の実測値を引き継いでしまう。
    sticky_key = slug + "|" + dashlib.as_str(mission.get("startedAt"))
    prev = _sticky.get(sticky_key, {})

    # 0. 起動呼び出しのIDが一致するもの。**推測がいっさい入らない唯一の規則**で、
    #    ほかのどれよりも強い。記録側の toolUseId は hook が自動で登録したときに入り
    #    （update_state.py hook）、実機側は meta.json に書かれている。同じ Agent
    #    呼び出しから出た2つの値なので、一致は「同じもの」を意味する。
    #
    #    **compatible() の門を通さない。** あの門はモデル表記と時刻のずれで
    #    「たぶん違う」を落とすためのもので、確実な手がかりに重ねる意味がない。
    #    重ねると、モデル名の書き方が違うだけで確実な対応づけを捨てることになる。
    for rec in sorted(running, key=lambda r: r["id"]):
        tuid = dashlib.as_str(rec.get("toolUseId")).strip()
        if not tuid:
            continue
        hits = [c for c in cands
                if c["agentId"] not in used and c["_toolUseId"] == tuid]
        if len(hits) == 1:
            pairs[rec["id"]] = hits[0]["agentId"]
            used.add(hits[0]["agentId"])

    # 1. 名前が Agent ツールの description と完全に一致するもの。運用でこの2つを
    #    そろえてもらえば、ここだけで決まる（Workflow 経由には description が無い）。
    for rec in sorted(running, key=lambda r: r["id"]):
        if rec["id"] in pairs:
            continue
        name = dashlib.as_str(rec.get("name")).strip()
        if not name:
            continue
        hits = [c for c in cands
                if c["agentId"] not in used
                and c["description"].strip() == name
                and compatible(rec, c)]
        if len(hits) == 1:
            pairs[rec["id"]] = hits[0]["agentId"]
            used.add(hits[0]["agentId"])

    # 2. 記録の名前か任務が、その機体へ渡した指示文にそのまま現れているか。
    #    Workflow ツールで起動した機体には meta.json に description が無いので、規則1は
    #    一度も発火しない。そこで「指示文に、その語句が入っているか」を手がかりにする。
    #    似ている度合いではなく**そのまま含まれるか**だけを見るのは、似ている度合いで
    #    順位を付けると、僅差のときに毎ティック順位が入れ替わるため。
    #    片側に1つ、反対側にも1つ、という双方向の一意性を満たすときだけ結ぶ。
    def needles(rec):
        return [s for s in (dashlib.as_str(rec.get("name")).strip(),
                            dashlib.as_str(rec.get("mission")).strip())
                if len(s) >= MIN_NEEDLE]

    def named(rec, cand) -> bool:
        p = cand.get("_prompt") or ""
        return bool(p) and any(n in p for n in needles(rec))

    open_recs = [r for r in sorted(running, key=lambda r: r["id"]) if r["id"] not in pairs]
    for rec in open_recs:
        hits = [c for c in cands
                if c["agentId"] not in used and named(rec, c) and compatible(rec, c)]
        if len(hits) != 1:
            continue
        rivals = [o for o in open_recs
                  if o["id"] != rec["id"] and o["id"] not in pairs
                  and named(o, hits[0]) and compatible(o, hits[0])]
        # 隣のミッションの記録も見る。班全体への共通の前置きが渡っていると、
        # その1体の指示文に両チームの名前が出てくることがある。
        rivals += [o for o in peers if named(o, hits[0]) and compatible(o, hits[0])]
        if rivals:
            continue
        pairs[rec["id"]] = hits[0]["agentId"]
        used.add(hits[0]["agentId"])

    # 3. 前回の対応を引き継ぐ。毎ティック解き直すと、僅差のときに2枚のカードの数字が
    #    入れ替わる（静止画では絶対に気づけない壊れ方になる）。
    for rec in sorted(running, key=lambda r: r["id"]):
        if rec["id"] in pairs:
            continue
        aid = prev.get(rec["id"])
        if aid and aid in by_id and aid not in used and compatible(rec, by_id[aid]):
            pairs[rec["id"]] = aid
            used.add(aid)

    # 4. 双方向に一意なときだけ結ぶ。1体の記録に候補が1つしかなく、その候補を
    #    欲しがっている記録も1つだけ、という場合に限る。少しでも迷ったら結ばない。
    remaining = [r for r in sorted(running, key=lambda r: r["id"]) if r["id"] not in pairs]
    fits = {r["id"]: [c for c in cands if c["agentId"] not in used and compatible(r, c)]
            for r in remaining}
    for rec in remaining:
        mine = fits[rec["id"]]
        if len(mine) != 1:
            continue
        only = mine[0]
        if only["agentId"] in used:
            continue
        rivals = [rid for rid, lst in fits.items()
                  if rid != rec["id"] and any(c["agentId"] == only["agentId"] for c in lst)]
        # 隣のミッションにも、その実機と矛盾しない記録があるなら結ばない。
        # この規則は「他に候補が無いから」で結ぶので、見えていない相手がいると
        # そのまま隣のチームの機体を取ってしまう。
        rivals += [o for o in peers if compatible(o, only)]
        if rivals:
            continue
        pairs[rec["id"]] = only["agentId"]
        used.add(only["agentId"])

    def public(c: dict) -> dict:
        """対応づけ用の手がかり（_ 始まり）を落として、画面へ渡す形にする。"""
        return {k: v for k, v in c.items() if not k.startswith("_")}

    for rec in running:
        aid = pairs.get(rec["id"])
        if not aid:
            continue
        rec["live"] = public(by_id[aid])
        taken[aid] = slug

    with _LOCK:
        _sticky[sticky_key] = dict(pairs)
        if len(_sticky) > 64:      # 終わったミッションのぶんを溜め込まない
            for k in list(_sticky)[:-32]:
                _sticky.pop(k, None)

    # 記録に無い実機の親を、実測で辿る。meta.json の toolUseId はその機体を起動した
    # Agent 呼び出しのIDで、同じIDは親のログに tool_use として現れる。だから親子は
    # **推測ではなく実測**で決まる（系統樹に線を引かないのは変えない。ここで出すのは
    # 素性だけで、線を引けば「どの世代のどこに置くか」という推測が必ず入るため）。
    owner = {}
    for c in cands:
        for tid in (c.get("_spawns") or ()):
            owner[tid] = c["agentId"]
    rec_of_agent = {aid: rid for rid, aid in pairs.items()}
    name_of_rec = {dashlib.as_str(r.get("id")): dashlib.as_str(r.get("name")) for r in agents}
    desc_of_agent = dict(known_desc)
    for c in cands:
        desc_of_agent[c["agentId"]] = c["description"]

    orphans = []
    for c in sorted(cands, key=lambda x: x["agentId"]):
        if c["agentId"] in used:
            continue
        o = public(c)
        # meta.json に親が直接書いてあればそれを使う。無いときだけ、起動呼び出しの
        # IDを親のログの tool_use と突き合わせる。どちらも実測で、推測は入らない。
        pid = c.get("_parentAgentId") or owner.get(c.get("_toolUseId") or "")
        if pid:
            # 親がカードに結ばれていればその名前を、まだなら親自身の説明を出す。
            o["parentAgentId"] = pid
            o["parentName"] = (name_of_rec.get(rec_of_agent.get(pid, ""), "")
                               or desc_of_agent.get(pid, ""))
        orphans.append(o)
    return orphans


def measure_for(project_path: str, name: str, model: str, started_at: str,
                mission: str = "", others=()):
    """完了した1体の実測値を、記録に焼き付けるために取り直す。

    対応が一意に決まらなければ None を返す。ここで曖昧なまま返すと、別の機体の数字を
    記録に永久に書き込むことになる（画面のちらつきと違って、あとから直せない）。
    """
    now = time.time()
    want_path = norm_path(project_path)
    want_slug = dashlib.slug_for_path(Path(project_path)) if project_path else ""
    if not want_path and not want_slug:
        return None
    rs = parse_ts(dashlib.as_str(started_at))
    if rs is None:
        # 起動時刻が無いと時間窓が丸ごと外れ、何年前の機体でも候補に残る。
        # 記録に永久に残る値をそんな状態で決めない。
        return None
    window = pair_window_sec()
    rm = model_key(model)
    floor = rs - MISSION_SLACK_SEC
    hits = []
    for entry in enumerate_agents(now):
        if entry["mtime"] < floor:
            continue
        c = describe(entry)
        if not _belongs(c, want_path, want_slug):
            continue
        cm = model_key(c["model"])
        if rm and cm and rm != cm:
            continue
        desc = c["description"].strip()
        if name and desc and desc != name.strip():
            continue
        m = measure(c, now)
        if not m:
            continue
        acc = read_agent_file(c["path"])
        if abs(acc["firstTs"] - rs) > window:
            continue
        m["_prompt"] = c.get("prompt") or ""
        # description が名前と一致していれば、それ自体が身元の裏付けになる。
        m["_named"] = bool(name) and desc == name.strip()
        hits.append(m)

    # **身元の裏付けは、候補が1体のときも必須。** ここを省くと、
    # 「たまたま1体しか残らなかった」だけで別の機体の数字を記録へ永久に焼き付ける。
    # Workflow 経由の実機は description が空なので、名前の門番は素通りしてしまう。
    keys = [s for s in (dashlib.as_str(name).strip(), dashlib.as_str(mission).strip())
            if len(s) >= MIN_NEEDLE]

    def backed(h) -> bool:
        return bool(h["_named"]) or (bool(keys) and any(k in h["_prompt"] for k in keys))

    hits = [h for h in hits if backed(h)]
    if len(hits) != 1:
        return None

    # 双方向の一意性（assign_live の規則2と同じ考え方）。その指示文が他の機体の
    # 名前や任務にも触れているなら、そこから本人だとは言えない。班全体への
    # 共通の前置きを渡された隣の機体が、そのまま当たってしまう。
    if not hits[0]["_named"]:
        p = hits[0]["_prompt"]
        for o in others or ():
            for s in (dashlib.as_str(o.get("name")).strip(),
                      dashlib.as_str(o.get("mission")).strip()):
                if len(s) >= MIN_NEEDLE and s in p:
                    return None

    return {k: v for k, v in hits[0].items() if not k.startswith("_")}
