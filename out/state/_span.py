# -*- coding: utf-8 -*-
"""检查 out/work 原始采集覆盖的日期范围（runHistory / records），判断能否重跑 step_7。"""
import json, sys
from pathlib import Path
from collections import Counter
ROOT = Path(__file__).resolve().parent.parent.parent
WORK = ROOT / "out" / "work"

s2 = json.loads((WORK / "step_2_failed_runs.json").read_text(encoding="utf-8"))
cd = Counter()
for key, info in s2.items():
    for h in (info.get("runHistory") or []):
        e = (h.get("end") or "")[:10]
        if e:
            cd[e] += 1
print("step_2 runHistory end 日期分布:", dict(sorted(cd.items())))
print("step_2 pipelines:", len(s2), " _meta.workdays:", (s2.get("_meta") or {}).get("workdayCount"))

s6 = json.loads((WORK / "step_6_records.json").read_text(encoding="utf-8"))
rd = Counter()
for r in s6.get("records") or []:
    rd[str(r.get("date"))[:10]] += 1
print("step_6 records 日期分布:", dict(sorted(rd.items())), " 总:", len(s6.get("records") or []))

s1b = json.loads((WORK / "step_1_bad_pipelines.json").read_text(encoding="utf-8"))
print("step_1 dateRange:", json.dumps(s1b.get("dateRange"), ensure_ascii=False))
sn = [(b["product"], b.get("pipelineShortName"), str(b.get("pipelineId"))[:8]) for b in s1b.get("pipelines") or []]
print("openUBMC/MindCluster 短名:")
for p, s, i in sn:
    if p in ("openUBMC", "MindCluster"):
        print("   %-12s %-22s %s" % (p, s, i))
