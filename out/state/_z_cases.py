# -*- coding: utf-8 -*-
"""只读探针：逐用例打印 name/localLog/错误行/deepHits，并可按证据文件统计签名命中。
用法: python _z_cases.py <day> <comp> <pipe> <outfile>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def main():
    day, comp, pipe = sys.argv[1], sys.argv[2], sys.argv[3]
    outp = Path(sys.argv[4])
    base = AR / day[:4] / day[:7] / day / comp / pipe
    doc = json.loads((base / "pipeline.json").read_text(encoding="utf-8"))
    ev = json.loads((base / "pipeline.evidence.json").read_text(encoding="utf-8"))
    files = ev.get("files") or {}
    buf = []
    P = lambda s="": buf.append(s)
    for ri, rec in enumerate(doc.get("records") or []):
        P("#" * 80)
        P("record[%d] %s" % (ri, rec.get("recordId")))
        for c in rec.get("cases") or []:
            lf = c.get("localLog") or "--"
            dh = c.get("deepHits")
            P("- %s | %s | errCount=%s" % (c.get("name"), lf, c.get("errorCount")))
            P("    desc: %s" % (c.get("description") or "")[:220])
            for em in c.get("errorMessages") or []:
                P("    em L%s %s | %s" % (em.get("line"), em.get("level"), (em.get("msg") or "")[:200]))
            if dh:
                P("    deepHits: %s" % json.dumps(dh, ensure_ascii=False)[:600])
            # 统计该 case 证据文件里的关键签名
            body = files.get(lf)
            if isinstance(body, dict):
                lines = body.get("lines") or []
                txt = "\n".join(str(x) for x in lines)
                for pat, label in (("hcclCommInitRootInfoConfig", "HCCL"),
                                   ("topkNum", "TOPK"),
                                   ("accuracy not passed", "ACC")):
                    n = len(re.findall(pat, txt))
                    if n:
                        P("    sig %s: %d" % (label, n))
    outp.write_text("\n".join(buf) + "\n", encoding="utf-8")
    print("wrote", len(buf), "->", outp)


main()
