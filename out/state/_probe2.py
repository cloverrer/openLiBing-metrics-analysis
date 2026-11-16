# -*- coding: utf-8 -*-
"""临时只读探针：导出指定归档日各 pending 记录的 tasks/logFile/errorLines 摘要。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def trunc(s, n=180):
    s = " ".join(str(s or "").split())
    return s[:n]


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
                v = rec.get("verdict") or {}
                print("=" * 70)
                print(rec.get("recordId"), "| cat=", v.get("category"),
                      "| ftt=", rec.get("failedTaskType"), "| status=", rec.get("status"))
                for t in rec.get("tasks") or []:
                    print("  [task]", trunc(t.get("name"), 90),
                          "| type=", t.get("type"), "| status=", t.get("status"))
                    print("      log=", t.get("logFile"))
                    for el in (t.get("errorLines") or [])[:6]:
                        print("      err>", trunc(el, 200))
                for st in rec.get("subTasks") or []:
                    print("  [sub]", trunc(st.get("name"), 90),
                          "| log=", st.get("logFile"),
                          "| errs=", len(st.get("errorLines") or []))
                em = rec.get("errorMessages") or []
                if em:
                    print("  errorMessages:", len(em))
                    for e in em[:8]:
                        print("     >", e.get("level"), "|", e.get("case"),
                              "|", e.get("source"), ":", e.get("line"))
                        print("       ", trunc(e.get("text"), 400))


main()
