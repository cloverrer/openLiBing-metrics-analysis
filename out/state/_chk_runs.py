# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path("out/archive/2026/2026-11")
for day in ["2026-11-06", "2026-11-11"]:
    pj = json.loads((ROOT / day / "HPCKit" / "kudnn" / "pipeline.json").read_text(encoding="utf-8"))
    print("=== %s kudnn ===" % day)
    print("stepIndex:", pj.get("stepIndex"))
    steps = pj.get("steps") or {}
    for k, v in steps.items():
        if isinstance(v, dict):
            print("  step", k, "keys:", list(v.keys())[:12],
                  "| runHistory len:", len(v.get("runHistory") or []))
            rh = v.get("runHistory") or []
            if rh:
                print("     runHistory 结束日:", sorted(set(str((x.get("end") or ""))[:10] for x in rh)))
                print("     rn:", [x.get("rn") for x in rh])
                print("     iva:", [x.get("iva") for x in rh])
        else:
            print("  step", k, "=", type(v).__name__)
    print("  counts:", pj.get("counts"))
    print("  dateBasis:", pj.get("dateBasis"))
