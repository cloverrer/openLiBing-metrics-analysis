# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
arch = ROOT / "out" / "archive" / "2026" / "2026-11"


def dump(day, comp):
    p = arch / day / "_day.json"
    d = json.loads(p.read_text(encoding="utf-8-sig"))
    print("==", day, comp)
    for pl in d.get("pipelines") or []:
        if pl.get("component") != comp:
            continue
        print("   pipeline=%s | name=%s | id=%s | platform=%s"
              % (pl.get("pipeline"), pl.get("pipelineName"), pl.get("pipelineId"), pl.get("platform")))
        print("      path=%s" % pl.get("path"))


for day in ("2026-11-12", "2026-11-13"):
    dump(day, "openUBMC")
dump("2026-11-13", "Ascend-CANN")
for day in ("2026-11-12", "2026-11-13"):
    dump(day, "Agentsdk")
