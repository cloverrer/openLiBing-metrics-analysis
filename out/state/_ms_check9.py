# -*- coding: utf-8 -*-
import json
from pathlib import Path
from collections import Counter

d = json.load(open(Path('out/work/step_2_dash_raw.json'), encoding='utf-8'))
v = d['MindStudio|msmemscope']
print('keys:', list(v.keys()))
recs = v.get('records')
print('records:', len(recs) if recs is not None else None)
if recs:
    print('sample keys:', list(recs[0].keys()))
    for r in recs[:5]:
        print(' rn=%s status=%s start=%s end=%s iva=%s cpr=%s' % (
            r.get('pipelineRunNumber'), r.get('pipelineRunStatus'),
            str(r.get('pipelineRunStartTime'))[:19], str(r.get('pipelineRunEndtime'))[:19],
            r.get('isVersionAvailable'), r.get('casePassRate')))
    ends = [str(r.get('pipelineRunEndtime'))[:10] for r in recs]
    print('end-date dist:', dict(Counter(ends)))
    starts = [str(r.get('pipelineRunStartTime'))[:10] for r in recs]
    print('start-date dist:', dict(Counter(starts)))
    other = {k: val for k, val in v.items() if k != 'records'}
    print('other:', json.dumps(other, ensure_ascii=False)[:400])
