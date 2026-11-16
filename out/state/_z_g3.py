# -*- coding: utf-8 -*-
"""只读探针：在内嵌证据中按正则搜索，输出 filekey:line | text[:280]
用法: python _z_g3.py <day> <comp> <pipe> <regex> <outfile> [maxhits]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def main():
    day, comp, pipe, pat = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    outp = Path(sys.argv[5])
    mx = int(sys.argv[6]) if len(sys.argv) > 6 else 40
    ev = json.loads((AR / day[:4] / day[:7] / day / comp / pipe / "pipeline.evidence.json").read_text(encoding="utf-8"))
    rx = re.compile(pat)
    buf = []
    hits = 0
    for name, body in (ev.get("files") or {}).items():
        lines = body.get("lines") if isinstance(body, dict) else body
        if not isinstance(lines, list):
            continue
        for i, ln in enumerate(lines):
            s = str(ln)
            if rx.search(s):
                buf.append("%s:%d | %s" % (name, i + 1, s.strip()[:280]))
                hits += 1
                if hits >= mx:
                    break
        if hits >= mx:
            break
    outp.write_text("\n".join(buf) + "\n", encoding="utf-8")
    print("hits", hits, "->", outp)


main()
