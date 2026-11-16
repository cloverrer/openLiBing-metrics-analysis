# -*- coding: utf-8 -*-
"""4 组跨日重复副本的编译口径与当日 bsDetail 对照。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import iter_archive_days  # noqa: E402

GROUPS = {
    "727649f778a44fbea40e080401a8245e": ("Ascend-CANN", "ops-math"),
    "2c2a0e51da7b4af1a734f4e488aa02cf": ("MindCluster", "MultimodalSDK"),
    "43237995207": ("vllm-ascend", "a2.yaml"),
    "43238001464": ("vllm-ascend", "a3.yaml"),
}


def day_pl(date, comp, pipe):
    p = ROOT / "out" / "archive" / date[:4] / date[:7] / date / "_day.json"
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    for pl in doc.get("pipelines") or []:
        nm = str(pl.get("pipeline") or pl.get("pipelineShortName") or "")
        if nm == pipe or nm.startswith(pipe):
            return pl
    return None


for rid, (comp, pipe) in GROUPS.items():
    print("=" * 80)
    print("## %s  %s/%s" % (rid[:20], comp, pipe))
    for d, _ in iter_archive_days():
        pdir = ROOT / "out" / "archive" / d[:4] / d[:7] / d / comp / pipe
        if not pdir.is_dir():
            continue
        doc = pipeline_doc.load(pdir) or {}
        rh = {str(h.get("rn")): h for h in
              (((doc.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or [])}
        for r in doc.get("records") or []:
            if str(r.get("pipelineRunId") or "") != rid:
                continue
            h = rh.get(str(r.get("buildNumber"))) or {}
            print("  %s #%s status=%s %s→%s bc=%s bpc=%s iva=%s an=%s" % (
                d, r.get("buildNumber"), r.get("status"), r.get("startedAt"),
                r.get("endedAt"), h.get("bc"), h.get("bpc"), h.get("iva"),
                (r.get("analysis") or {}).get("status")))
        pl = day_pl(d, comp, pipe)
        if pl:
            print("     _day bsDetail=%s vaDetail=%s" %
                  (json.dumps(pl.get("bsDetail"), ensure_ascii=False),
                   json.dumps(pl.get("vaDetail"), ensure_ascii=False)))
