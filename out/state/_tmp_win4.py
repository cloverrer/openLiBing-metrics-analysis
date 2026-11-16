import os, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_win4_out.txt")
buf = []

rel = r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json"
p = os.path.join(ROOT, rel)
with open(p, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

rx = re.compile(r"Failed to allocate|Environment allocation|exit code|失败组合|pes=|FAILED to run")
for i, line in enumerate(lines, 1):
    if rx.search(line):
        buf.append("L%d : %s" % (i, line.strip()[:300]))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf[:60]) + "\n")
print("written", min(len(buf), 60), "lines")
