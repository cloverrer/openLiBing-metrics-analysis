# -*- coding: utf-8 -*-
"""打印候选 cites 行的精确原文，供构造可命中的 keyError。"""
import json
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
DAY = ROOT / "out/archive/2026/2026-11/2026-11-16"

EV = {
    "CANN": DAY / "Ascend-CANN/os/pipeline.evidence.json",
    "SG": DAY / "SgLang/nightly-test-npu.yml/pipeline.evidence.json",
    "UBS": DAY / "UBS Core/Nightly-CI-Version-pipeline_BeiMing/pipeline.evidence.json",
    "VL": DAY / "vllm-ascend/a3.yaml/pipeline.evidence.json",
}

CACHE = {}


def load(tag):
    if tag not in CACHE:
        CACHE[tag] = json.load(io.open(EV[tag], encoding="utf-8")).get("files") or {}
    return CACHE[tag]


def show(tag, sub, ln):
    files = load(tag)
    hits = [k for k in files if sub in k]
    if not hits:
        print("NO MATCH", tag, sub)
        return
    k = hits[0]
    lines = files[k].get("lines") or []
    txt = lines[ln - 1] if 0 < ln <= len(lines) else "<OOR>"
    print("### %s : %s : L%d" % (tag, k, ln))
    print(txt)
    print()


show("CANN", "41_os_153_Build_A3_image", 97)
show("UBS", "_261_Deploy_Test_ubs_engine.log", 2)
show("UBS", "_262_Deploy_Test_ubturbo_smap.log", 2)
show("SG", "132866286657_multi-node-poc", 811)
show("SG", "4_multi-node-mix-poc (kimi_k3_w4a8_32p_gpqa", 14885)
show("SG", "10_multi-node-poc (deepseek_v4_flash_w8a8_1p1d_16p_in128k", 510)
show("SG", "132873418319_multi-node-poc", 531)
show("SG", "133091277942_multi-node-mix-poc", 718)
show("SG", "133095943416_multi-node-mix-poc", 1360)
show("SG", "133340755431_multi-node-poc", 630)
show("SG", "133302785092_multi-node-poc", 311)
show("SG", "133303671681_multi-node-poc", 687)
show("SG", "133303913207_multi-node-poc", 714)
show("SG", "133309711840_multi-node-mix-poc", 2939)
show("SG", "133324841013_multi-node-poc", 553)
show("SG", "133373908398_multi-node-poc", 672)
show("SG", "133388055851_multi-node-poc", 638)
show("VL", "132845808398_multi-node", 2343)
show("VL", "132974265350_double-node", 2915)
