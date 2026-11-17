# -*- coding: utf-8 -*-
"""导出 23 条记录的 ftt/status/counts/分析状态等元数据。只读。"""
import json
import builtins
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
OUT = open(ROOT / "out/state/_meta16.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pend = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
for it in pend["records"]:
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    rec = doc["records"][int(parts[1].rstrip("]"))]
    keys = ["recordId", "status", "failedTaskType", "ftt", "pipelineRunId",
            "startedAt", "endedAt", "counts", "githubMeta", "analysis"]
    d = {k: rec.get(k) for k in keys if k in rec}
    print(json.dumps(d, ensure_ascii=False)[:900])
    print("-" * 60)
OUT.close()
