# -*- coding: utf-8 -*-
"""扫描 11-16 各组件归档内嵌证据，按关键签名统计每个日志文件的命中情况。"""
import json
import re
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")

SIGS = [
    ("set_env_missing", r"set_env\.bash: No such file"),
    ("pod_not_running", r"is not running, status: Succeeded"),
    ("sgl_kernel_operators", r"No module named 'sgl_kernel_npu\.operators'"),
    ("sgl_kernel_memcache", r"No module named 'sgl_kernel_npu\.operators\.mem_cache'"),
    ("router_timeout_sym", r"cannot import name 'SGL_ROUTER_REQUEST_TIMEOUT_SECS'"),
    ("sgl_router_bin", r"FileNotFoundError: sgl-router binary"),
    ("gloo_closed", r"Connection closed by peer"),
    ("kda_attr", r"wants_int64_query_start_loc"),
    ("oom_killed", r"Killed|SIGKILL|exit code -9|out of memory|OOM"),
    ("not_all_nodes", r"Not all nodes are ready after"),
    ("timeout_12600", r"timeout in 12600s|not enough resource"),
    ("bind_addr", r"Cannot assign requested address"),
    ("custom_container", r"custom container implementation failed"),
    ("warmup_failed", r"Warmup failed"),
    ("monitor_not_detected", r"Monitoring ended but target pattern was not detected"),
    ("nodes_ready_ok", r"is ready"),
]

# (pipeline, evidence_path, [ (recordId, [logFile substrings]) ])
TARGETS = {
    "SgLang": {"path": "out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml/pipeline.evidence.json"},
    "vllm-ascend": {"path": "out/archive/2026/2026-11/2026-11-16/vllm-ascend/a3.yaml/pipeline.evidence.json"},
}

for comp, cfg in TARGETS.items():
    d = json.load(io.open(ROOT / cfg["path"], encoding="utf-8"))
    files = d.get("files") or {}
    print("=" * 90)
    print("###", comp, "files:", len(files))
    for k in sorted(files):
        lines = files[k].get("lines") or []
        hits = {}
        for name, pat in SIGS:
            rx = re.compile(pat)
            n = 0
            first = None
            for i, ln in enumerate(lines, 1):
                if rx.search(ln):
                    n += 1
                    if first is None:
                        first = i
            if n:
                hits[name] = (n, first)
        short = k.split("/")[-1][:70]
        print("--", short, "lines=%d" % len(lines))
        for name, (n, first) in hits.items():
            print("     %-22s n=%-4d firstL=%d" % (name, n, first))
