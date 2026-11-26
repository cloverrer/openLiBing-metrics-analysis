# -*- coding: utf-8 -*-
"""版本可用度「逐日分子/分母」的统一口径（社区链路口径，rateRule='days'）。

口径（用户确认）：
  1) 当天开始执行、当天没执行完 → 当天算「有执行」但**不可用**（开始日进分母、记不可用）；
  2) 就算最终成功，可用也只记到**结束日**；
  3) 当天完全没开始执行 → 当天不进分母（未执行的日子不计入）；
  4) **只要执行了就算有执行**：被中断的运行（Jenkins 的 ABORTED、openLiBing 的 CANCELED）
     同样说明当天真的启动过，照常进分母，但**永不计可用** —— 当日只有这类运行，
     当日就算「没有版本可用」（分母 1、分子 0），而不是「当天没跑过」。

落到逐日 vaDetail：
  daysInPeriod(分母) 满 1 的日子 = 当天有运行「开始」或「结束」的日子（去重）；
  availDays(分子)  满 1 的日子 = 当天有 iva=true 的运行「结束」。
所以跨午夜运行（开始日 ≠ 结束日）会让开始日 +1 天分母、结束日 +1 天分子（成功时），
纯开始日（当天没有任何运行结束）只进分母、分子为 0。

消费方：
  tools/collect_community_nightly.py  采集时写 _day.json 条目的 vaDetail
  tools/rebuild_community_day.py      从磁盘 pipeline.json 重建/校准历史 _day.json
两处共用本模块，避免再分叉出第二套口径。
"""


def _d10(v):
    return str(v or "")[:10]


def _span_days(sday, eday):
    """返回 [开始日, 结束日] 两个日子（相同则一个）；不做区间展开，避免把「挂起数周」的
    异常运行扩成几十天分母 —— 口径只认「哪一天开始执行」「哪一天结束」。"""
    if sday and eday and sday != eday:
        return [sday, eday]
    return [sday or eday]


def day_va(runs, never_avail_statuses=(), days_in_scope=None):
    """按统一口径算逐日 vaDetail。

    runs                   运行列表：每项含 start / end / iva / status
    never_avail_statuses   这些状态（大写，如 {"ABORTED"} / {"CANCELED", "CANCELLED"}）
                           算「执行过」→ 照常进分母，但永不计可用
    days_in_scope          允许计入的日子集合（通常 = 已有 _day.json 的归档日）；None 表示不限

    返回 {day: {"availDays": 0/1, "daysInPeriod": 0/1}}
    """
    never = {str(x).upper() for x in (never_avail_statuses or ())}
    out = {}

    def _ok(d):
        return d and (days_in_scope is None or d in days_in_scope)

    for h in runs or []:
        h = h or {}
        sday = _d10(h.get("start")) or _d10(h.get("end"))
        eday = _d10(h.get("end")) or sday
        if not sday and not eday:
            continue
        for d in _span_days(sday, eday):
            if _ok(d):
                out.setdefault(d, {"availDays": 0, "daysInPeriod": 1})
        # 中断的执行（aborted/canceled）只进分母、永不计可用
        if str(h.get("status") or "").upper() in never:
            continue
        # 可用只记结束日（跨午夜成功算结束日的）
        if h.get("iva") is True and _ok(eday):
            out.setdefault(eday, {"availDays": 0, "daysInPeriod": 1})["availDays"] = 1
    return out


def day_bs_detail(runs, skip_statuses=()):
    """逐日编译明细：{day: {"buildCount": n, "buildPassCount": m}}，按**结束日**归属。

    与旧实现一致：只统计当天结束的运行，aborted/canceled 不计入次数。
    """
    skip = {str(x).upper() for x in (skip_statuses or ())}
    out = {}
    for h in runs or []:
        if str((h or {}).get("status") or "").upper() in skip:
            continue
        d = _d10(h.get("end")) or _d10(h.get("start"))
        if not d:
            continue
        bc = h.get("bc")
        bpc = h.get("bpc")
        if bc is None and bpc is None:
            continue
        item = out.setdefault(d, {"buildCount": 0, "buildPassCount": 0})
        item["buildCount"] += int(bc or 0)
        item["buildPassCount"] += int(bpc or 0)
    return out
