# -*- coding: utf-8 -*-
"""临时只读探针：输出指定归档日 pending 记录的 recordId 与完整 logFile 列表。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def main():
    day = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else ""
    day_dir = AR / day[:4] / day[:7] / day
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        if want and want.lower() not in comp.name.lower():
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = json.loads(pj.read_text(encoding="utf-8"))
            for rec in doc.get("records") or []:
                an = rec.get("analysis") or {}
                if an.get("status") != "pending":
                    continue
                print("##", rec.get("recordId"))
                for t in rec.get("tasks") or []:
                    if t.get("logFile"):
                        print("   ", t.get("logFile"))
                for st in rec.get("subTasks") or []:
                    if st.get("logFile"):
                        print("   ", st.get("logFile"))


main()
