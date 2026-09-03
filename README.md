# Subagent Dashboard

**English** | [日本語](README.ja.md) | [中文](README.zh.md) | [한국어](README.ko.md)

A local app for watching, in real time, how many Claude Code subagents are running right now,
which ones have finished, and how much time and how many tokens they used.
You read the state off the robots' faces and movements.

- **No external libraries** — runs on the Python standard library alone. No `pip install` needed
- **No internet** — zero CDN references. Works offline
- **Runs anywhere** — Windows / macOS / Linux, Python 3.9 or later
- **Lives anywhere** — copy the folder and it works from wherever you put it (a USB stick is fine)

---

## Getting started (2 steps)

### 1. Initial setup (a wizard)

Put the folder wherever you like, then run the setup tool.

#### Recommended: full setup (initial setup + the VSCode extension)

**On Windows:**
- Double-click `setup-full.bat`

**On macOS / Linux:**
- Double-click `setup-full.sh`

**That alone completes all of the following:**
1. Detecting your Python environment
2. Initial setup (writing the operating rules into every AI coding CLI installed on this machine)
3. Installing the VSCode extension

#### Alternative: initial setup only (if you do not use VSCode)

**On Windows:**
- Double-click `setup.bat`

**On macOS / Linux:**
- Double-click `setup.sh`

#### Running it from the command line

```bash
# full setup (Windows)
dash.cmd ext install

# initial setup only (Windows)
dash.cmd install

# macOS / Linux
./dash install
```

**A wizard-style installer starts and sets everything up in four steps:**

1. **Environment check** — verifies the Python version, the file layout and write permissions
2. **Automatic detection** — finds the Python command, the paths and the location of the config files
3. **Writing the config files** — updates the instructions file of every AI coding CLI it finds, plus the VSCode keybindings
4. **Setup complete** — tells you how to start it and what to do next

When every item has a ✓, you are done.

- It detects and embeds the real location of this folder, so **the same commands work on a different PC**
- It rewrites only the region between its markers, so it does not damage anything else already in that CLI's instructions file
- To see what it will write first, run `dash install --print`
- To undo it, run `python install.py --uninstall`

**🧩 Which CLIs it writes to:**

Setup finds every AI coding CLI installed on the machine and writes the same operating rules into each one's own
instructions file — the body of the rules is identical; only the location differs.

| CLI | File written |
| --- | --- |
| Claude Code | `~/.claude/CLAUDE.md` |
| Codex CLI | `~/.codex/AGENTS.md` |
| Gemini CLI | `~/.gemini/GEMINI.md` |
| GitHub Copilot CLI | `~/.copilot/copilot-instructions.md` |
| opencode | `~/.config/opencode/AGENTS.md` |
| Amp | `~/.config/amp/AGENTS.md` |
| Cline | `~/Documents/Cline/Rules/subagent-dashboard.md` |
| Roo Code | `~/.roo/rules/subagent-dashboard.md` |
| Windsurf | `~/.codeium/windsurf/memories/global_rules.md` |
| Qwen Code | `~/.qwen/QWEN.md` |

A CLI missing from this table is not unsupported — it is just not one of the common ones this tool recognises
automatically. Run `python install.py --list-agents` to see the full status of every CLI it knows about,
including ones you've added yourself. Cline and Roo Code read a whole folder of rule files rather than a single
one, so the tool drops one dedicated file into that folder instead of editing your own rules there. Cursor and
Aider are left out on purpose: neither reads a user-level instructions file automatically (Cursor only reads a
per-repository `AGENTS.md`; Aider needs the file named explicitly in its config) — point a per-repository file at
it with `--agent-file`, the same option that covers any other CLI not in this table. For `--agent`,
`--agent-file` and `--list-agents` in full, see [OPERATION.md](OPERATION.md).

**🚀 Automatic setup:**

When an unconfigured state is detected on the first run (for example when the server starts), **it offers to run setup for you.**
- In an interactive environment (run directly in a terminal), a confirmation dialog appears
- In a non-interactive environment (run by Claude), it prints a warning and continues
- If you use the VSCode extension, it runs automatically after the tool is deployed

**🔍 Checking that it works (the diagnostic tool):**

To confirm that everything was configured correctly, run the diagnostic script:

```bash
python diagnose.py
```

It checks six items wizard-style, and you are set once they are all ✓.
If it finds a problem, it prints the cause and the fix as a numbered list.

### 2. Open the screen

```bash
# Windows
dash.cmd serve --open

# macOS / Linux
./dash serve --open
```

Your browser opens. Leave that window running.
**One server is enough — it shows this one screen no matter which project you are working in.**

After that, just ask Claude to do work as usual. When a subagent is launched,
a robot appears on the spot.

The screen shows **the teams that are running right now** (if several projects are active at once, they all line up as tabs).
A team stays on screen after its work ends, and when you next start work in the same project the previous
record is not deleted — it stays available as a "past record" tab. When nothing is running you get the idle screen.

---

## Using it

**The manual ships with the app.** Start the server and open:

```text
http://127.0.0.1:3939/manual.html
```

You can also open it from the "?" button at the top right of the dashboard.
It explains, with diagrams, what the robot faces mean, how to read the cards, and what to do when you are stuck.

### Commands you will use

`dash` is `dash.cmd` on Windows and `./dash` on macOS / Linux.

| Command | What it does |
| --- | --- |
| `dash serve --open` | Start the screen's server and open the browser (`Ctrl+C` to stop) |
| `dash serve --port 4000` | Start it on a specific port |
| `dash projects` | List the registered projects. `→` marks the one the current folder maps to |
| `dash status` | Show the contents of the current project |
| `dash demo` | Insert dummy data for checking the display |
| `dash reset` | Empty the current project |
| `dash history` | List this project's past missions (`history/`) |
| `dash install` | Initial setup (run this after moving to another PC) |

Running `dash` on its own prints the list. Each command has details under `dash <command> --help`.

The commands that write state (`start` / `add` / `done` / `finish`) are normally run by Claude automatically,
so you do not need to type them yourself.

`dash autofinish` is a command apart from those — it is meant to be called from a SessionEnd hook, to **close
whatever mission is still running when the session ends.** A forgotten close is the one failure mode this tool
cannot fix after the fact (the next `start` pushes it into history still marked running, and there is no way to
mark it finished from there), so this ties the close to the end of the session rather than to a person
remembering. With no mission running it prints nothing and exits; leave out `--project` and it closes every
mission running in parallel in that directory. It only closes missions it opened, though — a mission another
session in the same folder is still working on is left alone (skipped silently where the session ID is known,
closed as before where it is not). See [OPERATION.md](OPERATION.md) for an example hook configuration.

### Running two missions at once in the same folder

There is one record destination per project (= per working folder). **If another session tries to push out or
overwrite a mission record that is still running, the tool itself now refuses** (exit code 1; the guidance
prints a ready-to-paste `--project` command). Add `--force` only when you want to push through anyway — it
still pushes the mission out as before, but the record that gets pushed out keeps a note of what pushed it
out. This protection only takes effect when `mission.sessionId` (sourced from `CLAUDE_CODE_SESSION_ID`) is
present on both sides, so older records and environments where `CLAUDE_CODE_SESSION_ID` is not passed through
remain unprotected, as before. If you already know you'll be running in parallel, splitting the record
destination with `--project` beforehand avoids the collision altogether and causes the least friction.

```bash
dash start  --project issue51 --title "issue51 investigation" --model claude-opus-5
dash add    --project issue51 --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "..."
dash done   --project issue51 --id SCOUT-A --headline "..."
dash finish --project issue51 --headline "..."
```

Put `--project` on all four commands. Miss it on even one and that one command writes to the current folder's
side — that is, to the other team's record. `dash install` writes this procedure into every installed CLI's
instructions file as well, so the agent follows the same rule. See [OPERATION.md](OPERATION.md)'s
"6.1. Running two or more missions at the same time in the same directory" for details.

### Looking at past records

Running `start` again in the same project does not delete what was there.
The whole thing is moved to `missions/<project>/history/<start time>/`, and you can look back at it by
picking it from the tab bar (past records are shown with the elapsed time stopped).

By default the 20 most recent are kept per project; anything beyond that moves to `trash/`, oldest first
(you can recover from `trash/` by moving the folder back). You can also list them from the command line.

```bash
dash history
```

---

## Opening it as a VSCode extension (recommended)

You can put a Subagent Dashboard tab inside VSCode. You never have to switch to a browser, and the extension
takes care of starting the server.

### Installing it (once)

```bash
# Windows
dash.cmd ext install

# macOS / Linux
./dash ext install
```

After that, reload VSCode (`Ctrl+Shift+P` → Reload Window).

You need neither npm nor `vsce`. The `.vsix` is assembled using only the Python standard library and handed to `code --install-extension`.

### Using it

Press the **robot icon** that has appeared in the activity bar on the far left, and Subagent Dashboard opens as an editor tab.
If you would rather keep it in a narrow strip on the left, set `agentDashboard.sidebarBehavior` to `embed` and it appears inside the sidebar.

Typing "Subagent Dashboard" in the command palette (`Ctrl+Shift+P`) does the same thing.

| Command | What it does |
|---|---|
| Subagent Dashboard: Open in a tab | Show Subagent Dashboard as an editor tab |
| Subagent Dashboard: Open in a browser | Open it in the OS default browser |
| Subagent Dashboard: Restart the server | Stop the server this extension started and bring it back up |
| Subagent Dashboard: Stop the server | Stop the server this extension started |
| Subagent Dashboard: Deploy or update the tool | Put the bundled tool in its deploy location |
| Subagent Dashboard: Run initial setup | Run initial setup (`install.py`) after confirmation |
| Subagent Dashboard: Reset the setup flag | Clear the "already done" record so it runs again next time |
| Subagent Dashboard: Show the log | See the startup progress and the output from the Python side |

If the server is not running, the extension starts it. If one is already running it reuses it, so processes do not pile up. If the port is taken it moves up to the next number and opens the screen on that one.

A server you started elsewhere (`dash serve` in a terminal, say) is only reused — the extension never stops it on its own.

### Handing it to someone else

**The extension contains the whole dashboard tool.** It works on someone else's PC even if they have nothing installed.

```bash
dash.cmd ext package
```

Two files appear in `dist/`. **Attach these to an email.**

- `agent-dashboard-<version>.vsix` — the extension itself (about 0.1MB)
- `インストール手順.txt` — instructions you can pass along as-is

The person receiving it can install it entirely from the VSCode UI (Extensions panel → `…` → "Install from VSIX..."). The `code` command is not needed.

The first time they press the icon, a confirmation says "the tool will be placed here", and on approval it is unpacked into `~/.claude/agent-dashboard`. **It is never run from where it was bundled.** The extension folder's name contains the version number, so it changes wholesale on an update — records kept there would be lost.

Distributing an updated version overwrites in the same way. It does not touch `missions/` (your work records).

**On an update, the operating rules are redistributed too — to every CLI they were written to.** Otherwise the tool
would be new while the procedure the agent reads stayed at the previous version (initial setup never runs again
automatically once it has succeeded). When you update from the extension, the confirmation about "what gets written
where" follows right after the tool is placed, and approving it replaces the contents between the markers in each of
those files with the new procedure. If you skip it, or if you updated by copying over the files without the
extension, run it by hand.

```bash
python ~/.claude/agent-dashboard/install.py
```

If you keep using an old one, you are told at `start` time and when the server starts. To check whether they match
right now, look at "operating-rules version" in `python diagnose.py`.

> A `.vsix` is a ZIP inside, so a corporate mail gateway may block it.
> If that happens, change the extension before sending (for example `.vsix` → `.txt`) and have the recipient change it back.

### Other commands

```bash
dash ext build       # only build the .vsix (it appears in dist/)
dash ext status      # check whether it is installed and whether the version matches
dash ext uninstall   # remove it
```

For the extension's settings and troubleshooting see [extension/README.md](extension/README.md); for the design rationale see [EXTENSION_PLAN.md](EXTENSION_PLAN.md).

---

## Global Access

This is the route to take if you do not install the extension. It opens the dashboard quickly from any project folder.

### Overview

Once you have run initial setup with the `dash install` command, pressing `Ctrl+Shift+D` opens the dashboard **no matter which project you are working in**.
You do not have to reopen the agent-dashboard folder.

> `Ctrl+Shift+D` is the same key VSCode uses by default for the "Run and Debug" view (`workbench.view.debug`).
> Running `dash install` gives ours priority, and the debug view stops opening on that key.
> If you use the extension, no keybinding is registered, so this conflict does not arise.
>
> **In earlier versions this registration did not take effect.** `install.py` was writing the keybinding to a file VSCode does not read (the extension folder). The destination has been corrected to the proper per-OS user settings file.

### Setup (once)

Run the following in the agent-dashboard directory.

```bash
# Windows
dash.cmd install

# macOS / Linux
chmod +x dash        # first time only
./dash install
```

That configures the following:

- **Keybinding registration**: assigns the dashboard launch action to `Ctrl+Shift+D` in VSCode
- **Reachable from any project**: whichever workspace VSCode has open, the same shortcut starts it

### How to use it

1. **Open any project in VSCode**

2. **Press `Ctrl+Shift+D`**

   The dashboard starts automatically and appears in your browser (or SimpleWebService).

   The first launch takes a few seconds while the server comes up.

3. **Then ask Claude to do work as usual**

   When a subagent is launched, a robot appears on the dashboard.

### How it works

- **The `AGENT_DASHBOARD_HOME` environment variable** remembers where agent-dashboard lives
- **The `open_dashboard.py` script** starts the server and opens the browser
- **A health check** confirms that http://127.0.0.1:3939 responds before opening it

### Troubleshooting

| Problem | What to do |
| --- | --- |
| `Ctrl+Shift+D` does nothing | Open "Keyboard Shortcuts" in the VSCode settings, search for `openDashboard` and check that it is registered |
| The dashboard does not open | Open a terminal and run `dash serve --open` directly |
| The port is in use and it will not start | Specify a different port with the `--port 4000` option: `dash serve --port 4000 --open` |
| I want to open it manually | Run `python <agent-dashboard-path>/open_dashboard.py` in a terminal |

---

## Settings

### Changing where records are saved

By default they are saved in this folder's `missions/`.
If this folder sits somewhere unwritable (`Program Files`, say),
it falls back automatically to the OS's standard user-data area.

To set it explicitly, use an environment variable.

```bash
# Windows (PowerShell)
$env:AGENT_DASHBOARD_HOME = "D:\dashboard-data"

# macOS / Linux
export AGENT_DASHBOARD_HOME=~/dashboard-data
```

### Other environment variables

| Variable | Effect |
| --- | --- |
| `AGENT_DASHBOARD_HOME` | Where records are saved |
| `AGENT_DASHBOARD_PROJECT` | Pin the target project (`--project` wins over it) |
| `AGENT_DASHBOARD_HISTORY_KEEP` | How many past records to keep per project (default 20; `0` keeps none) |
| `PORT` | The server's default port (`--port` wins over it) |
| `CLAUDE_CONFIG_DIR` | Where Claude Code's `CLAUDE.md` lives |
| `CODEX_HOME` | Where Codex CLI's `AGENTS.md` lives |
| `GEMINI_CLI_HOME` | Where Gemini CLI's `GEMINI.md` lives |
| `COPILOT_HOME` | Where GitHub Copilot CLI's instructions live |
| `OPENCODE_CONFIG_DIR` | Where opencode's `AGENTS.md` lives |
| `AGENT_DASHBOARD_AGENTS_FILE` | Where the list of CLIs you added yourself is kept (default: `agents.json` beside the mission records) |

### Display language

English, Japanese, Chinese (Simplified) and Korean are supported. **You get a language that suits your environment without configuring anything.**

- **The screen (dashboard and manual)** — switch it with the language selector at the top right. The first time, it is decided from your browser's language settings; after you pick one it is saved in that browser (independently of the server-side setting).
- **Command output** — `dash lang` prints the current language and **where that decision came from**. Add a language code to change it.

```bash
dash lang        # see the current language and how it was decided
dash lang en     # en / ja / zh / ko
```

The decision runs top to bottom, and **the first one that resolves is used**.

| Order | How it is decided |
| --- | --- |
| 1 | The `AGENT_DASHBOARD_LANG` environment variable |
| 2 | The setting saved with `dash lang <code>` |
| 3 | The `LC_ALL` / `LC_MESSAGES` / `LANG` environment variables |
| 4 | The operating system's display language |
| 5 | English |

The environment variable beats the saved setting, so if `dash lang ja` seems to change nothing, `AGENT_DASHBOARD_LANG` is set (`dash lang` says so).

**Agent names and mission text are never translated.** They are free text that the agent writes with `dash add`, recorded exactly as written and shown on the screen exactly as recorded. The language the agent writes them in comes from the block `install.py` puts into each CLI's instructions file, and that block follows the **command-output** language above — not the screen language. So switching the selector at the top right does not change them. `dash lang <code>` does: it rewrites the block in the new language on the spot, so the language you set is always the language teams are formed in.

```bash
dash lang en          # 1. choose the language (the block is rewritten with it)
                      # 2. restart the agent's session (its instructions file is read at startup)
```

Only blocks that point at *this* copy of the tool are rewritten, so changing the language in a second copy never repoints one of your instructions files somewhere else. If it reports that the operating rules are not written anywhere, that copy has not been set up yet — run `python install.py` once.

Records that already exist stay in the language they were written in. Retranslating them would make the screen show something other than what actually happened.

Any text without a translation comes out in English. **A missing translation never stops a command.**

---

## How it works

```text
Claude launches a subagent / receives a completion report
        │
        ▼
  update_state.py  ──writes──▶  missions/<project>/state.json
                     │          missions/<project>/agents/*.json (grandchildren, self-reported)
                     │
                     └─ on every start, the whole existing record is moved aside
                                    missions/<project>/history/<start time>/
                                          │
                                     read and merged
                                          ▼
                                    server.py  ──▶  /api/state (running teams + the tab list)
                                                  ──▶  /api/run (one past record)
                                                        │
                                                  fetched once a second
                                                        ▼
                                                  public/index.html
```

- `update_state.py` is the only way state gets written. Times, generations and totals are all computed automatically
- Writes go through a temporary file and are swapped in, so a reader never sees half-written JSON
- Grandchild agents write to their own files, so writes never collide
- A project is identified by "folder name + a 6-digit hash of the full path". Folders with the same name never get mixed up

### What it deliberately does not show

Subagents do not report progress while they work. There is no measured percentage to show, so
**it will not invent a plausible-looking number. There is no progress bar at all.**
Whether something is running is conveyed only by the robot's movement and the card's colour.

The exception is "awaiting report" (the amber marker on a unit that has running subordinates), and even that is
**derived from the recorded parent-child relationships**. It is not a fabricated number, but while "the child is
running" is a fact, "the parent is waiting" is an inference, so it is wrong whenever the parent is doing its own
work in parallel.

For the same reason, token counts and tool-use counts that were not in the completion report are shown as `—`.
That is not a fault; it is the correct way to display "unknown". The command post's own model follows the same
rule: leave `--model` out of `start` and it shows as "unknown" too, instead of a guessed or hard-coded value.

### Unit colour shows the model

The colour of the egg-shaped body and arms shows which model is driving that unit: red = Fable, orange =
Opus / Sol, pale green = Haiku / Luna, aqua = Gemini, and white = Sonnet / Terra and everything else.

The eyes, visor, antenna, chest light, mouth, and the state animation (idle / running / awaiting
report / done) are unchanged. That space already carries "state", and layering a second meaning —
"model" — onto it would make the two compete.

A model name the dashboard cannot recognise is left white. Guessing and painting it some other
colour would let the screen lie silently. A unit whose model was never recorded — such as one a
hook registered — is white for the same reason. That is not a fault; it is the correct display.

The state glow (cyan while running, amber while awaiting report, mint when done) sits on top of the
body colour exactly as before, so colour-coding the model never gets in the way of reading state.

### Freezing units with no record when a mission closes

`finish` (and `dash autofinish`) freezes whatever units are running right now with no record into `state.json`,
**before** the mission is marked finished. Only a running mission has its live state read, so without this,
those units would vanish from both the screen and history the moment you close — there would be no trace they
were ever there. What gets frozen stays where it was when you closed, shown **as finished** (whatever elapsed
time, tokens and tool calls had been measured by then stay on the card). It is never counted toward the unit total.

---

## File layout

```text
├─ dash.cmd / dash    launchers (Windows / POSIX)
├─ dash.py            unified entry point
├─ server.py          the serving server
├─ update_state.py    the state-update CLI
├─ install.py         initial setup
├─ dashlib.py         shared logic
├─ i18n.py            display-language switching
├─ i18n_data*.py      translation tables for command output (ja / zh / ko)
├─ build_vsix.py      assembles and installs the VSCode extension
├─ check_i18n.py      checks for missing and unused translations (for development)
├─ README.md          this file (English; ja / zh / ko versions sit alongside)
├─ OPERATION.md       the operating procedure for Claude (English; ja / zh / ko versions sit alongside)
├─ EXTENSION_PLAN.md  the plan and design for the extension
├─ extension/         the VSCode extension source (no build step)
│  ├─ package.json    the extension manifest
│  ├─ package.nls*.json  translations for the manifest
│  ├─ extension.js    the extension itself
│  ├─ i18n.js         display-language switching for the extension
│  ├─ i18n_data.js    the extension's translation table
│  ├─ test_extension.js  a check that runs under plain node
│  └─ media/          icons and the script that generates them
├─ public/
│  ├─ index.html      the dashboard screen
│  ├─ i18n.js         the screen's translation table and switching
│  ├─ manual-i18n.js  the manual's prose (4 languages)
│  └─ manual.html     the manual
├─ dist/              the assembled .vsix (not tracked)
└─ missions/          the records, per project
```

## Requirements

- Python 3.9 or later
- Windows / macOS / Linux
- A modern browser (Chrome / Edge / Firefox)

The robot faces use the CSS `d` property, so mouth shapes do not change in Safari
(everything else looks and behaves the same).

---

## Troubleshooting

### Nothing shows up on the dashboard

**Symptom:** Claude launches subagents but nothing appears on the dashboard

**Things to check:**

1. **Did you run `install.py`?**

   It has to be run once on the target machine:

   ```bash
   cd <where the dashboard lives>
   python install.py
   ```

2. **Run the diagnostic script:**

   ```bash
   python diagnose.py
   ```

   Check that every item is ✓.

3. **Restart the agent's session**

   Changes to its instructions file are read at startup, so a running session does not pick them up.

4. **Check the current directory**

   The dashboard decides the target project from **the directory of the project you are working in**.

   ```bash
   dash projects
   ```

   The project marked `→` is the current target.

5. **Did you install a new AI coding CLI after running setup?**

   Setup only writes operating rules into the CLIs that exist at that moment — this is the one trap in the
   design. Install another CLI afterwards and it has none, so subagents launched from it silently show up
   nowhere on the dashboard. The fix is one line: run `python install.py` again. The tool now watches for
   exactly this: the warning appears when a mission's `start` runs, when the server starts, and
   `python diagnose.py` fails, instead of passing, while any installed CLI is still unwritten.

### I want to run it from a relative path

Relative paths do not work. The reason is that the commands Claude runs execute in **the directory of the project you are working in**.

**Solutions:**

1. **Run `install.py` (recommended)**
2. **Set the `AGENT_DASHBOARD_HOME` environment variable**
3. **Add a global wrapper script to your PATH**

For details on 1 and 2, see the "Getting started" and "Settings" sections above.

### The port is in use and it will not start

```bash
dash serve --port 4000
```

Specify a different port number. The server moves up automatically, but you can also state one explicitly.

### It does not work on another user's machine after distribution

**Make sure `install.py` is run on the receiving machine.**

`install.py` automatically detects:

- The Python command name (`python`, `python3`, `py -3`)
- Where the dashboard is placed (absolute path)
- OS-specific settings

These differ per environment, so settings built on the distributing machine do not work on another one.
