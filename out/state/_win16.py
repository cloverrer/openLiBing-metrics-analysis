# -*- coding: utf-8 -*-
"""批量取多条记录的关键日志窗口，写文件。只读。"""
import json
import builtins
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

OUT = open(ROOT / "out/state/_win16.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pend = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))

# (recordId, taskIndex, subIndex(-1 none), l1, l2)
JOBS = [
    ("Ascend-CANN|os#153", 0, -1, 85, 101),
    ("SgLang|nightly-test-npu.yml#2211", 0, -1, 795, 815),
    ("SgLang|nightly-test-npu.yml#2213", 0, -1, 515, 535),
    ("SgLang|nightly-test-npu.yml#2214", 0, -1, 705, 725),
    ("SgLang|nightly-test-npu.yml#2215", 0, -1, 1320, 1370),
    ("SgLang|nightly-test-npu.yml#2218", 0, -1, 700, 730),
    ("SgLang|nightly-test-npu.yml#2220", 0, -1, 300, 345),
    ("SgLang|nightly-test-npu.yml#2222", 0, -1, 660, 715),
    ("SgLang|nightly-test-npu.yml#2223", 0, -1, 710, 730),
    ("SgLang|nightly-test-npu.yml#2223", 1, -1, 2100, 2120),
    ("SgLang|nightly-test-npu.yml#2224", 0, -1, 2900, 2965),
    ("SgLang|nightly-test-npu.yml#2225", 0, -1, 548, 580),
    ("SgLang|nightly-test-npu.yml#2226", 0, -1, 665, 700),
    ("vllm-ascend|a3.yaml#16563", 0, -1, 2295, 2320),
    ("vllm-ascend|a3.yaml#16563", 0, -1, 2360, 2415),
    ("vllm-ascend|a3.yaml#16564", 0, -1, 2900, 2948),
]


def find(rid):
    for it in pend["records"]:
        if it["recordId"] == rid:
            return it
    return None


def load(rid):
    it = find(rid)
    parts = it["file"].rsplit(" records[", 1)
    p = ROOT / "out" / parts[0]
    doc = json.loads(p.read_text(encoding="utf-8"))
    idx = int(parts[1].rstrip("]"))
    return doc["records"][idx], p.parent


for rid, ti, si, l1, l2 in JOBS:
    rec, pdir = load(rid)
    tasks = rec.get("tasks") or []
    if ti >= len(tasks):
        print("### %s task[%d] NOT FOUND" % (rid, ti))
        continue
    t = tasks[ti]
    if si >= 0:
        t = (t.get("subTasks") or [])[si]
    path = t.get("logFile") or t.get("localLog")
    print("=" * 90)
    print("### %s task[%d] sub=%d  path=%s  L%d-%d" % (rid, ti, si, path, l1, l2))
    if not path:
        print("   (no log path)")
        continue
    text, ok = pipeline_doc.evidence_window(pdir, path, l1, l2, max_lines=200)
    if not ok:
        print("   (window not available)")
        continue
    lines = text.split("\n")
    for i, ln in enumerate(lines, start=l1):
        print("L%d: %s" % (i, ln[:400]))
    print("")

OUT.close()
