import sys
from pathlib import Path
sys.path.insert(0, str(Path(r".")))
from lib import pipeline_doc
pdir = Path("out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml")
def win(tag, path, a, b):
    t,_ = pipeline_doc.evidence_window(pdir, path, a, b, max_lines=b-a+1)
    print("### ", tag)
    for i,l in enumerate(t.split("\n"), a):
        s=l
        if s.strip():
            print("L%-5d| %s" % (i, s[:220]))
    print("-"*90)
win(2224, "github_logs/gh_43870381982/133309711840_multi-node-mix-poc (kimi_k3_w4a8_32p_mix_in128k_out1k_decode_prefix, 4, test_reg~77367e.txt", 2900, 2960)
win(2225, "github_logs/gh_43874714626/133324841013_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", 520, 580)
win(2226, "github_logs/gh_43888687387/133373908398_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", 640, 700)
win(2227, "github_logs/gh_43892530840/133388055851_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", 600, 640)
