# -*- coding: utf-8 -*-
"""按首页口径(cap wdN)重算全 11 月组件级 VA/BS，核对用户预期。"""
import json, collections
from pathlib import Path

ROOT = Path("out/archive/2026/2026-11")
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"]
WD = len(DAYS)


def load(day):
    return json.loads((ROOT / day / "_day.json").read_text(encoding="utf-8"))


pipes = {}
for day in DAYS:
    d = load(day)
    for p in d.get("pipelines") or []:
        r = pipes.setdefault(p["key"], {"key": p["key"], "component": p["component"],
                                        "pipeline": p.get("pipelineName") or p.get("pipeline"),
                                        "dims": set(), "vaA": 0, "vaN": 0,
                                        "bsP": 0, "bsC": 0})
        for x in p.get("dims") or []:
            r["dims"].add(x)
        vd = p.get("vaDetail") or {}
        if float(vd.get("daysInPeriod") or 0) > 0:
            r["vaA"] += float(vd.get("availDays") or 0)
            r["vaN"] += float(vd.get("daysInPeriod") or 0)
        bd = p.get("bsDetail") or {}
        if float(bd.get("buildCount") or 0) > 0:
            r["bsP"] += float(bd.get("buildPassCount") or 0)
            r["bsC"] += float(bd.get("buildCount") or 0)

# pipeline rate
for r in pipes.values():
    noVA = not (r["vaN"] > 0)
    noBS = not (r["bsC"] > 0)
    r["noRun"] = noVA and noBS
    r["vaRate"] = None if noVA else min(1, r["vaA"] / WD)
    r["bsRate"] = None if noBS else (r["bsP"] / r["bsC"] if r["bsC"] else None)

comp = collections.defaultdict(lambda: {"va": [], "pipes": 0, "pipesVA": 0})
for r in pipes.values():
    c = comp[r["component"]]
    c["pipes"] += 1
    if "va" in r["dims"] and r["vaRate"] is not None:
        c["va"].append(r["vaRate"])
        c["pipesVA"] += 1

print("=== 组件级版本可用度（首页口径：各流水线 vaRate 算术平均） ===")
for name in sorted(comp):
    c = comp[name]
    avg = (sum(c["va"]) / len(c["va"]) * 100) if c["va"] else None
    print("%-18s VA=%s  (统计 %d/%d 条流水线)" % (
        name, "--" if avg is None else "%.2f%%" % avg, c["pipesVA"], c["pipes"]))

print()
print("=== HPCKit 各流水线明细 ===")
for r in sorted(pipes.values(), key=lambda x: x["pipeline"] or ""):
    if r["component"] != "HPCKit":
        continue
    print("  %-46s dims=%s vaA=%s/%s vaRate=%s bsP=%s/%s" % (
        r["pipeline"], ",".join(sorted(r["dims"])), r["vaA"], r["vaN"],
        "--" if r["vaRate"] is None else "%.2f%%" % (r["vaRate"] * 100), r["bsP"], r["bsC"]))

print()
print("=== 逐日 _day.json 里 HPCKit 的 vaDetail（按流水线） ===")
for day in DAYS:
    d = load(day)
    for p in d.get("pipelines") or []:
        if p["component"] != "HPCKit":
            continue
        vd = p.get("vaDetail") or {}
        print("  %s %-46s daysInPeriod=%s availDays=%s vaRate=%s" % (
            day, p.get("pipelineName"), vd.get("daysInPeriod"), vd.get("availDays"), p.get("vaRate")))
