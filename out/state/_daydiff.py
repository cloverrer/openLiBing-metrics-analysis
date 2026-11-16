import json, sys
from pathlib import Path
from collections import defaultdict
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days
per = {}
allk = set()
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    ks = set()
    for e in day.get("pipelines") or []:
        ks.add("%s|%s" % (e.get("component"), e.get("pipelineId") or e.get("pipeline")))
    per[date] = ks
    allk |= ks
for d in sorted(per):
    print(d, len(per[d]))
print("union", len(allk))
for d in sorted(per):
    for k in sorted(allk - per[d]):
        print("  %s 缺失 %s" % (d, k))
