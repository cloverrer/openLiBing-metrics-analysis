# -*- coding: utf-8 -*-
"""核对 _day.json 与 pipeline.json 的 records / runHistory 是否跨日（单日筛选泄漏根因）。"""
import json
from pathlib import Path

ROOT = Path("out/archive/2026/2026-11")
for day in ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"]:
    dj = json.loads((ROOT / day / "_day.json").read_text(encoding="utf-8"))
    print("=== %s  _day.json: pipelines=%d ===" % (day, len(dj.get("pipelines") or [])))
    for p in (dj.get("pipelines") or []):
        if p["component"] != "HPCKit" or p.get("pipeline") != "kudnn":
            continue
        pj = json.loads((ROOT / day / "HPCKit" / "kudnn" / "pipeline.json").read_text(encoding="utf-8"))
        print("  pipeline.json keys:", list(pj.keys()))
        recs = pj.get("records") or []
        print("  _day: records=%s  pipeline.records=%d" % (p.get("records"), len(recs)))
        days_of_recs = sorted(set(str((r.get("endedAt") or ""))[:10] for r in recs))
        print("  records 结束日:", days_of_recs)
        print("  records buildNumber:", [r.get("buildNumber") for r in recs])
        runs = pj.get("runs") or []
        rdays = sorted(set(str((r.get("end") or ""))[:10] for r in runs))
        print("  runs=%d  运行结束日跨度:" % len(runs), rdays)
        print("  runs rn:", [r.get("rn") for r in runs])
        break
