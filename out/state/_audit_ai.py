# -*- coding: utf-8 -*-
"""审计：逐条记录看 analysis.status / 根因正文 / 归档分类，找出页面上会显示
「待 AI 根因分析」或「--」的行，并按原因归类。只读，不改任何归档。"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import ARCHIVE_ROOT, day_pipeline_scope, iter_archive_days  # noqa: E402


def main():
    cross = Counter()                 # (verdict.category, an.status, hasRC) -> n
    nonna = []                        # 失败类但未分析
    pend = []                         # pending
    odd = []                          # 状态异常（缺失/未知状态）
    total = 0
    for date, day_dir in iter_archive_days():
        allowed = day_pipeline_scope(day_dir)
        for comp in sorted(p for p in day_dir.iterdir() if p.is_dir()):
            if comp.name.startswith("_"):
                continue
            for pipe in sorted(p for p in comp.iterdir() if p.is_dir()):
                if allowed is not None and (comp.name, pipe.name) not in allowed:
                    continue
                if not pipeline_doc.path_of(pipe).is_file():
                    continue
                doc = pipeline_doc.load(pipe) or {}
                for i, rec in enumerate(doc.get("records") or []):
                    total += 1
                    v = rec.get("verdict") or {}
                    an = rec.get("analysis") or {}
                    cat = v.get("category") or "--"
                    st = an.get("status") or "(missing)"
                    rc = (an.get("rootCause") or "").strip()
                    it = an.get("issueType")
                    cross[(cat, st, bool(rc))] += 1
                    loc = "%s %s/%s #%s rec[%d]" % (date, comp.name, pipe.name,
                                                    rec.get("buildNumber"), i)
                    lt = rec.get("light") or {}
                    info = "%s | cat=%s st=%s rc=%s issueType=%s | va=%s bs=%s | ftt=%s" % (
                        loc, cat, st, "Y" if rc else "N", it, lt.get("vaRate"),
                        lt.get("bsRate"), rec.get("failedTaskType"))
                    if st == "pending":
                        pend.append(info)
                    elif st == "na":
                        if cat not in ("success",):
                            nonna.append(info)
                    elif st not in ("na",):
                        odd.append(info)
    print("总记录数:", total)
    print()
    print("== 归档分类 x analysis.status x 有无根因 ==")
    for (cat, st, has), n in sorted(cross.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %-16s %-10s 根因=%-3s  %d" % (cat, st, "Y" if has else "N", n))
    print()
    print("== 失败类记录却标 na（页面上根因/定性/分类都会显示 --）: %d ==" % len(nonna))
    for s in nonna:
        print("  " + s)
    print()
    print("== pending（页面显示「待 AI 根因分析」）: %d ==" % len(pend))
    for s in pend:
        print("  " + s)
    print()
    print("== 状态异常（既非 na 也非 pending）: %d ==" % len(odd))
    for s in odd:
        print("  " + s)


if __name__ == "__main__":
    main()
