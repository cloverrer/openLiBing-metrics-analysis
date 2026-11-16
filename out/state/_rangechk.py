import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days
days = {}
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    ks = set()
    for e in day.get("pipelines") or []:
        ks.add((e.get("component"), e.get("pipelineId") or e.get("pipeline")))
    days[date] = ks
def union(f, t):
    u = set()
    for d in days:
        if f <= d <= t:
            u |= days[d]
    c = defaultdict(int)
    for comp, k in u:
        c[comp] += 1
    return u, c
for f, t in [("2026-11-10","2026-11-12"), ("2026-11-13","2026-11-13"), ("2026-11-10","2026-11-13")]:
    u, c = union(f, t)
    print("%s ~ %s  合计 %d 条 | openUBMC=%d MindCluster=%d" % (f, t, len(u), c["openUBMC"], c["MindCluster"]))
