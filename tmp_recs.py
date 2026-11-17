import json
p = r"out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml/pipeline.json"
d = json.load(open(p, encoding="utf-8"))
for i in [1,2,4,5,6,7,8,10,12,16]:
    r = d["records"][i]
    print("==== idx",i, r.get("recordId"), "status", r.get("status"), "ftt", r.get("failedTaskType"), "| platform", r.get("platform"))
    print("   light", r.get("light"), "| verdict", (r.get("verdict") or {}))
    print("   links", json.dumps(r.get("links") or {}, ensure_ascii=False)[:300])
    print("   counts", r.get("counts"))
    print("   evidence", json.dumps(r.get("evidence") or {}, ensure_ascii=False)[:400])
    print("   suggestions", json.dumps(r.get("suggestions") or [], ensure_ascii=False)[:300])
    for t in r.get("tasks") or []:
        print("   TASK", t.get("type"), (t.get("jobName") or "")[:50], "| log:", (t.get("logFile") or "")[:90], "| note:", (t.get("evidenceNote") or "")[:80])
