# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_2_dash_raw.json'), encoding='utf-8'))
n_real_err = []
n_ok = 0
for key, v in d.items():
    if isinstance(v, dict):
        if v.get('code') == -1 or 'error' in v and v.get('code') != 200:
            n_real_err.append(key)
        elif v.get('code') == 200:
            n_ok += 1
print('code=200 ok:', n_ok)
print('code=-1 REAL ERR:', len(n_real_err))
for k in n_real_err:
    print('  ', k, d[k].get('error'))
