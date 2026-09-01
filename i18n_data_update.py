#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""update_state.py（状態更新CLI）の翻訳表。

**鍵は英語の原文そのもの**（i18n.py の t() を参照）。原文を書き換えたら、ここの
鍵も一緒に書き換えること。合っていない鍵は「訳が無い」と見なされて英語で出る。

i18n.py は i18n_data → i18n_data_update → i18n_data_install の順に読み込んで合成する。
**同じ原文を i18n_data.py と重複させないこと**（先に読んだほうが残るので、ここに
書いても効かない鍵が生まれて紛らわしい）。

抜けを数えるには:

    python check_i18n.py

`{name}` の差し込みは呼び手が .format() で行う。**訳文でも同じ名前を残すこと。**
語順は言語ごとに変えてよいが、名前を変えたり落としたりすると KeyError になる。

外部ライブラリは使いません（Python 標準ライブラリのみ）。
"""

from __future__ import annotations

CATALOG: dict[str, dict[str, str]] = {}

# ============================================================ 日本語
CATALOG["ja"] = {
    # ---- 共通の補助（die / project_label / read_state）
    "Error: {msg}": "エラー: {msg}",
    "{name} ({slug}{where})": "{name}（{slug}{where}）",
    "This project has no state.json ({err}).":
        "このプロジェクトの state.json がありません（{err}）。",
    "      Target: {name}": "      対象: {name}",
    '      Run  update_state.py start --title "..."  first.':
        '      先に  update_state.py start --title "..."  を実行してください。',

    # ---- done: 機体が現在のミッションに居ないとき
    "{id} is not in state.json. Run add for it first.":
        "{id} は state.json に存在しません。先に add してください。",
    '{id} is not in the current mission "{title}".\n'
    '      The same ID is in the recent history "{lost}" (history/{run_id}/), so\n'
    "      that one was probably pushed out by another start. A record that has\n"
    "      been pushed out can no longer be written to (it cannot be marked\n"
    "      finished afterwards).":
        "{id} は現在のミッション「{title}」に居ません。\n"
        "      直近の履歴「{lost}」（history/{run_id}/）に同じ ID が居るので、\n"
        "      そちらは別の start に押し出されたと考えられます。押し出された記録には\n"
        "      もう書き込めません（あとから完了にはできません）。",
    '      Running add here registers it as a unit of "{title}", so the two\n'
    "      records get mixed together. When you run two missions in parallel in\n"
    "      the same directory, put --project <a unique name> on all of\n"
    "      start / add / done / finish so the records are kept apart.":
        "      ここで add すると「{title}」の機体として登録され、2本の記録が混ざります。\n"
        "      同じディレクトリで2本を並行するときは、start / add / done / finish の\n"
        "      すべてに --project <一意な名前> を付けて記録先を分けてください。",

    # ---- start
    "Command": "指令塔",
    "overall control": "全体統括",
    "Mission started — {title}": "ミッション開始 — {title}",
    "Mission started: {title}": "ミッションを開始しました: {title}",
    "  Target project: {name}": "  対象プロジェクト: {name}",
    "  Archived the previous mission into history: history/{run_id}/":
        "  前のミッションを履歴へ退避しました: history/{run_id}/",
    "    You can list them with  update_state.py history":
        "    一覧は  update_state.py history  で見られます。",
    '  ⚠️  All {n} units of the archived "{title}" were back, '
    "but finish was never run.":
        "  ⚠️  退避した「{title}」は {n} 体すべて帰還済みでしたが、finish が打たれていません。",
    '      It stays in the history as "Unfinished" '
    "(it cannot be marked finished afterwards).":
        "      履歴では「未完」として残ります（あとから完了にはできません）。",
    '  ⚠️  The archived "{title}" ended while still running '
    "(there are units that never returned).":
        "  ⚠️  退避した「{title}」は稼働中のまま終わりました（未帰還の機体があります）。",
    '      It stays in the history as "Unfinished".':
        "      履歴では「未完」として残ります。",
    "      If you meant to run two missions at once, there are not enough\n"
    "      record destinations. When running them in parallel in the same\n"
    "      directory, split them with  start --project <a unique name>\n"
    "      (put the same --project on add / done / finish too).":
        "      2本を同時に走らせるつもりだった場合、記録先が足りていません。\n"
        "      同じディレクトリで並行するときは\n"
        "      start --project <一意な名前> で分けてください\n"
        "      （add / done / finish にも同じ --project を付ける）。",
    "  Moved {n} old records over the limit of {keep} to the trash: {list}":
        "  保持件数（{keep} 件）を超えた古い記録 {n} 件をゴミ箱へ移しました: {list}",
    "  Cleared away {n} grandchild self-report files from the previous mission.":
        "  前のミッションの孫の自己申告ファイルを {n} 件片付けました。",

    # ---- add
    "Warning: the parent {id} is not in state.json. "
    "It will be shown in the first column.":
        "警告: 親 {id} が state.json に見つかりません。1列目として表示します。",
    "Warning: {id} is already registered. Overwriting it.":
        "警告: {id} は既に登録済みです。上書きします。",
    "{name} ({id}) is standing by": "{name}（{id}）待機開始",
    "{name} ({id}) was born — {mission}": "{name}（{id}）誕生 — {mission}",
    "no mission recorded": "任務未記載",
    "Registered: {id} ({name} / {status} / column {gen})":
        "登録しました: {id}（{name} / {status} / {gen}列目）",

    # ---- done
    "elapsed {time}": "所要 {time}",
    "{n} tokens": "{n} トークン",
    "{n} tool calls": "ツール {n} 回",
    "Back home — {headline} ({detail})": "帰還 — {headline}（{detail}）",
    "no report": "報告なし",
    "Marked done: {id} ({detail})": "完了にしました: {id}（{detail}）",
    "  * Values you left out were measured from Claude Code's own records ({id}).":
        '  * 省略された数値は、Claude Code 自身の記録から実測で補いました（{id}）。',
    '  * No token count was given, so it is null (the screen shows "—").':
        "  ※ トークン数は未指定のため null（画面では「—」表示）",
    '  * No tool-call count was given, so it is null (the screen shows "—").':
        "  ※ ツール使用回数は未指定のため null（画面では「—」表示）",
    "  ★ That is all {n} units back home. The mission has not been closed yet.":
        "  ★ これで {n} 体すべてが帰還しました。ミッションはまだ締められていません。",
    '     python update_state.py finish '
    '--headline "<one-line summary of the whole mission>"':
        '     python update_state.py finish --headline "<全体の一行要約>"',

    # ---- finish
    "Warning: {n} agents have not finished ({ids}). "
    "Recording the mission as done anyway.":
        "警告: 未完了のエージェントが {n} 体います（{ids}）。そのまま完了として記録します。",
    "all units back home": "全機帰還",
    "ended without ever deploying": "未出動のまま終了",
    "Mission complete — {n} units / {tokens} tokens in total / elapsed {time}":
        "ミッション完了 — 機体 {n} / 合計 {tokens} トークン / 所要 {time}",
    "Marked the mission as done.": "ミッションを完了にしました。",
    "  Target project": "  対象プロジェクト",
    "  Units": "  機体数",
    "  Total tokens": "  合計トークン",
    " (nothing measured)": "（実測値なし）",
    "  Elapsed": "  所要時間",

    # ---- log
    "Added a log line. ({name})": "ログを追加しました。（{name}）",

    # ---- status
    " (all units back, not closed)": "（全機帰還済み・未締め）",
    "Project": "プロジェクト",
    "Mission": "ミッション",
    "Phase": "フェーズ",
    "Started": "開始",
    "Updated": "更新",
    "Summary": "サマリー",
    "{n} units / {tokens} tokens in total / elapsed {time}":
        "機体 {n} / 合計 {tokens} トークン / 所要 {time}",
    "Gen": "世代",
    "Status": "状態",
    "Name": "名前",
    "Elapsed": "所要",
    "Tokens": "トークン",
    "Tools": "ツール",
    "awaiting report": "報告待ち",
    "  Grandchild self-report files: {n} ({path})":
        "  孫の自己申告ファイル: {n} 件（{path}）",
    "  Log: {n} lines (latest: {text})": "  ログ: {n} 行（最新: {text}）",
    " ({time} since the last one came back)": "（最後の帰還から {time}）",
    "  ★ All {n} units are back, but the mission has not been closed{since}.":
        "  ★ {n} 体すべて帰還済みですが、ミッションが締められていません{since}。",

    # ---- projects
    "Mission storage: {path}": "ミッション保存先: {path}",
    "Project for this folder: {slug}": "カレントディレクトリの対象: {slug}",
    "  There are no records yet (the screen is on standby).":
        "  記録はまだありません（画面は待機中）。",
    '  In your working directory, run  update_state.py start --title "..."':
        '  作業するディレクトリで  update_state.py start --title "..."  を実行してください。',
    "Progress": "進捗",
    "Last updated": "最終更新",
    "Slug": "スラッグ",
    "  ★ = on screen, and stays there until the next start":
        "  ★ = 画面に映っていて、かつ次に start するまで残り続けるチーム",
    "  ● = on screen (running, or the other half of a parallel run)":
        "  ● = 画面に映っているチーム（稼働中、または並列で走っていた片割れ）",
    "  → = the target derived from the current directory":
        "  → = カレントディレクトリから自動判定される対象",
    "  Only ★ and ● appear on the screen. The unmarked ones are only kept as\n"
    "  records and never appear. Delete the ones you do not need with  "
    "update_state.py remove":
        "  画面に出るのは ★ と ● だけです。印の無いものは記録として置いてあるだけで\n"
        "  画面には出ません。要らないものは  update_state.py remove  で消せます。",

    # ---- history
    "Could not read the history: {err}": "履歴を読めませんでした: {err}",
    "Target project:": "対象プロジェクト:",
    "History folder:": "履歴の保存先:",
    "Records kept:": "保持件数:",
    "Current mission:": "現在のミッション:",
    "{n} records (change with the environment variable {var})":
        "{n} 件（環境変数 {var} で変更）",
    "0 records — history is turned off (environment variable {var})":
        "0 件 — 履歴を残さない設定です（環境変数 {var}）",
    "{title} ({phase})": "{title}（{phase}）",
    "  There are no past records yet.": "  過去の記録はまだありません。",
    "  The next time you run start, the current record is archived into\n"
    "  history/ and lines up here.":
        "  次に start したとき、いまの記録が history/ に退避されて\n"
        "  ここに並びます。",
    "Finished": "終了",
    "Units": "機体",
    "  {n} records (newest first). Once the limit is reached, "
    "the oldest go to the trash.":
        "  {n} 件（新しい順）。上限に達すると古いものからゴミ箱へ移ります。",
    "  Units = the number registered in state.json (Command excluded).\n"
    "  Grandchild self-reports are not counted.":
        "  機体 = state.json に登録された数（指令塔を除く）。\n"
        "  孫の自己申告は含みません。",

    # ---- demo（表示テスト用のダミーデータ）
    "display test (dummy data)": "表示テスト（ダミーデータ）",
    "Scout A": "偵察A",
    "Scout B": "偵察B",
    "Scout C": "偵察C",
    "Analysis A-1": "分析A-1",
    "Sweep A-1-x": "走査A-1-x",
    "find every API call site under src/": "src/ 配下のAPI呼び出し箇所を洗い出す",
    "trace the dependencies of the test code": "テストコードの依存関係を追跡する",
    "check the documentation for gaps (waiting to deploy)":
        "ドキュメントの記述漏れを確認する（出動待ち）",
    "classify the 23 sites found by impact": "特定された23件を影響度で分類する",
    "cross-check the classification and drop duplicates (grandchild self-report)":
        "分類結果を突き合わせて重複を除く（孫の自己申告）",
    "pinned down 23 call sites across 7 files": "呼び出し箇所を7ファイル23件で特定",
    "registered by self-report": "自己申告で登録",
    "Wrote display-test data.": "表示テスト用データを書き込みました。",
    "  Standby, running, awaiting report, done, grandchild self-reports and\n"
    "  missing measured values (—) all appear on the screen.":
        "  待機中・稼働中・報告待ち・完了・孫の自己申告・実測値なし（—）が\n"
        "  すべて画面に出ます。",

    # ---- reset
    "Reset state.json (standby). Target: {name}":
        "state.json を初期化しました（待機中）。対象: {name}",
    "* The screen keeps this team selected but returns to the standby screen.":
        "※ 画面はこのチームを映したまま待機画面に戻ります。",
    "* The current record is emptied without being archived (only start archives it).":
        "※ いまの記録は履歴へ退避されずに空になります（履歴へ残すのは start だけです）。",
    "* The {n} past records in history/ are left untouched (list them with history).":
        "※ history/ の過去の記録 {n} 件はそのまま残っています（一覧は history）。",
    "* To delete the whole record folder (past records included), use remove.":
        "※ 記録のフォルダごと（過去の記録も含めて）消すなら remove を使ってください。",
    "* The grandchild self-report files are still there. Add --purge to delete them.":
        "※ 孫の自己申告ファイルは残っています。消すには --purge を付けてください。",
    "Deleted {n} grandchild self-report files.":
        "孫の自己申告ファイルを {n} 件削除しました。",

    # ---- remove
    "There is no record for this project (missions/{slug}/ is not there).":
        "このプロジェクトの記録はありません（missions/{slug}/ が無い）。",
    "      You can check the list with  update_state.py projects":
        "      一覧は  update_state.py projects  で確認できます。",
    "Warning: {n} agents are still running ({ids}).":
        "警告: 稼働中のエージェントが {n} 体います（{ids}）。",
    "This environment cannot ask for confirmation. Add --yes if you mean to delete it.":
        "確認を取れない環境です。意図して消す場合は --yes を付けてください。",
    "About to delete the records of {name}. Are you sure? [y/N]: ":
        "{name} の記録を削除します。よろしいですか？ [y/N]: ",
    "Cancelled.": "中止しました。",
    "Failed to delete: {err}": "削除に失敗しました: {err}",
    "Deleted for good: {name}": "完全に削除しました: {name}",
    "Deleted (moved to the trash): {name}": "削除しました（ゴミ箱へ移動）: {name}",
    "  Moved to": "  移動先",
    "  To undo": "  戻すには",
    "move this folder back to {path}": "このフォルダを {path} に戻してください。",

    # ---- 引数定義（--help に出る文）
    "give an integer (got: {value})": "整数を指定してください（受け取った値: {value}）",
    "give an integer of 0 or more (got: {value})":
        "0以上の整数を指定してください（受け取った値: {value}）",
    "target project (derived from the current directory when omitted)":
        "対象プロジェクト（省略時はカレントディレクトリから自動判定）",
    "Subagent Dashboard — the state-update CLI "
    "(the target project is derived from the current directory)":
        "Subagent Dashboard — 状態更新CLI"
        "（対象プロジェクトはカレントディレクトリから自動判定）",
    "Leave out any value you could not measure (--tokens / --tools). "
    "Never fill in an estimate.":
        "実測できなかった値（--tokens / --tools）は省略してください。推定値を入れないこと。",
    "command": "コマンド",
    "start a mission (the records so far move to history/, "
    "where history can look them up)":
        "ミッションを開始する（それまでの記録は history/ へ退避され、history で見返せる）",
    "name of the mission": "ミッション名",
    "model ID of the command post": "指令塔のモデルID",
    "register a subagent right after starting it":
        "サブエージェントを起動した直後に登録する",
    "identifier (for example SCOUT-A)": "識別子（例: SCOUT-A）",
    "name shown on the screen (same as the ID when omitted)":
        "画面に出る名前（省略時はIDと同じ）",
    "ID of the parent (the command post when omitted)": "親のID（省略時は指令塔）",
    "model ID that was used": "使用したモデルID",
    "what the task is": "任務内容",
    "copy the measured values in once the report arrives":
        "完了通知を受け取ったら実測値を転記する",
    "seconds taken (computed from the start time when omitted)":
        "所要秒（省略時は起動時刻から算出）",
    "token count (leave it out if you did not get one)":
        "トークン数（未取得なら省略）",
    "tool-call count (leave it out if you did not get one)":
        "ツール使用回数（未取得なら省略）",
    "one-line summary of the result": "結果の一行要約",
    "close the mission once everyone has finished":
        "全員完了したらミッションを完了にする",
    "one-line summary of the whole mission": "ミッション全体の一行要約",
    "add one line of commentary": "実況を1行追加する",
    "show the current state": "現在の状態を表示する",
    "list the registered projects": "登録済みプロジェクトを一覧表示する",
    "list this project's past missions":
        "このプロジェクトの過去のミッションを一覧表示する",
    "fill in data for testing the display": "表示テスト用データを入れる",
    "put the current state.json back to standby (past records in history/ "
    "are kept; use remove to delete the records themselves)":
        "現在の state.json を待機中に戻す"
        "（history/ の過去の記録はそのまま。記録ごと消すなら remove）",
    "also delete the grandchild self-report files": "孫の自己申告ファイルも削除する",
    "delete the whole record of the project (past records in history/ go "
    "too; by default they are moved to the trash)":
        "プロジェクトの記録を丸ごと削除する"
        "（history/ の過去の記録も一緒に。既定はゴミ箱へ移動）",
    "skip the confirmation": "確認を省略する",
    "delete for good instead of moving to the trash":
        "ゴミ箱へ移さず完全に削除する",
}

# ============================================================ 中文（简体）
CATALOG["zh"] = {
    # ---- 共通の補助（die / project_label / read_state）
    "Error: {msg}": "错误: {msg}",
    "{name} ({slug}{where})": "{name}（{slug}{where}）",
    "This project has no state.json ({err}).":
        "本项目没有 state.json（{err}）。",
    "      Target: {name}": "      目标: {name}",
    '      Run  update_state.py start --title "..."  first.':
        '      请先执行  update_state.py start --title "..."',

    # ---- done: 機体が現在のミッションに居ないとき
    "{id} is not in state.json. Run add for it first.":
        "{id} 不在 state.json 中。请先执行 add。",
    '{id} is not in the current mission "{title}".\n'
    '      The same ID is in the recent history "{lost}" (history/{run_id}/), so\n'
    "      that one was probably pushed out by another start. A record that has\n"
    "      been pushed out can no longer be written to (it cannot be marked\n"
    "      finished afterwards).":
        "{id} 不在当前任务「{title}」中。\n"
        "      最近的历史「{lost}」（history/{run_id}/）中有相同的 ID，\n"
        "      因此那一个应该是被别的 start 挤出去了。被挤出的记录\n"
        "      已经无法写入（无法事后改成完成）。",
    '      Running add here registers it as a unit of "{title}", so the two\n'
    "      records get mixed together. When you run two missions in parallel in\n"
    "      the same directory, put --project <a unique name> on all of\n"
    "      start / add / done / finish so the records are kept apart.":
        "      在这里 add 会把它登记为「{title}」的单元，两份记录就会混在一起。\n"
        "      要在同一目录下并行跑两个时，请在 start / add / done / finish 的\n"
        "      全部命令上加 --project <唯一的名称> 来分开记录位置。",

    # ---- start
    "Command": "指挥塔",
    "overall control": "全局统筹",
    "Mission started — {title}": "任务开始 — {title}",
    "Mission started: {title}": "已开始任务: {title}",
    "  Target project: {name}": "  目标项目: {name}",
    "  Archived the previous mission into history: history/{run_id}/":
        "  已把上一个任务转存到历史: history/{run_id}/",
    "    You can list them with  update_state.py history":
        "    可以用  update_state.py history  查看列表。",
    '  ⚠️  All {n} units of the archived "{title}" were back, '
    "but finish was never run.":
        "  ⚠️  转存的「{title}」中 {n} 个单元已全部归队，但没有敲 finish。",
    '      It stays in the history as "Unfinished" '
    "(it cannot be marked finished afterwards).":
        "      在历史中会作为「未完成」留下（无法事后改成完成）。",
    '  ⚠️  The archived "{title}" ended while still running '
    "(there are units that never returned).":
        "  ⚠️  转存的「{title}」在运行中的状态下结束了（有尚未归队的单元）。",
    '      It stays in the history as "Unfinished".':
        "      在历史中会作为「未完成」留下。",
    "      If you meant to run two missions at once, there are not enough\n"
    "      record destinations. When running them in parallel in the same\n"
    "      directory, split them with  start --project <a unique name>\n"
    "      (put the same --project on add / done / finish too).":
        "      如果本来打算同时跑两个，那就是记录位置不够。\n"
        "      要在同一目录下并行时，请用\n"
        "      start --project <唯一的名称> 分开\n"
        "      （add / done / finish 也要加同样的 --project）。",
    "  Moved {n} old records over the limit of {keep} to the trash: {list}":
        "  已把超出保留条数（{keep} 条）的 {n} 条旧记录移入回收站: {list}",
    "  Cleared away {n} grandchild self-report files from the previous mission.":
        "  已清理上一个任务的孙代理自行申报文件 {n} 个。",

    # ---- add
    "Warning: the parent {id} is not in state.json. "
    "It will be shown in the first column.":
        "警告: 在 state.json 中找不到父级 {id}。将显示在第 1 列。",
    "Warning: {id} is already registered. Overwriting it.":
        "警告: {id} 已经登记过了。将覆盖它。",
    "{name} ({id}) is standing by": "{name}（{id}）开始待机",
    "{name} ({id}) was born — {mission}": "{name}（{id}）诞生 — {mission}",
    "no mission recorded": "任务内容未记载",
    "Registered: {id} ({name} / {status} / column {gen})":
        "已登记: {id}（{name} / {status} / 第 {gen} 列）",

    # ---- done
    "elapsed {time}": "耗时 {time}",
    "{n} tokens": "{n} Token",
    "{n} tool calls": "工具 {n} 次",
    "Back home — {headline} ({detail})": "归队 — {headline}（{detail}）",
    "no report": "无报告",
    "Marked done: {id} ({detail})": "已置为完成: {id}（{detail}）",
    "  * Values you left out were measured from Claude Code's own records ({id}).":
        '  * 省略的数值已从 Claude Code 自身的记录中实测补全（{id}）。',
    '  * No token count was given, so it is null (the screen shows "—").':
        "  ※ 未指定 Token 数，因此为 null（画面显示「—」）",
    '  * No tool-call count was given, so it is null (the screen shows "—").':
        "  ※ 未指定工具使用次数，因此为 null（画面显示「—」）",
    "  ★ That is all {n} units back home. The mission has not been closed yet.":
        "  ★ 至此 {n} 个单元已全部归队。任务还没有收尾。",
    '     python update_state.py finish '
    '--headline "<one-line summary of the whole mission>"':
        '     python update_state.py finish --headline "<整体的一行摘要>"',

    # ---- finish
    "Warning: {n} agents have not finished ({ids}). "
    "Recording the mission as done anyway.":
        "警告: 有 {n} 个代理尚未完成（{ids}）。仍将按完成记录。",
    "all units back home": "全员归队",
    "ended without ever deploying": "未出动即结束",
    "Mission complete — {n} units / {tokens} tokens in total / elapsed {time}":
        "任务完成 — 单元 {n} / 合计 {tokens} Token / 耗时 {time}",
    "Marked the mission as done.": "已把任务置为完成。",
    "  Target project": "  目标项目",
    "  Units": "  单元数",
    "  Total tokens": "  合计 Token",
    " (nothing measured)": "（无实测值）",
    "  Elapsed": "  耗时",

    # ---- log
    "Added a log line. ({name})": "已追加日志。（{name}）",

    # ---- status
    " (all units back, not closed)": "（全部归队·未收尾）",
    "Project": "项目",
    "Mission": "任务",
    "Phase": "阶段",
    "Started": "开始",
    "Updated": "更新",
    "Summary": "汇总",
    "{n} units / {tokens} tokens in total / elapsed {time}":
        "单元 {n} / 合计 {tokens} Token / 耗时 {time}",
    "Gen": "世代",
    "Status": "状态",
    "Name": "名称",
    "Elapsed": "耗时",
    "Tokens": "Token",
    "Tools": "工具",
    "awaiting report": "等待回报",
    "  Grandchild self-report files: {n} ({path})":
        "  孙代理自行申报文件: {n} 个（{path}）",
    "  Log: {n} lines (latest: {text})": "  日志: {n} 行（最新: {text}）",
    " ({time} since the last one came back)": "（距最后一次归队 {time}）",
    "  ★ All {n} units are back, but the mission has not been closed{since}.":
        "  ★ {n} 个单元已全部归队，但任务还没有收尾{since}。",

    # ---- projects
    "Mission storage: {path}": "任务保存位置: {path}",
    "Project for this folder: {slug}": "当前目录对应的项目: {slug}",
    "  There are no records yet (the screen is on standby).":
        "  还没有任何记录（画面处于待机中）。",
    '  In your working directory, run  update_state.py start --title "..."':
        '  请在作业目录中执行  update_state.py start --title "..."',
    "Progress": "进度",
    "Last updated": "最后更新",
    "Slug": "slug",
    "  ★ = on screen, and stays there until the next start":
        "  ★ = 显示在画面上，并且会一直留到下一次 start 的小队",
    "  ● = on screen (running, or the other half of a parallel run)":
        "  ● = 显示在画面上的小队（运行中，或并行跑的另一半）",
    "  → = the target derived from the current directory":
        "  → = 由当前目录自动判定出的对象",
    "  Only ★ and ● appear on the screen. The unmarked ones are only kept as\n"
    "  records and never appear. Delete the ones you do not need with  "
    "update_state.py remove":
        "  会出现在画面上的只有 ★ 和 ●。没有标记的只是作为记录放着，\n"
        "  不会出现在画面上。不需要的可以用  update_state.py remove  删除。",

    # ---- history
    "Could not read the history: {err}": "无法读取历史: {err}",
    "Target project:": "目标项目:",
    "History folder:": "历史保存位置:",
    "Records kept:": "保留条数:",
    "Current mission:": "当前任务:",
    "{n} records (change with the environment variable {var})":
        "{n} 条（用环境变量 {var} 修改）",
    "0 records — history is turned off (environment variable {var})":
        "0 条 — 设置为不保留历史（环境变量 {var}）",
    "{title} ({phase})": "{title}（{phase}）",
    "  There are no past records yet.": "  还没有过去的记录。",
    "  The next time you run start, the current record is archived into\n"
    "  history/ and lines up here.":
        "  下一次 start 时，当前的记录会转存到 history/\n"
        "  并排列在这里。",
    "Finished": "结束",
    "Units": "单元",
    "  {n} records (newest first). Once the limit is reached, "
    "the oldest go to the trash.":
        "  {n} 条（由新到旧）。达到上限后从旧的开始移入回收站。",
    "  Units = the number registered in state.json (Command excluded).\n"
    "  Grandchild self-reports are not counted.":
        "  单元 = 在 state.json 中登记的数量（不含指挥塔）。\n"
        "  不包含孙代理的自行申报。",

    # ---- demo（表示テスト用のダミーデータ）
    "display test (dummy data)": "显示测试（示例数据）",
    "Scout A": "侦察A",
    "Scout B": "侦察B",
    "Scout C": "侦察C",
    "Analysis A-1": "分析A-1",
    "Sweep A-1-x": "扫描A-1-x",
    "find every API call site under src/": "梳理 src/ 下的 API 调用位置",
    "trace the dependencies of the test code": "追踪测试代码的依赖关系",
    "check the documentation for gaps (waiting to deploy)":
        "确认文档中的遗漏之处（等待出动）",
    "classify the 23 sites found by impact": "把找出的 23 处按影响度分类",
    "cross-check the classification and drop duplicates (grandchild self-report)":
        "比对分类结果并去除重复（孙代理自行申报）",
    "pinned down 23 call sites across 7 files": "在 7 个文件中锁定 23 处调用位置",
    "registered by self-report": "以自行申报登记",
    "Wrote display-test data.": "已写入用于显示测试的数据。",
    "  Standby, running, awaiting report, done, grandchild self-reports and\n"
    "  missing measured values (—) all appear on the screen.":
        "  待机中·运行中·等待回报·已完成·孙代理自行申报·无实测值（—）\n"
        "  全都会出现在画面上。",

    # ---- reset
    "Reset state.json (standby). Target: {name}":
        "已初始化 state.json（待机中）。目标: {name}",
    "* The screen keeps this team selected but returns to the standby screen.":
        "※ 画面仍选中这支小队，但会回到待机画面。",
    "* The current record is emptied without being archived (only start archives it).":
        "※ 当前的记录不会转存到历史，而是直接清空（转存到历史的只有 start）。",
    "* The {n} past records in history/ are left untouched (list them with history).":
        "※ history/ 中过去的 {n} 条记录原样保留（用 history 查看列表）。",
    "* To delete the whole record folder (past records included), use remove.":
        "※ 若要连记录文件夹一起（包括过去的记录）删除，请用 remove。",
    "* The grandchild self-report files are still there. Add --purge to delete them.":
        "※ 孙代理的自行申报文件仍然保留。要删除请加 --purge。",
    "Deleted {n} grandchild self-report files.":
        "已删除孙代理自行申报文件 {n} 个。",

    # ---- remove
    "There is no record for this project (missions/{slug}/ is not there).":
        "本项目没有记录（missions/{slug}/ 不存在）。",
    "      You can check the list with  update_state.py projects":
        "      可以用  update_state.py projects  确认列表。",
    "Warning: {n} agents are still running ({ids}).":
        "警告: 有 {n} 个代理正在运行中（{ids}）。",
    "This environment cannot ask for confirmation. Add --yes if you mean to delete it.":
        "当前环境无法进行确认。若确实要删除，请加 --yes。",
    "About to delete the records of {name}. Are you sure? [y/N]: ":
        "即将删除 {name} 的记录。确定吗？ [y/N]: ",
    "Cancelled.": "已中止。",
    "Failed to delete: {err}": "删除失败: {err}",
    "Deleted for good: {name}": "已彻底删除: {name}",
    "Deleted (moved to the trash): {name}": "已删除（移入回收站）: {name}",
    "  Moved to": "  移动到",
    "  To undo": "  恢复",
    "move this folder back to {path}": "把这个文件夹移回 {path} 即可。",

    # ---- 引数定義（--help に出る文）
    "give an integer (got: {value})": "请指定整数（收到的值: {value}）",
    "give an integer of 0 or more (got: {value})":
        "请指定 0 以上的整数（收到的值: {value}）",
    "target project (derived from the current directory when omitted)":
        "目标项目（省略时由当前目录自动判定）",
    "Subagent Dashboard — the state-update CLI "
    "(the target project is derived from the current directory)":
        "Subagent Dashboard — 状态更新 CLI"
        "（目标项目由当前目录自动判定）",
    "Leave out any value you could not measure (--tokens / --tools). "
    "Never fill in an estimate.":
        "没能实测到的值（--tokens / --tools）请省略。不要填入估计值。",
    "command": "命令",
    "start a mission (the records so far move to history/, "
    "where history can look them up)":
        "开始任务（在此之前的记录会转存到 history/，可用 history 回看）",
    "name of the mission": "任务名称",
    "model ID of the command post": "指挥塔的模型 ID",
    "register a subagent right after starting it":
        "在启动子代理之后立即登记",
    "identifier (for example SCOUT-A)": "标识符（例: SCOUT-A）",
    "name shown on the screen (same as the ID when omitted)":
        "显示在画面上的名称（省略时与 ID 相同）",
    "ID of the parent (the command post when omitted)": "父级的 ID（省略时为指挥塔）",
    "model ID that was used": "使用的模型 ID",
    "what the task is": "任务内容",
    "copy the measured values in once the report arrives":
        "收到完成通知后把实测值转记进来",
    "seconds taken (computed from the start time when omitted)":
        "耗时秒数（省略时由启动时刻算出）",
    "token count (leave it out if you did not get one)":
        "Token 数（未取得就省略）",
    "tool-call count (leave it out if you did not get one)":
        "工具使用次数（未取得就省略）",
    "one-line summary of the result": "结果的一行摘要",
    "close the mission once everyone has finished":
        "全员完成后把任务置为完成",
    "one-line summary of the whole mission": "任务整体的一行摘要",
    "add one line of commentary": "追加一行实况",
    "show the current state": "显示当前状态",
    "list the registered projects": "列出已注册的项目",
    "list this project's past missions":
        "列出本项目过去的任务",
    "fill in data for testing the display": "写入用于显示测试的数据",
    "put the current state.json back to standby (past records in history/ "
    "are kept; use remove to delete the records themselves)":
        "把当前的 state.json 退回待机中"
        "（history/ 中过去的记录保持原样。要连记录一起删除请用 remove）",
    "also delete the grandchild self-report files": "同时删除孙代理的自行申报文件",
    "delete the whole record of the project (past records in history/ go "
    "too; by default they are moved to the trash)":
        "整个删除项目的记录"
        "（history/ 中过去的记录也一并删除。默认移入回收站）",
    "skip the confirmation": "省略确认",
    "delete for good instead of moving to the trash":
        "不移入回收站而是彻底删除",
}

# ============================================================ 한국어
CATALOG["ko"] = {
    # ---- 共通の補助（die / project_label / read_state）
    "Error: {msg}": "오류: {msg}",
    "{name} ({slug}{where})": "{name} ({slug}{where})",
    "This project has no state.json ({err}).":
        "이 프로젝트에는 state.json 이 없습니다 ({err}).",
    "      Target: {name}": "      대상: {name}",
    '      Run  update_state.py start --title "..."  first.':
        '      먼저  update_state.py start --title "..."  를 실행하세요.',

    # ---- done: 機体が現在のミッションに居ないとき
    "{id} is not in state.json. Run add for it first.":
        "{id} 은(는) state.json 에 없습니다. 먼저 add 하세요.",
    '{id} is not in the current mission "{title}".\n'
    '      The same ID is in the recent history "{lost}" (history/{run_id}/), so\n'
    "      that one was probably pushed out by another start. A record that has\n"
    "      been pushed out can no longer be written to (it cannot be marked\n"
    "      finished afterwards).":
        "{id} 은(는) 현재 미션 「{title}」에 없습니다.\n"
        "      최근 이력 「{lost}」(history/{run_id}/) 에 같은 ID 가 있으므로,\n"
        "      그쪽은 다른 start 에 밀려난 것으로 보입니다. 밀려난 기록에는\n"
        "      더 이상 쓸 수 없습니다 (나중에 완료로 만들 수 없습니다).",
    '      Running add here registers it as a unit of "{title}", so the two\n'
    "      records get mixed together. When you run two missions in parallel in\n"
    "      the same directory, put --project <a unique name> on all of\n"
    "      start / add / done / finish so the records are kept apart.":
        "      여기서 add 하면 「{title}」의 유닛으로 등록되어 두 기록이 섞입니다.\n"
        "      같은 디렉터리에서 두 개를 병렬로 돌릴 때는 start / add / done / finish\n"
        "      전부에 --project <고유한 이름> 을 붙여 기록 위치를 나누세요.",

    # ---- start
    "Command": "지휘탑",
    "overall control": "전체 총괄",
    "Mission started — {title}": "미션 시작 — {title}",
    "Mission started: {title}": "미션을 시작했습니다: {title}",
    "  Target project: {name}": "  대상 프로젝트: {name}",
    "  Archived the previous mission into history: history/{run_id}/":
        "  이전 미션을 이력으로 옮겼습니다: history/{run_id}/",
    "    You can list them with  update_state.py history":
        "    목록은  update_state.py history  로 볼 수 있습니다.",
    '  ⚠️  All {n} units of the archived "{title}" were back, '
    "but finish was never run.":
        "  ⚠️  옮겨진 「{title}」은 {n} 대 전원 귀환 완료였지만 finish 가 실행되지 않았습니다.",
    '      It stays in the history as "Unfinished" '
    "(it cannot be marked finished afterwards).":
        "      이력에는 「미완」으로 남습니다 (나중에 완료로 만들 수 없습니다).",
    '  ⚠️  The archived "{title}" ended while still running '
    "(there are units that never returned).":
        "  ⚠️  옮겨진 「{title}」은 가동 중인 채로 끝났습니다 (귀환하지 않은 유닛이 있습니다).",
    '      It stays in the history as "Unfinished".':
        "      이력에는 「미완」으로 남습니다.",
    "      If you meant to run two missions at once, there are not enough\n"
    "      record destinations. When running them in parallel in the same\n"
    "      directory, split them with  start --project <a unique name>\n"
    "      (put the same --project on add / done / finish too).":
        "      두 개를 동시에 돌릴 생각이었다면 기록 위치가 모자랍니다.\n"
        "      같은 디렉터리에서 병렬로 돌릴 때는\n"
        "      start --project <고유한 이름> 으로 나누세요\n"
        "      (add / done / finish 에도 같은 --project 를 붙입니다).",
    "  Moved {n} old records over the limit of {keep} to the trash: {list}":
        "  보관 건수({keep} 건)를 넘은 오래된 기록 {n} 건을 휴지통으로 옮겼습니다: {list}",
    "  Cleared away {n} grandchild self-report files from the previous mission.":
        "  이전 미션의 손자 자가 보고 파일을 {n} 건 정리했습니다.",

    # ---- add
    "Warning: the parent {id} is not in state.json. "
    "It will be shown in the first column.":
        "경고: 부모 {id} 를 state.json 에서 찾을 수 없습니다. 1열째로 표시합니다.",
    "Warning: {id} is already registered. Overwriting it.":
        "경고: {id} 은(는) 이미 등록되어 있습니다. 덮어씁니다.",
    "{name} ({id}) is standing by": "{name}({id}) 대기 시작",
    "{name} ({id}) was born — {mission}": "{name}({id}) 탄생 — {mission}",
    "no mission recorded": "임무 미기재",
    "Registered: {id} ({name} / {status} / column {gen})":
        "등록했습니다: {id}({name} / {status} / {gen}열째)",

    # ---- done
    "elapsed {time}": "소요 {time}",
    "{n} tokens": "{n} 토큰",
    "{n} tool calls": "도구 {n} 회",
    "Back home — {headline} ({detail})": "귀환 — {headline}({detail})",
    "no report": "보고 없음",
    "Marked done: {id} ({detail})": "완료로 만들었습니다: {id}({detail})",
    "  * Values you left out were measured from Claude Code's own records ({id}).":
        '  * 생략된 수치는 Claude Code 자체 기록에서 실측으로 채웠습니다({id}).',
    '  * No token count was given, so it is null (the screen shows "—").':
        "  ※ 토큰 수가 지정되지 않아 null 입니다 (화면에는 「—」로 표시)",
    '  * No tool-call count was given, so it is null (the screen shows "—").':
        "  ※ 도구 사용 횟수가 지정되지 않아 null 입니다 (화면에는 「—」로 표시)",
    "  ★ That is all {n} units back home. The mission has not been closed yet.":
        "  ★ 이로써 {n} 대 전원이 귀환했습니다. 미션은 아직 마무리되지 않았습니다.",
    '     python update_state.py finish '
    '--headline "<one-line summary of the whole mission>"':
        '     python update_state.py finish --headline "<전체의 한 줄 요약>"',

    # ---- finish
    "Warning: {n} agents have not finished ({ids}). "
    "Recording the mission as done anyway.":
        "경고: 완료되지 않은 에이전트가 {n} 대 있습니다({ids}). 그대로 완료로 기록합니다.",
    "all units back home": "전원 귀환",
    "ended without ever deploying": "미출동 상태로 종료",
    "Mission complete — {n} units / {tokens} tokens in total / elapsed {time}":
        "미션 완료 — 유닛 {n} / 합계 {tokens} 토큰 / 소요 {time}",
    "Marked the mission as done.": "미션을 완료로 만들었습니다.",
    "  Target project": "  대상 프로젝트",
    "  Units": "  유닛 수",
    "  Total tokens": "  총 토큰",
    " (nothing measured)": "(실측값 없음)",
    "  Elapsed": "  소요 시간",

    # ---- log
    "Added a log line. ({name})": "로그를 추가했습니다. ({name})",

    # ---- status
    " (all units back, not closed)": "(전원 귀환 완료·미종료)",
    "Project": "프로젝트",
    "Mission": "미션",
    "Phase": "단계",
    "Started": "시작",
    "Updated": "갱신",
    "Summary": "요약",
    "{n} units / {tokens} tokens in total / elapsed {time}":
        "유닛 {n} / 합계 {tokens} 토큰 / 소요 {time}",
    "Gen": "세대",
    "Status": "상태",
    "Name": "이름",
    "Elapsed": "소요",
    "Tokens": "토큰",
    "Tools": "도구",
    "awaiting report": "보고 대기",
    "  Grandchild self-report files: {n} ({path})":
        "  손자 자가 보고 파일: {n} 건 ({path})",
    "  Log: {n} lines (latest: {text})": "  로그: {n} 행 (최신: {text})",
    " ({time} since the last one came back)": "(마지막 귀환으로부터 {time})",
    "  ★ All {n} units are back, but the mission has not been closed{since}.":
        "  ★ {n} 대 전원 귀환 완료이지만 미션이 마무리되지 않았습니다{since}.",

    # ---- projects
    "Mission storage: {path}": "미션 저장 위치: {path}",
    "Project for this folder: {slug}": "현재 디렉터리의 대상: {slug}",
    "  There are no records yet (the screen is on standby).":
        "  아직 기록이 없습니다 (화면은 대기 중).",
    '  In your working directory, run  update_state.py start --title "..."':
        '  작업할 디렉터리에서  update_state.py start --title "..."  를 실행하세요.',
    "Progress": "진척",
    "Last updated": "최종 갱신",
    "Slug": "슬러그",
    "  ★ = on screen, and stays there until the next start":
        "  ★ = 화면에 나오고 있고, 다음 start 까지 계속 남는 팀",
    "  ● = on screen (running, or the other half of a parallel run)":
        "  ● = 화면에 나오고 있는 팀 (가동 중이거나, 병렬로 돌던 다른 한쪽)",
    "  → = the target derived from the current directory":
        "  → = 현재 디렉터리에서 자동으로 판정되는 대상",
    "  Only ★ and ● appear on the screen. The unmarked ones are only kept as\n"
    "  records and never appear. Delete the ones you do not need with  "
    "update_state.py remove":
        "  화면에 나오는 것은 ★ 와 ● 뿐입니다. 표시가 없는 것은 기록으로 놓여 있을 뿐\n"
        "  화면에는 나오지 않습니다. 필요 없는 것은  update_state.py remove  로 지울 수 있습니다.",

    # ---- history
    "Could not read the history: {err}": "이력을 읽지 못했습니다: {err}",
    "Target project:": "대상 프로젝트:",
    "History folder:": "이력 저장 위치:",
    "Records kept:": "보관 건수:",
    "Current mission:": "현재 미션:",
    "{n} records (change with the environment variable {var})":
        "{n} 건 (환경 변수 {var} 로 변경)",
    "0 records — history is turned off (environment variable {var})":
        "0 건 — 이력을 남기지 않는 설정입니다 (환경 변수 {var})",
    "{title} ({phase})": "{title} ({phase})",
    "  There are no past records yet.": "  과거의 기록이 아직 없습니다.",
    "  The next time you run start, the current record is archived into\n"
    "  history/ and lines up here.":
        "  다음에 start 하면 지금의 기록이 history/ 로 옮겨져\n"
        "  여기에 나열됩니다.",
    "Finished": "종료",
    "Units": "유닛",
    "  {n} records (newest first). Once the limit is reached, "
    "the oldest go to the trash.":
        "  {n} 건 (최신순). 상한에 도달하면 오래된 것부터 휴지통으로 옮겨집니다.",
    "  Units = the number registered in state.json (Command excluded).\n"
    "  Grandchild self-reports are not counted.":
        "  유닛 = state.json 에 등록된 수 (지휘탑 제외).\n"
        "  손자의 자가 보고는 포함하지 않습니다.",

    # ---- demo（表示テスト用のダミーデータ）
    "display test (dummy data)": "표시 테스트 (더미 데이터)",
    "Scout A": "정찰A",
    "Scout B": "정찰B",
    "Scout C": "정찰C",
    "Analysis A-1": "분석A-1",
    "Sweep A-1-x": "주사A-1-x",
    "find every API call site under src/": "src/ 아래의 API 호출 지점을 훑어낸다",
    "trace the dependencies of the test code": "테스트 코드의 의존 관계를 추적한다",
    "check the documentation for gaps (waiting to deploy)":
        "문서의 누락된 기술을 확인한다 (출동 대기)",
    "classify the 23 sites found by impact": "특정된 23건을 영향도로 분류한다",
    "cross-check the classification and drop duplicates (grandchild self-report)":
        "분류 결과를 대조해 중복을 제거한다 (손자의 자가 보고)",
    "pinned down 23 call sites across 7 files": "호출 지점을 7개 파일 23건으로 특정",
    "registered by self-report": "자가 보고로 등록",
    "Wrote display-test data.": "표시 테스트용 데이터를 기록했습니다.",
    "  Standby, running, awaiting report, done, grandchild self-reports and\n"
    "  missing measured values (—) all appear on the screen.":
        "  대기 중·가동 중·보고 대기·완료·손자의 자가 보고·실측값 없음(—)이\n"
        "  모두 화면에 나옵니다.",

    # ---- reset
    "Reset state.json (standby). Target: {name}":
        "state.json 을 초기화했습니다 (대기 중). 대상: {name}",
    "* The screen keeps this team selected but returns to the standby screen.":
        "※ 화면은 이 팀을 선택한 채로 대기 화면으로 돌아갑니다.",
    "* The current record is emptied without being archived (only start archives it).":
        "※ 지금의 기록은 이력으로 옮겨지지 않고 비워집니다 (이력에 남기는 것은 start 뿐입니다).",
    "* The {n} past records in history/ are left untouched (list them with history).":
        "※ history/ 의 과거 기록 {n} 건은 그대로 남아 있습니다 (목록은 history).",
    "* To delete the whole record folder (past records included), use remove.":
        "※ 기록 폴더째로 (과거 기록까지 포함해) 지우려면 remove 를 쓰세요.",
    "* The grandchild self-report files are still there. Add --purge to delete them.":
        "※ 손자의 자가 보고 파일은 남아 있습니다. 지우려면 --purge 를 붙이세요.",
    "Deleted {n} grandchild self-report files.":
        "손자의 자가 보고 파일을 {n} 건 삭제했습니다.",

    # ---- remove
    "There is no record for this project (missions/{slug}/ is not there).":
        "이 프로젝트의 기록이 없습니다 (missions/{slug}/ 가 없습니다).",
    "      You can check the list with  update_state.py projects":
        "      목록은  update_state.py projects  로 확인할 수 있습니다.",
    "Warning: {n} agents are still running ({ids}).":
        "경고: 가동 중인 에이전트가 {n} 대 있습니다({ids}).",
    "This environment cannot ask for confirmation. Add --yes if you mean to delete it.":
        "확인을 받을 수 없는 환경입니다. 의도해서 지우는 경우에는 --yes 를 붙이세요.",
    "About to delete the records of {name}. Are you sure? [y/N]: ":
        "{name} 의 기록을 삭제합니다. 괜찮습니까? [y/N]: ",
    "Cancelled.": "중지했습니다.",
    "Failed to delete: {err}": "삭제에 실패했습니다: {err}",
    "Deleted for good: {name}": "완전히 삭제했습니다: {name}",
    "Deleted (moved to the trash): {name}": "삭제했습니다 (휴지통으로 이동): {name}",
    "  Moved to": "  이동처",
    "  To undo": "  복구",
    "move this folder back to {path}": "이 폴더를 {path} 로 되돌리세요.",

    # ---- 引数定義（--help に出る文）
    "give an integer (got: {value})": "정수를 지정하세요 (받은 값: {value})",
    "give an integer of 0 or more (got: {value})":
        "0 이상의 정수를 지정하세요 (받은 값: {value})",
    "target project (derived from the current directory when omitted)":
        "대상 프로젝트 (생략하면 현재 디렉터리에서 자동 판정)",
    "Subagent Dashboard — the state-update CLI "
    "(the target project is derived from the current directory)":
        "Subagent Dashboard — 상태 갱신 CLI"
        " (대상 프로젝트는 현재 디렉터리에서 자동 판정)",
    "Leave out any value you could not measure (--tokens / --tools). "
    "Never fill in an estimate.":
        "실측하지 못한 값(--tokens / --tools)은 생략하세요. 추정값을 넣지 말 것.",
    "command": "명령",
    "start a mission (the records so far move to history/, "
    "where history can look them up)":
        "미션을 시작한다 (그때까지의 기록은 history/ 로 옮겨져 history 로 다시 볼 수 있다)",
    "name of the mission": "미션 이름",
    "model ID of the command post": "지휘탑의 모델 ID",
    "register a subagent right after starting it":
        "서브에이전트를 시작한 직후에 등록한다",
    "identifier (for example SCOUT-A)": "식별자 (예: SCOUT-A)",
    "name shown on the screen (same as the ID when omitted)":
        "화면에 나오는 이름 (생략하면 ID 와 같음)",
    "ID of the parent (the command post when omitted)": "부모의 ID (생략하면 지휘탑)",
    "model ID that was used": "사용한 모델 ID",
    "what the task is": "임무 내용",
    "copy the measured values in once the report arrives":
        "완료 통지를 받으면 실측값을 옮겨 적는다",
    "seconds taken (computed from the start time when omitted)":
        "소요 초 (생략하면 시작 시각에서 산출)",
    "token count (leave it out if you did not get one)":
        "토큰 수 (얻지 못했으면 생략)",
    "tool-call count (leave it out if you did not get one)":
        "도구 사용 횟수 (얻지 못했으면 생략)",
    "one-line summary of the result": "결과의 한 줄 요약",
    "close the mission once everyone has finished":
        "전원 완료되면 미션을 완료로 만든다",
    "one-line summary of the whole mission": "미션 전체의 한 줄 요약",
    "add one line of commentary": "실황을 한 줄 추가한다",
    "show the current state": "현재 상태를 표시한다",
    "list the registered projects": "등록된 프로젝트를 목록으로 표시한다",
    "list this project's past missions":
        "이 프로젝트의 과거 미션을 목록으로 표시한다",
    "fill in data for testing the display": "표시 테스트용 데이터를 넣는다",
    "put the current state.json back to standby (past records in history/ "
    "are kept; use remove to delete the records themselves)":
        "현재의 state.json 을 대기 중으로 되돌린다"
        " (history/ 의 과거 기록은 그대로. 기록째 지우려면 remove)",
    "also delete the grandchild self-report files": "손자의 자가 보고 파일도 삭제한다",
    "delete the whole record of the project (past records in history/ go "
    "too; by default they are moved to the trash)":
        "프로젝트의 기록을 통째로 삭제한다"
        " (history/ 의 과거 기록도 함께. 기본값은 휴지통으로 이동)",
    "skip the confirmation": "확인을 생략한다",
    "delete for good instead of moving to the trash":
        "휴지통으로 옮기지 않고 완전히 삭제한다",
}
