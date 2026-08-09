#!/usr/bin/env python3
"""Subagent Dashboard — 状態更新CLI

state.json の書き換えは必ずこのCLI経由で行う。時刻・世代・ログ・サマリー集計は
すべてここで自動処理するので、書式崩れや取りこぼしが構造的に起きない。

対象プロジェクトは **カレントディレクトリから自動判定** される。
どのプロジェクトで作業していても、同じコマンドをそのまま実行すればよい。

    start  --title "..."                  ミッション開始
    add    --id SCOUT-A --name "偵察A" ... サブエージェントを登録
    done   --id SCOUT-A --sec 42 ...       完了を記録
    finish --headline "..."                ミッション完了

    log --who "指令塔" --text "..."        イベントログに1行足す
    status / projects / history / demo / reset [--purge] / remove [--yes]

start のたびに、それまでの state.json と agents/ は
missions/<slug>/history/<runId>/ へ退避される（過去のミッションは消えない）。
一覧は history、残す件数は環境変数 AGENT_DASHBOARD_HISTORY_KEEP（既定 20）。

呼び出し方（どれでも同じ）:
    python update_state.py <コマンド> ...   このファイルを直接実行
    dash <コマンド> ...                     同じディレクトリのランチャ経由（Windows は dash.cmd）

別のプロジェクトを対象にしたいときだけ --project を付ける。
実測できなかった値（--tokens / --tools）は省略すれば null が入り、画面は「—」と表示する。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import dashlib
import i18n
from i18n import t
from dashlib import (
    COMMAND_ID,
    STATUSES,
    agents_dir,
    cell,
    elapsed_sec_from,
    fmt_num,
    fmt_sec,
    iso_ago,
    now_iso,
    pad,
    state_file,
)

dashlib.use_utf8_stdio()

# 初回実行時の自動セットアップ（非対話環境では警告のみ）
try:
    import auto_setup
    auto_setup.check_and_setup(silent=True)
except Exception:
    pass  # セットアップに失敗しても本体の動作は続ける


# ---------------------------------------------------------------- 補助


def die(msg: str) -> None:
    print(t("Error: {msg}").format(msg=msg), file=sys.stderr)
    sys.exit(1)


def pick_project(args) -> dict:
    try:
        return dashlib.resolve_project(getattr(args, "project", None))
    except ValueError as e:
        die(str(e))


def project_label(project: dict) -> str:
    where = f" / {project['path']}" if project.get("path") else ""
    return t("{name} ({slug}{where})").format(
        name=project["name"], slug=project["slug"], where=where
    )


def read_state(slug: str, project: dict, required: bool) -> dict:
    ok, value, err = dashlib.read_json_safe(state_file(slug))
    if not ok or not isinstance(value, dict):
        if required:
            die(
                t("This project has no state.json ({err}).").format(err=err)
                + "\n"
                + t("      Target: {name}").format(name=project_label(project))
                + "\n"
                + t('      Run  update_state.py start --title "..."  first.')
            )
        return dashlib.empty_state(project)

    value.setdefault("agents", [])
    value.setdefault("log", [])
    if not isinstance(value["agents"], list):
        value["agents"] = []
    if not isinstance(value["log"], list):
        value["log"] = []
    if not isinstance(value.get("mission"), dict):
        value["mission"] = dashlib.empty_state()["mission"]
    # プロジェクト情報が欠けていれば今回の解決結果で補う
    info = value.get("project") if isinstance(value.get("project"), dict) else {}
    value["project"] = {
        "slug": slug,
        "name": info.get("name") or project["name"],
        "path": info.get("path") or project["path"],
    }
    return value


def push_log(state: dict, who: str, text: str) -> None:
    state["log"].append({"at": now_iso(), "who": who, "text": text})


def find_agent(state: dict, agent_id: str):
    for a in state["agents"]:
        if a.get("id") == agent_id:
            return a
    return None


def find_in_history(slug: str, agent_id: str, limit: int = 5) -> dict | None:
    """その機体が直近の履歴に居ないか探す。居ればその記録の要約を返す。

    現在のミッションに居ない機体を done しようとしたとき、「まだ add していない」のと
    「別の start に押し出された」のとでは、次に取るべき手が正反対になる。前者は add すれば
    直るが、後者で add すると**押し出した側のチームの機体として登録される**＝2本の
    ミッションの記録が混ざる。区別せずに「先に add してください」とだけ言えば、
    後者の人を必ず間違いへ導くので、ここで見分ける。

    見るのは直近 limit 件まで。SCOUT-A のような ID は毎回使い回されるので、古い記録に
    同じ ID が居るのは当たり前であり、それは押し出しの証拠にならない。
    """
    for run in dashlib.list_runs(slug)[:limit]:
        ok, value, _ = dashlib.read_json_safe(dashlib.run_state_file(slug, run["runId"]))
        if not ok or not isinstance(value, dict):
            continue
        agents = value.get("agents")
        if not isinstance(agents, list):
            continue
        if any(isinstance(a, dict) and a.get("id") == agent_id for a in agents):
            return run
    return None


def missing_agent_message(project: dict, state: dict, agent_id: str) -> str:
    """done しようとした機体が現在のミッションに居ないときの案内。

    押し出されたと分かった場合だけ、言うことを変える（find_in_history の説明を参照）。
    """
    lost = find_in_history(project["slug"], agent_id)
    if lost is None:
        return (
            t("{id} is not in state.json. Run add for it first.").format(id=agent_id)
            + "\n"
            + t("      Target: {name}").format(name=project_label(project))
        )

    mission = state.get("mission") if isinstance(state.get("mission"), dict) else {}
    now_title = dashlib.as_str(mission.get("title")) or t("(untitled mission)")
    return "\n".join([
        t('{id} is not in the current mission "{title}".\n'
          '      The same ID is in the recent history "{lost}" (history/{run_id}/), so\n'
          "      that one was probably pushed out by another start. A record that has\n"
          "      been pushed out can no longer be written to (it cannot be marked\n"
          "      finished afterwards).")
        .format(id=agent_id, title=now_title, lost=lost["title"], run_id=lost["runId"]),
        t("      Target: {name}").format(name=project_label(project)),
        t('      Running add here registers it as a unit of "{title}", so the two\n'
          "      records get mixed together. When you run two missions in parallel in\n"
          "      the same directory, put --project <a unique name> on all of\n"
          "      start / add / done / finish so the records are kept apart.")
        .format(title=now_title),
    ])


def generation_of(state: dict, parent_id: str | None) -> int:
    if not parent_id:
        return 0
    cur = find_agent(state, parent_id)
    if cur is None:
        return 1  # 親が居ない場合は指令塔直下扱い
    depth = 1
    seen = {parent_id}
    while cur and cur.get("parentId") and depth < dashlib.MAX_DEPTH:
        nxt = find_agent(state, cur["parentId"])
        if nxt is None or nxt["id"] in seen:
            break
        seen.add(nxt["id"])
        cur = nxt
        depth += 1
    return depth


def unfinished_mission(state: dict) -> dict | None:
    """「全機帰還したのに finish が打たれていない」状態を見つける。

    締め忘れは何も壊さない。だから誰も気づかない。次の start が来れば稼働中の
    まま履歴へ流れ、それまで画面には「稼働中」と出続ける。**防ぐのではなく、
    見えるようにする**ための判定をここに1つだけ置き、done / start / status の
    3か所と画面がこの同じ規則を使う。

    締め忘れと言えるのは、次のすべてが揃ったときだけ。
      - ミッションが running（done は締め済み、standby はまだ始まっていない）
      - サブエージェントが1体以上いる（0体なら「開始しただけ」で、締める段階にない）
      - そのサブエージェントが全員 done（1体でも稼働中なら、まだ待っている最中）

    指令塔（COMMAND）は数えない。指令塔は finish を打つまで running のままなのが
    正しい姿なので、ここに含めると条件が永久に揃わず、警告が一度も出なくなる。
    """
    mission = state.get("mission") if isinstance(state.get("mission"), dict) else {}
    if mission.get("phase") != "running":
        return None

    agents = state.get("agents") if isinstance(state.get("agents"), list) else []
    workers = [a for a in agents if isinstance(a, dict) and a.get("id") != COMMAND_ID]
    if not workers:
        return None
    if any(a.get("status") != "done" for a in workers):
        return None

    # 最後の1体が帰ってきた時刻。ISO 文字列同士の比較で足りる（同じ書式で書かれる）。
    stamps = [dashlib.as_str(a.get("finishedAt")) for a in workers]
    last = max((s for s in stamps if s), default="")
    return {
        "count": len(workers),
        "title": dashlib.as_str(mission.get("title")) or t("(untitled mission)"),
        "lastAt": last or None,
    }


# ---------------------------------------------------------------- コマンド


def cmd_start(args) -> None:
    project = pick_project(args)
    title = args.title or t("(untitled mission)")
    at = now_iso()

    # 上書きする前に、いま置き換えようとしているものを見ておく。稼働中のまま
    # 履歴へ流れる記録は、以後ずっと「未完」として残るのに、退避の時点では何も
    # 言われない。ここが締め忘れに気づける最後の場所になる。
    # 見るだけで直さない。あとから finishedAt を書けば、それは実測ではなくなる。
    previous = read_state(project["slug"], project, required=False)
    prev_mission = previous.get("mission", {})
    prev_running = prev_mission.get("phase") == "running"
    prev_pending = unfinished_mission(previous)

    state = dashlib.empty_state(project)
    state["mission"].update({"phase": "running", "title": title, "startedAt": at})
    state["agents"].append(
        {
            "id": COMMAND_ID,
            "name": t("Command"),
            "parentId": None,
            "generation": 0,
            "model": args.model,
            "mission": t("overall control"),
            "status": "running",
            "startedAt": at,
            "finishedAt": None,
            "result": None,
        }
    )
    push_log(state, t("Command"), t("Mission started — {title}").format(title=title))

    # 前のミッションを history/<runId>/ へ退避してから上書きする。ここを通らないと
    # 過去の作業が痕跡なく消える。失敗しても start は止めない（警告だけ出て None が返る）。
    archived = dashlib.archive_current_run(project["slug"])

    dashlib.write_state(project["slug"], state)

    # 画面に映すチームをここに差し替える。これが「次が稼働したら前のチームは
    # 消える」の唯一の分岐点。done や finish では動かさないので、完了したチームは
    # 次の start が来るまで映ったままになる。
    dashlib.set_current(project["slug"])

    # 前のミッションの孫（自己申告）を持ち越さない。
    # state.json だけ作り直して agents/ を残すと、完了通知が来なかった孫が
    # 以降すべてのミッションで「稼働中」のまま並び続ける。
    stale = 0
    try:
        for p in agents_dir(project["slug"]).iterdir():
            if p.suffix.lower() == ".json":
                p.unlink()
                stale += 1
    except OSError:
        pass

    print(t("Mission started: {title}").format(title=title))
    print(t("  Target project: {name}").format(name=project_label(project)))
    # **自由記述の言語は、ここでしか伝えられない。** 運用ルールはエージェントの
    # セッション開始時に一度読まれるだけなので、途中で dash lang しても届かない。
    # start は1ミッションに1回しか打たれないので、毎回出しても埋もれない。
    print(dashlib.expected_lang_notice())
    if archived["runId"]:
        print(t("  Archived the previous mission into history: history/{run_id}/")
              .format(run_id=archived["runId"]))
        print(t("    You can list them with  update_state.py history"))

    # 退避したものが締められていなかったことを、ここで1度だけ言う。もう直せないので
    # 「次から気をつける」ための知らせ。全機帰還済み（＝純粋な締め忘れ）と、
    # まだ帰っていない機体がある（＝途中で放棄）とでは意味が違うので言い分ける。
    if prev_running and archived["runId"]:
        prev_title = dashlib.as_str(prev_mission.get("title")) or t("(untitled mission)")
        if prev_pending:
            print(
                t('  ⚠️  All {n} units of the archived "{title}" were back, '
                  "but finish was never run.")
                .format(n=prev_pending["count"], title=prev_title)
            )
            print(t('      It stays in the history as "Unfinished" '
                    "(it cannot be marked finished afterwards)."))
        else:
            print(
                t('  ⚠️  The archived "{title}" ended while still running '
                  "(there are units that never returned).").format(title=prev_title)
            )
            print(t('      It stays in the history as "Unfinished".'))
            # 未帰還のまま押し出された、はほとんどの場合「2本を同時に走らせたかった」。
            # 押し出された機体に done を打つと存在しないと言われて弾かれるので、
            # ここで対策まで言い切る。次の start を打つ前に読める唯一の場所。
            print(
                t("      If you meant to run two missions at once, there are not enough\n"
                  "      record destinations. When running them in parallel in the same\n"
                  "      directory, split them with  start --project <a unique name>\n"
                  "      (put the same --project on add / done / finish too).")
            )
    if archived["pruned"]:
        print(
            t("  Moved {n} old records over the limit of {keep} to the trash: {list}")
            .format(n=len(archived["pruned"]), keep=dashlib.history_keep(),
                    list=", ".join(archived["pruned"]))
        )
    if stale:
        print(t("  Cleared away {n} grandchild self-report files from the previous mission.")
              .format(n=stale))

    # 運用ルールが本体より古ければ、ここで知らせる。start は1ミッションに1回しか
    # 打たれないので、add / done のたびに繰り返して読み飛ばされることがない。
    notice = dashlib.stale_block_notice()
    if notice:
        print()
        print(notice)
        print()

    # セットアップのあとで別の CLI を入れた人は、この知らせが出るまで何も気づけない
    # （画面には何も出ないだけで、エラーにはならない）。add / done は1ミッションで
    # 何度も打たれるので、そちらに出すと読み飛ばされる。start だけに出す。
    unwired = dashlib.unwired_agent_notice()
    if unwired:
        print()
        print(unwired)
        print()

    # タイトルが設定言語で書かれていないように見えたら知らせる。**あとから直せない**
    # ので（title を書き換えるコマンドは無い）、直せると言ってはいけない。
    if args.title:
        notice = dashlib.free_text_lang_notice(
            [("--title", args.title)] if dashlib.free_text_lang_mismatch(args.title) else [],
            fixable=False,
        )
        if notice:
            print(notice)


def cmd_add(args) -> None:
    project = pick_project(args)
    slug = project["slug"]
    state = read_state(slug, project, required=True)

    parent_id = args.parent or COMMAND_ID
    if parent_id != COMMAND_ID and find_agent(state, parent_id) is None:
        print(
            t("Warning: the parent {id} is not in state.json. "
              "It will be shown in the first column.").format(id=parent_id),
            file=sys.stderr,
        )

    existing = find_agent(state, args.id)

    # **打ち直しで実測値を消さない。** 言語を直すには同じ ID で add を打ち直すことになる
    # ので、ここが無条件の上書きだと、その操作が done 済みの result（所要・トークン・
    # ツール・要約）を消し、ミッションまで running へ巻き戻して summary を消す。
    # 記述を直したいだけの人が集計を失うのは、黙って壊れる側の挙動。
    # 渡されなかったものは既存の値を残す（--status を省いたら状態も保つ）。
    status = args.status or (existing or {}).get("status") or "running"

    agent = {
        "id": args.id,
        "name": args.name or (existing or {}).get("name") or args.id,
        "parentId": parent_id,
        "generation": generation_of(state, parent_id),
        # 空のままにして、表示の直前に dashlib.normalize_agent が t("unknown") を
        # 当てる。ここで訳文を書き込むと、記録した言語がそのまま state.json に残る。
        "model": args.model or (existing or {}).get("model") or "",
        "mission": args.mission or (existing or {}).get("mission") or "",
        "status": status,
        "startedAt": ((existing or {}).get("startedAt")
                      or (None if status == "standby" else now_iso())),
        "finishedAt": (existing or {}).get("finishedAt"),
        "result": (existing or {}).get("result"),
    }

    if existing is not None:
        print(t("Warning: {id} is already registered. Overwriting it.").format(id=args.id),
              file=sys.stderr)
        print(t("         The measured values and the status are kept "
                "(only what you passed is replaced)."), file=sys.stderr)
        existing.update(agent)
    else:
        state["agents"].append(agent)

    parent = find_agent(state, parent_id)
    parent_name = t("Command") if parent_id == COMMAND_ID else (parent or {}).get("name", parent_id)
    if existing is not None:
        # 「誕生」と書くと、同じ機体が2回生まれたことになる。ログは追記しかしないので、
        # 打ち直しは打ち直しとして残す（古い行も消さない。書いたとおりに残すのが約束）。
        push_log(state, parent_name,
                 t("{name} ({id}) was rewritten — {mission}")
                 .format(name=agent["name"], id=args.id,
                         mission=agent["mission"] or t("no mission recorded")))
    elif status == "standby":
        push_log(state, parent_name,
                 t("{name} ({id}) is standing by").format(name=agent["name"], id=args.id))
    else:
        push_log(state, parent_name,
                 t("{name} ({id}) was born — {mission}")
                 .format(name=agent["name"], id=args.id,
                         mission=agent["mission"] or t("no mission recorded")))

    # 完了済みのミッションに**新しく**機体を足したときは running に戻す（作業が再開した）。
    # 既存機体の打ち直しでは戻さない。戻すと summary（合計）が消える。
    if state["mission"].get("phase") != "running" and existing is None:
        state["mission"].update({"phase": "running", "finishedAt": None, "summary": None})

    dashlib.write_state(slug, state)

    print(t("Registered: {id} ({name} / {status} / column {gen})")
          .format(id=args.id, name=agent["name"], status=status,
                  gen=agent["generation"]))
    print(t("  Target project: {name}").format(name=project_label(project)))

    # 設定された言語で書かれていないように見えたら知らせる。**書き込みは止めない。**
    checks = []
    if args.name and args.name != args.id and dashlib.free_text_lang_mismatch(args.name):
        checks.append(("--name", args.name))
    if args.mission and dashlib.free_text_lang_mismatch(args.mission):
        checks.append(("--mission", args.mission))
    notice = dashlib.free_text_lang_notice(checks, fixable=True)
    if notice:
        print(notice)


def cmd_done(args) -> None:
    project = pick_project(args)
    slug = project["slug"]
    state = read_state(slug, project, required=True)

    agent = find_agent(state, args.id)
    if agent is None:
        die(missing_agent_message(project, state, args.id))

    elapsed = args.sec if args.sec is not None else elapsed_sec_from(agent.get("startedAt"))

    agent["status"] = "done"
    agent["finishedAt"] = now_iso()
    agent["result"] = {
        "elapsedSec": elapsed,
        "tokens": args.tokens,
        "toolCalls": args.tools,
        "headline": args.headline,
    }

    bits = [t("elapsed {time}").format(time=fmt_sec(elapsed))]
    if args.tokens is not None:
        bits.append(t("{n} tokens").format(n=fmt_num(args.tokens)))
    if args.tools is not None:
        bits.append(t("{n} tool calls").format(n=args.tools))

    push_log(state, agent["name"],
             t("Back home — {headline} ({detail})")
             .format(headline=args.headline or t("no report"), detail=" / ".join(bits)))
    dashlib.write_state(slug, state)

    print(t("Marked done: {id} ({detail})")
          .format(id=args.id, detail=" / ".join(bits)))
    print(t("  Target project: {name}").format(name=project_label(project)))
    if args.tokens is None:
        print(t('  * No token count was given, so it is null (the screen shows "—").'))
    if args.tools is None:
        print(t('  * No tool-call count was given, so it is null (the screen shows "—").'))

    if args.headline and dashlib.free_text_lang_mismatch(args.headline):
        notice = dashlib.free_text_lang_notice([("--headline", args.headline)], fixable=True)
        if notice:
            print(notice)

    # 締め忘れが起きる瞬間はここ。最後の1体を done にした直後、報告をまとめる作業に
    # 意識が移り、その手前にある finish が抜ける。だから催促はこの出口に置く。
    # そのまま貼れる形で出すのは、思い出しても書式を思い出せないと結局止まるため。
    pending = unfinished_mission(state)
    if pending:
        print()
        print(t("  ★ That is all {n} units back home. The mission has not been closed yet.")
              .format(n=pending["count"]))
        print(t('     python update_state.py finish '
                '--headline "<one-line summary of the whole mission>"'))


def cmd_finish(args) -> None:
    project = pick_project(args)
    slug = project["slug"]
    state = read_state(slug, project, required=True)

    workers = [a for a in state["agents"] if a.get("id") != COMMAND_ID]
    unfinished = [a for a in workers if a.get("status") != "done"]
    if unfinished:
        ids = ", ".join(a["id"] for a in unfinished)
        print(
            t("Warning: {n} agents have not finished ({ids}). "
              "Recording the mission as done anyway.").format(n=len(unfinished), ids=ids),
            file=sys.stderr,
        )

    token_values = [
        a["result"]["tokens"]
        for a in workers
        if isinstance(a.get("result"), dict) and a["result"].get("tokens") is not None
    ]
    total_tokens = sum(token_values) if token_values else None

    at = now_iso()
    elapsed = elapsed_sec_from(state["mission"].get("startedAt"))
    headline = args.headline or t("all units back home")

    command = find_agent(state, COMMAND_ID)
    if command is not None:
        command.update(
            {
                "status": "done",
                "finishedAt": at,
                "result": {
                    "elapsedSec": elapsed,
                    "tokens": None,
                    "toolCalls": None,
                    "headline": headline,
                },
            }
        )

    for a in workers:
        if a.get("status") == "standby":
            a["status"] = "done"
            a["finishedAt"] = at
            if not isinstance(a.get("result"), dict):
                a["result"] = {
                    "elapsedSec": None,
                    "tokens": None,
                    "toolCalls": None,
                    "headline": t("ended without ever deploying"),
                }

    state["mission"].update(
        {
            "phase": "done",
            "finishedAt": at,
            "summary": {
                "agentCount": len(workers),
                "totalTokens": total_tokens,
                "elapsedSec": elapsed,
                "headline": headline,
            },
        }
    )

    push_log(
        state,
        t("Command"),
        t("Mission complete — {n} units / {tokens} tokens in total / elapsed {time}")
        .format(n=len(workers), tokens=fmt_num(total_tokens), time=fmt_sec(elapsed)),
    )
    dashlib.write_state(slug, state)

    # 表示幅は言語で変わるので、余白は pad() に数えさせる（全角を2桁として数える）。
    w = 20
    print(t("Marked the mission as done."))
    print(pad(t("  Target project"), w) + project_label(project))
    print(pad(t("  Units"), w) + str(len(workers)))
    print(pad(t("  Total tokens"), w) + fmt_num(total_tokens)
          + (t(" (nothing measured)") if total_tokens is None else ""))
    print(pad(t("  Elapsed"), w) + fmt_sec(elapsed))

    if args.headline and dashlib.free_text_lang_mismatch(args.headline):
        notice = dashlib.free_text_lang_notice([("--headline", args.headline)], fixable=True)
        if notice:
            print(notice)


def cmd_log(args) -> None:
    project = pick_project(args)
    slug = project["slug"]
    state = read_state(slug, project, required=True)
    push_log(state, args.who, args.text)
    dashlib.write_state(slug, state)
    print(t("Added a log line. ({name})").format(name=project["name"]))


def cmd_status(args) -> None:
    project = pick_project(args)
    slug = project["slug"]
    state = read_state(slug, project, required=False)
    mission = state["mission"]
    phases = {"standby": t("standby"), "running": t("running"), "done": t("done")}
    phase_label = phases.get(mission.get("phase"), "?")

    # 「稼働中」とだけ出すと、締め忘れが動いている最中と見分けられない。
    pending = unfinished_mission(state)
    if pending:
        phase_label += t(" (all units back, not closed)")

    # 表示幅は言語で変わるので、余白は pad() に数えさせる。
    w = 14
    print()
    print(pad(t("Project"), w) + project_label(project))
    print(pad(t("Mission"), w) + str(mission.get("title")))
    print(pad(t("Phase"), w) + phase_label)
    print(pad(t("Started"), w) + (mission.get("startedAt") or "—"))
    print(pad(t("Updated"), w) + (state.get("updatedAt") or "—"))
    summary = mission.get("summary")
    if isinstance(summary, dict):
        print(
            pad(t("Summary"), w)
            + t("{n} units / {tokens} tokens in total / elapsed {time}")
            .format(n=summary.get("agentCount"),
                    tokens=fmt_num(summary.get("totalTokens")),
                    time=fmt_sec(summary.get("elapsedSec")))
        )
    print()

    # 「状態」の桁は t("awaiting report") が入る幅にしてある（cell は width-2 で切る）。
    cols = [(t("Gen"), 6), (t("Status"), 18), ("ID", 16), (t("Name"), 20),
            (t("Elapsed"), 10), (t("Tokens"), 12), (t("Tools"), 8)]
    print("  " + "".join(cell(h, w) for h, w in cols))
    print("  " + "".join(pad("-" * (w - 2), w) for _, w in cols))

    # 「報告待ち」は画面と同じく導出で出す（state.json には書かれていない）。
    # dashlib.assign_waiting は正規化済みの dict を前提にしているので、生の
    # state.json を読むここでは .get() で同じ規則を組み直す。孫の自己申告は
    # 元から一覧に出していないので、ここでも数えない。
    ids = {a.get("id") for a in state["agents"]}
    waiting_ids = {
        a.get("parentId")
        for a in state["agents"]
        if a.get("status") == "running"
        and a.get("parentId") in ids
        and a.get("parentId") != a.get("id")
    }

    for a in state["agents"]:
        st = phases.get(a.get("status"), str(a.get("status")))
        if a.get("status") == "running" and a.get("id") in waiting_ids:
            st = t("awaiting report")
        result = a.get("result") if isinstance(a.get("result"), dict) else {}
        sec = elapsed_sec_from(a.get("startedAt")) if a.get("status") == "running" else result.get("elapsedSec")
        row = [
            str(a.get("generation")),
            st,
            str(a.get("id")),
            str(a.get("name")),
            fmt_sec(sec),
            fmt_num(result.get("tokens")),
            fmt_num(result.get("toolCalls")),
        ]
        print("  " + "".join(cell(v, w) for v, (_, w) in zip(row, cols)))

    try:
        self_count = len([p for p in agents_dir(slug).iterdir() if p.suffix.lower() == ".json"])
    except OSError:
        self_count = 0

    last = state["log"][-1]["text"] if state["log"] else "—"
    print()
    print(t("  Grandchild self-report files: {n} ({path})")
          .format(n=self_count, path=agents_dir(slug)))
    print(t("  Log: {n} lines (latest: {text})")
          .format(n=len(state["log"]), text=last))
    if pending:
        ago = elapsed_sec_from(pending["lastAt"])
        since = t(" ({time} since the last one came back)").format(time=fmt_sec(ago)) \
            if ago is not None else ""
        print()
        print(t("  ★ All {n} units are back, but the mission has not been closed{since}.")
              .format(n=pending["count"], since=since))
        print(t('     python update_state.py finish '
                '--headline "<one-line summary of the whole mission>"'))
    print()


def cmd_projects(args) -> None:
    projects = dashlib.list_projects()
    current = pick_project(args)
    # 画面と同じ判定を使う。resolve_active_slug は「1チームだけ映していた頃」の
    # 名残で基準が違い（フェーズを見ず最終更新順に落ちる）、そちらを使うと
    # ここの ● が画面に出ていないチームに付いてしまう。
    shown = set(dashlib.resolve_visible_slugs())
    pointer = dashlib.read_current()

    print()
    print(t("Mission storage: {path}").format(path=dashlib.MISSIONS_DIR))
    print(t("Project for this folder: {slug}").format(slug=current["slug"]))
    print()

    if not projects:
        print(t("  There are no records yet (the screen is on standby)."))
        print(t('  In your working directory, run  '
                'update_state.py start --title "..."'))
        print()
        return

    cols = [("", 6), (t("Project"), 30), (t("Phase"), 10), (t("Progress"), 11),
            (t("Last updated"), 22), (t("Slug"), 26)]
    phases = {"standby": t("standby"), "running": t("running"), "done": t("done")}
    print("  " + "".join(cell(h, w) for h, w in cols))
    print("  " + "".join(pad("-" * (w - 2), w) for _, w in cols))
    for p in projects:
        phase = phases.get(p["phase"], "?")
        mark = ("★" if p["slug"] == pointer else "●" if p["slug"] in shown else "")
        mark += "→" if p["slug"] == current["slug"] else ""
        row = [
            mark,
            p["name"],
            phase,
            f"{p['done']}/{p['total']}",
            (p["updatedAt"] or "—")[:19].replace("T", " "),
            p["slug"],
        ]
        print("  " + "".join(cell(v, w) for v, (_, w) in zip(row, cols)))
    print()
    print(t("  ★ = on screen, and stays there until the next start"))
    print(t("  ● = on screen (running, or the other half of a parallel run)"))
    print(t("  → = the target derived from the current directory"))
    print(t("  Only ★ and ● appear on the screen. The unmarked ones are only kept as\n"
            "  records and never appear. Delete the ones you do not need with  "
            "update_state.py remove"))
    print()


def cmd_history(args) -> None:
    """このプロジェクトの過去のミッションを一覧表示する。

    start のたびに、それまでの state.json と agents/ が history/<runId>/ へ移る。
    ここに出るものは画面からも見返せる。
    """
    project = pick_project(args)
    slug = project["slug"]
    keep = dashlib.history_keep()

    try:
        runs = dashlib.list_runs(slug)
    except OSError as e:
        die(t("Could not read the history: {err}").format(err=e))

    state = read_state(slug, project, required=False)
    mission = state["mission"]
    phase_label = {"standby": t("standby"), "running": t("running"), "done": t("done")}

    # 表示幅は言語で変わるので、余白は pad() に数えさせる。
    w = 18
    print()
    print(pad(t("Target project:"), w) + project_label(project))
    print(pad(t("History folder:"), w) + str(dashlib.history_dir(slug)))
    if keep:
        print(pad(t("Records kept:"), w)
              + t("{n} records (change with the environment variable {var})")
              .format(n=keep, var=dashlib.ENV_HISTORY_KEEP))
    else:
        print(pad(t("Records kept:"), w)
              + t("0 records — history is turned off "
                  "(environment variable {var})").format(var=dashlib.ENV_HISTORY_KEEP))
    print(pad(t("Current mission:"), w)
          + t("{title} ({phase})").format(
              title=mission.get("title"),
              phase=phase_label.get(mission.get("phase"), "?")))
    print()

    if not runs:
        print(t("  There are no past records yet."))
        print(t("  The next time you run start, the current record is archived into\n"
                "  history/ and lines up here."))
        print()
        return

    cols = [("runId", 20), (t("Started"), 22), (t("Finished"), 22), (t("Status"), 10),
            (t("Units"), 8), (t("Mission"), 34)]
    print("  " + "".join(cell(h, w) for h, w in cols))
    print("  " + "".join(pad("-" * (w - 2), w) for _, w in cols))
    for r in runs:
        row = [
            r["runId"],
            (r["startedAt"] or "—")[:19].replace("T", " "),
            (r["finishedAt"] or "—")[:19].replace("T", " "),
            phase_label.get(r["phase"], "?"),
            str(r["agentCount"]),
            r["title"],
        ]
        print("  " + "".join(cell(v, w) for v, (_, w) in zip(row, cols)))
    print()
    print(t("  {n} records (newest first). Once the limit is reached, "
            "the oldest go to the trash.").format(n=len(runs)))
    print(t("  Units = the number registered in state.json (Command excluded).\n"
            "  Grandchild self-reports are not counted."))
    print()


def cmd_demo(args) -> None:
    """表示テスト用。現在時刻を基準に作るので経過時間が自然に見える。"""
    project = pick_project(args)
    slug = project["slug"]

    # ダミーの文言も訳す。英語の利用者が demo を打ったときに日本語のカードが並ぶと
    # 「表示テスト」にならない。以下は全部 t() を通した値を組み立ててから入れる。
    demo_title = t("display test (dummy data)")
    name_a = t("Scout A")
    name_b = t("Scout B")
    name_c = t("Scout C")
    name_a1 = t("Analysis A-1")
    name_a1x = t("Sweep A-1-x")
    mission_a = t("find every API call site under src/")
    mission_b = t("trace the dependencies of the test code")
    mission_c = t("check the documentation for gaps (waiting to deploy)")
    mission_a1 = t("classify the 23 sites found by impact")
    mission_a1x = t("cross-check the classification and drop duplicates "
                    "(grandchild self-report)")
    headline_a = t("pinned down 23 call sites across 7 files")

    state = dashlib.empty_state(project)
    state["mission"].update(
        {"phase": "running", "title": demo_title, "startedAt": iso_ago(96)}
    )
    state["agents"] = [
        {
            "id": COMMAND_ID,
            "name": t("Command"),
            "parentId": None,
            "generation": 0,
            "model": "claude-opus-5",
            "mission": t("overall control"),
            "status": "running",
            "startedAt": iso_ago(96),
            "finishedAt": None,
            "result": None,
        },
        {
            "id": "SCOUT-A",
            "name": name_a,
            "parentId": COMMAND_ID,
            "generation": 1,
            "model": "claude-sonnet-5",
            "mission": mission_a,
            "status": "done",
            "startedAt": iso_ago(90),
            "finishedAt": iso_ago(48),
            "result": {
                "elapsedSec": 42,
                "tokens": 18400,
                "toolCalls": None,  # 実測できなかった場合の表示確認用
                "headline": headline_a,
            },
        },
        {
            "id": "SCOUT-B",
            "name": name_b,
            "parentId": COMMAND_ID,
            "generation": 1,
            "model": "claude-sonnet-5",
            "mission": mission_b,
            "status": "running",
            "startedAt": iso_ago(34),
            "finishedAt": None,
            "result": None,
        },
        {
            "id": "SCOUT-C",
            "name": name_c,
            "parentId": COMMAND_ID,
            "generation": 1,
            "model": "claude-haiku-4-5",
            "mission": mission_c,
            "status": "standby",
            "startedAt": None,
            "finishedAt": None,
            "result": None,
        },
        {
            "id": "A-1",
            "name": name_a1,
            "parentId": "SCOUT-A",
            "generation": 2,
            "model": "claude-sonnet-5",
            "mission": mission_a1,
            "status": "running",
            "startedAt": iso_ago(20),
            "finishedAt": None,
            "result": None,
        },
    ]
    born = t("{name} ({id}) was born — {mission}")
    state["log"] = [
        {
            "at": iso_ago(96),
            "who": t("Command"),
            "text": t("Mission started — {title}").format(title=demo_title),
        },
        {
            "at": iso_ago(90),
            "who": t("Command"),
            "text": born.format(name=name_a, id="SCOUT-A", mission=mission_a),
        },
        {
            "at": iso_ago(88),
            "who": t("Command"),
            "text": t("{name} ({id}) is standing by").format(name=name_c, id="SCOUT-C"),
        },
        {
            "at": iso_ago(48),
            "who": name_a,
            "text": t("Back home — {headline} ({detail})").format(
                headline=headline_a,
                detail=" / ".join([
                    t("elapsed {time}").format(time=fmt_sec(42)),
                    t("{n} tokens").format(n=fmt_num(18400)),
                ]),
            ),
        },
        {
            "at": iso_ago(34),
            "who": t("Command"),
            "text": born.format(name=name_b, id="SCOUT-B", mission=mission_b),
        },
        {
            "at": iso_ago(20),
            "who": name_a,
            "text": born.format(name=name_a1, id="A-1", mission=mission_a1),
        },
    ]

    dashlib.write_state(slug, state)
    dashlib.set_current(slug)   # 試しに見るのだから、そのまま画面に映す

    # 孫の自己申告サンプル（サーバー側マージの動作確認用）
    target = agents_dir(slug)
    target.mkdir(parents=True, exist_ok=True)
    sample = {
        "id": "A-1-x",
        "name": name_a1x,
        "parentId": "A-1",
        "model": "claude-haiku-4-5",
        "mission": mission_a1x,
        "status": "running",
        "startedAt": iso_ago(11),
        "log": [{
            "at": iso_ago(11),
            "who": name_a1,
            "text": born.format(name=name_a1x, id="A-1-x",
                                mission=t("registered by self-report")),
        }],
    }
    (target / "A-1-x.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(t("Wrote display-test data."))
    print(t("  Target project: {name}").format(name=project_label(project)))
    print(t("  Standby, running, awaiting report, done, grandchild self-reports and\n"
            "  missing measured values (—) all appear on the screen."))


def cmd_reset(args) -> None:
    project = pick_project(args)
    slug = project["slug"]

    dashlib.write_state(slug, dashlib.empty_state(project))
    print(t("Reset state.json (standby). Target: {name}")
          .format(name=project_label(project)))

    if dashlib.read_current() == slug:
        print(t("* The screen keeps this team selected but returns to the standby screen."))
    print(t("* The current record is emptied without being archived "
            "(only start archives it)."))
    try:
        kept = len(dashlib.list_runs(slug))
    except OSError:
        kept = 0
    if kept:
        print(t("* The {n} past records in history/ are left untouched "
                "(list them with history).").format(n=kept))
    print(t("* To delete the whole record folder (past records included), use remove."))

    if not args.purge:
        print(t("* The grandchild self-report files are still there. "
                "Add --purge to delete them."))
        return

    purged = 0
    try:
        for p in agents_dir(slug).iterdir():
            if p.suffix.lower() == ".json":
                p.unlink()
                purged += 1
    except OSError:
        pass
    print(t("Deleted {n} grandchild self-report files.").format(n=purged))


def cmd_remove(args) -> None:
    """プロジェクトの記録ごと削除する。

    reset は state.json を空にするだけで missions/<slug>/ を残すので、そのプロジェクトは
    「待機中」として並び続ける。記録そのものを消したいときはこちら。history/ の過去の
    記録も一緒に（フォルダごと）ゴミ箱へ移る。過去の記録を1件だけ消すなら
    dashlib.delete_run() を使う画面側の削除操作を使うこと。
    """
    project = pick_project(args)
    slug = project["slug"]

    if slug not in dashlib.list_slugs():
        die(
            t("There is no record for this project (missions/{slug}/ is not there).")
            .format(slug=slug)
            + "\n"
            + t("      Target: {name}").format(name=project_label(project))
            + "\n"
            + t("      You can check the list with  update_state.py projects")
        )

    state = read_state(slug, project, required=False)
    running = [a for a in state["agents"] if a.get("status") == "running"]
    if running:
        ids = ", ".join(str(a.get("id")) for a in running)
        print(t("Warning: {n} agents are still running ({ids}).")
              .format(n=len(running), ids=ids), file=sys.stderr)

    if not args.yes:
        # Windows では標準入力が NUL に繋がれていても isatty() が真になることがあるので、
        # ここは通ってしまう。その場合 input() が即 EOF を返すので、下で中止する。
        if not sys.stdin.isatty():
            die(t("This environment cannot ask for confirmation. "
                  "Add --yes if you mean to delete it."))
        try:
            # 応答の突き合わせは訳さない（どの言語でも [y/N] と書いてあるので、
            # 訳語で分岐すると翻訳のゆれがそのまま判定のずれになる）。
            answer = input(t("About to delete the records of {name}. Are you sure? [y/N]: ")
                           .format(name=project_label(project)))
        except EOFError:
            print()
            die(t("This environment cannot ask for confirmation. "
                  "Add --yes if you mean to delete it."))
        if answer.strip().lower() not in ("y", "yes"):
            print(t("Cancelled."))
            return

    try:
        info = dashlib.delete_project(slug, permanent=args.force)
    except (OSError, ValueError) as e:
        die(t("Failed to delete: {err}").format(err=e))

    if info["permanent"]:
        print(t("Deleted for good: {name}").format(name=project_label(project)))
        return

    w = 12
    print(t("Deleted (moved to the trash): {name}").format(name=project_label(project)))
    print(pad(t("  Moved to"), w) + str(info["movedTo"]))
    print(pad(t("  To undo"), w)
          + t("move this folder back to {path}").format(path=dashlib.mission_dir(slug)))


# ---------------------------------------------------------------- 引数定義


def non_negative_int(v: str) -> int:
    try:
        n = int(v)
    except ValueError:
        raise argparse.ArgumentTypeError(
            t("give an integer (got: {value})").format(value=v)) from None
    if n < 0:
        raise argparse.ArgumentTypeError(
            t("give an integer of 0 or more (got: {value})").format(value=v))
    return n


def add_project_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--project",
        default=None,
        help=t("target project (derived from the current directory when omitted)"),
    )


def _relanguage_instructions() -> None:
    """運用ルールを、いま選ばれた言語で書き直す（書き込んである CLI だけ）。

    **言語の設定と、エージェントがチームを組む言語は同じものでなければならない。**
    運用ルールの言語は「`--title` / `--name` / `--mission` / `--headline` を何語で
    書くか」そのものなので、設定だけ変えて運用ルールを置いていくと、設定は日本語なのに
    チームは英語で組まれる。しかも食い違いは画面の見た目ではなく**記録の中身**に出る
    ので、気づいたときには過去の記録が全部その言語で残っている。だから保存した直後に
    ここで書き直す（利用者に install.py の再実行を覚えておいてもらうのは無理）。

    書き直す先は install.rewrite_blocks() が選ぶ（このコピーを指しているものだけ）。
    **失敗は必ず知らせる。** 黙って旧言語のまま残るのが、いちばん気づけない壊れ方。
    """
    hint = "  python %s" % (dashlib.TOOL_ROOT / "install.py")
    try:
        import install  # 遅延 import。lang 以外のコマンドに install.py を巻き込まない
        done, failed = install.rewrite_blocks()
    except Exception as e:  # install.py が無い／読めない配布物でも lang は成立させる
        print(t("  ⚠️  Could not rewrite the operating rules ({path}): {err}")
              .format(path=dashlib.TOOL_ROOT / "install.py", err=e))
        print(t("      Rewrite them in the new language by running:"))
        print(hint)
        return

    for path, err in failed:
        print(t("  ⚠️  Could not rewrite the operating rules ({path}): {err}")
              .format(path=path, err=err))
    if failed:
        print(t("      Rewrite them in the new language by running:"))
        print(hint)

    for path in done:
        print(t("  The operating rules were rewritten in this language: {path}")
              .format(path=path))
    if done:
        print(t("  Restart the agent's session "
                "(the operating rules are read when it starts)."))
    elif not failed:
        # 未設定のコピー（開発用など）。ここで install.py を勧めておかないと、
        # 「言語は設定できたのにチームは英語のまま」の原因が最後まで分からない。
        print(t("  note: the operating rules of this copy are not written anywhere, "
                "so only the messages above changed."))
        print(t("      Rewrite them in the new language by running:"))
        print(hint)


def cmd_lang(args) -> None:
    """表示言語を見る／決める。

    引数を省いたときは「いま何で、どこから決まったか」を出す。決まり方が
    環境変数・保存値・OS の3系統あるので、出し所を書かないと「設定したのに
    変わらない」（＝環境変数が勝っている）を自力で切り分けられない。
    """
    if args.code:
        try:
            chosen = dashlib.write_lang_setting(args.code)
        except (ValueError, OSError) as e:
            print(t("Could not set the language: {err}").format(err=e), file=sys.stderr)
            sys.exit(1)
        print(t("Language set to {label} ({code}).")
              .format(label=i18n.label(chosen), code=chosen))
        print(t("  saved in {path}").format(path=dashlib.LANG_FILE))
        _relanguage_instructions()
        if os.environ.get(i18n.ENV_LANG):
            # 環境変数のほうが強い。保存はしたが、この端末では効かないと言っておく。
            print(t("  note: {var} is set, so it takes precedence over this setting.")
                  .format(var=i18n.ENV_LANG))
        return

    current = i18n.get_lang()
    print(t("Language: {label} ({code})")
          .format(label=i18n.label(current), code=current))
    env = os.environ.get(i18n.ENV_LANG)
    if env:
        print(t("  from the environment variable {var}={value}")
              .format(var=i18n.ENV_LANG, value=env))
    elif dashlib.read_lang_setting():
        print(t("  from the saved setting {path}").format(path=dashlib.LANG_FILE))
    else:
        print(t("  detected from the operating system"))
    print(t("  available: {list}")
          .format(list=" / ".join("%s (%s)" % (i18n.label(x), x) for x in i18n.SUPPORTED)))


def build_parser() -> argparse.ArgumentParser:
    # prog は指定しない。dash 経由で呼ばれたときに正しい名前が出るようにするため。
    p = argparse.ArgumentParser(
        description=t("Subagent Dashboard — the state-update CLI "
                      "(the target project is derived from the current directory)"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=t("Leave out any value you could not measure (--tokens / --tools). "
                 "Never fill in an estimate."),
    )
    sub = p.add_subparsers(dest="cmd", metavar=t("command"))

    s = sub.add_parser(
        "start",
        help=t("start a mission (the records so far move to history/, "
               "where history can look them up)"),
    )
    s.add_argument("--title", default="", help=t("name of the mission"))
    # 既定を空にしてあるのは、司令塔のモデルを**このツールが知る手段が無い**ため。
    # 特定のモデル ID を既定に置くと、別のモデル（Codex の GPT など）が回したときに
    # 画面が黙って嘘をつく。--tokens を推測で埋めないのと同じ理由で、分からないものは
    # 空のまま「—」と出す。運用ルールの start 行に --model を書いてあるので、
    # 手順どおりに動くエージェントは自分の ID を渡してくる。
    s.add_argument("--model", default="",
                   help=t("model ID of the command post"))
    add_project_arg(s)
    s.set_defaults(func=cmd_start)

    a = sub.add_parser("add", help=t("register a subagent right after starting it"))
    a.add_argument("--id", required=True, help=t("identifier (for example SCOUT-A)"))
    a.add_argument("--name", default="",
                   help=t("name shown on the screen (same as the ID when omitted)"))
    a.add_argument("--parent", default=COMMAND_ID,
                   help=t("ID of the parent (the command post when omitted)"))
    a.add_argument("--model", default="", help=t("model ID that was used"))
    a.add_argument("--mission", default="", help=t("what the task is"))
    # 既定を None にしてあるのは「省略された」と「running を指定した」を区別するため。
    # 区別できないと、打ち直しのたびに done 済みの機体が running へ戻ってしまう。
    a.add_argument("--status", default=None, choices=STATUSES,
                   help=t("initial state (running when omitted; kept as it is "
                          "when the unit already exists)"))
    add_project_arg(a)
    a.set_defaults(func=cmd_add)

    d = sub.add_parser("done",
                       help=t("copy the measured values in once the report arrives"))
    d.add_argument("--id", required=True)
    d.add_argument("--sec", type=non_negative_int, default=None,
                   help=t("seconds taken (computed from the start time when omitted)"))
    d.add_argument("--tokens", type=non_negative_int, default=None,
                   help=t("token count (leave it out if you did not get one)"))
    d.add_argument("--tools", type=non_negative_int, default=None,
                   help=t("tool-call count (leave it out if you did not get one)"))
    d.add_argument("--headline", default="", help=t("one-line summary of the result"))
    add_project_arg(d)
    d.set_defaults(func=cmd_done)

    f = sub.add_parser("finish",
                       help=t("close the mission once everyone has finished"))
    f.add_argument("--headline", default="",
                   help=t("one-line summary of the whole mission"))
    add_project_arg(f)
    f.set_defaults(func=cmd_finish)

    lg = sub.add_parser("log", help=t("add one line of commentary"))
    lg.add_argument("--who", default=t("Command"))
    lg.add_argument("--text", required=True)
    add_project_arg(lg)
    lg.set_defaults(func=cmd_log)

    st = sub.add_parser("status", help=t("show the current state"))
    add_project_arg(st)
    st.set_defaults(func=cmd_status)

    pj = sub.add_parser("projects", help=t("list the registered projects"))
    add_project_arg(pj)
    pj.set_defaults(func=cmd_projects)

    hi = sub.add_parser("history",
                        help=t("list this project's past missions"))
    add_project_arg(hi)
    hi.set_defaults(func=cmd_history)

    dm = sub.add_parser("demo", help=t("fill in data for testing the display"))
    add_project_arg(dm)
    dm.set_defaults(func=cmd_demo)

    rs = sub.add_parser(
        "reset",
        help=t("put the current state.json back to standby (past records in history/ "
               "are kept; use remove to delete the records themselves)"),
    )
    rs.add_argument("--purge", action="store_true",
                    help=t("also delete the grandchild self-report files"))
    add_project_arg(rs)
    rs.set_defaults(func=cmd_reset)

    rm = sub.add_parser(
        "remove", aliases=["rm"],
        help=t("delete the whole record of the project (past records in history/ go "
               "too; by default they are moved to the trash)"),
    )
    rm.add_argument("--yes", "-y", action="store_true",
                    help=t("skip the confirmation"))
    rm.add_argument("--force", action="store_true",
                    help=t("delete for good instead of moving to the trash"))
    add_project_arg(rm)
    rm.set_defaults(func=cmd_remove)

    ln = sub.add_parser("lang", help=t("show or set the language of these messages"))
    ln.add_argument("code", nargs="?", default=None,
                    help=t("en / ja / zh / ko (omit to show the current setting)"))
    ln.set_defaults(func=cmd_lang)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
