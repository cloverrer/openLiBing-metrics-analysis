# -*- coding: utf-8 -*-
"""只读探针：导出指定归档日 SgLang 已 done 记录的 analysis（学习口径）。"""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
day = sys.argv[1]
base = ROOT / "out" / "archive" / "2026" / "2026-11" / day / "SgLang" / "nightly-test-npu.yml" / "pipeline.json"
if not base.is_file():
    print("no file %s" % base); raise SystemExit
doc = json.loads(base.read_text(encoding="utf-8"))
out = []
for rec in doc.get("records") or []:
    a = rec.get("analysis") or {}
    if a.get("status") != "done":
        continue
    out.append("### %s" % rec.get("recordId"))
    out.append("  issueType=%s | issueDetail=%s" % (a.get("issueType"), a.get("issueDetail")))
    out.append("  keyError=%s" % a.get("keyError"))
    out.append("  rootCause=%s" % a.get("rootCause"))
    out.append("  advice=%s" % a.get("advice"))
    out.append("  cites=%s" % json.dumps(a.get("cites"), ensure_ascii=False))
    out.append("")
Path(ROOT / "out" / "state" / ("_ref_%s.txt" % day)).write_text("\n".join(out), encoding="utf-8")
print("ok %d recs" % len([1 for r in (doc.get('records') or []) if (r.get('analysis') or {}).get('status') == 'done']))
