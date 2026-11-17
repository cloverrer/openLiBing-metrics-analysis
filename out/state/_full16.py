# -*- coding: utf-8 -*-
"""打印指定纪录指定行原文，每行截断 240 字。"""
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


WANT = [
    ("Ascend-CANN|os#153", 0, 96, 98),
    ("SgLang|nightly-test-npu.yml#2223", 0, 712, 716),
    ("SgLang|nightly-test-npu.yml#2224", 0, 2937, 2940),
    ("vllm-ascend|a3.yaml#16563", 0, 2308, 2312),
    ("vllm-ascend|a3.yaml#16564", 0, 2913, 2916),
    ("UBS Core|Nightly-CI-Version-pipeline_BeiMing#261", 1, 1, 3),
    ("UBS Core|Nightly-CI-Version-pipeline_BeiMing#262", 1, 1, 3),
    ("SgLang|nightly-test-npu.yml#2211", 0, 808, 815),
    ("SgLang|nightly-test-npu.yml#2212", 1, 508, 512),
    ("SgLang|nightly-test-npu.yml#2213", 0, 529, 533),
    ("SgLang|nightly-test-npu.yml#2214", 0, 716, 720),
    ("SgLang|nightly-test-npu.yml#2215", 0, 1358, 1362),
    ("SgLang|nightly-test-npu.yml#2218", 0, 712, 716),
    ("SgLang|nightly-test-npu.yml#2220", 0, 310, 313),
    ("SgLang|nightly-test-npu.yml#2222", 0, 685, 689),
    ("SgLang|nightly-test-npu.yml#2225", 0, 552, 556),
    ("SgLang|nightly-test-npu.yml#2226", 0, 671, 675),
    ("SgLang|nightly-test-npu.yml#2227", 0, 636, 640),
]

out = []
for rid, ti, a, b in WANT:
    rec, pdir = record(rid)
    path = rec["tasks"][ti].get("logFile")
    out.append("### %s  ti=%d L%d-%d" % (rid, ti, a, b))
    for ln in range(a, b + 1):
        text, ok = pipeline_doc.evidence_window(pdir, path, ln, ln, max_lines=1)
        if not ok:
            out.append("  L%d !! 读不到" % ln)
            continue
        t = " ".join(text.split())
        out.append("  L%d | %s" % (ln, t[:240]))
    out.append("")
(ROOT / "out/state/_full16.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
