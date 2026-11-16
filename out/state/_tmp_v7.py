import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json")

# 在 Kimi-K2.6 job 段（L7400~8400）里找所有 ERROR/失败行
lo, hi = 7400, 8400
rx = re.compile(r"ERROR|error|failed|FAILED|exceed", re.I)
n = 0
with open(p, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f, 1):
        if lo <= i <= hi and rx.search(line):
            print("L%d : %s" % (i, line.strip()[:340]))
            n += 1
            if n >= 25:
                break
