# -*- coding: utf-8 -*-
"""只读：打印指定记录的 errorMessages / tasks[].cases 原始结构（UTF-8 落盘）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day, want = sys.argv[1], sys.argv[2].replace("/", "|")
    outp = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parent / "_raw.txt"
    day_dir = AR / day[:4] / day[:7] / day
    out = []
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            for rec in doc.get("records") or []:
                if str(rec.get("recordId")).replace("/", "|") != want:
                    continue
                out.append(json.dumps({
                    "recordId": rec.get("recordId"),
                    "status": rec.get("status"),
                    "failedTaskType": rec.get("failedTaskType"),
                    "errorMessages": rec.get("errorMessages"),
                    "errorLines": rec.get("errorLines"),
                    "stepErrMsgs": rec.get("stepErrMsgs"),
                    "tasks": [
                        {"name": t.get("name"), "type": t.get("type"), "logFile": t.get("logFile"),
                         "cases": [{"state": c.get("state"), "description": c.get("description"),
                                    "localLog": c.get("localLog")} for c in (t.get("cases") or [])]}
                        for t in (rec.get("tasks") or [])
                    ],
                }, ensure_ascii=False, indent=1))
    outp.write_text("\n".join(out) + "\n", encoding="utf-8")
    sys.stdout.write("wrote -> %s (records=%d)\n" % (outp, len(out)))


main()
