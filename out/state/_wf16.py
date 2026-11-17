# -*- coding: utf-8 -*-
import json
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


W = [
    ("SgLang|nightly-test-npu.yml#2212", 1, 585, 645),
    ("SgLang|nightly-test-npu.yml#2212", 7, 14818, 14860),
    ("SgLang|nightly-test-npu.yml#2220", 0, 330, 374),
    ("SgLang|nightly-test-npu.yml#2222", 0, 660, 720),
    ("SgLang|nightly-test-npu.yml#2223", 2, 2470, 2500),
]
out = []
for rid, ti, a, b in W:
    rec, pdir = record(rid)
    path = rec["tasks"][ti].get("logFile")
    out.append("### %s ti=%d L%d-%d" % (rid, ti, a, b))
    for ln in range(a, b + 1):
        text, ok = pipeline_doc.evidence_window(pdir, path, ln, ln, max_lines=1)
        if not ok:
            continue
        t = " ".join(text.split())
        if t:
            out.append("  L%d | %s" % (ln, t[:230]))
    out.append("")
(ROOT / "out/state/_wf16.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
