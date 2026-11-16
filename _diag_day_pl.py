# -*- coding: utf-8 -*-
"""打印指定流水线在各归档日的 _day.json 明细（va/bs 比率与 detail）。"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pipeline", required=True)
ap.add_argument("--component")
args = ap.parse_args()

for d, ddir in iter_archive_days():
    p = ddir / "_day.json"
    if not p.is_file():
        continue
    doc = json.loads(p.read_text(encoding="utf-8"))
    for pl in doc.get("pipelines") or []:
        name = str(pl.get("pipeline") or pl.get("pipelineShortName") or "")
        comp = str(pl.get("component") or pl.get("product") or "")
        if args.pipeline and args.pipeline not in name:
            continue
        if args.component and args.component != comp:
            continue
        print("== %s  %s / %s" % (d, comp, name))
        for k in ("versionAvailabilityRate", "buildSuccessRate", "dims",
                  "vaDetail", "bsDetail", "workdays", "availDays"):
            if k in pl:
                print("   %s = %s" % (k, json.dumps(pl[k], ensure_ascii=False)))
