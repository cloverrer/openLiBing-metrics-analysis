# -*- coding: utf-8 -*-
"""定向取证：导出若干关键窗口。"""
import json
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
D = ROOT / "out/archive/2026/2026-11/2026-11-16"
SG = D / "SgLang/nightly-test-npu.yml/pipeline.evidence.json"
CAN = D / "Ascend-CANN/os/pipeline.evidence.json"
VL = D / "vllm-ascend/a3.yaml/pipeline.evidence.json"

out = []


def win(ev, sub, a, b, tag):
    d = json.load(io.open(ev, encoding="utf-8"))
    files = d.get("files") or {}
    hits = [k for k in files if sub in k]
    if not hits:
        out.append("### %s :: NO MATCH %s" % (tag, sub))
        return
    for k in hits[:1]:
        lines = files[k].get("lines") or []
        out.append("### %s :: %s (total %d)" % (tag, k, len(lines)))
        for i in range(a - 1, min(b, len(lines))):
            out.append("L%d: %s" % (i + 1, lines[i][:500]))
        out.append("")


# Ascend-CANN L97 全文
win(CAN, "41_os_153_Build_A3_image", 95, 101, "CANN153")
# 2212 kimi kda
win(SG, "4_multi-node-mix-poc (kimi_k3_w4a8_32p_gpqa", 14880, 14900, "2212-kimi-kda")
win(SG, "4_multi-node-mix-poc (kimi_k3_w4a8_32p_gpqa", 15700, 15760, "2212-kimi-oserr")
win(SG, "10_multi-node-poc (deepseek_v4_flash_w8a8_1p1d_16p_in128k", 1230, 1290, "2212-ds")
# 2218
win(SG, "133327323785_multi-node-poc", 700, 745, "2218-a")
win(SG, "133340755431_multi-node-poc", 610, 660, "2218-b")
# 2223
win(SG, "133303913207_multi-node-poc", 712, 760, "2223-a")
# 2224
win(SG, "133309711840_multi-node-mix-poc", 2930, 2995, "2224")
# 2225
win(SG, "133324841013_multi-node-poc", 548, 610, "2225")
# 2226
win(SG, "133373908398_multi-node-poc", 665, 725, "2226")
# 2220
win(SG, "133302785092_multi-node-poc", 300, 374, "2220")
# 2227
win(SG, "133388055851_multi-node-poc", 620, 645, "2227")
# 2215 kill/oom grep-ish window
win(SG, "133095943416_multi-node-mix-poc", 1355, 1400, "2215")
# vllm 16564
win(VL, "132974265350_double-node", 2900, 2975, "16564")
win(VL, "132974265350_double-node", 3600, 3760, "16564-tail")

Path(ROOT / "out/state/_deep16.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote", len(out))
