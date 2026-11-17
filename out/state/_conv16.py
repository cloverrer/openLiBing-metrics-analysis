# -*- coding: utf-8 -*-
"""扫描归档，统计各 analysis.issueType 对应的 failedTaskType 分布，确认惯例。"""
import json
import io
from pathlib import Path
from collections import Counter

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
ARCH = ROOT / "out/archive"

pair = Counter()
rows = []
for p in sorted(ARCH.rglob("pipeline.json")):
    try:
        doc = json.load(io.open(p, encoding="utf-8"))
    except Exception:
        continue
    for rec in doc.get("records") or []:
        a = rec.get("analysis") or {}
        if a.get("status") != "done":
            continue
        it = a.get("issueType")
        ftt = rec.get("failedTaskType")
        pair[(str(ftt), str(it))] += 1
        if ftt == "其他任务":
            rows.append((rec.get("recordId"), it, a.get("issueDetail"), p.parent.name, p.parent.parent.name))

print("== (ftt, issueType) 计数 ==")
for (ftt, it), n in sorted(pair.items(), key=lambda x: -x[1]):
    print("%4d  ftt=%-10s -> %s" % (n, ftt, it))
print()
print("== ftt=其他任务 的已定稿记录 ==")
for r in rows[:40]:
    print("  %-46s %-14s %-24s %s/%s" % r)
print("total 其他任务 done:", len(rows))
