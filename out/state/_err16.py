# -*- coding: utf-8 -*-
"""紧凑导出 23 条记录的 task/jobName/errorLines（截断），确认每条的失败点。"""
import json
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))

PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
out = []
for it in PEND["records"]:
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    rec = doc["records"][int(parts[1].rstrip("]"))]
    out.append("### %s  ftt=%s" % (it["recordId"], rec.get("failedTaskType")))
    for ti, t in enumerate(rec.get("tasks") or []):
        el = t.get("errorLines")
        if isinstance(el, list):
            el = " ; ".join(" ".join(str(x).split())[:150] for x in el[:3])
        out.append("  ti=%d [%s] job=%s" % (ti, t.get("type"), str(t.get("jobName"))[:80]))
        out.append("      err=%s" % (str(el)[:420],))
        if t.get("emptyTestResult"):
            out.append("      emptyTestResult=True")
    out.append("")
(ROOT / "out/state/_err16.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
