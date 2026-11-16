# -*- coding: utf-8 -*-
"""看最近一次采集（out/work）的流水线清单里 openUBMC / MindCluster 有哪些。"""
import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(__file__).resolve().parent.parent.parent
WORK = ROOT / "out" / "work"
p = WORK / "step_1_bad_pipelines.json"
if not p.is_file():
    print("MISSING", p)
    for f in sorted(WORK.glob("*.json")):
        print("  ", f.name, f.stat().st_size)
    sys.exit(0)
d = json.loads(p.read_text(encoding="utf-8"))
print("generatedAt:", d.get("generatedAt"), " range:", d.get("startDate"), "~", d.get("endDate"))
rows = d.get("pipelines") or []
byc = defaultdict(list)
for b in rows:
    byc[b.get("product")].append(b)
print("总条数:", len(rows))
for c in ("openUBMC", "MindCluster"):
    print("== %s (%d 条) ==" % (c, len(byc.get(c, []))))
    for b in byc.get(c, []):
        print("   pid=%s name=%-40s platform=%-9s dims=%s" % (
            (str(b.get("pipelineId")) or "-")[:8], b.get("pipelineName"),
            b.get("platform"), b.get("dims")))
print("-- 全部组件条数 --")
for c in sorted(byc):
    print("   %-16s %d" % (c, len(byc[c])))
