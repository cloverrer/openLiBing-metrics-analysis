# -*- coding: utf-8 -*-
"""探针：MindCluster 各归档日流水线灯态与运行历史。"""
import io
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "out", "archive", "2026", "2026-11")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    comp = "MindCluster"
    runs_by = {}
    for d in sorted(os.listdir(ARCH)):
        day_dir = os.path.join(ARCH, d)
        if not os.path.isdir(day_dir):
            continue
        dj = os.path.join(day_dir, "_day.json")
        if not os.path.isfile(dj):
            continue
        day = load(dj)
        print("\n== %s ==" % d)
        for pl in day.get("pipelines", []):
            if pl.get("component") != comp:
                continue
            print("   %-45s dims=%s va=%s bs=%s runsInPeriod=%s runsToday=%s vaRate=%s" % (
                pl.get("pipelineName") or pl.get("pipeline"), pl.get("dims"),
                pl.get("vaDetail"), pl.get("bsDetail"), pl.get("runsInPeriod"),
                pl.get("runsToday"), pl.get("vaRate")))
            pj = os.path.join(ROOT, "out", "archive", "2026", "2026-11", d,
                              comp, pl.get("pipeline"), "pipeline.json")
            if os.path.isfile(pj):
                j = load(pj)
                rh = ((j.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
                for h in rh:
                    print("        rn=%s %s %s -> %s iva=%s bc=%s bpc=%s" % (
                        h.get("rn"), h.get("status"), h.get("start"), h.get("end"),
                        h.get("iva"), h.get("bc"), h.get("bpc")))


if __name__ == "__main__":
    main()
