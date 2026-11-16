import os, re, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cites3_out.txt")
buf = []

def grep_ev(rel, pats, cap=3):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        buf.append("  !! missing " + rel)
        return
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    buf.append("  total lines: %d" % len(lines))
    for p_ in pats:
        hits = []
        for i, line in enumerate(lines, 1):
            if re.search(p_, line):
                hits.append((i, line.strip()[:260]))
        buf.append("  PAT %s -> %d hits" % (p_, len(hits)))
        for i, l in hits[:cap]:
            buf.append("    L%d : %s" % (i, l))

buf.append("== shmem#145 Test_shmem log (11-10)")
grep_ev(r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json",
        [r"Environment allocation failed", r"apply_env_res.*'status': 'queued'", r"apply_env_res.*failed|allocation", r"exited with", r"FAILED", r"超时"], 3)

buf.append("== shmem#142/#140 (11-09) fail signature")
grep_ev(r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json",
        [r"COMPUTE_TASK_INFO", r"run failed", r"profiling", r"FAILED\(失败\)"], 2)

buf.append("== ops-nn 11-09 (#168 #169) accuracy fail")
grep_ev(r"2026\2026-11\2026-11-09\Ascend-CANN\ops-nn\pipeline.evidence.json",
        [r"acc_pass_result= Failed", r"accuracy not passed", r"Not Pass", r"assert.*fail", r"compare.*fail"], 3)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
