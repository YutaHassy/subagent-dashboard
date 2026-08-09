# 復元記録

このリポジトリは、配布物 `agent-dashboard-0.4.3.vsix` **だけ**から復元したものです。
元のリポジトリはこのPC上のどこにも残っていませんでした。

**どのファイルが原本で、どのファイルが書き直したものかを、ここに正直に分けて書きます。**
このファイル自体は復元作業の産物で、元のリポジトリには存在しません。

---

## 1. 原本そのまま（23ファイル）

`.vsix` に同梱されていたファイルです。**バイト単位で原本と一致**することを確認済み
（`.vsix` 内の各エントリと復元先ファイルの SHA-256 を突き合わせ、全件一致）。

配置は `README.md` と `OPERATION.md` のファイル構成図に従いました。
`.vsix` の中では `extension/tool/` に押し込まれていますが、そこはリポジトリ直下が原位置です。

| .vsix 内のパス | 復元先 |
| --- | --- |
| `extension/tool/dash.py` ほか本体13点 | リポジトリ直下 |
| `extension/tool/public/*.html` | `public/` |
| `extension/package.json` `extension.js` `README.md` `CHANGELOG.md` `media/*` | `extension/` |

改行コードが混在しています（`OPERATION.md` と `public/*.html` だけ CRLF、他は LF。
`VERSION` は `0.4.3\r\n` の7バイト）。**テキストとして読み書きすると壊れる**ので、
バイト列のまま書き戻しています。編集するときも改行コードを揃えないでください。

`.vsix` の梱包材（`extension.vsixmanifest` と `[Content_Types].xml`）は
ビルド時の生成物なので、ソースとしては復元していません（`build_vsix.py` が作ります）。

---

## 2. 書き直したファイル（原本ではない）

`.vsix` に同梱されない決まりだった開発用ファイルのうち、
**残っているコードと `extension/CHANGELOG.md` の記述から仕様が確定できるもの**を書き直しました。
文体は寄せてありますが、**原本の写しではありません。**

### `build_vsix.py` — 検証で裏が取れています

`dash ext build|install|package|status|uninstall` の実体。

**`python build_vsix.py build` が生成する `.vsix` は、原本 `agent-dashboard-0.4.3.vsix` と
バイト単位で一致します。** zip エントリ25件の順序・各エントリの中身・圧縮後サイズ・
`external_attr`、そしてファイル全体サイズ 222,402 バイトまで同じで、差はタイムスタンプだけです。
`ext package` が出す `古い版を抜く.bat` も 2,435 バイトで一致（CP932 / CRLF）。

> **この一致は 0.4.3 時点の話です。** 0.5.0 で製品名を `Subagent Dashboard` に統一し、
> `.bat` の案内文（拡張機能パネルでの検索語）を書き換えたため、いま生成すると
> 2,584 バイトになります。リポジトリ直下に残してある `古い版を抜く.bat`（2,435 バイト）は
> **0.4.3 の原本**で、上の照合の証拠として置いてあるものです。生成物と一致しなくなったのは
> 想定どおりで、消さないでください。生成物は `dist/` のほうです。

つまり**このファイルは「原本と同じものを作る」ことが証明できている**再構築物です。
ただし一致するのは*出力*であって、*ソースが原本と同じ*という意味ではありません。

- 原本から確定できたもの: `PAYLOAD_FILES` の14点とその順序、`extension/` 側の並び、
  `extension.vsixmanifest` と `[Content_Types].xml` の全文、`VERSION` の中身と生成方法、
  `CLEANUP_TEMPLATE` の全文、`LEGACY_EXT_IDS`、生成物は `writestr` で同梱物は `write`
  という使い分け（`external_attr` から判別できた）。
- 推測で埋めたもの: `PAYLOAD_SKIP` と `EXT_SKIP` の正確な中身、同梱漏れ検査の走査範囲、
  `install` / `status` などの画面の文面。

### `check_wiring.py` — 検証済み

`public/index.html` の `need()` が引いているセレクタが、同じ HTML の markup
（`<script>` の外）に実在するかを検める道具。`build_vsix.build()` が最初に呼びます。

- 現行の `index.html` に対して `need()` 24件（うち親を指定したもの9件）を全件確認。
  `CHANGELOG.md` の「23個」は 0.3.1 時点の数で、0.4.0 の `#zoom-auto` で1件増えています。
- 変異試験8通りで見張りが噛むことを確認（HTML だけ改名／JS だけ旧名へ／入れ子の class 名ずれ／
  `<script>` 内の文字列にしか無い名前／`<template>` 内の改名 などで鳴り、健全な複製では鳴らない）。
- 推測で埋めたもの: 出力の文面、`main(argv)` という API の形、対応する CSS セレクタの範囲
  （`#id` `.class` タグ 子孫 `>` のみ。読めないセレクタは合格にせず落とす方針）。

### `auto_setup.py` — 検証済み

`server.py` と `update_state.py` が `try: import` している「あれば初回だけ初期設定を促す」層。
判定そのものは `dashlib` 側にあるので、こちらは薄い呼び出しに徹しています。

- 呼び出し側が残っているので `check_and_setup(silent: bool = False) -> bool` という
  契約は確定。`silent=True` は無音、例外は外に出さない、版のずれは扱わない（そちらは
  `server.py` と `update_state.py` が `dashlib` を直接見ている）。
- 推測で埋めたもの: 文面と確認の形。
- **未解決**: `update_state.py` の呼び出し側コメントと `README.md` は「非対話環境では警告を
  表示して続行」と読めます。原本の `silent=True` は一行の警告を出していたかもしれません。
  今は無音にしてあります。

### `.gitignore` / `RESTORE_NOTES.md`

どちらも元のリポジトリには存在しません。今回足したものです。

---

## 3. 復元できていないファイル

参照だけが残っていて、中身を確定する手がかりが足りないものです。
`dash.py` や文書がこれらを指しているので、**呼ぶと落ちる／案内が実行不能**になります。

| ファイル | 参照元 | 分かっていること |
| --- | --- | --- |
| `package_dist.py` | `dash.py:113` | `dash package` の実体。「配布用パッケージ一式（ZIP + VSIX + 手順書）」を作る。配布ルートにある `セットアップ手順.html` はこれの生成物と思われる |
| `EXTENSION_PLAN.md` | `extension.js:5`, `extension.js:886`, `README.md:255`, `OPERATION.md:108` | 拡張の設計文書。`node_modules` を使わない理由（3章）と、ポートの決定権を拡張側に残す設計（5.3章）の出典 |
| `test_tabs.py` | `OPERATION.md:571` | タブ一覧の動作確認。一時ディレクトリを使い記録に触らない |
| `test_upgrade.py` | `CHANGELOG.md:139` | `CLAUDE.md` の版マーカーの読み書きと古い版判定の確認 |
| `test_parallel.py` | `CHANGELOG.md:101` | 押し出しの検知と `--project` 分離の確認 |
| `extension/test_extension.js` | `README.md:412`, `OPERATION.md:578` | `node` だけで走る拡張の試験。`extension.js` 末尾が公開している `__test` を突く |
| `extension/media/make_icons.py` | `OPERATION.md:638` | アイコン画像の生成。**このプロジェクト唯一の外部依存（Pillow）**で、絵を描き直すときだけ必要 |

`extension.js:2044-2060` が `__test` として何を公開しているかは残っているので、
`test_extension.js` は書き直せる余地があります（今回は手を付けていません）。

**`dash package` は動きません**（`package_dist.py` が無いため）。`dash ext package` は動きますが、
手順書 HTML は作らず `.vsix` と `古い版を抜く.bat` だけを出します。`dash.py` の USAGE は
`ext package` も手順書を作ると読めるので、ここは原本と食い違っている可能性があります。

---

## 4. 文書とコードの食い違い（復元前からあったもの）

復元の失敗ではなく、**原本の時点で残っていたずれ**です。直していません。

- `README.md:259` の「グローバルアクセス」は*拡張機能を入れない場合の導線*と説明していますが、
  `install.py:216` が `Ctrl+Shift+D` に割り当てるのは拡張が提供するコマンド
  `agentDashboard.open` です。拡張なしでは何も起きません（`install.py:861` 自身が
  「拡張機能を入れると効きます」と出しています）。
- `diagnose.py:268` が案内する `配布後のセットアップ手順.md` は存在しません。
  実際に配られているのは `セットアップ手順.html` です。
- `README.md` と `OPERATION.md` のファイル構成図は、`.vsix` に同梱されない開発用ファイルを
  実在物として載せています。配布物だけを受け取った人には実行できないコマンドの案内になります
  （`public/manual.html` の同じ図には最初から載っていないので、利用者向け文書は実態と一致）。

---

## 5. 元のリポジトリを取り戻す道

書き直したものより原本のほうが確実です。**先にこちらを試す価値があります。**

- このフォルダは OneDrive の中にあります。元のフォルダを消したのが最近なら、
  OneDrive の「ごみ箱」または「ファイルの復元（Files Restore）」から戻せる可能性があります。
- 原本が戻ったら、この復元版で上書きせず、**まず差分を取ってください。**
