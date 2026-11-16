# -*- coding: utf-8 -*-
"""临时：核对 out/work step_2 运行历史的日期覆盖（判断能否安全重跑 step_7）。"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
d = json.loads((ROOT / "out" / "work" / "step_2_failed_runs.json").read_text(encoding="utf-8"))
c = collections.Counter()
n = 0
for k, v in d.items():
    if k.startswith("_"):
        continue
    for h in (v.get("runHistory") or []):
        c[str(h.get("end"))[:10]] += 1
        n += 1
print("meta:", json.dumps(d.get("_meta") or {}, ensure_ascii=False)[:400])
print("runs:", n)
print("by day:", sorted(c.items()))
