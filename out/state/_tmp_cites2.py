import os, re, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cites2_out.txt")
buf = []

def grep_file(path, pats, cap=3):
    if not os.path.exists(path):
        buf.append("  !! missing " + path)
        return
    counts = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            for p in pats:
                if re.search(p, line):
                    counts.setdefault(p, []).append((i, line.strip()[:240]))
    for p, hits in counts.items():
        buf.append("  PAT %s -> %d hits" % (p, len(hits)))
        for i, l in hits[:cap]:
            buf.append("    L%d : %s" % (i, l))

# shmem#145 job log - env alloc final state
p = os.path.join(ROOT, r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json")
buf.append("== shmem 11-10 evidence (job log embedded or file refs)")
# find the actual job log file under archive dir
shmem_dir = os.path.join(ROOT, r"2026\2026-11\2026-11-10\Ascend-CANN\shmem")
for fn in os.listdir(shmem_dir):
    buf.append("  file: " + fn)

logp = None
for root, dirs, files in os.walk(shmem_dir):
    for fn in files:
        if "13_shmem_145" in fn and fn.endswith(".log"):
            logp = os.path.join(root, fn)
if logp:
    buf.append("== shmem145 log grep: " + logp)
    grep_file(logp, [r"Environment allocation failed", r"apply_env_res.*failed", r"queued", r"FAILED\(失败\)", r"exited with", r"ERROR", r"TimeoutError"], 4)

# HPCKit evidence lines
buf.append("== HPCKit 11-06 hmpi evidence")
hp = os.path.join(ROOT, r"2026\2026-11\2026-11-06\HPCKit\hmpi\pipeline.evidence.json")
if os.path.exists(hp):
    with open(hp, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if "Access denied" in line or "Authentication failed" in line or "remote: " in line[:200] and "denied" in line:
                buf.append("  L%d : %s" % (i, line.strip()[:240]))
                if i > 200000:
                    break

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
