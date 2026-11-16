# -*- coding: utf-8 -*-
"""分析状态归一 —— 让每条记录的 analysis.status 与「当日切片」口径重新对齐。

为什么需要这个工具：判定「一条失败运行该不该做根因分析」的口径改过几轮（从 step_1 的
区间看板值改成 lib/dim_affects 的记录级当日切片）。口径一改，**旧归档里已经写死的
analysis.status 就与新口径分叉**，表现为两类自相矛盾的记录：

  1) 漏分析：影响当日某维度指标，却标成 na —— 页面上就是一行「定性 -- / 问题分类 --」
     的空行混在根因表里，用户看到的「为什么没分析」；
  2) 多分析：不影响当日任何维度指标，却已有根因（done）或还是 pending —— 达标日里
     该豁免的运行被多分析了一遍。

本工具对每一条失败/取消记录，就地按 lib/dim_affects（与 step_6、两个校验工具、页面 JS
同一份口径）重算归属，只在「口径说该分析、归档说不用」或反过来时改写 analysis.status：

  归属非空 + status=na            → 改 pending（重新排队给 AI 补根因）
  归属非空 + status=done 但根因为空 → 改 pending
  归属为空 + status=pending/done   → 改 na 并清空根因（回退为豁免，保留一条 waived 痕迹）
  其余（该 pending 的 pending、该 na 的 na、该 done 的 done）一律不动

只动 analysis 一个字段；记录其余内容（任务/用例/证据/定性）一律保持归档原样。
旧记录若缺 light.affects（新 schema 的自描述字段），默认不动 —— 两个校验工具与页面都会
用同一份口径就地重算，判定结果完全一致；需要把该字段补齐时显式加 --backfill-affects。

用法:
  python tools/normalize_analysis.py                        # 只扫描并列清单（不改任何文件）
  python tools/normalize_analysis.py --apply                # 就地改写状态并打印每条变更
  python tools/normalize_analysis.py --apply --backfill-affects   # 同时补齐缺失的 light.affects
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.dim_affects import affects_of, day_avail_of  # noqa: E402
from lib.paths import iter_archive_days, iter_scoped_pipelines, rel  # noqa: E402

FAIL_STATUS = {"FAILED", "CANCELED", "CANCELLED"}
WAIVED_REASON = "不影响当日任何维度指标（当日版本可用且该次运行编译全过），不做根因分析"


def rec_affects(rec, doc, day):
    """一条记录实际影响的维度：新归档采信 light.affects；缺字段就地按同一份口径重算。"""
    lt = rec.get("light") or {}
    a = lt.get("affects")
    if isinstance(a, list):
        return a
    if str(rec.get("status") or "").upper() not in FAIL_STATUS:
        return []
    steps = (doc or {}).get("steps") or {}
    dims = ((steps.get("step_1_lights") or {}).get("pipeline") or {}).get("dims") or []
    rh = (steps.get("step_2_runs") or {}).get("runHistory") or []
    run = {str(h.get("rn")): h for h in rh}.get(str(rec.get("buildNumber")))
    return affects_of(dims, day_avail_of(rh, day), run)


def scan(backfill):
    """遍历全部归档日，返回需处理的记录清单（状态不一致，或按需补齐 light.affects）。"""
    out = []
    for day, day_dir in iter_archive_days():
        for comp, pipe, adir in iter_scoped_pipelines(day_dir):
            doc = pipeline_doc.load(adir)
            if not doc:
                continue
            for rec in doc.get("records") or []:
                if str(rec.get("status") or "").upper() not in FAIL_STATUS:
                    continue
                aff = rec_affects(rec, doc, day)
                lt = rec.get("light") or {}
                an = rec.get("analysis") or {}
                st = an.get("status") or ""
                root = str(an.get("rootCause") or "").strip()
                if aff and st == "na":
                    want = "pending"
                elif aff and st == "done" and not root:
                    want = "pending"
                elif not aff and st in ("pending", "done"):
                    want = "na"
                else:
                    want = st
                need_affects = backfill and not isinstance(lt.get("affects"), list)
                if want != st or need_affects:
                    out.append({"day": day, "dir": adir, "recordId": str(rec.get("recordId") or ""),
                                "component": comp, "pipeline": pipe, "rn": rec.get("buildNumber"),
                                "now": st, "want": want, "affects": aff,
                                "change": want != st, "need_affects": need_affects})
    return out


def _pending():
    return {"status": "pending", "rootCause": None, "advice": None,
            "cites": [], "updatedAt": None, "source": None}


def _na(now, old):
    return {"status": "na", "rootCause": None, "advice": None, "cites": [],
            "keyError": None, "issueType": None, "issueDetail": None, "possibilities": [],
            "updatedAt": now, "source": old.get("source"),
            "waived": {"at": now, "from": old.get("status"), "reason": WAIVED_REASON}}


def main():
    ap = argparse.ArgumentParser(description="让 analysis.status 与当日切片口径对齐")
    ap.add_argument("--apply", action="store_true", help="就地改写（默认只扫描）")
    ap.add_argument("--backfill-affects", action="store_true",
                    help="同时给缺该字段的旧记录补上 light.affects")
    args = ap.parse_args()

    items = scan(args.backfill_affects)
    print("== 分析状态归一 ==")
    print("需处理的记录：%d 条（其中改状态 %d 条%s）"
          % (len(items), sum(1 for x in items if x["change"]),
             "，补 light.affects %d 条" % sum(1 for x in items if x["need_affects"])
             if args.backfill_affects else ""))
    for x in items:
        print("  %s %s/%s #%s：status %s → %s（归属 %s）%s"
              % (x["day"], x["component"], x["pipeline"], x["rn"],
                 x["now"] or "-", x["want"] or "-", "/".join(x["affects"]) or "无",
                 "；补 light.affects" if x["need_affects"] else ""))
    if not items:
        print("结论：归档分析状态与口径一致，无需改写")
        return 0
    if not args.apply:
        print("（dry-run，未改动任何文件；加 --apply 就地改写）")
        return 0

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done = fail = 0
    for x in items:
        def mutate(rec, x=x, now=now):
            if x["need_affects"]:
                rec.setdefault("light", {})["affects"] = x["affects"]
            if not x["change"]:
                return
            an = rec.get("analysis") or {}
            rec["analysis"] = (_pending() if x["want"] == "pending"
                               else _na(now, an) if x["want"] == "na" else an)
        found, path = pipeline_doc.update_record(x["dir"], x["recordId"], mutate)
        if found:
            done += 1
        else:
            fail += 1
            print("  !! 写回失败: %s（%s）" % (x["recordId"], rel(path)))
    print("== 已归一 %d 条，失败 %d 条 ==" % (done, fail))
    if done:
        print("== 下一步：python tools/verify_archive.py 与 python tools/list_pending.py --strict "
              "复核；本次若把记录改回了 pending，先跑 AI 补根因再 --only step9 重出页面")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
