# Changelog

Claude Code の変更履歴の自動記録（`changelog_cli.py summarize` により生成。手で編集しても次の summarize で上書きされる）。

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
