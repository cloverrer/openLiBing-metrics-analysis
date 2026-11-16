# -*- coding: utf-8 -*-
import json
from pathlib import Path

for i in (2, 3, 4):
    f = Path('out/work/step_2_dash_batch%d.json' % i)
    d = json.load(open(f, encoding='utf-8'))
    print('== batch', i, 'keys:', list(d.keys()))
    dash = d.get('dash') or {}
    print('  dash keys:', list(dash.keys())[:10])
    # 每条流水线的结果
    for k, v in (dash.items() if isinstance(dash, dict) else []):
        if isinstance(v, dict) and v.get('code') != 200:
            print('  ERR', k, str(v.get('error'))[:80])
    ok = sum(1 for v in (dash.values() if isinstance(dash, dict) else []) if isinstance(v, dict) and v.get('code') == 200)
    print('  ok:', ok)
