# -*- coding: utf-8 -*-
"""综合只读探针：输出指定归档日 pending 记录的结构与证据文件清单。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def evidence_files(pdir):
    ev = pdir / "pipeline.evidence.json"
    if not ev.is_file():
        return {}
    doc = load(ev)
    return doc.get("files") or {}


def main():
    day = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else ""
    outp = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    buf = []
    P = lambda s: buf.append(s)  # noqa: E731
    day_dir = AR / day[:4] / day[:7] / day
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        if want and want.lower() not in comp.name.lower():
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            ev = evidence_files(pipe)
            for rec in doc.get("records") or []:
                an = rec.get("analysis") or {}
                if an.get("status") != "pending":
                    continue
                v = rec.get("verdict") or {}
                light = rec.get("light") or {}
                P("#" * 70)
                P("RID=%s | cat=%s | ftt=%s | status=%s | VA=%s BS=%s"
                  % (rec.get("recordId"), v.get("category"), rec.get("failedTaskType"),
                     rec.get("status"), light.get("vaRate"), light.get("bsRate")))
                P("  pipeline=%s platform=%s" % (rec.get("pipeline"), rec.get("platform")))
                for t in rec.get("tasks") or []:
                    P("  TASK name=%s type=%s status=%s logFile=%s"
                      % (t.get("name"), t.get("type"), t.get("status"), t.get("logFile")))
                    for c in t.get("cases") or []:
                        if str(c.get("state") or "").lower() in ("failed", "fail", "error"):
                            P("     CASE state=%s desc=%s localLog=%s"
                              % (c.get("state"), (c.get("description") or "")[:160],
                                 c.get("localLog")))
                for st in rec.get("subTasks") or []:
                    P("  SUB name=%s type=%s status=%s logFile=%s"
                      % (st.get("name"), st.get("type"), st.get("status"), st.get("logFile")))
                em = rec.get("errorMessages") or []
                P("  errorMessages=%d" % len(em))
                for e in em[:8]:
                    if isinstance(e, dict):
                        P("     EM level=%s src=%s line=%s msg=%s"
                          % (e.get("level"), e.get("source"), e.get("line"),
                             str(e.get("message"))[:300]))
                    else:
                        P("     EM %s" % str(e)[:300])
                gj = rec.get("githubJob") or {}
                if gj:
                    P("  GH conclusion=%s note=%s url=%s"
                      % (gj.get("conclusion"), gj.get("evidenceNote"), gj.get("htmlUrl")))
                tr = rec.get("testResults") or {}
                if tr:
                    P("  TR keys=%s" % list(tr.keys()))
                    for k, val in tr.items():
                        P("     %s=%s" % (k, str(val)[:300]))
                P("  EVFILES=%d" % len(ev))
                for k, v2 in ev.items():
                    P("     %s (%d lines)" % (k, (v2 or {}).get("lineCount") or 0))
    text = "\n".join(buf) + "\n"
    if outp:
        outp.write_text(text, encoding="utf-8")
        sys.stdout.write("written %d lines -> %s\n" % (len(buf), outp))
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


main()
