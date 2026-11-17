# -*- coding: utf-8 -*-
"""按文件名子串从归档内嵌证据取行窗口，便于逐条取证。
用法: python out/state/evwin.py <流水线evidence.json> <文件名子串> <起始行> <结束行>
"""
import json
import sys
import io

path, sub, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
d = json.load(io.open(path, encoding='utf-8'))
files = d.get('files') or {}
hits = [k for k in files if sub in k]
if not hits:
    print('NO MATCH for', sub)
    sys.exit(1)
for k in hits[:3]:
    lines = files[k].get('lines') or []
    print('== %s (total %d lines)' % (k, len(lines)))
    for i in range(a - 1, min(b, len(lines))):
        print('L%d: %s' % (i + 1, lines[i]))
