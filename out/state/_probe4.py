# -*- coding: utf-8 -*-
"""只读探针：打印单条 pending 记录的字段结构 + 错误候选行（含 path:L 引用）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load_record(day, comp, pipe, build):
    d = AR / day[:4] / day[:7] / day / comp / pipe / "pipeline.json"
    doc = json.loads(d.read_text(encoding="utf-8"))
    for rec in doc.get("records") or []:
        if str(rec.get("buildNo")) == str(build) or str(build) in str(rec.get("recordId")):
            return rec
    return None


def main():
    day, comp, pipe, build = sys.argv[1:5]
    rec = load_record(day, comp, pipe, build)
    if not rec:
        print("not found")
        return
    print("== keys:", sorted(rec.keys()))
    for k in ("recordId", "status", "failedTaskType", "category", "verdict", "light"):
        print(" ", k, "=", json.dumps(rec.get(k), ensure_ascii=False)[:300])
    an = rec.get("analysis") or {}
    print(" analysis:", json.dumps({kk: vv for kk, vv in an.items() if kk != "possibilities"},
                                   ensure_ascii=False)[:400])
    for k in ("errorMessages", "errors", "evidence", "jobs", "tasks", "failedTasks"):
        v = rec.get(k)
        if v is None:
            continue
        print(" --", k, "type=", type(v).__name__, "len=", len(v) if hasattr(v, "__len__") else "-")
        print("   ", json.dumps(v, ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()
