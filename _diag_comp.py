# -*- coding: utf-8 -*-
"""按组件打印「归档口径」的逐日运行矩阵：每天有哪些运行、状态、iva、所在维度。

用于回答两类问题：
  1) 某组件某天三条流水线没有版本可用，为什么组件级仍显示 100%（是无运行被排除，还是跑了但可用）
  2) 某组件执行记录弹窗里为什么看不到失败（失败是否落在当天有其他运行成功的日子里 → 日粒度点灯为绿）

用法: python _diag_comp.py <组件名前缀> [from] [to]
"""
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
    pref = sys.argv[1] if len(sys.argv) > 1 else ""
    frm = sys.argv[2] if len(sys.argv) > 2 else "2026-11-10"
    to = sys.argv[3] if len(sys.argv) > 3 else "2026-11-16"
    pipe_of = {}
    for d in sorted(os.listdir(ARCH)):
        if not (frm <= d <= to):
            continue
        dj = os.path.join(ARCH, d, "_day.json")
        if not os.path.exists(dj):
            continue
        day = load(dj)
        for pl in day.get("pipelines", []):
            comp = pl.get("component") or ""
            if pref and pref.lower() not in comp.lower():
                continue
            k = (comp, str(pl.get("pipelineId") or pl.get("pipeline")), d)
            pipe_of.setdefault((comp, str(pl.get("pipelineId") or pl.get("pipeline"))),
                               {"name": pl.get("pipelineName"), "days": {}})
            pipe_of[(comp, str(pl.get("pipelineId") or pl.get("pipeline")))]["days"][d] = pl
    for (comp, pid), ent in sorted(pipe_of.items()):
        print("=" * 100)
        print("%s  %s  (%s)" % (comp, ent["name"], pid))
        print("  %-12s %-10s %-9s %-9s %s" % ("日期", "rateRule", "可用日", "分母", "当天运行"))
        for d in sorted(ent["days"]):
            pl = ent["days"][d]
            vd = pl.get("vaDetail") or {}
            rh = []
            pj = os.path.join(ROOT, "out", str(pl.get("path") or ""), "pipeline.json")
            if os.path.exists(pj):
                pp = load(pj)
                for h in (((pp.get("steps") or {}).get("step_2_runs") or {}).get("runHistory")) or []:
                    if str(h.get("end") or "")[:10] == d:
                        rh.append("#%s %s iva=%s" % (h.get("rn"), h.get("status"), h.get("iva")))
            print("  %-12s %-10s %-9s %-9s %s" % (
                d, pl.get("rateRule"), vd.get("availDays"), vd.get("daysInPeriod"),
                " | ".join(rh) or "（无运行结束于当天）"))


if __name__ == "__main__":
    main()
