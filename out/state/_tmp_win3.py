import os, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_win3_out.txt")
buf = []

rel = r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json"
p = os.path.join(ROOT, rel)
with open(p, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

rx = re.compile(r"失败组合|pes|FAILED to run|Aborted|core|cann.*error|ERROR.*\(")
for i, line in enumerate(lines, 1):
    if rx.search(line) and "step-indent" not in line[:60]:
        buf.append("L%d : %s" % (i, line.strip()[:260]))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf[:120]) + "\n")
print("written", min(len(buf), 120), "lines")
