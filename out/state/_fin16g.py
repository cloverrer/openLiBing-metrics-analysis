# -*- coding: utf-8 -*-
import io, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa
OUT = io.open(ROOT / "out/state/_fin16g.txt", "w", encoding="utf-8", newline="\n")
BASE = ROOT / "out/archive/2026/2026-11/2026-11-16"
G = "github_logs/"
CASES = [
    ("SgLang/nightly-test-npu.yml", G + "gh_43874714626/133324841013_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", 536, 552),
    ("SgLang/nightly-test-npu.yml", G + "gh_43870381982/133309711840_multi-node-mix-poc (kimi_k3_w4a8_32p_mix_in128k_out1k_decode_prefix, 4, test_reg~77367e.txt", 2928, 2950),
    ("SgLang/nightly-test-npu.yml", G + "gh_43733552254/12_nightly-4-npu-a3 _ run (0).txt", 430, 470),
]
for comp, relp, a, b in CASES:
    base = BASE / comp
    OUT.write("### %s L%d-%d\n" % (relp[-44:], a, b))
    text, got = pipeline_doc.evidence_window(base, relp, a, b, max_lines=200)
    if not got:
        OUT.write("  !!不可读\n")
        continue
    for i, ln in enumerate(text.split("\n"), a):
        OUT.write("  L%d: %s\n" % (i, ln.strip()[:300]))
OUT.close()
print("done")
