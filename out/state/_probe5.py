# -*- coding: utf-8 -*-
"""只读探针：列出单条 pending 记录的错误候选（cites 候选 + 引用行原文）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

AR = ROOT / "out" / "archive"


def find_dir(day, comp, pipe):
    return AR / day[:4] / day[:7] / day / comp / pipe


def load_rec(pdir, build):
    doc = pipeline_doc.load(pdir) or {}
    for rec in doc.get("records") or []:
        if build in str(rec.get("recordId")):
            return rec
    return None


def raw_line(pdir, path, line):
    if not path or line is None:
        return None
    txt, ok = pipeline_doc.evidence_window(pdir, path, int(line), int(line), max_lines=1)
    if not ok:
        return "<unreadable>"
    return txt.strip()[:400]


def main():
    day, comp, pipe, build = sys.argv[1:5]
    pdir = find_dir(day, comp, pipe)
    rec = load_rec(pdir, build)
    if not rec:
        print("not found:", pdir)
        return
    print("REC", rec.get("recordId"), "| status=", rec.get("status"),
          "| ftt=", rec.get("failedTaskType"),
          "| verdict=", json.dumps(rec.get("verdict"), ensure_ascii=False))
    print("evidence:", json.dumps(rec.get("evidence"), ensure_ascii=False))
    print("counts:", json.dumps(rec.get("counts"), ensure_ascii=False))
    for t in rec.get("tasks") or []:
        print(" TASK", t.get("jobName"), t.get("type"), json.dumps(t.get("summary"), ensure_ascii=False),
              "| ftt=", t.get("failedTaskType"))
        for c in (t.get("cases") or []):
            if c.get("state") not in (None, "passed", "success"):
                print("    CASE", c.get("name"), c.get("state"), "| localLog=", c.get("localLog"))
    print("--- errorMessages ---")
    for i, m in enumerate(rec.get("errorMessages") or []):
        src, ln = m.get("source"), m.get("line")
        raw = raw_line(pdir, src, ln) if ln is not None else None
        print("[%d] task=%s case=%s level=%s src=%s:%s" % (
            i, m.get("task"), m.get("case"), m.get("level"), src, ln))
        print("     msg:", (m.get("text") or m.get("msg") or "")[:260])
        if raw is not None:
            print("     RAW:", raw)


if __name__ == "__main__":
    main()
