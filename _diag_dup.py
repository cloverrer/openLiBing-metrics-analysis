# -*- coding: utf-8 -*-
"""全仓扫描：同一 pipelineRunId 出现在多个归档日（跨午夜陈旧副本）的完整清单。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import iter_archive_days  # noqa: E402

seen = {}
for d, ddir in iter_archive_days():
    for comp in sorted(ddir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            if not pipe.is_dir():
                continue
            doc = pipeline_doc.load(pipe) or {}
            for r in doc.get("records") or []:
                rid = str(r.get("pipelineRunId") or "")
                if not rid:
                    continue
                seen.setdefault(rid, []).append((
                    d, comp.name, pipe.name, r.get("buildNumber"), r.get("status"),
                    r.get("startedAt"), r.get("endedAt"),
                    (r.get("analysis") or {}).get("status")))

n = 0
for rid, rows in seen.items():
    if len(rows) > 1:
        n += 1
        print("== pipelineRunId %s  出现 %d 次" % (rid, len(rows)))
        for row in sorted(rows, key=lambda x: str(x[0])):
            print("   %s %s/%s #%s status=%s %s→%s an=%s" % row)
print("---- 跨日重复 runId 共 %d 组 ----" % n)
