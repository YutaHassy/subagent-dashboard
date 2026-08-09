#!/usr/bin/env python3
"""Subagent Dashboard — 画面の配線検査（開発用）

    python check_wiring.py                public/index.html を検める
    python check_wiring.py <file.html>    別のファイルを検める（変異試験に使う）

画面の JS が `need(セレクタ)` で引いている要素が、**同じファイルの markup に実在するか**
だけを検める。合わなければ 0 以外で終わるので、`build_vsix.py` の `build()` から最初に
呼べば、食い違ったまま .vsix を作ることができなくなる。

**なぜ機械に検めさせるのか。** この食い違いは人が気をつけて防げる種類のものではない。
Subagent Dashboard は開いたまま放置するページで、1秒ごとにポーリングはするが自分をリロードしない。
開いた状態で HTML の `id` を書き換えても、すでに走っている旧スクリプトは影響を受けずに
動き続ける。破綻が表に出るのは**次に新規ロードした瞬間**なので、改名した本人の画面では
最後まで正常に見える。v0.2.5 では実際にこれが出荷され、利用者からは「サーバーの不調」と
見分けが付かない沈黙にしか見えなかった。

判定するのは `need()` を通ったものだけ。`need()` は「静的な markup に必ずある」という
約束の要素にしか使っていないので、無ければ食い違いだと断定できる。JS が組み立てる要素
（`.tab-item` や `.agent`）は約束が違うので対象外にする。

**照合先は `<script>` の外側の markup だけ。** スクリプトの中の文字列まで数えると、JS が
自分で書き出した名前を自分で確かめることになって、肝心の食い違いを見逃す（この画面は
`'<div class="c-top">…'` のような組み立て用の文字列を大量に持っている）。逆に
`<template>`（`#team-tpl`）の中身は markup として扱う。`renderTeam()` が clone して使う
**静的な骨組み**で、そこの class を改名すれば同じ事故が起きる場所だから。

外部ライブラリは使いません（標準ライブラリの `html.parser` だけ）。
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib  # noqa: E402  （日本語を出すので、他のスクリプトと同じ下ごしらえを使う）

dashlib.use_utf8_stdio()

DEFAULT_HTML = HERE / "public" / "index.html"

# 終了タグを書かない要素。閉じ忘れの巻き戻し（handle_endtag）でこれらを待ってしまうと、
# 後続の要素が全部この中にぶら下がり、親子関係（= 第2引数の検査）が嘘になる。
VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


# ==== markup を木にする ================================================


class _Node:
    """要素1つ。セレクタ照合に要るものだけ持つ（属性の全部は要らない）。"""

    __slots__ = ("tag", "ids", "classes", "parent", "children", "line")

    def __init__(self, tag: str, attrs, parent, line: int):
        self.tag = tag
        self.parent = parent
        self.children: list[_Node] = []
        self.line = line
        self.ids: set[str] = set()
        self.classes: set[str] = set()
        for name, value in attrs or ():
            if not value:
                continue
            if name == "id":
                self.ids.update(value.split())
            elif name == "class":
                self.classes.update(value.split())

    def __repr__(self) -> str:  # 失敗時の読みやすさのためだけ
        return f"<{self.tag} {self.line}行目>"


def _descendants(node: _Node):
    """その要素の子孫を順に返す（自分自身は含めない）。"""
    for child in node.children:
        yield child
        yield from _descendants(child)


class _MarkupParser(HTMLParser):
    """markup を粗く木にしつつ、`<script>` の中身を別に集める。

    `<script>` の中のタグは要素にならない（HTMLParser が CDATA として素通しするため）。
    これがこの道具の肝で、JS が文字列で持っている `'<div class="c-top">'` のたぐいを
    「markup に在る」と数えないための仕掛けでもある。

    閉じ忘れ・閉じ過ぎに耐えるよう、終了タグは**同じ名前が積まれている所まで巻き戻す**
    方式にした。ここで例外にすると、検査したい食い違いより先に道具が落ちてしまう。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#document", (), None, 0)
        self._stack = [self.root]
        self.scripts: list[tuple[int, str]] = []   # [(<script> の行番号, 中身)]
        self._script: tuple[int, list[str]] | None = None

    def _open(self, tag: str, attrs, closed: bool) -> _Node:
        node = _Node(tag, attrs, self._stack[-1], self.getpos()[0])
        self._stack[-1].children.append(node)
        if not closed and tag not in VOID_TAGS:
            self._stack.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        self._open(tag, attrs, False)
        if tag == "script":
            self._script = (self.getpos()[0], [])

    def handle_startendtag(self, tag, attrs):
        self._open(tag, attrs, True)

    def handle_data(self, data):
        if self._script is not None:
            self._script[1].append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            line, buf = self._script
            self.scripts.append((line, "".join(buf)))
            self._script = None
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                del self._stack[i:]
                return
        # 対応する開始タグが無い終了タグは黙って捨てる（木を壊さない）


# ==== セレクタ（CSS のごく一部）========================================


class SelectorUnsupported(ValueError):
    """読めないセレクタ。**黙って合格にはしない。**

    読めないものを「在ることにする」と、見張りが居ないのと同じになる。逆に落として
    おけば、その形を使いたくなった人がここに追記することになる。
    """


_COMPOUND = re.compile(r"^(?P<tag>\*|[A-Za-z][A-Za-z0-9_-]*)?(?P<rest>(?:[#.][A-Za-z_][A-Za-z0-9_-]*)+)?$")
_PART = re.compile(r"[#.][A-Za-z_][A-Za-z0-9_-]*")


def parse_selector(sel: str) -> list[tuple[str | None, tuple]]:
    """`#id` / `.class` / タグ名 と、その並び（子孫・`>`）だけを読む。

    返すのは [(結合子, (タグ, id 集合, class 集合)), ...]（左から右）。結合子は先頭が
    None、以降は " "（子孫）か ">"（子）。属性セレクタや擬似クラスは need() では一度も
    使っていないので、読めなければ SelectorUnsupported を投げる。
    """
    text = " ".join(sel.split())
    if not text:
        raise SelectorUnsupported("空のセレクタ")
    if "," in text:
        raise SelectorUnsupported(f"カンマ区切りは読めません: {sel}")

    steps: list[tuple[str | None, tuple]] = []
    combinator: str | None = None
    for token in re.findall(r">|[^\s>]+", text):
        if token == ">":
            if not steps:
                raise SelectorUnsupported(f"'>' で始まっています: {sel}")
            combinator = ">"
            continue
        m = _COMPOUND.match(token)
        if not m or (not m.group("tag") and not m.group("rest")):
            raise SelectorUnsupported(f"この形は読めません: {sel}")
        ids, classes = set(), set()
        for part in _PART.findall(m.group("rest") or ""):
            (ids if part[0] == "#" else classes).add(part[1:])
        steps.append((combinator, (m.group("tag"), ids, classes)))
        combinator = " "
    if combinator == ">":
        raise SelectorUnsupported(f"'>' で終わっています: {sel}")
    return steps


def _match_compound(node: _Node, compound: tuple) -> bool:
    tag, ids, classes = compound
    if tag and tag != "*" and node.tag != tag:
        return False
    return ids <= node.ids and classes <= node.classes


def _matches(node: _Node, steps: list) -> bool:
    """右から左へ照合する（ブラウザと同じ順）。"""
    combinator, compound = steps[-1]
    if not _match_compound(node, compound):
        return False
    rest = steps[:-1]
    if not rest:
        return True
    if combinator == ">":
        return node.parent is not None and _matches(node.parent, rest)
    ancestor = node.parent
    while ancestor is not None:
        if _matches(ancestor, rest):
            return True
        ancestor = ancestor.parent
    return False


def select_all(scope: _Node, steps: list) -> list[_Node]:
    """scope の子孫から、そのセレクタに合うものを全部返す（querySelectorAll 相当）。"""
    return [n for n in _descendants(scope) if _matches(n, steps)]


# ==== need() の呼び出しを拾う ==========================================

# need('#foo') / need('.bar', elBaz) の両方。第1引数が文字列リテラルのものだけを拾う
# （変数を渡している呼び出しは、静的には何を引くのか分からないので数えない）。
_NEED_CALL = re.compile(
    r"need\(\s*(?P<q>['\"`])(?P<sel>(?:\\.|(?!(?P=q)).)*?)(?P=q)"
    r"\s*(?:,\s*(?P<root>[A-Za-z_$][A-Za-z0-9_$]*)\s*)?\)",
    re.S,
)

# 直前が「const elDlg = 」なら、その変数名は以後この要素を指す。第2引数（親）を
# 辿るのに使う。
_ASSIGN_TAIL = re.compile(r"(?:const|let|var)\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*$")

# 正規表現リテラルが始まりうる位置の直前文字（除算の '/' と見分けるための定石）。
_REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%~^<>")


class _Call:
    """1つの need() 呼び出し。"""

    __slots__ = ("selector", "root_name", "var_name", "line")

    def __init__(self, selector: str, root_name: str | None, var_name: str | None, line: int):
        self.selector = selector
        self.root_name = root_name
        self.var_name = var_name
        self.line = line

    @property
    def key(self) -> tuple:
        return (self.line, self.selector, self.root_name)


def _blank_js_comments(text: str) -> str:
    """コメントを**同じ長さの空白に置き換える**（消さない）。

    消すと位置がずれて「何行目の need() か」を出せなくなる。install.py の JSONC 処理と
    同じ手。文字列と正規表現リテラルは中身を読み飛ばすだけで、そのまま残す（need() の
    引数は文字列なので、消してしまっては元も子もない）。

    コメントを潰すのは、説明文に書いた `need('#foo')` を本物の要求と数えないため。
    見張りが幻の要求で赤くなると、次からは誰も真に受けなくなる。
    """
    out = list(text)
    n = len(text)
    i = 0
    prev = ""          # 直前の意味のある1文字（正規表現リテラルの判定に使う）
    while i < n:
        c = text[i]
        if c in "'\"`":
            quote = c
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            prev = quote
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            end = n if end == -1 else end + 2
            for k in range(i, end):
                if text[k] != "\n":
                    out[k] = " "
            i = end
            continue
        if c == "/" and (prev == "" or prev in _REGEX_PRECEDERS):
            i += 1                      # 正規表現リテラル。中の // や引用符に騙されない
            in_class = False
            while i < n:
                ch = text[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == "\n":
                    break
                if ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    i += 1
                    break
                i += 1
            prev = "/"
            continue
        if not c.isspace():
            prev = c
        i += 1
    return "".join(out)


def _find_calls(script: str, first_line: int) -> list[_Call]:
    calls: list[_Call] = []
    for m in _NEED_CALL.finditer(script):
        head_start = script.rfind("\n", 0, m.start()) + 1
        assign = _ASSIGN_TAIL.search(script[head_start:m.start()])
        calls.append(_Call(
            selector=m.group("sel"),
            root_name=m.group("root"),
            var_name=assign.group("name") if assign else None,
            line=first_line + script.count("\n", 0, m.start()),
        ))
    return calls


# ==== 検査 =============================================================


class Result:
    """検査の結果。`problems` が空なら合格。"""

    def __init__(self, path: Path):
        self.path = path
        self.calls: list[_Call] = []
        self.scoped = 0                     # 第2引数（親）付きの呼び出しの数
        self.problems: list[str] = []       # 1件でもあれば不合格
        self.notes: list[str] = []          # 落とさないが伝えること

    @property
    def ok(self) -> bool:
        return not self.problems


def inspect(html_path: Path) -> Result:
    """1ファイルを検める。**ここでは何も印字しない**（呼び手で出し分けるため）。"""
    result = Result(html_path)
    text = html_path.read_text(encoding="utf-8")

    parser = _MarkupParser()
    parser.feed(text)
    parser.close()

    for first_line, script in parser.scripts:
        found = _find_calls(_blank_js_comments(script), first_line)
        result.calls.extend(found)
        # 安全網。コメント潰しが行き過ぎて**本物の need() を落としていないか**を、
        # 素の本文と数を突き合わせて確かめる。黙って減るのが一番まずい。
        kept = {c.key for c in found}
        for c in _find_calls(script, first_line):
            if c.key not in kept:
                result.notes.append(
                    f"{c.line}行目の need('{c.selector}') はコメントの中と判断して数えませんでした"
                )

    if not result.calls:
        result.problems.append(
            "need() の呼び出しが1つも見つかりませんでした"
            "（この道具か画面のどちらかが、想定と違う形になっています）"
        )
        return result

    varmap = {c.var_name: c for c in result.calls if c.var_name}

    for call in result.calls:
        if call.root_name:
            result.scoped += 1
        try:
            steps = parse_selector(call.selector)
        except SelectorUnsupported as e:
            result.problems.append(f"{call.line}行目 need('{call.selector}') … {e}")
            continue

        scope, why = _scope_nodes(call, varmap, parser.root, result)
        if scope is None:
            result.problems.append(
                f"{call.line}行目 need('{call.selector}', {call.root_name}) … {why}"
            )
            continue

        if any(select_all(node, steps) for node in scope):
            continue

        # 親を need() まで辿れたときだけ「どこの中を探したか」を書く。辿れなかった
        # ものは文書全体を探しているので、書くと嘘になる（その旨は notes に出ている）。
        parent = varmap.get(call.root_name) if call.root_name else None
        where = f"（{call.root_name} ＝ {parent.selector} の中）" if parent else ""
        result.problems.append(
            f"{call.line}行目 need('{call.selector}') … markup にありません{where}"
        )

    return result


def _scope_nodes(call: _Call, varmap: dict, root: _Node, result: Result, seen: tuple = ()):
    """この呼び出しが探す範囲を返す。(要素のリスト, "") か (None, 理由)。

    親を指定した need('.dialog-box', elDlg) は、`const elDlg = need('#dialog-overlay')`
    まで辿って**その中に在るか**を見る。入れ子の class 名だけがずれた食い違いは、
    文書全体から探していると素通りしてしまう。
    """
    if not call.root_name:
        return [root], ""
    if call.root_name in seen:
        return None, f"親 {call.root_name} の参照が循環しています"

    parent = varmap.get(call.root_name)
    if parent is None:
        # need() 以外で作られた要素を親に渡している。何を指すか静的には辿れないので、
        # 文書全体から探して**落とさずに知らせる**（辿れないことを不合格にすると、
        # 正しい書き方まで止めてしまう）。
        result.notes.append(
            f"{call.line}行目 need('{call.selector}', {call.root_name}) … "
            f"{call.root_name} を need() まで辿れないので、文書全体から探しました"
        )
        return [root], ""

    scope, why = _scope_nodes(parent, varmap, root, result, seen + (call.root_name,))
    if scope is None:
        return None, why
    try:
        steps = parse_selector(parent.selector)
    except SelectorUnsupported as e:
        return None, f"親のセレクタが読めません（{e}）"

    found: list[_Node] = []
    for node in scope:
        found.extend(select_all(node, steps))
    if not found:
        return None, f"親 '{parent.selector}' が markup にないので確かめられません"
    return found, ""


# ==== 表示 =============================================================


def report(result: Result) -> None:
    print(f"画面の配線検査: {result.path}")
    print(f"  need() が引いているセレクタ: {len(result.calls)} 件"
          f"（うち親を指定したもの {result.scoped} 件）")
    for note in result.notes:
        print(f"  ・{note}")
    if result.ok:
        print("  ✓ すべて markup（<script> の外）に実在しました")
        return
    print(f"  ✗ {len(result.problems)} 件が合いません:")
    for problem in result.problems:
        print(f"      {problem}")
    print()
    print("    HTML と JS のどちらかを改名して、もう片方が追随していない可能性があります。")
    print("    このまま出すと、次に**新規ロード**した画面で「画面に不具合」が出ます")
    print("    （開いたままの画面は最後まで正常に見えるので、手元では気づけません）。")


def main(argv: list[str] | None = None) -> int:
    """0 なら合格。build_vsix.py の build() はこの戻り値だけを見ればよい。"""
    parser = argparse.ArgumentParser(
        prog="check_wiring.py",
        description="画面の JS が引いているセレクタが markup に実在するかを検める",
    )
    parser.add_argument("html", nargs="?", default=str(DEFAULT_HTML),
                        help=f"検めるファイル（既定: {DEFAULT_HTML}）")
    args = parser.parse_args(argv)

    path = Path(args.html).expanduser()
    try:
        result = inspect(path)
    except OSError as e:
        print(f"配線検査: {path} を読めません（{e}）", file=sys.stderr)
        return 2
    report(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
