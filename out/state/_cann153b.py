# -*- coding: utf-8 -*-
"""在 Ascend-CANN os#153 L97 中找关键 docker 失败片段。只读。"""
import re
import json
import builtins
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

OUT = open(ROOT / "out/state/_cann153b.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pdir = ROOT / "out/archive/2026/2026-11/2026-11-16/Ascend-CANN/os"
text, ok = pipeline_doc.evidence_window(
    pdir, "job_logs/41_os_153_Build_A3_image.log", 97, 97, max_lines=5)
print("len=%d ok=%s" % (len(text), ok))
pats = ["failed to solve", "failed to compute", "ERROR:", "error:", "error_msg",
        "no such host", "timed out", "timeout", "denied", "not found", "Unable to",
        "cannot", "Cannot", "exit code", "COPY", "RUN ", "pip install"]
for pat in pats:
    for m in re.finditer(re.escape(pat), text):
        s = max(0, m.start() - 90)
        e = min(len(text), m.end() + 160)
        print("[%s] ...%s..." % (pat, text[s:e].replace("\n", " ")))
        break  # 每个模式只取首个命中，避免刷屏
OUT.close()
