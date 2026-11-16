# -*- coding: utf-8 -*-
"""只读探针：打印内嵌证据中命中关键词的整行原文（不截断），供挑选 keyError/cites。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ARCH = ROOT / "out" / "archive"


def main():
    day, comp, pipe = sys.argv[1], sys.argv[2], sys.argv[3]
    pat = re.compile(sys.argv[4])
    subs = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "-" else None
    width = int(sys.argv[6]) if len(sys.argv) > 6 else 1000
    base = ARCH / day[:4] / day[:7] / day / comp / pipe
    ev = json.loads((base / "pipeline.evidence.json").read_text(encoding="utf-8"))
    n = 0
    for name, body in (ev.get("files") or {}).items():
        if subs and subs not in name:
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        lines = lines if isinstance(lines, list) else []
        for i, ln in enumerate(lines):
            s = str(ln)
            if pat.search(s):
                n += 1
                if n > 40:
                    break
                print("%s:L%d | %s" % (name, i + 1, s[:width]))
    print("== hits:", n)


main()
