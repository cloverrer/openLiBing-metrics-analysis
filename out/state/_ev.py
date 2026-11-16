# -*- coding: utf-8 -*-
"""只读探针：批量输出 2026-11-09 待分析记录的候选关键报错原文行。
用法: python _ev.py <day> <ridFilter> <outfile>
对每条 pending 记录，输出 errorMessages[] 中带行号的证据原文（去重、截断 400 字符）。
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
    filt = sys.argv[2] if len(sys.argv) > 2 else ""
    outp = Path(sys.argv[3]) if len(sys.argv) > 3 else (Path(__file__).parent / "_ev_out.txt")
    day_dir = AR / day[:4] / day[:7] / day
    buf = []
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            evf = pipe / "pipeline.evidence.json"
            files = (load(evf).get("files") or {}) if evf.is_file() else {}
            for rec in doc.get("records") or []:
                rid = str(rec.get("recordId"))
                if (rec.get("analysis") or {}).get("status") != "pending":
                    continue
                if filt and filt.lower() not in rid.lower():
                    continue
                buf.append("========")
                buf.append("RID=%s ftt=%s status=%s" % (rid, rec.get("failedTaskType"), rec.get("status")))
                seen = set()
                for em in rec.get("errorMessages") or []:
                    src = em.get("source") or em.get("src")
                    ln = em.get("line")
                    if not src or not ln:
                        continue
                    key = (src, ln)
                    if key in seen:
                        continue
                    seen.add(key)
                    fl = files.get(src) or {}
                    lines = [str(x).rstrip("\r") for x in (fl.get("lines") or [])]
                    txt = em.get("text") or (lines[ln - 1] if 1 <= ln <= len(lines) else "<NO LINE>")
                    buf.append("[%s:L%s] %s" % (src, ln, str(txt)[:400]))
                # 再补 cases 的 localLog 首行
                for t in rec.get("tasks") or []:
                    for c in t.get("cases") or []:
                        ll = c.get("localLog")
                        if ll and ll not in seen:
                            seen.add(ll)
                            buf.append("(case %s) %s" % (ll, str(c.get("description"))[:300]))
    outp.write_text("\n".join(buf) + "\n", encoding="utf-8")
    sys.stdout.write("wrote %d lines -> %s\n" % (len(buf), outp))


main()
