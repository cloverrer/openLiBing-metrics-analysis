# -*- coding: utf-8 -*-
"""只读：从某归档记录的内嵌证据里抽取指定文件的 ERROR/FAIL 行并按内容去重计数。
用法: python _p_errdist.py <day> <comp> <pipe> <file-substr> <out>
"""
import json, re, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day, comp, pipe, sub, outp = sys.argv[1:6]
    base = AR / day[:4] / day[:7] / day / comp / pipe
    ev = load(base / "pipeline.evidence.json")
    files = ev.get("files") or {}
    rx = re.compile(r"ERROR|FAIL|超时|失败|Traceback|Exception|error")
    tag = re.compile(r"<[^>]+>")
    cnt = Counter()
    order = []
    for name, body in files.items():
        if sub not in name:
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        for ln in (lines or []):
            s = tag.sub("", str(ln))
            s = s.replace("&quot;", '"').replace("&#39;", "'").replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
            s = re.sub(r"\s+", " ", s).strip()
            if not s or not rx.search(s):
                continue
            key = s[-160:]
            if key not in cnt:
                order.append(s[:220])
            cnt[key] += 1
    buf = []
    for k, v in cnt.most_common():
        buf.append("%4d | %s" % (v, k))
    Path(outp).write_text("\n".join(buf) + "\n", encoding="utf-8")
    print("distinct=%d -> %s" % (len(cnt), outp))


main()
