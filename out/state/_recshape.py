import json, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
p = ROOT / "out/archive/2026/2026-11/2026-11-10/boostkit/Bigdata"
d = pipeline_doc.load(p) or {}
rec = (d.get("records") or [])[0]
print("RECORD KEYS:", sorted(rec.keys()))
for k in ("recordId","status","failedTaskType","counts","light","verdict"):
    print("--", k, "=>", json.dumps(rec.get(k), ensure_ascii=False)[:400])
print()
print("--- step_2 runs sample (per-run iva/bc/bpc) ---")
s2 = ((d.get("steps") or {}).get("step_2_runs") or {})
print("step_2 keys:", sorted(s2.keys()))
rh = s2.get("runHistory") or []
print("runHistory n =", len(rh))
for r in rh[:3]:
    print("   ", json.dumps(r, ensure_ascii=False)[:500])
