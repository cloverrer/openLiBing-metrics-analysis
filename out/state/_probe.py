# -*- coding: utf-8 -*-
"""临时只读探针：按日期打印待分析记录的摘要字段（不落盘、不改归档）。用完即删。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AR = ROOT / "out" / "archive"


def trunc(s, n=220):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[:n] + "…"


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
                print("=" * 8, rec.get("recordId"), "| cat=", v.get("category"),
                      "| ftt=", rec.get("failedTaskType"), "| status=", rec.get("status"),
                      "| VA/BS=", (rec.get("light") or {}).get("vaRate"),
                      (rec.get("light") or {}).get("bsRate"))
                for t in rec.get("tasks") or []:
                    print("  [task]", t.get("type"), t.get("jobName"),
                          "| log=", t.get("logFile") or "--",
                          "| cases=", len(t.get("cases") or []),
                          "| errLines=", len(t.get("errorLines") or []))
                    for c in (t.get("cases") or []):
                        em = (c.get("errorMessages") or [{}])[0]
                        print("     case:", c.get("name"), "|",
                              trunc(c.get("description") or em.get("text") or "", 160))
                for e in rec.get("errorMessages") or []:
                    print("   E:", e.get("source") or e.get("file") or "", ":",
                          e.get("line") or "", "|", trunc(e.get("text") or e.get("message") or "", 200))
                for c in rec.get("cases") or []:
                    print("   C:", c.get("name"), "|", trunc(c.get("description") or "", 200))


if __name__ == "__main__":
    main()
