import os, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_meta4_out.txt")
buf = []

TARGETS = [
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["120", "121", "124"]),
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2128", "2132"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
    (r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.json", ["145"]),
]

def walk(obj, path=""):
    if isinstance(obj, dict):
        rid = obj.get("runId") or obj.get("id") or ""
        if isinstance(rid, str) and "#" in rid:
            yield path, obj
        for k, v in obj.items():
            yield from walk(v, path + "/" + str(k))
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            yield from walk(v, path + "[%d]" % idx)

for rel, ids in TARGETS:
    p = os.path.join(ROOT, rel)
    buf.append("== " + rel)
    if not os.path.exists(p):
        buf.append("  !! missing")
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    top_keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
    buf.append("  top keys: %s" % top_keys)
    found = 0
    for path, rec in walk(data):
        rid = str(rec.get("runId") or rec.get("id"))
        if rid.split("#")[-1] in ids:
            found += 1
            buf.append("  REC %s  path=%s" % (rid, path))
            buf.append("    status=%s end=%s" % (rec.get("status"), rec.get("endTime")))
            for k in ("keyError", "failReason", "message", "note", "summary", "classify"):
                if rec.get(k):
                    buf.append("    %s: %s" % (k, str(rec[k])[:300]))
            tasks = rec.get("tasks") or rec.get("failedTasks") or []
            for t in tasks[:10]:
                if isinstance(t, dict):
                    buf.append("    task: %s | %s | log=%s" % (t.get("name"), t.get("status"), t.get("log")))
    if not found:
        buf.append("  (no record matched ids %s)" % ids)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
