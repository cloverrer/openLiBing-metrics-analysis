# -*- coding: utf-8 -*-
"""诊断：逐日对比 _day.json.pipelines[] 里的社区条目 vs 磁盘上的社区 pipeline.json。"""
import io
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "out", "archive", "2026", "2026-11")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    for d in sorted(os.listdir(ARCH)):
        day_dir = os.path.join(ARCH, d)
        dj = os.path.join(day_dir, "_day.json")
        if not os.path.isfile(dj):
            continue
        day = load(dj)
        in_day = {}
        for pl in day.get("pipelines", []):
            if pl.get("channel") == "community":
                in_day[pl.get("key")] = pl
        on_disk = {}
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
                try:
                    j = load(pj)
                except ValueError:
                    continue
                if j.get("channel") == "community":
                    on_disk["%s|%s" % (comp, pipe)] = j.get("pipelineName")
        miss = [k for k in on_disk if k not in in_day]
        extra = [k for k in in_day if k not in on_disk]
        if on_disk or in_day:
            print("%s  磁盘社区条目 %d / _day.json 社区条目 %d" % (d, len(on_disk), len(in_day)))
            for k in miss:
                print("    !! 磁盘有、_day.json 缺失: %s (%s)" % (k, on_disk[k]))
            for k in extra:
                print("    !! _day.json 有、磁盘无: %s" % k)


if __name__ == "__main__":
    main()
