import json, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

DUMPS = [
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2125", "2128", "2132", "2133"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["121", "124"]),
    (r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.json", ["140", "142"]),
    (r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.json", ["143", "144"]),
    (r"2026\2026-11\2026-11-06\MindIE\MindIE-Motor\pipeline.json", ["117"]),
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["120"]),
]

def find_recs(data, ids):
    hits = []
    for rec in data.get("records", []):
        rid = str(rec.get("runId") or rec.get("id") or "")
        for i in ids:
            if rid.endswith("#" + i) or rid.split("#")[-1] == i:
                hits.append(rec)
    return hits

for rel, ids in DUMPS:
    p = os.path.normpath(os.path.join(ROOT, rel))
    if not os.path.exists(p):
        print("!! not found", rel)
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    for rec in find_recs(data, ids):
        print("=" * 70)
        print("REC", rec.get("runId"), "| status=", rec.get("status"), "| end=", rec.get("endTime"))
        print("  fields:", list(rec.keys()))
        for t in (rec.get("tasks") or []):
            print("  task: %s | status=%s | log=%s" % (t.get("name"), t.get("status"), t.get("log")))
        for k in ("keyError", "keyErrors", "failReason", "message", "note"):
            if rec.get(k):
                print("  %s: %s" % (k, str(rec[k])[:500]))
        tr = rec.get("testResults")
        if tr:
            print("  testResults:", json.dumps(tr, ensure_ascii=False)[:800])
        for k in ("failedTaskType", "buildCount", "buildPassCount"):
            if rec.get(k) is not None:
                print("  %s: %s" % (k, rec[k]))
