#!/usr/bin/env python3
"""Subagent Dashboard — 共通ロジック

server.py と update_state.py が共有する。プロジェクトの識別・状態ファイルの読み書き・
孫の自己申告のマージをここに集約している。外部ライブラリは使わない。

ディレクトリ構成:
    ~/.claude/agent-dashboard/
    ├─ dashlib.py            このファイル
    ├─ server.py             配信サーバー
    ├─ update_state.py       状態更新CLI
    ├─ public/index.html     画面
    ├─ missions/
    │  └─ <slug>/            プロジェクトごとに分離される
    │     ├─ state.json      いま画面に映すミッション（形は昔から変えていない）
    │     ├─ agents/         孫の自己申告（1体1ファイル）
    │     └─ history/        過去のミッション（start のたびに1件増える）
    │        └─ <runId>/     runId は YYYYMMDD-HHMMSS（そのミッションの開始時刻）
    │           ├─ state.json
    │           └─ agents/
    └─ trash/                削除したプロジェクト・過去の記録の置き場
                             （フォルダを戻せば復旧できる）

置き場所を差し替える環境変数（**2つある。意味がまったく違う。取り違え注意**）:

    AGENT_DASHBOARD_DATA_HOME … 「記録の置き場」だけを差し替える。
        これを設定すると missions/ と trash/ がそこに移る。**コード（本体）の
        場所には一切影響しない。** 試験や一時的な隔離はこちらを使うこと。

    AGENT_DASHBOARD_HOME … 歴史的に2つの意味を兼ねてしまっている。
        ・dashlib（Python 側）      … 記録の置き場（＝上と同じ意味）
        ・extension/extension.js の ensureHome() … ダッシュボード本体（コード）の場所

    ⚠️ この取り違えが実際に事故を起こしている。拡張の試験で「記録だけを一時フォルダへ
       逃がす」つもりで AGENT_DASHBOARD_HOME を設定しても、拡張側ではそれが
       「本体の場所」の指定として解釈される。結果、記録は逃げないまま
       **本物の missions/ を読むサーバーが立ち上がり、実データを壊した。**
       記録だけを移したいときは必ず AGENT_DASHBOARD_DATA_HOME を使うこと。
       AGENT_DASHBOARD_HOME の既存の意味は変えていない（使っている人がいるため）。

    優先順位: AGENT_DASHBOARD_DATA_HOME → AGENT_DASHBOARD_HOME
              → ツールと同じディレクトリ → OS 標準のユーザーデータ置き場
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import unicodedata
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

import i18n  # noqa: E402  （文言の翻訳。i18n.py は dashlib を import しない）
from i18n import t  # noqa: E402

#: read_json_safe が「ファイルが無い」ときに返す説明の**原文**。
#: 突き合わせは必ず is_not_created() を通すこと。訳文を直に書いて比べると、
#: 言語を変えた瞬間に判定だけが静かに外れる（「記録が無い」を「壊れている」と
#: 読み違えて、警告が出っぱなしになる）。
ERR_NOT_CREATED = "not created yet"


def is_not_created(err: str) -> bool:
    """read_json_safe の説明が「ファイルがまだ無い」か。

    表示用の文を判定に使うのは本来よくないが、read_json_safe の戻り値の形
    （成功したか, 中身, **説明**）は呼び手が何箇所もあって変えにくい。せめて
    突き合わせを1箇所に閉じ込めて、訳文が各所に散らばらないようにする。
    """
    return err == t(ERR_NOT_CREATED)

COMMAND_ID = "COMMAND"
MAX_LOG = 300
MAX_DEPTH = 16  # 世代の探索上限（親子関係が循環しても止まるように）
STATUSES = ("standby", "running", "done")
PHASES = ("standby", "running", "done")

ENV_PROJECT = "AGENT_DASHBOARD_PROJECT"

# ENV_HOME は「記録の置き場」と「本体（コード）の場所」の2つの意味を兼ねてしまっている
# （後者は extension/extension.js の ensureHome()）。ENV_DATA_HOME は前者だけを指す。
# 記録だけを移したいとき（試験・一時的な隔離）は必ず ENV_DATA_HOME を使うこと。
# 詳しくはモジュール冒頭の説明を読むこと。
ENV_HOME = "AGENT_DASHBOARD_HOME"
ENV_DATA_HOME = "AGENT_DASHBOARD_DATA_HOME"

# 既定の「稼働中とみなす」時間窓（秒）。running のまま放置された記録を
# いつまでも画面に出し続けないための保険。
DEFAULT_ACTIVE_WINDOW_SEC = 3 * 60 * 60
ENV_ACTIVE_WINDOW = "AGENT_DASHBOARD_ACTIVE_WINDOW"

# history/ に残す過去のミッションの件数。超えた分は古い順に trash/ へ移す。
# 0 にすると退避そのものをしない（履歴を残さない＝昔の動作）。
DEFAULT_HISTORY_KEEP = 20
ENV_HISTORY_KEEP = "AGENT_DASHBOARD_HISTORY_KEEP"

# Windows と macOS はパスの大文字小文字を区別しない。スラッグ算出で揃えるため。
CASE_INSENSITIVE_FS = sys.platform in ("win32", "darwin")


# ---------------------------------------------------------------- 置き場所の決定

TOOL_ROOT = Path(__file__).resolve().parent
PUBLIC_DIR = TOOL_ROOT / "public"


def doc_path(stem: str) -> Path:
    """README / OPERATION の、**いまの表示言語のもの**を返す。

    英語版が `README.md`、他は `README.ja.md` のように接尾辞が付く。

    対応表をここ1箇所に置いているのは、案内する側（install.py が CLAUDE.md に
    書く手引き、diagnose.py が出す「困ったらこれを読め」）が増えるたびに同じ
    対応表を書き写すと、言語を足したときに片方だけ直し忘れるため。
    英語版へ落とすのは、その言語の版が無いときだけでよい。
    """
    lang = i18n.get_lang()
    if lang == "en":
        return TOOL_ROOT / f"{stem}.md"
    localized = TOOL_ROOT / f"{stem}.{lang}.md"
    return localized if localized.exists() else TOOL_ROOT / f"{stem}.md"


# ------------------------------------------------------- 運用ルールの書き先（CLI ごと）
#
# 運用ルールの**本文はどの CLI でも同じ**（呼ぶのは同じ update_state.py で、
# update_state.py はモデル ID を見ていない）。違うのは「その CLI が起動時に必ず読む
# ファイルはどれか」だけ。Claude Code は ~/.claude/CLAUDE.md、Codex CLI は
# ~/.codex/AGENTS.md を読む。
#
# 対応表をここ1箇所に置いているのは、書く側（install.py）と読む側（diagnose.py /
# auto_setup.py / 下の版チェック）がファイルを跨いでいるため。片方にだけ CLI を足すと
# 「書き込んだのに未設定と言われる」噛み合わせ事故になり、症状から原因に辿り着けない。
#
# **組み込みの表は「よく使われる CLI の近道」であって、対応できる範囲ではない。**
# 知らない CLI や、これから出てくる CLI にも書けなければ意味が無いので、表は
#
#   1. ここの組み込み
#   2. 利用者が足した分（AGENTS_FILE の JSON。同じ鍵なら利用者側が勝つ）
#
# を重ねたものとして扱う。install.py --agent-file <パス> は 2 に1件足してから書く。
# 新しい CLI が出ても、このファイルを配り直さずに追随できる形にしてある。
#
#   key      : 鍵。コマンドライン（--agent）と JSON で指す名前
#   label    : 画面に出す名前。**訳さない**（製品名なので、どの言語でも同じ綴り）
#   home_env : 設定フォルダの場所を変える環境変数。無ければ ""
#   home     : 既定の設定フォルダ。"~" から書く
#   file     : その CLI が起動時に読むファイルの名前
# file にフォルダを含めてよい（"rules/subagent-dashboard.md"）。1つのファイルではなく
# **ルール置き場のフォルダを丸ごと読む** CLI が実際にあり、そこには専用の1枚を置くのが
# 一番行儀がよい（既存のルールに追記すると、その CLI の作法と喧嘩する）。
#
# ここに無い CLI は install.py --agent-file で足せる。**表に載っていないことは
# 「対応していない」を意味しない。** 表は近道であって、境界ではない。
#
# 印の意味:
#   [確認済] 公式ドキュメント/リポジトリで場所を確かめたもの
#   [未確認] 二次情報しか取れなかったもの。設定フォルダが実在するときだけ書くので
#            外していても実害は小さいが、直す価値はある
BUILTIN_AGENT_TARGETS: tuple[dict, ...] = (
    # [確認済]
    {"key": "claude", "label": "Claude Code", "home_env": "CLAUDE_CONFIG_DIR",
     "home": "~/.claude", "file": "CLAUDE.md"},
    {"key": "codex", "label": "Codex CLI", "home_env": "CODEX_HOME",
     "home": "~/.codex", "file": "AGENTS.md"},
    {"key": "gemini", "label": "Gemini CLI", "home_env": "GEMINI_CLI_HOME",
     "home": "~/.gemini", "file": "GEMINI.md"},
    {"key": "copilot", "label": "GitHub Copilot CLI", "home_env": "COPILOT_HOME",
     "home": "~/.copilot", "file": "copilot-instructions.md"},
    {"key": "opencode", "label": "opencode", "home_env": "OPENCODE_CONFIG_DIR",
     "home": "~/.config/opencode", "file": "AGENTS.md"},
    # Amp は ~/.config/AGENTS.md も読むが、そちらは狙わない。~/.config は Amp を
    # 入れていなくても大抵あるので、自動判定が誰の環境にも書き込んでしまう。
    {"key": "amp", "label": "Amp", "home_env": "",
     "home": "~/.config/amp", "file": "AGENTS.md"},
    # ルール置き場が「フォルダ」の CLI。専用の1枚を置く。
    {"key": "cline", "label": "Cline", "home_env": "",
     "home": "~/Documents/Cline/Rules", "file": "subagent-dashboard.md"},
    {"key": "roo", "label": "Roo Code", "home_env": "",
     "home": "~/.roo", "file": "rules/subagent-dashboard.md"},
    # [未確認]
    {"key": "windsurf", "label": "Windsurf", "home_env": "",
     "home": "~/.codeium/windsurf/memories", "file": "global_rules.md"},
    {"key": "qwen", "label": "Qwen Code", "home_env": "",
     "home": "~/.qwen", "file": "QWEN.md"},
)

# 載せていない CLI と、その理由（消さないこと。次に調べ直す人が同じ道を辿らないように）:
#   Cursor  — 利用者ごとのルールファイルが無い。読むのはリポジトリ内の AGENTS.md だけ
#   Aider   — 起動時に必ず読む指示ファイルという仕組みが無い（設定で明示的に指すやり方）
# どちらも、リポジトリ内のファイルを --agent-file で指せば同じことができる。

#: 利用者が足した CLI を置く JSON。場所は環境変数で変えられる（試験用）。
ENV_AGENTS_FILE = "AGENT_DASHBOARD_AGENTS_FILE"

AGENT_ENTRY_KEYS = ("key", "label", "home_env", "home", "file")


def agents_file() -> Path:
    """利用者が足した CLI の一覧（JSON）の場所。

    AGENTS_FILE を直に読まずこの関数を通すのは、環境変数での差し替えを
    **呼ばれた時点で**効かせるため（取り込み時に固めると試験で差し替えられない）。
    """
    env = os.environ.get(ENV_AGENTS_FILE)
    if env and env.strip():
        return Path(env).expanduser()
    return AGENTS_FILE


def _clean_entry(raw: object) -> dict | None:
    """JSON の1件を表の形に整える。使えないものは None（**捨てるが落とさない**）。

    ここで例外にすると、書き損じた JSON が1つあるだけで update_state.py 全体が
    動かなくなる。運用ルールを書く道具が、設定ファイルの誤字で本業を止めてよい
    理由が無い。使える行だけ拾って進む。
    """
    if not isinstance(raw, dict):
        return None
    key = str(raw.get("key", "")).strip().lower()
    name = str(raw.get("file", "")).strip()
    home = str(raw.get("home", "")).strip()
    if not key or not name or not home:
        return None
    # パス区切りや空白を含む鍵は、--agent の値としても JSON の見出しとしても
    # 扱いにくいので受け付けない（フォルダ名に化ける場所がある）。
    if any(ch in key for ch in "/\\ \t"):
        return None
    return {
        "key": key,
        "label": str(raw.get("label", "")).strip() or key,
        "home_env": str(raw.get("home_env", "")).strip(),
        "home": home,
        "file": name,
    }


def load_user_agents() -> list[dict]:
    """利用者が足した CLI。ファイルが無い・壊れているときは空リスト。"""
    path = agents_file()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    # {"agents": [...]} でも [...] でも受ける。手で書く人が迷わないように。
    if isinstance(raw, dict):
        raw = raw.get("agents")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        entry = _clean_entry(item)
        if entry and entry["key"] not in seen:
            seen.add(entry["key"])
            out.append(entry)
    return out


def add_user_agent(entry: dict) -> None:
    """利用者の一覧に1件足す（同じ鍵があれば置き換える）。

    書けなければ OSError をそのまま投げる。ここを握り潰すと「登録したのに
    次回いなくなっている」になり、利用者は原因を追えない。
    """
    cleaned = _clean_entry(entry)
    if cleaned is None:
        raise ValueError("invalid agent entry: %r" % (entry,))
    others = [e for e in load_user_agents() if e["key"] != cleaned["key"]]
    path = agents_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"agents": others + [cleaned]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def agent_targets() -> list[dict]:
    """組み込みと利用者定義を重ねた、いま有効な CLI の一覧。

    同じ鍵があれば**利用者側が勝つ**。組み込みの想定が古くなった（CLI 側が読む
    ファイルを変えた）ときに、配り直しを待たずに手元で直せるようにするため。
    """
    merged = {e["key"]: dict(e) for e in BUILTIN_AGENT_TARGETS}
    for entry in load_user_agents():
        merged[entry["key"]] = entry
    return list(merged.values())


def agent_keys() -> tuple[str, ...]:
    return tuple(e["key"] for e in agent_targets())


def _agent_entry(key: str) -> dict:
    for entry in agent_targets():
        if entry["key"] == key:
            return entry
    raise KeyError(key)


def agent_label(key: str) -> str:
    """画面に出す CLI の名前。**訳さない**（製品名なので、どの言語でも同じ綴り）。"""
    return _agent_entry(key)["label"]


def agent_config_dir(key: str) -> Path:
    """その CLI の設定ディレクトリ（場所を変える環境変数があればそれを尊重する）。"""
    entry = _agent_entry(key)
    env_name = entry.get("home_env") or ""
    env = os.environ.get(env_name) if env_name else None
    if env and env.strip():
        return Path(env).expanduser().resolve()
    return Path(entry["home"]).expanduser().resolve()


def instruction_file(key: str) -> Path:
    """その CLI が起動時に読む、運用ルールを書き込むファイル。"""
    return agent_config_dir(key) / _agent_entry(key)["file"]


def claude_config_dir() -> Path:
    """Claude の設定ディレクトリ（CLAUDE_CONFIG_DIR があればそれを尊重する）。"""
    return agent_config_dir("claude")


def present_agents() -> list[str]:
    """設定フォルダが実在する CLI。**入っていない CLI に書き込まないため**の判定。

    フォルダの有無だけを見る。CLI 本体を PATH から探しにいかないのは、拡張や
    パッケージ管理ごとに置き場所が違って当てにならないうえ、置き場所が分からない
    だけで「未対応」と表示してしまうため。設定フォルダは必ずホーム直下にできる。
    """
    out = []
    for key in agent_keys():
        try:
            if agent_config_dir(key).is_dir():
                out.append(key)
        except OSError:  # 壊れたパスを書かれても、他の CLI の判定は続ける
            continue
    return out


# ------------------------------------------- 運用ルールに書いた版（CLI ごとに古くなる）
#
# 本体（コード）と運用ルールは**別々に古くなる**。本体は拡張の更新や上書きコピーで
# 新しくなるが、運用ルールは誰かが install.py を実行し直すまで古いまま残る（初期設定は
# 一度成功すると自動では二度と走らない）。運用ルールが増えた版では、増えたぶんが
# エージェントに届かないまま次の作業が始まってしまう。
#
# **判定をここに置いているのは、dashlib が必ず配られるため。** 同じことを auto_setup.py に
# 書くと、開発ディレクトリでは動くのに配布物では動かない（auto_setup.py は .vsix に
# 同梱しない＝ build_vsix.PAYLOAD_SKIP）。書く側（install.py）もここの定数を使う。

# しるしの**中身**は CLI が増えても変えない。CLAUDE.md と AGENTS.md で別のしるしに
# すると、片方しか外せない --uninstall ができあがる。
BLOCK_BEGIN = "<!-- agent-dashboard:begin -->"
BLOCK_END = "<!-- agent-dashboard:end -->"

# 版のしるしは囲みの**内側**に置く。BEGIN / END は決して変えない。変えると、それ以前に
# 書き込んだブロックを見つけられなくなり、差し替えのつもりが二重書き込みになる。
BLOCK_VERSION_MARK = "<!-- agent-dashboard:version "


def tool_version() -> str:
    """いま動いている本体の版。読めなければ空文字。"""
    try:
        return (TOOL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def instruction_text(key: str) -> str | None:
    """その CLI の運用ルールファイルの中身。読めなければ None。"""
    target = instruction_file(key)
    if not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except OSError:
        return None


def block_installed(key: str) -> bool:
    """その CLI の運用ルールファイルに、いま動いているこの本体の運用ルールがあるか。

    マーカーだけでなくパスも見る。同じツールのコピーが複数あるとき、運用ルールが別の
    コピーを指していれば、ここは False でなければならない（記録の書き込み先が分かれる）。
    """
    text = instruction_text(key)
    if text is None:
        return False
    if BLOCK_BEGIN not in text or BLOCK_END not in text:
        return False
    us = str(TOOL_ROOT / "update_state.py")
    return us in text or us.replace("\\", "/") in text


def installed_agents() -> list[str]:
    """運用ルールが書き込まれている CLI。1つも無ければ空リスト（＝未設定）。"""
    return [key for key in agent_keys() if block_installed(key)]


def block_version(key: str) -> str | None:
    """その CLI に書かれているブロックの版。しるしが無ければ None。

    0.4.1 までのブロックにはしるしが無いので、そこから更新すると必ず None になる
    ＝「古い」と判定される。実際に古いので、これが正しい。
    """
    text = instruction_text(key)
    if text is None:
        return None
    start = text.find(BLOCK_BEGIN)
    if start == -1:
        return None
    stop = text.find(BLOCK_END, start)
    if stop == -1:
        return None

    block = text[start:stop]
    i = block.find(BLOCK_VERSION_MARK)
    if i == -1:
        return None
    j = block.find("-->", i)
    if j == -1:
        return None
    return block[i + len(BLOCK_VERSION_MARK):j].strip() or None


def unwired_agents() -> list[str]:
    """入っているのに運用ルールが書かれていない CLI。

    **セットアップのあとに CLI を入れた人が必ず落ちる穴。** 初期設定は「そのとき
    入っていた CLI」にしか書かない（入れていない CLI のフォルダを勝手に作らない
    ため）。あとから別の CLI を入れると、そちらには何も書かれていないまま、
    画面には何も出ない状態が続く。

    1つでも書けていれば設定済みと見なす判定だけだと、この状態が「緑」に見える。
    見えるようにするための判定をここに1つ置き、update_state / server / diagnose /
    auto_setup の4か所が同じ規則を使う。
    """
    written = set(installed_agents())
    return [key for key in present_agents() if key not in written]


def unwired_agent_notice() -> str | None:
    """後から入れた CLI に運用ルールが届いていなければ、知らせる文面を返す。

    まだ1つも書いていない人には返さない（その人向けの案内は初回セットアップ側が
    持っていて、ここで重ねると初回の画面が警告だらけになる）。stale_block_notice と
    同じ考え方で、文面を返すだけで印字はしない。
    """
    if not installed_agents():
        return None
    pending = unwired_agents()
    if not pending:
        return None

    names = ", ".join(agent_label(key) for key in pending)
    return (
        t("  ⚠️  {names} is installed, but the operating rules have not been "
          "written for it.").format(names=names)
        + "\n"
        + t("      It was probably installed after the setup ran. "
            "Until you write them,")
        + "\n"
        + t("      subagents started from it will not show up on the screen. Please run:")
        + "\n"
        + f"        python {TOOL_ROOT / 'install.py'}\n"
        + t("      (Only the marked block is written. Nothing else is touched.)")
    )


def stale_block_notice() -> str | None:
    """運用ルールが本体より古ければ、知らせる文面を返す。古くなければ None。

    文面を返すだけで印字はしない。呼び手（update_state の start / server の起動 /
    diagnose）で出し方が違うので、ここで print すると出し分けができなくなる。

    まだ設定していない人には None を返す。その人向けの案内は初回セットアップ側が
    持っていて、ここで重ねると初回の画面が警告だらけになって肝心の手順が埋もれる。

    書き込み先が複数あるときは**古いものだけ**を挙げる。両方に書いてあって片方だけ
    古い（CLI を後から足した直後がこれ）ときに、全部を挙げると直す先が分からない。
    """
    stale: list[str] = []
    current = tool_version()
    if not current:  # 自分の版が分からないときは黙る。比較の根拠が無い
        return None

    for key in installed_agents():
        installed = block_version(key)
        if installed == current:
            continue
        where = (t("no version recorded") if installed is None
                 else t("version {v}").format(v=installed))
        stale.append(t("{name} ({where})").format(
            name=instruction_file(key).name, where=where))

    if not stale:
        return None

    return (
        t("  ⚠️  The operating rules are older than the tool "
          "({stale} / tool version {current}).").format(
              stale=" / ".join(stale), current=current)
        + "\n"
        + t("      Updating the tool does not update the rules. Please run:")
        + "\n"
        + f"        python {TOOL_ROOT / 'install.py'}\n"
        + t("      (Only the marked block is replaced. Nothing else is touched.)")
    )


# ------------------------------------- 自由記述の言語（走っているセッションへ届ける）
#
# 自由記述（`--title` / `--name` / `--mission` / `--headline`）を何語で書くかは、
# エージェントが**セッション開始時に読んだ運用ルール**で決まる。`dash lang` で設定を
# 変えて運用ルールを書き直しても、**すでに走っているセッションには届かない**
# （運用ルールは起動時に一度読まれるだけ）。その結果、ツールが書く既定ラベル
# （`t()` を通る「指令塔」など）は新しい言語なのに、エージェントが書いた行は古い言語の
# まま、という混在が起きる。**実際に起きた**（指令塔だけ日本語で、第1世代は英語）。
#
# **走っているセッションへ届く経路は、エージェントが必ず読むコマンドの出力しかない。**
# だから start では毎回「この言語で書く」と1行出し、受け取った自由記述が明らかに違う
# 言語のときは警告する。判定をここに置くのは、書く側（update_state）と読む側
# （将来 server や diagnose が同じ判断をしたくなったとき）が同じ規則を見るため。
#
# **警告に留め、決して書き込みを拒否しない。** 判定は文字種を見るだけの当て推量で、
# 固有名詞やコールサインを英語で書く運用は正しくありうる。当て推量で人の手を止めるのは
# `--tokens` を推測で埋めないのと同じ理由で、このツールの方針に反する。

#: 期待する言語ごとの「その言語で書いたなら必ず現れる文字」。
#: 日本語と中国語は漢字を共有しているので、**互いの取り違えは検出できない**。
#: そこまで当てようとすると誤検出のほうが増える（英語混在との区別が付かない）。
_LANG_SCRIPTS = {
    # かな + 漢字（かなが1文字でもあれば日本語と分かる）
    "ja": "[぀-ヿ㐀-䶿一-鿿豈-﫿]",
    # 漢字
    "zh": "[㐀-䶿一-鿿豈-﫿]",
    # ハングル（音節 + 字母）
    "ko": "[가-힣ᄀ-ᇿ㄰-㆏]",
}
_CJK_ANY = re.compile("|".join(_LANG_SCRIPTS.values()))

#: 英語で書かれていそうか。2文字以上の英単語を要求するので、記号や数字だけでは真にならない。
_ASCII_WORD = re.compile(r"[A-Za-z]{2,}")

#: ID・パス・版番号のような識別子。`SCOUT-A` や `src/api.py` を英語と見なさないため。
_IDENTIFIER_LIKE = re.compile(r"^[A-Za-z0-9._/\\:-]+$")

#: これより短い記述は判定しない。`42` や `---` を言語で語るのは無理がある。
MIN_LANG_CHECK_CHARS = 6


def free_text_lang_mismatch(text, lang: str | None = None) -> bool:
    """その自由記述が、設定された言語で書かれていない**ように見える**か。

    見えるだけで、断定はしない（呼び手は警告に使い、書き込みは止めない）。
    誤検出を避けるため、次は最初から対象外にする。
      - 短すぎるもの（`MIN_LANG_CHECK_CHARS` 未満）
      - 識別子の形をしたもの（`SCOUT-A` / `src/api.py` / `v0.5.1`）
      - 期待する言語の文字が1文字でも入っているもの（日本語の文に `API` が混ざるのは正常）
      - 対応表に無い言語（判定の根拠が無いので黙る）
    """
    s = as_str(text).strip()
    if len(s) < MIN_LANG_CHECK_CHARS:
        return False
    if _IDENTIFIER_LIKE.match(s):
        return False
    want = lang or i18n.get_lang()
    if want == "en":
        # 英語設定に CJK が混ざるのは稀なので、1文字でも入っていれば知らせる。
        return bool(_CJK_ANY.search(s))
    pattern = _LANG_SCRIPTS.get(want)
    if pattern is None:
        return False
    if re.search(pattern, s):
        return False
    return bool(_ASCII_WORD.search(s))


def expected_lang_notice() -> str:
    """「自由記述はこの言語で書く」の1行。**常に返す**（警告ではなく指示）。

    start の出力に無条件で出すためのもの。stale_block_notice() のように
    「問題があるときだけ」にしてはいけない——設定を変えた直後は何も問題が起きて
    いないのに、エージェントの手元にある運用ルールだけが古い、という状況だから。
    """
    lang = i18n.get_lang()
    return t("  Write the free text (--title / --name / --mission / --headline) "
             "in this language: {label} ({code}).").format(
                 label=i18n.label(lang), code=lang)


def free_text_lang_notice(mismatches, *, fixable: bool) -> str | None:
    """食い違っていた自由記述を知らせる文面。1件も無ければ None。

    文面を返すだけで印字はしない（stale_block_notice() と同じ約束）。

    :param mismatches: [(オプション名, 渡された値), ...]
    :param fixable: あとから直せるか。`add` / `done` / `finish` は同じ `--id` で
        打ち直せば直る（実測値は保たれる）。`start` の `--title` は**直す手段が無い**
        ので、直せると言ってはいけない。言えば、次の start で全員を履歴へ流す。
    """
    if not mismatches:
        return None
    lang = i18n.get_lang()
    fields = " / ".join(
        t('{flag} "{value}"').format(flag=flag, value=clip(as_str(value), 40))
        for flag, value in mismatches
    )
    lines = [
        t("  ⚠️  The language is set to {label} ({code}), but this does not look like "
          "it: {fields}").format(label=i18n.label(lang), code=lang, fields=fields),
    ]
    if fixable:
        lines.append(
            t("      If that was not deliberate, run the same command again with the same\n"
              "      --id and the corrected text. The value is replaced, and the measured\n"
              "      values are kept (the event log keeps the line it already wrote).")
        )
    else:
        lines.append(
            t("      A mission title cannot be corrected afterwards. Only a new start can\n"
              "      change it, and that archives the current mission while it is running.")
        )
    lines.append(
        t("      If it was deliberate (a proper noun, a call sign), ignore this.")
    )
    return "\n".join(lines)


def os_data_home() -> Path:
    """OS の標準的なユーザーデータ置き場。"""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home()
        return Path(base) / "agent-dashboard"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "agent-dashboard"
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "agent-dashboard"


def _is_writable(path: Path) -> bool:
    """実際に書いて確かめる（Windows では os.access が信頼できないため）。"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve_data_home() -> Path:
    """ミッションの保存先（missions/ と trash/ の親）を決める。

    1. 環境変数 AGENT_DASHBOARD_DATA_HOME があればそこ
       「記録の置き場」だけを指す変数。拡張側（extension.js）はこれを見ないので、
       本体の場所の判定に影響しない。試験や一時的な隔離はこれを使う。
    2. 環境変数 AGENT_DASHBOARD_HOME があればそこ
       昔からある変数。dashlib では 1 と同じ意味だが、extension.js では
       「本体（コード）の場所」という別の意味で使われている（冒頭の説明を参照）。
       既存の利用者のために意味は変えず、1 の次に見る。
    3. ツールと同じディレクトリ（USBメモリなどに置いた持ち運び運用ができる）
    4. ツール側が書き込み不可なら OS 標準のユーザーデータ置き場
    """
    for name in (ENV_DATA_HOME, ENV_HOME):
        env = os.environ.get(name)
        if env and env.strip():
            return Path(env).expanduser().resolve()
    if _is_writable(TOOL_ROOT):
        return TOOL_ROOT
    return os_data_home()


DATA_HOME = resolve_data_home()
MISSIONS_DIR = DATA_HOME / "missions"
#: state.json の錠置き場。**missions/ の中に置いてはいけない**（理由は state_lock）。
LOCKS_DIR = DATA_HOME / "locks"

#: 利用者が足した CLI の一覧。記録と同じ場所に置く（本体を入れ替えても残るように）。
#: 差し替えるときは agents_file() 経由で読むこと。定義がここなのは DATA_HOME より
#: 前には決まらないため。
AGENTS_FILE = DATA_HOME / "agents.json"
# 削除したプロジェクトの置き場。missions/ の外に置く。
# 中に作ると list_slugs() がゴミ箱自身を1つのプロジェクトとして拾ってしまう。
TRASH_DIR = DATA_HOME / "trash"

# 画面に映す唯一のチーム。start だけがここを書き換える。
# missions/ の中に置いてよい（list_slugs はディレクトリだけを見て、
# さらに先頭がドットのものを除くので、これを拾うことはない）。
CURRENT_FILE = MISSIONS_DIR / ".current"

# 説明書やヘルプに出す実行コマンド（環境ごとに違うため）
PY_CMD = "python" if sys.platform == "win32" else "python3"
LAUNCHER = "dash.cmd" if sys.platform == "win32" else "./dash"

# ---------------------------------------------------------------- 表示言語
#
# 保存先を DATA_HOME に置くのは、記録と同じ場所に置いておけば USB に入れて
# 持ち運んだときも設定が付いてくるため。**この読み書きは i18n.py には置けない。**
# あちらは DATA_HOME を知らない（知るには dashlib を import することになり、
# dashlib が i18n を import しているので循環する）。
LANG_FILE = DATA_HOME / "lang"


def read_lang_setting() -> str | None:
    """保存された表示言語。無ければ None。**読めなくても落とさない。**"""
    try:
        return i18n.normalize(LANG_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def write_lang_setting(lang: str) -> str:
    """表示言語を保存して、その場でも切り替える。正規化した言語コードを返す。"""
    hit = i18n.normalize(lang)
    if not hit:
        raise ValueError(
            i18n.t("unknown language: {lang} (choose from {list})")
            .format(lang=lang, list=" / ".join(i18n.SUPPORTED))
        )
    DATA_HOME.mkdir(parents=True, exist_ok=True)
    LANG_FILE.write_text(hit + "\n", encoding="utf-8")
    # 保存値より環境変数のほうが強いが、いま明示的に選んだのだから force で通す。
    i18n.set_lang(hit, force=True)
    return hit


# 起動時に1回だけ効かせる。環境変数で明示されていればそちらが勝つ（set_lang の既定）。
_saved_lang = read_lang_setting()
if _saved_lang:
    i18n.set_lang(_saved_lang)

#: 最後に読み込んだ設定ファイルの更新時刻。refresh_lang() が読み直すかの判断に使う。
_lang_mtime: float | None = None


def refresh_lang() -> str:
    """保存された言語設定が変わっていたら読み直す。いまの言語コードを返す。

    **立ち上げっぱなしのプロセス（server.py）のために要る。** 起動時に1回決めるだけだと、
    `dash lang` で切り替えても再起動するまで古い言語のまま出し続ける。CLI は1コマンドで
    終わるので関係ないが、サーバーは何時間も同じプロセスのまま動く。

    毎リクエストで呼ばれても軽いように、**更新時刻が変わったときだけ**読む
    （画面は1秒ごとに取りに来るので、毎回ファイルを読み解くのは無駄）。
    読めなければ何もしない（設定ファイルが無いのは正常な状態）。
    """
    global _lang_mtime
    try:
        mtime = LANG_FILE.stat().st_mtime
    except OSError:
        return i18n.get_lang()
    if mtime == _lang_mtime:
        return i18n.get_lang()
    _lang_mtime = mtime
    hit = read_lang_setting()
    if hit:
        i18n.set_lang(hit)
    return i18n.get_lang()


def use_utf8_stdio() -> None:
    """Windows のコンソールでも多言語の字が化けないようにする。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


# ---------------------------------------------------------------- 時刻・書式


def now_iso(when: datetime | None = None) -> str:
    """ローカルタイムゾーン付きの ISO8601（秒精度）。例: 2026-07-30T10:30:00+09:00"""
    return (when or datetime.now()).astimezone().replace(microsecond=0).isoformat()


def iso_ago(seconds: float) -> str:
    return now_iso(datetime.now() - timedelta(seconds=seconds))


def elapsed_sec_from(iso: str | None):
    if not iso:
        return None
    try:
        started = datetime.fromisoformat(iso)
    except ValueError:
        return None
    now = datetime.now(started.tzinfo) if started.tzinfo else datetime.now()
    return max(0, round((now - started).total_seconds()))


def fmt_sec(sec) -> str:
    if sec is None:
        return "—"
    s = max(0, round(sec))
    h, rem = divmod(s, 3600)
    m, r = divmod(rem, 60)
    return f"{h}:{m:02d}:{r:02d}" if h else f"{m:02d}:{r:02d}"


def fmt_num(n) -> str:
    return "—" if n is None else f"{n:,}"


def disp_width(s: str) -> int:
    """全角文字を2桁として数える（表の桁を揃えるため）。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s: str, width: int) -> str:
    return s + " " * max(0, width - disp_width(s))


def clip(s: str, width: int) -> str:
    """表示幅が width を超える場合は末尾を切って「…」を付ける。"""
    if disp_width(s) <= width:
        return s
    out: list[str] = []
    used = 0
    for ch in s:
        w = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if used + w > width - 1:  # 「…」の1桁分を残す
            break
        out.append(ch)
        used += w
    return "".join(out) + "…"


def cell(s: str, width: int) -> str:
    """幅 width の列に収める。長すぎるものは切り詰め、列間に2桁の余白を残す。"""
    return pad(clip(s, width - 2), width)


# ---------------------------------------------------------------- 型の詰め直し


def as_str(v) -> str:
    return v if isinstance(v, str) else ""


def as_num(v):
    """数値なら数値、それ以外（None・文字列・bool）は None。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def read_json_safe(path: Path) -> tuple[bool, object, str]:
    """(成功したか, 中身, エラー説明) を返す。例外は投げない。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, None, t(ERR_NOT_CREATED)
    except OSError as e:
        return False, None, str(e)
    except UnicodeDecodeError as e:
        # UnicodeDecodeError は ValueError の系統で OSError ではないため、上の except では
        # 捕まらない。ここで捕まえないと、壊れた1ファイルの巻き添えで /api/state が毎秒
        # 500 を返し、無関係な稼働中のチームまで画面から消える。
        return False, None, t("not readable as UTF-8 ({reason})").format(reason=e.reason)
    if not raw.strip():
        return False, None, t("empty file")
    try:
        return True, json.loads(raw), ""
    except json.JSONDecodeError as e:
        return False, None, t(
            "not readable as JSON ({msg} / line {line}, column {col})"
        ).format(msg=e.msg, line=e.lineno, col=e.colno)


# ---------------------------------------------------------------- プロジェクトの識別

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_name(name: str) -> str:
    return _UNSAFE.sub("_", name).strip(". ") or "project"


def slug_for_path(path: Path) -> str:
    """作業ディレクトリから一意なスラッグを作る。

    同名のディレクトリが別の場所にあっても衝突しないよう、フルパスのハッシュ6桁を付ける。
    大文字小文字を区別しないファイルシステムでは、揃えてから算出する。
    """
    p = path.resolve()
    base = sanitize_name(p.name or p.drive.replace(":", "") or "root")
    key = str(p).lower() if CASE_INSENSITIVE_FS else str(p)
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:6]
    return f"{base}-{digest}"


def list_slugs() -> list[str]:
    """missions/ 直下のディレクトリ名＝記録が残っている作業ディレクトリの一覧。

    画面はこの中の1つ（resolve_active_slug が決めるもの）だけを映す。
    一覧そのものは CLI の projects コマンドと、.current が無いときの
    フォールバックのために使う。


    先頭がドットのものは除く（.git などをプロジェクトと誤認しないため）。
    スラッグは sanitize_name が先頭のドットを落とすので、正規のものが除外されることはない。
    """
    try:
        return sorted(
            d.name for d in MISSIONS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")
        )
    except OSError:
        return []


def mission_dir(slug: str) -> Path:
    return MISSIONS_DIR / slug


def state_file(slug: str) -> Path:
    return MISSIONS_DIR / slug / "state.json"


def agents_dir(slug: str) -> Path:
    return MISSIONS_DIR / slug / "agents"


def history_dir(slug: str) -> Path:
    """過去のミッションの置き場。missions/<slug>/ の中に置く。

    list_slugs() は missions/ 直下しか見ないので、これがプロジェクトと誤認される
    ことはない（プロジェクトの持ち物なので、remove すれば履歴も一緒に片付く）。
    """
    return MISSIONS_DIR / slug / "history"


def run_dir(slug: str, run_id: str) -> Path:
    return MISSIONS_DIR / slug / "history" / run_id


def run_state_file(slug: str, run_id: str) -> Path:
    return run_dir(slug, run_id) / "state.json"


def run_agents_dir(slug: str, run_id: str) -> Path:
    return run_dir(slug, run_id) / "agents"


def is_valid_slug(slug: str) -> bool:
    """外から渡されたスラッグが missions/ 直下の1階層を指しているかだけを検証する。

    スラッグには日本語も空白も入りうる（slug_for_path はディレクトリ名をほぼそのまま使う）ので、
    文字種の許可リストは作れない。区切り文字が混ざっていないことだけを見る。
    """
    if not isinstance(slug, str):
        return False
    s = slug.strip()
    if not s or s in (".", ".."):
        return False
    if "\x00" in s or "/" in s or "\\" in s:
        return False
    return Path(s).name == s


# runId は YYYYMMDD-HHMMSS。同じ秒に2回退避したときだけ -2, -3 … が付く。
_RUN_ID_RE = re.compile(r"^\d{8}-\d{6}(?:-\d+)?$")


def is_valid_run_id(run_id: str) -> bool:
    """外から渡された runId が history/ 直下の1階層を指しているかを検証する。

    slug と違って runId は自分で作る値なので、書式そのものを許可リストにできる。
    strip() はしない（前後に空白が付いたものをそのままパスに使わせないため）。
    """
    if not isinstance(run_id, str) or not run_id:
        return False
    if run_id in (".", ".."):
        return False
    if "\x00" in run_id or "/" in run_id or "\\" in run_id:
        return False
    if Path(run_id).name != run_id:
        return False
    return bool(_RUN_ID_RE.match(run_id))


def set_current(slug: str) -> None:
    """画面に映すチームを差し替える。start からだけ呼ぶ。

    書けなくても致命的ではない（resolve_active_slug が最終更新順に落ちる）ので、
    失敗は握って進む。ここで止めると、記録は残っているのに start が失敗する。
    """
    try:
        MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        CURRENT_FILE.write_text(slug + "\n", encoding="utf-8")
    except OSError as e:
        # ここも _warn 経由にする。知らせる処理が例外を投げて start を落とすと、
        # 「書けなくても致命的ではない」という上の但し書きが嘘になる
        _warn(
            t("Failed to write the .current file"),
            e,
            t("this mission may not appear on the dashboard"),
        )


def read_current() -> str | None:
    """記録されているチーム。実体が無くなっていれば None。"""
    try:
        slug = CURRENT_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    except UnicodeDecodeError:
        # OSError では捕まらない系統。ここで漏らすと /api/state が毎秒 500 になる。
        return None
    if not is_valid_slug(slug) or not mission_dir(slug).is_dir():
        return None
    return slug


def clear_current() -> None:
    try:
        CURRENT_FILE.unlink()
    except OSError:
        pass


def _state_mtime(slug: str) -> float:
    try:
        return state_file(slug).stat().st_mtime
    except OSError:
        return 0.0


def resolve_active_slug() -> str | None:
    """画面に映す唯一のチームを決める。

    1. .current（直近の start が書いたもの）
    2. 無ければ state.json が一番新しいもの
       （.current を持たない古いインストールから引き継いだ場合のため）
    3. 記録が1つも無ければ None＝待機画面

    2 で build_state を使わないのは、1秒ごとに全プロジェクトを組み立てる
    ことになるため。ここでは更新時刻の比較で足りる。
    """
    slug = read_current()
    if slug:
        return slug
    slugs = list_slugs()
    if not slugs:
        return None
    return max(slugs, key=_state_mtime)


def active_window_sec() -> int:
    """「稼働中」とみなす時間窓（秒）を決める。

    環境変数で運用ごとに調整できるようにしておく（放置された running 記録を
    どれだけ長く画面に出し続けるかは現場によって事情が違うため）。
    正の整数として読めない値は既定値にフォールバックする。
    """
    raw = os.environ.get(ENV_ACTIVE_WINDOW, "").strip()
    if raw:
        try:
            n = int(raw)
            if n > 0:
                return n
        except ValueError:
            pass
    return DEFAULT_ACTIVE_WINDOW_SEC


def _iso_ts(raw) -> float | None:
    """ISO8601 文字列をエポック秒に。読めないものは None。

    タイムゾーン付きと無しが混在しても比較できるよう、datetime のままでは返さず
    必ず float に落とす（aware と naive を直接比べると TypeError になる）。
    """
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except ValueError:
        return None


def resolve_visible_slugs(current: str | None = ...) -> list[str]:
    """画面に映すチーム全部を決める（複数チームの並列稼働に対応するため）。

    含めるもの:
      1. mission.phase == "running" かつ state.json の更新が時間窓内のもの
      2. .current が指すもの（フェーズや時間窓を問わず必ず含める。完了した
         チームも次の start までは映し続けたいので）
      3. 「稼働中のチームが動き始めたあとに完了したチーム」
         並列稼働の片方が finish したとき、そのチームはもう .current ではないので
         2 では拾えず、完了した瞬間に画面から消えてサマリーを誰も読めない。
         一方、順番に作業しているだけの場合（前のチームが終わってから次を start）は
         「前のチームは表示不要」が要件なので、残してはいけない。ここで落としても
         過去のミッションは history/ に退避されており list_runs()／read_run() で
         見返せるので、記録が消えるわけではない。
         この2つは「完了時刻が、いま稼働しているチームの開始時刻より後か」で分かれる。

    並び順は mission.startedAt の降順（新しく始まったものが先頭）。startedAt が
    無い／壊れているものは末尾へ。

    1秒ごとに呼ばれるため build_state（孫の自己申告まで読む重い処理）は使わず、
    各チームの state.json を1回だけ読んで phase と時刻だけ見る。

    current は呼び出し側が既に読んでいれば渡せる（既定は自分で読む）。同じリクエスト内で
    2回読むと、その間に start が走ったときに返す内容が食い違うため。
    """
    if current is ...:
        current = read_current()

    threshold = datetime.now().timestamp() - active_window_sec()

    started: dict[str, float | None] = {}
    finished: dict[str, float | None] = {}
    running: list[str] = []
    done: list[str] = []

    for slug in list_slugs():
        ok, value, _ = read_json_safe(state_file(slug))
        mission = value.get("mission") if ok and isinstance(value, dict) else {}
        if not isinstance(mission, dict):
            mission = {}
        started[slug] = _iso_ts(mission.get("startedAt"))
        finished[slug] = _iso_ts(mission.get("finishedAt"))
        phase = mission.get("phase")
        if phase == "running" and _state_mtime(slug) >= threshold:
            running.append(slug)
        elif phase == "done":
            done.append(slug)

    visible: list[str] = list(running)
    seen: set[str] = set(visible)

    # 稼働中のうち最も遅く始まったもの。これより後に完了したチームは「並列で
    # 走っていた片割れ」なので残す。稼働中が居なければ判定できないので誰も残さない。
    starts = [started[s] for s in running if started[s] is not None]
    newest_start = max(starts) if starts else None
    if newest_start is not None:
        for slug in done:
            if slug in seen:
                continue
            end = finished[slug]
            if end is not None and end >= newest_start:
                seen.add(slug)
                visible.append(slug)

    if current and current not in seen:
        seen.add(current)
        visible.append(current)
        started.setdefault(current, None)  # list_slugs() に無い場合の保険

    # (有効な startedAt を持つか, その値) の順。無効なものは常に後ろへ回したいので
    # 真偽を先頭に置き、reverse=True で「新しい方が先頭」を実現する。
    visible.sort(key=lambda s: (started.get(s) is not None, started.get(s) or 0.0), reverse=True)
    return visible


def _rehome_current() -> None:
    """.current が指していた記録が消えたときの引き継ぎ先を決める。

    単に消すと、まだ動いているチームが finish した瞬間に画面から居なくなる
    （完了したチームを残す根拠は .current だけなので）。残っている稼働中のうち
    最も新しく始まったものへ引き継いで、完了報告が読めるようにする。
    稼働中が居なければ素直に外す＝待機画面へ戻る。
    """
    clear_current()
    running = [s for s in resolve_visible_slugs(None) if s]
    if running:
        set_current(running[0])   # resolve_visible_slugs は開始が新しい順


def _reserve_trash_dir(base_name: str) -> Path:
    """trash/<base_name>-<日時>/ の空いている名前を1つ決める（作りはしない）。

    名前が衝突したら連番を足す。フォルダ1つを丸ごと移すときは移動先そのものに、
    複数のものをまとめて入れるときは入れ物の名前に使う。
    """
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = TRASH_DIR / f"{base_name}-{stamp}"
    n = 2
    while dest.exists():
        dest = TRASH_DIR / f"{base_name}-{stamp}-{n}"
        n += 1
    return dest


def _move_to_trash(target: Path, base_name: str) -> Path:
    """target を trash/<base_name>-<日時>/ へ移す。名前が衝突したら連番を足す。

    プロジェクトごと消すときも過去の記録1件を消すときも、ゴミ箱の作法は同じにする
    （フォルダを戻せば復旧できる、という約束を1か所で守るため）。
    """
    dest = _reserve_trash_dir(base_name)
    shutil.move(str(target), str(dest))
    return dest


def delete_project(slug: str, permanent: bool = False) -> dict:
    """記録を消す＝missions/<slug>/ を無くす。

    既定では trash/<slug>-<日時>/ へ移すだけなので、フォルダを戻せば元に戻る。
    permanent=True のときだけ本当に消す。

    返り値: {"slug": ..., "permanent": bool, "movedTo": 移動先 or None}
    """
    if not is_valid_slug(slug):
        raise ValueError(t("invalid slug: {slug!r}").format(slug=slug))

    target = mission_dir(slug)
    if not target.is_dir():
        raise FileNotFoundError(t("missions/{slug}/ does not exist").format(slug=slug))
    # シンボリックリンクや .. を経由して missions/ の外を消させない
    if target.resolve().parent != MISSIONS_DIR.resolve():
        raise ValueError(t("not directly under missions/: {path}").format(path=target))

    # 消したものを指したままにしない。
    was_current = read_current() == slug

    if permanent:
        shutil.rmtree(target)
        if was_current:
            _rehome_current()
        return {"slug": slug, "permanent": True, "movedTo": None}

    dest = _move_to_trash(target, slug)
    if was_current:
        _rehome_current()
    return {"slug": slug, "permanent": False, "movedTo": str(dest)}


# ---------------------------------------------------------------- 履歴（過去のミッション）
#
# 昔は1プロジェクト1レコードで、同じディレクトリで start すると前のミッションが
# 痕跡なく消えていた（trash/ にも残らなかった）。start のたびに state.json と
# agents/ を history/<runId>/ へ丸ごと移して、後から見返せるようにする。
# state.json の形と場所は変えていないので、既存の読み手はそのまま動く。

# runId を「日時部分」と「同秒衝突の連番」に分けるため（並べ替えに使う）。
_RUN_ID_PARTS = re.compile(r"^(\d{8}-\d{6})(?:-(\d+))?$")


def _warn(what: str, err: object = None, hint: str = "") -> None:
    """止めずに知らせる。履歴まわりの失敗で start を落とさないため。

    **知らせること自体が失敗しても、それで止めない。** ここは「退避に失敗したが
    start は続ける」という経路の中から呼ばれる。書き込み先が壊れているときは
    stderr も道連れになっていることがあり（親がパイプを閉じた後など）、
    そこで例外を漏らすと「止めないための関数」が start を落とす。
    """
    try:
        print(t("⚠️  Warning: {what}").format(what=what), file=sys.stderr)
        if err is not None:
            print(t("   Cause: {err}").format(err=err), file=sys.stderr)
        if hint:
            print(f"   {hint}", file=sys.stderr)
        sys.stderr.flush()
    except Exception:
        pass


def history_keep() -> int:
    """history/ に残す件数。環境変数 AGENT_DASHBOARD_HISTORY_KEEP、既定 20。

    0 は「履歴を残さない」＝退避しない（昔の動作）。負の数や数字でない値は既定値。
    """
    raw = os.environ.get(ENV_HISTORY_KEEP, "").strip()
    if raw:
        try:
            n = int(raw)
            if n >= 0:
                return n
        except ValueError:
            pass
    return DEFAULT_HISTORY_KEEP


def _run_key(run_id: str) -> tuple[str, int]:
    """runId の並べ替えキー。同じ秒の -2, -10 を数値として比べるため。"""
    m = _RUN_ID_PARTS.match(run_id)
    if not m:
        return (run_id, 0)
    return (m.group(1), int(m.group(2) or 1))


def _all_run_ids(slug: str) -> list[str]:
    """history/ にある runId を新しい順に。書式に合わない名前は無視する。

    無視したものは間引きの対象にもしない（人が置いたフォルダを勝手に捨てないため）。
    """
    try:
        names = [
            d.name for d in history_dir(slug).iterdir() if d.is_dir() and is_valid_run_id(d.name)
        ]
    except OSError:
        return []
    return sorted(names, key=_run_key, reverse=True)


# ---------------------------------------------------------------- 空の殻（中身の無い履歴）
#
# 退避は _move_current_to_history() が dest.mkdir() → shutil.move() の順で行う。
# mkdir に成功したあとで move が失敗すると、history/<runId>/ が中身の無い
# フォルダとして残る。これを「殻」と呼ぶ。
#
# 殻を保持枠（直近 N 件）に数えると、殻は常に新しい runId を持つため間引きで
# 生き残り、代わりに本物の古い記録が捨てられる。「直近20件」のはずが本物は
# 20件未満しか残らない、という壊れ方をしていた。
#
# 判定は3つに分ける。**迷ったら必ず「中身がある」側に倒す。**
#   record … state.json が「在る」。読めるかどうかは問わない。壊れた JSON も
#            人が直せる記録なので、絶対に殻扱いしない。
#   orphan … state.json は無いが、フォルダの中に何かファイルが残っている
#            （agents/ の自己申告など）。中身がある以上は記録として扱い、
#            保持枠に数え、溢れたら trash/ へ退避する＝消さずに残す。
#   shell  … state.json も無く、入れ子も含めてファイルが1つも無い。これだけを殻とする。
#
# 片付けは os.rmdir だけで行う（_rmdir_tree）。os.rmdir は空のディレクトリに
# しか成功しないので、**万一 shell の判定を誤っても、ファイルが消えることは
# 原理的に起こりえない。** 消えるのは 0 バイトのフォルダだけなので trash/ へ
# 退避する意味も無く（戻すものが無い）、そのまま取り除く。

_RUN_RECORD = "record"
_RUN_ORPHAN = "orphan"
_RUN_SHELL = "shell"

# 殻を片付けるまでの猶予（秒）。他プロセスが退避の途中
# （dest.mkdir() 済み・shutil.move() 前）で、その一瞬だけ殻に見えるものを
# 巻き込まないため。退避は一瞬で終わるので、これだけあれば十分に安全側。
SHELL_GRACE_SEC = 60


def _has_any_file(root: Path) -> bool:
    """root の下（入れ子も含めて）にファイルが1つでもあるか。

    判断がつかないとき（読めない・権限が無い等）は True を返す。「中身がある」側へ
    倒すことで、その履歴は殻の判定から外れ、片付けの対象にならない。
    シンボリックリンクは辿らず、それ自体を「中身」として数える。
    """
    try:
        for entry in os.scandir(root):
            try:
                if entry.is_dir(follow_symlinks=False):
                    if _has_any_file(Path(entry.path)):
                        return True
                else:
                    return True  # ファイル・リンク・その他は中身とみなす
            except OSError:
                return True
    except OSError:
        return True
    return False


def _rmdir_tree(root: Path) -> bool:
    """空のディレクトリだけを取り除く。**ファイルは1つも消さない。**

    使うのは os.rmdir だけ。os.rmdir は中身が空のディレクトリにしか成功しないので、
    呼び出し側が判定を誤って中身のあるフォルダを渡しても、ファイルが失われることは
    起こりえない（途中で失敗して False を返すだけ）。
    """
    try:
        for entry in os.scandir(root):
            if not entry.is_dir(follow_symlinks=False):
                return False  # ファイルかリンクがある＝殻ではない。何もせず引き返す
            if not _rmdir_tree(Path(entry.path)):
                return False
    except OSError:
        return False
    try:
        os.rmdir(root)
        return True
    except OSError:
        return False


def _stat_fingerprint(st) -> tuple:
    """state.json の「変わっていないこと」を判定する鍵。

    mtime を秒で見ると同一秒内の書き換えを取りこぼすので ns で見る
    （NTFS は 100ns、ext4 は ns 精度）。さらに、このツールが state.json を置く経路は
    write_state() の os.replace と _move_current_to_history() の shutil.move で、
    どちらも「別の場所で作ったファイルの名前を差し替える」＝ mtime は元ファイルのものが
    そのまま引き継がれる。つまり mtime だけでは「中身が入れ替わったのに mtime が同じ」を
    見逃しうる。そこで実体が変わったことを直接示す st_ino（Windows でもファイル
    インデックスが入る）と st_dev を鍵に混ぜる。
    """
    return (st.st_mtime_ns, st.st_size, st.st_ino, st.st_dev)


def _classify_run(slug: str, run_id: str) -> tuple[str, tuple | None]:
    """履歴1件が record / orphan / shell のどれかを返す（指紋つき）。"""
    try:
        st = run_state_file(slug, run_id).stat()
    except FileNotFoundError:
        # state.json が無い。中身が本当に空のときだけ殻。
        if _has_any_file(run_dir(slug, run_id)):
            return _RUN_ORPHAN, None
        return _RUN_SHELL, None
    except OSError:
        # 読めない理由が分からない（権限など）。中身がある可能性を否定できないので
        # 記録として扱う＝殻にはしない。
        return _RUN_RECORD, None
    return _RUN_RECORD, _stat_fingerprint(st)


def _scan_runs(slug: str) -> list[tuple[str, str, tuple | None]]:
    """history/ を1回走査して (runId, 種別, 指紋) を新しい順に返す。"""
    return [(run_id, *_classify_run(slug, run_id)) for run_id in _all_run_ids(slug)]


def _existing_run_ids(slug: str) -> list[str]:
    """保持枠（直近 N 件）に数える runId を新しい順に。**空の殻は数えない。**

    殻を数えると、殻は常に新しい runId を持つため間引きで生き残り、本物の
    古い記録を追い出してしまう（上の説明を参照）。中身のある orphan は数える。
    """
    return [r for r, kind, _ in _scan_runs(slug) if kind != _RUN_SHELL]


def sweep_empty_runs(slug: str) -> list[str]:
    """history/ に溜まった空の殻を取り除く。取り除いた runId の一覧を返す。

    **書き込み系の経路からだけ呼ぶこと。** list_runs() は画面から1秒ごとに
    叩かれる読み取り経路なので、そこから消しに行ってはいけない
    （他プロセスが退避の途中で作ったばかりのフォルダを壊しうる）。
    """
    swept: list[str] = []
    base = history_dir(slug)
    try:
        base_real = base.resolve()
    except OSError:
        return swept
    cutoff = datetime.now().timestamp() - SHELL_GRACE_SEC

    for run_id, kind, _ in _scan_runs(slug):
        if kind != _RUN_SHELL:
            continue
        target = run_dir(slug, run_id)
        # シンボリックリンクや .. を経由して history/ の外を触らせない
        try:
            if target.resolve().parent != base_real:
                continue
            # 出来たばかりのものは触らない（他プロセスが退避の最中かもしれない）
            if target.stat().st_mtime > cutoff:
                continue
        except OSError:
            continue
        if _rmdir_tree(target):  # 空のフォルダしか消さない
            swept.append(run_id)
    return swept


def _run_id_for_current(slug: str) -> str:
    """いまの state.json を退避するときの runId を決める。

    そのミッションの開始時刻（mission.startedAt）から作る。無い／壊れているときは
    state.json の更新時刻を使う。それも取れなければ現在時刻。
    """
    path = state_file(slug)
    ok, value, _ = read_json_safe(path)
    started = None
    if ok and isinstance(value, dict) and isinstance(value.get("mission"), dict):
        started = value["mission"].get("startedAt")
    ts = _iso_ts(started)
    if ts is None:
        try:
            ts = path.stat().st_mtime
        except OSError:
            ts = datetime.now().timestamp()
    try:
        return datetime.fromtimestamp(ts).strftime("%Y%m%d-%H%M%S")
    except (OSError, OverflowError, ValueError):
        return datetime.now().strftime("%Y%m%d-%H%M%S")


def _move_current_to_history(slug: str) -> str:
    """state.json と agents/ を history/<runId>/ へ移して runId を返す（失敗時は例外）。"""
    base = _run_id_for_current(slug)
    hdir = history_dir(slug)
    hdir.mkdir(parents=True, exist_ok=True)

    dest = hdir / base
    n = 2
    while dest.exists():
        dest = hdir / f"{base}-{n}"
        n += 1
    # 先に場所を取る。存在確認と移動の間に他プロセスが同じ名前を作るのを防ぐ
    # （mkdir は既にあれば FileExistsError で失敗するので、上書きにはならない）。
    dest.mkdir()

    shutil.move(str(state_file(slug)), str(dest / "state.json"))
    src_agents = agents_dir(slug)
    if src_agents.is_dir():
        shutil.move(str(src_agents), str(dest / "agents"))
        # 孫の置き場は空で作り直す。昔の start は agents/ の中の *.json だけを消して
        # フォルダ自体は残していた。孫は「このパスに1ファイル書く」と指示されており、
        # 親フォルダを自分で作らない書き方もあるので、無くしてしまうと申告できなくなる。
        try:
            src_agents.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # 作れなくても退避自体は成功している
    return dest.name


def prune_history(slug: str, keep: int | None = None) -> list[str]:
    """history/ が保持件数を超えていたら古い順に trash/ へ移す。

    返り値: trash/ へ移した runId の一覧（古い順）。

    先に空の殻（退避が途中で落ちた跡の、中身の無いフォルダ）を取り除く。殻を
    残したままにすると保持枠を食い、本物の記録を追い出してしまうため。殻の片付けは
    os.rmdir だけで行うので、記録が失われることはない（sweep_empty_runs を参照）。

    keep=0（＝履歴を残さない設定）のときは間引きはしない。既にある記録を設定変更だけで
    掃除してしまわないため。殻の片付けだけは行う（消えるのは0バイトのフォルダだけ）。
    """
    try:
        sweep_empty_runs(slug)
    except OSError:
        pass  # 片付けに失敗しても間引きは続ける（保持枠の勘定からは既に外れている）

    n = history_keep() if keep is None else keep
    if n <= 0:
        return []

    doomed = _existing_run_ids(slug)[n:]  # 新しい順に並んでいるので、溢れるのは後ろ＝古い方
    moved: list[str] = []
    base = history_dir(slug)
    for run_id in reversed(doomed):  # 古い方から片付ける
        target = run_dir(slug, run_id)
        # シンボリックリンクや .. を経由して history/ の外を消させない
        if target.resolve().parent != base.resolve():
            continue
        _move_to_trash(target, f"{slug}-{run_id}")
        moved.append(run_id)
    return moved


def is_unstarted_state(state) -> bool:
    """まだ一度も start していない、器だけの state か（reset の直後がこれ）。

    phase と機体の有無の両方を見る。start 直後は指令塔しか居らず「機体0体」に
    見えるが、そちらは phase が running なので未開始とは別物になる。
    """
    if not isinstance(state, dict):
        return False
    mission = state.get("mission")
    if not isinstance(mission, dict) or mission.get("phase") != "standby":
        return False
    return not state.get("agents")


def archive_current_run(slug: str) -> dict:
    """いまの state.json と agents/ を history/ へ退避する。start の write_state() 直前に呼ぶ。

    返り値: {"runId": 退避した runId or None, "pruned": trash へ移した runId の一覧}

    例外は投げない（set_current と同じ方針）。記録が残っているのに start が落ちるのが
    一番困るので、失敗しても警告だけ出して呼び出し側を進ませる。
    """
    result: dict = {"runId": None, "pruned": []}

    if history_keep() <= 0:  # 履歴を残さない設定＝昔どおり上書きさせる
        return result
    if not state_file(slug).is_file():  # 初回の start。退避するものが無い。
        return result

    # 未開始の器（reset の直後）は退避しない。中身が無いので残す値が無いうえに、
    # 退避すると history/ に「待機中・機体0体」の記録が生まれ、押しても何も出ない
    # タブが並ぶ。しかもそれは runId を持つため、画面側の未開始タブの間引き
    # （server._is_unstarted_tab は runId の無い現在のタブだけを見る）では
    # 降ろせず、以後ずっと残り続ける。
    # 読めなければ退避する側に倒す。中身のある記録を「読めなかった」だけで
    # 捨てるほうが、空の履歴が1件増えるよりはるかに損害が大きい。
    ok, current, _ = read_json_safe(state_file(slug))
    if ok and is_unstarted_state(current):
        return result

    try:
        result["runId"] = _move_current_to_history(slug)
    except OSError as e:
        _warn(
            t("Could not move the previous mission into history/"),
            e,
            t("this start will overwrite the previous record (the mission still begins)"),
        )
        return result

    try:
        result["pruned"] = prune_history(slug)
    except OSError as e:
        _warn(t("Could not move old records from history/ into trash/"), e)
    return result


# ---------------------------------------------------------------- 履歴の要約キャッシュ
#
# /api/state は画面から1秒ごとに叩かれ、その中で build_tabs() が全プロジェクトの
# list_runs() を呼ぶ。素直に書くと history/ の state.json を毎秒すべて開いて
# JSON パースすることになり、プロジェクトが増えるほど1秒の予算を食い潰す
# （実測: 20プロジェクト×履歴20件で中央値 322ms＝ポーリング間隔の3割）。
#
# 過去の記録は history/ へ退避されたら基本的に変わらないので、1件ずつ
# 「そのファイルが変わっていなければ前回の要約を使い回す」形にする。
#
# 【毎回必ずやり直すこと】＝「速いが古い」を起こさない根拠
#   * history/ 直下の一覧を取り直す      → 記録の増減は必ずその場で見える
#   * 各 state.json の os.stat を取り直す → 変更は指紋の不一致として必ず見える
#   省くのは read_text と json.loads だけ。読み込みが要るかどうかの判断そのものは
#   毎回ファイルシステムに問い合わせているので、キャッシュがあってもなくても
#   list_runs() が返す内容は同じになる。
#
# 【指紋】_stat_fingerprint を参照（mtime を ns で見て、さらに st_ino を混ぜる）。
#
# 【スレッド安全】server.py は ThreadingHTTPServer なので複数スレッドから同時に
#   呼ばれる。辞書の操作は必ずロックの中で行い、ファイルの読み込みはロックの外で
#   行う（読み込みは何度やっても同じ結果なので、同じ記録を2スレッドが同時に
#   読んで両方が書き戻しても壊れない。逆にロックを持ったまま読むと、
#   1件の遅いファイルが全スレッドを待たせる）。
#   呼び出し側へは必ず複製を返す（受け取った側が書き換えてもキャッシュは汚れない）。
#
# 【上限】LRU で件数を固定する。プロジェクトと履歴がいくら増えても、
#   保持するのは最近使われた RUN_CACHE_MAX 件だけなのでメモリは頭打ちになる。

# 1件あたり数百バイト程度の要約。既定の保持件数20なら25プロジェクト分に相当する。
RUN_CACHE_MAX = 512

_run_cache: "OrderedDict[tuple[str, str], tuple[tuple, dict]]" = OrderedDict()
_run_cache_lock = threading.Lock()


def _run_cache_get(key: tuple[str, str], fingerprint: tuple | None) -> dict | None:
    """指紋が一致したときだけ前回の要約の複製を返す。"""
    if fingerprint is None:  # 指紋を取れないものは毎回読み直す（古い内容を返さないため）
        return None
    with _run_cache_lock:
        hit = _run_cache.get(key)
        if hit is None or hit[0] != fingerprint:
            return None
        _run_cache.move_to_end(key)  # 直近に使ったものとして扱う
        return dict(hit[1])


def _run_cache_put(key: tuple[str, str], fingerprint: tuple | None, summary: dict) -> None:
    if fingerprint is None:
        return
    with _run_cache_lock:
        _run_cache[key] = (fingerprint, dict(summary))
        _run_cache.move_to_end(key)
        while len(_run_cache) > RUN_CACHE_MAX:
            _run_cache.popitem(last=False)  # 一番長く使われていないものから捨てる


def clear_run_cache() -> None:
    """要約キャッシュを空にする。正しさのためには不要（指紋で必ず検証している）。

    試験や、置き場ごと差し替えたときの後始末のために用意しておく。
    """
    with _run_cache_lock:
        _run_cache.clear()


def run_cache_stats() -> dict:
    """いま何件抱えているか（上限が効いていることの確認用）。"""
    with _run_cache_lock:
        return {"entries": len(_run_cache), "max": RUN_CACHE_MAX}


def _summarize_run(slug: str, run_id: str) -> tuple[dict | None, bool]:
    """履歴1件の state.json を読んで軽い要約を作る。

    返り値: (要約 or None, その要約をキャッシュしてよいか)

    **読み込みに失敗した結果は決してキャッシュしない。** 失敗の中には
    「そのとき限り」のものがある。とくに Windows では、他のプロセスが os.replace で
    state.json を差し替えている一瞬に読むと PermissionError になることがある
    （旧実装でも同じように起きていた。read_json_safe はこれを握って既定値の要約に
    落とすので、画面ではタイトルが一瞬「（無題のミッション）」に見える）。
    これを指紋つきで覚えてしまうと、次にファイルが変わるまでその誤った要約を
    返し続けることになる＝「速いが古い」。覚えるのは JSON として読み切れたものだけにする。
    """
    ok, value, err = read_json_safe(run_state_file(slug, run_id))
    if not ok and is_not_created(err):
        # state.json の無いフォルダ（退避が途中で落ちた跡）は記録として出さない
        return None, False

    mission: dict = {}
    agents: list = []
    if ok and isinstance(value, dict):
        if isinstance(value.get("mission"), dict):
            mission = value["mission"]
        if isinstance(value.get("agents"), list):
            agents = value["agents"]

    return {
        "runId": run_id,
        "title": as_str(mission.get("title")) or t("(untitled mission)"),
        "phase": mission.get("phase") if mission.get("phase") in PHASES else "standby",
        "startedAt": as_str(mission.get("startedAt")) or None,
        "finishedAt": as_str(mission.get("finishedAt")) or None,
        "agentCount": sum(
            1
            for a in agents
            if isinstance(a, dict) and as_str(a.get("id")) and a.get("id") != COMMAND_ID
        ),
    }, ok


def list_runs(slug: str) -> list[dict]:
    """history/ にある過去の記録の軽い一覧。新しい順。

    各要素: {"runId", "title", "phase", "startedAt", "finishedAt", "agentCount"}

    1秒ごとに呼ばれても平気なように build_state は使わない。各 run の state.json は
    「前回から変わっていなければ」読まずに前回の要約を使う（上のキャッシュの説明を参照）。
    孫の自己申告は数えない＝agentCount は state.json に登録された機体数から
    指令塔を除いた数。

    ここは読み取り経路なので、空の殻を見つけても消しには行かない（一覧から外すだけ）。
    片付けは書き込み系の prune_history() / archive_current_run() が行う。
    """
    runs: list[dict] = []
    for run_id, kind, fingerprint in _scan_runs(slug):
        if kind != _RUN_RECORD:  # 殻も orphan も state.json が無い＝記録として出さない
            continue

        key = (slug, run_id)
        summary = _run_cache_get(key, fingerprint)
        if summary is None:
            summary, cacheable = _summarize_run(slug, run_id)
            if summary is None:
                # stat と読み込みの間に消えた。古い内容を出すより出さない方が正しい。
                continue
            if cacheable:  # 読めなかったものは覚えない（_summarize_run の説明を参照）
                _run_cache_put(key, fingerprint, summary)
        runs.append(summary)
    return runs


def delete_run(slug: str, run_id: str) -> dict:
    """過去の記録1件を trash/ へ移す（フォルダを戻せば復旧できる）。

    返り値: {"slug": ..., "runId": ..., "movedTo": 移動先}
    """
    if not is_valid_slug(slug):
        raise ValueError(t("invalid slug: {slug!r}").format(slug=slug))
    if not is_valid_run_id(run_id):
        raise ValueError(t("invalid runId: {run_id!r}").format(run_id=run_id))

    target = run_dir(slug, run_id)
    if not target.is_dir():
        raise FileNotFoundError(t("missions/{slug}/history/{run_id}/ does not exist")
                                .format(slug=slug, run_id=run_id))
    # シンボリックリンクや .. を経由して missions/ の外を消させない。
    # プロジェクト自体が missions/ 直下であることと、run が その history/ 直下で
    # あることの2段で確かめる。
    if mission_dir(slug).resolve().parent != MISSIONS_DIR.resolve():
        raise ValueError(t("not directly under missions/: {path}").format(path=mission_dir(slug)))
    if target.resolve().parent != history_dir(slug).resolve():
        raise ValueError(t("not directly under history/: {path}").format(path=target))

    dest = _move_to_trash(target, f"{slug}-{run_id}")
    return {"slug": slug, "runId": run_id, "movedTo": str(dest)}


def delete_current_run(slug: str) -> dict:
    """完了した「現在のミッション」（state.json と agents/）を trash/ へ移す。

    history/ へ移されるのは次の start が走ったときだけなので、1度きりのミッションは
    完了しても state.json の枠に残り続ける。画面で「完了」と出ているものを片付ける
    手段が無くなるため、delete_run とは別にこの経路を用意する。

    まだ終わっていないもの（phase が done 以外）は消さない。稼働中の記録を画面の
    ボタン1つで消せるようにはしない。state.json が読めないものも done と確かめられない
    ので消さない（画面でも「完了」とは出ない）。

    history/ に記録が1件も残らない場合は、空の入れ物を残さずプロジェクトごと trash/ へ
    移す（結果は delete_project と同じ）。

    返り値: {"slug", "runId": None, "movedTo": 移動先, "removedProject": bool}
    """
    if not is_valid_slug(slug):
        raise ValueError(t("invalid slug: {slug!r}").format(slug=slug))

    target = mission_dir(slug)
    path = state_file(slug)
    if not path.is_file():
        raise FileNotFoundError(t("missions/{slug}/state.json does not exist").format(slug=slug))
    # シンボリックリンクや .. を経由して missions/ の外を消させない
    if target.resolve().parent != MISSIONS_DIR.resolve():
        raise ValueError(t("not directly under missions/: {path}").format(path=target))

    ok, value, err = read_json_safe(path)
    phase = None
    if ok and isinstance(value, dict) and isinstance(value.get("mission"), dict):
        phase = value["mission"].get("phase")
    if phase != "done":
        if not ok:
            raise ValueError(t("cannot read state.json ({err})").format(err=err))
        raise ValueError(t("a mission that has not finished cannot be deleted"))

    # 消したものを指したままにしない（delete_project と同じ後始末）。
    was_current = read_current() == slug

    # history/ が空になるなら、中身の無いプロジェクトのフォルダだけが残らないようにする。
    if not _existing_run_ids(slug):
        dest = _move_to_trash(target, slug)
        if was_current:
            _rehome_current()
        return {"slug": slug, "runId": None, "movedTo": str(dest), "removedProject": True}

    dest = _reserve_trash_dir(f"{slug}-current")
    dest.mkdir(parents=True)
    shutil.move(str(path), str(dest / "state.json"))

    src_agents = agents_dir(slug)
    if src_agents.is_dir():
        shutil.move(str(src_agents), str(dest / "agents"))
        # 孫の置き場は空で作り直す（_move_current_to_history と同じ理由。孫は
        # 「このパスに1ファイル書く」と指示されており、親フォルダを自分で作らない
        # 書き方もあるので、無くしてしまうと申告できなくなる）。
        try:
            src_agents.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # 作れなくても削除自体は成功している

    if was_current:
        _rehome_current()
    return {"slug": slug, "runId": None, "movedTo": str(dest), "removedProject": False}


def read_project_info(slug: str) -> dict:
    ok, value, _ = read_json_safe(state_file(slug))
    if ok and isinstance(value, dict) and isinstance(value.get("project"), dict):
        return value["project"]
    return {}


def resolve_project(explicit: str | None = None) -> dict:
    """どのプロジェクトを対象にするかを決める。

    優先順位: --project 指定 → 環境変数 AGENT_DASHBOARD_PROJECT → カレントディレクトリ

    返り値: {"slug": ..., "name": 表示名, "path": 元のパス}
    """
    hint = (explicit or os.environ.get(ENV_PROJECT) or "").strip()

    if hint:
        matches = [s for s in list_slugs() if s == hint or s.startswith(hint + "-")]
        if len(matches) == 1:
            slug = matches[0]
            info = read_project_info(slug)
            return {
                "slug": slug,
                "name": info.get("name") or slug,
                "path": info.get("path") or "",
            }
        if len(matches) > 1:
            raise ValueError(
                t("the project hint \"{hint}\" matches {n} projects: {list}")
                .format(hint=hint, n=len(matches), list=", ".join(matches))
            )
        # 既存に無い場合は名前指定として新規作成する。
        # path には、名前で分けていても「実際にどこで動いているか」は事実なので
        # カレントディレクトリを記録する。ここを空にすると、あとから補う手段が無く
        # （read_state は欠けている項目しか埋めない）、実際の作業場所を知る必要がある
        # 機能——稼働中の実測の読み取りなど——がそのミッションで永久に動かなくなる。
        return {"slug": sanitize_name(hint), "name": hint, "path": str(Path.cwd().resolve())}

    cwd = Path.cwd().resolve()
    return {"slug": slug_for_path(cwd), "name": cwd.name, "path": str(cwd)}


# ---------------------------------------------------------------- 状態ファイル


def empty_state(project: dict | None = None) -> dict:
    return {
        "version": 2,
        "project": dict(project) if project else {"slug": "", "name": "", "path": ""},
        "updatedAt": None,
        "mission": {
            "phase": "standby",
            "title": t("(no mission started)"),
            "startedAt": None,
            "finishedAt": None,
            "summary": None,
        },
        "agents": [],
        "log": [],
    }


def write_state(slug: str, state: dict) -> None:
    """一時ファイルに書いてから差し替える。読み込み側が書きかけのJSONを読むことがない。

    一時ファイルの名前にプロセスIDを入れてあるのは、**同時に2つが書くとき**のため。
    名前が固定だと、片方が書いている最中にもう片方が同じ名前を truncate して開き、
    混ざった中身が os.replace で本番へ入る。差し替えそのものが不可分でも、
    差し替える中身が壊れていたら意味がない。
    """
    state["updatedAt"] = now_iso()
    state["log"] = state["log"][-MAX_LOG:]
    mission_dir(slug).mkdir(parents=True, exist_ok=True)
    target = state_file(slug)
    tmp = target.with_name(target.name + ".%d.tmp" % os.getpid())
    try:
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, target)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


#: state.json の錠を待つ上限と、置き去りの錠を壊すまでの時間（秒）。
#: 待ちは短くてよい。ここで待たされるのは hook で、その先にあるのは
#: 「サブエージェントが起動するかどうか」だからである。
STATE_LOCK_WAIT_SEC = 5.0
STATE_LOCK_STALE_SEC = 30.0


@contextlib.contextmanager
def state_lock(slug: str):
    """state.json の「読んで・直して・書く」を、プロセスをまたいで直列化する。

    **これが無いと記録が黙って消える。** 1回のメッセージで6体まとめて起動すると
    hook が6プロセス同時にここへ来る。錠が無ければ、あとから書いたほうが
    「自分が読んだ時点の state」で上書きするので、先に書かれた5体が消える。
    os.replace が守ってくれるのは1回の書き込みだけで、読んでから書くまでの間は
    守らない。

    **取れなくても最後には進む。** 記録が1つ競り負けるのは困るが、hook が固まって
    Agent の起動そのものが止まるほうがずっと悪い。上限まで待ったら錠を無視して
    進む（置き去りの錠なら壊す）。
    """
    # **錠を missions/<slug>/ の中に置かない。** そこへ作ると、まだ存在しない
    # プロジェクトのディレクトリが錠のために先にでき、list_slugs() は missions/ 直下の
    # ディレクトリ名をそのまま数えるので、それを「もうあるプロジェクト」と見る。
    # すると start --project <新しい名前> の resolve_project が既存扱いに倒れ、
    # **作業場所（path）が空のまま記録される**（実測で踏んだ）。path が空だと、
    # そのミッションは稼働中の実測を一生読めない（あとから補う手段も無い）。
    try:
        LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        yield        # 錠を置けない。掛けずに進む（止めるよりまし）
        return
    path = LOCKS_DIR / (slug + ".lock")
    fd = None
    deadline = time.time() + STATE_LOCK_WAIT_SEC
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            # 前の持ち主が落ちて残った錠は、古くなった時点で壊してよい。
            try:
                if (time.time() - path.stat().st_mtime) > STATE_LOCK_STALE_SEC:
                    path.unlink()
                    continue
            except OSError:
                pass
            if time.time() >= deadline:
                break   # 待ち切った。錠なしで進む（止めるよりまし）
            time.sleep(0.02)
        except OSError:
            break       # 錠を作れない置き場（読み取り専用など）。錠なしで進む
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------- 正規化とマージ

#: 0.4.3 までの update_state.py が「モデル未指定」を表すために書き込んでいた値。
#: 当時は表示語をそのまま保存していた。読み取り側で空に寄せて、過去の記録でも
#: 読み手の言語で「不明」が出るようにする。
_LEGACY_UNKNOWN_MODEL = "不明"


def _model_value(raw) -> str:
    """モデル名を**言語に依存しない形**で返す。未指定なら空文字。

    ここで t("unknown") を返してはいけない。この値は server.py が JSON にして
    ブラウザへ渡すが、**画面の言語はブラウザ側が決める**ので、サーバーの言語で
    訳した語を入れると「サーバーは日本語・画面は韓国語」のときにそこだけ日本語で
    出る。訳すのは表示の直前（index.html 側）の仕事。
    """
    text = as_str(raw)
    return "" if text == _LEGACY_UNKNOWN_MODEL else text


def normalize_agent(a, source: str):
    """素の dict を画面が期待する形に整える。壊れていれば None を返して捨てる。"""
    if not isinstance(a, dict) or not as_str(a.get("id")):
        return None

    status = a.get("status") if a.get("status") in STATUSES else "running"

    result = None
    r = a.get("result")
    if isinstance(r, dict):
        result = {
            "elapsedSec": as_num(r.get("elapsedSec")),
            "tokens": as_num(r.get("tokens")),
            "toolCalls": as_num(r.get("toolCalls")),
            "headline": as_str(r.get("headline")),
        }

    return {
        "id": as_str(a.get("id")),
        "name": as_str(a.get("name")) or as_str(a.get("id")),
        "parentId": as_str(a.get("parentId")) or None,
        "generation": 0,  # 下の assign_generations で必ず上書きする
        "model": _model_value(a.get("model")),
        "mission": as_str(a.get("mission")),
        "status": status,
        "waiting": False,  # 下の assign_waiting で必ず上書きする（読み取り側の導出）
        "live": None,      # 下の assign_live で上書きする（稼働中で、実機が特定できたときだけ）
        "startedAt": as_str(a.get("startedAt")) or None,
        "finishedAt": as_str(a.get("finishedAt")) or None,
        "result": result,
        "source": source,  # 'main' = state.json / 'self' = 孫の自己申告
        # この機体を起動した Agent 呼び出しのID。hook が自動で登録したときだけ入る。
        # 実機の meta.json の toolUseId と突き合わせれば、名前も時刻も見ずに
        # 対応づけが決まる（livefeed.assign_live の規則0）。
        "toolUseId": as_str(a.get("toolUseId")) or None,
    }


def normalize_log_entry(e, fallback_who: str = ""):
    if not isinstance(e, dict):
        return None
    text = as_str(e.get("text"))
    if not text:
        return None
    return {
        "at": as_str(e.get("at")) or None,
        "who": as_str(e.get("who")) or fallback_who or "?",
        "text": text,
    }


def assign_generations(agents: list[dict]) -> None:
    """世代を parentId から実測で算出する。

    自己申告ファイルが generation を間違えて書いても画面は壊れない。
    """
    by_id = {a["id"]: a for a in agents}
    for a in agents:
        # 親IDが指定されているのに実体が居ない「孤児」は、指令塔直下として扱う
        if a["parentId"] and a["parentId"] not in by_id:
            a["generation"] = 1
            continue
        depth = 0
        cur = a
        seen = {a["id"]}
        while cur["parentId"] and cur["parentId"] in by_id and depth < MAX_DEPTH:
            cur = by_id[cur["parentId"]]
            if cur["id"] in seen:  # 循環
                break
            seen.add(cur["id"])
            depth += 1
        a["generation"] = depth


def assign_waiting(agents: list[dict]) -> None:
    """「報告待ち」を親子関係から導出する。稼働中の子を1体以上持つ稼働中の親が該当。

    書き込み側（update_state.py）には対応するコマンドが無い。これは state.json に
    記録される事実ではなく、記録された事実からの導出だからである。ダッシュボードへの
    書き込みは「起動直後」と「完了通知時」の2点だけ、という設計を崩さずに済む。

    ただし「子が動いている」は事実でも「親が待っている」は推測である点に注意。
    親が子と並行して自分の作業を進めていることはあり、そのときは実態とズレる。
    トークン数のような実測値と違い、外れても数字の捏造にはならないので導出で出すが、
    ラベルは status とは別扱いにして「稼働中」を上書きしない（status は 'running' のまま）。

    親の判定は画面側の effectiveParentId() と揃える。parentId が実在しない孤児は
    どの親にも数えない（画面でも指令塔の子ではなく根として並ぶため）。
    """
    ids = {a["id"] for a in agents}
    has_running_child: set[str] = set()
    for a in agents:
        if a["status"] != "running":
            continue
        pid = a["parentId"]
        if pid and pid in ids and pid != a["id"]:
            has_running_child.add(pid)
    for a in agents:
        a["waiting"] = a["status"] == "running" and a["id"] in has_running_child


def assign_live_safely(agents: list[dict], project_path: str, mission: dict, slug: str) -> list:
    """稼働中の機体に、Claude Code の記録から読んだ実測値を載せる。

    載るのは実測値だけで、推定はしない（トークン・ツール回数・経過秒は、そのエージェントの
    JSONL から数えた実数）。どの実機がどのカードかを確信できないときは何も載せない——
    別の機体の数字をカードに出すのが最悪の結果なので、「分からない」を優先する。

    livefeed は読むだけのモジュールだが、ここで例外を漏らすと /api/state が毎秒 500 を
    返し、稼働中のチームまで画面から消える。だから何が起きても黙って諦める。
    live が出ないことは、画面が壊れることより、はるかに軽い。

    返り値は「記録に無いのに動いている機体」の一覧。系統樹には入れず別枠で出す
    （親を推測して系統樹を描くと、それは実測ではなくなる）。
    """
    try:
        import livefeed
        return livefeed.assign_live(agents, project_path, mission, slug)
    except Exception:
        for a in agents:
            a["live"] = None
        return []


def extract_from_self_report(value) -> tuple[list, list]:
    """孫の自己申告1ファイル分を読む。単体 dict・リスト・{agents,log} の3形式を受け付ける。"""
    agents: list = []
    log: list = []
    if isinstance(value, list):
        agents.extend(value)
    elif isinstance(value, dict):
        if isinstance(value.get("agents"), list):
            agents.extend(value["agents"])
        if isinstance(value.get("log"), list):
            log.extend(value["log"])
        if as_str(value.get("id")):  # 単体エージェントとして書かれている
            agents.append(value)
    return agents, log


def _log_sort_key(e: dict):
    """時刻順に並べる。時刻が無い／読めないものは末尾へ。"""
    if not e["at"]:
        return (1, 0.0)
    try:
        return (0, datetime.fromisoformat(e["at"]).timestamp())
    except ValueError:
        return (1, 0.0)


def _build_state(slug: str, state_path: Path, agents_path: Path, *, live: bool = False) -> dict:
    """state.json と agents/*.json をマージして1つの状態にする（置き場所は引数で受ける）。

    現在のミッション（missions/<slug>/）と過去の記録（history/<runId>/）を
    まったく同じ形に組み立てるため、実体はここ1つにしてある。画面は同じ描画機構で
    どちらも描く。

    live=True のときだけ、稼働中の機体に実測の稼働状況を載せる（assign_live）。
    既定を False にしてあるのは、履歴が誤って live 判定されないようにするため。
    過去の記録は凍結されていなければならない。
    """
    warnings: list[str] = []

    ok, base, err = read_json_safe(state_path)
    if not ok or not isinstance(base, dict):
        if not ok and not is_not_created(err):
            warnings.append(t("cannot read state.json ({err})").format(err=err))
        base = empty_state()

    # --- state.json 側のエージェント（ID衝突時はこちらが優先）
    merged: dict[str, dict] = {}
    for raw in base.get("agents") if isinstance(base.get("agents"), list) else []:
        a = normalize_agent(raw, "main")
        if a and a["id"] not in merged:
            merged[a["id"]] = a

    logs: list[dict] = []
    for raw in base.get("log") if isinstance(base.get("log"), list) else []:
        e = normalize_log_entry(raw)
        if e:
            logs.append(e)

    # --- 孫（自己申告）の取り込み
    self_files: list[Path] = []
    try:
        self_files = sorted(p for p in agents_path.iterdir() if p.suffix.lower() == ".json")
    except FileNotFoundError:
        pass
    except OSError as e:
        warnings.append(t("cannot read agents/ ({err})").format(err=e))

    for path in self_files:
        ok_self, value, err_self = read_json_safe(path)
        if not ok_self:
            warnings.append(t("cannot read agents/{name} ({err})")
                            .format(name=path.name, err=err_self))
            continue
        raw_agents, raw_log = extract_from_self_report(value)
        for raw in raw_agents:
            a = normalize_agent(raw, "self")
            if a is None:
                warnings.append(t("agents/{name} contains an invalid agent definition")
                                .format(name=path.name))
                continue
            if a["id"] in merged:  # ID衝突は state.json 側の勝ち
                continue
            merged[a["id"]] = a
        for raw in raw_log:
            e = normalize_log_entry(raw, path.stem)
            if e:
                logs.append(e)

    # mission / summary / project は assign_live に渡すので、agents より先に組み立てる。
    # （summary は mission から取るので3行セットで動かすこと）
    mission = base.get("mission") if isinstance(base.get("mission"), dict) else empty_state()["mission"]
    summary = mission.get("summary")
    project = base.get("project") if isinstance(base.get("project"), dict) else {}

    agents = list(merged.values())
    assign_generations(agents)
    assign_waiting(agents)   # 孫の取り込み後に走らせる。孫だけが動いている親を取りこぼさないため
    live_orphans: list = []
    if live:
        live_orphans = assign_live_safely(agents, as_str(project.get("path")), mission, slug)
    logs.sort(key=_log_sort_key)

    return {
        "version": 2,
        "serverTime": now_iso(),  # 画面側の時計ズレを補正するため
        "updatedAt": as_str(base.get("updatedAt")) or None,
        "project": {
            "slug": slug,
            "name": as_str(project.get("name")) or slug,
            "path": as_str(project.get("path")),
        },
        "mission": {
            "phase": mission.get("phase") if mission.get("phase") in PHASES else "standby",
            "title": as_str(mission.get("title")) or t("(untitled mission)"),
            "startedAt": as_str(mission.get("startedAt")) or None,
            "finishedAt": as_str(mission.get("finishedAt")) or None,
            "summary": {
                "agentCount": as_num(summary.get("agentCount")),
                "totalTokens": as_num(summary.get("totalTokens")),
                "elapsedSec": as_num(summary.get("elapsedSec")),
                "headline": as_str(summary.get("headline")),
            }
            if isinstance(summary, dict)
            else None,
        },
        "agents": agents,
        "log": logs[-MAX_LOG:],
        "sources": {
            "main": ok,
            "selfReports": len(self_files),
            "warnings": warnings,
            # 記録に無いのに動いている機体。トップレベルではなくここに置くのは、画面の
            # 再描画の判定（sig）が sources を見ているため。トップレベルに置くと、孤児が
            # 増えても減っても画面が描き直されない。
            "liveOrphans": live_orphans,
        },
    }


def build_state(slug: str) -> dict:
    """いま画面に映すミッションの状態。"""
    return _build_state(slug, state_file(slug), agents_dir(slug), live=True)


def read_run(slug: str, run_id: str) -> dict:
    """過去の記録1件の完全な状態。build_state(slug) と同じ形を返す。

    孫の自己申告も、その run に一緒に退避された agents/ の方を読む。
    記録が無ければ FileNotFoundError。
    """
    if not is_valid_slug(slug):
        raise ValueError(t("invalid slug: {slug!r}").format(slug=slug))
    if not is_valid_run_id(run_id):
        raise ValueError(t("invalid runId: {run_id!r}").format(run_id=run_id))

    path = run_state_file(slug, run_id)
    if not path.is_file():
        raise FileNotFoundError(t("missions/{slug}/history/{run_id}/state.json does not exist")
                                .format(slug=slug, run_id=run_id))
    return _build_state(slug, path, run_agents_dir(slug, run_id))


def summarize_project(slug: str) -> dict:
    """CLI の一覧・起動ログ用の要約。稼働中の数を出すため孫も含めて数える。"""
    s = build_state(slug)
    workers = [a for a in s["agents"] if a["id"] != COMMAND_ID]
    return {
        "slug": slug,
        "name": s["project"]["name"],
        "path": s["project"]["path"],
        "phase": s["mission"]["phase"],
        "title": s["mission"]["title"],
        "updatedAt": s["updatedAt"],
        "running": sum(1 for a in workers if a["status"] == "running"),
        "done": sum(1 for a in workers if a["status"] == "done"),
        "total": len(workers),
    }


#: ユーザー名を伏せるときの置き換え文字列。
#:
#: **ここは訳さない。** この値は取扱説明書（manual.html）にも埋め込まれるが、
#: 説明書の言語を決めているのは**ブラウザ側**（localStorage）で、こちらを訳すと
#: サーバーの言語で決まってしまう。韓国語で読んでいる人の画面に日本語の
#: 「(ご自身のユーザー名)」が1か所だけ混ざる、という食い違いが起きる。
#: `<username>` なら、どの言語で読んでいても同じ意味に読めて、実際のパスとも
#: 見分けが付く。
USER_MASK = "<username>"


def _display_path(path) -> str:
    """説明書に出すパス。ホームディレクトリのうち**ユーザー名の1階層だけ**を
    `<username>` に置き換えて、画面越しにユーザー名が見えてしまわないようにする。

    ホームごと伏せずにユーザー名だけを伏せるのは、`C:/Users/<username>/.claude/…`（Windows の場合）
    のようにパスの形が残り、自分のどこを指しているのか読み手が判断できるため。

    コマンド例（コピペして実行する箇所）にもこれを使う。そのままでは実行できないが、
    説明書は画面共有や配布資料に写ることがあり、そこにユーザー名を出さないほうを
    優先する。読み手には `<username>` を自分のユーザー名に読み替えてもらう。
    """
    text = str(path)
    home = str(Path.home())
    if text == home or text.startswith(home + os.sep):
        return str(Path(home).parent / USER_MASK) + text[len(home):]
    return text


def _paths_are_masked() -> bool:
    """説明書に出るパスに `<username>` が現れるか。

    ツール本体がホームの外（開発用のチェックアウトなど）にあるときは1つも
    伏せられない。そのとき「`<username>` は読み替えてください」という注記だけが
    残ると、画面に無いものの説明になってしまうので、出す／出さないをここで決める。
    """
    return _display_path(TOOL_ROOT) != str(TOOL_ROOT)


def _instruction_paths_display() -> str:
    """説明書に出す「運用ルールはここ」のパス。

    実際に書き込まれている CLI のぶんだけを出す。未設定なら Claude Code のパスを
    出す（これから設定する人にとっては、書き込まれる予定の場所が知りたい情報で、
    対応 CLI を全部並べても選べない）。
    """
    keys = installed_agents() or ["claude"]
    return " / ".join(_display_path(instruction_file(key)) for key in keys)


def render_template(text: str) -> str:
    """HTML 内のプレースホルダを実際の環境の値に差し替える。

    説明書に環境ごとのパスを埋め込むために使う。これにより配布物には
    特定PCのパスを一切含めなくて済む。
    """
    return (
        text.replace("{{TOOL_ROOT}}", _display_path(TOOL_ROOT))
        .replace("{{MISSIONS_DIR}}", _display_path(MISSIONS_DIR))
        .replace("{{DATA_HOME}}", _display_path(DATA_HOME))
        .replace("{{INSTRUCTION_FILES}}", _instruction_paths_display())
        .replace("{{SERVER_PY}}", _display_path(TOOL_ROOT / "server.py"))
        .replace("{{UPDATE_PY}}", _display_path(TOOL_ROOT / "update_state.py"))
        .replace("{{LAUNCHER_PATH}}", _display_path(TOOL_ROOT / LAUNCHER.lstrip("./")))
        .replace("{{PY}}", PY_CMD)
        .replace("{{LAUNCHER}}", LAUNCHER)
        .replace("{{MASKED}}", "1" if _paths_are_masked() else "")
    )


def list_projects() -> list[dict]:
    """更新が新しい順に並べる。表示名が重複する場合は親ディレクトリ名を前に付ける。"""
    items = [summarize_project(s) for s in list_slugs()]

    counts: dict[str, int] = {}
    for p in items:
        counts[p["name"]] = counts.get(p["name"], 0) + 1
    for p in items:
        if counts.get(p["name"], 0) > 1 and p["path"]:
            parent = Path(p["path"]).parent.name
            if parent:
                p["name"] = f"{parent}/{p['name']}"

    items.sort(key=lambda p: (p["updatedAt"] or ""), reverse=True)
    return items
