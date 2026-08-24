#!/usr/bin/env python3
"""Subagent Dashboard — 初期設定

    python install.py                 設定する（入っている CLI を全部見つけて書く）
    python install.py --print         書き込む内容を表示するだけ（何も変更しない）
    python install.py --uninstall     書き込んだ設定を取り消す
    python install.py --list-agents   知っている CLI と書き込み先の一覧
    python install.py --agent codex   書き込む先を1つに絞る（all で登録済み全部）
    python install.py --agent-file <パス>
                                      一覧に無い CLI のファイルを名指しで足す

やること:
  1. Python の起動コマンド（python / python3 / py -3）を実測で判定する
  2. エージェント CLI のグローバル設定ファイルに運用ルールを書き込む
     （Claude Code なら CLAUDE.md、Codex CLI なら AGENTS.md。本文はどれも同じ）
     - 入っている CLI を設定フォルダの有無で判定し、見つかった全部に書く
     - 対応表は dashlib.BUILTIN_AGENT_TARGETS。**そこに無い CLI にも書ける**
       （--agent-file で足すと agents.json に覚え、次回から一覧に出る）
     - このツールの実際の場所を埋め込むので、どのPCでも同じ手順で動く
     - マーカーで囲んだ範囲だけを更新するので、既存の記述は壊さない
  3. VSCode のユーザーキーバインド（keybindings.json）に Ctrl+Shift+D を登録する
     - VSCode が実際に読む場所（OS ごとに違う）に書く
     - 拡張機能のコマンド agentDashboard.open を直接呼ぶ
  4. macOS / Linux ではランチャ（./dash）に実行権限を付ける
  5. 書き込み先の確認と動作チェックを行う

外部ライブラリは使いません（Python 標準ライブラリのみ）。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib  # noqa: E402
import i18n  # noqa: E402
from i18n import t  # noqa: E402

dashlib.use_utf8_stdio()

# 書く側と読む側が同じものを見るように、マーカーは dashlib のものを使う。
# ここでベタ書きに戻すと、片方だけ直したときに黙ってすれ違う（読む側は dashlib）。
BEGIN = dashlib.BLOCK_BEGIN
END = dashlib.BLOCK_END
VERSION_MARK = dashlib.BLOCK_VERSION_MARK
tool_version = dashlib.tool_version


# ---------------------------------------------------------------- 環境の判定


def detect_python_command() -> str:
    """PATH から使える Python 3 の呼び出し方を実測で決める。

    見つからなければ現在動いている実行ファイルの絶対パスを使う（常に確実）。
    """
    candidates = [["python"], ["python3"], ["py", "-3"]]
    for cand in candidates:
        if not shutil.which(cand[0]):
            continue
        try:
            r = subprocess.run(
                cand + ["-c", "import sys; print(sys.version_info[0])"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0 and r.stdout.strip().startswith("3"):
            return " ".join(cand)
    return quote(str(Path(sys.executable)))


def quote(path: str) -> str:
    """空白を含むパスを安全に渡せるようにする。"""
    return f'"{path}"' if " " in path else path


def claude_config_dir() -> Path:
    return dashlib.agent_config_dir("claude")


def select_agents(choice: str) -> list[str]:
    """運用ルールを書き込む CLI を決める。

    既定（auto）は「設定フォルダが実在する CLI 全部」。入れていない CLI のフォルダを
    こちらが作ってしまうと、その CLI 側の初回セットアップが「もう設定済み」と誤認する
    ことがあるので、**自動では既にある所にしか書かない**。

    **利用者が自分で足した CLI は、フォルダの有無に関わらず必ず含める。** 組み込みは
    「入っていそうなら書く」という当て推量だが、--agent-file で足した1件は本人が
    名指しした意思表示で、当てに行く必要が無い。ここを present だけで絞ると、
    登録した直後に「書かれない」という一番腹の立つ挙動になる。

    1つも見つからないときは Claude Code に書く。これから入れる人にとっては、
    何も書かずに終わるより「置いてある」ほうが必ず得（読まれないだけで害は無い）。
    名指しの --agent は、その CLI をこれから入れる人の指定なのでフォルダを作る。
    all は登録済みの全部（使っていない CLI にも置いておきたい人向け）。
    """
    if choice == "all":
        return list(dashlib.agent_keys())
    if choice != "auto":
        return [choice]
    chosen = list(dashlib.present_agents())
    for entry in dashlib.load_user_agents():
        if entry["key"] not in chosen:
            chosen.append(entry["key"])
    return chosen or ["claude"]


def register_agent_file(path_text: str) -> str:
    """--agent-file で渡された「そのファイル」を CLI として登録し、鍵を返す。

    表に無い CLI（社内ツール、出たばかりのもの、まだ誰も知らないもの）に対応する
    ための逃げ道。ここで一覧に足しておくのは、次回の --uninstall と diagnose が
    同じ場所を見られるようにするため。**書いた場所を覚えていないと消せない。**

    鍵は置き場のフォルダ名から作る（~/.foo/AGENTS.md なら foo）。ただし rules や
    memories のような**どの CLI にもある一般名**は飛ばして、その上の名前を採る。
    ~/.foo/rules/AGENTS.md を "rules" と呼んでしまうと、次に別の CLI の rules/ を
    足したときに見分けが付かない。

    既にある鍵とぶつかったら番号を足す。勝手に上書きすると、名前が似ているだけの
    別物を黙って壊すことになる。
    """
    target = Path(path_text).expanduser()
    if not target.name:
        raise ValueError(t("--agent-file needs a path to a file, not a folder"))
    home = target.parent if str(target.parent) not in ("", ".") else Path.cwd()

    # 置き場そのものではなく「その CLI の名前」に当たる所まで遡る。
    GENERIC = {"rules", "memories", "instructions", "config", "prompts", "agents",
               "settings", ".config", "documents"}
    named = home
    while named.parent != named and named.name.lstrip(".").lower() in GENERIC:
        named = named.parent

    base = named.name.lstrip(".").lower() or "custom"
    base = "".join(ch for ch in base if ch.isalnum() or ch in "-_") or "custom"
    existing = {e["key"]: e for e in dashlib.agent_targets()}
    key = base
    n = 2
    while key in existing and (
        existing[key]["file"] != target.name
        or Path(existing[key]["home"]).expanduser().resolve() != home.resolve()
    ):
        key = "%s-%d" % (base, n)
        n += 1

    dashlib.add_user_agent({
        "key": key,
        "label": existing.get(key, {}).get("label") or named.name.lstrip(".") or key,
        "home_env": existing.get(key, {}).get("home_env", ""),
        "home": str(home),
        "file": target.name,
    })
    return key


# ---------------------------------------------------------------- 書き込む内容


def operation_manual() -> Path:
    """いまの表示言語に合わせた手引きのパス。

    運用ルールに書く案内は「エージェントが実際に開いて読む本」なので、本文と同じ
    言語のものを指さないと、書いた運用ルールと手引きで言葉が食い違う。
    対応表は dashlib に1つだけ置いてある（diagnose.py も同じものを使う）。
    """
    return dashlib.doc_path("OPERATION")


def build_block(py: str) -> str:
    us = quote(str(HERE / "update_state.py"))
    sv = quote(str(HERE / "server.py"))
    op = operation_manual()
    # BEGIN / END / VERSION_MARK は機械が読むしるしなので訳さない。本文だけを訳す。
    body = t("""## Subagent Dashboard

Whenever you launch subagents, always reflect what is happening on the dashboard.
The target project is detected automatically from the current directory, so the same commands work in any project.

```bash
# once, before the mission starts
{py} {us} start --title "<name of the work>" --model <your own model ID>

# right after you launch each subagent, one at a time
{py} {us} add --id SCOUT-A --name "<a readable name>" --model <model ID> --mission "<the task>"

# a unit that a subagent launched, not you: name its parent
{py} {us} add --id SCOUT-A-1 --parent SCOUT-A --name "<a readable name>" --model <model ID> --mission "<the task>"

# every time you receive a completion report
{py} {us} done --id SCOUT-A --sec <seconds> --tokens <number> --tools <number> --headline "<one-line result summary>"

# once, when every unit is back
{py} {us} finish --headline "<one-line overall summary>"
```

- **Do not forget `finish`.** Nothing breaks when you forget, which is exactly why nobody notices. The screen keeps saying "running", and the next time you `start`, that record is left behind as "unfinished" - **it can never be marked complete afterwards**. A reminder to run `finish` appears the moment you mark the last unit `done`, so close the mission when you see it.
- **Leave out any number that was not in the completion report (`--tokens` / `--tools` / `--sec`); do not estimate it.** Leaving it out shows "—" on the screen, and that is the correct state. Writing an estimate defeats the whole purpose of this dashboard.
- **`--parent` is what draws the tree.** Leave it out and the unit is filed directly under Command, so the screen shows a single column however deep the team really goes. Pass the parent's `--id` for every unit that a subagent launched rather than you.
- **Run `add` once per unit; never fold several into one entry.** An entry like "scout team (6)" loses the six members and everything they launched below them, and it cannot be recovered afterwards. When a subagent launches children of its own, put this in that subagent's own instructions: one JSON file per child, carrying **that subagent's own ID as `parentId`**, written into the grandchild self-report directory that `{py} {us} status` prints - `{op}` has the format.
- **Write the free text in English** (`--title` / `--name` / `--mission` / `--headline`). It is recorded exactly as you write it and shown on the screen exactly as recorded - nothing is translated afterwards. Follow the language of these instructions, not the language of the conversation.
- To watch the screen, start one `{py} {sv}` and open <http://127.0.0.1:3939/>. Every `start` adds one tab, and **past work stays viewable as tabs** (the 20 most recent per project; older ones move to the trash automatically). Finished tabs can be deleted from the screen.
- **Use the `update_state.py` at the path above.** If a copy sits somewhere else, running that one splits the `missions/` that gets written, and nothing appears on the screen.
- For the details (grandchild agents, `--project`, helper commands), see `{op}`.

### When you run two or more missions at once in the same directory (required)

Mission records are kept **one per project (= per working directory)**. If you type a second
`start` in the same directory, the first one is pushed into the history tabs while it is still
running, and every `done` for that first one after that fails with "does not exist". **There is
no way to mark a pushed-out record as finished later on.** Separating the records in advance is
the only remedy.

When you run missions in parallel in the same directory, give each `start` a unique name with
`--project` (passing a name that does not exist creates a new project under that name).

```bash
{py} {us} start --project <a unique name> --title "<name of the work>" --model <your own model ID>
{py} {us} add --project <a unique name> --id SCOUT-A --name "<a readable name>" --model <model ID> --mission "<the task>"
{py} {us} done --project <a unique name> --id SCOUT-A --headline "<one-line result summary>"
{py} {us} finish --project <a unique name> --headline "<one-line overall summary>"
```

- **Put `--project` on all four commands.** Miss it on even one, and that one command writes to
  the record of the current directory = the other team's record.
- Missions that run in different directories have separate records to begin with, so they do not
  need `--project`.
""").format(py=py, us=us, sv=sv, op=op)
    return BEGIN + "\n" + VERSION_MARK + tool_version() + " -->\n" + body + END


class BrokenMarkerError(Exception):
    """運用ルールファイルのマーカーが片方しか無い（手で編集して壊れた）。

    このまま追記すると BEGIN が2つ・END が1つの状態になり、次に --uninstall した
    ときに利用者が自分で書いた記述まで丸ごと消える。だから書かずに止める。
    """


def _find_blocks(text: str) -> list[tuple[int, int]]:
    """BEGIN..END で囲まれた範囲を全部返す。[(開始, 終了(END の直後)), ...]"""
    spans: list[tuple[int, int]] = []
    i = 0
    while True:
        start = text.find(BEGIN, i)
        if start == -1:
            return spans
        end = text.find(END, start + len(BEGIN))
        if end == -1:
            return spans
        spans.append((start, end + len(END)))
        i = end + len(END)


def apply_block(text: str, block: str) -> tuple[str, str, int]:
    """マーカーで囲まれた範囲だけを差し替える。

    (新しい内容, 何をしたか, 片付けた重複ブロックの数) を返す。**2番目は表示文では
    なく符牒**（created / appended / updated）にしてある。表示文を返すと、呼び手が
    それを文に埋め込むことになり、訳した瞬間に文法が壊れる。
    """
    spans = _find_blocks(text)

    if not spans:
        if BEGIN in text or END in text:
            raise BrokenMarkerError(
                t("the markers ({begin} / {end}) are not paired")
                .format(begin=BEGIN, end=END)
            )
        if not text.strip():
            return block + "\n", "created", 0
        sep = "" if text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + block + "\n", "appended", 0

    # 1つ目があった場所に新しいブロックを置く。過去の二重書き込みで2つ以上ある場合は
    # 余りを取り除く（マーカーの外にある記述には触らない）。
    at = spans[0][0]
    out = text
    for start, end in reversed(spans):
        out = out[:start] + out[end:]
    out = out[:at] + block + out[at:]

    return out, "updated", len(spans) - 1


def remove_block(text: str) -> tuple[str, bool]:
    """BEGIN..END の範囲を全部取り除く。マーカーの外は触らない。"""
    spans = _find_blocks(text)
    if not spans:
        return text, False
    out = text
    for start, end in reversed(spans):
        head = out[:start].rstrip("\n")
        tail = out[end:].lstrip("\n")
        if head and tail:
            out = head + "\n\n" + tail
        elif head:
            out = head + "\n"
        else:
            out = tail
    return out, True


# ---------------------------------------------------------------- keybindings.json 処理


KEY = "ctrl+shift+d"
KEY_COMMAND = "agentDashboard.open"
# かつてこのツールが書いていた形式。ターミナルに文字列を流し込む方式で、
# open_dashboard.py の場所とターミナルが開いていることに依存していた。
LEGACY_KEY_COMMAND = "workbench.action.terminal.sendSequence"


def vscode_user_dir() -> Path:
    """VSCode が **ユーザー設定として実際に読む** ディレクトリ。

    ~/.vscode は拡張機能の置き場であって設定の置き場ではない。そこに
    keybindings.json を置いても VSCode は読まない（実測で確認済み）。
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata and appdata.strip() else Path.home() / "AppData" / "Roaming"
        return base / "Code" / "User"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg and xdg.strip() else Path.home() / ".config"
    return base / "Code" / "User"


def keybindings_path() -> Path:
    return vscode_user_dir() / "keybindings.json"


def legacy_keybindings_path() -> Path:
    """0.2.x までの install.py が間違って書いていた場所（VSCode は読まない）。"""
    return Path.home() / ".vscode" / "keybindings.json"


def build_keybinding_entry() -> dict:
    """ダッシュボード用のキーバインドエントリ。

    拡張機能が登録するコマンドを直接呼ぶ。パスにもターミナルにも依存しない。
    （拡張の contributes.keybindings ではなくユーザー設定に書くのは、VSCode 標準の
      Ctrl+Shift+D「実行とデバッグ」より確実に優先させるため。）
    """
    return {"key": KEY, "command": KEY_COMMAND}


# ------------------------------------------------ JSONC（コメント付き JSON）の扱い
#
# VSCode の keybindings.json は JSONC で、既定で「// Place your key bindings...」という
# コメントが入っている。json.loads はこれを読めないので、素で読むと必ず失敗する。
# また、利用者が自分で書いたエントリ・コメント・字下げを壊さないよう、書き込みは
# 「元のテキストに必要な分だけ差し込む／該当箇所だけ切り取る」方式で行う。


def _blank_jsonc(text: str) -> str:
    """コメントと末尾カンマを空白に置き換える。**文字位置は元と1対1で保つ。**

    位置が保たれるので、この結果から求めた位置を元テキストの編集に使える。
    """
    out = list(text)
    n = len(text)
    i = 0
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = i
            while j < n and text[j] not in "\r\n":
                out[j] = " "
                j += 1
            i = j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            close = text.find("*/", i + 2)
            j_end = n if close == -1 else close + 2
            j = i
            while j < j_end:
                if text[j] not in "\r\n":  # 行数を変えない
                    out[j] = " "
                j += 1
            i = j_end
            continue
        i += 1

    # 末尾カンマ（JSONC では許されるが json.loads は受け付けない）
    blanked = out
    n = len(blanked)
    i = 0
    in_str = False
    while i < n:
        c = blanked[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
        elif c == ",":
            j = i + 1
            while j < n and blanked[j].isspace():
                j += 1
            if j < n and blanked[j] in "}]":
                blanked[i] = " "
        i += 1
    return "".join(blanked)


def _item_spans(blanked: str) -> list[tuple[int, int]]:
    """配列の各要素の (開始, 終了) を返す。blanked は _blank_jsonc を通した文字列。

    json.loads で妥当性を確かめた後に呼ぶこと。
    """
    spans: list[tuple[int, int]] = []
    n = len(blanked)
    i = blanked.index("[") + 1
    while i < n:
        c = blanked[i]
        if c.isspace() or c == ",":
            i += 1
            continue
        if c == "]":
            break
        start = i
        depth = 0
        in_str = False
        while i < n:
            ch = blanked[i]
            if in_str:
                if ch == "\\":
                    i += 2
                    continue
                if ch == '"':
                    in_str = False
                i += 1
                continue
            if ch == '"':
                in_str = True
                i += 1
                continue
            if ch in "{[":
                depth += 1
                i += 1
                continue
            if ch in "}]":
                if depth == 0:
                    break  # 配列の閉じ括弧
                depth -= 1
                i += 1
                if depth == 0:
                    break  # 要素の終わり
                continue
            if ch == "," and depth == 0:
                break
            i += 1
        end = i
        while end > start and blanked[end - 1].isspace():
            end -= 1
        spans.append((start, end))
    return spans


def _read_keybindings(path: Path) -> tuple[str, list, str]:
    """(元テキスト, 解析したリスト, 位置保持済みテキスト) を返す。

    Raises:
        OSError: 読めない
        ValueError: JSON として壊れている / 配列ではない
    """
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if not text.strip():
        return text, [], ""
    blanked = _blank_jsonc(text)
    try:
        data = json.loads(blanked)
    except json.JSONDecodeError as e:
        raise ValueError(t("not readable as JSON ({err})").format(err=e)) from e
    if not isinstance(data, list):
        raise ValueError(
            t("the contents are not an array "
              "(VSCode's keybindings.json is an array)"))
    return text, data, blanked


def _entry_indent(blanked: str) -> str:
    """既存の要素に合わせた字下げ。分からなければ VSCode 既定の4スペース。"""
    spans = _item_spans(blanked) if "[" in blanked else []
    if spans:
        line_start = blanked.rfind("\n", 0, spans[0][0]) + 1
        lead = blanked[line_start:spans[0][0]]
        if lead.strip() == "" and lead:
            return lead
    return "    "


def _insert_entry(text: str, entry: dict) -> str:
    """配列の末尾に要素を差し込む。既存の内容・コメント・字下げは触らない。

    VSCode は同じキーの定義が複数あれば **後ろの方** を採用するので、末尾に置く。
    """
    blanked = _blank_jsonc(text)
    close = blanked.rfind("]")
    if close == -1:
        raise ValueError(t("the closing bracket of the array was not found"))

    indent = _entry_indent(blanked)
    body = json.dumps(entry, indent=4, ensure_ascii=False)
    block = "\n".join(indent + line for line in body.splitlines())

    head = blanked[:close].rstrip()
    cut = len(head)  # 最後の要素（または "["）の直後
    need_comma = not (head.endswith("[") or head.endswith(","))
    middle = text[cut:close]  # 最後の要素と "]" の間（空白やコメント）

    if middle.strip() == "":
        middle = "\n"
    return text[:cut] + ("," if need_comma else "") + "\n" + block + middle + text[close:]


def _cut_spans(text: str, blanked: str, spans: list[tuple[int, int]]) -> str:
    """指定した要素を、隣のカンマと区切りの空白ごと切り取る。他の要素には触らない。

    要素の前後にある改行・字下げは書式のためだけの空白なので、コメントを含まない
    範囲に限って一緒に削り、その要素が最初から無かったのと同じ並びに戻す
    （さもないと、切り取った跡に空白だけの行が残って壊れて見える）。

    空白だけかどうかは **元テキスト**（コメントを消していない方）で確かめる。
    blanked はコメントも空白に見えてしまうので、blanked だけで判定すると
    利用者のコメントまで一緒に削ってしまいかねない。
    """
    out = text
    ref = blanked

    def blank_end(i: int) -> int:
        """i から後ろへ、コメントを含まない空白が続く末尾を返す（無ければ i）。"""
        j = i
        while j < len(ref) and ref[j].isspace():
            j += 1
        return j if out[i:j].strip() == "" else i

    def blank_start(i: int) -> int:
        """i から前へ、コメントを含まない空白が続く先頭を返す（無ければ i）。"""
        j = i
        while j > 0 and ref[j - 1].isspace():
            j -= 1
        return j if out[j:i].strip() == "" else i

    for start, end in sorted(spans, reverse=True):
        s, e = start, end
        j = e
        while j < len(ref) and ref[j].isspace():
            j += 1
        if j < len(ref) and ref[j] == ",":
            e = blank_end(j + 1)  # 後ろのカンマと、次の要素までの区切り空白も消す
        else:
            k = s
            while k > 0 and ref[k - 1].isspace():
                k -= 1
            if k > 0 and ref[k - 1] == ",":
                s = k - 1  # 末尾要素なら前のカンマを消す（区切り空白は k..s に含まれ済み）
            else:
                # 前後どちらにもカンマが無い＝配列に残るのはこの要素だけ。
                # "[" と "]" の内側にある空白も、コメントが無ければ一緒に削る。
                s = blank_start(s)
                e = blank_end(e)
        out = out[:s] + out[e:]
        ref = ref[:s] + ref[e:]
    return out


def _is_ours(entry: object) -> bool:
    """このツールが書いたエントリか（今の形式・古い形式の両方）。

    利用者が自分で ctrl+shift+d に別のコマンドを割り当てている場合は False。
    消していいのは自分が書いたものだけ。
    """
    if not isinstance(entry, dict) or entry.get("key") != KEY:
        return False
    cmd = entry.get("command")
    if cmd == KEY_COMMAND:
        return True
    if cmd == LEGACY_KEY_COMMAND:
        args = entry.get("args")
        text = args.get("text", "") if isinstance(args, dict) else ""
        return "open_dashboard.py" in str(text)
    return False


def _is_current(entry: object) -> bool:
    """今の形式（拡張コマンドを直接呼ぶ）で入っているか。"""
    return (
        isinstance(entry, dict)
        and entry.get("key") == KEY
        and entry.get("command") == KEY_COMMAND
    )


def install_keybinding(path: Path) -> tuple[str, str]:
    """キーバインドを登録する。(状態, 説明) を返す。

    状態: added / updated / unchanged / shadowed / conflict / no-vscode / error
    """
    user_dir = path.parent
    if not user_dir.is_dir():
        if not user_dir.parent.is_dir():
            return "no-vscode", (
                t("the VSCode settings folder was not found ({path}). VSCode may "
                  "not be installed, or you may be using Insiders / VSCodium")
                .format(path=user_dir)
            )
        try:
            user_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return "error", t("cannot create {path} ({err})").format(path=user_dir, err=e)

    entry = build_keybinding_entry()

    try:
        text, data, blanked = _read_keybindings(path)
    except OSError as e:
        return "error", t("cannot read {path} ({err})").format(path=path, err=e)
    except ValueError as e:
        # 利用者のファイルが壊れている。上書きすると中身が消えるので触らない。
        return "error", t("{path} cannot be rewritten ({err})").format(path=path, err=e)

    if not text.strip():
        body = json.dumps([entry], indent=4, ensure_ascii=False)
        try:
            write_text_atomic(path, body + "\n")
        except OSError as e:
            return "error", t("cannot write to {path} ({err})").format(path=path, err=e)
        return "added", t("created the file and registered the binding")

    spans = _item_spans(blanked)
    if len(spans) != len(data):  # 解析がずれた。手を出さない方が安全。
        return "error", t("the structure of {path} could not be read fully "
                          "(nothing was changed, to be safe)").format(path=path)

    ours = [i for i, e in enumerate(data) if _is_ours(e)]
    current = [i for i in ours if _is_current(data[i])]
    legacy = [i for i in ours if i not in current]
    foreign = [
        i for i, e in enumerate(data)
        if isinstance(e, dict) and e.get("key") == KEY and i not in ours
    ]

    foreign_names = ", ".join(str(data[i].get("command", "?")) for i in foreign)

    if current and not legacy:
        # VSCode は同じキーの定義が複数あれば後ろを採用する。ours より後ろに別の
        # 割り当てがあると、登録済みでも Ctrl+Shift+D は Subagent Dashboard を開かない。
        if foreign and max(foreign) > max(current):
            return "shadowed", (
                t("it is registered, but a different binding further down ({names}) "
                  "takes precedence, so Ctrl+Shift+D does not open it")
                .format(names=foreign_names)
            )
        return "unchanged", t("already registered (no change)")

    if not current and foreign:
        return "conflict", (
            t("{key} is already bound to a different command ({names}). It was not "
              "registered, so as not to overwrite your own setting")
            .format(key=KEY, names=foreign_names)
        )

    new_text = text
    if legacy:
        new_text = _cut_spans(new_text, blanked, [spans[i] for i in legacy])
    if not current:
        try:
            new_text = _insert_entry(new_text, entry)
        except ValueError as e:
            return "error", t("{path} cannot be rewritten ({err})").format(path=path, err=e)

    if new_text == text:
        return "unchanged", t("already registered (no change)")

    try:
        write_text_atomic(path, new_text)
    except OSError as e:
        return "error", t("cannot write to {path} ({err})").format(path=path, err=e)

    if legacy and current:
        return "updated", t("removed the old-style entry")
    if legacy:
        return "updated", t("replaced the old-style entry with the current one")
    return "added", t("registered")


def remove_our_keybindings(path: Path) -> tuple[str, str]:
    """このツールが書いたエントリだけを取り除く。(状態, 説明) を返す。

    状態: removed / none / missing / error
    ファイルごと消すことはしない。利用者が自分で書いたエントリは残す。
    """
    if not path.is_file():
        return "missing", t("the file does not exist (nothing was done)")

    try:
        text, data, blanked = _read_keybindings(path)
    except OSError as e:
        return "error", t("cannot read {path} ({err})").format(path=path, err=e)
    except ValueError as e:
        return "error", t("{path} cannot be rewritten ({err})").format(path=path, err=e)

    spans = _item_spans(blanked) if text.strip() else []
    if len(spans) != len(data):
        return "error", t("the structure of {path} could not be read fully "
                          "(nothing was changed, to be safe)").format(path=path)

    targets = [spans[i] for i, e in enumerate(data) if _is_ours(e)]
    if not targets:
        return "none", t("there are no entries from this tool (nothing was done)")

    new_text = _cut_spans(text, blanked, targets)
    try:
        write_text_atomic(path, new_text)
    except OSError as e:
        return "error", t("cannot write to {path} ({err})").format(path=path, err=e)
    return "removed", t("removed {n} entries").format(n=len(targets))


def count_our_keybindings(path: Path) -> int:
    """このツールが書いたエントリの数。読めなければ -1。"""
    if not path.is_file():
        return 0
    try:
        _text, data, _blanked = _read_keybindings(path)
    except (OSError, ValueError):
        return -1
    return sum(1 for e in data if _is_ours(e))


# ---------------------------------------------------------------- 処理


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def rewrite_blocks() -> tuple[list[Path], list[Path], list[tuple[Path, str]]]:
    """書き込んである運用ルールを、**いまの表示言語で**書き直す。

    `dash lang <コード>` から呼ぶ。表示言語を変えても、エージェントが実際に読む運用
    ルールは書き込んだときの言語のまま残る。運用ルールの言語は
    「エージェントが `--title` / `--name` / `--mission` / `--headline` を何語で書くか」
    そのものなので、放っておくと **設定は日本語なのにチームは英語で組まれる** という、
    画面のどこを見ても原因の分からない食い違いになる（食い違いは画面の見た目ではなく
    記録の中身に出るため、気づいたときには過去の記録が全部その言語で残っている）。

    書く先は **dashlib.installed_agents() が返したものだけ**。あれは「ブロックがこの
    コピーを指している」CLI しか返さないので、開発用の別コピーで lang を変えても、
    本番の運用ルールを別のディレクトリへ向け替えてしまう事故は起きない。未設定の CLI に
    新しく書き込むこともしない（初期設定は do_install の仕事で、あちらは環境チェックと
    キーバインドまで面倒を見る。言語を選んだだけの人に、それを黙って始めてはいけない）。

    返すのは (書き直したファイル, 既にその言語だったファイル, [(書けなかったファイル, 理由)])。
    **書き換えていないものを「書き直した」と言わない**ために3つに分ける（同じ言語を
    選び直したときに4本とも「書き直した」と出るのは、事実と違う）。**失敗をここで
    握り潰さない**（黙って旧言語のまま残るのが、いちばん気づけない壊れ方）。
    """
    block = build_block(detect_python_command())
    changed: list[Path] = []
    kept: list[Path] = []
    failed: list[tuple[Path, str]] = []
    for key in dashlib.installed_agents():
        target = dashlib.instruction_file(key)
        try:
            existing = target.read_text(encoding="utf-8")
            updated, _action, _tidied = apply_block(existing, block)
            if updated == existing:
                kept.append(target)
                continue
            write_text_atomic(target, updated)
        except (OSError, BrokenMarkerError) as e:
            failed.append((target, str(e)))
            continue
        changed.append(target)
    return changed, kept, failed


def make_launcher_executable() -> str | None:
    if sys.platform == "win32":
        return None
    launcher = HERE / "dash"
    if not launcher.is_file():
        return None
    try:
        mode = launcher.stat().st_mode
        launcher.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return str(launcher)
    except OSError as e:
        print(t("Warning: could not make ./dash executable ({err})").format(err=e),
              file=sys.stderr)
        return None


def _probe_writable(directory: Path) -> str | None:
    """本当に書けるか1ファイル書いて確かめる。書けたら None、駄目なら理由。"""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / f".agent-dashboard-probe-{os.getpid()}"
        probe.write_text("", encoding="utf-8")
        probe.unlink()
        return None
    except OSError as e:
        return str(e)


# 運用ルールに書く手順が指し示すファイル。1つでも欠けると、書いた手順が
# 「実行できないコマンド」になる。
REQUIRED_FILES = [
    Path("dashlib.py"),
    Path("update_state.py"),
    Path("server.py"),
    Path("public") / "index.html",
]


def check_environment(agents: list[str]) -> list[str]:
    """先に進めない条件だけを返す。VSCode の有無などは致命的ではないので含めない。"""
    problems: list[str] = []

    if sys.version_info < (3, 9):
        problems.append(
            t("Python 3.9 or newer is required (this is {v})")
            .format(v=sys.version.split()[0])
        )

    missing = [str(rel) for rel in REQUIRED_FILES if not (HERE / rel).is_file()]
    if missing:
        problems.append(
            t("the following files were not found "
              "(the package may be incomplete): {list}")
            .format(list=", ".join(missing))
        )

    # 実際に書き換える先に書けるか。ここを見ないまま「✓ 書き込み権限 OK」と
    # 出してしまうと、ステップ3で初めて失敗が分かる。
    reason = _probe_writable(dashlib.MISSIONS_DIR)
    if reason:
        problems.append(
            t("cannot write to the mission storage ({path} / {reason})")
            .format(path=dashlib.MISSIONS_DIR, reason=reason)
        )

    for key in agents:
        directory = dashlib.agent_config_dir(key)
        reason = _probe_writable(directory)
        if reason:
            problems.append(
                t("cannot write to the config folder of {name} ({path} / {reason})")
                .format(name=dashlib.agent_label(key), path=directory, reason=reason)
            )

    return problems


def _box(title: str) -> None:
    """ステップの見出し枠。

    訳語に全角が混ざると len では桁が合わないので、幅は dashlib.pad()/clip()
    （全角を2桁として数える）で揃える。
    """
    print("┌" + "─" * 68 + "┐")
    print("│ " + dashlib.pad(dashlib.clip(title, 66), 66) + " │")
    print("└" + "─" * 68 + "┘")


def _row(mark: str, label: str, value: str, width: int) -> None:
    """「  ✓ ラベル    : 値」の1行。ラベルの幅も表示幅で揃える。

    mark が空なら印は付けず、字下げも増やさない（ステップ2の一覧がこれ）。
    """
    head = "  " + mark + " " if mark else "  "
    print(head + dashlib.pad(label, width) + ": " + value)


def do_install(print_only: bool, agent_choice: str = "auto") -> int:
    py = detect_python_command()
    block = build_block(py)
    agents = select_agents(agent_choice)
    targets = [(key, dashlib.instruction_file(key)) for key in agents]
    keybindings_target = keybindings_path()
    legacy_target = legacy_keybindings_path()
    keybinding_entry = build_keybinding_entry()

    # ウィザード形式のヘッダー
    print()
    print("=" * 70)
    print(t("  Subagent Dashboard — installer"))
    print("=" * 70)
    print()

    if print_only:
        print(t("  What would be written (--print, so nothing is actually changed)"))
        print("  --------------------------------------------------")
        print()
        for _, target in targets:
            print(t("What will be added to {name} ({path}):")
                  .format(name=target.name, path=target))
        print(block)
        print()
        print(t("The entry that will be added to keybindings.json ({path}):")
              .format(path=keybindings_target))
        print(json.dumps(keybinding_entry, indent=4, ensure_ascii=False))
        print()
        stale = count_our_keybindings(legacy_target)
        if stale > 0:
            print(t("* The old location ({path}) still holds")
                  .format(path=legacy_target))
            print(t("  {n} invalid entries written earlier by this tool. "
                    "Running this removes them.").format(n=stale))
            print()
        return 0

    # ステップ 1: 環境チェック
    _box(t("Step 1/4: Environment check"))
    print()

    problems = check_environment(agents)
    if problems:
        print(t("  ✗ The following problems were found:"))
        for p in problems:
            print(t("    - {problem}").format(problem=p))
        print()
        print(t("  Please solve these problems and run this again."))
        print()
        return 1

    _row("✓", t("Python version"), sys.version.split()[0], 21)
    _row("✓", t("Platform"), sys.platform, 21)
    _row("✓", t("File layout"),
         t("OK ({n} files, all present)").format(n=len(REQUIRED_FILES)), 21)
    _row("✓", t("Write permission"),
         t("OK ({missions} / {config})").format(
             missions=dashlib.MISSIONS_DIR,
             config=" / ".join(str(dashlib.agent_config_dir(k)) for k in agents)), 21)
    _row("✓", t("Tool location"), str(HERE), 21)

    # VSCode のキーバインドは無くても致命的ではない（方法1と方法3で開ける）ので、
    # ここでは止めずに状況だけ伝える。
    if keybindings_target.parent.is_dir() or keybindings_target.parent.parent.is_dir():
        reason = _probe_writable(keybindings_target.parent)
        if reason:
            _row("⚠", t("VSCode keybinding"),
                 t("cannot write ({reason})").format(reason=reason), 21)
        else:
            _row("✓", t("VSCode keybinding"),
                 t("OK ({path})").format(path=keybindings_target.parent), 21)
    else:
        _row("⚠", t("VSCode keybinding"),
             t("the settings folder was not found ({path})")
             .format(path=keybindings_target.parent), 21)
    print()

    # CLAUDE.md にはこのファイルの実際の場所が焼き込まれ、記録の保存先（missions/）も
    # そこを基準に決まる。組み立て途中のコピーを指定してしまうと、Claude が書く先と
    # サーバーが読む先が別ディレクトリに分かれ、画面に何も出ないまま気づけなくなる。
    if any(part == "dist" for part in HERE.parts):
        print(t("  ⚠ You are running this from inside the distribution (under dist/)."))
        print(t("     If you go on, records will be stored in {path}.")
              .format(path=HERE / "missions"))
        print(t("     Move the unpacked folder outside dist/ before running this."))
        print()

    # ステップ 2: 自動検出
    _box(t("Step 2/4: Automatic detection of the environment"))
    print()
    _row("", t("Dashboard location"), str(HERE), 23)
    _row("", t("Python command"), py, 23)
    _row("", t("Mission storage"), str(dashlib.MISSIONS_DIR), 23)
    # 見つかった CLI を1行ずつ出す。まとめて1行にすると、2つ目が入っていることに
    # 気づかないまま「片方にしか書かれていない」と誤解される。
    for key, target in targets:
        _row("", t("Config file ({name})").format(name=dashlib.agent_label(key)),
             str(target), 23)
    _row("", t("VSCode keybinding"), str(keybindings_target), 23)
    stale = count_our_keybindings(legacy_target)
    if stale > 0:
        print(t("  (leftovers in the old location: {path} / {n})")
              .format(path=legacy_target, n=stale))
    print()

    # ステップ 3: 設定の書き込み
    _box(t("Step 3/4: Writing to the config files"))
    print()

    # 書けない CLI が1つでもあれば止める。**残りに書いて成功と表示しない。**
    # 片方だけ書けた状態は、次に起動する CLI によって動いたり動かなかったりする
    # 一番たちの悪い壊れ方で、しかも成功と出ていたら誰も疑わない。
    for _, target in targets:
        name = target.name
        existing = ""
        if target.is_file():
            try:
                existing = target.read_text(encoding="utf-8")
            except OSError as e:
                print(t("  ✗ Error: cannot read {path} ({err})")
                      .format(path=target, err=e), file=sys.stderr)
                return 1

        try:
            updated, action, tidied = apply_block(existing, block)
        except BrokenMarkerError as e:
            print(t("  ✗ Error: {path} cannot be touched ({err})")
                  .format(path=target, err=e), file=sys.stderr)
            print(t("    Writing now would wipe out your own text the next time "
                    "--uninstall runs."), file=sys.stderr)
            print(t("    Pair up the markers in {path}, then run this again.")
                  .format(path=target), file=sys.stderr)
            return 1

        if updated == existing:
            print(t("  ✓ {name} is already up to date (no change)").format(name=name))
            continue

        try:
            write_text_atomic(target, updated)
        except OSError as e:
            print(t("  ✗ Error: cannot write to {path} ({err})")
                  .format(path=target, err=e), file=sys.stderr)
            return 1

        if action == "created":
            print(t("  ✓ {name} was created.").format(name=name))
        elif action == "appended":
            print(t("  ✓ The settings were appended to {name}.").format(name=name))
        elif tidied:
            print(t("  ✓ {name} was updated "
                    "(also tidied up {n} duplicated old blocks).")
                  .format(name=name, n=tidied))
        else:
            print(t("  ✓ {name} was updated.").format(name=name))
        print("    " + str(target))
        print(t("    (only the marked block is updated; "
                "anything already there is kept)"))

    # keybindings.json を更新（VSCode が実際に読む場所）
    kb_status, kb_msg = install_keybinding(keybindings_target)
    if kb_status in ("added", "updated"):
        print(t("  ✓ keybindings.json was updated ({msg})").format(msg=kb_msg))
        print("    " + str(keybindings_target))
        print(t("    (Ctrl+Shift+D → agentDashboard.open. "
                "It works once the extension is installed.)"))
    elif kb_status == "unchanged":
        print(t("  ✓ keybindings.json needed no change ({msg})").format(msg=kb_msg))
    elif kb_status in ("conflict", "shadowed"):
        if kb_status == "shadowed":
            print(t("  ⚠ Ctrl+Shift+D does not work ({msg})").format(msg=kb_msg))
        else:
            print(t("  ⚠ Ctrl+Shift+D was not registered ({msg})").format(msg=kb_msg))
        print(t("    Open {path} and either drop that binding, or bind another key")
              .format(path=keybindings_target))
        print(t('    with {{"key": "<the key you like>", "command": "{cmd}"}}.')
              .format(cmd=KEY_COMMAND))
    elif kb_status == "no-vscode":
        print(t("  ⚠ Ctrl+Shift+D was not registered ({msg})").format(msg=kb_msg))
    else:
        print(t("  ⚠ Warning: keybindings.json could not be updated ({msg})")
              .format(msg=kb_msg), file=sys.stderr)

    # 以前のバージョンが間違って書いた場所（~/.vscode）の後始末。
    # VSCode はここを読まないので、残っていても効かないが、見た人を混乱させる。
    if legacy_target != keybindings_target:
        stale = count_our_keybindings(legacy_target)
        if stale > 0:
            st, sm = remove_our_keybindings(legacy_target)
            if st == "removed":
                print(t("  ✓ Cleaned up the dead entries in the old location ({msg})")
                      .format(msg=sm))
                print("    " + str(legacy_target))
                print(t("    (VSCode does not read this location. "
                        "Other entries were left alone.)"))
            else:
                print(t("  ⚠ {n} dead entries remain in the old location: {path}")
                      .format(n=stale, path=legacy_target), file=sys.stderr)
                print(t("    They could not be cleaned up ({msg}). "
                        "Deleting them by hand is fine.").format(msg=sm),
                      file=sys.stderr)
        elif stale < 0:
            print(t("  ⚠ The file in the old location could not be read: {path}")
                  .format(path=legacy_target), file=sys.stderr)
            print(t("    Dead entries written earlier by this tool may still be there."),
                  file=sys.stderr)

    launcher = make_launcher_executable()
    if launcher:
        print(t("  ✓ Made the launcher executable: ./dash"))

    print()

    # ステップ 4: 完了
    _box(t("Step 4/4: Setup complete!"))
    print()
    if kb_status in ("added", "updated", "unchanged"):
        print(t("  🎉 The installation is complete!"))
    else:
        print(t("  The installation is complete "
                "(Ctrl+Shift+D was not registered)."))
    print()
    print(t("  You can open the dashboard in these ways:"))
    print()
    print(t("  [Option 1] Start it from the command line (recommended)"))
    launcher_name = "dash.cmd" if sys.platform == "win32" else "dash"
    print("    " + str(HERE / launcher_name) + " serve --open")
    print()
    if kb_status in ("added", "updated", "unchanged"):
        print(t("  [Option 2] A VSCode keyboard shortcut"))
        print(t("    Press Ctrl+Shift+D "
                "(it works once you install the extension below)"))
    else:
        print(t("  [Option 2] A VSCode keyboard shortcut "
                "→ not registered this time"))
        print(t("    See the ⚠ above for why. Options 1 and 3 work as they are."))
    print()
    print(t("  [Option 3] The VSCode extension (more convenient)"))
    print("    " + str(HERE / launcher_name) + " ext install")
    print(t("    then click the robot icon at the far left"))
    print()
    print("  ──────────────────────────────────────────────────────────────────")
    print(t("  📖 The manual (it opens once the server is running)"))
    print("     http://127.0.0.1:3939/manual.html")
    print()
    print(t("  🔍 If something goes wrong, run the diagnostics script"))
    print("     python " + str(HERE / "diagnose.py"))
    print("  ──────────────────────────────────────────────────────────────────")
    print()
    print("=" * 70)
    print()
    return 0


def do_list_agents() -> int:
    """知っている CLI と、それぞれの書き込み先・いまの状態を並べる。

    「対応しているのか」「どこに書かれるのか」「もう書いてあるのか」の3つは、
    別々の場所を見ないと分からないと必ず取り違えられる。1画面に並べる。
    """
    installed = set(dashlib.installed_agents())
    present = set(dashlib.present_agents())
    builtin_keys = {e["key"] for e in dashlib.BUILTIN_AGENT_TARGETS}

    print()
    print(t("The CLIs this tool knows about:"))
    print()
    for entry in dashlib.agent_targets():
        key = entry["key"]
        if key in installed:
            mark, state = "✓", t("written")
        elif key in present:
            mark, state = "・", t("installed, not written yet")
        else:
            mark, state = " ", t("not found on this machine")
        origin = "" if key in builtin_keys else t(" (added by you)")
        _row(mark, key, "%s%s" % (dashlib.agent_label(key), origin), 12)
        print("       " + str(dashlib.instruction_file(key)) + "  — " + state)
    print()
    print(t("For a CLI that is not on this list, point at its file directly:"))
    print("  python " + str(HERE / "install.py") + " --agent-file <path>")
    print(t("Entries you add are remembered in {path}").format(
        path=dashlib.agents_file()))
    print()
    return 0


def do_uninstall() -> int:
    # 取り消しは**対応 CLI 全部**を見る（--agent では絞らない）。書いた側は自動判定で
    # 増えることがあるので、消す側を絞ると「入れた覚えのない所に残る」ようになる。
    targets = [(key, dashlib.instruction_file(key)) for key in dashlib.agent_keys()]
    keybindings_target = keybindings_path()
    legacy_target = legacy_keybindings_path()
    print()
    for _, target in targets:
        print("  " + dashlib.pad(t("Config file"), 20) + str(target))
    print("  " + dashlib.pad(t("Keybinding settings"), 20) + str(keybindings_target))
    if legacy_target != keybindings_target:
        print("  " + dashlib.pad(t("(the old location)"), 20) + str(legacy_target))
    print()

    removed_any = False
    failed = False

    # 運用ルールファイルから削除
    for _, target in targets:
        name = target.name
        if not target.is_file():
            print(t("  {name} does not exist.").format(name=name))
            continue
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError as e:
            print(t("Error: cannot read {path} ({err})").format(path=target, err=e),
                  file=sys.stderr)
            return 1

        cleaned, removed = remove_block(existing)
        if removed:
            try:
                write_text_atomic(target, cleaned)
            except OSError as e:
                print(t("Error: cannot write to {path} ({err})")
                      .format(path=target, err=e), file=sys.stderr)
                return 1
            print(t("  Removed the settings from {name} "
                    "(anything else was left alone).").format(name=name))
            removed_any = True
        else:
            print(t("  {name} has no settings from this tool.").format(name=name))

    # keybindings.json から削除（今の場所と、以前間違って書いていた場所の両方）
    seen: set[Path] = set()
    for label, path in (("keybindings.json", keybindings_target),
                        (t("the keybindings.json in the old location"), legacy_target)):
        if path in seen:
            continue
        seen.add(path)
        status, msg = remove_our_keybindings(path)
        if status == "removed":
            print(t("  Removed the settings from {label} ({msg}).")
                  .format(label=label, msg=msg))
            print(t("    (other entries written by you were left alone)"))
            removed_any = True
        elif status == "error":
            print(t("  Warning: deleting from {label} failed ({msg})")
                  .format(label=label, msg=msg), file=sys.stderr)
            failed = True
        else:
            print("  " + label + ": " + msg)

    if not removed_any:
        print(t("  Nothing was deleted."))
        print()
        return 1 if failed else 0

    print(t("  The mission records are still there: {path}")
          .format(path=dashlib.MISSIONS_DIR))
    print()
    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="install.py",
        description=t("First-time setup for the Subagent Dashboard"),
    )
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help=t("only show what would be written (changes nothing)"))
    parser.add_argument("--uninstall", action="store_true",
                        help=t("undo the settings that were written"))
    parser.add_argument("--agent", choices=("auto", "all") + dashlib.agent_keys(),
                        default="auto",
                        help=t("which CLI to write the operating rules for "
                               "(the default writes to every one that is installed)"))
    parser.add_argument("--agent-file", dest="agent_file", default="",
                        help=t("write to this file as well, for a CLI that is not "
                               "in the list (it gets remembered)"))
    parser.add_argument("--list-agents", dest="list_agents", action="store_true",
                        help=t("show the CLIs this tool knows about, and stop"))
    args = parser.parse_args()

    if args.list_agents:
        sys.exit(do_list_agents())

    # --agent-file は「ここにも書く」であって「ここだけに書く」ではない。登録だけ
    # 済ませ、選び方は --agent に任せる（既定の auto は登録した分を必ず含む）。
    choice = args.agent
    if args.agent_file:
        try:
            register_agent_file(args.agent_file)
        except (ValueError, OSError) as e:
            print(t("Error: {err}").format(err=e), file=sys.stderr)
            sys.exit(1)

    code = do_uninstall() if args.uninstall else do_install(args.print_only, choice)
    sys.exit(code)


if __name__ == "__main__":
    main()
