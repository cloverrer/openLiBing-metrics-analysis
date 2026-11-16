# -*- coding: utf-8 -*-
"""临时只读探针：按 pipeline.evidence.json 内嵌证据取指定文件的行窗口，落盘 UTF-8。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    day, comp, pipe = sys.argv[1], sys.argv[2], sys.argv[3]
    subs, l1, l2 = sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
    outp = Path(sys.argv[7])
    base = ROOT / "out" / "archive" / day[:4] / day[:7] / day / comp / pipe
    ev = load(base / "pipeline.evidence.json")
    files = ev.get("files") or {}
    buf = []
    for name, body in files.items():
        if subs not in name:
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        lines = lines if isinstance(lines, list) else []
        buf.append("===== %s (total %d)" % (name, len(lines)))
        for i in range(max(0, l1 - 1), min(len(lines), l2)):
            buf.append("[L%d] %s" % (i + 1, str(lines[i])[:400]))
    outp.write_text("\n".join(buf), encoding="utf-8")
    print("wrote", outp, len(buf), "lines")


if __name__ == "__main__":
    main()
