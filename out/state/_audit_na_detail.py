# -*- coding: utf-8 -*-
"""列出「失败/取消但 status=na」的记录明细：状态、失败任务类型、证据是否齐、任务数。只读。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import day_pipeline_scope, iter_archive_days  # noqa: E402


def main():
    for date, day_dir in iter_archive_days():
        allowed = day_pipeline_scope(day_dir)
        for comp in sorted(p for p in day_dir.iterdir() if p.is_dir()):
            if comp.name.startswith("_"):
                continue
            for pipe in sorted(p for p in comp.iterdir() if p.is_dir()):
                if allowed is not None and (comp.name, pipe.name) not in allowed:
                    continue
                if not pipeline_doc.path_of(pipe).is_file():
                    continue
                doc = pipeline_doc.load(pipe) or {}
                for i, rec in enumerate(doc.get("records") or []):
                    v = rec.get("verdict") or {}
                    an = rec.get("analysis") or {}
                    if an.get("status") != "na" or v.get("category") == "success":
                        continue
                    ev = rec.get("evidence") or {}
                    tasks = rec.get("tasks") or []
                    bad = [t for t in tasks if t.get("type") == "test"]
                    logs = [t for t in tasks if t.get("type") == "log"]
                    print("%s %s/%s #%s" % (date, comp.name, pipe.name, rec.get("buildNumber")))
                    print("    status=%s ftt=%s cat=%s conf=%s va=%s bs=%s"
                          % (rec.get("status"), rec.get("failedTaskType"),
                             v.get("category"), v.get("confidence"),
                             (rec.get("light") or {}).get("vaRate"),
                             (rec.get("light") or {}).get("bsRate")))
                    print("    tasks=%d(测试%d/日志%d) cases=%d errors=%d evidenceFiles=%d missing=%s"
                          % (len(tasks), len(bad), len(logs), len(rec.get("cases") or []),
                             len(rec.get("errorMessages") or []), len(ev.get("files") or []),
                             ev.get("missing") or []))
                    for t in tasks[:4]:
                        print("      · [%s] %s log=%s errLines=%d empty=%s stepErr=%d"
                              % (t.get("type"), t.get("jobName"), t.get("logFile") or "--",
                                 len(t.get("errorLines") or []), t.get("emptyTestResult"),
                                 len(t.get("stepErrMsgs") or [])))


if __name__ == "__main__":
    main()
