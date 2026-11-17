import json
p = r"out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml/pipeline.json"
d = json.load(open(p, encoding="utf-8"))
for i, r in enumerate(d.get("records", [])):
    an = r.get("analysis") or {}
    if an.get("status") != "pending" or i < 11:
        continue
    print("==== idx", i, r.get("recordId"), r.get("status"), "| ftt", r.get("ftt"), "| verdict", (r.get("verdict") or {}).get("category"))
    print("  start", r.get("startTime"), "end", r.get("endTime"), "| githubRun", (r.get("githubRun") or {}).get("runId") if r.get("githubRun") else None)
    print("  keys:", [k for k in r.keys()])
    for t in r.get("tasks") or []:
        print("  TASK", t.get("type"), "|", (t.get("jobName") or "")[:45], "| log:", (t.get("logFile") or ""))
        print("       note:", (t.get("evidenceNote") or ""))
        print("       concl:", t.get("githubJob") if t.get("githubJob") else "")
        for ln in (t.get("errorLines") or [])[:10]:
            print("     -", str(ln)[:180])
