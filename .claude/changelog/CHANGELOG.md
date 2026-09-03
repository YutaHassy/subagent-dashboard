# Changelog

Claude Code の変更履歴の自動記録（`changelog_cli.py summarize` により生成。手で編集しても次の summarize で上書きされる）。

## 2026-09-03 14:10:45 — 系統樹の下に「置き場所が決まらない機体」の区画を新設し、そこへ至る途中で見つけた改行コードの破壊と孤児判定の2つの穴を直した

■ まず git（ユーザー指示「今時点でのものを一度git系に上げておき」）

作業前に git status を見たところ、public/index.html の diff が 9,775 行という異常な大きさだった。
調べると、0.8.0 の作業で使った patch スクリプトが io.open(p,'w') で書き戻していて、Windows の
既定の改行変換により **9ファイルが丸ごと LF → CRLF になっていた**（build_vsix.py / changelog_setup.py /
check_livefeed.py / dashlib.py / i18n_data_install.py / i18n_data_update.py / install.py / livefeed.py /
update_state.py）。作業ツリーでは public/index.html と public/i18n.js も同じ状態だった。

.gitattributes は `* -text`（Git に一切変換させない）、RESTORE_NOTES.md は「編集するときも改行コードを
揃えないでください」と明記している。壊れるのは (a) diff がファイル全体になり何を変えたか読めない、
(b) build_vsix.py が組む .vsix のバイトが変わる（原本との照合が前提のリポジトリ）。

fix_eol.py で 13 ファイルを LF に戻し、中身が改行以外に変わっていないことを git show と突き合わせて
確認（意図した5ファイル以外はすべて「改行を除いて HEAD と同一: はい」）。履歴は書き換えず、
2コミットに分けて feature/wiring-under へ push（gitlab / origin 両方）:
  22e185f 改行コードを LF に戻す（0.8.0 で私が CRLF にしていた）
  c258ac5 起動元が実測で分かった孤児を系統樹の中に置く

以降の編集はすべて io.open(..., newline='') で書き、LF が保たれていることを都度確認した。

■ 下部区画（ユーザー指示「実装はチーム体制で行ってください」）

Explore を3体並列で走らせて下調べ（DOM/CSS の骨組み・カード生成の JS 配線・多言語の作法）、
実装後にレビュー1体。判断と編集はすべて自分で行った。

public/index.html:
- .team-body は row（木と右の側面パネルの横並び）なので、.tree-pane（縦の器）を1枚挟んだ。
  区画の幅は木の幅に収める（側面パネルをよける／変更を小さくする）
- .orphan-bay を新設。見出し（件数入り）＋開閉ボタン＋注記＋本体。本体は flex-wrap で
  ロボを上・カードを下に積んだ単位を並べる
- createAgent から buildAgentDom() を切り出した。区画のカードは t.cards に登録せず
  t.orphanCards に持つ（登録すると render の刈り取りで毎回消え、drawLinks の cardRects に
  混ざって系統樹の線の経路まで曲がる）
- paintOrphans（文字の行）を paintOrphanBay（カード）に置き換え。呼び出しは updateClocks 経由の
  まま（stateSig に毎秒変わる値が入っていないため render は走らない）
- 畳み方は #app.bay-collapsed で max-height:0 + opacity:0。display:none を使わないのは
  ロボのアニメーションが巻き戻るため（.agent のコメントに既存の注記あり）
- resetView に t.orphanCards の片付けを追加
- updateAgentClock: 記録に無い機体は開始時刻を名乗れないので、実測ログの幅（live.elapsedSec）を
  出す。記録から出せるときは上書きしない
- 右の側面パネルにあった .live-orphans は削除

public/i18n.js: live.bay_title / live.bay_note / live.bay_show / live.bay_hide を4言語ぶん追加、
使われなくなった live.orphans_title を4言語から削除。

■ 途中で見つかった2つの穴（どちらも実物で踏んだ）

(1) livefeed.assign_live の入口に `if not running: return []` があり、**記録された稼働中の機体が
    1体も無いと孤児も空**になっていた。add を全部打ち忘れた／hook が発火しなかった場面＝この
    一覧がいちばん要る場面でだけ何も出ない。実測: hook が発火しないまま3体を起動したミッションで
    孤児0件。early return を外した（以降の対応づけの輪は running を回すだけなので、空なら
    候補は全員そのまま孤児として流れる）。検査 [30] を新設。

(2) 完了の合図でカードから live は外れるが実機のログは残るため、**系統樹に完了として並んでいる
    機体が下部区画にもう一度出た**（実測: 調査を終えた3体）。走っている記録の対応づけが全部
    終わったあとに、終わった記録にも実機を割り当てる輪を足した（live は載せない。孤児から外す
    ことと、その機体を親に持つ孫の置き場所が決まることが目的）。名前で結ぶほうは compatible() を
    通さず双方向の一意を求める——打ち忘れに気づいてあとから add する場面で開始時刻がずれるため。
    検査 [31] を新設（横取りしないこと／終わった記録に実測を載せないこと／名前が重なったら
    どちらにも結ばないことを含む）。

(1) は直す前のコードで検査が実際に落ちることを確認済み。

■ 確認したこと

- check_livefeed.py 全31節が通る。check_autoreg.py も通る
- 隔離したダミー（ポート3964）で: 起動元が実測で分かった機体は系統樹の第2世代、分からない3体が
  区画にロボ＋カードで並ぶ。機体数は 0/2 のまま（区画のカードは数えない）、線3本、
  コンソールエラーなし
- 開閉が両方向に動き、閉じても見出しは残る。max-height 483px ↔ 0px
- 4言語すべてで見出し・注記・ボタン・カードが入れ替わり、件数が保たれる
- 実物（ポート3961）で: 4体が系統樹に並び、区画は空で hidden

■ ダッシュボード

このプロジェクトの CLAUDE.md は「add と done を自分で打つな、hook が書く」と決めているが、
hook は Claude Code の起動時にしか読み込まれず、前のセッションで入れたものはこのセッションでは
効かない（0.8.0 で判明済みの制約）。結果、4体とも記録ゼロで画面に出なかった。ユーザーの指摘を受け、
重複が起きえないことを確認したうえで手で add / done を入れた（完了3体の所要・トークン・ツール回数は
完了通知の実測値。model は実機に入っていなかったので推測せず省略）。

■ 残っていること

- 今回ぶん（下部区画＋穴2つ）はまだコミットしていない。レビュー1体の結果待ち
- 版は 0.8.0 のまま

- セッション: `82c684a9-727d-4a7e-a09b-daf186db21cd`

---
