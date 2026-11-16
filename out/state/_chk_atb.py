import json, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
for rel in ["2026-11-12/Ascend-CANN/atb", "2026-11-12/vllm-ascend/a3.yaml"]:
    p = ROOT / "out/archive/2026/2026-11" / rel
    d = pipeline_doc.load(p) or {}
    s2 = ((d.get("steps") or {}).get("step_2_runs") or {})
    rh = s2.get("runHistory") or []
    print("==", rel, " runHistory", len(rh), "失败记录", len([r for r in (d.get("records") or []) if (r.get("verdict") or {}).get("category")!="success"]))
    tot_bc = sum(r.get("bc") or 0 for r in rh); tot_bpc = sum(r.get("bpc") or 0 for r in rh)
    print("   Σbc=%s Σbpc=%s -> bs=%s ; 归档 light.bsRate=%s" % (tot_bc, tot_bpc, (tot_bpc/tot_bc if tot_bc else None), (d.get("records") or [{}])[0].get("light",{}).get("bsRate")))
    for r in sorted(rh, key=lambda x: str(x.get("end") or "")):
        flag = "  <== bpc<bc" if (r.get("bc") or 0) > 0 and (r.get("bpc") is not None) and r.get("bpc") < r.get("bc") else ""
        print("   rn=%-7s %-10s bc=%-4s bpc=%-4s cpr=%-6s iva=%-6s end=%s%s"
              % (r.get("rn"), r.get("status"), r.get("bc"), r.get("bpc"), r.get("cpr"), r.get("iva"), r.get("end"), flag))
    print("   excludedRuns:", json.dumps(s2.get("excludedRuns"), ensure_ascii=False)[:300])
    print()
