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
import re
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


def history_runs(home: Path, slug: str) -> list:
    """history/ に並んでいる runId の一覧。退避が起きた（増えた）かどうかの検査に使う。"""
    hist = home / "missions" / slug / "history"
    if not hist.is_dir():
        return []
    return sorted(p.name for p in hist.iterdir())


def latest_history_state(home: Path, slug: str) -> dict:
    """history/ に一番最後に増えた runId の state.json を読む。押し出された記録の検査に使う。"""
    hist = home / "missions" / slug / "history"
    run_id = sorted(p.name for p in hist.iterdir())[-1]
    return json.loads((hist / run_id / "state.json").read_text(encoding="utf-8"))


def run_hook(payload: dict, cwd: Path, home: Path, session: str = "sess-main") -> tuple:
    """hook サブコマンドを、Claude Code の PreToolUse/PostToolUse と同じ形
    （標準入力に JSON を渡す）で叩く。戻り値は run() と同じ (終了コード, 出力)。
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
    p = subprocess.run([sys.executable, "-X", "utf8", CLI, "hook"],
                       cwd=str(cwd), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       input=json.dumps(payload, ensure_ascii=False))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def extract_project_hint(out: str) -> str:
    """拒否メッセージが案内する --project の名前を抜き出す。suggest_project() が
    同じセッションからは同じ名前を返すことの検査に使う。見つからなければ空文字。
    """
    m = re.search(r'--project\s+"([^"]+)"', out)
    return m.group(1) if m else ""


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

        print()
        print("[10] start は、稼働中で他セッションの記録を押し出さない")
        # 直前の [9] で締まっている記録を、甲（sess-kou）が仕切り直す。
        run(["start", "--title", "甲のミッション2", "--model", "claude-opus-5"],
            work, home, session="sess-kou")
        run(["add", "--id", "SCOUT-A", "--name", "偵察A", "--model", "claude-sonnet-5",
             "--mission", "甲の調査A"], work, home, session="sess-kou")
        hist_before10 = history_runs(home, slug)
        rc, out = run(["start", "--title", "乙のミッション", "--model", "claude-opus-5"],
                      work, home, session="sess-otsu")
        check("終了コードは 1", rc, 1)
        check("history/ は増えていない（押し出されていない）",
              history_runs(home, slug), hist_before10)
        check("state.json は甲の記録のまま",
              state_of(home, slug)["mission"]["title"], "甲のミッション2")
        check("甲の機体もそのまま残る",
              sorted(a["id"] for a in state_of(home, slug)["agents"]),
              sorted(["COMMAND", "SCOUT-A"]))

        print()
        print("[11] [10] に --force を付ければ、いままでどおり押し出す")
        rc, out = run(["start", "--title", "乙のミッション", "--model", "claude-opus-5",
                      "--force"], work, home, session="sess-otsu")
        check("終了コードは 0", rc, 0)
        check("history/ が1件増える", len(history_runs(home, slug)), len(hist_before10) + 1)
        pushed = latest_history_state(home, slug)["mission"]
        check("押し出された記録の phase は running のまま", pushed["phase"], "running")
        check("finishedAt は書かれていない（実測でない値を書かない約束）",
              pushed.get("finishedAt"), None)
        note = pushed.get("interruptedBy") or {}
        check("interruptedBy.by は start", note.get("by"), "start")
        check("interruptedBy.title は押し出した側（乙）のミッション名",
              note.get("title"), "乙のミッション")
        check("interruptedBy.sameSession は false（別セッションによる押し出し）",
              note.get("sameSession"), False)
        check("interruptedBy.at に押し出された時刻が入る", bool(note.get("at")), True)

        print()
        print("[12] 完了済みの記録の退避には interruptedBy を書かない")
        run(["finish", "--headline", "乙、完了"], work, home, session="sess-otsu")
        hist_before12 = history_runs(home, slug)
        run(["start", "--title", "次のミッション", "--model", "claude-opus-5"],
            work, home, session="sess-kou")
        check("history/ が1件増える", len(history_runs(home, slug)), len(hist_before12) + 1)
        done_pushed = latest_history_state(home, slug)["mission"]
        check("phase は done のまま退避される", done_pushed["phase"], "done")
        check("interruptedBy キーは無い（_stamp_interrupted の早期リターン経路）",
              "interruptedBy" in done_pushed, False)

        print()
        print("[13] add / done / finish / log は、他セッションが start した記録には書けない")
        # いまの記録の持ち主は甲（sess-kou、[12] で start した）。乙（sess-otsu）が
        # 気づかず書き込もうとする。
        before13 = (home / "missions" / slug / "state.json").read_bytes()
        rc, out = run(["add", "--id", "PLAN-A", "--name", "追加機体", "--model", "claude-opus-5",
                      "--mission", "気づかず打った add"], work, home, session="sess-otsu")
        check("add は終了コード 1", rc, 1)
        rc, out = run(["done", "--id", "NOPE-ID", "--headline", "結果"],
                      work, home, session="sess-otsu")
        check("done は終了コード 1", rc, 1)
        check('done の案内は持ち主違いが先。find_agent の「居ません」ではない'
              "（NOPE-ID への言及が無い）", "NOPE-ID" in out, False)
        rc, out = run(["finish", "--headline", "結果"], work, home, session="sess-otsu")
        check("finish は終了コード 1", rc, 1)
        rc, out = run(["log", "--who", "乙", "--text", "こっそり書いたログ"],
                      work, home, session="sess-otsu")
        check("log は終了コード 1", rc, 1)
        after13 = (home / "missions" / slug / "state.json").read_bytes()
        check("拒否された4件で state.json は1バイトも変わっていない", after13, before13)

        print()
        print("[14] [13] に --force を付ければ書ける")
        rc, out = run(["add", "--id", "PLAN-A", "--name", "追加機体", "--model", "claude-opus-5",
                      "--mission", "力ずくの add", "--force"], work, home, session="sess-otsu")
        check("add --force は終了コード 0", rc, 0)
        rc, out = run(["done", "--id", "PLAN-A", "--headline", "力ずくの結果", "--force"],
                      work, home, session="sess-otsu")
        check("done --force は終了コード 0", rc, 0)
        rc, out = run(["log", "--who", "乙", "--text", "力ずくで書いたログ", "--force"],
                      work, home, session="sess-otsu")
        check("log --force は終了コード 0", rc, 0)
        rc, out = run(["finish", "--headline", "力ずくで締めた", "--force"],
                      work, home, session="sess-otsu")
        check("finish --force は終了コード 0", rc, 0)
        check("state.json に反映されている（力ずくで書いたログが残る）",
              any("力ずくで書いたログ" in (e.get("text") or "")
                  for e in state_of(home, slug)["log"]),
              True)
        check("phase は done になっている", phase_of(home, slug), "done")

        print()
        print("[15] 同じセッションからは、他セッションが start した記録にも今までどおり書ける")
        # サブエージェントが親の CLAUDE_CODE_SESSION_ID をそのまま受け継ぐ経路の代理検査。
        # ここが通らないと、司令塔が start したミッションへサブエージェントが1体も
        # 書き込めなくなる——締め忘れよりも重い、道具そのものが壊れる事故になる。
        run(["start", "--title", "乙の追撃", "--model", "claude-opus-5"],
            work, home, session="sess-otsu")
        rc, out = run(["add", "--id", "SCOUT-X", "--name", "偵察X", "--model", "claude-sonnet-5",
                      "--mission", "同じセッションからの add"], work, home, session="sess-otsu")
        check("--force 無しで終了コード 0", rc, 0)
        check("機体が記録される",
              "SCOUT-X" in [a["id"] for a in state_of(home, slug)["agents"]], True)

        print()
        print("[16] sessionId の有無の組み合わせ4通りで、すべて通る（§6の表そのもの）")
        run(["start", "--title", "組み合わせA", "--model", "claude-opus-5"],
            work, home, session="")
        rc, out = run(["add", "--id", "COMBO-A", "--name", "組A", "--model", "claude-sonnet-5",
                      "--mission", "記録に無し・呼び手に有り"], work, home, session="sess-x1")
        check("記録に sessionId 無し・呼び手に有り → 通る", rc, 0)
        check("機体が記録される（後方互換）",
              "COMBO-A" in [a["id"] for a in state_of(home, slug)["agents"]], True)

        run(["start", "--title", "組み合わせB", "--model", "claude-opus-5"],
            work, home, session="sess-x2")
        rc, out = run(["add", "--id", "COMBO-B", "--name", "組B", "--model", "claude-sonnet-5",
                      "--mission", "記録に有り・呼び手に無し"], work, home, session="")
        check("記録に sessionId 有り・呼び手に無し → 通る", rc, 0)
        check("機体が記録される（後方互換）",
              "COMBO-B" in [a["id"] for a in state_of(home, slug)["agents"]], True)

        run(["start", "--title", "組み合わせC", "--model", "claude-opus-5"],
            work, home, session="")
        rc, out = run(["add", "--id", "COMBO-C", "--name", "組C", "--model", "claude-sonnet-5",
                      "--mission", "両方とも無し"], work, home, session="")
        check("両方とも sessionId 無し → 通る（後方互換）", rc, 0)
        check("機体が記録される（後方互換）",
              "COMBO-C" in [a["id"] for a in state_of(home, slug)["agents"]], True)

        run(["start", "--title", "組み合わせD", "--model", "claude-opus-5"],
            work, home, session="sess-y")
        rc, out = run(["add", "--id", "COMBO-D", "--name", "組D", "--model", "claude-sonnet-5",
                      "--mission", "両方とも同じ値"], work, home, session="sess-y")
        check("両方とも同じ sessionId → 通る", rc, 0)
        check("機体が記録される",
              "COMBO-D" in [a["id"] for a in state_of(home, slug)["agents"]], True)

        print()
        print("[17] suggest_project() は同じセッションからは同じ名前を返す")
        rc, out1 = run(["start", "--title", "衝突1", "--model", "claude-opus-5"],
                       work, home, session="sess-z")
        check("1回目も拒否", rc, 1)
        rc, out2 = run(["start", "--title", "衝突2", "--model", "claude-opus-5"],
                       work, home, session="sess-z")
        check("2回目も拒否", rc, 1)
        name1 = extract_project_hint(out1)
        name2 = extract_project_hint(out2)
        check("--project の案内が出る", bool(name1), True)
        check("同じセッションなら2回とも同じ名前", name1, name2)

        print()
        print("[18] hook は、2本稼働中でも自分のセッションのものへ絞り込める（提案B）")
        run(["finish", "--headline", "片付け"], work, home, session="sess-y")
        run(["start", "--title", "甲hook", "--model", "claude-opus-5"],
            work, home, session="sess-kou-h")
        kou_hook_slug = current_slug(home)
        run(["start", "--project", "otsu-hook", "--title", "乙hook",
             "--model", "claude-opus-5"], work, home, session="sess-otsu-h")
        before_kou_hook = len(state_of(home, kou_hook_slug)["agents"])
        before_otsu_hook = len(state_of(home, "otsu-hook")["agents"])
        hook_payload = {
            "tool_name": "Task",
            "tool_use_id": "toolu_hooktest18",
            "hook_event_name": "PreToolUse",
            "cwd": str(work),
            "tool_input": {"description": "偵察H", "prompt": "hook 絞り込みの検査"},
        }
        run_hook(hook_payload, work, home, session="sess-kou-h")
        check("甲の記録にだけ機体が増える",
              len(state_of(home, kou_hook_slug)["agents"]), before_kou_hook + 1)
        check("乙の記録は変わらない(絞り込めなければ両方とも増えない。[6]相当が2本ある場合の検査)",
              len(state_of(home, "otsu-hook")["agents"]), before_otsu_hook)

        print()
        print("[19] demo は、稼働中で他セッションの記録を拒否する（cmd_start と同じ規則）")
        # [18] で稼働中のまま残った記録（甲hook、持ち主 sess-kou-h）を、
        # 正しい持ち主で締めてから検査を始める。
        run(["finish", "--headline", "demo検査の前に片付け"], work, home, session="sess-kou-h")
        run(["start", "--title", "甲のdemo保護", "--model", "claude-opus-5"],
            work, home, session="sess-kou-demo")
        run(["add", "--id", "SCOUT-D", "--name", "偵察D", "--model", "claude-sonnet-5",
             "--mission", "甲のdemo前の調査"], work, home, session="sess-kou-demo")
        hist_before19 = history_runs(home, slug)
        rc, out = run(["demo"], work, home, session="sess-otsu-demo")
        check("終了コードは 1", rc, 1)
        check("history/ は増えていない（退避すらされていない）",
              history_runs(home, slug), hist_before19)
        check("state.json は甲の記録のまま（ダミーで上書きされていない）",
              state_of(home, slug)["mission"]["title"], "甲のdemo保護")
        check("甲の機体もそのまま残る",
              sorted(a["id"] for a in state_of(home, slug)["agents"]),
              sorted(["COMMAND", "SCOUT-D"]))

        print()
        print("[20] [19] に --force を付ければ通り、上書き前の記録は history/ へ退避される")
        rc, out = run(["demo", "--force"], work, home, session="sess-otsu-demo")
        check("終了コードは 0", rc, 0)
        check("history/ が1件増える", len(history_runs(home, slug)), len(hist_before19) + 1)
        pushed19 = latest_history_state(home, slug)["mission"]
        check("押し出された記録の phase は running のまま", pushed19["phase"], "running")
        check("finishedAt は書かれていない（実測でない値を書かない約束）",
              pushed19.get("finishedAt"), None)
        check("退避された記録の機体も無事に残っている（history 側）",
              sorted(a["id"] for a in latest_history_state(home, slug)["agents"]),
              sorted(["COMMAND", "SCOUT-D"]))
        note19 = pushed19.get("interruptedBy") or {}
        check("interruptedBy.by は demo", note19.get("by"), "demo")
        check("interruptedBy.sameSession は false（別セッションによる上書き）",
              note19.get("sameSession"), False)
        check("demo のダミーデータに置き換わっている",
              state_of(home, slug)["mission"]["title"], "表示テスト（ダミーデータ）")

        print()
        print("[21] 同じセッションの demo でも、既存の記録は history/ へ退避される（消えない）")
        run(["start", "--title", "甲の本番ミッション", "--model", "claude-opus-5"],
            work, home, session="sess-kou-demo2")
        run(["add", "--id", "SCOUT-E", "--name", "偵察E", "--model", "claude-sonnet-5",
             "--mission", "甲の本番調査"], work, home, session="sess-kou-demo2")
        hist_before21 = history_runs(home, slug)
        rc, out = run(["demo"], work, home, session="sess-kou-demo2")
        check("終了コードは 0（自分のセッションなので --force は要らない）", rc, 0)
        check("history/ が1件増える（同一セッションでも退避される）",
              len(history_runs(home, slug)), len(hist_before21) + 1)
        pushed21 = latest_history_state(home, slug)["mission"]
        check("退避された記録の phase は running のまま", pushed21["phase"], "running")
        check("退避された記録のタイトルは demo 前の本番ミッションのまま",
              pushed21["title"], "甲の本番ミッション")
        check("退避された記録の機体も無事に残っている（history 側）",
              sorted(a["id"] for a in latest_history_state(home, slug)["agents"]),
              sorted(["COMMAND", "SCOUT-E"]))
        note21 = pushed21.get("interruptedBy") or {}
        check("interruptedBy.by は demo", note21.get("by"), "demo")
        check("interruptedBy.sameSession は true（同一セッションによる上書き）",
              note21.get("sameSession"), True)
        check("demo のダミーデータに置き換わっている",
              state_of(home, slug)["mission"]["title"], "表示テスト（ダミーデータ）")

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
