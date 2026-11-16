# -*- coding: utf-8 -*-
import json
from pathlib import Path

# 检查 step_1 raw 中 MindStudio 的 nightly 明细是否有接口失败
for name in ('step_1_nightly_raw.json', 'step_1_ops_raw.json', 'step_1_nightly_detail.json'):
    f = Path('out/work') / name
    if not f.exists():
        print(name, ': missing')
        continue
    d = json.load(open(f, encoding='utf-8'))
    print('==', name, type(d).__name__)
    items = d if isinstance(d, list) else (d.get('products') or d.get('pipelines') or [])
    if isinstance(d, dict):
        print('  keys:', list(d.keys())[:10])
