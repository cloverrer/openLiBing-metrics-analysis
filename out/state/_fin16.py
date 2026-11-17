# -*- coding: utf-8 -*-
"""收尾取证：输出剩余待定记录的精确行，用于最终确定 keyError 与 cites。"""
import io, json, re, sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa

OUT = io.open(ROOT / "out/state/_fin16.txt", "w", encoding="utf-8", newline="\n")


def W(*a):
    OUT.write(" ".join(str(x) for x in a) + "\n")


CASES = [
    ("Ascend-CANN/os",
     "job_logs/41_os_153_Build_A3_image.log", r"chmod: cannot access"),
    ("SgLang/nightly-test-npu.yml",
     "github_logs/gh_43733552254/12_nightly-4-npu-a3 _ run (0).txt", r"##\[error\]|exit code|ERROR|failed"),
    ("SgLang/nightly-test-npu.yml",
     "github_logs/gh_43868335184/133302785092_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa, 1, 1, 1, test_registe~6b37f9.txt",
     r"##\[error\]|error:|Error"),
    ("SgLang/nightly-test-npu.yml",
     "github_logs/gh_43892530840/133388055851_multi-node-poc (deepseek_v4_flash_0731_w8a8_1p1d_16p_gpqa_overlap, 1, 1, 1, test~51bfbb.txt",
     r"##\[error\]|error:"),
    ("vllm-ascend/a3.yaml",
     "github_logs/gh_43724674356/132845808301_multi-node (main, MiniMax-M3-w8a8-PP-prefix-PD, MiniMax-M3-w8a8-PP-prefix-PD.yam~0635a2.txt",
     r"aisbench case failed"),
    ("vllm-ascend/a3.yaml",
     "github_logs/gh_43724674356/132845808398_multi-node (main, Kimi-K3-W4A8-A3-1M-PD, Kimi-K3-W4A8-A3-1M-PD.yaml, tests_SIT_c~68088f.txt",
     r"aisbench case failed|FAIL_TAG"),
    ("vllm-ascend/a3.yaml",
     "github_logs/gh_43755516664/132974265350_double-node (releases-v0.30.0, GLM-5.3-Flash-W8A8-130k-PD, GLM-5.3-Flash-W8A8-13~da5de9.txt",
     r"FAIL_TAG|##\[error\]"),
]

ARCH = ROOT / "out/archive/2026/2026-11/2026-11-16"
for comp, relp, pat in CASES:
    base = ARCH / comp
    W("### %s :: %s" % (comp, relp[-60:]))
    text, got = pipeline_doc.evidence_window(base, relp, 1, 200000, max_lines=200000)
    if not got:
        W("   !! 证据不可读")
        continue
    lines = text.split("\n")
    rx = re.compile(pat)
    n = 0
    for i, ln in enumerate(lines, 1):
        if rx.search(ln):
            n += 1
            if n <= 6:
                W("   L%d: %s" % (i, ln.strip()[:400]))
    W("   (命中 %d 行，总 %d 行)" % (n, len(lines)))
OUT.close()
print("done")
