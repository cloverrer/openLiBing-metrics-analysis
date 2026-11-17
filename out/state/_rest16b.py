# -*- coding: utf-8 -*-
import json
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
out = []
for it in PEND["records"]:
    if it["recordId"] not in (
        "MindCluster|Agentsdk~5992cb#2",
        "SgLang|nightly-test-npu.yml#2216",
        "SgLang|nightly-test-npu.yml#2217",
        "SgLang|nightly-test-npu.yml#2219",
    ):
        continue
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    rec = doc["records"][int(parts[1].rstrip("]"))]
    keys = {k: v for k, v in rec.items() if k not in ("tasks",)}
    out.append("### " + it["recordId"])
    out.append(json.dumps(keys, ensure_ascii=False, indent=1))
    out.append("")
(ROOT / "out/state/_rest16b.txt").write_text("\n".join(out), encoding="utf-8")
print("ok")
