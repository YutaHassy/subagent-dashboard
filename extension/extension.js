/**
 * Subagent Dashboard — VSCode 拡張機能
 *
 * ビルド工程を持たない素の CommonJS。require するのは 'vscode' と Node 組み込みだけで、
 * node_modules は使わない。理由は EXTENSION_PLAN.md の「3. 方針」を参照。
 *
 * やっていることは 4 つ。
 *   1. ダッシュボード本体が無ければ、同梱している荷物を ~/.claude/agent-dashboard へ配置する
 *   2. サーバー（Python）が居るかを調べ、居なければ立てる
 *   3. 立てたポートを自分で決めているので、必ず正しい URL を知っている
 *   4. その URL を VSCode のサイドバーとタブ（Webview）に埋めて出す
 *
 * **同梱した荷物の場所では動かさない。** 拡張フォルダにはバージョン番号が入っていて、
 * 更新するとフォルダごと変わる。そこに記録（missions/）が書かれると消えてしまう。
 */

'use strict';

const vscode = require('vscode');
const cp = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');

// 利用者に見える文言は全部ここを通す。鍵は英語の原文そのもの（i18n.js を参照）。
// **t という名前の局所変数を作らないこと。** 影に隠れると、その関数の中だけ
// 文言が英語のまま出る、という気づきにくい壊れ方をする。
const { t, htmlLang } = require('./i18n');

// ---------------------------------------------------------------- 定数

const HEALTH_PATH = '/api/env';       // ここが JSON を返せばサーバーは生きている
const PORT_SCAN_MAX = 10;             // 既定ポートから何個先まで空きを探すか
const HEALTH_TIMEOUT_MS = 15000;      // 起動待ちの上限
const HEALTH_INTERVAL_MS = 250;       // 起動待ちのポーリング間隔
const PROBE_TIMEOUT_MS = 1200;        // 1回の生存確認の上限
const VIEW_ID = 'agentDashboard.view';

/**
 * タブ（Webview）の種類。**ここを変えると、前の版で開いていたタブは復元できなくなる。**
 * VSCode は閉じたときのこの文字列を覚えていて、開き直したときに同じ文字列で登録された
 * 相手（registerWebviewPanelSerializer）を探すため。
 */
const PANEL_TYPE = 'agentDashboard.panel';

/**
 * 初期設定（install.py）の実行記録。globalState に置くので、
 * ワークスペースを移っても・拡張を入れ直しても「もう済んでいる」ことを覚えている。
 */
const SETUP_DONE_KEY = 'initialSetupDone';      // 一度でも成功したら true
// 「今後たずねない」の記録（initialSetupSkipped）は廃止した。**尋ねなくなったので、
// 断る手段も無くなった**——拡張を入れた＝使う、という前提に変えたため。
// 古い版で立てた値が globalState に残っていても、もう誰も読まない。
// 自動で走らせたくない環境は、設定 agentDashboard.runSetupOnFirstRun を切る。
const SETUP_TIMEOUT_MS = 180000;                // install.py の実行にかける上限
const MACHINE_KEY_STORED = 'lastMachineKey';    // 前回起動したマシンのキーを保存

/**
 * 変更履歴トラッキングの初期設定（changelog_setup.py）の実行記録。
 *
 * **マシン単位の SETUP_DONE_KEY とは別軸。** 1台のマシンで複数の
 * リポジトリを開く利用者がほとんどなので、ワークスペース（＝プロジェクト）ごとに
 * 判定しないと2つ目以降のリポジトリで一切設定されない。キーはワークスペースの絶対パスを
 * ハッシュ化した値を末尾に付けて作る（例: `changelogSetupDone:<hash>`）。
 */
const CHANGELOG_SETUP_DONE_PREFIX = 'changelogSetupDone:';
const CHANGELOG_SETUP_SKIP_PREFIX = 'changelogSetupSkipped:';
/**
 * 「今後どのワークスペースでもたずねない」。**ハッシュを付けない、全体に効く1本の鍵。**
 *
 * ワークスペース単位の SKIP しか無いと、リポジトリを開くたびに1枚ずつモーダルが出て、
 * 全部まとめて断る手段が設定のトグルだけになる。ここを立てたら、以後どのワークスペースでも
 * 自動では持ちかけない（コマンドからの手動実行は今まで通り通る）。
 *
 * **マシン単位の初期設定にはこれに当たるものが無い。** あちらは確認そのものを廃止した
 * （拡張を入れた＝使う）。こちらが残っているのは、書き込む先が利用者のリポジトリの中で、
 * 断られたら1バイトも書かない、が守るべき順序だから。
 */
const CHANGELOG_SETUP_SKIP_ALL_KEY = 'changelogSetupSkippedEverywhere';
const CHANGELOG_SETUP_TIMEOUT_MS = 180000;      // changelog_setup.py の実行にかける上限（install.py と同じ目安）

/**
 * 本体を置く場所。ここは拡張の更新に巻き込まれないので、記録が消えない。
 *
 * 環境変数 AGENT_DASHBOARD_DEPLOY_DIR で差し替えられる。ホームディレクトリを
 * 使いたくない環境向けの逃げ道であり、動作確認が本物の設置先を壊さずに済む道でもある。
 */
const DEPLOY_DIR = process.env.AGENT_DASHBOARD_DEPLOY_DIR
  ? path.resolve(process.env.AGENT_DASHBOARD_DEPLOY_DIR)
  : path.join(os.homedir(), '.claude', 'agent-dashboard');

// ---------------------------------------------------------------- 状態

/** @type {vscode.OutputChannel} */
let out;
/** @type {vscode.StatusBarItem | undefined} */
let statusItem;
/** @type {vscode.WebviewPanel | undefined} */
let panel;
/**
 * タブがいま失敗の紙（iframe ではない画面）を出しているか。
 * 設定を直したときに描き直すかどうかの判断に使う。
 */
let panelNotice = false;
/** @type {DashboardView | undefined} */
let sidebar;

/**
 * この拡張が起動したサーバー。外で起動されていたサーバーを再利用した場合は null のまま。
 * null でないときだけ、我々に停止する権利がある。
 * @type {{ proc: import('child_process').ChildProcess, port: number, home: string } | null}
 */
let owned = null;

/** いまつながっているポート（再利用したものも含む）。未接続なら null。 */
let activePort = null;

/**
 * **いま立ち上げようとしているプロセス。** 立ち上げの最中に死んだときは、停止の紙を出さない。
 *
 * その結末（理由と次の一手）は ensureServerOnce が返し、呼び手が紙にする。ここで
 * showStopped() を割り込ませると、正しい紙が出るまでの間ずっと「サーバーは停止しています」
 * という**まだ起きていないことを断言した紙**が残る。そこに書かれた「もう一度試す」も、
 * 進行中の Promise に合流するだけで何も起きないので、押しても画面が変わらない。
 * @type {import('child_process').ChildProcess | null}
 */
let startingProc = null;

/** 検出済みの Python コマンド。1 セッション内でキャッシュする。 */
let pythonCache = null;

/** open の多重実行を防ぐ。 */
let busy = false;

/**
 * ensureServer() の実行中の Promise。同時に呼ばれたら、これを共有して同じ結果を返す。
 * サーバーが二重に立って owned が死んだプロセスを指すのを防ぐための唯一の砦。
 * @type {Promise<{ port: number } | { error: string, reason: string }> | null}
 */
let ensureServerInFlight = null;

/** 更新の呼びかけは1セッションに1回だけにする。 */
let updateOffered = false;

/** install.py が走っている最中は true。二重実行を防ぐ。 */
let setupInFlight = false;

/** 初期設定の確認も1セッションに1回だけ。断られたあと何度も出さない。 */
let setupPrompted = false;

/** changelog_setup.py が走っている最中は true。二重実行を防ぐ（マシン単位の setupInFlight とは別）。 */
let changelogSetupInFlight = false;

/** ワークスペース単位の初期設定の確認も1セッションに1回だけ。 */
let changelogSetupPrompted = false;

// ---------------------------------------------------------------- 小道具

function log(message) {
  // **t という名前にしない。** 翻訳の t() を影で隠すと、この関数から下で
  // 文言が英語のまま出る（実際にそれで壊した前例がある）。
  const stamp = new Date().toLocaleTimeString('en-GB', { hour12: false });
  out.appendLine(`[${stamp}] ${message}`);
}

function cfg() {
  return vscode.workspace.getConfiguration('agentDashboard');
}

/** Windows では大小や区切りの違いを無視してパスを比べる。 */
function samePath(a, b) {
  if (!a || !b) return false;
  const norm = (p) => {
    let s = path.resolve(p);
    if (process.platform === 'win32') s = s.replace(/\\/g, '/').toLowerCase();
    return s.replace(/\/+$/, '');
  };
  return norm(a) === norm(b);
}

function urlFor(port) {
  return `http://127.0.0.1:${port}/`;
}

/**
 * 今のウィンドウで開いているワークスペースの、最初のフォルダの絶対パス。
 * 開いていなければ null。マルチルートでも最初の1つだけを見る
 * （どのフォルダが「今の」ワークスペースかを自動で決め打ちしない設計は
 * changelog 初期設定フローと揃えてある。詳細はそちらのコメントを参照）。
 */
function currentWorkspacePath() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || !folders.length) return null;
  const uri = folders[0].uri;
  // 仮想ワークスペース（vscode-vfs:// 等）の fsPath は `\github\owner\repo` のような
  // 「ローカルには存在しないのにローカルパスに見える」文字列。画面へ渡しても
  // 一致するプロジェクトは無いので、渡さない（先頭のプロジェクトに落ちる）。
  if (!uri || uri.scheme !== 'file') return null;
  return uri.fsPath;
}

/** エラーを出しつつ、ログを見る導線を必ず添える。 */
async function fail(message) {
  log(t('Failed: {message}', { message }));
  // ボタンの文言は変数に取ってから比べる。訳した文字列を直接 === で比べると、
  // 英語以外の言語で黙って一致しなくなる（押しても何も起きないボタンになる）。
  const viewLog = t('View log');
  const pick = await vscode.window.showErrorMessage(t('Subagent Dashboard: {message}', { message }), viewLog);
  if (pick === viewLog) out.show(true);
}

function looksLikeHome(dir) {
  return fs.existsSync(path.join(dir, 'dash.py')) && fs.existsSync(path.join(dir, 'server.py'));
}

function expand(raw) {
  return path.resolve(String(raw).trim().replace(/^~(?=[/\\]|$)/, os.homedir()));
}

// ---------------------------------------------------------------- 同梱した本体の配置

/** .vsix に同梱した本体の置き場所（読み取り専用の荷物として扱う）。 */
function bundleDir(context) {
  return path.join(context.extensionPath, 'tool');
}

function readVersion(dir) {
  try {
    return fs.readFileSync(path.join(dir, 'VERSION'), 'utf8').trim() || null;
  } catch (e) {
    return null;
  }
}

/** x.y.z を比べる。a が小さければ -1。 */
function cmpVersion(a, b) {
  const pa = String(a || '0').split('.').map((n) => parseInt(n, 10) || 0);
  const pb = String(b || '0').split('.').map((n) => parseInt(n, 10) || 0);
  for (let i = 0; i < 3; i++) {
    const x = pa[i] || 0;
    const y = pb[i] || 0;
    if (x !== y) return x < y ? -1 : 1;
  }
  return 0;
}

/** 上書きしながら足すだけ。既にあるもの（missions/ など）は消さない。 */
function copyInto(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  let n = 0;
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) n += copyInto(from, to);
    else { fs.copyFileSync(from, to); n++; }
  }
  return n;
}

/**
 * 同梱した本体を DEPLOY_DIR へ配置する。
 * @returns {{ home: string } | { error: string }}
 */
function deployBundle(context) {
  const src = bundleDir(context);
  if (!looksLikeHome(src)) {
    return { error: t('This extension does not bundle the dashboard tool ({src}).', { src }) };
  }
  try {
    const n = copyInto(src, DEPLOY_DIR);
    // POSIX 用ランチャに実行権限を戻す（ZIP は権限を運ばない）
    if (process.platform !== 'win32') {
      try { fs.chmodSync(path.join(DEPLOY_DIR, 'dash'), 0o755); } catch (e) { /* 無くても困らない */ }
    }
    log(t('Deployed the tool: {dir} ({n} files / version {version})', {
      dir: DEPLOY_DIR, n, version: readVersion(src) || t('unknown'),
    }));
    // 初期設定（install.py）はここでは走らせない。書き換える先が
    // ~/.claude/CLAUDE.md という「その人の設定」なので、必ず確認を取ってから。
    // 呼び手が scheduleSetup() を呼ぶ。
    return { home: DEPLOY_DIR };
  } catch (e) {
    return { error: t('Failed to deploy the tool: {err}', { err: e && e.message }) };
  }
}

/** 同梱の方が新しければ、1セッションに1回だけ更新を持ちかける。 */
async function offerUpdate(context, home) {
  if (updateOffered || !cfg().get('autoUpdateOnNewVersion')) return;
  if (!samePath(home, DEPLOY_DIR)) return;  // 自分で置いた場所以外は触らない
  const src = bundleDir(context);
  const bundled = readVersion(src);
  const current = readVersion(home);
  if (!bundled || cmpVersion(current, bundled) >= 0) return;
  updateOffered = true;

  const label = current
    ? t('version {from} -> {to}', { from: current, to: bundled })
    : t('version {to}', { to: bundled });
  const update = t('Update');
  const pick = await vscode.window.showInformationMessage(
    t('Subagent Dashboard: The bundled tool is newer ({label}). Update {dir}?', { label, dir: DEPLOY_DIR }),
    update, t('Later')
  );
  if (pick !== update) { log(t('The tool update was declined.')); return; }
  const r = deployBundle(context);
  if ('error' in r) { await fail(r.error); return; }
  vscode.window.showInformationMessage(
    t('Subagent Dashboard: Updated the tool to {version}. Your records (missions/) are untouched. Restart the server to apply it.',
      { version: bundled })
  );

  // 本体を新しくしても、CLAUDE.md に書いた運用ルールは古いまま残る。**本体と運用ルールは
  // 別々に古くなる。** 初期設定は一度成功すると自動では二度と走らない（globalState が
  // 覚えている）ので、scheduleSetup では届かない。運用ルールが増えた版では、増えたぶんが
  // Claude に届かないまま次の作業が始まってしまう。
  // manual: true で呼ぶと、何をどこに書くかを見せる確認から出し直せる。ここで自前の
  // ボタンを足すと、そのあと同じ確認がもう一度出て二段構えになるので足さない。
  await runSetup(context, r.home, { manual: true });
}

// ---------------------------------------------------------------- 場所の解決

/**
 * ダッシュボード本体の場所を決める。無ければ同梱物の配置を持ちかける。
 *
 * 順番は 設定 → ~/.claude/agent-dashboard → 環境変数 → 同梱物を配置。
 * ただし **設定 agentDashboard.home が指定されていて中身が違う場合は、別の場所へ勝手に逃げない。**
 * 逃げると、指定した覚えのない別のダッシュボードを見せられることになる。
 *
 * 失敗には reason を必ず付ける。失敗の紙のボタンは reason で決めており、
 * 文面の文字言い回しに依存させると、文章を直した拍子にボタンが変わってしまう。
 *
 * @param {boolean} interactive 未配置なら、その場で配置してよければ true
 *   （false は「押した覚えのない操作を勝手に始めない」ための道。タブの復元がそれ）
 * @returns {Promise<{ home: string } | { error: string, reason: string }>}
 */
async function ensureHome(context, interactive) {
  const fromSetting = String(cfg().get('home') || '').trim();
  if (fromSetting) {
    const home = expand(fromSetting);
    if (looksLikeHome(home)) {
      log(t('Dashboard tool: {home} (setting agentDashboard.home)', { home }));
      return { home };
    }
    return {
      reason: 'badSetting',
      error:
        t('The setting agentDashboard.home does not point at the dashboard tool: {home}', { home }) + '\n' +
        t('(Point it at the folder that holds dash.py and server.py. Leave it empty to search automatically.)'),
    };
  }

  if (looksLikeHome(DEPLOY_DIR)) {
    log(t('Dashboard tool: {home}', { home: DEPLOY_DIR }));
    offerUpdate(context, DEPLOY_DIR)
      .catch((e) => log(t('Error while asking about the update: {err}', { err: e && e.message })));
    return { home: DEPLOY_DIR };
  }

  const fromEnv = String(process.env.AGENT_DASHBOARD_HOME || '').trim();
  if (fromEnv) {
    const home = expand(fromEnv);
    if (looksLikeHome(home)) {
      log(t('Dashboard tool: {home} (environment variable AGENT_DASHBOARD_HOME)', { home }));
      return { home };
    }
  }

  // ここまで来たら未配置。同梱の荷物から置く
  const src = bundleDir(context);
  if (!looksLikeHome(src)) {
    // ここに来るのは「配る .vsix の作り方を間違えた」とき。設定を直しても解決しないので、
    // 利用者に agentDashboard.home を触らせる前に、まず何が起きているかを言う。
    return {
      reason: 'noBundle',
      error:
        t('The dashboard tool was not found.') + '\n' +
        t('It is neither at the deploy location ({dir}) nor bundled with this extension ({src}).',
          { dir: DEPLOY_DIR, src }) + '\n\n' +
        t('This .vsix seems to carry no tool. Ask whoever distributed it to rebuild a .vsix with the tool included, or, if you already have the tool (the folder that holds dash.py and server.py), put that path in the setting agentDashboard.home.'),
    };
  }
  if (!interactive) {
    return {
      reason: 'notDeployed',
      error: t('The tool is not deployed yet. Run the command "Subagent Dashboard: Deploy or update the tool".'),
    };
  }

  // **置いてよいかは訊かない。** 拡張を入れた＝使う、という前提。ここで断られた画面は
  // 「道具が無いので開けません」としか言えず、入れた人が次に何をすればよいのかも分からない。
  // 置くのは利用者のホーム配下の1か所で、同梱の荷物をそのまま複製するだけ。
  // どこへ置いたかはログに残る。
  log(t('The Subagent Dashboard tool will be placed here:') + ' ' + DEPLOY_DIR + '\n'
    + t('(The files bundled with the extension are copied. Your records will collect here from now on.)'));
  const placed = deployBundle(context);
  if ('error' in placed) return { reason: 'deployFailed', error: placed.error };
  // 置けたら初期設定を持ちかける。待たない — ここで待つと画面が出るのが遅くなるし、
  // install.py が書く先とサーバーが読む先は別なので、並んで走っても困らない。
  scheduleSetup(context, placed.home);
  return placed;
}

// ---------------------------------------------------------------- Python の解決

function tryPython(command) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (ok) => { if (!done) { done = true; resolve(ok); } };
    try {
      const proc = cp.spawn(command, ['-c', 'import sys; print(sys.version_info[0])'], {
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'ignore'],
      });
      let buf = '';
      proc.stdout.setEncoding('utf8');
      proc.stdout.on('data', (c) => { buf += c; });
      proc.on('error', () => finish(false));
      proc.on('close', (code) => finish(code === 0 && buf.trim() === '3'));
      setTimeout(() => { try { proc.kill(); } catch (e) { /* 既に死んでいる */ } finish(false); }, 6000);
    } catch (e) {
      finish(false);
    }
  });
}

/**
 * 使える Python を探す。
 * 設定 → Python 拡張の選択中インタープリタ → python / py / python3 の順。
 * @returns {Promise<string | null>}
 */
async function resolvePython() {
  const fromSetting = String(cfg().get('pythonPath') || '').trim();
  if (fromSetting) {
    if (await tryPython(fromSetting)) return fromSetting;
    log(t('The setting agentDashboard.pythonPath ("{path}") did not work. Falling back to auto-detection.',
      { path: fromSetting }));
  }

  if (pythonCache && (await tryPython(pythonCache))) return pythonCache;
  pythonCache = null;

  // Python 拡張が選んでいるインタープリタを借りる（入っていなければ黙って飛ばす）
  try {
    const ext = vscode.extensions.getExtension('ms-python.python');
    if (ext) {
      const api = ext.isActive ? ext.exports : await ext.activate();
      let candidate = null;
      if (api && api.environments && typeof api.environments.getActiveEnvironmentPath === 'function') {
        const p = api.environments.getActiveEnvironmentPath();
        candidate = p && p.path ? p.path : null;
      }
      if (!candidate && api && api.settings && typeof api.settings.getExecutionDetails === 'function') {
        const d = api.settings.getExecutionDetails();
        if (d && Array.isArray(d.execCommand) && d.execCommand.length) candidate = d.execCommand[0];
      }
      if (candidate && (await tryPython(candidate))) {
        log(t('Python: {path} (the interpreter selected in the Python extension)', { path: candidate }));
        pythonCache = candidate;
        return candidate;
      }
    }
  } catch (e) {
    log(t('Could not read it from the Python extension (ignored, continuing): {err}', { err: e && e.message }));
  }

  for (const name of process.platform === 'win32' ? ['python', 'py', 'python3'] : ['python3', 'python']) {
    if (await tryPython(name)) {
      log(t('Python: {path} (found on PATH)', { path: name }));
      pythonCache = name;
      return name;
    }
  }
  return null;
}

// ---------------------------------------------------------------- 初期設定（install.py）

/**
 * globalState を取り出す。持っていない context（試験用の偽物など）では null。
 *
 * 記録できない環境で確認だけ出すと、毎回同じことを聞かれる画面になる。
 * そうなるくらいなら黙って何もしない方がよいので、null を返して呼び手に判断させる。
 */
function memento(context) {
  const g = context && context.globalState;
  return g && typeof g.get === 'function' && typeof g.update === 'function' ? g : null;
}

/** install.py が CLAUDE.md を書く場所。install.py 側の claude_config_dir() と同じ規則。 */
function claudeConfigDir() {
  const env = String(process.env.CLAUDE_CONFIG_DIR || '').trim();
  return env ? path.resolve(env) : path.join(os.homedir(), '.claude');
}

/**
 * VSCode がユーザーのキーバインドを読む場所。
 *
 * **~/.vscode ではない。** あそこは拡張の置き場で、VSCode は keybindings.json を読まない。
 * そこを見ていると「書けます」と言いながら、実際には Ctrl+Shift+D が増えていない、
 * という嘘の成功を出してしまう。install.py 側も同じ規則で計算している。
 */
function vscodeKeybindingsPath() {
  if (process.platform === 'win32') {
    // APPDATA が無い環境（サービス実行など）でも当てが要るので、既定の場所を組み立てる
    const appData = String(process.env.APPDATA || '').trim();
    const base = appData ? appData : path.join(os.homedir(), 'AppData', 'Roaming');
    return path.join(base, 'Code', 'User', 'keybindings.json');
  }
  if (process.platform === 'darwin') {
    return path.join(os.homedir(), 'Library', 'Application Support', 'Code', 'User', 'keybindings.json');
  }
  const xdg = String(process.env.XDG_CONFIG_HOME || '').trim();
  const base = xdg ? xdg : path.join(os.homedir(), '.config');
  return path.join(base, 'Code', 'User', 'keybindings.json');
}

/** まだ無いディレクトリは親を辿る。確認のためだけにフォルダを作ってしまわない。 */
function existingAncestor(dir) {
  let p = path.resolve(dir);
  for (let i = 0; i < 64; i++) {
    if (fs.existsSync(p)) return p;
    const parent = path.dirname(p);
    if (parent === p) return p;
    p = parent;
  }
  return p;
}

/**
 * その場所に本当に書けるかを、1ファイル書いて消して確かめる。
 *
 * 存在するかどうかでは分からない。会社の端末ではホーム配下が読み取り専用にされていたり、
 * OneDrive の同期対象で一時的に掴まれていたりする。走らせてから途中で転ぶと、
 * CLAUDE.md だけ書けて keybindings.json は書けていない、といった半端な状態が残る。
 *
 * @returns {{ ok: true } | { ok: false, reason: string }}
 */
function checkWritable(target) {
  const dir = existingAncestor(target);
  const probeFile = path.join(dir, `.agent-dashboard-probe-${process.pid}`);
  try {
    fs.writeFileSync(probeFile, '', { encoding: 'utf8' });
    return { ok: true };
  } catch (e) {
    const code = (e && e.code) || '';
    const why =
      code === 'EACCES' || code === 'EPERM' ? t('writing is not permitted')
        : code === 'EROFS' ? t('it is read-only')
          : code === 'ENOSPC' ? t('there is no free space')
            : String((e && e.message) || code || e);
    return { ok: false, reason: t('{dir} ({why})', { dir, why }) };
  } finally {
    try { fs.unlinkSync(probeFile); } catch (e2) { /* 作れていなければ消すものも無い */ }
  }
}

/**
 * install.py が書き込む場所の一覧。preflightSetup() と試験の両方から使う。
 * 「どこを検査したか」を試験から確かめられるように、判定と分けて切り出してある。
 * @returns {[string, string][]} [表示名, ディレクトリ]
 */
function setupTargets(home) {
  return [
    [t('Home directory'), os.homedir()],
    [t('Claude config folder'), claudeConfigDir()],
    // 検査するのは実際に書かれるファイルの親。~/.vscode を見ても意味がない
    [t('VSCode keybindings'), path.dirname(vscodeKeybindingsPath())],
    [t('Dashboard tool'), home],
  ];
}

/**
 * install.py が触る先に書けるかを、実行前にまとめて確かめる。
 * @returns {string[]} 書けなかった場所の説明。空なら問題なし。
 */
function preflightSetup(home) {
  const blocked = [];
  for (const [label, dir] of setupTargets(home)) {
    const r = checkWritable(dir);
    if (!r.ok) blocked.push(t('{label}: {reason}', { label, reason: r.reason }));
  }
  return blocked;
}

/** 出力の末尾だけを取り出す。全部出すと通知が読めなくなる。 */
function tailLines(text, n) {
  return String(text || '')
    .split(/\r?\n/)
    .map((l) => l.replace(/\s+$/, ''))
    .filter((l) => l.trim())
    .slice(-n)
    .join('\n');
}

// install.py は「ステップ 1/4: 環境チェック」のような見出しを出す。そこだけ拾って進捗に出す。
//
// **見出しの語は install.py 側の言語で変わる。** 日本語だけを見ていると、あちらを英語化した
// 瞬間に進捗が黙って動かなくなる（例外は出ないので気づけない）。language ごとの語を並べて
// おき、どれでも拾えるようにしてある。ここに無い言語でも、進捗が出ないだけで設定は通る。
const STEP_RE = /(?:ステップ|Step|步骤|단계)\s*(\d+)\s*\/\s*(\d+)\s*[:：]\s*([^│|]+)/i;

/**
 * install.py を1回実行する。投げずに、必ず結果を返す。
 *
 * @returns {Promise<{ kind: 'ok' | 'exit' | 'spawn' | 'timeout' | 'cancel',
 *                     code: number | null, stdout: string, stderr: string, detail?: string }>}
 */
function runInstaller(python, installer, home, progress, token) {
  return new Promise((resolve) => {
    let settled = false;
    let stdout = '';
    let stderr = '';
    let timer = null;
    /** @type {import('child_process').ChildProcess | null} */
    let proc = null;

    const done = (kind, code, detail) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve({ kind, code: typeof code === 'number' ? code : null, stdout, stderr, detail });
    };
    const kill = () => { try { if (proc) proc.kill(); } catch (e) { /* もう死んでいる */ } };

    try {
      proc = cp.spawn(python, [installer], {
        cwd: home,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
        // install.py は罫線と絵文字を出す。Windows の既定（cp932）のままパイプへ繋ぐと
        // print が UnicodeEncodeError で落ち、設定が途中まで書かれた状態で止まる。
        env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' }),
      });
    } catch (e) {
      return done('spawn', null, (e && e.message) || String(e));
    }

    const attach = (stream, tag, onChunk) => {
      if (!stream) return;
      stream.setEncoding('utf8');
      let rest = '';
      stream.on('data', (chunk) => {
        onChunk(chunk);
        rest += chunk;
        const lines = rest.split(/\r?\n/);
        rest = lines.pop();
        for (const line of lines) {
          if (!line.trim()) continue;
          log(`${tag} ${line}`);
          const m = STEP_RE.exec(line);
          if (m && progress) {
            const total = Number(m[2]) || 4;
            progress.report({ message: `${m[1]}/${m[2]} ${m[3].trim()}`, increment: 100 / total });
          }
        }
      });
    };
    attach(proc.stdout, t('setup |'), (c) => { stdout += c; });
    attach(proc.stderr, t('setup !'), (c) => { stderr += c; });

    proc.on('error', (err) => done('spawn', null, (err && err.message) || String(err)));
    proc.on('close', (code) => done(code === 0 ? 'ok' : 'exit', code));

    timer = setTimeout(() => { kill(); done('timeout', null); }, SETUP_TIMEOUT_MS);

    if (token && typeof token.onCancellationRequested === 'function') {
      token.onCancellationRequested(() => { kill(); done('cancel', null); });
    }
  });
}

/**
 * 初期設定を実行する。**確認を取ってからしか走らせない。**
 *
 * install.py が書き換えるのは ~/.claude/CLAUDE.md と ~/.vscode/keybindings.json、
 * つまりこの拡張の外にある「その人の設定」。黙って触ってよいものではないので、
 * 何をどこに書くかを先に見せる。
 *
 * @param {vscode.ExtensionContext} context
 * @param {string} home ダッシュボード本体の場所
 * @param {{ manual?: boolean }} [opts] manual=true ならコマンドから明示的に呼ばれた（初回判定を無視する）
 */
async function runSetup(context, home, opts) {
  const manual = !!(opts && opts.manual);

  if (setupInFlight) {
    const msg = t('First-time setup is already running. Wait for it to finish, then try again.');
    log(t('{message} (ignored a duplicate run)', { message: msg }));
    // manual は利用者が自分でボタンを押した道。ログだけ吐いて黙って返ると
    // 「押したのに何も起きない」ことになり、他の失敗と違って手掛かりが残らない
    if (manual) vscode.window.showWarningMessage(t('Subagent Dashboard: {message}', { message: msg }));
    return;
  }
  // 排他は check-then-act にしてはいけない。最初の await より後ろでフラグを立てると、
  // 同時に呼ばれたとき両方が判定をすり抜けて install.py が2本走る（実測）。
  setupInFlight = true;
  try {
    await runSetupSteps(context, home, manual);
  } finally {
    setupInFlight = false;
  }
}

/**
 * runSetup の中身。排他フラグは呼び手（runSetup）が持っているので、ここでは触らない。
 *
 * 失敗時の「もう一度試す」は再帰ではなくループで回す。再帰にすると自分自身の排他に
 * 引っかかって、押しても何も起きない状態になる。
 *
 * @param {vscode.ExtensionContext} context
 * @param {string} home
 * @param {boolean} manualIn
 */
async function runSetupSteps(context, home, manualIn) {
  let manual = manualIn;
  const store = memento(context);

  if (!manual) {
    // ---- 要件1・5: 初回かどうかを globalState で判定する
    if (!cfg().get('runSetupOnFirstRun')) return;
    if (setupPrompted) return;
    if (!store) { log(t('globalState is unavailable, so the first-run setup prompt is skipped.')); return; }

    // ---- 環境変数トリガー: AGENT_DASHBOARD_RESET_SETUP または CLAUDE_CODE_RESET_ONBOARDING が '1' ならリセット
    if (process.env.AGENT_DASHBOARD_RESET_SETUP === '1' || process.env.CLAUDE_CODE_RESET_ONBOARDING === '1') {
      await store.update(SETUP_DONE_KEY, false);
      log(t('An environment variable triggered a setup reset.'));
    }

    if (store.get(SETUP_DONE_KEY)) { log(t('First-time setup has already run (globalState).')); return; }
    setupPrompted = true;
  }

  // 「もう一度試す」でここへ戻る。回数の上限は置かない（押した回数だけ試す）
  for (let attempt = 1; ; attempt++) {
    const installer = path.join(home, 'install.py');
    if (!fs.existsSync(installer)) {
      const msg = t('The first-time setup script was not found: {path}', { path: installer });
      log(msg);
      if (manual) await fail(msg);
      return;
    }

    // ---- 要件6: 走らせる前に、書けるかどうかを実測する
    const blocked = preflightSetup(home);
    if (blocked.length) {
      log(t('First-time setup was stopped (some locations are not writable):') + '\n  ' + blocked.join('\n  '));
      // 記録しない。権限を直せば次の起動でもう一度案内できる
      const viewLog0 = t('View log');
      const pick0 = await vscode.window.showErrorMessage(
        t('Subagent Dashboard: The locations needed for first-time setup are not writable.') + '\n' + blocked.join('\n'),
        viewLog0
      );
      if (pick0 === viewLog0) out.show(true);
      return;
    }

    // ---- 何をするかを見せる。**「するかどうか」は訊かない。**
    // 拡張を入れた＝使う、という前提に変えた。初期設定をしないまま入れておく状態は、
    // 「Ctrl+Shift+D が効かない」「Claude Code が使い方を知らない」という、
    // 壊れているのと見分けが付かない画面にしかならないため。
    // 書き込むのは利用者のホーム配下の2か所だけで、CLAUDE.md は目印で囲んだ区画しか
    // 書き換えないし、--uninstall で戻せる。走ったことは進捗表示と完了通知で分かる。
    //
    // 確認を出すのは、利用者が自分でコマンド「初期設定を実行」を呼んだときだけ。
    // そこは何が書かれるかを読める唯一の場所で、押した本人が閉じれば止められる。
    // 失敗して「もう一度試す」で戻ってきたときは出さない（manualIn で見るのはそのため。
    // 押し直しのたびに同じモーダルを出しても、読む内容は増えない）。
    const claudeMd = path.join(claudeConfigDir(), 'CLAUDE.md');
    const keybindings = vscodeKeybindingsPath();
    if (manualIn && attempt === 1) {
      const yes = t('Run');
      const pick = await vscode.window.showInformationMessage(
        t('The first-time setup for Subagent Dashboard will run. Is that OK?'),
        {
          modal: true,
          detail:
            t('Settings will be written into these two files.') + '\n\n' +
            `1. ${claudeMd}\n` +
            t('   Text that teaches Claude Code how to use Subagent Dashboard. Only the block between\n   the markers is rewritten, so nothing else already written there is lost.') + '\n\n' +
            `2. ${keybindings}\n` +
            t('   Makes Ctrl+Shift+D open Subagent Dashboard. If that key is already taken, it is left alone.') + '\n\n' +
            t('To undo it: python "{path}" --uninstall', { path: installer }),
        },
        yes
      );
      if (pick !== yes) {
        log(t('First-time setup was skipped. You can run it any time from the command "Run initial setup".'));
        return;
      }
    } else if (!manualIn && attempt === 1) {
      log(t('Running the first-time setup without asking (installing the extension is taken to mean it will be used). Files: {a} / {b}',
        { a: claudeMd, b: keybindings }));
    }

    const python = await resolvePython();
    if (!python) {
      await fail(
        t('Python was not found, so first-time setup cannot run. Put the path to the executable in the setting agentDashboard.pythonPath, or run this yourself:') +
        `\npython "${installer}"`
      );
      return;
    }

    // ---- 要件2: 実行中は進捗を出す
    log(t('Running first-time setup: {python} "{path}"', { python, path: installer }));
    const r = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: t('Running the first-time setup for Subagent Dashboard…'),
        cancellable: true,
      },
      (progress, token) => runInstaller(python, installer, home, progress, token)
    );

    // ---- 要件3: 成功と失敗で出し分ける
    if (r.kind === 'ok') {
      if (store) await store.update(SETUP_DONE_KEY, true);
      log(t('First-time setup finished.'));
      const openIt = t('Open Subagent Dashboard');
      const viewLog1 = t('View log');
      const next = await vscode.window.showInformationMessage(
        t('Subagent Dashboard: Setup complete. The instructions are written into CLAUDE.md, and Ctrl+Shift+D now opens it.'),
        openIt, viewLog1
      );
      if (next === openIt) await cmdOpen(context);
      else if (next === viewLog1) out.show(true);
      return;
    }

    if (r.kind === 'cancel') {
      log(t('First-time setup was cancelled. It may have been written partway through.'));
      vscode.window.showWarningMessage(
        t('Subagent Dashboard: First-time setup was cancelled. You can start over from the command "Run initial setup".')
      );
      return;
    }

    // 失敗。install.py は環境チェックの不備を標準出力に出すので、
    // stderr が空でも stdout を拾わないと「理由の分からない失敗」になる
    const detail =
      r.kind === 'spawn' ? t('Python could not be started: {err}', { err: r.detail })
        : r.kind === 'timeout' ? t('It did not finish within {sec} seconds.', { sec: SETUP_TIMEOUT_MS / 1000 })
          : tailLines(r.stderr, 8) || tailLines(r.stdout, 8) || t('There was no output.');
    const head =
      r.kind === 'exit'
        ? t('First-time setup failed (exit code {code}).', { code: r.code })
        : t('First-time setup failed.');

    log(t('Failed: {message}', { message: `${head}\n${detail}` }));
    const tryAgain = t('Try again');
    const viewLog2 = t('View log');
    const retry = await vscode.window.showErrorMessage(
      t('Subagent Dashboard: {message}', { message: head }) + `\n${detail}\n\n` +
      t('Running it yourself shows more detail: python "{path}"', { path: installer }),
      tryAgain, viewLog2
    );
    if (retry === viewLog2) { out.show(true); return; }
    if (retry !== tryAgain) return;
    // 押し直された道なので、以後は manual として扱う（初回判定で黙って飛ばさない）
    manual = true;
    log(t('Trying first-time setup again (attempt {n}).', { n: attempt + 1 }));
  }
}

/** 配置直後や起動直後に、初回セットアップの確認を持ちかける（待たない）。 */
function scheduleSetup(context, home) {
  runSetup(context, home, { manual: false })
    .catch((e) => log(t('Error while asking about first-time setup (ignored, continuing): {err}', { err: e && e.message })));
}

/**
 * マシン固有のキーを生成する。vscode.env.machineId が無い環境（テスト等）では os.hostname() で代替。
 * @returns {Promise<string>}
 */
async function getMachineKey() {
  const machineId = vscode.env?.machineId || os.hostname();
  return `setup_done_${machineId}`;
}

// ---------------------------------------------------------------- 初期設定（changelog_setup.py、ワークスペース単位）
//
// ここから下は「変更履歴トラッキング」機能のための初回設定フロー。上の install.py 系とは
// 完全に別軸で判定する（マシンにつき1回 ではなく ワークスペースにつき1回）。
// changelog_setup.py 自体は agent-dashboard 本体（home）に同梱される想定で、まだ存在しない
// 環境でも例外にはならず、単に「見つからなかった」ログを出して終わる（fs.existsSync で先に確認する）。

/**
 * ワークスペースのフォルダパスを globalState のキーに使えるハッシュへ変える。
 *
 * **samePath() の正規化ロジックとは独立させてある。** あちらは既にたくさんの呼び手が
 * 依存している既存資産なので、ここで正規化の中身を変えたくなっても samePath 側には触れない
 * （そちらを変えると起動時のポート再利用判定など、無関係な場所まで巻き添えにする）。
 * Windows では大小・区切りの違いを無視する（同じフォルダを別ワークスペースとして扱わないため）。
 */
function workspaceFolderHash(folderPath) {
  let s = path.resolve(String(folderPath));
  if (process.platform === 'win32') s = s.replace(/\\/g, '/').toLowerCase();
  s = s.replace(/\/+$/, '');
  return crypto.createHash('sha256').update(s, 'utf8').digest('hex');
}

function changelogSetupDoneKey(hash) { return `${CHANGELOG_SETUP_DONE_PREFIX}${hash}`; }
function changelogSetupSkipKey(hash) { return `${CHANGELOG_SETUP_SKIP_PREFIX}${hash}`; }

/**
 * changelog_setup.py が書き込む先の一覧。preflightChangelogSetup() と試験の両方から使う。
 * install.py 側の setupTargets() と同じ役割だが、対象はワークスペース内の2箇所だけ。
 * @returns {[string, string][]} [表示名, ディレクトリ]
 */
function changelogSetupTargets(workspaceRoot) {
  return [
    [t('Workspace folder'), workspaceRoot],
    [t('.claude folder'), path.join(workspaceRoot, '.claude')],
  ];
}

/**
 * changelog_setup.py が触る先に書けるかを、実行前にまとめて確かめる。
 * install.py 側の preflightSetup() と同じ型（1ファイル書いて消す実測、checkWritable() を共用）を、
 * ワークスペース内の書き込み先に適用したもの。
 * @returns {string[]} 書けなかった場所の説明。空なら問題なし。
 */
function preflightChangelogSetup(workspaceRoot) {
  const blocked = [];
  // 同じディレクトリを2回叩かない。`.claude` がまだ無いワークスペースでは
  // existingAncestor() が親（＝ワークスペース直下）に落ちるので、素直に回すと
  // 同じ場所へプローブファイルを2回書いて2回消すことになる（利用者のリポジトリを
  // 監視しているビルドツールから見れば、無意味な変更が2回起きる）。
  const seen = new Set();
  for (const [label, dir] of changelogSetupTargets(workspaceRoot)) {
    const probeDir = existingAncestor(dir);
    const key = process.platform === 'win32' ? probeDir.toLowerCase() : probeDir;
    if (seen.has(key)) continue;
    seen.add(key);
    const r = checkWritable(dir);
    if (!r.ok) blocked.push(t('{label}: {reason}', { label, reason: r.reason }));
  }
  return blocked;
}

/**
 * .gitignore の扱いを選ばせる QuickPick。EXTENSION_PLAN.md「4.6 .gitignore の扱い」節の
 * (A)/(B)/(C) をそのまま choices にしている。既定は (A)。
 * @returns {Promise<'A' | 'B' | 'C' | undefined>} Esc でキャンセルしたら undefined
 */
async function pickGitignoreMode() {
  const items = [
    {
      mode: 'A',
      label: `$(check) ${t('Ignore only the raw log (recommended)')}`,
      detail: t('log/ is ignored. sessions/, index.json and CHANGELOG.md stay tracked in Git, so the history lives in the repository.'),
    },
    {
      mode: 'B',
      label: `$(circle-large-outline) ${t('Ignore nothing')}`,
      detail: t('Everything under .claude/changelog/, including the raw log, is tracked as a full audit trail. Careful: the raw log keeps the first 10 lines of every Bash command and the tail of its output, so anything sensitive you typed on a command line gets committed to the repository.'),
    },
    {
      mode: 'C',
      label: `$(eye-closed) ${t('Ignore all of .claude/changelog/')}`,
      detail: t('Nothing under it is tracked in Git. Fully local to this machine.'),
    },
  ];
  const pick = await vscode.window.showQuickPick(items, {
    title: t('Subagent Dashboard: How should .claude/changelog/ be treated in .gitignore?'),
    placeHolder: t('Pick one (Escape cancels the setup)'),
    ignoreFocusOut: true,
  });
  return pick ? pick.mode : undefined;
}

/**
 * changelog_setup.py を1回実行する。**runInstaller と同じ型（進捗・タイムアウト・キャンセル）を
 * 踏襲**しつつ、任意の引数配列を渡せるようにしたきょうだい関数。
 *
 * install.py 側の runInstaller() 自体には触れていない（マシン単位フローのロジックを変えない、
 * という今回の制約のため）。中身がほぼ同じなのは承知のうえで、あえて共通化していない。
 *
 * @returns {Promise<{ kind: 'ok' | 'exit' | 'spawn' | 'timeout' | 'cancel',
 *                     code: number | null, stdout: string, stderr: string, detail?: string }>}
 */
function runChangelogSetupScript(python, scriptPath, args, cwd, progress, token) {
  return new Promise((resolve) => {
    let settled = false;
    let stdout = '';
    let stderr = '';
    let timer = null;
    /** @type {import('child_process').ChildProcess | null} */
    let proc = null;

    const done = (kind, code, detail) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      resolve({ kind, code: typeof code === 'number' ? code : null, stdout, stderr, detail });
    };
    const kill = () => { try { if (proc) proc.kill(); } catch (e) { /* もう死んでいる */ } };

    try {
      proc = cp.spawn(python, [scriptPath, ...args], {
        cwd,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
        // install.py と同じ理由。罫線や絵文字を出されても cp932 で落ちないように
        env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' }),
      });
    } catch (e) {
      return done('spawn', null, (e && e.message) || String(e));
    }

    const attach = (stream, tag, onChunk) => {
      if (!stream) return;
      stream.setEncoding('utf8');
      let rest = '';
      stream.on('data', (chunk) => {
        onChunk(chunk);
        rest += chunk;
        const lines = rest.split(/\r?\n/);
        rest = lines.pop();
        for (const line of lines) {
          if (!line.trim()) continue;
          log(`${tag} ${line}`);
          // changelog_setup.py が install.py と同じ「ステップ N/M: …」見出しを出す前提で
          // 拾っている。出さない実装でも例外にはならず、進捗の増分が出ないだけで動作は止まらない。
          const m = STEP_RE.exec(line);
          if (m && progress) {
            const total = Number(m[2]) || 4;
            progress.report({ message: `${m[1]}/${m[2]} ${m[3].trim()}`, increment: 100 / total });
          }
        }
      });
    };
    attach(proc.stdout, t('changelog setup |'), (c) => { stdout += c; });
    attach(proc.stderr, t('changelog setup !'), (c) => { stderr += c; });

    proc.on('error', (err) => done('spawn', null, (err && err.message) || String(err)));
    proc.on('close', (code) => done(code === 0 ? 'ok' : 'exit', code));

    timer = setTimeout(() => { kill(); done('timeout', null); }, CHANGELOG_SETUP_TIMEOUT_MS);

    if (token && typeof token.onCancellationRequested === 'function') {
      token.onCancellationRequested(() => { kill(); done('cancel', null); });
    }
  });
}

/**
 * ワークスペース単位の初期設定を実行する。**確認を取ってからしか走らせない。**
 * runSetup()（マシン単位）と同じ排他の型を踏襲した、独立した排他フラグを持つきょうだい関数。
 *
 * @param {vscode.ExtensionContext} context
 * @param {string} home ダッシュボード本体の場所（changelog_setup.py もここに居る想定）
 * @param {{ manual?: boolean, folder?: vscode.WorkspaceFolder }} [opts]
 *   manual=true ならコマンドから明示的に呼ばれた（初回判定を無視する）。
 *   folder を渡すと、対象フォルダを vscode.workspace.workspaceFolders[0] の決め打ちではなく
 *   明示的に指定できる（コマンドパレットからの手動実行で、利用者が選んだフォルダを使うため）。
 */
async function runWorkspaceChangelogSetup(context, home, opts) {
  const manual = !!(opts && opts.manual);

  if (changelogSetupInFlight) {
    const msg = t('The changelog setup is already running. Wait for it to finish, then try again.');
    log(t('{message} (ignored a duplicate run)', { message: msg }));
    if (manual) vscode.window.showWarningMessage(t('Subagent Dashboard: {message}', { message: msg }));
    return;
  }
  // runSetup() と同じ理由: check-then-act にしない。フラグは最初の await より前で立てる。
  changelogSetupInFlight = true;
  try {
    await runWorkspaceChangelogSetupSteps(context, home, manual, opts && opts.folder);
  } finally {
    changelogSetupInFlight = false;
  }
}

/**
 * runWorkspaceChangelogSetup の中身。排他フラグは呼び手が持っているので、ここでは触らない。
 * runSetupSteps() と同じ「失敗時はループで再試行」の型。
 *
 * @param {vscode.ExtensionContext} context
 * @param {string} home
 * @param {boolean} manualIn
 * @param {vscode.WorkspaceFolder} [forcedFolder] 指定があればこちらを優先する
 */
async function runWorkspaceChangelogSetupSteps(context, home, manualIn, forcedFolder) {
  let manual = manualIn;
  const store = memento(context);

  // ---- 対象フォルダの決定。
  // **マルチルートワークスペースでも、自動判定は最初のフォルダだけを見る。** 他のフォルダへ
  // 自動で書き込むのは事故のもと（意図しないリポジトリに hooks や .gitignore が増える）。
  // 他のフォルダに設定したい場合は、コマンドパレットから手動で（forcedFolder を渡して）実行する。
  const folders = vscode.workspace.workspaceFolders;
  const folder = forcedFolder || (folders && folders.length ? folders[0] : undefined);
  if (!folder) {
    if (manual) {
      vscode.window.showInformationMessage(t('Subagent Dashboard: No folder is open, so there is nothing to set up.'));
    } else {
      log(t('No workspace folder is open. The changelog setup is skipped.'));
    }
    return;
  }
  // ---- **ローカルのファイルシステムでなければ、ここで降りる。**
  //
  // package.json は virtualWorkspaces: true を宣言しているので、Remote Repositories
  // などで開いた `vscode-vfs://github/owner/repo` でもこの拡張は動く。そのとき
  // uri.fsPath は `\github\owner\repo` という「ローカルには無いのにローカルパスに見える」
  // 文字列になる。checkWritable() は existingAncestor() でドライブルートまで遡るので
  // 「書けます」と通ってしまい、確認モーダルにはもっともらしいパスが出て、
  // changelog_setup.py が C:\github\owner\repo\.claude\ という**利用者が開いてもいない
  // 場所**に本物のフォルダを作る。scheme を見ること以外にこれを防ぐ手段は無い。
  //
  // uri そのものが無い（試験のダミー等）ときも 'file' ではないほうへ倒す。ここで
  // 間違える向きは「余計に書き込む」ではなく「何もしない」でなければならない。
  const scheme = folder.uri ? String(folder.uri.scheme || '') : '';
  if (scheme !== 'file') {
    const msg = t('This folder is not on the local file system (scheme: {scheme}), so changelog tracking cannot be set up here. The hooks run Python against local files.',
      { scheme: scheme || t('unknown') });
    // 自動の道では黙って降りる（利用者は何も頼んでいない）。手動で呼ばれたときだけ理由を出す。
    if (manual) {
      log(msg);
      vscode.window.showInformationMessage(t('Subagent Dashboard: {message}', { message: msg }));
    } else {
      log(t('The changelog setup is skipped: the workspace is not on the local file system (scheme: {scheme}).', { scheme: scheme || t('unknown') }));
    }
    return;
  }

  const workspaceRoot = folder.uri.fsPath;
  const hash = workspaceFolderHash(workspaceRoot);
  const doneKey = changelogSetupDoneKey(hash);
  const skipKey = changelogSetupSkipKey(hash);

  if (!manual) {
    if (!cfg().get('runChangelogSetupOnFirstRun')) return;
    if (changelogSetupPrompted) return;
    // ---- **信頼していないワークスペースには、自分から持ちかけない。**
    // untrustedWorkspaces.supported: true なので、この拡張は信頼していないフォルダでも
    // 動く。しかしここで持ちかけているのは「全ツール呼び出しでこのマシンの Python を
    // 起動する hook を、そのフォルダに書き込んでよいか」であって、Workspace Trust が
    // 止めようとしていることそのもの。信頼していない間は、コマンドから明示的に
    // 呼ばれた場合（manual）だけに限る。
    // isTrusted が無い版の VSCode では undefined になるので、=== false で見る
    // （「分からない」を「信頼していない」に読み替えて黙らせない）。
    if (vscode.workspace.isTrusted === false) {
      log(t('The workspace is not trusted, so the changelog setup is not offered. You can still run it from the command "Set up changelog tracking".'));
      return;
    }
    if (!store) { log(t('globalState is unavailable, so the changelog setup prompt is skipped.')); return; }

    // ---- 環境変数トリガー。マシン単位フロー（runSetupSteps）と同じ2つの変数を見る。
    // あちらだけがリセットされて、こちらに前の判断が残るという食い違いを作らない。
    if (process.env.AGENT_DASHBOARD_RESET_SETUP === '1' || process.env.CLAUDE_CODE_RESET_ONBOARDING === '1') {
      const n = await resetChangelogSetupFlags(store);
      log(t('An environment variable triggered a setup reset ({n} changelog records cleared).', { n }));
    }

    if (store.get(CHANGELOG_SETUP_SKIP_ALL_KEY)) { log(t('The changelog setup is set to "Do not ask again in any workspace".')); return; }
    if (store.get(doneKey)) { log(t('The changelog setup has already run for this workspace (globalState).')); return; }
    if (store.get(skipKey)) { log(t('The changelog setup is set to "Do not ask again" for this workspace.')); return; }
    changelogSetupPrompted = true;
  }

  for (let attempt = 1; ; attempt++) {
    const scriptPath = path.join(home, 'changelog_setup.py');
    if (!fs.existsSync(scriptPath)) {
      const msg = t('The changelog setup script was not found: {path}', { path: scriptPath });
      log(msg);
      if (manual) await fail(msg);
      return;
    }

    // ---- 何をするかを見せて、確認を取る（runSetupSteps の確認モーダルと同じ型）
    //
    // **書けるかどうかの実測（preflight）は、この確認より後ろに置く。** あちらは
    // 対象ディレクトリに実際にファイルを1つ書いて消す。同意を取る前にそれをやると、
    // 利用者のリポジトリ直下に `.agent-dashboard-probe-<pid>` が一瞬現れて消え、
    // vite / nodemon / jest --watch / tsc -w が動いていれば再ビルドや再テストが走る。
    // 断られたら1バイトも書かない、が正しい順序（install.py 側はホーム配下しか
    // 触らないので、あちらの順序をそのまま真似てはいけなかった）。
    const settingsLocal = path.join(workspaceRoot, '.claude', 'settings.local.json');
    const gitignore = path.join(workspaceRoot, '.gitignore');
    const yes = manual ? t('Run') : t('Set up');
    const notAgain = t('Do not ask again for this workspace');
    const notAgainAnywhere = t('Do not ask again in any workspace');
    const buttons = manual ? [yes] : [yes, notAgain, notAgainAnywhere];

    const pick = await vscode.window.showInformationMessage(
      t('Subagent Dashboard: Set up changelog tracking for this workspace?'),
      {
        modal: true,
        detail:
          t('Workspace: {path}', { path: workspaceRoot }) + '\n\n' +
          t('This records what Claude Code changes in this project as it works. Settings will be written into these files.') + '\n\n' +
          `1. ${settingsLocal}\n` +
          t('   Adds hooks that call changelog_cli.py so edits are logged automatically. This file is meant to stay untracked (personal, machine-specific), so it never leaves this machine on its own.') + '\n\n' +
          `2. ${gitignore}\n` +
          t('   How much of .claude/changelog/ ends up tracked in Git is chosen on the next screen.') + '\n\n' +
          t('This is independent from the machine-wide setup: it is asked once per workspace, not once per machine.') +
          (manual ? '' : '\n\n' + t('Nothing is written until you choose "Set up". Closing this dialog (Esc) also stops the question for this workspace; the command "Set up changelog tracking" runs it later.')),
      },
      ...buttons
    );

    if (pick === notAgainAnywhere) {
      if (store) await store.update(CHANGELOG_SETUP_SKIP_ALL_KEY, true);
      log(t('The changelog setup: "Do not ask again in any workspace" was chosen. You can still run it per workspace from the command "Set up changelog tracking".'));
      return;
    }
    if (pick === notAgain) {
      if (store) await store.update(skipKey, true);
      log(t('The changelog setup: "Do not ask again" was chosen for this workspace. You can still run it later from the command "Set up changelog tracking".'));
      return;
    }
    if (pick !== yes) {
      // **Esc / キャンセルも、このワークスペースでは記録して二度と自動では出さない。**
      // 何も記録しないと、同じリポジトリを開き直すたびに同じモーダルが出る（ワークスペース
      // 単位のフローなので、断る回数がリポジトリの数だけ増える）。上のモーダルに
      // 「閉じてもこのワークスペースでは尋ねません」と先に書いてあるので、黙って
      // 決めているわけではない。手動（manual）の道では何も記録しない——自分で
      // 呼び出したものを閉じただけで、次から出なくなるのは筋が通らない。
      if (!manual && store) await store.update(skipKey, true);
      log(manual
        ? t('The changelog setup was cancelled. You can run it any time from the command "Set up changelog tracking".')
        : t('The changelog setup was skipped for this workspace. You can run it any time from the command "Set up changelog tracking".'));
      return;
    }

    // ---- 同意を得たので、ここで初めてワークスペースに触れる。書けるかどうかを実測する
    //      （install.py 側の preflightSetup と同じ規律。順序だけが違う理由は上のコメント）
    const blocked = preflightChangelogSetup(workspaceRoot);
    if (blocked.length) {
      log(t('The changelog setup was stopped (some locations are not writable):') + '\n  ' + blocked.join('\n  '));
      const viewLog0 = t('View log');
      const pick0 = await vscode.window.showErrorMessage(
        t('Subagent Dashboard: The locations needed for the changelog setup are not writable.') + '\n' + blocked.join('\n'),
        viewLog0
      );
      if (pick0 === viewLog0) out.show(true);
      return;
    }

    const mode = await pickGitignoreMode();
    if (!mode) {
      log(t('The changelog setup was cancelled (no .gitignore mode was chosen).'));
      return;
    }

    const python = await resolvePython();
    if (!python) {
      await fail(
        t('Python was not found, so the changelog setup cannot run. Put the path to the executable in the setting agentDashboard.pythonPath, or run this yourself:') +
        `\npython "${scriptPath}" --project-root "${workspaceRoot}" --gitignore-mode ${mode}`
      );
      return;
    }

    log(t('Running the changelog setup: {python} "{path}" --project-root "{root}" --gitignore-mode {mode}',
      { python, path: scriptPath, root: workspaceRoot, mode }));
    const r = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: t('Setting up changelog tracking for this workspace…'),
        cancellable: true,
      },
      (progress, token) => runChangelogSetupScript(
        python, scriptPath, ['--project-root', workspaceRoot, '--gitignore-mode', mode], home, progress, token
      )
    );

    // ---- 成功と失敗で出し分ける
    if (r.kind === 'ok') {
      if (store) {
        await store.update(doneKey, true);
        await store.update(skipKey, false);
      }
      log(t('The changelog setup finished for {path}.', { path: workspaceRoot }));
      vscode.window.showInformationMessage(
        t('Subagent Dashboard: Changelog tracking is set up for this workspace.')
      );
      return;
    }

    if (r.kind === 'cancel') {
      log(t('The changelog setup was cancelled. It may have been written partway through.'));
      vscode.window.showWarningMessage(
        t('Subagent Dashboard: The changelog setup was cancelled. You can start over from the command "Set up changelog tracking".')
      );
      return;
    }

    const detail =
      r.kind === 'spawn' ? t('Python could not be started: {err}', { err: r.detail })
        : r.kind === 'timeout' ? t('It did not finish within {sec} seconds.', { sec: CHANGELOG_SETUP_TIMEOUT_MS / 1000 })
          : tailLines(r.stderr, 8) || tailLines(r.stdout, 8) || t('There was no output.');
    const head =
      r.kind === 'exit'
        ? t('The changelog setup failed (exit code {code}).', { code: r.code })
        : t('The changelog setup failed.');

    log(t('Failed: {message}', { message: `${head}\n${detail}` }));
    const tryAgain = t('Try again');
    const viewLog2 = t('View log');
    const retry = await vscode.window.showErrorMessage(
      t('Subagent Dashboard: {message}', { message: head }) + `\n${detail}\n\n` +
      t('Running it yourself shows more detail: python "{path}" --project-root "{root}" --gitignore-mode {mode}',
        { path: scriptPath, root: workspaceRoot, mode }),
      tryAgain, viewLog2
    );
    if (retry === viewLog2) { out.show(true); return; }
    if (retry !== tryAgain) return;
    // 押し直された道なので、以後は manual として扱う（初回判定で黙って飛ばさない）
    manual = true;
    log(t('Trying the changelog setup again (attempt {n}).', { n: attempt + 1 }));
  }
}

/**
 * ワークスペース単位（changelog）の記録を全部消す。「初期設定をやり直す」から呼ぶ。
 *
 * 鍵はワークスペースごとに増える（`changelogSetupDone:<hash>`）ので、1本ずつ名前を
 * 知って消すことはできない。globalState.keys()（VSCode 1.69 以降）があれば接頭辞で
 * 総なめし、無い版では**いま開いているフォルダぶんだけ**を確実に消す。
 * どちらの道でも「消した数」を返し、呼び手が黙らずに済むようにする。
 *
 * @param {{ get: Function, update: Function, keys?: Function }} store
 * @returns {Promise<number>} 消した記録の数
 */
async function resetChangelogSetupFlags(store) {
  if (!store) return 0;
  const targets = new Set([CHANGELOG_SETUP_SKIP_ALL_KEY]);

  if (typeof store.keys === 'function') {
    let keys = [];
    try { keys = store.keys() || []; } catch (e) { keys = []; }
    for (const k of keys) {
      if (typeof k !== 'string') continue;
      if (k.indexOf(CHANGELOG_SETUP_DONE_PREFIX) === 0 || k.indexOf(CHANGELOG_SETUP_SKIP_PREFIX) === 0) targets.add(k);
    }
  } else {
    // keys() が無い版。開いているフォルダぶんだけでも消す（何も消えないよりはよい）
    for (const f of vscode.workspace.workspaceFolders || []) {
      if (!f.uri || f.uri.scheme !== 'file') continue;
      const h = workspaceFolderHash(f.uri.fsPath);
      targets.add(changelogSetupDoneKey(h));
      targets.add(changelogSetupSkipKey(h));
    }
  }

  let n = 0;
  for (const k of targets) {
    // undefined を入れると鍵ごと消える（false を書くと「断った」記録として残ってしまう）
    if (store.get(k) === undefined) continue;
    await store.update(k, undefined);
    n++;
  }
  changelogSetupPrompted = false;
  return n;
}

/** 起動直後に、ワークスペース単位の初期設定の確認を持ちかける（待たない）。 */
function scheduleWorkspaceChangelogSetup(context, home) {
  runWorkspaceChangelogSetup(context, home, { manual: false })
    .catch((e) => log(t('Error while asking about the changelog setup (ignored, continuing): {err}', { err: e && e.message })));
}

// ---------------------------------------------------------------- 生存確認

/**
 * ポートを1つ叩いて、そこに何が居るかを判定する。
 * @returns {Promise<{ kind: 'ours' | 'other' | 'free', toolRoot?: string }>}
 */
function probe(port) {
  return new Promise((resolve) => {
    let settled = false;
    const done = (v) => { if (!settled) { settled = true; resolve(v); } };

    const req = http.get(
      // agent:false で接続を毎回作り直す。Node は既定で接続を再利用するので、
      // 直前に死んだサーバー向けの古い接続を掴んで ECONNRESET になることがある
      { host: '127.0.0.1', port, path: HEALTH_PATH, agent: false, headers: { Connection: 'close' } },
      (res) => {
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (c) => { if (body.length < 65536) body += c; });
        res.on('end', () => {
          if (res.statusCode !== 200) return done({ kind: 'other' });
          try {
            const json = JSON.parse(body);
            // 我々のサーバーだけが返す形。これで別アプリを掴んでも事故らない
            if (json && typeof json.toolRoot === 'string' && typeof json.missionsDir === 'string') {
              return done({ kind: 'ours', toolRoot: json.toolRoot });
            }
          } catch (e) { /* JSON でない = 別のもの */ }
          done({ kind: 'other' });
        });
      }
    );
    req.setTimeout(PROBE_TIMEOUT_MS, () => {
      req.destroy();
      log(t('Port {port}: no response within {ms}ms.', { port, ms: PROBE_TIMEOUT_MS }));
      done({ kind: 'other' });
    });
    req.on('error', (err) => {
      // 接続を拒否された = 誰も居ない。それ以外は「何か居る」と保守的に見る
      const code = err && err.code;
      if (code !== 'ECONNREFUSED') log(t('Port {port}: connection error {code}', { port, code: code || err }));
      done({ kind: code === 'ECONNREFUSED' ? 'free' : 'other' });
    });
  });
}

/**
 * 使うポートを決める。すでに我々のサーバーが同じ home で動いていればそれを再利用する。
 * @returns {Promise<{ port: number, reuse: boolean } | { error: string, reason: string }>}
 */
async function decidePort(home) {
  const start = Number(cfg().get('port')) || 3939;
  for (let port = start; port <= start + PORT_SCAN_MAX; port++) {
    const r = await probe(port);
    if (r.kind === 'free') {
      log(t('Port {port} is free. Starting the server there.', { port }));
      return { port, reuse: false };
    }
    if (r.kind === 'ours' && samePath(r.toolRoot, home)) {
      log(t('A server is already running on port {port}. Reusing it.', { port }));
      return { port, reuse: true };
    }
    log(
      r.kind === 'ours'
        ? t('Port {port} is taken by a dashboard from another location ({root}). Looking at the next one.',
          { port, root: r.toolRoot })
        : t('Port {port} is taken by something else. Looking at the next one.', { port })
    );
  }
  return {
    reason: 'port',
    error: t('Ports {from} through {to} are all taken. Please change the setting agentDashboard.port.',
      { from: start, to: start + PORT_SCAN_MAX }),
  };
}

// ---------------------------------------------------------------- サーバーの起動

function spawnServer(python, home, port) {
  // dash.py 経由で起動する。dash.py が標準出力を UTF-8 に直してくれるので、
  // 日本語のログをパイプで受けても化けない。--no-retry でポートの繰り上げを止め、
  // 「拡張が決めた番号でしか立たない」状態にしている（EXTENSION_PLAN.md 5.3）。
  const args = [path.join(home, 'dash.py'), 'serve', '--host', '127.0.0.1', '--port', String(port), '--no-retry'];
  log(t('Starting: {command}', {
    command: `${python} ${args.map((a) => (/\s/.test(a) ? `"${a}"` : a)).join(' ')}`,
  }));

  const proc = cp.spawn(python, args, {
    cwd: home,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' }),
  });

  const pipe = (stream, tag) => {
    if (!stream) return;
    stream.setEncoding('utf8');
    let rest = '';
    stream.on('data', (chunk) => {
      rest += chunk;
      const lines = rest.split(/\r?\n/);
      rest = lines.pop();
      for (const line of lines) if (line.trim()) log(`${tag} ${line}`);
    });
  };
  pipe(proc.stdout, t('server |'));
  pipe(proc.stderr, t('server !'));

  proc.on('error', (err) => log(t('The server failed to start: {err}', { err: err && err.message })));
  proc.on('exit', (code, signal) => {
    log(t('The server exited (code={code} signal={signal})', { code, signal }));
    // ここへ来るのは**予期しない終了だけ**。明示的な停止や立て直しでは
    // stopOwnedServer / ensureServer が kill より先に owned = null を立てるので、
    // 下の条件が偽になって素通りする（その性質に頼っているので壊さないこと）。
    if (owned && owned.proc === proc) {
      owned = null;
      if (activePort === port) activePort = null;
      updateStatus();
      // サイドバーは繋がらない iframe を出したままになる。Python 側が落ちる・
      // OS に殺される・ターミナルから止められる、はどれも起きるのに、ここだけ
      // showStopped() が抜けていた。次の一手を必ず画面に出す。
      //
      // ただし**立ち上げの最中に死んだときは出さない。** そのときの結末は
      // ensureServerOnce が理由付きで返すので、ここで割り込むと嘘の紙が先に出る。
      if (proc === startingProc) {
        log(t('It exited while starting up, so the stopped notice is withheld (the startup path reports the outcome).'));
      } else if (sidebar) {
        try { sidebar.showStopped(); } catch (e) { log(t('Could not show the stopped notice: {err}', { err: e && e.message })); }
      }
    }
  });

  return proc;
}

/**
 * 起動したサーバーが応答するまで待つ。
 *
 * **死亡は owned ではなく、待っている proc そのものを見て判定する。**
 * owned を見ていたころ（`owned && owned.proc.exitCode !== null`）は、spawnServer の
 * exit ハンドラが先に `owned = null` を立てるので**この条件が永久に偽**になり、
 * 即死する環境で deadlineMs（15 秒）を丸ごと使い切っていた。
 *
 * 眠っている間に死んだら待たずに起きる。exitCode を覗くだけだと、気づくのが
 * 最悪 HEALTH_INTERVAL_MS ぶん遅れる。
 *
 * @param {import('child_process').ChildProcess} proc いま立ち上げようとしているプロセス
 * @returns {Promise<'ok' | 'dead' | 'timeout'>}
 *   dead と timeout は分けて返す。「15 秒以内に応答しませんでした」と言われたのに
 *   実際は 1 秒で死んでいた、では次の一手が決まらない。
 */
async function waitHealthy(port, home, deadlineMs, proc) {
  const dead = () => !!proc && (proc.exitCode !== null || proc.signalCode !== null);
  // exit の聞き手は1つだけ張る。ループの中で張ると回数ぶん積もって警告が出る
  let exited = dead();
  const gone = new Promise((resolve) => {
    if (exited) return resolve();
    if (proc && typeof proc.once === 'function') proc.once('exit', () => { exited = true; resolve(); });
  });

  const until = Date.now() + deadlineMs;
  while (Date.now() < until) {
    const r = await probe(port);
    if (r.kind === 'ours' && samePath(r.toolRoot, home)) return 'ok';
    if (exited || dead()) return 'dead';
    let timer = null;
    await Promise.race([
      new Promise((resolve) => { timer = setTimeout(resolve, HEALTH_INTERVAL_MS); }),
      gone,
    ]);
    if (timer) clearTimeout(timer);
  }
  return exited || dead() ? 'dead' : 'timeout';
}

/**
 * サーバーが居る状態を作る。**同時に2本走らせない。**
 *
 * 紙のボタンは押して 2 秒で戻るのに、この処理は decidePort だけで最悪 11ポート×1.2秒、
 * waitHealthy でさらに 15 秒かかる。画面が変わらないので利用者はもう一度押す。
 * 排他が無いと、1本目が spawn 済みでまだ bind していない隙間で probe が free を返し、
 * 2本目を spawn して owned を上書きする。2本目は --no-retry で即死するが waitHealthy は
 * 1本目の応答を見て healthy と判定するので、owned.proc が死んだ方を指す。
 * そうなると cmdStop が「停止しました」と言うのに実体は生き残り、ポートを掴んだままになる。
 *
 * 実行中の Promise を共有するので、配置の確認モーダルが2枚出る問題も同時に消える。
 * @returns {Promise<{ port: number } | { error: string, reason: string }>}
 */
async function ensureServer(context, interactive) {
  if (ensureServerInFlight) {
    log(t('Securing the server is already in progress. Waiting for that result.'));
    return ensureServerInFlight;
  }
  const p = ensureServerOnce(context, interactive);
  ensureServerInFlight = p;
  try {
    return await p;
  } finally {
    // 自分が立てた分だけ下ろす（後から入れ替わっていたら触らない）
    if (ensureServerInFlight === p) ensureServerInFlight = null;
  }
}

/** ensureServer の中身。排他は呼び手が持っているので、ここでは気にしない。 */
async function ensureServerOnce(context, interactive) {
  const resolved = await ensureHome(context, interactive !== false);
  if ('error' in resolved) return resolved;
  const home = resolved.home;

  // すでに我々が立てたものが生きていれば、それをそのまま使う
  if (owned && owned.proc.exitCode === null && samePath(owned.home, home)) {
    const r = await probe(owned.port);
    if (r.kind === 'ours') { activePort = owned.port; updateStatus(); return { port: owned.port }; }
  }

  const decided = await decidePort(home);
  if ('error' in decided) return decided;

  if (decided.reuse) {
    activePort = decided.port;
    updateStatus();
    return { port: decided.port };
  }

  if (!cfg().get('autoStartServer')) {
    return {
      reason: 'autoStartOff',
      error: t('No server is listening on port {port}. Auto-start is turned off in the settings (agentDashboard.autoStartServer).',
        { port: decided.port }),
    };
  }

  const python = await resolvePython();
  if (!python) {
    return {
      reason: 'python',
      error: t('Python was not found. Put the path to the executable in the setting agentDashboard.pythonPath. (This tool needs Python 3.9 or newer.)'),
    };
  }

  const state = await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: t('Starting the Subagent Dashboard server…'),
      cancellable: false,
    },
    async () => {
      const proc = spawnServer(python, home, decided.port);
      owned = { proc, port: decided.port, home };
      // 立ち上げの最中に死んでも、停止の紙を割り込ませない（結末はこの関数が返す）
      startingProc = proc;
      try {
        const r = await waitHealthy(decided.port, home, HEALTH_TIMEOUT_MS, proc);
        if (r !== 'ok') {
          // kill より先に手放す。そうしないと exit ハンドラが「予期しない終了」と勘違いして
          // サイドバーに停止の紙を出し、このあと呼び手が出す理由付きの紙と喧嘩する
          if (owned && owned.proc === proc) owned = null;
          try { proc.kill(); } catch (e) { /* 既に死んでいる */ }
        }
        return r;
      } finally {
        if (startingProc === proc) startingProc = null;
      }
    }
  );

  if (state !== 'ok') {
    return {
      reason: 'serverDead',
      error: state === 'dead'
        ? t('The server exited right after starting. The log holds the output from the Python side.') + '\n' +
          t('(This happens when Python is too old, the deployed tool is broken, or a firewall or resident program is blocking listening on 127.0.0.1.)')
        : t('The server did not respond within {sec} seconds. The log holds the output from the Python side.',
          { sec: HEALTH_TIMEOUT_MS / 1000 }),
    };
  }

  log(t('Startup complete: {url}', { url: urlFor(decided.port) }));
  activePort = decided.port;
  updateStatus();
  return { port: decided.port };
}

/**
 * 拡張が立てたサーバーを止める。外部のものには手を付けない。
 *
 * @returns {boolean} 本当に生きているものを止めたときだけ true。
 *   既に終わっていたプロセスに対して true を返すと、呼び手が「停止しました」と
 *   言ってしまう。実体が無いのに成功を名乗るのは、この画面が一番やってはいけないこと。
 */
function stopOwnedServer(reason) {
  if (!owned) return false;
  const proc = owned.proc;
  // kill より先に手放す。exit ハンドラは owned.proc が自分かどうかで
  // 「予期しない終了」を見分けているので、ここで消しておけば素通りしてくれる
  owned = null;
  activePort = null;
  if (proc.exitCode !== null || proc.signalCode !== null) {
    log(t('The server had already exited ({reason}). There is nothing to stop.', { reason }));
    updateStatus();
    return false;
  }
  log(t('Stopping the server ({reason})', { reason }));
  try { proc.kill(); } catch (e) { log(t('Failed to stop it: {err}', { err: e && e.message })); }
  updateStatus();
  return true;
}

// ---------------------------------------------------------------- 画面

/**
 * HTML に埋める文字列のエスケープ。**訳した文字列も必ずここを通す。**
 *
 * 訳文に & や < が混じることは十分ありうるし、混じった瞬間に画面が壊れるのに
 * その場では気づけない。panelHtml と noticeHtml で同じものを使う。
 */
function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/**
 * Webview に流し込む外枠の HTML。中身は iframe 1枚だけ。
 *
 * この形は VSCode 同梱の Simple Browser 拡張（resources/app/extensions/simple-browser）と
 * 同じ構造で、あちらは frame-src を `*` にしている。こちらは繋ぐ先が分かっているので
 * オリジンを1つだけ許可して閉じてある。
 *
 * iframe に sandbox 属性を付けていないのは意図的。付けると
 *   - allow-same-origin が無いと画面側の fetch('/api/state') が壊れる
 *   - allow-modals が無いとタブ削除の確認ダイアログ（window.confirm）が動かない
 * という制約がぶら下がる。付けない場合は既定で全部使えるので、許可漏れで機能が欠ける事故が起きない。
 * 中身は自分で立てたローカルサーバーなので、隔離して守る相手がいない。
 *
 * @param {number} port
 * @param {string | null} [workspacePath] 今のワークスペースの絶対パス。渡すと iframe の src に
 *   `?workspace=` クエリとして付ける。変更履歴画面（public/index.html の clWorkspaceParam）が
 *   これを読んで、登録済みプロジェクトの中から今開いているワークスペースを自動で選ぶ。
 *   渡さない・null のときは `${origin}/` のままで、画面は先頭のプロジェクトに落ちる。
 */
function panelHtml(port, workspacePath) {
  const origin = `http://127.0.0.1:${port}`;
  // <title> は HTML なのでエスケープを通す。訳文に & や < が入っても壊れないように
  const title = escapeHtml(t('Subagent Dashboard'));
  // encodeURIComponent が " < > & も %XX に変換するので、そのまま属性値に埋めて安全
  const src = workspacePath ? `${origin}/?workspace=${encodeURIComponent(workspacePath)}` : `${origin}/`;
  return `<!DOCTYPE html>
<html lang="${htmlLang()}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; frame-src ${origin}; style-src 'unsafe-inline';">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
  html, body { margin: 0; padding: 0; height: 100%; overflow: hidden; background: #0d131c; }
  iframe { display: block; border: 0; width: 100%; height: 100%; }
</style>
</head>
<body>
<iframe src="${src}" allow="clipboard-read; clipboard-write"></iframe>
</body>
</html>`;
}

/**
 * 起動中や失敗のときにサイドバーへ出す紙。黒い画面のまま黙らせない。
 *
 * `actions` を渡すと押せるボタンが並ぶ。**通知（showInformationMessage）は、出ないことがある。**
 * 通知を切っている、別の通知に流された、そもそも通知が出る手前で止まった — どれも起きる。
 * そうなると利用者の手には何も残らないので、詰まった理由を出している画面そのものに、
 * 先へ進む手段を置く。押すと postMessage が飛んで DashboardView.onAction が受ける。
 *
 * @param {string} title
 * @param {string} [detail]
 * @param {{ id: string, label: string, primary?: boolean }[]} [actions]
 */
function noticeHtml(title, detail, actions) {
  const esc = escapeHtml;
  const list = Array.isArray(actions) ? actions : [];
  // インラインの script を CSP で通すための使い捨ての鍵。'unsafe-inline' は使わない
  const nonce = crypto.randomBytes(16).toString('base64');
  const buttons = list
    .map((a) =>
      `<button type="button" data-action="${esc(a.id)}"${a.primary ? ' class="primary"' : ''}>${esc(a.label)}</button>`
    )
    .join('\n  ');

  return `<!DOCTYPE html>
<html lang="${htmlLang()}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
<style>
  body {
    margin: 0; padding: 18px 16px;
    font: 13px/1.7 var(--vscode-font-family, sans-serif);
    color: var(--vscode-foreground);
    background: var(--vscode-sideBar-background);
  }
  h1 { font-size: 13px; font-weight: 600; margin: 0 0 8px; }
  p { margin: 0; color: var(--vscode-descriptionForeground); white-space: pre-wrap; }
  .actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; }
  button {
    font: inherit; line-height: 1.4; padding: 4px 12px; cursor: pointer;
    border: 1px solid var(--vscode-button-border, transparent); border-radius: 2px;
    color: var(--vscode-button-secondaryForeground, var(--vscode-button-foreground));
    background: var(--vscode-button-secondaryBackground, var(--vscode-button-background));
  }
  button.primary {
    color: var(--vscode-button-foreground);
    background: var(--vscode-button-background);
  }
  button:hover { background: var(--vscode-button-secondaryHoverBackground, var(--vscode-button-hoverBackground)); }
  button.primary:hover { background: var(--vscode-button-hoverBackground); }
  button:focus-visible { outline: 1px solid var(--vscode-focusBorder); outline-offset: 2px; }
  button:disabled { opacity: .55; cursor: default; }
</style>
</head>
<body>
<h1>${esc(title)}</h1>
${detail ? `<p>${esc(detail)}</p>` : ''}
${list.length ? `<div class="actions">\n  ${buttons}\n</div>` : ''}
${list.length ? `<script nonce="${nonce}">
  const api = acquireVsCodeApi();
  const all = Array.from(document.querySelectorAll('button[data-action]'));
  for (const b of all) {
    b.addEventListener('click', () => {
      // 押した直後は全部止める。配置や初期設定は時間がかかるので、
      // 連打されると同じものが二重に走ったように見える
      for (const x of all) x.disabled = true;
      api.postMessage({ action: b.dataset.action });
      setTimeout(() => { for (const x of all) x.disabled = false; }, 2000);
    });
  }
</script>` : ''}
</body>
</html>`;
}

/**
 * いま本体があると思われる場所を返す。**尋ねないし、作らない。**
 * ボタンの出し分けを決めるためだけに使う。
 *
 * 探す順番は ensureHome() と**完全に一致させる**（設定 → DEPLOY_DIR → 環境変数）。
 * ずれると、ensureHome が使う本体と画面が前提にしている本体が食い違い、
 * たとえば AGENT_DASHBOARD_HOME で指定している人に「本体を配置」を勧めてしまう。
 * 押されると DEPLOY_DIR に二重配置され、記録（missions/）が二箇所に分裂する。
 *
 * 「どこにも無い」と「設定が指す先に無い」は区別する。後者で配置を勧めても、
 * deployBundle が置くのは DEPLOY_DIR（固定）なのに ensureHome は設定を最優先するので、
 * 画面は寸分違わぬ紙に戻る。害だけがあって何も好転しない。
 *
 * @returns {{ kind: 'ok', home: string } | { kind: 'badSetting', home: string } | { kind: 'none' }}
 */
function currentHome() {
  const fromSetting = String(cfg().get('home') || '').trim();
  if (fromSetting) {
    // 設定があるときは他所へ逃げない。ensureHome() と同じ約束
    const home = expand(fromSetting);
    return looksLikeHome(home) ? { kind: 'ok', home } : { kind: 'badSetting', home };
  }

  if (looksLikeHome(DEPLOY_DIR)) return { kind: 'ok', home: DEPLOY_DIR };

  const fromEnv = String(process.env.AGENT_DASHBOARD_HOME || '').trim();
  if (fromEnv) {
    const home = expand(fromEnv);
    if (looksLikeHome(home)) return { kind: 'ok', home };
  }

  return { kind: 'none' };
}

/**
 * 失敗の紙に並べるボタンを決める。
 *
 * **primary は「何が原因か」で決める。**「本体が置いてあるか」だけで決めていたころは、
 * 設定が不正なときに配置ボタンが先頭に来て、押すと ~/.claude/CLAUDE.md が書き換わるのに
 * 画面は同じ紙のまま、という一番たちの悪い失敗をしていた。
 *
 * 判定に文面の文字列を使わないこと。文章を直した拍子にボタンが変わる。
 *
 * @param {string} [reason] ensureHome / decidePort / ensureServer が返した失敗の理由コード
 */
function noticeActions(reason) {
  const state = currentHome();
  // 設定が指す先に本体が無いなら、原因は設定ひとつ。配置ボタンは**一切出さない**
  const badSetting = reason === 'badSetting' || state.kind === 'badSetting';

  let primary;
  if (badSetting) {
    primary = { id: 'settings', label: t('Fix the setting agentDashboard.home'), primary: true };
  } else if (reason === 'python') {
    // install.py も Python を要るので、ここで初期設定を勧めても空振りする
    primary = { id: 'settings', label: t('Set where Python is'), primary: true };
  } else if (reason === 'port') {
    primary = { id: 'settings', label: t('Change the port number'), primary: true };
  } else if (reason === 'autoStartOff') {
    // 自分で切った設定なので、もう一度試しても同じ紙に戻るだけ
    primary = { id: 'settings', label: t('Look at the auto-start setting'), primary: true };
  } else if (reason === 'noBundle') {
    // 置く荷物が無い。配置ボタンを出しても押せる先が無い
    primary = { id: 'settings', label: t('Set where the tool is'), primary: true };
  } else if (reason === 'declined' || reason === 'notDeployed' || reason === 'deployFailed') {
    primary = { id: 'deploy', label: t('Deploy the tool and set it up'), primary: true };
  } else {
    // serverDead など、時間を置けば通ることがあるもの
    primary = { id: 'retry', label: t('Try again'), primary: true };
  }

  const actions = [primary];
  const add = (a) => { if (!actions.some((x) => x.id === a.id)) actions.push(a); };
  add({ id: 'retry', label: t('Try again') });
  if (state.kind === 'ok') add({ id: 'setup', label: t('Run initial setup') });
  else if (!badSetting) add({ id: 'deploy', label: t('Deploy the tool and set it up') });
  add({ id: 'settings', label: t('Open the settings') });
  add({ id: 'log', label: t('View log') });
  return actions;
}

/**
 * 失敗の紙のボタンが押されたときの処理。**サイドバーとタブで同じ道を通す。**
 *
 * 紙は同じものが両方に出るので、ここを分けると「左では配置できるのにタブでは何も起きない」
 * のような、押した場所で結果が変わる画面ができる。
 *
 * @param {vscode.ExtensionContext} context
 * @param {string} action
 * @param {() => Promise<void> | void} retry 押したあとに画面を描き直す手続き（押した場所ごとに違う）
 * @returns {Promise<boolean>} 知っているボタンだったか
 */
async function runNoticeAction(context, action, retry) {
  switch (action) {
    case 'deploy':
      // 配置したあと、初期設定は manual として走らせる。ここは利用者が自分で押した道なので、
      // 「もう済んでいる」という記録（globalState）で黙って飛ばしてはいけない
      await cmdDeploy(context, { manualSetup: true });
      await retry();
      return true;
    case 'setup':
      await cmdRunSetup(context);
      await retry();
      return true;
    case 'retry':
      await retry();
      return true;
    case 'settings':
      await vscode.commands.executeCommand('workbench.action.openSettings', 'agentDashboard');
      return true;
    case 'log':
      out.show(true);
      return true;
    default:
      return false;
  }
}

/**
 * @param {number} port
 * @param {{ reveal?: boolean }} [opts]
 *   reveal=false なら、既にあるタブを前に出さずに中身だけ差し替える。
 *   再起動のように「利用者がタブを触っていない」道で勝手に前へ出さないため。
 */
function openWebview(context, port, opts) {
  const reveal = !(opts && opts.reveal === false);
  if (panel) {
    paintPanel(panel, port);
    if (reveal) panel.reveal(panel.viewColumn || vscode.ViewColumn.One, false);
    return;
  }
  const created = vscode.window.createWebviewPanel(
    PANEL_TYPE,
    t('Subagent Dashboard'),
    { viewColumn: vscode.ViewColumn.Active, preserveFocus: false },
    {
      // 外枠に script は書いていないが、ここを false にすると Webview 自体の sandbox から
      // allow-scripts が外れ、入れ子の iframe まで JS が止まる。画面が動かなくなるので true。
      enableScripts: true,
      // タブを裏に回してもロボットのアニメーションとポーリングを保つ
      retainContextWhenHidden: true,
      // 外枠はローカルファイルを一切読まない
      localResourceRoots: [],
      // 将来 Remote / SSH で使うときのため。ローカルでは無害
      portMapping: [{ webviewPort: port, extensionHostPort: port }],
    }
  );
  adoptPanel(context, created);
  paintPanel(created, port);
  log(t('Showed {url} in the webview.', { url: urlFor(port) }));
}

/**
 * 作ったタブ・復元されたタブを、この拡張が持つ1枚として引き受ける。
 *
 * **復元で渡ってくるタブは VSCode が作ったもの**なので、createWebviewPanel の戻り値と
 * 同じ世話（アイコン・後始末・ボタンの受け口）を焼かないと、見た目も操作も欠けたタブになる。
 * 両方の道がここを通るようにして、片方だけ手当てを忘れる形を作らない。
 *
 * @param {vscode.ExtensionContext} context
 * @param {vscode.WebviewPanel} p
 */
function adoptPanel(context, p) {
  panel = p;
  panelNotice = false;

  try {
    const iconDir = vscode.Uri.joinPath(context.extensionUri, 'media');
    p.iconPath = {
      light: vscode.Uri.joinPath(iconDir, 'panel-light.png'),
      dark: vscode.Uri.joinPath(iconDir, 'panel-dark.png'),
    };
  } catch (e) {
    log(t('Could not set the tab icon (the display continues): {err}', { err: e && e.message }));
  }

  p.onDidDispose(() => {
    if (panel === p) { panel = undefined; panelNotice = false; }
  }, null, context.subscriptions);

  // 失敗の紙に置いたボタンの受け口。iframe を出している間は誰も送ってこない。
  // **サイドバーだけに付けていては足りない。** 復元は「開いたら真っ先に紙が出る」道を
  // 持っているので、ここが無いと押せないボタンだけが並んだタブができる。
  if (typeof p.webview.onDidReceiveMessage === 'function') {
    const d = p.webview.onDidReceiveMessage((msg) =>
      onPanelAction(context, p, msg && msg.action)
        .catch((e) => log(t('Error while handling a tab button: {err}', { err: e && e.message })))
    );
    const subs = context && context.subscriptions;
    if (Array.isArray(subs) && d && typeof d.dispose === 'function') subs.push(d);
  }
}

/**
 * タブに iframe を出す。
 *
 * ポートが繰り上がっているとき、作成時の portMapping のままだと Remote / SSH で
 * 繋がらない（ローカルでは無害なので気づけない）。サイドバー側は refresh() で
 * options ごと入れ替えているので、タブ側も揃える。
 *
 * @param {vscode.WebviewPanel} p
 * @param {number} port
 */
function paintPanel(p, port) {
  try {
    p.webview.options = Object.assign({}, p.webview.options, {
      enableScripts: true,
      localResourceRoots: [],
      portMapping: [{ webviewPort: port, extensionHostPort: port }],
    });
  } catch (e) {
    log(t('Could not update the tab portMapping (the display continues): {err}', { err: e && e.message }));
  }
  p.webview.html = panelHtml(port, currentWorkspacePath());
  if (panel === p) panelNotice = false;
}

/**
 * 復元されたタブを、いまのサーバーへ繋ぎ直す。
 *
 * **前に見ていたポート番号は覚えないし、使い回さない。** VSCode を閉じた時点で、この拡張が
 * 立てたサーバーは止まっている（設定 stopServerOnExit の既定が true）。番号だけ復元しても
 * 繋がらない iframe が出るだけなので、開くときと同じ道（ensureServer）でもう一度確保する。
 *
 * **尋ねない（interactive=false）。** 復元はウィンドウを開き直した拍子に起きる。押した覚えの
 * ない場面で「本体を配置しますか？」というモーダルを突きつけるのは筋が悪い。本体が無いときは
 * 紙に「配置して初期設定」のボタンを出し、押されてから尋ねる。
 *
 * @param {vscode.ExtensionContext} context
 * @param {vscode.WebviewPanel} p
 */
async function restorePanel(context, p) {
  p.webview.html = noticeHtml(t('Starting Subagent Dashboard…'));
  panelNotice = true;

  const r = await ensureServer(context, false);
  if (panel !== p) { log(t('The restored tab was closed while we were waiting.')); return; }

  if ('error' in r) {
    log(t('Restored tab: {message}', { message: r.error }));
    // ボタンは理由コードで決める。文面から推測しない（サイドバーと同じ約束）
    p.webview.html = noticeHtml(t('Subagent Dashboard cannot be shown'), r.error, noticeActions(r.reason));
    panelNotice = true;
    return;
  }

  paintPanel(p, r.port);
  log(t('Reconnected the restored tab to {url}.', { url: urlFor(r.port) }));
}

/**
 * タブに出した失敗の紙のボタンが押された。
 *
 * **「もう一度試す」で描き直すのはタブ側。** ここを sidebar.refresh() に落とすと、
 * 押した場所と直る場所が食い違い、タブは紙のまま変わらない。
 *
 * @param {vscode.ExtensionContext} context
 * @param {vscode.WebviewPanel} p
 * @param {string} action
 */
async function onPanelAction(context, p, action) {
  log(t('Tab button: {action}', { action }));
  const handled = await runNoticeAction(context, action, () => restorePanel(context, p));
  if (!handled) log(t('That button was not recognised: {action}', { action }));
}

/**
 * アクティビティバーから開くサイドバーの中身。
 *
 * retainContextWhenHidden は付けていない（既定の false）。サイドバーを閉じている間は
 * 中身が捨てられるので、見ていないのにポーリングし続けることがない。
 * 開き直すと resolveWebviewView がもう一度呼ばれて描き直される。
 */
class DashboardView {
  constructor(context) {
    this.context = context;
    /** @type {vscode.WebviewView | undefined} */
    this.view = undefined;
    this.port = null;
  }

  resolveWebviewView(webviewView) {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true, localResourceRoots: [] };
    webviewView.webview.html = noticeHtml(t('Starting Subagent Dashboard…'));

    // 受け取った Disposable は context.subscriptions に積む。捨てると deactivate で
    // 明示的に切れない（重複配信は retainContextWhenHidden:false のおかげで起きないが、
    // 規約違反なのは変わらない）。
    const keep = [];
    if (typeof webviewView.onDidDispose === 'function') {
      keep.push(webviewView.onDidDispose(() => { if (this.view === webviewView) this.view = undefined; }));
    }
    // 失敗の紙に置いたボタンの受け口。iframe を出しているときは誰も送ってこない
    if (typeof webviewView.webview.onDidReceiveMessage === 'function') {
      // VSCode は戻り値を見ないが、返しておくと試験から押した結果を待てる
      keep.push(webviewView.webview.onDidReceiveMessage((msg) =>
        this.onAction(msg && msg.action)
          .catch((e) => log(t('Error while handling a button: {err}', { err: e && e.message })))
      ));
    }
    const subs = this.context && this.context.subscriptions;
    if (Array.isArray(subs)) {
      for (const d of keep) if (d && typeof d.dispose === 'function') subs.push(d);
    }

    // 既定（sidebarBehavior = openInTab）では、ここには埋め込まずタブへ移す。
    // アクティビティバーのアイコンのクリック先そのものを差し替える手段は VSCode に
    // 無いので、開かれた直後に自分で移すのが唯一の道。
    if (this.tabMode()) {
      this.handOffToTab(webviewView).catch((e) => {
        log(t('Error while handing off to a tab: {err}', { err: e && e.message }));
        if (this.view !== webviewView) return;
        // ここで黙ると、サイドバーは閉じていないのに「起動しています…」のまま止まる
        try {
          webviewView.webview.html = noticeHtml(
            t('It could not be opened in a tab'),
            t('An unexpected error occurred: {err}', { err: (e && e.message) || e }),
            noticeActions()
          );
        } catch (e2) {
          log(t('The failure notice could not be shown either: {err}', { err: e2 && e2.message }));
        }
      });
      return;
    }

    // catch を付けないと、reject したときに「起動しています…」（ボタン0個）が
    // 残ったままになり、利用者にできることがゼロになる。
    // ここは onAction 経由と違って、失敗を受け止める相手が他に居ない。
    this.refresh().catch((e) => {
      log(t('Error while first painting the sidebar: {err}', { err: e && e.message }));
      if (this.view !== webviewView) return;
      try {
        webviewView.webview.html = noticeHtml(
          t('Subagent Dashboard cannot be shown'),
          t('An unexpected error occurred: {err}', { err: (e && e.message) || e }),
          noticeActions()
        );
      } catch (e2) {
        log(t('The failure notice could not be shown either: {err}', { err: e2 && e2.message }));
      }
    });
  }

  /**
   * 失敗の紙のボタンが押された。
   *
   * 何が起きても紙を出し直すところまで戻す。押したのに画面が変わらないのが一番困る。
   * @param {string} action
   */
  async onAction(action) {
    log(t('Sidebar button: {action}', { action }));
    if (action === 'reopen') {
      // 「タブで開きました」の紙に置いたボタン。閉じ損ねたサイドバーからの逃げ道なので、
      // ここで refresh() に落としてはいけない（左側に埋め込み直すことになる）。
      // タブ側には出ない紙なので、共通の処理には置かない
      await cmdOpen(this.context);
      return;
    }
    const handled = await runNoticeAction(this.context, action, () => this.refresh());
    if (!handled) log(t('That button was not recognised: {action}', { action }));
  }

  /** アイコンを押したらタブへ移す設定か。既定は移す。 */
  tabMode() {
    return String(cfg().get('sidebarBehavior') || 'openInTab') !== 'embed';
  }

  /**
   * サイドバーに埋め込まず、タブへ移す（設定 sidebarBehavior = openInTab）。
   *
   * **開けたときだけサイドバーを閉じる。** 失敗しているのに閉じると、cmdOpen が出した
   * トーストが消えたあとには何も残らず、「アイコンを押したのに何も起きない」になる。
   * 失敗したときは埋め込み表示に落として、理由と次の一手（設定・配置・ログ）を出す。
   *
   * @param {vscode.WebviewView} webviewView
   */
  async handOffToTab(webviewView) {
    webviewView.webview.html = noticeHtml(t('Opening it in a tab…'));
    const opened = await cmdOpen(this.context);
    if (this.view !== webviewView) return;  // 待っている間に閉じられた

    if (!opened) {
      log(t('It could not be moved to a tab. The sidebar stays open and shows the reason.'));
      await this.refresh();
      return;
    }

    // 閉じる前に置いておく。closeSidebar が効かない環境では、これが唯一の案内になる
    webviewView.webview.html = noticeHtml(
      t('Opened in a tab'),
      t('The icon in the activity bar opens a tab every time you press it. To see it embedded here on the left instead, set agentDashboard.sidebarBehavior to embed.'),
      [
        { id: 'reopen', label: t('Open in a tab again'), primary: true },
        { id: 'settings', label: t('Open the settings') },
      ]
    );

    try {
      await vscode.commands.executeCommand('workbench.action.closeSidebar');
      log(t('It moved to a tab, so the sidebar was closed.'));
    } catch (e) {
      // 閉じられなくても実害はない。タブは既に開いていて、案内も出ている
      log(t('The sidebar could not be closed: {err}', { err: e && e.message }));
    }
  }

  /** サーバーを確保して iframe を出す。失敗しても紙を出して理由を見せる。 */
  async refresh() {
    const view = this.view;
    if (!view) return;
    const r = await ensureServer(this.context, true);
    if (this.view !== view) return;  // 待っている間に閉じられた
    if ('error' in r) {
      log(t('Sidebar: {message}', { message: r.error }));
      // ボタンは理由コードで決める。文面から推測しない
      view.webview.html = noticeHtml(t('Subagent Dashboard cannot be shown'), r.error, noticeActions(r.reason));
      this.port = null;
      return;
    }
    this.port = r.port;
    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [],
      portMapping: [{ webviewPort: r.port, extensionHostPort: r.port }],
    };
    view.webview.html = panelHtml(r.port, currentWorkspacePath());
    log(t('Showed {url} in the sidebar.', { url: urlFor(r.port) }));
  }

  /**
   * サーバーを立て直したときや設定が変わったときに呼ぶ。投げっぱなしにしない。
   *
   * **tabMode でもここでは handOffToTab を使わない。** この道はタイトルバーの $(refresh)
   * （cmdRestart）からも来るので、cmdOpen を通すと更新を押すたびに新しいタブが開く。
   * そもそも tabMode でサイドバーがまだ見えているのは、移すのに失敗したか閉じ損ねたとき
   * だけなので、ここは埋め込みで見せるのが復旧としても正しい。
   */
  reload() {
    if (this.view) {
      this.refresh().catch((e) => log(t('Error while repainting the sidebar: {err}', { err: e && e.message })));
    }
  }

  /**
   * 停止したときに呼ぶ。
   * ここで refresh() を呼んではいけない。サイドバーが開いていると、
   * 止めた直後にサーバーを立て直してしまい「停止できない」状態になる。
   */
  showStopped() {
    this.port = null;
    if (!this.view) return;
    this.view.webview.html = noticeHtml(
      t('The server is stopped'),
      t('To show it again, press "Try again" below. The refresh button above (Restart the server) and the command "Subagent Dashboard: Open in a tab" do the same thing.'),
      [
        { id: 'retry', label: t('Try again'), primary: true },
        { id: 'log', label: t('View log') },
      ]
    );
  }
}

async function openSimpleBrowser(port) {
  try {
    // 存在しないコマンドを呼ぶと例外になるので、先に居るか確かめる
    const all = await vscode.commands.getCommands(true);
    if (!all.includes('simpleBrowser.show')) {
      log(t('The Simple Browser command was not found.'));
      return false;
    }
    await vscode.commands.executeCommand('simpleBrowser.show', urlFor(port));
    log(t('Opened {url} in Simple Browser.', { url: urlFor(port) }));
    return true;
  } catch (e) {
    log(t('Simple Browser was not usable: {err}', { err: e && e.message }));
    return false;
  }
}

async function openExternal(port) {
  const ok = await vscode.env.openExternal(vscode.Uri.parse(urlFor(port)));
  log(t('Opened it in an external browser (succeeded={ok}): {url}', { ok, url: urlFor(port) }));
  return ok;
}

// ---------------------------------------------------------------- コマンド

/**
 * Subagent Dashboard を開く。
 *
 * **戻り値は「開けたか」。** DashboardView.handOffToTab() がこれを見て、
 * サイドバーを閉じてよいかを決める。開けていないのに閉じると、理由を出す場所ごと
 * 消えて「アイコンを押したのに何も起きない」になる。
 *
 * @returns {Promise<boolean>}
 */
async function cmdOpen(context, forceMode) {
  if (busy) { log(t('The startup path is already running. Ignored a duplicate run.')); return false; }
  busy = true;
  try {
    const r = await ensureServer(context, true);
    if ('error' in r) { await fail(r.error); return false; }
    const port = r.port;

    const mode = forceMode || String(cfg().get('openIn') || 'webview');
    if (mode === 'external') return await openExternal(port);
    if (mode === 'simpleBrowser') {
      if (await openSimpleBrowser(port)) return true;
      return await openExternal(port);
    }
    try {
      openWebview(context, port);
      return true;
    } catch (e) {
      log(t('The webview could not be opened: {err}', { err: e && e.message }));
      if (await openSimpleBrowser(port)) return true;
      return await openExternal(port);
    }
  } finally {
    busy = false;
  }
}

/**
 * サーバーを立て直す。
 *
 * **cmdOpen を呼んではいけない。** この道はサイドバーのタイトルバーの $(refresh) からも来る。
 * cmdOpen を通すと、更新を押しただけで新しい Webview タブが開き、設定 openIn が external の
 * 人では OS の既定ブラウザまで立ち上がる。showStopped() の文面がこの更新ボタンを復旧手段として
 * 案内しているので、なおさら踏みやすい。
 *
 * 既に開いているタブがあれば新しいポートに繋ぎ直すだけ。無ければ開かない。
 */
async function cmdRestart(context) {
  const had = stopOwnedServer(t('restart'));
  if (!had) log(t('This extension has no server of its own running. Starting a new one.'));
  // ポートが解放されるまで少し待つ
  await new Promise((r) => setTimeout(r, 600));

  const r = await ensureServer(context, true);
  if ('error' in r) {
    // 黙って終わらせない。押した人には理由が要る
    await fail(r.error);
    if (sidebar) sidebar.reload();   // 紙に理由と次の一手を出す
    return;
  }
  if (panel) {
    try {
      openWebview(context, r.port, { reveal: false });
    } catch (e) {
      log(t('Reconnecting the tab failed (the sidebar is refreshed anyway): {err}', { err: e && e.message }));
    }
  }
  if (sidebar) sidebar.reload();
}

async function cmdStop() {
  if (stopOwnedServer(t('stop command'))) {
    vscode.window.showInformationMessage(t('Subagent Dashboard: The server was stopped.'));
    if (sidebar) sidebar.showStopped();
    return;
  }
  if (activePort !== null) {
    vscode.window.showWarningMessage(
      t('Subagent Dashboard: The server on port {port} was not started by this extension, so it is left alone. Stop it from the terminal that started it.',
        { port: activePort })
    );
    return;
  }
  vscode.window.showInformationMessage(t('Subagent Dashboard: There is no server to stop.'));
}

/**
 * @param {vscode.ExtensionContext} context
 * @param {{ manualSetup?: boolean }} [opts]
 *   manualSetup=true なら、配置のあとの初期設定を manual として走らせる。
 *   利用者が自分で押した道では、globalState の「もう済んでいる」で黙って飛ばさない。
 */
async function cmdDeploy(context, opts) {
  const src = bundleDir(context);
  const bundled = readVersion(src);
  const current = looksLikeHome(DEPLOY_DIR) ? readVersion(DEPLOY_DIR) : null;
  const unknown = t('unknown');
  const what = current
    ? t('{dir}\nwill be updated from version {from} to version {to}.',
      { dir: DEPLOY_DIR, from: current || unknown, to: bundled || unknown })
    : t('Version {version} will be placed in\n{dir}.', { dir: DEPLOY_DIR, version: bundled || unknown });

  const pick = await vscode.window.showInformationMessage(
    t('The Subagent Dashboard tool will be deployed.') + `\n\n${what}\n\n` +
    t('Your records (missions/ and trash/) are not touched.'),
    { modal: true },
    current ? t('Update') : t('Deploy')
  );
  if (!pick) { log(t('The deployment was called off.')); return; }

  const r = deployBundle(context);
  if ('error' in r) { await fail(r.error); return; }
  updateOffered = true;

  // 置く先（DEPLOY_DIR）は固定なのに、ensureHome は設定 agentDashboard.home を最優先する。
  // 設定が本体の無い別の場所を指していると、ここに置いたものは**使われない**。
  // それを黙って「再起動すると反映されます」と言うのは、実現しないことの約束になる。
  // 置くのはやめない（記録の置き場としては正しい場所なので、消してやり直す方が損）。
  // 代わりに、使われないことと直し方を言う。
  const state = currentHome();
  if (state.kind === 'badSetting') {
    log(t('The tool was deployed, but the setting agentDashboard.home points at {home}, so it will not be used.',
      { home: state.home }));
    const openSettings = t('Open the settings');
    const viewLog = t('View log');
    const pick2 = await vscode.window.showWarningMessage(
      t('Subagent Dashboard: The tool was placed in {dir} (version {version}).',
        { dir: DEPLOY_DIR, version: bundled || unknown }) + '\n' +
      t('However, the setting agentDashboard.home points at {home}, and there is no tool there. As things stand, what was just placed will not be used. Clearing that setting makes the place it was put get used automatically.',
        { home: state.home }),
      openSettings, viewLog
    );
    if (pick2 === openSettings) {
      try {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'agentDashboard.home');
      } catch (e) {
        log(t('The settings could not be opened: {err}', { err: e && e.message }));
      }
    } else if (pick2 === viewLog) {
      out.show(true);
    }
    // 初期設定（install.py）は走らせない。使われない配置に合わせて
    // その人の CLAUDE.md まで書き換えると、直すものが増えるだけ。
    // 設定を直したあとは、失敗の紙の「初期設定を実行」やコマンドから走らせられる。
    return;
  }

  vscode.window.showInformationMessage(
    t('Subagent Dashboard: The tool was placed in {dir} (version {version}).',
      { dir: DEPLOY_DIR, version: bundled || unknown }) + ' ' +
    t('Restart the server to apply it.')
  );
  // 更新（既にあったものを上書きした）なら、運用ルールも配り直す必要がある。本体だけ
  // 新しくすると、CLAUDE.md に書いた手順は前の版のまま残る（offerUpdate の説明を参照）。
  // 初回の配置は scheduleSetup のままでよい。まだ一度も設定していない人向けの案内は
  // そちらが持っていて、断る選択肢（今後たずねない）もそちらにしかない。
  if ((opts && opts.manualSetup) || current) await runSetup(context, r.home, { manual: true });
  else scheduleSetup(context, r.home);
}

/** コマンド「初期設定を実行」。初回かどうかに関係なく、確認したうえで走らせる。 */
async function cmdRunSetup(context) {
  const resolved = await ensureHome(context, true);
  if ('error' in resolved) { await fail(resolved.error); return; }
  await runSetup(context, resolved.home, { manual: true });
}

/**
 * コマンド「変更履歴トラッキングの初期設定を実行」。ワークスペース単位のフローを、
 * 自動プロンプトで断られたあと・スキップされたあとでも手動でやり直せる導線。
 *
 * マルチルートで2つ以上フォルダが開いていれば、対象をピッカーで選ばせる
 * （自動判定は最初のフォルダだけを見るが、手動実行はそちらに限らない）。
 */
async function cmdRunChangelogSetup(context) {
  const resolved = await ensureHome(context, true);
  if ('error' in resolved) { await fail(resolved.error); return; }

  const folders = vscode.workspace.workspaceFolders;
  if (!folders || !folders.length) {
    vscode.window.showInformationMessage(t('Subagent Dashboard: No folder is open, so there is nothing to set up.'));
    return;
  }
  let folder = folders[0];
  if (folders.length > 1 && typeof vscode.window.showWorkspaceFolderPick === 'function') {
    const picked = await vscode.window.showWorkspaceFolderPick({
      placeHolder: t('Which folder should changelog tracking be set up for?'),
    });
    if (!picked) return;
    folder = picked;
  }
  await runWorkspaceChangelogSetup(context, resolved.home, { manual: true, folder });
}

// ---------------------------------------------------------------- ステータスバー

function updateStatus() {
  if (!statusItem) return;
  if (!cfg().get('showStatusBar')) { statusItem.hide(); return; }
  const running = activePort !== null;
  statusItem.text = running
    ? `$(hubot) ${t('Subagent Dashboard')} :${activePort}`
    : `$(hubot) ${t('Subagent Dashboard')}`;
  statusItem.tooltip = running
    ? t('Open Subagent Dashboard (running at {url} — {who})', {
      url: urlFor(activePort),
      who: owned ? t('started by this extension') : t('started outside'),
    })
    : t('Open Subagent Dashboard (the server is stopped; opening it starts one automatically)');
  statusItem.show();
}

// ---------------------------------------------------------------- 出入り口

function activate(context) {
  out = vscode.window.createOutputChannel(t('Subagent Dashboard'));
  context.subscriptions.push(out);
  log(t('The extension started.'));

  statusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 0);
  statusItem.command = 'agentDashboard.open';
  context.subscriptions.push(statusItem);
  updateStatus();

  sidebar = new DashboardView(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(VIEW_ID, sidebar, {
      // サイドバーを閉じている間は中身を捨てる。見ていない画面がポーリングし続けないように
      webviewOptions: { retainContextWhenHidden: false },
    })
  );

  // ---- タブの復元
  //
  // ウィンドウを開き直すと（Developer: Reload Window、VSCode の再起動、更新後の再読み込み）、
  // VSCode は前に開いていたタブを自分で作り直し、ここに登録した相手へ渡してくる。
  // **登録していないと、そのタブは「復元できませんでした」と出たまま二度と直らない。**
  // retainContextWhenHidden は「開いている間」の話で、閉じて開き直す道には効かない。
  //
  // 渡ってくる state（webview 側の setState で保存されるもの）は使わない。外枠は
  // script を持たないので常に空で、そもそも前回のポートは当てにならない（restorePanel 参照）。
  if (typeof vscode.window.registerWebviewPanelSerializer === 'function') {
    context.subscriptions.push(
      vscode.window.registerWebviewPanelSerializer(PANEL_TYPE, {
        deserializeWebviewPanel: async (webviewPanel) => {
          if (panel && panel !== webviewPanel) {
            // 既に1枚持っているなら、復元されたほうは畳む。2枚あると同じ画面が2本ぶん
            // ポーリングするうえ、再起動のときにどちらを繋ぎ直すのかも決まらない
            log(t('A tab is already open, so the restored tab is closed.'));
            try {
              webviewPanel.dispose();
            } catch (e) {
              log(t('The restored tab could not be closed: {err}', { err: e && e.message }));
            }
            return;
          }
          log(t('Restoring the tab that was open before.'));
          adoptPanel(context, webviewPanel);
          await restorePanel(context, webviewPanel);
        },
      })
    );
  } else {
    log(t('This VSCode does not support restoring tabs (registerWebviewPanelSerializer is missing).'));
  }

  // ---- マシン変更検知・自動リセット（バックグラウンド実行）
  (async () => {
    try {
      const store = memento(context);
      if (store) {
        const currentMachineKey = await getMachineKey();
        const lastMachineKey = store.get(MACHINE_KEY_STORED);
        if (lastMachineKey && lastMachineKey !== currentMachineKey) {
          log(t('The machine changed ({from} -> {to}). Resetting the first-time setup.',
            { from: lastMachineKey, to: currentMachineKey }));
          await store.update(SETUP_DONE_KEY, false);
          setupPrompted = false;  // リセット時にはもう一度走らせる
        }
        // 初回やマシン変更後は現在のマシンキーを記録
        if (!lastMachineKey || lastMachineKey !== currentMachineKey) {
          await store.update(MACHINE_KEY_STORED, currentMachineKey);
        }
      }
    } catch (e) {
      log(t('Error while detecting the machine (ignored, continuing): {err}', { err: e && e.message }));
    }

    // マシン検知完了後、setupを提案。
    // 場所の判定は currentHome() に任せる（AGENT_DASHBOARD_HOME を見落とすと、
    // 環境変数で本体を指している人には初期設定の案内が一度も出ない）
    const state = currentHome();
    if (state.kind === 'ok') {
      // ワークスペース単位の changelog 初期設定も、同じ「本体がある」条件で持ちかける。
      // changelog_setup.py は本体（home）に同梱される想定なので、本体そのものが無ければ
      // 判定しようがない。
      //
      // **マシン単位の初期設定が片付くまで待ってから持ちかける。** 両方とも modal な
      // 確認ダイアログを出しうる。並べて投げると、良くて初回起動時にモーダルが2枚続けて
      // 出る（どちらの話をされているのか分からない）。VSCode が modal を直列化する前提に
      // 寄りかかった書き方だったが、その前提は確かめていない。await すれば、順番は
      // こちらの都合ではなく事実として決まる。
      await runSetup(context, state.home, { manual: false })
        .catch((e) => log(t('Error while asking about first-time setup (ignored, continuing): {err}', { err: e && e.message })));
      scheduleWorkspaceChangelogSetup(context, state.home);
    }
  })();

  context.subscriptions.push(
    vscode.commands.registerCommand('agentDashboard.open', () => cmdOpen(context)),
    vscode.commands.registerCommand('agentDashboard.openExternal', () => cmdOpen(context, 'external')),
    vscode.commands.registerCommand('agentDashboard.restartServer', () => cmdRestart(context)),
    vscode.commands.registerCommand('agentDashboard.stopServer', () => cmdStop()),
    vscode.commands.registerCommand('agentDashboard.deploy', () => cmdDeploy(context)),
    vscode.commands.registerCommand('agentDashboard.runSetup', () => cmdRunSetup(context)),
    vscode.commands.registerCommand('agentDashboard.runChangelogSetup', () => cmdRunChangelogSetup(context)),
    vscode.commands.registerCommand('agentDashboard.resetOnboarding', async () => {
      const reset = t('Reset');
      const pick = await vscode.window.showInformationMessage(
        t('Subagent Dashboard: The first-time setup flags will be reset.'),
        { modal: true },
        reset
      );
      if (pick === reset) {
        const store = memento(context);
        if (!store) {
          // 黙って終わると「押したのに効いたのか分からない」状態が残る。
          // 記録の置き場が無いことを言えば、少なくとも次に打つ手が決まる
          await fail(
            t('This environment cannot save the first-time setup record, so it cannot be reset (globalState is unavailable). Reload the window, then run it directly from the command "Run initial setup".')
          );
          return;
        }
        await store.update(SETUP_DONE_KEY, false);
        const currentMachineKey = await getMachineKey();
        await store.update(MACHINE_KEY_STORED, currentMachineKey);
        setupPrompted = false;
        // ---- ワークスペース単位（changelog）の記録も一緒に消す。
        // ここで消し忘れると「初期設定をやり直す」と言いながら変更履歴側だけ
        // 前の判断が残り、--reset でも戻せない状態になる。鍵はワークスペースごとに
        // 増えるので、接頭辞で総なめする（keys() が無い版の VSCode では、いま開いて
        // いるフォルダぶんだけでも確実に消す）。
        const cleared = await resetChangelogSetupFlags(store);
        log(t('The first-time setup flags were reset (including {n} changelog records).', { n: cleared }));
        await vscode.window.showInformationMessage(
          t('Subagent Dashboard: Reset complete. Reload the window (Command Palette > Developer: Reload Window) to apply it.')
        );
      }
    }),
    vscode.commands.registerCommand('agentDashboard.showLog', () => out.show(true)),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (!e.affectsConfiguration('agentDashboard')) return;
      if (e.affectsConfiguration('agentDashboard.pythonPath')) pythonCache = null;
      updateStatus();
      // 失敗の紙の「設定を開く」から home を直しても、描き直さなければ古いエラーのまま。
      // 「もう一度試す」を押せば直るが、そこに気づける前提を置かない。
      if (
        e.affectsConfiguration('agentDashboard.home') ||
        e.affectsConfiguration('agentDashboard.port') ||
        e.affectsConfiguration('agentDashboard.pythonPath')
      ) {
        if (sidebar) sidebar.reload();
        // タブが失敗の紙を出しているなら、そちらも描き直す。サイドバーだけ直すと、
        // 設定を直したのにタブは古いエラーのまま残り、直ったことに気づけない。
        // iframe が出ているタブには触らない（見ている画面が理由なく作り直される）
        if (panel && panelNotice) {
          restorePanel(context, panel)
            .catch((e) => log(t('Error while repainting the tab: {err}', { err: e && e.message })));
        }
      }
    })
  );

  // 立ち上がった時点で、外で動いているサーバーがあればステータスバーに反映しておく。
  // 見つからなくても何もしない（勝手にサーバーを立てない・勝手に配置しない）。
  (async () => {
    // 順番は ensureHome() と揃える（currentHome() がその順番を持っている）。設定が指す場所が先。
    // 逆にすると、設定で別の場所を指しているのに配置先を見てしまい、
    // 「自分のサーバーなのに他人のものと判定して繋がらない」ことが起きる。
    // AGENT_DASHBOARD_HOME を見落とすのも同じ事故で、稼働中のサーバーを見つけられないまま
    // 「本体を配置」を勧め、押されると DEPLOY_DIR に二重配置されて記録が分裂する。
    const state = currentHome();
    if (state.kind !== 'ok') return;
    const home = state.home;

    // 本体が既にあるのに初期設定がまだなら、マシン変更検知の後に持ちかけられる（マシン変更検知内で実行）。
    // 未配置のときは何もしない（配置の流れの中で改めて聞く）。

    const start = Number(cfg().get('port')) || 3939;
    for (let port = start; port <= start + PORT_SCAN_MAX; port++) {
      const r = await probe(port);
      if (r.kind === 'ours' && samePath(r.toolRoot, home)) {
        activePort = port;
        log(t('Found a running server: {url}', { url: urlFor(port) }));
        updateStatus();
        return;
      }
      if (r.kind === 'free') return;  // 空きに当たったらそれ以上先は見ない
    }
  })().catch((e) => log(t('Error while scanning at startup (ignored): {err}', { err: e && e.message })));
}

function deactivate() {
  if (cfg().get('stopServerOnExit')) stopOwnedServer(t('VSCode is shutting down'));
  else if (owned) {
    log(t('The server is left running (the setting agentDashboard.stopServerOnExit is false).'));
  }
}

/**
 * 試験（extension/test_extension.js）から中身を突くための窓。**製品コードから使わない。**
 *
 * 出しているのは「画面に何を出すか」を決める判断と、覗き見だけ。状態を書き換える口は置いていない。
 * これを閉じると、項目ごとに「直ったこと」を確かめる術が画面の文面頼みになり、
 * 文章を直した拍子に試験が通らなくなる（あるいは壊れても通ってしまう）。
 */
const __test = {
  currentHome,
  noticeActions,
  vscodeKeybindingsPath,
  setupTargets,
  getOwned: () => owned,
  getPanel: () => panel,
  workspaceFolderHash,
  changelogSetupDoneKey,
  changelogSetupSkipKey,
  changelogSetupTargets,
  panelHtml,
};

module.exports = { activate, deactivate, __test };
