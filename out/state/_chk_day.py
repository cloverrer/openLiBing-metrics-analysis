import json, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
for rel in ["2026-11-12/Ascend-CANN/atb", "2026-11-12/vllm-ascend/a3.yaml"]:
    p = ROOT / "out/archive/2026/2026-11" / rel
    d = pipeline_doc.load(p) or {}
    print("==", rel)
    s1 = ((d.get("steps") or {}).get("step_1_lights") or {})
    pl = s1.get("pipeline") or {}
    print("  step_1.pipeline =", json.dumps(pl, ensure_ascii=False)[:900])
    print("  step_1 keys =", sorted(s1.keys()))
    s2 = ((d.get("steps") or {}).get("step_2_runs") or {})
    for k in ("days", "dateRange", "meta"):
        v = s2.get(k)
        if v is not None:
            print("  step_2.%s = %s" % (k, json.dumps(v, ensure_ascii=False)[:400]))
    s7 = None
    print("  steps present =", sorted((d.get("steps") or {}).keys()))
    print()
day = json.loads((ROOT / "out/archive/2026/2026-11/2026-11-12/_day.json").read_text(encoding="utf-8"))
for e in day.get("pipelines") or []:
    if e.get("component") in ("Ascend-CANN", "vllm-ascend") and e.get("pipeline") in ("atb", "a3.yaml"):
        print("DAY ENTRY:", json.dumps(e, ensure_ascii=False))
