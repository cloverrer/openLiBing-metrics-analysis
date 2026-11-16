import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json")

rx = re.compile(r"TPOT.*[0-9]|P50|p99|mean_.*latency|avg.*ms|verify_metric|check_.*fail|result.*(fail|pass)", re.I)
hits = []
with open(p, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f, 1):
        if rx.search(line) and "TPOT50-PD" in line:
            hits.append((i, line.strip()[:320]))
        if len(hits) >= 15:
            break
for i, t in hits:
    print("L%d : %s" % (i, t))
if not hits:
    # 兜底：搜所有 TPOT 数值行
    rx2 = re.compile(r"TPOT")
    n = 0
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if rx2.search(line):
                print("L%d : %s" % (i, line.strip()[:320]))
                n += 1
                if n >= 15:
                    break
