#!/usr/bin/env python3
"""Subagent Dashboard — 初回セットアップの橋渡し（開発用）

server.py と update_state.py が起動時に1回だけ呼ぶ。

    try:
        import auto_setup
        auto_setup.check_and_setup(silent=False)   # server.py（人が見ている）
        auto_setup.check_and_setup(silent=True)    # update_state.py（Claude が回す）
    except Exception:
        pass

やることは「CLAUDE.md にまだ運用ルールが書かれていない」を見つけて、人が居るときだけ
知らせる（承諾があれば install.py を呼ぶ）ことだけ。**それ以上のことをしてはいけない。**
呼び手は両方とも try/except で囲っていて、**このファイルが無くても動く**ように書いてある
（`.vsix` には同梱しない ＝ 配布先には存在しない）。無くても動くものに、無いと困ることを
足すと、開発ディレクトリでだけ通って配布先で通らない状態ができる。

**判定そのもの（設定済みか・版が古いか）は dashlib に置いてある。** dashlib は必ず配られる
ので、配布先でも同じ判断ができる。ここに判定を書き写してはいけない ── 0.4.2 で実際に
これをやり、「開発ディレクトリでは動くのに、更新した人の手元では何も起きない」状態を
作った（extension/CHANGELOG.md 0.4.2 の「判定は dashlib.py に置いた」の項）。

版のずれ（運用ルールが本体より古い）もここでは扱わない。server.py の起動時と
update_state.py の start が dashlib.stale_block_notice() を直接見ている。**配布先にも要る
知らせなので、無くなりうるこのファイルには置けない。**

外部ライブラリは使いません（Python 標準ライブラリのみ）。
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib  # noqa: E402
from i18n import t  # noqa: E402

# 出力の文字化け対策（use_utf8_stdio）は呼び手が済ませてから import してくる。
# ここで重ねて呼ばない（このファイルは「無くてもよい層」なので、環境をいじらない）。

INSTALLER = HERE / "install.py"


# ---------------------------------------------------------------- 相手が居るかの判定


def _is_interactive() -> bool:
    """人が端末の前に居て、問いに答えられるか。

    拡張はサーバーを stdio=pipe で起動し、Claude は CLI をパイプで回す。どちらも
    答えられる人が居ないので、訊いてはいけない（訊けば答えを待って止まり、
    「サーバーが起動しない」に化ける）。
    """
    try:
        return bool(sys.stdin and sys.stdin.isatty() and sys.stdout.isatty())
    except (AttributeError, ValueError, OSError):
        return False


# ---------------------------------------------------------------- 案内


def _how_to() -> str:
    return f"{dashlib.PY_CMD} {INSTALLER}"


def _run_installer() -> bool:
    """install.py を同じプロセスで呼ぶ。**書き込む中身はあちらの持ち物。**

    import をここまで遅らせているのは、install.py が欠けた配置でも「案内するだけ」は
    成り立たせるため。冒頭で import すると、その場合に呼び手側の except へ落ちて、
    知らせるべきことまで消える。
    """
    try:
        import install
    except ImportError:
        print(t("      install.py not found. Please unpack the distribution again."))
        return False
    return install.do_install(print_only=False) == 0


def _offer_setup() -> bool:
    """未設定であることを知らせ、人が居れば承諾を取って設定する。"""
    print()
    print(t("  ⚠️  First-time setup is not done yet "
            "(CLAUDE.md has no operating rules)."))
    print(t("      The screen still opens, but Claude does not know how to use"))
    print(t("      Subagent Dashboard, so starting subagents will show nothing."))
    print()

    if not _is_interactive():
        print(t("      To set it up, run: {how}").format(how=_how_to()))
        print()
        return False

    try:
        answer = input(t("      Set it up now? [Y/n]: ")).strip().lower()
    except (EOFError, OSError, KeyboardInterrupt):
        # Windows では標準入力が NUL に繋がれていても isatty() が真になることがあり、
        # ここまで来てしまう（update_state.py の remove と同じ罠）。その場合 input() は
        # 即 EOF を返すので、案内だけ出して先へ進む。
        print()
        print(t("      To set it up, run: {how}").format(how=_how_to()))
        print()
        return False

    if answer not in ("", "y", "yes"):
        print(t("      Understood. To set it up later, run {how}.").format(how=_how_to()))
        print()
        return False

    return _run_installer()


# ---------------------------------------------------------------- 入口


def check_and_setup(silent: bool = False) -> bool:
    """初期設定が済んでいれば True。済んでいなければ案内して False を返す。

    silent=True では**何も出力しない**。呼び手（update_state.py）は Claude が1コマンド
    ごとに回す CLI で、そこに毎回の注意書きが混ざると、肝心の start / done の応答が
    埋もれる。未設定のまま update_state が動くのは、そもそも CLAUDE.md 以外の道筋で
    呼ばれた場合だけなので、ここで急いで知らせる相手が居ない。

    silent=False（server.py）のときだけ人向けに知らせる。サーバーの起動は人が画面を
    見に来た瞬間なので、ここで気づけると手当てまで一続きになる。

    **例外を外に出さない。** 呼び手の本業はサーバーの起動と状態の更新であって初期設定
    ではない。ここで転んで本業を巻き添えにするくらいなら、黙って False を返すほうがよい
    （呼び手側の try/except も同じ考えで置かれている。二重にしているのは、あちらが
    「このファイルが無い場合」の受けも兼ねているため）。
    """
    try:
        if dashlib.claude_block_installed():
            return True
        if silent:
            return False
        return _offer_setup()
    except Exception:
        return False


if __name__ == "__main__":
    dashlib.use_utf8_stdio()
    ok = check_and_setup(silent=False)
    if ok:
        print(t("First-time setup is already done ({path}).")
              .format(path=dashlib.claude_config_dir() / "CLAUDE.md"))
    sys.exit(0 if ok else 1)
