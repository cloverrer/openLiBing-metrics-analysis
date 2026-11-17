# -*- coding: utf-8 -*-
"""探测 T6(测试报告)/T5(日志分页+导出) 对 UBS Core 失败任务的返回内容。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib.cdp_exec import load_config, run_page_js  # noqa: E402

cfg = load_config()
PID = "b51d159e1b9d4c6798dcda723e1876db"
PRJ = 300122
RID = "53259da75fa0470b99bffe91213721ef"   # #255
ITEMS = [
    {"key": "UBS", "pipeline": "Nightly-CI-Version-pipeline_BeiMing",
     "pipelineName": "Nightly-CI-Version-pipeline_BeiMing", "rn": "255", "st": "FAILED",
     "projectId": PRJ, "pipelineId": PID, "rid": RID,
     "jobId": "f5b5bc58a1bc40618e81720ee84323cb", "jobName": "Test_ubturbo-smap",
     "stepIds": ["5ae9c307362b4fca93f1a31db135430e"],
     "steps": [{"id": "5ae9c307362b4fca93f1a31db135430e", "name": "Test_ubturbo-smap",
                "status": "FAILED", "errMsg": None,
                "lastDispatchId": "4e09bf4bbfb3450d98e78d181f3561f4"}],
     "jobErrMsg": None, "jobLastDispatchId": None},
    {"key": "UBS", "pipeline": "Nightly-CI-Version-pipeline_BeiMing",
     "pipelineName": "Nightly-CI-Version-pipeline_BeiMing", "rn": "255", "st": "FAILED",
     "projectId": PRJ, "pipelineId": PID, "rid": RID,
     "jobId": "109fd3762b5543dbb29d63fa21e10c61", "jobName": "Deploy_ubs-comm",
     "stepIds": ["995b305a2f58481697f8aa720e4c4759"],
     "steps": [{"id": "995b305a2f58481697f8aa720e4c4759", "name": "Deploy_ubs-comm",
                "status": "FAILED", "errMsg": '{"errorMessage":"[jenkins]任务执行失败!"}',
                "lastDispatchId": "8c3993a187074e99a00bbbec28c4ebd1"}],
     "jobErrMsg": '{"errorMessage":"[jenkins]任务执行失败!","errorCode":"DEV-JENKINS-10012"}',
     "jobLastDispatchId": "8c3993a187074e99a00bbbec28c4ebd1"},
]

print("=== T6 测试报告 ===")
out6 = run_page_js("step_4_testreport.js",
                   {"items": ITEMS, "pageSize": 100, "delay": 300, "conc": 2,
                    "maxTry": 3, "retryBackoffMs": [1000, 2000]},
                   "_probe_ubs_t6.json", cfg, "PROBE-T6")
print(json.dumps(out6, ensure_ascii=False)[:2000])

print("\n=== T5 分页日志 ===")
out5 = run_page_js("step_5_logs.js",
                   {"items": ITEMS, "logLimit": 2000, "maxErrLines": 40, "delay": 300,
                    "conc": 2, "maxTry": 3, "retryBackoffMs": [1000, 2000]},
                   "_probe_ubs_t5p.json", cfg, "PROBE-T5P")
for r in out5.get("results") or []:
    print("  job=%s code=%s has_more=%s tailLen=%s errLines=%d" % (
        r.get("jobName"), r.get("code"), r.get("has_more"),
        len(r.get("logTail") or ""), len(r.get("errorLines") or [])))
    print("     tail: %s" % json.dumps((r.get("logTail") or "")[-400:], ensure_ascii=False))
    print("     errs: %s" % json.dumps((r.get("errorLines") or [])[:5], ensure_ascii=False))
print("  errors=%s" % json.dumps(out5.get("errors") or [], ensure_ascii=False)[:600])

print("\n=== T5 导出 ===")
out5e = run_page_js("step_5_export.js",
                    {"items": ITEMS, "delay": 300, "conc": 2, "maxTry": 3,
                     "retryBackoffMs": [1000, 2000], "pollTimeoutMs": 120000},
                    "_probe_ubs_t5e.json", cfg, "PROBE-T5E")
for r in out5e.get("results") or []:
    print("  job=%s export=%s reason=%s url=%s" % (
        r.get("jobName"), r.get("export"), str(r.get("reason"))[:200], str(r.get("url"))[:160]))
