#!/usr/bin/env python3
"""Claude Code 変更履歴トラッキング — データ層

changelog_cli.py から呼ばれる。責務は「ファイルの読み書き」だけで、hook stdin の
JSON をどう解釈するか（PreToolUse/PostToolUse の分岐、diffStat の抽出など）は
changelog_cli.py 側に置く。ここでは「もう組み立て終わったフィールド」を受け取って
保存し、保存したものを読み返して集計・整形するところまでを担当する。

ディレクトリ構成（プロジェクトローカル。1プロジェクト = 1 Git リポジトリ想定）:
    <project>/.claude/changelog/
    ├─ log/
    │  └─ <sessionId>.jsonl   生ログ。1行 = 1回のツール呼び出し（機械的・無選別）
    ├─ sessions/
    │  └─ <sessionId>.json    セッション要約（Claude が summarize で書く／自動代筆もある）
    ├─ index.json             セッションの新しい順の軽量一覧（sessions/*.json から再構築できる）
    └─ CHANGELOG.md           人間向け Markdown（sessions/*.json から再構築できる）

ホーム側（プロジェクトをまたいで1つ）:
    ~/.claude/agent-dashboard/changelog_registry.json
        {"path", "slug", "lastEventAt", "lastSummaryAt"} の配列。
        Phase 3 の server.py が「どのプロジェクトに変更履歴があるか」を見つける
        唯一の手がかりになる（プロジェクトローカル保存だけでは発見できないため）。

置き場所は dashlib.DATA_HOME を使う（ハードコードしない）。本番では
dashlib.resolve_data_home() が書き込み可能な TOOL_ROOT（= ~/.claude/agent-dashboard）
を選ぶので結果は同じだが、環境変数 AGENT_DASHBOARD_DATA_HOME による試験時の隔離が
そのまま効く（dashlib 冒頭のコメントにある「試験や一時的な隔離はこちらを使うこと」を
そのまま享受できる）。

規律（state.json / update_state.py と揃える）:
    - 実測できない値は推測で埋めない。素直に None（JSON の null）にする。
    - 書き込みは一時ファイル → os.replace のアトミック差し替え。
    - 外部依存ゼロ（標準ライブラリのみ）。
    - 自由記述（headline/body）は書かれた言語のまま保存し、翻訳・加工しない。

本文（diff の全文や変更前ファイル）は決してこのモジュールを通じて保存しない。
diffStat（追加/削除の行数）だけを扱う関数は changelog_cli.py 側にあるが、
契約として明記しておく: append_raw_event() に渡す dict のどのキーにも
originalFile・structuredPatch のような原文フィールドを含めてはならない。
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

import dashlib

# ---------------------------------------------------------------- パス

CHANGELOG_SUBPATH = (".claude", "changelog")
REGISTRY_FILENAME = "changelog_registry.json"

#: 生ログの末尾だけを残すときの上限（Bash の stdout/stderr）。
#: 全文は保存しない——標準出力に機微情報が出ることもあるため、tail に留める。
MAX_TAIL_LINES = 20
MAX_TAIL_CHARS = 4000

#: 生ログに残す Bash **コマンド本体**の上限（こちらは先頭を残す。truncate_command 参照）。
#: stdout/stderr だけ切り詰めてコマンドを無制限にすると、ヒアドキュメントで
#: ファイルを書く運用でファイル全文がそのまま jsonl に残る（実測3131文字、
#: 中の PASSWORD=… もそのまま）。gitignore モード B/C ではそれがリポジトリに入る。
MAX_COMMAND_LINES = 10
MAX_COMMAND_CHARS = 1000

#: 生ログ1件を読むときの想定フィールド順（読みやすさのためだけで、意味は持たない）。
RAW_FIELD_ORDER = (
    "seq", "at", "sessionId", "toolName", "toolUseId", "filePath",
    "bashCommand", "bashCommandTruncated", "diffStat", "bashResult",
    "status", "success", "durationMs",
)

#: この文字列を含む Bash コマンドは「変更履歴ツール自身の呼び出し」と見なす。
SELF_CLI_MARKER = "changelog_cli.py"


def changelog_dir(project_root: Path) -> Path:
    return Path(project_root, *CHANGELOG_SUBPATH)


def log_dir(project_root: Path) -> Path:
    return changelog_dir(project_root) / "log"


def sessions_dir(project_root: Path) -> Path:
    return changelog_dir(project_root) / "sessions"


def index_path(project_root: Path) -> Path:
    return changelog_dir(project_root) / "index.json"


def changelog_md_path(project_root: Path) -> Path:
    return changelog_dir(project_root) / "CHANGELOG.md"


def session_log_path(project_root: Path, session_id: str) -> Path:
    return log_dir(project_root) / f"{session_id}.jsonl"


def session_summary_path(project_root: Path, session_id: str) -> Path:
    return sessions_dir(project_root) / f"{session_id}.json"


def registry_path() -> Path:
    return dashlib.DATA_HOME / REGISTRY_FILENAME


# ---------------------------------------------------------------- セッションIDの検証
#
# session_id は Claude Code の hook stdin から来る、外から渡される値。
# そのままファイル名に使うので、dashlib.is_valid_slug と同じ考え方で
# パス区切り・危険文字を弾く（`../`等でchangelog/の外を触らせないため）。

_SESSION_ID_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_valid_session_id(session_id) -> bool:
    if not isinstance(session_id, str):
        return False
    s = session_id.strip()
    if not s or s in (".", ".."):
        return False
    if _SESSION_ID_UNSAFE.search(s):
        return False
    return Path(s).name == s


# ---------------------------------------------------------------- シェル用の引用符付け
#
# 「Python でこのスクリプトを実行する」という同じ1つの文字列を、この機能は3か所で
# 組み立てている:
#     1. hook の command 文字列               （changelog_setup.build_hook_specs）
#     2. CLAUDE.md に書く実行例               （install.build_changelog_block）
#     3. stop-check が stderr に出す実行指示   （changelog_cli.cmd_stop_check）
# **3つとも同じ POSIX シェルに渡る**（下記）ので、引用の流儀もここ1つに揃える。
# レビュー指摘のとおり、以前は「空白があれば二重引用符」「バックスラッシュが
# あれば二重引用符」「決め打ちで二重引用符」と3か所3流儀で、1か所直しても
# 残りは化けたままだった。
#
# なぜ POSIX シェルの規則なのか（Phase 1 のE2E実機検証で確認済み）:
#   - Claude Code は hooks.command を Windows 上でも bash 経由で実行する
#     （実機で `/usr/bin/bash: line 1: terminal-notifier: command not found`
#     を確認）。Claude が CLAUDE.md を読んで打つ Bash ツールも同じシェル。
#   - 引用の外にあるバックスラッシュはエスケープとして食われ、
#     `C:\Users\…\changelog_cli.py` が `C:Users…changelog_cli.py` に化ける
#     （＝「そんなファイルは無い」で全hookが機能しなくなる）。
#   - 二重引用符の中でも `$` `` ` `` `\` `"` は解釈される。`$` を含むパス
#     （`C:\build$\tools` のような共有名）は二重引用符の中で展開されて消える。
#     **完全にリテラルなのは単一引用符の中だけ**なので、単一引用符を使う。
#
# install.py の quote()（空白を含むときだけ二重引用符）は、これとは用途が違う
# 「人間が cmd.exe / PowerShell に打つ例」用で、あちらはあちらで正しい。だから
# 共有関数に巻き込まず、そのまま残してある。


def sh_quote(s) -> str:
    """POSIX シェルに1語として渡すための引用（shlex.quote と同じ規則）。

    安全な文字だけの語（`python`, `/usr/bin/python3` など）は引用符を付けずに
    返る。バックスラッシュ・空白・`$` などを含む語は単一引用符で囲まれ、語の中の
    単一引用符も POSIX の作法（`'"'"'`）で正しく閉じ直される。
    """
    return shlex.quote(str(s))


def sh_launcher(py: str) -> str:
    """Python の起動コマンド（`python` / `py -3` / 実行ファイルの絶対パス）を引用する。

    `py -3` のような複数語を丸ごと引用すると「py -3」という名前の実行ファイルを
    探しに行って壊れるので、**語ごとに**引用する。ただしパスらしき文字列
    （区切り文字を含む）は空白を含んでいても1語として扱う——空白入りのパスを
    語で割ってしまう方が確実に壊れる。install.quote() が既に付けた二重引用符は
    一度外してから付け直す（引用符ごと1語として引用すると、引用符そのものが
    パスの一部になってしまう）。
    """
    s = (py or "").strip()
    if not s:
        return s
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    elif "\\" not in s and "/" not in s:
        # `python` / `python3` / `py -3` のような裸のコマンド語（+オプション）。
        return " ".join(sh_quote(w) for w in s.split())
    # ここに来たのは実行ファイルのパス。**区切りを / に直してから**引用する。
    # bash は `/` を含まない語をコマンド名と見なして PATH から探すため、
    # `C:\…\python.exe` は引用の仕方に関わらず command not found になる
    # （実測。単一引用符でも二重引用符でも同じ）。`C:/…/python.exe` なら動く。
    return sh_quote(s.replace("\\", "/"))


def sh_cli_command(py: str, cli_path, *args: str) -> str:
    """`<python> <changelog_cli.py> <サブコマンド…>` を POSIX シェル用に組み立てる。

    3か所（hook / CLAUDE.md / stop-check のメッセージ）が同じ形になるように、
    組み立てそのものをここに置く。引数は既に引用済みとみなさず、そのまま渡す
    （`--headline "<何を・なぜ>"` のような**人間向けの見本**を含むことがあるため、
    ここでは引用しない。呼び手が必要なら sh_quote する）。
    """
    parts = [sh_launcher(py), sh_quote(cli_path)]
    parts.extend(a for a in args if a)
    return " ".join(parts)


# ---------------------------------------------------------------- アトミック書き込み
#
# dashlib.write_state と同じ作法（一時ファイル → os.replace）。dashlib には
# state.json 専用の write_state() しか無く、汎用の書き込みヘルパーは公開されて
# いないので、同じ作法をここに1つだけ用意する（book-keeping 用のファイルが
# 複数あるため：sessions/*.json, index.json, CHANGELOG.md, registry）。


def _atomic_write_text(path: Path, text: str) -> None:
    """一時ファイル → os.replace で差し替える。

    一時ファイル名に **PID を入れる**。dashlib.write_state は固定名（`.tmp`）だが、
    こちらは同じプロジェクトで2つのセッションが同時に Stop することが現実的に
    起こりうる（CHANGELOG.md / index.json は Stop のたびに書き直される）。固定名
    だと2つのプロセスが同じ一時ファイルを掴み、Windows では os.replace が
    PermissionError で落ちる。PID を入れれば衝突しない。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except BaseException:
        # 書き損じた一時ファイルを残さない（残すと次に見た人が中身を疑う）。
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _atomic_write_json(path: Path, value) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


# ---------------------------------------------------------------- ファイルロック
#
# 生ログの追記（seq の採番を含む）とホーム側レジストリの読み書きだけ、簡易ロックで
# 保護する。サブエージェント（Task経由）のツール呼び出しも同じ PostToolUse フックを
# 通って同じ jsonl に書きに来ることがあり、そこだけは複数プロセスの同時書き込みが
# 実際に起こりうるため。
#
# **ロックが取れなくてもフックを止めない。** ここで待ちすぎたり例外を投げたりすると
# 「記録のためのフックがユーザーの操作をブロックする」という本末転倒が起きる。
# タイムアウトしたら、ロック無しのまま進む（多少の seq の乱れより、フックが
# 詰まることの方がずっと悪い）。


class FileLock:
    """`<target>.lock` の排他作成だけを使う、依存ゼロの簡易ロック。"""

    def __init__(self, target: Path, timeout: float = 3.0, stale_after: float = 15.0):
        self.lock_path = Path(str(target) + ".lock")
        self.timeout = timeout
        self.stale_after = stale_after
        self._held = False

    def __enter__(self) -> "FileLock":
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self._held = True
                return self
            except FileExistsError:
                # 前のプロセスが異常終了してロックだけ残った場合の保険。
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                    if age > self.stale_after:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    self._held = False
                    return self  # ロック無しで進む（上の説明を参照）
                time.sleep(0.02)
            except OSError:
                self._held = False
                return self

    def __exit__(self, *exc) -> bool:
        if self._held:
            try:
                self.lock_path.unlink()
            except OSError:
                pass
        return False


# ---------------------------------------------------------------- 生ログ（raw jsonl）


def _count_lines(path: Path) -> int:
    """seq採番のために、いまの行数をファイル全体を読んで数える。

    既知のスケーリング限界: 1回の追記のたびにファイル全体を読み直すので、
    1セッションのツール呼び出しが数千件を超えるあたりから重くなり始める
    （O(n) が呼び出し回数ぶん積み重なる）。通常のセッション規模（数十〜数百件）
    では無視できる差だが、プラン記載の Phase 4「raw logのローテーション」で
    対処する前提の割り切り。厳密な連番よりも「フックを詰まらせない」ことを優先する。
    """
    if not path.is_file():
        return 0
    try:
        # errors="replace": jsonl に不正なバイトが1つ混ざっただけで
        # UnicodeDecodeError（OSError ではないので下の except では捕まらない）が
        # 飛び、そのセッションの記録が以後ずっと止まる——という壊れ方を避ける。
        # 数えているのは行数だけなので、化けた文字が混ざっても害は無い。
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except (OSError, ValueError):
        return 0


def append_raw_event(project_root: Path, session_id: str, fields: dict) -> dict | None:
    """1行分のフィールド（seq/at 抜き）を受け取り、jsonlへ1行追記する。

    seq はこの呼び出し時点の行数+1（ロックの中で数える）。at が渡されていなければ
    now_iso() を補う。書き込んだ行（dict）を返す。session_id が不正なら書かずに
    None を返す（フックを落とさないため、ここでは例外を投げない）。
    """
    if not is_valid_session_id(session_id):
        return None

    path = session_log_path(project_root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    row_in = dict(fields)
    row_in.setdefault("at", dashlib.now_iso())
    row_in["sessionId"] = session_id

    # コマンド本体の切り詰めは**書き込みの一本道であるここ**で必ず通す。呼び手
    # （changelog_cli の _build_fields_*）でやると、経路が増えたときに片方だけ
    # 素通りする。上限を超えたことは bashCommandTruncated で分かるようにする。
    if isinstance(row_in.get("bashCommand"), str):
        trimmed, was_truncated = truncate_command(row_in["bashCommand"])
        row_in["bashCommand"] = trimmed
        row_in["bashCommandTruncated"] = bool(row_in.get("bashCommandTruncated")) or was_truncated

    with FileLock(path):
        seq = _count_lines(path) + 1
        row_in["seq"] = seq
        row = {k: row_in.get(k) for k in RAW_FIELD_ORDER}
        line = json.dumps(row, ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    return row


def read_raw_events(project_root: Path, session_id: str) -> list[dict]:
    """生ログを seq 順（＝書いた順）で全部読む。壊れた行は1行だけ読み飛ばす。"""
    if not is_valid_session_id(session_id):
        return []
    path = session_log_path(project_root, session_id)
    if not path.is_file():
        return []
    try:
        # errors="replace": 不正なバイトが1つ混ざっただけで、そのセッションの
        # 記録・要約・stop-check が以後すべて黙って止まるのを避ける。壊れた行は
        # 下の json.loads で弾かれ、無事な行はそのまま読める。
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return []
    out: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # 1行破損で全体を落とさない
        if isinstance(row, dict):
            out.append(row)
    return out


def dedupe_bash_events(events: list[dict]) -> list[dict]:
    """同じ toolUseId の行は最後（pending→completedの更新後）だけ残す。

    Bash は PreToolUse で status:"pending" を先に書き、PostToolUse が来れば
    同じ toolUseId で status:"completed" の行を「追記」する（生ログは追記のみで
    行を書き換えない）。toolUseId が無い行（Edit/Write/NotebookEdit など）は
    重複しないのでそのまま残す。
    """
    keep: list[dict | None] = list(events)
    seen: dict[str, int] = {}
    for i, e in enumerate(events):
        tuid = e.get("toolUseId")
        if not tuid:
            continue
        if tuid in seen:
            keep[seen[tuid]] = None
        seen[tuid] = i
    return [e for e in keep if e is not None]


def is_self_invocation(event) -> bool:
    """その行が「変更履歴ツール自身を呼んだだけ」の Bash 呼び出しかどうか。

    summarize は Claude が Bash で実行する。**その Bash 呼び出し自体**が
    PreToolUse / PostToolUse で生ログに入るため、summarize した直後は必ず
    「未要約が1件ある」状態になる。この1件を数えていたせいで、
        summarize した → Stop がブロック → もう一度 summarize → Stop（2回目）
        → stop_hook_active=true → 代筆経路 → auto:true
    と、**手で書いた要約があるセッションまで例外なく auto:true に汚染され**、
    CHANGELOG.md にも毎回 `[自動追記] … Bash x1` が積まれていた（実測）。
    プロジェクトへの変更ではなく記録作業そのものなので、未要約の勘定からも
    要約の集計からも外す。

    切り詰め（truncate_command）は先頭を残すので、
    `python '…/changelog_cli.py' summarize …` の目印は必ず残る。
    """
    if not isinstance(event, dict) or event.get("toolName") != "Bash":
        return False
    cmd = event.get("bashCommand")
    return isinstance(cmd, str) and SELF_CLI_MARKER in cmd


# ---------------------------------------------------------------- tail 抽出（Bash出力）


def _opt_str(v) -> str | None:
    return v if isinstance(v, str) else None


def tail_text(text: str | None) -> tuple[str | None, bool]:
    """末尾 MAX_TAIL_LINES 行・MAX_TAIL_CHARS 文字だけを残す。(tail, truncated) を返す。"""
    if text is None:
        return None, False
    lines = text.splitlines()
    truncated = False
    if len(lines) > MAX_TAIL_LINES:
        lines = lines[-MAX_TAIL_LINES:]
        truncated = True
    joined = "\n".join(lines)
    if len(joined) > MAX_TAIL_CHARS:
        joined = joined[-MAX_TAIL_CHARS:]
        truncated = True
    return joined, truncated


def head_text(text: str | None, max_lines: int, max_chars: int) -> tuple[str | None, bool]:
    """先頭 max_lines 行・max_chars 文字だけを残す。(head, truncated) を返す。"""
    if text is None:
        return None, False
    truncated = False
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True
    joined = "\n".join(lines)
    if len(joined) > max_chars:
        joined = joined[:max_chars]
        truncated = True
    return joined, truncated


def truncate_command(command) -> tuple[str | None, bool]:
    """生ログに残す Bash コマンド本体を上限まで切り詰める。(command, truncated)。

    **末尾ではなく先頭を残す**。stdout/stderr は「結果」なので直近＝末尾が要る
    （tail_text）が、コマンドは「何をしようとしたか」が先頭に出る。
    `cat > secrets.env <<'EOF'` のような書き込みでは、末尾に来るのは
    ヒアドキュメントの中身＝まさに残したくないものの方。

    これは秘密の墨消しではない（1行目に秘密を書けば残る）。「際限なく溜めない」
    ための上限で、コマンドの意図が読める程度（既定10行・1000文字）に留める。
    切り詰めたことは呼び手が bashCommandTruncated で分かる。
    """
    if not isinstance(command, str):
        return (command if command is None else None), False
    return head_text(command, MAX_COMMAND_LINES, MAX_COMMAND_CHARS)


def extract_bash_result(tool_response) -> dict | None:
    if not isinstance(tool_response, dict):
        return None
    stdout_tail, out_trunc = tail_text(_opt_str(tool_response.get("stdout")))
    stderr_tail, err_trunc = tail_text(_opt_str(tool_response.get("stderr")))
    return {
        "stdoutTail": stdout_tail,
        "stderrTail": stderr_tail,
        "truncated": bool(out_trunc or err_trunc),
    }


def infer_bash_success(tool_response) -> bool | None:
    """Phase 0 実機検証の補正: exitCode は存在しない。stderr/interrupted からの
    緩い推測に留め、確信が持てなければ None にする（推測で埋めない規律）。
    """
    if not isinstance(tool_response, dict):
        return None
    interrupted = tool_response.get("interrupted")
    stderr = tool_response.get("stderr")
    if interrupted is True:
        return False
    if isinstance(stderr, str) and stderr.strip():
        return None  # 何か stderr に出ているが、それだけでは失敗と断定できない
    if interrupted is False:
        return True  # 中断されておらず stderr も空 → 緩く成功とみなす
    return None


# ---------------------------------------------------------------- diffStat 抽出（Edit/Write/NotebookEdit）
#
# **ここが唯一、原文（originalFile・structuredPatch の中身）に触れる場所。**
# 触れるのは行数を数えるためだけで、戻り値は {"added": int|None, "removed": int|None}
# の2値のみ。呼び出し側（changelog_cli.py）はこの戻り値だけを raw ログへ渡すこと。


def _stat_from_patch(patch) -> dict | None:
    if not isinstance(patch, list) or not patch:
        return None
    added = removed = 0
    counted = False
    for hunk in patch:
        if not isinstance(hunk, dict):
            continue
        lines = hunk.get("lines")
        if not isinstance(lines, list):
            continue
        counted = True
        for line in lines:
            if not isinstance(line, str) or not line:
                continue
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
    return {"added": added, "removed": removed} if counted else None


def _diff_stat_from_texts(original: str, new_text: str) -> dict:
    added = removed = 0
    sm = difflib.SequenceMatcher(a=original.splitlines(), b=new_text.splitlines(), autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "replace":
            removed += i2 - i1
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1
    return {"added": added, "removed": removed}


def _guess_new_text(tool_name: str, tool_input: dict) -> str | None:
    if not isinstance(tool_input, dict):
        return None
    if tool_name == "Write":
        return _opt_str(tool_input.get("content"))
    if tool_name == "Edit":
        return _opt_str(tool_input.get("new_string"))
    if tool_name == "NotebookEdit":
        return _opt_str(tool_input.get("new_source"))
    return None  # MultiEdit 等、複数編集をまとめて1つの新テキストにはできない


def extract_diff_stat(tool_name: str, tool_input, tool_response) -> dict:
    """変更前全文・diff本体は一切保持せず、追加/削除の行数だけを返す。

    優先順位（Phase 1 検証で実機の tool_response を捕捉し、以下の形を確認済み。
    claude 2.1.251, Windows）:
      1. tool_response.structuredPatch
         Edit、および Write の「既存ファイル上書き」（tool_response.type ==
         "update"）で実機確認済み。Write の「新規作成」（type == "create"）では
         structuredPatch が空リスト [] で返る（_stat_from_patch は空リストを
         「使えない」として None を返し、下の 4. へフォールする）。
      2. tool_response.edits[].structuredPatch（MultiEdit）
         現行の claude 2.1.251 には MultiEdit ツール自体が存在せず
         （`ToolSearch select:MultiEdit` でも見つからない）実機未検証のまま。
         将来 MultiEdit が復活した場合に備えて経路だけ残す（無害な保険）。
      3. NotebookEdit: tool_response.old_source / new_source
         実機確認済み。edit_mode="replace" では両方とも文字列で入る。
         edit_mode="insert" では old_source キー自体が存在しない（新規セル）。
         edit_mode="delete" では new_source が ""（セル削除）。
         originalFile/updated_file のような「ノートブック全体」のフィールド名
         ではなく、この cell 単位の old_source/new_source を使う方が
         セル1つぶんの差分だけで済み、扱う原文の範囲も小さくて済む。
      4. Write の新規作成（tool_response.type == "create"）
         実機確認済み: この場合 originalFile は null（空文字列ではない）で
         structuredPatch は []。null を「元は存在しなかった（＝空文字列相当）」
         として扱い、content 全体を追加行として数える。
      5. tool_response.originalFile と新テキストの行差分
         Edit/Write 上書きの保険フォールバック（通常は 1. で拾われるため、
         structuredPatch が壊れている・欠けている場合のみ通る）。
      6. どれも無ければ {"added": None, "removed": None}（推測で埋めない）

    どの分岐を通っても、読むのはこの関数の中だけで、戻り値は
    {"added": int|None, "removed": int|None} の2値のみ。
    """
    if not isinstance(tool_response, dict):
        return {"added": None, "removed": None}

    stat = _stat_from_patch(tool_response.get("structuredPatch"))
    if stat is not None:
        return stat

    edits = tool_response.get("edits")
    if isinstance(edits, list) and edits:
        added = removed = 0
        counted = False
        for e in edits:
            if not isinstance(e, dict):
                continue
            s = _stat_from_patch(e.get("structuredPatch"))
            if s is not None:
                counted = True
                added += s["added"] or 0
                removed += s["removed"] or 0
        if counted:
            return {"added": added, "removed": removed}

    if tool_name == "NotebookEdit" and ("old_source" in tool_response or "new_source" in tool_response):
        old_source = tool_response.get("old_source")
        new_source = tool_response.get("new_source")
        old_source = old_source if isinstance(old_source, str) else ""
        new_source = new_source if isinstance(new_source, str) else ""
        return _diff_stat_from_texts(old_source, new_source)

    if tool_name == "Write" and tool_response.get("type") == "create":
        new_text = _guess_new_text(tool_name, tool_input)
        if isinstance(new_text, str):
            return _diff_stat_from_texts("", new_text)

    original = tool_response.get("originalFile")
    new_text = _guess_new_text(tool_name, tool_input)
    if isinstance(original, str) and isinstance(new_text, str):
        return _diff_stat_from_texts(original, new_text)

    return {"added": None, "removed": None}


def extract_file_path(tool_input, tool_response) -> str | None:
    for src in (tool_response, tool_input):
        if not isinstance(src, dict):
            continue
        for key in ("filePath", "file_path", "notebook_path"):
            v = src.get(key)
            if isinstance(v, str) and v:
                return v
    return None


# ---------------------------------------------------------------- セッション要約


def read_session_summary(project_root: Path, session_id: str) -> dict | None:
    if not is_valid_session_id(session_id):
        return None
    ok, value, _ = dashlib.read_json_safe(session_summary_path(project_root, session_id))
    return value if ok and isinstance(value, dict) else None


def pending_summary_info(project_root: Path, session_id: str) -> dict:
    """stop-check が「未要約の生ログがあるか」を判定するための軽い情報。

    summarizedUpToSeq より新しい seq を持つ行を「未要約」とみなす。要約が
    一度も無ければ 0 として扱う（全部が未要約）。

    ただし **summarize の実行そのもの（is_self_invocation）は未要約に数えない**。
    数えていたせいで「summarize した直後に必ず未要約が1件ある」状態になり、
    Stop が毎回ブロック→代筆に流れていた（is_self_invocation の説明を参照）。
    数えた件数は selfInvocationCount として別に返す（消えたのではなく除いた、と
    デバッグ時に分かるように）。
    """
    events = read_raw_events(project_root, session_id)
    latest_seq = events[-1]["seq"] if events else 0
    summary = read_session_summary(project_root, session_id)
    summarized_up_to = 0
    has_summary = summary is not None
    if has_summary:
        n = dashlib.as_num(summary.get("summarizedUpToSeq"))
        summarized_up_to = n if isinstance(n, (int, float)) else 0

    pending_raw = [e for e in events if isinstance(e.get("seq"), int) and e["seq"] > summarized_up_to]
    pending_all = dedupe_bash_events(pending_raw)
    pending = [e for e in pending_all if not is_self_invocation(e)]
    return {
        "latestSeq": latest_seq,
        "summarizedUpToSeq": summarized_up_to,
        "pendingEvents": pending,
        "pendingCount": len(pending),
        "selfInvocationCount": len(pending_all) - len(pending),
        "hasSummary": has_summary,
    }


def write_session_summary(
    project_root: Path,
    session_id: str,
    *,
    headline: str,
    body: str | None,
    auto: bool,
    summarized_up_to_seq: int,
    extra_files=None,
) -> dict | None:
    """セッション要約ファイルを書く（上書き）。書いた内容（dict）を返す。

    startedAt は最初に書かれた値を保つ（同じセッションが複数回 summarize
    されても、セッションの開始時刻は変わらないため）。endedAt / filesTouched /
    toolCallCounts はこの呼び出し時点の生ログ全体から機械的に再集計する
    （「セッション全体の、いま分かっている最新像」を保つ設計。差分だけを
    溜め込む形にすると、複数回の summarize で要約が断片化してしまう）。

    session_id が不正なら書かずに None を返す。
    """
    if not is_valid_session_id(session_id):
        return None

    events = read_raw_events(project_root, session_id)
    clean = dedupe_bash_events(events)

    started_at = events[0]["at"] if events else None
    existing = read_session_summary(project_root, session_id)
    if existing and existing.get("startedAt"):
        started_at = existing["startedAt"]

    files: set[str] = set()
    counts: dict[str, int] = {}
    for e in clean:
        # 記録作業そのもの（summarize / status を Bash で叩いた分）は、この
        # セッションが「何をしたか」ではないので集計に入れない。入れると
        # CHANGELOG.md の「ツール呼び出し: Bash x3」が記録作業で水増しされる。
        if is_self_invocation(e):
            continue
        tool = e.get("toolName")
        if isinstance(tool, str) and tool:
            counts[tool] = counts.get(tool, 0) + 1
        fp = e.get("filePath")
        if isinstance(fp, str) and fp:
            files.add(fp)
    for f in (extra_files or []):
        f = dashlib.as_str(f)
        if f:
            files.add(f)

    summary = {
        "sessionId": session_id,
        "startedAt": started_at,
        "endedAt": dashlib.now_iso(),
        "summarizedUpToSeq": summarized_up_to_seq,
        "headline": dashlib.as_str(headline),
        "body": body if isinstance(body, str) else None,
        "auto": bool(auto),
        "filesTouched": sorted(files),
        "toolCallCounts": counts,
    }
    _atomic_write_json(session_summary_path(project_root, session_id), summary)
    return summary


# ---------------------------------------------------------------- index.json / CHANGELOG.md


def list_all_summaries(project_root: Path) -> list[dict]:
    d = sessions_dir(project_root)
    out: list[dict] = []
    try:
        paths = sorted(d.iterdir())
    except OSError:
        return out
    for p in paths:
        if p.suffix != ".json":
            continue
        ok, value, _ = dashlib.read_json_safe(p)
        if ok and isinstance(value, dict):
            out.append(value)
    out.sort(key=lambda s: (s.get("endedAt") or s.get("startedAt") or ""), reverse=True)
    return out


def write_index(project_root: Path) -> dict:
    summaries = list_all_summaries(project_root)
    entries = [
        {
            "sessionId": s.get("sessionId"),
            "startedAt": s.get("startedAt"),
            "endedAt": s.get("endedAt"),
            "headline": s.get("headline"),
            "auto": bool(s.get("auto")),
            "fileCount": len(s.get("filesTouched") or []),
            "toolCallCount": sum((s.get("toolCallCounts") or {}).values()),
        }
        for s in summaries
    ]
    index = {"updatedAt": dashlib.now_iso(), "sessions": entries}
    _atomic_write_json(index_path(project_root), index)
    return index


def render_changelog_md(project_root: Path) -> Path:
    summaries = list_all_summaries(project_root)
    lines = [
        "# Changelog",
        "",
        "Claude Code の変更履歴の自動記録"
        "（`changelog_cli.py summarize` により生成。手で編集しても次の summarize で上書きされる）。",
        "",
    ]
    if not summaries:
        lines.append("(まだ記録がありません)")
        lines.append("")
    for s in summaries:
        when = (s.get("endedAt") or s.get("startedAt") or "")[:19].replace("T", " ") or "?"
        headline = s.get("headline") or "(見出しなし)"
        auto_mark = " `auto`" if s.get("auto") else ""
        lines.append(f"## {when} — {headline}{auto_mark}")
        lines.append("")
        body = s.get("body")
        if body:
            lines.append(body)
            lines.append("")
        files = s.get("filesTouched") or []
        if files:
            lines.append("- ファイル: " + ", ".join(files))
        counts = s.get("toolCallCounts") or {}
        if counts:
            counts_str = ", ".join(f"{k} x{v}" for k, v in sorted(counts.items()))
            lines.append("- ツール呼び出し: " + counts_str)
        lines.append(f"- セッション: `{s.get('sessionId')}`")
        lines.append("")
        lines.append("---")
        lines.append("")
    path = changelog_md_path(project_root)
    _atomic_write_text(path, "\n".join(lines).rstrip("\n") + "\n")
    return path


def render_all(project_root: Path) -> Path:
    """index.json と CHANGELOG.md を sessions/*.json から作り直す（冪等）。"""
    write_index(project_root)
    return render_changelog_md(project_root)


# ---------------------------------------------------------------- 中央レジストリ


def read_registry() -> list[dict]:
    entries, _ok = read_registry_checked()
    return entries


def read_registry_checked() -> tuple[list[dict], bool]:
    """(登録の一覧, 読めたか) を返す。

    2番目が False なのは「ファイルは在るのに読めなかった」ときだけ（壊れた JSON、
    配列ではない、不正なバイト列）。まだ無い・空っぽは「読めた（0件）」として
    True を返す。**この区別が無いと、壊れた登録簿を [] と読んでそのまま書き直し、
    他のプロジェクトの登録を黙って消してしまう。**
    """
    reg_path = registry_path()
    ok, value, _ = dashlib.read_json_safe(reg_path)
    if not ok or not isinstance(value, list):
        if not reg_path.is_file():
            return [], True  # まだ作られていないだけ
        try:
            empty = not reg_path.read_text(encoding="utf-8", errors="replace").strip()
        except (OSError, ValueError):
            empty = False
        return [], bool(empty)
    out: list[dict] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        path = dashlib.as_str(item.get("path"))
        if not path:
            continue
        out.append(
            {
                "path": path,
                "slug": dashlib.as_str(item.get("slug")) or dashlib.slug_for_path(Path(path)),
                "lastEventAt": dashlib.as_str(item.get("lastEventAt")) or None,
                "lastSummaryAt": dashlib.as_str(item.get("lastSummaryAt")) or None,
            }
        )
    return out, True


def _write_registry(entries: list[dict]) -> None:
    _atomic_write_json(registry_path(), entries)


def quarantine_registry() -> Path | None:
    """壊れて読めない登録簿を脇へ避ける（改名する）。避けた先を返す。

    ここを素通りして [] から書き直すと、**他のプロジェクトの登録が黙って消える**
    （各プロジェクトは次のイベントで勝手に復活するが、消えたこと自体は誰にも
    分からない）。中身が読めなくても、捨てずに残しておけば後から手で拾える。
    """
    path = registry_path()
    if not path.is_file():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.corrupt-{stamp}.bak")
    if dest.exists():
        dest = path.with_name(f"{path.name}.corrupt-{stamp}-{os.getpid()}.bak")
    try:
        os.replace(path, dest)
    except OSError:
        return None
    print(
        f"changelog: 登録簿 {path} を読めませんでした。上書きせず {dest.name} へ"
        "退避し、新しい登録簿を作り直します（他プロジェクトの登録は次回の記録で"
        "自動的に復活します）。",
        file=sys.stderr,
    )
    return dest


def upsert_registry(
    project_root: Path, *, event_at: str | None = None, summary_at: str | None = None
) -> dict:
    """レジストリに1件登録・更新する。event_at/summary_at のうち渡された方だけ更新する。"""
    path_str = str(Path(project_root).resolve())
    slug = dashlib.slug_for_path(Path(project_root))

    with FileLock(registry_path()):
        entries, readable = read_registry_checked()
        if not readable:
            # 読めなかった＝壊れている。上書きする前に退避する（消さない）。
            quarantine_registry()
        found = None
        for e in entries:
            if e["path"] == path_str:
                found = e
                break
        if found is None:
            found = {"path": path_str, "slug": slug, "lastEventAt": None, "lastSummaryAt": None}
            entries.append(found)
        else:
            found["slug"] = slug
        if event_at:
            found["lastEventAt"] = event_at
        if summary_at:
            found["lastSummaryAt"] = summary_at
        _write_registry(entries)
        return dict(found)


# ---------------------------------------------------------------- デバッグ用の軽い集計


def list_session_ids_with_logs(project_root: Path) -> list[str]:
    d = log_dir(project_root)
    try:
        return sorted(p.stem for p in d.iterdir() if p.suffix == ".jsonl")
    except OSError:
        return []
