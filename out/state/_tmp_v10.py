import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json")

# Kimi-K3-MRV2 job 从开头找真正失败原因（run 开始 01:01），看 benchmark 汇总/断言行
rx = re.compile(r"aisbench|TPOT|throughput|Throughput|Accuracy|accuracy|score|assert|AssertionError|exceed", re.I)
n = 0
with open(p, "r", encoding="utf-8", errors="replace") as f:
    for i, line in enumerate(f, 1):
        if i < 2400 and rx.search(line):
            print("L%d : %s" % (i, line.strip()[:340]))
            n += 1
            if n >= 20:
                break
