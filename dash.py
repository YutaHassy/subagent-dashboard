#!/usr/bin/env python3
"""Subagent Dashboard — 統合エントリポイント

このファイル1つから、サーバー起動・状態更新・初期設定をすべて呼び出せる。

    dash serve [--open]                 画面のサーバーを起動する
    dash install                        初期設定（エージェント用の設定ファイルに追記）
    dash ext install                    VSCode 拡張機能として入れる

    dash start  --title "..."           ミッション開始
    dash add    --id SCOUT-A ...        サブエージェントを登録
    dash done   --id SCOUT-A ...        完了を記録
    dash finish --headline "..."        ミッション完了

    dash status / projects / demo / reset / remove / log

Windows では dash.cmd、macOS / Linux では ./dash から呼び出せる。
直接 `python dash.py serve` としても同じ。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Windows のコンソールでも多言語の字が化けないようにする（dashlib を読み込む前に済ませる）
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

SERVE = {"serve", "server", "up", "start-server"}
INSTALL = {"install", "setup"}
EXT = {"ext", "extension", "vscode"}
PACKAGE = {"package", "dist", "build-dist"}
HELP = {"-h", "--help", "help", ""}

from i18n import t  # noqa: E402


def _usage() -> str:
    """コマンド一覧。**呼ばれるたびに組む**（import 時に固めると、あとから
    言語を切り替えても前の言語のまま出てしまう）。"""
    return t("""
Subagent Dashboard

  Open the screen
    dash serve                 start the server (leave it running)
    dash serve --open          start it and open a browser too
    dash serve --port 4000     choose the port

  First-time setup
    dash install               write the operating rules into the agent's config file
    dash install --print       only show what would be written (changes nothing)

  Build a distribution package
    dash package               build the full package (ZIP + VSIX + setup guide)

  VSCode extension
    dash ext install           build the extension and install it into VSCode
    dash ext package           build the full distribution (.vsix + guide, to email)
    dash ext build             build only the .vsix (lands in dist/)
    dash ext status            check whether it is installed
    dash ext uninstall         remove the extension

  Update the state (normally the agent runs these automatically)
    dash start  --title "name of the work"
    dash add    --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "the task"
    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "result summary"
    dash finish --headline "overall summary"

  Inspect and misc
    dash status                show the contents of the current project
    dash projects              list the registered projects
    dash demo                  fill in dummy data for checking the display
    dash reset [--purge]       empty the current project (the tab stays)
    dash remove [--yes]        delete the current project's records (the tab goes)
    dash log --text "..."      append one line to the event log
    dash lang <en|ja|zh|ko>    choose the language of these messages

  For details on each command, run  dash <command> --help
""").strip()


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""

    if cmd in HELP:
        print(_usage())
        return

    if cmd in SERVE:
        sys.argv = ["dash serve", *argv[1:]]
        import server

        server.main()
        return

    if cmd in INSTALL:
        sys.argv = ["dash install", *argv[1:]]
        import install

        install.main()
        return

    if cmd in EXT:
        sys.argv = ["dash ext", *argv[1:]]
        import build_vsix

        build_vsix.main()
        return

    if cmd in PACKAGE:
        import package_dist

        package_dist.main()
        return

    # それ以外は状態更新CLIへそのまま渡す
    sys.argv = ["dash", *argv]
    import update_state

    update_state.main()


if __name__ == "__main__":
    main()
