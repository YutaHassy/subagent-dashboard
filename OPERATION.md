# Operating Manual (for Claude)

**English** | [日本語](OPERATION.ja.md) | [中文](OPERATION.zh.md) | [한국어](OPERATION.ko.md)

Every time you launch or finish a subagent, update the state by following this procedure.
**Always write through `update_state.py`. Never edit `state.json` directly.**
Timestamps, generations, the log and the summary totals are all handled by the CLI, so writing them by hand will break them without fail.

## Notation used in this file

Command examples are abbreviated as `dash`. The real thing is the launcher that sits **in the same directory as this file**
(`dash.cmd` on Windows, `./dash` on macOS / Linux). All three of the following do exactly the same thing.

```bash
dash add --id SCOUT-A ...                        # through the launcher
python <this directory>/dash.py add ...          # the launcher's body directly
python <this directory>/update_state.py add      # the CLI directly
```

**The command examples with the full path — the ones to use at run time — are written into Claude's global config `CLAUDE.md`.**
Use those as they are (`dash install` generates them to match this environment).
The actual location of this directory is also printed at the top of `dash projects` output.

## The target project is decided automatically

**The target project is detected automatically from the current directory.**
Whichever project you are working in, run the same commands as they are.
State is stored per project, separated under `missions/<slug>/`.

The slug is "directory name + a 6-digit hash of the full path", so a directory
with the same name in a different location will never get mixed in.

---

## 0. Starting the server (once only, shared by every project)

```bash
dash serve
```

Open the URL it prints in a browser. **You only ever need one server running.**
Whichever project you are working in, it shows up on that single screen.
If the port is taken it moves up automatically, so use the URL printed in the startup log.

**The server decides which team is shown.** There is no switching operation.

| Screen | When |
| --- | --- |
| Idle screen | When there is not a single tab (you have never run `start`, or you deleted every record) |
| A running team | From the moment you run `start` |
| A finished team | It stays on screen after `finish` as well |
| The next team | The next `start` swaps it in, and the previous team leaves the screen |
| **Several teams stacked vertically** | Every team running in parallel is shown at the same time (newest start first) |

What gets shown is "**every running team + the team `missions/.current` points at**". The only thing that
rewrites `.current` is **`start` (and `demo`)** — `done` and `finish` never move it. That is why a
finished screen never jumps to a different project on its own.

On top of that, **a team that finished after a running team had already started** is kept as well. When you
run two in parallel and one of them calls `finish` first, that team is no longer `.current`, so without this
rule it would vanish the moment it finished and nobody could read its completion report. Conversely, if you
are simply working in sequence (starting the next team only after the previous one is over), the previous
team's completion comes before the next start, so that one does leave the screen, exactly as required.

So that records left sitting in `running` are not shown forever, there is a **time window, 3 hours by default**.
A `running` record whose `state.json` is older than that is not shown. The window can be changed with the
environment variable `AGENT_DASHBOARD_ACTIVE_WINDOW` (in seconds). Extend it if you are handling missions
that go for a long time without any report.

**An empty shell that has never once been `start`ed ("(no mission started)") is shown only when there is not a
single other tab to choose.** This is what you get right after `dash reset`, or for a project that exists in
name only. It is a tab that shows nothing when pressed and does not disappear until the next `start`, so left
alone these pile up in the tab strip. Hiding it even when there is nothing else would remove the project's very
existence from the screen, so in that case it is kept (empty shells do not count as "other tabs" for each other;
if they did, having two of them would make both disappear and drop you to the idle screen).
A mission that was just `start`ed and has zero units is `running`, so this rule does not apply to it.

The previous mission's record is moved aside into `missions/<slug>/history/<runId>/`. **Leaving the screen does
not delete it.** Select its tab and you can look through its contents later (list them with `dash history`).

Retention is the most recent 20 runs per project. Anything beyond that moves to `trash/`, oldest first. The
count can be changed with the environment variable `AGENT_DASHBOARD_HISTORY_KEEP` (set it to `0` and nothing is
moved aside — it goes back to the old overwrite behaviour). Setting it to `0` does not clean up a `history/`
that has already accumulated, so that temporarily changing a setting does not send every past record to the trash.

---

## 0.05. Launching from the VSCode extension (recommended; a human does this)

If the human is using VSCode, this takes the fewest steps. Claude does not have to do anything.

```bash
dash ext install     # once only, then reload VSCode
```

After that, pressing the robot icon in the activity bar on the far left opens it in an editor tab.
The "Subagent Dashboard: Open in Tab" entry in the Command Palette and the 🤖 Subagent Dashboard item in
the status bar do the same thing.
To keep it as a narrow strip on the left, set `agentDashboard.sidebarBehavior` to `embed`.

To hand it to other people, run `dash ext package`. Attach the `.vsix` that lands in `dist/` and the setup
guide to an email. The extension bundles the dashboard itself, and on the receiving side it is placed into
`~/.claude/agent-dashboard` (with a confirmation the first time).

**Only the points Claude needs to know:**

- The extension decides whether the server is alive with `GET /api/env`, and only treats it as "our server" when `toolRoot` matches
- The extension picks a free port itself and then starts the server with `dash.py serve --port <number> --no-retry`. **Because it stops the server from moving the port up, the number the extension knows and the actual number always match**
- A server started by the extension stops when VSCode exits. It never touches a server you started with `dash serve` in a terminal
- Therefore, **if Claude has started a server with `dash serve` and the human then opens it from the extension, nothing gets started twice** (the extension reuses the existing one)

For details see `EXTENSION_PLAN.md`; for how to use the extension see `extension/README.md`.

---

## 0.1. Launching from any project (Global Launch)

The route for when the extension is not installed. This is how it works when you launch the dashboard with `Ctrl+Shift+D` from an arbitrary project folder.

### What it is for

- You are working on several projects at once
- Reopening the agent-dashboard folder every time is tedious
- You want quick access from a VSCode keyboard shortcut

### Process flow

```text
The user presses Ctrl+Shift+D
        │
        ▼
  VSCode runs the keybinding
        │
        ▼
  python open_dashboard.py
        │
        ▼
  Detects where agent-dashboard is
  from the environment variable AGENT_DASHBOARD_HOME
        │
        ▼
  Starts python dash.py serve
        │
        ▼
  Connects to http://127.0.0.1:3939
  ↓ health check (waits up to 5 seconds)
        │
        ▼
  Opens it in the browser / SimpleWebService
```

### Technical details

#### Locating the directory

When `install.py` runs, it detects and records the path to agent-dashboard in the following order of priority:

1. **The environment variable `AGENT_DASHBOARD_HOME`** is already set → use that path
2. **Not set in the environment** → detect the directory `install.py` was run from
3. **Embedded in `CLAUDE.md`** → the full path is included in the commands Claude runs automatically

#### Starting the server

`open_dashboard.py` starts the server as follows:

```python
# 1. Settle where agent-dashboard is (search in the order the environment variables are set)
dashboard_home = AGENT_DASHBOARD_HOME or DEFAULT_PATH

# 2. Check whether the server is already running
# try to connect to http://127.0.0.1:3939

if the server does not answer:
    # 3. Start a new server process
    subprocess.Popen([
        "python",
        f"{dashboard_home}/dash.py",
        "serve",
        "--detach"  # start in the background
    ])
    
    # 4. Health check (wait up to 5 seconds)
    for i in range(50):  # 0.1 s x 50 = 5 s
        if http://127.0.0.1:3939 answers:
            break
        sleep(0.1)

# 5. Open the browser
webbrowser.open("http://127.0.0.1:3939")
```

#### Handling a port collision

When several users work on the same machine:

1. User A presses `Ctrl+Shift+D` → starts on port 3939
2. User B presses `Ctrl+Shift+D` → port 3939 is in use
3. User B's server starts on 3940
4. Each user connects to their own configured port

**It is displayed inside the dashboard, so a changed URL causes no trouble.**

#### IDE integration example (VSCode)

What `install.py` registers in `keybindings.json`:

```json
{
  "key": "ctrl+shift+d",
  "command": "agentDashboard.open"
}
```

It calls a command owned by the extension directly. It depends on neither a path nor a terminal, so it does not
break if the dashboard is moved somewhere else. **If the extension is not installed, this key does nothing**
(because the command does not exist).

The write target is the place VSCode actually reads as user settings.

| OS | Location |
| --- | --- |
| Windows | `%APPDATA%\Code\User\keybindings.json` |
| macOS | `~/Library/Application Support/Code/User/keybindings.json` |
| Linux | `$XDG_CONFIG_HOME/Code/User/keybindings.json` (default `~/.config/Code/User/`) |

`Ctrl+Shift+D` is assigned to "Run and Debug" by VSCode's own defaults.
In the extension's `contributes.keybindings`, the priority against that default assignment is
environment-dependent, so it is written to the user settings side, which wins reliably.

> **About versions up to 0.2.4**
> The write target was `~/.vscode/keybindings.json`. That is where extensions live, and VSCode does not read
> keybindings from there. In other words, `Ctrl+Shift+D` was not working at all.
> `install.py` in 0.2.5 cleans up entries it wrote itself in that old location
> (it does not touch entries the user wrote themselves).

---

## 1. When a mission starts

Run this once in the directory of the project you are working in, **before** launching even one subagent.
Everything up to that point is moved aside into `history/<runId>/`, and you start from a state with only the
command post in it (other projects are unaffected). **Because it is moved aside, you can look back at the
previous mission later.** Any grandchild self-report files (`agents/*.json`) left over from the previous mission
move to the archive together with it. They are not carried over because a grandchild whose completion report
never arrived would otherwise stay lined up as "running" in every mission from then on.

If moving the record aside fails, `start` does not stop (it prints a warning and continues), because being
unable to start while a record exists is the worse outcome.

```bash
dash start --title "refactor impact survey"
```

**When you run a second mission at the same time in the same directory, split the record destination with
`--project`.** Running `start` as-is pushes the first mission out while it is still running, and from then on
its record cannot be kept. → "6.1. Running two or more missions at the same time in the same directory"

---

## 2. Immediately after launching a subagent

Run this **immediately** after calling the Agent tool. Not in one batch afterwards — once per launch.

```bash
dash add --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "list every API call site under src/"
```

| Option | If omitted | Notes |
| --- | --- | --- |
| `--id` | **required** | A short identifier such as `SCOUT-A` or `A-1`. Appears in the log and on the card |
| `--name` | same as id | The name shown large on the screen |
| `--parent` | `COMMAND` | The parent's ID. If you had an agent spawn a grandchild, give the parent agent's ID |
| `--model` | empty (the screen shows "unknown") | The model ID you actually used |
| `--mission` | empty | The task. Shown on the card in two lines |
| `--status` | `running` | Use `standby` if you are only lining it up, waiting to be deployed |
| `--project` | the current directory | Specify only when you want to target a different project |

**Write the free text in English** (`--title` / `--name` / `--mission` / `--headline`). It is recorded exactly as you
write it and shown on the screen exactly as recorded — nothing is translated afterwards. Follow the language of this
manual, not the language of the conversation. To change which language that is, run `dash lang <en|ja|zh|ko>` and then
`python install.py` to rewrite the block in `CLAUDE.md`; records that already exist are left as they were written.

The generation (which column it sits in) is computed automatically from `--parent`, so do not specify it.
**"awaiting report" is also derived automatically from `--parent`**, so there is no need to declare that the
command post has started waiting (specifying `--parent` correctly is exactly what makes "awaiting report" accurate).

**If you launched several at once, run `add` as many times as there are units.** There is no way to batch them into one call.

---

## 3. When a completion report arrives

```bash
dash done --id SCOUT-A --sec 42 --tokens 18400 --tools 11 --headline "identified 23 call sites across 7 files"
```

| Option | If omitted | Notes |
| --- | --- | --- |
| `--id` | **required** | |
| `--sec` | actual seconds elapsed since `startedAt` | If the report states a duration, pass it. If not, omit it |
| `--tokens` | `null` → the screen shows "—" | **If it is not in the report, you must omit it** |
| `--tools` | `null` → the screen shows "—" | **If it is not in the report, you must omit it** |
| `--headline` | empty | A one-line summary of the result. Shown in green at the bottom of the card |

### The absolute rule about measured values

**A number that was not included in the completion report must be omitted, not estimated.** Omitting it puts
`null` in, and the screen shows "—". That is the correct state, not a gap to be filled in.
Writing `--tokens 20000` because "it was probably around 20k tokens" destroys the purpose of this dashboard
(seeing what actually happened), so never do it.

---

## 4. When everyone has finished

```bash
dash finish --headline "impact scoped; the change set is settled at 12 files"
```

- The phase becomes "Done" and a summary appears. **The screen stays in this finished state** (until the next `start`)
- The unit count, total tokens and elapsed time are totalled by the CLI (you do not need to pass anything other than `--headline`)
- The total token count is the sum over the units you passed `--tokens` for. If no unit has a figure, it shows "—"
- A unit still sitting in `standby` is treated as finished, as "ended without ever deploying"

### The watch for a forgotten close

Forgetting to run `finish` **breaks nothing and stops nothing**. That is why you cannot notice it.
Left alone, the screen keeps saying "Running", the next `start` flushes it into history still marked running,
and it stays there forever as an "Unfinished" record (**there is no way to mark it finished afterwards**).

A forgotten close always happens at the moment your attention shifts to writing up the report, right after you
marked the last unit `done`, so there are four places — including that one — where you are told about it.
**Every one of them only tells you; none of them fixes it.** Writing `finishedAt` after the fact would make it
no longer a measured value.

| Where | When it appears | What you get |
| --- | --- | --- |
| `done` | Right after you mark the last unit done | `★ That is all N units back home. …` plus a `finish` line you can paste as-is |
| `status` | The whole time the close is missing | The phase reads "Running (**all units back, not closed**)" / the time elapsed since the last return |
| `start` | When you start the next one with the close still missing | `⚠️ All N units of the archived "…" were back, but finish was never run.` |
| Screen | The whole time the close is missing | The mission bar and the tab badge turn amber and blink "**All back · not closed**" / "**Open**" |

Something is judged to be a "forgotten close" only when all of the following hold.

- The mission is `running` (`done` means already closed, `standby` means it has not started yet)
- There is **at least one** subagent (with zero, it was "only started" and is not at the stage of being closed)
- **Every** one of those subagents is `done` (if even one is still running, you are still waiting)

The command post is not counted. Staying `running` until you run `finish` is its correct state, so counting it
would mean the conditions could never all hold and the warning would never appear even once.

If you `start` the next one while units have not returned, that is not a "forgotten close" but an
**abandonment mid-flight**, so `start` words it differently: `⚠️ …ended while still running (there are units
that never returned)`. This also happens without fail when you try to run two missions in parallel in the same
directory, so in that case it goes on to give the countermeasure (splitting the record destination with
`--project`). → "6.1. Running two or more missions at the same time in the same directory"

---

## 5. Helper commands

Add a single line of commentary. Use it when you want to leave a decision or a change of direction in the log.

```bash
dash log --who "Command" --text "decided to re-run Scout B"
```

Show the current project's state as a table. For checking that your writes are landing.
The absolute path grandchildren write to is also printed at the end.

```bash
dash status
```

List the registered projects. The `→` marks the one the current directory targets.

```bash
dash projects
```

Fill in data for testing the display (standby, running, awaiting report, done, grandchildren and
missing measured values all appear). Use this while adjusting the look.

```bash
dash demo
```

Reset. Adding `--purge` also deletes the grandchild self-report files. It affects the current project only.
`reset` keeps `missions/<slug>/`. If you `reset` the team currently on screen, you go straight
**back to the idle screen** (`.current` is not moved, so it does not jump to another project).
All that remains after `reset` is the "(no mission started)" shell, so **if there is any other tab to choose,
that tab is not shown on the screen** (see the end of section 0). If past records exist, their tabs remain.

```bash
dash reset
dash reset --purge
```

Delete the records themselves. By default it only moves them to `trash/<slug>-<timestamp>/`, so you can recover
by moving the folder back where it was. It deletes for good only when you add `--force`.
If you delete the team currently on screen, you get the idle screen until the next `start`.

```bash
dash remove              # asks for confirmation interactively
dash remove --yes        # skips the confirmation (--yes is mandatory in non-interactive environments)
dash remove --yes --force  # deletes for good instead of moving to the trash
```

---

## 5.1. Deleting records

Every `start` adds one tab, so left alone they pile up. There are three ways to delete them.

| Operation | What happens | Can it be undone |
| --- | --- | --- |
| The "✕" on a tab on screen | Moves that one tab to `trash/` | Recoverable by moving the folder back out of the trash |
| "Delete finished records" on screen | Moves every tab marked "Done" to `trash/` in one go | Same as above |
| `dash remove` | Moves all of `missions/<slug>/` (including `history/`) to `trash/<slug>-<timestamp>/` | Same as above |
| `dash remove --yes --force` | Deletes for good | Cannot be undone |

- Past records can be listed with `dash history`. The list of projects is `dash projects`.
- **What can be deleted from the screen is "past records" and "the current mission once finished".** A running
  or standby mission gets no "✕", and the server refuses the request even if one arrives.
- The current mission (`state.json`) is moved into `history/` only when you run the next `start` in the same
  project. **A one-off mission stays in the current slot even after it finishes**, so it is made deletable from
  the screen as it is.
- If no past record would be left for that project, the project itself is moved to `trash/` rather than leaving
  an empty folder behind (the result is the same as `dash remove`).
- Deleting the project currently on screen with `dash remove` also clears `.current`, so you get the idle screen
  until the next `start`.
- Deletion is accepted over `POST` only. `GET` returns 405 and never deletes anything.
- There is no permanent-delete route from the screen. Sending `permanent` is rejected with 400.
  An operation that cannot be undone is only possible from the CLI (`--force`).

---

## 6. Targeting a different project

Pass the slug to `--project` (a prefix is enough).

```bash
dash status --project learning
dash done --id SCOUT-A --project learning --headline "..."
```

If the prefix matches two or more, it is an error, so check the correct slug with `dash projects`.
It can also be given with the environment variable `AGENT_DASHBOARD_PROJECT` (`--project` takes priority).

If you pass a name that does not exist, a new project is created under that name.
In other words you can also create missions unrelated to any directory, such as `--project manual-test`.

---

## 6.1. Running two or more missions at the same time in the same directory (required)

There is only **one record destination per project (= per working directory)**.
Run a second `start` in the same directory and the first one is **pushed out into history while still running**.
A record that has been pushed out can no longer be written to, so the first mission's `done` is rejected with
"not there", and nothing more is recorded for it. **There is also no way to mark it finished afterwards**
(by design, values that were not measured are never written). Splitting the record destination in advance is
the only countermeasure.

```bash
# When running in parallel in the same directory, give start a unique name with --project to split them
# (pass a name that does not exist and a new project is created under that name)
dash start --project PAVS_ER-issue51 --title "issue51 impact survey"

# Put the same --project on that mission's add / done / finish as well — all of them
dash add --project PAVS_ER-issue51 --id SCOUT-A --name "Scout A" --model claude-sonnet-5 --mission "..."
dash done --project PAVS_ER-issue51 --id SCOUT-A --headline "..."
dash finish --project PAVS_ER-issue51 --headline "..."
```

- **Put `--project` on all four commands.** Forget it on even one and that command alone writes to the record on
  the current-directory side — the other team — and the two records get mixed together.
- Missions running in different directories already have different record destinations, so `--project` is not needed.
- Each split is treated as an independent project. Two tabs line up on the screen, and running teams are shown at the same time.
- It can also be given with the environment variable `AGENT_DASHBOARD_PROJECT` (`--project` takes priority).

When a push-out does happen, you are told in two places. **Both only tell you; neither fixes it.**

| Where | What you get |
| --- | --- |
| `start` | `⚠️ The archived "…" ended while still running`, followed by the procedure for splitting with `--project` |
| `done` | "not in the current mission '…' / the same ID is in the recent history '…'" plus a warning that running `add` here would mix the records together |

The guidance from `done` **words it differently depending on whether you "have not run add yet" or "were pushed out"**.
If the same ID is in the last 5 history entries, it is treated as a push-out (`update_state.find_in_history`).
If it did not distinguish and only said "run add first", the person who was pushed out would do exactly that and
**mix the first mission's unit into the team that pushed them out**. That is why it is worded differently.

---

## 7. Grandchild agents (when a subagent spawns children of its own)

To avoid write conflicts, a grandchild **writes its own entry into its own dedicated file**.
The write target differs per project, so **always give the subagent the absolute path**.
The path is printed at the end of `dash status`.

Include the following in the instructions you give the subagent (replace `<grandchild directory>` with the real path).

> When you launch a child agent, write out the following JSON to
> `<grandchild directory>/<child's ID>.json`.
> One file per unit. Never touch any other file.
>
> ```json
> {
>   "id": "A-1-x",
>   "name": "Scan A-1-x",
>   "parentId": "A-1",
>   "model": "claude-haiku-4-5",
>   "mission": "remove duplicates from the classification results",
>   "status": "running",
>   "startedAt": "2026-07-30T10:30:00+09:00",
>   "log": [{ "at": "2026-07-30T10:30:00+09:00", "who": "Analysis A-1", "text": "Scan A-1-x born" }]
> }
> ```
>
> When it finishes, overwrite the same file in the following form.
> Leave any value you could not measure as `null` (do not fill it in by guessing).
>
> ```json
> {
>   "id": "A-1-x",
>   "name": "Scan A-1-x",
>   "parentId": "A-1",
>   "model": "claude-haiku-4-5",
>   "mission": "remove duplicates from the classification results",
>   "status": "done",
>   "startedAt": "2026-07-30T10:30:00+09:00",
>   "finishedAt": "2026-07-30T10:30:22+09:00",
>   "result": { "elapsedSec": 22, "tokens": null, "toolCalls": null, "headline": "removed 3 duplicates" },
>   "log": [{ "at": "2026-07-30T10:30:22+09:00", "who": "Scan A-1-x", "text": "back home — removed 3 duplicates" }]
> }
> ```

The server merges `state.json` and `agents/*.json` automatically, so nothing has to be configured on the screen side.
A grandchild's card gets a "self-reported" badge.

- `generation` does not need to be written (it is recomputed from `parentId`)
- If an ID collides with one in `state.json`, the `state.json` side wins
- A file with broken JSON is ignored and a warning appears at the bottom right of the screen (the other units keep being displayed)

---

## 8. Structural limits (know these)

| Item | Reality |
| --- | --- |
| Update timing | Only two points: "right after launch" and "on the completion report". Silence while it runs |
| Progress % | Not shown, because there is no source of measured progress. There is no progress bar either (whether it is running shows in the robot's motion and the card's colour) |
| Awaiting report | Derived on the reading side as "a running parent that has running children" and shown in amber. It is not written into `state.json` and there is no command to report it. If a parent is doing its own work in parallel with its children, it diverges from reality |
| Elapsed time while running | The screen counts up every second from `startedAt` |
| Token count and tool calls | Measured values only when they were included in the completion report. Otherwise "—" |
| Screen refresh | Fetches `/api/state` once a second with caching disabled, and redraws only when the content changed |
| Deciding which team is shown | Decided on the server side alone. The browser remembers nothing, so the same team appears on whichever machine you open it |
| Parallel operation | Every running team is stacked vertically and shown at the same time. The order is newest start first |
| Number of record destinations | Exactly one per project (= per working directory). Run a second `start` in the same directory and the first is pushed out into history while still running, and can no longer be written to. To run in parallel, split with `--project` (→ 6.1) |
| Versions of the tool and of the operating rules | They go stale separately. Updating the tool leaves the operating rules in `CLAUDE.md` stale until you run `install.py` again. If they diverge, you are told at `start` and at server startup (you can also check it with "operating rules version" in `diagnose.py`) |
| Teams being swapped out | A team that has disappeared from `teams` in `/api/state` has its shell cleaned up on the spot |
| Running start again in the same folder | The slug does not change, so it watches for a change in `mission.startedAt` and throws away the previous mission's log |
| When the connection drops | It keeps the last display and the connection indicator at the top right turns red |
| Layout of the family tree | A parent is placed at the vertical centre of the children it spawned. The command post sits at the vertical centre of the whole tree. It is centred vertically only when the tree fits on screen; when it overflows it is aligned to the top |
| How layout is applied | Moved with `.agent`'s `top` only. The DOM is never reordered (moving an element resets the CSS animations underneath it to 0). `transform` is not used either (it collides with the birth animation) |

---

## 9. Files and environment

The contents of this directory. Every path is resolved at run time, so it works wherever you put it.

```text
├─ dash.cmd / dash    launcher (Windows / POSIX)
├─ dash.py            unified entry point
├─ server.py          serving server (shared by all projects; start only one)
├─ update_state.py    state update CLI (the only way in to the state)
├─ install.py         first-time setup (writes into CLAUDE.md)
├─ dashlib.py         shared logic (path resolution, project identification, merging, formatting)
├─ build_vsix.py      builds and installs the VSCode extension (dash ext ...)
├─ test_tabs.py       checks the tab list behaviour. Runs with python test_tabs.py (touches no records)
├─ README.md          setup guide (for humans)
├─ OPERATION.md       this manual
├─ EXTENSION_PLAN.md  the plan and design of the extension work (what was verified and what was decided)
├─ extension/         source of the VSCode extension. No build step, no node_modules
│  ├─ package.json    extension manifest (version, commands and settings are authoritative here)
│  ├─ extension.js    the extension itself (plain CommonJS)
│  ├─ test_extension.js  behaviour check. Runs with node extension/test_extension.js
│  └─ media/          icons and the script that generates them
├─ public/
│  ├─ index.html      the dashboard screen
│  └─ manual.html     the user manual (for humans; read through the server)
├─ dist/              the built .vsix. Not tracked, since it can be rebuilt
├─ missions/          per-project records (the storage location can be changed with an environment variable)
│  └─ .current        the slug of the team currently on screen. Only start and demo rewrite it
└─ trash/             where deleted projects go. To restore one, move the folder back into missions/
```

### Environment variables

| Variable | Effect |
| --- | --- |
| `AGENT_DASHBOARD_HOME` | Changes where records are stored (default is this directory; if it is not writable, the OS's user data area) |
| `AGENT_DASHBOARD_PROJECT` | Fixes the target project (`--project` takes priority) |
| `PORT` | The server's default port (`--port` takes priority) |
| `CLAUDE_CONFIG_DIR` | Where `install.py` writes `CLAUDE.md` |
| `AGENT_DASHBOARD_LANG` | The language of the output (`en` / `ja` / `zh` / `ko`). Takes priority over the saved setting |

### Display language

Command output supports `en` / `ja` / `zh` / `ko`. It is decided in the order below, and the first one that settles it wins.

1. The environment variable `AGENT_DASHBOARD_LANG`
2. The setting saved with `dash lang <code>` (`<record storage location>/lang`)
3. The environment variables `LC_ALL` / `LC_MESSAGES` / `LANG`
4. The OS display language
5. English

```bash
python <tool location>/update_state.py lang        # see the current language and how it was decided
python <tool location>/update_state.py lang en     # change it
```

The language of the screen (the dashboard and the user manual) is decided separately **on the browser side**
(the selector at the top right; the first time it is auto-detected from the browser's language settings, and
after that it is saved in that browser). **Changing the command language does not change the screen.** The reverse is also true.

A sentence with no translation comes out in English. A missing translation never stops a command.

### API

| Endpoint | What it returns |
| --- | --- |
| `/api/state` | The state of the teams to show (`teams`) plus the tab list (`tabs`) |
| `/api/run?slug=<slug>&runId=<runId>` | The complete state of one past run. Omit `runId` for the one in progress. Taken as a query because the slug can contain non-ASCII characters |
| `/api/projects` | The project list only |
| `/api/env` | The runtime environment (various paths, platform, Python version) |
| `POST /api/project/delete` | Deletes a project's records (moves them to `trash/` by default). Body `{"slug": "..."}`, `Content-Type: application/json` required |
| `POST /api/history/delete` | Moves a mission's record to `trash/`. Body `{"runs": [{"slug","runId"}, ...]}` or `{"phase": "done"}`. Passing `null` for `runId` targets the current mission (`state.json`), but only a finished one can be deleted |

`tabs` is fetched once a second, so it is kept **a light list** (`runId` / `title` / `phase` /
`startedAt` / `finishedAt` / `projectName` / `agentCount` / `doneCount` / `isCurrent`).
It does not go as far as opening the grandchildren's self-reports. Only one selected entry needs its contents,
and that is fetched with `/api/run`.

A shell that has never once been `start`ed (`runId` is `null`, `phase` is `standby`, zero units) is not included
in `tabs` when there are other tabs to return. **At that point the same project is also removed from `teams`.**
Every second the screen side does both "clean up teams that are not in `tabs`" and "create teams that are in
`teams`", so if the two disagree it endlessly creates and destroys the shell for the same team.

`doneCount` exists only to surface a forgotten close (`phase` still `running` while every unit is `done`) on the
tab, and **when it could not be counted it returns `null`, not `0`**. For past records (`history/`) it is always
`null`. `0` would carry the meaning "not one unit has returned", so if it could not be told apart from "unknown"
the screen would be lying.

If even one invalid `slug` / `runId` is mixed into `runs`, it returns **400 and deletes nothing**.
A `..` slipping in is not a "partial failure" but an error in the request itself, so it does not delete halfway
and leave things in a half-finished state. A record that merely does not exist is put into `failed` and the rest proceeds.

Destructive operations are accepted over `POST` only. A `GET` to `/api/project/*` returns `405` with `Allow: POST`
(so that records are not deleted by a browser prefetch or a link pressed by accident).

### Dependencies

No external library is used at all. `http.server` / `json` / `pathlib` / `argparse` /
`datetime` / `hashlib` / `unicodedata` / `webbrowser` and so on are all Python standard library.
The HTML under `public/` is self-contained too, with zero CDN references. It runs on Python 3.9 and later, on Windows / macOS / Linux.

The VSCode extension follows the same policy. Building the `.vsix` is done with `zipfile` alone, so neither npm
nor `vsce` is needed, and the extension itself uses only `require('vscode')` and Node built-ins (no `node_modules`).
The one exception is `extension/media/make_icons.py`, which needs Pillow only when redrawing the artwork.
It plays no part in running the tool, so the "zero external libraries" above still holds.
