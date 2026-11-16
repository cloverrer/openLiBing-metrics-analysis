import os, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_meta5_out.txt")
buf = []

TARGETS = [
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["120", "121", "124"]),
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2128", "2132"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
    (r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.json", ["145"]),
]

for rel, ids in TARGETS:
    p = os.path.join(ROOT, rel)
    buf.append("== " + rel)
    if not os.path.exists(p):
        buf.append("  !! missing")
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    for rec in data.get("records", []):
        rid = str(rec.get("runId") or rec.get("id") or "")
        if rid.split("#")[-1] in ids:
            buf.append("  REC %s" % rid)
            buf.append("    keys: %s" % list(rec.keys()))
            buf.append("    status=%s end=%s" % (rec.get("status"), rec.get("endTime")))
            for k in ("keyError", "failReason", "message", "note", "summary", "classify", "reason"):
                if rec.get(k):
                    buf.append("    %s: %s" % (k, str(rec[k])[:400]))
            tasks = rec.get("tasks") or []
            for t in tasks[:12]:
                if isinstance(t, dict):
                    buf.append("    task: %s | %s | log=%s" % (t.get("name"), t.get("status"), t.get("log")))
            tr = rec.get("testResults")
            if tr:
                buf.append("    testResults: %s" % json.dumps(tr, ensure_ascii=False)[:600])
            ev = rec.get("evidence")
            if ev:
                buf.append("    evidence: %s" % json.dumps(ev, ensure_ascii=False)[:600])

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
