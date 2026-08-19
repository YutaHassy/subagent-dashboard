/* ============================================================================
 * manual-i18n.js — 取扱説明書（manual.html）の本文
 *
 * i18n.js とは別ファイルにしてある。説明書は本文だけで画面の文言表の何倍もあり、
 * ダッシュボードを開いただけの人にはひとことも要らないため（説明書は「？」を
 * 押した**あと**に iframe で読み込まれる）。
 *
 * 差し込み（{PY} {TOOL_ROOT} など）は manual.html が I18N.setVars() で入れる。
 * ここに実際のパスを書かないのは、配布物に特定のPCのパスを含めないため
 * （サーバーが manual.html の {{...}} を実環境の値へ差し替える仕組みに乗せている）。
 *
 * 訳が欠けているキーは英語に落ちる（i18n.js の t() 参照）。
 * ========================================================================== */
'use strict';

(function (global) {

  if (!global.I18N || typeof global.I18N.extend !== 'function') {
    // 単体で開かれた等で i18n.js が無いときは、何もせず黙って諦める。
    // manual.html の markup には英語が入っているので、そのまま英語で読める。
    return;
  }

  const M = {};

  // ============================================================== English（原文）
  M.en = {
    'manual.doctitle': 'Manual — Subagent Dashboard',

    'm.eyebrow':   'Manual',
    'm.h1':        'Subagent Dashboard',
    'm.lead':      'A screen for watching, in real time, how many of Claude Code’s subagents are running, which have finished, and how much time and how many tokens they used. The robots’ faces and motion tell you the state at a glance.',
    'm.open':      '▶ Open the dashboard',
    'm.toc':       'Contents',

    // --- 1
    'm.s1.title':  'What is this for?',
    'm.s1.p1':     'When you ask Claude for a sizeable investigation or piece of work, it starts several <strong>subagents</strong> (AI underlings) behind the scenes and runs them in parallel. In the normal view, though, you can barely see how many are running or which have finished.',
    'm.s1.p2':     'This screen is <strong>Subagent Dashboard</strong>, where you watch that happen.',
    'm.s1.li1':    'Leftmost is <strong>Command</strong> (Claude itself); the further right, the deeper the generation (underlings of underlings)',
    'm.s1.li2':    'Parent and child are joined by a line. A glowing, flowing line means that unit is running',
    'm.s1.li3':    'A finished unit leaves behind its measured values (duration, token count) and a one-line summary of its result',
    'm.s1.li4':    'The event log on the right narrates births and returns as they happen',
    'm.s1.note.b': 'Claude does the updating',
    'm.s1.note.p': 'You never have to type anything. Claude writes to the dashboard the moment it starts a subagent and the moment it receives a completion report. All you do is open the screen and watch.',

    // --- 2
    'm.s2.title':  'Get started in 3 steps',
    'm.s2.step1.h':'Start the server',
    'm.s2.step1.p1':'Run the following in a terminal (Command Prompt / PowerShell / shell). <strong>One server handles the records of every project, but only running teams and the most recent team appear on screen.</strong>',
    'm.s2.step1.p2':'Adding <code>--open</code> opens the browser too. Calling Python directly does the same thing.',
    'm.s2.step1.p3':'A URL is printed once it starts. Leave that window open.',
    'm.s2.step2.h':'Open it in a browser',
    'm.s2.step2.p1':'Open the URL that was printed (usually the one below). Bookmarking it saves time.',
    'm.s2.step2.p2':'If the port was already taken by another app, it shifts to 3940, 3941 and so on automatically — use the URL from the startup log.',
    'm.s2.step3.h':'Ask Claude to do some work',
    'm.s2.step3.p1':'From here just ask Claude for an investigation or a task as you normally would. When a subagent starts, a robot <strong>pops into view</strong> on the spot. The screen refreshes about once a second, so there is no need to reload.',
    'm.s2.note.b': 'When you just want to see it move',
    'm.s2.note.p': 'To check the display without waiting for real work, run the following in the folder of the project you want to look at. It fills in dummy data covering standby, running, awaiting report and done.',
    'm.mask.b':    'The paths below hide your user name',
    'm.mask.p':    'Where a path on this page runs through your home folder, the user-name part is shown as <code>&lt;username&gt;</code>, so a screenshot or a shared screen never carries it. Replace that part with your own user name before you run the command.',

    // --- 3
    'm.s3.title':  'The robots’ faces tell you the state',
    'm.s3.p1':     'There are only four states. Each has a distinct face and motion, so you can tell them apart from across the room. Of these, “awaiting report” is a kind of working state, given to <strong>units that have running underlings</strong>.',
    'm.s3.cap.standby':'Standby',
    'm.s3.sub.standby':'Round eyes, slow blinking.<br>Drifts faintly in time with its breathing',
    'm.s3.cap.running':'Working',
    'm.s3.sub.running':'Blinking briskly, concentrating.<br>Antenna and chest lamp flash',
    'm.s3.cap.waiting':'Awaiting report',
    'm.s3.sub.waiting':'Settles down and waits for its children.<br>The scan line stops and the chest lamp turns amber',
    'm.s3.cap.done':   'Done',
    'm.s3.sub.done':   'Eyes curve into arcs with delight.<br>Its colour changes and the result is shown',
    'm.s3.p2':     'When a new unit appears, it <strong>pops into place</strong> right there (a ring of light spreads out). Even if you miss it, the event log keeps a “… born” line.',

    // --- 4
    'm.s4.title':  'How to read a card',
    'm.s4.demo_name':   'Scout A',
    'm.s4.demo_mission':'List every API call site under src/',
    'm.s4.legend1':'<b>Name and ID</b> — the larger text is the name, the small monospace one is the identifier',
    'm.s4.legend2':'<b>Model name</b> — the model that unit used',
    'm.s4.legend3':'<b>Self-reported badge</b> — given to units that a grandchild (an underling’s underling) registered itself',
    'm.s4.legend4':'<b>Awaiting-report badge</b> — given to units that have running underlings (see the box below)',
    'm.s4.legend5':'<b>Mission</b> — what it was asked to do (up to two lines)',
    'm.s4.legend6':'<b>Elapsed / Tokens / Tools</b> — while running, the elapsed time ticks every second. After completion these are measured values',
    'm.s4.p1':     'On completion a <strong>one-line summary of the result</strong> is added below the card in green, and the whole card fades to grey. Things you no longer need to look at sink visually, so only what is still moving catches your eye.',
    'm.s4.note1.b':'“Awaiting report” is derived, not recorded',
    'm.s4.note1.p1':'A unit holding one or more running underlings gets “awaiting report”: its motion drops to breathing and it turns amber. If Command is in this state, the thing to look at is the children stretching off to the right.',
    'm.s4.note1.p2':'But this is not a fact written in <code>state.json</code> — it is <strong>derived from the parent-child relationships</strong>. “A child is running” is a fact; “the parent is waiting” is an inference, and it diverges from reality when the parent is doing its own work alongside its children. Keep in mind that it is handled differently from measured values such as token counts. There is no command for reporting it (writes still happen at exactly two moments: right after launch, and on the completion report).',
    'm.s4.note2.b':'There is no progress bar',
    'm.s4.note2.p1':'Subagents do not report “I am N% done” while they work. That means the measured percentage simply does not exist anywhere. There used to be a flowing stripe that only meant “this is moving”, but it read as if it showed progress, so it was removed. Whether something is running is clear from the robot’s motion and the card colour. The elapsed time is real.',

    // --- 5
    'm.s5.title':  'Which teams appear on screen',
    'm.s5.p1':     'Two things decide what you see. <strong>What you can pick from</strong> is the tab bar: every project’s mission in progress, and every past mission kept in <code>history/</code>, line up there — one tab per <code>start</code>. <strong>What is drawn</strong> is the tab you have selected; only one team is on screen at a time. When you open the screen a running team is picked for you, and if a new mission starts while you are reading an old record, the screen pulls you back to the live one.',
    'm.s5.th1':    'Situation',
    'm.s5.th2':    'Screen',
    'm.s5.r1a':    'No records at all',
    'm.s5.r1b':    'Standby screen',
    'm.s5.r2a':    'Team A is running',
    'm.s5.r2b':    'A is picked and drawn',
    'm.s5.r3a':    'A ran <code>finish</code>',
    'm.s5.r3b':    'Still shows A (stays in the done state)',
    'm.s5.r4a':    'B then ran <code>start</code>',
    'm.s5.r4b':    'The screen moves to B. A stays in the tab bar and can be brought back',
    'm.s5.r5a':    'A and B are running at the same time',
    'm.s5.r5b':    'Both get a tab; the one you pick is drawn (one at a time)',
    'm.s5.diagram':
      'Standby (no records at all)\n' +
      '   │ start\n' +
      '   ▼\n' +
      'A is running ────────────────► screen: A\n' +
      '   │ finish\n' +
      '   ▼\n' +
      'A is done (.current is still A)─► screen: A (stays visible in the done state)\n' +
      '   │ start in another folder\n' +
      '   ▼\n' +
      'B is running (.current becomes B)► screen: B (A stays in the tab bar)\n' +
      '\n' +
      'Everything running, and every past mission, lines up in the tab bar.\n' +
      'The screen draws the one tab you picked — one at a time. The newest is leftmost.\n' +
      '   ┌──────────┬──────────┬────────────────┐\n' +
      '   │ B (live) │ A (done) │ A (past record)│ ← tab bar\n' +
      '   └──────────┴──────────┴────────────────┘',
    'm.s5.note1.b':'When one of two parallel runs finishes first, its report does not vanish',
    'm.s5.note1.p1':'Say you run A and B in parallel and A <code>finish</code>es first. At that point A is no longer “the most recently <code>start</code>ed team”, so left alone it would stop being sent to the screen the instant it completed. To avoid that, <b>teams that finished after the currently running team began</b> keep being sent as live. Its record would still be reachable from the tab bar either way; this is so that a report you are reading does not go still under you the moment it lands.',
    'm.s5.note1.p2':'If you are simply working in sequence (you <code>start</code> the next team after the previous one ended), the previous team’s completion comes before the new start, so it leaves the screen as the table above says. The two cases are told apart automatically by comparing the finish time against the start time.',
    'm.s5.note2.b':'Which teams are sent live is the server’s decision',
    'm.s5.note2.p1':'The only commands that write the file <code>missions/.current</code> are <code>start</code> and <code>demo</code>. <code>add</code> / <code>done</code> / <code>finish</code> never move it, so a finished screen will not switch itself to some other project. Query strings such as <code>?project=</code> are deliberately ignored: which teams the server streams is its decision, by design. What <em>you</em> choose is which of them — and which past record — to look at, from the tab bar. That choice is remembered in your browser.',
    'm.s5.p2':     'So that an old record left in <code>running</code> is not streamed forever after updates stopped, there is a time window of <strong>3 hours</strong> by default. A <code>running</code> record whose <code>state.json</code> is older than that is treated as abandoned and is no longer sent as a live team (the record itself stays, and stays selectable from the tab bar). The window can be changed with the environment variable <code>AGENT_DASHBOARD_ACTIVE_WINDOW</code> (in seconds).',
    'm.s5.p3':     'Which project you get is <strong>decided automatically by the folder you are working in</strong>. Folders with the same name in different places are told apart by full path, so they never mix (the name used to tell them apart appears only inside the record folder, never on screen).',
    'm.s5.note3.b':'Leaving the screen does not delete the record',
    'm.s5.note3.p1':'The records of a team that is no longer displayed remain in <code>missions/&lt;slug&gt;/</code>. Use the following commands to list, delete, or reset them.',
    'm.s5.th3':    'Command',
    'm.s5.th4':    'What it does',
    'm.s5.c1':     'Lists the remaining records. <code>●</code> marks the team currently on screen',
    'm.s5.c2':     'Deletes a record. By default it only moves it to <code>trash/&lt;slug&gt;-&lt;timestamp&gt;/</code>, so putting the folder back restores it. Add <code>--yes --force</code> to delete it for good',
    'm.s5.c3':     'Returns that project’s record to standby (the folder itself stays)',

    // --- 6
    'm.s6.title':  '“—” is not a malfunction',
    'm.s6.note.b': 'Important',
    'm.s6.note.p': 'Token counts and tool-call counts sometimes show <code>—</code>. That means <strong>the value was not included in the completion report</strong>, and it is the correct display. It is honestly showing that the number could not be obtained.',
    'm.s6.p1':     'The policy here is not to fill in estimates. Once the screen is lined with numbers that mean “probably about 20k tokens”, there is no point looking at it to make a decision. <code>—</code> means “unknown”, not “zero”.',
    'm.s6.p2':     'The token total is likewise the sum of only the units that could be measured. If every unit is unknown, the total is <code>—</code> as well.',

    // --- 7
    'm.s7.title':  'Inside the machinery',
    'm.s7.p1':     'From here on you do not need to read any of this to use the tool. For those who want to know how it works, this explains what the code actually does, in a user’s vocabulary.',
    'm.s7.h1':     'The overall build',
    'm.s7.p2':     'This dashboard uses no external libraries at all. It runs on the Python standard library (<code>http.server</code> and friends) plus plain HTML, CSS and JavaScript. The VSCode extension is likewise built only from <code>vscode</code> and Node.js built-in modules, and has no <code>node_modules</code>. This is the result of prioritising portability and not disturbing your environment.',
    'm.s7.h2':     'How the data flows',
    'm.s7.p3':     'From an update to the display, things flow like this.',
    'm.s7.flow':
      'Claude runs update_state.py add\n' +
      '  └ writes missions/&lt;slug&gt;/state.json (written to .tmp, then swapped in with os.replace)\n' +
      '       ↑ the swap is atomic, so the server reading once a second never sees broken JSON\n' +
      'Server (server.py)\n' +
      '  └ on each GET /api/state, once a second\n' +
      '      ├ looks at missions/.current and each state.json’s phase to decide which teams to show\n' +
      '      └ merges state.json and agents/*.json into one JSON response\n' +
      'Browser (public/index.html)\n' +
      '  └ fetches /api/state once a second\n' +
      '      ├ does nothing if the content is identical to last time (change detection)\n' +
      '      └ if it changed, redraws only the teams that changed',
    'm.s7.h3':     'The state is nothing but files',
    'm.s7.p4':     'There is no database. <code>missions/&lt;slug&gt;/state.json</code> is the single source of truth. The processes do not share state in memory, so shutting the server down loses nothing, and <code>update_state.py</code> can write even when the server is not running.',
    'm.s7.h4':     'Slugs (project identifiers)',
    'm.s7.p5':     'A project identifier (slug) is built as “folder name + the first six digits of the SHA1 of the full path”. Folders with the same name in different places therefore never collide. Windows and macOS treat paths case-insensitively, so the path is lower-cased before the hash is computed.',
    'm.s7.h5':     'How the storage location is chosen',
    'm.s7.p6':     'The place records are stored is decided in this order of priority.',
    'm.s7.li1':    'The environment variable <code>AGENT_DASHBOARD_HOME</code>, if it is set',
    'm.s7.li2':    'Otherwise the folder the tool itself sits in (if it is writable). This also supports carrying it around on a USB stick',
    'm.s7.li3':    'If that is not writable either, the OS’s standard user-data location',
    'm.s7.p7':     'The location actually in use right now is:',
    'm.s7.h6':     'Grandchild agents reporting themselves',
    'm.s7.p8':     'A subagent that cannot go through <code>update_state.py</code> (a grandchild, in effect) can register itself on screen by writing a file at <code>missions/&lt;slug&gt;/agents/&lt;ID&gt;.json</code>. The server merges that content with <code>state.json</code> when it reads, but <strong>if an ID collides, the <code>state.json</code> side wins</strong> (self-reports are strictly supplementary). Running <code>start</code> deletes every self-report file from the previous mission. This keeps a grandchild whose completion report never arrived from sitting on screen as “running” forever.',
    'm.s7.h7':     'The server recomputes the generation (which column) every time',
    'm.s7.p9':     'Which generation (column) a unit lands in on screen is not taken from the stored value — the server re-derives it every time by following <code>parentId</code>. So writing a wrong generation into a self-report file cannot break the display. A unit whose parent cannot be found is treated as sitting directly under Command, and a cycle in the parent-child relationships is detected and stops the traversal.',
    'm.s7.h8':     'How the family tree is laid out',
    'm.s7.p10':    'Units are arranged as a “tidy tree growing sideways”. A parent is placed at the centre of the vertical span its children occupy. Positions are settled from the deepest generation inward, and when things get tight, the unit and its whole subtree are pushed down together. Each unit’s position is given by its vertical coordinate (<code>top</code>) alone; the DOM order is never changed. Reordering elements makes the browser abort and restart every CSS animation beneath them — which would reset the breathing, blinking and expression changes of every robot already on screen each time a new unit appeared.',
    'm.s7.h9':     'The lines joining parent and child',
    'm.s7.p11':    'The lines joining parent and child are drawn as curves between the measured positions of the cards and robots as actually rendered. Because it uses the drawn positions rather than the computed ones, the lines do not drift when the card height changes with text length or wrapping. When many units are running the dashed-line animation is stopped: a repaint would run every frame for each line, so stopping the motion keeps the load down.',
    'm.s7.h10':    'How the screen updates',
    'm.s7.p12':    'The screen updates by fetching the latest state once a second. There is no always-on connection such as a WebSocket (that would add a dependency). A signature is built from the mission, units and log count in what came back, and nothing is redrawn if it matches the previous fetch. Only the elapsed time of running units ticks every second. Even if the server’s clock and the browser’s clock disagree, the server time included in each response corrects for it every time. If a stale response arrives late because of network delay, the stale one is discarded.',
    'm.s7.h11':    'The server',
    'm.s7.p13':    'The server listens on <code>127.0.0.1</code> (inside your own PC only). The default port is 3939; if it is in use, it tries up to 10 higher numbers to find a free one. Only the contents of the <code>public/</code> folder are served, and any other path is refused. Deleting records is accepted over <code>POST</code> only, so it never happens just from opening a URL in a browser (<code>GET</code>) — this is to prevent accidental deletion.',
    'm.s7.h12':    'The VSCode extension',
    'm.s7.p14':    'The VSCode extension merely starts the server and embeds <code>http://127.0.0.1:&lt;port&gt;/</code> inside a webview. The screen is exactly the same as viewing it in a browser directly. The liveness check looks for its own tool location (<code>toolRoot</code>) in the response, so it will never accidentally attach to a server someone else happened to start.',
    'm.s7.h13':    'Only measured values are shown',
    'm.s7.p15':    'Of elapsed time, token count, tool-call count <strong>and the model name</strong>, any value that was not passed in is stored as “unknown” — the first three are displayed as <code>—</code>, the model name as “unknown”. It is never filled in with a plausible estimate. The command post’s own model follows the same rule: leave <code>--model</code> off <code>start</code> and it shows as unknown, rather than falling back to a fixed model ID. This policy is stated in several places in the code (documentation, command help, and runtime output). The purpose of this screen is to see what actually happened, and filling the gaps would destroy that purpose.',
    'm.s7.h14':    'Why the “?” button opens an overlay',
    'm.s7.p16':    'A VSCode webview does not permit the screen embedded inside it to open a new window (its <code>sandbox</code> attribute does not include <code>allow-popups</code>). That restriction propagates to nested frames, so while you are viewing this inside VSCode, trying to open the manual link in a new window is <strong>ignored without even raising an error</strong>. That is why this manual opens as an overlay within the screen rather than in a new window. When you are viewing it directly in a browser, “Open in a new window” is available too.',

    // --- 8
    'm.s8.title':  'Commands you run yourself',
    'm.s8.p1':     'Claude updates things automatically day to day, so in practice these are all you use. In the table <code>{LAUNCHER_PATH}</code> is abbreviated to <code>dash</code>. Writing <code>{PY} {UPDATE_PY}</code> does the same thing.',
    'm.s8.th1':    'Command',
    'm.s8.th2':    'What it does',
    'm.s8.c1':     'Starts the screen’s server and opens the browser. Stop it with <code>Ctrl+C</code> in that window',
    'm.s8.c2':     'Lists the registered projects. <code>→</code> marks the one for the current folder',
    'm.s8.c3':     'Shows the contents of the current project as a table',
    'm.s8.c4':     'Fills in dummy data for checking the display',
    'm.s8.c5':     'Empties the current project (other projects are unaffected)',
    'm.s8.c6':     'First-time setup after moving to another PC (writes the paths into the instructions file of every AI coding CLI on this machine)',
    'm.s8.c7':     'Lists this project’s past missions (the ones kept in <code>history/</code>)',
    'm.s8.note.b': 'Where you run them',
    'm.s8.note.p': 'The target project is decided by <strong>the folder you run the command in</strong>. To act on a different project, add part of its name, as in <code>--project learning</code>.',

    // --- 9
    'm.s9.title':  'When something goes wrong',
    'm.s9.q1':     'The screen is black, or says there are no units yet',
    'm.s9.a1':     'No mission has started for that project yet. Asking Claude for some work will fill it in. To check the display right away, run <code>update_state.py demo</code>.',
    'm.s9.q2':     'The indicator in the top right turned red',
    'm.s9.a2':     'The connection to the server has dropped. Check that the window you started the server in is still open. If it was closed, running <code>python ...\\server.py</code> again brings it back. Note that the last view stays put even when the connection drops, so the screen never goes blank.',
    'm.s9.q3':     'I cannot open 3939',
    'm.s9.a3':     'If another app was using the port, it shifts automatically to 3940, 3941 and so on. The actual URL is printed in the window you started the server in — open that one.',
    'm.s9.q4':     'A yellow warning appeared in the side panel',
    'm.s9.a4':     'It means one of the files a grandchild agent wrote is corrupt. The broken file is ignored and the other units keep displaying. You can leave it alone safely, but if it bothers you, <code>dash reset --purge</code> cleans up that project’s grandchild files.',
    'm.s9.q5':     'I want to delete a project I no longer need',
    'm.s9.a5':     'Running <code>{PY} {UPDATE_PY} remove</code> is the safe way. By default it only moves it to <code>trash/&lt;slug&gt;-&lt;timestamp&gt;/</code>, so putting the folder back recovers from a mistake. To delete by hand, remove the whole folder for that project from the directory below. It then disappears from the list (<code>{PY} {UPDATE_PY} projects</code>).',
    'm.s9.q6':     'How far back are past missions kept?',
    'm.s9.a6':     '<strong>Up to 20 past missions</strong> are kept per project. Running <code>start</code> again does not overwrite the previous one: the whole record moves to <code>missions/&lt;project&gt;/history/&lt;start time&gt;/</code> and can be brought back up from the tab bar. Past the 20th, the oldest move to <code>trash/</code> (moving the folder back recovers it), and the number can be changed with the environment variable <code>AGENT_DASHBOARD_HISTORY_KEEP</code>. The event log keeps the most recent 300 lines.',
    'm.s9.q7':     'The agent is not updating it',
    'm.s9.a7a':    'The operating rules are written into the instructions file of every AI coding CLI installed on this machine (<span class="path">{INSTRUCTION_FILES}</span>), so it usually updates automatically. If it seems to have forgotten, just add “and update the dashboard too”.',
    'm.s9.a7b':    'If those rules are not there (right after copying to another PC, say), run <code>dash install</code> once. The correct paths for that PC get written into every CLI it finds.',
    'm.s9.q8':     'I want to use it on another PC / move where it lives',
    'm.s9.a8a':    'Copy the whole folder, then run <code>dash install</code> once at the destination. Paths are resolved at run time, so it can live anywhere.',
    'm.s9.a8b':    'To change where records are stored, point the environment variable <code>AGENT_DASHBOARD_HOME</code> at a folder (useful for a shared drive or a different disk).',
    'm.s9.q9':     'The unit names are in a different language from the screen',
    'm.s9.a9a':    'Names and mission text are <strong>never translated</strong>. They are free text the agent wrote when it registered the unit, and the screen shows them exactly as recorded — switching the language at the top right changes the headings and labels around them, not the records themselves.',
    'm.s9.a9b':    'Which language the agent writes them in is decided separately, on the command side. Run <code>dash lang en</code> (or <code>ja</code> / <code>zh</code> / <code>ko</code>), then restart your AI coding CLI’s session — that one command also rewrites the operating rules in the new language, so the language you set is the language teams are formed in. Missions already recorded stay as they were written, because this screen is here to show what actually happened.',

    // --- 10
    'm.s10.title': 'Where everything lives',
    'm.s10.p1':    'The tool itself is here.',
    'm.s10.tree':
      '├─ dash.cmd / dash    launcher (everything can be called through it)\n' +
      '├─ dash.py            the launcher itself\n' +
      '├─ server.py          the screen’s server\n' +
      '├─ update_state.py    the command that rewrites the state\n' +
      '├─ install.py         first-time setup (for when you move to another PC)\n' +
      '├─ dashlib.py         internals shared by the above\n' +
      '├─ README.md          installation guide\n' +
      '├─ OPERATION.md       the detailed operating guide, for Claude\n' +
      '├─ public/\n' +
      '│  ├─ index.html      the dashboard screen\n' +
      '│  ├─ i18n.js         the wording table for the screen\n' +
      '│  ├─ manual-i18n.js  the wording table for this manual\n' +
      '│  └─ manual.html     this manual\n' +
      '└─ missions/          the records, per project\n' +
      '   └─ &lt;project name&gt;-&lt;6 digits&gt;/\n' +
      '      ├─ state.json         the current situation\n' +
      '      └─ agents/            grandchild agents’ self-reports',
    'm.s10.p2':    'Records are stored here.',
    'm.s10.p3':    'No further installation is needed. It runs on Python’s standard features alone, using neither external libraries nor an internet connection. The screen is self-contained too. It behaves the same on Windows, macOS and Linux.',
    'm.footer1':   'Subagent Dashboard — Python 3.9+ / no external libraries / Windows, macOS and Linux',
    'm.footer2':   'The detailed operating guide for Claude is in <code>OPERATION.md</code> under <span class="path">{TOOL_ROOT}</span>.',
  };

  // ============================================================== 日本語
  M.ja = {
    'manual.doctitle': '取扱説明書 — Subagent Dashboard',

    'm.eyebrow':   '取扱説明書',
    'm.h1':        'Subagent Dashboard',
    'm.lead':      'Claude Code のサブエージェントが、いま何体動いていて、どれが終わって、どれだけ時間とトークンを使ったのかをリアルタイムで見るための画面です。ロボットの表情と動きで状態が分かります。',
    'm.open':      '▶ ダッシュボードを開く',
    'm.toc':       '目次',

    'm.s1.title':  'これは何をするもの？',
    'm.s1.p1':     'Claude にまとまった調査や作業を頼むと、Claude は裏側で<strong>サブエージェント</strong>（手下のAI）を何体か起動して並列に働かせます。ところが普段の画面では、それが何体動いているのか、どれが終わったのかがほとんど見えません。',
    'm.s1.p2':     'その様子を横から覗くための画面が <strong>Subagent Dashboard</strong> です。',
    'm.s1.li1':    '左端が<strong>指令塔</strong>（Claude 本体）、右へ行くほど深い世代（手下の手下）',
    'm.s1.li2':    '親子は線でつながる。線が光って流れているのは、その機体が稼働中という意味',
    'm.s1.li3':    '終わった機体は実測値（所要時間・トークン数）と結果の一行要約を残す',
    'm.s1.li4':    '右側のイベントログに「誕生」「帰還」が実況として流れる',
    'm.s1.note.b': '更新するのは Claude です',
    'm.s1.note.p': 'あなたが手で入力する必要はありません。Claude がサブエージェントを起動した瞬間と、完了通知を受け取った瞬間に自動で書き込みます。あなたは画面を開いて眺めるだけです。',

    'm.s2.title':  '3ステップで始める',
    'm.s2.step1.h':'サーバーを起動する',
    'm.s2.step1.p1':'ターミナル（コマンドプロンプト / PowerShell / シェル）で次を実行します。<strong>1つのサーバーでどのプロジェクトの記録も扱えますが、画面に映るのは稼働中のチームと直近のチームだけです。</strong>',
    'm.s2.step1.p2':'<code>--open</code> を付けるとブラウザも自動で開きます。Python を直接呼んでも同じです。',
    'm.s2.step1.p3':'起動すると URL が表示されます。この窓は閉じずに開いたままにしておいてください。',
    'm.s2.step2.h':'ブラウザで開く',
    'm.s2.step2.p1':'表示された URL（通常は下記）を開きます。ブックマークしておくと楽です。',
    'm.s2.step2.p2':'ポートが他のアプリに使われていた場合は 3940、3941… と自動でずれるので、起動ログに出た URL を使ってください。',
    'm.s2.step3.h':'Claude に作業を頼む',
    'm.s2.step3.p1':'あとは普段どおり Claude に調査や作業を頼むだけです。サブエージェントが起動されると、その場でロボットが<strong>ポンッと現れます</strong>。約1秒ごとに自動更新されるので、画面を再読み込みする必要はありません。',
    'm.s2.note.b': 'まず動きを見たいとき',
    'm.s2.note.p': '実際の作業を待たずに表示を確かめたい場合は、見たいプロジェクトのフォルダで次を実行してください。待機中・稼働中・報告待ち・完了が揃ったダミーデータが入ります。',
    'm.mask.b':    'パスのユーザー名は伏せています',
    'm.mask.p':    'このページのパスがホームフォルダを通るとき、ユーザー名の部分は <code>&lt;username&gt;</code> と表示されます——画面共有やスクリーンショットに写り込ませないためです。コマンドを実行するときは、その部分をご自身のユーザー名に読み替えてください。',

    'm.s3.title':  'ロボットの表情で状態が分かる',
    'm.s3.p1':     '状態は4つだけです。表情と動きが違うので、遠目でも判別できます。このうち「報告待ち」は作業中の一種で、<strong>稼働中の手下を抱えている機体</strong>に付きます。',
    'm.s3.cap.standby':'待機中',
    'm.s3.sub.standby':'円い目でゆっくり瞬き。<br>呼吸に合わせてほのかに動く',
    'm.s3.cap.running':'作業中',
    'm.s3.sub.running':'活発に瞬きながら集中。<br>アンテナと胸のランプが点滅',
    'm.s3.cap.waiting':'報告待ち',
    'm.s3.sub.waiting':'動きを落として子の報告を待つ。<br>走査線が止まり、胸のランプが琥珀に変わる',
    'm.s3.cap.done':   '完了',
    'm.s3.sub.done':   '目を弧にして喜びを表現。<br>体色が変わり結果を表示',
    'm.s3.p2':     '新しい機体が増えたときは、その場で<strong>ポンッと弾けて現れます</strong>（光の輪が広がります）。見逃してもイベントログに「◯◯ 誕生」と残ります。',

    'm.s4.title':  'カードの読み方',
    'm.s4.demo_name':   '偵察A',
    'm.s4.demo_mission':'src/ 配下のAPI呼び出し箇所を洗い出す',
    'm.s4.legend1':'<b>名前と ID</b> — 大きい方が名前、小さい等幅文字が識別子',
    'm.s4.legend2':'<b>モデル名</b> — その機体が使ったモデル',
    'm.s4.legend3':'<b>自己申告バッジ</b> — 孫（手下の手下）が自分で書き込んだ機体に付く',
    'm.s4.legend4':'<b>報告待ちバッジ</b> — 稼働中の手下を抱えている機体に付く（下の囲みを参照）',
    'm.s4.legend5':'<b>任務内容</b> — 何をさせているか（2行まで）',
    'm.s4.legend6':'<b>経過／トークン／ツール</b> — 稼働中は経過時間が毎秒進む。完了後は実測値',
    'm.s4.p1':     '完了すると、カードの下に<strong>結果の一行要約</strong>が緑文字で追加され、カード全体が灰色に落ちます。「もう見なくていいもの」が視覚的に沈むので、いま動いているものだけが目に入ります。',
    'm.s4.note1.b':'「報告待ち」は導出です',
    'm.s4.note1.p1':'稼働中の手下を1体以上抱えている機体には「報告待ち」が付き、動きが呼吸に落ちて琥珀色になります。指令塔がここに入っていたら、見るべきは右へ伸びた子の方です。',
    'm.s4.note1.p2':'ただしこれは <code>state.json</code> に書かれている事実ではなく、<strong>親子関係からの導出</strong>です。「子が動いている」は事実ですが「親が待っている」は推測で、親が子と並行して自分の作業を進めているときは実態とズレます。トークン数のような実測値とは扱いが違う、と覚えておいてください。報告するためのコマンドはありません（書き込みは今も「起動直後」と「完了通知時」の2点だけです）。',
    'm.s4.note2.b':'進捗バーはありません',
    'm.s4.note2.p1':'サブエージェントは作業中に「いま何％」を報告してきません。つまり％の実測値はどこにも存在しません。以前は「動いている」ことだけを示す流れるストライプを置いていましたが、進み具合を表しているように読めてしまうので外しました。稼働中かどうかはロボの動きとカードの色で分かります。経過時間は本物です。',

    'm.s5.title':  'どのチームが画面に映るか',
    'm.s5.p1':     '画面に映るものは2つの要素で決まります。<strong>選べる範囲</strong>はタブ列です。稼働中の各プロジェクトのミッションと、<code>history/</code> に残っている過去のミッションが、<code>start</code> 1回につき1枚のタブとしてそこに並びます。<strong>実際に表示される</strong>のは選んだ1枚だけで、同時に画面に出るチームは常に1つです。画面を開くと稼働中のチームが自動で選ばれ、古い記録を読んでいる間に新しいミッションが始まると、画面はその稼働中のチームへ引き戻されます。',
    'm.s5.th1':    '状況',
    'm.s5.th2':    '画面',
    'm.s5.r1a':    '記録が一つも無い',
    'm.s5.r1b':    '待機画面',
    'm.s5.r2a':    'チームAが稼働中',
    'm.s5.r2b':    'Aが選ばれて表示される',
    'm.s5.r3a':    'Aが <code>finish</code> した',
    'm.s5.r3b':    'Aのまま表示（完了状態で残る）',
    'm.s5.r4a':    '次にBが <code>start</code> した',
    'm.s5.r4b':    '画面はBに移る。Aはタブ列に残り、呼び戻せる',
    'm.s5.r5a':    'AとBが同時に稼働中',
    'm.s5.r5b':    '両方にタブが付く。選んだ方だけが表示される（一度に1つ）',
    'm.s5.diagram':
      '待機（記録が一つも無い）\n' +
      '   │ start\n' +
      '   ▼\n' +
      'Aが稼働中 ────────────────► 画面: A\n' +
      '   │ finish\n' +
      '   ▼\n' +
      'Aが完了（.current は A のまま）─► 画面: A（完了状態のまま表示され続ける）\n' +
      '   │ 別フォルダで start\n' +
      '   ▼\n' +
      'Bが稼働中（.current が B に変わる）► 画面: B（Aはタブ列に残る）\n' +
      '\n' +
      '稼働中のものすべてと、過去のミッションすべてが、タブ列に並びます。\n' +
      '画面は選んだ1枚のタブだけを表示します——一度に1つ。新しい方が左に来ます。\n' +
      '   ┌─────────────┬───────────┬─────────────────┐\n' +
      '   │ B（稼働中） │ A（完了） │ A（過去の記録） │ ← タブ列\n' +
      '   └─────────────┴───────────┴─────────────────┘',
    'm.s5.note1.b':'並列で走らせた片方が先に終わっても、完了報告は消えません',
    'm.s5.note1.p1':'AとBを並列で走らせていて、Aが先に <code>finish</code> したとします。この時点でAはもう「直近に <code>start</code> されたチーム」ではないため、そのままにしておくと完了した瞬間に画面へ送られなくなってしまいます。それを避けるため、<b>いま動いているチームが始まったあとに完了したチーム</b>は、引き続き稼働中として送られ続けます。Aの記録はどちらにしてもタブ列から見られますが、これは読んでいる最中の報告が、届いたその瞬間に止まってしまわないようにするためです。',
    'm.s5.note1.p2':'順番に作業しているだけの場合（前のチームが終わってから次を <code>start</code> した場合）は、前のチームの完了が次の開始より前になるので、上の表のとおり画面から降ります。この2つは完了した時刻と開始した時刻の前後で自動的に区別されます。',
    'm.s5.note2.b':'どのチームを映すかはサーバー側の判断です',
    'm.s5.note2.p1':'<code>missions/.current</code> というファイルを書き換えるのは <code>start</code> と <code>demo</code> だけです。<code>add</code> / <code>done</code> / <code>finish</code> はこのファイルを動かさないので、完了した画面が勝手に別のプロジェクトへ切り替わることはありません。URL に <code>?project=</code> のような指定を付けても意図的に受け付けません——どのチームをサーバーが送るかは、設計としてサーバー側が決めることだからです。<em>あなた</em>が選べるのは、その中のどれを——そしてどの過去の記録を——タブ列から見るか、という点です。その選択はブラウザに記憶されます。',
    'm.s5.p2':     '<code>running</code>（稼働中）のまま更新が止まった古い記録を延々と映し続けないように、既定<strong>3時間</strong>の時間窓があります。<code>state.json</code> の更新がそれより古い <code>running</code> は「放置された」とみなされ、稼働中のチームとしては送られなくなります（記録自体は残り、タブ列から引き続き選べます）。この時間窓は環境変数 <code>AGENT_DASHBOARD_ACTIVE_WINDOW</code>（秒単位）で変更できます。',
    'm.s5.p3':     'どのプロジェクトになるかは<strong>作業しているフォルダで自動的に決まります</strong>。同じ名前のフォルダが別の場所にあっても、フルパスで区別されるので混ざりません（区別に使われる名前は記録フォルダの中だけに現れ、画面には出ません）。',
    'm.s5.note3.b':'画面から消えても記録は消えていません',
    'm.s5.note3.p1':'表示されなくなったチームの記録は <code>missions/&lt;スラッグ&gt;/</code> にそのまま残っています。一覧・削除・初期化には次のコマンドを使います。',
    'm.s5.th3':    'コマンド',
    'm.s5.th4':    '何をするか',
    'm.s5.c1':     '残っている記録の一覧。<code>●</code> がいま画面に映っているチーム',
    'm.s5.c2':     '記録を消す。既定では <code>trash/&lt;スラッグ&gt;-&lt;日時&gt;/</code> へ移すだけなので、フォルダを戻せば復旧できます。完全に消すには <code>--yes --force</code> を付けます',
    'm.s5.c3':     'そのプロジェクトの記録を待機中に戻します（フォルダ自体は残ります）',

    'm.s6.title':  '「—」は故障ではありません',
    'm.s6.note.b': '重要',
    'm.s6.note.p': 'トークン数やツール使用回数に <code>—</code> と出ることがあります。これは<strong>その値が完了通知に含まれていなかった</strong>という意味で、正常な表示です。数字が取れなかったことを正直に表示しています。',
    'm.s6.p1':     'ここに推定値を入れない方針にしています。「だいたい2万トークンくらいだろう」という数字が並んでしまうと、この画面を見て判断する意味がなくなるからです。<code>—</code> は「不明」であって「ゼロ」ではありません。',
    'm.s6.p2':     '合計トークンも、実測できた機体だけを足した値です。全機が不明なら合計も <code>—</code> になります。',

    'm.s7.title':  '仕組みの内側',
    'm.s7.p1':     'ここから先は、使うだけなら読む必要のない話です。仕組みを詳しく知りたい人のために、実際のコードの動きを利用者向けの言葉で説明します。',
    'm.s7.h1':     '全体の作り',
    'm.s7.p2':     'このダッシュボードは外部ライブラリを一切使っていません。Python 標準ライブラリ（<code>http.server</code> など）と、素の HTML・CSS・JavaScript だけで動いています。VSCode 拡張機能の側も <code>vscode</code> と Node.js の組み込みモジュールだけで作られていて、<code>node_modules</code> を持ちません。持ち運びやすさと、環境を壊さないことを優先した結果です。',
    'm.s7.h2':     'データの流れ',
    'm.s7.p3':     '更新から画面表示までは、次のように流れます。',
    'm.s7.flow':
      'Claude が update_state.py add を実行\n' +
      '  └ missions/&lt;スラッグ&gt;/state.json を書く（.tmp に書いてから os.replace で差し替え）\n' +
      '       ↑ 原子的に差し替えるので、1秒ごとに読んでいるサーバーが壊れた JSON を見ることがない\n' +
      'サーバー（server.py）\n' +
      '  └ 1秒ごとの GET /api/state を受けて\n' +
      '      ├ missions/.current と各 state.json の phase を見て「映すチーム」を決める\n' +
      '      └ state.json ＋ agents/*.json を混ぜて JSON を組み立てる\n' +
      'ブラウザ（public/index.html）\n' +
      '  └ 1秒ごとに /api/state を取得\n' +
      '      ├ 前回と内容が同じなら何もしない（差分検知）\n' +
      '      └ 変わっていたら、そのチームだけ描き直す',
    'm.s7.h3':     '状態はファイルだけ',
    'm.s7.p4':     'データベースは使っていません。<code>missions/&lt;スラッグ&gt;/state.json</code> が唯一の正本です。プロセス同士がメモリ上で状態を共有しているわけではないので、サーバーを落としても記録は失われませんし、<code>update_state.py</code> はサーバーが動いていなくても書き込めます。',
    'm.s7.h4':     'スラッグ（プロジェクトの識別子）',
    'm.s7.p5':     'プロジェクトの識別子（スラッグ）は「フォルダ名 ＋ フルパスの SHA1 の先頭6桁」という形で作られます。同じ名前のフォルダが別の場所にあっても衝突しません。Windows と macOS はパスの大文字小文字を区別しないので、ハッシュを計算する前にパスを小文字に揃えています。',
    'm.s7.h5':     '保存先の決まり方',
    'm.s7.p6':     '記録の保存先は、次の優先順で決まります。',
    'm.s7.li1':    '環境変数 <code>AGENT_DASHBOARD_HOME</code> が指定されていれば、そこ',
    'm.s7.li2':    '指定が無ければ、ツール自身が置かれているフォルダ（書き込めれば）。USBメモリなどに入れて持ち運ぶ運用もできます',
    'm.s7.li3':    'そこにも書き込めなければ、OS標準のユーザーデータ置き場',
    'm.s7.p7':     'いまの実際の保存先は次のとおりです。',
    'm.s7.h6':     '孫エージェントの自己申告',
    'm.s7.p8':     '<code>update_state.py</code> を経由できないサブエージェント（孫にあたる存在）は、<code>missions/&lt;スラッグ&gt;/agents/&lt;ID&gt;.json</code> というファイルに自分で書き込んで、画面に登録することもできます。サーバーは読み込み時にこの内容を <code>state.json</code> と混ぜますが、<strong>ID が重複した場合は <code>state.json</code> 側が勝ちます</strong>（自己申告はあくまで補助的な扱いです）。<code>start</code> を実行すると、前のミッションの自己申告ファイルはすべて削除されます。完了通知が来なかった孫が、いつまでも「稼働中」のまま画面に残り続けるのを防ぐためです。',
    'm.s7.h7':     '世代（何列目か）はサーバーが毎回計算し直す',
    'm.s7.p9':     '機体が画面上で何世代目（何列目）に来るかは、保存された値をそのまま使うのではなく、<code>parentId</code>（親のID）をたどってサーバーが毎回実測し直します。そのため、自己申告ファイルに世代の値を誤って書いても画面が壊れることはありません。親が見つからない機体は指令塔の直下として扱われ、親子関係が循環してしまっている場合も検出して処理を止めます。',
    'm.s7.h8':     '系統樹の並べ方',
    'm.s7.p10':    '機体は「横に伸びる整形木」という形で配置されます。親は、自分が生んだ子たちが占める縦の範囲の中央に来るように置かれます。深い世代から順に位置を確定していき、間隔が詰まってきたら、その機体と配下の部分木をまとめて下にずらします。それぞれの機体の位置は上下の座標（<code>top</code>）だけで指定していて、画面上の並び順そのものは変更しません。要素の並び順を変えると、ブラウザはその要素以下のCSSアニメーションを中断していちから作り直してしまうためです。機体が増えるたびに、すでに表示されている全ロボットの呼吸・瞬き・表情の変化がリセットされてしまうのを避けています。',
    'm.s7.h9':     '親子をつなぐ線',
    'm.s7.p11':    '親子をつなぐ線は、実際に描画されたカードとロボットの位置を測定して、そのつなぎ目に曲線を引いています。計算上の位置ではなく実際に描かれた位置を使っているので、文字数や折り返しでカードの高さが変わっても線がずれません。稼働中の機体が多いときは、線の破線アニメーションを止めます。機体の数だけ毎フレーム再描画が発生するため、動きを止めて負荷を抑えています。',
    'm.s7.h10':    '画面の更新',
    'm.s7.p12':    '画面は1秒ごとに最新の状態を取りに行く方式で更新されます。WebSocket のような常時接続の仕組みは使っていません（依存を増やさないためです）。取得した内容からミッション・機体・ログ件数の特徴を作り、前回取得時と変わっていなければ描き直しません。稼働中の機体の経過時間だけは毎秒進みます。サーバーの時刻とブラウザの時刻がずれていても、応答に含まれるサーバー側の時刻で毎回補正されます。通信の遅れなどで古い応答が後から届いた場合は、その古い方は捨てられます。',
    'm.s7.h11':    'サーバー',
    'm.s7.p13':    'サーバーは <code>127.0.0.1</code>（自分のPCの中だけ）で待ち受けます。既定のポートは 3939 で、使用中の場合は 10 回まで番号を繰り上げて空いているポートを探します。配信されるのは <code>public/</code> フォルダの中身だけで、それ以外のパスを指定すると拒否されます。記録を消す操作は <code>POST</code> でのみ受け付けられ、ブラウザで直接開く（<code>GET</code>）だけでは実行されません。うっかり消してしまうことを防ぐためです。',
    'm.s7.h12':    'VSCode 拡張機能',
    'm.s7.p14':    'VSCode 拡張機能は、サーバーを起動して <code>http://127.0.0.1:&lt;ポート&gt;/</code> を webview の中に埋め込んで表示しているだけです。画面の中身はブラウザで直接見るときとまったく同じです。生存確認は、応答の中に自分自身のツールの場所（<code>toolRoot</code>）が含まれているかで判定しているので、たまたま他の人が別に立てたサーバーに繋いでしまうことはありません。',
    'm.s7.h13':    '実測値しか出さない',
    'm.s7.p15':    '経過時間・トークン数・ツール使用回数、そして<strong>モデル名</strong>のうち、渡されなかった値は「不明」として保存されます——最初の3つは画面に <code>—</code> と表示され、モデル名は「不明」と表示されます。それらしい推定値で埋めることは一切ありません。司令塔自身のモデルも同じ扱いです。<code>start</code> の <code>--model</code> を省略すると、決まったモデルIDにフォールバックするのではなく、不明として表示されます。この方針はコードの複数箇所(説明文・コマンドのヘルプ・実行時の表示)に明記されています。この画面の目的は「実際に何が起きたか」を見ることなので、埋めてしまうとその目的が壊れてしまうからです。',
    'm.s7.h14':    '「？」ボタンがオーバーレイで開く理由',
    'm.s7.p16':    'VSCode の webview は、中に埋め込んだ画面が新しいウィンドウを開くことを許可していません（<code>sandbox</code> 属性に <code>allow-popups</code> が含まれないためです）。この制約は入れ子になった画面にも及ぶので、VSCode に埋め込んで見ているときは、説明書へのリンクを新しいウィンドウで開こうとしても<strong>エラーも出ないまま無視されてしまいます</strong>。そのため、この説明書は新しいウィンドウではなく画面の中のオーバーレイとして開くようにしています。ブラウザで直接見ているときは「別ウィンドウで開く」も選べます。',

    'm.s8.title':  '自分で使うコマンド',
    'm.s8.p1':     '普段は Claude が自動で更新するので、あなたが使うのは実質これだけです。表では <code>{LAUNCHER_PATH}</code> を <code>dash</code> と省略しています。<code>{PY} {UPDATE_PY}</code> と書いても同じ動作です。',
    'm.s8.th1':    'コマンド',
    'm.s8.th2':    '何をするか',
    'm.s8.c1':     '画面のサーバーを起動してブラウザを開く。止めるときはその窓で <code>Ctrl+C</code>',
    'm.s8.c2':     '登録されているプロジェクトを一覧表示する。<code>→</code> が現在のフォルダの対象',
    'm.s8.c3':     'いまのプロジェクトの中身を表で確認する',
    'm.s8.c4':     '表示確認用のダミーデータを入れる',
    'm.s8.c5':     'いまのプロジェクトを空にする（他のプロジェクトには影響しない）',
    'm.s8.c6':     '別のPCに移したときの初期設定（このマシンにある各AIコーディングCLIの指示ファイルにパスを書き込みます）',
    'm.s8.c7':     'このプロジェクトの過去のミッションを一覧表示します（<code>history/</code> に残っているもの）',
    'm.s8.note.b': '実行する場所',
    'm.s8.note.p': '対象プロジェクトは<strong>コマンドを実行したフォルダ</strong>で決まります。別のプロジェクトを操作したいときは <code>--project learning</code> のように名前の一部を付けてください。',

    'm.s9.title':  '困ったとき',
    'm.s9.q1':     '画面が真っ暗、または「まだ機体がいません」と出る',
    'm.s9.a1':     'そのプロジェクトでまだミッションが始まっていない状態です。Claude に作業を頼めば埋まります。すぐ表示を確認したいなら <code>update_state.py demo</code> を実行してください。',
    'm.s9.q2':     '右上のインジケータが赤くなった',
    'm.s9.a2':     'サーバーとの通信が切れています。サーバーを起動した窓が閉じていないか確認してください。閉じていた場合は <code>python ...\\server.py</code> をもう一度実行すれば復帰します。なお通信が切れても直前の表示は残るので、画面が消えてしまうことはありません。',
    'm.s9.q3':     '3939 で開けない',
    'm.s9.a3':     '他のアプリがポートを使っていた場合、自動で 3940、3941… にずれます。サーバーを起動した窓に実際の URL が出ているので、そちらを開いてください。',
    'm.s9.q4':     'サイドパネルに黄色い警告が出た',
    'm.s9.a4':     '孫エージェントが書き込んだファイルのどれかが壊れている、という意味です。壊れたファイルは無視され、他の機体の表示は続きます。放置しても問題ありませんが、気になる場合は <code>dash reset --purge</code> でそのプロジェクトの孫ファイルを掃除できます。',
    'm.s9.q5':     '要らなくなったプロジェクトを消したい',
    'm.s9.a5':     '<code>{PY} {UPDATE_PY} remove</code> を実行するのが安全です。既定では <code>trash/&lt;スラッグ&gt;-&lt;日時&gt;/</code> へ移すだけなので、間違えてもフォルダを戻せば復旧できます。手作業で消したい場合は、下記フォルダの中から該当するプロジェクトのフォルダを丸ごと削除してください。一覧（<code>{PY} {UPDATE_PY} projects</code>）から消えます。',
    'm.s9.q6':     '過去のミッションはどこまで残る？',
    'm.s9.a6':     '<strong>過去のミッションは最大20件</strong>がプロジェクトごとに保持されます。もう一度 <code>start</code> しても前回分は上書きされません——記録一式が <code>missions/&lt;project&gt;/history/&lt;start time&gt;/</code> に移動し、タブ列から呼び戻せます。20件を超えると、最も古いものから <code>trash/</code> に移動します（フォルダを戻せば復元できます）。この件数は環境変数 <code>AGENT_DASHBOARD_HISTORY_KEEP</code> で変更できます。イベントログは直近300行まで保持されます。',
    'm.s9.q7':     'エージェントが更新してくれない',
    'm.s9.a7a':    '運用ルールは、このマシンにインストールされている各AIコーディングCLIの指示ファイル(<span class="path">{INSTRUCTION_FILES}</span>)に書き込まれているので、通常は自動で更新されます。忘れているようなら「ダッシュボードも更新して」と一言添えてください。',
    'm.s9.a7b':    'その設定が入っていない場合(別のPCにコピーした直後など)は、一度だけ <code>dash install</code> を実行してください。そのPCで見つかった各CLIに、正しいパスが書き込まれます。',
    'm.s9.q8':     '別のPCで使いたい / 場所を移したい',
    'm.s9.a8a':    'フォルダを丸ごとコピーして、コピー先で <code>dash install</code> を1回実行してください。パスは実行時に自動で解決されるので、置き場所はどこでも構いません。',
    'm.s9.a8b':    '記録の保存先を変えたい場合は、環境変数 <code>AGENT_DASHBOARD_HOME</code> にフォルダを指定してください（共有ドライブや別ドライブに置きたいときに使います）。',
    'm.s9.q9':     '名前や任務内容だけ、画面と違う言語で出ている',
    'm.s9.a9a':    '名前と任務内容は<strong>翻訳されません</strong>。これらはエージェントが部隊を登録したときに書いた自由記述で、画面は記録されたとおりに出します——右上で言語を切り替えると、その周りの見出しやラベルは変わりますが、記録そのものは変わりません。',
    'm.s9.a9b':    'エージェントが何語で書くかは、コマンド側で別に決まっています。<code>dash lang ja</code>(または <code>en</code> / <code>zh</code> / <code>ko</code>)を実行して、使っているAIコーディングCLIのセッションを再起動してください——このコマンドが運用ルールも新しい言語に書き直すので、設定した言語がそのままチームを組む言語になります。すでに記録されたミッションは書かれたときのままです。この画面は「実際に起きたこと」を映すためのものだからです。',

    'm.s10.title': 'どこに何があるか',
    'm.s10.p1':    'このツールは次の場所にあります。',
    'm.s10.tree':
      '├─ dash.cmd / dash    ランチャ（これ経由で全部呼べる）\n' +
      '├─ dash.py            ランチャの本体\n' +
      '├─ server.py          画面のサーバー\n' +
      '├─ update_state.py    状態を書き換えるコマンド\n' +
      '├─ install.py         初期設定（別PCに移したとき用）\n' +
      '├─ dashlib.py         上記が共有する内部処理\n' +
      '├─ README.md          導入手順\n' +
      '├─ OPERATION.md       Claude 用の詳しい運用手順\n' +
      '├─ public/\n' +
      '│  ├─ index.html      ダッシュボード画面\n' +
      '│  ├─ i18n.js         画面の文言表\n' +
      '│  ├─ manual-i18n.js  この説明書の文言表\n' +
      '│  └─ manual.html     この説明書\n' +
      '└─ missions/          プロジェクトごとの記録\n' +
      '   └─ &lt;プロジェクト名&gt;-&lt;6桁&gt;/\n' +
      '      ├─ state.json         いまの状況\n' +
      '      └─ agents/            孫エージェントの自己申告',
    'm.s10.p2':    '記録の保存先は次の場所です。',
    'm.s10.p3':    '追加のインストールは不要です。Python の標準機能だけで動いていて、外部ライブラリもインターネット接続も使いません。画面も1枚の HTML で完結しています。Windows / macOS / Linux のどれでも同じように動きます。',
    'm.footer1':   'Subagent Dashboard — Python 3.9 以降 / 外部ライブラリなし / Windows・macOS・Linux 対応',
    'm.footer2':   'Claude 向けの詳細な運用手順は <span class="path">{TOOL_ROOT}</span> の <code>OPERATION.md</code> にあります。',
  };

  // ============================================================== 中文（简体）
  M.zh = {
    'manual.doctitle': '使用手册 — Subagent Dashboard',

    'm.eyebrow':   '使用手册',
    'm.h1':        'Subagent Dashboard',
    'm.lead':      '用于实时查看 Claude Code 的子代理当前有几个在运行、哪些已经结束、各自花了多少时间和多少 Token 的画面。通过机器人的表情和动作即可看出状态。',
    'm.open':      '▶ 打开面板',
    'm.toc':       '目录',

    'm.s1.title':  '这是做什么用的？',
    'm.s1.p1':     '当你请 Claude 做一项成规模的调查或工作时，它会在背后启动若干<strong>子代理</strong>（下属 AI）并让它们并行工作。但在平常的界面里，几乎看不到有几个在运行、哪些已经结束。',
    'm.s1.p2':     '这个画面就是从旁观察这一切的 <strong>Subagent Dashboard</strong>。',
    'm.s1.li1':    '最左边是<strong>指挥塔</strong>（Claude 本体），越往右代数越深（下属的下属）',
    'm.s1.li2':    '父子之间用线相连。线发光流动，表示该单元正在运行',
    'm.s1.li3':    '结束的单元会留下实测值（耗时、Token 数）和结果的一行摘要',
    'm.s1.li4':    '右侧的事件日志会实时播报「诞生」和「归队」',
    'm.s1.note.b': '负责更新的是 Claude',
    'm.s1.note.p': '你不需要手动输入任何内容。Claude 会在启动子代理的那一刻，以及收到完成回报的那一刻自动写入。你只要打开画面看着就好。',

    'm.s2.title':  '三步开始使用',
    'm.s2.step1.h':'启动服务器',
    'm.s2.step1.p1':'在终端（命令提示符 / PowerShell / Shell）中执行以下命令。<strong>一个服务器可以处理所有项目的记录，但画面上只会显示运行中的小队和最近的小队。</strong>',
    'm.s2.step1.p2':'加上 <code>--open</code> 会同时自动打开浏览器。直接调用 Python 效果相同。',
    'm.s2.step1.p3':'启动后会显示 URL。请不要关闭这个窗口。',
    'm.s2.step2.h':'在浏览器中打开',
    'm.s2.step2.p1':'打开显示出来的 URL（通常是下面这个）。加入书签会方便许多。',
    'm.s2.step2.p2':'如果端口已被其他应用占用，会自动顺延为 3940、3941…… 请使用启动日志中出现的 URL。',
    'm.s2.step3.h':'请 Claude 开始工作',
    'm.s2.step3.p1':'接下来照常请 Claude 做调查或工作即可。子代理一被启动，机器人就会当场<strong>「啵」地出现</strong>。画面约每秒自动刷新一次，无需重新加载。',
    'm.s2.note.b': '只想先看看效果时',
    'm.s2.note.p': '若不想等待实际工作就确认显示效果，请在想查看的项目文件夹中执行以下命令。它会写入包含待机中、运行中、等待回报、已完成的示例数据。',
    'm.mask.b':    '下面的路径隐去了你的用户名',
    'm.mask.p':    '本页面路径经过主文件夹时，用户名部分会显示为 <code>&lt;username&gt;</code>，这样截图或共享屏幕时都不会带出它。运行命令前，请把那部分换成你自己的用户名。',

    'm.s3.title':  '从机器人的表情看出状态',
    'm.s3.p1':     '状态只有四种。表情和动作各不相同，远远就能分辨。其中「等待回报」是工作中的一种，会出现在<strong>拥有运行中下属的单元</strong>上。',
    'm.s3.cap.standby':'待机中',
    'm.s3.sub.standby':'圆圆的眼睛缓慢眨动。<br>随呼吸轻微晃动',
    'm.s3.cap.running':'工作中',
    'm.s3.sub.running':'活泼地眨眼，全神贯注。<br>天线和胸口的灯闪烁',
    'm.s3.cap.waiting':'等待回报',
    'm.s3.sub.waiting':'放慢动作等待子单元回报。<br>扫描线停止，胸口的灯转为琥珀色',
    'm.s3.cap.done':   '已完成',
    'm.s3.sub.done':   '眼睛弯成弧形表达喜悦。<br>体色改变并显示结果',
    'm.s3.p2':     '有新单元加入时，会当场<strong>「啵」地弹出现身</strong>（光环向外扩散）。即使错过了，事件日志中也会留下「◯◯ 诞生」的记录。',

    'm.s4.title':  '如何读懂卡片',
    'm.s4.demo_name':   '侦察A',
    'm.s4.demo_mission':'梳理 src/ 目录下所有 API 调用位置',
    'm.s4.legend1':'<b>名称与 ID</b> — 大的是名称，小的等宽字体是标识符',
    'm.s4.legend2':'<b>模型名</b> — 该单元使用的模型',
    'm.s4.legend3':'<b>自行申报徽章</b> — 出现在由孙代理（下属的下属）自行写入的单元上',
    'm.s4.legend4':'<b>等待回报徽章</b> — 出现在拥有运行中下属的单元上（参见下方方框）',
    'm.s4.legend5':'<b>任务内容</b> — 让它做什么（最多两行）',
    'm.s4.legend6':'<b>已用时／Token／工具</b> — 运行中已用时每秒递增。完成后为实测值',
    'm.s4.p1':     '完成后，卡片下方会以绿色文字追加<strong>结果的一行摘要</strong>，整张卡片会变成灰色。「已经不必再看的东西」在视觉上沉下去，于是只有还在运行的内容映入眼帘。',
    'm.s4.note1.b':'「等待回报」是推导出来的',
    'm.s4.note1.p1':'拥有一个以上运行中下属的单元会被标上「等待回报」，动作放缓为呼吸并转为琥珀色。如果指挥塔处于这个状态，该看的是向右延伸出去的子单元。',
    'm.s4.note1.p2':'但这并不是写在 <code>state.json</code> 里的事实，而是<strong>从父子关系推导出来的</strong>。「子在运行」是事实，「父在等待」则是推测，当父单元与子单元并行推进自己的工作时就会与实情不符。请记住它与 Token 数这类实测值的性质不同。没有用于回报它的命令（写入至今仍只有「启动直后」和「收到完成回报时」两个时点）。',
    'm.s4.note2.b':'没有进度条',
    'm.s4.note2.p1':'子代理在工作过程中不会回报「现在完成了百分之几」。也就是说，百分比的实测值根本不存在于任何地方。以前曾放过一条只表示「正在动」的流动条纹，但它容易被读成在表示进度，因此移除了。是否在运行，从机器人的动作和卡片颜色就能看出。已用时是真实的。',

    'm.s5.title':  '哪些小队会显示在画面上',
    'm.s5.p1':     '画面呈现的内容由两点决定。<strong>可供选择的范围</strong>是标签栏：各个项目正在进行的任务，以及保存在 <code>history/</code> 中的每一个过去任务，都会排列在那里——每执行一次 <code>start</code> 对应一个标签。<strong>实际显示的</strong>是你选中的那一个标签，同一时刻画面上只会有一个小队。打开画面时会自动为你选好一个正在运行的小队；如果在你查看旧记录期间又有新任务开始，画面会把你带回那个正在运行的小队。',
    'm.s5.th1':    '情况',
    'm.s5.th2':    '画面',
    'm.s5.r1a':    '完全没有记录',
    'm.s5.r1b':    '待机画面',
    'm.s5.r2a':    '小队 A 运行中',
    'm.s5.r2b':    'A 被选中并显示',
    'm.s5.r3a':    'A 执行了 <code>finish</code>',
    'm.s5.r3b':    '仍显示 A（以完成状态保留）',
    'm.s5.r4a':    '接着 B 执行了 <code>start</code>',
    'm.s5.r4b':    '画面切换到 B。A 留在标签栏中，可以随时调回',
    'm.s5.r5a':    'A 和 B 同时运行中',
    'm.s5.r5b':    '两者都会各有一个标签；显示的是你选中的那一个（一次一个）',
    'm.s5.diagram':
      '待机（完全没有记录）\n' +
      '   │ start\n' +
      '   ▼\n' +
      'A 运行中 ────────────────► 画面: A\n' +
      '   │ finish\n' +
      '   ▼\n' +
      'A 已完成（.current 仍为 A）─► 画面: A（以完成状态继续显示）\n' +
      '   │ 在另一个文件夹里 start\n' +
      '   ▼\n' +
      'B 运行中（.current 变为 B）► 画面: B（A 留在标签栏中）\n' +
      '\n' +
      '所有正在运行的任务，以及所有过去的任务，都会排列在标签栏中。\n' +
      '画面只显示你选中的那一个标签——一次一个。较新的排在最左边。\n' +
      '   ┌─────────────┬─────────────┬─────────────────┐\n' +
      '   │ B（运行中） │ A（已完成） │ A（过去的记录） │ ← 标签栏\n' +
      '   └─────────────┴─────────────┴─────────────────┘',
    'm.s5.note1.b':'并行运行时其中一方先结束，完成回报也不会消失',
    'm.s5.note1.p1':'假设你并行运行 A 和 B，而 A 先执行了 <code>finish</code>。此时 A 已不再是「最近一次 <code>start</code> 的小队」，若放任不管，它会在完成的瞬间不再被推送到画面上。为避免这种情况，<b>在当前运行中的小队开始之后才完成的小队</b>会继续被当作运行中推送。无论如何，A 的记录都能从标签栏中找到；这样做是为了不让你正在阅读的报告，在送达的那一刻就在你眼前定格。',
    'm.s5.note1.p2':'如果只是按顺序工作（前一个小队结束后才 <code>start</code> 下一个），前一个小队的完成时间早于下一个的开始时间，因此会如上表所示从画面上退场。这两种情况会根据完成时刻与开始时刻的先后自动区分。',
    'm.s5.note2.b':'显示哪个小队由服务器决定',
    'm.s5.note2.p1':'会改写 <code>missions/.current</code> 这个文件的只有 <code>start</code> 和 <code>demo</code>。<code>add</code> / <code>done</code> / <code>finish</code> 不会移动它，因此已完成的画面不会擅自切换到别的项目。即使在 URL 上加 <code>?project=</code> 这样的指定，也会被有意忽略——服务器要推送哪些小队，是它按设计做出的决定。<em>你</em>能选择的，是从标签栏中查看其中的哪一个——以及哪一条过去的记录。这个选择会被浏览器记住。',
    'm.s5.p2':     '为了不让停止更新却仍处于 <code>running</code>（运行中）的旧记录一直显示下去，默认设有<strong>3 小时</strong>的时间窗口。<code>state.json</code> 的更新早于该窗口的 <code>running</code> 会被视为「已被放置」，不再作为运行中的小队被推送（记录本身仍会保留，并可继续从标签栏中选择）。该时间窗口可通过环境变量 <code>AGENT_DASHBOARD_ACTIVE_WINDOW</code>（单位为秒）修改。',
    'm.s5.p3':     '属于哪个项目<strong>由你所在的工作文件夹自动决定</strong>。即使不同位置有同名文件夹，也会以完整路径区分，不会混淆（用于区分的名称只出现在记录文件夹内部，不会显示在画面上）。',
    'm.s5.note3.b':'从画面上消失并不代表记录被删除',
    'm.s5.note3.p1':'不再显示的小队，其记录仍原样保留在 <code>missions/&lt;slug&gt;/</code> 中。列出、删除、初始化请使用以下命令。',
    'm.s5.th3':    '命令',
    'm.s5.th4':    '作用',
    'm.s5.c1':     '列出保留下来的记录。<code>●</code> 表示当前显示在画面上的小队',
    'm.s5.c2':     '删除记录。默认只是移入 <code>trash/&lt;slug&gt;-&lt;时间戳&gt;/</code>，把文件夹放回去即可恢复。要彻底删除请加上 <code>--yes --force</code>',
    'm.s5.c3':     '将该项目的记录恢复为待机中（文件夹本身保留）',

    'm.s6.title':  '「—」不是故障',
    'm.s6.note.b': '重要',
    'm.s6.note.p': 'Token 数和工具使用次数有时会显示 <code>—</code>。这表示<strong>该数值未包含在完成回报中</strong>，是正常显示。它如实地表明数字没有取到。',
    'm.s6.p1':     '这里采取不填入估算值的方针。如果画面上排满了「大概两万 Token 左右吧」这样的数字，看这个画面来做判断就失去了意义。<code>—</code> 的意思是「未知」，而不是「零」。',
    'm.s6.p2':     'Token 合计同样只是把能实测到的单元相加得出的值。如果所有单元都未知，合计也会是 <code>—</code>。',

    'm.s7.title':  '机制的内部',
    'm.s7.p1':     '从这里开始的内容，只是使用的话不必阅读。为了想深入了解机制的人，下面用面向使用者的语言说明代码实际的运作。',
    'm.s7.h1':     '整体构造',
    'm.s7.p2':     '这个面板完全没有使用外部库。它仅靠 Python 标准库（<code>http.server</code> 等）以及原生的 HTML、CSS、JavaScript 运行。VSCode 扩展一侧也只用 <code>vscode</code> 和 Node.js 的内置模块构建，不含 <code>node_modules</code>。这是优先考虑便携性和不破坏你的环境的结果。',
    'm.s7.h2':     '数据的流向',
    'm.s7.p3':     '从更新到画面显示，流程如下。',
    'm.s7.flow':
      'Claude 执行 update_state.py add\n' +
      '  └ 写入 missions/&lt;slug&gt;/state.json（先写 .tmp，再用 os.replace 替换）\n' +
      '       ↑ 由于是原子替换，每秒读取的服务器不会读到损坏的 JSON\n' +
      '服务器（server.py）\n' +
      '  └ 每秒接收 GET /api/state 后\n' +
      '      ├ 查看 missions/.current 和各 state.json 的 phase，决定「要显示的小队」\n' +
      '      └ 将 state.json 与 agents/*.json 合并组装成 JSON\n' +
      '浏览器（public/index.html）\n' +
      '  └ 每秒获取一次 /api/state\n' +
      '      ├ 与上次内容相同则什么都不做（差分检测）\n' +
      '      └ 若有变化，只重绘发生变化的小队',
    'm.s7.h3':     '状态只有文件',
    'm.s7.p4':     '没有使用数据库。<code>missions/&lt;slug&gt;/state.json</code> 是唯一的正本。进程之间并不在内存中共享状态，因此关掉服务器也不会丢失记录，而且 <code>update_state.py</code> 在服务器没有运行时也能写入。',
    'm.s7.h4':     'Slug（项目的标识符）',
    'm.s7.p5':     '项目的标识符（slug）由「文件夹名 ＋ 完整路径 SHA1 的前 6 位」构成。即使不同位置有同名文件夹也不会冲突。由于 Windows 和 macOS 不区分路径大小写，在计算哈希前会先把路径统一转为小写。',
    'm.s7.h5':     '保存位置的决定方式',
    'm.s7.p6':     '记录的保存位置按以下优先顺序决定。',
    'm.s7.li1':    '如果指定了环境变量 <code>AGENT_DASHBOARD_HOME</code>，就用它',
    'm.s7.li2':    '未指定时，使用工具自身所在的文件夹（如果可写）。也支持放进 U 盘随身携带的用法',
    'm.s7.li3':    '如果那里也不可写，则使用操作系统标准的用户数据目录',
    'm.s7.p7':     '当前实际的保存位置如下。',
    'm.s7.h6':     '孙代理的自行申报',
    'm.s7.p8':     '无法经由 <code>update_state.py</code> 的子代理（相当于孙代理）也可以自行写入 <code>missions/&lt;slug&gt;/agents/&lt;ID&gt;.json</code> 文件，把自己注册到画面上。服务器在读取时会把这些内容与 <code>state.json</code> 合并，但<strong>如果 ID 重复，则以 <code>state.json</code> 一侧为准</strong>（自行申报终究只是辅助）。执行 <code>start</code> 时，上一个任务的自行申报文件会全部被删除。这是为了防止没有收到完成回报的孙代理一直以「运行中」的状态留在画面上。',
    'm.s7.h7':     '代数（第几列）由服务器每次重新计算',
    'm.s7.p9':     '单元在画面上位于第几代（第几列），并不是直接使用保存的值，而是由服务器每次沿着 <code>parentId</code>（父的 ID）重新推算。因此即使在自行申报文件里写错了代数，画面也不会出错。找不到父的单元会被视为直接位于指挥塔之下；父子关系出现循环时也会被检测出来并停止处理。',
    'm.s7.h8':     '谱系树的排布方式',
    'm.s7.p10':    '单元以「向右延伸的整形树」的形式排布。父单元被放在它所生子单元占据的纵向范围的中央。位置从最深的代数开始依次确定，当间距变紧时，会把该单元连同其下的子树一起向下移动。每个单元的位置只由纵坐标（<code>top</code>）指定，画面上的排列顺序本身不会改变。因为一旦改变元素顺序，浏览器就会中断该元素以下的 CSS 动画并从头重建——那样每增加一个单元，画面上已有的所有机器人的呼吸、眨眼、表情变化都会被重置。',
    'm.s7.h9':     '连接父子的线',
    'm.s7.p11':    '连接父子的线，是通过测量实际绘制出来的卡片和机器人的位置，在其连接处画出曲线的。由于使用的是实际绘制的位置而非计算位置，即使卡片高度因字数或换行而变化，线也不会错位。运行中的单元较多时，会停止线的虚线动画。因为每一条线每帧都会引发重绘，停止动作可以抑制负载。',
    'm.s7.h10':    '画面的更新',
    'm.s7.p12':    '画面采用每秒获取一次最新状态的方式更新。没有使用 WebSocket 这类常连接机制（为了不增加依赖）。它会根据获取到的内容生成任务、单元、日志条数的特征，若与上次获取时相同则不重绘。只有运行中单元的已用时会每秒递增。即使服务器与浏览器的时钟有偏差，也会用响应中包含的服务器时刻每次校正。若因网络延迟等原因旧的响应后到达，则会丢弃旧的那个。',
    'm.s7.h11':    '服务器',
    'm.s7.p13':    '服务器在 <code>127.0.0.1</code>（仅限本机内部）监听。默认端口为 3939，若被占用则最多顺延 10 次寻找空闲端口。对外提供的只有 <code>public/</code> 文件夹中的内容，指定其他路径会被拒绝。删除记录的操作只接受 <code>POST</code>，仅在浏览器中直接打开（<code>GET</code>）不会执行。这是为了防止误删。',
    'm.s7.h12':    'VSCode 扩展',
    'm.s7.p14':    'VSCode 扩展只是启动服务器，并把 <code>http://127.0.0.1:&lt;端口&gt;/</code> 嵌入 webview 中显示而已。画面内容与在浏览器中直接查看完全相同。存活确认是通过响应中是否包含自身工具的位置（<code>toolRoot</code>）来判定的，因此不会碰巧连上别人另行启动的服务器。',
    'm.s7.h13':    '只显示实测值',
    'm.s7.p15':    '已用时间、Token 数、工具调用次数，以及<strong>模型名称</strong>之中，未传入的值会被保存为「未知」——前三项在画面上显示为 <code>—</code>，模型名称则显示为「未知」。绝不会用看似合理的估算值填补。指挥部自身的模型也遵循同一规则：在 <code>start</code> 上不加 <code>--model</code>，它就会显示为未知，而不会回退到某个固定的模型 ID。这一方针在代码的多处（说明文、命令帮助、运行时显示）都有明确记载。这个画面的目的是看「实际发生了什么」，一旦填补，这个目的就被破坏了。',
    'm.s7.h14':    '「？」按钮以浮层方式打开的原因',
    'm.s7.p16':    'VSCode 的 webview 不允许其中嵌入的画面打开新窗口（因为其 <code>sandbox</code> 属性不包含 <code>allow-popups</code>）。该限制也会波及嵌套的画面，因此在 VSCode 中嵌入查看时，试图用新窗口打开手册链接会<strong>连错误都不报就被忽略</strong>。所以这份手册不是以新窗口，而是以画面内的浮层方式打开。在浏览器中直接查看时，也可以选择「在新窗口中打开」。',

    'm.s8.title':  '你自己会用到的命令',
    'm.s8.p1':     '平时由 Claude 自动更新，所以你实际用到的就只有这些。表中把 <code>{LAUNCHER_PATH}</code> 简写为 <code>dash</code>。写成 <code>{PY} {UPDATE_PY}</code> 效果相同。',
    'm.s8.th1':    '命令',
    'm.s8.th2':    '作用',
    'm.s8.c1':     '启动画面的服务器并打开浏览器。要停止时在该窗口按 <code>Ctrl+C</code>',
    'm.s8.c2':     '列出已注册的项目。<code>→</code> 表示当前文件夹对应的那个',
    'm.s8.c3':     '以表格形式查看当前项目的内容',
    'm.s8.c4':     '写入用于确认显示效果的示例数据',
    'm.s8.c5':     '清空当前项目（不影响其他项目）',
    'm.s8.c6':     '迁移到别的电脑时的初始设置（把路径写入这台机器上每个 AI 编程 CLI 的指示文件中）',
    'm.s8.c7':     '列出该项目过去的任务（保存在 <code>history/</code> 中的那些）',
    'm.s8.note.b': '在哪里执行',
    'm.s8.note.p': '目标项目由<strong>执行命令时所在的文件夹</strong>决定。想操作别的项目时，请像 <code>--project learning</code> 这样加上名称的一部分。',

    'm.s9.title':  '遇到问题时',
    'm.s9.q1':     '画面一片漆黑，或显示「还没有单元」',
    'm.s9.a1':     '该项目还没有开始任何任务。请 Claude 做点工作就会填上。若想立刻确认显示效果，请执行 <code>update_state.py demo</code>。',
    'm.s9.q2':     '右上角的指示灯变红了',
    'm.s9.a2':     '与服务器的通信中断了。请确认启动服务器的那个窗口是否已被关闭。若已关闭，再次执行 <code>python ...\\server.py</code> 即可恢复。另外，即使通信中断，之前的显示仍会保留，画面不会消失。',
    'm.s9.q3':     '3939 打不开',
    'm.s9.a3':     '如果其他应用占用了端口，会自动顺延到 3940、3941……。启动服务器的窗口里会显示实际的 URL，请打开那个。',
    'm.s9.q4':     '侧栏出现了黄色警告',
    'm.s9.a4':     '意思是孙代理写入的某个文件已损坏。损坏的文件会被忽略，其他单元照常显示。放着不管也没问题，若在意可以用 <code>dash reset --purge</code> 清理该项目的孙代理文件。',
    'm.s9.q5':     '想删除不再需要的项目',
    'm.s9.a5':     '执行 <code>{PY} {UPDATE_PY} remove</code> 最为安全。默认只是移入 <code>trash/&lt;slug&gt;-&lt;时间戳&gt;/</code>，即使弄错了，把文件夹放回去也能恢复。若想手动删除，请从下面的文件夹中整个删掉对应项目的文件夹。之后它会从列表（<code>{PY} {UPDATE_PY} projects</code>）中消失。',
    'm.s9.q6':     '过去的任务能保留多久？',
    'm.s9.a6':     '每个项目最多保留<strong>20 个过去的任务</strong>。再次执行 <code>start</code> 不会覆盖上一次的记录——整份记录会移动到 <code>missions/&lt;project&gt;/history/&lt;start time&gt;/</code>，并可从标签栏中调回。超过 20 个后，最旧的会被移动到 <code>trash/</code>（把文件夹移回去即可恢复）。这个数量可以通过环境变量 <code>AGENT_DASHBOARD_HISTORY_KEEP</code> 修改。事件日志最多保留最近 300 行。',
    'm.s9.q7':     'AI 不帮我更新',
    'm.s9.a7a':    '运行规则会写入这台机器上安装的每一个 AI 编程 CLI 的指示文件中（<span class="path">{INSTRUCTION_FILES}</span>），通常会自动更新。如果它似乎忘了，补一句「顺便也更新面板」即可。',
    'm.s9.a7b':    '如果这些规则不在那里（比如刚复制到另一台电脑后），请执行一次 <code>dash install</code>。它会把这台电脑上正确的路径写入它找到的每一个 CLI 中。',
    'm.s9.q8':     '想在别的电脑上使用 / 想更换位置',
    'm.s9.a8a':    '把整个文件夹复制过去，然后在目标位置执行一次 <code>dash install</code>。路径会在运行时自动解析，放在哪里都可以。',
    'm.s9.a8b':    '想更改记录的保存位置时，请把环境变量 <code>AGENT_DASHBOARD_HOME</code> 指向某个文件夹（适用于想放在共享盘或其他磁盘的场合）。',
    'm.s9.q9':     '只有名字和任务内容跟画面是不同的语言',
    'm.s9.a9a':    '名字和任务内容<strong>不会被翻译</strong>。它们是 AI 登记部队时写下的自由文本，画面照记录的样子显示——在右上角切换语言，改变的是它们周围的标题和标签，记录本身不会变。',
    'm.s9.a9b':    'AI 用什么语言来写，是在命令那一侧另外定下的。执行 <code>dash lang zh</code>（或 <code>en</code> / <code>ja</code> / <code>ko</code>），然后重启你的 AI 编程 CLI 会话——这一条命令也会把运行规则改写成新的语言，所以你设置的语言就是组队时使用的语言。已经记录下来的任务保持写下时的样子，因为这个画面是用来映照「实际发生的事情」的。',

    'm.s10.title': '什么东西在什么位置',
    'm.s10.p1':    '本工具位于以下位置。',
    'm.s10.tree':
      '├─ dash.cmd / dash    启动器（一切都可经由它调用）\n' +
      '├─ dash.py            启动器本体\n' +
      '├─ server.py          画面的服务器\n' +
      '├─ update_state.py    改写状态的命令\n' +
      '├─ install.py         初始设置（迁移到别的电脑时用）\n' +
      '├─ dashlib.py         上述文件共享的内部处理\n' +
      '├─ README.md          安装步骤\n' +
      '├─ OPERATION.md       给 Claude 的详细运行手册\n' +
      '├─ public/\n' +
      '│  ├─ index.html      面板画面\n' +
      '│  ├─ i18n.js         画面的文案表\n' +
      '│  ├─ manual-i18n.js  本手册的文案表\n' +
      '│  └─ manual.html     本手册\n' +
      '└─ missions/          各项目的记录\n' +
      '   └─ &lt;项目名&gt;-&lt;6 位&gt;/\n' +
      '      ├─ state.json         当前状况\n' +
      '      └─ agents/            孙代理的自行申报',
    'm.s10.p2':    '记录的保存位置如下。',
    'm.s10.p3':    '无需额外安装。它仅靠 Python 的标准功能运行，既不使用外部库也不需要联网。画面也自成一体。在 Windows / macOS / Linux 上的表现完全相同。',
    'm.footer1':   'Subagent Dashboard — Python 3.9 以上 / 无外部库 / 支持 Windows・macOS・Linux',
    'm.footer2':   '给 Claude 的详细运行手册位于 <span class="path">{TOOL_ROOT}</span> 下的 <code>OPERATION.md</code>。',
  };

  // ============================================================== 한국어
  M.ko = {
    'manual.doctitle': '사용 설명서 — Subagent Dashboard',

    'm.eyebrow':   '사용 설명서',
    'm.h1':        'Subagent Dashboard',
    'm.lead':      'Claude Code 의 서브에이전트가 지금 몇 대 움직이고 있고, 어느 것이 끝났으며, 시간과 토큰을 얼마나 썼는지를 실시간으로 보기 위한 화면입니다. 로봇의 표정과 움직임으로 상태를 알 수 있습니다.',
    'm.open':      '▶ 대시보드 열기',
    'm.toc':       '목차',

    'm.s1.title':  '이것은 무엇을 하는 것인가요?',
    'm.s1.p1':     'Claude 에게 규모 있는 조사나 작업을 맡기면, Claude 는 뒤에서 <strong>서브에이전트</strong>（부하 AI）를 여러 대 띄워 병렬로 일하게 합니다. 그런데 평소 화면에서는 그것이 몇 대 움직이고 있는지, 어느 것이 끝났는지가 거의 보이지 않습니다.',
    'm.s1.p2':     '그 모습을 옆에서 들여다보기 위한 화면이 <strong>Subagent Dashboard</strong>입니다.',
    'm.s1.li1':    '왼쪽 끝이 <strong>지휘탑</strong>（Claude 본체）, 오른쪽으로 갈수록 깊은 세대（부하의 부하）',
    'm.s1.li2':    '부모와 자식은 선으로 이어집니다. 선이 빛나며 흐르는 것은 그 유닛이 가동 중이라는 뜻',
    'm.s1.li3':    '끝난 유닛은 실측값（소요 시간・토큰 수）과 결과의 한 줄 요약을 남깁니다',
    'm.s1.li4':    '오른쪽 이벤트 로그에 「탄생」과 「귀환」이 중계처럼 흘러갑니다',
    'm.s1.note.b': '갱신하는 것은 Claude 입니다',
    'm.s1.note.p': '직접 입력할 필요는 없습니다. Claude 가 서브에이전트를 띄운 순간과 완료 보고를 받은 순간에 자동으로 씁니다. 당신은 화면을 열어 바라보기만 하면 됩니다.',

    'm.s2.title':  '3단계로 시작하기',
    'm.s2.step1.h':'서버를 시작한다',
    'm.s2.step1.p1':'터미널（명령 프롬프트 / PowerShell / 셸）에서 다음을 실행합니다. <strong>서버 하나로 모든 프로젝트의 기록을 다룰 수 있지만, 화면에 나오는 것은 가동 중인 팀과 가장 최근 팀뿐입니다.</strong>',
    'm.s2.step1.p2':'<code>--open</code> 을 붙이면 브라우저도 자동으로 열립니다. Python 을 직접 불러도 같습니다.',
    'm.s2.step1.p3':'시작하면 URL 이 표시됩니다. 이 창은 닫지 말고 열어 두세요.',
    'm.s2.step2.h':'브라우저에서 연다',
    'm.s2.step2.p1':'표시된 URL（보통은 아래）을 엽니다. 북마크해 두면 편합니다.',
    'm.s2.step2.p2':'포트를 다른 앱이 쓰고 있었다면 3940, 3941… 로 자동으로 밀리므로, 시작 로그에 나온 URL 을 쓰세요.',
    'm.s2.step3.h':'Claude 에게 작업을 맡긴다',
    'm.s2.step3.p1':'다음부터는 평소대로 Claude 에게 조사나 작업을 맡기기만 하면 됩니다. 서브에이전트가 시작되면 그 자리에서 로봇이 <strong>퐁 하고 나타납니다</strong>. 약 1초마다 자동으로 갱신되므로 화면을 새로 고칠 필요가 없습니다.',
    'm.s2.note.b': '우선 움직이는 모습을 보고 싶을 때',
    'm.s2.note.p': '실제 작업을 기다리지 않고 표시를 확인하고 싶다면, 보고 싶은 프로젝트 폴더에서 다음을 실행하세요. 대기 중・가동 중・보고 대기・완료가 모두 갖춰진 더미 데이터가 들어갑니다.',
    'm.mask.b':    '아래 경로는 사용자 이름을 가렸습니다',
    'm.mask.p':    '이 페이지의 경로가 홈 폴더를 지날 때, 사용자 이름 부분은 <code>&lt;username&gt;</code> 으로 표시됩니다——화면 공유나 스크린샷에 찍히지 않도록 하기 위해서입니다. 명령을 실행하기 전에, 그 부분을 자신의 사용자 이름으로 바꿔 주세요.',

    'm.s3.title':  '로봇의 표정으로 상태를 알 수 있습니다',
    'm.s3.p1':     '상태는 네 가지뿐입니다. 표정과 움직임이 다르므로 멀리서도 구별할 수 있습니다. 이 중 「보고 대기」는 작업 중의 한 종류로, <strong>가동 중인 부하를 거느린 유닛</strong>에 붙습니다.',
    'm.s3.cap.standby':'대기 중',
    'm.s3.sub.standby':'둥근 눈으로 천천히 깜빡입니다.<br>호흡에 맞춰 은은하게 움직입니다',
    'm.s3.cap.running':'작업 중',
    'm.s3.sub.running':'활발하게 깜빡이며 집중합니다.<br>안테나와 가슴의 램프가 점멸합니다',
    'm.s3.cap.waiting':'보고 대기',
    'm.s3.sub.waiting':'움직임을 줄이고 자식의 보고를 기다립니다.<br>주사선이 멈추고 가슴의 램프가 호박색으로 바뀝니다',
    'm.s3.cap.done':   '완료',
    'm.s3.sub.done':   '눈을 호로 만들어 기쁨을 표현합니다.<br>몸 색이 바뀌고 결과가 표시됩니다',
    'm.s3.p2':     '새 유닛이 늘어날 때는 그 자리에서 <strong>퐁 하고 튀어나옵니다</strong>（빛의 고리가 퍼집니다）. 놓쳐도 이벤트 로그에 「◯◯ 탄생」이 남습니다.',

    'm.s4.title':  '카드 읽는 법',
    'm.s4.demo_name':   '정찰A',
    'm.s4.demo_mission':'src/ 아래의 API 호출 지점을 모두 찾아낸다',
    'm.s4.legend1':'<b>이름과 ID</b> — 큰 쪽이 이름, 작은 고정폭 문자가 식별자',
    'm.s4.legend2':'<b>모델명</b> — 그 유닛이 사용한 모델',
    'm.s4.legend3':'<b>자가 보고 배지</b> — 손자（부하의 부하）가 스스로 기록한 유닛에 붙습니다',
    'm.s4.legend4':'<b>보고 대기 배지</b> — 가동 중인 부하를 거느린 유닛에 붙습니다（아래 상자 참조）',
    'm.s4.legend5':'<b>임무 내용</b> — 무엇을 시키고 있는지（두 줄까지）',
    'm.s4.legend6':'<b>경과／토큰／도구</b> — 가동 중에는 경과 시간이 매초 늘어납니다. 완료 후에는 실측값',
    'm.s4.p1':     '완료되면 카드 아래에 <strong>결과의 한 줄 요약</strong>이 초록 글씨로 추가되고, 카드 전체가 회색으로 가라앉습니다. 「더 볼 필요가 없는 것」이 시각적으로 가라앉으므로, 지금 움직이는 것만 눈에 들어옵니다.',
    'm.s4.note1.b':'「보고 대기」는 도출된 값입니다',
    'm.s4.note1.p1':'가동 중인 부하를 한 대 이상 거느린 유닛에는 「보고 대기」가 붙고, 움직임이 호흡으로 잦아들며 호박색이 됩니다. 지휘탑이 이 상태라면 봐야 할 것은 오른쪽으로 뻗은 자식 쪽입니다.',
    'm.s4.note1.p2':'다만 이것은 <code>state.json</code> 에 적힌 사실이 아니라 <strong>부모-자식 관계로부터의 도출</strong>입니다. 「자식이 움직이고 있다」는 사실이지만 「부모가 기다리고 있다」는 추측이며, 부모가 자식과 병행하여 자기 작업을 진행 중일 때는 실제와 어긋납니다. 토큰 수 같은 실측값과는 다루는 방식이 다르다는 점을 기억해 두세요. 이를 보고하기 위한 명령은 없습니다（기록은 지금도 「시작 직후」와 「완료 보고 시」 두 시점뿐입니다）.',
    'm.s4.note2.b':'진행률 표시줄은 없습니다',
    'm.s4.note2.p1':'서브에이전트는 작업 중에 「지금 몇 퍼센트」인지 보고하지 않습니다. 즉 퍼센트의 실측값은 어디에도 존재하지 않습니다. 예전에는 「움직이고 있다」는 것만 나타내는 흐르는 줄무늬를 두었지만, 진행 정도를 나타내는 것처럼 읽혀서 없앴습니다. 가동 중인지 아닌지는 로봇의 움직임과 카드 색으로 알 수 있습니다. 경과 시간은 진짜입니다.',

    'm.s5.title':  '어떤 팀이 화면에 나오는가',
    'm.s5.p1':     '화면에 무엇이 나오는지는 두 가지로 정해집니다. <strong>고를 수 있는 범위</strong>는 탭 바입니다. 가동 중인 각 프로젝트의 미션과 <code>history/</code> 에 남아 있는 지난 미션들이 <code>start</code> 한 번당 탭 하나로 그곳에 나란히 놓입니다. <strong>실제로 표시되는 것</strong>은 그중 선택한 탭 하나뿐이며, 화면에는 한 번에 팀 하나만 나옵니다. 화면을 열면 가동 중인 팀이 자동으로 선택되고, 지난 기록을 보는 동안 새 미션이 시작되면 화면은 그 가동 중인 팀으로 다시 이동합니다.',
    'm.s5.th1':    '상황',
    'm.s5.th2':    '화면',
    'm.s5.r1a':    '기록이 전혀 없음',
    'm.s5.r1b':    '대기 화면',
    'm.s5.r2a':    '팀 A 가 가동 중',
    'm.s5.r2b':    'A 가 선택되어 표시됨',
    'm.s5.r3a':    'A 가 <code>finish</code> 함',
    'm.s5.r3b':    'A 그대로 표시（완료 상태로 남음）',
    'm.s5.r4a':    '다음으로 B 가 <code>start</code> 함',
    'm.s5.r4b':    '화면은 B 로 이동함. A 는 탭 바에 남아 다시 불러올 수 있음',
    'm.s5.r5a':    'A 와 B 가 동시에 가동 중',
    'm.s5.r5b':    '둘 다 탭이 생김. 선택한 쪽만 표시됨（한 번에 하나）',
    'm.s5.diagram':
      '대기（기록이 전혀 없음）\n' +
      '   │ start\n' +
      '   ▼\n' +
      'A 가 가동 중 ────────────────► 화면: A\n' +
      '   │ finish\n' +
      '   ▼\n' +
      'A 완료（.current 는 A 그대로）─► 화면: A（완료 상태로 계속 표시됨）\n' +
      '   │ 다른 폴더에서 start\n' +
      '   ▼\n' +
      'B 가동 중（.current 가 B 로 바뀜）► 화면: B（A 는 탭 바에 남음）\n' +
      '\n' +
      '지금 가동 중인 것 전부와 지난 미션 전부가 탭 바에 나란히 놓입니다.\n' +
      '화면은 선택한 탭 하나만 표시합니다——한 번에 하나. 가장 최근 것이 맨 왼쪽에 옵니다.\n' +
      '   ┌──────────────┬───────────┬────────────────┐\n' +
      '   │ B（가동 중） │ A（완료） │ A（지난 기록） │ ← 탭 바\n' +
      '   └──────────────┴───────────┴────────────────┘',
    'm.s5.note1.b':'병렬로 돌린 한쪽이 먼저 끝나도 완료 보고는 사라지지 않습니다',
    'm.s5.note1.p1':'A 와 B 를 병렬로 돌리다가 A 가 먼저 <code>finish</code> 했다고 합시다. 이 시점에서 A 는 더 이상 「가장 최근에 <code>start</code> 된 팀」이 아니므로, 그대로 두면 완료된 순간 화면으로 보내지지 않게 됩니다. 그렇게 되지 않도록, <b>지금 가동 중인 팀이 시작된 뒤에 완료된 팀</b>은 계속 가동 중인 것으로 취급되어 보내집니다. A 의 기록은 어느 쪽이든 탭 바에서 볼 수 있지만, 이는 읽고 있던 보고서가 도착한 그 순간 그대로 멈춰버리지 않도록 하기 위해서입니다.',
    'm.s5.note1.p2':'순서대로 작업하고 있을 뿐인 경우（이전 팀이 끝난 뒤 다음을 <code>start</code> 한 경우）에는 이전 팀의 완료가 다음 시작보다 앞서므로, 위 표대로 화면에서 내려갑니다. 이 둘은 완료한 시각과 시작한 시각의 앞뒤로 자동 구분됩니다.',
    'm.s5.note2.b':'어떤 팀을 보여줄지는 서버 쪽의 결정입니다',
    'm.s5.note2.p1':'<code>missions/.current</code> 라는 파일을 고쳐 쓰는 것은 <code>start</code> 와 <code>demo</code> 뿐입니다. <code>add</code> / <code>done</code> / <code>finish</code> 는 이 파일을 움직이지 않으므로, 완료된 화면이 제멋대로 다른 프로젝트로 바뀌는 일은 없습니다. URL 에 <code>?project=</code> 같은 지정을 붙여도 의도적으로 받지 않습니다——어떤 팀을 서버가 보낼지는 설계상 서버 쪽이 정하는 일이기 때문입니다. <em>당신</em>이 고를 수 있는 것은, 그중 어느 것을——그리고 어느 지난 기록을——탭 바에서 볼지 입니다. 그 선택은 브라우저에 기억됩니다.',
    'm.s5.p2':     '<code>running</code>（가동 중）인 채로 갱신이 멈춘 오래된 기록을 계속 보여주지 않도록, 기본 <strong>3시간</strong>의 시간 창이 있습니다. <code>state.json</code> 의 갱신이 그보다 오래된 <code>running</code> 은 「방치되었다」고 보고, 가동 중인 팀으로는 더 이상 보내지지 않습니다（기록 자체는 남아 탭 바에서 계속 선택할 수 있습니다）. 이 시간 창은 환경 변수 <code>AGENT_DASHBOARD_ACTIVE_WINDOW</code>（초 단위）로 바꿀 수 있습니다.',
    'm.s5.p3':     '어느 프로젝트가 될지는 <strong>작업 중인 폴더로 자동으로 정해집니다</strong>. 같은 이름의 폴더가 다른 곳에 있어도 전체 경로로 구분되므로 섞이지 않습니다（구분에 쓰이는 이름은 기록 폴더 안에만 나타나고 화면에는 나오지 않습니다）.',
    'm.s5.note3.b':'화면에서 사라져도 기록은 지워지지 않습니다',
    'm.s5.note3.p1':'표시되지 않게 된 팀의 기록은 <code>missions/&lt;슬러그&gt;/</code> 에 그대로 남아 있습니다. 목록・삭제・초기화에는 다음 명령을 씁니다.',
    'm.s5.th3':    '명령',
    'm.s5.th4':    '무엇을 하는가',
    'm.s5.c1':     '남아 있는 기록의 목록. <code>●</code> 가 지금 화면에 나와 있는 팀',
    'm.s5.c2':     '기록을 지웁니다. 기본적으로는 <code>trash/&lt;슬러그&gt;-&lt;일시&gt;/</code> 로 옮길 뿐이므로, 폴더를 되돌리면 복구됩니다. 완전히 지우려면 <code>--yes --force</code> 를 붙입니다',
    'm.s5.c3':     '그 프로젝트의 기록을 대기 중으로 되돌립니다（폴더 자체는 남습니다）',

    'm.s6.title':  '「—」는 고장이 아닙니다',
    'm.s6.note.b': '중요',
    'm.s6.note.p': '토큰 수나 도구 사용 횟수에 <code>—</code> 라고 나올 때가 있습니다. 이는 <strong>그 값이 완료 보고에 포함되어 있지 않았다</strong>는 뜻이며 정상적인 표시입니다. 숫자를 얻지 못했다는 사실을 정직하게 표시하고 있습니다.',
    'm.s6.p1':     '여기에 추정값을 넣지 않는 방침입니다. 「대략 2만 토큰쯤이겠지」 같은 숫자가 늘어서면 이 화면을 보고 판단할 의미가 없어지기 때문입니다. <code>—</code> 는 「불명」이지 「0」이 아닙니다.',
    'm.s6.p2':     '총 토큰도 실측할 수 있었던 유닛만 더한 값입니다. 모든 유닛이 불명이면 합계도 <code>—</code> 가 됩니다.',

    'm.s7.title':  '구조의 안쪽',
    'm.s7.p1':     '여기서부터는 쓰기만 할 거라면 읽을 필요가 없는 이야기입니다. 구조를 자세히 알고 싶은 사람을 위해, 실제 코드의 동작을 사용자의 말로 설명합니다.',
    'm.s7.h1':     '전체 구성',
    'm.s7.p2':     '이 대시보드는 외부 라이브러리를 전혀 쓰지 않습니다. Python 표준 라이브러리（<code>http.server</code> 등）와 순수한 HTML・CSS・JavaScript 만으로 동작합니다. VSCode 확장 쪽도 <code>vscode</code> 와 Node.js 내장 모듈만으로 만들어져 있어 <code>node_modules</code> 를 갖지 않습니다. 들고 다니기 쉬움과 환경을 망가뜨리지 않는 것을 우선한 결과입니다.',
    'm.s7.h2':     '데이터의 흐름',
    'm.s7.p3':     '갱신에서 화면 표시까지는 다음과 같이 흐릅니다.',
    'm.s7.flow':
      'Claude 가 update_state.py add 를 실행\n' +
      '  └ missions/&lt;슬러그&gt;/state.json 을 씀（.tmp 에 쓴 뒤 os.replace 로 교체）\n' +
      '       ↑ 원자적으로 교체하므로, 1초마다 읽는 서버가 깨진 JSON 을 보는 일이 없다\n' +
      '서버（server.py）\n' +
      '  └ 1초마다의 GET /api/state 를 받아\n' +
      '      ├ missions/.current 와 각 state.json 의 phase 를 보고 「보여줄 팀」을 정한다\n' +
      '      └ state.json ＋ agents/*.json 을 섞어 JSON 을 조립한다\n' +
      '브라우저（public/index.html）\n' +
      '  └ 1초마다 /api/state 를 가져온다\n' +
      '      ├ 지난번과 내용이 같으면 아무것도 하지 않는다（차분 감지）\n' +
      '      └ 바뀌었다면 그 팀만 다시 그린다',
    'm.s7.h3':     '상태는 파일뿐',
    'm.s7.p4':     '데이터베이스는 쓰지 않습니다. <code>missions/&lt;슬러그&gt;/state.json</code> 이 유일한 정본입니다. 프로세스끼리 메모리에서 상태를 공유하지 않으므로 서버를 내려도 기록은 사라지지 않고, <code>update_state.py</code> 는 서버가 돌지 않아도 기록할 수 있습니다.',
    'm.s7.h4':     '슬러그（프로젝트 식별자）',
    'm.s7.p5':     '프로젝트의 식별자（슬러그）는 「폴더명 ＋ 전체 경로 SHA1 의 앞 6자리」 형태로 만들어집니다. 같은 이름의 폴더가 다른 곳에 있어도 충돌하지 않습니다. Windows 와 macOS 는 경로의 대소문자를 구분하지 않으므로, 해시를 계산하기 전에 경로를 소문자로 맞춥니다.',
    'm.s7.h5':     '저장 위치가 정해지는 방식',
    'm.s7.p6':     '기록의 저장 위치는 다음 우선순위로 정해집니다.',
    'm.s7.li1':    '환경 변수 <code>AGENT_DASHBOARD_HOME</code> 이 지정되어 있으면 그곳',
    'm.s7.li2':    '지정이 없으면 도구 자신이 놓인 폴더（쓸 수 있다면）. USB 메모리 등에 넣어 들고 다니는 운용도 가능합니다',
    'm.s7.li3':    '거기에도 쓸 수 없으면 OS 표준의 사용자 데이터 위치',
    'm.s7.p7':     '지금 실제 저장 위치는 다음과 같습니다.',
    'm.s7.h6':     '손자 에이전트의 자가 보고',
    'm.s7.p8':     '<code>update_state.py</code> 를 거칠 수 없는 서브에이전트（손자에 해당하는 존재）는 <code>missions/&lt;슬러그&gt;/agents/&lt;ID&gt;.json</code> 이라는 파일에 스스로 기록해 화면에 등록할 수도 있습니다. 서버는 읽을 때 이 내용을 <code>state.json</code> 과 섞지만, <strong>ID 가 겹치면 <code>state.json</code> 쪽이 이깁니다</strong>（자가 보고는 어디까지나 보조적인 취급입니다）. <code>start</code> 를 실행하면 이전 미션의 자가 보고 파일은 전부 삭제됩니다. 완료 보고가 오지 않은 손자가 언제까지나 「가동 중」인 채 화면에 남는 것을 막기 위해서입니다.',
    'm.s7.h7':     '세대（몇 번째 열인가）는 서버가 매번 다시 계산합니다',
    'm.s7.p9':     '유닛이 화면에서 몇 세대（몇 번째 열）에 오는지는 저장된 값을 그대로 쓰지 않고, <code>parentId</code>（부모의 ID）를 따라가 서버가 매번 다시 산출합니다. 그래서 자가 보고 파일에 세대 값을 잘못 써도 화면이 망가지지 않습니다. 부모를 찾을 수 없는 유닛은 지휘탑 바로 아래로 취급되며, 부모-자식 관계가 순환하는 경우도 검출해 처리를 멈춥니다.',
    'm.s7.h8':     '계통수를 배치하는 방식',
    'm.s7.p10':    '유닛은 「옆으로 뻗는 정형 트리」 형태로 배치됩니다. 부모는 자신이 낳은 자식들이 차지하는 세로 범위의 중앙에 오도록 놓입니다. 깊은 세대부터 차례로 위치를 확정해 가고, 간격이 좁아지면 그 유닛과 그 아래 부분 트리를 통째로 아래로 밀어냅니다. 각 유닛의 위치는 세로 좌표（<code>top</code>）만으로 지정하며, 화면상의 나열 순서 자체는 바꾸지 않습니다. 요소의 순서를 바꾸면 브라우저가 그 아래의 CSS 애니메이션을 중단하고 처음부터 다시 만들기 때문입니다. 유닛이 늘어날 때마다 이미 표시된 모든 로봇의 호흡・깜빡임・표정 변화가 초기화되는 것을 피하고 있습니다.',
    'm.s7.h9':     '부모와 자식을 잇는 선',
    'm.s7.p11':    '부모와 자식을 잇는 선은 실제로 그려진 카드와 로봇의 위치를 측정해 그 이음매에 곡선을 그립니다. 계산상의 위치가 아니라 실제로 그려진 위치를 쓰므로, 글자 수나 줄바꿈으로 카드 높이가 달라져도 선이 어긋나지 않습니다. 가동 중인 유닛이 많을 때는 선의 파선 애니메이션을 멈춥니다. 유닛 수만큼 매 프레임 다시 그리기가 발생하므로, 움직임을 멈춰 부하를 억제합니다.',
    'm.s7.h10':    '화면의 갱신',
    'm.s7.p12':    '화면은 1초마다 최신 상태를 가져오는 방식으로 갱신됩니다. WebSocket 같은 상시 연결 구조는 쓰지 않습니다（의존을 늘리지 않기 위해서입니다）. 가져온 내용에서 미션・유닛・로그 건수의 특징을 만들어, 지난번과 달라지지 않았으면 다시 그리지 않습니다. 가동 중인 유닛의 경과 시간만 매초 늘어납니다. 서버의 시각과 브라우저의 시각이 어긋나 있어도, 응답에 담긴 서버 쪽 시각으로 매번 보정됩니다. 통신 지연 등으로 오래된 응답이 나중에 도착한 경우, 그 오래된 쪽은 버립니다.',
    'm.s7.h11':    '서버',
    'm.s7.p13':    '서버는 <code>127.0.0.1</code>（자기 PC 안에서만）에서 대기합니다. 기본 포트는 3939 이고, 사용 중이면 최대 10번까지 번호를 올려 빈 포트를 찾습니다. 제공되는 것은 <code>public/</code> 폴더의 내용뿐이며, 그 밖의 경로를 지정하면 거부됩니다. 기록을 지우는 조작은 <code>POST</code> 로만 받으므로, 브라우저에서 직접 여는 것（<code>GET</code>）만으로는 실행되지 않습니다. 실수로 지우는 것을 막기 위해서입니다.',
    'm.s7.h12':    'VSCode 확장',
    'm.s7.p14':    'VSCode 확장은 서버를 시작해 <code>http://127.0.0.1:&lt;포트&gt;/</code> 를 webview 안에 끼워 넣어 보여줄 뿐입니다. 화면의 내용은 브라우저에서 직접 볼 때와 완전히 같습니다. 생존 확인은 응답 안에 자기 자신의 도구 위치（<code>toolRoot</code>）가 들어 있는지로 판정하므로, 우연히 다른 사람이 따로 띄운 서버에 붙는 일은 없습니다.',
    'm.s7.h13':    '실측값만 내보냅니다',
    'm.s7.p15':    '경과 시간・토큰 수・도구 사용 횟수, 그리고 <strong>모델 이름</strong> 중 넘어오지 않은 값은 「불명」으로 저장됩니다——앞의 세 가지는 화면에 <code>—</code> 로 표시되고, 모델 이름은 「불명」으로 표시됩니다. 그럴듯한 추정값으로 채우는 일은 절대 없습니다. 지휘부 자신의 모델도 같은 규칙을 따릅니다. <code>start</code> 에서 <code>--model</code> 을 빼면, 고정된 모델 ID 로 대체되는 대신 불명으로 표시됩니다. 이 방침은 코드의 여러 곳(설명문・명령 도움말・실행 시 표시)에 명기되어 있습니다. 이 화면의 목적은 「실제로 무슨 일이 있었는가」를 보는 것이므로, 채워 버리면 그 목적이 망가지기 때문입니다.',
    'm.s7.h14':    '「？」버튼이 오버레이로 열리는 이유',
    'm.s7.p16':    'VSCode 의 webview 는 안에 끼워 넣은 화면이 새 창을 여는 것을 허용하지 않습니다（<code>sandbox</code> 속성에 <code>allow-popups</code> 가 들어 있지 않기 때문입니다）. 이 제약은 중첩된 화면에도 미치므로, VSCode 에 끼워 넣어 보고 있을 때는 설명서 링크를 새 창으로 열려고 해도 <strong>오류조차 나지 않은 채 무시됩니다</strong>. 그래서 이 설명서는 새 창이 아니라 화면 안의 오버레이로 열도록 하고 있습니다. 브라우저에서 직접 보고 있을 때는 「새 창으로 열기」도 고를 수 있습니다.',

    'm.s8.title':  '직접 쓰는 명령',
    'm.s8.p1':     '평소에는 Claude 가 자동으로 갱신하므로, 당신이 쓰는 것은 사실상 이것뿐입니다. 표에서는 <code>{LAUNCHER_PATH}</code> 를 <code>dash</code> 로 줄여 썼습니다. <code>{PY} {UPDATE_PY}</code> 라고 써도 같은 동작입니다.',
    'm.s8.th1':    '명령',
    'm.s8.th2':    '무엇을 하는가',
    'm.s8.c1':     '화면의 서버를 시작하고 브라우저를 엽니다. 멈출 때는 그 창에서 <code>Ctrl+C</code>',
    'm.s8.c2':     '등록된 프로젝트를 목록으로 표시합니다. <code>→</code> 가 현재 폴더의 대상',
    'm.s8.c3':     '지금 프로젝트의 내용을 표로 확인합니다',
    'm.s8.c4':     '표시 확인용 더미 데이터를 넣습니다',
    'm.s8.c5':     '지금 프로젝트를 비웁니다（다른 프로젝트에는 영향이 없습니다）',
    'm.s8.c6':     '다른 PC 로 옮겼을 때의 초기 설정（이 컴퓨터에 있는 모든 AI 코딩 CLI 의 지시 파일에 경로를 씁니다）',
    'm.s8.c7':     '이 프로젝트의 지난 미션을 나열합니다（<code>history/</code> 에 남아 있는 것들）',
    'm.s8.note.b': '실행하는 위치',
    'm.s8.note.p': '대상 프로젝트는 <strong>명령을 실행한 폴더</strong>로 정해집니다. 다른 프로젝트를 다루고 싶을 때는 <code>--project learning</code> 처럼 이름의 일부를 붙이세요.',

    'm.s9.title':  '곤란할 때',
    'm.s9.q1':     '화면이 캄캄하거나 「아직 유닛이 없습니다」라고 나옵니다',
    'm.s9.a1':     '그 프로젝트에서 아직 미션이 시작되지 않은 상태입니다. Claude 에게 작업을 맡기면 채워집니다. 바로 표시를 확인하고 싶다면 <code>update_state.py demo</code> 를 실행하세요.',
    'm.s9.q2':     '오른쪽 위 표시등이 빨개졌습니다',
    'm.s9.a2':     '서버와의 통신이 끊겼습니다. 서버를 시작한 창이 닫히지 않았는지 확인하세요. 닫혔다면 <code>python ...\\server.py</code> 를 다시 실행하면 복구됩니다. 통신이 끊겨도 직전 표시는 남으므로 화면이 사라지는 일은 없습니다.',
    'm.s9.q3':     '3939 로 열리지 않습니다',
    'm.s9.a3':     '다른 앱이 포트를 쓰고 있었다면 자동으로 3940, 3941… 로 밀립니다. 서버를 시작한 창에 실제 URL 이 나와 있으니 그쪽을 여세요.',
    'm.s9.q4':     '사이드 패널에 노란 경고가 나왔습니다',
    'm.s9.a4':     '손자 에이전트가 쓴 파일 중 하나가 깨져 있다는 뜻입니다. 깨진 파일은 무시되고 다른 유닛의 표시는 계속됩니다. 그대로 둬도 문제없지만, 신경 쓰인다면 <code>dash reset --purge</code> 로 그 프로젝트의 손자 파일을 정리할 수 있습니다.',
    'm.s9.q5':     '필요 없어진 프로젝트를 지우고 싶습니다',
    'm.s9.a5':     '<code>{PY} {UPDATE_PY} remove</code> 를 실행하는 것이 안전합니다. 기본적으로는 <code>trash/&lt;슬러그&gt;-&lt;일시&gt;/</code> 로 옮길 뿐이므로, 잘못해도 폴더를 되돌리면 복구됩니다. 손으로 지우고 싶다면 아래 폴더에서 해당 프로젝트의 폴더를 통째로 삭제하세요. 목록（<code>{PY} {UPDATE_PY} projects</code>）에서 사라집니다.',
    'm.s9.q6':     '지난 미션은 어디까지 남나요?',
    'm.s9.a6':     '<strong>지난 미션은 최대 20개</strong>까지 프로젝트별로 보관됩니다. 다시 <code>start</code> 해도 이전 것을 덮어쓰지 않습니다——기록 전체가 <code>missions/&lt;project&gt;/history/&lt;start time&gt;/</code> 로 옮겨지며, 탭 바에서 다시 불러올 수 있습니다. 20개를 넘으면 가장 오래된 것부터 <code>trash/</code> 로 옮겨집니다（폴더를 되돌리면 복구됩니다）. 이 개수는 환경 변수 <code>AGENT_DASHBOARD_HISTORY_KEEP</code> 으로 바꿀 수 있습니다. 이벤트 로그는 최근 300줄까지 보관됩니다.',
    'm.s9.q7':     'AI 가 갱신해 주지 않습니다',
    'm.s9.a7a':    '운용 규칙은 이 컴퓨터에 설치된 모든 AI 코딩 CLI 의 지시 파일（<span class="path">{INSTRUCTION_FILES}</span>）에 적혀 있으므로 보통은 자동으로 갱신됩니다. 잊은 것 같으면 「대시보드도 갱신해 줘」라고 한마디 덧붙이세요.',
    'm.s9.a7b':    '그 규칙이 들어 있지 않은 경우（다른 PC 에 복사한 직후 등）에는 한 번만 <code>dash install</code> 을 실행하세요. 그 PC 에서 찾아낸 각 CLI 에 올바른 경로가 기록됩니다.',
    'm.s9.q8':     '다른 PC 에서 쓰고 싶다 / 위치를 옮기고 싶다',
    'm.s9.a8a':    '폴더를 통째로 복사하고, 복사한 곳에서 <code>dash install</code> 을 한 번 실행하세요. 경로는 실행 시 자동으로 해결되므로 어디에 둬도 상관없습니다.',
    'm.s9.a8b':    '기록의 저장 위치를 바꾸고 싶다면 환경 변수 <code>AGENT_DASHBOARD_HOME</code> 에 폴더를 지정하세요（공유 드라이브나 다른 드라이브에 두고 싶을 때 씁니다）.',
    'm.s9.q9':     '이름과 임무 내용만 화면과 다른 언어로 나온다',
    'm.s9.a9a':    '이름과 임무 내용은 <strong>번역되지 않습니다</strong>. 이것들은 AI 가 부대를 등록할 때 적은 자유 기술이며, 화면은 기록된 그대로 내보냅니다——오른쪽 위에서 언어를 바꾸면 그 주위의 제목과 라벨은 바뀌지만, 기록 자체는 바뀌지 않습니다.',
    'm.s9.a9b':    'AI 가 어느 언어로 쓸지는 명령 쪽에서 따로 정해져 있습니다. <code>dash lang ko</code>(또는 <code>en</code> / <code>ja</code> / <code>zh</code>)를 실행하고, 사용 중인 AI 코딩 CLI 세션을 재시작하세요——이 명령 하나가 운용 규칙도 새 언어로 다시 쓰므로, 설정한 언어가 그대로 팀을 짜는 언어가 됩니다. 이미 기록된 미션은 쓰였을 때 그대로입니다. 이 화면은 「실제로 일어난 일」을 비추기 위한 것이기 때문입니다.',

    'm.s10.title': '무엇이 어디에 있는가',
    'm.s10.p1':    '이 도구는 다음 위치에 있습니다.',
    'm.s10.tree':
      '├─ dash.cmd / dash    런처（이것을 거쳐 전부 부를 수 있음）\n' +
      '├─ dash.py            런처의 본체\n' +
      '├─ server.py          화면의 서버\n' +
      '├─ update_state.py    상태를 고쳐 쓰는 명령\n' +
      '├─ install.py         초기 설정（다른 PC 로 옮겼을 때용）\n' +
      '├─ dashlib.py         위 파일들이 공유하는 내부 처리\n' +
      '├─ README.md          도입 절차\n' +
      '├─ OPERATION.md       Claude 용 상세 운용 절차\n' +
      '├─ public/\n' +
      '│  ├─ index.html      대시보드 화면\n' +
      '│  ├─ i18n.js         화면의 문구 표\n' +
      '│  ├─ manual-i18n.js  이 설명서의 문구 표\n' +
      '│  └─ manual.html     이 설명서\n' +
      '└─ missions/          프로젝트별 기록\n' +
      '   └─ &lt;프로젝트명&gt;-&lt;6자리&gt;/\n' +
      '      ├─ state.json         현재 상황\n' +
      '      └─ agents/            손자 에이전트의 자가 보고',
    'm.s10.p2':    '기록의 저장 위치는 다음과 같습니다.',
    'm.s10.p3':    '추가 설치는 필요 없습니다. Python 의 표준 기능만으로 동작하며, 외부 라이브러리도 인터넷 연결도 쓰지 않습니다. 화면도 그 자체로 완결됩니다. Windows / macOS / Linux 어디서든 똑같이 동작합니다.',
    'm.footer1':   'Subagent Dashboard — Python 3.9 이상 / 외부 라이브러리 없음 / Windows・macOS・Linux 지원',
    'm.footer2':   'Claude 를 위한 상세 운용 절차는 <span class="path">{TOOL_ROOT}</span> 의 <code>OPERATION.md</code> 에 있습니다.',
  };

  global.I18N.extend(M);

})(window);
