# -*- coding: utf-8 -*-
"""针对 2212 kimi 调度异常取证。只读。"""
import json
import builtins
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

OUT = open(ROOT / "out/state/_win16b.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pend = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))


def load(rid):
    for it in pend["records"]:
        if it["recordId"] == rid:
            parts = it["file"].rsplit(" records[", 1)
            p = ROOT / "out" / parts[0]
            doc = json.loads(p.read_text(encoding="utf-8"))
            return doc["records"][int(parts[1].rstrip("]"))], p.parent
    return None, None


# 2212 kimi_k3_w4a8_32p_gpqa -> task idx 7 ; 2216/2217/2219 tasks dump
rec, pdir = load("SgLang|nightly-test-npu.yml#2212")
tasks = rec.get("tasks") or []
print("2212 task count = %d" % len(tasks))
for i, t in enumerate(tasks):
    print("  [%d] %s" % (i, t.get("jobName")))
    if i in (7, 8, 9):
        for el in (t.get("errorLines") or []):
            print("      %s" % json.dumps(el, ensure_ascii=False)[:260])
# kimi k3 gpqa is idx 7; read window around scheduler exception
for idx, l1, l2 in [(7, 14830, 14895)]:
    t = tasks[idx]
    path = t.get("logFile")
    text, ok = pipeline_doc.evidence_window(pdir, path, l1, l2, max_lines=100)
    print("--- %s %s L%d-%d ok=%s" % (t.get("jobName"), path, l1, l2, ok))
    if ok:
        for i, ln in enumerate(text.split("\n"), start=l1):
            print("L%d: %s" % (i, ln[:300]))

for rid in ("SgLang|nightly-test-npu.yml#2216", "SgLang|nightly-test-npu.yml#2217",
            "SgLang|nightly-test-npu.yml#2219"):
    r, _ = load(rid)
    print("=" * 80)
    print("%s tasks=%s  raw=%s" % (rid, json.dumps(r.get("tasks"), ensure_ascii=False)[:400],
                                   json.dumps({k: v for k, v in r.items() if k != "tasks"}, ensure_ascii=False)[:600]))

OUT.close()
