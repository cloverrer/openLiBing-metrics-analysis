# -*- coding: utf-8 -*-
import json
from pathlib import Path

# 检查 step_1 的产品级数据：MindStudio 产品下有几条流水线、每条的 versionAvailabilityRate
f = Path('out/work/step_1_bad_pipelines.json')
d = json.load(open(f, encoding='utf-8'))
print('top keys:', list(d.keys())[:10])
print('products:', len(d.get('products') or d.get('pipelines') or []))

# pipelines 数组
for p in d.get('pipelines') or []:
    if p.get('product') == 'MindStudio':
        print('MS pipe:', p.get('key'), 'vaRate=', p.get('versionAvailabilityRate'), 'bsRate=', p.get('buildSuccessRate'), 'dims=', p.get('dims'))

# 产品级
for prod in d.get('products') or []:
    if isinstance(prod, dict) and prod.get('product') == 'MindStudio':
        print('product entry:', json.dumps({k: v for k, v in prod.items() if k != 'pipelines'}, ensure_ascii=False)[:600])
