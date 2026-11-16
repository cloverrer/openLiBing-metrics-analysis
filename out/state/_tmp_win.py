import json, sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

record_dir = sys.argv[1]
fname = sys.argv[2]
start, end = int(sys.argv[3]), int(sys.argv[4])
d = json.load(open(record_dir + '/pipeline.evidence.json', encoding='utf-8'))
val = (d.get('files') or {}).get(fname)
if val is None:
    print(f"!! file not found: {fname}")
    sys.exit(1)
if isinstance(val, dict):
    lines = val.get('lines') or []
else:
    lines = str(val).split('\n')
for i in range(start - 1, min(end, len(lines))):
    print(f"{i+1}\t{lines[i].rstrip()[:300]}")
