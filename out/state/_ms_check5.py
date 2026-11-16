# -*- coding: utf-8 -*-
import json
from pathlib import Path

# 检查 step_2 原始产物中 msprof 的元数据（为何 runHistory=0）
d = json.load(open(Path('out/work/step_2_failed_runs.json'), encoding='utf-8'))
for key in ('MindStudio|msprof', 'MindStudio|msprobe', 'MindStudio|msmodelslim'):
    info = d.get(key) or {}
    print('==', key)
    print('  keys:', list(info.keys()))
    meta = info.get('meta') or {}
    print('  meta:', json.dumps({k: meta.get(k) for k in ('dashVa', 'dashBs', 'vaTrack', 'bsTrack', 'vaReason', 'collected')}, ensure_ascii=False))
    days = info.get('days') or {}
    for day, dv in days.items():
        if isinstance(dv, dict):
            print('  day', day, ':', json.dumps({k: dv.get(k) for k in ('kept', 'availed', 'note', 'status', 'excluded')}, ensure_ascii=False)[:200])
    print('  note:', str(info.get('note'))[:200])
