# -*- coding: utf-8 -*-
"""在归档内嵌证据里按正则 grep，回显命中行（带原始行号）。
用法: python out/state/evgrep.py <evidence.json> <文件名子串> <正则> [上下行数] [最多命中]
"""
import json
import re
import sys
import io

path, sub, pat = sys.argv[1], sys.argv[2], sys.argv[3]
ctx = int(sys.argv[4]) if len(sys.argv) > 4 else 0
cap = int(sys.argv[5]) if len(sys.argv) > 5 else 25
d = json.load(io.open(path, encoding='utf-8'))
files = d.get('files') or {}
rx = re.compile(pat)
for k in [k for k in files if sub in k][:2]:
    lines = files[k].get('lines') or []
    print('== %s (total %d)' % (k, len(lines)))
    n = 0
    shown = set()
    for i, ln in enumerate(lines):
        if rx.search(ln):
            for j in range(max(0, i - ctx), min(len(lines), i + ctx + 1)):
                if j in shown:
                    continue
                shown.add(j)
                print('L%d: %s' % (j + 1, lines[j][:400]))
            n += 1
            if n >= cap:
                break
    if n == 0:
        print('  (no match)')
