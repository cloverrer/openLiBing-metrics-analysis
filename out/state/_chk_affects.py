# -*- coding: utf-8 -*-
"""临时：核对归档失败/取消记录的 light.affects 字段现状。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
from lib.paths import iter_archive_days

FAIL = {"FAILED", "CANCELED", "CANCELLED"}


def main():
    miss, has = [], 0
    tot_fail = 0
    for d, p in iter_archive_days():
        day_dir = p
        for comp in sorted(day_dir.iterdir()):
            if not comp.is_dir() or comp.name.startswith("_"):
                continue
            for pipe in sorted(comp.iterdir()):
                if not pipe.is_dir():
                    continue
                doc = pipeline_doc.load(pipe)
                if not doc:
                    continue
                for rec in doc.get("records") or []:
                    st = str(rec.get("status") or "").upper()
                    if st not in FAIL:
                        continue
                    tot_fail += 1
                    lt = rec.get("light") or {}
                    if "affects" in lt:
                        has += 1
                    else:
                        miss.append((d, comp.name, pipe.name,
                                     rec.get("buildNumber"), lt.get("dims")))
    print("失败/取消记录 %d 条；有 affects %d；缺 affects %d" % (tot_fail, has, len(miss)))
    for m in miss[:20]:
        print("  缺:", m)


if __name__ == "__main__":
    main()
