# -*- coding: utf-8 -*-
"""诊断 #83 / #183 两条 11-12 异常记录的归属由来。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.dim_affects import affects_of, day_avail_of  # noqa: E402

CASES = [
    ("2026-11-12", "MindCluster", "MultimodalSDK", "83"),
    ("2026-11-12", "Ascend-CANN", "atb", "183"),
]


def day_dir(d):
    return ROOT / "out" / "archive" / d[:4] / d[:7] / d


def load_day(d):
    p = day_dir(d) / "_day.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def brief_run(h):
    return dict(rn=h.get("rn"), status=h.get("status"), iva=h.get("iva"),
                bc=h.get("bc"), bpc=h.get("bpc"),
                start=h.get("start"), end=h.get("end"),
                prId=h.get("pipelineRunId") or h.get("prId"))


for d, comp, pipe, bn in CASES:
    print("=" * 90)
    print("## %s %s/%s #%s" % (d, comp, pipe, bn))
    pdir = day_dir(d) / comp / pipe
    doc = pipeline_doc.load(pdir) or {}
    steps = doc.get("steps") or {}
    dims = ((steps.get("step_1_lights") or {}).get("pipeline") or {}).get("dims") or []
    rh = (steps.get("step_2_runs") or {}).get("runHistory") or []
    print("  dims=%s  day_avail=%s" % (dims, day_avail_of(rh, d)))
    recs = doc.get("records") or []
    for r in recs:
        if str(r.get("buildNumber")) == bn:
            print("  record: status=%s endedAt=%s date=%s" % (r.get("status"), r.get("endedAt"), r.get("date")))
            print("          light=%s" % json.dumps(r.get("light"), ensure_ascii=False))
            print("          analysis=%s" % json.dumps(r.get("analysis"), ensure_ascii=False))
    print("  runHistory:")
    for h in rh:
        print("   ", json.dumps(brief_run(h), ensure_ascii=False))
    # 检查 11-13 是否有同一 pipelineRunId / 同构建号
    prids = set()
    for h in rh:
        v = h.get("pipelineRunId") or h.get("prId")
        if v:
            prids.add(str(v))
    for other in ["2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]:
        if other == d:
            continue
        odir = day_dir(other) / comp / pipe
        if not odir.is_dir():
            continue
        odoc = pipeline_doc.load(odir) or {}
        osteps = odoc.get("steps") or {}
        orh = (osteps.get("step_2_runs") or {}).get("runHistory") or []
        for h in orh:
            v = str(h.get("pipelineRunId") or h.get("prId") or "")
            if v and v in prids:
                print("  >> 跨日重复 pipelineRunId=%s 在 %s: %s" % (v, other, json.dumps(brief_run(h), ensure_ascii=False)))
