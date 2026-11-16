# -*- coding: utf-8 -*-
"""按首页 render() 的口径重算组件级 VA/BS，用于核对首页数值。"""
import json
from pathlib import Path

root = Path("out/archive/2026/2026-11")
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"]


def load(day):
    return json.loads((root / day / "_day.json").read_text(encoding="utf-8"))


def comp(days, label):
    pipes = {}
    prods = {}
    for day in days:
        d = load(day)
        for p in d.get("pipelines") or []:
            r = pipes.setdefault(p["key"], {"key": p["key"], "component": p["component"], "dims": set(),
                                            "vaA": 0, "vaN": 0, "bsP": 0, "bsC": 0})
            r["dims"].update(p.get("dims") or [])
            vd = p.get("vaDetail") or {}
            if float(vd.get("daysInPeriod") or 0) > 0:
                r["vaA"] += float(vd.get("availDays") or 0)
                r["vaN"] += float(vd.get("daysInPeriod") or 0)
            bd = p.get("bsDetail") or {}
            if float(bd.get("buildCount") or 0) > 0:
                r["bsP"] += float(bd.get("buildPassCount") or 0)
                r["bsC"] += float(bd.get("buildCount") or 0)
        for pr in d.get("products") or []:
            prods.setdefault(pr["product"], {})[day] = pr
    print("=" * 70)
    print("RANGE", label)
    byc = {}
    for k, r in pipes.items():
        byc.setdefault(r["component"], []).append(r)
    for c in sorted(byc):
        rs = byc[c]
        vaVals, bsVals = [], []
        vaD = ""
        for r in rs:
            if "va" in r["dims"] and r["vaN"] > 0:
                v = r["vaA"] / r["vaN"]
                vaVals.append(v)
                if v < 1:
                    vaD += "  <%s %.4f (%g/%g)>" % (r["key"], v, r["vaA"], r["vaN"])
            if "bs" in r["dims"] and r["bsC"] > 0:
                bsVals.append(r["bsP"] / r["bsC"])
        va = sum(vaVals) / len(vaVals) if vaVals else None
        bs = sum(bsVals) / len(bsVals) if bsVals else None
        print("%-22s VA=%s (%d pipes) BS=%s%s" % (
            c, "--" if va is None else "%.4f" % va, len(vaVals),
            "--" if bs is None else "%.4f" % bs, vaD))


comp(DAYS, "11-06 ~ 11-12 (默认近7天)")
comp(["2026-11-10"], "11-10 ~ 11-10")
comp(["2026-11-12"], "11-12 ~ 11-12")
comp(["2026-11-11"], "11-11 ~ 11-11")
