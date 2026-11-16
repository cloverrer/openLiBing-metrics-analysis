# -*- coding: utf-8 -*-
"""列出各归档日每个组件下的流水线 key（用于核对首页组件级流水线条数）。"""
import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days

union = defaultdict(dict)   # component -> {key: set(dates)}
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    comps = defaultdict(list)
    for e in day.get("pipelines") or []:
        comps[e.get("component")].append((e.get("key"), e.get("pipelineName"),
                                          e.get("runsInPeriod"), (e.get("pipelineId") or "")[:8]))
        union[e.get("component")][e.get("key")] = union[e.get("component")].get(e.get("key"), set()) | {date}
    print("== %s ==" % date)
    for c in sorted(x for x in comps if x):
        print("   %-14s %2d 条: %s" % (c, len(comps[c]),
              ", ".join("%s(pid=%s,run=%s)" % (k, p, r) for k, n, r, p in comps[c])))
print()
print("======= 区间 union（首页口径）=======")
for c in sorted(union):
    print("%-14s %2d 条" % (c, len(union[c])))
    for k in sorted(union[c]):
        print("      %-40s 出现于 %s" % (k, ",".join(sorted(union[c][k]))))
