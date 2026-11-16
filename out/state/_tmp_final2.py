import os, re, sys, io, json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

def scan(rel, pat, cap=4, lo=0, hi=10**9):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("  !! not found:", rel)
        return
    rx = re.compile(pat)
    n = 0
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if lo <= i <= hi and rx.search(line):
                print("  L%d : %s" % (i, line.strip()[:260]))
                n += 1
                if n >= cap:
                    return
    if n == 0:
        print("  (no match)")

print("== shmem145 env (11-09/10 evidence) ==")
scan(r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json",
     r"Environment allocation failed", 3)
print("== shmem141 queued count (11-09) ==")
scan(r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json",
     r"'status': 'queued'", 2)

print("== sgl2085 InitDram (11-06) ==")
scan(r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
     r"InitDramSegment", 3)
print("== sgl2086 (same file, HYGM) ==")
scan(r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
     r"hybm|HYBM", 3)

print("== vllm16451 (run 42099201193 in evidence) ==")
scan(r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
     r"Timeout reached|Insufficient huawei.com/ascend", 3)

print("== sgl2133 err (11-09) ==")
scan(r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
     r"overlap_fia_unset", 3)

print("== record meta: MIE 121/124, SGL 2091/2100/2128/2132, msot264 ==")
for rel, ids in [
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["120", "121", "124"]),
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2128", "2132"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
]:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("  !! missing", rel)
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    for rec in data.get("records", []):
        rid = str(rec.get("runId") or "")
        for i in ids:
            if rid.split("#")[-1] == i:
                print("  REC", rid, "| status=", rec.get("status"), "| end=", rec.get("endTime"))
                for k in ("keyError", "failReason", "message", "note"):
                    if rec.get(k):
                        print("    %s: %s" % (k, str(rec[k])[:260]))
                for t in (rec.get("tasks") or [])[:6]:
                    print("    task: %s | %s" % (t.get("name"), t.get("status")))
