# -*- coding: utf-8 -*-
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
base = ROOT / "out" / "archive" / "2026" / "2026-11" / "2026-11-09" / "SgLang" / "nightly-test-npu.yml"
doc = json.loads((base / "pipeline.json").read_text(encoding="utf-8"))
out = []
for rec in doc.get("records") or []:
    out.append("RID=%s status=%s ftt=%r runId=%r" % (
        rec.get("recordId"), rec.get("status"), rec.get("failedTaskType"), rec.get("pipelineRunId")))
    out.append("  evidence=%s" % json.dumps(rec.get("evidence"), ensure_ascii=False)[:1500])
    out.append("  verdict=%s" % json.dumps(rec.get("verdict"), ensure_ascii=False)[:400])
    em = rec.get("errorMessages") or []
    out.append("  errorMessages n=%d" % len(em))
    for e in em[:4]:
        out.append("    %s" % json.dumps(e, ensure_ascii=False)[:300])
    out.append("")
Path(ROOT / "out" / "state" / "_sg_ev.txt").write_text("\n".join(out), encoding="utf-8")
print("ok")
