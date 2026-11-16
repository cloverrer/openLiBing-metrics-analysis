# -*- coding: utf-8 -*-
"""导出 #83 的完整记录关键字段，供写回根因参考。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

pdir = ROOT / "out" / "archive" / "2026" / "2026-11" / "2026-11-12" / "MindCluster" / "MultimodalSDK"
doc = pipeline_doc.load(pdir) or {}
for r in doc.get("records") or []:
    if str(r.get("buildNumber")) == "83":
        slim = {k: r.get(k) for k in
                ("recordId", "status", "failedTaskType", "startedAt", "endedAt",
                 "verdict", "counts", "analysis", "links")}
        print(json.dumps(slim, ensure_ascii=False, indent=2))
        print("--- tasks (jobName/type/fallback/evidenceNote/logFile/errorLines count/cases) ---")
        for t in r.get("tasks") or []:
            print(json.dumps({
                "jobName": t.get("jobName"), "type": t.get("type"),
                "fallback": t.get("fallback"), "logFile": t.get("logFile"),
                "evidenceNote": t.get("evidenceNote"),
                "nErrorLines": len(t.get("errorLines") or []),
                "stepErrMsgs": t.get("stepErrMsgs"), "jobErrMsg": t.get("jobErrMsg"),
                "nCases": len(t.get("cases") or []),
                "cases": [{"name": c.get("name"), "msgs": c.get("errorMessages"),
                           "deepHits": c.get("deepHits"), "desc": c.get("description")}
                          for c in (t.get("cases") or [])],
            }, ensure_ascii=False, indent=2))
        print("--- errorMessages ---")
        print(json.dumps(r.get("errorMessages"), ensure_ascii=False, indent=2))
        print("--- evidence ---")
        print(json.dumps(r.get("evidence"), ensure_ascii=False, indent=2))
