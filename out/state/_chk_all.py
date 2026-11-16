# -*- coding: utf-8 -*-
"""按首页口径重算：组件级 VA = 各流水线(可用日/区间工作日) 的算术平均；
组件级 BS = Σ编译通过 / Σ编译次数。逐区间打印，用于和用户预期（11 月只有 HPCKit 80%）核对。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ARCH = ROOT / "out" / "archive" / "2026" / "2026-11"
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12"]


def load_day(d):
    p = ARCH / d / "_day.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def compute(days):
    # pipes[key] = dict
    pipes = {}
    for d in days:
        doc = load_day(d)
        if not doc:
            continue
        for pl in doc.get("pipelines", []):
            r = pipes.setdefault(pl["key"], {"comp": pl["component"], "pipe": pl["pipeline"],
                                             "dims": set(), "vaA": 0, "vaN": 0, "bsP": 0, "bsC": 0})
            for dm in pl.get("dims", []):
                r["dims"].add(dm)
            vd = pl.get("vaDetail") or {}
            if vd.get("daysInPeriod", 0) > 0:
                r["vaA"] += vd.get("availDays", 0)
                r["vaN"] += vd.get("daysInPeriod", 0)
            bd = pl.get("bsDetail") or {}
            if bd.get("buildCount", 0) > 0:
                r["bsP"] += bd.get("buildPassCount", 0)
                r["bsC"] += bd.get("buildCount", 0)
    wd = len(days)  # 全部取工作日
    comps = {}
    for r in pipes.values():
        c = comps.setdefault(r["comp"], {"va": [], "bsP": 0, "bsC": 0, "detail": []})
        va = (r["vaA"] / wd) if ("va" in r["dims"] and r["vaN"] > 0) else None
        if va is not None:
            c["va"].append(va)
        if "bs" in r["dims"] and r["bsC"] > 0:
            c["bsP"] += r["bsP"]
            c["bsC"] += r["bsC"]
        c["detail"].append((r["pipe"], va, r["vaA"], r["vaN"], r["bsP"], r["bsC"]))
    out = {}
    for name, c in comps.items():
        va = sum(c["va"]) / len(c["va"]) if c["va"] else None
        bs = (c["bsP"] / c["bsC"]) if c["bsC"] else None
        out[name] = (va, bs, c["detail"])
    return out


RANGES = [("单日 " + d, [d]) for d in DAYS] + [("全区间 11-06~11-12", DAYS)]
for label, days in RANGES:
    res = compute(days)
    print("=" * 8, label, "工作日", len(days))
    for name in sorted(res, key=lambda n: (res[n][0] is None, res[n][0] if res[n][0] is not None else 9)):
        va, bs, det = res[name]
        vs = "--" if va is None else "%.2f%%" % (va * 100)
        bss = "--" if bs is None else "%.2f%%" % (bs * 100)
        print("  %-22s VA=%-8s BS=%-8s" % (name, vs, bss))
    h = res.get("HPCKit")
    if h:
        print("  [HPCKit 明细]")
        for pipe, va, vaA, vaN, bsP, bsC in sorted(h[2]):
            print("     %-8s VA=%s (%d/%d)  BS=%d/%d" % (
                pipe, "--" if va is None else "%.0f%%" % (va * 100), vaA, vaN, bsP, bsC))
