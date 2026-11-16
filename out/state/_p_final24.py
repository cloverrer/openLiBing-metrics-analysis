# -*- coding: utf-8 -*-
"""只读探针：批量导出指定归档日全部 pending 记录的分析输入（含 errorMessages 的 source:line）。
用法: python _p_final24.py <day> <outfile> [limit]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day = sys.argv[1]
    outp = Path(sys.argv[2])
    lim = int(sys.argv[3]) if len(sys.argv) > 3 else 25
    buf = []
    P = lambda s="": buf.append(s)
    day_dir = AR / day[:4] / day[:7] / day
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            for rec in doc.get("records") or []:
                if (rec.get("analysis") or {}).get("status") != "pending":
                    continue
                v = rec.get("verdict") or {}
                lt = rec.get("light") or {}
                P("=" * 90)
                P("RID=%s | #%s | ftt=%s | status=%s | cat=%s | VA=%s BS=%s" % (
                    rec.get("recordId"), rec.get("buildNumber"), rec.get("failedTaskType"),
                    rec.get("status"), v.get("category"), lt.get("vaRate"), lt.get("bsRate")))
                P("  起止: %s -> %s" % (rec.get("startedAt"), rec.get("endedAt")))
                ev = rec.get("evidence") or {}
                if ev.get("missing"):
                    P("  证据缺口: %s" % ev.get("missing"))
                for i, e in enumerate((v.get("basis") or [])[:6]):
                    P("  basis[%d]: %s" % (i, e))
                tasks = rec.get("tasks") or []
                P("  -- tasks(%d) --" % len(tasks))
                for t in tasks:
                    P("    [%s] %s | log=%s | errLines=%d" % (
                        t.get("type"), t.get("jobName"), t.get("logFile") or "--",
                        len(t.get("errorLines") or [])))
                    for el in (t.get("errorLines") or [])[:4]:
                        if isinstance(el, dict):
                            P("        line=%s | %s" % (el.get("line"), (el.get("text") or el.get("message") or "")[:200]))
                        else:
                            P("        %s" % str(el)[:200])
                errs = rec.get("errorMessages") or []
                P("  -- errorMessages(%d) --" % len(errs))
                for e in errs[:lim]:
                    P("    %s:%s | %s" % (e.get("source") or e.get("src") or "",
                                          e.get("line"), (e.get("text") or e.get("message") or "")[:240]))
                cases = rec.get("cases") or []
                if cases:
                    P("  -- cases(%d) --" % len(cases))
                    for c in cases[:lim]:
                        fe = ((c.get("errorMessages") or [{}])[0] or {})
                        P("    %s [%s] %s:%s | %s" % (
                            c.get("name"), c.get("state"), fe.get("source") or fe.get("src") or "",
                            fe.get("line"), (fe.get("text") or fe.get("message") or "")[:200]))
    outp.write_text("\n".join(buf) + "\n", encoding="utf-8")
    sys.stdout.write("wrote %d lines -> %s\n" % (len(buf), outp))


main()
