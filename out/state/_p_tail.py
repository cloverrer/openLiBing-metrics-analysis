# -*- coding: utf-8 -*-
"""只读探针：打印某证据文件的尾部 N 行（带行号）。
用法: python _p_tail.py <day> <pipeSubstr> <fileSubstr> <N> <outfile>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"
day, psub, fsub, n, outp = sys.argv[1:6]
n = int(n)
day_dir = AR / day[:4] / day[:7] / day
buf = []
for comp in sorted(day_dir.iterdir()):
    if not comp.is_dir() or comp.name.startswith("_"):
        continue
    for pipe in sorted(comp.iterdir()):
        evf = pipe / "pipeline.evidence.json"
        if not evf.is_file():
            continue
        relkey = str(pipe.relative_to(day_dir)).replace("\\", "/")
        if psub not in relkey:
            continue
        files = (json.loads(evf.read_text(encoding="utf-8")).get("files") or {})
        for k in sorted(files):
            if fsub not in k:
                continue
            lines = [str(x).rstrip("\r") for x in (files[k] or {}).get("lines") or []]
            buf.append("===== %s (total %d)" % (k, len(lines)))
            for i in range(max(1, len(lines) - n + 1), len(lines) + 1):
                buf.append("[L%d] %s" % (i, lines[i - 1][:400]))
Path(outp).write_text("\n".join(buf) + "\n", encoding="utf-8")
print("wrote %d -> %s" % (len(buf), outp))
