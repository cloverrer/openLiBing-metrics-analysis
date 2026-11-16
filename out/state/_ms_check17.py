# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_1_nightly_raw.json'), encoding='utf-8'))
print('failures:', json.dumps(d.get('failures'), ensure_ascii=False)[:500])
print('retryInfo:', json.dumps(d.get('retryInfo'), ensure_ascii=False)[:500])
print('maxTry:', d.get('maxTry'))
ms = [t for t in d.get('details') or [] if isinstance(t, dict) and 'MindStudio' in str(t.get('product'))]
print('MS details:', len(ms))
for t in ms[:2]:
    print(json.dumps({k: t.get(k) for k in ('product', 'nightlyVersionAvailabilityRate', 'nightlyBuildSuccessRate', 'code')}, ensure_ascii=False)[:300])
    pipes = t.get('pipelines') or t.get('records') or []
    print('  pipes:', len(pipes))
