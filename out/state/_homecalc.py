# -*- coding: utf-8 -*-
"""按页面口径（组件 + pipelineId）核对首页流水线条数。"""
import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days

missing = 0
union = defaultdict(dict)   # comp -> {mk: set(dates)}
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    for e in day.get("pipelines") or []:
        pid = e.get("pipelineId")
        if not pid:
            missing += 1
            print("  !! 无 pipelineId: %s %s/%s" % (date, e.get("component"), e.get("pipeline")))
        mk = "%s|%s" % (e.get("component"), pid or e.get("pipeline"))
        d = union[e.get("component")].setdefault(mk, {"dates": set(), "name": e.get("pipeline"),
                                                      "pname": e.get("pipelineName"),
                                                      "plat": e.get("platform"), "run": 0})
        d["dates"].add(date)
        d["run"] += int(e.get("runsInPeriod") or 0)
print("缺 pipelineId 的条目数:", missing)
print()
tot = 0
for c in sorted(union):
    print("%-16s %d 条" % (c, len(union[c])))
    tot += len(union[c])
    for mk in sorted(union[c]):
        d = union[c][mk]
        print("     %-46s plat=%-9s run=%-3d 出现于 %s" % (
            mk, d["plat"], d["run"], ",".join(sorted(d["dates"]))))
print()
print("合计流水线条数:", tot)
