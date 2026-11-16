# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_2_dash_raw.json'), encoding='utf-8'))
for key in ('MindStudio|msprof', 'MindStudio|msmemscope', 'MindStudio|msprobe'):
    v = d.get(key)
    print('==', key, type(v).__name__, len(v) if hasattr(v, '__len__') else '')
    if isinstance(v, list):
        print('  n =', len(v))
        for r in v[:6]:
            print('   rn=%s status=%s start=%s end=%s iva=%s cpr=%s' % (
                r.get('pipelineRunNumber'), r.get('pipelineRunStatus'),
                str(r.get('pipelineRunStartTime'))[:19], str(r.get('pipelineRunEndtime'))[:19],
                r.get('isVersionAvailable'), r.get('casePassRate')))
        # 时间字段样本
        print('  sample keys:', list(v[0].keys()) if v else '(empty)')
        ends = [str(r.get('pipelineRunEndtime'))[:10] for r in v]
        from collections import Counter
        print('  end-date dist:', dict(Counter(ends)))
