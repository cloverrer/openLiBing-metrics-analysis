# -*- coding: utf-8 -*-
"""收尾取证：vllm 16564 失败用例、CANN L97 是否含 chmod 文本。"""
import json
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
DAY = ROOT / "out/archive/2026/2026-11/2026-11-16"
out = []


def load(p):
    return (json.load(io.open(p, encoding="utf-8")).get("files") or {})


# vllm 16564
vl = load(DAY / "vllm-ascend/a3.yaml/pipeline.evidence.json")
for k, v in vl.items():
    lines = v.get("lines") or []
    hits = [(i + 1, ln) for i, ln in enumerate(lines) if "aisbench case failed" in ln or "FAIL_TAG" in ln or "Upload failed" in ln]
    if hits:
        out.append("== VL %s (total %d)" % (k, len(lines)))
        for no, ln in hits[:12]:
            out.append("L%d: %s" % (no, ln[:500]))
        out.append("")

# CANN L97 / L95-101
cn = load(DAY / "Ascend-CANN/os/pipeline.evidence.json")
for k, v in cn.items():
    lines = v.get("lines") or []
    out.append("== CANN %s (total %d)" % (k, len(lines)))
    for i in range(94, min(101, len(lines))):
        ln = lines[i]
        out.append("L%d (len=%d): %s" % (i + 1, len(ln), ln[:260]))
    # 检查 chmod 文本
    for i, ln in enumerate(lines):
        if "chmod" in ln and "Ascend-cann" in ln:
            idx = ln.find("chmod")
            out.append("   chmod@L%d: ...%s..." % (i + 1, ln[max(0, idx - 30):idx + 120]))
    out.append("")

Path(ROOT / "out/state/_last16.txt").write_text("\n".join(out), encoding="utf-8")
print("wrote", len(out))
