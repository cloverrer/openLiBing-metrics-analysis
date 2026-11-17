# -*- coding: utf-8 -*-
import io, re, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa
OUT = io.open(ROOT / "out/state/_fin16c.txt", "w", encoding="utf-8", newline="\n")
base = ROOT / "out/archive/2026/2026-11/2026-11-16/vllm-ascend/a3.yaml"
relp = "github_logs/gh_43755516664/132974265350_double-node (releases-v0.30.0, GLM-5.3-Flash-W8A8-130k-PD, GLM-5.3-Flash-W8A8-13~da5de9.txt"
text, got = pipeline_doc.evidence_window(base, relp, 1, 200000, max_lines=200000)
rx = re.compile(r"aisbench case failed|Benchmark failed|Timeout|timeout|reason:|did not complete|TimeoutError|test_multi_node")
lines = text.split("\n")
n = 0
for i, ln in enumerate(lines, 1):
    if rx.search(ln):
        n += 1
        if n <= 25:
            OUT.write("  L%d: %s\n" % (i, ln.strip()[:600]))
OUT.write("命中 %d / %d\n" % (n, len(lines)))
OUT.close()
print("done")
