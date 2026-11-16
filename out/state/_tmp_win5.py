import os, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_win5_out.txt")
buf = []

def win(rel, lo, hi):
    p = os.path.join(ROOT, rel)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    buf.append("== %s L%d-L%d (total %d)" % (rel, lo, hi, len(lines)))
    for i in range(max(0, lo - 1), min(len(lines), hi)):
        buf.append("  L%d : %s" % (i + 1, lines[i].strip()[:280]))

# shmem 11-10: first failed combination area (pes=8 int32 around L2881)
win(r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json", 4390, 4465)

# shmem 11-09 #142: same allgather check L9100-9200 region for failure signature
win(r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json", 9840, 9878)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
