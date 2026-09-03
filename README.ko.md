# Subagent Dashboard

[English](README.md) | [日本語](README.ja.md) | [中文](README.zh.md) | **한국어**

Claude Code 의 서브에이전트가 지금 몇 대 움직이고 있고, 어느 것이 끝났으며,
시간과 토큰을 얼마나 썼는지를 실시간으로 보기 위한 로컬 앱입니다.
로봇의 표정과 움직임으로 상태를 알 수 있습니다.

- **외부 라이브러리 없음** — Python 표준 라이브러리만으로 동작합니다. `pip install` 은 필요 없습니다
- **인터넷 불필요** — CDN 참조 제로. 오프라인 환경에서도 동작합니다
- **PC 를 가리지 않음** — Windows / macOS / Linux, Python 3.9 이상에서 동작합니다
- **두는 위치를 가리지 않음** — 폴더째 복사하면 어디서든 동작합니다 (USB 메모리도 가능)

---

## 도입 (2단계)

### 1. 초기 설정 (마법사 형식)

폴더를 원하는 위치에 두고 셋업 도구를 실행합니다.

#### 권장: 완전 셋업 (초기 설정 + VSCode 확장)

**Windows 의 경우:**
- `setup-full.bat` 을 더블클릭

**macOS / Linux 의 경우:**
- `setup-full.sh` 를 더블클릭

**이것만으로 다음이 모두 완료됩니다:**
1. Python 환경의 검출
2. 초기 설정 (설치된 AI 코딩 CLI 들의 운용 규칙 파일에 쓰기)
3. VSCode 확장 기능의 설치

#### 대체: 초기 설정만 (VSCode 를 쓰지 않는 경우)

**Windows 의 경우:**
- `setup.bat` 을 더블클릭

**macOS / Linux 의 경우:**
- `setup.sh` 를 더블클릭

#### 커맨드 라인에서 실행하는 경우

```bash
# 완전 셋업 (Windows)
dash.cmd ext install

# 초기 설정만 (Windows)
dash.cmd install

# macOS / Linux
./dash install
```

**마법사 형식의 설치 프로그램이 시작되어 4 단계로 자동 셋업합니다:**

1. **환경 점검** — Python 버전, 파일 구성, 쓰기 권한을 확인
2. **환경의 자동 검출** — Python 명령, 경로, 설정 파일의 위치를 검출
3. **설정 파일에 쓰기** — 발견된 AI 코딩 CLI 들의 운용 규칙 파일과 VSCode 키 바인딩을 갱신
4. **셋업 완료** — 시작 방법과 다음 단계를 안내

모든 항목에 ✓ 가 붙으면 완료입니다.

- 이 폴더의 실제 위치를 검출해서 심어 두므로 **다른 PC 에서도 같은 명령이면 됩니다**
- 마커로 둘러싼 범위만 고쳐 쓰므로 각 CLI 의 기존 설정 내용은 망가뜨리지 않습니다
- 쓸 내용을 먼저 확인하고 싶을 때는 `dash install --print`
- 취소할 때는 `python install.py --uninstall`

**🚀 자동 셋업 기능:**

첫 실행 시(서버 시작 시 등)에 미설정이 검출되면 **자동으로 셋업을 안내합니다.**
- 대화형 환경(터미널에서 직접 실행)에서는 확인 대화상자가 표시됩니다
- 비대화형 환경(Claude 가 실행)에서는 경고를 표시하고 계속 진행합니다
- VSCode 확장 기능을 쓰는 경우에는 본체 배치 후에 자동 실행됩니다

**🔍 동작 확인 (진단 도구):**

제대로 설정되었는지 확인하려면 진단 스크립트를 실행하세요:

```bash
python diagnose.py
```

마법사 형식으로 6 개 항목을 점검하며, 모두 ✓ 가 되면 성공입니다.
문제가 발견되면 원인과 해결책이 번호와 함께 표시됩니다.

#### 지원하는 AI 코딩 CLI 들

초기 설정은 머신에서 발견되는 모든 AI 코딩 CLI 에 운용 규칙을 쓰입니다. 이 도구가 인식하는 CLI 는 다음과 같습니다.

| CLI | 운용 규칙이 쓰이는 위치 |
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

표에 없는 CLI 도 지원됩니다(아래 참조). **Cursor** 와 **Aider** 는 사용자 레벨의 자동 읽기 설정 파일이 없으므로, 저장소별 설정 파일을 가리키는 `--agent-file` 옵션으로 지정합니다.

#### 특정 CLI 를 대상으로 설정하기

```bash
python install.py --list-agents          # 발견된 모든 CLI 와 설정 상태를 표시
python install.py                        # 이 머신에서 발견된 모든 CLI 에 쓰기
python install.py --agent codex          # 특정 CLI 만 대상으로 하기 (codex / gemini / 등)
python install.py --agent all            # 알려진 모든 CLI 에 쓰기 (설치 여부와 상관없이)
python install.py --agent-file <경로>    # 이 경로의 파일도 함께 쓰기
```

`--agent-file` 로 추가한 CLI 는 `agents.json` 에 영구적으로 등록되어, 이후 `--list-agents` 에 나타나고, 다음 `install.py` 에서 갱신되며, `--uninstall` 로 정리됩니다. 새로운 CLI 나 사내용 도구를 지원하면서 도구 버전 업그레이드를 기다릴 필요가 없습니다.

`agents.json` 은 수동으로도 편집할 수 있습니다. 기존 항목의 `key` 가 일치하면 내장 설정을 무시하므로, CLI 가 설정 파일 위치를 바꾼 경우 도구 업그레이드를 기다리지 않고 로컬에서 고칠 수 있습니다.

**초기 설정 후 새로운 AI 코딩 CLI 를 설치한 경우, `python install.py` 를 다시 실행해야 합니다.** 설정 시점에 없던 CLI 에는 규칙이 쓰이지 않아서, 그 CLI 로 시작한 서브에이전트는 대시보드에 나타나지 않습니다. 진단 도구(`python diagnose.py`)에서 이를 감지할 수 있습니다.

### 2. 화면 열기

```bash
# Windows
dash.cmd serve --open

# macOS / Linux
./dash serve --open
```

브라우저가 열립니다. 이 창은 계속 띄워 둔 채로 두세요.
서버는 **하나만 띄워 두면 어느 프로젝트에서 작업하고 있든 이 화면에 나옵니다.**

그다음은 평소대로 Claude 에게 작업을 맡기기만 하면 됩니다. 서브에이전트가 시작되면
그 자리에 로봇이 나타납니다.

화면에 비치는 것은 **지금 움직이고 있는 팀**입니다 (여러 프로젝트가 동시에 돌고 있으면 전부 탭에 늘어섭니다).
작업이 끝나도 그대로 남고, 다음에 같은 프로젝트에서 작업을 시작하면 이전 기록은 사라지지 않고
탭의 「과거 기록」으로 남습니다. 아무것도 움직이고 있지 않을 때는 대기 화면입니다.

---

## 사용법

**취급 설명서가 앱에 함께 들어 있습니다.** 서버를 시작하고 다음을 열어 보세요.

```text
http://127.0.0.1:3939/manual.html
```

대시보드 화면 오른쪽 위의 「?」 버튼에서도 열 수 있습니다.
로봇 표정의 의미, 카드 읽는 법, 곤란할 때의 대처가 그림과 함께 적혀 있습니다.

### 자주 쓰는 명령

`dash` 는 Windows 에서는 `dash.cmd`, macOS / Linux 에서는 `./dash` 입니다.

| 명령 | 내용 |
| --- | --- |
| `dash serve --open` | 화면의 서버를 시작하고 브라우저를 연다 (`Ctrl+C` 로 정지) |
| `dash serve --port 4000` | 포트를 지정해서 시작한다 |
| `dash projects` | 등록된 프로젝트 목록. `→` 가 현재 폴더의 대상 |
| `dash status` | 지금 프로젝트의 내용을 표시 |
| `dash demo` | 표시 확인용 더미 데이터를 넣는다 |
| `dash reset` | 지금 프로젝트를 비운다 |
| `dash history` | 이 프로젝트의 과거 미션(`history/`)을 목록으로 표시 |
| `dash install` | 초기 설정 (다른 PC 로 옮겼을 때 실행) |

`dash` 만으로 실행하면 목록이 나옵니다. 각 명령은 `dash <명령> --help` 로 자세한 내용을 볼 수 있습니다.

상태를 고쳐 쓰는 명령(`start` / `add` / `done` / `finish`)은 보통 Claude 가 자동으로 실행하므로
손으로 칠 필요는 없습니다. `autofinish` 는 보통 SessionEnd hook 이 자동으로 실행하므로
이 역시 손으로 칠 필요가 없습니다(자세한 내용은 아래 「세션이 끝나면 자동으로 마감」 참고).

### 세션이 끝나면 자동으로 마감(autofinish)

`.claude/settings.local.json` 에 SessionEnd hook 을 설정해 두면, 세션이 끝나는 순간
`dash autofinish` 가 자동으로 실행되어 열려 있던 미션을 마감합니다. Claude 가 `finish` 를
치는 것을 잊어도 상관없습니다.

```json
"SessionEnd": [
  {
    "matcher": "",
    "hooks": [
      { "type": "command", "command": "python 'C:\\path\\to\\update_state.py' autofinish; exit 0" }
    ]
  }
]
```

가동 중인 미션이 없으면 아무 일도 일어나지 않습니다. `--project` 를 붙이지 않으면 현재
디렉터리에서 가동 중인 미션을 전부 마감합니다(`--project` 로 나눠서 병렬로 돌리던 것도
포함). `--project <이름>` 을 붙이면 그 하나만 마감합니다.

마감할 때, 그 순간 가동 중이었지만 기록에는 없던 유닛도 당시 모습 그대로 기록에 새겨집니다
(유닛 수에는 세지 않습니다). 자세한 내용은 `OPERATION.md` 를 참고하세요.

autofinish 는 **자신이 속한 세션**이 연 미션만 마감합니다 — `start` 가 세션 ID 를
`mission.sessionId` 에 기록해 두고, 세션 ID 를 알 수 없는 환경에서만 예전처럼 전부
마감합니다. 같은 폴더에서 Claude Code 를 두 개 띄웠을 때, 한쪽이 끝났다고 아직 작업
중인 다른 쪽 미션까지 닫혀 버리는 사고를 막기 위한 장치입니다.

> `/clear` 도 SessionEnd 를 발생시키므로, 작업 도중에 미션이 마감되는 경우가 있습니다.
> 지나치게 닫히는 것은 다음 `start` 로 다시 하면 되지만, **마감을 놓치는 것은 고칠 수
> 없습니다** — 이것이 바로 autofinish 가 막으려는 것입니다.

### 같은 폴더에서 두 개를 동시에 돌릴 때

미션의 기록처는 프로젝트(＝작업 폴더)마다 하나입니다. 같은 폴더에서 두 번째를
`start` 하면, 첫 번째는 가동 중인 채로 이력으로 밀려나며 이후 그 첫 번째에는 기록할 수 없습니다
(나중에 완료로 고칠 수도 없습니다). 병행할 때는 `--project` 로 기록처를 나누세요.

```bash
dash start  --project issue51 --title "issue51 조사" --model claude-opus-5
dash add    --project issue51 --id SCOUT-A --name "정찰A" --model claude-sonnet-5 --mission "..."
dash done   --project issue51 --id SCOUT-A --headline "..."
dash finish --project issue51 --headline "..."
```

`--project` 는 4 개 명령 모두에 붙입니다. 하나라도 빠뜨리면 그 명령만 현재 폴더 쪽
＝다른 한쪽 팀에 쓰이게 됩니다. 이 절차는 `dash install` 이 각 AI 코딩 CLI 의 운용 규칙 파일에도 써 넣으므로
에이전트도 같은 규칙으로 움직입니다.

### 과거 기록 보기

같은 프로젝트에서 `start` 를 다시 해도 그때까지의 기록은 사라지지 않습니다.
`missions/<프로젝트>/history/<시작 시각>/` 으로 통째로 보관되며, 화면의 탭 바에서 고르면 되돌아볼 수 있습니다
(과거 기록은 경과 시간이 멈춘 상태로 표시됩니다).

보관 건수는 프로젝트마다 최근 20 건(기본값)이며, 넘친 만큼은 오래된 것부터 `trash/` 로 옮깁니다
(`trash/` 는 폴더를 되돌려 놓으면 복구할 수 있습니다). 목록은 명령으로도 확인할 수 있습니다.

```bash
dash history
```

---

## VSCode 확장 기능으로 열기 (추천)

VSCode 안에 Subagent Dashboard 탭을 띄울 수 있습니다. 브라우저로 전환하지 않아도 되고, 서버 시작도 확장이 알아서 챙깁니다.

### 넣기 (한 번만)

```bash
# Windows
dash.cmd ext install

# macOS / Linux
./dash ext install
```

그 뒤 VSCode 를 다시 읽어들이세요 (`Ctrl+Shift+P` → Reload Window).

npm 도 `vsce` 도 필요 없습니다. `.vsix` 를 Python 표준 라이브러리만으로 조립해서 `code --install-extension` 에 넘기고 있습니다.

### 쓰기

왼쪽 끝 활동 표시줄에 늘어난 **로봇 아이콘**을 누르면 에디터 탭에 Subagent Dashboard 가 나옵니다.
왼쪽에 길쭉하게 두고 싶을 때는 설정 `agentDashboard.sidebarBehavior` 를 `embed` 로 하면 사이드바 안에 나옵니다.

명령 팔레트(`Ctrl+Shift+P`)에서 「Subagent Dashboard」라고 쳐도 마찬가지입니다.

| 명령 | 무엇을 하는가 |
|---|---|
| Subagent Dashboard: 탭으로 열기 | 에디터 탭에 Subagent Dashboard 를 띄운다 |
| Subagent Dashboard: 브라우저로 열기 | OS 의 기본 브라우저로 연다 |
| Subagent Dashboard: 서버 재시작 | 이 확장이 시작한 서버를 멈추고 다시 세운다 |
| Subagent Dashboard: 서버 정지 | 이 확장이 시작한 서버를 멈춘다 |
| Subagent Dashboard: 본체 배치／갱신 | 함께 들어 있는 본체를 배치처에 둔다 |
| Subagent Dashboard: 초기 설정 실행 | 초기 설정(`install.py`)을 확인한 뒤 실행한다 |
| Subagent Dashboard: 초기 설정 플래그 초기화 | 「이미 끝났다」는 기록을 지워, 다음에 다시 실행되게 한다 |
| Subagent Dashboard: 로그 표시 | 시작 경과와 Python 쪽 출력을 본다 |

서버가 돌고 있지 않으면 확장이 시작합니다. 이미 돌고 있으면 그것을 그대로 쓰므로 프로세스가 늘어나는 일은 없습니다. 포트가 차 있으면 다음 번호로 올려서, 그 번호로 화면을 엽니다.

바깥(터미널의 `dash serve` 등)에서 세운 서버는, 확장이 그대로 쓸 뿐 멋대로 멈추지 않습니다.

### 남에게 나눠 주기

확장 기능에는 **대시보드 본체가 통째로 들어 있습니다.** 상대의 PC 에 아무것도 없어도 이것 하나로 동작합니다.

```bash
dash.cmd ext package
```

`dist/` 에 파일 2 개가 나옵니다. **이것을 메일에 첨부하세요.**

- `agent-dashboard-<버전>.vsix` — 확장 기능 본체 (약 0.1MB)
- `インストール手順.txt` — 그대로 건네줄 수 있는 안내서

받은 사람은 VSCode 화면만으로 넣을 수 있습니다 (확장 기능 패널 → `…` → 「VSIX 에서 설치...」).
`code` 명령은 필요 없습니다.

처음 아이콘을 누르면 「본체를 여기에 둡니다」라는 확인이 나오고, 승낙하면 `~/.claude/agent-dashboard` 에 풀립니다. **함께 들어 있던 위치에서는 돌리지 않습니다.** 확장 폴더의 이름에는 버전 번호가 들어 있어서 갱신하면 폴더째 바뀌기 때문에, 거기에 기록을 두면 사라져 버리기 때문입니다.

갱신판을 나눠 줄 때도 같은 절차로 덮어쓸 수 있습니다. `missions/`(작업 기록)에는 손대지 않습니다.

**갱신할 때는 각 AI 코딩 CLI 의 운용 규칙 파일도 다시 배포됩니다.** 본체를 새것으로 해도 에이전트가 읽는
안내서는 이전 판 그대로 남기 때문입니다 (초기 설정은 한 번 성공하면 자동으로는 두 번 다시
돌지 않습니다). 확장에서 갱신하면 본체를 둔 다음에 「무엇을 어디에 쓸지」의 확인이 이어서
나오므로, 승낙하면 각 CLI 의 운용 규칙 파일의 마커 안이 새 절차로 교체됩니다. 넘겼을 경우나, 확장을
쓰지 않고 덮어쓰기 복사로 갱신한 경우에는 손으로 실행하세요.

```bash
python ~/.claude/agent-dashboard/install.py
```

낡은 채로 쓰고 있으면 `start` 할 때와 서버 시작 시에 알림이 나옵니다. 지금 맞춰져 있는지는
`python diagnose.py` 의 「운용 규칙의 판」에서 확인할 수 있습니다.

> `.vsix` 는 속이 ZIP 이라서 사내 메일 관문에 걸릴 때가 있습니다.
> 그럴 때는 확장자를 바꿔서 보내고(예 `.vsix` → `.txt`), 받은 쪽에서 되돌리게 하세요.

### 그 밖의 명령

```bash
dash ext build       # .vsix 를 만들기만 한다 (dist/ 에 나온다)
dash ext status      # 들어 있는지, 판이 맞는지 확인한다
dash ext uninstall   # 뺀다
```

확장의 설정·문제 해결은 [extension/README.md](extension/README.md) 를, 설계의 경위는 [EXTENSION_PLAN.md](EXTENSION_PLAN.md) 를 보세요.

---

## 글로벌 액세스 (Global Access)

확장 기능을 넣지 않는 경우의 통로입니다. 임의의 프로젝트 폴더에서 대시보드를 빠르게 열 수 있습니다.

### 개요

`dash install` 명령으로 초기 설정을 하면 **어느 프로젝트에서 작업하고 있든** `Ctrl+Shift+D` 만 누르면 대시보드가 열립니다.
agent-dashboard 폴더를 다시 열 필요는 없습니다.

> `Ctrl+Shift+D` 는 VSCode 표준의 「실행 및 디버그」 뷰(`workbench.view.debug`)와 같은 키입니다.
> `dash install` 을 실행하면 이쪽이 우선되어, 디버그 뷰는 그 키로 열리지 않게 됩니다.
> 확장 기능을 쓰는 경우에는 키 바인딩을 등록하지 않으므로 이 충돌은 일어나지 않습니다.
>
> **이전 판에서는 이 등록이 듣지 않는 결함이 있었습니다.** `install.py` 가 VSCode 가 읽지 않는 파일(확장 기능의 보관 위치)에 키 바인딩을 써 넣고 있었기 때문입니다. 쓰는 위치를 OS 별로 올바른 사용자 설정 파일로 고쳐 두었습니다.

### 셋업 (한 번만)

agent-dashboard 디렉터리에서 다음을 실행합니다.

```bash
# Windows
dash.cmd install

# macOS / Linux
chmod +x dash        # 처음 한 번만
./dash install
```

이것으로 다음이 설정됩니다:

- **키 바인딩 등록**: VSCode 에서 `Ctrl+Shift+D` 에 대시보드 시작 동작을 할당합니다
- **임의의 프로젝트에서 접근 가능**: VSCode 가 어느 워크스페이스를 열고 있어도 같은 단축키로 시작할 수 있습니다

### 사용법

1. **임의의 프로젝트를 VSCode 로 엽니다**

2. **`Ctrl+Shift+D` 를 누릅니다**

   대시보드가 자동으로 시작되어 브라우저(또는 SimpleWebService)에 표시됩니다.

   첫 시작 때는 서버가 뜨는 데 몇 초 걸립니다.

3. **그다음은 평소대로 Claude 에게 작업을 맡깁니다**

   서브에이전트가 시작되면 대시보드에 로봇이 나타납니다.

### 구조

- **환경 변수 `AGENT_DASHBOARD_HOME`** 로 agent-dashboard 의 위치를 기억합니다
- **`open_dashboard.py` 스크립트**가 서버를 시작하고 브라우저를 엽니다
- **헬스 체크**로 http://127.0.0.1:3939 의 응답을 확인한 뒤에 엽니다

### 문제 해결

| 문제 | 대처 |
| --- | --- |
| `Ctrl+Shift+D` 가 듣지 않는다 | VSCode 설정에서 「바로 가기 키」를 열고 `openDashboard` 를 검색해 등록 상태를 확인하세요 |
| 대시보드가 열리지 않는다 | 터미널을 열고 `dash serve --open` 을 직접 실행하세요 |
| 포트가 사용 중이라 시작할 수 없다 | `--port 4000` 옵션으로 다른 포트를 지정하세요: `dash serve --port 4000 --open` |
| 수동으로 열고 싶다 | 터미널에서 `python <agent-dashboard-path>/open_dashboard.py` 를 실행하세요 |

---

## 설정

### 기록의 저장 위치 바꾸기

기본값으로는 이 폴더의 `missions/` 에 저장합니다.
이 폴더가 쓰기 불가인 위치(`Program Files` 등)에 있는 경우에는
OS 표준의 사용자 데이터 영역으로 자동 폴백합니다.

명시적으로 지정하고 싶을 때는 환경 변수를 씁니다.

```bash
# Windows (PowerShell)
$env:AGENT_DASHBOARD_HOME = "D:\dashboard-data"

# macOS / Linux
export AGENT_DASHBOARD_HOME=~/dashboard-data
```

### 그 밖의 환경 변수

| 변수 | 효과 |
| --- | --- |
| `AGENT_DASHBOARD_HOME` | 기록의 저장 위치 |
| `AGENT_DASHBOARD_PROJECT` | 대상 프로젝트를 고정한다 (`--project` 가 우선) |
| `AGENT_DASHBOARD_HISTORY_KEEP` | 과거 기록을 프로젝트마다 몇 건 남길지 (기본값 20. `0` 이면 보관하지 않음) |
| `PORT` | 서버의 기본 포트 (`--port` 가 우선) |
| `CLAUDE_CONFIG_DIR` | Claude Code 의 `CLAUDE.md` 가 있는 위치 |
| `CODEX_HOME` | Codex CLI 의 `AGENTS.md` 가 있는 위치 |
| `GEMINI_CLI_HOME` | Gemini CLI 의 `GEMINI.md` 가 있는 위치 |
| `COPILOT_HOME` | GitHub Copilot CLI 의 설정 파일이 있는 위치 |
| `OPENCODE_CONFIG_DIR` | opencode 의 `AGENTS.md` 가 있는 위치 |
| `AGENT_DASHBOARD_AGENTS_FILE` | 직접 추가한 CLI 목록이 저장되는 위치 (기본값: 기록 폴더의 `agents.json`) |

### 표시 언어

영어·일본어·중국어(간체)·한국어를 지원합니다. **아무것도 설정하지 않아도 환경에 맞는 언어로 나옵니다.**

- **화면(대시보드·취급 설명서)** — 오른쪽 위의 언어 선택기로 전환합니다. 처음에는 브라우저의 언어 설정에서 자동으로 정해지고, 고른 뒤에는 이 브라우저에 저장됩니다 (서버 쪽 설정과는 독립입니다).
- **명령의 출력** — `dash lang` 으로 지금의 언어와, 그것이 **어디에서 정해졌는지**가 나옵니다. 바꿀 때는 언어 코드를 붙입니다.

```bash
dash lang        # 지금의 언어와 정해지는 방식을 본다
dash lang en     # en / ja / zh / ko
```

정해지는 방식은 위에서부터 순서대로이며, **가장 먼저 정해진 것이 쓰입니다**.

| 순서 | 정해지는 방식 |
| --- | --- |
| 1 | 환경 변수 `AGENT_DASHBOARD_LANG` |
| 2 | `dash lang <코드>` 로 저장한 설정 |
| 3 | 환경 변수 `LC_ALL` / `LC_MESSAGES` / `LANG` |
| 4 | OS 의 표시 언어 |
| 5 | 영어 |

환경 변수 쪽이 저장한 설정보다 강하므로, `dash lang ja` 를 실행해도 바뀌지 않는 경우에는 `AGENT_DASHBOARD_LANG` 이 설정되어 있습니다 (`dash lang` 이 그 사실을 표시합니다).

**에이전트의 이름과 임무 내용은 번역되지 않습니다.** 이것들은 에이전트가 `dash add` 로 써 넣는 자유 기술이며, 적은 그대로 기록되고 기록된 그대로 화면에 나옵니다. 에이전트가 어느 언어로 쓸지는 `install.py` 가 각 CLI 의 운용 규칙 파일에 넣는 기술로 정해지고, 그 기술은 위의 **명령의 출력** 언어를 따릅니다——화면의 언어가 아닙니다. 오른쪽 위의 선택기를 바꿔도 달라지지 않는 것은 이 때문입니다. 바꾸는 것은 `dash lang <코드>` 이며, **그 자리에서 기술도 새 언어로 다시 쓰입니다**(설정한 언어 = 팀을 짜는 언어).

```bash
dash lang ko          # 1. 언어를 정한다 (기술도 이 언어로 다시 쓰인다)
                      # 2. 에이전트의 세션을 재시작한다 (운용 규칙은 시작할 때 읽힌다)
```

다시 쓰이는 것은 **이 복사본을 가리키는 기술뿐**이므로, 다른 복사본에서 언어를 바꿔도 다른 저장소의 운용 규칙이 가리켜지는 일은 없습니다. 「운용 규칙이 어디에도 쓰여 있지 않다」고 나오면 그 저장소는 아직 초기 설정을 하지 않은 것이므로 `python install.py` 를 한 번 실행해 주세요.

**이미 있는 기록은 쓰였을 때의 언어 그대로**입니다. 나중에 다시 번역하면, 화면이 「실제로 일어난 일」과 다른 것을 비추게 됩니다.

번역이 준비되어 있지 않은 문장은 영어 그대로 나옵니다. **번역 누락 때문에 명령이 멈추는 일은 없습니다.**

---

## 구조

```text
Claude 가 서브에이전트를 시작 / 완료 보고를 수신
        │
        ▼
  update_state.py  ──기록──▶  missions/<프로젝트>/state.json
                   │          missions/<프로젝트>/agents/*.json (손자의 자기 신고)
                   │
                   └─ start 할 때마다 그때까지의 기록을 통째로 보관
                                  missions/<프로젝트>/history/<시작 시각>/
                                        │
                                      읽기·병합
                                        ▼
                                  server.py  ──▶  /api/state (진행 중인 팀＋탭 목록)
                                                ──▶  /api/run (과거 기록 1 건)
                                                      │
                                                 1초마다 가져오기
                                                      ▼
                                                public/index.html
```

- 상태를 쓰는 창구는 `update_state.py` 뿐. 시각·세대·집계는 모두 자동 계산됩니다
- 쓰기는 임시 파일을 거쳐 갈아 끼우므로, 읽는 도중에 깨진 JSON 을 읽는 일이 없습니다
- 손자 에이전트는 자기 전용 파일에 쓰므로 쓰기가 충돌하지 않습니다
- 프로젝트의 식별은 「폴더 이름 + 전체 경로의 해시 6 자리」. 이름이 같은 폴더라도 섞이지 않습니다

### 표시하지 않는 것

서브에이전트는 작업 중에 진척을 보고하지 않습니다. 즉 진척 %의 실측값은 존재하지 않으므로,
**그럴싸한 숫자를 만들어서 표시하는 일은 하지 않습니다. 진행 바 자체를 두지 않았습니다.**
가동 중인지 아닌지는 로봇의 움직임과 카드의 색으로만 나타내고 있습니다.

예외는 「보고 대기」(가동 중인 부하를 안고 있는 기체에 붙는 호박색 표시)이며, 이것만은
**기록된 부모-자식 관계로부터의 도출**입니다. 숫자를 날조하고 있는 것은 아니지만,
「자식이 움직이고 있다」는 사실이어도 「부모가 기다리고 있다」는 추측이므로, 부모가 병행해서 자기 작업을
하고 있을 때는 실태와 어긋납니다.

같은 이유로, 완료 보고에 포함되지 않았던 토큰 수나 도구 사용 횟수는 `—` 로 표시합니다.
이것은 고장이 아니라 「알 수 없음」이라는 올바른 표시입니다.

---

## 파일 구성

```text
├─ dash.cmd / dash    런처 (Windows / POSIX)
├─ dash.py            통합 엔트리 포인트
├─ server.py          배포 서버
├─ update_state.py    상태 갱신 CLI
├─ install.py         초기 설정
├─ dashlib.py         공통 로직
├─ i18n.py            표시 언어의 전환
├─ i18n_data*.py      명령 출력의 번역표 (ja / zh / ko)
├─ build_vsix.py      VSCode 확장 기능을 조립해서 넣는다
├─ check_i18n.py      번역의 누락·잉여를 점검한다 (개발용)
├─ README.md          이 문서 (영어. ja / zh / ko 판이 나란히 있다)
├─ OPERATION.md       Claude 용 운영 절차 (영어. ja / zh / ko 판이 나란히 있다)
├─ EXTENSION_PLAN.md  확장 기능화의 계획과 설계
├─ extension/         VSCode 확장 기능의 소스 (빌드 공정 없음)
│  ├─ package.json    확장 매니페스트
│  ├─ package.nls*.json  확장 매니페스트의 번역
│  ├─ extension.js    확장 본체
│  ├─ i18n.js         확장의 표시 언어 전환
│  ├─ i18n_data.js    확장의 번역표
│  ├─ test_extension.js  동작 확인 (node 만으로 돈다)
│  └─ media/          아이콘과 그 생성 스크립트
├─ public/
│  ├─ index.html      대시보드 화면
│  ├─ i18n.js         화면의 번역표와 전환
│  ├─ manual-i18n.js  취급 설명서의 본문 (4 개 언어)
│  └─ manual.html     취급 설명서
├─ dist/              조립한 .vsix (추적하지 않음)
└─ missions/          프로젝트별 기록
```

## 동작 요건

- Python 3.9 이상
- Windows / macOS / Linux
- 모던 브라우저 (Chrome / Edge / Firefox)

로봇의 표정에는 CSS 의 `d` 속성을 쓰고 있기 때문에, Safari 에서는 입 모양이 바뀌지 않습니다
(그 밖의 표시와 동작은 같습니다).

---

## 문제 해결

### 대시보드에 반영되지 않는다

**증상:** Claude 가 서브에이전트를 시작해도 대시보드에 아무것도 표시되지 않는다

**원인 점검:**

1. **`install.py` 를 실행했습니까?**

   배포 대상 머신에서 반드시 한 번 실행해야 합니다:

   ```bash
   cd <대시보드의 위치>
   python install.py
   ```

2. **진단 스크립트를 실행하세요:**

   ```bash
   python diagnose.py
   ```

   모든 점검이 ✓ 가 되어 있는지 확인하세요.

3. **에이전트의 세션을 다시 시작하세요**

   운용 규칙의 변경은 시작할 때 읽어들이므로, 실행 중인 세션에는 반영되지 않습니다.

4. **현재 디렉터리를 확인하세요**

   대시보드는 **작업 중인 프로젝트의 디렉터리**에서 대상 프로젝트를 판정합니다.

   ```bash
   dash projects
   ```

   `→` 표시가 붙어 있는 프로젝트가 현재의 대상입니다.

### 상대 경로로 돌리고 싶다

상대 경로로는 돌지 않습니다. 이유는, Claude 가 실행하는 명령이 **작업 중인 프로젝트의 디렉터리**에서 실행되기 때문입니다.

**해결책:**

1. **`install.py` 를 실행한다(권장)**
2. **환경 변수 `AGENT_DASHBOARD_HOME` 을 설정한다**
3. **글로벌 래퍼 스크립트를 PATH 에 추가한다**

위 1, 2 의 자세한 내용은 위쪽의 「도입」 절과 「설정」 절을 참조하세요.

### 포트가 사용 중이라 시작할 수 없다

```bash
dash serve --port 4000
```

다른 포트 번호를 지정하세요. 서버는 자동으로 번호를 올리지만, 명시적으로 지정할 수도 있습니다.

### 배포 후 다른 사용자의 머신에서 돌지 않는다

**반드시 배포 대상 머신에서 `install.py` 를 실행하게 하세요.**

`install.py` 는 다음을 자동 검출합니다:

- Python 의 명령 이름(`python`, `python3`, `py -3`)
- 대시보드의 배치 위치(절대 경로)
- OS 고유의 설정

이것들은 환경마다 다르기 때문에, 배포한 쪽 머신에서 만든 설정은 다른 머신에서는 돌지 않습니다.
