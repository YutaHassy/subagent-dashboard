#!/usr/bin/env python3
"""コマンド出力の言語切り替え。

英語を原文とし、日本語・中国語（簡体）・韓国語を載せる。

**キーは英語の原文そのもの**にしてある（gettext と同じやり方）。キー名を別に
発明すると、コードを読む側が `t("cli.start.done")` から実際に出る文を想像できなく
なる。原文をそのまま書いておけば、翻訳表が無くてもコードだけで意味が読める。

    from i18n import t
    print(t("Wrote display-test data."))
    print(t("  Target project: {name}").format(name=name))

訳が無いキーはそのまま原文（英語）を返す。**翻訳の抜けで例外にはしない。**
このツールは「黙って壊れない」ことを優先しているので、訳が1つ足りないだけで
コマンドが落ちるのは方針に反する。

言語の決まり方（上から順に、最初に決まったものを使う）:

    1. 環境変数 AGENT_DASHBOARD_LANG（en / ja / zh / ko）
    2. 保存された設定（dashlib が読み込んで set_lang() を呼ぶ）
    3. 環境変数 LC_ALL / LC_MESSAGES / LANG
    4. OS の表示言語（Windows は GetUserDefaultUILanguage、他は locale）
    5. 英語

このモジュールは **dashlib を import しない。** 逆に dashlib がこちらを import する
ので、参照を双方向にすると循環する。保存された設定を読むのは DATA_HOME を知って
いる dashlib の仕事で、こちらは set_lang() で受け取るだけにしてある。
"""

from __future__ import annotations

import os
import sys

SUPPORTED = ("en", "ja", "zh", "ko")

ENV_LANG = "AGENT_DASHBOARD_LANG"

#: セレクタや一覧に出す名前。**その言語自身の表記**にする。
LANG_LABELS = {
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
    "ko": "한국어",
}


def normalize(tag) -> str | None:
    """'ja_JP.UTF-8' や 'zh-Hant-TW' を、対応している4つのどれかへ寄せる。

    対応外なら None を返す（呼び手が次の候補へ進めるように）。
    """
    if not tag or not isinstance(tag, str):
        return None
    low = tag.strip().lower().replace("_", "-")
    if not low:
        return None
    if low.startswith("en"):
        return "en"
    if low.startswith("ja"):
        return "ja"
    if low.startswith("ko"):
        return "ko"
    # 繁体字も簡体字の表へ寄せる。訳が無いよりは読めるほうがよいという判断。
    if low.startswith("zh"):
        return "zh"
    return None


def _from_env() -> str | None:
    for name in (ENV_LANG, "LC_ALL", "LC_MESSAGES", "LANG"):
        hit = normalize(os.environ.get(name))
        if hit:
            return hit
    return None


def _from_os() -> str | None:
    """OS の表示言語。**環境変数より弱い**ので、呼ぶ順は _from_env のあと。"""
    if sys.platform == "win32":
        # Windows のコンソールでは LANG が入っていないのが普通なので、ここが本命。
        # ctypes が使えない環境（一部の組み込み Python）でも落とさない。
        try:
            import ctypes

            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            primary = lcid & 0x3FF
            return {0x09: "en", 0x11: "ja", 0x04: "zh", 0x12: "ko"}.get(primary)
        except Exception:
            return None
    try:
        import locale

        loc = locale.getlocale()[0]
        if not loc:
            # setlocale していないと getlocale() が None を返すことがある。
            # 既定ロケールを一度読みに行く（読めなければ諦める）。
            try:
                loc = locale.setlocale(locale.LC_CTYPE, "")
            except Exception:
                loc = None
        return normalize(loc)
    except Exception:
        return None


def detect() -> str:
    """環境から言語を決める。保存された設定はここでは見ない（set_lang で受け取る）。"""
    return _from_env() or _from_os() or "en"


_lang = detect()

#: 環境変数で明示されていたか。set_lang() が保存設定で上書きしてよいかの判定に使う。
#: **環境変数のほうが強い**（その場限りで切り替えたい人の指定を保存値で潰さない）。
_forced = _from_env() is not None


def get_lang() -> str:
    return _lang


def set_lang(lang, *, force: bool = False) -> str:
    """言語を差し替える。

    :param lang: 'en' / 'ja' / 'zh' / 'ko'（'ja_JP' のような書き方も受ける）
    :param force: True なら環境変数の指定より優先する（``--lang`` のような
        明示的な指定に使う）。既定では環境変数の指定を尊重して何もしない。
    """
    global _lang
    hit = normalize(lang)
    if not hit:
        return _lang
    if _forced and not force:
        return _lang
    _lang = hit
    return _lang


def t(text: str) -> str:
    """原文（英語）を今の言語へ訳す。訳が無ければ原文をそのまま返す。"""
    if _lang == "en":
        return text
    return CATALOG.get(_lang, {}).get(text, text)


def label(lang: str) -> str:
    return LANG_LABELS.get(lang, lang)


# ---------------------------------------------------------------- 翻訳表
#
# 中身は i18n_data*.py にある。**訳が読めなくてもコマンドは動かなければならない**
# ので、読み込みに失敗したら英語のまま進む（ここで落とすと、翻訳ファイルが1つ
# 壊れただけで update_state.py が使えなくなる）。
#
# ファイルを分けてあるのは、1つが 10 万文字を超えると編集のたびに全体を読み直す
# ことになるため。**どのファイルに入れても引き方は同じ**なので、置き場所は
# 「どのコマンドの文か」で決めてよい。同じ原文が複数のファイルにあった場合は、
# 先に読んだほうを残す（あとから読んだ表で黙って上書きされると、どちらが出るのか
# 追えなくなる）。
CATALOG: dict = {}


def _merge(table) -> None:
    for lang, pairs in (table or {}).items():
        dest = CATALOG.setdefault(lang, {})
        for src, translated in pairs.items():
            dest.setdefault(src, translated)


for _mod in ("i18n_data", "i18n_data_update", "i18n_data_install"):
    try:
        _merge(__import__(_mod).CATALOG)
    except Exception:  # pragma: no cover - 配布物が欠けたときの保険
        pass


def missing(lang: str) -> list[str]:
    """その言語で訳が入っていない原文を返す。翻訳の抜けを数える補助。"""
    have = CATALOG.get(lang, {})
    base = set()
    for table in CATALOG.values():
        base |= set(table.keys())
    return sorted(k for k in base if k not in have)
