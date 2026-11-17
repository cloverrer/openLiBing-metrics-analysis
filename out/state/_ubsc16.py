# -*- coding: utf-8 -*-
"""同上，但所有行截断。"""
import json
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
IDX = {it["recordId"]: it for it in PEND["records"]}


def record(rid):
    it = IDX[rid]
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    return doc["records"][int(parts[1].rstrip("]"))], (ROOT / "out" / parts[0]).parent


def one(text, n=400):
    return " ".join(text.split())[:n]


out = []
for rid in ["UBS Core|Nightly-CI-Version-pipeline_BeiMing#261",
            "UBS Core|Nightly-CI-Version-pipeline_BeiMing#262"]:
    rec, pdir = record(rid)
    out.append("### %s" % rid)
    for ti, t in enumerate(rec["tasks"]):
        path = t.get("logFile")
        out.append("  -- ti=%d job=%s type=%s" % (ti, t.get("jobName"), t.get("type")))
        out.append("     errorLines=%s" % (t.get("errorLines"),))
        out.append("     stepErrMsgs=%s" % (t.get("stepErrMsgs"),))
        for ln in range(1, 12):
            text, ok = pipeline_doc.evidence_window(pdir, path, ln, ln, max_lines=1)
            if not ok:
                break
            out.append("     L%d | %s" % (ln, one(text)))
    out.append("")

rec, pdir = record("Ascend-CANN|os#153")
path = rec["tasks"][0]["logFile"]
out.append("### Ascend-CANN 153 tasks[0] errorLines=%s" % (rec["tasks"][0].get("errorLines"),))
out.append("### Ascend-CANN 153 tasks[0] stepErrMsgs=%s" % (rec["tasks"][0].get("stepErrMsgs"),))
out.append("### Ascend-CANN 153 tasks[0] excerpt=%s" % one(str(rec["tasks"][0].get("excerpt") or ""), 800))
for ln in range(90, 99):
    text, ok = pipeline_doc.evidence_window(pdir, path, ln, ln, max_lines=1)
    if ok:
        out.append("  L%d | %s" % (ln, one(text, 500)))

(ROOT / "out/state/_ubsc16.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
