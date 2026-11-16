# -*- coding: utf-8 -*-
"""只读探针：导出 SgLang 各 github 记录的 jobs 结论 / testResults / githubMeta。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"
day = sys.argv[1]
outp = Path(sys.argv[2])
buf = []
P = lambda s="": buf.append(s)
day_dir = AR / day[:4] / day[:7] / day
for comp in sorted(day_dir.iterdir()):
    if not comp.is_dir() or comp.name.startswith("_"):
        continue
    if "SgLang" not in comp.name:
        continue
    for pipe in sorted(comp.iterdir()):
        pj = pipe / "pipeline.json"
        if not pj.is_file():
            continue
        doc = json.loads(pj.read_text(encoding="utf-8"))
        for rec in doc.get("records") or []:
            if (rec.get("analysis") or {}).get("status") != "pending":
                continue
            P("=" * 90)
            P("RID=%s  keys=%s" % (rec.get("recordId"), sorted(rec.keys())))
            gm = rec.get("githubMeta") or {}
            P("githubMeta keys=%s" % sorted(gm.keys()))
            P("  failedJobs=%s" % json.dumps(gm.get("failedJobs"), ensure_ascii=False)[:1500])
            P("  cancelledJobs=%s" % json.dumps(gm.get("cancelledJobs"), ensure_ascii=False)[:600])
            P("  run=%s status=%s conclusion=%s attempt=%s" % (
                gm.get("runId"), gm.get("status"), gm.get("conclusion"), gm.get("runAttempt")))
            tr = rec.get("testResults")
            if tr:
                P("testResults=%s" % json.dumps(tr, ensure_ascii=False)[:2500])
            for t in rec.get("tasks") or []:
                P("  TASK [%s] %s | concl=%s | log=%s" % (
                    t.get("type"), str(t.get("jobName"))[:70], t.get("conclusion") or t.get("state"),
                    t.get("logFile")))
                gj = t.get("githubJob") or {}
                if gj:
                    P("     gj status=%s concl=%s steps=%s" % (
                        gj.get("status"), gj.get("conclusion"),
                        json.dumps([(s.get("name"), s.get("conclusion")) for s in (gj.get("steps") or [])],
                                   ensure_ascii=False)[:900]))
outp.write_text("\n".join(buf) + "\n", encoding="utf-8")
print("wrote %d -> %s" % (len(buf), outp))
