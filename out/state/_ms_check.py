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
            print('  ', pipe, 'NO pipeline.json')
            continue
        d = json.load(open(f, encoding='utf-8'))
        va = d.get('versionAvailability') or d.get('va') or d.get('metrics', {}).get('va')
        bs = d.get('buildSuccess') or d.get('bs') or d.get('metrics', {}).get('bs')
        recs = d.get('records') or []
        n_ok = sum(1 for r in recs if (r.get('verdict') or {}).get('category') == 'success')
        print('  %-18s va=%s bs=%s records=%d (success=%d)' % (pipe, va, bs, len(recs), n_ok))
        print('    top keys:', [k for k in d.keys() if k not in ('records',)][:15])
