# -*- coding: utf-8 -*-
"""模拟首页「执行记录」弹窗的取数：逐日读 _day.json -> pipeline.json -> step_2_runs.runHistory，
按结束日过滤 + 按 rn 去重，统计每条流水线在区间内会展示的运行。"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "out", "archive", "2026", "2026-11")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    frm, to = sys.argv[1], sys.argv[2]
    only = sys.argv[3] if len(sys.argv) > 3 else None
    days = [d for d in sorted(os.listdir(ARCH)) if frm <= d <= to]
    seen = {}
    out = {}
    for d in days:
        dj = os.path.join(ARCH, d, "_day.json")
        if not os.path.exists(dj):
            continue
        day = load(dj)
        for pl in day.get("pipelines", []):
            if only and only not in (pl.get("component") or ""):
                continue
            key = (pl.get("component") or "") + "|" + str(pl.get("pipelineId") or pl.get("pipeline"))
            path = pl.get("path")
            if not path:
                continue
            pj = os.path.join(ROOT, "out", path.lstrip("/"), "pipeline.json")
            pj = pj.replace("out\\archive", "out\\archive")
            if not os.path.exists(pj):
                continue
            pp = load(pj)
            rh = (((pp.get("steps") or {}).get("step_2_runs") or {}).get("runHistory")) or []
            ent = out.setdefault(key, {"name": pl.get("pipelineName"), "comp": pl.get("component"),
                                       "runs": []})
            for h in rh:
                rn = str(h.get("rn"))
                k = key + "|" + rn
                if not rn or rn == "undefined" or k in seen:
                    continue
                seen[k] = 1
                end = str(h.get("end") or "")
                dy = end[:10]
                if dy and (dy < frm or dy > to):
                    continue
                ent["runs"].append({"rn": h.get("rn"), "status": h.get("status"),
                                    "end": end, "iva": h.get("iva")})
    for key, ent in out.items():
        runs = ent["runs"]
        bad = [r for r in runs if str(r["status"]).upper() in ("FAILED", "FAILURE", "CANCELED", "ABORTED")]
        print("%-46s %-26s 运行 %-3d 失败/取消/中止 %-3d %s"
              % (key, ent["name"], len(runs), len(bad),
                 "" if bad else ("<-- 一条失败都没有" if runs else "<-- 无运行历史")))


if __name__ == "__main__":
    main()
