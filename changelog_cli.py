#!/usr/bin/env python3
"""Claude Code 変更履歴トラッキング — CLI本体（Phase 1: MVP、UI統合なし）

hooks から呼ばれる2つ（log-event / stop-check）と、Claude が対話ターン内で呼ぶ
summarize、そして手動デバッグ用の render / status / list を提供する。

    log-event [--phase pre|post]   PostToolUse（既定）または PreToolUse の
                                    hook JSON を stdin で受け取り、生ログへ1行追記する。
    stop-check                     Stop の hook JSON を stdin で受け取り、未要約の
                                    生ログがあれば exit 2 でブロックする。
    summarize --session <id> --headline "..." [--body "..."] [--files ...]
                                    セッション要約・index.json・CHANGELOG.md・
                                    中央レジストリを更新する。
    render [--project <path>]      index.json と CHANGELOG.md を再生成する（冪等）。
    status [--project <path>] [--session <id>]
    list   [--project <path>]

hooks から呼ばれる2つは **絶対にセッションを止めてはいけない**（stop-check の
意図的なブロックを除く）。

    log-event  … 何があっても exit 0。
    stop-check … 「未要約がある」と判断して意図的にブロックするときだけ exit 2。
                 それ以外は何があっても exit 0。

「何があっても」には **argparse の失敗も import の失敗も含む**。argparse は
引数が読めないとき exit 2 で終わるが、PreToolUse フックの exit 2 は
「そのツール呼び出しを拒否する」の意味なので、`--phase` の打ち間違い1つで
**すべての Bash が拒否される**（実際に一度起きた）。だから main() は
SystemExit を含む全ての脱出を捕まえ、サブコマンドごとの約束どおりの
終了コードへ正規化してから終わる。フックの command 文字列側にも
`; exit 0` を足してある（changelog_setup.build_hook_specs）——Python が
そもそも起動できなかった場合（このファイルを消した・移動した）は、
こちらのコードは1行も動けないため。stop-check にだけは付けない
（意図的な exit 2 まで潰してしまう）。

Phase 0 実機検証で確認した2つの補正:
    - Windows の既定 stdin デコード（cp932）では日本語が化ける。
      sys.stdin.buffer.read().decode("utf-8") を必ず使う（素朴な sys.stdin.read() は禁止）。
    - Bash が失敗すると PostToolUse が発火しない。そのため PreToolUse（Bash限定）で
      先に status:"pending" を書き、PostToolUse が来たら同じ toolUseId で
      status:"completed" の行を追記する（生ログは追記のみ。書き換えない）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# changelog_setup.py と同じ流儀で、自分の隣を確実に import できるようにする。
# フックは任意の cwd から呼ばれるので、sys.path[0] がここになる保証はない。
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

#: import に失敗しても**この時点では落ちない**。落ちると Python は exit 1（や
#: トレースバック）で終わり、フックとしては「エラーで止まった」ことになる。
#: 何が起きたかは main() が終了コードを正規化したうえで stderr に出す。
IMPORT_ERROR: Exception | None = None
try:
    import dashlib
    import changelog_lib as cl
except Exception as _e:  # pragma: no cover - 配布物が欠けたときの保険
    dashlib = None  # type: ignore[assignment]
    cl = None  # type: ignore[assignment]
    IMPORT_ERROR = _e
else:
    dashlib.use_utf8_stdio()


#: stop-check が「未要約がある」と判断して**意図的に**セッションの終了を
#: 止めるときの終了コード。Claude Code の hooks の約束（2 = ブロック）。
#: これ以外の 2 は必ず 0 へ正規化する（main() 参照）。
BLOCK_EXIT_CODE = 2

#: フックから呼ばれるサブコマンド。ここに挙げたものだけ終了コードを正規化する。
HOOK_COMMANDS = ("log-event", "stop-check")


# ---------------------------------------------------------------- 補助


def die(msg: str) -> None:
    print(f"エラー: {msg}", file=sys.stderr)
    sys.exit(1)


def _read_stdin_json() -> dict:
    """hook stdin を必ず UTF-8 として読む（Phase 0 実機検証で確認した cp932 化け対策）。"""
    raw_bytes = sys.stdin.buffer.read()
    raw = raw_bytes.decode("utf-8")
    if not raw.strip():
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def resolve_project_root(data: dict) -> Path:
    """hook JSON からプロジェクトルートを決める。

    優先順位: 環境変数 CLAUDE_PROJECT_DIR → stdin の "cwd" → プロセスの cwd。

    **CLAUDE_PROJECT_DIR を先に見る。** stdin の "cwd" はセッションの現在の
    作業ディレクトリで、Phase 0 の検証ではプロジェクトルートと一致していたが、
    サブディレクトリで起動されたセッションでは一致しない。cwd を優先すると
    `<project>/src/.claude/changelog/` のような迷子の記録が生まれ、レジストリに
    別プロジェクトとして登録され、同じ作業の履歴が2か所に割れる。
    CLAUDE_PROJECT_DIR は Claude Code が「プロジェクトのルート」として渡してくる
    値なので、記録の置き場所としてはこちらが正しい。
    """
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir and env_dir.strip():
        return Path(env_dir).resolve()
    cwd = data.get("cwd")
    if isinstance(cwd, str) and cwd.strip():
        return Path(cwd).resolve()
    return Path.cwd().resolve()


def project_root_arg(value: str | None) -> Path:
    return Path(value).resolve() if value else Path.cwd().resolve()


# ---------------------------------------------------------------- log-event の
# フィールド組み立て（hook JSON → raw ログの1行）


_EDIT_LIKE_TOOLS = ("Edit", "MultiEdit", "Write", "NotebookEdit")


def _build_fields_pre(data: dict) -> dict | None:
    """PreToolUse（Bash限定）。実行前に status:"pending" で先に記録する。"""
    tool_name = data.get("tool_name")
    if tool_name != "Bash":
        return None  # matcher は Bash 限定の想定。それ以外が来ても何もしない。
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    return {
        "toolName": "Bash",
        "toolUseId": data.get("tool_use_id"),
        "filePath": None,
        "bashCommand": dashlib.as_str(tool_input.get("command")) or None,
        "diffStat": None,
        "bashResult": None,
        "status": "pending",
        "success": None,
        "durationMs": None,
    }


def _build_fields_post(data: dict) -> dict | None:
    tool_name = data.get("tool_name")
    tool_input = data.get("tool_input") if isinstance(data.get("tool_input"), dict) else {}
    tool_response = data.get("tool_response") if isinstance(data.get("tool_response"), dict) else {}

    if tool_name == "Bash":
        return {
            "toolName": "Bash",
            "toolUseId": data.get("tool_use_id"),
            "filePath": None,
            "bashCommand": dashlib.as_str(tool_input.get("command")) or None,
            "diffStat": None,
            "bashResult": cl.extract_bash_result(tool_response),
            "status": "completed",
            "success": cl.infer_bash_success(tool_response),
            # 実機検証で確認済み: PostToolUse の hook JSON はトップレベルに
            # duration_ms を実測値として持つ（例: 1377）。推測ではなく実測値の
            # 受け渡しなので「推測で埋めない」規律には反しない。数値でなければ
            # （欠けている・型がおかしい）dashlib.as_num が None を返し、従来通り
            # null のままになる。
            "durationMs": dashlib.as_num(data.get("duration_ms")),
        }

    if tool_name in _EDIT_LIKE_TOOLS:
        return {
            "toolName": tool_name,
            "toolUseId": data.get("tool_use_id"),
            "filePath": cl.extract_file_path(tool_input, tool_response),
            "bashCommand": None,
            # 変更前全文・diff本体はここで抽出だけして即座に捨てる。
            # extract_diff_stat() の戻り値は {"added": int|None, "removed": int|None} のみ。
            "diffStat": cl.extract_diff_stat(tool_name, tool_input, tool_response),
            "bashResult": None,
            "status": None,  # status は Bash だけが意味を持つ
            "success": None,
            # 実機検証で確認済み: duration_ms はトップレベルに Bash 限定ではなく
            # Edit/Write/NotebookEdit の PostToolUse でも入っている（例: Edit=35,
            # Write=18, NotebookEdit=22）。Bash と同じ扱いで素直に採用する。
            "durationMs": dashlib.as_num(data.get("duration_ms")),
        }

    return None  # matcher に無いツールが来ても静かに無視


def cmd_log_event(args) -> int:
    # ここから下で何が起きても、必ず 0 を返す（hooks の説明を参照）。**sys.exit は
    # 使わない**——途中の sys.exit(0) は SystemExit であって「正常終了」ではなく、
    # 例外処理の流れを分かりにくくするだけ。終了コードは main() が一手に扱う。
    try:
        data = _read_stdin_json()
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"log-event: stdin を読めません（{e}）。記録をスキップします。", file=sys.stderr)
        return 0

    try:
        session_id = data.get("session_id")
        if not session_id:
            return 0  # セッションIDが無いと記録先が決められない

        hook_event_name = data.get("hook_event_name")
        json_phase = "pre" if hook_event_name == "PreToolUse" else "post"
        if args.phase != json_phase:
            print(
                f"log-event: 警告: --phase={args.phase} だが "
                f"hook_event_name={hook_event_name!r}。JSON側を優先します。",
                file=sys.stderr,
            )

        fields = _build_fields_pre(data) if json_phase == "pre" else _build_fields_post(data)
        if fields is None:
            return 0  # 対象外のツール（matcher設定ミス等）

        project_root = resolve_project_root(data)
        row = cl.append_raw_event(project_root, session_id, fields)
        if row is not None:
            cl.upsert_registry(project_root, event_at=dashlib.now_iso())
    except Exception as e:  # フックが例外で落ちてセッションを止めることは絶対に無いようにする
        print(f"log-event: 内部エラー（{type(e).__name__}: {e}）。記録をスキップします。",
              file=sys.stderr)

    return 0


# ---------------------------------------------------------------- stop-check


def auto_headline(pending_events: list[dict]) -> str:
    counts: dict[str, int] = {}
    for e in pending_events:
        tool = e.get("toolName") or "?"
        counts[tool] = counts.get(tool, 0) + 1
    parts = ", ".join(f"{k} x{v}" for k, v in sorted(counts.items()))
    return f"(自動記録) {parts}" if parts else "(自動記録) 変更あり"


def build_digest(pending_events: list[dict]) -> str:
    lines: list[str] = []
    for e in pending_events:
        tool = e.get("toolName")
        if tool == "Bash":
            cmd = e.get("bashCommand") or "?"
            if e.get("bashCommandTruncated"):
                # 生ログに残っているのは先頭だけ、と分かるようにする（切り詰めた
                # 続きを「無かったこと」として要約させないため）。
                cmd = f"{cmd} …（以下略：コマンドが長いため先頭のみ記録）"
            status = e.get("status")
            success = e.get("success")
            if status == "pending":
                tag = "実行中 または 失敗（PostToolUse未着）"
            elif success is True:
                tag = "成功（推測）"
            elif success is False:
                tag = "中断/失敗"
            else:
                tag = "結果不明"
            lines.append(f"- Bash: {cmd}  [{tag}]")
        elif tool in _EDIT_LIKE_TOOLS:
            fp = e.get("filePath") or "?"
            ds = e.get("diffStat") or {}
            added, removed = ds.get("added"), ds.get("removed")
            stat = f"+{added}/-{removed}" if added is not None or removed is not None else "変更行数不明"
            lines.append(f"- {tool}: {fp}  [{stat}]")
        else:
            lines.append(f"- {tool}: {e.get('filePath') or e.get('bashCommand') or ''}")
    return "\n".join(lines) if lines else "(内訳なし)"


def cmd_stop_check(args) -> int:
    try:
        data = _read_stdin_json()
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"stop-check: stdin を読めません（{e}）。ブロックせず終了します。", file=sys.stderr)
        return 0

    try:
        session_id = data.get("session_id")
        if not session_id:
            return 0

        stop_hook_active = bool(data.get("stop_hook_active"))
        project_root = resolve_project_root(data)
        info = cl.pending_summary_info(project_root, session_id)

        if info["pendingCount"] == 0:
            # 未要約が「summarize を実行した Bash 呼び出しそのもの」しか無い場合も
            # ここに来る（pending_summary_info が数えていない）。**何もしない。**
            # 以前はこれを1件と数えていたため、要約を書いた直後の Stop が必ず
            # ブロックし、2回目の Stop で代筆経路に入って auto:true になっていた。
            return 0

        if stop_hook_active:
            # 無限ループ対策: 既にブロックした後の2回目なら、機械的な仮ヘッドラインで
            # 代筆して CHANGELOG.md への反映だけを保証する（Claude に再度書かせない）。
            #
            # **既存の要約（Claude が書いた headline/body）を上書きで消してはいけない。**
            # write_session_summary は毎回まるごと上書きする作りなので、ここで単純に
            # auto_headline() だけを渡すと、以前に手で書いた要約が新しい代筆で
            # 消えてしまう（実際にこの実装で一度再現し、直した）。前回の要約が
            # あればそれを土台にして、今回の分だけ機械的な注記として追記する。
            new_bits = auto_headline(info["pendingEvents"])
            existing = cl.read_session_summary(project_root, session_id)
            prior_headline = (existing or {}).get("headline") or ""
            prior_body = (existing or {}).get("body") or ""
            if prior_headline:
                headline = prior_headline
                note = f"[自動追記] Stop hookの二重ブロックを避けるため、次を機械的に記録しました: {new_bits}"
                body = f"{prior_body}\n\n{note}" if prior_body else note
                # **auto は立てない。** auto は「誰も要約を書かなかったセッション」の
                # 目印（Phase 4 の再要約導線が拾う対象）で、「代筆で1行足した」印では
                # ない。既に人が書いた見出しがあるのに立てると、全セッションが
                # auto:true になって目印の意味が消える（実測でそうなっていた）。
                auto = bool((existing or {}).get("auto"))
            else:
                headline = new_bits
                body = None
                auto = True  # 本当に誰も書かなかったセッションだけ
            cl.write_session_summary(
                project_root,
                session_id,
                headline=headline,
                body=body,
                auto=auto,
                summarized_up_to_seq=info["latestSeq"],
            )
            cl.render_all(project_root)
            cl.upsert_registry(project_root, summary_at=dashlib.now_iso())
            print(
                "stop-check: stop_hook_active=true のため、機械的な仮ヘッドラインで"
                "代筆して CHANGELOG.md への反映だけ保証しました（無限ループ対策）。",
                file=sys.stderr,
            )
            return 0

        # 実行例は Claude が Bash ツール（＝POSIX シェル）へそのまま打つ文字列。
        # 引用は共通のヘルパーに任せる（3か所で流儀を分けない。changelog_lib の
        # 「シェル用の引用符付け」の節を参照）。
        run_line = cl.sh_cli_command(
            "python", str(Path(__file__).resolve()),
            "summarize", "--session", cl.sh_quote(session_id),
            '--headline "<何を・なぜ、一行で>" --body "<詳細（任意）>"',
        )
        digest = build_digest(info["pendingEvents"])
        msg = (
            "このセッションにまだ要約されていない変更履歴があります。"
            "終了する前に次を実行して要約してください:\n"
            f"  {run_line}\n\n"
            "未要約の内容（生ログからの機械集計。捏造せず、これを踏まえて書いてください）:\n"
            f"{digest}"
        )
        print(msg, file=sys.stderr)
        return BLOCK_EXIT_CODE
    except Exception as e:
        print(f"stop-check: 内部エラー（{type(e).__name__}: {e}）。ブロックせず終了します。",
              file=sys.stderr)
        return 0


# ---------------------------------------------------------------- summarize / render


def cmd_summarize(args) -> None:
    project_root = project_root_arg(args.project)
    if not cl.is_valid_session_id(args.session):
        die(f"--session の値が不正です: {args.session!r}")
    if not args.headline or not args.headline.strip():
        die("--headline は必須です（何も書かず終えることはできません）")

    info = cl.pending_summary_info(project_root, args.session)
    summary = cl.write_session_summary(
        project_root,
        args.session,
        headline=args.headline,
        body=args.body,
        auto=False,
        summarized_up_to_seq=info["latestSeq"],
        extra_files=args.files,
    )
    if summary is None:
        die("要約の書き込みに失敗しました（session_id を確認してください）")

    cl.render_all(project_root)
    cl.upsert_registry(project_root, summary_at=dashlib.now_iso())

    tool_total = sum(summary["toolCallCounts"].values())
    print(f"要約を記録しました: {cl.session_summary_path(project_root, args.session)}")
    print(f"  ファイル: {len(summary['filesTouched'])}件 / ツール呼び出し: {tool_total}件"
          f" / summarizedUpToSeq={summary['summarizedUpToSeq']}")
    print(f"  CHANGELOG.md: {cl.changelog_md_path(project_root)}")
    print(f"  index.json  : {cl.index_path(project_root)}")


def cmd_render(args) -> None:
    project_root = project_root_arg(args.project)
    cl.render_all(project_root)
    print(f"再生成しました: {cl.changelog_md_path(project_root)}")
    print(f"                {cl.index_path(project_root)}")


# ---------------------------------------------------------------- status / list（デバッグ用）


def cmd_status(args) -> None:
    project_root = project_root_arg(args.project)
    cdir = cl.changelog_dir(project_root)
    w = 20
    print()
    print(dashlib.pad("プロジェクト", w) + str(project_root))
    print(dashlib.pad("changelog/", w) + str(cdir) + ("" if cdir.is_dir() else "  (未作成)"))

    sessions = cl.list_session_ids_with_logs(project_root)
    summaries = cl.list_all_summaries(project_root)
    summarized_ids = {s.get("sessionId") for s in summaries}
    print(dashlib.pad("生ログのセッション", w) + f"{len(sessions)}件")
    print(dashlib.pad("要約済みセッション", w) + f"{len(summaries)}件")

    reg = [e for e in cl.read_registry() if Path(e["path"]).resolve() == project_root]
    if reg:
        e = reg[0]
        print(dashlib.pad("レジストリ", w)
              + f"lastEventAt={e['lastEventAt'] or '—'} / lastSummaryAt={e['lastSummaryAt'] or '—'}")
    else:
        print(dashlib.pad("レジストリ", w) + "未登録")

    unsummarized = [sid for sid in sessions if sid not in summarized_ids]
    if unsummarized:
        print(dashlib.pad("未要約", w) + ", ".join(unsummarized))

    if args.session:
        info = cl.pending_summary_info(project_root, args.session)
        print()
        print(f"セッション {args.session}:")
        print(f"  latestSeq={info['latestSeq']} summarizedUpToSeq={info['summarizedUpToSeq']} "
              f"pendingCount={info['pendingCount']} hasSummary={info['hasSummary']}")
        if info.get("selfInvocationCount"):
            print(f"  （うち {info['selfInvocationCount']}件は changelog_cli.py 自身の"
                  "呼び出しなので未要約に数えていません）")
        if info["pendingEvents"]:
            print(build_digest(info["pendingEvents"]))
    print()


def cmd_list(args) -> None:
    project_root = project_root_arg(args.project)
    ok, index, err = dashlib.read_json_safe(cl.index_path(project_root))
    entries = index.get("sessions") if ok and isinstance(index, dict) else []
    if not isinstance(entries, list):
        entries = []

    print()
    print(f"プロジェクト: {project_root}")
    if not entries:
        print("  記録がありません（summarize がまだ一度も実行されていません、"
              "または render がまだ実行されていません）。")
        print()
        return

    cols = [("sessionId", 20), ("終了", 22), ("見出し", 40), ("auto", 6), ("F", 4), ("T", 4)]
    print("  " + "".join(dashlib.cell(h, wd) for h, wd in cols))
    print("  " + "".join(dashlib.pad("-" * (wd - 2), wd) for _, wd in cols))
    for e in entries:
        row = [
            dashlib.as_str(e.get("sessionId"))[:18],
            (dashlib.as_str(e.get("endedAt")) or "—")[:19].replace("T", " "),
            dashlib.as_str(e.get("headline")) or "—",
            "yes" if e.get("auto") else "",
            str(e.get("fileCount") or 0),
            str(e.get("toolCallCount") or 0),
        ]
        print("  " + "".join(dashlib.cell(v, wd) for v, (_, wd) in zip(row, cols)))
    print()


# ---------------------------------------------------------------- 引数定義


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Claude Code 変更履歴トラッキング CLI（Phase 1: log-event / "
                     "stop-check / summarize / render / status / list）",
    )
    sub = p.add_subparsers(dest="cmd", metavar="command")

    le = sub.add_parser("log-event", help="hookから: stdinのhook JSONを生ログへ1行追記する")
    le.add_argument("--phase", choices=("pre", "post"), default="post",
                     help="pre=PreToolUse（Bash限定）/ post=PostToolUse（既定）")
    le.set_defaults(func=cmd_log_event)

    sc = sub.add_parser("stop-check", help="hookから: 未要約の生ログがあればexit 2でブロックする")
    sc.set_defaults(func=cmd_stop_check)

    sm = sub.add_parser("summarize", help="セッション要約・index.json・CHANGELOG.md・レジストリを更新する")
    sm.add_argument("--session", required=True, help="対象セッションID")
    sm.add_argument("--headline", required=True, help="一行の見出し（何を・なぜ）")
    sm.add_argument("--body", default=None, help="詳細（任意。省略時はnull）")
    sm.add_argument("--files", nargs="*", default=None,
                     help="生ログから機械抽出したファイル一覧に追加したいものがあれば（任意。上書きではなく追加）")
    sm.add_argument("--project", default=None, help="対象プロジェクトのルート（省略時はカレントディレクトリ）")
    sm.set_defaults(func=cmd_summarize)

    rd = sub.add_parser("render", help="index.jsonとCHANGELOG.mdを再生成する（冪等）")
    rd.add_argument("--project", default=None)
    rd.set_defaults(func=cmd_render)

    st = sub.add_parser("status", help="デバッグ用: 現在の状態を表示する")
    st.add_argument("--project", default=None)
    st.add_argument("--session", default=None, help="このセッションの未要約分も見る")
    st.set_defaults(func=cmd_status)

    ls = sub.add_parser("list", help="デバッグ用: セッション一覧を表示する")
    ls.add_argument("--project", default=None)
    ls.set_defaults(func=cmd_list)

    return p


def _warn(msg: str) -> None:
    """stderr へ1行。**ここで失敗しても呼び手を巻き込まない**（出力先が閉じている
    ことすらありうる。終了コードの正規化より優先されるものは無い）。"""
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


def _requested_command(argv: list[str]) -> str | None:
    """argparse に通す**前に**、どのサブコマンドの呼び出しかだけを読む。

    argparse は引数が読めないと問答無用で exit 2 で終わるので、その前に
    「これはフックからの呼び出しか」を知っておく必要がある（フックかどうかで
    終了コードの約束が違う）。フックのサブコマンド名が argv のどこかにあれば
    それを採る——`--bogus log-event` のような壊れた並びでも、意図は読めるため。
    """
    for a in argv:
        if a in HOOK_COMMANDS:
            return a
    for a in argv:
        if not a.startswith("-"):
            return a
    return None


def main(argv: list[str] | None = None) -> int:
    """終了コードを返す（sys.exit はここから先でしか呼ばない）。

    **この関数からは例外も SystemExit も外に出ない。** フックから呼ばれる
    log-event / stop-check については、argparse の失敗（exit 2）・import の失敗・
    想定外の例外まで含めて、約束どおりの終了コードへ必ず正規化する:

        log-event  → 常に 0
        stop-check → cmd_stop_check が意図して返した BLOCK_EXIT_CODE のときだけ 2。
                     それ以外（argparse の 2 も含む）は 0。

    「意図した 2」かどうかは**値ではなく出どころ**で見分ける。意図的なブロックは
    cmd_stop_check の `return` から来るのに対し、argparse の 2 は SystemExit として
    飛んでくる——だから下の except に落ちた時点で、それは意図した 2 ではない。
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = _requested_command(argv)
    is_hook = cmd in HOOK_COMMANDS

    try:
        if IMPORT_ERROR is not None:
            _warn(f"{cmd or 'changelog_cli'}: 必要なモジュールを読み込めません"
                  f"（{type(IMPORT_ERROR).__name__}: {IMPORT_ERROR}）。"
                  + ("記録をスキップします。" if is_hook else ""))
            return 0 if is_hook else 1

        parser = build_parser()
        args = parser.parse_args(argv)
        func = getattr(args, "func", None)
        if func is None:
            parser.print_help()
            return 0
        code = func(args)
        return code if isinstance(code, int) else 0

    except SystemExit as e:
        raw = e.code
        code = 0 if raw is None else (raw if isinstance(raw, int) else 1)
        if is_hook:
            if code != 0:
                _warn(f"{cmd}: 引数を解釈できませんでした（終了コード {code}）。"
                      "フックがセッションを止めないよう 0 として終了します。")
            return 0
        return code

    except BaseException as e:  # KeyboardInterrupt も含めて、外に出さない
        _warn(f"{cmd or 'changelog_cli'}: 内部エラー（{type(e).__name__}: {e}）。"
              + ("ブロックせず終了します。" if is_hook else ""))
        return 0 if is_hook else 1


if __name__ == "__main__":
    sys.exit(main())
