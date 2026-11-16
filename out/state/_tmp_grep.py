import json, sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

record_dir = sys.argv[1]
pat = re.compile(sys.argv[2])
maxhits = int(sys.argv[3]) if len(sys.argv) > 3 else 40
d = json.load(open(record_dir + '/pipeline.evidence.json', encoding='utf-8'))
files = d.get('files') or {}
hits = 0
for key, val in files.items():
    if isinstance(val, dict):
        lines = val.get('lines') or []
    elif isinstance(val, str):
        lines = val.split('\n')
    else:
        lines = []
    for i, l in enumerate(lines, 1):
        if pat.search(l):
            print(f"{key}:{i}\t{l.strip()[:240]}")
            hits += 1
            if hits >= maxhits:
                print(f"... stop at {hits} hits")
                sys.exit(0)
print(f"== total {hits} hits")
