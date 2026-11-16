# -*- coding: utf-8 -*-
import json
from pathlib import Path

# 每个批次的失败分布
for i in (2, 3, 4):
    f = Path('out/work/step_2_dash_batch%d.json' % i)
    if not f.exists():
        continue
    d = json.load(open(f, encoding='utf-8'))
    ok = err = 0
    err_keys = []
    for k, v in (d.items() if isinstance(d, dict) else []):
        if isinstance(v, dict):
            if v.get('code') == 200:
                ok += 1
            else:
                err += 1
                err_keys.append(k)
    print('batch%d: ok=%d err=%d' % (i, ok, err))
    if err:
        print('   errs:', err_keys)
