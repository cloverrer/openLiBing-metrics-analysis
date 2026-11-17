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
win("2227 tail", "github_logs/gh_43892530840/133388055851_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt", 660, 707)
win("2223", "github_logs/gh_43868646557/133303913207_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt", 700, 775)
