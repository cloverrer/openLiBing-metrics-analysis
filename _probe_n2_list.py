# -*- coding: utf-8 -*-
"""探测 UBS Core 单流水线的 N2 全量记录，打印逐条关键字段。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib.cdp_exec import load_config, run_page_js  # noqa: E402

cfg = load_config()
PIPE = {"key": "UBS|Nightly-CI-Version-pipeline_BeiMing",
        "projectId": 300122,
        "pipelineId": "b51d159e1b9d4c6798dcda723e1876db"}
out = run_page_js("step_2_dashboard.js",
                  {"startDate": "2026-11-09", "endDate": "2026-11-14",
                   "pageSize": 100, "delay": 300, "conc": 1,
                   "maxTry": 3, "retryBackoffMs": [1000, 2000],
                   "pipelines": [PIPE]},
                  "_probe_n2_list.json", cfg, "PROBE-N2")
d = (out.get("dash") or {}).get(PIPE["key"]) or {}
recs = (d.get("data") or {}).get("records") or []
print("code=%s total=%s records=%d" % (d.get("code"), (d.get("data") or {}).get("total"), len(recs)))
for r in sorted(recs, key=lambda x: str(x.get("pipelineRunNumber"))):
    print(json.dumps({k: r.get(k) for k in (
        "pipelineRunNumber", "pipelineRunId", "pipelineStatus", "isVersionAvailable",
        "buildCount", "buildPassCount", "failedTaskType", "casePassRate",
        "pipelineRunStarttime", "pipelineRunEndtime", "platform", "displayTitle", "event")},
        ensure_ascii=False))
