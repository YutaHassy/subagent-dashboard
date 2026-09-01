#!/usr/bin/env python3
"""Subagent Dashboard — VSCode 拡張の組み立て

    dash ext build       .vsix を dist/ に作るだけ
    dash ext install     組み立てて VSCode に入れる
    dash ext package     配布物一式を作る（.vsix と「古い版を抜く.bat」）
    dash ext status      入っているか確認する
    dash ext uninstall   拡張機能を抜く

直接 `python build_vsix.py build` としても同じ（dash.py が sys.argv を差し替えて
main() を呼ぶだけなので、呼ばれ方の違いは使い方の表示に出る文言だけ）。

.vsix は中身が決まった zip でしかないので、**npm も vsce も使わない**。
外部ライブラリは使いません（Python 標準ライブラリのみ）。

同梱するもの:
    extension/            拡張そのもの（package.json / extension.js / media/）
    extension/tool/       ダッシュボード本体（これが無いと拡張は初期設定すらできない）

同梱漏れを止める仕組み（0.2.1〜0.2.3 の事故の再発防止）:
    本体が丸ごと欠けた .vsix を3回配った。原因は「列挙し忘れ」を検出する手立てが
    無かったこと。そこで PAYLOAD_FILES（同梱する）と PAYLOAD_SKIP（配らないと決めた）の
    どちらにも載っていないファイルがリポジトリにあれば、ビルドを中止する。
    新しいファイルを足した人は、必ずどちらかに書くことになる。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dashlib  # noqa: E402

dashlib.use_utf8_stdio()

EXT_SRC = HERE / "extension"
DIST = HERE / "dist"


# ---------------------------------------------------------------- 同梱するもの
#
# **順序に意味がある。** この順でそのまま zip に書き出す。並べ替えると .vsix の
# バイト列が変わり、「前回と同じものを作り直したのか」を差分で確かめられなくなる。
#
# VERSION が先頭なのは、これだけが生成物だから（下の write_version_file を参照）。
# 残りはリポジトリのファイルをそのまま入れる。

PAYLOAD_FILES = [
    "VERSION",              # 生成物。package.json の version から作る
    "dash.py",              # 統合エントリポイント
    "server.py",            # 配信サーバー
    "dashlib.py",           # 共通ロジック
    # 稼働中のサブエージェントを Claude Code の記録から実測で読む。dashlib が
    # assign_live_safely() の中で import する。**必ず配ること。** 配らないと import が
    # 失敗して、その except に吸われ「live が永久に出ない」という気づけない壊れ方になる。
    "livefeed.py",
    "i18n.py",              # 文言の切り替え（dashlib が import する）
    "i18n_data.py",         # 文言表 ja/zh/ko。無くても英語で動くが、無いと英語しか出ない
    "i18n_data_update.py",  # 同上（update_state.py の分）
    "i18n_data_install.py", # 同上（install.py の分）
    "update_state.py",      # 状態更新CLI
    "install.py",           # 初期設定
    # 変更履歴トラッキング（Claude Code 専用）。changelog_cli.py は hooks から、
    # changelog_setup.py は拡張機能のワークスペース初期設定から呼ばれる。
    # 3つとも配布先で要る——1つでも欠けると hooks が ImportError で落ちる。
    "changelog_lib.py",     # 記録・要約・CHANGELOG.md 生成の土台
    "changelog_cli.py",     # hooks から呼ばれる CLI 本体
    "changelog_setup.py",   # プロジェクトローカルの初期設定
    "open_dashboard.py",    # キーバインドの旧形式が案内している
    "diagnose.py",          # 完了メッセージが案内している
    "dash.cmd",             # ランチャ（Windows）
    "dash",                 # ランチャ（POSIX）
    "public/index.html",    # 画面
    "public/i18n.js",       # 画面の文言表。index.html が <head> で読む
    "public/manual-i18n.js",  # 取扱説明書の本文。manual.html が <head> で読む
    "public/manual.html",   # 取扱説明書
    # 文書は4言語とも配る。**英語版だけにしないこと。** install.py が CLAUDE.md へ
    # 書き込む運用ルールは、その言語の OPERATION.<lang>.md を参照先として埋め込む。
    # 配らないと、そこだけリンク切れになる（配布先でしか起きないので気づけない）。
    "README.md",            # 導入手順（英語＝基準版）
    "README.ja.md",
    "README.zh.md",
    "README.ko.md",
    "OPERATION.md",         # 運用の手引き（英語＝基準版）
    "OPERATION.ja.md",
    "OPERATION.zh.md",
    "OPERATION.ko.md",
]

# 「配らないと決めた」もの。ここに書いてあれば同梱漏れ検査は通す。
# 無くても配布先で動くものだけを入れること。**配布先でも要るものを間違って
# ここへ入れると、開発ディレクトリでは動くのに配った先では動かない**という、
# いちばん気づきにくい壊れ方をする（0.4.2 で実際に踏んだ。CHANGELOG 参照）。
PAYLOAD_SKIP = {
    # 組み立て・配布の道具そのもの
    "build_vsix.py",
    "package_dist.py",
    "check_wiring.py",
    "check_i18n.py",
    "check_livefeed.py",
    "check_agents.py",
    "check_lang.py",
    "auto_setup.py",
    "make_icons.py",
    "make_icons_simple.py",
    # 試験（配布先では走らせない）
    "test_tabs.py",
    "test_parallel.py",
    "test_upgrade.py",
    # 開発用の文書。.md は許可制にしてある（README / OPERATION の4言語版だけを配る）
    "EXTENSION_PLAN.md",
    "AUTOSETUP_TEST_GUIDE.md",
    "CODE_REFERENCE.md",
    "FEATURE_GUIDE.md",
    "CHANGELOG.md",
    "RESTORE_NOTES.md",
    "配布後のセットアップ手順.md",
    # このリポジトリを触るエージェント向けの指示。**製品の一部ではない**ので配らない
    # （配ると、配布先の CLAUDE.md をこちらの開発ルールで上書きしかねない）
    "CLAUDE.md",
}

# 同梱漏れ検査で「本体候補」として拾う対象。
# 拡張子で絞るのは、dist/ の生成物や配布用の .bat / .html まで拾って
# 「知らないファイルがある」と鳴らないようにするため。public/ の下は全部が候補。
SCAN_SUFFIXES = (".py", ".md", ".cmd")
SCAN_NAMES = ("dash", "VERSION")
SCAN_DIRS = ("public",)

# extension/ 側で配らないもの。こちらは順序も列挙も
# 「ディレクトリを名前順にたどる」で決まるので、除外だけを書く。
EXT_SKIP = {
    "test_extension.js",    # 動作確認用。node で走らせるもの
    "make_icons.py",        # media/ のアイコン生成スクリプト
    "make_icons_simple.py",
    "package-lock.json",
    "node_modules",
    "__pycache__",
    ".vscodeignore",
    ".DS_Store",
}


# ---------------------------------------------------------------- 古い拡張 ID
#
# 0.4.3 で発行元を local から YutaHassy へ変えた。VSCode にとって拡張 ID は
# 「発行元.名前」なので、これは別物の拡張になる。--force で入れ替わるのは ID が
# 同じときだけで、古いほうは残り、アイコンもサーバーも2つ並んで動いてしまう。
# 気づかないまま2つ動いている状態を作らないよう、install と status で見張る。
#
# **一覧はこれで全部。** 名前（package.json の name）は 0.1.0 から一度も変えていないので、
# この製品がこれまでに名乗った ID は local.agent-dashboard（0.1.0〜0.4.2）と
# YutaHassy.agent-dashboard（0.4.3〜、現行）の2つだけ。古いほうはこの1件で尽きている。
#
# **表示名を変えても ID は変わらない。** ID は publisher.name だけで決まる。製品名を
# Subagent Dashboard に統一したときも name は agent-dashboard のまま据え置いた。
# name か publisher を変える日が来たら、そのとき捨てる側の ID をここへ足すこと。
# 逆に、存在しない ID を足さないこと（.bat が毎回「入っていません」と出すだけになる）。

LEGACY_EXT_IDS = ("local.agent-dashboard",)


# ---------------------------------------------------------------- 生成物の名前

CLEANUP_BAT = "古い版を抜く.bat"

# 手順書は package_dist.py（dash package）が作る。build_vsix.py は作らない。
# ここに名前だけ持っているのは、**古い手順書を消すため**。`ext build` は .vsix だけを
# 作り直すので、dist/ に前回の手順書が残ると「新しい .vsix と古い説明」が並ぶ。
# 黙って残していたので、見つけたら消して知らせる。
GUIDE_HTML = "セットアップ手順.html"


# ---------------------------------------------------------------- 「古い版を抜く.bat」
#
# 配る相手に「拡張機能パネルを開いて発行元を見比べて消してください」と頼まずに
# 済ませるための後始末スクリプト。ダブルクリックすると、入っていれば抜き、
# 入っていなければ何もしない。missions/ などの記録には触れない。
#
# 差し込むのは OLD_IDS だけ（LEGACY_EXT_IDS から埋めるので、一覧を増やせば
# .bat も勝手に追従する）。
#
# **%% 書式（"...%s" % x）は使わない。** 本文は `%%i` や `%LOCALAPPDATA%` のように
# `%` だらけで、書式に渡した瞬間に全部を書き直すはめになる。str.format にしておけば
# `%` はただの文字で通る（本文に波括弧は1つも無い）。
#
# **製品名 Subagent Dashboard は空白を含む。** 出しているのは rem と echo の行だけで、
# set にも findstr にも渡していない。渡すなら `set "NAME=Subagent Dashboard"` のように
# 代入全体を引用符で囲むこと（`set NAME=Subagent Dashboard` だと末尾の空白まで入る）。
# `for %%i in (...)` に入れると空白で2語に割れるので、そこへは絶対に入れない。
#
# **丸括弧 ( ) を案内文に書かないこと。** 案内文は `if ... ( ... )` の中にあり、
# 素の `)` はその場でブロックを閉じてしまう。使うなら全角の（）にする
# （CP932 の全角括弧は 2バイト目が 0x69/0x6A なので cmd.exe には括弧に見えない）。
#
# 書き出しは CP932・改行は CRLF（write_cleanup_bat を参照）。

CLEANUP_TEMPLATE = """@echo off
rem 古い版（発行元 local）の Subagent Dashboard を VSCode から抜く。
rem 0.4.3 で発行元を変えたため拡張 ID が変わった。VSCode にとっては別物の拡張なので、
rem 新しいほうを入れても古いほうは残り、2つ並んで動いてしまう。
rem このファイルは自動生成物（build_vsix.py の CLEANUP_TEMPLATE）。手で直さないこと。

rem 遅延展開は使わない。有効にすると案内文の [!] の ! が消える。
setlocal
for /f "tokens=2 delims=:" %%c in ('chcp') do set "SAVED_CP=%%c"
chcp 932 >nul

set "OLD_IDS={old_ids}"

echo.
echo   古い版の Subagent Dashboard を抜きます
echo   ================================================
echo.

set "CODE="
for /f "delims=" %%p in ('where code 2^>nul') do if not defined CODE set "CODE=%%p"
if not defined CODE if exist "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\bin\\code.cmd" set "CODE=%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\bin\\code.cmd"
if not defined CODE if exist "%ProgramFiles%\\Microsoft VS Code\\bin\\code.cmd" set "CODE=%ProgramFiles%\\Microsoft VS Code\\bin\\code.cmd"

if not defined CODE (
  echo   [!] VSCode の code コマンドが見つかりませんでした。
  echo.
  echo       お手数ですが、手で抜いてください。
  echo         1. VSCode を開く
  echo         2. Ctrl+Shift+X で拡張機能パネルを開く
  echo         3. 「Subagent Dashboard」で検索する
  echo            出てこないときは、検索欄に @installed agent-dashboard と入れる
  echo         4. 発行元が local のほうを右クリックし、アンインストールを選ぶ
  goto :done
)

echo   VSCode        %CODE%
echo.

set /a REMOVED=0
set /a FAILED=0
for %%i in (%OLD_IDS%) do (
  call "%CODE%" --list-extensions | findstr /i /x /c:"%%i" >nul
  if errorlevel 1 (
    echo   入っていません: %%i
  ) else (
    echo   抜いています: %%i
    call "%CODE%" --uninstall-extension %%i
    if errorlevel 1 (set /a FAILED+=1) else (set /a REMOVED+=1)
  )
)

echo.
if %FAILED% GTR 0 (
  echo   [!] 抜けなかったものがあります。
  echo       VSCode を閉じてからもう一度実行するか、拡張機能パネル（Ctrl+Shift+X）で
  echo       「Subagent Dashboard」または @installed agent-dashboard で探し、
  echo       発行元が local のほうを手で削除してください。
) else if %REMOVED% GTR 0 (
  echo   [OK] 抜きました。VSCode を開いているときは再読み込みしてください。
  echo        Ctrl+Shift+P → Reload Window
) else (
  echo   [OK] 古い版は入っていませんでした。何もしていません。
)

echo.
echo   作業の記録（.claude\\agent-dashboard）には触っていません。
echo   新しい版を入れると、そのまま続きから見られます。

:done
echo.
pause
chcp %SAVED_CP% >nul
endlocal
"""


# ---------------------------------------------------------------- .vsix の中身の型
#
# [Content_Types].xml は「この拡張子はこの種類」という対応表。VSCode は
# これを読んでから中身を取り出すので、載っていない拡張子があると展開に失敗する。
# 拡張子を持たないもの（VERSION と dash）は Default では書けないので Override で補う。

CONTENT_TYPES = {
    "cmd": "text/plain",
    "html": "text/html",
    "js": "application/javascript",
    "json": "application/json",
    "md": "text/markdown",
    "png": "image/png",
    "py": "text/plain",
    "svg": "image/svg+xml",
    "vsixmanifest": "text/xml",
}
DEFAULT_CONTENT_TYPE = "text/plain"  # 拡張子を持たないもの（VERSION / dash）


class BuildError(Exception):
    """ビルドを中止する理由。main() が拾って理由だけを出す。"""


# ---------------------------------------------------------------- package.json


def read_package_json() -> dict:
    """extension/package.json を読む。ここが版と ID の唯一の出どころ。"""
    import json

    path = EXT_SRC / "package.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise BuildError(f"{path} を読めません（{e}）") from e
    except json.JSONDecodeError as e:
        raise BuildError(f"{path} が JSON として読めません（{e}）") from e


def ext_id(pkg: dict) -> str:
    """VSCode から見た拡張 ID（発行元.名前）。"""
    return f"{pkg.get('publisher', '')}.{pkg.get('name', '')}"


def vsix_name(pkg: dict) -> str:
    return f"{pkg.get('name', 'extension')}-{pkg.get('version', '0.0.0')}.vsix"


# ---------------------------------------------------------------- 同梱漏れ検査


def scan_payload_candidates() -> list[str]:
    """リポジトリ側の「本体候補」を走査する。返すのは PAYLOAD_FILES と同じ書き方の相対パス。

    dist/ や missions/ を巻き込まないよう、直下は拡張子で絞り、あとは public/ の下だけを
    たどる（本体はこの2か所にしか無い、という前提そのものを検査で守っている）。
    """
    found: list[str] = []

    for entry in sorted(HERE.iterdir(), key=lambda p: p.name.lower()):
        if not entry.is_file():
            continue
        if entry.name in SCAN_NAMES or entry.suffix in SCAN_SUFFIXES:
            found.append(entry.name)

    for name in SCAN_DIRS:
        base = HERE / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*"), key=lambda p: str(p).lower()):
            if path.is_file():
                found.append(path.relative_to(HERE).as_posix())

    return found


def check_payload_coverage() -> None:
    """PAYLOAD_FILES にも PAYLOAD_SKIP にも載っていないものがあれば中止する。

    「知らないファイルがあったら止まる」であって「知っているファイルが揃っているか」
    ではない。揃っているかどうかは build() が実際に開く時点で必ず分かる。
    """
    known = set(PAYLOAD_FILES) | PAYLOAD_SKIP
    unknown = [rel for rel in scan_payload_candidates() if rel not in known]
    if not unknown:
        return
    raise BuildError(
        "同梱するかどうかが決まっていないファイルがあります:\n"
        + "".join(f"    {rel}\n" for rel in unknown)
        + "  build_vsix.py の PAYLOAD_FILES（配る）か PAYLOAD_SKIP（配らない）の\n"
        "  どちらかに追記してください。列挙し忘れたまま配らないための検査です。"
    )


def check_wiring_first() -> None:
    """画面の配線（HTML の id と JS が引くセレクタ）を検める。**build の一番最初に呼ぶ。**

    Subagent Dashboard は開いたまま放置するページで、自分をリロードしない。HTML の id を書き換えても
    走っている旧スクリプトは動き続けるので、破綻は次に新規ロードした瞬間まで表に出ない
    ＝改名した本人の画面では最後まで正常に見える。人が気をつけて防げる種類の間違いでは
    ないので、食い違ったまま .vsix を作れないようにしてある。

    落ちたときは古い .vsix を消す前に止まる（手元に何も残らない状態を作らない）ので、
    ここは build() のどの破壊的な処理よりも前に置くこと。

    道具そのものが見つからないときは、止めずに警告して進む。検査は配線の見張りであって
    ビルドの必須部品ではないし、ここで止めると check_wiring.py を消しただけで
    .vsix が一切作れなくなる。
    """
    try:
        import check_wiring  # type: ignore
    except ImportError:
        print("  ⚠ check_wiring.py が見つかりません。配線の検査を飛ばします。",
              file=sys.stderr)
        return

    # **引数は必ず明示的に空で渡す。** check_wiring.main() は既定で sys.argv[1:] を読むが、
    # そこには build_vsix 側のサブコマンド（"build" など）が入っている。渡し忘れると
    # 「build という名前の HTML を検める」ことになって、必ず読み込みに失敗する。
    try:
        result = check_wiring.main([])
    except TypeError:
        result = check_wiring.main()

    # 戻り値の流儀を決め打ちにしない。終了コード（0 が合格）でも真偽でも、
    # 何も返さない（＝例外を投げなければ合格）でも受ける。
    if result is None:
        ok = True
    elif isinstance(result, bool):
        ok = result
    else:
        ok = result == 0

    if ok:
        print("  ✓ 画面の配線     OK")
        return
    raise BuildError(
        "画面の配線の検査（check_wiring.py）が通りませんでした。\n"
        "  食い違ったまま .vsix は作れません。dist/ の中身には触っていません。"
    )


# ---------------------------------------------------------------- 生成物


def write_version_file(version: str) -> Path | bytes:
    """VERSION をリポジトリ直下に置いて、そのパスを返す。

    中身は package.json の version 1行。**改行は CRLF。** この1行は Windows の
    メモ帳で開かれることがあり、LF だけだと1行に潰れて読めない
    （dashlib.tool_version() は strip() するのでどちらでも動く）。

    .vsix へは「作った文字列」ではなくこのファイルを入れる。dashlib.tool_version() が
    TOOL_ROOT/VERSION を読むので、開発ディレクトリと配布物で同じ1ファイルを見ることに
    なり、片方だけ古い版を名乗る状態が作れない。

    **中身が変わらないときは書かない。** 同じ内容で書き直すと更新時刻だけが動いて、
    差分を見る側に嘘の変更が見える。

    書けなかったときは、その場で作った中身を返す（.vsix は作れる）。止めるほどの
    ことではないが、リポジトリ側の版表示は古いままになるので警告は出す。
    """
    data = (version + "\r\n").encode("utf-8")
    target = HERE / "VERSION"
    try:
        if not target.is_file() or target.read_bytes() != data:
            target.write_bytes(data)
        return target
    except OSError as e:
        print(f"  ⚠ {target} を更新できませんでした（{e}）", file=sys.stderr)
        return data


def build_manifest(pkg: dict) -> bytes:
    """extension.vsixmanifest を package.json から機械的に作る。

    手で書くと package.json との二重管理になり、版を上げたのに manifest が古いまま、
    という状態が黙って作れてしまう。出どころは package.json ひとつに絞る。
    """
    def attr(value: object) -> str:
        return escape(str(value), {'"': "&quot;"})

    engine = (pkg.get("engines") or {}).get("vscode", "")
    tags = ",".join(pkg.get("keywords") or [])
    categories = ",".join(pkg.get("categories") or [])
    icon = pkg.get("icon", "")

    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="{attr(pkg.get('name', ''))}" Version="{attr(pkg.get('version', ''))}" Publisher="{attr(pkg.get('publisher', ''))}" />
    <DisplayName>{escape(str(pkg.get('displayName', '')))}</DisplayName>
    <Description xml:space="preserve">{escape(str(pkg.get('description', '')))}</Description>
    <Tags>{escape(tags)}</Tags>
    <Categories>{escape(categories)}</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Icon>extension/{attr(icon)}</Icon>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="{attr(engine)}" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value="" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="ui,workspace" />
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value="" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Content.Changelog" Path="extension/CHANGELOG.md" Addressable="true" />
    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/media/icon.png" Addressable="true" />
  </Assets>
</PackageManifest>
"""
    return xml.encode("utf-8")


def build_content_types(names: list[str]) -> bytes:
    """[Content_Types].xml を、実際に入れるものの一覧から作る。

    決め打ちで書くと、拡張子が1つ増えたときに黙って展開できない .vsix ができる。
    知らない拡張子が出てきたらここで止める（CONTENT_TYPES に足させる）。
    """
    exts: list[str] = []
    overrides: list[str] = []
    for name in names:
        ext = name.rsplit("/", 1)[-1].rsplit(".", 1)
        if len(ext) == 2 and ext[1]:
            if ext[1] not in CONTENT_TYPES:
                raise BuildError(
                    f"{name} の拡張子（.{ext[1]}）が CONTENT_TYPES にありません。\n"
                    "  載っていない拡張子があると VSCode は .vsix を展開できません。"
                )
            if ext[1] not in exts:
                exts.append(ext[1])
        else:
            # 拡張子を持たないものは Default で書けないので、1件ずつ Override する
            overrides.append(name)

    lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
    ]
    for ext in sorted(exts):
        lines.append(f'  <Default Extension="{ext}" ContentType="{CONTENT_TYPES[ext]}" />')
    for name in overrides:
        lines.append(f'  <Override PartName="/{name}" ContentType="{DEFAULT_CONTENT_TYPE}" />')
    lines.append("</Types>")
    return ("\n".join(lines) + "\n").encode("utf-8")


# ---------------------------------------------------------------- 入れるものを並べる


def iter_extension_files() -> list[tuple[str, Path]]:
    """extension/ の中身を「名前順・ディレクトリに当たったら即そこへ降りる」順で並べる。

    Windows のエクスプローラや dir と同じたどり方（大文字小文字は区別しない）。
    zip の中身の並びをこの規則ひとつで決めておけば、同じソースからは必ず同じ並びの
    .vsix ができる＝作り直したものを前回のものと差分で比べられる。
    """
    out: list[tuple[str, Path]] = []

    def walk(base: Path, prefix: str) -> None:
        try:
            entries = sorted(base.iterdir(), key=lambda p: p.name.lower())
        except OSError as e:
            raise BuildError(f"{base} を読めません（{e}）") from e
        for entry in entries:
            if entry.name in EXT_SKIP or entry.name.startswith("."):
                continue
            rel = prefix + entry.name
            if entry.is_dir():
                walk(entry, rel + "/")
            else:
                out.append((f"extension/{rel}", entry))

    if not EXT_SRC.is_dir():
        raise BuildError(f"{EXT_SRC} がありません")
    walk(EXT_SRC, "")
    return out


def iter_payload_files(version_source: Path | bytes) -> list[tuple[str, Path | bytes]]:
    """extension/tool/ に入れる本体を PAYLOAD_FILES の順に並べる。"""
    out: list[tuple[str, Path | bytes]] = []
    missing: list[str] = []
    for rel in PAYLOAD_FILES:
        arcname = f"extension/tool/{rel}"
        if rel == "VERSION":
            # 生成物。write_version_file が置いたファイル（書けなければ中身そのもの）
            out.append((arcname, version_source))
            continue
        src = HERE / rel
        if not src.is_file():
            missing.append(rel)
            continue
        out.append((arcname, src))
    if missing:
        raise BuildError(
            "同梱するファイルが見つかりません:\n"
            + "".join(f"    {rel}\n" for rel in missing)
            + "  本体が欠けた .vsix は、初期設定のダイアログすら出ずに死にます。"
        )
    return out


# ---------------------------------------------------------------- build


def build() -> Path:
    """.vsix を dist/ に作って、そのパスを返す。

    順番に意味がある:
      1. 配線の検査（落ちたら、古い .vsix を消す前に止まる）
      2. 同梱漏れの検査（同上）
      3. VERSION の生成
      4. 古い生成物を片付けてから zip を書く
    3 まで通ってから初めて dist/ に手を付ける。手元に何も残らない状態は作らない。
    """
    print()
    print("  VSCode 拡張を組み立てます")
    print("  ------------------------------------------------")

    check_wiring_first()

    check_payload_coverage()
    print(f"  ✓ 同梱漏れ検査   OK（本体 {len(PAYLOAD_FILES)} ファイル）")

    pkg = read_package_json()
    version = str(pkg.get("version", ""))
    if not version:
        raise BuildError("extension/package.json に version がありません")
    version_source = write_version_file(version)

    entries: list[tuple[str, Path | bytes]] = []
    entries.extend(iter_extension_files())
    entries.extend(iter_payload_files(version_source))

    manifest = build_manifest(pkg)
    # 型の表には extension.vsixmanifest も要る（.vsixmanifest という拡張子で入るため）。
    # 表そのもの（[Content_Types].xml）は載せない。中身ではなく目録の側なので、
    # 自分を自分で説明する必要がない。
    content_types = build_content_types(
        ["extension.vsixmanifest"] + [name for name, _ in entries]
    )

    DIST.mkdir(parents=True, exist_ok=True)
    target = DIST / vsix_name(pkg)

    # 前回の .vsix を先に消す。残したまま同じ名前へ書くと、書き込みに失敗したときに
    # 「古いものが新しい名前で置いてある」という一番たちの悪い状態になる。
    if target.exists():
        target.unlink()

    # `ext build` は .vsix しか作り直さない。dist/ に前回の手順書が残っていると
    # 「新しい .vsix と古い説明」が並ぶので、消して知らせる（黙って残さない）。
    stale_guide = DIST / GUIDE_HTML
    if stale_guide.exists():
        try:
            stale_guide.unlink()
            print(f"  ⚠ 古い手順書を消しました: {stale_guide.name}")
            print("     手順書を作るのは package のほうです。要るなら ext package を実行してください。")
        except OSError as e:
            print(f"  ⚠ 古い手順書を消せませんでした（{e}）: {stale_guide}", file=sys.stderr)

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        # この2つは .vsix の目次。必ず先頭に置く
        zf.writestr("extension.vsixmanifest", manifest)
        zf.writestr("[Content_Types].xml", content_types)
        for arcname, source in entries:
            if isinstance(source, bytes):
                zf.writestr(arcname, source)
            else:
                zf.write(source, arcname)

    size = target.stat().st_size
    print(f"  ✓ 出来ました     {target}")
    print(f"     版 {version} / {len(entries) + 2} エントリ / {size:,} バイト")
    print()
    return target


# ---------------------------------------------------------------- VSCode の code コマンド


def find_code() -> str | None:
    """VSCode の code コマンドを探す。見つからなければ None。

    探す場所は「古い版を抜く.bat」と揃えてある。片方だけ見つかる状況を作ると、
    .bat では抜けたのに ext status では「code が無い」と出る、という食い違いになる。
    """
    found = shutil.which("code")
    if found:
        return found

    candidates: list[Path] = []
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        program_files = os.environ.get("ProgramFiles")
        if local:
            candidates.append(Path(local) / "Programs" / "Microsoft VS Code" / "bin" / "code.cmd")
        if program_files:
            candidates.append(Path(program_files) / "Microsoft VS Code" / "bin" / "code.cmd")
    elif sys.platform == "darwin":
        candidates.append(
            Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")
        )
    else:
        candidates.append(Path("/usr/bin/code"))
        candidates.append(Path("/usr/local/bin/code"))
        candidates.append(Path("/snap/bin/code"))

    for path in candidates:
        if path.is_file():
            return str(path)
    return None


def require_code() -> str:
    code = find_code()
    if code:
        return code
    raise BuildError(
        "VSCode の code コマンドが見つかりませんでした。\n"
        "  VSCode を開き、Ctrl+Shift+P →「Shell Command: Install 'code' command in PATH」\n"
        "  を実行してから、もう一度お試しください。\n"
        "  （.vsix は出来ています。拡張機能パネルの「…」→「VSIX からのインストール」でも入ります）"
    )


def run_code(code: str, args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            [code, *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=180,
        )
    except OSError as e:
        raise BuildError(f"code コマンドを実行できません（{e}）: {code}") from e
    except subprocess.SubprocessError as e:
        raise BuildError(f"code コマンドが応答しません（{e}）") from e


def list_extensions(code: str) -> list[str]:
    r = run_code(code, ["--list-extensions"])
    if r.returncode != 0:
        raise BuildError(f"拡張機能の一覧を取れませんでした（{r.stderr.strip()}）")
    return [line.strip() for line in r.stdout.splitlines() if line.strip()]


def report_legacy(installed: list[str]) -> None:
    """古い ID が残っていたら、抜き方を出す。

    残っていても新しいほうは動く。だから黙っていると気づけない（アイコンもサーバーも
    2つ並ぶ）。止めはしないが、必ず目に入るところに出す。
    """
    lower = {name.lower() for name in installed}
    stale = [old for old in LEGACY_EXT_IDS if old.lower() in lower]
    if not stale:
        return
    print()
    print("  ⚠ 古い版が残っています。抜いてください（2つ並んで動きます）:")
    for old in stale:
        print(f"      code --uninstall-extension {old}")
    print(f"    dist/{CLEANUP_BAT}（ext package で作れます）をダブルクリックしても抜けます。")


# ---------------------------------------------------------------- install / uninstall / status


def install() -> int:
    """組み立てて VSCode に入れる。"""
    target = build()
    code = require_code()

    print(f"  VSCode        {code}")
    r = run_code(code, ["--install-extension", str(target), "--force"])
    if r.stdout.strip():
        for line in r.stdout.strip().splitlines():
            print(f"    {line}")
    if r.returncode != 0:
        print(f"  ✗ 入れられませんでした（{r.stderr.strip()}）", file=sys.stderr)
        return 1

    pkg = read_package_json()
    print(f"  ✓ 入りました     {ext_id(pkg)} 版 {pkg.get('version', '')}")
    try:
        report_legacy(list_extensions(code))
    except BuildError as e:
        print(f"  ⚠ 古い版の確認ができませんでした（{e}）", file=sys.stderr)

    print()
    print("  VSCode を開いているときは再読み込みしてください（Ctrl+Shift+P → Reload Window）。")
    print("  左端のロボットのアイコン、または Ctrl+Shift+D で開きます。")
    print()
    return 0


def uninstall() -> int:
    code = require_code()
    pkg = read_package_json()
    ident = ext_id(pkg)

    installed = list_extensions(code)
    if ident not in installed:
        print(f"  入っていません: {ident}")
        report_legacy(installed)
        return 0

    r = run_code(code, ["--uninstall-extension", ident])
    if r.returncode != 0:
        print(f"  ✗ 抜けませんでした（{r.stderr.strip()}）", file=sys.stderr)
        return 1
    print(f"  ✓ 抜きました     {ident}")
    print("  作業の記録（missions/）には触っていません。")
    return 0


def status() -> int:
    pkg = read_package_json()
    ident = ext_id(pkg)

    code = find_code()
    print()
    print("  VSCode 拡張の状態")
    print("  ------------------------------------------------")
    print(f"  拡張 ID       {ident}")
    print(f"  ソースの版    {pkg.get('version', '')}")

    target = DIST / vsix_name(pkg)
    if target.is_file():
        print(f"  組み立て済み  {target}（{target.stat().st_size:,} バイト）")
    else:
        print(f"  組み立て済み  まだありません（{dashlib.PY_CMD} {Path(__file__).name} build）")

    if not code:
        print("  VSCode        code コマンドが見つかりません（入っているかは確認できません）")
        print()
        return 1

    print(f"  VSCode        {code}")
    installed = list_extensions(code)
    if ident in installed:
        print(f"  ✓ 入っています: {ident}")
    else:
        print(f"  ✗ 入っていません: {ident}")
        print(f"     {dashlib.PY_CMD} {Path(__file__).name} install で入れられます")
    report_legacy(installed)
    print()
    return 0


# ---------------------------------------------------------------- package


def write_cleanup_bat(dest: Path) -> Path:
    """「古い版を抜く.bat」を書き出す。**CP932・CRLF で書く。**

    LF だけの .bat は cmd.exe が `for` を読み違えて落ちる
    （`for /f ... in ('chcp')` が「認識されていません」になる）。
    文字コードも同じ理由で CP932。UTF-8 のまま置くと案内文が化ける。
    """
    text = CLEANUP_TEMPLATE.format(old_ids=" ".join(LEGACY_EXT_IDS))
    crlf = text.replace("\r\n", "\n").replace("\n", "\r\n")
    path = dest / CLEANUP_BAT
    path.write_bytes(crlf.encode("cp932"))
    return path


def package() -> int:
    """配布物一式を dist/ に作る（.vsix と「古い版を抜く.bat」）。"""
    target = build()
    bat = write_cleanup_bat(DIST)

    print("  配布物（dist/）")
    print("  ------------------------------------------------")
    print(f"    {target.name}")
    print(f"    {bat.name}")
    print()
    print("  相手にはこの2つを渡してください。")
    print("  .bat は 0.4.2 以前から上げる人だけが使います（入っていなければ何もしません）。")
    print()
    return 0


# ---------------------------------------------------------------- CLI

USAGE = """
VSCode 拡張機能の組み立て（Subagent Dashboard）

  dash ext build             .vsix を作るだけ（dist/ に出る）
  dash ext install           拡張機能を組み立てて VSCode に入れる
  dash ext package           配布物一式を作る（.vsix と「古い版を抜く.bat」）
  dash ext status            入っているか確認する
  dash ext uninstall         拡張機能を抜く

  直接呼ぶときは  python build_vsix.py <サブコマンド>  でも同じです。
""".strip()

HELP = {"-h", "--help", "help", ""}


def main() -> None:
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""

    if cmd in HELP:
        print(USAGE)
        return

    actions = {
        "build": lambda: (build(), 0)[1],
        "install": install,
        "package": package,
        "status": status,
        "uninstall": uninstall,
    }
    action = actions.get(cmd)
    if action is None:
        print(f"知らないサブコマンドです: {cmd}", file=sys.stderr)
        print(file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(2)

    try:
        sys.exit(action())
    except BuildError as e:
        print()
        print(f"  ✗ {e}", file=sys.stderr)
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
