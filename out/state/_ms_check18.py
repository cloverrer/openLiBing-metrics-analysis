# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_1_nightly_raw.json'), encoding='utf-8'))
det = d.get('details')
print('details type:', type(det).__name__)
if isinstance(det, dict):
    for k, v in det.items():
        if 'MindStudio' in k:
            print('key:', k, 'sub keys:', list(v.keys())[:12] if isinstance(v, dict) else type(v).__name__)
            print(json.dumps({kk: vv for kk, vv in v.items() if not isinstance(vv, (list, dict))}, ensure_ascii=False)[:400])
            recs = v.get('records') or v.get('pipelines') or []
            print('  records:', len(recs))
            for r in recs[:8]:
                if isinstance(r, dict):
                    print('   ', r.get('pipelineName') or r.get('pipeline'), 'va=', r.get('versionAvail') or r.get('nightlyVersionAvailabilityRate'))
