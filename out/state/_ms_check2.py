# -*- coding: utf-8 -*-
import json, os
from pathlib import Path

base = Path('out/archive/2026/2026-11')
for day in sorted(os.listdir(base)):
    ms = base / day / 'MindStudio'
    if not ms.is_dir():
        continue
    print('==', day)
    for pipe in sorted(os.listdir(ms)):
        f = ms / pipe / 'pipeline.json'
        if not f.exists():
            continue
        d = json.load(open(f, encoding='utf-8'))
        print('  %-18s counts=%s' % (pipe, json.dumps(d.get('counts'), ensure_ascii=False)))
        for r in d.get('records') or []:
            v = r.get('verdict') or {}
            print('     #%s %s status=%s va=%s cpr=%s avail=%s' % (
                r.get('buildNumber'), (v.get('category') or '')[:14], r.get('status'),
                r.get('isVersionAvailable'), r.get('casePassRate'), r.get('versionAvail')))
