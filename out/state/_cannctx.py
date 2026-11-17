# -*- coding: utf-8 -*-
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
IDX = {it["recordId"]: it for it in PEND["records"]}


def record(rid):
    it = IDX[rid]
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    return doc["records"][int(parts[1].rstrip("]"))], (ROOT / "out" / parts[0]).parent


rec, pdir = record("Ascend-CANN|os#153")
path = rec["tasks"][0]["logFile"]
text, ok = pipeline_doc.evidence_window(pdir, path, 97, 97, max_lines=1)
out = []
for m in re.finditer(r".{160}(?:chmod|Ascend-cann|cannot access|ERROR: process).{220}", text):
    out.append(">>> " + m.group(0))
(ROOT / "out/state/_cannctx.txt").write_text("\n\n".join(out), encoding="utf-8")
print("done", len(out))
