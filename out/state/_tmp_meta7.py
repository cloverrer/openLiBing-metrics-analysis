import os, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_meta7_out.txt")
buf = []

TARGETS = [
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["120", "121", "124"]),
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2128", "2132"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
    (r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.json", ["145"]),
]

def rid_of(rec):
    r = str(rec.get("recordId") or "")
    return r

for rel, ids in TARGETS:
    p = os.path.join(ROOT, rel)
    buf.append("== " + rel)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    for rec in data.get("records", []):
        rid = rid_of(rec)
        num = rid.split("#")[-1]
        if num in ids:
            buf.append("  REC %s status=%s ended=%s" % (rid, rec.get("status"), rec.get("endedAt")))
            for k in ("errorMessages", "keyError", "note"):
                if rec.get(k):
                    buf.append("    %s: %s" % (k, json.dumps(rec[k], ensure_ascii=False)[:500]))
            ev = rec.get("evidence")
            if ev:
                buf.append("    evidence: %s" % json.dumps(ev, ensure_ascii=False)[:800])
            cases = rec.get("cases")
            if cases:
                buf.append("    cases: %s" % json.dumps(cases, ensure_ascii=False)[:800])
            tasks = rec.get("tasks") or []
            for t in tasks[:12]:
                if isinstance(t, dict):
                    buf.append("    task: %s | %s" % (t.get("name"), t.get("status")))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
