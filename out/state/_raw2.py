# -*- coding: utf-8 -*-
"""只读：github 记录 jobName / errorLines / jobErrMsg / evidence.github。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day, want = sys.argv[1], sys.argv[2].replace("/", "|")
    outp = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parent / "_ghmeta.txt"
    day_dir = AR / day[:4] / day[:7] / day
    out = []
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            for rec in doc.get("records") or []:
                if str(rec.get("recordId")).replace("/", "|") != want:
                    continue
                out.append("RID=%s status=%s build=%s run=%s" % (
                    rec.get("recordId"), rec.get("status"), rec.get("buildNumber"), rec.get("pipelineRunId")))
                ev = rec.get("evidence") or {}
                out.append("evidence.github=%s" % json.dumps(ev.get("github"), ensure_ascii=False)[:6000])
                out.append("evidence.missing=%s" % json.dumps(ev.get("missing"), ensure_ascii=False)[:800])
                for t in rec.get("tasks") or []:
                    gj = t.get("githubJob") or {}
                    out.append("TASK %s conclusion=%s note=%s" % (t.get("jobName"), gj.get("conclusion"), t.get("evidenceNote")))
                    out.append("  jobErrMsg=%s" % json.dumps(t.get("jobErrMsg"), ensure_ascii=False)[:1200])
                    out.append("  stepErrMsgs=%s" % json.dumps(t.get("stepErrMsgs"), ensure_ascii=False)[:1200])
                    out.append("  errorLines=%s" % json.dumps(t.get("errorLines"), ensure_ascii=False)[:2500])
    outp.write_text("\n".join(out) + "\n", encoding="utf-8")
    sys.stdout.write("wrote -> %s\n" % outp)


main()
