# -*- coding: utf-8 -*-
"""列出指定流水线在各归档日的全部运行记录（rid/status/时间/bc/bpc），并标注同日同 rid 重复。"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import iter_archive_days  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pipeline", required=True)
ap.add_argument("--component")
args = ap.parse_args()

seen = {}
for d, ddir in iter_archive_days():
    for comp in sorted(ddir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        if args.component and comp.name != args.component:
            continue
        for pipe in sorted(comp.iterdir()):
            if not pipe.is_dir() or args.pipeline not in pipe.name:
                continue
            doc = pipeline_doc.load(pipe) or {}
            steps = doc.get("steps") or {}
            rh = {str(h.get("rn")): h for h in
                  ((steps.get("step_2_runs") or {}).get("runHistory") or [])}
            for r in doc.get("records") or []:
                rid = str(r.get("pipelineRunId") or "")
                h = rh.get(str(r.get("buildNumber"))) or {}
                ev = bool((r.get("evidence") or {}).get("files"))
                print("%s %s/%s #%-4s rid=%s status=%s %s→%s bc=%s bpc=%s ev=%s an=%s" % (
                    d, comp.name, pipe.name, r.get("buildNumber"), rid[:12],
                    r.get("status"), r.get("startedAt"), r.get("endedAt"),
                    h.get("bc"), h.get("bpc"), ev,
                    (r.get("analysis") or {}).get("status")))
                if rid:
                    seen.setdefault(rid, []).append("%s#%s" % (d, r.get("buildNumber")))
print("---- 同一 pipelineRunId 出现在多个归档日 ----")
for rid, where in seen.items():
    if len(where) > 1:
        print("  %s -> %s" % (rid[:12], ", ".join(where)))
