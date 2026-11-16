# -*- coding: utf-8 -*-
"""临时：核对若干流水线逐日 iva / availDays，确认「当日可用」判定属实。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
from lib.paths import iter_archive_days

WANT = [("SgLang", "nightly-test-npu.yml"), ("vllm-ascend", "a2.yaml")]


def main():
    for d, day_dir in iter_archive_days():
        dj = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
        for comp, pipe in WANT:
            pdir = day_dir / comp / pipe
            if not pdir.is_dir():
                continue
            pl = None
            for p in dj.get("pipelines") or []:
                if p.get("component") == comp and p.get("pipeline") == pipe:
                    pl = p
            doc = pipeline_doc.load(pdir) or {}
            runs = ((doc.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
            today = []
            for h in runs:
                if str(h.get("end") or "")[:10] == d:
                    today.append((h.get("rn"), h.get("status"), h.get("iva"),
                                  h.get("bc"), h.get("bpc"), h.get("cpr")))
            print("== %s %s/%s  vaDetail=%s  当日运行 %d 条"
                  % (d, comp, pipe, json.dumps((pl or {}).get("vaDetail") or {}), len(today)))
            for t in today[:12]:
                print("     rn=%s status=%s iva=%s bc=%s bpc=%s cpr=%s" % t)


if __name__ == "__main__":
    main()
