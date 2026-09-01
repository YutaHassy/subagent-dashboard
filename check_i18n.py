# -*- coding: utf-8 -*-
"""翻訳表の抜け・余り・差し込み名のずれを機械的に検める（開発用。配布物には入らない）。

ソースの t("...") を全部集めて、各言語の表と突き合わせる。
原文を書き換えたのに表の鍵を直し忘れると、ここで「missing / unused」の対で出る。
"""
import ast
import io
import os
import re
import sys

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)

FILES = ['dashlib.py', 'server.py', 'update_state.py', 'install.py',
         'diagnose.py', 'auto_setup.py', 'open_dashboard.py', 'dash.py',
         'livefeed.py']

# 定数を経由して t() へ渡している原文（AST からは literal に見えない）
EXTRA = ['not created yet']


def const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        a, b = const_str(node.left), const_str(node.right)
        if a is not None and b is not None:
            return a + b
    return None


def collect(path):
    tree = ast.parse(io.open(path, encoding='utf-8').read())
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None)
        if name != 't' or not node.args:
            continue
        text = const_str(node.args[0])
        if text is not None:
            out.append(text)
    return out


def main():
    import i18n
    src = list(EXTRA)
    for f in FILES:
        p = os.path.join(PROJ, f)
        if not os.path.isfile(p):
            continue
        for s in collect(p):
            if s not in src:
                src.append(s)

    ph = lambda s: set(re.findall(r'\{(\w+)', s))
    bad = 0
    print('source strings passed through t(): %d' % len(src))
    for lang in ('ja', 'zh', 'ko'):
        table = i18n.CATALOG.get(lang, {})
        miss = [k for k in src if k not in table]
        unused = [k for k in table if k not in src]
        print('%s: %3d translated | %2d missing | %2d unused'
              % (lang, len(table), len(miss), len(unused)))
        for k in miss:
            print('    MISSING %r' % (k[:80],))
            bad += 1
        for k in unused:
            print('    UNUSED  %r' % (k[:80],))
            bad += 1
        for k, v in table.items():
            if ph(k) != ph(v):
                print('    PLACEHOLDER %r: %s vs %s' % (k[:60], sorted(ph(k)), sorted(ph(v))))
                bad += 1
    print('OK' if bad == 0 else '%d problem(s)' % bad)
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
