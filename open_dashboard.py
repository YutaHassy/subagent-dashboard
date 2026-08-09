#!/usr/bin/env python3
"""グローバルダッシュボードランチャースクリプト

任意のプロジェクトワークスペースから呼び出してダッシュボードを起動する。
サーバーをバックグラウンドで起動し、ヘルスチェック後にブラウザで開く。

使用方法:
  python open_dashboard.py
  または別のプロジェクトから:
  python ~/.claude/agent-dashboard/open_dashboard.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 文言の翻訳。**このファイルは単体で呼ばれる**（キーバインドの旧形式が直接指している）
# ので、隣に i18n.py が無い置かれ方もありうる。無ければ原文（英語）をそのまま返す
# 素通しに落として、ランチャそのものは動かし続ける。
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from i18n import t
except Exception:  # pragma: no cover - 単体で持ち出されたときの保険
    def t(text: str) -> str:
        return text


# ================================================================ カラー定数


class Colors:
    """ANSI カラーコード（Windows 10+ でサポート）"""
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    GRAY = "\033[90m"
    RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """テキストを指定色でカラー化（Windows だけ無効化の場合対応）"""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass
    return f"{color}{text}{Colors.RESET}"


# ================================================================ パス解決


def resolve_dashboard_root() -> Path:
    """ダッシュボードのルートディレクトリを決定する

    優先順位:
    1. このスクリプト自身の置き場所
    2. 環境変数 AGENT_DASHBOARD_HOME
    3. ~/.claude/agent-dashboard

    Returns:
        ダッシュボード根ディレクトリのパス
    """
    # このスクリプトが置いてあるディレクトリ
    script_dir = Path(__file__).resolve().parent
    if (script_dir / "dash.py").exists():
        return script_dir

    # 環境変数
    env_home = os.environ.get("AGENT_DASHBOARD_HOME", "").strip()
    if env_home:
        dash_home = Path(env_home).expanduser().resolve()
        if (dash_home / "dash.py").exists():
            return dash_home

    # デフォルト
    default_home = Path.home() / ".claude" / "agent-dashboard"
    return default_home


# ================================================================ サーバー管理


def start_server(dashboard_root: Path) -> bool:
    """バックグラウンドでダッシュボードサーバーを起動する

    Args:
        dashboard_root: ダッシュボードのルートディレクトリ

    Returns:
        起動成功したかどうか
    """
    try:
        dash_py = dashboard_root / "dash.py"
        if not dash_py.exists():
            print(colorize(t("  ✗ dash.py not found: {path}").format(path=dash_py),
                           Colors.YELLOW))
            return False

        # バックグラウンド起動
        if sys.platform == "win32":
            # Windows: CREATE_NO_WINDOW を使ってコンソールウィンドウを出さない
            subprocess.Popen(
                [sys.executable, str(dash_py), "serve"],
                cwd=str(dashboard_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
        else:
            # macOS / Linux
            subprocess.Popen(
                [sys.executable, str(dash_py), "serve"],
                cwd=str(dashboard_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # プロセスグループを分離
            )

        return True
    except Exception as e:
        print(colorize(t("  ✗ Failed to start the server: {err}").format(err=e),
                       Colors.YELLOW))
        return False


# ================================================================ ヘルスチェック


def wait_for_server(max_wait_sec: float = 10.0) -> bool:
    """サーバーが起動するのを待つ（最大 max_wait_sec 秒）

    Args:
        max_wait_sec: 最大待機秒数

    Returns:
        サーバーが応答するようになったかどうか
    """
    url = "http://127.0.0.1:3939/"
    start = time.time()
    interval = 0.5  # 500ms ごとにチェック

    while time.time() - start < max_wait_sec:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass
        time.sleep(interval)

    return False


# ================================================================ ブラウザを開く


def open_in_vscode_simple_browser(url: str) -> bool:
    """VSCode の Simple Browser コマンドで URL を開く

    Args:
        url: 開く URL

    Returns:
        成功したかどうか
    """
    try:
        subprocess.run(
            ["code", "--command", "simpleBrowser.openURL", "--args", url],
            timeout=3,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def open_in_default_browser(url: str) -> bool:
    """OS のデフォルトブラウザで URL を開く

    Args:
        url: 開く URL

    Returns:
        成功したかどうか
    """
    try:
        if sys.platform == "win32":
            os.startfile(url)
        elif sys.platform == "darwin":
            subprocess.run(["open", url], timeout=3, check=False)
        else:  # Linux
            subprocess.run(["xdg-open", url], timeout=3, check=False)
        return True
    except Exception:
        return False


def open_dashboard(url: str = "http://127.0.0.1:3939") -> bool:
    """ダッシュボード URL をブラウザで開く（VSCode -> 標準ブラウザの順）

    Args:
        url: 開く URL

    Returns:
        成功したかどうか
    """
    # VSCode Simple Browser を試す
    if open_in_vscode_simple_browser(url):
        return True

    # フォールバック: OS のデフォルトブラウザ
    if open_in_default_browser(url):
        return True

    return False


# ================================================================ メイン処理


def main() -> int:
    """メイン処理

    Returns:
        終了コード (0: 成功, 1: 失敗)
    """
    # === バナー ===
    print()
    print(colorize(t("  Starting the dashboard"), Colors.CYAN))
    print(colorize("  ================================================", Colors.CYAN))
    print()

    # === ダッシュボードのルート決定 ===
    dashboard_root = resolve_dashboard_root()
    print(colorize(t("  Dashboard: {path}").format(path=dashboard_root), Colors.GRAY))

    if not dashboard_root.exists():
        print(colorize(t("  ✗ The dashboard directory was not found"), Colors.YELLOW))
        return 1

    # === サーバー起動 ===
    print(colorize(t("  Starting the server..."), Colors.GRAY))
    if not start_server(dashboard_root):
        return 1

    # === ヘルスチェック ===
    print(colorize(t("  Checking the connection..."), Colors.GRAY))
    if wait_for_server(max_wait_sec=10.0):
        print(colorize(t("  ✓ The server is up"), Colors.GREEN))
    else:
        print(
            colorize(
                t("  ⚠ Timed out checking the connection. Please try again."),
                Colors.YELLOW,
            )
        )

    print()

    # === ブラウザを開く ===
    url = "http://127.0.0.1:3939"
    print(colorize(t("  Opening the browser..."), Colors.GRAY))

    if open_dashboard(url):
        time.sleep(0.5)
        print(colorize(t("  ✓ Ready"), Colors.GREEN))
    else:
        print(
            colorize(
                t("  ⚠ Could not open a browser. Please open {url} yourself.")
                .format(url=url),
                Colors.YELLOW,
            )
        )

    print()
    print(colorize(f"  🤖 {url}", Colors.CYAN))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
