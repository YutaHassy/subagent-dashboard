#!/usr/bin/env python3
"""初期設定（install.py）の出力の翻訳表。

**鍵は英語の原文そのもの**（i18n.py の t() を参照）。原文を書き換えたら、ここの
鍵も一緒に書き換えること。合っていない鍵は「訳が無い」と見なされて英語で出る
——静かに落ちるのではなく、英語で出たら訳し漏れ、と読めるようにしてある。

i18n_data.py に既にある原文はここに書かない。合成時は先に読んだ表が勝つので、
両方に書くと「どちらが出ているのか」を追えなくなる。

`{name}` の差し込みは呼び手が .format() で行う。**訳文でも同じ名前を残すこと。**

外部ライブラリは使いません（Python 標準ライブラリのみ）。
"""

from __future__ import annotations

# ------------------------------------------------------------ CLAUDE.md 本文
#
# CLAUDE.md に書き込む運用ルールの本文。長いので定数に出してある（鍵は英語の原文
# そのものなので、EN を鍵・各言語を値として下の表に並べる）。
# 差し込み {py} {us} {sv} {op} は install.py 側で .format() する。
# BEGIN / END / VERSION_MARK の行はこの本文には含めない（機械が読むしるしなので訳さない）。

BLOCK_EN = """## Subagent Dashboard

Whenever you launch subagents, always reflect what is happening on the dashboard.
The target project is detected automatically from the current directory, so the same commands work in any project.

```bash
# once, before the mission starts
{py} {us} start --title "<name of the work>" --model <your own model ID>

# right after you launch each subagent, one at a time
{py} {us} add --id SCOUT-A --name "<a readable name>" --model <model ID> --mission "<the task>"

# a unit that a subagent launched, not you: name its parent
{py} {us} add --id SCOUT-A-1 --parent SCOUT-A --name "<a readable name>" --model <model ID> --mission "<the task>"

# every time you receive a completion report
{py} {us} done --id SCOUT-A --sec <seconds> --tokens <number> --tools <number> --headline "<one-line result summary>"

# once, when every unit is back
{py} {us} finish --headline "<one-line overall summary>"
```

- **Do not forget `finish`.** Nothing breaks when you forget, which is exactly why nobody notices. The screen keeps saying "running", and the next time you `start`, that record is left behind as "unfinished" - **it can never be marked complete afterwards**. A reminder to run `finish` appears the moment you mark the last unit `done`, so close the mission when you see it.
- **Leave out any number that was not in the completion report (`--tokens` / `--tools` / `--sec`); do not estimate it.** Leaving it out shows "—" on the screen, and that is the correct state. Writing an estimate defeats the whole purpose of this dashboard.
- **`--parent` is what draws the tree.** Leave it out and the unit is filed directly under Command, so the screen shows a single column however deep the team really goes. Pass the parent's `--id` for every unit that a subagent launched rather than you.
- **Run `add` once per unit; never fold several into one entry.** An entry like "scout team (6)" loses the six members and everything they launched below them, and it cannot be recovered afterwards. When a subagent launches children of its own, put this in that subagent's own instructions: one JSON file per child, carrying **that subagent's own ID as `parentId`**, written into the grandchild self-report directory that `{py} {us} status` prints - `{op}` has the format.
- **Write the free text in English** (`--title` / `--name` / `--mission` / `--headline`). It is recorded exactly as you write it and shown on the screen exactly as recorded - nothing is translated afterwards. Follow the language of these instructions, not the language of the conversation.
- To watch the screen, start one `{py} {sv}` and open <http://127.0.0.1:3939/>. Every `start` adds one tab, and **past work stays viewable as tabs** (the 20 most recent per project; older ones move to the trash automatically). Finished tabs can be deleted from the screen.
- **Use the `update_state.py` at the path above.** If a copy sits somewhere else, running that one splits the `missions/` that gets written, and nothing appears on the screen.
- For the details (grandchild agents, `--project`, helper commands), see `{op}`.

### When you run two or more missions at once in the same directory (required)

Mission records are kept **one per project (= per working directory)**. If you type a second
`start` in the same directory, the first one is pushed into the history tabs while it is still
running, and every `done` for that first one after that fails with "does not exist". **There is
no way to mark a pushed-out record as finished later on.** Separating the records in advance is
the only remedy.

When you run missions in parallel in the same directory, give each `start` a unique name with
`--project` (passing a name that does not exist creates a new project under that name).

```bash
{py} {us} start --project <a unique name> --title "<name of the work>" --model <your own model ID>
{py} {us} add --project <a unique name> --id SCOUT-A --name "<a readable name>" --model <model ID> --mission "<the task>"
{py} {us} done --project <a unique name> --id SCOUT-A --headline "<one-line result summary>"
{py} {us} finish --project <a unique name> --headline "<one-line overall summary>"
```

- **Put `--project` on all four commands.** Miss it on even one, and that one command writes to
  the record of the current directory = the other team's record.
- Missions that run in different directories have separate records to begin with, so they do not
  need `--project`.
"""

BLOCK_JA = """## Subagent Dashboard

サブエージェントを起動する作業では、必ず状況をダッシュボードに反映してください。
対象プロジェクトはカレントディレクトリから自動判定されるので、どのプロジェクトでも同じコマンドで動きます。

```bash
# ミッション開始前に1回
{py} {us} start --title "<作業の名前>" --model <自分のモデル ID>

# サブエージェントを起動した直後に、1体ずつ
{py} {us} add --id SCOUT-A --name "<読みやすい名前>" --model <モデルID> --mission "<任務内容>"

# サブエージェントが起動した機体は、親のIDを付ける
{py} {us} add --id SCOUT-A-1 --parent SCOUT-A --name "<読みやすい名前>" --model <モデルID> --mission "<任務内容>"

# 完了通知を受け取ったら、その都度
{py} {us} done --id SCOUT-A --sec <秒> --tokens <数> --tools <数> --headline "<結果の一行要約>"

# 全員完了したら1回
{py} {us} finish --headline "<全体の一行要約>"
```

- **`finish` を忘れないでください。** 打ち忘れても何も壊れないので気づけません。画面には「稼働中」と出続け、次に `start` したときその記録は「未完」として残り、**あとから完了にはできません**。最後の1体を `done` にした時点で `finish` の催促が出るので、それを見たら締めてください。
- **完了通知に含まれていなかった数値（`--tokens` / `--tools` / `--sec`）は推定せず省略してください。** 省略すれば画面に「—」と表示され、それが正しい状態です。推定値を書くのはこのダッシュボードの目的を壊す行為です。
- **系統樹を描いているのは `--parent` です。** 付けないとその機体は指令塔の直下に置かれ、実際は何世代に展開していても画面は1列のままになります。自分ではなくサブエージェントが起動した機体には、必ず親の `--id` を渡してください。
- **`add` は1体につき1回で、複数体を1件にまとめないでください。** 「調査班（6名）」のような1件は、6体とその配下に展開した機体を丸ごと失い、**あとから復元できません**。サブエージェント自身に子を起動させる場合は、**そのサブエージェント自身のIDを `parentId` にした**JSONを子1体につき1ファイル、`{py} {us} status` が表示する孫の自己申告フォルダへ書き出すよう、起動時の指示文に含めてください（形式は `{op}`）。
- **自由記述は日本語で書いてください**（`--title` / `--name` / `--mission` / `--headline`）。書いたとおりに記録され、記録したとおりに画面へ出ます——あとから翻訳はされません。会話の言語ではなく、この指示の言語に合わせてください。
- 画面は `{py} {sv}` を1つ起動して <http://127.0.0.1:3939/> で見ます。`start` するたびに1タブ増え、**過去の作業もタブで見返せます**（プロジェクトごとに直近20件。古いものから自動でゴミ箱へ移ります）。完了したタブは画面から削除できます。
- **`update_state.py` は上のパスのものを使ってください。** 別の場所にコピーがある場合、そちらを実行すると書き込み先の `missions/` が分かれてしまい、画面に何も出ません。
- 詳細（孫エージェントの扱い、`--project` 指定、補助コマンド）は `{op}` を参照してください。

### 同じディレクトリで2本以上を同時に走らせるとき（必須）

ミッションの記録先は**プロジェクト（＝作業ディレクトリ）ごとに1つ**です。同じディレクトリで
2本目の `start` を打つと、1本目は稼働中のまま履歴タブへ押し出され、以後その1本目に対する
`done` は「存在しません」というエラーになります。**押し出された記録をあとから完了に直す手段は
ありません。** 事前に記録先を分けることが唯一の対策です。

同じディレクトリで並行させるときは、`start` に `--project` で一意な名前を付けて分けてください
（存在しない名前を渡せば、その名前で新しいプロジェクトが作られます）。

```bash
{py} {us} start --project <一意な名前> --title "<作業の名前>" --model <自分のモデル ID>
{py} {us} add --project <一意な名前> --id SCOUT-A --name "<読みやすい名前>" --model <モデルID> --mission "<任務内容>"
{py} {us} done --project <一意な名前> --id SCOUT-A --headline "<結果の一行要約>"
{py} {us} finish --project <一意な名前> --headline "<全体の一行要約>"
```

- **`--project` は4コマンドすべてに付けてください。** 1つでも付け忘れると、そのコマンドだけ
  カレントディレクトリ側の記録＝もう一方のチームに書き込まれます。
- 別々のディレクトリで走るミッション同士は記録先がもともと別なので、`--project` は要りません。
"""

BLOCK_ZH = """## Subagent Dashboard

在启动子代理的工作中，务必把状况反映到面板上。
目标项目会从当前目录自动判定，所以在任何项目里都用同样的命令。

```bash
# 任务开始前执行一次
{py} {us} start --title "<工作的名称>" --model <你自己的模型 ID>

# 启动子代理之后立刻，一体一体地登记
{py} {us} add --id SCOUT-A --name "<好读的名字>" --model <模型ID> --mission "<任务内容>"

# 由子代理启动、而非由你启动的一体：注明其父级
{py} {us} add --id SCOUT-A-1 --parent SCOUT-A --name "<好读的名字>" --model <模型ID> --mission "<任务内容>"

# 每次收到完成通知时
{py} {us} done --id SCOUT-A --sec <秒> --tokens <数> --tools <数> --headline "<结果的一行摘要>"

# 全员完成后执行一次
{py} {us} finish --headline "<整体的一行摘要>"
```

- **请不要忘记 `finish`。** 忘了敲也不会坏掉任何东西，所以察觉不到。画面上会一直显示「运行中」，下次 `start` 时那条记录会作为「未完成」留下，**事后无法再改成完成**。把最后一体置为 `done` 的时点会出现 `finish` 的催促，看到它就请收尾。
- **完成通知里没有的数值（`--tokens` / `--tools` / `--sec`）请不要估算，直接省略。** 省略后画面上会显示「—」，那才是正确的状态。写上估算值是破坏这个面板目的的行为。
- **绘制树状结构的是 `--parent`。** 不加的话，那一体会直接归在指挥部之下，无论团队实际展开到多深，画面都会显示为一列。不是由你而是由子代理启动的每一体，都请传入其父级的 `--id`。
- **每一体运行一次 `add`，绝不要把多体合并为一条记录。** 像「侦察小队（6名）」这样的条目会丢失那6体及其下方启动的所有单位，而且事后无法恢复。当子代理自行启动子级时，请在该子代理的启动指示中包含以下内容：为每个子级写入一个 JSON 文件，**将该子代理自身的 ID 作为 `parentId`**，写入 `{py} {us} status` 显示的孙级自我报告目录——格式见 `{op}`。
- **自由文本请用中文书写**（`--title` / `--name` / `--mission` / `--headline`）。会照你写下的样子记录，照记录的样子显示在画面上——事后不会翻译。请对齐这份指示的语言，而不是对话的语言。
- 画面是启动一个 `{py} {sv}`，然后在 <http://127.0.0.1:3939/> 上看。每 `start` 一次就多一个标签页，**过去的工作也能用标签页回看**（每个项目保留最近 20 条。旧的会自动移入回收站）。已完成的标签页可以从画面上删除。
- **请使用上面那个路径的 `update_state.py`。** 如果别的地方有副本，执行那一个会让写入的 `missions/` 分家，画面上就什么都不出现。
- 详细内容（孙代理的处理、`--project` 指定、辅助命令）请参照 `{op}`。

### 在同一个目录里同时跑两个以上时（必须）

任务的记录位置是**每个项目（＝工作目录）一个**。在同一个目录里敲第二个
`start`，第一个就会在运行中的状态下被挤进历史标签页，此后针对第一个的
`done` 会报「不存在」的错误。**被挤出去的记录事后没有办法改成完成。**
事先把记录位置分开是唯一的对策。

在同一个目录里并行时，请给 `start` 加上 `--project` 起一个唯一的名字来区分
（传一个不存在的名字，就会用那个名字新建一个项目）。

```bash
{py} {us} start --project <唯一的名字> --title "<工作的名称>" --model <你自己的模型 ID>
{py} {us} add --project <唯一的名字> --id SCOUT-A --name "<好读的名字>" --model <模型ID> --mission "<任务内容>"
{py} {us} done --project <唯一的名字> --id SCOUT-A --headline "<结果的一行摘要>"
{py} {us} finish --project <唯一的名字> --headline "<整体的一行摘要>"
```

- **`--project` 请加在全部四个命令上。** 哪怕漏掉一个，那一个命令就只会写进
  当前目录一侧的记录＝另一支队伍那边。
- 在不同目录里跑的任务，记录位置本来就是分开的，所以不需要 `--project`。
"""

BLOCK_KO = """## Subagent Dashboard

서브에이전트를 띄우는 작업에서는 반드시 상황을 대시보드에 반영하세요.
대상 프로젝트는 현재 디렉터리에서 자동으로 판정되므로, 어느 프로젝트에서든 같은 명령으로 움직입니다.

```bash
# 미션 시작 전에 한 번
{py} {us} start --title "<작업의 이름>" --model <자신의 모델 ID>

# 서브에이전트를 띄운 직후에, 한 대씩
{py} {us} add --id SCOUT-A --name "<읽기 쉬운 이름>" --model <모델ID> --mission "<임무 내용>"

# 서브에이전트가 띄운 기체에는 부모의 ID를 붙이기
{py} {us} add --id SCOUT-A-1 --parent SCOUT-A --name "<읽기 쉬운 이름>" --model <모델ID> --mission "<임무 내용>"

# 완료 보고를 받을 때마다
{py} {us} done --id SCOUT-A --sec <초> --tokens <수> --tools <수> --headline "<결과의 한 줄 요약>"

# 전원 완료되면 한 번
{py} {us} finish --headline "<전체의 한 줄 요약>"
```

- **`finish` 를 잊지 마세요.** 잊고 치지 않아도 아무것도 망가지지 않기 때문에 알아챌 수 없습니다. 화면에는 계속 「가동 중」이라고 나오고, 다음에 `start` 했을 때 그 기록은 「미완」으로 남으며, **나중에 완료로 만들 수는 없습니다**. 마지막 한 대를 `done` 으로 만든 시점에 `finish` 를 재촉하는 안내가 나오므로, 그것을 보면 마무리하세요.
- **완료 보고에 들어 있지 않던 수치(`--tokens` / `--tools` / `--sec`)는 추정하지 말고 생략하세요.** 생략하면 화면에 「—」로 표시되며, 그것이 올바른 상태입니다. 추정값을 적는 것은 이 대시보드의 목적을 망가뜨리는 행위입니다.
- **계통도를 그리는 것은 `--parent` 입니다.** 붙이지 않으면 그 기체는 지령탑 바로 아래에 놓이며, 실제로는 몇 세대까지 전개되어 있어도 화면에는 한 열로만 표시됩니다. 자신이 아니라 서브에이전트가 띄운 기체에는 반드시 부모의 `--id` 를 넘겨주세요.
- **`add` 는 한 대마다 한 번 실행하고, 여러 대를 한 건으로 합치지 마세요.** 「조사반(6명)」 같은 한 건은 여섯 대와 그 아래에 띄운 기체를 전부 잃게 만들며, 나중에 복원할 수 없습니다. 서브에이전트가 자신의 자식을 띄우는 경우에는, 자식 한 대마다 **그 서브에이전트 자신의 ID를 `parentId`로 넣은** JSON 파일 하나를 `{py} {us} status`가 표시하는 손자 자체 보고 폴더에 쓰도록 띄울 때의 지시문에 포함하세요(형식은 `{op}`).
- **자유 기술은 한국어로 쓰세요**(`--title` / `--name` / `--mission` / `--headline`). 적은 그대로 기록되고, 기록된 그대로 화면에 나옵니다——나중에 번역되지 않습니다. 대화의 언어가 아니라 이 지시의 언어에 맞추세요.
- 화면은 `{py} {sv}` 를 하나 띄우고 <http://127.0.0.1:3939/> 에서 봅니다. `start` 할 때마다 탭이 하나 늘고, **지난 작업도 탭으로 되돌아볼 수 있습니다**(프로젝트마다 최근 20건. 오래된 것부터 자동으로 휴지통으로 옮겨집니다). 완료된 탭은 화면에서 삭제할 수 있습니다.
- **`update_state.py` 는 위 경로의 것을 쓰세요.** 다른 곳에 복사본이 있는 경우, 그쪽을 실행하면 기록되는 `missions/` 가 갈라져 화면에 아무것도 나오지 않습니다.
- 자세한 내용(손자 에이전트의 취급, `--project` 지정, 보조 명령)은 `{op}` 를 참조하세요.

### 같은 디렉터리에서 두 개 이상을 동시에 돌릴 때 (필수)

미션의 기록 위치는 **프로젝트(= 작업 디렉터리)마다 하나**입니다. 같은 디렉터리에서
두 번째 `start` 를 치면, 첫 번째는 가동 중인 채로 이력 탭으로 밀려나고, 이후 그 첫 번째에 대한
`done` 은 「존재하지 않습니다」라는 오류가 됩니다. **밀려난 기록을 나중에 완료로 고치는 수단은
없습니다.** 미리 기록 위치를 나누는 것이 유일한 대책입니다.

같은 디렉터리에서 병행할 때는 `start` 에 `--project` 로 고유한 이름을 붙여 나누세요
(존재하지 않는 이름을 넘기면 그 이름으로 새 프로젝트가 만들어집니다).

```bash
{py} {us} start --project <고유한 이름> --title "<작업의 이름>" --model <자신의 모델 ID>
{py} {us} add --project <고유한 이름> --id SCOUT-A --name "<읽기 쉬운 이름>" --model <모델ID> --mission "<임무 내용>"
{py} {us} done --project <고유한 이름> --id SCOUT-A --headline "<결과의 한 줄 요약>"
{py} {us} finish --project <고유한 이름> --headline "<전체의 한 줄 요약>"
```

- **`--project` 는 네 명령 모두에 붙이세요.** 하나라도 빠뜨리면 그 명령만
  현재 디렉터리 쪽의 기록 = 다른 한쪽 팀에 기록됩니다.
- 서로 다른 디렉터리에서 도는 미션끼리는 기록 위치가 원래 다르므로 `--project` 는 필요 없습니다.
"""

# ------------------------------------------------------------ CLAUDE.md 本文（変更履歴トラッキング）
#
# install.build_changelog_block() が書き込む第2のブロックの本文。Subagent Dashboard
# のブロック（上）とは独立していて、書き先は CLAUDE.md だけ。
# 差し込み {py} {cli} は install.py 側で .format() する。

CHANGELOG_BLOCK_EN = """## Claude Code Changelog Tracking

Some projects have Claude Code changelog tracking configured (project-local, under `.claude/changelog/` in that project). It is a separate feature from Subagent Dashboard above: it records what *you* changed in that project and why, not subagent missions. If `.claude/changelog/` does not exist in the current project, none of this applies to you here.

When it is configured for the current project:

- **Recording itself is fully automatic. You never have to run anything to make an entry exist.** A hook already logs every Edit/Write/NotebookEdit/Bash call to a raw log as you work — that part needs no action from you.
- **At a natural breakpoint in the session, proactively call `summarize` yourself, on your own judgement, rather than waiting to be forced:**
  ```
  {py} {cli} summarize --session <id> --headline "<what changed and why, one line>" --body "<details, optional>"
  ```
  Run `{py} {cli} status` first if you need the current session's id — it lists any session for this project that still has unsummarized entries. A Stop hook exists as a safety net that blocks the end of a session if nothing has been summarized yet; treat hitting that as a fallback you would rather avoid, not the normal way this gets done.
- **Write only what you can actually back up from the raw log. Never invent a headline or body.** If you are not sure what happened in the session, run `{py} {cli} status --session <id>` (or `list`) first and summarize from what it shows — do not guess or pad the description to sound more complete than it is.
"""

CHANGELOG_BLOCK_JA = """## Claude Code 変更履歴トラッキング

プロジェクトによっては、Claude Code の変更履歴トラッキングが設定されています（プロジェクトローカル。そのプロジェクトの `.claude/changelog/` 配下）。上の Subagent Dashboard とは別の機能で、記録するのはサブエージェントの編成ではなく、**あなた自身がそのプロジェクトで何を・なぜ変更したか**です。いま作業しているプロジェクトに `.claude/changelog/` が無ければ、ここでは関係ありません。

いま作業しているプロジェクトで設定されている場合:

- **記録そのものは完全に自動です。記録を残すために何かを実行する必要はありません。** 作業中の Edit/Write/NotebookEdit/Bash はすべて hook が生ログへ書いています——その部分であなたがすることは何もありません。
- **セッションの区切りがついたところで、強制されるのを待たず、自分の判断で `summarize` を呼んでください:**
  ```
  {py} {cli} summarize --session <id> --headline "<何を・なぜ変えたか、一行で>" --body "<詳細（任意）>"
  ```
  いまのセッションIDが必要なら、先に `{py} {cli} status` を実行してください——このプロジェクトで未要約の記録が残っているセッションが出ます。何も要約されないままセッションが終わろうとすると Stop hook が安全網として止めますが、それは避けたい最後の受け皿であって、通常の書き方ではありません。
- **生ログから裏付けられることだけを書いてください。見出しや本文を捏造しないこと。** そのセッションで何があったか自信が持てないときは、先に `{py} {cli} status --session <id>`（または `list`）を実行し、出てきたものだけを踏まえて要約してください——推測で埋めたり、実際より充実して見えるように盛ったりしないこと。
"""

CHANGELOG_BLOCK_ZH = """## Claude Code 变更历史追踪

有些项目配置了 Claude Code 的变更历史追踪（保存在项目本地，即该项目的 `.claude/changelog/` 下）。它与上面的 Subagent Dashboard 是两个功能：记录的不是子代理的编成，而是**你自己在那个项目里改了什么、为什么改**。如果当前项目里没有 `.claude/changelog/`，这一节在这里就与你无关。

当前项目配置了它时:

- **记录本身完全自动。为了留下一条记录，你不需要执行任何命令。** 你工作中的每一次 Edit/Write/NotebookEdit/Bash 都已由 hook 写入原始日志——这部分不需要你动手。
- **在会话告一段落时，不要等着被强制，自己判断并主动调用 `summarize`:**
  ```
  {py} {cli} summarize --session <id> --headline "<改了什么、为什么，一行>" --body "<详情（可选）>"
  ```
  如果需要当前会话的 id，先执行 `{py} {cli} status`——它会列出这个项目里仍有未汇总记录的会话。若什么都没汇总就想结束会话，Stop hook 会作为安全网拦下来；但那是你宁可避免的兜底，不是正常的写法。
- **只写你能从原始日志中确认的内容。绝不要编造标题或正文。** 如果你不确定这次会话里发生了什么，先执行 `{py} {cli} status --session <id>`（或 `list`），只根据它显示的内容来汇总——不要靠猜测填补，也不要把描述写得比实际更充实。
"""

CHANGELOG_BLOCK_KO = """## Claude Code 변경 이력 추적

일부 프로젝트에는 Claude Code 변경 이력 추적이 설정되어 있습니다(프로젝트 로컬. 해당 프로젝트의 `.claude/changelog/` 아래). 위의 Subagent Dashboard 와는 별개의 기능으로, 기록하는 것은 서브에이전트의 편성이 아니라 **당신 자신이 그 프로젝트에서 무엇을 왜 바꿨는지**입니다. 지금 작업 중인 프로젝트에 `.claude/changelog/` 가 없다면 여기서는 해당되지 않습니다.

지금 작업 중인 프로젝트에 설정되어 있는 경우:

- **기록 자체는 완전히 자동입니다. 기록을 남기기 위해 무언가를 실행할 필요는 없습니다.** 작업 중의 Edit/Write/NotebookEdit/Bash 는 모두 hook 이 원본 로그에 쓰고 있습니다——그 부분에서 당신이 할 일은 없습니다.
- **세션이 한 단락 지어지는 지점에서, 강제되기를 기다리지 말고 스스로 판단해 `summarize` 를 호출하세요:**
  ```
  {py} {cli} summarize --session <id> --headline "<무엇을 왜 바꿨는지, 한 줄로>" --body "<상세(선택)>"
  ```
  지금 세션의 id 가 필요하면 먼저 `{py} {cli} status` 를 실행하세요——이 프로젝트에서 아직 요약되지 않은 기록이 남아 있는 세션이 나옵니다. 아무것도 요약되지 않은 채 세션이 끝나려 하면 Stop hook 이 안전망으로 막지만, 그것은 피하고 싶은 최후의 받침이지 평소의 방식이 아닙니다.
- **원본 로그로 뒷받침할 수 있는 것만 쓰세요. 제목이나 본문을 지어내지 마세요.** 그 세션에서 무슨 일이 있었는지 확신이 서지 않으면 먼저 `{py} {cli} status --session <id>`(또는 `list`)를 실행하고, 거기 나온 것만을 근거로 요약하세요——추측으로 메우거나 실제보다 충실해 보이도록 부풀리지 마세요.
"""

CATALOG: dict[str, dict[str, str]] = {}

# ============================================================ 日本語
CATALOG["ja"] = {
    # ---- install: CLAUDE.md に書き込む本文（変更履歴トラッキングのブロック）
    CHANGELOG_BLOCK_EN: CHANGELOG_BLOCK_JA,

    '    (only the marked block is updated; anything already there is kept — including the Subagent Dashboard block above)':
        '    （マーカーで囲まれた範囲のみ更新。既存の記述は保持されます——上の Subagent Dashboard のブロックも含めて）',
    'What will be added to {name} ({path}) (changelog tracking block):':
        '{name}（{path}）に追記される内容（変更履歴トラッキングのブロック）:',
    '  ✓ {name} (changelog tracking block) is already up to date (no change)':
        '  ✓ {name} は最新です（変更履歴トラッキングのブロック。変更なし）',
    '  ✓ {name} was created (changelog tracking block).':
        '  ✓ {name} を新規作成しました（変更履歴トラッキングのブロック）',
    '  ✓ The changelog tracking block was appended to {name}.':
        '  ✓ {name} に変更履歴トラッキングのブロックを追記しました',
    '  ✓ {name} was updated (changelog tracking block; also tidied up {n} duplicated old blocks).':
        '  ✓ {name} を更新しました（変更履歴トラッキングのブロック。重複していた古いブロック {n} 個も整理）',
    '  ✓ {name} was updated (changelog tracking block).':
        '  ✓ {name} を更新しました（変更履歴トラッキングのブロック）',
    '  Removed the Subagent Dashboard and changelog tracking settings from {name} (anything else was left alone).':
        '  {name} から Subagent Dashboard と変更履歴トラッキングの設定を削除しました（他の記述はそのままです）',
    '  Removed the changelog tracking settings from {name} (anything else was left alone).':
        '  {name} から変更履歴トラッキングの設定を削除しました（他の記述はそのままです）',

    # ---- install: CLAUDE.md に書き込む本文
    BLOCK_EN: BLOCK_JA,

    # ---- install: CLAUDE.md の差し替え
    "the markers ({begin} / {end}) are not paired":
        "マーカー（{begin} / {end}）が対になっていません",
    "  ✓ {name} was created.": "  ✓ {name} を新規作成しました",
    "  ✓ The settings were appended to {name}.": "  ✓ {name} に追記しました",
    "  ✓ {name} was updated.": "  ✓ {name} を更新しました",
    "  ✓ {name} was updated (also tidied up {n} duplicated old blocks).":
        "  ✓ {name} を更新しました（重複していた古いブロック {n} 個も整理）",
    "    (only the marked block is updated; anything already there is kept)":
        "    （マーカーで囲まれた範囲のみ更新。既存の記述は保持されます）",

    # ---- install: keybindings.json の読み書き
    "the contents are not an array (VSCode's keybindings.json is an array)":
        "中身が配列ではありません（VSCode の keybindings.json は配列）",
    "the closing bracket of the array was not found":
        "配列の閉じ括弧が見つかりません",
    "cannot create {path} ({err})": "{path} を作れません（{err}）",
    "cannot read {path} ({err})": "{path} を読めません（{err}）",
    "{path} cannot be rewritten ({err})": "{path} は書き換えられません（{err}）",
    "cannot write to {path} ({err})": "{path} に書き込めません（{err}）",
    "the structure of {path} could not be read fully "
    "(nothing was changed, to be safe)":
        "{path} の構造を読み切れませんでした（安全のため変更していません）",

    # ---- install: キーバインドの登録
    "the VSCode settings folder was not found ({path}). VSCode may not be "
    "installed, or you may be using Insiders / VSCodium":
        "VSCode の設定フォルダが見つかりません（{path}）。"
        "VSCode が未インストールか、Insiders / VSCodium をお使いの可能性があります",
    "created the file and registered the binding": "作成して登録しました",
    "it is registered, but a different binding further down ({names}) takes "
    "precedence, so Ctrl+Shift+D does not open it":
        "登録はされていますが、後ろにある別の割り当て（{names}）が"
        "優先されるため、Ctrl+Shift+D では開きません",
    "already registered (no change)": "既に登録されています（変更なし）",
    "{key} is already bound to a different command ({names}). It was not "
    "registered, so as not to overwrite your own setting":
        "{key} は既に別のコマンド（{names}）に割り当てられています。"
        "利用者の設定を上書きしないため、登録していません",
    "removed the old-style entry": "古い形式のエントリを取り除きました",
    "replaced the old-style entry with the current one":
        "古い形式のエントリを今の形式に置き換えました",
    "registered": "登録しました",

    # ---- install: キーバインドの取り消し
    "the file does not exist (nothing was done)":
        "ファイルがありません（何もしていません）",
    "there are no entries from this tool (nothing was done)":
        "このツールのエントリはありません（何もしていません）",
    "removed {n} entries": "{n} 個のエントリを取り除きました",

    # ---- install: 環境チェック
    "Warning: could not make ./dash executable ({err})":
        "警告: ./dash に実行権限を付けられませんでした（{err}）",
    "Python 3.9 or newer is required (this is {v})":
        "Python 3.9 以降が必要です（いま {v}）",
    "the following files were not found (the package may be incomplete): {list}":
        "次のファイルが見つかりません（ファイルが揃っていない可能性があります）: {list}",
    "cannot write to the mission storage ({path} / {reason})":
        "ミッション保存先に書き込めません（{path} / {reason}）",
    "cannot write to the config folder of {name} ({path} / {reason})":
        "{name} の設定フォルダに書き込めません（{path} / {reason}）",

    # ---- install: 見出しと --print
    "  Subagent Dashboard — installer":
        "  Subagent Dashboard — インストーラー",
    "  What would be written (--print, so nothing is actually changed)":
        "  書き込む内容（--print なので実際には変更しません）",
    "What will be added to {name} ({path}):":
        "{name}（{path}）に追記する内容:",
    "The entry that will be added to keybindings.json ({path}):":
        "keybindings.json（{path}）に追加するエントリ:",
    "* The old location ({path}) still holds":
        "※ 古い場所（{path}）に、このツールが以前書いた",
    "  {n} invalid entries written earlier by this tool. Running this removes them.":
        "  無効なエントリが {n} 個残っています。実行すると取り除きます。",

    # ---- install: ステップ 1（環境チェック）
    "Step 1/4: Environment check": "ステップ 1/4: 環境チェック",
    "  ✗ The following problems were found:": "  ✗ 次の問題が見つかりました:",
    "    - {problem}": "    ・{problem}",
    "  Please solve these problems and run this again.":
        "  これらの問題を解決してから再度実行してください。",
    "Platform": "プラットフォーム",
    "Write permission": "書き込み権限",
    "Tool location": "ツールの場所",
    "VSCode keybinding": "VSCode キーバインド",
    "OK ({n} files, all present)": "OK（{n} 件すべて確認）",
    "OK ({missions} / {config})": "OK（{missions} / {config}）",
    "OK ({path})": "OK（{path}）",
    "cannot write ({reason})": "書き込めません（{reason}）",
    "the settings folder was not found ({path})":
        "設定フォルダが見つかりません（{path}）",
    "  ⚠ You are running this from inside the distribution (under dist/).":
        "  ⚠ 配布物の中（dist/ の下）から実行しています。",
    "     If you go on, records will be stored in {path}.":
        "     このまま進めると、記録の保存先が {path} になります。",
    "     Move the unpacked folder outside dist/ before running this.":
        "     配布物を展開したフォルダを、dist/ の外へ移してから実行してください。",

    # ---- install: ステップ 2（自動検出）
    "Step 2/4: Automatic detection of the environment":
        "ステップ 2/4: 環境の自動検出",
    "Dashboard location": "ダッシュボードの場所",
    "Python command": "Python 実行コマンド",
    "Config file ({name})": "設定ファイル（{name}）",
    "  (leftovers in the old location: {path} / {n})":
        "  （古い場所に残骸あり: {path} / {n} 個）",

    # ---- install: ステップ 3（書き込み）
    "Step 3/4: Writing to the config files": "ステップ 3/4: 設定ファイルへの書き込み",
    "  ✗ Error: cannot read {path} ({err})":
        "  ✗ エラー: {path} を読めません（{err}）",
    "  ✗ Error: {path} cannot be touched ({err})":
        "  ✗ エラー: {path} に手を出せません（{err}）",
    "    Writing now would wipe out your own text the next time --uninstall runs.":
        "    このまま書くと、次に --uninstall したとき利用者の記述まで消えます。",
    "    Pair up the markers in {path}, then run this again.":
        "    {path} のマーカーを対にしてから、もう一度実行してください。",
    "  ✗ Error: cannot write to {path} ({err})":
        "  ✗ エラー: {path} に書き込めません（{err}）",
    "  ✓ {name} is already up to date (no change)":
        "  ✓ {name} は既に最新です（変更なし）",
    "  ✓ keybindings.json was updated ({msg})":
        "  ✓ keybindings.json を更新しました（{msg}）",
    "    (Ctrl+Shift+D → agentDashboard.open. "
    "It works once the extension is installed.)":
        "    （Ctrl+Shift+D → agentDashboard.open。拡張機能を入れると効きます）",
    "  ✓ keybindings.json needed no change ({msg})":
        "  ✓ keybindings.json は変更不要でした（{msg}）",
    "  ⚠ Ctrl+Shift+D does not work ({msg})":
        "  ⚠ Ctrl+Shift+D は効きません（{msg}）",
    "  ⚠ Ctrl+Shift+D was not registered ({msg})":
        "  ⚠ Ctrl+Shift+D は登録しませんでした（{msg}）",
    "    Open {path} and either drop that binding, or bind another key":
        "    {path} を開いて、その割り当てを外すか、別のキーに",
    '    with {{"key": "<the key you like>", "command": "{cmd}"}}.':
        '    {{"key": "<好きなキー>", "command": "{cmd}"}} を書いてください。',
    "  ⚠ Warning: keybindings.json could not be updated ({msg})":
        "  ⚠ 警告: keybindings.json を更新できませんでした（{msg}）",
    "  ✓ Cleaned up the dead entries in the old location ({msg})":
        "  ✓ 古い場所の無効なエントリを片付けました（{msg}）",
    "    (VSCode does not read this location. Other entries were left alone.)":
        "    （VSCode はこの場所を読みません。他のエントリは残しています）",
    "  ⚠ {n} dead entries remain in the old location: {path}":
        "  ⚠ 古い場所に無効なエントリが {n} 個残っています: {path}",
    "    They could not be cleaned up ({msg}). Deleting them by hand is fine.":
        "    片付けられませんでした（{msg}）。手で消しても問題ありません。",
    "  ⚠ The file in the old location could not be read: {path}":
        "  ⚠ 古い場所のファイルを読めませんでした: {path}",
    "    Dead entries written earlier by this tool may still be there.":
        "    このツールが以前書いた無効なエントリが残っている可能性があります。",
    "  ✓ Made the launcher executable: ./dash":
        "  ✓ ランチャに実行権限を付けました: ./dash",

    # ---- install: ステップ 4（完了）
    "Step 4/4: Setup complete!": "ステップ 4/4: セットアップ完了！",
    "  🎉 The installation is complete!": "  🎉 インストールが完了しました！",
    "  The installation is complete (Ctrl+Shift+D was not registered).":
        "  インストールが完了しました（Ctrl+Shift+D の登録は見送りました）。",
    "  You can open the dashboard in these ways:":
        "  次の方法でダッシュボードを開けます:",
    "  [Option 1] Start it from the command line (recommended)":
        "  【方法1】コマンドから起動（推奨）",
    "  [Option 2] A VSCode keyboard shortcut":
        "  【方法2】VSCode のキーボードショートカット",
    "    Press Ctrl+Shift+D (it works once you install the extension below)":
        "    Ctrl+Shift+D を押す（下の拡張機能を入れてから効きます）",
    "  [Option 2] A VSCode keyboard shortcut → not registered this time":
        "  【方法2】VSCode のキーボードショートカット → 今回は登録していません",
    "    See the ⚠ above for why. Options 1 and 3 work as they are.":
        "    上の ⚠ の理由を見てください。方法1と方法3はそのまま使えます。",
    "  [Option 3] The VSCode extension (more convenient)":
        "  【方法3】VSCode 拡張機能（より便利）",
    "    then click the robot icon at the far left":
        "    を実行してから、左端のロボットアイコンをクリック",
    "  📖 The manual (it opens once the server is running)":
        "  📖 取扱説明書（起動後に開きます）",
    "  🔍 If something goes wrong, run the diagnostics script":
        "  🔍 問題が起きたら診断スクリプトを実行",

    # ---- install: --uninstall
    "Config file": "設定ファイル",
    "Keybinding settings": "キーバインド設定",
    "(the old location)": "（古い場所）",
    "  {name} does not exist.": "  {name} がありません。",
    "Error: cannot read {path} ({err})": "エラー: {path} を読めません（{err}）",
    "Error: cannot write to {path} ({err})": "エラー: {path} に書き込めません（{err}）",
    "  Removed the settings from {name} (anything else was left alone).":
        "  {name} から設定を削除しました（他の記述は残しています）。",
    "  {name} has no settings from this tool.":
        "  {name} にはこのツールの設定がありません。",
    "the keybindings.json in the old location": "古い場所の keybindings.json",
    "  Removed the settings from {label} ({msg}).":
        "  {label} から設定を削除しました（{msg}）。",
    "    (other entries written by you were left alone)":
        "    （利用者が書いた他のエントリは残しています）",
    "  Warning: deleting from {label} failed ({msg})":
        "  警告: {label} の削除に失敗しました（{msg}）",
    "  Nothing was deleted.": "  何も削除されませんでした。",
    "  The mission records are still there: {path}":
        "  ミッションの記録は残っています: {path}",

    # ---- install: CLI の検出と一覧
    "The CLIs this tool knows about:": "このツール対応の CLI:",
    "For a CLI that is not on this list, point at its file directly:":
        "リストにない CLI を指す場合は、そのファイルを直接指定してください:",
    "--agent-file needs a path to a file, not a folder":
        "--agent-file はファイルのパスが必要です（フォルダではなく）",
    " (added by you)": "（ユーザーが追加）",
    "write to this file as well, for a CLI that is not in the list "
    "(it gets remembered)":
        "リストにない CLI 用に、このファイルにも書き込む（記憶されます）",
    "show the CLIs this tool knows about, and stop":
        "このツール対応の CLI を表示して終了する",
    "written": "書き込み済み",
    "Entries you add are remembered in {path}":
        "追加したエントリは {path} に記録されます",
    "installed, not written yet": "インストール済みですが、未書き込み",
    "not found on this machine": "このマシンに見つかりません",
    "Error: {err}": "エラー: {err}",

    # ---- install: 引数
    "First-time setup for the Subagent Dashboard":
        "Subagent Dashboard の初期設定",
    "only show what would be written (changes nothing)":
        "書き込む内容を表示するだけ（何も変更しない）",
    "undo the settings that were written": "書き込んだ設定を取り消す",
    "which CLI to write the operating rules for "
    "(the default writes to every one that is installed)":
        "運用ルールを書き込む CLI（既定では入っている CLI 全部に書きます）",
}

# ============================================================ 中文（简体）
CATALOG["zh"] = {
    # ---- install: CLAUDE.md に書き込む本文（変更履歴トラッキングのブロック）
    CHANGELOG_BLOCK_EN: CHANGELOG_BLOCK_ZH,

    '    (only the marked block is updated; anything already there is kept — including the Subagent Dashboard block above)':
        '    （只更新标记包围的范围，既有内容都会保留——包括上面的 Subagent Dashboard 块）',
    'What will be added to {name} ({path}) (changelog tracking block):':
        '将写入 {name}（{path}）的内容（变更历史追踪的块）:',
    '  ✓ {name} (changelog tracking block) is already up to date (no change)':
        '  ✓ {name} 已是最新（变更历史追踪的块，无变化）',
    '  ✓ {name} was created (changelog tracking block).':
        '  ✓ 已新建 {name}（变更历史追踪的块）',
    '  ✓ The changelog tracking block was appended to {name}.':
        '  ✓ 已向 {name} 追加变更历史追踪的块',
    '  ✓ {name} was updated (changelog tracking block; also tidied up {n} duplicated old blocks).':
        '  ✓ 已更新 {name}（变更历史追踪的块；同时整理了重复的旧块 {n} 个）',
    '  ✓ {name} was updated (changelog tracking block).':
        '  ✓ 已更新 {name}（变更历史追踪的块）',
    '  Removed the Subagent Dashboard and changelog tracking settings from {name} (anything else was left alone).':
        '  已从 {name} 删除 Subagent Dashboard 与变更历史追踪的设置（其他内容原样保留）',
    '  Removed the changelog tracking settings from {name} (anything else was left alone).':
        '  已从 {name} 删除变更历史追踪的设置（其他内容原样保留）',

    # ---- install: CLAUDE.md に書き込む本文
    BLOCK_EN: BLOCK_ZH,

    # ---- install: CLAUDE.md の差し替え
    "the markers ({begin} / {end}) are not paired":
        "标记（{begin} / {end}）没有成对",
    "  ✓ {name} was created.": "  ✓ 已新建 {name}",
    "  ✓ The settings were appended to {name}.": "  ✓ 已向 {name} 追加写入",
    "  ✓ {name} was updated.": "  ✓ 已更新 {name}",
    "  ✓ {name} was updated (also tidied up {n} duplicated old blocks).":
        "  ✓ 已更新 {name}（顺便整理了重复的 {n} 个旧块）",
    "    (only the marked block is updated; anything already there is kept)":
        "    （只更新标记包围的范围。已有的记述会保留）",

    # ---- install: keybindings.json の読み書き
    "the contents are not an array (VSCode's keybindings.json is an array)":
        "内容不是数组（VSCode 的 keybindings.json 是数组）",
    "the closing bracket of the array was not found":
        "找不到数组的右方括号",
    "cannot create {path} ({err})": "无法创建 {path}（{err}）",
    "cannot read {path} ({err})": "无法读取 {path}（{err}）",
    "{path} cannot be rewritten ({err})": "无法改写 {path}（{err}）",
    "cannot write to {path} ({err})": "无法写入 {path}（{err}）",
    "the structure of {path} could not be read fully "
    "(nothing was changed, to be safe)":
        "没能完整读懂 {path} 的结构（为安全起见没有做任何修改）",

    # ---- install: キーバインドの登録
    "the VSCode settings folder was not found ({path}). VSCode may not be "
    "installed, or you may be using Insiders / VSCodium":
        "找不到 VSCode 的配置文件夹（{path}）。"
        "可能是没有安装 VSCode，或者用的是 Insiders / VSCodium",
    "created the file and registered the binding": "已创建文件并完成注册",
    "it is registered, but a different binding further down ({names}) takes "
    "precedence, so Ctrl+Shift+D does not open it":
        "虽然已经注册，但后面还有另一个绑定（{names}）优先，"
        "所以按 Ctrl+Shift+D 打不开",
    "already registered (no change)": "已经注册过了（无变更）",
    "{key} is already bound to a different command ({names}). It was not "
    "registered, so as not to overwrite your own setting":
        "{key} 已经绑定到别的命令（{names}）。"
        "为了不覆盖使用者的设置，没有进行注册",
    "removed the old-style entry": "已移除旧格式的条目",
    "replaced the old-style entry with the current one":
        "已把旧格式的条目换成现在的格式",
    "registered": "已注册",

    # ---- install: キーバインドの取り消し
    "the file does not exist (nothing was done)": "文件不存在（什么都没做）",
    "there are no entries from this tool (nothing was done)":
        "没有这个工具写的条目（什么都没做）",
    "removed {n} entries": "已移除 {n} 个条目",

    # ---- install: 環境チェック
    "Warning: could not make ./dash executable ({err})":
        "警告: 无法给 ./dash 加上执行权限（{err}）",
    "Python 3.9 or newer is required (this is {v})":
        "需要 Python 3.9 以上（现在是 {v}）",
    "the following files were not found (the package may be incomplete): {list}":
        "找不到以下文件（可能是文件不齐全）: {list}",
    "cannot write to the mission storage ({path} / {reason})":
        "无法写入任务保存位置（{path} / {reason}）",
    "cannot write to the config folder of {name} ({path} / {reason})":
        "无法写入 {name} 的配置文件夹（{path} / {reason}）",

    # ---- install: 見出しと --print
    "  Subagent Dashboard — installer":
        "  Subagent Dashboard — 安装程序",
    "  What would be written (--print, so nothing is actually changed)":
        "  将要写入的内容（因为带了 --print，实际上不做任何修改）",
    "What will be added to {name} ({path}):":
        "要追加写入 {name}（{path}）的内容:",
    "The entry that will be added to keybindings.json ({path}):":
        "要添加到 keybindings.json（{path}）的条目:",
    "* The old location ({path}) still holds":
        "※ 旧的位置（{path}）里，还留着这个工具以前写的",
    "  {n} invalid entries written earlier by this tool. Running this removes them.":
        "  无效条目 {n} 个。执行之后会被移除。",

    # ---- install: ステップ 1（環境チェック）
    "Step 1/4: Environment check": "步骤 1/4: 环境检查",
    "  ✗ The following problems were found:": "  ✗ 发现了以下问题:",
    "    - {problem}": "    ・{problem}",
    "  Please solve these problems and run this again.":
        "  请解决这些问题之后再执行一次。",
    "Platform": "平台",
    "Write permission": "写入权限",
    "Tool location": "本体的位置",
    "VSCode keybinding": "VSCode 键绑定",
    "OK ({n} files, all present)": "OK（{n} 个全部确认）",
    "OK ({missions} / {config})": "OK（{missions} / {config}）",
    "OK ({path})": "OK（{path}）",
    "cannot write ({reason})": "无法写入（{reason}）",
    "the settings folder was not found ({path})":
        "找不到配置文件夹（{path}）",
    "  ⚠ You are running this from inside the distribution (under dist/).":
        "  ⚠ 正在从分发包内部（dist/ 之下）执行。",
    "     If you go on, records will be stored in {path}.":
        "     就这样继续的话，记录的保存位置会变成 {path}。",
    "     Move the unpacked folder outside dist/ before running this.":
        "     请把解压分发包得到的文件夹移到 dist/ 之外，然后再执行。",

    # ---- install: ステップ 2（自動検出）
    "Step 2/4: Automatic detection of the environment": "步骤 2/4: 环境的自动检测",
    "Dashboard location": "面板的位置",
    "Python command": "Python 执行命令",
    "Config file ({name})": "配置文件（{name}）",
    "  (leftovers in the old location: {path} / {n})":
        "  （旧的位置有残留: {path} / {n} 个）",

    # ---- install: ステップ 3（書き込み）
    "Step 3/4: Writing to the config files": "步骤 3/4: 写入配置文件",
    "  ✗ Error: cannot read {path} ({err})": "  ✗ 错误: 无法读取 {path}（{err}）",
    "  ✗ Error: {path} cannot be touched ({err})":
        "  ✗ 错误: 不能碰 {path}（{err}）",
    "    Writing now would wipe out your own text the next time --uninstall runs.":
        "    就这样写下去的话，下次执行 --uninstall 时会连使用者自己写的内容一起删掉。",
    "    Pair up the markers in {path}, then run this again.":
        "    请把 {path} 里的标记配成对，然后再执行一次。",
    "  ✗ Error: cannot write to {path} ({err})": "  ✗ 错误: 无法写入 {path}（{err}）",
    "  ✓ {name} is already up to date (no change)":
        "  ✓ {name} 已经是最新的了（无变更）",
    "  ✓ keybindings.json was updated ({msg})":
        "  ✓ 已更新 keybindings.json（{msg}）",
    "    (Ctrl+Shift+D → agentDashboard.open. "
    "It works once the extension is installed.)":
        "    （Ctrl+Shift+D → agentDashboard.open。装上扩展之后就会生效）",
    "  ✓ keybindings.json needed no change ({msg})":
        "  ✓ keybindings.json 无需改动（{msg}）",
    "  ⚠ Ctrl+Shift+D does not work ({msg})":
        "  ⚠ Ctrl+Shift+D 不会生效（{msg}）",
    "  ⚠ Ctrl+Shift+D was not registered ({msg})":
        "  ⚠ 没有注册 Ctrl+Shift+D（{msg}）",
    "    Open {path} and either drop that binding, or bind another key":
        "    请打开 {path}，去掉那个绑定，或者换一个键写上",
    '    with {{"key": "<the key you like>", "command": "{cmd}"}}.':
        '    {{"key": "<你喜欢的键>", "command": "{cmd}"}}。',
    "  ⚠ Warning: keybindings.json could not be updated ({msg})":
        "  ⚠ 警告: 无法更新 keybindings.json（{msg}）",
    "  ✓ Cleaned up the dead entries in the old location ({msg})":
        "  ✓ 已清理旧位置的无效条目（{msg}）",
    "    (VSCode does not read this location. Other entries were left alone.)":
        "    （VSCode 不会读取这个位置。其他条目都保留着）",
    "  ⚠ {n} dead entries remain in the old location: {path}":
        "  ⚠ 旧的位置里还留着 {n} 个无效条目: {path}",
    "    They could not be cleaned up ({msg}). Deleting them by hand is fine.":
        "    没能清理掉（{msg}）。手动删除也没有问题。",
    "  ⚠ The file in the old location could not be read: {path}":
        "  ⚠ 无法读取旧位置的文件: {path}",
    "    Dead entries written earlier by this tool may still be there.":
        "    那里可能还留着这个工具以前写的无效条目。",
    "  ✓ Made the launcher executable: ./dash":
        "  ✓ 已给启动器加上执行权限: ./dash",

    # ---- install: ステップ 4（完了）
    "Step 4/4: Setup complete!": "步骤 4/4: 安装完成！",
    "  🎉 The installation is complete!": "  🎉 安装已经完成！",
    "  The installation is complete (Ctrl+Shift+D was not registered).":
        "  安装已经完成（这次没有注册 Ctrl+Shift+D）。",
    "  You can open the dashboard in these ways:":
        "  可以用以下方法打开面板:",
    "  [Option 1] Start it from the command line (recommended)":
        "  【方法1】从命令行启动（推荐）",
    "  [Option 2] A VSCode keyboard shortcut":
        "  【方法2】VSCode 的键盘快捷键",
    "    Press Ctrl+Shift+D (it works once you install the extension below)":
        "    按 Ctrl+Shift+D（装上下面的扩展之后才会生效）",
    "  [Option 2] A VSCode keyboard shortcut → not registered this time":
        "  【方法2】VSCode 的键盘快捷键 → 这次没有注册",
    "    See the ⚠ above for why. Options 1 and 3 work as they are.":
        "    请看上面 ⚠ 的理由。方法1和方法3照样能用。",
    "  [Option 3] The VSCode extension (more convenient)":
        "  【方法3】VSCode 扩展（更方便）",
    "    then click the robot icon at the far left":
        "    执行之后，点击最左边的机器人图标",
    "  📖 The manual (it opens once the server is running)":
        "  📖 使用手册（启动之后打开）",
    "  🔍 If something goes wrong, run the diagnostics script":
        "  🔍 出问题时请执行诊断脚本",

    # ---- install: --uninstall
    "Config file": "配置文件",
    "Keybinding settings": "键绑定设置",
    "(the old location)": "（旧的位置）",
    "  {name} does not exist.": "  没有 {name}。",
    "Error: cannot read {path} ({err})": "错误: 无法读取 {path}（{err}）",
    "Error: cannot write to {path} ({err})": "错误: 无法写入 {path}（{err}）",
    "  Removed the settings from {name} (anything else was left alone).":
        "  已从 {name} 删除设置（其他记述都保留着）。",
    "  {name} has no settings from this tool.":
        "  {name} 里没有这个工具的设置。",
    "the keybindings.json in the old location": "旧位置的 keybindings.json",
    "  Removed the settings from {label} ({msg}).":
        "  已从 {label} 删除设置（{msg}）。",
    "    (other entries written by you were left alone)":
        "    （使用者自己写的其他条目都保留着）",
    "  Warning: deleting from {label} failed ({msg})":
        "  警告: 从 {label} 删除失败（{msg}）",
    "  Nothing was deleted.": "  什么都没有删除。",
    "  The mission records are still there: {path}":
        "  任务的记录还留着: {path}",

    # ---- install: CLI 的检测和列表
    "The CLIs this tool knows about:": "本工具支持的 CLI:",
    "For a CLI that is not on this list, point at its file directly:":
        "对于不在这个列表里的 CLI，直接指向它的文件:",
    "--agent-file needs a path to a file, not a folder":
        "--agent-file 需要一个文件路径，而不是文件夹",
    " (added by you)": "（由你添加）",
    "write to this file as well, for a CLI that is not in the list "
    "(it gets remembered)":
        "对于不在列表里的 CLI 也写入这个文件（会被记录）",
    "show the CLIs this tool knows about, and stop":
        "显示本工具支持的 CLI 并停止",
    "written": "已写入",
    "Entries you add are remembered in {path}":
        "你添加的条目会存储在 {path}",
    "installed, not written yet": "已安装，尚未写入",
    "not found on this machine": "在这台机器上找不到",
    "Error: {err}": "错误: {err}",

    # ---- install: 引数
    "First-time setup for the Subagent Dashboard": "Subagent Dashboard 的初始设置",
    "only show what would be written (changes nothing)":
        "只显示将要写入的内容（不做任何修改）",
    "undo the settings that were written": "取消已经写入的设置",
    "which CLI to write the operating rules for "
    "(the default writes to every one that is installed)":
        "写入运行规则的 CLI（默认写入所有已安装的 CLI）",
}

# ============================================================ 한국어
CATALOG["ko"] = {
    # ---- install: CLAUDE.md に書き込む本文（変更履歴トラッキングのブロック）
    CHANGELOG_BLOCK_EN: CHANGELOG_BLOCK_KO,

    '    (only the marked block is updated; anything already there is kept — including the Subagent Dashboard block above)':
        '    (마커로 둘러싸인 범위만 갱신합니다. 기존 내용은 그대로 유지됩니다——위의 Subagent Dashboard 블록 포함)',
    'What will be added to {name} ({path}) (changelog tracking block):':
        '{name}({path}) 에 추가되는 내용(변경 이력 추적 블록):',
    '  ✓ {name} (changelog tracking block) is already up to date (no change)':
        '  ✓ {name} 은(는) 이미 최신입니다(변경 이력 추적 블록. 변경 없음)',
    '  ✓ {name} was created (changelog tracking block).':
        '  ✓ {name} 을(를) 새로 만들었습니다(변경 이력 추적 블록)',
    '  ✓ The changelog tracking block was appended to {name}.':
        '  ✓ {name} 에 변경 이력 추적 블록을 추가했습니다',
    '  ✓ {name} was updated (changelog tracking block; also tidied up {n} duplicated old blocks).':
        '  ✓ {name} 을(를) 갱신했습니다(변경 이력 추적 블록. 중복된 오래된 블록 {n} 개도 정리)',
    '  ✓ {name} was updated (changelog tracking block).':
        '  ✓ {name} 을(를) 갱신했습니다(변경 이력 추적 블록)',
    '  Removed the Subagent Dashboard and changelog tracking settings from {name} (anything else was left alone).':
        '  {name} 에서 Subagent Dashboard 와 변경 이력 추적 설정을 삭제했습니다(다른 내용은 그대로 둡니다)',
    '  Removed the changelog tracking settings from {name} (anything else was left alone).':
        '  {name} 에서 변경 이력 추적 설정을 삭제했습니다(다른 내용은 그대로 둡니다)',

    # ---- install: CLAUDE.md に書き込む本文
    BLOCK_EN: BLOCK_KO,

    # ---- install: CLAUDE.md の差し替え
    "the markers ({begin} / {end}) are not paired":
        "마커({begin} / {end})가 짝을 이루고 있지 않습니다",
    "  ✓ {name} was created.": "  ✓ {name} 를 새로 만들었습니다",
    "  ✓ The settings were appended to {name}.": "  ✓ {name} 에 추가로 기록했습니다",
    "  ✓ {name} was updated.": "  ✓ {name} 를 갱신했습니다",
    "  ✓ {name} was updated (also tidied up {n} duplicated old blocks).":
        "  ✓ {name} 를 갱신했습니다 (중복되어 있던 오래된 블록 {n} 개도 정리)",
    "    (only the marked block is updated; anything already there is kept)":
        "    (마커로 둘러싸인 범위만 갱신합니다. 기존의 기술은 유지됩니다)",

    # ---- install: keybindings.json の読み書き
    "the contents are not an array (VSCode's keybindings.json is an array)":
        "내용이 배열이 아닙니다 (VSCode 의 keybindings.json 은 배열)",
    "the closing bracket of the array was not found":
        "배열의 닫는 괄호를 찾을 수 없습니다",
    "cannot create {path} ({err})": "{path} 를 만들 수 없습니다 ({err})",
    "cannot read {path} ({err})": "{path} 를 읽을 수 없습니다 ({err})",
    "{path} cannot be rewritten ({err})": "{path} 는 고쳐 쓸 수 없습니다 ({err})",
    "cannot write to {path} ({err})": "{path} 에 쓸 수 없습니다 ({err})",
    "the structure of {path} could not be read fully "
    "(nothing was changed, to be safe)":
        "{path} 의 구조를 끝까지 읽지 못했습니다 (안전을 위해 변경하지 않았습니다)",

    # ---- install: キーバインドの登録
    "the VSCode settings folder was not found ({path}). VSCode may not be "
    "installed, or you may be using Insiders / VSCodium":
        "VSCode 의 설정 폴더를 찾을 수 없습니다 ({path}). "
        "VSCode 가 설치되어 있지 않거나, Insiders / VSCodium 을 쓰고 계실 수 있습니다",
    "created the file and registered the binding": "파일을 만들어 등록했습니다",
    "it is registered, but a different binding further down ({names}) takes "
    "precedence, so Ctrl+Shift+D does not open it":
        "등록은 되어 있지만, 뒤쪽에 있는 다른 할당({names})이 "
        "우선하므로 Ctrl+Shift+D 로는 열리지 않습니다",
    "already registered (no change)": "이미 등록되어 있습니다 (변경 없음)",
    "{key} is already bound to a different command ({names}). It was not "
    "registered, so as not to overwrite your own setting":
        "{key} 는 이미 다른 명령({names})에 할당되어 있습니다. "
        "사용자의 설정을 덮어쓰지 않기 위해 등록하지 않았습니다",
    "removed the old-style entry": "옛 형식의 항목을 제거했습니다",
    "replaced the old-style entry with the current one":
        "옛 형식의 항목을 지금의 형식으로 바꿨습니다",
    "registered": "등록했습니다",

    # ---- install: キーバインドの取り消し
    "the file does not exist (nothing was done)":
        "파일이 없습니다 (아무것도 하지 않았습니다)",
    "there are no entries from this tool (nothing was done)":
        "이 도구의 항목은 없습니다 (아무것도 하지 않았습니다)",
    "removed {n} entries": "{n} 개의 항목을 제거했습니다",

    # ---- install: 環境チェック
    "Warning: could not make ./dash executable ({err})":
        "경고: ./dash 에 실행 권한을 주지 못했습니다 ({err})",
    "Python 3.9 or newer is required (this is {v})":
        "Python 3.9 이상이 필요합니다 (지금은 {v})",
    "the following files were not found (the package may be incomplete): {list}":
        "다음 파일을 찾을 수 없습니다 (파일이 갖춰져 있지 않을 수 있습니다): {list}",
    "cannot write to the mission storage ({path} / {reason})":
        "미션 저장 위치에 쓸 수 없습니다 ({path} / {reason})",
    "cannot write to the config folder of {name} ({path} / {reason})":
        "{name} 의 설정 폴더에 쓸 수 없습니다 ({path} / {reason})",

    # ---- install: 見出しと --print
    "  Subagent Dashboard — installer":
        "  Subagent Dashboard — 설치 프로그램",
    "  What would be written (--print, so nothing is actually changed)":
        "  기록할 내용 (--print 이므로 실제로는 변경하지 않습니다)",
    "What will be added to {name} ({path}):":
        "{name} ({path}) 에 추가로 기록할 내용:",
    "The entry that will be added to keybindings.json ({path}):":
        "keybindings.json ({path}) 에 추가할 항목:",
    "* The old location ({path}) still holds":
        "※ 옛 위치({path}) 에 이 도구가 이전에 기록한",
    "  {n} invalid entries written earlier by this tool. Running this removes them.":
        "  무효한 항목이 {n} 개 남아 있습니다. 실행하면 제거합니다.",

    # ---- install: ステップ 1（環境チェック）
    "Step 1/4: Environment check": "단계 1/4: 환경 점검",
    "  ✗ The following problems were found:": "  ✗ 다음 문제가 발견되었습니다:",
    "    - {problem}": "    ・{problem}",
    "  Please solve these problems and run this again.":
        "  이 문제들을 해결한 뒤 다시 실행하세요.",
    "Platform": "플랫폼",
    "Write permission": "쓰기 권한",
    "Tool location": "도구의 위치",
    "VSCode keybinding": "VSCode 키 바인딩",
    "OK ({n} files, all present)": "OK ({n} 건 모두 확인)",
    "OK ({missions} / {config})": "OK ({missions} / {config})",
    "OK ({path})": "OK ({path})",
    "cannot write ({reason})": "쓸 수 없습니다 ({reason})",
    "the settings folder was not found ({path})":
        "설정 폴더를 찾을 수 없습니다 ({path})",
    "  ⚠ You are running this from inside the distribution (under dist/).":
        "  ⚠ 배포물 안(dist/ 아래)에서 실행하고 있습니다.",
    "     If you go on, records will be stored in {path}.":
        "     이대로 진행하면 기록의 저장 위치가 {path} 가 됩니다.",
    "     Move the unpacked folder outside dist/ before running this.":
        "     배포물을 푼 폴더를 dist/ 밖으로 옮긴 뒤 실행하세요.",

    # ---- install: ステップ 2（自動検出）
    "Step 2/4: Automatic detection of the environment": "단계 2/4: 환경 자동 검출",
    "Dashboard location": "대시보드의 위치",
    "Python command": "Python 실행 명령",
    "Config file ({name})": "설정 파일 ({name})",
    "  (leftovers in the old location: {path} / {n})":
        "  (옛 위치에 잔재 있음: {path} / {n} 개)",

    # ---- install: ステップ 3（書き込み）
    "Step 3/4: Writing to the config files": "단계 3/4: 설정 파일에 기록",
    "  ✗ Error: cannot read {path} ({err})":
        "  ✗ 오류: {path} 를 읽을 수 없습니다 ({err})",
    "  ✗ Error: {path} cannot be touched ({err})":
        "  ✗ 오류: {path} 에 손을 댈 수 없습니다 ({err})",
    "    Writing now would wipe out your own text the next time --uninstall runs.":
        "    이대로 기록하면 다음에 --uninstall 했을 때 사용자가 쓴 내용까지 지워집니다.",
    "    Pair up the markers in {path}, then run this again.":
        "    {path} 의 마커를 짝으로 맞춘 뒤 다시 실행하세요.",
    "  ✗ Error: cannot write to {path} ({err})":
        "  ✗ 오류: {path} 에 쓸 수 없습니다 ({err})",
    "  ✓ {name} is already up to date (no change)":
        "  ✓ {name} 는 이미 최신입니다 (변경 없음)",
    "  ✓ keybindings.json was updated ({msg})":
        "  ✓ keybindings.json 을 갱신했습니다 ({msg})",
    "    (Ctrl+Shift+D → agentDashboard.open. "
    "It works once the extension is installed.)":
        "    (Ctrl+Shift+D → agentDashboard.open. 확장을 설치하면 작동합니다)",
    "  ✓ keybindings.json needed no change ({msg})":
        "  ✓ keybindings.json 은 고칠 필요가 없었습니다 ({msg})",
    "  ⚠ Ctrl+Shift+D does not work ({msg})":
        "  ⚠ Ctrl+Shift+D 는 듣지 않습니다 ({msg})",
    "  ⚠ Ctrl+Shift+D was not registered ({msg})":
        "  ⚠ Ctrl+Shift+D 는 등록하지 않았습니다 ({msg})",
    "    Open {path} and either drop that binding, or bind another key":
        "    {path} 를 열어 그 할당을 없애거나, 다른 키에",
    '    with {{"key": "<the key you like>", "command": "{cmd}"}}.':
        '    {{"key": "<원하는 키>", "command": "{cmd}"}} 를 적어 주세요.',
    "  ⚠ Warning: keybindings.json could not be updated ({msg})":
        "  ⚠ 경고: keybindings.json 을 갱신하지 못했습니다 ({msg})",
    "  ✓ Cleaned up the dead entries in the old location ({msg})":
        "  ✓ 옛 위치의 무효한 항목을 정리했습니다 ({msg})",
    "    (VSCode does not read this location. Other entries were left alone.)":
        "    (VSCode 는 이 위치를 읽지 않습니다. 다른 항목은 그대로 두었습니다)",
    "  ⚠ {n} dead entries remain in the old location: {path}":
        "  ⚠ 옛 위치에 무효한 항목이 {n} 개 남아 있습니다: {path}",
    "    They could not be cleaned up ({msg}). Deleting them by hand is fine.":
        "    정리하지 못했습니다 ({msg}). 직접 지워도 문제없습니다.",
    "  ⚠ The file in the old location could not be read: {path}":
        "  ⚠ 옛 위치의 파일을 읽지 못했습니다: {path}",
    "    Dead entries written earlier by this tool may still be there.":
        "    이 도구가 이전에 기록한 무효한 항목이 남아 있을 수 있습니다.",
    "  ✓ Made the launcher executable: ./dash":
        "  ✓ 런처에 실행 권한을 주었습니다: ./dash",

    # ---- install: ステップ 4（完了）
    "Step 4/4: Setup complete!": "단계 4/4: 설치 완료!",
    "  🎉 The installation is complete!": "  🎉 설치가 완료되었습니다!",
    "  The installation is complete (Ctrl+Shift+D was not registered).":
        "  설치가 완료되었습니다 (Ctrl+Shift+D 등록은 보류했습니다).",
    "  You can open the dashboard in these ways:":
        "  다음 방법으로 대시보드를 열 수 있습니다:",
    "  [Option 1] Start it from the command line (recommended)":
        "  【방법1】명령으로 시작 (권장)",
    "  [Option 2] A VSCode keyboard shortcut":
        "  【방법2】VSCode 의 키보드 단축키",
    "    Press Ctrl+Shift+D (it works once you install the extension below)":
        "    Ctrl+Shift+D 를 누른다 (아래의 확장을 설치해야 작동합니다)",
    "  [Option 2] A VSCode keyboard shortcut → not registered this time":
        "  【방법2】VSCode 의 키보드 단축키 → 이번에는 등록하지 않았습니다",
    "    See the ⚠ above for why. Options 1 and 3 work as they are.":
        "    위의 ⚠ 이유를 봐 주세요. 방법1과 방법3은 그대로 쓸 수 있습니다.",
    "  [Option 3] The VSCode extension (more convenient)":
        "  【방법3】VSCode 확장 (더 편리)",
    "    then click the robot icon at the far left":
        "    를 실행한 뒤, 맨 왼쪽의 로봇 아이콘을 클릭",
    "  📖 The manual (it opens once the server is running)":
        "  📖 사용 설명서 (시작한 뒤에 열립니다)",
    "  🔍 If something goes wrong, run the diagnostics script":
        "  🔍 문제가 생기면 진단 스크립트를 실행",

    # ---- install: --uninstall
    "Config file": "설정 파일",
    "Keybinding settings": "키 바인딩 설정",
    "(the old location)": "(옛 위치)",
    "  {name} does not exist.": "  {name} 가 없습니다.",
    "Error: cannot read {path} ({err})": "오류: {path} 를 읽을 수 없습니다 ({err})",
    "Error: cannot write to {path} ({err})": "오류: {path} 에 쓸 수 없습니다 ({err})",
    "  Removed the settings from {name} (anything else was left alone).":
        "  {name} 에서 설정을 삭제했습니다 (다른 기술은 남겨 두었습니다).",
    "  {name} has no settings from this tool.":
        "  {name} 에는 이 도구의 설정이 없습니다.",
    "the keybindings.json in the old location": "옛 위치의 keybindings.json",
    "  Removed the settings from {label} ({msg}).":
        "  {label} 에서 설정을 삭제했습니다 ({msg}).",
    "    (other entries written by you were left alone)":
        "    (사용자가 쓴 다른 항목은 남겨 두었습니다)",
    "  Warning: deleting from {label} failed ({msg})":
        "  경고: {label} 에서 삭제에 실패했습니다 ({msg})",
    "  Nothing was deleted.": "  아무것도 삭제되지 않았습니다.",
    "  The mission records are still there: {path}":
        "  미션의 기록은 남아 있습니다: {path}",

    # ---- install: CLI 의 검출과 목록
    "The CLIs this tool knows about:": "이 도구가 지원하는 CLI:",
    "For a CLI that is not on this list, point at its file directly:":
        "목록에 없는 CLI 는 파일을 직접 가리키세요:",
    "--agent-file needs a path to a file, not a folder":
        "--agent-file 은 폴더가 아닌 파일 경로가 필요합니다",
    " (added by you)": "（직접 추가함）",
    "write to this file as well, for a CLI that is not in the list "
    "(it gets remembered)":
        "목록에 없는 CLI 용으로도 이 파일에 기록합니다 (저장됩니다)",
    "show the CLIs this tool knows about, and stop":
        "이 도구가 지원하는 CLI 를 표시하고 종료합니다",
    "written": "기록 완료",
    "Entries you add are remembered in {path}":
        "추가한 항목은 {path} 에 저장됩니다",
    "installed, not written yet": "설치되어 있지만 아직 기록되지 않음",
    "not found on this machine": "이 컴퓨터에서 찾을 수 없습니다",
    "Error: {err}": "오류: {err}",

    # ---- install: 引数
    "First-time setup for the Subagent Dashboard":
        "Subagent Dashboard 의 초기 설정",
    "only show what would be written (changes nothing)":
        "기록할 내용을 표시만 한다 (아무것도 변경하지 않는다)",
    "undo the settings that were written": "기록한 설정을 취소한다",
    "which CLI to write the operating rules for "
    "(the default writes to every one that is installed)":
        "운용 규칙을 기록할 CLI (기본값은 설치되어 있는 CLI 전부)",
}
