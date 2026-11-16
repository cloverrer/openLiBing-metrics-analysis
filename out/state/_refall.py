# -*- coding: utf-8 -*-
"""只读探针：导出指定归档日全部 done 记录的 analysis 摘要（学习口径）。"""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
day = sys.argv[1]
d = ROOT / "out" / "archive" / "2026" / "2026-11" / day
out = []
n = 0
for comp in sorted(d.iterdir()):
    if not comp.is_dir():
        continue
    for pipe in sorted(comp.iterdir()):
        pj = pipe / "pipeline.json"
        if not pj.is_file():
            continue
        doc = json.loads(pj.read_text(encoding="utf-8"))
        for rec in doc.get("records") or []:
            a = rec.get("analysis") or {}
            if a.get("status") != "done":
                continue
            n += 1
            out.append("### %s" % rec.get("recordId"))
            out.append("  issueType=%s | issueDetail=%s" % (a.get("issueType"), a.get("issueDetail")))
            out.append("  keyError=%s" % a.get("keyError"))
            out.append("  rootCause=%s" % a.get("rootCause"))
            out.append("  advice=%s" % a.get("advice"))
            out.append("  cites=%s" % json.dumps(a.get("cites"), ensure_ascii=False))
            out.append("")
Path(ROOT / "out" / "state" / ("_refall_%s.txt" % day)).write_text("\n".join(out), encoding="utf-8")
print("done=%d" % n)
