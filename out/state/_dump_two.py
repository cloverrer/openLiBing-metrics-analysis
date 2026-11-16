# -*- coding: utf-8 -*-
"""dump 可疑组件在 _day.json 的原始条目 + 磁盘目录（核对身份漂移/重复）。"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days, iter_archive_pipelines
from lib import pipeline_doc

WATCH = {"openUBMC", "MindCluster"}
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    print("### %s" % date)
    for e in day.get("pipelines") or []:
        if e.get("component") in WATCH:
            print("  DAY  %-12s key=%-40s pid=%s name=%s platform=%s run=%s recs=%s dims=%s" % (
                e.get("component"), e.get("key"), (e.get("pipelineId") or "-")[:8],
                e.get("pipelineName"), e.get("platform"), e.get("runsInPeriod"),
                e.get("records"), e.get("dims")))
    for comp, pname_dir, pdir in iter_archive_pipelines(day_dir):
        if comp not in WATCH:
            continue
        d = pipeline_doc.load(pdir) or {}
        pl = ((d.get("steps") or {}).get("step_1_lights") or {}).get("pipeline") or {}
        print("  DISK %-12s dir=%-24s pid=%s name=%s recs=%d" % (
            comp, pname_dir, (pl.get("pipelineId") or "-")[:8], pl.get("pipelineName"),
            len(d.get("records") or [])))
