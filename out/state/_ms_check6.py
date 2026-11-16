# -*- coding: utf-8 -*-
import json
from pathlib import Path

d = json.load(open(Path('out/work/step_2_failed_runs.json'), encoding='utf-8'))
for key in ('MindStudio|msprof', 'MindStudio|msmodelslim', 'MindStudio|msot'):
    info = d.get(key) or {}
    print('==', key)
    print('  availDays=%s daysInPeriod=%s' % (info.get('availDays'), info.get('daysInPeriod')))
    print('  recompute=%s scheduledOnly=%s vaRateRecomputed=%s dayAvail=%s' % (
        info.get('recompute'), info.get('scheduledOnly'), info.get('vaRateRecomputed'),
        json.dumps(info.get('dayAvail'), ensure_ascii=False)[:300]))
    days = info.get('days') or {}
    for day, dv in sorted(days.items()):
        print('  day', day, ':', json.dumps(dv, ensure_ascii=False)[:260])
