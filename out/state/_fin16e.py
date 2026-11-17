# -*- coding: utf-8 -*-
import io, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa
OUT = io.open(ROOT / "out/state/_fin16e.txt", "w", encoding="utf-8", newline="\n")
base = ROOT / "out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml"
doc = pipeline_doc.load(base) or {}
for i, r in enumerate(doc.get("records") or []):
    OUT.write("#%s ftt=%r status=%r verdict=%r tasks=%d evidence=%r\n" % (
        r.get("buildNumber"), r.get("failedTaskType"), r.get("status"),
        (r.get("verdict") or {}).get("category"), len(r.get("tasks") or []),
        (r.get("evidence") or {}).get("files")))
    for t in (r.get("tasks") or []):
        OUT.write("     job=%r type=%r errLines=%s errMsgs=%s note=%r\n" % (
            (t.get("jobName") or "")[:48], t.get("type"),
            len(t.get("errorLines") or []), len(t.get("errorMessages") or []),
            t.get("evidenceNote")))
OUT.close()
print("done")
