import json, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib.paths import iter_archive_days
for date, day_dir in iter_archive_days():
    day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
    want = set()
    for e in day.get("pipelines") or []:
        want.add((e.get("component"), e.get("pipeline")))
    have = []
    for comp in sorted(p for p in day_dir.iterdir() if p.is_dir()):
        for pl in sorted(p for p in comp.iterdir() if p.is_dir()):
            have.append((comp.name, pl.name, str(pl)))
    extra = [h for h in have if (h[0], h[1]) not in want]
    print(date, "dirs=", len(have), "day.json=", len(want), "extra=", len(extra))
    for e in extra:
        print("    EXTRA", e[0], "/", e[1])
