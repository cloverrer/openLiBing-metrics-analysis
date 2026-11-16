import json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

RELS = [
    r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json",
    r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json",
    r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json",
    r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json",
    r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.json",
    r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.json",
    r"2026\2026-11\2026-11-06\MindIE\MindIE-Motor\pipeline.json",
]

for rel in RELS:
    p = os.path.normpath(os.path.join(ROOT, rel))
    if not os.path.exists(p):
        print("!! not found", rel)
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    recs = data.get("records", [])
    print("%s -> %d records" % (rel, len(recs)))
    for rec in recs:
        rid = rec.get("runId") or rec.get("id") or "?"
        print("   %s | status=%s" % (rid, rec.get("status")))
