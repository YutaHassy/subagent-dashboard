# Subagent Dashboard

[English](README.md) | [日本語](README.ja.md) | **中文** | [한국어](README.ko.md)

这是一个本地应用，用于实时查看 Claude Code 的子代理现在有几个在运行、哪些已经结束、
各自用掉了多少时间和多少 Token。通过机器人的表情和动作即可看出状态。

- **无外部库** — 只用 Python 标准库就能运行。不需要 `pip install`
- **不需要联网** — 零 CDN 引用。在离线环境下也能运行
- **不挑电脑** — Windows / macOS / Linux，Python 3.9 以上都能运行
- **不挑放置位置** — 整个文件夹复制过去，放在哪里都能运行（放在 U 盘里也可以）

---

## 安装（两步）

### 1. 初始设置（向导式）

把文件夹放到你喜欢的位置，然后运行安装工具。

#### 推荐：完整安装（初始设置 + VSCode 扩展）

**在 Windows 上：**
- 双击 `setup-full.bat`

**在 macOS / Linux 上：**
- 双击 `setup-full.sh`

**只要这一步，以下内容就全部完成：**
1. Python 环境的检测
2. 初始设置（向所有已安装的 AI 编程工具写入运行规则）
3. VSCode 扩展的安装

#### 备选：只做初始设置（不使用 VSCode 时）

**在 Windows 上：**
- 双击 `setup.bat`

**在 macOS / Linux 上：**
- 双击 `setup.sh`

#### 从命令行执行时

```bash
# 完整安装（Windows）
dash.cmd ext install

# 只做初始设置（Windows）
dash.cmd install

# macOS / Linux
./dash install
```

**向导式的安装程序会启动，用 4 个步骤自动完成安装：**

1. **环境检查** — 确认 Python 版本、文件构成、写入权限
2. **环境的自动检测** — 检测 Python 命令、路径、配置文件的位置
3. **写入运行规则** — 向每个已安装的 AI 编程工具的指定位置写入规则（如 `~/.claude/CLAUDE.md`、`~/.codex/AGENTS.md` 等），同时更新 VSCode 快捷键绑定
4. **安装完成** — 说明启动方法和后续步骤

所有项目都打上 ✓ 就完成了。

- 会检测出本文件夹的实际位置并嵌入进去，因此**在别的电脑上也用同样的命令就够了**
- 只改写标记（marker）括起来的范围，因此不会破坏各工具的配置文件中已有的内容
- 想先确认将要写入的内容时用 `dash install --print`
- 想撤销时用 `python install.py --uninstall`

**🚀 自动安装功能：**

首次运行时（例如启动服务器时）如果检测到尚未设置，**会自动引导你进行安装。**
- 在交互式环境（在终端里直接运行）下会弹出确认对话框
- 在非交互式环境（由 Claude 执行）下会显示警告并继续
- 使用 VSCode 扩展时，会在本体放置完成后自动运行

**🔍 运行确认（诊断工具）：**

想确认是否已正确设置时，请运行诊断脚本：

```bash
python diagnose.py
```

它会以向导形式检查 6 个项目，全部变成 ✓ 就是成功了。
如果发现问题，会带编号地显示原因和解决办法。

**📋 支持的 AI 编程工具：**

下表列出了本工具可以为其写入运行规则的 AI 编程工具。它会自动检测机器上已安装的工具，并为每个工具在其指定的位置写入运行规则。

| 工具 | 规则写入位置 |
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

**不在上表中的工具未必不支持。** 如下所述，你可以注册任意工具。

**Cursor** 和 **Aider** 的情况：这两个工具没有自动读取的全局规则文件，但可以用 `--agent-file` 选项为项目级别的规则文件提供支持。

**🔧 支持其他工具或自定义位置：**

如果你要支持不在上表中的工具，或者需要更改某个工具的规则位置，可以用以下命令：

```bash
# 列出所有已知的工具及其写入状态
python install.py --list-agents

# 为某个特定工具写入（如果已安装）
python install.py --agent codex

# 为所有已知的工具写入（无论是否已安装）
python install.py --agent all

# 为不在已知列表中的工具写入（指定文件路径）
python install.py --agent-file /path/to/your/tool/rules.md
```

用 `--agent-file` 指定的文件会被永久记录在 `agents.json` 中（与任务记录放在同一位置），之后会自动包含在 `--list-agents` 的列表里，每次运行 `install.py` 时都会更新，卸载时也会清理。

`agents.json` 也可以手工编辑。每个条目包含以下字段：
- `key` - 用于 `--agent` 命令的短标识符
- `label` - 显示名称
- `home_env` - 指向工具位置的环境变量名（可以为空）
- `home` - 工具的主目录路径（可以用 `~` 开头）
- `file` - 规则文件名（可能包含子目录）

如果 `agents.json` 中某条的 `key` 与内置工具相同，会覆盖内置的配置，这样可以在工具改变规则位置时迅速调整，而无需等待工具更新。

> **⚠️ 初始设置之后安装新工具时**
>
> 初始设置时只会向当时已安装的工具写入规则。如果之后又安装了新的 AI 编程工具，那个工具会没有规则，导致从它启动的子代理在面板上什么都显示不了。
>
> 解决办法很简单 — 只需再运行一次 `python install.py`：
>
> ```bash
> python install.py
> ```
>
> 本工具会自动检测这种情况：当任务 `start` 时、服务器启动时，或者运行 `python diagnose.py` 时，如果发现某个已安装的工具还没有规则，就会显示警告。

### 2. 打开画面

```bash
# Windows
dash.cmd serve --open

# macOS / Linux
./dash serve --open
```

浏览器会打开。请让这个窗口一直保持启动状态。
服务器**只要启动一个，不管你在哪个项目里工作，都会显示在这个画面上。**

之后照常请 Claude 做工作就行了。子代理一被启动，机器人就会当场出现。

画面上映出的是**当前正在运行的小队**（如果有多个项目同时在跑，它们会全部排列在标签页里）。
工作结束之后也会原样留着，下次在同一个项目里开始工作时，之前的记录不会消失，
而是作为标签页的「过去的记录」保留下来。什么都没有运行时是待机画面。

---

## 使用方法

**使用手册随应用一同附带。** 请启动服务器后打开下面的地址。

```text
http://127.0.0.1:3939/manual.html
```

也可以从面板画面右上角的「?」按钮打开。
里面配图写明了机器人表情的含义、卡片的读法，以及遇到麻烦时的处理办法。

### 常用命令

`dash` 在 Windows 上是 `dash.cmd`，在 macOS / Linux 上是 `./dash`。

| 命令 | 内容 |
| --- | --- |
| `dash serve --open` | 启动画面的服务器并打开浏览器（用 `Ctrl+C` 停止） |
| `dash serve --port 4000` | 指定端口启动 |
| `dash projects` | 已登记项目的一览。带 `→` 的是当前文件夹对应的对象 |
| `dash status` | 显示当前项目的内容 |
| `dash demo` | 放入用于确认显示效果的示例数据 |
| `dash reset` | 把当前项目清空 |
| `dash history` | 列出本项目过去的任务（`history/`） |
| `dash install` | 初始设置（移到别的电脑上时执行） |

只输入 `dash` 执行会显示一览。各命令可以用 `dash <命令> --help` 查看详情。

改写状态的命令（`start` / `add` / `done` / `finish`）通常由 Claude 自动执行，
不需要你手动输入。

### 在同一个文件夹里同时跑两条时

任务的记录位置是每个项目（＝工作文件夹）一个。在同一个文件夹里 `start` 第二条时，
第一条会保持在运行中的状态被挤进历史里，此后就无法再向那第一条写入记录了
（事后也无法改成完成）。要并行时，请用 `--project` 把记录位置分开。

```bash
dash start  --project issue51 --title "issue51 的调查" --model claude-opus-5
dash add    --project issue51 --id SCOUT-A --name "侦察A" --model claude-sonnet-5 --mission "..."
dash done   --project issue51 --id SCOUT-A --headline "..."
dash finish --project issue51 --headline "..."
```

`--project` 要加在全部 4 条命令上。哪怕只有一条忘了加，那一条命令就会写到当前文件夹一侧
＝写到另一支小队里去。这套步骤会被写进各工具的运行规则中，因此各编程工具也会按同样的规则行动。

### 查看过去的记录

即使在同一个项目里重新 `start`，此前的记录也不会消失。
它们会被整体转移到 `missions/<项目>/history/<开始时刻>/`，从画面的标签栏里选择就能回看
（过去的记录会以经过时间停住的状态显示）。

保留件数是每个项目最近 20 件（默认），超出的部分会从旧的开始移动到 `trash/`
（`trash/` 只要把文件夹放回去就能恢复）。一览也可以用命令确认。

```bash
dash history
```

---

## 作为 VSCode 扩展打开（推荐）

可以在 VSCode 里开出 Subagent Dashboard 的标签页。不用切换到浏览器，服务器的启动也由扩展来照料。

### 装入（只需一次）

```bash
# Windows
dash.cmd ext install

# macOS / Linux
./dash ext install
```

之后请重新加载 VSCode（`Ctrl+Shift+P` → Reload Window）。

既不需要 npm 也不需要 `vsce`。`.vsix` 是只用 Python 标准库组装出来，再交给 `code --install-extension` 的。

### 使用

按下最左边活动栏里新增的**机器人图标**，编辑器的标签页里就会出现 Subagent Dashboard。
想把它细长地摆在左侧时，把设置 `agentDashboard.sidebarBehavior` 改成 `embed`，它就会出现在侧边栏里。

在命令面板（`Ctrl+Shift+P`）里输入「Subagent Dashboard」也是一样的。

| 命令 | 做什么 |
|---|---|
| Subagent Dashboard: 在标签页中打开 | 在编辑器的标签页里开出 Subagent Dashboard |
| Subagent Dashboard: 在浏览器中打开 | 用 OS 的默认浏览器打开 |
| Subagent Dashboard: 重启服务器 | 停止这个扩展启动的服务器并重新建立 |
| Subagent Dashboard: 停止服务器 | 停止这个扩展启动的服务器 |
| Subagent Dashboard: 放置／更新本体 | 把随附的本体放到目标位置 |
| Subagent Dashboard: 执行初始设置 | 确认之后执行初始设置（`install.py`） |
| Subagent Dashboard: 重置初始设置的标志 | 清除「已经做完了」的记录，下次再次执行 |
| Subagent Dashboard: 显示日志 | 查看启动的经过和 Python 一侧的输出 |

服务器没在运行时，扩展会把它启动起来。已经在运行时会直接复用，因此进程不会越积越多。端口被占用时会顺延到下一个号码，并用那个号码打开画面。

在外面（例如终端的 `dash serve`）立起来的服务器，扩展只会复用，不会擅自停掉。

### 分发给别人

扩展里**完整地装着面板本体**。就算对方的 PC 上什么都没有，光靠这一个也能跑起来。

```bash
dash.cmd ext package
```

`dist/` 里会输出 2 个文件。**请把它们添加到邮件附件里。**

- `agent-dashboard-<版本>.vsix` — 扩展本体（约 0.1MB）
- `インストール手順.txt` — 可以直接交给对方的操作说明书

收到的人只用 VSCode 的画面就能装上（扩展面板 → `…` →「从 VSIX 安装...」）。
不需要 `code` 命令。

首次按下图标时会弹出「要把本体放在这里」的确认，同意之后就会展开到 `~/.claude/agent-dashboard`。**不会在随附物所在的位置运行。** 因为扩展文件夹的名字里带着版本号，一更新整个文件夹就会变，把记录放在那里就会消失。

分发更新版时也可以用同样的步骤覆盖。不会碰 `missions/`（工作的记录）。

**更新的时候，各工具的运行规则也会重新分发一次。** 因为即使把本体更新了，各工具读的
规则仍会停留在旧版（初始设置一旦成功过一次，就不会再自动跑第二次）。从扩展进行
更新时，放置本体之后会接着弹出「把什么写到哪里」的确认，同意之后各规则文件就会
替换成新的内容。如果你跳过了，或者没有用扩展而是用覆盖复制的方式更新的，请手动执行。

```bash
python ~/.claude/agent-dashboard/install.py
```

一直用着旧的，会在 `start` 时和服务器启动时收到提示。当前是否已经一致，可以在
`python diagnose.py` 的「运行规则的版本」中确认。

> `.vsix` 的内容其实是 ZIP，因此有可能被公司内部的邮件关卡拦下来。
> 那种情况下请改掉扩展名再发（例如 `.vsix` → `.txt`），让收到的人改回来。

### 其他命令

```bash
dash ext build       # 只制作 .vsix（输出到 dist/）
dash ext status      # 确认是否装上了、版本是否一致
dash ext uninstall   # 卸载
```

扩展的设置与疑难解答请看 [extension/README.md](extension/README.md)，设计的来龙去脉请看 [EXTENSION_PLAN.md](EXTENSION_PLAN.md)。

---

## 全局访问（Global Access）

这是不安装扩展时的入口。可以从任意项目文件夹快速打开面板。

### 概要

用 `dash install` 命令做完初始设置后，**不管你在哪个项目里工作**，只要按 `Ctrl+Shift+D` 就能打开面板。
不需要重新打开 agent-dashboard 文件夹。

> `Ctrl+Shift+D` 和 VSCode 标准的「运行和调试」视图（`workbench.view.debug`）是同一个键。
> 执行 `dash install` 之后这边会优先，调试视图就不再用那个键打开了。
> 使用扩展时不会注册快捷键绑定，因此不会发生这个冲突。
>
> **在以前的版本里，这个注册有过不生效的缺陷。** 那是因为 `install.py` 把快捷键绑定写进了 VSCode 不会读取的文件（扩展的存放处）。现在已经把写入位置改成了各 OS 正确的用户配置文件。

### 安装（只需一次）

在 agent-dashboard 的目录下执行下面的命令。

```bash
# Windows
dash.cmd install

# macOS / Linux
chmod +x dash        # 只需首次
./dash install
```

这样就会设置好以下内容：

- **快捷键绑定的注册**：在 VSCode 里把面板的启动动作分配给 `Ctrl+Shift+D`
- **可以从任意项目访问**：不管 VSCode 打开的是哪个工作区，都能用同一个快捷键启动

### 使用方法

1. **用 VSCode 打开任意项目**

2. **按下 `Ctrl+Shift+D`**

   面板会自动启动，并显示在浏览器（或 SimpleWebService）里。

   首次启动时，服务器启动会花上几秒钟。

3. **之后照常请 Claude 做工作**

   子代理一被启动，机器人就会出现在面板上。

### 机制

- 用**环境变量 `AGENT_DASHBOARD_HOME`** 记住 agent-dashboard 的位置
- **`open_dashboard.py` 脚本**启动服务器并打开浏览器
- 用**健康检查**确认 http://127.0.0.1:3939 有响应之后再打开

### 疑难解答

| 问题 | 处理 |
| --- | --- |
| `Ctrl+Shift+D` 不起作用 | 请在 VSCode 的设置里打开「键盘快捷方式」，搜索 `openDashboard` 确认注册情况 |
| 面板打不开 | 请打开终端直接执行 `dash serve --open` |
| 端口被占用启动不了 | 请用 `--port 4000` 选项指定别的端口：`dash serve --port 4000 --open` |
| 想手动打开 | 请在终端执行 `python <agent-dashboard-path>/open_dashboard.py` |

---

## 设置

### 更改记录的保存位置

默认保存在本文件夹的 `missions/` 里。
如果本文件夹位于不可写入的位置（例如 `Program Files`），
会自动回退到 OS 标准的用户数据区域。

想要明确指定时使用环境变量。

```bash
# Windows (PowerShell)
$env:AGENT_DASHBOARD_HOME = "D:\dashboard-data"

# macOS / Linux
export AGENT_DASHBOARD_HOME=~/dashboard-data
```

### 其他环境变量

| 变量 | 效果 |
| --- | --- |
| `AGENT_DASHBOARD_HOME` | 记录的保存位置 |
| `AGENT_DASHBOARD_PROJECT` | 固定对象项目（`--project` 优先） |
| `AGENT_DASHBOARD_HISTORY_KEEP` | 每个项目保留多少件过去的记录（默认 20。填 `0` 则不转移） |
| `PORT` | 服务器的默认端口（`--port` 优先） |
| `CLAUDE_CONFIG_DIR` | Claude Code 的 `CLAUDE.md` 的位置 |
| `CODEX_HOME` | Codex CLI 的 `AGENTS.md` 的位置 |
| `GEMINI_CLI_HOME` | Gemini CLI 的 `GEMINI.md` 的位置 |
| `COPILOT_HOME` | GitHub Copilot CLI 的规则文件的位置 |
| `OPENCODE_CONFIG_DIR` | opencode 的 `AGENTS.md` 的位置 |
| `AGENT_DASHBOARD_AGENTS_FILE` | 自定义添加的工具列表的保存位置（默认为任务记录位置下的 `agents.json`） |

### 显示语言

支持英语、日语、中文（简体）、韩语。**什么都不设置，也会以符合环境的语言显示出来。**

- **画面（面板、使用手册）** — 用右上角的语言选择器切换。首次会根据浏览器的语言设置自动决定，选过之后就会保存在这个浏览器里（与服务器一侧的设置相互独立）。
- **命令的输出** — `dash lang` 会显示当前的语言，以及它**是从哪里定下来的**。要更改时加上语言代码。

```bash
dash lang        # 查看当前语言和它的决定方式
dash lang en     # en / ja / zh / ko
```

决定方式是从上往下依次判断，**最先定下来的那个会被采用**。

| 顺序 | 决定方式 |
| --- | --- |
| 1 | 环境变量 `AGENT_DASHBOARD_LANG` |
| 2 | 用 `dash lang <代码>` 保存的设置 |
| 3 | 环境变量 `LC_ALL` / `LC_MESSAGES` / `LANG` |
| 4 | OS 的显示语言 |
| 5 | 英语 |

因为环境变量比保存下来的设置更强，所以如果执行 `dash lang ja` 之后仍然不变，那就是设置了 `AGENT_DASHBOARD_LANG`（`dash lang` 会把这一点显示出来）。

**代理的名字和任务内容不会被翻译。** 它们是各编程工具用 `dash add` 写进去的自由文本，照写下的样子记录，照记录的样子显示在画面上。各工具用什么语言来写，由 `install.py` 放进各规则文件的那段说明决定，而那段说明跟随下面的**命令的输出**的语言——不是画面的语言。切换右上角的选择器之所以不会改变它们，就是这个原因。改变它们的是 `dash lang <代码>`：**它会当场把所有规则文件中的说明也用新的语言重写**（你设置的语言就是组队时使用的语言）。

```bash
dash lang zh          # 1. 定下语言（所有规则文件中的说明也会被改写成这个语言）
                      # 2. 重启各编程工具的会话（规则在启动时读取）
```

被重写的**只有指向这一份副本的说明**，所以在别的副本里改变语言，绝不会把规则文件的指向换到别的目录去。如果它提示运行规则没有写在任何地方，说明那份副本还没有做初始设置——执行一次 `python install.py` 即可。

**已经存在的记录保持写下时的语言。** 事后重新翻译，会让画面显示出与「实际发生的事情」不同的东西。

没有准备译文的句子会以英语原样显示。**不会因为翻译有遗漏就让命令停下来。**

---

## 机制

```text
Claude 启动子代理 / 收到完成回报
        │
        ▼
  update_state.py  ──写入──▶  missions/<项目>/state.json
                   │          missions/<项目>/agents/*.json（孙代理的自行申报）
                   │
                   └─ 每次 start 时，把此前的记录整体转移出去
                                  missions/<项目>/history/<开始时刻>/
                                        │
                                     读取、合并
                                        ▼
                                  server.py  ──▶  /api/state（进行中的小队＋标签页一览）
                                                ──▶  /api/run（过去的记录 1 件）
                                                      │
                                                每秒获取一次
                                                      ▼
                                                public/index.html
```

- 写入状态的入口只有 `update_state.py`。时刻、代数、汇总全部会自动计算
- 写入是经由临时文件替换的，因此不会在读取途中读到损坏的 JSON
- 孙代理写进自己专用的文件，因此写入不会冲突
- 项目的识别方式是「文件夹名 + 完整路径的 6 位哈希」。即使是同名文件夹也不会混在一起

### 不显示的东西

子代理在工作过程中不会回报进度。也就是说，进度百分比的实测值根本不存在，因此
**不会编造一个看起来像模像样的数字显示出来。进度条本身就没有放。**
是否在运行，只用机器人的动作和卡片的颜色来表示。

例外是「等待回报」（给拥有运行中下属的单元加上的琥珀色显示），只有这一个是
**从记录下来的父子关系推导出来的**。它并不是在捏造数字，不过「子在运行」是事实，
「父在等待」却是推测，因此当父一边并行地做着自己的工作时，就会和实际情况有偏差。

出于同样的理由，完成回报中没有包含的 Token 数和工具使用次数会显示为 `—`。
这不是故障，而是「未知」这个正确的显示。

---

## 文件构成

```text
├─ dash.cmd / dash    启动器（Windows / POSIX）
├─ dash.py            统一入口点
├─ server.py          分发服务器
├─ update_state.py    状态更新 CLI
├─ install.py         初始设置
├─ dashlib.py         公共逻辑
├─ i18n.py            显示语言的切换
├─ i18n_data*.py      命令输出的翻译表（ja / zh / ko）
├─ build_vsix.py      组装 VSCode 扩展并安装
├─ check_i18n.py      检查翻译的缺失与多余（开发用）
├─ README.md          本文档（英语。另有 ja / zh / ko 版）
├─ OPERATION.md       给 Claude 用的运行手册（英语。另有 ja / zh / ko 版）
├─ EXTENSION_PLAN.md  扩展化的计划与设计
├─ extension/         VSCode 扩展的源码（没有构建工序）
│  ├─ package.json    扩展清单
│  ├─ package.nls*.json  扩展清单的译文
│  ├─ extension.js    扩展本体
│  ├─ i18n.js         扩展的显示语言切换
│  ├─ i18n_data.js    扩展的翻译表
│  ├─ test_extension.js  运行确认（只用 node 就能跑）
│  └─ media/          图标，以及它的生成脚本
├─ public/
│  ├─ index.html      面板画面
│  ├─ i18n.js         画面的翻译表与切换
│  ├─ manual-i18n.js  使用手册的正文（4 种语言）
│  └─ manual.html     使用手册
├─ dist/              组装好的 .vsix（不纳入版本跟踪）
└─ missions/          每个项目的记录
```

## 运行要求

- Python 3.9 以上
- Windows / macOS / Linux
- 现代浏览器（Chrome / Edge / Firefox）

机器人的表情用到了 CSS 的 `d` 属性，因此在 Safari 上嘴的形状不会变化
（除此之外的显示和动作都是一样的）。

---

## 疑难解答

### 面板上没有任何反映

**症状：** Claude 启动了子代理，面板上却什么都不显示

**原因排查：**

1. **你执行 `install.py` 了吗？**

   在分发目标的机器上必须执行一次：

   ```bash
   cd <面板所在的位置>
   python install.py
   ```

2. **请运行诊断脚本：**

   ```bash
   python diagnose.py
   ```

   请确认所有检查项都变成了 ✓。

3. **请重启各编程工具的会话**

   规则文件的改动是在启动时读取的，因此不会反映到正在运行的会话里。

4. **请确认当前目录**

   面板是根据**正在工作的项目的目录**来判定对象项目的。

   ```bash
   dash projects
   ```

   带着 `→` 标记的项目就是当前的对象。

### 想用相对路径运行

用相对路径是跑不起来的。原因在于，Claude 执行的命令是在**正在工作的项目的目录**下执行的。

**解决办法：**

1. **执行 `install.py`（推荐）**
2. **设置环境变量 `AGENT_DASHBOARD_HOME`**
3. **把全局包装脚本添加到 PATH**

上述 1、2 的详情，请参照上面的「安装」节和「设置」节。

### 端口被占用启动不了

```bash
dash serve --port 4000
```

请指定别的端口号。服务器会自动顺延，不过也可以明确指定。

### 分发之后，在别人的机器上跑不起来

**请务必让对方在分发目标的机器上执行 `install.py`。**

`install.py` 会自动检测以下内容：

- Python 的命令名（`python`, `python3`, `py -3`）
- 面板的放置位置（绝对路径）
- OS 特有的设置

这些东西每个环境都不一样，因此在分发源的机器上做好的设置，在别的机器上是不能用的。
