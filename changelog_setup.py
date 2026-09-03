#!/usr/bin/env python3
"""Claude Code 変更履歴トラッキング — プロジェクトローカルの初期設定（Phase 2）

VS Code 拡張機能側から、ワークスペースにつき1回呼ばれる想定のスクリプト。
呼び出し形式は固定（拡張機能側と合意済みのインタフェース。勝手に変えない）:

    python changelog_setup.py --project-root <workspaceの絶対パス> \\
        --gitignore-mode <A|B|C> [--print] [--uninstall]

責務:
  1. <project-root>/.claude/changelog/{log,sessions}/ ディレクトリを作成する。
  2. <project-root>/.claude/settings.local.json へ hooks.PreToolUse（Bash用）/
     hooks.PostToolUse / hooks.Stop の3エントリをマージ追記する
     （既存の他のフックエントリ・キー順は一切変更しない。判定は「command文字列に
     changelog_cli.py を含むエントリが既にあるか」——あれば何もしない）。
  3. --gitignore-mode に応じて <project-root>/.gitignore へ追記提案する
     （A: log/ のみ無視・既定/推奨、B: 何もしない、C: .claude/changelog/ ごと無視。
     既に同じ行があれば足さない）。
     **モード B は生ログ（log/）まで Git の追跡対象に残す。** 生ログには実行した
     Bash コマンドの先頭10行と出力の末尾が入るので、コマンドラインに書いた
     機微情報（トークン・パスワード等）がそのままリポジトリにコミットされうる。
  4. changelog_lib.py の upsert_registry() を再利用して、このプロジェクトを
     ~/.claude/agent-dashboard/changelog_registry.json へ登録する。

終了コード: 成功で 0。失敗時は非0 + stderr にエラーメッセージ。
べき等: 同じ内容なら再実行しても安全（余計な追記・重複を作らない）。

--print: 実際に書き込む内容を表示するだけ（dry-run。確認ダイアログでの表示用）。
         ファイル・ディレクトリへの書き込みは一切行わない。
--uninstall: 追加した hooks エントリと .gitignore への追記だけを取り除く。
         ディレクトリ（.claude/changelog/ 配下の実データ）と中央レジストリへの
         登録は取り除かない（記録済みの変更履歴を誤って消さないため。実際に
         プロジェクトの changelog を削除したい場合は利用者が手動で行う）。

Python 起動コマンドの決め方（"python" / "python3" / "py -3" の実測判定）は
install.py の detect_python_command() をそのまま再利用する（車輪の再発明をしない。
install.py 側にも同じ検出結果を書く一貫性がある）。hook の command 文字列の引用は
changelog_lib.sh_cli_command() に一本化してある（install.quote() は「人間が
cmd.exe / PowerShell に打つ例」用で、用途が違う）。
registry 登録は changelog_lib.upsert_registry() を再利用する。
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib  # noqa: E402
import changelog_lib as cl  # noqa: E402
import install  # noqa: E402  (detect_python_command() / quote() の再利用のため)

dashlib.use_utf8_stdio()


class SetupError(Exception):
    """呼び出し側（VS Code 拡張機能）に非0終了+メッセージで伝えるべきエラー。"""


# ---------------------------------------------------------------- hooks の組み立て

#: この3つの hook イベント種別だけを扱う。plan の「Hooks設定」節どおりの構造。
HOOK_EVENT_TYPES = ("PreToolUse", "PostToolUse", "Stop")

#: 「もう設定済みか」を判定する目印。この文字列を command に含むエントリが
#: 既にあれば、そのイベント種別には何も足さない（べき等・重複防止）。
#:
#: **目印は merge_hooks / unmerge_hooks の引数である。** ここは変更履歴用の既定値に
#: すぎない。settings.local.json には別系統の hook（サブエージェントの自動登録）も
#: 入りうるので、判定を定数に固定すると、2系統目で**べき等性が壊れて毎回重複追加され、
#: 取り消しでは一件も消えない**（どちらも黙って起きる）。
HOOK_MARKER = "changelog_cli.py"


#: log-event の hook command の末尾に足す多層防御。
#:
#: changelog_cli.main() は argparse の失敗も import の失敗も 0 に正規化するが、
#: **Python がそもそも起動できなければ、そのコードは1行も動かない**
#: （agent-dashboard を移動・削除した、python が PATH から消えた、等）。
#: そのときシェルが返すのは 2 や 127 で、PreToolUse の非0は「そのツール呼び出しを
#: 拒否する」の意味になり、**すべての Bash が拒否される**。`; exit 0` を付けておけば、
#: 直前が何で終わっていてもこのフックは 0 で終わる。
#:
#: **stop-check には付けない。** あちらは exit 2 が「要約を書かせるための意図した
#: ブロック」で、機能そのもの。ここで潰したら stop-check は何もしないのと同じになる。
HOOK_TAIL_NEVER_FAIL = "; exit 0"


def build_hook_specs(py: str, cli_path: str) -> dict:
    """3つの hook イベント種別ごとに、追加すべき1エントリ（matcher+hooks）を返す。

    plan の「Hooks設定」節にある構造そのもの:
        PreToolUse  (matcher: "Bash")   → log-event --phase pre
        PostToolUse (matcher: "Edit|MultiEdit|Write|NotebookEdit|Bash") → log-event
        Stop        (matcher: "")       → stop-check

    引用は changelog_lib の共通ヘルパー（sh_launcher / sh_quote）に任せる。
    以前はここに専用の _hook_quote があり、install.quote()・stop-check の
    メッセージと合わせて**同じ用途で3か所3流儀**になっていた（レビュー指摘）。
    引用の理屈（なぜ単一引用符か）は changelog_lib の該当節に1か所だけ書いてある。
    """
    log_pre = cl.sh_cli_command(py, cli_path, "log-event", "--phase", "pre")
    log_post = cl.sh_cli_command(py, cli_path, "log-event")
    stop = cl.sh_cli_command(py, cli_path, "stop-check")
    return {
        "PreToolUse": {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": log_pre + HOOK_TAIL_NEVER_FAIL}],
        },
        "PostToolUse": {
            "matcher": "Edit|MultiEdit|Write|NotebookEdit|Bash",
            "hooks": [{"type": "command", "command": log_post + HOOK_TAIL_NEVER_FAIL}],
        },
        "Stop": {
            "matcher": "",
            "hooks": [{"type": "command", "command": stop}],
        },
    }


def _entry_has_marker(entry, marker=HOOK_MARKER) -> bool:
    """このエントリは自分たちが足したものか。

    marker は文字列でも文字列のタプルでもよい。タプルのときは**全部**含むことを
    求める。1語だけで見分けようとすると、その語を含む利用者自身の hook を
    自分のものと取り違えて、取り消しのときに他人の設定を消してしまう。
    """
    if not isinstance(entry, dict):
        return False
    hooks_list = entry.get("hooks")
    if not isinstance(hooks_list, list):
        return False
    needles = (marker,) if isinstance(marker, str) else tuple(marker)
    for h in hooks_list:
        if isinstance(h, dict):
            cmd = h.get("command")
            if isinstance(cmd, str) and all(n in cmd for n in needles):
                return True
    return False


def _array_has_marker(arr, marker=HOOK_MARKER) -> bool:
    return isinstance(arr, list) and any(_entry_has_marker(e, marker) for e in arr)


def merge_hooks(settings: dict, specs: dict, marker=HOOK_MARKER) -> tuple[dict, dict]:
    """settings（dict）に specs の3エントリをマージした新しい dict を返す。

    引数の settings は変更しない（deepcopy して返す）。**既存の他のエントリ・
    キー順には一切触れない**——各イベント種別の配列に、まだ無ければ末尾へ
    1エントリ追加するだけ。既に changelog_cli.py を含むエントリがあれば、その
    イベント種別には何もしない（要求どおりの判定粒度）。

    戻り値: (新しい settings, {event_type: bool}) 。bool は「今回追加したか」。
    settings.hooks が dict 以外、または settings.hooks.<event_type> が list 以外
    なら SetupError を投げる（壊れた設定を黙って書き換えない）。
    """
    out = copy.deepcopy(settings) if isinstance(settings, dict) else {}
    hooks = out.get("hooks")
    if hooks is None:
        hooks = {}
        out["hooks"] = hooks
    elif not isinstance(hooks, dict):
        raise SetupError(
            "settings.local.json の hooks がオブジェクトではありません"
            "（壊れているか、想定と違う形式です。手動での確認をお願いします）。"
        )

    added: dict[str, bool] = {}
    for event_type, spec in specs.items():
        arr = hooks.get(event_type)
        if arr is None:
            arr = []
            hooks[event_type] = arr
        elif not isinstance(arr, list):
            raise SetupError(
                f"settings.local.json の hooks.{event_type} が配列ではありません"
                "（壊れているか、想定と違う形式です。手動での確認をお願いします）。"
            )

        if _array_has_marker(arr, marker):
            added[event_type] = False
            continue
        arr.append(copy.deepcopy(spec))
        added[event_type] = True

    return out, added


def unmerge_hooks(settings: dict, specs: dict, marker=HOOK_MARKER) -> tuple[dict, dict]:
    """merge_hooks が足したエントリ（command に changelog_cli.py を含むもの）だけを
    取り除く。他の hook エントリ・他のキーには一切触れない。

    配列が空になったら、そのイベント種別キーごと削除する。hooks 自体が空になれば
    hooks キーも削除する（後始末。空配列を残さない）。

    戻り値: (新しい settings, {event_type: 削除した件数})
    """
    out = copy.deepcopy(settings) if isinstance(settings, dict) else {}
    removed: dict[str, int] = {et: 0 for et in specs}
    hooks = out.get("hooks")
    if not isinstance(hooks, dict):
        return out, removed

    for event_type in specs:
        arr = hooks.get(event_type)
        if not isinstance(arr, list):
            continue
        kept = [e for e in arr if not _entry_has_marker(e, marker)]
        removed[event_type] = len(arr) - len(kept)
        if kept:
            hooks[event_type] = kept
        else:
            hooks.pop(event_type, None)

    if not hooks:
        out.pop("hooks", None)
    return out, removed


# ---------------------------------------------------------------- settings.local.json の読み書き


def settings_local_path(project_root: Path) -> Path:
    return project_root / ".claude" / "settings.local.json"


def read_settings_local(path: Path) -> dict:
    """存在しなければ {}。壊れていれば SetupError（黙って上書きしない）。"""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SetupError(f"{path} を読めません（{e}）") from e
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise SetupError(
            f"{path} が JSON として読めません（{e.msg} / {e.lineno}行目 {e.colno}列目）。"
            "壊れている可能性があるため、書き込みを中止しました。"
        ) from e
    if not isinstance(data, dict):
        raise SetupError(f"{path} の中身がオブジェクトではありません。")
    return data


def _atomic_write_json(path: Path, value: dict) -> None:
    # 一時ファイル名に PID を入れる（同じプロジェクトで2つ動いても衝突しない。
    # Windows では衝突した瞬間に os.replace が PermissionError で落ちる）。
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- .gitignore の処理

#: このスクリプトが管理する行のマーカーコメント。**この行の直後にある行だけ**を
#: --uninstall の対象にする（利用者が偶然同じパターンを自分で書いていた行を
#: 誤って消さないための安全策）。
GITIGNORE_MARKER = "# agent-dashboard: Claude Code changelog tracking (auto-added; safe to remove)"

#: モードごとに追加する1行。B は何もしない。
GITIGNORE_PATTERNS = {
    "A": ".claude/changelog/log/",
    "C": ".claude/changelog/",
}


def gitignore_path(project_root: Path) -> Path:
    return project_root / ".gitignore"


def plan_gitignore_add(path: Path, mode: str) -> tuple[str | None, bool]:
    """(追加するパターン行 または None, 既に足す必要が無いか) を返す。

    mode "B" は常に (None, True)（何もしない）。
    既にファイル中にそのパターンの行がそのまま存在すれば (pattern, True)
    （足す必要は無いが、モードとしては「その行がある」ことを表す）。
    """
    if mode == "B":
        return None, True
    pattern = GITIGNORE_PATTERNS[mode]
    if not path.is_file():
        return pattern, False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SetupError(f"{path} を読めません（{e}）") from e
    existing_lines = {line.strip() for line in text.splitlines()}
    if pattern in existing_lines:
        return pattern, True
    return pattern, False


def apply_gitignore_add(path: Path, pattern: str) -> None:
    """マーカーコメント + パターン行を末尾に追記する。既存の内容には一切触れず、
    末尾に足すだけ（読みやすいよう、直前が空行でなければ1行空けてから足す）。
    """
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text or text.endswith("\n\n"):
        prefix = ""
    elif text.endswith("\n"):
        prefix = "\n"
    else:
        prefix = "\n\n"
    new_text = text + prefix + GITIGNORE_MARKER + "\n" + pattern + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.gitignore.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)


def _scan_gitignore_marker_lines(lines: list[str]) -> list[int]:
    """GITIGNORE_MARKER の行のうち、直後が管理対象パターン行であるものの
    インデックスを返す（マーカー単体のインデックス。ペアの先頭）。

    マーカーの付いていない、利用者が自分で書いた同一パターンの行はここには
    含まれない＝絶対に対象にならない。
    """
    known_patterns = set(GITIGNORE_PATTERNS.values())
    hits: list[int] = []
    i = 0
    while i < len(lines):
        if (lines[i].strip() == GITIGNORE_MARKER
                and i + 1 < len(lines) and lines[i + 1].strip() in known_patterns):
            hits.append(i)
            i += 2
            continue
        i += 1
    return hits


def count_gitignore_entries(path: Path) -> int:
    """このツールが付けたマーカー付きの行が何組あるか（プレビュー用。読み取りのみ）。"""
    if not path.is_file():
        return 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SetupError(f"{path} を読めません（{e}）") from e
    return len(_scan_gitignore_marker_lines(text.split("\n")))


def remove_gitignore_entries(path: Path) -> int:
    """GITIGNORE_MARKER の直後にある管理対象パターン行だけを取り除く。

    マーカーの付いていない、利用者が自分で書いた同一パターンの行は絶対に
    消さない。取り除いた組の数を返す（0 なら変更なし＝ファイルは書き換えない）。
    """
    if not path.is_file():
        return 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SetupError(f"{path} を読めません（{e}）") from e

    lines = text.split("\n")
    hits = set(_scan_gitignore_marker_lines(lines))
    if not hits:
        return 0

    out_lines: list[str] = []
    i = 0
    while i < len(lines):
        if i in hits:
            i += 2  # マーカー行とパターン行の両方を飛ばす（=削除）
            continue
        out_lines.append(lines[i])
        i += 1

    new_text = "\n".join(out_lines)
    # 連続する空行が残りがちなので、末尾の余分な空行だけ軽く整える
    # （利用者の記述の間にある空行には触らない——末尾だけを見る）。
    new_text = new_text.rstrip("\n")
    new_text = (new_text + "\n") if new_text else ""

    tmp = path.with_name(f"{path.name}.{os.getpid()}.gitignore.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, path)
    return len(hits)


# ---------------------------------------------------------------- ディレクトリ作成


def plan_directories(project_root: Path) -> list[Path]:
    """作る必要があるディレクトリ（まだ無いもの）を返す。"""
    dirs = [cl.log_dir(project_root), cl.sessions_dir(project_root)]
    return [d for d in dirs if not d.is_dir()]


# ---------------------------------------------------------------- メイン処理


def do_setup(project_root: Path, gitignore_mode: str, *, print_only: bool) -> int:
    py = install.detect_python_command()
    # 引用は build_hook_specs（= changelog_lib の共通ヘルパー）に任せるので、
    # ここでは**生のパスのまま**渡す（二重に引用すると引用符がパスの一部になる）。
    cli_path = str(HERE / "changelog_cli.py")
    specs = build_hook_specs(py, cli_path)

    settings_path = settings_local_path(project_root)
    existing_settings = read_settings_local(settings_path)
    merged_settings, added = merge_hooks(existing_settings, specs)

    gitignore_target = gitignore_path(project_root)
    gi_pattern, gi_already = plan_gitignore_add(gitignore_target, gitignore_mode)

    dirs_to_create = plan_directories(project_root)

    print()
    print("=" * 70)
    print("  Claude Code 変更履歴トラッキング — プロジェクトローカル初期設定")
    print("=" * 70)
    print()
    print("  プロジェクト        : " + str(project_root))
    print()

    print("  [1] ディレクトリ")
    for d in (cl.log_dir(project_root), cl.sessions_dir(project_root)):
        state = "作成します" if d in dirs_to_create else "既に存在（変更なし）"
        print(f"      {d}  … {state}")
    print()

    print("  [2] settings.local.json  " + str(settings_path))
    for event_type in specs:
        if added[event_type]:
            spec = specs[event_type]
            print(f"      hooks.{event_type}: 追加します"
                  f"  matcher={spec['matcher']!r}  command={spec['hooks'][0]['command']!r}")
        else:
            print(f"      hooks.{event_type}: 既に設定済み（変更なし）")
    print()

    print(f"  [3] .gitignore（モード {gitignore_mode}）  " + str(gitignore_target))
    if gitignore_mode == "B":
        print("      何もしません（モード B）")
        print("      注意: 生ログ（log/）も Git の追跡対象のままになります。"
              "生ログには Bash コマンドの先頭10行と出力の末尾が入るため、"
              "コマンドラインに書いた機微情報もリポジトリにコミットされます。")
    elif gi_already:
        print(f"      既に同じ行があります（変更なし）: {gi_pattern}")
    else:
        print(f"      次の行を追記します: {gi_pattern}")
    print()

    print("  [4] 中央レジストリ  " + str(cl.registry_path()))
    print("      このプロジェクトを登録します（changelog_lib.upsert_registry）")
    print()

    if print_only:
        print("  --print が指定されているため、実際の書き込みは行っていません。")
        print()
        return 0

    # ---- ここから実際の書き込み ----

    for d in dirs_to_create:
        d.mkdir(parents=True, exist_ok=True)

    if any(added.values()):
        _atomic_write_json(settings_path, merged_settings)

    if gitignore_mode != "B" and not gi_already and gi_pattern:
        apply_gitignore_add(gitignore_target, gi_pattern)

    cl.upsert_registry(project_root)

    print("  完了しました。")
    print()
    return 0


def do_uninstall_setup(project_root: Path, gitignore_mode: str, *, print_only: bool) -> int:
    """hooks エントリと .gitignore への追記だけを取り除く。

    ディレクトリ（.claude/changelog/ の実データ）と中央レジストリへの登録は
    そのまま残す（責務の説明どおり。過去の記録を誤って消さないため）。
    gitignore_mode は受け取るが、削除の対象は「このツールが付けたマーカー付きの
    行」全部（A/C どちらのパターンでも）——過去にモードを切り替えて運用していた
    場合でも取りこぼさないための判断（詳細は報告を参照）。
    """
    py = install.detect_python_command()
    # 引用は build_hook_specs（= changelog_lib の共通ヘルパー）に任せるので、
    # ここでは**生のパスのまま**渡す（二重に引用すると引用符がパスの一部になる）。
    cli_path = str(HERE / "changelog_cli.py")
    specs = build_hook_specs(py, cli_path)

    settings_path = settings_local_path(project_root)
    existing_settings = read_settings_local(settings_path)
    new_settings, removed = unmerge_hooks(existing_settings, specs)
    any_hook_removed = any(removed.values())

    gitignore_target = gitignore_path(project_root)
    gitignore_hit_count = count_gitignore_entries(gitignore_target)
    would_remove_gitignore = gitignore_hit_count > 0

    print()
    print("=" * 70)
    print("  Claude Code 変更履歴トラッキング — プロジェクトローカル設定の取り消し")
    print("=" * 70)
    print()
    print("  プロジェクト        : " + str(project_root))
    print()
    print("  [1] settings.local.json  " + str(settings_path))
    for event_type in specs:
        print(f"      hooks.{event_type}: "
              + (f"{removed[event_type]}件のエントリを取り除きます" if removed[event_type] else "対象なし"))
    print()
    print("  [2] .gitignore  " + str(gitignore_target))
    print("      " + ("このツールが追記した行を取り除きます" if would_remove_gitignore else "対象なし"))
    print()
    print("  ディレクトリ（.claude/changelog/ の実データ）と中央レジストリへの登録は"
          "そのまま残します。")
    print()

    if print_only:
        print("  --print が指定されているため、実際の書き込みは行っていません。")
        print()
        return 0

    if any_hook_removed:
        _atomic_write_json(settings_path, new_settings)
    if would_remove_gitignore:
        remove_gitignore_entries(gitignore_target)

    print("  完了しました。")
    print()
    return 0


# ---------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="changelog_setup.py",
        description="Claude Code 変更履歴トラッキング — プロジェクトローカルの初期設定",
    )
    p.add_argument("--project-root", required=True, help="workspace の絶対パス")
    p.add_argument("--gitignore-mode", required=True, choices=("A", "B", "C"),
                    help="A: log/のみ無視（既定/推奨）  "
                         "B: 何もしない（生ログもコミットされる。Bashコマンドの先頭10行が"
                         "リポジトリに残るので機微情報に注意）  "
                         "C: .claude/changelog/ ごと無視")
    p.add_argument("--print", dest="print_only", action="store_true",
                    help="実際に書き込む内容を表示するだけ（dry-run。何も変更しない）")
    p.add_argument("--uninstall", action="store_true",
                    help="追加した hooks エントリと .gitignore への追記だけを取り除く")
    return p


def main() -> None:
    args = build_parser().parse_args()

    project_root = Path(args.project_root).expanduser()
    try:
        project_root = project_root.resolve(strict=False)
    except OSError as e:
        print(f"エラー: --project-root を解決できません（{e}）", file=sys.stderr)
        sys.exit(1)

    if not project_root.is_dir():
        print(f"エラー: --project-root がディレクトリとして見つかりません: {project_root}",
              file=sys.stderr)
        sys.exit(1)

    try:
        if args.uninstall:
            code = do_uninstall_setup(project_root, args.gitignore_mode, print_only=args.print_only)
        else:
            code = do_setup(project_root, args.gitignore_mode, print_only=args.print_only)
    except SetupError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"エラー: ファイル操作に失敗しました（{e}）", file=sys.stderr)
        sys.exit(1)

    sys.exit(code)


if __name__ == "__main__":
    main()
