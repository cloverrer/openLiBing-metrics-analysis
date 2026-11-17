# -*- coding: utf-8 -*-
"""模拟页面组件级版本可用度：读 _day.json，按 page 口径（逐日 vaA/vaN 累加、
无运行流水线排除、分母=该流水线在区间内有执行记录的天数 vaN，缺 vaDetail 才退回 wdN）
算每个组件在区间内的可用度。"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
ARCH = os.path.join(ROOT, "out", "archive", "2026", "2026-11")
from lib.workdays import build_workday_set  # noqa: E402


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    frm, to = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else None
    try:
        wd = build_workday_set(frm, to)[0]
    except Exception:  # noqa: BLE001
        wd = set()
    wdN = len([d for d in wd if frm <= d <= to])
    print("区间 %s~%s  法定工作日数 wdN=%d %s" % (frm, to, wdN, sorted(wd)))
    days = [d for d in sorted(os.listdir(ARCH)) if frm <= d <= to]
    pipes = {}
    for d in days:
        dj = os.path.join(ARCH, d, "_day.json")
        if not os.path.exists(dj):
            continue
        day = load(dj)
        for pl in day.get("pipelines", []):
            mk = (pl.get("component") or "") + "|" + str(pl.get("pipelineId") or pl.get("pipeline"))
            r = pipes.setdefault(mk, {"comp": pl.get("component"), "name": pl.get("pipelineName"),
                                      "rule": "", "dims": set(), "vaA": 0, "vaN": 0,
                                      "vaVals": [], "bsP": 0, "bsC": 0, "days": []})
            if pl.get("rateRule"):
                r["rule"] = pl["rateRule"]
            for x in (pl.get("dims") or []):
                r["dims"].add(x)
            vd = pl.get("vaDetail") or {}
            r["days"].append((d, vd.get("availDays"), vd.get("daysInPeriod")))
            if vd and (vd.get("daysInPeriod") or 0) > 0:
                r["vaA"] += int(vd.get("availDays") or 0)
                r["vaN"] += int(vd.get("daysInPeriod") or 0)
            bd = pl.get("bsDetail") or {}
            r["bsP"] += int(bd.get("buildPassCount") or 0)
            r["bsC"] += int(bd.get("buildCount") or 0)
    bycomp = {}
    for mk, r in pipes.items():
        if only and only not in (r["comp"] or ""):
            continue
        bycomp.setdefault(r["comp"], []).append((mk, r))
    for comp, items in sorted(bycomp.items()):
        print("=== %s ===" % comp)
        vals = []
        for mk, r in items:
            if "va" not in r["dims"]:
                continue
            no_run = not (r["vaN"] > 0 or r["vaVals"])
            den = r["vaN"] if r["vaN"] > 0 else wdN   # 分母=有执行记录的天数，缺 vaDetail 才退回工作日数
            if no_run:
                print("   %-56s 无执行记录(排除) 逐日=%s" % (r["name"], r["days"]))
                continue
            rate = (r["vaA"] / float(den)) if (den and den > 0) else None
            if rate is not None:
                vals.append(rate)
            print("   %-56s vaA=%s vaN=%s rule=%s -> %s  逐日=%s"
                  % (r["name"], r["vaA"], r["vaN"], r["rule"],
                     ("%.1f%%" % (100 * rate)) if rate is not None else "--", r["days"]))
        if vals:
            print("   组件级 = %s (%d 条)" % ("%.1f%%" % (100 * sum(vals) / len(vals)), len(vals)))
        print()


if __name__ == "__main__":
    main()
