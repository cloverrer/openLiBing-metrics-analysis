# -*- coding: utf-8 -*-
"""只读探针：导出 SgLang 当日归档的证据文件清单 + 各记录任务/errorLines。"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive" / "2026" / "2026-11"
day = "2026-11-09"
base = AR / day / "SgLang" / "nightly-test-npu.yml"
doc = json.loads((base / "pipeline.json").read_text(encoding="utf-8"))
ev = json.loads((base / "pipeline.evidence.json").read_text(encoding="utf-8"))

out = []
out.append("== evidence files ==")
files = ev.get("files") or {}
for k in sorted(files):
    v = files[k]
    out.append("  %s  [%d lines]" % (k, (len(v.splitlines()) if isinstance(v, str) else -1)))
out.append("")
for rec in doc.get("records") or []:
    a = (rec.get("analysis") or {}).get("status")
    out.append("RID=%s status=%s ftt=%s analysis=%s" % (
        rec.get("recordId"), rec.get("status"), rec.get("failedTaskType"), a))
    for t in rec.get("tasks") or []:
        out.append("  TASK name=%s concl=%s platform=%s isTest=%s" % (
            t.get("name"), t.get("conclusion"), t.get("platform"), t.get("isTestJob")))
        for el in (t.get("errorLines") or [])[:12]:
            out.append("    EL %s" % el)
        tr = t.get("testResults")
        if tr:
            out.append("    TR %s" % json.dumps(tr, ensure_ascii=False)[:400])
    out.append("")

Path(ROOT / "out" / "state" / "_sg_probe.txt").write_text("\n".join(out), encoding="utf-8")
print("written %d lines" % len(out))
