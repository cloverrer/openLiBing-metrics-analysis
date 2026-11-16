import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json")
rx = re.compile(r"TPOT.*ms|benchmark.*(fail|Fail)|aisbench|expect|<=|≥|<= *[0-9]")
shown = 0
with open(p, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f, 1):
        if rx.search(line):
            print("L%d : %s" % (i, line.strip()[:320]))
            shown += 1
            if shown >= 20:
                break
