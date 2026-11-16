# -*- coding: utf-8 -*-
"""模拟页面组件级口径：按区间逐日累加流水线级 va/bsDetail，列出非 100% 的组件。"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days  # noqa: E402

RANGE = ("2026-11-10", "2026-11-13")

# 逐日读 _day.json
pipes = {}   # (comp, pipelineId|pipeline) -> dict
comp = defaultdict(lambda: {"vaVals": [], "bsP": 0, "bsC": 0, "vaA": 0, "vaN": 0})
for d, ddir in iter_archive_days():
    if not (RANGE[0] <= d <= RANGE[1]):
        continue
    p = ddir / "_day.json"
    if not p.is_file():
        continue
    doc = json.loads(p.read_text(encoding="utf-8"))
    for pl in doc.get("pipelines") or []:
        k = (pl.get("component"), pl.get("pipelineId") or pl.get("pipeline"))
        pipes.setdefault(k, {"dims": set(), "bsP": 0, "bsC": 0, "vaA": 0, "vaN": 0,
                             "days": set()})
        r = pipes[k]
        for x in pl.get("dims") or []:
            r["dims"].add(x)
        vd = pl.get("vaDetail") or {}
        bd = pl.get("bsDetail") or {}
        if (vd.get("daysInPeriod") or 0) > 0:
            r["vaA"] += vd.get("availDays") or 0
            r["vaN"] += vd.get("daysInPeriod") or 0
        if (bd.get("buildCount") or 0) > 0:
            r["bsP"] += bd.get("buildPassCount") or 0
            r["bsC"] += bd.get("buildCount") or 0
        r["days"].add(d)

# 组件级：va = 各 va 流水线 vaRate 平均（分母为区间工作日数这里用 vaN 近似）；bs = ΣP/ΣC
wdcnt = 4
agg = defaultdict(lambda: {"va": [], "bsP": 0, "bsC": 0, "pipes": 0})
for (c, _pid), r in pipes.items():
    a = agg[c]
    a["pipes"] += 1
    if "va" in r["dims"]:
        va = min(1.0, r["vaA"] / wdcnt) if wdcnt else None
        a["va"].append(va)
    if "bs" in r["dims"]:
        if r["bsC"] > 0:
            a["bsP"] += r["bsP"]
            a["bsC"] += r["bsC"]

print("区间 %s ~ %s（逐日累加口径）" % RANGE)
for c in sorted(agg):
    a = agg[c]
    va = sum(a["va"]) / len(a["va"]) if a["va"] else None
    bs = (a["bsP"] / a["bsC"]) if a["bsC"] else None
    flag = ""
    if va is not None and va < 0.9999:
        flag += "  <= VA<100%"
    if bs is not None and bs < 0.9999:
        flag += "  <= BS<100%"
    print("  %-18s VA=%s  BS=%s%s" % (
        c,
        "--" if va is None else "%.2f%%" % (va * 100),
        "--" if bs is None else "%.2f%% (Σ%d/Σ%d)" % (bs * 100, a["bsP"], a["bsC"]),
        flag))
