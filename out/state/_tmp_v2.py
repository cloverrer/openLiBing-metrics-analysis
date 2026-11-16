import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json")

rx = re.compile(r"TPOT|Expected|assert|Target|metrics|not .*than|less than|greater than|FAIL_TAG.*✗|The following aisbench", re.I)
shown = 0
with open(p, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f, 1):
        if rx.search(line):
            print("L%d : %s" % (i, line.strip()[:300]))
            shown += 1
            if shown >= 25:
                break
