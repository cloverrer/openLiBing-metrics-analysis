# -*- coding: utf-8 -*-
"""通用只读探针：在指定流水线内嵌证据中，按关键词正则找出带行号的原文，供挑选 keyError/cites。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ARCH = ROOT / "out" / "archive"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    day, comp, pipe = sys.argv[1], sys.argv[2], sys.argv[3]
    pat = re.compile(sys.argv[4])
    subs = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] != "-" else None
    bufr = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    base = ARCH / day[:4] / day[:7] / day / comp / pipe
    ev = load(base / "pipeline.evidence.json")
    files = ev.get("files") or {}
    out = []
    for name, body in files.items():
        if subs and subs not in name:
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        lines = lines if isinstance(lines, list) else []
        for i, ln in enumerate(lines):
            s = str(ln)
            if pat.search(s):
                lo = max(0, i - bufr)
                hi = min(len(lines), i + bufr + 1)
                out.append("---- %s (total %d)" % (name, len(lines)))
                for k in range(lo, hi):
                    out.append("[L%d] %s" % (k + 1, str(lines[k])[:300]))
    print("\n".join(out) if out else "(no hit)")
    print("== hits:", len(out))


main()
