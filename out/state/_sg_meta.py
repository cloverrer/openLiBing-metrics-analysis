# -*- coding: utf-8 -*-
"""只读探针：导出 SgLang 各记录 githubMeta 关键字段。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
base = ROOT / "out" / "archive" / "2026" / "2026-11" / "2026-11-09" / "SgLang" / "nightly-test-npu.yml"
doc = json.loads((base / "pipeline.json").read_text(encoding="utf-8"))
out = []
for rec in doc.get("records") or []:
    gm = rec.get("githubMeta") or {}
    out.append("RID=%s status=%s" % (rec.get("recordId"), rec.get("status")))
    out.append("  keys=%s" % ",".join(sorted(rec.keys())))
    if isinstance(gm, dict):
        out.append("  githubMeta.runId=%s failed=%d cancelled=%d" % (
            gm.get("runId"), len(gm.get("failedJobs") or []), len(gm.get("cancelledJobs") or [])))
        for j in (gm.get("failedJobs") or []):
            out.append("    FAIL %s id=%s steps=%s" % (str(j.get("name"))[:110], j.get("id"),
                       [s.get("name") for s in (j.get("steps") or [])]))
        for j in (gm.get("cancelledJobs") or []):
            out.append("    CXL  %s id=%s" % (str(j.get("name"))[:110], j.get("id")))
    out.append("  runRect=%s" % json.dumps(rec.get("runRect") or rec.get("run") or {}, ensure_ascii=False)[:200])
    out.append("")

Path(ROOT / "out" / "state" / "_sg_meta.txt").write_text("\n".join(out), encoding="utf-8")
print("ok")
