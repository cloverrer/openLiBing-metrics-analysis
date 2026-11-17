# -*- coding: utf-8 -*-
"""导出剩余待定记录的日志窗口 + 关键模式检索。"""
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


WIN = [
    ("SgLang|nightly-test-npu.yml#2215", 0, 1315, 1400),
    ("SgLang|nightly-test-npu.yml#2218", 0, 640, 720),
    ("SgLang|nightly-test-npu.yml#2223", 0, 700, 760),
    ("SgLang|nightly-test-npu.yml#2224", 0, 2925, 2995),
    ("SgLang|nightly-test-npu.yml#2226", 0, 635, 680),
    ("SgLang|nightly-test-npu.yml#2212", 0, 500, 560),
    ("SgLang|nightly-test-npu.yml#2214", 0, 625, 650),
]
PATS = [
    ("SgLang|nightly-test-npu.yml#2215", 0, r"OOM|oom|Killed|killed|MemoryError|out of memory|code -9"),
    ("SgLang|nightly-test-npu.yml#2226", 0, r"mem_cache|operators"),
    ("SgLang|nightly-test-npu.yml#2223", 0, r"set_env\.bash|customize"),
]
out = []
for rid, ti, a, b in WIN:
    rec, pdir = record(rid)
    path = rec["tasks"][ti].get("logFile")
    out.append("### %s ti=%d L%d-%d" % (rid, ti, a, b))
    for ln in range(a, b + 1, 2):
        text, ok = pipeline_doc.evidence_window(pdir, path, ln, ln + 1, max_lines=2)
        if not ok:
            continue
        for sub in text.split("\n"):
            t = " ".join(sub.split())
            if t:
                out.append("  L%d | %s" % (ln, t[:230]))
                ln += 1
    out.append("")
for rid, ti, pat in PATS:
    rec, pdir = record(rid)
    path = rec["tasks"][ti].get("logFile")
    out.append("### GREP %s %s" % (rid, pat))
    text, ok = pipeline_doc.evidence_window(pdir, path, 1, 99999, max_lines=99999)
    if not ok:
        out.append("  !! 读不到")
        continue
    for i, line in enumerate(text.split("\n"), 1):
        if re.search(pat, line):
            out.append("  L%d | %s" % (i, " ".join(line.split())[:230]))
    out.append("")
(ROOT / "out/state/_win16d.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
