#!/usr/bin/env python3
"""Subagent Dashboard — 診断スクリプト

配布先のユーザーが問題を診断するためのツールです。

使い方:
    python diagnose.py

何をチェックするか:
    1. Python のバージョン
    2. ダッシュボードのファイル構成
    3. CLAUDE.md の設定状態
    4. ミッション保存先の書き込み権限
    5. カレントディレクトリから判定される対象プロジェクト
    6. 既存のミッション記録

問題が見つかれば、解決策を提示します。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib
from i18n import t

dashlib.use_utf8_stdio()

#: 枠の内側の桁数。罫線の本数と必ず揃えること。
BOX_WIDTH = 66


def box(text: str) -> None:
    """1行を罫線で囲んで出す。

    **幅は文字数ではなく表示幅で合わせる。** 全角は2桁を占めるので、
    `str.ljust` で詰めると日本語・中国語・韓国語で右の罫線がずれる
    （実際に4言語化したときこれで崩れた）。長すぎる訳は clip が畳む。
    """
    rule = "─" * (BOX_WIDTH + 2)
    print("┌" + rule + "┐")
    print("│ " + dashlib.pad(dashlib.clip(text, BOX_WIDTH), BOX_WIDTH) + " │")
    print("└" + rule + "┘")


# ANSI カラーコード(Windows でも動く環境が増えてきたので使う)
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def colored(text: str, color: str) -> str:
    """Windows でも無理なく動くように、色付けは控えめに。"""
    if sys.platform == "win32" and not os.environ.get("WT_SESSION"):
        return text  # Windows Terminal 以外では色を付けない
    return f"{color}{text}{RESET}"


def check_python_version() -> tuple[bool, str]:
    """Python 3.9 以降が必要。"""
    version = sys.version_info
    if version >= (3, 9):
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    return False, t("Python {v} (3.9 or newer is required)").format(
        v="%d.%d.%d" % (version.major, version.minor, version.micro))


def check_file_structure() -> tuple[bool, str]:
    """必要なファイルが揃っているか。"""
    required = [
        HERE / "dashlib.py",
        HERE / "server.py",
        HERE / "update_state.py",
        HERE / "install.py",
        HERE / "public" / "index.html",
        HERE / "public" / "manual.html",
    ]
    missing = [f for f in required if not f.is_file()]
    if not missing:
        return True, t("all required files are present ({n})").format(n=len(required))
    return False, t("missing: {list}").format(
        list=", ".join(f.name for f in missing))


def check_claude_md() -> tuple[bool, str]:
    """CLAUDE.md に設定が書き込まれているか。"""
    target = dashlib.claude_config_dir() / "CLAUDE.md"
    if not target.is_file():
        return False, t("CLAUDE.md does not exist ({path})").format(path=target)

    try:
        text = target.read_text(encoding="utf-8")
    except OSError as e:
        return False, t("read error: {err}").format(err=e)

    begin = "<!-- agent-dashboard:begin -->"
    end = "<!-- agent-dashboard:end -->"

    if begin not in text or end not in text:
        return False, t("the settings are not written (no marker found)")

    # パスが正しいか確認
    us = str(HERE / "update_state.py")
    if us not in text and us.replace("\\", "/") not in text:
        return (
            False,
            t("the path does not match. Please run install.py (expected: {path})")
            .format(path=us),
        )

    return True, t("configured ({path})").format(path=target)


def check_claude_md_version() -> tuple[bool, str]:
    """CLAUDE.md の運用ルールが本体と同じ版か。

    本体と運用ルールは別々に古くなる。本体は拡張の更新や上書きコピーで新しくなるが、
    CLAUDE.md は install.py を実行し直すまで古いまま残る（初期設定は一度成功すると
    自動では二度と走らない）。ここで版を突き合わせておかないと、増えた運用ルールが
    誰にも届いていないことに、事故が起きるまで気づけない。
    """
    if not dashlib.claude_block_installed():
        return False, t("not configured (fix the item above first)")

    current = dashlib.tool_version()
    if not current:
        return False, t("cannot read the tool's VERSION")

    installed = dashlib.claude_block_version()
    if installed == current:
        return True, t("up to date (version {v})").format(v=current)

    where = (t("no version recorded (0.4.1 or earlier)") if installed is None
             else t("version {v}").format(v=installed))
    return (
        False,
        t("out of date (CLAUDE.md: {where} / tool: version {current}). "
          "Please run python {path}").format(
              where=where, current=current, path=HERE / "install.py"),
    )


def check_missions_dir() -> tuple[bool, str]:
    """ミッション保存先に書き込めるか。"""
    try:
        dashlib.MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        probe = dashlib.MISSIONS_DIR / ".write-probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return True, t("writable ({path})").format(path=dashlib.MISSIONS_DIR)
    except OSError as e:
        return False, t("not writable: {err}").format(err=e)


def check_current_project() -> tuple[bool, str]:
    """カレントディレクトリから判定されるプロジェクトを表示。"""
    try:
        project = dashlib.resolve_project()
        return True, f"{project['name']} ({project['slug']})"
    except ValueError as e:
        return False, str(e)


def check_existing_missions() -> tuple[bool, str]:
    """既存のミッション記録を列挙。"""
    slugs = dashlib.list_slugs()
    if not slugs:
        return True, t("none (fresh install)")
    return True, t("{n} project records present").format(n=len(slugs))


def main() -> None:
    print()
    print("=" * 70)
    print(t("  🔍 Subagent Dashboard \u2014 diagnostics"))
    print("=" * 70)
    print()

    # (鍵, 表示ラベル, 関数)。**鍵は訳さない。** 下の解決策の出し分けはこの鍵で行う。
    # 以前はラベルの部分一致（`if "Python" in label`）で分けていたが、それだと
    # ラベルを訳した瞬間に日本語以外では1件も一致せず、助言が丸ごと消える。
    checks = [
        ("python",   t("Python version"),           check_python_version),
        ("files",    t("File layout"),              check_file_structure),
        ("claude",   t("CLAUDE.md settings"),       check_claude_md),
        ("version",  t("Operating-rules version"),  check_claude_md_version),
        ("missions", t("Mission storage"),          check_missions_dir),
        ("project",  t("Project for this folder"),  check_current_project),
        ("records",  t("Existing mission records"), check_existing_missions),
    ]

    results: list[tuple[str, str, bool, str]] = []
    all_ok = True

    box(t("Running system checks..."))
    print()

    for key, label, check_func in checks:
        ok, msg = check_func()
        results.append((key, label, ok, msg))
        if not ok:
            all_ok = False

    # 結果を表示。ラベルの幅は表示幅で揃える（訳語に全角が混ざると len では合わない）
    for key, label, ok, msg in results:
        status = colored("✓", GREEN) if ok else colored("✗", RED)
        print(f"  {status}  {dashlib.pad(label, 28)} {msg}")

    print()
    print("─" * 70)
    print()

    # まとめ
    if all_ok:
        print(colored(t("  ✅ Everything looks good."), GREEN))
        print()
        print(t("  The dashboard is set up correctly."))
        print()
        print(t("  You can start the server with:"))
        print()
        if sys.platform == "win32":
            print(f'    dash.cmd serve --open')
        else:
            print(f'    ./dash serve --open')
        print()
        print(t("  Or, to use the VSCode extension:"))
        print()
        if sys.platform == "win32":
            print(f'    dash.cmd ext install')
        else:
            print(f'    ./dash ext install')
        print()
        print("=" * 70)
        print()
    else:
        print(colored(t("  ❌ Problems were found"), RED))
        print()
        box(t("How to fix"))
        print()

        # 個別の解決策
        problem_count = 0
        installer = f'            python "{HERE / "install.py"}"'
        if sys.platform != "win32":
            installer = installer.replace("python ", "python3 ", 1)
        for key, label, ok, msg in results:
            if ok:
                continue
            problem_count += 1
            print(f"  [{problem_count}] {label}")
            if key == "python":
                print(t("      Cause: the Python version is too old"))
                print(t("      Fix:   install Python 3.9 or newer"))
                print("            https://www.python.org/downloads/")
            elif key == "files":
                print(t("      Cause: required files are missing"))
                print(t("      Fix:   get a complete package from wherever you "
                        "obtained this"))
            elif key == "claude":
                print(t("      Cause: Claude has not been configured yet"))
                print(t("      Fix:   run the following command"))
                print(installer)
            elif key == "version":
                print(t("      Cause: the tool was updated, but the operating rules "
                        "in CLAUDE.md are still old"))
                print(t("             (updating the tool does not rewrite CLAUDE.md)"))
                print(t("      Fix:   run the following command"))
                print(installer)
                print(t("            only the marked block is replaced"))
            elif key == "missions":
                print(t("      Cause: the mission storage folder is not writable"))
                print(t("      Fix:   check the write permissions on the folder"))
                print(f"            {dashlib.MISSIONS_DIR}")
            elif key == "project":
                print(t("      Cause: the project directory could not be determined"))
                print(t("      Fix:   run this from the root of your project"))
            print()

        print("─" * 70)
        print()
        # 読み手の言語の版を指す。英語版だけを指すと、CLI は韓国語なのに
        # 案内先だけ英語という状態になる。
        #
        # 案内するのは**実在するものだけ**。ここは「困ったときに開く先」なので、
        # 無いファイルを並べると、利用者は自分の配置が壊れていると思う
        # （実際 0.4.3 まで、存在しない『配布後のセットアップ手順.md』を案内していた）。
        print(t("  If the problem persists, check these files:"))
        for doc in (dashlib.doc_path("README"), HERE / "セットアップ手順.html"):
            if doc.exists():
                print(f"    - {doc}")
        print()
        print("=" * 70)
        print()

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
