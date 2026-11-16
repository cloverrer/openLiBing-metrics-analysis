# -*- coding: utf-8 -*-
"""只读探针：按文件子串 + 行窗口打印内嵌证据。
用法: python _p_win.py <day> <comp/pipe-rid-or-substr> <pathSubstr> <l1> <l2> <outfile>
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"

day, key, psub, l1, l2, outp = sys.argv[1:7]
l1, l2 = int(l1), int(l2)
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
        if key and key not in relkey:
            continue
        files = (json.loads(evf.read_text(encoding="utf-8")).get("files") or {})
        for k in sorted(files):
            if psub not in k:
                continue
            v = files[k]
            if isinstance(v, dict):
                lines = [str(x).rstrip("\r") for x in (v.get("lines") or [])]
            elif isinstance(v, list):
                lines = [str(x).rstrip("\r") for x in v]
            else:
                lines = str(v).splitlines()
            buf.append("===== %s" % k)
            for i in range(l1, min(l2, len(lines)) + 1):
                buf.append("[L%d] %s" % (i, str(lines[i - 1])[:400]))
            buf.append("")
Path(outp).write_text("\n".join(buf) + "\n", encoding="utf-8")
print("lines=%d" % len(buf))
