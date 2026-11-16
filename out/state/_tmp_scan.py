import json, sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'state', '_scan_all.txt')
files = glob.glob(os.path.join(ROOT, 'archive', '**', 'pipeline.json'), recursive=True)
buf = []
for path in sorted(files):
    try:
        d = json.load(open(path, encoding='utf-8'))
    except Exception as ex:
        buf.append(f"!! parse fail {path}: {ex}")
        continue
    recs = d.get('records') or []
    pend = [r for r in recs if (r.get('analysis') or {}).get('status') == 'pending']
    if not pend:
        continue
    rel = os.path.relpath(path, os.path.join(ROOT, 'archive'))
    for r in pend:
        buf.append(f"=== {rel} #{r.get('buildNumber')} status={r.get('status')} end={r.get('endedAt') or r.get('endTime')}")
        for t in (r.get('tasks') or []):
            buf.append(f"    task={t.get('jobName')} type={t.get('type')} log={t.get('logFile')}")
        cases = r.get('cases') or []
        if cases:
            names = [c.get('name') or c.get('caseName') or '?' for c in cases]
            buf.append(f"    cases({len(names)}): {', '.join(names[:8])}{' ...' if len(names) > 8 else ''}")
        msgs = r.get('errorMessages') or []
        texts = [(e.get('text') or '').strip() for e in msgs]
        texts = [t for t in texts if t]
        for t in texts[:6]:
            buf.append(f"    ERR {t[:200]}")
        if len(texts) > 6:
            buf.append(f"    ERR ... (+{len(texts)-6} more)")

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(buf))
print(f"written {len(buf)} lines to _scan_all.txt")
