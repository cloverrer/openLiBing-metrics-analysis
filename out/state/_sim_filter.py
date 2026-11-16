# -*- coding: utf-8 -*-
"""临时：复刻 step_9 页面侧记录级维度过滤，统计各维度将展示的失败记录。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
from lib.paths import iter_archive_days

FAIL = {"FAILED", "CANCELED", "CANCELLED"}


def main():
    per_dim = {"va": [], "bs": [], "none": []}
    nrec = 0
    for d, day_dir in iter_archive_days():
        dj = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
        plIdx = {}
        for p in dj.get("pipelines") or []:
            nm = p.get("pipelineName") or p.get("pipeline") or ""
            plIdx[d + "|" + nm] = p
        for comp in sorted(day_dir.iterdir()):
            if not comp.is_dir() or comp.name.startswith("_"):
                continue
            for pipe in sorted(comp.iterdir()):
                if not pipe.is_dir():
                    continue
                doc = pipeline_doc.load(pipe) or {}
                runs = ((doc.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
                runBy = {}
                for h in runs:
                    runBy[str(h.get("rn"))] = h
                for rec in doc.get("records") or []:
                    if str(rec.get("status") or "").upper() not in FAIL:
                        continue
                    nrec += 1
                    nm = pipe.name
                    # 页面 plName 来自 _day.json 条目
                    pl = None
                    for k, v in plIdx.items():
                        if k.startswith(d + "|") and (v.get("pipeline") == pipe.name
                                                      or v.get("pipelineName") == pipe.name):
                            pl = v
                    if pl is None:
                        # 退化：直接按目录名匹配
                        for p in dj.get("pipelines") or []:
                            if p.get("path", "").endswith(comp.name + "/" + pipe.name):
                                pl = p
                    pl = pl or {}
                    ds = pl.get("dims") or []
                    vd = pl.get("vaDetail") or {}
                    run = runBy.get(str(rec.get("buildNumber"))) or {}
                    aff = []
                    if "va" in ds and vd.get("availDays") != 1:
                        aff.append("va")
                    if "bs" in ds and isinstance(run.get("bc"), int) and isinstance(run.get("bpc"), int) \
                            and run["bc"] > 0 and run["bpc"] < run["bc"]:
                        aff.append("bs")
                    tag = (d, comp.name, pipe.name, rec.get("buildNumber"), aff)
                    if not aff:
                        per_dim["none"].append(tag)
                    for x in aff:
                        per_dim[x].append(tag)
    print("失败/取消记录总数 %d" % nrec)
    for k in ("va", "bs", "none"):
        print("--- %s: %d" % (k, len(per_dim[k])))
        for t in per_dim[k]:
            print("    ", t)


if __name__ == "__main__":
    main()
