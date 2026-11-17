# -*- coding: utf-8 -*-
import json
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))

for it in PEND["records"]:
    if it["component"] not in ("SgLang", "vllm-ascend", "UBS Core", "Ascend-CANN"):
        continue
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    rec = doc["records"][int(parts[1].rstrip("]"))]
    print("###", it["recordId"])
    for i, t in enumerate(rec.get("tasks", [])):
        lf = t.get("logFile")
        print("   [%d] %s | %s" % (i, t.get("type"), lf if lf else t.get("download")))
