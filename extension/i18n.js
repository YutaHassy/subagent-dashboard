/**
 * i18n.js — VSCode 拡張の言語切り替え
 *
 * 英語を原文とし、日本語・中国語（簡体）・韓国語を載せる。設計は画面側
 * （public/i18n.js）と Python 側（i18n.py）から引き継いでいる:
 *
 *   - **鍵は英語の原文そのもの。** 別名の鍵を発明しない。t("View log")
 *     と書いてあれば、翻訳表を開かなくても何が出るか読める。
 *   - **訳が無ければ原文を返す。** 翻訳の抜けで例外にしない。1つ訳し忘れただけで
 *     拡張が起動しなくなるのは、このツールの方針（黙って壊れない）に反する。
 *   - `{name}` の差し込みは params から。**差し込み先が無い `{...}` はそのまま残す。**
 *     空文字に潰すと「文が欠けている」という読める壊れ方にならない。
 *
 * 言語は vscode.env.language から決める。VSCode が返すのは 'en' / 'ja' /
 * 'zh-cn' / 'zh-tw' / 'ko' などなので、4つ（en|ja|zh|ko）へ寄せる。
 *
 * **'vscode' を require できなくても落ちない。** node 単体で読み込んで確かめたい
 * ときのため（その場合は 'en'）。翻訳表（i18n_data.js）が読めなかったときも同じで、
 * 英語のまま進む。
 *
 *   const { t } = require('./i18n');
 *   t('Subagent Dashboard')
 *   t('Port {port} is free. Starting the server there.', { port: 3939 })
 */

'use strict';

const SUPPORTED = ['en', 'ja', 'zh', 'ko'];

/** 翻訳表。読めなくても英語で動く（ここで throw させない）。 */
let CATALOG = {};
try {
  const data = require('./i18n_data');
  if (data && typeof data === 'object') CATALOG = data;
} catch (e) {
  CATALOG = {};
}

/**
 * 'ja-JP' や 'zh-Hant-TW' のようなタグを、対応している4つのどれかに寄せる。
 * 対応外なら null（呼び手が既定へ落とす）。
 *
 * 繁体字（zh-tw / zh-hant）も簡体字の表へ寄せる。訳が無いよりは読めるほうが
 * よい、という既存の判断（public/i18n.js・i18n.py）に合わせている。
 */
function normalize(tag) {
  if (typeof tag !== 'string') return null;
  const low = tag.trim().toLowerCase().replace(/_/g, '-');
  if (!low) return null;
  if (low === 'en' || low.indexOf('en-') === 0) return 'en';
  if (low === 'ja' || low.indexOf('ja-') === 0) return 'ja';
  if (low === 'ko' || low.indexOf('ko-') === 0) return 'ko';
  if (low === 'zh' || low.indexOf('zh-') === 0) return 'zh';
  return null;
}

/**
 * VSCode の表示言語を読む。
 * require('vscode') に失敗する環境（node 単体での確認）でも落とさない。
 */
function detect() {
  try {
    // eslint-disable-next-line global-require
    const vscode = require('vscode');
    const tag = vscode && vscode.env ? vscode.env.language : null;
    return normalize(tag) || 'en';
  } catch (e) {
    return 'en';
  }
}

let current = detect();

function getLang() {
  return current;
}

/**
 * 言語を差し替える。対応外のタグは黙って無視する（いまの言語のまま）。
 * 拡張の本筋では使わない。動作確認から言語を切り替えるための口。
 */
function setLang(tag) {
  const hit = normalize(tag);
  if (hit) current = hit;
  return current;
}

/**
 * <html lang> に入れる値。zh は地域まで書かないとフォント選択が地域で割れる
 * （public/i18n.js の htmlLang() と同じ）。
 */
function htmlLang() {
  return current === 'zh' ? 'zh-Hans' : current;
}

/** {name} を params から埋める。無いものは**そのまま残す**。 */
function fill(text, params) {
  if (text.indexOf('{') < 0) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name) => {
    if (!params) return whole;
    const v = params[name];
    return (v === undefined || v === null) ? whole : String(v);
  });
}

/**
 * 原文（英語）を今の言語へ訳す。**訳が無ければ原文をそのまま返す。**
 *
 * @param {string} text 英語の原文。**必ず文字列リテラルで書くこと**
 *   （変数を渡すと、翻訳表との突き合わせが機械で検査できなくなる）
 * @param {Object} [params] {name} に差し込む値
 * @returns {string}
 */
function t(text, params) {
  const src = typeof text === 'string' ? text : String(text);
  let raw = src;
  if (current !== 'en') {
    const table = CATALOG[current];
    if (table && Object.prototype.hasOwnProperty.call(table, src)) {
      const hit = table[src];
      if (typeof hit === 'string') raw = hit;
    }
  }
  return fill(raw, params);
}

/** その原文の訳を持っているか。翻訳の抜けを数える補助。 */
function has(text, lang) {
  const table = CATALOG[lang || current];
  return !!table && Object.prototype.hasOwnProperty.call(table, text);
}

module.exports = { t, getLang, setLang, normalize, htmlLang, has, langs: SUPPORTED.slice() };
