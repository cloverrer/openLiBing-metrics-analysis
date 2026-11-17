# -*- coding: utf-8 -*-
"""社区记录「错误行证据」离线重算 —— 不联网、不重新采集，只用已归档的控制台日志重算 errorMessages。

为什么要重算:
  早先 error_lines() 从日志头往下取满 MAX_ERR_LINES 行就停。openGauss 那类 4 万行日志前段
  全是 `Failed to set locale, defaulting to C.UTF-8` 噪音，60 个名额在 L3000 前就被占满，
  真正在 L39xxx 的 `No space left on device` 一条都进不来 —— 页面上就表现为
  「根因写着磁盘写满，证据弹窗里全是 locale 警告」。
  采集侧（tools/collect_community_nightly.py）已改为「尾部优先 + 硬证据优先 + 噪音过滤 +
  归一化去重」，本工具把既有归档按同一口径重算一遍，不重新抓日志。

改什么:
  records[].errorMessages、records[].tasks[].errorLines、records[].counts.errorMessages、
  records[].verdict.basis 里的命中行数，以及 steps.step_5_logs.results（tasks 的同步副本）。

不动什么:
  日志原文（pipeline.evidence.json）、AI 结论（records[].analysis，其 keyError/cites 指的行号
  本来就落在重算后的证据里，反而更一致）、时间字段、统计口径与日期归属。

用法:
  python tools/rederive_community_errors.py --dry-run     # 只报差异，不落盘
  python tools/rederive_community_errors.py               # 落盘
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import pipeline_doc  # noqa: E402
from lib.paths import ARCHIVE_ROOT  # noqa: E402
from tools.collect_community_nightly import error_lines  # noqa: E402

_BASIS_PAT = re.compile(r"控制台日志命中错误行\s*\d+\s*行")


def communities():
    """社区组件名（数据源配置里声明，避免把 openLiBing 侧组件一起重算）。"""
    try:
        doc = json.loads((ROOT / "community_sources.json").read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return [c.get("id") for c in (doc.get("communities") or []) if c.get("id")]


def iter_dirs():
    for comp in communities():
        for pdir in sorted(ARCHIVE_ROOT.glob("*/*/*/%s/*" % comp)):
            if pipeline_doc.has_pipeline(pdir):
                yield comp, pdir


def rederive(pdir):
    """重算单个流水线目录，返回 [(执行号, 原行数, 新行数, 新首行, 新末行)]。"""
    doc = pipeline_doc.load(pdir)
    if not doc:
        return []
    ev = pipeline_doc.load_evidence(pdir) if pipeline_doc.has_evidence(pdir) else {}
    files = (ev or {}).get("files") or {}
    recs = doc.get("records") or []
    changed = []
    for r in recs:
        tasks = r.get("tasks") or []
        log_file = (tasks[0].get("logFile") if tasks else None) or ""
        lines = ((files.get(log_file) or {}).get("lines")) or []
        if not lines:
            continue                      # 没有归档日志（成功构建/未抓日志）→ 不动
        rows = error_lines("\n".join(lines))
        before = len(r.get("errorMessages") or [])
        r["errorMessages"] = [{"task": tasks[0].get("jobName"), "source": log_file,
                               "line": n, "level": "LOG", "text": s} for n, s in rows]
        tasks[0]["errorLines"] = ["L%d: %s" % (n, s) for n, s in rows]
        counts = r.get("counts") or {}
        counts["errorMessages"] = len(rows)
        r["counts"] = counts
        verdict = r.get("verdict") or {}
        if isinstance(verdict.get("basis"), list):
            verdict["basis"] = [_BASIS_PAT.sub("控制台日志命中错误行 %d 行" % len(rows), b)
                                for b in verdict["basis"]]
            r["verdict"] = verdict
        changed.append((r.get("buildNumber"), before, len(rows),
                        rows[0][1] if rows else "-", rows[-1][1] if rows else "-"))
    if not changed:
        return []
    s5 = (doc.get("steps") or {}).get("step_5_logs")
    if isinstance(s5, dict):             # 同步 step_5_logs.results（tasks 的镜像副本）
        s5["results"] = [t for r in recs for t in (r.get("tasks") or [])]
    pipeline_doc.save(pdir, doc)
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印差异，不写盘")
    args = ap.parse_args()

    total, dirs = 0, 0
    for comp, pdir in iter_dirs():
        rows = rederive(pdir) if not args.dry_run else _dry(pdir)
        if not rows:
            continue
        dirs += 1
        rel = pdir.relative_to(ARCHIVE_ROOT)
        print("== %s" % rel)
        for num, before, after, first, last in rows:
            total += 1
            print("   #%-6s 错误行 %d -> %d" % (num, before, after))
            print("        首行: %s" % str(first)[:110])
            print("        末行: %s" % str(last)[:110])
    print("-- %s：%d 个流水线目录、%d 条执行记录" % ("预演（未落盘）" if args.dry_run else "已落盘", dirs, total))
    return 0


def _dry(pdir):
    """预演：算一遍但不写盘（复用 rederive 的算法，只是不 save）。"""
    doc = pipeline_doc.load(pdir)
    if not doc:
        return []
    ev = pipeline_doc.load_evidence(pdir) if pipeline_doc.has_evidence(pdir) else {}
    files = (ev or {}).get("files") or {}
    out = []
    for r in doc.get("records") or []:
        tasks = r.get("tasks") or []
        log_file = (tasks[0].get("logFile") if tasks else None) or ""
        lines = ((files.get(log_file) or {}).get("lines")) or []
        if not lines:
            continue
        rows = error_lines("\n".join(lines))
        out.append((r.get("buildNumber"), len(r.get("errorMessages") or []), len(rows),
                    rows[0][1] if rows else "-", rows[-1][1] if rows else "-"))
    return out


if __name__ == "__main__":
    sys.exit(main())
