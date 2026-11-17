# -*- coding: utf-8 -*-
import io, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa
OUT = io.open(ROOT / "out/state/_fin16f.txt", "w", encoding="utf-8", newline="\n")
BASE = ROOT / "out/archive/2026/2026-11/2026-11-16"
G = "github_logs/"
CASES = [
    ("SgLang/nightly-test-npu.yml", G + "gh_43731798211/132866286657_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 2, 1, 1, test_registe~90810f.txt", [811]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43733552254/10_multi-node-poc (deepseek_v4_flash_w8a8_1p1d_16p_in128k_out1k_prefix90_20ms, 1, 1~5c11ad.txt", [510, 511]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43734093288/132873418319_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 2, 1, 1, test_registe~90810f.txt", [531]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43804251765/133091277942_multi-node-mix-poc (kimi_k3_w4a8_32p_mix_in128k_out1k_decode_prefix, 4, test_reg~77367e.txt", [633, 718]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43805718761/133095943416_multi-node-mix-poc (kimi_k3_w4a8_32p_mix_in128k_out1k_decode_prefix, 4, test_reg~77367e.txt", [1360, 1372]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43867439699/133327323785_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt", [706]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43868335184/133302785092_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt", [311, 340]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43868640459/133303671681_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", [687, 713]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43868646557/133303913207_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt", [723]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43870381982/133309711840_multi-node-mix-poc (kimi_k3_w4a8_32p_mix_in128k_out1k_decode_prefix, 4, test_reg~77367e.txt", [2938]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43874714626/133324841013_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", [553]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43888687387/133373908398_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", [643, 672]),
    ("SgLang/nightly-test-npu.yml", G + "gh_43892530840/133388055851_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", [638]),
]
for comp, relp, lines in CASES:
    base = BASE / comp
    OUT.write("### %s @%s\n" % (relp[-46:], lines))
    for L in lines:
        text, got = pipeline_doc.evidence_window(base, relp, L, L, max_lines=1)
        OUT.write("  L%d: %s\n" % (L, (text or "!!").strip()))
OUT.close()
print("done")
