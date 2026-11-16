# -*- coding: utf-8 -*-
import json
from pathlib import Path

# N2 原始明细：msmemscope/msprof 的运行记录时间分布
d = json.load(open(Path('out/work/step_2_dash_raw.json'), encoding='utf-8'))
print('type:', type(d).__name__, 'keys:', list(d.keys())[:8] if isinstance(d, dict) else len(d))
pipes = d.get('pipelines') if isinstance(d, dict) else d
if isinstance(pipes, dict):
    for key, v in pipes.items():
        if 'msmemscope' in key or 'msprof' in key or key in ('MindStudio|msprobe',):
            print('==', key, type(v).__name__)
            recs = v.get('records') if isinstance(v, dict) else v
            print('  records:', len(recs or []))
            for r in (recs or [])[:8]:
                print('   ', json.dumps({k: str(r.get(k))[:30] for k in ('pipelineRunNumber', 'pipelineRunStatus', 'pipelineRunEndtime', 'pipelineRunStartTime', 'isVersionAvailable', 'casePassRate')}, ensure_ascii=False))
            if isinstance(v, dict):
                for k in v.keys():
                    if k != 'records':
                        print('  meta:', k, str(v[k])[:120])
