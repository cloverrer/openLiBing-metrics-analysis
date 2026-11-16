import os, re, sys, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_final3_out.txt")
buf = []

def log(s):
    buf.append(s)

def scan(rel, pat, cap=4):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        log("  !! not found: " + rel)
        return
    rx = re.compile(pat)
    n = 0
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if rx.search(line):
                log("  L%d : %s" % (i, line.strip()[:300]))
                n += 1
                if n >= cap:
                    return
    if n == 0:
        log("  (no match)")

log("== shmem145 env alloc fail (11-10) ==")
scan(r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json", r"Environment allocation failed", 3)
log("== shmem141 queued (11-09) ==")
scan(r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json", r"'status': 'queued'", 2)
log("== sgl2085 InitDram (11-06) ==")
scan(r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json", r"InitDramSegment|ES9999", 3)
log("== sgl2086 HYBM (11-06) ==")
scan(r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json", r"hybm|HYBM", 3)
log("== vllm16451 timeout/npu (11-06) ==")
scan(r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json", r"Timeout reached|Insufficient .*npu|pending.*pod|Pending", 3)
log("== sgl2133 fia_unset (11-09) ==")
scan(r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json", r"overlap_fia_unset", 3)

log("== record meta ==")
for rel, ids in [
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["120", "121", "124"]),
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2128", "2132"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
]:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        log("  !! missing " + rel)
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    for rec in data.get("records", []):
        rid = str(rec.get("runId") or "")
        for i in ids:
            if rid.split("#")[-1] == i:
                log("  REC %s | status=%s | end=%s" % (rid, rec.get("status"), rec.get("endTime")))
                for k in ("keyError", "failReason", "message", "note"):
                    if rec.get(k):
                        log("    %s: %s" % (k, str(rec[k])[:300]))
                for t in (rec.get("tasks") or [])[:8]:
                    log("    task: %s | %s | log=%s" % (t.get("name"), t.get("status"), t.get("log")))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", OUT, len(buf), "lines")
