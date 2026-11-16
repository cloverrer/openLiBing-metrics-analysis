# -*- coding: utf-8 -*-
"""只读探针：导出当日全部 pending 记录的 errorMessages（source:line | text）。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
day = "2026-11-09"
day_dir = ROOT / "out" / "archive" / day[:4] / day[:7] / day
out = []
for comp in sorted(day_dir.iterdir()):
    if not comp.is_dir() or comp.name.startswith("_"):
        continue
    for pipe in sorted(comp.iterdir()):
        pj = pipe / "pipeline.json"
        if not pj.is_file():
            continue
        doc = json.loads(pj.read_text(encoding="utf-8"))
        for rec in doc.get("records") or []:
            if (rec.get("analysis") or {}).get("status") != "pending":
                continue
            out.append("### %s  ftt=%r status=%s" % (
                rec.get("recordId"), rec.get("failedTaskType"), rec.get("status")))
            for e in (rec.get("errorMessages") or []):
                src = e.get("source") or e.get("src") or ""
                out.append("  %s:L%s | %s" % (src, e.get("line"), str(e.get("text"))[:230]))
            for t in (rec.get("tasks") or []):
                for el in (t.get("errorLines") or [])[:10]:
                    out.append("  [EL] %s" % str(el)[:230])
            out.append("")
Path(ROOT / "out" / "state" / "_all_em.txt").write_text("\n".join(out), encoding="utf-8")
print("lines=%d" % len(out))
