"""autofinish（セッション終了時の自動締め）の検査。

    python check_autofinish.py

締め忘れは、この道具で**あとから直せない唯一の壊れ方**である。打ち忘れても何も
壊れないので気づけず、画面は「稼働中」と言い続け、次に start した時点でその記録は
「未完」として履歴へ押し出される——そこから完了にする手段は無い。だから
autofinish は SessionEnd hook に配線して使う。

ここで守りたいのは3つ。

1. 稼働中でなければ**何も言わない**こと。hook はセッションが終わるたびに走るので、
   ミッションを開いていないときに出力が混ざってはいけない。
2. **そのディレクトリの稼働中を全部**締めること。--project で記録先を分けて並行させた
   側を取りこぼすと、締め忘れを無くす仕組みが、いちばん締め忘れやすい形を落とす。
3. **別のフォルダのミッションを巻き込まない**こと。勝手によその記録を閉じるのは、
   締め忘れより重い事故になる。

実際に update_state.py を子プロセスとして呼ぶ（hook が呼ぶのと同じ形）。記録の置き場は
一時ディレクトリへ逃がすので、このマシンに残っている記録には触らない。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLI = str(HERE / "update_state.py")
NL = chr(10)

FAILED: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print("  OK   " + label)
    else:
        print("  NG   " + label + NL
              + "         期待: " + repr(want) + NL
              + "         実際: " + repr(got))
        FAILED.append(label)


def run(args: list, cwd: Path, home: Path, session: str = "sess-main") -> tuple:
    """hook が呼ぶのと同じ形で update_state.py を叩く。

    session は Claude Code のセッションID（CLAUDE_CODE_SESSION_ID）。ミッションの
    持ち主を決めるのはこれなので、検査でも本物と同じ渡し方をする。空文字を渡すと
    「素性が分からない環境」を再現できる。
    """
    env = dict(os.environ)
    env["AGENT_DASHBOARD_DATA_HOME"] = str(home)
    env["AGENT_DASHBOARD_LANG"] = "ja"
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("AGENT_DASHBOARD_PROJECT", None)
    if session:
        env["CLAUDE_CODE_SESSION_ID"] = session
    else:
        env.pop("CLAUDE_CODE_SESSION_ID", None)
    p = subprocess.run([sys.executable, "-X", "utf8", CLI] + list(args),
                       cwd=str(cwd), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def current_slug(home: Path) -> str:
    return (home / "missions" / ".current").read_text(encoding="utf-8").strip()


def state_of(home: Path, slug: str) -> dict:
    return json.loads((home / "missions" / slug / "state.json").read_text(encoding="utf-8"))


def phase_of(home: Path, slug: str) -> str:
    f = home / "missions" / slug / "state.json"
    if not f.is_file():
        return "(記録なし)"
    return state_of(home, slug)["mission"]["phase"]


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="dash-autofinish-"))
    try:
        home = tmp / "home"
        work = tmp / "work"
        other = tmp / "other"
        work.mkdir(parents=True)
        other.mkdir(parents=True)

        print("[1] 稼働中のミッションが無ければ、何も言わない")
        rc, out = run(["autofinish"], work, home)
        check("終了コードは 0", rc, 0)
        check("出力は空", out.strip(), "")

        print()
        print("[2] このディレクトリの稼働中を締める")
        run(["start", "--title", "本体", "--model", "claude-opus-5"], work, home)
        slug = current_slug(home)
        check("開始直後は稼働中", phase_of(home, slug), "running")
        rc, out = run(["autofinish"], work, home)
        check("終了コードは 0", rc, 0)
        check("完了になった", phase_of(home, slug), "done")
        check("見出しは自動締めのものが入る",
              state_of(home, slug)["mission"]["summary"]["headline"],
              "セッション終了により自動で締めました")

        print()
        print("[3] --project で分けた側も、同じディレクトリなら締まる")
        run(["start", "--title", "本体2", "--model", "claude-opus-5"], work, home)
        run(["start", "--project", "waki", "--title", "分けた側",
             "--model", "claude-opus-5"], work, home)
        check("2本とも稼働中",
              [phase_of(home, slug), phase_of(home, "waki")], ["running", "running"])
        run(["autofinish"], work, home)
        check("2本とも締まった",
              [phase_of(home, slug), phase_of(home, "waki")], ["done", "done"])

        print()
        print("[4] 別のフォルダのミッションは巻き込まない")
        run(["start", "--title", "よそのミッション", "--model", "claude-opus-5"], other, home)
        other_slug = current_slug(home)
        run(["start", "--title", "こちらのミッション", "--model", "claude-opus-5"], work, home)
        run(["autofinish"], work, home)
        check("こちらは締まった", phase_of(home, slug), "done")
        check("よそは稼働中のまま", phase_of(home, other_slug), "running")

        print()
        print("[5] --project を明示したら、その1本だけを見る")
        run(["start", "--title", "本体3", "--model", "claude-opus-5"], work, home)
        run(["start", "--project", "waki", "--title", "分けた側2",
             "--model", "claude-opus-5"], work, home)
        run(["autofinish", "--project", "waki"], work, home)
        check("指定した側は締まった", phase_of(home, "waki"), "done")
        check("指定しなかった側は稼働中のまま", phase_of(home, slug), "running")

        print()
        print("[6] 記録に無い機体が居なければ、余計な鍵を増やさない")
        run(["autofinish"], work, home)
        check("締まった", phase_of(home, slug), "done")
        check("orphans は書かれていない", "orphans" in state_of(home, slug), False)

        print()
        print("[7] 手で打った finish の見出しは、自動締めに上書きされない")
        run(["start", "--title", "本体4", "--model", "claude-opus-5"], work, home)
        run(["finish", "--headline", "自分で書いた一行"], work, home)
        check("自分の見出しが残る",
              state_of(home, slug)["mission"]["summary"]["headline"], "自分で書いた一行")
        rc, out = run(["autofinish"], work, home)
        check("締め終わったあとは、もう何も言わない", out.strip(), "")

        print()
        print("[8] 他のセッションが開いたミッションは締めない")
        # 同じフォルダで Claude Code を2つ開くのは普通にある。片方が終わっただけで、
        # まだ作業しているもう片方のミッションが完了になっていた（実測で踏んだ事故）。
        run(["start", "--title", "甲のミッション", "--model", "claude-opus-5"],
            work, home, session="sess-kou")
        check("開いた側の持ち主が記録される",
              state_of(home, slug)["mission"].get("sessionId"), "sess-kou")
        rc, out = run(["autofinish"], work, home, session="sess-otsu")
        check("よその終了では締まらない", phase_of(home, slug), "running")
        check("そのとき何も言わない", out.strip(), "")
        run(["autofinish"], work, home, session="sess-kou")
        check("持ち主の終了なら締まる", phase_of(home, slug), "done")

        print()
        print("[9] 素性が分からない環境では、今までどおり締める")
        # ここで「分からないから締めない」にすると、この仕組みが黙って死ぬ。
        # 閉じすぎは次の start でやり直せるが、閉じ忘れは直せない。
        run(["start", "--title", "素性不明", "--model", "claude-opus-5"],
            work, home, session="")
        check("持ち主は記録されない",
              "sessionId" in state_of(home, slug)["mission"], False)
        run(["autofinish"], work, home, session="")
        check("それでも締まる", phase_of(home, slug), "done")

        run(["start", "--title", "素性不明2", "--model", "claude-opus-5"],
            work, home, session="")
        run(["autofinish"], work, home, session="sess-dare")
        check("持ち主の無い記録は、誰の終了でも締まる", phase_of(home, slug), "done")

        # 後片付け。よそのミッションを稼働中のまま残さない。
        run(["autofinish"], other, home)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILED:
        print("NG " + str(len(FAILED)) + " 件: " + " / ".join(FAILED))
        return 1
    print("すべて通りました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
