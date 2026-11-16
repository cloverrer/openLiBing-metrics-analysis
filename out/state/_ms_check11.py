# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_2_dash_raw.json'), encoding='utf-8'))
print('pipelines:', len(d))
n_ok = n_err = 0
for key, v in d.items():
    if isinstance(v, dict) and 'code' in v:
        n_err += 1
        print('ERR', key, json.dumps(v, ensure_ascii=False)[:200])
    elif isinstance(v, dict):
        n_ok += 1
    else:
        print('??', key, type(v).__name__)
print('ok=%d err=%d' % (n_ok, n_err))
# 查看正常条目的结构样本
for key, v in d.items():
    if isinstance(v, dict) and 'code' not in v:
        print('sample ok:', key, list(v.keys()), 'records=', len(v.get('records') or []))
        recs = v.get('records') or []
        if recs:
            print('  rec keys:', list(recs[0].keys())[:15])
        break
