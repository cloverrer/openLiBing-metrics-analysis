# -*- coding: utf-8 -*-
"""只读：从内嵌证据的指定文件中按正则抽取行（去标签）。用法: python _p_grep1.py <day> <comp> <pipe> <file-substr> <regex> <out> [max]
"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day, comp, pipe, sub, pat, outp = sys.argv[1:7]
    mx = int(sys.argv[7]) if len(sys.argv) > 7 else 120
    base = AR / day[:4] / day[:7] / day / comp / pipe
    ev = load(base / "pipeline.evidence.json")
    files = ev.get("files") or {}
    rx = re.compile(pat)
    rx_tag = re.compile(r"<[^>]+>")
    buf = []
    for name, body in files.items():
        if sub not in name:
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        for i, ln in enumerate(lines or [], 1):
            s = rx_tag.sub("", str(ln))
            s = s.replace("&quot;", '"').replace("&#39;", "'").replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
            s = re.sub(r"\s+", " ", s).strip()
            if not s or not rx.search(s):
                continue
            buf.append("%s:L%d | %s" % (name, i, s[:300]))
            if len(buf) >= mx:
                break
        if len(buf) >= mx:
            break
    Path(outp).write_text("\n".join(buf) + "\n", encoding="utf-8")
    print("hits=%d -> %s" % (len(buf), outp))


main()
