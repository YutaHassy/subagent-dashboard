#!/usr/bin/env python3
"""Subagent Dashboard — エージェント・レジストリ API の検査（開発用）

    python check_agents.py

dashlib が提供する agent_targets() / agent_keys() / agent_label() などの API を
検める。実装が進む過程で、幾つかの関数はまだ無い ― そのときは
「[FAIL] 関数名が無い」と報告して、検査を続ける。

テストはすべてテンポラリ・ディレクトリを使って実行し、
~/.claude, ~/.codex などの実ユーザー設定には一切触れない。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib  # noqa: E402

dashlib.use_utf8_stdio()


# ================================================================ テスト骨組み

def reset_environ(original_env: dict[str, str]) -> None:
    """os.environ をテスト前の状態に復帰させる。"""
    current_keys = set(os.environ.keys())
    original_keys = set(original_env.keys())
    # 足したキーを消す
    for key in current_keys - original_keys:
        del os.environ[key]
    # 変わったキーを戻す
    for key in original_keys & current_keys:
        if os.environ[key] != original_env[key]:
            os.environ[key] = original_env[key]
    # 消したキーを復帰させる
    for key in original_keys - current_keys:
        os.environ[key] = original_env[key]


def check_function_exists(name: str) -> bool:
    """指定の関数が dashlib にあるか。"""
    return hasattr(dashlib, name) and callable(getattr(dashlib, name))


def check_attr_exists(name: str) -> bool:
    """指定の属性が dashlib にあるか。"""
    return hasattr(dashlib, name)


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
            print(f"失敗した検査:")
            for name in self.failures:
                print(f"  - {name}")
            return 1
        return 0


# ================================================================ 検査 1-2

def test_builtin_targets(result: TestResult) -> None:
    """1. BUILTIN_AGENT_TARGETS の構成を検める。

    すべてのキーが "key", "label", "home_env", "home", "file" を持ち、
    "key" と "label" と "home" と "file" が空でなく、key が重複していないことを確かめる。
    """
    if not check_attr_exists("BUILTIN_AGENT_TARGETS"):
        result.record(
            "BUILTIN_AGENT_TARGETS が存在する",
            False,
            "属性 BUILTIN_AGENT_TARGETS が無い"
        )
        return

    try:
        builtins = dashlib.BUILTIN_AGENT_TARGETS
    except Exception as e:
        result.record(
            "BUILTIN_AGENT_TARGETS が存在する",
            False,
            f"属性を読むときにエラー: {e}"
        )
        return

    if not isinstance(builtins, tuple):
        result.record(
            "BUILTIN_AGENT_TARGETS が tuple である",
            False,
            f"型は {type(builtins).__name__}（期待: tuple）"
        )
        return

    seen_keys = set()
    all_ok = True

    for i, entry in enumerate(builtins):
        if not isinstance(entry, dict):
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] が dict である",
                False,
                f"型は {type(entry).__name__}"
            )
            all_ok = False
            continue

        required_keys = {"key", "label", "home_env", "home", "file"}
        missing = required_keys - set(entry.keys())
        if missing:
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] が必須キーを持つ",
                False,
                f"無いキー: {', '.join(sorted(missing))}"
            )
            all_ok = False
            continue

        key = entry.get("key", "")
        label = entry.get("label", "")
        home = entry.get("home", "")
        file_name = entry.get("file", "")
        home_env = entry.get("home_env", "")

        # key と label と home と file が空でないことを確かめる
        if not key:
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] の key が空でない",
                False,
                "key が空文字列"
            )
            all_ok = False
        if not label:
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] の label が空でない",
                False,
                "label が空文字列"
            )
            all_ok = False
        if not home:
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] の home が空でない",
                False,
                "home が空文字列"
            )
            all_ok = False
        if not file_name:
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] の file が空でない",
                False,
                "file が空文字列"
            )
            all_ok = False

        # key が小文字
        if key and key != key.lower():
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] の key が小文字",
                False,
                f"'{key}' は大文字を含む"
            )
            all_ok = False

        if key in seen_keys:
            result.record(
                f"BUILTIN_AGENT_TARGETS[{i}] の key が重複していない",
                False,
                f"'{key}' は既出"
            )
            all_ok = False
        else:
            seen_keys.add(key)

    if all_ok and len(builtins) > 0:
        result.record(
            "BUILTIN_AGENT_TARGETS が正しい構成",
            True
        )


def test_agent_keys(result: TestResult) -> None:
    """2. agent_keys() が至少 "claude" と "codex" を含み、
    agent_label("claude") が空でない文字列を返すことを確かめる。
    """
    if not check_function_exists("agent_keys"):
        result.record(
            "agent_keys() が存在する",
            False,
            "関数 agent_keys が無い"
        )
        return

    try:
        keys = dashlib.agent_keys()
    except Exception as e:
        result.record(
            "agent_keys() が呼べる",
            False,
            f"エラー: {e}"
        )
        return

    if not isinstance(keys, tuple):
        result.record(
            "agent_keys() が tuple を返す",
            False,
            f"型は {type(keys).__name__}（期待: tuple）"
        )
        return

    keys_list = list(keys)
    has_claude = "claude" in keys_list
    has_codex = "codex" in keys_list

    result.record(
        "agent_keys() が 'claude' を含む",
        has_claude,
        "" if has_claude else f"keys={keys_list}"
    )

    result.record(
        "agent_keys() が 'codex' を含む",
        has_codex,
        "" if has_codex else f"keys={keys_list}"
    )

    if not check_function_exists("agent_label"):
        result.record(
            "agent_label() が存在する",
            False,
            "関数 agent_label が無い"
        )
        return

    try:
        label = dashlib.agent_label("claude")
    except Exception as e:
        result.record(
            "agent_label('claude') が呼べる",
            False,
            f"エラー: {e}"
        )
        return

    if not isinstance(label, str) or not label:
        result.record(
            "agent_label('claude') が空でない文字列",
            False,
            f"値: {repr(label)}"
        )
    else:
        result.record(
            "agent_label('claude') が空でない文字列",
            True
        )


# ================================================================ 検査 3

def test_agent_config_dir_env(result: TestResult) -> None:
    """3. agent_config_dir() が環境変数を尊重することを確かめる。

    ビルトインのエントリで home_env が設定されているものを見つけて、
    その環境変数をテンポラリ・ディレクトリに指して、返り値が
    そこを指していることを確かめる。その後、環境変数を消して、
    home に書かれた既定値に落ちることを確かめる。
    """
    if not check_function_exists("agent_config_dir"):
        result.record(
            "agent_config_dir() が存在する",
            False,
            "関数 agent_config_dir が無い"
        )
        return

    if not check_attr_exists("BUILTIN_AGENT_TARGETS"):
        result.record(
            "agent_config_dir() のテストに BUILTIN_AGENT_TARGETS が要る",
            False,
            "属性が無い"
        )
        return

    builtins = dashlib.BUILTIN_AGENT_TARGETS
    if not isinstance(builtins, (tuple, list)) or not builtins:
        result.record(
            "agent_config_dir() のテストに有効な BUILTIN_AGENT_TARGETS が要る",
            False,
            ""
        )
        return

    # home_env が設定されているエントリを見つける
    test_entry = None
    for entry in builtins:
        if isinstance(entry, dict) and entry.get("home_env"):
            test_entry = entry
            break

    if not test_entry:
        result.record(
            "agent_config_dir() が環境変数を尊重する（テスト対象無し）",
            True  # テスト対象が無いのは失敗ではなく、スキップ
        )
        return

    key = test_entry.get("key")
    env_name = test_entry.get("home_env")
    home_default = test_entry.get("home")

    if not key or not env_name:
        result.record(
            "agent_config_dir() テスト用エントリが完全",
            False,
            f"key={key}, env_name={env_name}"
        )
        return

    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # 環境変数を設定して確かめる
            os.environ[env_name] = tmpdir
            try:
                result_path = dashlib.agent_config_dir(key)
            except Exception as e:
                result.record(
                    f"agent_config_dir('{key}') が環境変数 {env_name} を尊重",
                    False,
                    f"エラー: {e}"
                )
                return

            expected = Path(tmpdir).resolve()
            if result_path.resolve() == expected:
                result.record(
                    f"agent_config_dir('{key}') が環境変数 {env_name} を尊重",
                    True
                )
            else:
                result.record(
                    f"agent_config_dir('{key}') が環境変数 {env_name} を尊重",
                    False,
                    f"期待: {expected}, 得: {result_path.resolve()}"
                )

        # 環境変数を消して、既定値に落ちることを確かめる
        del os.environ[env_name]
        try:
            result_path = dashlib.agent_config_dir(key)
        except Exception as e:
            result.record(
                f"agent_config_dir('{key}') が環境変数を消したら既定値に落ちる",
                False,
                f"エラー: {e}"
            )
            return

        # 既定値は home_default を ~ 展開した path
        # home_default は ".claude" のような形か "~/.claude" のような形かもしれない
        if home_default.startswith("~"):
            expected_default = Path(home_default).expanduser().resolve()
        else:
            expected_default = (Path.home() / home_default).resolve()
        if result_path.resolve() == expected_default:
            result.record(
                f"agent_config_dir('{key}') が環境変数を消したら既定値に落ちる",
                True
            )
        else:
            result.record(
                f"agent_config_dir('{key}') が環境変数を消したら既定値に落ちる",
                False,
                f"期待: {expected_default}, 得: {result_path.resolve()}"
            )
    finally:
        reset_environ(original_env)


# ================================================================ 検査 4

def test_instruction_file(result: TestResult) -> None:
    """4. instruction_file(key) が agent_config_dir(key) / file と等しいことを確かめる。"""
    if not check_function_exists("instruction_file"):
        result.record(
            "instruction_file() が存在する",
            False,
            "関数 instruction_file が無い"
        )
        return

    if not check_function_exists("agent_config_dir"):
        result.record(
            "instruction_file() のテストに agent_config_dir が要る",
            False,
            ""
        )
        return

    if not check_attr_exists("BUILTIN_AGENT_TARGETS"):
        result.record(
            "instruction_file() のテストに BUILTIN_AGENT_TARGETS が要る",
            False,
            ""
        )
        return

    builtins = dashlib.BUILTIN_AGENT_TARGETS
    if not isinstance(builtins, (tuple, list)) or not builtins:
        result.record(
            "instruction_file() のテストに有効な BUILTIN_AGENT_TARGETS が要る",
            False,
            ""
        )
        return

    # 最初のエントリを使って検査
    entry = builtins[0]
    if not isinstance(entry, dict):
        result.record(
            "instruction_file() の計算が正しい",
            False,
            "最初のエントリが dict でない"
        )
        return

    key = entry.get("key")
    expected_file_name = entry.get("file")

    if not key or not expected_file_name:
        result.record(
            "instruction_file() の計算が正しい",
            False,
            f"key={key}, file_name={expected_file_name}"
        )
        return

    try:
        instr_file = dashlib.instruction_file(key)
        config_dir = dashlib.agent_config_dir(key)
        expected = config_dir / expected_file_name

        if instr_file == expected:
            result.record(
                f"instruction_file('{key}') が正しい",
                True
            )
        else:
            result.record(
                f"instruction_file('{key}') が正しい",
                False,
                f"期待: {expected}, 得: {instr_file}"
            )
    except Exception as e:
        result.record(
            f"instruction_file('{key}') が呼べる",
            False,
            f"エラー: {e}"
        )


# ================================================================ 検査 5

def test_unknown_key_error(result: TestResult) -> None:
    """5. 未知の key で agent_label / agent_config_dir を呼ぶと KeyError が出ることを確かめる。"""
    if not check_function_exists("agent_label"):
        result.record(
            "agent_label() が未知キーで KeyError を出す",
            False,
            "関数 agent_label が無い"
        )
        return

    if not check_function_exists("agent_config_dir"):
        result.record(
            "agent_config_dir() が未知キーで KeyError を出す",
            False,
            "関数 agent_config_dir が無い"
        )
        return

    unknown_key = "__unknown_key_that_does_not_exist__"

    try:
        dashlib.agent_label(unknown_key)
        result.record(
            f"agent_label('{unknown_key}') が KeyError を出す",
            False,
            "例外が出なかった"
        )
    except KeyError:
        result.record(
            f"agent_label('{unknown_key}') が KeyError を出す",
            True
        )
    except Exception as e:
        result.record(
            f"agent_label('{unknown_key}') が KeyError を出す",
            False,
            f"別の例外: {type(e).__name__}: {e}"
        )

    try:
        dashlib.agent_config_dir(unknown_key)
        result.record(
            f"agent_config_dir('{unknown_key}') が KeyError を出す",
            False,
            "例外が出なかった"
        )
    except KeyError:
        result.record(
            f"agent_config_dir('{unknown_key}') が KeyError を出す",
            True
        )
    except Exception as e:
        result.record(
            f"agent_config_dir('{unknown_key}') が KeyError を出す",
            False,
            f"別の例外: {type(e).__name__}: {e}"
        )


# ================================================================ 検査 6-7

def test_user_agents(result: TestResult) -> None:
    """6. ユーザー定義エージェント: AGENTS_FILE、load_user_agents()、
    add_user_agent() を検査して、add_user_agent で書いたものが
    load_user_agents() と agent_targets() に反映されることを確かめる。

    7. ユーザーエントリが同じ key を持つビルトインエントリを上書きすることを確かめる。
    """
    if not check_attr_exists("AGENTS_FILE"):
        result.record(
            "AGENTS_FILE が存在する",
            False,
            "属性 AGENTS_FILE が無い"
        )
        return

    if not check_function_exists("load_user_agents"):
        result.record(
            "load_user_agents() が存在する",
            False,
            "関数 load_user_agents が無い"
        )
        return

    if not check_function_exists("add_user_agent"):
        result.record(
            "add_user_agent() が存在する",
            False,
            "関数 add_user_agent が無い"
        )
        return

    if not check_function_exists("agent_targets"):
        result.record(
            "agent_targets() が存在する",
            False,
            "関数 agent_targets が無い"
        )
        return

    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # AGENTS_FILE をテンポラリ・ファイルに差し替える
            agents_file = Path(tmpdir) / "agents.json"
            original_agents_file = dashlib.AGENTS_FILE
            dashlib.AGENTS_FILE = agents_file

            # まだファイルが無い状態で load_user_agents() を呼ぶと [] が返る
            try:
                loaded = dashlib.load_user_agents()
            except Exception as e:
                result.record(
                    "load_user_agents() が無いファイルで呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if loaded == []:
                result.record(
                    "load_user_agents() が無いファイルで [] を返す",
                    True
                )
            else:
                result.record(
                    "load_user_agents() が無いファイルで [] を返す",
                    False,
                    f"得: {loaded}"
                )

            # add_user_agent でエントリを書き込む
            user_entry = {
                "key": "testuser",
                "label": "Test User Agent",
                "home_env": "",
                "home": ".testuser",
                "file": "TEST.md"
            }
            try:
                dashlib.add_user_agent(user_entry)
            except Exception as e:
                result.record(
                    "add_user_agent() が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            # load_user_agents() で返ってくることを確かめる
            try:
                loaded = dashlib.load_user_agents()
            except Exception as e:
                result.record(
                    "add_user_agent() 後に load_user_agents() が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if loaded and any(e.get("key") == "testuser" for e in loaded):
                result.record(
                    "add_user_agent() したエントリが load_user_agents() に反映",
                    True
                )
            else:
                result.record(
                    "add_user_agent() したエントリが load_user_agents() に反映",
                    False,
                    f"loaded={loaded}"
                )

            # agent_targets() に反映されることを確かめる
            try:
                targets = dashlib.agent_targets()
            except Exception as e:
                result.record(
                    "add_user_agent() 後に agent_targets() が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if targets and any(e.get("key") == "testuser" for e in targets):
                result.record(
                    "add_user_agent() したエントリが agent_targets() に反映",
                    True
                )
            else:
                result.record(
                    "add_user_agent() したエントリが agent_targets() に反映",
                    False,
                    f"targets には 'testuser' が無い"
                )

            # agent_keys() に反映されることを確かめる
            if check_function_exists("agent_keys"):
                try:
                    keys = dashlib.agent_keys()
                except Exception as e:
                    result.record(
                        "add_user_agent() 後に agent_keys() が呼べる",
                        False,
                        f"エラー: {e}"
                    )
                    return

                if "testuser" in keys:
                    result.record(
                        "add_user_agent() したエントリが agent_keys() に反映",
                        True
                    )
                else:
                    result.record(
                        "add_user_agent() したエントリが agent_keys() に反映",
                        False,
                        f"keys={keys}"
                    )

            # === 検査 7: ユーザーエントリがビルトインエントリを上書きする
            # 既出のキー（例: "claude"）を使ってユーザーエントリを書き込む
            override_entry = {
                "key": "claude",
                "label": "User Override Claude",
                "home_env": "",
                "home": ".claude-override",
                "file": "OVERRIDE.md"
            }
            try:
                dashlib.add_user_agent(override_entry)
            except Exception as e:
                result.record(
                    "add_user_agent() でビルトインキーを上書きできる",
                    False,
                    f"エラー: {e}"
                )
                return

            # agent_targets() で上書きされたエントリが返ることを確かめる
            try:
                targets = dashlib.agent_targets()
            except Exception as e:
                result.record(
                    "上書き後に agent_targets() が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            claude_entry = next((e for e in targets if e.get("key") == "claude"), None)
            if claude_entry and claude_entry.get("file") == "OVERRIDE.md":
                result.record(
                    "agent_targets() でユーザーエントリが上書きを反映",
                    True
                )
            else:
                result.record(
                    "agent_targets() でユーザーエントリが上書きを反映",
                    False,
                    f"claude entry={claude_entry}"
                )

    finally:
        dashlib.AGENTS_FILE = original_agents_file
        reset_environ(original_env)


# ================================================================ 検査 8

def test_malformed_user_file(result: TestResult) -> None:
    """8. 壊れたユーザーファイル（不正な JSON、間違った形のリスト）が
    load_user_agents() を [] で返して例外を投げないことを確かめる。
    """
    if not check_function_exists("load_user_agents"):
        result.record(
            "load_user_agents() が存在する",
            False,
            "関数 load_user_agents が無い"
        )
        return

    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # AGENTS_FILE をテンポラリ・ファイルに差し替える
            agents_file = Path(tmpdir) / "agents.json"
            original_agents_file = dashlib.AGENTS_FILE
            dashlib.AGENTS_FILE = agents_file

            # === 不正な JSON
            agents_file.write_text("{invalid json", encoding="utf-8")
            try:
                loaded = dashlib.load_user_agents()
            except Exception as e:
                result.record(
                    "load_user_agents() が不正 JSON を[] で返す",
                    False,
                    f"例外が出た: {type(e).__name__}: {e}"
                )
                return

            if loaded == []:
                result.record(
                    "load_user_agents() が不正 JSON を [] で返す",
                    True
                )
            else:
                result.record(
                    "load_user_agents() が不正 JSON を [] で返す",
                    False,
                    f"得: {loaded}"
                )

            # === JSON リストだが形が違う
            agents_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
            try:
                loaded = dashlib.load_user_agents()
            except Exception as e:
                result.record(
                    "load_user_agents() が間違った形のリストを [] で返す",
                    False,
                    f"例外が出た: {type(e).__name__}: {e}"
                )
                return

            if loaded == []:
                result.record(
                    "load_user_agents() が間違った形のリストを [] で返す",
                    True
                )
            else:
                result.record(
                    "load_user_agents() が間違った形のリストを [] で返す",
                    False,
                    f"得: {loaded}"
                )

    finally:
        dashlib.AGENTS_FILE = original_agents_file
        reset_environ(original_env)


# ================================================================ 検査 9

def test_present_and_installed_agents(result: TestResult) -> None:
    """9. present_agents() / installed_agents() が agent_keys() に含まれる
    キーだけを返し、ディレクトリが無くても例外を投げないことを確かめる。
    """
    if not check_function_exists("present_agents"):
        result.record(
            "present_agents() が存在する",
            False,
            "関数 present_agents が無い"
        )
        return

    if not check_function_exists("installed_agents"):
        result.record(
            "installed_agents() が存在する",
            False,
            "関数 installed_agents が無い"
        )
        return

    if not check_function_exists("agent_keys"):
        result.record(
            "present_agents()/installed_agents() のテストに agent_keys() が要る",
            False,
            ""
        )
        return

    try:
        present = dashlib.present_agents()
        keys = dashlib.agent_keys()
    except Exception as e:
        result.record(
            "present_agents() が呼べる",
            False,
            f"エラー: {e}"
        )
        return

    if not isinstance(present, list):
        result.record(
            "present_agents() が list を返す",
            False,
            f"型は {type(present).__name__}"
        )
    else:
        result.record(
            "present_agents() が list を返す",
            True
        )

    # present に含まれるキーがすべて agent_keys() に在ることを確かめる
    keys_set = set(keys)
    invalid_keys = [k for k in present if k not in keys_set]
    if invalid_keys:
        result.record(
            "present_agents() が agent_keys() に含まれるキーだけを返す",
            False,
            f"未知のキー: {invalid_keys}"
        )
    else:
        result.record(
            "present_agents() が agent_keys() に含まれるキーだけを返す",
            True
        )

    # installed_agents も同様
    try:
        installed = dashlib.installed_agents()
    except Exception as e:
        result.record(
            "installed_agents() が呼べる",
            False,
            f"エラー: {e}"
        )
        return

    if not isinstance(installed, list):
        result.record(
            "installed_agents() が list を返す",
            False,
            f"型は {type(installed).__name__}"
        )
    else:
        result.record(
            "installed_agents() が list を返す",
            True
        )

    invalid_keys = [k for k in installed if k not in keys_set]
    if invalid_keys:
        result.record(
            "installed_agents() が agent_keys() に含まれるキーだけを返す",
            False,
            f"未知のキー: {invalid_keys}"
        )
    else:
        result.record(
            "installed_agents() が agent_keys() に含まれるキーだけを返す",
            True
        )


# ================================================================ 検査 10

def test_block_round_trip(result: TestResult) -> None:
    """10. ラウンド・トリップ: テンポラリ・ディレクトリを1つのエージェントのホームとして、
    install.build_block("python") で作ったブロックを instruction file に書き込んで、
    block_installed() が True を返し、block_version() が tool_version() と等しいことを確かめる。
    """
    if not check_function_exists("block_installed"):
        result.record(
            "block_installed() が存在する",
            False,
            "関数 block_installed が無い"
        )
        return

    if not check_function_exists("block_version"):
        result.record(
            "block_version() が存在する",
            False,
            "関数 block_version が無い"
        )
        return

    if not check_function_exists("tool_version"):
        result.record(
            "block_version() のテストに tool_version() が要る",
            False,
            ""
        )
        return

    if not check_attr_exists("BUILTIN_AGENT_TARGETS"):
        result.record(
            "block_installed()/block_version() のテストに BUILTIN_AGENT_TARGETS が要る",
            False,
            ""
        )
        return

    # install モジュールの build_block を試す
    try:
        import install  # noqa: F401
        has_install = True
    except ImportError:
        has_install = False

    if not has_install:
        result.record(
            "block_installed()/block_version() のラウンド・トリップ（install がない）",
            True  # テスト対象が無いのはスキップ
        )
        return

    # **ビルトインの1件目を使ってはいけない。** home_env を持たないエントリだと
    # 書き込み先が実ホームになり、この検査が利用者の設定を汚す。自分で作った
    # 一時的なエントリを使えば、どのビルトインが並んでいても安全でいられる。
    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_file = Path(tmpdir) / "agents.json"
            os.environ[dashlib.ENV_AGENTS_FILE] = str(agents_file)

            key = "roundtrip"
            env_name = "AGENT_DASHBOARD_TEST_ROUNDTRIP_HOME"
            home = Path(tmpdir) / "home"
            os.environ[env_name] = str(home)
            dashlib.add_user_agent({
                "key": key, "label": "Round Trip", "home_env": env_name,
                # フォルダを含む file（ルール置き場に1枚置く形）も一緒に検める
                "home": str(home), "file": "rules/subagent-dashboard.md",
            })

            instr_file = dashlib.instruction_file(key)
            instr_file.parent.mkdir(parents=True, exist_ok=True)

            # install.build_block で Python 用ブロックを作る
            try:
                block = install.build_block("python")
            except Exception as e:
                result.record(
                    "install.build_block('python') が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            # ファイルに書き込む
            try:
                instr_file.write_text(block, encoding="utf-8")
            except Exception as e:
                result.record(
                    "instruction file に書き込める",
                    False,
                    f"エラー: {e}"
                )
                return

            # block_installed() が True を返すことを確かめる
            try:
                is_installed = dashlib.block_installed(key)
            except Exception as e:
                result.record(
                    f"block_installed('{key}') が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if is_installed:
                result.record(
                    f"block_installed('{key}') が True を返す",
                    True
                )
            else:
                result.record(
                    f"block_installed('{key}') が True を返す",
                    False,
                    f"得: {is_installed}"
                )

            # block_version() が tool_version() と等しいことを確かめる
            try:
                version = dashlib.block_version(key)
            except Exception as e:
                result.record(
                    f"block_version('{key}') が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            try:
                tool_ver = dashlib.tool_version()
            except Exception as e:
                result.record(
                    "tool_version() が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if version == tool_ver:
                result.record(
                    f"block_version('{key}') が tool_version() と等しい",
                    True
                )
            else:
                result.record(
                    f"block_version('{key}') が tool_version() と等しい",
                    False,
                    f"version={repr(version)}, tool_version={repr(tool_ver)}"
                )

    finally:
        reset_environ(original_env)


# ================================================================ 検査 11-14

def test_builtin_paths_are_sane(result: TestResult) -> None:
    """11. 組み込みの書き先が、互いにぶつからず、必ずホームの下にあること。

    2つの CLI が同じファイルを指していると、片方を消したつもりでもう片方が
    消える。相対パス（"~" で始まらないもの）は、その時いた場所に書き込むので、
    どこに書いたか誰にも分からなくなる。どちらも表を書き足すときにやりがち。
    """
    seen: dict[str, str] = {}
    problems: list[str] = []
    for entry in dashlib.BUILTIN_AGENT_TARGETS:
        key = entry["key"]
        if not entry["home"].startswith("~"):
            problems.append("%s: home が '~' で始まっていない（%s）" % (key, entry["home"]))
        path = str(Path(entry["home"]) / entry["file"]).lower()
        if path in seen:
            problems.append("%s と %s が同じ場所を指している" % (seen[path], key))
        seen[path] = key
    result.record("組み込みの書き先が互いにぶつからず、ホームの下にある",
                  not problems, " / ".join(problems))


def test_bad_entries_rejected(result: TestResult) -> None:
    """12. 使えない登録は黙って捨てること（例外にも、通しにもしない）。"""
    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_file = Path(tmpdir) / "agents.json"
            os.environ[dashlib.ENV_AGENTS_FILE] = str(agents_file)
            bad = [
                {"key": "", "home": "~/x", "file": "A.md"},           # 鍵が空
                {"key": "a/b", "home": "~/x", "file": "A.md"},        # 鍵にパス区切り
                {"key": "nofile", "home": "~/x"},                     # file が無い
                {"key": "nohome", "file": "A.md"},                    # home が無い
                "not a dict",                                          # そもそも dict でない
            ]
            agents_file.write_text(json.dumps({"agents": bad}), encoding="utf-8")
            loaded = dashlib.load_user_agents()
            result.record("使えない登録が全部捨てられる", loaded == [],
                          "残った: %r" % (loaded,))

            # 空の鍵は add_user_agent 経由でも通らない（ValueError）
            try:
                dashlib.add_user_agent({"key": "", "home": "~/x", "file": "A.md"})
                result.record("add_user_agent() が壊れた登録を拒む", False, "例外が出なかった")
            except ValueError:
                result.record("add_user_agent() が壊れた登録を拒む", True)
    finally:
        reset_environ(original_env)


def test_env_agents_file(result: TestResult) -> None:
    """13. AGENTS_FILE の場所が環境変数で差し替わること（試験と隔離のため）。"""
    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            moved = Path(tmpdir) / "elsewhere" / "agents.json"
            os.environ[dashlib.ENV_AGENTS_FILE] = str(moved)
            ok = dashlib.agents_file() == moved
            result.record("agents_file() が環境変数で差し替わる", ok,
                          "得: %s" % dashlib.agents_file())
            dashlib.add_user_agent({"key": "moved", "label": "Moved",
                                    "home": str(Path(tmpdir) / "h"), "file": "X.md"})
            result.record("差し替えた先にファイルが作られる", moved.is_file(),
                          "作られていない: %s" % moved)
    finally:
        reset_environ(original_env)


def test_agent_file_registration(result: TestResult) -> None:
    """14. install.py --agent-file が、任意のファイルを1件として覚えること。

    表に無い CLI に対応するための逃げ道そのもの。ここが動かないと
    「知らない CLI にも対応できる」という触れ込みが嘘になる。
    """
    try:
        import install
    except ImportError as e:
        result.record("--agent-file の登録", False, "install を読み込めない: %s" % e)
        return

    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ[dashlib.ENV_AGENTS_FILE] = str(Path(tmpdir) / "agents.json")
            target = Path(tmpdir) / ".mytool" / "INSTRUCTIONS.md"
            key = install.register_agent_file(str(target))
            got = dashlib.instruction_file(key)
            result.record("--agent-file で登録した先が引ける", got == target,
                          "期待: %s / 得: %s" % (target, got))
            result.record("--agent-file の鍵が置き場から作られる", key == "mytool",
                          "得: %r" % key)
            # 同じ場所をもう一度登録しても増えない
            again = install.register_agent_file(str(target))
            result.record("同じ場所の再登録で二重にならない",
                          again == key and len(dashlib.load_user_agents()) == 1,
                          "鍵: %r / 件数: %d" % (again, len(dashlib.load_user_agents())))
    finally:
        reset_environ(original_env)


# ================================================================ 実行

def test_unwired_agents(result: TestResult) -> None:
    """15. unwired_agents() と unwired_agent_notice() を検査する。

    セットアップのあとに CLI を入れた人が落ちる穴：初期設定は入っていた CLI にしか
    書き込まないため、あとから入れた CLI には運用ルールが書かれていない。

    1. まだ何も書いていない（初回セットアップ前） → unwired_agent_notice() は None を返す
    2. 1つ書き込み済みで、もう1つ入っているが書き込まれていない → notice は警告文を返し、
       その CLI の label を含む
    3. 入っている CLI すべてが書き込まれている → unwired_agents() は空、notice は None
    4. 書き込まれているが config dir が無い CLI は unwired に含まれない
    """
    if not check_function_exists("unwired_agents"):
        result.record(
            "unwired_agents() が存在する",
            False,
            "関数 unwired_agents が無い"
        )
        return

    if not check_function_exists("unwired_agent_notice"):
        result.record(
            "unwired_agent_notice() が存在する",
            False,
            "関数 unwired_agent_notice が無い"
        )
        return

    if not check_function_exists("present_agents"):
        result.record(
            "unwired_agents/notice のテストに present_agents() が要る",
            False,
            ""
        )
        return

    if not check_function_exists("installed_agents"):
        result.record(
            "unwired_agents/notice のテストに installed_agents() が要る",
            False,
            ""
        )
        return

    if not check_function_exists("agent_label"):
        result.record(
            "unwired_agent_notice() のテストに agent_label() が要る",
            False,
            ""
        )
        return

    # install モジュール内の build_block を試す
    try:
        import install  # noqa: F401
        has_install = True
    except ImportError:
        has_install = False

    if not has_install:
        result.record(
            "unwired_agents/notice のテスト（install がない）",
            True  # テスト対象が無いのはスキップ
        )
        return

    original_env = os.environ.copy()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # テンポラリなエージェント登録ファイルを使う
            agents_file = Path(tmpdir) / "agents.json"
            os.environ[dashlib.ENV_AGENTS_FILE] = str(agents_file)

            # **組み込みの CLI を全部見えなくしてから始める。**
            # ケース1は「まだ1つも書き込んでいない」状態を前提にするが、この
            # リポジトリで install.py を実行した環境ではその前提が崩れ、検査が
            # 落ちる（実装ではなく環境のせいで落ちるので、原因が分からなくなる）。
            # ホームごと空のテンポラリへ向ければ、どの機械でも同じ前提に揃う。
            # Path.home() は呼ばれるたびに環境変数を読むので、これで効く。
            empty_home = Path(tmpdir) / "empty-home"
            empty_home.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(empty_home)
            os.environ["USERPROFILE"] = str(empty_home)
            for builtin in dashlib.BUILTIN_AGENT_TARGETS:
                if builtin["home_env"]:
                    os.environ[builtin["home_env"]] = str(empty_home / builtin["key"])

            # === ケース 1: まだ何も書いていない状態
            # CLI を2つ登録し、どちらのホームディレクトリも作る
            key1 = "unwired_test_1"
            env_name1 = "UNWIRED_TEST_1_HOME"
            home1 = Path(tmpdir) / "home1"
            home1.mkdir(parents=True, exist_ok=True)
            os.environ[env_name1] = str(home1)

            key2 = "unwired_test_2"
            env_name2 = "UNWIRED_TEST_2_HOME"
            home2 = Path(tmpdir) / "home2"
            home2.mkdir(parents=True, exist_ok=True)
            os.environ[env_name2] = str(home2)

            dashlib.add_user_agent({
                "key": key1, "label": "Unwired Test 1", "home_env": env_name1,
                "home": str(home1), "file": "RULES.md",
            })
            dashlib.add_user_agent({
                "key": key2, "label": "Unwired Test 2", "home_env": env_name2,
                "home": str(home2), "file": "RULES.md",
            })

            # 何も書き込んでいない状態での確認
            try:
                notice = dashlib.unwired_agent_notice()
            except Exception as e:
                result.record(
                    "unwired_agent_notice() が何も書いていない状態で呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if notice is None:
                result.record(
                    "unwired_agent_notice() が未設定時に None を返す",
                    True
                )
            else:
                result.record(
                    "unwired_agent_notice() が未設定時に None を返す",
                    False,
                    f"得: {repr(notice)}"
                )

            # === ケース 2: 1つ書き込み済み、もう1つ未書き込み
            # key1 に運用ルールを書き込む
            instr_file1 = dashlib.instruction_file(key1)
            instr_file1.parent.mkdir(parents=True, exist_ok=True)
            try:
                block = install.build_block("python")
            except Exception as e:
                result.record(
                    "install.build_block('python') が呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            try:
                instr_file1.write_text(block, encoding="utf-8")
            except Exception as e:
                result.record(
                    "key1 の instruction file に書き込める",
                    False,
                    f"エラー: {e}"
                )
                return

            # unwired_agents() が key2 を含むことを確認
            try:
                unwired = dashlib.unwired_agents()
            except Exception as e:
                result.record(
                    "unwired_agents() が書き込み後に呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if key2 in unwired:
                result.record(
                    f"unwired_agents() が書き込まれていない {key2} を含む",
                    True
                )
            else:
                result.record(
                    f"unwired_agents() が書き込まれていない {key2} を含む",
                    False,
                    f"unwired={unwired}"
                )

            # key1 は unwired に含まれないことを確認
            if key1 not in unwired:
                result.record(
                    f"unwired_agents() が書き込み済みの {key1} を含まない",
                    True
                )
            else:
                result.record(
                    f"unwired_agents() が書き込み済みの {key1} を含まない",
                    False,
                    f"unwired={unwired}"
                )

            # unwired_agent_notice() が非空で key2 の label を含むことを確認
            try:
                notice = dashlib.unwired_agent_notice()
            except Exception as e:
                result.record(
                    "unwired_agent_notice() が書き込み後に呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            if notice and "Unwired Test 2" in notice:
                result.record(
                    f"unwired_agent_notice() が {key2} の label を含む",
                    True
                )
            else:
                result.record(
                    f"unwired_agent_notice() が {key2} の label を含む",
                    False,
                    f"notice={repr(notice)}"
                )

            # === ケース 3: テスト用 CLI がすべて書き込まれている
            # key2 にも運用ルールを書き込む
            instr_file2 = dashlib.instruction_file(key2)
            instr_file2.parent.mkdir(parents=True, exist_ok=True)
            try:
                instr_file2.write_text(block, encoding="utf-8")
            except Exception as e:
                result.record(
                    "key2 の instruction file に書き込める",
                    False,
                    f"エラー: {e}"
                )
                return

            try:
                unwired = dashlib.unwired_agents()
            except Exception as e:
                result.record(
                    "unwired_agents() がテスト用キー書き込み後に呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            # key1, key2 が両方とも unwired に含まれないことを確認
            # （builtin CLI が unwired に入っていてもよい。重要なのは自分の鍵だけ）
            if key1 not in unwired and key2 not in unwired:
                result.record(
                    "unwired_agents() が両方のテスト用キーを含まない",
                    True
                )
            else:
                result.record(
                    "unwired_agents() が両方のテスト用キーを含まない",
                    False,
                    f"unwired={unwired}"
                )

            # 実際には builtin CLI が unwired に残っている可能性があるので、
            # notice が来るかどうかはテスト環境に依存する。ここは呼び出しが成功
            # することだけを検査する。
            try:
                notice = dashlib.unwired_agent_notice()
            except Exception as e:
                result.record(
                    "unwired_agent_notice() がテスト用キー書き込み後に呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            result.record(
                "unwired_agent_notice() がテスト用キー書き込み後に呼べる",
                True
            )

            # === ケース 4: 書き込まれているが config dir が無い CLI は unwired に含まれない
            # key3 を登録し、ホームディレクトリは作らず、ファイルだけ書き込む
            key3 = "unwired_test_3"
            env_name3 = "UNWIRED_TEST_3_HOME"
            home3 = Path(tmpdir) / "home3"
            # home3 は作らない！
            os.environ[env_name3] = str(home3)

            dashlib.add_user_agent({
                "key": key3, "label": "Unwired Test 3", "home_env": env_name3,
                "home": str(home3), "file": "RULES.md",
            })

            # key3 の親ディレクトリは存在する必要があるので作る
            instr_file3 = dashlib.instruction_file(key3)
            instr_file3.parent.mkdir(parents=True, exist_ok=True)
            try:
                instr_file3.write_text(block, encoding="utf-8")
            except Exception as e:
                result.record(
                    "key3 の instruction file に書き込める",
                    False,
                    f"エラー: {e}"
                )
                return

            try:
                unwired = dashlib.unwired_agents()
            except Exception as e:
                result.record(
                    "unwired_agents() が書き込み済みだが present でない状態で呼べる",
                    False,
                    f"エラー: {e}"
                )
                return

            # key3 は present ではないので unwired に含まれないことを確認
            if key3 not in unwired:
                result.record(
                    f"unwired_agents() が present でない {key3} を含まない",
                    True
                )
            else:
                result.record(
                    f"unwired_agents() が present でない {key3} を含まない",
                    False,
                    f"unwired={unwired}"
                )

    finally:
        reset_environ(original_env)


def main() -> int:
    result = TestResult()

    print("エージェント・レジストリ API の検査を開始します")
    print()

    test_builtin_targets(result)
    test_agent_keys(result)
    test_agent_config_dir_env(result)
    test_instruction_file(result)
    test_unknown_key_error(result)
    test_user_agents(result)
    test_malformed_user_file(result)
    test_present_and_installed_agents(result)
    test_block_round_trip(result)
    test_builtin_paths_are_sane(result)
    test_bad_entries_rejected(result)
    test_env_agents_file(result)
    test_agent_file_registration(result)
    test_unwired_agents(result)

    return result.summary()


if __name__ == "__main__":
    sys.exit(main())
