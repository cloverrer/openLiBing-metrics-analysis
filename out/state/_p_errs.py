# -*- coding: utf-8 -*-
"""只读探针：抽取 case_logs HTML 中 ERROR/FAILED 行的 msg 文本（去标签）。
用法: python _p_errs.py <day> <pipeSubstr> <caseFileSubstr> <outfile> [maxN]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"

day, psub, csub, outp = sys.argv[1:5]
maxn = int(sys.argv[5]) if len(sys.argv) > 5 else 200
day_dir = AR / day[:4] / day[:7] / day
TAG = re.compile(r"<[^>]+>")
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
            if csub not in k:
                continue
            lines = [str(x).rstrip("\r") for x in (files[k] or {}).get("lines") or []]
            for i, s in enumerate(lines, 1):
                if ("class='ERROR'" in s or "class=\"ERROR\"" in s or "ERROR</td>" in s
                        or "FAILED" in s or "step-error" in s):
                    txt = TAG.sub("", lines[i] if i < len(lines) else "")
                    nxt = lines[i] if i < len(lines) else ""
                    m = re.search(r'msg-scroll">(.*?)</div>', nxt)
                    msg = TAG.sub("", m.group(1)) if m else ""
                    if msg.strip():
                        buf.append("[L%d] %s" % (i, msg.strip()[:220]))
            buf.append("== total lines: %d" % len(lines))
Path(outp).write_text("\n".join(buf[:maxn]) + "\n", encoding="utf-8")
print("wrote %d -> %s" % (min(len(buf), maxn), outp))
