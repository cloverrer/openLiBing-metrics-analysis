# -*- coding: utf-8 -*-
import io, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa
OUT = io.open(ROOT / "out/state/_fin16b.txt", "w", encoding="utf-8", newline="\n")


def dump(comp, relp, spans):
    base = ROOT / "out/archive/2026/2026-11/2026-11-16" / comp
    OUT.write("### %s :: %s\n" % (comp, relp[-50:]))
    text, got = pipeline_doc.evidence_window(base, relp, 1, 200000, max_lines=200000)
    if not got:
        OUT.write("   !! 不可读\n")
        return
    lines = text.split("\n")
    for a, b in spans:
        for i in range(a, min(b, len(lines)) + 1):
            OUT.write("  L%d: %s\n" % (i, lines[i - 1].strip()[:900]))
        OUT.write("  ---\n")


dump("vllm-ascend/a3.yaml",
     "github_logs/gh_43724674356/132845808301_multi-node (main, MiniMax-M3-w8a8-PP-prefix-PD, MiniMax-M3-w8a8-PP-prefix-PD.yam~0635a2.txt",
     [(2305, 2315), (2365, 2380)])
dump("vllm-ascend/a3.yaml",
     "github_logs/gh_43724674356/132845808398_multi-node (main, Kimi-K3-W4A8-A3-1M-PD, Kimi-K3-W4A8-A3-1M-PD.yaml, tests_SIT_c~68088f.txt",
     [(2338, 2350), (2425, 2445)])
dump("vllm-ascend/a3.yaml",
     "github_logs/gh_43755516664/132974265350_double-node (releases-v0.30.0, GLM-5.3-Flash-W8A8-130k-PD, GLM-5.3-Flash-W8A8-13~da5de9.txt",
     [(2930, 2950)])
OUT.close()
print("done")
