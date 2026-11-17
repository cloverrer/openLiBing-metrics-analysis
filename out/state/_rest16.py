# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))

TARGETS = [
    "MindCluster|Agentsdk~5992cb#2",
    "UBS Core|Nightly-CI-Version-pipeline_BeiMing#261",
    "UBS Core|Nightly-CI-Version-pipeline_BeiMing#262",
    "SgLang|nightly-test-npu.yml#2227",
    "SgLang|nightly-test-npu.yml#2216",
    "SgLang|nightly-test-npu.yml#2217",
    "SgLang|nightly-test-npu.yml#2219",
    "SgLang|nightly-test-npu.yml#2221",
    "SgLang|nightly-test-npu.yml#2211",
]

out = []
for it in PEND["records"]:
    if it["recordId"] not in TARGETS:
        continue
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    rec = doc["records"][int(parts[1].rstrip("]"))]
    out.append("### %s status=%s failedTaskType=%s" % (it["recordId"], rec.get("status"), rec.get("failedTaskType")))
    for i, t in enumerate(rec.get("tasks", [])):
        out.append("  [%d] type=%s job=%s logFile=%s bytes=%s lines=%s download=%s" % (
            i, t.get("type"), t.get("jobName"), t.get("logFile"), t.get("logBytes"), t.get("logLines"), t.get("download")))
        for e in (t.get("errorLines") or [])[:12]:
            out.append("      err: %r" % (e,))
        for s in (t.get("stepErrMsgs") or [])[:8]:
            out.append("      step: %r" % (s,))
        for c in (t.get("cases") or [])[:8]:
            out.append("      case: %s state=%s err=%r" % (c.get("name"), c.get("state"), (c.get("errorMessages") or [])[:2]))
        if t.get("evidenceNote"):
            out.append("      note: %s" % t["evidenceNote"])
    out.append("")

(ROOT / "out/state/_rest16.txt").write_text("\n".join(out), encoding="utf-8")
print("bytes=", (ROOT / "out/state/_rest16.txt").stat().st_size)
