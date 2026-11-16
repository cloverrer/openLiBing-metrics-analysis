# -*- coding: utf-8 -*-
"""看 openUBMC / MindCluster 各流水线逐日的 vaDetail/bsDetail（核对首页比率成因）。"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days

WATCH = ("openUBMC", "MindCluster")
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    for e in day.get("pipelines") or []:
        if e.get("component") not in WATCH:
            continue
        vd = e.get("vaDetail") or {}
        bd = e.get("bsDetail") or {}
        print("%s %-12s %-22s pid=%s va=%s/%s bs=%s/%s dims=%s run=%s" % (
            date, e.get("component"), e.get("pipeline"), (e.get("pipelineId") or "-")[:8],
            vd.get("availDays"), vd.get("daysInPeriod"),
            bd.get("buildPassCount"), bd.get("buildCount"),
            e.get("dims"), e.get("runsInPeriod")))
