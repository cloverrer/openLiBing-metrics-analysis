# -*- coding: utf-8 -*-
"""按记录维度统计 11-16 各失败运行日志文件的失败签名命中，并给出首个命中行。"""
import json
import re
import io
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
PEND = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))

SIGS = [
    ("set_env_missing", r"set_env\.bash: No such file"),
    ("pod_succeeded", r"is not running, status: Succeeded"),
    ("k_operators", r"No module named 'sgl_kernel_npu\.operators'"),
    ("k_memcache", r"No module named 'sgl_kernel_npu\.operators\.mem_cache'"),
    ("router_timeout_sym", r"cannot import name 'SGL_ROUTER_REQUEST_TIMEOUT_SECS'"),
    ("router_bin", r"FileNotFoundError: sgl-router binary"),
    ("gloo_closed", r"Connection closed by peer"),
    ("kda_attr", r"wants_int64_query_start_loc"),
    ("oom", r"Killed|SIGKILL|exit code -9|out of memory|OOM"),
    ("not_all_nodes", r"Not all nodes are ready after"),
    ("timeout_12600", r"timeout in 12600s|not enough resource"),
    ("bind_addr", r"Cannot assign requested address"),
    ("custom_container", r"custom container implementation failed"),
    ("monitor_not_detected", r"Monitoring ended but target pattern was not detected"),
    ("oserr2", r"No such file or directory \(os error 2\)"),
]
RXC = [(n, re.compile(p)) for n, p in SIGS]

lines_out = []
for it in PEND["records"]:
    rid = it["recordId"]
    parts = it["file"].rsplit(" records[", 1)
    docp = ROOT / "out" / parts[0]
    evp = docp.parent / "pipeline.evidence.json"
    if not evp.exists():
        continue
    ev = json.loads(evp.read_text(encoding="utf-8"))
    files = ev.get("files") or {}
    doc = json.loads(docp.read_text(encoding="utf-8"))
    rec = doc["records"][int(parts[1].rstrip("]"))]
    lines_out.append("### " + rid)
    for t in rec.get("tasks", []):
        lf = t.get("logFile")
        if not lf or lf not in files:
            continue
        ls = files[lf].get("lines") or []
        agg = {}
        for name, rx in RXC:
            for i, ln in enumerate(ls, 1):
                if rx.search(ln):
                    agg.setdefault(name, [0, i])
                    agg[name][0] += 1
        lines_out.append("  -- %s (%d lines)" % (lf.split("/")[-1][:60], len(ls)))
        for name in [s[0] for s in SIGS]:
            if name in agg:
                lines_out.append("       %-20s n=%d firstL=%d" % (name, agg[name][0], agg[name][1]))
    lines_out.append("")

(ROOT / "out/state/_sig16byrec.txt").write_text("\n".join(lines_out), encoding="utf-8")
print("done")
