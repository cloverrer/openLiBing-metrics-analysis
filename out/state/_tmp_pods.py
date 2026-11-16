import json, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open(r'out/archive/2026/2026-11/2026-11-06/MindIE/MindIE-Motor/pipeline.evidence.json', encoding='utf-8'))
lines = d['files']['case_logs/case_0000.html']['lines']

cur = None
for i in range(5712, 8900):
    t = re.sub(r'<[^>]+>', '', lines[i]).strip().replace('&quot;', '"')
    m = re.search(r'"name":\s*"((?:vllm|mindie)[a-z0-9.-]*)"', t)
    if m and 'app' not in t and 'generateName' not in t:
        cur = m.group(1)
    m2 = re.search(r'"phase":\s*"(\w+)"', t)
    if m2:
        print(f"L{i+1} {cur} phase={m2.group(1)}")
    m3 = re.search(r'"startedAt":\s*"([^"]+)"', t)
    if m3:
        print(f"L{i+1} {cur} startedAt={m3.group(1)}")
    m4 = re.search(r'"restartCount":\s*(\d+)', t)
    if m4:
        print(f"L{i+1} {cur} restartCount={m4.group(1)}")
