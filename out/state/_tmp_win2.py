import os, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_win2_out.txt")
buf = []

def win(rel, lo, hi, pats=None):
    p = os.path.join(ROOT, rel)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    buf.append("== %s L%d-L%d (total %d)" % (rel, lo, hi, len(lines)))
    rx = re.compile(pats) if pats else None
    for i in range(max(0, lo - 1), min(len(lines), hi)):
        s = lines[i].strip()
        if rx and not rx.search(s):
            continue
        buf.append("  L%d : %s" % (i + 1, s[:300]))

# shmem 11-10: around the two FAILED markers
win(r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json", 4460, 4495)
win(r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json", 9095, 9130)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
