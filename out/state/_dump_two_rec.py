# -*- coding: utf-8 -*-
"""临时：导出 #83 / #183 两条记录的完整字段与证据，用于补根因 / 判定。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
from lib.dim_affects import affects_of, day_avail_of
from lib.paths import ARCHIVE_ROOT

TARGETS = [
    ("2026-11-12", "MindCluster", "MultimodalSDK", 83),
    ("2026-11-12", "Ascend-CANN", "atb", 183),
]


def dump(date, comp, pipe, bn):
    pdir = ARCHIVE_ROOT / date[:4] / date[:7] / date / comp / pipe
    doc = pipeline_doc.load(pdir) or {}
    steps = doc.get("steps") or {}
    dims = ((steps.get("step_1_lights") or {}).get("pipeline") or {}).get("dims") or []
    rh = (steps.get("step_2_runs") or {}).get("runHistory") or []
    print("=" * 70)
    print("%s %s/%s #%s  dims=%s  day_avail=%s" % (date, comp, pipe, bn, dims,
                                                   day_avail_of(rh, date)))
    for h in rh:
        if str(h.get("end"))[:10] == date:
            print("   run rn=%s status=%s iva=%s bc=%s bpc=%s cpr=%s"
                  % (h.get("rn"), h.get("status"), h.get("iva"), h.get("bc"),
                     h.get("bpc"), h.get("cpr")))
    for rec in doc.get("records") or []:
        if str(rec.get("buildNumber")) != str(bn):
            continue
        print("   record status=%s category=%s analysis=%s"
              % (rec.get("status"), (rec.get("verdict") or {}).get("category"),
                 json.dumps(rec.get("analysis") or {}, ensure_ascii=False)[:400]))
        print("   light=%s" % json.dumps(rec.get("light") or {}, ensure_ascii=False))
        print("   failedTaskType=%s" % rec.get("failedTaskType"))
        for t in rec.get("tasks") or []:
            print("   task [%s] %s logFile=%s" % (t.get("type"), t.get("jobName"), t.get("logFile")))
            for e in (t.get("errorLines") or [])[:12]:
                if isinstance(e, dict):
                    print("        %s:%s %s" % (e.get("logFile") or "", e.get("line"),
                                                (e.get("text") or "")[:160]))
                else:
                    print("        %s" % str(e)[:160])
            for c in (t.get("cases") or [])[:6]:
                print("        case %s [%s]" % (c.get("name"), c.get("state")))
        for e in (rec.get("errorMessages") or [])[:15]:
            print("   err %s:%s %s" % (e.get("source"), e.get("line"), (e.get("text") or "")[:200]))
        for c in (rec.get("cases") or [])[:10]:
            print("   case %s [%s] %s" % (c.get("name"), c.get("state"),
                                          (c.get("description") or "")[:200]))
        print("   evidence.files=%s missing=%s"
              % ((rec.get("evidence") or {}).get("files"),
                 (rec.get("evidence") or {}).get("missing")))


if __name__ == "__main__":
    for t in TARGETS:
        dump(*t)
