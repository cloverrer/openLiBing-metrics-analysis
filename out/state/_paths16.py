# -*- coding: utf-8 -*-
"""导出各记录的精确 logFile 路径（cites 必须逐字一致）。"""
import json
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
DAY = ROOT / "out/archive/2026/2026-11/2026-11-16"

TARGETS = [
    ("Ascend-CANN", "os", 153), ("MindCluster", "Agentsdk~5992cb", 2),
    ("SgLang", "nightly-test-npu.yml", 2211), ("SgLang", "nightly-test-npu.yml", 2212),
    ("SgLang", "nightly-test-npu.yml", 2213), ("SgLang", "nightly-test-npu.yml", 2214),
    ("SgLang", "nightly-test-npu.yml", 2215), ("SgLang", "nightly-test-npu.yml", 2218),
    ("SgLang", "nightly-test-npu.yml", 2220), ("SgLang", "nightly-test-npu.yml", 2222),
    ("SgLang", "nightly-test-npu.yml", 2223), ("SgLang", "nightly-test-npu.yml", 2224),
    ("SgLang", "nightly-test-npu.yml", 2225), ("SgLang", "nightly-test-npu.yml", 2226),
    ("SgLang", "nightly-test-npu.yml", 2227),
    ("UBS Core", "Nightly-CI-Version-pipeline_BeiMing", 261),
    ("UBS Core", "Nightly-CI-Version-pipeline_BeiMing", 262),
    ("vllm-ascend", "a3.yaml", 16563), ("vllm-ascend", "a3.yaml", 16564),
]

out = []
for comp, pipe, bn in TARGETS:
    p = DAY / comp / pipe / "pipeline.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for rec in d.get("records") or []:
        if rec.get("buildNumber") != bn:
            continue
        out.append("== %s" % rec["recordId"])
        for t in rec.get("tasks") or []:
            if t.get("logFile"):
                out.append("   %s" % t["logFile"])
Path(ROOT / "out/state/_paths16.txt").write_text("\n".join(out), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
