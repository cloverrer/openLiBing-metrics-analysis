# -*- coding: utf-8 -*-
"""临时：抽样核对失败记录的 light 字段 + 当日口径 + 对应运行 bc/bpc/iva。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
from lib.paths import iter_archive_days

FAIL = {"FAILED", "CANCELED", "CANCELLED"}


def main():
    n = 0
    for d, day_dir in iter_archive_days():
        dj = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
        pl_by_path = {p.get("path"): p for p in dj.get("pipelines") or []}
        for comp in sorted(day_dir.iterdir()):
            if not comp.is_dir() or comp.name.startswith("_"):
                continue
            for pipe in sorted(comp.iterdir()):
                if not pipe.is_dir():
                    continue
                doc = pipeline_doc.load(pipe) or {}
                runs = ((doc.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
                run_by_rn = {str(h.get("rn")): h for h in runs}
                for rec in doc.get("records") or []:
                    if str(rec.get("status") or "").upper() not in FAIL:
                        continue
                    n += 1
                    if n > 6:
                        return
                    pl = None
                    for p in dj.get("pipelines") or []:
                        if p.get("path", "").endswith(comp.name + "/" + pipe.name):
                            pl = p
                    rn = str(rec.get("buildNumber"))
                    h = run_by_rn.get(rn) or {}
                    print("--- %s %s/%s #%s" % (d, comp.name, pipe.name, rn))
                    print("   status=%s  light=%s" % (rec.get("status"),
                          json.dumps(rec.get("light") or {}, ensure_ascii=False)))
                    print("   rec.buildNumber=%r  run.rn=%r  run.bc=%r run.bpc=%r run.iva=%r"
                          % (rec.get("buildNumber"), h.get("rn"), h.get("bc"), h.get("bpc"),
                             h.get("iva")))
                    if pl:
                        print("   day.vaDetail=%s  day.bsDetail=%s  dims=%s"
                              % (json.dumps(pl.get("vaDetail") or {}),
                                 json.dumps(pl.get("bsDetail") or {}), pl.get("dims")))
                    else:
                        print("   !! 未匹配到 _day.json 的 pipeline 条目")


if __name__ == "__main__":
    main()
