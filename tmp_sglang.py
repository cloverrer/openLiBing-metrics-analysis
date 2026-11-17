import json
p = r"out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml/pipeline.json"
d = json.load(open(p, encoding="utf-8"))
for i, r in enumerate(d.get("records", [])):
    an = r.get("analysis") or {}
    if an.get("status") != "pending":
        continue
    print("== idx", i, "recId", r.get("recordId"), "status", r.get("status"), "ftt", r.get("ftt"))
    print("   time", r.get("endTime"), "verdict", (r.get("verdict") or {}).get("category"))
    for t in r.get("tasks") or []:
        print("   task", t.get("type"), "|", t.get("jobName"), "| errLines", len(t.get("errorLines") or []))
        for c in t.get("cases") or []:
            print("      case", c.get("state"), c.get("name"))
        for e in (t.get("errorMessages") or [])[:4]:
            print("      ERR", str(e.get("line"))[:6], "|", (e.get("text") or "")[:150])
