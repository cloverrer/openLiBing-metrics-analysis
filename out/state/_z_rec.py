# -*- coding: utf-8 -*-
"""只读探针：打印归档 pipeline.json 指定组件内每条记录的结构概览（cases 的键与首个错误行映射）。
用法: python _z_rec.py <day> <comp> <pipe> <outfile>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def main():
    day, comp, pipe = sys.argv[1], sys.argv[2], sys.argv[3]
    outp = Path(sys.argv[4])
    doc = json.loads((AR / day[:4] / day[:7] / day / comp / pipe / "pipeline.json").read_text(encoding="utf-8"))
    buf = []
    P = lambda s="": buf.append(s)
    P("TOP KEYS: %s" % list(doc.keys()))
    for ri, rec in enumerate(doc.get("records") or []):
        P("=" * 80)
        P("record[%d] keys: %s" % (ri, list(rec.keys())))
        P("recordId=%s build=%s" % (rec.get("recordId"), rec.get("buildNumber")))
        cases = rec.get("cases") or []
        P("cases(%d) sample keys: %s" % (len(cases), list(cases[0].keys()) if cases else None))
        for c in cases[:3]:
            P("  CASE full: %s" % json.dumps(c, ensure_ascii=False)[:1200])
        errs = rec.get("errorMessages") or []
        P("errorMessages(%d) sample: %s" % (len(errs), json.dumps(errs[0], ensure_ascii=False)[:400] if errs else None))
        tasks = rec.get("tasks") or []
        P("tasks(%d) keys: %s" % (len(tasks), list(tasks[0].keys()) if tasks else None))
        if tasks:
            P("  task0: %s" % json.dumps({k: v for k, v in tasks[0].items() if k != "errorLines"}, ensure_ascii=False)[:800])
    outp.write_text("\n".join(buf) + "\n", encoding="utf-8")
    print("wrote", len(buf), "->", outp)


main()
