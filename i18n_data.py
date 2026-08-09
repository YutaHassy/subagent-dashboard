#!/usr/bin/env python3
"""コマンド出力の翻訳表。

**鍵は英語の原文そのもの**（i18n.py の t() を参照）。原文を書き換えたら、ここの
鍵も一緒に書き換えること。合っていない鍵は「訳が無い」と見なされて英語で出る
——静かに落ちるのではなく、英語で出たら訳し漏れ、と読めるようにしてある。

抜けを数えるには:

    python -c "import i18n; print(len(i18n.missing('zh')))"

`{name}` の差し込みは呼び手が .format() で行う。**訳文でも同じ名前を残すこと。**
語順は言語ごとに変えてよいが、名前を変えたり落としたりすると KeyError になる。

外部ライブラリは使いません（Python 標準ライブラリのみ）。
"""

from __future__ import annotations

CATALOG: dict[str, dict[str, str]] = {}

# ============================================================ 日本語
CATALOG["ja"] = {
    # ---- update_state: lang コマンド
    'unknown language: {lang} (choose from {list})':
        '不明な言語です: {lang}（{list} から選んでください）',
    'show or set the language of these messages':
        'これらのメッセージの言語を表示／設定する',
    'en / ja / zh / ko (omit to show the current setting)':
        'en / ja / zh / ko（省略すると現在の設定を表示）',
    'Language: {label} ({code})':
        '言語: {label}（{code}）',
    '  detected from the operating system':
        '  OS から判定しました',
    '  available: {list}':
        '  選べるもの: {list}',
    'Language set to {label} ({code}).':
        '言語を {label}（{code}）に設定しました。',
    '  saved in {path}':
        '  保存先: {path}',
    '  from the environment variable {var}={value}':
        '  環境変数 {var}={value} によります',
    '  note: {var} is set, so it takes precedence over this setting.':
        '  注意: {var} が設定されているので、そちらがこの設定より優先されます。',
    '  from the saved setting {path}':
        '  保存された設定 {path} によります',
    'Could not set the language: {err}':
        '言語を設定できませんでした: {err}',

    # ---- 自由記述の言語チェック
    "  Write the free text (--title / --name / --mission / --headline) "
    "in this language: {label} ({code}).":
        "  自由記述（--title / --name / --mission / --headline）を"
        "この言語で書いてください: {label}（{code}）。",
    '{flag} "{value}"':
        '{flag} "{value}"',
    "  ⚠️  This does not look like {label} ({code}), the language that is set: "
    "{fields}":
        "  ⚠️  {label}（{code}）には見えません（設定されている言語です）: "
        "{fields}",
    "      If that was a mistake, run the same command again with the same --id\n"
    "      and the corrected text. The value is replaced and the measured values\n"
    "      are kept (the event log keeps the line it already wrote).":
        "      間違っていたら、同じ --id で同じコマンドを実行し直してください\n"
        "      テキストを修正してください。値は置き換わり、実測値は保たれます\n"
        "      （イベントログはすでに書いた行を保ちます）。",
    "      The mission title cannot be corrected afterwards. Only a new start can\n"
    "      change it, and that archives this mission while it is still running.":
        "      ミッションのタイトルはあとから直せません。新しい start だけで\n"
        "      変えられます。稼働中のまま、このミッションをアーカイブします。",
    "      If it was deliberate (a proper noun, a call sign), ignore this.":
        "      もしそれが意図的なもの（固有名詞、コールサイン）なら、無視してください。",
    "         The measured values and the status are kept "
    "(only what you passed is replaced).":
        "         実測値と状態は保たれます"
        "（渡されたものだけが置き換わります）。",
    "{name} ({id}) was rewritten — {mission}":
        "{name}（{id}）は書き直されました — {mission}",
    "initial state (running when omitted; kept as it is "
    "when the unit already exists)":
        "初期状態（省略時は running；機体が既に存在するときは保持）",

    '  The operating rules were rewritten in this language: {path}':
        '  運用ルールをこの言語で書き直しました: {path}',
    "  Restart the agent's session "
    "(the operating rules are read when it starts).":
        '  エージェントのセッションを開き直してください'
        '（運用ルールは開始時に読み込まれます）。',
    '  ⚠️  Could not rewrite the operating rules ({path}): {err}':
        '  ⚠️  運用ルールを書き直せませんでした（{path}）: {err}',
    '      Rewrite them in the new language by running:':
        '      新しい言語で書き直すには、次を実行してください:',
    '  note: the operating rules of this copy are not written anywhere, '
    'so only the messages above changed.':
        '  注意: このコピーの運用ルールはどこにも書かれていないので、'
        '変わったのは上のメッセージだけです。',

    # ---- dash: コマンド一覧（dash --help）
    '\nSubagent Dashboard\n\n  Open the screen\n    dash serve                 start the server (leave it running)\n    dash serve --open          start it and open a browser too\n    dash serve --port 4000     choose the port\n\n  First-time setup\n    dash install               write the operating rules into the agent\'s config file\n    dash install --print       only show what would be written (changes nothing)\n\n  Build a distribution package\n    dash package               build the full package (ZIP + VSIX + setup guide)\n\n  VSCode extension\n    dash ext install           build the extension and install it into VSCode\n    dash ext package           build the full distribution (.vsix + guide, to email)\n    dash ext build             build only the .vsix (lands in dist/)\n    dash ext status            check whether it is installed\n    dash ext uninstall         remove the extension\n\n  Update the state (normally the agent runs these automatically)\n    dash start  --title "name of the work"\n    dash add    --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "the task"\n    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "result summary"\n    dash finish --headline "overall summary"\n\n  Inspect and misc\n    dash status                show the contents of the current project\n    dash projects              list the registered projects\n    dash demo                  fill in dummy data for checking the display\n    dash reset [--purge]       empty the current project (the tab stays)\n    dash remove [--yes]        delete the current project\'s records (the tab goes)\n    dash log --text "..."      append one line to the event log\n    dash lang <en|ja|zh|ko>    choose the language of these messages\n\n  For details on each command, run  dash <command> --help\n':
        '\nSubagent Dashboard\n\n  画面を開く\n    dash serve                 サーバーを起動する（そのまま起動しっぱなしにする）\n    dash serve --open          起動してブラウザも開く\n    dash serve --port 4000     ポートを指定する\n\n  初期設定\n    dash install               エージェントの設定ファイルに運用ルールを書き込む\n    dash install --print       書き込む内容を確認するだけ（変更しない）\n\n  配布パッケージ作成\n    dash package               配布用パッケージ一式を作る（ZIP + VSIX + 手順書）\n\n  VSCode 拡張機能\n    dash ext install           拡張機能を組み立てて VSCode に入れる\n    dash ext package           配布物一式を作る（.vsix と手順書。メール添付用）\n    dash ext build             .vsix を作るだけ（dist/ に出る）\n    dash ext status            入っているか確認する\n    dash ext uninstall         拡張機能を抜く\n\n  状態の更新（通常はエージェントが自動で実行する）\n    dash start  --title "作業の名前"\n    dash add    --id SCOUT-A --name "偵察A" --model claude-sonnet-5 --mission "任務内容"\n    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "結果の要約"\n    dash finish --headline "全体の要約"\n\n  確認・その他\n    dash status                いまのプロジェクトの中身を表示\n    dash projects              登録済みプロジェクトの一覧\n    dash demo                  表示確認用のダミーデータを入れる\n    dash reset [--purge]       いまのプロジェクトを空にする（タブは残る）\n    dash remove [--yes]        いまのプロジェクトの記録ごと削除（タブが消える）\n    dash log --text "..."      イベントログに1行足す\n    dash lang <en|ja|zh|ko>    これらのメッセージの言語を選ぶ\n\n  各コマンドの詳細は  dash <コマンド> --help  で表示されます。\n',

    # ---- dashlib: JSON の読み取り
    "not created yet": "未作成",
    "empty file": "空ファイル",
    "not readable as UTF-8 ({reason})": "UTF-8 として読めません（{reason}）",
    "not readable as JSON ({msg} / line {line}, column {col})":
        "JSONとして読めません（{msg} / {line}行{col}文字目）",
    "not readable as JSON ({err})": "JSON として読めません（{err}）",

    # ---- dashlib: 版のずれ
    "no version recorded": "版の記載なし",
    "{name} ({where})": "{name}（{where}）",
    "version {v}": "版 {v}",
    "  ⚠️  The operating rules are older than the tool "
    "({stale} / tool version {current}).":
        "  ⚠️  運用ルールが本体より古いままです（{stale} / 本体 版 {current}）。",
    "      Updating the tool does not update the rules. Please run:":
        "      本体を新しくしても、運用ルールは自動では更新されません。次を実行してください:",
    "      (Only the marked block is replaced. Nothing else is touched.)":
        "      （マーカーで囲まれた範囲だけが差し替わります。他の記述には触れません）",
    "  ⚠️  {names} is installed, but the operating rules have not been written for it.":
        "  ⚠️  {names} がインストールされていますが、このツール向けの運用ルールが書かれていません。",
    "      It was probably installed after the setup ran. Until you write them,":
        "      セットアップ実行後にインストールされた可能性があります。書き込むまでの間、",
    "      subagents started from it will not show up on the screen. Please run:":
        "      そこから起動したサブエージェントは画面に表示されません。次を実行してください:",
    "      (Only the marked block is written. Nothing else is touched.)":
        "      （マーカーで囲まれた範囲だけが書き込まれます。他の記述には触れません）",
    "      Cause: a CLI was installed after the setup ran, so it has no operating rules":
        "      原因: セットアップ実行後に CLI がインストールされたため、運用ルールがない",

    # ---- dashlib: 警告と失敗
    "⚠️  Warning: {what}": "⚠️  警告: {what}",
    "   Cause: {err}": "   原因: {err}",
    "Failed to write the .current file": ".current ファイルの書き込みに失敗しました",
    "this mission may not appear on the dashboard":
        "ダッシュボードに表示されない可能性があります",
    "Could not move the previous mission into history/":
        "前のミッションを history/ へ退避できませんでした",
    "this start will overwrite the previous record (the mission still begins)":
        "今回の start で前の記録は上書きされます（ミッションの開始は続行します）",
    "Could not move old records from history/ into trash/":
        "history/ の古い記録を trash/ へ移せませんでした",

    # ---- dashlib: 検証
    "invalid slug: {slug!r}": "スラッグが不正です: {slug!r}",
    "invalid runId: {run_id!r}": "runId が不正です: {run_id!r}",
    "missions/{slug}/ does not exist": "missions/{slug}/ がありません",
    "missions/{slug}/state.json does not exist": "missions/{slug}/state.json がありません",
    "missions/{slug}/history/{run_id}/ does not exist":
        "missions/{slug}/history/{run_id}/ がありません",
    "missions/{slug}/history/{run_id}/state.json does not exist":
        "missions/{slug}/history/{run_id}/state.json がありません",
    "not directly under missions/: {path}": "missions/ の直下ではありません: {path}",
    "not directly under history/: {path}": "history/ の直下ではありません: {path}",
    "cannot read state.json ({err})": "state.json を読めません（{err}）",
    "a mission that has not finished cannot be deleted":
        "まだ完了していないミッションは削除できません",
    'the project hint "{hint}" matches {n} projects: {list}':
        "プロジェクト指定「{hint}」が {n} 件に一致します: {list}",
    "cannot read agents/ ({err})": "agents/ を読めません（{err}）",
    "cannot read agents/{name} ({err})": "agents/{name} を読めません（{err}）",
    "agents/{name} contains an invalid agent definition":
        "agents/{name} に不正なエージェント定義があります",

    # ---- dashlib: 値が無いとき
    "(no mission started)": "（ミッション未開始）",
    "(untitled mission)": "（無題のミッション）",

    # ---- server: HTTP
    "{path} accepts only {allow}": "{path} は {allow} のみ受け付けます",
    "{path} does not accept POST": "{path} は POST を受け付けません",
    "Content-Type must be application/json": "Content-Type は application/json にしてください",
    "Content-Length is invalid": "Content-Length が不正です",
    "the request body is empty": "本文がありません",
    "the request body is too large": "本文が大きすぎます",
    "please send a JSON object": "JSON オブジェクトを送ってください",
    "requests from another origin are not accepted": "別オリジンからの操作は受け付けません",
    "specify a valid slug": "slug を正しく指定してください",
    "specify a valid runId": "runId を正しく指定してください",
    "{slug} has no record {run_id}": "{slug} に記録 {run_id} がありません",
    "{slug} has no records": "{slug} の記録がありません",
    "the record is not in the expected shape": "記録の形が想定と違います",
    "404 — {path} was not found": "404 — {path} が見つかりません",
    "failed to read: {err}": "読み込みに失敗しました: {err}",

    # ---- server: 削除
    "  Deleted the record: {slug}": "  記録を削除しました: {slug}",
    " (deleted permanently)": "（完全削除）",
    "  Deleted records: {n}": "  履歴を削除しました: {n} 件",
    " ({n} failed)": "（失敗 {n} 件）",
    "runs must list at least one {slug, runId} entry":
        "runs には {slug, runId} を1件以上並べてください",
    "runs[{i}] is not an object": "runs[{i}] がオブジェクトではありません",
    "runs[{i}].slug is invalid": "runs[{i}].slug が不正です",
    "runs[{i}].runId is invalid": "runs[{i}].runId が不正です",
    "phase must be one of {list}": "phase は {list} のいずれかにしてください",
    "specify either runs or phase": "runs か phase を指定してください",
    "permanent is not accepted (records are always moved to the trash)":
        "permanent は受け付けません（履歴は必ずゴミ箱へ移します）",
    "no such record": "記録がありません",

    # ---- server: 起動時のバナー
    "Port {port} is in use. Trying {next}…": "ポート {port} は使用中。{next} を試します…",
    "Failed to start: {err}": "起動に失敗しました: {err}",
    "No free port was found. Use --port to choose another one.":
        "空きポートが見つかりませんでした。--port で別のポートを指定してください。",
    "  Subagent Dashboard": "  Subagent Dashboard",
    "  Screen        {url}": "  画面          {url}",
    "  Manual        {url}": "  取扱説明書    {url}",
    "  Tool          {path}": "  ツール        {path}",
    "  Missions      {path}": "  ミッション    {path}",
    "  * Listening on {host}. Other machines on the same network can reach it.":
        "  ※ {host} で待ち受けています。同じネットワークの他端末からも見えます。",
    "standby": "待機中",
    "running": "稼働中",
    "done": "完了",
    "  Teams on screen  {n}": "  いま映すチーム  {n} 件",
    "    - {name} ({phase} / {done}/{total} done) {title}":
        "    - {name}（{phase} / {done}/{total} 完了） {title}",
    "  Teams on screen  none (standby screen)": "  いま映すチーム  なし（待機画面）",
    "    → In your working folder, run  {cmd} update_state.py start":
        "    → 作業するフォルダで  {cmd} update_state.py start  を実行してください",
    "  Stop          Ctrl+C": "  停止          Ctrl+C",
    "Stopped.": "停止しました。",

    # ---- server: 引数
    "The serving process for the Subagent Dashboard":
        "Subagent Dashboard の配信サーバー",
    "port to listen on (default {port}; the PORT environment variable also works)":
        "待ち受けポート（既定 {port}。環境変数 PORT も可）",
    "address to listen on (default 127.0.0.1; use 0.0.0.0 only when you want it "
    "visible on the LAN)":
        "待ち受けアドレス（既定 127.0.0.1。LAN公開したいときだけ 0.0.0.0）",
    "open a browser after starting": "起動後にブラウザを開く",
    "do not move to the next port when it is in use": "ポートが使用中でも繰り上げない",

    # ---- diagnose
    "  🔍 Subagent Dashboard — diagnostics":
        "  🔍 Subagent Dashboard — 診断ツール",
    "Running system checks...": "システムチェック実行中...",
    "Python version": "Python バージョン",
    "File layout": "ファイル構成",
    "Operating-rules settings": "運用ルール設定",
    "Operating-rules version": "運用ルールの版",
    "Mission storage": "ミッション保存先",
    "Project for this folder": "カレントディレクトリの対象",
    "Existing mission records": "既存のミッション記録",
    "Python {v} (3.9 or newer is required)": "Python {v}（3.9 以降が必要）",
    "all required files are present ({n})": "必要なファイルがすべて揃っています（{n} 件）",
    "missing: {list}": "不足: {list}",
    "{name} does not exist ({path})": "{name} が存在しません（{path}）",
    "read error: {err}": "読み込みエラー: {err}",
    "the settings are not written (no marker found)":
        "設定が書き込まれていません（マーカーが見つからない）",
    "the path does not match. Please run install.py (expected: {path})":
        "パスが一致しません。install.py を実行してください（期待: {path}）",
    "configured ({path})": "設定済み（{path}）",
    "not written for {names} (run install.py to add it)":
        "{names} には未記入（install.py を実行すると追加されます）",
    "not configured (fix the item above first)": "未設定（上の項目を先に直してください）",
    "cannot read the tool's VERSION": "本体の VERSION が読めません",
    "up to date (version {v})": "最新（版 {v}）",
    "no version recorded (0.4.1 or earlier)": "版の記載なし（0.4.1 以前）",
    "out of date ({stale} / tool: version {current}). Please run python {path}":
        "古いままです（{stale} / 本体: 版 {current}）。python {path} を実行してください",
    "writable ({path})": "書き込み可能（{path}）",
    "not writable: {err}": "書き込めません: {err}",
    "none (fresh install)": "なし（新規インストール）",
    "{n} project records present": "{n} 件のプロジェクト記録あり",
    "  ✅ Everything looks good.": "  ✅ すべて正常です！",
    "  The dashboard is set up correctly.": "  ダッシュボードは正しくセットアップされています。",
    "  You can start the server with:": "  次のコマンドでサーバーを起動できます:",
    "  Or, to use the VSCode extension:": "  または VSCode 拡張機能を使う場合:",
    "  ❌ Problems were found": "  ❌ 問題が見つかりました",
    "How to fix": "解決策",
    "      Cause: the Python version is too old": "      原因: Python のバージョンが古い",
    "      Fix:   install Python 3.9 or newer":
        "      対処: Python 3.9 以降をインストールしてください",
    "      Cause: required files are missing": "      原因: 必要なファイルが不足しています",
    "      Fix:   get a complete package from wherever you obtained this":
        "      対処: 配布元から完全なパッケージを受け取り直してください",
    "      Cause: no agent CLI has been configured yet": "      原因: エージェント CLI への設定が未完了です",
    "      Fix:   run the following command": "      対処: 次のコマンドを実行してください",
    "      Cause: the tool was updated, but the operating rules are still old":
        "      原因: 本体を更新したあと、運用ルールが古いまま残っています",
    "             (updating the tool does not rewrite them)":
        "           （本体の更新では運用ルールは書き換わりません）",
    "            only the marked block is replaced":
        "            マーカーで囲まれた範囲だけが差し替わります",
    "      Cause: the mission storage folder is not writable":
        "      原因: ミッション保存先に書き込めません",
    "      Fix:   check the write permissions on the folder":
        "      対処: フォルダの書き込み権限を確認してください",
    "      Cause: the project directory could not be determined":
        "      原因: プロジェクトディレクトリを判定できません",
    "      Fix:   run this from the root of your project":
        "      対処: プロジェクトのルートディレクトリで実行してください",
    "  If the problem persists, check these files:":
        "  問題が解決しない場合は、次のファイルを確認してください:",

    # ---- auto_setup
    "  ⚠️  First-time setup is not done yet "
    "(the operating rules have not been written anywhere).":
        "  ⚠️  初期設定がまだ済んでいません（運用ルールがどこにも書かれていません）。",
    "      The screen still opens, but the agent does not know how to use":
        "      このままでも画面は開きますが、エージェントは Subagent Dashboard の使い方を知らないので、",
    "      Subagent Dashboard, so starting subagents will show nothing.":
        "      サブエージェントを起動しても何も映りません。",
    "      install.py not found. Please unpack the distribution again.":
        "      install.py が見つかりません。配布物を展開し直してください。",
    "      To set it up, run: {how}": "      設定するには次を実行してください: {how}",
    "      Set it up now? [Y/n]: ": "      いま設定しますか？ [Y/n]: ",
    "      Understood. To set it up later, run {how}.":
        "      分かりました。あとで設定するときは {how} です。",
    "First-time setup is already done ({path}).": "初期設定は済んでいます（{path}）。",

    # ---- open_dashboard
    "  Starting the dashboard": "  ダッシュボード起動",
    "  Dashboard: {path}": "  ダッシュボード: {path}",
    "  ✗ The dashboard directory was not found": "  ✗ ダッシュボードディレクトリが見つかりません",
    "  ✗ dash.py not found: {path}": "  ✗ dash.py が見つかりません: {path}",
    "  ✗ Failed to start the server: {err}": "  ✗ サーバー起動に失敗しました: {err}",
    "  Starting the server...": "  サーバーを起動中...",
    "  Checking the connection...": "  接続確認中...",
    "  ✓ The server is up": "  ✓ サーバー起動完了",
    "  ⚠ Timed out checking the connection. Please try again.":
        "  ⚠ サーバーへの接続確認がタイムアウト。再試行してください。",
    "  Opening the browser...": "  ブラウザを開く...",
    "  ✓ Ready": "  ✓ 起動完了",
    "  ⚠ Could not open a browser. Please open {url} yourself.":
        "  ⚠ ブラウザが開けませんでした。手動で {url} を開いてください。",
}

# ============================================================ 中文（简体）
CATALOG["zh"] = {
    # ---- update_state: lang コマンド
    'unknown language: {lang} (choose from {list})':
        '未知的语言: {lang}（请从 {list} 中选择）',
    'show or set the language of these messages':
        '显示或设置这些消息的语言',
    'en / ja / zh / ko (omit to show the current setting)':
        'en / ja / zh / ko（省略则显示当前设置）',
    'Language: {label} ({code})':
        '语言: {label}（{code}）',
    '  detected from the operating system':
        '  由操作系统判定',
    '  available: {list}':
        '  可选: {list}',
    'Language set to {label} ({code}).':
        '已将语言设置为 {label}（{code}）。',
    '  saved in {path}':
        '  保存位置: {path}',
    '  from the environment variable {var}={value}':
        '  来自环境变量 {var}={value}',
    '  note: {var} is set, so it takes precedence over this setting.':
        '  注意: 已设置 {var}，它的优先级高于此设置。',
    '  from the saved setting {path}':
        '  来自已保存的设置 {path}',
    'Could not set the language: {err}':
        '无法设置语言: {err}',

    # ---- 自由记述的语言检查
    "  Write the free text (--title / --name / --mission / --headline) "
    "in this language: {label} ({code}).":
        "  请用这个语言写自由文本（--title / --name / --mission / --headline）: {label}（{code}）。",
    '{flag} "{value}"':
        '{flag} "{value}"',
    "  ⚠️  This does not look like {label} ({code}), the language that is set: "
    "{fields}":
        "  ⚠️  看起来不像 {label}（{code}），即设定的语言: "
        "{fields}",
    "      If that was a mistake, run the same command again with the same --id\n"
    "      and the corrected text. The value is replaced and the measured values\n"
    "      are kept (the event log keeps the line it already wrote).":
        "      如果那是个错误，用相同的 --id 再运行一次相同的命令\n"
        "      并更正文本。值会被替换，实测值保持不变\n"
        "      （事件日志保留它已经写过的那一行）。",
    "      The mission title cannot be corrected afterwards. Only a new start can\n"
    "      change it, and that archives this mission while it is still running.":
        "      任务标题之后无法更正。只有新的 start 才能\n"
        "      改变它，并且该任务在仍在运行时被存档。",
    "      If it was deliberate (a proper noun, a call sign), ignore this.":
        "      如果那是故意的（专有名词、呼号），请忽略。",
    "         The measured values and the status are kept "
    "(only what you passed is replaced).":
        "         实测值和状态保持不变"
        "（只有您传递的值被替换）。",
    "{name} ({id}) was rewritten — {mission}":
        "{name}（{id}）已重写 — {mission}",
    "initial state (running when omitted; kept as it is "
    "when the unit already exists)":
        "初始状态（省略时为 running；当该单位已存在时保持不变）",

    '  The operating rules were rewritten in this language: {path}':
        '  已用这个语言重写了运行规则: {path}',
    "  Restart the agent's session "
    "(the operating rules are read when it starts).":
        '  请重新打开代理的会话（运行规则是在开始时读入的）。',
    '  ⚠️  Could not rewrite the operating rules ({path}): {err}':
        '  ⚠️  无法重写运行规则（{path}）: {err}',
    '      Rewrite them in the new language by running:':
        '      要用新的语言重写，请执行:',
    '  note: the operating rules of this copy are not written anywhere, '
    'so only the messages above changed.':
        '  注意: 这份副本的运行规则没有写在任何地方，'
        '所以改变的只有上面的消息。',

    # ---- dash: コマンド一覧（dash --help）
    '\nSubagent Dashboard\n\n  Open the screen\n    dash serve                 start the server (leave it running)\n    dash serve --open          start it and open a browser too\n    dash serve --port 4000     choose the port\n\n  First-time setup\n    dash install               write the operating rules into the agent\'s config file\n    dash install --print       only show what would be written (changes nothing)\n\n  Build a distribution package\n    dash package               build the full package (ZIP + VSIX + setup guide)\n\n  VSCode extension\n    dash ext install           build the extension and install it into VSCode\n    dash ext package           build the full distribution (.vsix + guide, to email)\n    dash ext build             build only the .vsix (lands in dist/)\n    dash ext status            check whether it is installed\n    dash ext uninstall         remove the extension\n\n  Update the state (normally the agent runs these automatically)\n    dash start  --title "name of the work"\n    dash add    --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "the task"\n    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "result summary"\n    dash finish --headline "overall summary"\n\n  Inspect and misc\n    dash status                show the contents of the current project\n    dash projects              list the registered projects\n    dash demo                  fill in dummy data for checking the display\n    dash reset [--purge]       empty the current project (the tab stays)\n    dash remove [--yes]        delete the current project\'s records (the tab goes)\n    dash log --text "..."      append one line to the event log\n    dash lang <en|ja|zh|ko>    choose the language of these messages\n\n  For details on each command, run  dash <command> --help\n':
        '\nSubagent Dashboard\n\n  打开画面\n    dash serve                 启动服务器（保持运行）\n    dash serve --open          启动并打开浏览器\n    dash serve --port 4000     指定端口\n\n  初始设置\n    dash install               把运行规则写入智能体的配置文件\n    dash install --print       只显示将要写入的内容（不做修改）\n\n  制作分发包\n    dash package               制作完整的分发包（ZIP + VSIX + 说明书）\n\n  VSCode 扩展\n    dash ext install           构建扩展并安装到 VSCode\n    dash ext package           制作完整分发物（.vsix 和说明书，可作邮件附件）\n    dash ext build             只构建 .vsix（输出到 dist/）\n    dash ext status            确认是否已安装\n    dash ext uninstall         卸载扩展\n\n  更新状态（通常由智能体自动执行）\n    dash start  --title "工作的名称"\n    dash add    --id SCOUT-A --name "侦察A" --model claude-sonnet-5 --mission "任务内容"\n    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "结果摘要"\n    dash finish --headline "整体摘要"\n\n  查看及其他\n    dash status                显示当前项目的内容\n    dash projects              列出已注册的项目\n    dash demo                  写入用于确认显示的示例数据\n    dash reset [--purge]       清空当前项目（标签保留）\n    dash remove [--yes]        连同记录删除当前项目（标签消失）\n    dash log --text "..."      向事件日志追加一行\n    dash lang <en|ja|zh|ko>    选择这些消息的语言\n\n  各命令的详细说明请用  dash <命令> --help  查看。\n',

    "not created yet": "尚未创建",
    "empty file": "空文件",
    "not readable as UTF-8 ({reason})": "无法按 UTF-8 读取（{reason}）",
    "not readable as JSON ({msg} / line {line}, column {col})":
        "无法按 JSON 读取（{msg} / 第 {line} 行第 {col} 个字符）",
    "not readable as JSON ({err})": "无法按 JSON 读取（{err}）",

    "no version recorded": "未记录版本",
    "{name} ({where})": "{name}（{where}）",
    "version {v}": "版本 {v}",
    "  ⚠️  The operating rules are older than the tool "
    "({stale} / tool version {current}).":
        "  ⚠️  运行规则比本体旧（{stale} / 本体版本 {current}）。",
    "      Updating the tool does not update the rules. Please run:":
        "      更新本体不会自动更新运行规则。请执行：",
    "      (Only the marked block is replaced. Nothing else is touched.)":
        "      （只会替换标记包围的范围，其他内容不受影响）",
    "  ⚠️  {names} is installed, but the operating rules have not been written for it.":
        "  ⚠️  已安装 {names}，但尚未为其编写运行规则。",
    "      It was probably installed after the setup ran. Until you write them,":
        "      它很可能在设置运行后才安装的。只要未编写规则，",
    "      subagents started from it will not show up on the screen. Please run:":
        "      从中启动的子代理将不会显示在屏幕上。请执行:",
    "      (Only the marked block is written. Nothing else is touched.)":
        "      （只会写入标记包围的范围，其他内容不受影响）",
    "      Cause: a CLI was installed after the setup ran, so it has no operating rules":
        "      原因: CLI 在设置运行后被安装，因此它没有运行规则",

    "⚠️  Warning: {what}": "⚠️  警告: {what}",
    "   Cause: {err}": "   原因: {err}",
    "Failed to write the .current file": "写入 .current 文件失败",
    "this mission may not appear on the dashboard": "该任务可能不会显示在面板上",
    "Could not move the previous mission into history/":
        "无法把上一个任务移入 history/",
    "this start will overwrite the previous record (the mission still begins)":
        "本次 start 会覆盖上一次的记录（任务仍将开始）",
    "Could not move old records from history/ into trash/":
        "无法把 history/ 中的旧记录移入 trash/",

    "invalid slug: {slug!r}": "slug 不合法: {slug!r}",
    "invalid runId: {run_id!r}": "runId 不合法: {run_id!r}",
    "missions/{slug}/ does not exist": "missions/{slug}/ 不存在",
    "missions/{slug}/state.json does not exist": "missions/{slug}/state.json 不存在",
    "missions/{slug}/history/{run_id}/ does not exist":
        "missions/{slug}/history/{run_id}/ 不存在",
    "missions/{slug}/history/{run_id}/state.json does not exist":
        "missions/{slug}/history/{run_id}/state.json 不存在",
    "not directly under missions/: {path}": "不在 missions/ 的直接下级: {path}",
    "not directly under history/: {path}": "不在 history/ 的直接下级: {path}",
    "cannot read state.json ({err})": "无法读取 state.json（{err}）",
    "a mission that has not finished cannot be deleted": "尚未完成的任务无法删除",
    'the project hint "{hint}" matches {n} projects: {list}':
        "项目指定「{hint}」匹配到 {n} 个: {list}",
    "cannot read agents/ ({err})": "无法读取 agents/（{err}）",
    "cannot read agents/{name} ({err})": "无法读取 agents/{name}（{err}）",
    "agents/{name} contains an invalid agent definition":
        "agents/{name} 中存在不合法的代理定义",

    "(no mission started)": "（任务尚未开始）",
    "(untitled mission)": "（无标题任务）",

    "{path} accepts only {allow}": "{path} 只接受 {allow}",
    "{path} does not accept POST": "{path} 不接受 POST",
    "Content-Type must be application/json": "Content-Type 必须为 application/json",
    "Content-Length is invalid": "Content-Length 不合法",
    "the request body is empty": "请求正文为空",
    "the request body is too large": "请求正文过大",
    "please send a JSON object": "请发送 JSON 对象",
    "requests from another origin are not accepted": "不接受来自其他来源的操作",
    "specify a valid slug": "请正确指定 slug",
    "specify a valid runId": "请正确指定 runId",
    "{slug} has no record {run_id}": "{slug} 中没有记录 {run_id}",
    "{slug} has no records": "{slug} 没有任何记录",
    "the record is not in the expected shape": "记录的格式与预期不符",
    "404 — {path} was not found": "404 — 未找到 {path}",
    "failed to read: {err}": "读取失败: {err}",

    "  Deleted the record: {slug}": "  已删除记录: {slug}",
    " (deleted permanently)": "（已彻底删除）",
    "  Deleted records: {n}": "  已删除记录: {n} 条",
    " ({n} failed)": "（失败 {n} 条）",
    "runs must list at least one {slug, runId} entry":
        "runs 中至少要列出一条 {slug, runId}",
    "runs[{i}] is not an object": "runs[{i}] 不是对象",
    "runs[{i}].slug is invalid": "runs[{i}].slug 不合法",
    "runs[{i}].runId is invalid": "runs[{i}].runId 不合法",
    "phase must be one of {list}": "phase 必须是 {list} 之一",
    "specify either runs or phase": "请指定 runs 或 phase",
    "permanent is not accepted (records are always moved to the trash)":
        "不接受 permanent（记录一律移入回收站）",
    "no such record": "没有该记录",

    "Port {port} is in use. Trying {next}…": "端口 {port} 已被占用。尝试 {next}…",
    "Failed to start: {err}": "启动失败: {err}",
    "No free port was found. Use --port to choose another one.":
        "找不到空闲端口。请用 --port 指定其他端口。",
    "  Subagent Dashboard": "  Subagent Dashboard",
    "  Screen        {url}": "  画面          {url}",
    "  Manual        {url}": "  使用手册      {url}",
    "  Tool          {path}": "  工具          {path}",
    "  Missions      {path}": "  任务记录      {path}",
    "  * Listening on {host}. Other machines on the same network can reach it.":
        "  ※ 正在 {host} 上监听。同一网络中的其他设备也能看到。",
    "standby": "待机中",
    "running": "运行中",
    "done": "已完成",
    "  Teams on screen  {n}": "  当前显示的小队  {n} 组",
    "    - {name} ({phase} / {done}/{total} done) {title}":
        "    - {name}（{phase} / {done}/{total} 完成） {title}",
    "  Teams on screen  none (standby screen)": "  当前显示的小队  无（待机画面）",
    "    → In your working folder, run  {cmd} update_state.py start":
        "    → 请在工作目录中执行  {cmd} update_state.py start",
    "  Stop          Ctrl+C": "  停止          Ctrl+C",
    "Stopped.": "已停止。",

    "The serving process for the Subagent Dashboard": "Subagent Dashboard 的服务进程",
    "port to listen on (default {port}; the PORT environment variable also works)":
        "监听端口（默认 {port}；也可用环境变量 PORT）",
    "address to listen on (default 127.0.0.1; use 0.0.0.0 only when you want it "
    "visible on the LAN)":
        "监听地址（默认 127.0.0.1；只有想在局域网中公开时才用 0.0.0.0）",
    "open a browser after starting": "启动后打开浏览器",
    "do not move to the next port when it is in use": "端口被占用时不顺延",

    "  🔍 Subagent Dashboard — diagnostics":
        "  🔍 Subagent Dashboard — 诊断工具",
    "Running system checks...": "正在执行系统检查...",
    "Python version": "Python 版本",
    "File layout": "文件构成",
    "Operating-rules settings": "运行规则设置",
    "Operating-rules version": "运行规则的版本",
    "Mission storage": "任务保存位置",
    "Project for this folder": "当前目录对应的项目",
    "Existing mission records": "已有的任务记录",
    "Python {v} (3.9 or newer is required)": "Python {v}（需要 3.9 以上）",
    "all required files are present ({n})": "所需文件齐全（{n} 个）",
    "missing: {list}": "缺少: {list}",
    "{name} does not exist ({path})": "{name} 不存在（{path}）",
    "read error: {err}": "读取错误: {err}",
    "the settings are not written (no marker found)": "设置尚未写入（找不到标记）",
    "the path does not match. Please run install.py (expected: {path})":
        "路径不一致。请执行 install.py（期望: {path}）",
    "configured ({path})": "已配置（{path}）",
    "not written for {names} (run install.py to add it)":
        "{names} 尚未写入（执行 install.py 即可添加）",
    "not configured (fix the item above first)": "未配置（请先修复上面的项目）",
    "cannot read the tool's VERSION": "无法读取本体的 VERSION",
    "up to date (version {v})": "最新（版本 {v}）",
    "no version recorded (0.4.1 or earlier)": "未记录版本（0.4.1 及更早）",
    "out of date ({stale} / tool: version {current}). Please run python {path}":
        "仍是旧版（{stale} / 本体: 版本 {current}）。请执行 python {path}",
    "writable ({path})": "可写入（{path}）",
    "not writable: {err}": "无法写入: {err}",
    "none (fresh install)": "无（全新安装）",
    "{n} project records present": "存在 {n} 个项目记录",
    "  ✅ Everything looks good.": "  ✅ 一切正常！",
    "  The dashboard is set up correctly.": "  面板已正确设置。",
    "  You can start the server with:": "  可以用以下命令启动服务器:",
    "  Or, to use the VSCode extension:": "  或者，若要使用 VSCode 扩展:",
    "  ❌ Problems were found": "  ❌ 发现了问题",
    "How to fix": "解决办法",
    "      Cause: the Python version is too old": "      原因: Python 版本过旧",
    "      Fix:   install Python 3.9 or newer": "      对策: 请安装 Python 3.9 以上",
    "      Cause: required files are missing": "      原因: 缺少必要的文件",
    "      Fix:   get a complete package from wherever you obtained this":
        "      对策: 请从分发来源重新获取完整的包",
    "      Cause: no agent CLI has been configured yet": "      原因: 尚未完成对智能体 CLI 的设置",
    "      Fix:   run the following command": "      对策: 请执行以下命令",
    "      Cause: the tool was updated, but the operating rules are still old":
        "      原因: 更新本体后，运行规则仍是旧的",
    "             (updating the tool does not rewrite them)":
        "           （更新本体不会改写运行规则）",
    "            only the marked block is replaced": "            只会替换标记包围的范围",
    "      Cause: the mission storage folder is not writable":
        "      原因: 无法写入任务保存位置",
    "      Fix:   check the write permissions on the folder":
        "      对策: 请检查文件夹的写入权限",
    "      Cause: the project directory could not be determined":
        "      原因: 无法判定项目目录",
    "      Fix:   run this from the root of your project":
        "      对策: 请在项目的根目录中执行",
    "  If the problem persists, check these files:": "  若问题仍未解决，请查看以下文件:",

    "  ⚠️  First-time setup is not done yet "
    "(the operating rules have not been written anywhere).":
        "  ⚠️  尚未完成初始设置（运行规则尚未写入任何位置）。",
    "      The screen still opens, but the agent does not know how to use":
        "      画面仍可打开，但智能体不知道如何使用 Subagent Dashboard，",
    "      Subagent Dashboard, so starting subagents will show nothing.":
        "      因此即使启动子代理也不会显示任何内容。",
    "      install.py not found. Please unpack the distribution again.":
        "      找不到 install.py。请重新解压分发包。",
    "      To set it up, run: {how}": "      要进行设置，请执行: {how}",
    "      Set it up now? [Y/n]: ": "      现在就设置吗？ [Y/n]: ",
    "      Understood. To set it up later, run {how}.":
        "      明白了。之后要设置时请执行 {how}。",
    "First-time setup is already done ({path}).": "初始设置已完成（{path}）。",

    "  Starting the dashboard": "  正在启动面板",
    "  Dashboard: {path}": "  面板: {path}",
    "  ✗ The dashboard directory was not found": "  ✗ 找不到面板目录",
    "  ✗ dash.py not found: {path}": "  ✗ 找不到 dash.py: {path}",
    "  ✗ Failed to start the server: {err}": "  ✗ 服务器启动失败: {err}",
    "  Starting the server...": "  正在启动服务器...",
    "  Checking the connection...": "  正在确认连接...",
    "  ✓ The server is up": "  ✓ 服务器已启动",
    "  ⚠ Timed out checking the connection. Please try again.":
        "  ⚠ 确认与服务器的连接超时。请重试。",
    "  Opening the browser...": "  正在打开浏览器...",
    "  ✓ Ready": "  ✓ 启动完成",
    "  ⚠ Could not open a browser. Please open {url} yourself.":
        "  ⚠ 无法打开浏览器。请手动打开 {url}。",
}

# ============================================================ 한국어
CATALOG["ko"] = {
    # ---- update_state: lang コマンド
    'unknown language: {lang} (choose from {list})':
        '알 수 없는 언어입니다: {lang} ({list} 중에서 고르세요)',
    'show or set the language of these messages':
        '이 메시지들의 언어를 표시하거나 설정한다',
    'en / ja / zh / ko (omit to show the current setting)':
        'en / ja / zh / ko (생략하면 현재 설정을 표시)',
    'Language: {label} ({code})':
        '언어: {label} ({code})',
    '  detected from the operating system':
        '  운영체제에서 판정했습니다',
    '  available: {list}':
        '  선택 가능: {list}',
    'Language set to {label} ({code}).':
        '언어를 {label} ({code}) 로 설정했습니다.',
    '  saved in {path}':
        '  저장 위치: {path}',
    '  from the environment variable {var}={value}':
        '  환경 변수 {var}={value} 에 따릅니다',
    '  note: {var} is set, so it takes precedence over this setting.':
        '  참고: {var} 가 설정되어 있어 이 설정보다 우선합니다.',
    '  from the saved setting {path}':
        '  저장된 설정 {path} 에 따릅니다',
    'Could not set the language: {err}':
        '언어를 설정하지 못했습니다: {err}',

    # ---- 자유 기술의 언어 확인
    "  Write the free text (--title / --name / --mission / --headline) "
    "in this language: {label} ({code}).":
        "  자유 기술(--title / --name / --mission / --headline) 을 "
        "이 언어로 써주세요: {label}({code}).",
    '{flag} "{value}"':
        '{flag} "{value}"',
    "  ⚠️  This does not look like {label} ({code}), the language that is set: "
    "{fields}":
        "  ⚠️  {label}({code}), 설정된 언어 같지 않습니다: "
        "{fields}",
    "      If that was a mistake, run the same command again with the same --id\n"
    "      and the corrected text. The value is replaced and the measured values\n"
    "      are kept (the event log keeps the line it already wrote).":
        "      실수였다면 같은 --id 로 같은 명령을 다시 실행하고\n"
        "      수정된 텍스트를 입력하세요. 값은 교체되고 측정값은\n"
        "      보관됩니다(이벤트 로그는 이미 쓴 줄을 유지합니다).",
    "      The mission title cannot be corrected afterwards. Only a new start can\n"
    "      change it, and that archives this mission while it is still running.":
        "      미션 제목은 나중에 수정할 수 없습니다. 새로운 start 만이\n"
        "      이를 변경할 수 있으며, 이것은 실행 중인 미션을 보관합니다.",
    "      If it was deliberate (a proper noun, a call sign), ignore this.":
        "      의도적인 것(고유명사, 호출 신호)이면 무시하세요.",
    "         The measured values and the status are kept "
    "(only what you passed is replaced).":
        "         측정값과 상태는 유지됩니다"
        "(전달한 것만 교체됨).",
    "{name} ({id}) was rewritten — {mission}":
        "{name}({id})을(를) 다시 썼습니다 — {mission}",
    "initial state (running when omitted; kept as it is "
    "when the unit already exists)":
        "초기 상태(생략하면 running; 기체가 이미 존재하면 현상 유지)",

    '  The operating rules were rewritten in this language: {path}':
        '  운용 규칙을 이 언어로 다시 썼습니다: {path}',
    "  Restart the agent's session "
    "(the operating rules are read when it starts).":
        '  에이전트의 세션을 다시 열어 주세요'
        '(운용 규칙은 시작할 때 읽어 들입니다).',
    '  ⚠️  Could not rewrite the operating rules ({path}): {err}':
        '  ⚠️  운용 규칙을 다시 쓰지 못했습니다({path}): {err}',
    '      Rewrite them in the new language by running:':
        '      새 언어로 다시 쓰려면 다음을 실행해 주세요:',
    '  note: the operating rules of this copy are not written anywhere, '
    'so only the messages above changed.':
        '  주의: 이 복사본의 운용 규칙은 어디에도 쓰여 있지 않으므로, '
        '바뀐 것은 위의 메시지뿐입니다.',

    # ---- dash: コマンド一覧（dash --help）
    '\nSubagent Dashboard\n\n  Open the screen\n    dash serve                 start the server (leave it running)\n    dash serve --open          start it and open a browser too\n    dash serve --port 4000     choose the port\n\n  First-time setup\n    dash install               write the operating rules into the agent\'s config file\n    dash install --print       only show what would be written (changes nothing)\n\n  Build a distribution package\n    dash package               build the full package (ZIP + VSIX + setup guide)\n\n  VSCode extension\n    dash ext install           build the extension and install it into VSCode\n    dash ext package           build the full distribution (.vsix + guide, to email)\n    dash ext build             build only the .vsix (lands in dist/)\n    dash ext status            check whether it is installed\n    dash ext uninstall         remove the extension\n\n  Update the state (normally the agent runs these automatically)\n    dash start  --title "name of the work"\n    dash add    --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "the task"\n    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "result summary"\n    dash finish --headline "overall summary"\n\n  Inspect and misc\n    dash status                show the contents of the current project\n    dash projects              list the registered projects\n    dash demo                  fill in dummy data for checking the display\n    dash reset [--purge]       empty the current project (the tab stays)\n    dash remove [--yes]        delete the current project\'s records (the tab goes)\n    dash log --text "..."      append one line to the event log\n    dash lang <en|ja|zh|ko>    choose the language of these messages\n\n  For details on each command, run  dash <command> --help\n':
        '\nSubagent Dashboard\n\n  화면 열기\n    dash serve                 서버를 시작한다 (그대로 계속 띄워 둔다)\n    dash serve --open          시작하고 브라우저도 연다\n    dash serve --port 4000     포트를 지정한다\n\n  초기 설정\n    dash install               에이전트의 설정 파일에 운용 규칙을 기록한다\n    dash install --print       기록할 내용을 확인만 한다 (변경하지 않는다)\n\n  배포 패키지 만들기\n    dash package               배포용 패키지 일체를 만든다 (ZIP + VSIX + 설명서)\n\n  VSCode 확장\n    dash ext install           확장을 빌드해 VSCode 에 설치한다\n    dash ext package           배포물 일체를 만든다 (.vsix 와 설명서. 메일 첨부용)\n    dash ext build             .vsix 만 만든다 (dist/ 에 나온다)\n    dash ext status            설치되어 있는지 확인한다\n    dash ext uninstall         확장을 제거한다\n\n  상태 갱신 (보통은 에이전트가 자동으로 실행한다)\n    dash start  --title "작업의 이름"\n    dash add    --id SCOUT-A --name "정찰A" --model claude-sonnet-5 --mission "임무 내용"\n    dash done   --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "결과 요약"\n    dash finish --headline "전체 요약"\n\n  확인 및 기타\n    dash status                지금 프로젝트의 내용을 표시\n    dash projects              등록된 프로젝트 목록\n    dash demo                  표시 확인용 더미 데이터를 넣는다\n    dash reset [--purge]       지금 프로젝트를 비운다 (탭은 남는다)\n    dash remove [--yes]        지금 프로젝트를 기록째 삭제 (탭이 사라진다)\n    dash log --text "..."      이벤트 로그에 한 줄 추가\n    dash lang <en|ja|zh|ko>    이 메시지들의 언어를 고른다\n\n  각 명령의 자세한 내용은  dash <명령> --help  로 표시됩니다.\n',

    "not created yet": "아직 생성되지 않음",
    "empty file": "빈 파일",
    "not readable as UTF-8 ({reason})": "UTF-8 로 읽을 수 없습니다 ({reason})",
    "not readable as JSON ({msg} / line {line}, column {col})":
        "JSON 으로 읽을 수 없습니다 ({msg} / {line}행 {col}번째 문자)",
    "not readable as JSON ({err})": "JSON 으로 읽을 수 없습니다 ({err})",

    "no version recorded": "버전 기록 없음",
    "{name} ({where})": "{name} ({where})",
    "version {v}": "버전 {v}",
    "  ⚠️  The operating rules are older than the tool "
    "({stale} / tool version {current}).":
        "  ⚠️  운용 규칙이 본체보다 오래되었습니다 ({stale} / 본체 버전 {current}).",
    "      Updating the tool does not update the rules. Please run:":
        "      본체를 갱신해도 운용 규칙은 자동으로 갱신되지 않습니다. 다음을 실행하세요:",
    "      (Only the marked block is replaced. Nothing else is touched.)":
        "      (마커로 둘러싸인 범위만 교체됩니다. 다른 내용은 건드리지 않습니다.)",
    "  ⚠️  {names} is installed, but the operating rules have not been written for it.":
        "  ⚠️  {names} 이(가) 설치되었지만, 이에 대한 운용 규칙이 아직 기록되지 않았습니다.",
    "      It was probably installed after the setup ran. Until you write them,":
        "      설정 실행 후에 설치되었을 가능성이 있습니다. 기록할 때까지",
    "      subagents started from it will not show up on the screen. Please run:":
        "      여기서 시작한 서브에이전트는 화면에 표시되지 않습니다. 다음을 실행하세요:",
    "      (Only the marked block is written. Nothing else is touched.)":
        "      (마커로 둘러싸인 범위만 기록됩니다. 다른 내용은 건드리지 않습니다.)",
    "      Cause: a CLI was installed after the setup ran, so it has no operating rules":
        "      원인: CLI 가 설정 실행 후 설치되었으므로, 운용 규칙이 없습니다",

    "⚠️  Warning: {what}": "⚠️  경고: {what}",
    "   Cause: {err}": "   원인: {err}",
    "Failed to write the .current file": ".current 파일 쓰기에 실패했습니다",
    "this mission may not appear on the dashboard":
        "이 미션이 대시보드에 표시되지 않을 수 있습니다",
    "Could not move the previous mission into history/":
        "이전 미션을 history/ 로 옮기지 못했습니다",
    "this start will overwrite the previous record (the mission still begins)":
        "이번 start 로 이전 기록은 덮어써집니다 (미션 시작은 계속됩니다)",
    "Could not move old records from history/ into trash/":
        "history/ 의 오래된 기록을 trash/ 로 옮기지 못했습니다",

    "invalid slug: {slug!r}": "슬러그가 올바르지 않습니다: {slug!r}",
    "invalid runId: {run_id!r}": "runId 가 올바르지 않습니다: {run_id!r}",
    "missions/{slug}/ does not exist": "missions/{slug}/ 가 없습니다",
    "missions/{slug}/state.json does not exist": "missions/{slug}/state.json 이 없습니다",
    "missions/{slug}/history/{run_id}/ does not exist":
        "missions/{slug}/history/{run_id}/ 가 없습니다",
    "missions/{slug}/history/{run_id}/state.json does not exist":
        "missions/{slug}/history/{run_id}/state.json 이 없습니다",
    "not directly under missions/: {path}": "missions/ 바로 아래가 아닙니다: {path}",
    "not directly under history/: {path}": "history/ 바로 아래가 아닙니다: {path}",
    "cannot read state.json ({err})": "state.json 을 읽을 수 없습니다 ({err})",
    "a mission that has not finished cannot be deleted":
        "아직 완료되지 않은 미션은 삭제할 수 없습니다",
    'the project hint "{hint}" matches {n} projects: {list}':
        "프로젝트 지정 「{hint}」 이(가) {n} 건과 일치합니다: {list}",
    "cannot read agents/ ({err})": "agents/ 를 읽을 수 없습니다 ({err})",
    "cannot read agents/{name} ({err})": "agents/{name} 을(를) 읽을 수 없습니다 ({err})",
    "agents/{name} contains an invalid agent definition":
        "agents/{name} 에 올바르지 않은 에이전트 정의가 있습니다",

    "(no mission started)": "(미션 미시작)",
    "(untitled mission)": "(제목 없는 미션)",

    "{path} accepts only {allow}": "{path} 은(는) {allow} 만 받습니다",
    "{path} does not accept POST": "{path} 은(는) POST 를 받지 않습니다",
    "Content-Type must be application/json": "Content-Type 은 application/json 이어야 합니다",
    "Content-Length is invalid": "Content-Length 가 올바르지 않습니다",
    "the request body is empty": "본문이 없습니다",
    "the request body is too large": "본문이 너무 큽니다",
    "please send a JSON object": "JSON 객체를 보내주세요",
    "requests from another origin are not accepted": "다른 오리진에서의 조작은 받지 않습니다",
    "specify a valid slug": "slug 를 올바르게 지정하세요",
    "specify a valid runId": "runId 를 올바르게 지정하세요",
    "{slug} has no record {run_id}": "{slug} 에 기록 {run_id} 가 없습니다",
    "{slug} has no records": "{slug} 의 기록이 없습니다",
    "the record is not in the expected shape": "기록의 형식이 예상과 다릅니다",
    "404 — {path} was not found": "404 — {path} 을(를) 찾을 수 없습니다",
    "failed to read: {err}": "읽기에 실패했습니다: {err}",

    "  Deleted the record: {slug}": "  기록을 삭제했습니다: {slug}",
    " (deleted permanently)": " (완전 삭제)",
    "  Deleted records: {n}": "  기록을 삭제했습니다: {n} 건",
    " ({n} failed)": " (실패 {n} 건)",
    "runs must list at least one {slug, runId} entry":
        "runs 에는 {slug, runId} 를 한 건 이상 나열하세요",
    "runs[{i}] is not an object": "runs[{i}] 이(가) 객체가 아닙니다",
    "runs[{i}].slug is invalid": "runs[{i}].slug 가 올바르지 않습니다",
    "runs[{i}].runId is invalid": "runs[{i}].runId 가 올바르지 않습니다",
    "phase must be one of {list}": "phase 는 {list} 중 하나여야 합니다",
    "specify either runs or phase": "runs 또는 phase 를 지정하세요",
    "permanent is not accepted (records are always moved to the trash)":
        "permanent 는 받지 않습니다 (기록은 반드시 휴지통으로 옮깁니다)",
    "no such record": "기록이 없습니다",

    "Port {port} is in use. Trying {next}…": "포트 {port} 은(는) 사용 중입니다. {next} 을(를) 시도합니다…",
    "Failed to start: {err}": "시작에 실패했습니다: {err}",
    "No free port was found. Use --port to choose another one.":
        "빈 포트를 찾지 못했습니다. --port 로 다른 포트를 지정하세요.",
    "  Subagent Dashboard": "  Subagent Dashboard",
    "  Screen        {url}": "  화면          {url}",
    "  Manual        {url}": "  사용 설명서   {url}",
    "  Tool          {path}": "  도구          {path}",
    "  Missions      {path}": "  미션          {path}",
    "  * Listening on {host}. Other machines on the same network can reach it.":
        "  ※ {host} 에서 대기 중입니다. 같은 네트워크의 다른 기기에서도 보입니다.",
    "standby": "대기 중",
    "running": "가동 중",
    "done": "완료",
    "  Teams on screen  {n}": "  화면에 나오는 팀  {n} 건",
    "    - {name} ({phase} / {done}/{total} done) {title}":
        "    - {name} ({phase} / {done}/{total} 완료) {title}",
    "  Teams on screen  none (standby screen)": "  화면에 나오는 팀  없음 (대기 화면)",
    "    → In your working folder, run  {cmd} update_state.py start":
        "    → 작업할 폴더에서  {cmd} update_state.py start  를 실행하세요",
    "  Stop          Ctrl+C": "  중지          Ctrl+C",
    "Stopped.": "중지했습니다.",

    "The serving process for the Subagent Dashboard":
        "Subagent Dashboard 의 배포 서버",
    "port to listen on (default {port}; the PORT environment variable also works)":
        "대기할 포트 (기본값 {port}. 환경 변수 PORT 도 가능)",
    "address to listen on (default 127.0.0.1; use 0.0.0.0 only when you want it "
    "visible on the LAN)":
        "대기할 주소 (기본값 127.0.0.1. LAN 에 공개할 때만 0.0.0.0)",
    "open a browser after starting": "시작한 뒤 브라우저를 엽니다",
    "do not move to the next port when it is in use": "포트가 사용 중이어도 다음 포트로 넘기지 않습니다",

    "  🔍 Subagent Dashboard — diagnostics":
        "  🔍 Subagent Dashboard — 진단 도구",
    "Running system checks...": "시스템 점검 실행 중...",
    "Python version": "Python 버전",
    "File layout": "파일 구성",
    "Operating-rules settings": "운용 규칙 설정",
    "Operating-rules version": "운용 규칙의 버전",
    "Mission storage": "미션 저장 위치",
    "Project for this folder": "현재 디렉터리의 대상",
    "Existing mission records": "기존 미션 기록",
    "Python {v} (3.9 or newer is required)": "Python {v} (3.9 이상이 필요합니다)",
    "all required files are present ({n})": "필요한 파일이 모두 있습니다 ({n} 건)",
    "missing: {list}": "부족: {list}",
    "{name} does not exist ({path})": "{name} 가 존재하지 않습니다 ({path})",
    "read error: {err}": "읽기 오류: {err}",
    "the settings are not written (no marker found)":
        "설정이 기록되어 있지 않습니다 (마커를 찾을 수 없음)",
    "the path does not match. Please run install.py (expected: {path})":
        "경로가 일치하지 않습니다. install.py 를 실행하세요 (기대: {path})",
    "configured ({path})": "설정됨 ({path})",
    "not written for {names} (run install.py to add it)":
        "{names} 에는 기록되지 않음 (install.py 를 실행하면 추가됩니다)",
    "not configured (fix the item above first)": "미설정 (위 항목을 먼저 고치세요)",
    "cannot read the tool's VERSION": "본체의 VERSION 을 읽을 수 없습니다",
    "up to date (version {v})": "최신 (버전 {v})",
    "no version recorded (0.4.1 or earlier)": "버전 기록 없음 (0.4.1 이전)",
    "out of date ({stale} / tool: version {current}). Please run python {path}":
        "오래된 상태입니다 ({stale} / 본체: 버전 {current}). python {path} 를 실행하세요",
    "writable ({path})": "쓰기 가능 ({path})",
    "not writable: {err}": "쓸 수 없습니다: {err}",
    "none (fresh install)": "없음 (신규 설치)",
    "{n} project records present": "{n} 건의 프로젝트 기록 있음",
    "  ✅ Everything looks good.": "  ✅ 모두 정상입니다!",
    "  The dashboard is set up correctly.": "  대시보드가 올바르게 설정되어 있습니다.",
    "  You can start the server with:": "  다음 명령으로 서버를 시작할 수 있습니다:",
    "  Or, to use the VSCode extension:": "  또는 VSCode 확장을 사용하는 경우:",
    "  ❌ Problems were found": "  ❌ 문제가 발견되었습니다",
    "How to fix": "해결 방법",
    "      Cause: the Python version is too old": "      원인: Python 버전이 오래되었습니다",
    "      Fix:   install Python 3.9 or newer": "      조치: Python 3.9 이상을 설치하세요",
    "      Cause: required files are missing": "      원인: 필요한 파일이 부족합니다",
    "      Fix:   get a complete package from wherever you obtained this":
        "      조치: 배포처에서 완전한 패키지를 다시 받으세요",
    "      Cause: no agent CLI has been configured yet": "      원인: 에이전트 CLI 설정이 완료되지 않았습니다",
    "      Fix:   run the following command": "      조치: 다음 명령을 실행하세요",
    "      Cause: the tool was updated, but the operating rules are still old":
        "      원인: 본체를 갱신한 뒤 운용 규칙이 오래된 채로 남아 있습니다",
    "             (updating the tool does not rewrite them)":
        "           (본체 갱신으로는 운용 규칙이 바뀌지 않습니다)",
    "            only the marked block is replaced":
        "            마커로 둘러싸인 범위만 교체됩니다",
    "      Cause: the mission storage folder is not writable":
        "      원인: 미션 저장 위치에 쓸 수 없습니다",
    "      Fix:   check the write permissions on the folder":
        "      조치: 폴더의 쓰기 권한을 확인하세요",
    "      Cause: the project directory could not be determined":
        "      원인: 프로젝트 디렉터리를 판정할 수 없습니다",
    "      Fix:   run this from the root of your project":
        "      조치: 프로젝트의 루트 디렉터리에서 실행하세요",
    "  If the problem persists, check these files:":
        "  문제가 해결되지 않으면 다음 파일을 확인하세요:",

    "  ⚠️  First-time setup is not done yet "
    "(the operating rules have not been written anywhere).":
        "  ⚠️  초기 설정이 아직 끝나지 않았습니다 (운용 규칙이 어디에도 기록되어 있지 않습니다).",
    "      The screen still opens, but the agent does not know how to use":
        "      이대로도 화면은 열리지만, 에이전트는 Subagent Dashboard 사용법을 모르므로",
    "      Subagent Dashboard, so starting subagents will show nothing.":
        "      서브에이전트를 시작해도 아무것도 표시되지 않습니다.",
    "      install.py not found. Please unpack the distribution again.":
        "      install.py 를 찾을 수 없습니다. 배포물을 다시 풀어 주세요.",
    "      To set it up, run: {how}": "      설정하려면 다음을 실행하세요: {how}",
    "      Set it up now? [Y/n]: ": "      지금 설정하시겠습니까? [Y/n]: ",
    "      Understood. To set it up later, run {how}.":
        "      알겠습니다. 나중에 설정할 때는 {how} 입니다.",
    "First-time setup is already done ({path}).": "초기 설정은 이미 끝났습니다 ({path}).",

    "  Starting the dashboard": "  대시보드 시작",
    "  Dashboard: {path}": "  대시보드: {path}",
    "  ✗ The dashboard directory was not found": "  ✗ 대시보드 디렉터리를 찾을 수 없습니다",
    "  ✗ dash.py not found: {path}": "  ✗ dash.py 를 찾을 수 없습니다: {path}",
    "  ✗ Failed to start the server: {err}": "  ✗ 서버 시작에 실패했습니다: {err}",
    "  Starting the server...": "  서버를 시작하는 중...",
    "  Checking the connection...": "  연결을 확인하는 중...",
    "  ✓ The server is up": "  ✓ 서버 시작 완료",
    "  ⚠ Timed out checking the connection. Please try again.":
        "  ⚠ 서버 연결 확인이 시간 초과되었습니다. 다시 시도하세요.",
    "  Opening the browser...": "  브라우저를 여는 중...",
    "  ✓ Ready": "  ✓ 시작 완료",
    "  ⚠ Could not open a browser. Please open {url} yourself.":
        "  ⚠ 브라우저를 열지 못했습니다. 직접 {url} 을(를) 열어 주세요.",
}
