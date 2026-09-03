# -*- coding: utf-8 -*-
"""サブエージェント自動登録の hook 書き込みの検査（開発用。配布物には入らない）。

    python check_autoreg.py

settings.local.json は**利用者のもの**で、こちらが勝手に触ってよい場所ではない。
ここで守りたいのは3つ。

1. **べき等であること。** 2回入れても2本のまま。増えると hook が二重に走り、
   同じ機体が2回記録される。
2. **系統を取り違えないこと。** 変更履歴用の hook と自動登録用の hook は
   同じ配列に並ぶ。取り消しで相手のぶんまで消したら、利用者は気づかないまま
   もう片方の機能を失う。
3. **他人の設定に触れないこと。** 利用者が自分で書いた hook は、名前が似ていても
   こちらのものではない。
"""
from __future__ import annotations

import copy
import io
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import autoreg_setup as ar      # noqa: E402
import changelog_setup as cs    # noqa: E402
import dashlib                  # noqa: E402
import install                  # noqa: E402

FAILED: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  OK   {label}")
    else:
        print(f"  NG   {label}\n         期待: {want!r}\n         実際: {got!r}")
        FAILED.append(label)


def commands(settings: dict, event_type: str) -> list:
    """そのイベント種別に並んでいる command を、書かれている順に返す。"""
    arr = (settings.get("hooks") or {}).get(event_type) or []
    out = []
    for e in arr:
        for h in (e.get("hooks") or []):
            out.append(h.get("command", ""))
    return out


def kinds(settings: dict, event_type: str) -> list:
    """並んでいるエントリの系統を、書かれている順に返す。"""
    out = []
    for cmd in commands(settings, event_type):
        if all(n in cmd for n in ar.AUTOREG_MARKER):
            out.append("自動登録")
        elif cs.HOOK_MARKER in cmd:
            out.append("変更履歴")
        else:
            out.append("よそ")
    return out


def main() -> int:
    py = "python"
    auto = ar.build_autoreg_specs(py, str(HERE / "update_state.py"))
    chg = cs.build_hook_specs(py, str(HERE / "changelog_cli.py"))

    print("[1] 空の設定に入れる")
    s1, added = cs.merge_hooks({}, auto, ar.AUTOREG_MARKER)
    check("2本とも追加される", added, {"PreToolUse": True, "PostToolUse": True})
    check("PreToolUse に自動登録が1件", kinds(s1, "PreToolUse"), ["自動登録"])
    check("PostToolUse に自動登録が1件", kinds(s1, "PostToolUse"), ["自動登録"])
    check("Stop には何も足さない", "Stop" in (s1.get("hooks") or {}), False)
    check("matcher は Agent と Task の両方",
          s1["hooks"]["PreToolUse"][0]["matcher"], "Agent|Task")
    check("PreToolUse は必ず 0 で終わる（起動を止めないため）",
          commands(s1, "PreToolUse")[0].endswith("; exit 0"), True)

    print()
    print("[2] もう一度入れても増えない")
    s2, added2 = cs.merge_hooks(s1, auto, ar.AUTOREG_MARKER)
    check("2本とも「追加していない」と答える",
          added2, {"PreToolUse": False, "PostToolUse": False})
    check("PreToolUse は1件のまま", kinds(s2, "PreToolUse"), ["自動登録"])
    check("PostToolUse は1件のまま", kinds(s2, "PostToolUse"), ["自動登録"])

    print()
    print("[3] 変更履歴の hook と並んでも、互いを自分のものと思わない")
    both, _ = cs.merge_hooks(s1, chg, cs.HOOK_MARKER)
    check("PreToolUse に2系統が並ぶ", kinds(both, "PreToolUse"), ["自動登録", "変更履歴"])
    check("PostToolUse に2系統が並ぶ", kinds(both, "PostToolUse"), ["自動登録", "変更履歴"])
    check("変更履歴の Stop も入る", kinds(both, "Stop"), ["変更履歴"])
    _, again_auto = cs.merge_hooks(both, auto, ar.AUTOREG_MARKER)
    check("並んでいても自動登録はべき等",
          again_auto, {"PreToolUse": False, "PostToolUse": False})
    _, again_chg = cs.merge_hooks(both, chg, cs.HOOK_MARKER)
    check("並んでいても変更履歴はべき等",
          again_chg, {"PreToolUse": False, "PostToolUse": False, "Stop": False})

    print()
    print("[4] 自動登録だけを取り消す")
    left, removed = cs.unmerge_hooks(both, auto, ar.AUTOREG_MARKER)
    check("2本とも取り除いたと答える", removed, {"PreToolUse": 1, "PostToolUse": 1})
    check("変更履歴の PreToolUse は残る", kinds(left, "PreToolUse"), ["変更履歴"])
    check("変更履歴の PostToolUse は残る", kinds(left, "PostToolUse"), ["変更履歴"])
    check("変更履歴の Stop はそのまま", kinds(left, "Stop"), ["変更履歴"])

    print()
    print("[5] 変更履歴だけを取り消す")
    left2, removed2 = cs.unmerge_hooks(both, chg, cs.HOOK_MARKER)
    check("3本とも取り除いたと答える",
          removed2, {"PreToolUse": 1, "PostToolUse": 1, "Stop": 1})
    check("自動登録の PreToolUse は残る", kinds(left2, "PreToolUse"), ["自動登録"])
    check("自動登録の PostToolUse は残る", kinds(left2, "PostToolUse"), ["自動登録"])
    check("空になった Stop はキーごと消える", "Stop" in (left2.get("hooks") or {}), False)

    print()
    print("[6] 利用者が自分で書いた hook には触れない")
    # 名前が似ているだけの他人の hook。update_state.py を呼んでいても、
    # hook サブコマンドでなければこちらのものではない。
    mine = {"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command",
                                       "command": "python 'x/update_state.py' status"}]},
        {"matcher": "", "hooks": [{"type": "command", "command": "echo hook"}]},
    ]}}
    got, added6 = cs.merge_hooks(mine, auto, ar.AUTOREG_MARKER)
    check("他人の hook は自分のものと見なさない（ちゃんと追加される）",
          added6["PreToolUse"], True)
    check("他人の2件はそのまま残る",
          kinds(got, "PreToolUse"), ["よそ", "よそ", "自動登録"])
    back, removed6 = cs.unmerge_hooks(got, auto, ar.AUTOREG_MARKER)
    check("取り消しで消えるのは自分の1件だけ", removed6["PreToolUse"], 1)
    check("他人の2件は取り消し後も残る", kinds(back, "PreToolUse"), ["よそ", "よそ"])

    print()
    print("[7] 壊れた設定は黙って上書きしない")
    for broken, why in (({"hooks": "文字列"}, "hooks がオブジェクトでない"),
                        ({"hooks": {"PreToolUse": "配列でない"}}, "配列でない")):
        try:
            cs.merge_hooks(broken, auto, ar.AUTOREG_MARKER)
            check(why + " → 止まる", "通ってしまった", "SetupError")
        except cs.SetupError:
            check(why + " → 止まる", "SetupError", "SetupError")

    print()
    print("[8] 元の設定を書き換えない（deepcopy して返す）")
    src = copy.deepcopy(both)
    cs.merge_hooks(src, auto, ar.AUTOREG_MARKER)
    cs.unmerge_hooks(src, auto, ar.AUTOREG_MARKER)
    check("呼んでも引数はそのまま", src, both)

    print()
    print("[9] 書き込みと取り消しを実ファイルで通す")
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="autoreg-check-"))
    try:
        root = tmp / "proj"
        root.mkdir()
        path = cs.settings_local_path(root)
        check("最初は設定ファイルが無い", path.exists(), False)
        ar.do_setup(root, print_only=True)
        check("--print では作らない", path.exists(), False)
        ar.do_setup(root, print_only=False)
        check("書き込むと作られる", path.exists(), True)
        import json
        got = json.loads(io.open(path, encoding="utf-8").read())
        check("自動登録が2本入っている",
              [kinds(got, "PreToolUse"), kinds(got, "PostToolUse")],
              [["自動登録"], ["自動登録"]])
        ar.do_setup(root, print_only=False)
        got = json.loads(io.open(path, encoding="utf-8").read())
        check("2回入れても2本のまま",
              [kinds(got, "PreToolUse"), kinds(got, "PostToolUse")],
              [["自動登録"], ["自動登録"]])
        ar.do_uninstall(root, print_only=False)
        got = json.loads(io.open(path, encoding="utf-8").read())
        check("取り消すと hooks ごと消える", "hooks" in got, False)

        print()
        print("[10] 運用ルール（そのプロジェクトの CLAUDE.md）")
        # **これが無いと、自動登録は「重複を増やす機能」になる。** 機械ぜんぶに
        # 配ってある運用ルールは「起動したら add を打て」と言い続けるので、
        # hook が書いた記録の隣に手打ちの記録がもう1件並ぶ。
        root2 = tmp / "proj2"
        root2.mkdir()
        md = ar.instruction_path(root2)
        mine = "# 利用者が書いたもの\n\nこれは消えてはいけない。\n"
        md.write_text(mine, encoding="utf-8")

        ar.do_setup(root2, print_only=True)
        check("--print では書き換えない",
              md.read_text(encoding="utf-8"), mine)

        ar.do_setup(root2, print_only=False)
        after = md.read_text(encoding="utf-8")
        check("利用者の記述はそのまま残る", after.startswith(mine), True)
        check("add を打たないことが書かれている", "add" in after, True)
        begin, end = install.block_markers(install.AUTOREG_BLOCK_ID)
        check("目印が1組だけ入る",
              [after.count(begin), after.count(end)], [1, 1])
        check("ダッシュボード本体の目印とは重ならない",
              dashlib.BLOCK_BEGIN in after, False)

        ar.do_setup(root2, print_only=False)
        check("2回入れても目印は1組のまま",
              [md.read_text(encoding="utf-8").count(begin),
               md.read_text(encoding="utf-8").count(end)], [1, 1])

        ar.do_uninstall(root2, print_only=False)
        check("取り消すと利用者の記述だけが残る",
              md.read_text(encoding="utf-8").rstrip("\n"), mine.rstrip("\n"))

        # 目印が片方しか無い＝人が手で編集して壊れている。そのまま書き足すと、
        # 次の取り消しで利用者の記述まで巻き込んで消える。書かずに止める。
        root3 = tmp / "proj3"
        root3.mkdir()
        ar.instruction_path(root3).write_text(
            "# 手で壊した\n" + begin + "\n本文だけ残っている\n", encoding="utf-8")
        try:
            ar.do_setup(root3, print_only=True)
            check("目印が壊れていたら書かずに止まる", "通ってしまった", "SetupError")
        except cs.SetupError:
            check("目印が壊れていたら書かずに止まる", "SetupError", "SetupError")
        check("止まったので settings も書いていない",
              cs.settings_local_path(root3).exists(), False)
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILED:
        print(f"NG {len(FAILED)} 件: " + " / ".join(FAILED))
        return 1
    print("すべて通りました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
