# -*- coding: utf-8 -*-
import json
from pathlib import Path

root = Path("out/archive/2026/2026-11")


def scan(day, limit=4):
    base = root / day
    print("=" * 90)
    print("DAY", day)
    n = 0
    for comp in sorted(p for p in base.iterdir() if p.is_dir()):
        for pl in sorted(p for p in comp.iterdir() if p.is_dir()):
            pj = pl / "pipeline.json"
            if not pj.exists():
                continue
            d = json.loads(pj.read_text(encoding="utf-8"))
            recs = d.get("records") or []
            runs = ((d.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
            rec_days = {}
            for r in recs:
                k = str(r.get("endedAt") or "")[:10]
                rec_days[k] = rec_days.get(k, 0) + 1
            run_days = {}
            for r in runs:
                k = str(r.get("end") or "")[:10]
                run_days[k] = run_days.get(k, 0) + 1
            if len(rec_days) > 1 or len(run_days) > 1:
                print("  %s/%s  records=%d days=%s  runs=%d days=%s" % (
                    comp.name, pl.name, len(recs), rec_days, len(runs), run_days))
                n += 1
                if n >= limit:
                    return
    if not n:
        print("  (no cross-day pipeline.json found)")


scan("2026-11-06")
scan("2026-11-11")
scan("2026-11-12")
scan("2026-11-09")
scan("2026-11-10")
