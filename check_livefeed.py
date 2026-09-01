"""livefeed（稼働中の実測読み取り）の検査。

    python check_livefeed.py

合成した記録だけで判定するので、このマシンに何が残っているかに左右されない。
実機のデータで確かめた事実（トークンの式・ツール回数・所要秒）を、そのまま
検査の答えとして固定してある。

ここで守りたいのは2つ。
1. 実測値が正しく読めること。読み違えた数字を出すくらいなら何も出さないほうがよい。
2. **別の機体の数字をカードに出さないこと。** 対応づけに少しでも曖昧さがあるときは
   結ばない、を機械で確かめる。画面のちらつきと違って、間違った対応は人が気づけない。
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FAILED: list[str] = []


def check(label: str, got, want) -> None:
    if got == want:
        print(f"  OK   {label}")
    else:
        print(f"  NG   {label}\n         期待: {want!r}\n         実際: {got!r}")
        FAILED.append(label)


def iso(ts: float) -> str:
    """Claude Code が書くのと同じ末尾 Z 形式。"""
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def local_iso(ts: float) -> str:
    """state.json が書くのと同じ、地方時のオフセット付き形式。"""
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------- 合成データ

def write_agent(subagents: Path, agent_id: str, *, start: float, cwd: str,
                session: str, model: str = "sonnet", description: str = "",
                tools=(), tokens=(0, 0, 0), tail_open: bool = False,
                broken_line: bool = False, workflow_run: str = "",
                prompt: str = "任務") -> None:
    """1体ぶんの jsonl と meta.json を書く。

    tools は [(ツール名, 引数dict, 何秒後), ...]。tail_open=True なら最後の呼び出しの
    結果をわざと書かない（＝ツールを実行中の状態）。
    """
    d = subagents / "workflows" / workflow_run if workflow_run else subagents
    d.mkdir(parents=True, exist_ok=True)
    meta = {"agentType": "workflow-subagent" if workflow_run else "Explore", "spawnDepth": 1}
    if model:
        meta["model"] = model
    if description:
        meta["description"] = description
    (d / f"agent-{agent_id}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    rows = []
    base = {"agentId": agent_id, "isSidechain": True, "sessionId": session, "cwd": cwd}
    rows.append(dict(base, type="user", timestamp=iso(start),
                     message={"role": "user", "content": prompt}))
    tin, tcc, tcr = tokens
    for i, (name, inp, offset) in enumerate(tools):
        at = start + offset
        rows.append(dict(base, type="assistant", timestamp=iso(at), message={
            "role": "assistant",
            "content": [{"type": "tool_use", "id": f"tu{i}", "name": name, "input": inp}],
            "usage": {"input_tokens": tin, "cache_creation_input_tokens": tcc,
                      "cache_read_input_tokens": tcr, "output_tokens": 7},
        }))
        last = (i == len(tools) - 1)
        if not (last and tail_open):
            rows.append(dict(base, type="user", timestamp=iso(at + 1), message={
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": f"tu{i}", "content": "ok"}],
            }))
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    if broken_line:
        lines.insert(1, "{これは JSON ではない")
    (d / f"agent-{agent_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mission(missions: Path, slug: str, *, project_path: str, started: float,
                  agents: list) -> None:
    (missions / slug).mkdir(parents=True, exist_ok=True)
    (missions / slug / "agents").mkdir(exist_ok=True)
    state = {
        "version": 2,
        "project": {"slug": slug, "name": slug, "path": project_path},
        "updatedAt": local_iso(started),
        "mission": {"phase": "running", "title": "検査", "startedAt": local_iso(started),
                    "finishedAt": None, "summary": None},
        "agents": agents,
        "log": [],
    }
    (missions / slug / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def reset(livefeed, *, sticky: bool = True) -> None:
    """シナリオの切れ目で、モジュールが持っている状態を初期化する。

    台帳（_ledger）は「同じリクエストのあいだ、同じ実機を2つのチームが取らない」ための
    もので、実運用では 1.5 秒で失効する。検査は1秒に満たないあいだに何本ものミッションを
    続けて組み立てるので、明示的に戻さないと前のシナリオの割当を引きずる。
    """
    livefeed._enum_cache["at"] = 0.0
    livefeed._ledger["at"] = 0.0
    livefeed._ledger["taken"] = {}
    if sticky:
        livefeed._sticky.clear()


def rec(agent_id: str, name: str, model: str, started: float, status: str = "running") -> dict:
    return {"id": agent_id, "name": name, "parentId": "COMMAND", "generation": 1,
            "model": model, "mission": "任務", "status": status,
            "startedAt": local_iso(started), "finishedAt": None, "result": None}


# ---------------------------------------------------------------- 検査

def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="livefeed-check-"))
    try:
        data_home = tmp / "data"
        live_root = tmp / "projects"
        work = tmp / "work"
        work.mkdir(parents=True)
        (data_home / "missions").mkdir(parents=True)

        os.environ["AGENT_DASHBOARD_DATA_HOME"] = str(data_home)
        os.environ["AGENT_DASHBOARD_LIVE_ROOT"] = str(live_root)
        os.environ["AGENT_DASHBOARD_LIVE_ENUM_TTL"] = "1"

        import dashlib
        import livefeed

        project_path = str(work.resolve())
        slug = dashlib.slug_for_path(work.resolve())
        session = "11111111-2222-3333-4444-555555555555"
        subagents = live_root / slug / session / "subagents"

        now = time.time()
        started = now - 600

        print("\n[1] 実測値の読み取り（トークンは最後の assistant 行のコンテキスト長）")
        write_agent(subagents, "aaa1", start=started + 10, cwd=project_path, session=session,
                    model="sonnet", description="調査A",
                    tools=[("Bash", {"description": "一覧を見る"}, 0),
                           ("Read", {"file_path": "/x/y.py"}, 30),
                           ("Grep", {"pattern": "def foo"}, 60)],
                    tokens=(2, 1000, 50000))
        reset(livefeed)
        entry = [e for e in livefeed.enumerate_agents() if e["agentId"] == "aaa1"][0]
        m = livefeed.measure(livefeed.describe(entry), now)
        check("ツール回数は tool_use ブロック数", m["toolCalls"], 3)
        check("トークンは in+cache_creation+cache_read", m["tokens"], 51002)
        check("所要秒は最初と最後の行の差", m["elapsedSec"], 61)
        check("いま何をしているかはツール名", m["tool"], "Grep")
        check("その1行は引数の実物", m["toolLabel"], "def foo")

        print("\n[2] 名前が description と一致すれば結ぶ")
        reset(livefeed)
        write_mission(data_home / "missions", "t1", project_path=project_path,
                      started=started, agents=[rec("A", "調査A", "claude-sonnet-5", started + 10)])
        st = dashlib.build_state("t1")
        a = st["agents"][0]
        check("live が載る", bool(a["live"]), True)
        check("載ったのは正しい機体", (a["live"] or {}).get("agentId"), "aaa1")
        check("孤児はいない", st["sources"]["liveOrphans"], [])

        print("\n[3] モデルが違えば結ばない")
        reset(livefeed)
        write_mission(data_home / "missions", "t2", project_path=project_path,
                      started=started, agents=[rec("A", "調査A", "claude-opus-5", started + 10)])
        st = dashlib.build_state("t2")
        check("live は載らない", st["agents"][0]["live"], None)
        check("実機は孤児として出る", [o["agentId"] for o in st["sources"]["liveOrphans"]], ["aaa1"])

        print("\n[4] 同じ名前の候補が2体なら、どちらにも結ばない")
        write_agent(subagents, "aaa2", start=started + 12, cwd=project_path, session=session,
                    model="sonnet", description="調査A",
                    tools=[("Bash", {"description": "別の作業"}, 0)], tokens=(2, 10, 20))
        reset(livefeed)
        write_mission(data_home / "missions", "t3", project_path=project_path,
                      started=started, agents=[rec("A", "調査A", "claude-sonnet-5", started + 10)])
        st = dashlib.build_state("t3")
        check("曖昧なので結ばない", st["agents"][0]["live"], None)
        check("2体とも孤児", sorted(o["agentId"] for o in st["sources"]["liveOrphans"]),
              ["aaa1", "aaa2"])

        print("\n[5] Workflow 経由（description が無い）でも、候補が1体なら結ぶ")
        session2 = "99999999-2222-3333-4444-555555555555"
        sub2 = live_root / slug / session2 / "subagents"
        write_agent(sub2, "wf01", start=started + 20, cwd=project_path, session=session2,
                    model="opus", description="", workflow_run="wf_test",
                    tools=[("Bash", {"description": "設計を書く"}, 0)], tokens=(1, 5, 99))
        reset(livefeed)
        write_mission(data_home / "missions", "t4", project_path=project_path, started=started,
                      agents=[rec("D", "設計班", "claude-opus-5", started + 20)])
        st = dashlib.build_state("t4")
        check("一意なら結ぶ", (st["agents"][0]["live"] or {}).get("agentId"), "wf01")
        check("Workflow 経由だと分かる", (st["agents"][0]["live"] or {}).get("workflow"), True)

        print("\n[6] 候補も記録も2体で手がかりが無いときは、どちらも結ばない")
        write_agent(sub2, "wf02", start=started + 21, cwd=project_path, session=session2,
                    model="opus", description="", workflow_run="wf_test",
                    tools=[("Bash", {"description": "別の設計"}, 0)], tokens=(1, 5, 77))
        reset(livefeed)
        write_mission(data_home / "missions", "t5", project_path=project_path, started=started,
                      agents=[rec("D1", "設計班A", "claude-opus-5", started + 20),
                              rec("D2", "設計班B", "claude-opus-5", started + 21)])
        st = dashlib.build_state("t5")
        check("どちらも結ばない", [a["live"] for a in st["agents"]], [None, None])
        # このプロジェクトには他のシナリオで作った機体も残っているので、
        # 「全部で何体」ではなく「この2体が孤児側にいること」を見る。
        check("2体とも孤児",
              sorted(o["agentId"] for o in st["sources"]["liveOrphans"]
                     if o["agentId"].startswith("wf")), ["wf01", "wf02"])

        print("\n[7] 前回の対応を引き継ぐ（候補が増えても入れ替わらない）")
        reset(livefeed)
        write_mission(data_home / "missions", "t6", project_path=project_path, started=started,
                      agents=[rec("D", "設計班", "claude-opus-5", started + 20)])
        # まず wf01 だけが候補になる状況を作る（wf02 を一時的にどける）
        moved = sub2 / "workflows" / "wf_test" / "agent-wf02.jsonl"
        holder = tmp / "agent-wf02.jsonl"
        moved.rename(holder)
        reset(livefeed)
        st = dashlib.build_state("t6")
        first = (st["agents"][0]["live"] or {}).get("agentId")
        check("最初は wf01 に結ぶ", first, "wf01")
        holder.rename(moved)          # 候補が増える
        reset(livefeed, sticky=False)   # 前回の対応は残したまま、候補だけ増やす
        st = dashlib.build_state("t6")
        check("候補が増えても対応は変わらない", (st["agents"][0]["live"] or {}).get("agentId"), first)

        print("\n[8] ツールを実行中は沈黙と見なさない")
        session3 = "77777777-2222-3333-4444-555555555555"
        sub3 = live_root / slug / session3 / "subagents"
        write_agent(sub3, "busy1", start=now - 3000, cwd=project_path, session=session3,
                    model="haiku", description="長い仕事",
                    tools=[("Bash", {"description": "テストを回す"}, 0)],
                    tokens=(1, 1, 1), tail_open=True)
        write_agent(sub3, "idle1", start=now - 3000, cwd=project_path, session=session3,
                    model="haiku", description="止まった仕事",
                    tools=[("Bash", {"description": "何かした"}, 0)], tokens=(1, 1, 1))
        reset(livefeed)
        busy = livefeed.measure(livefeed.describe(
            [e for e in livefeed.enumerate_agents() if e["agentId"] == "busy1"][0]), now)
        idle = livefeed.measure(livefeed.describe(
            [e for e in livefeed.enumerate_agents() if e["agentId"] == "idle1"][0]), now)
        check("結果待ちのあいだは active", busy["state"], "active")
        check("結果待ちだと分かる", busy["busy"], True)
        check("本当に止まっていれば stalled", idle["state"], "stalled")

        print("\n[9] プロジェクトの場所が分からなければ何も出さない")
        write_mission(data_home / "missions", "t7", project_path="", started=started,
                      agents=[rec("A", "調査A", "claude-sonnet-5", started + 10)])
        st = dashlib.build_state("t7")
        check("live を載せない", st["agents"][0]["live"], None)
        check("孤児も出さない", st["sources"]["liveOrphans"], [])

        print("\n[10] ミッション開始より前の機体は拾わない")
        write_agent(sub3, "old1", start=started - 7200, cwd=project_path, session=session3,
                    model="sonnet", description="前のミッションの残骸",
                    tools=[("Bash", {"description": "昔の作業"}, 0)], tokens=(1, 1, 1))
        reset(livefeed)
        write_mission(data_home / "missions", "t8", project_path=project_path, started=started,
                      agents=[rec("A", "前のミッションの残骸", "claude-sonnet-5", started + 10)])
        st = dashlib.build_state("t8")
        check("時間窓の外は結ばない", st["agents"][0]["live"], None)
        check("孤児にも出さない",
              [o["agentId"] for o in st["sources"]["liveOrphans"] if o["agentId"] == "old1"], [])

        print("\n[11] 壊れた行があっても止まらない")
        session4 = "88888888-2222-3333-4444-555555555555"
        sub4 = live_root / slug / session4 / "subagents"
        write_agent(sub4, "brk1", start=started + 30, cwd=project_path, session=session4,
                    model="sonnet", description="壊れた記録",
                    tools=[("Bash", {"description": "作業"}, 0)], tokens=(1, 2, 3),
                    broken_line=True)
        reset(livefeed)
        write_mission(data_home / "missions", "t9", project_path=project_path, started=started,
                      agents=[rec("A", "壊れた記録", "claude-sonnet-5", started + 30)])
        st = dashlib.build_state("t9")
        check("壊れた行は読み飛ばして結ぶ", (st["agents"][0]["live"] or {}).get("agentId"), "brk1")
        check("残りは正しく数える", (st["agents"][0]["live"] or {}).get("toolCalls"), 1)

        print("\n[12] 履歴は凍結（live を混ぜない）")
        run_dir = data_home / "missions" / "t1" / "history" / "20260901-090000"
        run_dir.mkdir(parents=True)
        shutil.copy(data_home / "missions" / "t1" / "state.json", run_dir / "state.json")
        (run_dir / "agents").mkdir()
        r = dashlib.read_run("t1", "20260901-090000")
        check("履歴の live は None", [a["live"] for a in r["agents"]], [None])
        check("履歴に孤児は出ない", r["sources"]["liveOrphans"], [])

        print("\n[13] 完了時の焼き付けは一意なときだけ")
        reset(livefeed)
        got = livefeed.measure_for(project_path, "調査A", "claude-sonnet-5",
                                   local_iso(started + 10))
        check("同名2体があるので諦める", got, None)
        got = livefeed.measure_for(project_path, "壊れた記録", "claude-sonnet-5",
                                   local_iso(started + 30))
        check("一意なら実測値を返す", (got or {}).get("agentId"), "brk1")

        print("\n[14] 経過時間の見た目が破綻しない（負の値を出さない）")
        check("経過秒は非負", all(
            (a.get("live") or {}).get("elapsedSec", 0) >= 0 for a in st["agents"]), True)

        print()
        print("[15] 指示文に名前が入っていれば結ぶ（Workflow 経由の主な手がかり）")
        # Workflow ツールで起動した機体には meta.json に description が無い（実測）。
        # 代わりに「渡した指示文に、カードの名前がそのまま入っているか」を手がかりにする。
        # 似ている度合いではなく、そのまま含まれるかどうかだけを見る。
        session5 = "66666666-2222-3333-4444-555555555555"
        sub5 = live_root / slug / session5 / "subagents"
        write_agent(sub5, "px01", start=started + 40, cwd=project_path, session=session5,
                    model="sonnet", description="", workflow_run="wf_p",
                    prompt="共通の長い前置き。ここは2体とも同じ文面。" + ("あ" * 400)
                           + "# 観点: 読み取り層 を精査すること。",
                    tools=[("Bash", {"description": "読む"}, 0)], tokens=(1, 2, 300))
        write_agent(sub5, "px02", start=started + 41, cwd=project_path, session=session5,
                    model="sonnet", description="", workflow_run="wf_p",
                    prompt="共通の長い前置き。ここは2体とも同じ文面。" + ("あ" * 400)
                           + "# 観点: 対応づけ を精査すること。",
                    tools=[("Bash", {"description": "読む"}, 0)], tokens=(1, 2, 400))
        reset(livefeed)
        write_mission(data_home / "missions", "t10", project_path=project_path, started=started,
                      agents=[rec("R1", "観点: 読み取り層", "claude-sonnet-5", started + 40),
                              rec("R2", "観点: 対応づけ", "claude-sonnet-5", started + 41)])
        st = dashlib.build_state("t10")
        got = {a["id"]: (a["live"] or {}).get("agentId") for a in st["agents"]}
        check("指示文に名前が出てくる機体に結ぶ", got, {"R1": "px01", "R2": "px02"})

        print()
        print("[16] 同じ語が2体の指示文に出てくるときは結ばない")
        write_agent(sub5, "px03", start=started + 42, cwd=project_path, session=session5,
                    model="sonnet", description="", workflow_run="wf_p",
                    prompt="別の機体だが # 観点: 読み取り層 にも触れている。",
                    tools=[("Bash", {"description": "読む"}, 0)], tokens=(1, 2, 500))
        reset(livefeed)
        write_mission(data_home / "missions", "t11", project_path=project_path, started=started,
                      agents=[rec("R1", "観点: 読み取り層", "claude-sonnet-5", started + 40)])
        st = dashlib.build_state("t11")
        check("一意でなければ結ばない", st["agents"][0]["live"], None)

        print()
        print("[17] 対応づけ用の手がかりを画面へ渡さない")
        reset(livefeed)
        st = dashlib.build_state("t10")
        leaked = sorted(k for a in st["agents"] if a["live"] for k in a["live"] if k.startswith("_"))
        check("_ 始まりのキーが漏れていない", leaked, [])
        leaked_o = sorted(k for o in st["sources"]["liveOrphans"] for k in o if k.startswith("_"))
        check("孤児側にも漏れていない", leaked_o, [])

    finally:
        os.environ.pop("AGENT_DASHBOARD_DATA_HOME", None)
        os.environ.pop("AGENT_DASHBOARD_LIVE_ROOT", None)
        os.environ.pop("AGENT_DASHBOARD_LIVE_ENUM_TTL", None)
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    if FAILED:
        print(f"NG {len(FAILED)} 件: " + " / ".join(FAILED))
        return 1
    print("すべて通りました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
