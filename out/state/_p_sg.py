# -*- coding: utf-8 -*-
"""Dump SgLang github records: tasks + testResults + log windows."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
base = ROOT / "out" / "archive" / "2026" / "2026-11" / "2026-11-09" / "SgLang" / "nightly-test-npu.yml"
doc = json.loads((base / "pipeline.json").read_text(encoding="utf-8"))
ev = json.loads((base / "pipeline.evidence.json").read_text(encoding="utf-8"))
files = ev.get("files") or {}

out = []
for rec in doc.get("records") or []:
    rid = rec.get("recordId")
    out.append("=" * 70)
    out.append("RID=%s status=%s ftt=%s" % (rid, rec.get("status"), rec.get("failedTaskType")))
    for t in rec.get("tasks") or []:
        out.append("  TASK %s | concl=%s | log=%s" % (
            t.get("jobName"), (t.get("githubJob") or {}).get("conclusion"), t.get("logFile")))
        gj = t.get("githubJob") or {}
        if gj.get("steps"):
            out.append("     steps=%s" % gj.get("steps"))
        tr = t.get("testResults")
        if tr:
            out.append("     testResults=%s" % json.dumps(tr, ensure_ascii=False)[:1500])
        out.append("     errLines=%s" % json.dumps(t.get("errorLines") or [], ensure_ascii=False)[:800])
    for em in (rec.get("errorMessages") or [])[:6]:
        out.append("  EM %s:%s | %s" % (em.get("source"), em.get("line"), str(em.get("text"))[:200]))
Path(sys.argv[1]).write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote", sys.argv[1], len(out), "lines")
