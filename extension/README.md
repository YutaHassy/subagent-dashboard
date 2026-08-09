# Subagent Dashboard

Claude Code のサブエージェントの動きを系統樹で見る「Subagent Dashboard」を、どのプロジェクトを開いていても VSCode の中に出す拡張機能です。

**ダッシュボード本体を同梱しているので、これ1つで動きます。**

## 使い方

左端のアクティビティバーに増えたロボットのアイコンを押すと、エディタのタブに Subagent Dashboard が出ます。

初回だけ「本体をこの場所に置きます」と確認が出ます。置き場所は `~/.claude/agent-dashboard`（Windows なら `C:\Users\<名前>\.claude\agent-dashboard`）です。以後の作業記録もここに溜まります。

左側に細長く置いておきたいときは、設定 `agentDashboard.sidebarBehavior` を `embed` にすると、アイコンを押したときサイドバーの中に表示します（その場合、広く見たくなったらタイトルバーの **⧉（タブで開く）** を押します）。

ステータスバー左下の **🤖 Subagent Dashboard** からも同じように開けます。

| コマンド | 何をするか |
|---|---|
| Subagent Dashboard: タブで開く | エディタのタブに Subagent Dashboard を出す |
| Subagent Dashboard: ブラウザで開く | OS の既定ブラウザで開く |
| Subagent Dashboard: サーバーを再起動 | この拡張が起動したサーバーを止めて立て直す |
| Subagent Dashboard: サーバーを停止 | この拡張が起動したサーバーを止める |
| Subagent Dashboard: 本体を配置／更新 | 同梱している本体を配置先へ置く |
| Subagent Dashboard: 初期設定を実行 | 初期設定（`install.py`）を確認のうえ実行する |
| Subagent Dashboard: 初期設定のフラグをリセット | 「もう済んでいる」記録を消し、次回また確認を出す |
| Subagent Dashboard: ログを表示 | 起動の経過と Python 側の出力を見る |

サーバーが動いていなければ拡張が起動します。すでに動いていればそれを使い回すので、プロセスが増えていくことはありません。ポートが埋まっていれば次の番号へ繰り上げ、その番号で画面を開きます。

外（ターミナルの `dash serve` など）で立てたサーバーは、拡張は使い回すだけで勝手に止めません。

キーバインドは既定では割り当てていません。`Ctrl+Shift+D` は VSCode 標準の「実行とデバッグ」が使っているので、欲しい場合は別のキーを自分で割り当ててください。

```json
// keybindings.json
{ "key": "ctrl+alt+d", "command": "agentDashboard.open" }
```

## 設定

| 設定 | 既定 | 意味 |
|---|---|---|
| `agentDashboard.port` | `3939` | 最初に試すポート。埋まっていたら空きへ繰り上げる |
| `agentDashboard.home` | （空） | 本体の場所。空なら `~/.claude/agent-dashboard` |
| `agentDashboard.pythonPath` | （空） | 使う Python。空なら自動検出 |
| `agentDashboard.openIn` | `webview` | 「タブで開く」の表示先。`webview` / `simpleBrowser` / `external` |
| `agentDashboard.sidebarBehavior` | `openInTab` | アイコンを押したときの動き。`openInTab`（タブへ移してサイドバーを閉じる） / `embed`（サイドバーの中に出す） |
| `agentDashboard.autoStartServer` | `true` | 開くときサーバーが居なければ立てる |
| `agentDashboard.showStatusBar` | `true` | ステータスバーにボタンを出す |
| `agentDashboard.stopServerOnExit` | `true` | VSCode 終了時に、この拡張が立てたサーバーを止める |
| `agentDashboard.runSetupOnFirstRun` | `true` | 初めて使うとき、初期設定（`install.py`）を実行してよいか尋ねる |
| `agentDashboard.autoUpdateOnNewVersion` | `true` | 拡張を新しくしたとき、本体の更新を尋ねる |

`home` と `pythonPath` はユーザー設定にしか書けません。開いているフォルダ側の設定から実行対象を差し替えられないようにするためです。

環境変数 `AGENT_DASHBOARD_DEPLOY_DIR` を設定すると、本体の置き場所を `~/.claude/agent-dashboard` 以外にできます。

## 動くための前提

- VSCode 1.74 以降
- Python 3.9 以降（外部パッケージは不要）

## うまく動かないとき

まず **「Subagent Dashboard: ログを表示」** を見てください。どこで止まったかが日本語で出ます。

| 症状 | 見るところ |
|---|---|
| 「Python が見つかりません」 | `agentDashboard.pythonPath` に実行ファイルのパスを入れる |
| 「本体が見つかりません」 | 「本体を配置／更新」を実行する |
| 画面が真っ黒 | 設定 `openIn` を `external` にして、ブラウザでは見えるか確かめる |
| ポートが変わる | ログに「ポート … は別のものが使用中」と出ていないか確認。`port` を空いている番号に変える |
| 「Subagent Dashboard を表示できません」の画面で止まる | 通知を見逃したときの逃げ道。画面に並ぶボタンから続けられる。原因ごとに先頭のボタンが変わる（本体を配置／設定を開く／Python のパスを設定／ポートを設定）。「もう一度試す」「初期設定を実行」も添えられている |

## 仕組み

拡張がやるのは 4 つだけです。

1. 本体が無ければ、同梱している荷物を `~/.claude/agent-dashboard` へ**配置する**。同梱物の場所では動かさない（拡張フォルダはバージョンごとに変わるので、そこに記録を置くと更新で消える）
2. `GET /api/env` で生存確認し、返ってきた `toolRoot` が期待する場所と一致するかを見る。別アプリがポートを掴んでいても誤認しない
3. 空きポートを自分で決めて `dash.py serve --port <番号> --no-retry` で起動する。サーバー側の繰り上げを止めているので、拡張は常に正しい URL を知っている
4. その URL を `<iframe>` に入れてサイドバーとタブに出す

表示のロジックはすべてダッシュボード本体（`public/index.html`）側にあります。拡張は起動と表示の面倒を見るだけの薄い層です。
