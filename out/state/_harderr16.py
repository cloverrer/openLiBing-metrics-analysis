# -*- coding: utf-8 -*-
"""打印指定记录日志里的强错误行（带行号），用于精确定位根因。"""
import json
import re
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))

RX = re.compile(r"(ModuleNotFoundError|ImportError|AttributeError|RuntimeError|FileNotFoundError|"
                r"TimeoutError|Exception:|ERROR -|\[ERROR\]|error:|##\[error\]|Traceback \(most recent|"
                r"Could not|Cannot assign|Connection closed|Killed|OOM|No space|not running, status)")

SPEC = {
    "SgLang|nightly-test-npu.yml#2218": ["133327323785", "133340755431", "133381668819", "133394969649"],
    "SgLang|nightly-test-npu.yml#2225": ["133324841013"],
    "SgLang|nightly-test-npu.yml#2226": ["133373908398"],
    "SgLang|nightly-test-npu.yml#2215": ["133095943416"],
    "SgLang|nightly-test-npu.yml#2223": ["133303913207", "133347678142"],
    "SgLang|nightly-test-npu.yml#2227": ["133388055851"],
}

lines = []
for it in PEND["records"]:
    rid = it["recordId"]
    subs = SPEC.get(rid)
    if not subs:
        continue
    parts = it["file"].rsplit(" records[", 1)
    docp = ROOT / "out" / parts[0]
    ev = json.loads((docp.parent / "pipeline.evidence.json").read_text(encoding="utf-8"))
    files = ev.get("files") or {}
    lines.append("### " + rid)
    for sub in subs:
        for k in files:
            if sub not in k:
                continue
            ls = files[k].get("lines") or []
            lines.append("  == %s (%d)" % (k.split("/")[-1][:70], len(ls)))
            n = 0
            for i, ln in enumerate(ls, 1):
                if RX.search(ln):
                    lines.append("    L%d: %s" % (i, ln[:220]))
                    n += 1
                    if n >= 14:
                        lines.append("    ...")
                        break
    lines.append("")
(ROOT / "out/state/_harderr16.txt").write_text("\n".join(lines), encoding="utf-8")
print("done")
