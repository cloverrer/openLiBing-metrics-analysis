# -*- coding: utf-8 -*-
"""从已存的 T4 探测结果里提取失败任务的 jobId/stepId，供 T6/T5 探测使用。"""
import json
from pathlib import Path

p = Path("out/work/_probe_ubs_t4.json")
d = json.loads(p.read_text(encoding="utf-8"))
for det in d.get("details") or []:
    print("== run #%s (%s) rid=%s" % (det.get("rn"), det.get("rstatus"), det.get("rid")))
    for st in (det.get("data") or {}).get("stages") or []:
        for job in st.get("jobs") or []:
            if job.get("status") not in ("FAILED",):
                continue
            bad = [s for s in (job.get("steps") or []) if s.get("status") not in ("COMPLETED", None)]
            print("   job=%-40s id=%s status=%s steps=%s" % (
                job.get("name"), job.get("id"), job.get("status"),
                [(s.get("id"), s.get("status"), s.get("last_dispatch_id")) for s in bad]))
            print("       inputs=%s" % json.dumps(
                [{kv.get("key"): kv.get("value") for kv in (s.get("inputs") or [])} for s in bad],
                ensure_ascii=False)[:400])
