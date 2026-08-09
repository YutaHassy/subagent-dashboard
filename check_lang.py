#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subagent Dashboard — 言語設定がエージェントの記述に反映されるかの検査（開発用）

    python check_lang.py

対象は dashlib.free_text_lang_mismatch() / expected_lang_notice() /
free_text_lang_notice() と、それを使う update_state.py の start / add / done /
finish / lang。「設定した言語が、走っているセッションへ実際に届くか」「食い違いの
警告が出る／出ないが正しいか」「警告が書き込みを止めないか」「打ち直しで実測値が
消えないか」を、実際に CLI を1コマンドずつ動かして確かめる。

**本物のユーザー設定・このプロジェクト自身の記録には一切触れない。**
  - free_text_lang_mismatch() は text/lang を引数で受け取る純粋関数なので、
    そのまま呼んでも何も書き込まれない。
  - update_state.py の呼び出しはすべて別プロセス（subprocess）で行い、
    AGENT_DASHBOARD_DATA_HOME（missions/ agents.json / lang の置き場）と
    HOME・USERPROFILE・各 CLI の home_env（CLAUDE_CONFIG_DIR など）を
    tempfile.mkdtemp() で作った使い捨てのフォルダへ向け替える。この2つを
    揃えないと、home_env を持たない CLI（amp / cline / roo など）が
    Path.home() 経由で本物のホームを見に行ってしまう
    （check_agents.py の test_unwired_agents と同じ理由）。
  - 検査の最後に、使ったフォルダはまとめて削除する。

テストはすべてテンポラリ・ディレクトリを使って実行し、このプロジェクト自身の
missions/ agents.json / lang にも、~/.claude 等の本物の設定にも書き込まない。
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# **dashlib を import する前に隔離する。** DATA_HOME（missions/ agents.json / lang の
# 置き場）は import 時に一度だけ resolve_data_home() で決まり、書き込み先として
# TOOL_ROOT（＝このプロジェクトのフォルダ）が選ばれることがある。この検査スクリプト
# 自身の import が、このプロジェクトの本物の missions/ を汚す事故を最初から断つ。
_IMPORT_SANDBOX = Path(tempfile.mkdtemp(prefix="check_lang_import_"))
os.environ["AGENT_DASHBOARD_DATA_HOME"] = str(_IMPORT_SANDBOX / "data")
os.environ["CLAUDE_CONFIG_DIR"] = str(_IMPORT_SANDBOX / "claude")
os.environ["HOME"] = str(_IMPORT_SANDBOX / "home")
os.environ["USERPROFILE"] = str(_IMPORT_SANDBOX / "home")

import dashlib  # noqa: E402
import i18n  # noqa: E402

dashlib.use_utf8_stdio()

UPDATE_STATE = str(HERE / "update_state.py")
PY = sys.executable

# 検査全体で使い捨てるフォルダの根っこ。試験が失敗して早期に return しても、
# main() の finally と atexit の二重の網で必ず片付ける。
SANDBOX_ROOT = Path(tempfile.mkdtemp(prefix="check_lang_"))
atexit.register(lambda: shutil.rmtree(SANDBOX_ROOT, ignore_errors=True))
atexit.register(lambda: shutil.rmtree(_IMPORT_SANDBOX, ignore_errors=True))


# ================================================================ テスト骨組み
# （check_agents.py の TestResult とほぼ同じ形にしてある。書式を検査ごとに
#  変えると、複数の check_*.py を並べて読む人がその都度読み方を覚え直す羽目になる）


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures: list[str] = []

    def record(self, test_name: str, ok: bool, reason: str = "") -> None:
        marker = "[PASS]" if ok else "[FAIL]"
        print(f"{marker} {test_name}")
        if ok:
            self.passed += 1
        else:
            self.failed += 1
            if reason:
                print(f"       {reason}")
            self.failures.append(test_name)

    def summary(self) -> int:
        total = self.passed + self.failed
        print()
        print(f"検査結果: {self.passed} 件合格 / {self.failed} 件不合格（全 {total} 件）")
        if self.failures:
            print("失敗した検査:")
            for name in self.failures:
                print(f"  - {name}")
            return 1
        return 0


def check_function_exists(name: str) -> bool:
    return hasattr(dashlib, name) and callable(getattr(dashlib, name))


# ================================================================ 言語を強制する小道具
#
# 「いまの言語での正解」を、翻訳表を手で複製せずに実装そのものから作る。
# 訳文をここに書き写すと、訳を直したときに検査だけ取り残されて気づけなくなる。
# i18n._lang を直接書き換えるのは、set_lang() が「環境変数のほうが強い」規則を
# 持っていて、それを気にせず一時的に切り替えたいこの用途には force 付きの
# set_lang より率直なため（この検査スクリプト自身の以降の動作には影響しない
# ―― 自分の画面出力には t() を使わず、素の日本語をそのまま書いている）。


def with_forced_lang(lang: str, fn):
    saved = i18n._lang
    try:
        i18n._lang = lang
        return fn()
    finally:
        i18n._lang = saved


def expected_notice_text(lang: str) -> str:
    return with_forced_lang(lang, dashlib.expected_lang_notice)


def mismatch_notice_text(lang: str, mismatches, *, fixable: bool) -> str | None:
    return with_forced_lang(lang, lambda: dashlib.free_text_lang_notice(mismatches, fixable=fixable))


def command_label_for(lang: str) -> str:
    return with_forced_lang(lang, lambda: i18n.t("Command"))


_python_cmd_cache: list[str] = []


def detected_python_cmd() -> str:
    """install.detect_python_command() の結果をキャッシュする（実測のため毎回は重い）。"""
    if not _python_cmd_cache:
        import install
        _python_cmd_cache.append(install.detect_python_command())
    return _python_cmd_cache[0]


def build_block_for_lang(lang: str) -> str:
    import install
    return with_forced_lang(lang, lambda: install.build_block(detected_python_cmd()))


_FREE_TEXT_MARKER = "`--title` / `--name` / `--mission` / `--headline`"


def free_text_lang_line(lang: str) -> str:
    """運用ルールの本文にある「自由記述はこの言語で書け」の1行を取り出す。

    本文は t() を通してブロックまるごと1個の鍵で訳されているので、行ごとの
    鍵は無い。`--title` / `--name` / ... という並びはどの言語訳でも変わらない
    (コード片としてそのまま残る) ので、それを目印にその行を拾う。
    """
    block = build_block_for_lang(lang)
    for line in block.splitlines():
        if _FREE_TEXT_MARKER in line:
            return line
    return ""


# ================================================================ CLI 呼び出し


class _FakeProc:
    """subprocess 自体が起動できなかったときの代用品（検査を止めずに [FAIL] にする）。"""

    def __init__(self, err: Exception):
        self.returncode = -1
        self.stdout = ""
        self.stderr = "%s: %s" % (type(err).__name__, err)


def run_cli(args: list[str], *, project: str, data_home: Path,
            lang: str | None = None, claude_home: Path | None = None):
    """update_state.py を隔離された環境で1回実行する。

    隔離するもの:
      - AGENT_DASHBOARD_DATA_HOME … missions/ agents.json / lang の置き場
      - AGENT_DASHBOARD_PROJECT   … 対象プロジェクト（カレントディレクトリに依存しない）
      - HOME / USERPROFILE と、組み込み CLI の home_env 全部
        … present_agents()/installed_agents() が本物のホームを見に行かないように
      - AGENT_DASHBOARD_LANG / LC_ALL / LC_MESSAGES / LANG
        … lang を明示したときはそれだけで言語が決まるようにし、host の
          ロケールが検査結果を左右しないようにする
    """
    env = os.environ.copy()
    fake_home = data_home / "_fakehome"

    env[dashlib.ENV_DATA_HOME] = str(data_home)
    env[dashlib.ENV_PROJECT] = project
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    for entry in dashlib.BUILTIN_AGENT_TARGETS:
        env_name = entry.get("home_env") or ""
        if env_name:
            env[env_name] = str(fake_home / entry["key"])
    if claude_home is not None:
        env["CLAUDE_CONFIG_DIR"] = str(claude_home)
    env.pop(dashlib.ENV_AGENTS_FILE, None)

    for name in (i18n.ENV_LANG, "LC_ALL", "LC_MESSAGES", "LANG"):
        env.pop(name, None)
    if lang is not None:
        env[i18n.ENV_LANG] = lang

    try:
        return subprocess.run(
            [PY, UPDATE_STATE, *args],
            cwd=str(HERE),
            env=env,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return _FakeProc(e)


def read_state_json(data_home: Path, project: str) -> dict:
    path = data_home / "missions" / project / "state.json"
    return json.loads(path.read_text(encoding="utf-8"))


def find_agent(state: dict, agent_id: str) -> dict | None:
    for a in state.get("agents", []):
        if isinstance(a, dict) and a.get("id") == agent_id:
            return a
    return None


# ================================================================ 検査 1


def test_free_text_lang_mismatch_unit(result: TestResult) -> None:
    """1. free_text_lang_mismatch(text, lang) の単体検査。

    設定言語で書かれた文には食い違い無し、明らかに違う言語で書かれた文には
    食い違い有りとなること（ja/zh/ko/en の両方向）と、識別子・短い語・
    技術用語混じりの文で誤検出しないことを確かめる。誤検出しない側のほうが
    実運用（コールサインや固有名詞を英語で書く）への影響が大きい。
    """
    if not check_function_exists("free_text_lang_mismatch"):
        result.record("free_text_lang_mismatch() が存在する", False,
                      "関数 free_text_lang_mismatch が無い")
        return

    en_sentence = "This is written in English text"
    cases = [
        ("ja", "これは日本語で書かれた文章です", False, "ja設定 × 日本語の文 → 食い違いなし"),
        ("ja", en_sentence, True, "ja設定 × 英語の文 → 食い違いあり"),
        ("zh", "这是用中文写的一句话", False, "zh設定 × 中文の文 → 食い違いなし"),
        ("zh", en_sentence, True, "zh設定 × 英語の文 → 食い違いあり"),
        ("ko", "이것은 한국어로 쓴 문장입니다", False, "ko設定 × 韓国語の文 → 食い違いなし"),
        ("ko", en_sentence, True, "ko設定 × 英語の文 → 食い違いあり"),
        ("en", en_sentence, False, "en設定 × 英語の文 → 食い違いなし"),
        ("en", "これは日本語で書かれた文章です", True, "en設定 × CJKの文 → 食い違いあり"),
    ]
    for lang, text, expect, label in cases:
        try:
            got = dashlib.free_text_lang_mismatch(text, lang)
        except Exception as e:
            result.record(label, False, f"例外: {type(e).__name__}: {e}")
            continue
        result.record(label, got == expect, f"got={got!r} expect={expect!r} text={text!r}")

    # 誤検出しないこと（すべて ja 設定で検査する。何語設定でも短さ・識別子らしさ・
    # 期待言語の文字混入は最初から対象外になる、という判定の入口の話なので、
    # 設定言語を変えても結論は変わらない）。
    false_positive_cases = [
        ("SCOUT-A", "コールサインらしき文字列 (SCOUT-A) を誤検出しない"),
        ("src/api.py", "パスらしき文字列 (src/api.py) を誤検出しない"),
        ("v0.5.1", "版番号らしき文字列 (v0.5.1) を誤検出しない"),
        ("42", "短い数字 (42) を誤検出しない"),
        ("---", "記号だけの短い文字列 (---) を誤検出しない"),
        ("x" * (dashlib.MIN_LANG_CHECK_CHARS - 1),
         f"MIN_LANG_CHECK_CHARS未満の短い語（{dashlib.MIN_LANG_CHECK_CHARS - 1}文字）を誤検出しない"),
        ("APIの仕様を確認しました", "日本語の文に英単語 (API) が混ざったものを誤検出しない"),
    ]
    for text, label in false_positive_cases:
        try:
            got = dashlib.free_text_lang_mismatch(text, "ja")
        except Exception as e:
            result.record(label, False, f"例外: {type(e).__name__}: {e}")
            continue
        result.record(label, got is False, f"got={got!r} text={text!r}")


# ================================================================ 検査 2


def test_start_prints_lang_notice(result: TestResult) -> None:
    """2. start の出力に、必ず「この言語で書け」という1行が出ることを確かめる。

    dashlib.py のコメントにある通り、これが「走っているセッションへ言語を届ける
    唯一の経路」なので、ここが欠けると仕組み全体が意味を失う。4言語それぞれで
    start を実行し、expected_lang_notice() が返す文面がそのまま出力に含まれる
    ことを確かめる。
    """
    if not check_function_exists("expected_lang_notice"):
        result.record("expected_lang_notice() が存在する", False,
                      "関数 expected_lang_notice が無い")
        return

    for lang in ("en", "ja", "zh", "ko"):
        data_home = SANDBOX_ROOT / f"t2-{lang}"
        proc = run_cli(
            ["start", "--title", "Start Notice Check", "--model", "test-model"],
            project=f"t2-{lang}", data_home=data_home, lang=lang,
        )
        exit_ok = proc.returncode == 0
        result.record(f"[{lang}] start が終了コード0", exit_ok,
                      f"code={proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
        if not exit_ok:
            continue

        expected = expected_notice_text(lang)
        ok = bool(expected) and expected in proc.stdout
        result.record(f"[{lang}] start の出力に expected_lang_notice() の行が出る", ok,
                      f"期待して探した行:\n{expected!r}\n実際の標準出力:\n{proc.stdout}")


# ================================================================ 検査 3・4


def _mismatch_scenarios() -> dict:
    return {
        "mismatch": {
            "title": "This is an English mission title",
            "name": "An English agent name for testing",
            "mission": "This mission text is written in English",
            "headline_done": "This is an English done headline text",
            "headline_finish": "This is an English finish headline text",
        },
        "match": {
            "title": "回帰なしミッションの表題です",
            "name": "日本語で書いたエージェント名です",
            "mission": "日本語で書かれた任務の内容です",
            "headline_done": "日本語で書いた完了の一行報告です",
            "headline_finish": "日本語で書いた最終まとめの報告です",
        },
    }


def _compute_expected_notice(step: str, lang: str, values: dict) -> str | None:
    """cmd_start/cmd_add/cmd_done/cmd_finish の「checks を作って notice を作る」
    手順を、update_state.py を読んで確認したとおりに検査側でも組み立てる。
    """
    if step == "start":
        checks = ([("--title", values["title"])]
                  if dashlib.free_text_lang_mismatch(values["title"], lang) else [])
        return mismatch_notice_text(lang, checks, fixable=False) if checks else None
    if step == "add":
        checks = []
        if dashlib.free_text_lang_mismatch(values["name"], lang):
            checks.append(("--name", values["name"]))
        if dashlib.free_text_lang_mismatch(values["mission"], lang):
            checks.append(("--mission", values["mission"]))
        return mismatch_notice_text(lang, checks, fixable=True) if checks else None
    if step == "done":
        if dashlib.free_text_lang_mismatch(values["headline_done"], lang):
            return mismatch_notice_text(lang, [("--headline", values["headline_done"])], fixable=True)
        return None
    if step == "finish":
        if dashlib.free_text_lang_mismatch(values["headline_finish"], lang):
            return mismatch_notice_text(lang, [("--headline", values["headline_finish"])], fixable=True)
        return None
    raise ValueError(step)


def test_free_text_mismatch_notice(result: TestResult) -> None:
    """3・4. 自由記述が設定言語と食い違うときに警告が出て（食い違わなければ出ない）、
    警告が出ても書き込みが止まらないことを確かめる。

    設定言語は ja に固定し、英語の自由記述（食い違いあり）と日本語の自由記述
    （食い違いなし）の両方で start → add → done → finish の一巡を回し、
    各コマンドの標準出力（3の判定）と最終的な state.json の中身（4の判定：
    終了コードと記録された値）を突き合わせる。
    """
    if not check_function_exists("free_text_lang_notice"):
        result.record("free_text_lang_notice() が存在する", False,
                      "関数 free_text_lang_notice が無い")
        return

    lang = "ja"
    agent_id = "SCOUT-1"
    scenarios = _mismatch_scenarios()

    for tag, values in scenarios.items():
        project = f"t3-{tag}"
        data_home = SANDBOX_ROOT / project

        steps = {
            "start": run_cli(
                ["start", "--title", values["title"], "--model", "test-model"],
                project=project, data_home=data_home, lang=lang),
            "add": run_cli(
                ["add", "--id", agent_id, "--name", values["name"],
                 "--mission", values["mission"]],
                project=project, data_home=data_home, lang=lang),
            "done": run_cli(
                ["done", "--id", agent_id, "--headline", values["headline_done"]],
                project=project, data_home=data_home, lang=lang),
            "finish": run_cli(
                ["finish", "--headline", values["headline_finish"]],
                project=project, data_home=data_home, lang=lang),
        }

        for step, proc in steps.items():
            # 4. 警告が出ても書き込みは止まらない → 終了コードは常に0のはず。
            result.record(
                f"[{tag}/{step}] 終了コード0（警告があっても書き込みを止めない）",
                proc.returncode == 0,
                f"code={proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}",
            )

            # 3. 食い違いの警告が出る／出ない。
            expected = _compute_expected_notice(step, lang, values)
            if expected is not None:
                ok = expected in proc.stdout
                result.record(f"[{tag}/{step}] 食い違いの警告が正しい文面で出る", ok,
                              f"期待した文面:\n{expected!r}\n実際の標準出力:\n{proc.stdout}")
            else:
                # ⚠️ はこの検査の隔離環境（未設定・組み込みCLI無し）では
                # 自由記述の食い違い以外から出ない（stale/unwired の両方が None になる
                # ことは実装を読んで確認済み）ので、無いことの確認にそのまま使える。
                ok = "⚠️" not in proc.stdout
                result.record(f"[{tag}/{step}] 食い違いがないので警告が出ない", ok,
                              f"実際の標準出力:\n{proc.stdout}")

        # 4（続き）: 警告が出た/出ないに関わらず、値はそのまま state.json に記録される。
        try:
            state = read_state_json(data_home, project)
        except OSError as e:
            result.record(f"[{tag}] state.json が読める", False, str(e))
            continue

        got_title = state.get("mission", {}).get("title")
        result.record(f"[{tag}] state.json に title がそのまま記録される",
                      got_title == values["title"],
                      f"期待: {values['title']!r} / 得: {got_title!r}")

        agent = find_agent(state, agent_id)
        if agent is None:
            result.record(f"[{tag}] state.json にエージェントが記録される", False,
                          f"agents={state.get('agents')}")
            continue

        result.record(f"[{tag}] state.json に name がそのまま記録される",
                      agent.get("name") == values["name"], f"得: {agent.get('name')!r}")
        result.record(f"[{tag}] state.json に mission がそのまま記録される",
                      agent.get("mission") == values["mission"], f"得: {agent.get('mission')!r}")

        res = agent.get("result") if isinstance(agent.get("result"), dict) else {}
        result.record(f"[{tag}] state.json に done の headline がそのまま記録される",
                      res.get("headline") == values["headline_done"],
                      f"得: {res.get('headline')!r}")
        result.record(f"[{tag}] state.json の status が done になる",
                      agent.get("status") == "done", f"得: {agent.get('status')!r}")

        summary = state.get("mission", {}).get("summary")
        summary = summary if isinstance(summary, dict) else {}
        result.record(f"[{tag}] state.json の finish の headline がそのまま記録される",
                      summary.get("headline") == values["headline_finish"],
                      f"得: {summary.get('headline')!r}")


# ================================================================ 検査 5


def test_rewrite_preserves_measurements(result: TestResult) -> None:
    """5. 打ち直しで自由記述を直せて、しかも実測値・状態・要約が消えないことを確かめる。

    add（英語・食い違いあり）→ done（実測値つき）→ finish の後、同じ --id で
    add を打ち直して --name / --mission を日本語に直す。このとき:
      - name / mission は新しい値に変わる
      - result（elapsedSec / tokens / toolCalls / headline）は変わらない
      - status は done のまま
      - mission.phase は done のまま、summary も消えない
    直前に修正された箇所で、修正前はここが全部消えていた（回帰検査）。
    """
    lang = "ja"
    project = "t5-rewrite-regress"
    data_home = SANDBOX_ROOT / project
    agent_id = "SCOUT-X"

    steps = {
        "start": run_cli(
            ["start", "--title", "回帰検査ミッション", "--model", "test-model"],
            project=project, data_home=data_home, lang=lang),
        "add": run_cli(
            ["add", "--id", agent_id,
             "--name", "An English name before the rewrite",
             "--mission", "An English mission before the rewrite"],
            project=project, data_home=data_home, lang=lang),
        "done": run_cli(
            ["done", "--id", agent_id, "--sec", "77", "--tokens", "12345",
             "--tools", "9", "--headline", "回帰検査の完了報告"],
            project=project, data_home=data_home, lang=lang),
        "finish": run_cli(
            ["finish", "--headline", "回帰検査ミッション完了"],
            project=project, data_home=data_home, lang=lang),
    }
    for step, proc in steps.items():
        result.record(f"[打ち直し前準備] {step} が終了コード0", proc.returncode == 0,
                      f"code={proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")

    try:
        state_before = read_state_json(data_home, project)
    except OSError as e:
        result.record("打ち直し前の state.json が読める", False, str(e))
        return
    agent_before = find_agent(state_before, agent_id)
    if agent_before is None:
        result.record("打ち直し前にエージェントが記録されている", False,
                      f"agents={state_before.get('agents')}")
        return
    result_before = agent_before.get("result")
    if not isinstance(result_before, dict) or result_before.get("tokens") != 12345:
        result.record("打ち直し前の result に実測値が入っている（前提の確認）", False,
                      f"result={result_before!r}")
        return

    new_name = "日本語に直したエージェント名"
    new_mission = "日本語に直した任務内容"
    proc = run_cli(
        ["add", "--id", agent_id, "--name", new_name, "--mission", new_mission],
        project=project, data_home=data_home, lang=lang,
    )
    result.record("打ち直しの add が終了コード0", proc.returncode == 0,
                  f"code={proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")

    try:
        state_after = read_state_json(data_home, project)
    except OSError as e:
        result.record("打ち直し後の state.json が読める", False, str(e))
        return
    agent_after = find_agent(state_after, agent_id)
    if agent_after is None:
        result.record("打ち直し後もエージェントが記録されている", False,
                      f"agents={state_after.get('agents')}")
        return

    result.record("打ち直し後に name が新しい値になる", agent_after.get("name") == new_name,
                  f"得: {agent_after.get('name')!r}")
    result.record("打ち直し後に mission が新しい値になる", agent_after.get("mission") == new_mission,
                  f"得: {agent_after.get('mission')!r}")
    result.record("打ち直し後も result（elapsedSec/tokens/toolCalls/headline）が保たれる",
                  agent_after.get("result") == result_before,
                  f"前: {result_before!r}\n後: {agent_after.get('result')!r}")
    result.record("打ち直し後も status が done のまま巻き戻らない",
                  agent_after.get("status") == "done", f"得: {agent_after.get('status')!r}")

    mission_after = state_after.get("mission") if isinstance(state_after.get("mission"), dict) else {}
    result.record("打ち直し後も mission.phase が done のまま",
                  mission_after.get("phase") == "done", f"得: {mission_after.get('phase')!r}")
    result.record("打ち直し後も mission.summary が消えていない",
                  isinstance(mission_after.get("summary"), dict),
                  f"得: {mission_after.get('summary')!r}")


# ================================================================ 検査 6


def test_command_row_follows_lang(result: TestResult) -> None:
    """6. state.json の COMMAND 行（ツールが書く既定ラベル）が設定言語に追随することを
    確かめる。ここが言語に追随しないと、指令塔だけ違う言語で記録される食い違いが
    起きる（dashlib.py のコメントに書かれている、実際に起きた事故そのもの）。
    """
    for lang in ("en", "ja", "zh", "ko"):
        project = f"t6-{lang}"
        data_home = SANDBOX_ROOT / project
        proc = run_cli(
            ["start", "--title", "Command Row Check", "--model", "test-model"],
            project=project, data_home=data_home, lang=lang,
        )
        if proc.returncode != 0:
            result.record(f"[{lang}] start が終了コード0（COMMAND行検査の前提）", False,
                          f"code={proc.returncode}\nSTDERR={proc.stderr}")
            continue

        try:
            state = read_state_json(data_home, project)
        except OSError as e:
            result.record(f"[{lang}] state.json が読める", False, str(e))
            continue

        command_agent = find_agent(state, dashlib.COMMAND_ID)
        expected_label = command_label_for(lang)
        got = (command_agent or {}).get("name")
        ok = command_agent is not None and got == expected_label
        result.record(f"[{lang}] state.json の COMMAND 行の name が設定言語({lang})になる",
                      ok, f"期待: {expected_label!r} / 得: {got!r}")


# ================================================================ 検査 7


def test_lang_command_rewrites_rules(result: TestResult) -> None:
    """7. `update_state.py lang <コード>` が、書き込み済みの運用ルールをその言語で
    書き直すことを確かめる。

    サンドボックスの CLAUDE_CONFIG_DIR に、あらかじめ英語版の運用ルール（BEGIN/END
    のブロック）を書いた CLAUDE.md を用意しておき、`lang <code>` を実行して、
    ブロックの中の「自由記述はこの言語で書け」の行が code の言語になっていることを
    確かめる。書く先を dashlib.installed_agents() が返したものだけに絞っている
    実装なので、この検査でも「claude だけが installed と判定される」ように
    home_env を全部隔離してある（run_cli 参照）。
    """
    try:
        import install  # noqa: F401
    except ImportError as e:
        result.record("update_state.py lang が運用ルールを書き直す（install が無い）", False,
                      f"install を読み込めない: {e}")
        return

    for code in ("en", "ja", "zh", "ko"):
        project = f"t7-{code}"
        data_home = SANDBOX_ROOT / project
        claude_home = SANDBOX_ROOT / f"t7-{code}-claude"
        claude_home.mkdir(parents=True, exist_ok=True)
        claude_md = claude_home / "CLAUDE.md"

        # あらかじめ「英語で設定済み」の CLAUDE.md を用意する（実際に install.py を
        # 一度実行した後の状態を模す）。block_installed() はパスも見るので、この
        # プロジェクト自身の install.build_block() で作ったブロックでないと
        # 「installed」と判定されない。
        initial_block = build_block_for_lang("en")
        claude_md.write_text(initial_block + "\n", encoding="utf-8")

        proc = run_cli(["lang", code], project=project, data_home=data_home,
                       claude_home=claude_home)
        result.record(f"[{code}] update_state.py lang {code} が終了コード0",
                      proc.returncode == 0,
                      f"code={proc.returncode}\nSTDOUT={proc.stdout}\nSTDERR={proc.stderr}")
        if proc.returncode != 0:
            continue

        try:
            content = claude_md.read_text(encoding="utf-8")
        except OSError as e:
            result.record(f"[{code}] lang 実行後に CLAUDE.md が読める", False, str(e))
            continue

        hallmark = free_text_lang_line(code)
        ok = bool(hallmark) and hallmark in content
        result.record(f"[{code}] lang {code} でブロックの文面がその言語になる", ok,
                      f"探した行:\n{hallmark!r}\n実際の CLAUDE.md（抜粋）:\n{content[:1200]!r}")

        # ついでの確認: マーカーが2重に増えていない（差し替えであって追記になって
        # いないこと）。無くても罪は無いが、有れば --uninstall が壊れる兆候になる。
        begin_count = content.count(dashlib.BLOCK_BEGIN)
        result.record(f"[{code}] BEGIN マーカーが二重になっていない",
                      begin_count == 1, f"count={begin_count}")


# ================================================================ 実行


def main() -> int:
    result = TestResult()
    print("言語設定がエージェントの記述に反映されるかの検査を開始します")
    print(f"（作業フォルダ: {SANDBOX_ROOT}）")
    print()

    try:
        test_free_text_lang_mismatch_unit(result)
        test_start_prints_lang_notice(result)
        test_free_text_mismatch_notice(result)
        test_rewrite_preserves_measurements(result)
        test_command_row_follows_lang(result)
        test_lang_command_rewrites_rules(result)
    finally:
        shutil.rmtree(SANDBOX_ROOT, ignore_errors=True)
        shutil.rmtree(_IMPORT_SANDBOX, ignore_errors=True)

    return result.summary()


if __name__ == "__main__":
    sys.exit(main())
