#!/usr/bin/env python3
"""Subagent Dashboard — サブエージェント自動登録のプロジェクトローカル初期設定

    python autoreg_setup.py --project-root <workspace> [--print] [--uninstall]

<project-root>/.claude/settings.local.json へ hook を2本足す。

    PreToolUse  (matcher: Agent|Task) → update_state.py hook   起動を記録する
    PostToolUse (matcher: Agent|Task) → update_state.py hook   完了と実測値を記録する

これが入ると、サブエージェントを起動したときの `update_state.py add` と、
完了通知を受け取ったときの `done` を**人が打たなくてよくなる**。記録には
Agent 呼び出しのID（toolUseId）が入り、画面はそのIDで実機と対応づけるので、
名前や時刻の一致に頼らずに済む——「記録に無い稼働中の機体」が原理的に出なくなる。

**変更履歴トラッキング（changelog_setup.py）とは別の機能である。** 書き込み先の
ファイルは同じだが、目印（AUTOREG_MARKER）で系統を分けてあるので、片方を入れても
もう片方は動かないし、片方を取り消してももう片方は残る。

**入れた直後は効かない。** Claude Code は起動時に hook を読むので、書き込んだあと
開き直すまで1件も記録されない。何も起きないだけでエラーも出ないため、
この案内を省くと「入れたのに動かない」を誰も原因まで追えない。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import changelog_lib as cl        # noqa: E402  （コマンド文字列の組み立てだけ借りる）
import changelog_setup as cs      # noqa: E402  （settings.local.json の読み書きを借りる）
import install                    # noqa: E402  （python の判定・運用ルールの組み立て）


#: 自動登録の hook を見分ける目印。**両方**を command に含むエントリだけが対象。
#: 1語だけで見ると、利用者自身が update_state.py を呼ぶ hook を書いていたときに
#: それを自分のものと取り違えて、取り消しで他人の設定を消してしまう。
AUTOREG_MARKER = ("update_state.py", " hook")

#: サブエージェントを起動するツールの名前。呼び名は Claude Code の版で違うことが
#: あるので両方を拾う（受け側の update_state.HOOK_SPAWN_TOOLS と同じ並び）。
#: 余計に呼ばれても、受け側が tool_name を見て何もせずに 0 で終わる。
AUTOREG_MATCHER = "Agent|Task"

#: hook イベント種別。起動（Pre）と完了（Post）の2本だけ。Stop は要らない。
AUTOREG_EVENT_TYPES = ("PreToolUse", "PostToolUse")


def build_autoreg_specs(py: str, cli_path: str) -> dict:
    """イベント種別ごとに、追加すべき1エントリ（matcher + hooks）を返す。

    `; exit 0` は**両方に付ける**。PreToolUse の非0終了は「そのツール呼び出しを
    拒否する」の意味なので、python が起動できないだけで**サブエージェントの起動が
    すべて止まる**（ツールを移動した・PATH から python が消えた、で起きる）。
    記録が取れないのは困るが、仕事が止まるほうがずっと悪い。
    """
    cmd = cl.sh_cli_command(py, cli_path, "hook") + cs.HOOK_TAIL_NEVER_FAIL
    return {
        et: {"matcher": AUTOREG_MATCHER,
             "hooks": [{"type": "command", "command": cmd}]}
        for et in AUTOREG_EVENT_TYPES
    }


def _specs() -> dict:
    # 引用は sh_cli_command に任せるので、ここでは生のパスのまま渡す
    # （二重に引用すると引用符がパスの一部になる）。
    return build_autoreg_specs(install.detect_python_command(),
                              str(HERE / "update_state.py"))


#: 運用ルールを書き込む先。**そのプロジェクトの** CLAUDE.md。
#: 機械ぜんぶに配る運用ルール（install.py が書く ~/.claude/CLAUDE.md 等）とは別で、
#: 自動登録はプロジェクトごとに入れるものだから、こちらもプロジェクトごとに置く。
INSTRUCTION_FILE = "CLAUDE.md"


def instruction_path(project_root: Path) -> Path:
    return project_root / INSTRUCTION_FILE


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as e:
        raise cs.SetupError(f"{path} を読めません（{e}）") from e


def _atomic_write_text(path: Path, text: str) -> None:
    """書きかけを読ませない。一時ファイルに書いてから差し替える。"""
    tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as e:
        raise cs.SetupError(f"{path} へ書き込めません（{e}）") from e
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass


def _plan_instructions(project_root: Path) -> tuple[Path, str, str, str]:
    """CLAUDE.md をどう変えるかを決める。まだ書かない。

    戻り値: (書き込み先, 変更後の中身, 符牒, 変更前の中身)
    符牒は install.apply_block と同じ created / appended / updated / unchanged。
    """
    path = instruction_path(project_root)
    before = _read_text(path)
    block = install.build_autoreg_block(install.detect_python_command())
    try:
        after, what, _dupes = install.apply_block(before, block,
                                                  install.AUTOREG_BLOCK_ID)
    except install.BrokenMarkerError as e:
        # 片方しかマーカーが無い＝人が手で編集して壊れている。このまま書くと、
        # 次の取り消しで利用者が自分で書いた記述まで消える。書かずに止める。
        raise cs.SetupError(f"{path} の目印が壊れています（{e}）") from e
    if after == before:
        what = "unchanged"
    return path, after, what, before


_WHAT_JA = {
    "created": "新しく作ります",
    "appended": "末尾に書き足します",
    "updated": "既にある記述を今の版に差し替えます",
    "unchanged": "既に最新です（変更なし）",
}


def _restart_notice() -> None:
    print("  ★ Claude Code を開き直すまで効きません。")
    print("     hook は起動時に読み込まれるので、いま開いているセッションでは")
    print("     1件も記録されません。**エラーは出ません**（黙って何も起きません）。")


def do_setup(project_root: Path, *, print_only: bool) -> int:
    specs = _specs()
    settings_path = cs.settings_local_path(project_root)
    existing = cs.read_settings_local(settings_path)
    merged, added = cs.merge_hooks(existing, specs, AUTOREG_MARKER)

    print()
    print("=" * 70)
    print("  Subagent Dashboard — サブエージェント自動登録の初期設定")
    print("=" * 70)
    print()
    print("  プロジェクト        : " + str(project_root))
    print()
    print("  settings.local.json : " + str(settings_path))
    for event_type in specs:
        if added[event_type]:
            spec = specs[event_type]
            print(f"      hooks.{event_type}: 追加します"
                  f"  matcher={spec['matcher']!r}"
                  f"  command={spec['hooks'][0]['command']!r}")
        else:
            print(f"      hooks.{event_type}: 既に設定済み（変更なし）")
    print()

    md_path, md_after, what, _before = _plan_instructions(project_root)
    print("  運用ルール          : " + str(md_path))
    print("      " + _WHAT_JA[what])
    print("      「このプロジェクトでは add と done を打たない」を書きます。"
          "**これが無いと、")
    print("      運用ルールは今までどおり add を打てと言い続けるので、"
          "1体が2枚のカードになります。**")
    print()
    print("  start と finish は今までどおり手で打ってください"
          "（ミッションの区切りは人が決めるものなので）。")
    print()

    if print_only:
        print("  --print が指定されているため、実際の書き込みは行っていません。")
        print()
        return 0

    if any(added.values()):
        cs._atomic_write_json(settings_path, merged)
    if what != "unchanged":
        _atomic_write_text(md_path, md_after)

    print("  完了しました。")
    print()
    _restart_notice()
    print()
    return 0


def do_uninstall(project_root: Path, *, print_only: bool) -> int:
    """自動登録の hook だけを取り除く。

    変更履歴トラッキングの hook（changelog_cli.py を呼ぶもの）には触れない。
    目印が別なので、同じ配列に両方が入っていても片方だけが消える。
    """
    specs = _specs()
    settings_path = cs.settings_local_path(project_root)
    existing = cs.read_settings_local(settings_path)
    new_settings, removed = cs.unmerge_hooks(existing, specs, AUTOREG_MARKER)

    print()
    print("=" * 70)
    print("  Subagent Dashboard — サブエージェント自動登録の取り消し")
    print("=" * 70)
    print()
    print("  プロジェクト        : " + str(project_root))
    print()
    print("  settings.local.json : " + str(settings_path))
    for event_type in specs:
        print(f"      hooks.{event_type}: "
              + (f"{removed[event_type]}件のエントリを取り除きます"
                 if removed[event_type] else "対象なし"))
    print()

    md_path = instruction_path(project_root)
    md_before = _read_text(md_path)
    md_after, md_hit = install.remove_block(md_before, install.AUTOREG_BLOCK_ID)
    print("  運用ルール          : " + str(md_path))
    print("      " + ("このツールが書いた記述を取り除きます" if md_hit else "対象なし"))
    if md_hit and not md_after.strip():
        print("      （中身が空になりますが、ファイルは残します。"
              "消してよいかはこちらでは決められません）")
    print()
    print("  記録済みのミッション（missions/）には触れません。")
    print()

    if print_only:
        print("  --print が指定されているため、実際の書き込みは行っていません。")
        print()
        return 0

    if any(removed.values()):
        cs._atomic_write_json(settings_path, new_settings)
    if md_hit:
        _atomic_write_text(md_path, md_after)

    print("  完了しました。")
    print()
    _restart_notice()
    print()
    return 0


# ---------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="autoreg_setup.py",
        description="Subagent Dashboard — サブエージェント自動登録の初期設定",
    )
    p.add_argument("--project-root", required=True, help="workspace の絶対パス")
    p.add_argument("--print", dest="print_only", action="store_true",
                   help="書き込む内容を表示するだけ（dry-run。何も変更しない）")
    p.add_argument("--uninstall", action="store_true",
                   help="追加した hooks エントリだけを取り除く")
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
        print(f"エラー: --project-root がディレクトリではありません: {project_root}",
              file=sys.stderr)
        sys.exit(1)

    try:
        if args.uninstall:
            code = do_uninstall(project_root, print_only=args.print_only)
        else:
            code = do_setup(project_root, print_only=args.print_only)
    except cs.SetupError as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(code)


if __name__ == "__main__":
    main()
