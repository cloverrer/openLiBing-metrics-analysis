# -*- coding: utf-8 -*-
"""生成 2026-11-16 单日 23 条记录的根因结论 JSON。

直接从归档记录读取精确的 logFile 路径与指定行的真实文本，确保
keyError 一定是该行文本的子串、cites 一定可读，避免手写路径出错。
"""
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


def key_from_line(rid, ti, line, pat, pre=0, post=140):
    """按 pat 在真实行文本里定位，切出 keyError（保证是行文本子串）。"""
    rec, pdir = record(rid)
    path = (rec["tasks"][ti]).get("logFile")
    text, ok = pipeline_doc.evidence_window(pdir, path, line, line, max_lines=3)
    if not ok:
        raise SystemExit("!! %s 取不到 %s:L%d" % (rid, path, line))
    m = re.search(pat, text)
    if not m:
        raise SystemExit("!! %s pat 未命中 %s:L%d -> %s" % (rid, path, line, text[:200]))
    a = max(0, m.start() - pre)
    b = min(len(text), m.end() + post)
    return ("%s:L%d" % (path, line), text[a:b].strip())


# (recordId, [ (taskIdx, line, pat, pre, post), ... ] 或 None)
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

OUT = ROOT / "out/state/analysis_result.json"
OUT.write_text("", encoding="utf-8")

blob = json.loads(OUT.read_text(encoding="utf-8") or "{\"items\": []}")
