# -*- coding: utf-8 -*-
"""导出指定记录的关键字段：verdict / githubMeta(失败/取消 jobs) / evidence.github 元数据。"""
import json
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
DAY = ROOT / "out/archive/2026/2026-11/2026-11-16"

WANT = [
    ("MindCluster/Agentsdk~5992cb", 2),
    ("SgLang/nightly-test-npu.yml", 2216),
    ("SgLang/nightly-test-npu.yml", 2217),
    ("SgLang/nightly-test-npu.yml", 2219),
    ("SgLang/nightly-test-npu.yml", 2220),
    ("SgLang/nightly-test-npu.yml", 2221),
    ("SgLang/nightly-test-npu.yml", 2222),
    ("SgLang/nightly-test-npu.yml", 2227),
    ("UBS Core/Nightly-CI-Version-pipeline_BeiMing", 261),
    ("UBS Core/Nightly-CI-Version-pipeline_BeiMing", 262),
]

out = []
for rel, bn in WANT:
    p = DAY / rel / "pipeline.json"
    doc = json.load(io.open(p, encoding="utf-8"))
    for rec in doc.get("records") or []:
        if rec.get("buildNumber") != bn:
            continue
        out.append("######## %s" % rec.get("recordId"))
        out.append("status=%s ftt=%s start=%s end=%s" % (
            rec.get("status"), rec.get("failedTaskType"), rec.get("startedAt"), rec.get("endedAt")))
        out.append("verdict=%s" % json.dumps(rec.get("verdict"), ensure_ascii=False))
        g = ((rec.get("evidence") or {}).get("github")) or {}
        if g:
            out.append("github.runId=%s mode=%s totalJobs=%s complete=%s" % (
                g.get("runId"), g.get("mode"), g.get("totalJobs"), g.get("complete")))
            out.append("  displayTitle=%s" % g.get("displayTitle"))
            out.append("  failedJobs=%s" % json.dumps(g.get("failedJobs"), ensure_ascii=False)[:1500])
            out.append("  cancelledJobs=%s" % json.dumps(g.get("cancelledJobs"), ensure_ascii=False)[:800])
            out.append("  missing=%s" % json.dumps(g.get("missing"), ensure_ascii=False)[:600])
        gm = rec.get("githubMeta")
        if gm:
            out.append("githubMeta=%s" % json.dumps(gm, ensure_ascii=False)[:2000])
        ts = rec.get("tasks") or []
        out.append("tasks=%d" % len(ts))
        for t in ts:
            out.append("   - type=%s job=%s logFile=%s lines=%s" % (
                t.get("type"), (t.get("jobName") or "")[:70], t.get("logFile"), t.get("logLines")))
        out.append("")

Path(ROOT / "out/state/_meta16b.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote", len(out))
