# -*- coding: utf-8 -*-
"""校验 CITE_SPEC 每条引用：打印真实行文本，确认 pat 能命中。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
IDX = {it["recordId"]: it for it in PEND["records"]}


def record(rid):
    it = IDX[rid]
    parts = it["file"].rsplit(" records[", 1)
    doc = json.loads((ROOT / "out" / parts[0]).read_text(encoding="utf-8"))
    return doc["records"][int(parts[1].rstrip("]"))], (ROOT / "out" / parts[0]).parent


CITE_SPEC = {
    "Ascend-CANN|os#153": [(0, 97, r"cannot access 'Ascend-cann-A3-ops\*\.run'", 0, 96)],
    "MindCluster|Agentsdk~5992cb#2": None,
    "SgLang|nightly-test-npu.yml#2211": [(0, 811, r"ModuleNotFoundError: No module named 'sgl_kernel_npu\.operators'", 0, 0)],
    "SgLang|nightly-test-npu.yml#2212": [(1, 510, r"customize/bin/set_env\.bash: No such file or directory", 0, 0)],
    "SgLang|nightly-test-npu.yml#2213": [(0, 531, r"ImportError: cannot import name 'SGL_ROUTER_REQUEST_TIMEOUT_SECS'", 0, 0)],
    "SgLang|nightly-test-npu.yml#2214": [(0, 718, r"ModuleNotFoundError: No module named 'sgl_kernel_npu\.operators\.mem_cache'", 0, 0)],
    "SgLang|nightly-test-npu.yml#2215": [(0, 1360, r"RuntimeError: \[/pytorch/third_party/gloo/gloo/transport/tcp/pair\.cc:547\] Connection closed by peer", 0, 0)],
    "SgLang|nightly-test-npu.yml#2216": None,
    "SgLang|nightly-test-npu.yml#2217": None,
    "SgLang|nightly-test-npu.yml#2218": [(0, 714, r"Exception: Monitoring ended but target pattern was not detected", 0, 0)],
    "SgLang|nightly-test-npu.yml#2219": None,
    "SgLang|nightly-test-npu.yml#2220": [(0, 311, r"Executing the custom container implementation failed", 0, 60)],
    "SgLang|nightly-test-npu.yml#2221": None,
    "SgLang|nightly-test-npu.yml#2222": [(0, 687, r"FileNotFoundError: sgl-router binary 'sgl-router' not found", 0, 0)],
    "SgLang|nightly-test-npu.yml#2223": [(0, 714, r"Timeout: Not all nodes are ready after 3600 seconds", 0, 0)],
    "SgLang|nightly-test-npu.yml#2224": [(0, 2939, r"Pod not ready, maybe not enough resource", 0, 0)],
    "SgLang|nightly-test-npu.yml#2225": [(0, 553, r"is not running, status: Succeeded", 0, 0)],
    "SgLang|nightly-test-npu.yml#2226": [(0, 672, r"is not running, status: Succeeded", 0, 0)],
    "SgLang|nightly-test-npu.yml#2227": [(0, 638, r"Executing the custom container implementation failed", 0, 60)],
    "UBS Core|Nightly-CI-Version-pipeline_BeiMing#261": [(1, 1, r"任务被终止执行", 0, 0)],
    "UBS Core|Nightly-CI-Version-pipeline_BeiMing#262": [(1, 2, r"任务执行失败", 0, 0)],
    "vllm-ascend|a3.yaml#16563": [(0, 2310, r"Benchmark failed: pure_decode_99", 0, 40)],
    "vllm-ascend|a3.yaml#16564": [(0, 2915, r"TimeoutError: Timed out waiting for external DP ranks ready", 0, 30)],
}

out = []
for rid, specs in CITE_SPEC.items():
    out.append("### %s" % rid)
    if specs is None:
        out.append("    (no cite)")
        continue
    rec, pdir = record(rid)
    for ti, line, pat, pre, post in specs:
        t = (rec["tasks"][ti])
        path = t.get("logFile")
        text, ok = pipeline_doc.evidence_window(pdir, path, line, line, max_lines=3)
        if not ok:
            out.append("    !! ti=%d L%d 读不到 path=%s" % (ti, line, path))
            continue
        m = re.search(pat, text)
        flag = "OK " if m else "MISS"
        shown = text.strip().replace("\n", "\\n")
        if m:
            a = max(0, m.start() - pre)
            b = min(len(text), m.end() + post)
            shown = text[a:b].strip().replace("\n", "\\n")
        out.append("    %s ti=%d L%d | %s" % (flag, ti, line, shown[:300]))

(ROOT / "out/state/_val16.txt").write_text("\n".join(out), encoding="utf-8")
print("done")
