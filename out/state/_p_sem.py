# -*- coding: utf-8 -*-
import json
from pathlib import Path

root = Path("out/archive/2026/2026-11")
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"]
pdoc = json.loads((root / "2026-11-10" / "pipeline.json").read_text(encoding="utf-8")) if False else None

watch = ["HPCKit|kupl", "HPCKit|kudnn", "Ascend-CANN|ops-transformer", "boostkit|"]
for day in DAYS:
    d = json.loads((root / day / "_day.json").read_text(encoding="utf-8"))
    print("=" * 90)
    print("DAY", day, " dateRange=", d.get("dateRange"), " workdays=", d.get("workdays"), d.get("workdayCount"))
    for p in d.get("pipelines") or []:
        if any(p["key"].startswith(w) or w in p["key"] for w in watch):
            print("  %-40s dims=%-10s va=%s vaDetail=%s bs=%s bsDetail=%s runsInPeriod=%s runsToday=%s failedToday=%s" % (
                p["key"], ",".join(p.get("dims") or []), p.get("vaRate"), p.get("vaDetail"),
                p.get("bsRate"), p.get("bsDetail"), p.get("runsInPeriod"), p.get("runsToday"),
                p.get("failedRunsToday")))
