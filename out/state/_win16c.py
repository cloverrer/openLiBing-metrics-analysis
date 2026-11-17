# -*- coding: utf-8 -*-
"""定向取证 v3：按记录导出精确窗口（行截断 320 字），写入 _win16c.txt。"""
import json
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
SG = ROOT / "out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml/pipeline.evidence.json"
d = json.load(io.open(SG, encoding="utf-8"))
files = d.get("files") or {}

WINDOWS = [
    ("2211-module", "132866286657_multi-node-poc", 800, 815),
    ("2214-memcache", "133091277942_multi-node-mix-poc", 710, 725),
    ("2212-setenv", "10_multi-node-poc (deepseek_v4_flash_w8a8_1p1d_16p_in128k", 505, 515),
    ("2213-import", "132873418319_multi-node-poc", 524, 536),
    ("2220-runner", "133302785092_multi-node-poc", 300, 374),
    ("2222-router", "133303671681_multi-node-poc", 660, 715),
    ("2225-pod", "133324841013_multi-node-poc", 545, 600),
    ("2226-pod", "133373908398_multi-node-poc", 662, 700),
    ("2227-tail", "133388055851_multi-node-poc", 620, 707),
    ("2218-a-pod", "133327323785_multi-node-poc", 700, 735),
    ("2218-b-ready", "133340755431_multi-node-poc", 605, 662),
    ("2223-a-notready", "133303913207_multi-node-poc", 712, 760),
    ("2223-b-bind", "133347678142_multi-node-poc", 550, 575),
    ("2223-b-bind2", "133347678142_multi-node-poc", 2105, 2120),
    ("2224-timeout", "133309711840_multi-node-mix-poc", 2930, 2990),
    ("2215-kill", "133095943416_multi-node-mix-poc", 1355, 1400),
]

out = []
for tag, sub, a, b in WINDOWS:
    hits = [k for k in files if sub in k]
    if not hits:
        out.append("### %s :: NO MATCH %s" % (tag, sub))
        continue
    k = hits[0]
    lines = files[k].get("lines") or []
    out.append("### %s :: %s (total %d)" % (tag, k, len(lines)))
    for i in range(a - 1, min(b, len(lines))):
        out.append("L%d: %s" % (i + 1, lines[i][:320]))
    out.append("")

Path(ROOT / "out/state/_win16c.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote", len(out), "lines")
