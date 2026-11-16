# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_1_nightly_raw.json'), encoding='utf-8'))
v = d['details']['MindStudio']
data = v.get('data') or {}
print('data keys:', list(data.keys())[:15])
recs = data.get('records') or []
print('records:', len(recs))
for r in recs:
    print('  ', json.dumps({k: r.get(k) for k in ('pipelineName', 'versionAvail', 'versionAvailabilityRate', 'buildSuccess', 'pipelineId')}, ensure_ascii=False)[:220])
