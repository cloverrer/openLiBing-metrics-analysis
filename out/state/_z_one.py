# -*- coding: utf-8 -*-
"""只读探针：打印内嵌证据中指定文件若干行的完整原文（不截断）。
用法: python _z_one.py <day> <comp> <pipe> <filekey-substr> <line[,line...]> [outfile]
"""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def main():
    day, comp, pipe, sub = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    want = [int(x) for x in sys.argv[5].split(",")]
    outp = Path(sys.argv[6]) if len(sys.argv) > 6 else None
    ev = json.loads((AR / day[:4] / day[:7] / day / comp / pipe / "pipeline.evidence.json").read_text(encoding="utf-8"))
    buf = []
    for name, body in (ev.get("files") or {}).items():
        if sub not in name:
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        if not isinstance(lines, list):
            continue
        buf.append("=== %s (total %d)" % (name, len(lines)))
        for ln in want:
            if 1 <= ln <= len(lines):
                txt = html.unescape(re.sub(r"<[^>]+>", "", str(lines[ln - 1]))).strip()
                buf.append("[L%d] %s" % (ln, txt))
    txt = "\n".join(buf)
    if outp:
        outp.write_text(txt, encoding="utf-8")
        print("wrote", outp)
    else:
        print(txt)


main()
