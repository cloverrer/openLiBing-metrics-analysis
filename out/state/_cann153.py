# -*- coding: utf-8 -*-
"""打印 Ascend-CANN os#153 Build_A3_image 的 L97 全文（按 # 分段）。只读。"""
import json
import builtins
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

OUT = open(ROOT / "out/state/_cann153.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pdir = ROOT / "out/archive/2026/2026-11/2026-11-16/Ascend-CANN/os"
text, ok = pipeline_doc.evidence_window(
    pdir, "job_logs/41_os_153_Build_A3_image.log", 97, 97, max_lines=5)
print("ok=%s" % ok)
parts = text.split("#")
for p in parts:
    print("##" + p[:500])

# 也把 90-96 行 tail 看看 dockerd 相关信息
t2, ok2 = pipeline_doc.evidence_window(
    pdir, "job_logs/41_os_153_Build_A3_image.log", 1, 12, max_lines=20)
print("==== head ====")
for i, ln in enumerate(t2.split("\n"), start=1):
    print("L%d: %s" % (i, ln[:300]))

OUT.close()
