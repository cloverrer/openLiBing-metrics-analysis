import json
from pathlib import Path
root = Path("out/archive/2026/2026-11")
for day in ["2026-11-06","2026-11-09","2026-11-10","2026-11-11","2026-11-12"]:
    p = root/day/"_day.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    print("="*80)
    print("DAY", day, "keys:", list(d.keys()))
    pls = d.get("pipelines") or []
    print("pipelines:", len(pls))
    if pls:
        t = pls[0]
        print("sample pipeline keys:", list(t.keys()))
        print(json.dumps(t, ensure_ascii=False)[:1500])
    prods = d.get("products") or []
    if prods:
        print("sample product:", json.dumps(prods[0], ensure_ascii=False)[:600])
    break
