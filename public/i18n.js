/* ============================================================================
 * i18n.js — 画面（index.html / manual.html）の言語切り替え
 *
 * 英語を土台にして、日本語・中国語（簡体）・韓国語を載せる。訳が欠けている
 * ところは **英語に落ちる**（キー名を出さない）。翻訳の抜けで画面が読めなく
 * なるより、英語のまま出ているほうが直しやすいため。
 *
 * この画面は「黙って死なない」ことを最優先に作られている（index.html の
 * 「黙って死なないための下ごしらえ」節を参照）。その方針をここでも守る：
 *   - このファイルが読めなくても index.html は動く（向こうに退避 t() がある）
 *   - 知らないキーを渡されても例外にしない。英語 → キー名 の順に落ちる
 *   - localStorage が使えない環境（プライベートモード等）でも落ちない
 *
 * 使い方:
 *   I18N.t('dialog.delete_one.title')            文言を引く
 *   I18N.t('count.runs', { n: 3 })               {n} を差し込む
 *   I18N.apply(document)                         data-i18n 属性を一括反映
 *   I18N.setLang('ja')                           言語を変える（保存もする）
 *   I18N.onChange(fn)                            変わったときに呼ばれる
 *   I18N.mountSelect(selectEl)                   言語セレクタを組み立てる
 *
 * マークアップ側の属性:
 *   data-i18n="key"             textContent を差し替える
 *   data-i18n-html="key"        innerHTML を差し替える（訳文に <code> 等を含むとき）
 *   data-i18n-title="key"       title 属性
 *   data-i18n-aria-label="key"  aria-label 属性
 *
 * 複数形: 英語だけ「1件／それ以外」を言い分ける。キーに _one / _other を付けて
 * おくと、t(key, {n: 1}) が自動で選ぶ。日本語・中国語・韓国語は _other だけ持つ。
 * ========================================================================== */
'use strict';

(function (global) {

  const SUPPORTED = ['en', 'ja', 'zh', 'ko'];

  /** セレクタに出す名前。**その言語自身の表記**にする（読めない人が選べないため）。 */
  const LANG_LABELS = {
    en: 'English',
    ja: '日本語',
    zh: '中文',
    ko: '한국어',
  };

  /** 数値の桁区切りと日付に使う BCP 47 タグ。 */
  const LOCALES = {
    en: 'en-US',
    ja: 'ja-JP',
    zh: 'zh-CN',
    ko: 'ko-KR',
  };

  const STORE_KEY = 'dashboard:lang';

  // ==========================================================================
  // 文言
  //
  // 英語が原文。ja / zh / ko は英語のキーを埋めていく形にして、埋め忘れが
  // 「英語のまま出る」で済むようにしてある（キー名が画面に出ることはない）。
  // ==========================================================================

  const CATALOG = {};

  // -------------------------------------------------------------- English（原文）
  CATALOG.en = {
    // --- 画面まわり
    'app.title':           'Subagent Dashboard',
    'app.name':            'Subagent Dashboard',
    'lang.label':          'Language',

    // --- 接続状態
    'conn.connecting':     'Connecting…',
    'conn.connected':      'Connected',
    'conn.lost':           'Disconnected',
    'conn.lost_n':         '{msg} ({n})',
    'conn.fetch_failed':   'Fetch failed',
    'conn.broken':         'Display fault',

    // --- 拡大率
    'zoom.out':            'Zoom out',
    'zoom.out_to':         'Zoom out (to {n}%)',
    'zoom.in':             'Zoom in',
    'zoom.in_to':          'Zoom in (to {n}%)',
    'zoom.auto':           'Fit to frame (auto)',
    'zoom.auto_prefix':    'Auto ',
    'zoom.display_hint':   'Click to type a value (1–500). Ctrl+wheel over the tree also works.',
    'zoom.input_label':    'Zoom level (%)',

    // --- 上部の集計バッジ
    'count.standby':       'Standby',
    'count.running':       '{n} running',
    'count.done':          'Done',
    'count.runs_one':      ' · {n} record',
    'count.runs_other':    ' · {n} records',

    // --- タブ
    'tab.clear_done':      'Delete finished records',
    'tab.clear_done_title':'Moves the records of finished missions to the trash, all at once.',
    'tab.clear_count':     '({n})',
    'tab.delete_one':      'Delete this record (move to trash)',
    'tab.archived':        'Archived run',
    'tab.live':            'Mission in progress',
    'tab.tip':             '{kind} ({phase})\nProject: {project}\nMission: {title}\nStarted: {started}',
    'tab.tip_finished':    '\nFinished: {finished}',
    'tab.tip_agents':      '\nUnits: {n}',
    'tab.tip_unfinished':  '\n\nAll units are back, but the mission was never closed.\nRun update_state.py finish.',

    // --- 進行状態の札
    'phase.standby':       'Standby',
    'phase.running':       'Running',
    'phase.done':          'Done',
    'phase.short_standby': 'Idle',
    'phase.short_running': 'Live',
    'phase.short_done':    'Done',
    'phase.hist_standby':  'Not started',
    'phase.hist_running':  'Unfinished',
    'phase.hist_done':     'Done',
    'phase.unfinished_short': 'Open',
    'phase.unfinished':    'All back · not closed',
    'phase.unfinished_tip':'Every subagent has reported back, but the mission is not marked finished.\nRun update_state.py finish --headline "…".',

    // --- ミッションバーの数値
    'stat.elapsed':        'Elapsed',
    'stat.agents':         'Units',
    'stat.tokens':         'Tokens',
    'stat.took':           'Took',
    'stat.tools':          'Tools',
    'log.title':           'Event log',
    'log.toggle':          'Toggle event log',
    'log.show':            'Show event log',
    'log.hide':            'Hide event log',

    // --- 機体カード
    'card.self_reported':  'self-reported',
    'card.orphan':         'not in the records',
    'card.awaiting':       'awaiting report',
    // 稼働中の実測（live）。値は Claude Code がその機体について書いている記録から数えたもの。
    'live.unknown_tool':   'working',
    'live.tools_n':        '{n} calls',
    'live.quiet':          'quiet {s}',
    'live.stalled':        'no activity {s}',
    'live.bay_title':      'NOWHERE TO PUT THEM ({n})',
    'live.bay_note':       'Running, but not in the records, and their launcher could not be measured either — so there is no place for them in the tree.',
    'live.bay_note_frozen': 'They ran without ever being recorded, and were frozen into the record as they were when the mission was closed. Their launcher could not be measured either.',
    'live.bay_show':       'Show',
    'live.bay_hide':       'Hide',
    'live.orphan_parent':  'spawned by {name}',
    'card.no_mission':     '(no mission recorded)',
    'card.unknown_model':  'unknown',
    'gen.command':         'Command',
    'gen.nth':             'Generation {n}',

    // --- 過去の記録の札
    'archive.badge':       'Archived run',
    'archive.tip':         'Record ID {runId}\nStarted {started}\nFinished {finished}\nThis view is a snapshot; it does not update.',

    // --- 待機画面・空の系統樹
    'standby.head':        'Standing by',
    'standby.line1':       'Teams appear here once subagents start moving.',
    'standby.line2':       'To start one yourself, run this in your working directory:',
    'standby.line3':       'Just want to see how it looks? Use <code>update_state.py demo</code>.',
    'empty.archived_head': 'No units are left in this record.',
    'empty.archived_body': 'This mission ended without a single subagent being registered.',

    // --- ミッション完了のまとめ
    'summary.title':       'Mission complete',
    'summary.agents':      'Units',
    'summary.tokens':      'Total tokens',
    'summary.elapsed':     'Duration',
    'warn.title':          'Load warnings',

    // --- 記録の読み込み
    'run.loading':         'Loading the record…',
    'run.bad_shape':       'The record is not in the expected shape',
    'run.load_failed':     'Could not load the record: {msg}',
    'run.retry':           'Load again',
    'run.untitled':        '(untitled mission)',
    'run.no_project':      '(not recorded)',

    // --- ダイアログ
    'dialog.confirm':      'Confirm',
    'dialog.ok':           'OK',
    'dialog.cancel':       'Cancel',
    'dialog.close':        'Close',
    'dialog.delete_one.title':   'Delete one record',
    'dialog.delete_one.started': 'Started {when}',
    'dialog.delete_one.run_id':  ' (record ID {runId})',
    'dialog.delete_one.current': ' (finished current mission)',
    'dialog.delete_one.body':    'This record will be deleted.',
    'dialog.delete_one.last':    'This is the last record for this project, so the project goes with it.',
    'dialog.delete.trash':       'It is only moved to the trash (trash/), so it can be restored later.',
    'dialog.delete_one.ok':      'Delete',
    'dialog.delete_done.title':  'Delete finished records',
    'dialog.delete_done.body':   '{n} finished mission(s) will be deleted.',
    'dialog.delete_done.keep':   'Running and standby missions are not touched.',
    'dialog.delete_done.ok':     'Delete {n}',
    'dialog.delete_failed.title':'Could not delete',
    'dialog.delete_failed.body': 'The request did not reach the server. The records are untouched.',
    'dialog.delete_partial.title':'Some records could not be deleted',
    'dialog.delete_partial.done': '{n} deleted.',
    'dialog.delete_partial.fail': '{n} could not be deleted:',
    'dialog.bullet':             '· {text}',

    // --- 取扱説明書
    'manual.title':        'Manual',
    'manual.open':         'Open the manual',
    'manual.popout':       'Open in a new window',
    'manual.close':        'Close (Esc)',

    // --- 画面の切り替え（ミッション管制室／変更履歴）
    'screen.mission':      'Mission control',
    'screen.changelog':    'Changelog',

    // --- 変更履歴
    'cl.project':          'Project',
    'cl.option_count':     ' ({n})',
    'cl.last_update':      ' · updated {time}',
    'cl.no_projects':      'No project is registered yet.',
    'cl.empty':            'No changelog yet. Use Claude Code in a registered project and each session is recorded automatically when it ends.',
    'cl.conn_failed':      'Could not reach the server: {msg}',
    'cl.auto_badge':       'Not written',
    'cl.no_headline':      '(no headline)',
    'cl.body_show':        'Show the summary ▼',
    'cl.body_hide':        'Hide the summary ▲',
    'cl.detail_pending':   'The details for this session have not been fetched yet. Keep scrolling and they load.',
    'cl.files_n':          'Files ({n})',
    'cl.tools_count':      '{n} tool calls',
    'cl.session':          'session: {id}',

    // --- 内部の不具合（黙って死なないための表示）
    'broken.exception':    'Exception while loading: {msg}',
    'broken.at_line':      ' (line {n})',
    'broken.unknown':      'unknown',
    'broken.missing':      'Missing parts on the screen: {list}',
    'broken.load_state':   'Failed to read saved settings: {msg}',
    'broken.apply_zoom':   'Failed to apply the zoom level: {msg}',
    'broken.boot':         'Initialization failed: {msg}',
    'broken.i18n':         'Could not load i18n.js; falling back to English.',
    'console.fit_stopped': '[dashboard] auto-fit kept oscillating at the same size, so it was stopped',

    // --- 値が無いとき
    'value.none':          '—',
  };

  // -------------------------------------------------------------- 日本語
  CATALOG.ja = {
    'app.title':           'Subagent Dashboard',
    'app.name':            'Subagent Dashboard',
    'lang.label':          '言語',

    'conn.connecting':     '接続中…',
    'conn.connected':      '接続中',
    'conn.lost':           '切断',
    'conn.lost_n':         '{msg}（{n}回）',
    'conn.fetch_failed':   '取得失敗',
    'conn.broken':         '画面に不具合',

    'zoom.out':            '縮小',
    'zoom.out_to':         '縮小（{n}%へ）',
    'zoom.in':             '拡大',
    'zoom.in_to':          '拡大（{n}%へ）',
    'zoom.auto':           '枠に合わせる（自動）',
    'zoom.auto_prefix':    '自動 ',
    'zoom.display_hint':   'クリックで数値入力（1〜500）。系統樹の上で Ctrl+ホイールでも変えられます',
    'zoom.input_label':    '拡大率（%）',

    'count.standby':       '待機中',
    'count.running':       '稼働中 {n} チーム',
    'count.done':          '完了',
    'count.runs_other':    '・記録 {n} 件',

    'tab.clear_done':      '完了した記録を削除',
    'tab.clear_done_title':'完了したミッションの記録をまとめてゴミ箱へ移します',
    'tab.clear_count':     '（{n}件）',
    'tab.delete_one':      'この記録を削除（ゴミ箱へ移動）',
    'tab.archived':        '過去の記録',
    'tab.live':            '進行中のミッション',
    'tab.tip':             '{kind}（{phase}）\nプロジェクト: {project}\nミッション: {title}\n開始: {started}',
    'tab.tip_finished':    '\n終了: {finished}',
    'tab.tip_agents':      '\n機体: {n}',
    'tab.tip_unfinished':  '\n\n全機帰還済みですが、まだ締められていません。\nupdate_state.py finish を実行してください。',

    'phase.standby':       '待機中',
    'phase.running':       '稼働中',
    'phase.done':          '完了',
    'phase.short_standby': '待機',
    'phase.short_running': '稼働',
    'phase.short_done':    '完了',
    'phase.hist_standby':  '未着手',
    'phase.hist_running':  '未完',
    'phase.hist_done':     '完了',
    'phase.unfinished_short': '未締',
    'phase.unfinished':    '全機帰還・未締め',
    'phase.unfinished_tip':'サブエージェントは全員帰還しましたが、ミッションが完了になっていません。\nupdate_state.py finish --headline "..." を実行してください。',

    'stat.elapsed':        '経過',
    'stat.agents':         '機体',
    'stat.tokens':         'トークン',
    'stat.took':           '所要',
    'stat.tools':          'ツール',
    'log.title':           'イベントログ',
    'log.toggle':          'イベントログの表示切替',
    'log.show':            'イベントログを表示',
    'log.hide':            'イベントログを隠す',

    'card.self_reported':  '自己申告',
    'card.orphan':         '記録に無い',
    'card.awaiting':       '報告待ち',
    'live.unknown_tool':   '作業中',
    'live.tools_n':        'ツール {n}',
    'live.quiet':          '静かです {s}',
    'live.stalled':        '無風 {s}',
    'live.bay_title':      '置き場所が決まらない機体（{n}）',
    'live.bay_note':       '動いているのに記録が無く、起動元も実測で辿れなかった機体です。系統樹のどこに置けばよいかが決まりません。',
    'live.bay_note_frozen': '記録に無いまま動いていて、締めたときの姿をそのまま焼き付けた機体です。起動元も実測で辿れませんでした。',
    'live.bay_show':       '表示',
    'live.bay_hide':       '隠す',
    'live.orphan_parent':  '起動元 {name}',
    'card.no_mission':     '（任務未記載）',
    'card.unknown_model':  '不明',
    'gen.command':         '指令塔',
    'gen.nth':             '第 {n} 世代',

    'archive.badge':       '過去の記録',
    'archive.tip':         '記録ID {runId}\n開始 {started}\n終了 {finished}\nこの表示は記録された時点のもので、更新されません。',

    'standby.head':        '待機中',
    'standby.line1':       'サブエージェントが動き出すと、ここにチームが現れます。',
    'standby.line2':       '自分で始めるなら、作業するディレクトリで',
    'standby.line3':       '表示を試すだけなら <code>update_state.py demo</code> です。',
    'empty.archived_head': 'この記録には機体が残っていません。',
    'empty.archived_body': 'サブエージェントを1体も登録しないまま終わったミッションです。',

    'summary.title':       'ミッション完了',
    'summary.agents':      '機体数',
    'summary.tokens':      '合計トークン',
    'summary.elapsed':     '所要時間',
    'warn.title':          '読み込み警告',

    'run.loading':         '記録を読み込んでいます…',
    'run.bad_shape':       '記録の形が想定と違います',
    'run.load_failed':     '記録を読み込めませんでした：{msg}',
    'run.retry':           'もう一度読み込む',
    'run.untitled':        '（無題のミッション）',
    'run.no_project':      '（未記載）',

    'dialog.confirm':      '確認',
    'dialog.ok':           'OK',
    'dialog.cancel':       'やめる',
    'dialog.close':        '閉じる',
    'dialog.delete_one.title':   '記録を1件削除',
    'dialog.delete_one.started': '開始 {when}',
    'dialog.delete_one.run_id':  '（記録ID {runId}）',
    'dialog.delete_one.current': '（完了した現在のミッション）',
    'dialog.delete_one.body':    'この記録を削除します。',
    'dialog.delete_one.last':    'これがこのプロジェクト最後の記録なので、プロジェクトごと消えます。',
    'dialog.delete.trash':       'ゴミ箱（trash/）へ移すだけなので、あとで戻せます。',
    'dialog.delete_one.ok':      '削除する',
    'dialog.delete_done.title':  '完了した記録を削除',
    'dialog.delete_done.body':   '完了したミッション {n} 件を削除します。',
    'dialog.delete_done.keep':   '稼働中・待機中のミッションは削除されません。',
    'dialog.delete_done.ok':     '{n} 件を削除',
    'dialog.delete_failed.title':'削除できませんでした',
    'dialog.delete_failed.body': 'サーバーへの要求が通りませんでした。記録はそのまま残っています。',
    'dialog.delete_partial.title':'一部の記録を削除できませんでした',
    'dialog.delete_partial.done': '{n} 件を削除しました。',
    'dialog.delete_partial.fail': '{n} 件は削除できませんでした：',
    'dialog.bullet':             '・{text}',

    'manual.title':        '取扱説明書',
    'manual.open':         '取扱説明書を開く',
    'manual.popout':       '別ウィンドウで開く',
    'manual.close':        '閉じる（Esc）',

    'screen.mission':      'ミッション管制室',
    'screen.changelog':    '変更履歴',

    'cl.project':          'プロジェクト',
    'cl.option_count':     '（{n}件）',
    'cl.last_update':      ' ・最終更新 {time}',
    'cl.no_projects':      '登録済みのプロジェクトがまだありません。',
    'cl.empty':            'まだ変更履歴がありません。登録済みのプロジェクトで Claude Code を使うと、セッション終了時に自動で記録されます。',
    'cl.conn_failed':      '接続失敗: {msg}',
    'cl.auto_badge':       '未記入',
    'cl.no_headline':      '(見出しなし)',
    'cl.body_show':        '本文を表示 ▼',
    'cl.body_hide':        '本文をたたむ ▲',
    'cl.detail_pending':   'このセッションの詳細はまだ取得していません。下へスクロールすると読み込みます。',
    'cl.files_n':          'ファイル（{n}件）',
    'cl.tools_count':      'ツール呼び出し {n}件',
    'cl.session':          'session: {id}',

    'broken.exception':    '読み込み中の例外: {msg}',
    'broken.at_line':      '（{n}行目）',
    'broken.unknown':      '不明',
    'broken.missing':      '画面の部品が見つかりません: {list}',
    'broken.load_state':   '保存内容の読み込みに失敗: {msg}',
    'broken.apply_zoom':   '拡大率の反映に失敗: {msg}',
    'broken.boot':         '初期化に失敗: {msg}',
    'broken.i18n':         'i18n.js を読み込めなかったため、英語で表示しています。',
    'console.fit_stopped': '[dashboard] 自動フォーカスが同じ寸法のまま振動したため打ち切りました',

    'value.none':          '—',
  };

  // -------------------------------------------------------------- 中文（简体）
  CATALOG.zh = {
    'app.title':           'Subagent Dashboard',
    'app.name':            'Subagent Dashboard',
    'lang.label':          '语言',

    'conn.connecting':     '连接中…',
    'conn.connected':      '已连接',
    'conn.lost':           '已断开',
    'conn.lost_n':         '{msg}（{n} 次）',
    'conn.fetch_failed':   '获取失败',
    'conn.broken':         '界面异常',

    'zoom.out':            '缩小',
    'zoom.out_to':         '缩小（至 {n}%）',
    'zoom.in':             '放大',
    'zoom.in_to':          '放大（至 {n}%）',
    'zoom.auto':           '适应窗口（自动）',
    'zoom.auto_prefix':    '自动 ',
    'zoom.display_hint':   '点击可直接输入数值（1〜500）。在谱系树上按 Ctrl+滚轮也可调整',
    'zoom.input_label':    '缩放比例（%）',

    'count.standby':       '待机中',
    'count.running':       '运行中 {n} 组',
    'count.done':          '已完成',
    'count.runs_other':    '・记录 {n} 条',

    'tab.clear_done':      '删除已完成的记录',
    'tab.clear_done_title':'将已完成任务的记录一并移入回收站',
    'tab.clear_count':     '（{n} 条）',
    'tab.delete_one':      '删除此记录（移入回收站）',
    'tab.archived':        '历史记录',
    'tab.live':            '进行中的任务',
    'tab.tip':             '{kind}（{phase}）\n项目: {project}\n任务: {title}\n开始: {started}',
    'tab.tip_finished':    '\n结束: {finished}',
    'tab.tip_agents':      '\n单元: {n}',
    'tab.tip_unfinished':  '\n\n全部单元已归队，但任务尚未收尾。\n请执行 update_state.py finish。',

    'phase.standby':       '待机中',
    'phase.running':       '运行中',
    'phase.done':          '已完成',
    'phase.short_standby': '待机',
    'phase.short_running': '运行',
    'phase.short_done':    '完成',
    'phase.hist_standby':  '未开始',
    'phase.hist_running':  '未完成',
    'phase.hist_done':     '已完成',
    'phase.unfinished_short': '未收尾',
    'phase.unfinished':    '全部归队・未收尾',
    'phase.unfinished_tip':'所有子代理都已回报，但任务尚未标记为完成。\n请执行 update_state.py finish --headline "..."。',

    'stat.elapsed':        '已用时',
    'stat.agents':         '单元',
    'stat.tokens':         'Token',
    'stat.took':           '用时',
    'stat.tools':          '工具',
    'log.title':           '事件日志',
    'log.toggle':          '切换事件日志显示',
    'log.show':            '显示事件日志',
    'log.hide':            '隐藏事件日志',

    'card.self_reported':  '自行申报',
    'card.orphan':         '记录中没有',
    'card.awaiting':       '等待回报',
    'live.unknown_tool':   '作业中',
    'live.tools_n':        '工具 {n}',
    'live.quiet':          '安静 {s}',
    'live.stalled':        '无动静 {s}',
    'live.bay_title':      '无处安放的机体（{n}）',
    'live.bay_note':       '正在运行却没有记录，启动来源也无法实测，因此无法确定它们在系统树中的位置。',
    'live.bay_note_frozen': '在没有记录的情况下运行，收尾时按当时的样子固化到记录中的机体。启动来源也无法实测。',
    'live.bay_show':       '显示',
    'live.bay_hide':       '隐藏',
    'live.orphan_parent':  '由 {name} 启动',
    'card.no_mission':     '（未填写任务）',
    'card.unknown_model':  '未知',
    'gen.command':         '指挥塔',
    'gen.nth':             '第 {n} 代',

    'archive.badge':       '历史记录',
    'archive.tip':         '记录 ID {runId}\n开始 {started}\n结束 {finished}\n此画面是记录当时的快照，不会更新。',

    'standby.head':        '待机中',
    'standby.line1':       '子代理开始运行后，这里会出现小队。',
    'standby.line2':       '若要自行开始，请在工作目录中执行',
    'standby.line3':       '只想看看效果，可以用 <code>update_state.py demo</code>。',
    'empty.archived_head': '此记录中没有留下任何单元。',
    'empty.archived_body': '这是一次没有登记任何子代理就结束的任务。',

    'summary.title':       '任务完成',
    'summary.agents':      '单元数',
    'summary.tokens':      'Token 合计',
    'summary.elapsed':     '耗时',
    'warn.title':          '读取警告',

    'run.loading':         '正在读取记录…',
    'run.bad_shape':       '记录的格式与预期不符',
    'run.load_failed':     '无法读取记录：{msg}',
    'run.retry':           '重新读取',
    'run.untitled':        '（无标题任务）',
    'run.no_project':      '（未填写）',

    'dialog.confirm':      '确认',
    'dialog.ok':           '确定',
    'dialog.cancel':       '取消',
    'dialog.close':        '关闭',
    'dialog.delete_one.title':   '删除一条记录',
    'dialog.delete_one.started': '开始 {when}',
    'dialog.delete_one.run_id':  '（记录 ID {runId}）',
    'dialog.delete_one.current': '（已完成的当前任务）',
    'dialog.delete_one.body':    '将删除此记录。',
    'dialog.delete_one.last':    '这是该项目的最后一条记录，项目也会一并删除。',
    'dialog.delete.trash':       '只是移入回收站（trash/），之后仍可恢复。',
    'dialog.delete_one.ok':      '删除',
    'dialog.delete_done.title':  '删除已完成的记录',
    'dialog.delete_done.body':   '将删除 {n} 条已完成的任务记录。',
    'dialog.delete_done.keep':   '运行中和待机中的任务不会被删除。',
    'dialog.delete_done.ok':     '删除 {n} 条',
    'dialog.delete_failed.title':'删除失败',
    'dialog.delete_failed.body': '请求未能送达服务器。记录仍然保留。',
    'dialog.delete_partial.title':'部分记录未能删除',
    'dialog.delete_partial.done': '已删除 {n} 条。',
    'dialog.delete_partial.fail': '{n} 条未能删除：',
    'dialog.bullet':             '・{text}',

    'manual.title':        '使用手册',
    'manual.open':         '打开使用手册',
    'manual.popout':       '在新窗口中打开',
    'manual.close':        '关闭（Esc）',

    'screen.mission':      '任务管制室',
    'screen.changelog':    '变更历史',

    'cl.project':          '项目',
    'cl.option_count':     '（{n} 条）',
    'cl.last_update':      ' · 最后更新 {time}',
    'cl.no_projects':      '还没有已注册的项目。',
    'cl.empty':            '还没有变更历史。在已注册的项目里使用 Claude Code，每次会话结束时都会自动记录。',
    'cl.conn_failed':      '连接失败: {msg}',
    'cl.auto_badge':       '未填写',
    'cl.no_headline':      '(没有标题)',
    'cl.body_show':        '显示正文 ▼',
    'cl.body_hide':        '收起正文 ▲',
    'cl.detail_pending':   '这个会话的详情还没取回来。继续往下滚动就会加载。',
    'cl.files_n':          '文件（{n} 个）',
    'cl.tools_count':      '工具调用 {n} 次',
    'cl.session':          'session: {id}',

    'broken.exception':    '读取过程中发生异常: {msg}',
    'broken.at_line':      '（第 {n} 行）',
    'broken.unknown':      '未知',
    'broken.missing':      '找不到界面部件: {list}',
    'broken.load_state':   '读取已保存的设置失败: {msg}',
    'broken.apply_zoom':   '应用缩放比例失败: {msg}',
    'broken.boot':         '初始化失败: {msg}',
    'broken.i18n':         '未能载入 i18n.js，已回退为英文显示。',
    'console.fit_stopped': '[dashboard] 自动适应在同一尺寸下反复震荡，已停止',

    'value.none':          '—',
  };

  // -------------------------------------------------------------- 한국어
  CATALOG.ko = {
    'app.title':           'Subagent Dashboard',
    'app.name':            'Subagent Dashboard',
    'lang.label':          '언어',

    'conn.connecting':     '연결 중…',
    'conn.connected':      '연결됨',
    'conn.lost':           '연결 끊김',
    'conn.lost_n':         '{msg}（{n}회）',
    'conn.fetch_failed':   '가져오기 실패',
    'conn.broken':         '화면 오류',

    'zoom.out':            '축소',
    'zoom.out_to':         '축소（{n}%로）',
    'zoom.in':             '확대',
    'zoom.in_to':          '확대（{n}%로）',
    'zoom.auto':           '창에 맞추기（자동）',
    'zoom.auto_prefix':    '자동 ',
    'zoom.display_hint':   '클릭하면 값을 직접 입력할 수 있습니다（1〜500）. 계통수 위에서 Ctrl+휠로도 조절됩니다',
    'zoom.input_label':    '확대 비율（%）',

    'count.standby':       '대기 중',
    'count.running':       '가동 중 {n} 팀',
    'count.done':          '완료',
    'count.runs_other':    '・기록 {n} 건',

    'tab.clear_done':      '완료된 기록 삭제',
    'tab.clear_done_title':'완료된 미션의 기록을 한꺼번에 휴지통으로 옮깁니다',
    'tab.clear_count':     '（{n}건）',
    'tab.delete_one':      '이 기록 삭제（휴지통으로 이동）',
    'tab.archived':        '지난 기록',
    'tab.live':            '진행 중인 미션',
    'tab.tip':             '{kind}（{phase}）\n프로젝트: {project}\n미션: {title}\n시작: {started}',
    'tab.tip_finished':    '\n종료: {finished}',
    'tab.tip_agents':      '\n유닛: {n}',
    'tab.tip_unfinished':  '\n\n전원 귀환했지만 미션이 아직 마무리되지 않았습니다.\nupdate_state.py finish 를 실행하세요.',

    'phase.standby':       '대기 중',
    'phase.running':       '가동 중',
    'phase.done':          '완료',
    'phase.short_standby': '대기',
    'phase.short_running': '가동',
    'phase.short_done':    '완료',
    'phase.hist_standby':  '미착수',
    'phase.hist_running':  '미완료',
    'phase.hist_done':     '완료',
    'phase.unfinished_short': '미종료',
    'phase.unfinished':    '전원 귀환・미종료',
    'phase.unfinished_tip':'서브에이전트는 모두 보고를 마쳤지만 미션이 완료로 표시되지 않았습니다.\nupdate_state.py finish --headline "..." 을 실행하세요.',

    'stat.elapsed':        '경과',
    'stat.agents':         '유닛',
    'stat.tokens':         '토큰',
    'stat.took':           '소요',
    'stat.tools':          '도구',
    'log.title':           '이벤트 로그',
    'log.toggle':          '이벤트 로그 표시 전환',
    'log.show':            '이벤트 로그 표시',
    'log.hide':            '이벤트 로그 숨기기',

    'card.self_reported':  '자가 보고',
    'card.orphan':         '기록에 없음',
    'card.awaiting':       '보고 대기',
    'live.unknown_tool':   '작업 중',
    'live.tools_n':        '도구 {n}',
    'live.quiet':          '조용함 {s}',
    'live.stalled':        '무풍 {s}',
    'live.bay_title':      '놓을 자리를 정할 수 없는 기체({n})',
    'live.bay_note':       '가동 중인데 기록이 없고, 기동원도 실측으로 추적하지 못한 기체입니다. 계통수의 어디에 놓을지 정할 수 없습니다.',
    'live.bay_note_frozen': '기록에 없는 채로 가동하다가, 마감할 때의 모습 그대로 기록에 새긴 기체입니다. 기동원도 실측으로 추적하지 못했습니다.',
    'live.bay_show':       '표시',
    'live.bay_hide':       '숨기기',
    'live.orphan_parent':  '기동원 {name}',
    'card.no_mission':     '（임무 미기재）',
    'card.unknown_model':  '알 수 없음',
    'gen.command':         '지휘탑',
    'gen.nth':             '제 {n} 세대',

    'archive.badge':       '지난 기록',
    'archive.tip':         '기록 ID {runId}\n시작 {started}\n종료 {finished}\n이 화면은 기록된 시점의 것이며 갱신되지 않습니다.',

    'standby.head':        '대기 중',
    'standby.line1':       '서브에이전트가 움직이기 시작하면 여기에 팀이 나타납니다.',
    'standby.line2':       '직접 시작하려면 작업할 디렉터리에서',
    'standby.line3':       '표시만 확인하려면 <code>update_state.py demo</code> 입니다.',
    'empty.archived_head': '이 기록에는 남아 있는 유닛이 없습니다.',
    'empty.archived_body': '서브에이전트를 한 대도 등록하지 않은 채 끝난 미션입니다.',

    'summary.title':       '미션 완료',
    'summary.agents':      '유닛 수',
    'summary.tokens':      '총 토큰',
    'summary.elapsed':     '소요 시간',
    'warn.title':          '읽기 경고',

    'run.loading':         '기록을 읽는 중…',
    'run.bad_shape':       '기록의 형식이 예상과 다릅니다',
    'run.load_failed':     '기록을 읽지 못했습니다: {msg}',
    'run.retry':           '다시 읽기',
    'run.untitled':        '（제목 없는 미션）',
    'run.no_project':      '（미기재）',

    'dialog.confirm':      '확인',
    'dialog.ok':           '확인',
    'dialog.cancel':       '취소',
    'dialog.close':        '닫기',
    'dialog.delete_one.title':   '기록 1건 삭제',
    'dialog.delete_one.started': '시작 {when}',
    'dialog.delete_one.run_id':  '（기록 ID {runId}）',
    'dialog.delete_one.current': '（완료된 현재 미션）',
    'dialog.delete_one.body':    '이 기록을 삭제합니다.',
    'dialog.delete_one.last':    '이 프로젝트의 마지막 기록이므로 프로젝트째 사라집니다.',
    'dialog.delete.trash':       '휴지통（trash/）으로 옮길 뿐이므로 나중에 되돌릴 수 있습니다.',
    'dialog.delete_one.ok':      '삭제',
    'dialog.delete_done.title':  '완료된 기록 삭제',
    'dialog.delete_done.body':   '완료된 미션 {n} 건을 삭제합니다.',
    'dialog.delete_done.keep':   '가동 중・대기 중인 미션은 삭제되지 않습니다.',
    'dialog.delete_done.ok':     '{n} 건 삭제',
    'dialog.delete_failed.title':'삭제하지 못했습니다',
    'dialog.delete_failed.body': '서버에 요청이 전달되지 않았습니다. 기록은 그대로 남아 있습니다.',
    'dialog.delete_partial.title':'일부 기록을 삭제하지 못했습니다',
    'dialog.delete_partial.done': '{n} 건을 삭제했습니다.',
    'dialog.delete_partial.fail': '{n} 건은 삭제하지 못했습니다:',
    'dialog.bullet':             '・{text}',

    'manual.title':        '사용 설명서',
    'manual.open':         '사용 설명서 열기',
    'manual.popout':       '새 창으로 열기',
    'manual.close':        '닫기（Esc）',

    'screen.mission':      '미션 관제실',
    'screen.changelog':    '변경 이력',

    'cl.project':          '프로젝트',
    'cl.option_count':     '（{n}건）',
    'cl.last_update':      ' · 마지막 갱신 {time}',
    'cl.no_projects':      '등록된 프로젝트가 아직 없습니다.',
    'cl.empty':            '아직 변경 이력이 없습니다. 등록된 프로젝트에서 Claude Code 를 사용하면 세션이 끝날 때 자동으로 기록됩니다.',
    'cl.conn_failed':      '연결 실패: {msg}',
    'cl.auto_badge':       '미기입',
    'cl.no_headline':      '(제목 없음)',
    'cl.body_show':        '본문 보기 ▼',
    'cl.body_hide':        '본문 접기 ▲',
    'cl.detail_pending':   '이 세션의 상세는 아직 가져오지 않았습니다. 아래로 스크롤하면 읽어 옵니다.',
    'cl.files_n':          '파일（{n}개）',
    'cl.tools_count':      '도구 호출 {n}회',
    'cl.session':          'session: {id}',

    'broken.exception':    '읽는 중 예외 발생: {msg}',
    'broken.at_line':      '（{n}번째 줄）',
    'broken.unknown':      '알 수 없음',
    'broken.missing':      '화면 부품을 찾을 수 없습니다: {list}',
    'broken.load_state':   '저장된 설정을 읽지 못했습니다: {msg}',
    'broken.apply_zoom':   '확대 비율 적용에 실패했습니다: {msg}',
    'broken.boot':         '초기화에 실패했습니다: {msg}',
    'broken.i18n':         'i18n.js 를 읽지 못해 영어로 표시하고 있습니다.',
    'console.fit_stopped': '[dashboard] 자동 맞춤이 같은 크기에서 계속 진동하여 중단했습니다',

    'value.none':          '—',
  };

  // ==========================================================================
  // 判定と保存
  // ==========================================================================

  /** 'ja-JP' や 'zh-Hant-TW' のようなタグを、対応している4つのどれかに寄せる。
   *  対応外なら null（呼び手が次の候補へ進む）。 */
  function normalize(tag) {
    if (typeof tag !== 'string' || !tag) return null;
    const low = tag.toLowerCase();
    if (low === 'en' || low.indexOf('en-') === 0) return 'en';
    if (low === 'ja' || low.indexOf('ja-') === 0) return 'ja';
    if (low === 'ko' || low.indexOf('ko-') === 0) return 'ko';
    // 繁体字も簡体字の表へ寄せる。訳が無いよりは読めるほうがよいという判断。
    if (low === 'zh' || low.indexOf('zh-') === 0) return 'zh';
    return null;
  }

  /** localStorage は使えないことがある（プライベートモード、file://、埋め込み）。
   *  読み書きどちらも握りつぶして、既定へ落ちるだけにする。 */
  function readStored() {
    try {
      const v = global.localStorage.getItem(STORE_KEY);
      return SUPPORTED.indexOf(v) >= 0 ? v : null;
    } catch (e) { return null; }
  }
  function writeStored(lang) {
    try { global.localStorage.setItem(STORE_KEY, lang); } catch (e) { /* 保存できなくても動く */ }
  }

  /** 保存された選択 → ブラウザの言語 → 英語、の順。
   *  navigator.languages は優先順に並んでいるので、**対応している最初のもの**を採る。 */
  function detect() {
    const saved = readStored();
    if (saved) return saved;
    const nav = global.navigator || {};
    const list = [].concat(nav.languages || [], nav.language || [], nav.userLanguage || []);
    for (const tag of list) {
      const hit = normalize(tag);
      if (hit) return hit;
    }
    return 'en';
  }

  let current = detect();
  const listeners = [];

  // ==========================================================================
  // 引きと差し込み
  // ==========================================================================

  /** どの文にも共通で差し込める値（説明書に出す実環境のパスなど）。
   *  setVars() で入れる。params に同じ名前があればそちらが勝つ。 */
  let vars = {};

  /**
   * 文言全体で使う差し込み値を登録する。説明書がサーバーから受け取った
   * 実際のパス（`{PY}` `{TOOL_ROOT}` など）を入れるための口。
   * data-i18n 属性から引かれる文にも効かせたいので、params ではなくここに置く。
   */
  function setVars(next) {
    if (next && typeof next === 'object') vars = Object.assign({}, vars, next);
  }

  /** {name} を params → vars の順で埋める。どちらにも無いものは**そのまま残す**
   *  （空文字に潰すと、渡し忘れが「文が欠けている」という読める壊れ方にならない）。 */
  function fill(text, params) {
    if (text.indexOf('{') < 0) return text;
    return text.replace(/\{(\w+)\}/g, (whole, name) => {
      let v = params ? params[name] : undefined;
      if (v === undefined || v === null) v = vars[name];
      return (v === undefined || v === null) ? whole : String(v);
    });
  }

  /**
   * 文言表をあとから足す。説明書のように長い文だけを別ファイルに置き、
   * 開いたページでだけ読み込めるようにするための口。
   * @param {Object} more {en: {...}, ja: {...}, ...} の形
   */
  function extend(more) {
    if (!more || typeof more !== 'object') return;
    for (const lang of SUPPORTED) {
      if (!more[lang]) continue;
      CATALOG[lang] = Object.assign(CATALOG[lang] || {}, more[lang]);
    }
  }

  /** 英語だけ単複を言い分ける。他の3言語は _other だけ持つ。 */
  function pluralKey(key, params) {
    if (!params || typeof params.n !== 'number') return null;
    const suffix = (current === 'en' && Math.abs(params.n) === 1) ? '_one' : '_other';
    return key + suffix;
  }

  /**
   * 文言を引く。**見つからなくても例外にしない。**
   * 探す順は 現在の言語 → 現在の言語の複数形 → 英語 → 英語の複数形 → キー名。
   * @param {string} key
   * @param {Object} [params] {name} に差し込む値
   */
  function t(key, params) {
    const cur = CATALOG[current] || CATALOG.en;
    const pk = pluralKey(key, params);
    let raw;
    if (pk && cur[pk] !== undefined) raw = cur[pk];
    else if (cur[key] !== undefined) raw = cur[key];
    else if (pk && CATALOG.en[pk] !== undefined) raw = CATALOG.en[pk];
    else if (CATALOG.en[key] !== undefined) raw = CATALOG.en[key];
    // 英語にも無いキーは、日本語表以外に置き忘れた印。キー名を出して気づけるようにする。
    else raw = key;
    return fill(raw, params);
  }

  /** そのキーが**どこかの表に**あるか。呼び手が「訳が無いなら出さない」を選べるように。 */
  function has(key) {
    const cur = CATALOG[current] || {};
    return cur[key] !== undefined || CATALOG.en[key] !== undefined;
  }

  // ==========================================================================
  // DOM への反映
  // ==========================================================================

  const ATTR_MAP = [
    ['data-i18n-title',      'title'],
    ['data-i18n-aria-label', 'aria-label'],
    ['data-i18n-placeholder','placeholder'],
  ];

  /**
   * data-i18n 系の属性が付いた要素をまとめて訳す。
   * @param {Document|Element} [root] 省略すると document 全体
   */
  function apply(root) {
    const scope = root || global.document;
    if (!scope || !scope.querySelectorAll) return;
    for (const el of scope.querySelectorAll('[data-i18n]')) {
      el.textContent = t(el.getAttribute('data-i18n'));
    }
    for (const el of scope.querySelectorAll('[data-i18n-html]')) {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    }
    for (const [attr, target] of ATTR_MAP) {
      for (const el of scope.querySelectorAll('[' + attr + ']')) {
        el.setAttribute(target, t(el.getAttribute(attr)));
      }
    }
    // <title> と <html lang> は querySelectorAll では拾えないので個別に見る。
    // 文書まるごとを渡されたときだけ触る（部分適用で毎回書き換えない）。
    if (scope === global.document && scope.documentElement) {
      const titleKey = scope.documentElement.getAttribute('data-i18n-doctitle');
      if (titleKey) scope.title = t(titleKey);
      scope.documentElement.lang = htmlLang();
    }
  }

  /** <html lang> に入れる値。zh は地域まで書かないとフォント選択が地域で割れる。 */
  function htmlLang() {
    return current === 'zh' ? 'zh-Hans' : current;
  }

  // ==========================================================================
  // 切り替え
  // ==========================================================================

  function getLang() { return current; }

  /**
   * 言語を変える。同じ言語なら何もしない。
   * @param {string} lang 'en' | 'ja' | 'zh' | 'ko'
   * @param {{silent?: boolean}} [opts] silent なら購読者へ知らせない（初期化時に使う）
   */
  function setLang(lang, opts) {
    const next = normalize(lang) || (SUPPORTED.indexOf(lang) >= 0 ? lang : null);
    if (!next || next === current) return;
    current = next;
    writeStored(next);
    apply(global.document);
    if (!(opts && opts.silent)) {
      for (const fn of listeners) {
        // 1人の購読者が落ちても、残りには届ける。
        try { fn(next); } catch (e) { console.error('[i18n] listener failed', e); }
      }
    }
  }

  function onChange(fn) { if (typeof fn === 'function') listeners.push(fn); }

  /** 既存の <select> を言語セレクタに仕立てる。index.html と manual.html で共用する。 */
  function mountSelect(el) {
    if (!el) return;
    el.innerHTML = '';
    for (const lang of SUPPORTED) {
      const op = global.document.createElement('option');
      op.value = lang;
      op.textContent = LANG_LABELS[lang];
      el.appendChild(op);
    }
    el.value = current;
    el.addEventListener('change', () => setLang(el.value));
    // 別のタブや、説明書の iframe 側から変えられたときに追随する
    onChange(() => { el.value = current; });
  }

  // ==========================================================================
  // 書式
  // ==========================================================================

  /** 桁区切り。ロケールを固定していると、どの言語でも日本語の区切りになる。 */
  function fmtNumber(n) {
    try { return Number(n).toLocaleString(LOCALES[current] || 'en-US'); }
    catch (e) { return String(n); }
  }

  function locale() { return LOCALES[current] || 'en-US'; }

  // ==========================================================================
  // 別ウィンドウ・iframe との同期
  //
  // 説明書は index.html の中に iframe で開く。同じオリジンなので localStorage は
  // 共有されるが、**書いた側のウィンドウには storage イベントが飛ばない**。
  // よって「向こうで変えた」だけがこの経路で届く。これがちょうど必要な向き。
  // ==========================================================================
  global.addEventListener('storage', (e) => {
    if (!e || e.key !== STORE_KEY) return;
    const next = normalize(e.newValue) || (SUPPORTED.indexOf(e.newValue) >= 0 ? e.newValue : null);
    if (next && next !== current) {
      current = next;
      apply(global.document);
      for (const fn of listeners) {
        try { fn(next); } catch (err) { console.error('[i18n] listener failed', err); }
      }
    }
  });

  global.I18N = {
    t, has, apply, setLang, getLang, onChange, mountSelect,
    setVars, extend, fmtNumber, locale, htmlLang,
    langs: SUPPORTED.slice(),
    labels: Object.assign({}, LANG_LABELS),
  };

})(window);
