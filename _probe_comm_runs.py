# -*- coding: utf-8 -*-
"""探针：列出社区流水线在归档窗口内的全部运行（跨天合并），以及各归档日已有的 vaDetail。"""
import io
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "out", "archive", "2026", "2026-11")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    days = sorted(d for d in os.listdir(ARCH) if os.path.isdir(os.path.join(ARCH, d)) and d[:1].isdigit())
    print("归档日:", days)
    runs_by = {}
    for d in days:
        day_dir = os.path.join(ARCH, d)
        for comp in sorted(os.listdir(day_dir)):
            if comp.startswith("_"):
                continue
            cpath = os.path.join(day_dir, comp)
            if not os.path.isdir(cpath):
                continue
            for pipe in sorted(os.listdir(cpath)):
                pj = os.path.join(cpath, pipe, "pipeline.json")
                if not os.path.isfile(pj):
                    continue
                j = load(pj)
                if j.get("channel") != "community":
                    continue
                k = j.get("key")
                rh = ((j.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
                acc = runs_by.setdefault(k, {})
                for h in rh:
                    acc[h["rn"]] = (h.get("status"), h.get("start"), h.get("end"), h.get("iva"))
    for k in sorted(runs_by):
        print("\n==", k)
        for rn in sorted(runs_by[k]):
            st, s, e, iva = runs_by[k][rn]
            print("   rn=%s %s %s -> %s iva=%s" % (rn, st, s, e, iva))
    print("\n---- 各归档日 _day.json 社区条目 ----")
    for d in days:
        dj = os.path.join(ARCH, d, "_day.json")
        if not os.path.isfile(dj):
            continue
        day = load(dj)
        for pl in day.get("pipelines", []):
            if pl.get("channel") == "community":
                print("%s  %-60s va=%s bs=%s runsToday=%s note=%s" % (
                    d, pl.get("key"), pl.get("vaDetail"), pl.get("bsDetail"),
                    pl.get("runsToday"), pl.get("note")))


if __name__ == "__main__":
    main()
