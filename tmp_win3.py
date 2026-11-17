import sys
from pathlib import Path
sys.path.insert(0, str(Path(r".")))
from lib import pipeline_doc
pdir = Path("out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml")
def win(tag, path, a, b):
    t,_ = pipeline_doc.evidence_window(pdir, path, a, b, max_lines=b-a+1)
    print("###", tag)
    for i,l in enumerate(t.split("\n"), a):
        if l.strip(): print("L%-5d| %s" % (i, l[:210]))
    print("-"*90)
win("2215", "github_logs/gh_43805718761/133095943416_multi-node-mix-poc (kimi_k3_w4a8_32p_mix_in128k_out1k_decode_prefix, 4, test_reg~77367e.txt", 1320, 1380)
win("2218", "github_logs/gh_43867439699/133327323785_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt", 695, 735)
win("2212", "github_logs/gh_43733552254/9_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~45495f.txt", 626, 676)
win("2227", "github_logs/gh_43892530840/133388055851_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", 560, 640)
