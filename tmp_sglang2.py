import json
p = r"out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml/pipeline.json"
d = json.load(open(p, encoding="utf-8"))
for i, r in enumerate(d.get("records", [])):
    an = r.get("analysis") or {}
    if an.get("status") != "pending":
        continue
    print("==== idx", i, r.get("recordId"), r.get("status"))
    print("  buildUrl:", (r.get("buildUrl") or "")[:120])
    for t in r.get("tasks") or []:
        print("  TASK", t.get("type"), "|", (t.get("jobName") or "")[:40], "| log:", (t.get("logFile") or ""))
        for ln in (t.get("errorLines") or [])[:8]:
            print("     -", str(ln)[:170])
        for c in t.get("cases") or []:
            print("     CASE", c.get("state"), (c.get("name") or "")[:60], "|", (c.get("description") or "")[:90])
