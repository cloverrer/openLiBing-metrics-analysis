# -*- coding: utf-8 -*-
"""探测 UBS Core 失败运行的 T4 任务图谱（任务名/状态/步骤），确认 test/log 分流规则。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib.cdp_exec import load_config, run_page_js  # noqa: E402

cfg = load_config()
PID = "b51d159e1b9d4c6798dcda723e1876db"
PRJ = 300122
RUNS = [
    {"key": "UBS", "rn": "254", "st": "2026-11-10 12:00:06", "status": "FAILED",
     "rid": "435d3a5662b34cba9d5dad58cdaeaa4a", "track": "va", "dims": ["va", "bs"],
     "projectId": PRJ, "pipelineId": PID, "pipelineRunId": "435d3a5662b34cba9d5dad58cdaeaa4a"},
    {"key": "UBS", "rn": "255", "st": "2026-11-10 14:59:38", "status": "FAILED",
     "rid": "53259da75fa0470b99bffe91213721ef", "track": "va", "dims": ["va", "bs"],
     "projectId": PRJ, "pipelineId": PID, "pipelineRunId": "53259da75fa0470b99bffe91213721ef"},
    {"key": "UBS", "rn": "261", "st": "2026-11-13 12:00:04", "status": "FAILED",
     "rid": "8afd6c81382a451aad1649f31cd8d47b", "track": "va", "dims": ["va", "bs"],
     "projectId": PRJ, "pipelineId": PID, "pipelineRunId": "8afd6c81382a451aad1649f31cd8d47b"},
]
out = run_page_js("step_3_details.js",
                  {"runs": RUNS, "delay": 300, "conc": 2, "retry": 2, "backoffMs": 1500},
                  "_probe_ubs_t4.json", cfg, "PROBE-T4")
for d in out.get("details") or []:
    print("\n===== run #%s status=%s err=%s =====" % (d.get("rn"), d.get("rstatus"), d.get("err")))
    data = d.get("data") or {}
    for st in data.get("stages") or []:
        print("  [stage] %s" % st.get("name"))
        for job in st.get("jobs") or []:
            bad = [s for s in (job.get("steps") or []) if s.get("status") not in ("COMPLETED", None)]
            print("    job=%-28s status=%-10s steps=%d badSteps=%d" %
                  (job.get("name"), job.get("status"), len(job.get("steps") or []), len(bad)))
            for s in bad[:3]:
                print("        step=%s status=%s msg=%s" % (s.get("name"), s.get("status"),
                                                           str(s.get("message"))[:120]))
            if bad:
                print("        jobKeys=%s" % list(job.keys()))
