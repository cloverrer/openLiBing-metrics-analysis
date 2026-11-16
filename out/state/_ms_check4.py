# -*- coding: utf-8 -*-
import json
from pathlib import Path

# step_2: MindStudio 全部流水线的 runHistory/运行记录情况
d = json.load(open(Path('out/work/step_2_failed_runs.json'), encoding='utf-8'))
for key, info in d.items():
    if key == '_meta' or not key.startswith('MindStudio|'):
        continue
    print('==', key)
    hist = info.get('runHistory') or []
    print('  runHistory=%d failedRuns=%d' % (len(hist), len(info.get('failedRuns') or [])))
    for r in hist:
        print('   #%s %s %s iva=%s cpr=%s end=%s title=%s' % (
            r.get('rn'), r.get('status'), r.get('conclusion') or '',
            r.get('isVersionAvailable'), r.get('casePassRate'), (r.get('end') or '')[:19],
            (r.get('displayTitle') or '')[:40]))
