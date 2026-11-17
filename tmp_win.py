import sys
from pathlib import Path
sys.path.insert(0, str(Path(r".")))
from lib import pipeline_doc
pdir = Path("out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml")
def win(path, a, b):
    t,_ = pipeline_doc.evidence_window(pdir, path, a, b, max_lines=b-a+1)
    for i,l in enumerate(t.split("\n"), a):
        print("L%-5d| %s" % (i, l[:230]))
    print("-"*80)
print("### 2220 (exit code, no explicit err)")
win("github_logs/gh_43868335184/133302785092_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt", 250, 344)
