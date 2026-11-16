# -*- coding: utf-8 -*-
"""只读探针（批量）：对某归档日全部 pending 记录，输出错误候选（cite + 引用行原文）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

AR = ROOT / "out" / "archive"
RAW_MAX = 230


def raw_line(pdir, path, line):
    if not path or line is None:
        return None
    txt, ok = pipeline_doc.evidence_window(pdir, path, int(line), int(line), max_lines=1)
    if not ok:
        return "<unreadable>"
    return txt.strip().replace("\n", " ")[:RAW_MAX]


def main():
    day = sys.argv[1]
    want = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    day_dir = AR / day[:4] / day[:7] / day
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        if want and want not in comp.name.lower():
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = pipeline_doc.load(pipe) or {}
            for rec in doc.get("records") or []:
                if (rec.get("analysis") or {}).get("status") != "pending":
                    continue
                print("=" * 70)
                print("REC", rec.get("recordId"), "| status=", rec.get("status"),
                      "| ftt=", rec.get("failedTaskType"),
                      "| cat=", (rec.get("verdict") or {}).get("category"))
                ev = rec.get("evidence") or {}
                print("  evidence:", json.dumps(ev.get("files"), ensure_ascii=False),
                      "| missing:", json.dumps(ev.get("missing"), ensure_ascii=False),
                      "| github:", json.dumps(ev.get("github"), ensure_ascii=False)[:160])
                for t in rec.get("tasks") or []:
                    print("  TASK", t.get("jobName"), t.get("type"),
                          json.dumps(t.get("summary"), ensure_ascii=False))
                for i, m in enumerate(rec.get("errorMessages") or []):
                    src, ln = m.get("source"), m.get("line")
                    msg = (m.get("text") or m.get("msg") or "").strip().replace("\n", " ")
                    print("  [%d] %s %s:%s | %s" % (i, m.get("level"), src, ln, msg[:200]))
                    if ln is not None and src and "/" in str(src):
                        print("       RAW:", raw_line(pipe, src, ln))
                for i, s in enumerate(rec.get("suggestions") or []):
                    print("  SUG[%d]" % i, json.dumps(s, ensure_ascii=False)[:200])
                print("  counts:", json.dumps(rec.get("counts"), ensure_ascii=False))


if __name__ == "__main__":
    main()
