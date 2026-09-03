# Changelog

Claude Code の変更履歴の自動記録（`changelog_cli.py summarize` により生成。手で編集しても次の summarize で上書きされる）。

## 2026-09-03 17:28:44 — 機体色変更計画の md と html をリポジトリ直下に保存（git に上げるため）

前の要約で作成した計画書とプレビューHTMLを、ユーザーの指示でリポジトリ直下へ「機体色変更計画」の名前で保存した。

- 機体色変更計画.md  … C:\Users\J0116829\.claude\plans\merry-finding-popcorn.md をコピー（20038 バイト）
- 機体色変更計画.html … セッションのスクラッチパッドの robot-color-preview.html をコピー（28681 バイト）

置き場所は README.md / OPERATION.md / RESTORE_NOTES.md と同じリポジトリ直下（フラットに並べる既存の流儀に合わせた）。

コピー後に md を1箇所編集した: プレビューへのリンクが一時ディレクトリの絶対パスだったので、相対リンク [機体色変更計画.html](機体色変更計画.html) に置き換えた。

改行コードは両ファイルとも LF のままであることを grep -c で確認済み（0 件）。このリポジトリの .gitattributes は * -text で Git に変換させない設定のため、書いたバイトがそのままコミットされる。

git status では 2 件とも未追跡（??）。既存の 0.9.1 関連の変更 20 件ほどは今回触っていない。ダッシュボードの実装コード（public/index.html 等）は依然として未変更で、実装は未着手のまま。

- セッション: `763d583d-1d1d-41fb-bbd9-29c6f216b9f2`

---

## 2026-09-02 16:53:39 — 実物で見つけた2件（指令塔への誤った実測表示／孤児の沈黙）を d1929b3 にコミットした。版は上げていない

ユーザーの指示は「先にコミットだけしてください」。リリースはせず、コミットのみ。

■ コミット d1929b3（feature/wiring-under、3ファイル +77/-4）
- livefeed.py: assign_live の running から COMMAND_ID を外した。指令塔は主セッションであってサブエージェントではなく、その記録は <slug>/<sessionId>.jsonl で subagents/ の下には無いため、agent-*.jsonl が指令塔であることは原理的にありえない。あわせて親は meta.json の parentAgentId を優先し、候補から外れた機体の description も known_desc に覚えるようにした。
- check_livefeed.py: 検査 [25] を新設（指令塔に実測を載せない／meta の parentAgentId から起動元が出る）。
- public/index.html: 孤児の行に沈黙の長さ（live.quiet / live.stalled）を出す。idleSec が読めないときは出さない。

■ コミットメッセージに残した実測
- 孤児にならず指令塔に載った実例（orphan-demo 16:30、孫 ae4751e2f）
- その孫の meta.json の中身が agentType / description / toolUseId / parentAgentId / spawnDepth の5つだけで model が無いこと
- 終わった孤児が残る実例（16:36:5x に終了、16:37:15 時点で state=active）
- ログに終端の印が無いこと（全38行、末尾3行を確認。最後は assistant/text）
- 検査 [25] が直す前のコードで実際に落ちること

■ 版とリモート
extension/package.json と VERSION は 0.7.3 のまま。push もマージもしていないので main は 1d47ed6 のまま。

■ 残っている判断（ユーザー待ち）
1. 自動登録（PreToolUse:Agent で add、SubagentStop で done）に着手するか
2. orphan-demo2 を finish してよいか
3. 検証用サーバー 3960 / 3953 / 3954 を止めてよいか

- セッション: `82c684a9-727d-4a7e-a09b-daf186db21cd`

---

## 2026-09-01 08:56:03 — サブエージェントの稼働をリアルタイムに映す機能の調査と計画策定（コード変更なし）

Explore サブエージェント2体で agent-dashboard の構造（server.py / dashlib.py / update_state.py / public/index.html / hooks / changelog）と、Claude Code がサブエージェントの活動をどこに書き出しているかを調査。~/.claude/projects/<slug>/<sessionId>/subagents/agent-<agentId>.jsonl が稼働中にリアルタイム追記されること、親セッション JSONL の toolUseResult が agentId の名簿になること、changelog フックは親の session_id しか持たず帰属できないことを実データで確認した。結果を計画書 ~/.claude/plans/synthetic-honking-flask.md にまとめ、memory に live-subagent-feed-source.md を追加、dashboard-workflow-done-gap.md と MEMORY.md を更新。プロジェクトのソースコードは一切変更していない。

- セッション: `5f9681c8-2e83-49f0-9529-003290cc08a8`

---
