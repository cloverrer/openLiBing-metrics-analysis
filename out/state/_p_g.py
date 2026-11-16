# -*- coding: utf-8 -*-
"""只读探针：在指定记录的指定证据文件里按正则搜索，输出 UTF-8 结果。
用法: python _p_g.py <day> <rid> <pathSubstr> <regex> <outfile> [ctx]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day, rid, psub, pat, outp = sys.argv[1:6]
    ctx = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    rx = re.compile(pat, re.I)
    day_dir = AR / day[:4] / day[:7] / day
    want = rid.replace("/", "|").replace(" ", "")
    buf = []
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            if not any(str(r.get("recordId")).replace("/", "|") == want for r in doc.get("records") or []):
                continue
            evf = pipe / "pipeline.evidence.json"
            files = (load(evf).get("files") or {}) if evf.is_file() else {}
            for k in sorted(files):
                if psub not in k:
                    continue
                lines = [str(x).rstrip("\r") for x in (files[k] or {}).get("lines") or []]
                for i, s in enumerate(lines, 1):
                    if rx.search(s):
                        lo, hi = max(1, i - ctx), min(len(lines), i + ctx)
                        for j in range(lo, hi + 1):
                            buf.append("[%s:L%d] %s" % (k, j, lines[j - 1][:500]))
                        buf.append("----")
    Path(outp).write_text("\n".join(buf) + "\n", encoding="utf-8")
    sys.stdout.write("%d hits-block lines -> %s\n" % (len(buf), outp))


main()
