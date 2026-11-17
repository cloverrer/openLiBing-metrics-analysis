# -*- coding: utf-8 -*-
"""紧凑导出 11-16 各待分析记录的 evidence 清单（jobName / logFile / errorLines）。"""
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
        out.append("### %s  ftt=%s status=%s runs=%s" % (rec["recordId"], rec.get("failedTaskType"),
                                                         rec.get("status"), rec.get("pipelineRunId")))
        for t in rec.get("tasks") or []:
            head = "  [%s] job=%s file=%s lines=%s dl=%s trunc=%s" % (
                t.get("type"), t.get("jobName"), t.get("logFile"), t.get("logLines"),
                t.get("download"), t.get("truncated"))
            out.append(head)
            if t.get("evidenceNote"):
                out.append("    note: %s" % t["evidenceNote"])
            for e in (t.get("errorLines") or [])[:8]:
                out.append("    E %s" % e[:400])
            for s in (t.get("stepErrMsgs") or [])[:3]:
                out.append("    S %s" % s[:200])
            for st in (t.get("subTasks") or [])[:4]:
                out.append("    sub %s file=%s" % (st.get("name"), st.get("logFile")))
                for e in (st.get("errorLines") or [])[:4]:
                    out.append("      sE %s" % e[:300])
        out.append("")

Path(ROOT / "out/state/_evlist16.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote", len(out), "lines")
