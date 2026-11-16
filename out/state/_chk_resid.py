# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days, iter_archive_pipelines
from lib import pipeline_doc

for date, day_dir in iter_archive_days():
    dj = day_dir / "_day.json"
    day = json.loads(dj.read_text(encoding="utf-8"))
    in_day = {e.get("key") for e in day.get("pipelines") or []}
    for comp, pname_dir, pdir in iter_archive_pipelines(day_dir):
        key = "%s|%s" % (comp, pname_dir)
        d = pipeline_doc.load(pdir) or {}
        pl = ((d.get("steps") or {}).get("step_1_lights") or {}).get("pipeline") or {}
        nrec = len(d.get("records") or [])
        flag = "" if key in in_day else "  <<< NOT-IN-DAY"
        print("%s %-52s pid=%s recs=%d%s" % (date, key, (pl.get("pipelineId") or "-")[:8], nrec, flag))
