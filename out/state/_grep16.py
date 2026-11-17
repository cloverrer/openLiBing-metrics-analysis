# -*- coding: utf-8 -*-
"""在指定记录日志里 grep 关键词（带行号）。只读。"""
import json
import builtins
import re
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

OUT = open(ROOT / "out/state/_grep16.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pend = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))


def load(rid):
    for it in pend["records"]:
        if it["recordId"] == rid:
            parts = it["file"].rsplit(" records[", 1)
            doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
            return doc["records"][int(parts[1].rstrip("]"))], (ROOT / "out" / parts[0]).parent
    return None, None


CASES = [
    ("SgLang|nightly-test-npu.yml#2215", 0,
     r"Killed|oom|OOM|out of memory|exit code -9|SIGKILL|signal 9"),
    ("SgLang|nightly-test-npu.yml#2223", 0,
     r"Timeout|timeout|not ready|not all nodes"),
    ("SgLang|nightly-test-npu.yml#2224", 0,
     r"not enough resource|not ready|Timeout|timeout in"),
    ("vllm-ascend|a3.yaml#16563", 1,
     r"ERROR|failed"),
]

for rid, ti, pat in CASES:
    rec, pdir = load(rid)
    t = (rec.get("tasks") or [])[ti]
    path = t.get("logFile")
    n = pipeline_doc.evidence_line_count(pdir, path)
    print("=" * 70)
    print("### %s task[%d] lines=%d  pat=%s" % (rid, ti, n, pat))
    rx = re.compile(pat)
    shown = 0
    for l1 in range(1, n + 1, 200):
        text, ok = pipeline_doc.evidence_window(pdir, path, l1, min(l1 + 199, n), max_lines=200)
        if not ok:
            continue
        for i, ln in enumerate(text.split("\n"), start=l1):
            if rx.search(ln):
                print("L%d: %s" % (i, ln[:260]))
                shown += 1
                if shown >= 25:
                    break
        if shown >= 25:
            break
    if not shown:
        print("(no match)")

OUT.close()
