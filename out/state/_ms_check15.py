# -*- coding: utf-8 -*-
import json
from pathlib import Path

# step_1 产物：产品清单与看板值
d = json.load(open(Path('out/work/step_1_products.json'), encoding='utf-8'))
print('keys:', list(d.keys()))
for p in d.get('products') or []:
    if p.get('product') == 'MindStudio':
        print('MS product:', json.dumps(p, ensure_ascii=False)[:400])

# step_1 nightly 明细（每流水线看板值）
b = json.load(open(Path('out/work/step_1_bad_pipelines.json'), encoding='utf-8'))
print('notes:', json.dumps(b.get('notes'), ensure_ascii=False)[:500])
for p in b.get('pipelines') or []:
    if p.get('product') == 'MindStudio':
        print('  ', p.get('key'), 'va=', p.get('versionAvailabilityRate'), 'dims=', p.get('dims'), 'platform=', p.get('platform'))
