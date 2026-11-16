# -*- coding: utf-8 -*-
"""只读探针：按记录输出被引用证据文件的关键错误行（带原始行号）。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"
PAT = re.compile(r"(error|fail|fatal|timeout|exception|cannot|unable|refused|denied|"
                 r"not found|no space|killed|abort|cancel|assert|traceback|"
                 r"invalid|empty|not exist|no name|insufficient|oom|out of memory)",
                 re.I)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


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
            evf = pipe / "pipeline.evidence.json"
            files = (load(evf).get("files") or {}) if evf.is_file() else {}
            for rec in doc.get("records") or []:
                if (rec.get("analysis") or {}).get("status") != "pending":
                    continue
                P("=" * 72)
                P("RID=%s" % rec.get("recordId"))
                # 1) errorMessages 带的行号：直接取原文
                for e in rec.get("errorMessages") or []:
                    if not isinstance(e, dict):
                        continue
                    src = str(e.get("source") or "")
                    ln = e.get("line")
                    if src in files and ln:
                        lines = (files[src] or {}).get("lines") or []
                        try:
                            t = str(lines[int(ln) - 1])[:400]
                        except (IndexError, ValueError):
                            t = "<line out of range>"
                        P("  EM-LINE %s:%s | %s" % (src, ln, t))
                # 2) 被引用的日志文件：grep 关键错误行
                refs = []
                for t in rec.get("tasks") or []:
                    if t.get("logFile"):
                        refs.append(str(t["logFile"]))
                    for c in t.get("cases") or []:
                        if c.get("localLog"):
                            refs.append(str(c["localLog"]))
                for st in rec.get("subTasks") or []:
                    if st.get("logFile"):
                        refs.append(str(st["logFile"]))
                seen = set()
                for rp in refs:
                    if rp in seen or rp not in files:
                        continue
                    seen.add(rp)
                    lines = (files[rp] or {}).get("lines") or []
                    hits = 0
                    for i, s in enumerate(lines, 1):
                        s = str(s).rstrip("\r")
                        if PAT.search(s):
                            P("  GREP %s:%d | %s" % (rp, i, s.strip()[:300]))
                            hits += 1
                            if hits >= 18:
                                P("  GREP %s | ... (truncated)" % rp)
                                break
    text = "\n".join(buf) + "\n"
    if outp:
        outp.write_text(text, encoding="utf-8")
        sys.stdout.write("written %d lines -> %s\n" % (len(buf), outp))
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


main()
