# -*- coding: utf-8 -*-
"""记录级维度归属 —— 判定一条运行「影响当日哪个维度的指标」。

为什么要单独成模块：这份口径有三个消费方，必须完全一致，否则又会分叉出「静默漏分析」：
  1) steps/step_6_records.py  写 analysis.status（pending / na）与记录里的 light.affects；
  2) tools/verify_archive.py  交付前独立重算，兜住「应分析却没根因」的漏项；
  3) tools/list_pending.py    流程收尾时独立重算，--strict 一并拦截。

口径（**当日切片**，不看 step_1 的区间看板值 —— 区间聚合值与当日值在边界上会不一致）：
  va 命中 = 流水线含 va 维度，且当日版本不可用（当日没有任何 isVersionAvailable=true 的运行）
  bs 命中 = 流水线含 bs 维度，且这条运行自身编译未全过（buildCount>0 且 buildPassCount<buildCount）
命中任一维度 → 需要 AI 根因分析；两个都不命中 → 不做分析（达标日里的用例/环境类失败等）。

页面（steps/step_9_pages.py）里有一份等价的 JS 实现：按同一份归属决定「这条失败在哪个
维度页展示」，因此「页面显示的」与「要求有根因的」永远是同一批记录。
"""


def affects_of(dims, day_avail, run):
    """返回这条运行实际影响的维度列表（"va" / "bs" 的子集）。

    dims     流水线维度集合（含 "va" / "bs"）
    day_avail 当日可用标记：1 = 当日版本可用；0 / None = 当日不可用或未知（按不可用处理，宁可多分析）
    run      该次运行（取 bc / bpc 判编译口径）
    """
    dims = set(dims or [])
    aff = []
    if "va" in dims and day_avail != 1:
        aff.append("va")
    bc, bpc = (run or {}).get("bc"), (run or {}).get("bpc")
    if "bs" in dims and isinstance(bc, int) and isinstance(bpc, int) and bc > 0 and bpc < bc:
        aff.append("bs")
    return aff


def day_avail_of(run_history, day):
    """某日是否可用：当日起任一运行的 iva=true 即算可用，返回 1；否则 0。

    与 step_2 的 day_avail / step_7 归档里 _day.json 的 vaDetail.availDays 同一口径
    （当日存在 iva=true 的运行）。day 支持 YYYY-MM-DD（也兼容 MM-DD）。
    """
    d = str(day or "")
    k10, kmd = d[:10], d[5:10]
    for h in run_history or []:
        end = str(h.get("end") or "")
        if h.get("iva") is True and (end[:10] == k10 or end[5:10] == kmd):
            return 1
    return 0
