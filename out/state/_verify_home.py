# -*- coding: utf-8 -*-
"""临时核对：首页区间 union 流水线数 vs 当前采集清单。"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ARC = ROOT / "out" / "archive" / "2026" / "2026-11"

days = ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]
keys = collections.defaultdict(lambda: {"keys": {}, "nokey": []})
for d in days:
    p = ARC / d / "_day.json"
    if not p.exists():
        continue
    doc = json.loads(p.read_text(encoding="utf-8"))
    for pl in doc.get("pipelines") or []:
        comp = pl.get("component")
        rec = keys[comp]
        k = pl["key"]
        if k not in rec["keys"]:
            rec["keys"][k] = {"pipelineId": None, "dir": pl.get("pipeline"),
                              "name": pl.get("pipelineName"), "platform": pl.get("platform"),
                              "days": [], "runsInPeriod": pl.get("runsInPeriod")}
        rec["keys"][k]["days"].append(d + ":" + str(pl.get("runsToday")))

# 采集清单（11-13）
cur = json.loads((ROOT / "out" / "work" / "step_1_bad_pipelines.json").read_text(encoding="utf-8"))
cur_cnt = collections.Counter(p["product"] for p in cur["pipelines"])
cur_ids = collections.defaultdict(set)
for p in cur["pipelines"]:
    cur_ids[p["product"]].add(str(p.get("pipelineId")))

print("%-18s %6s %6s  %s" % ("组件", "采集", "首页", "差异"))
for comp in sorted(keys):
    ks = keys[comp]["keys"]
    n = len(ks)
    c = cur_cnt.get(comp, 0)
    flag = "" if n == c else "  <== 不一致"
    print("%-18s %6d %6d%s" % (comp, c, n, flag))
    if n != c:
        for k, v in ks.items():
            print("      %-46s %s" % (k, v["days"]))

extra = sorted(set(cur_cnt) - set(keys))
for comp in extra:
    print("%-18s %6d %6d  <== 归档完全缺失" % (comp, cur_cnt[comp], 0))
