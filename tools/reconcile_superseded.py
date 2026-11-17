# -*- coding: utf-8 -*-
"""跨日陈旧副本清理 —— 同一 pipelineRunId 只保留「结束时间最晚」的归档副本。

为什么会有重复：归档按【执行结束时间】把一条运行落到某一天。但采集很可能是在运行仍在
进行时做的快照 —— 同一条运行先在当天落了一份「运行中」记录（状态 FAILED、结束时间偏早、
编译计数只统计到已经跑完的那部分），运行真正结束（状态翻成 COMPLETED）后才在结束日落了
权威副本。两份同一 pipelineRunId 的记录彼此状态/结束时间相悖：较早的那份是陈旧快照，
一旦留在归档里，就会

  1) 让当日的编译分子/分母被重复计入（组件级编译成功率被拉低，例如 MindCluster 97.96%）；
  2) 让「这条到底该不该分析」在两个归档日得到相反答案，校验据此误报漏分析 / 多分析。

口径：同一 pipelineRunId 跨多个归档日出现时，只保留 end 最晚（并列取归档日最晚）的那一份；
其余从该日 pipeline.json 的 `records[]` 与 `steps.step_2_runs.runHistory` 中移除，
并同步重算该日的 vaDetail/bsDetail、比率、记录计数与 `_day.json` 汇总。

附带「版本可用度逐日口径重算」（--recalib-va）：口径升级成「当天有运行**开始或结束**都算
有执行记录」后，历史归档里写死的 vaDetail 会失真（跨午夜运行的开始日在旧口径下不进分母）。
该模式按磁盘上已归档的 pipeline.json runHistory 就地重算 openlibing 流水线的逐日 vaDetail，
跨午夜开始日缺条目时补一条轻量 synth 条目；社区条目由 tools/rebuild_community_day.py 负责。
只读归档、不联网、不重新取证，可反复安全重跑。

用法:
  python tools/reconcile_superseded.py                   # 只扫描并列清单（不改任何文件）
  python tools/reconcile_superseded.py --apply           # 就地清理陈旧副本并重算当日汇总
  python tools/reconcile_superseded.py --recalib-va      # 扫描版本可用度口径差异（不改文件）
  python tools/reconcile_superseded.py --recalib-va --apply   # 就地重算归档逐日 vaDetail
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc, va_caliber  # noqa: E402
from lib.paths import (ARCHIVE_ROOT, archive_day_dir, date_of,  # noqa: E402
                       iter_archive_days, iter_scoped_pipelines)

FAIL_STATUS = ("FAILED", "CANCELED", "CANCELLED")


def _load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _save_json(p, obj):
    p = Path(p)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(p))


def _day_of(s):
    return date_of(str(s or "").replace(" ", "T"))


def scan():
    """扫描全部归档日，返回 {rid: [副本…]}（只保留跨多个归档日的 rid）。"""
    seen = {}
    for day, day_dir in iter_archive_days():
        for comp, pipe, adir in iter_scoped_pipelines(day_dir):
            doc = pipeline_doc.load(adir)
            if not doc:
                continue
            for rec in doc.get("records") or []:
                rid = str(rec.get("pipelineRunId") or "")
                if not rid:
                    continue
                seen.setdefault(rid, []).append({
                    "day": day, "component": comp, "pipeline": pipe, "dir": adir,
                    "rn": rec.get("buildNumber"), "status": rec.get("status"),
                    "end": str(rec.get("endedAt") or ""),
                })
    return {k: v for k, v in seen.items() if len(v) > 1}


def plan(dups):
    """把重复副本拆成 (保留清单, 待删清单)。每条 rid 保留 end 最晚的一份。"""
    keeps, drops = [], []
    for rid, copies in dups.items():
        copies = sorted(copies, key=lambda c: (c["end"], c["day"]))
        keeps.append(dict(copies[-1], rid=rid))
        for c in copies[:-1]:
            drops.append(dict(c, rid=rid))
    drops.sort(key=lambda x: (x["day"], x["component"], x["pipeline"]))
    return keeps, drops


def _rec_counts(recs):
    return {
        "records": len(recs),
        "tasks": sum((r.get("counts") or {}).get("tasks") or 0 for r in recs),
        "cases": sum((r.get("counts") or {}).get("cases") or 0 for r in recs),
        "errorMessages": sum((r.get("counts") or {}).get("errorMessages") or 0 for r in recs),
    }


def _by_category(recs):
    cats = {}
    for r in recs:
        c = (r.get("verdict") or {}).get("category") or "unknown"
        cats[c] = cats.get(c, 0) + 1
    return cats


def _recompute_pipeline(adir, day, drop_rids):
    """就地移除某流水线某日的陈旧运行，重算该 pipeline.json 的正文计数与当日口径。

    返回当日（重算后）的 {records, today, failed_today, vaDetail, bsDetail,
    vaRate, bsRate, byCategory} ，供调用方回写 _day.json。
    """
    doc = pipeline_doc.load(adir)
    if not doc:
        return None
    rid_set = {str(r) for r in drop_rids}
    steps = doc.setdefault("steps", {})
    s2 = steps.setdefault("step_2_runs", {})
    s6 = steps.setdefault("step_6_records", {})

    # 1) runHistory / failedRuns 去掉陈旧运行
    rh = [h for h in (s2.get("runHistory") or []) if str(h.get("rid") or "") not in rid_set]
    s2["runHistory"] = rh
    s2["failedRuns"] = [f for f in (s2.get("failedRuns") or [])
                        if str(f.get("rid") or "") not in rid_set]

    # 2) records[] 去掉陈旧记录
    recs = [r for r in (doc.get("records") or [])
            if str(r.get("pipelineRunId") or "") not in rid_set]
    doc["records"] = recs

    # 3) 当日运行视图：按新的 runHistory 重排纳入/排除原因
    today = [h for h in rh if _day_of(h.get("end")) == day]
    today_rns = {str(h.get("rn")) for h in today}
    s2["runs"] = [{
        "rn": h.get("rn"), "pipelineRunId": h.get("rid"),
        "start": h.get("start"), "end": h.get("end"), "status": h.get("status"),
        "endedDate": _day_of(h.get("end")),
        "included": str(h.get("rn")) in today_rns,
        "reason": ("结束时间在归档日内，纳入当日归档记录（成功运行，只记录不取证）"
                   if str(h.get("rn")) in today_rns
                   else "结束时间属 %s，已归档到该日期目录" % _day_of(h.get("end"))),
    } for h in rh]
    s2["keptRuns"] = len(today)
    s2["keptFailedRuns"] = len([r for r in recs
                                if str(r.get("status") or "").upper() in FAIL_STATUS])
    s2["excludedRuns"] = len(s2["runs"]) - len(today)

    # 4) 各层计数
    counts = _rec_counts(recs)
    s6["counts"] = dict(s6.get("counts") or {}, **counts)
    doc["counts"] = dict(doc.get("counts") or {}, **counts)
    doc["dateBasis"] = dict(doc.get("dateBasis") or {})
    doc["dateBasis"]["runs"] = [{"rn": h.get("rn"), "status": h.get("status"),
                                 "endedAt": h.get("end")} for h in today]

    # 5) 编译分子/分母（比率由调用方按统一口径重算，见 _recompute_day）
    day_bc = sum((h.get("bc") or 0) for h in today if h.get("bc") is not None)
    day_bpc = sum((h.get("bpc") or 0) for h in today if h.get("bpc") is not None)
    all_bc = sum((h.get("bc") or 0) for h in rh if h.get("bc") is not None)
    all_bpc = sum((h.get("bpc") or 0) for h in rh if h.get("bpc") is not None)
    pipeline_doc.save(adir, doc)
    return {
        "records": recs, "today": today, "runHistory": rh,
        "failed_today": [r for r in recs
                         if str(r.get("status") or "").upper() in FAIL_STATUS],
        "runsInPeriod": len(rh),
        "bsDetail": {"buildPassCount": day_bpc, "buildCount": day_bc},
        "bsRate": (min(1.0, all_bpc / float(all_bc)) if all_bc > 0 else None),
        "byCategory": _by_category(recs),
    }


def _recompute_day(day, patches):
    """按流水线级重算结果回写该日 _day.json 的条目与日级汇总计数。"""
    dp = archive_day_dir(day) / "_day.json"
    if not dp.is_file():
        return False
    dd = _load_json(dp)
    workdays = {str(x) for x in (dd.get("workdays") or [])}
    for (comp, pipe), info in patches.items():
        for entry in dd.get("pipelines") or []:
            if entry.get("component") != comp or entry.get("pipeline") != pipe:
                continue
            recs = info["records"]
            entry["records"] = len(recs)
            entry["runNumbers"] = [r.get("buildNumber") for r in recs]
            entry["tasks"] = sum((r.get("counts") or {}).get("tasks") or 0 for r in recs)
            entry["cases"] = sum((r.get("counts") or {}).get("cases") or 0 for r in recs)
            entry["errorMessages"] = sum((r.get("counts") or {}).get("errorMessages") or 0
                                         for r in recs)
            entry["byCategory"] = info["byCategory"]
            entry["runsInPeriod"] = info["runsInPeriod"]
            entry["runsToday"] = len(info["today"])
            entry["failedRunsToday"] = len(info["failed_today"])
            entry["bsDetail"] = info["bsDetail"]
            entry["bsRate"] = info["bsRate"]
            # 版本可用度 = 可用日 / 该流水线有执行记录的天数（当天有运行**开始或结束**才算，
            # 跨午夜运行的开始日也进分母）。与 step_7 的 recompute_rates、页面 vaDenOf 同口径：
            # 必须用**整区间** runHistory 重算，而不是「当日运行」，否则分母只有一天、比率会算成 1/N。
            vm = va_caliber.day_va(
                [{"status": h.get("status"), "start": h.get("start"),
                  "end": h.get("end"), "iva": h.get("iva") is True}
                 for h in info["runHistory"]],
                skip_statuses=("CANCELED", "CANCELLED"),
                days_in_scope=(workdays or None))
            av = sum(1 for v in vm.values() if v.get("availDays"))
            dn = sum(1 for v in vm.values() if v.get("daysInPeriod"))
            entry["vaDetail"] = vm.get(day) or {"availDays": 0, "daysInPeriod": 0}
            entry["vaRate"] = (av / float(dn)) if dn > 0 else None
            if not info["today"]:
                entry["note"] = "当日无任何运行记录（该流水线的运行按结束时间归属到了别的日期）"
            break
    pipes = dd.get("pipelines") or []
    cats = {}
    for p in pipes:
        for k, v in (p.get("byCategory") or {}).items():
            cats[k] = cats.get(k, 0) + v
    counts = dd.setdefault("counts", {})
    counts["records"] = sum(p.get("records") or 0 for p in pipes)
    counts["tasks"] = sum(p.get("tasks") or 0 for p in pipes)
    counts["cases"] = sum(p.get("cases") or 0 for p in pipes)
    counts["errorMessages"] = sum(p.get("errorMessages") or 0 for p in pipes)
    counts["byCategory"] = cats
    _save_json(dp, dd)
    return True


def _refresh_index():
    """按各日 _day.json 重算 _index.json 的逐日计数（不动日期清单）。"""
    ip = ARCHIVE_ROOT / "_index.json"
    if not ip.is_file():
        return
    idx = _load_json(ip)
    for row in idx.get("days") or []:
        dd = archive_day_dir(row.get("date")) / "_day.json"
        if not dd.is_file():
            continue
        d = _load_json(dd)
        c = d.get("counts") or {}
        row["components"] = c.get("components") or row.get("components")
        row["pipelines"] = c.get("pipelines") or row.get("pipelines")
        row["records"] = c.get("records") or 0
        row["tasks"] = c.get("tasks") or 0
        row["cases"] = c.get("cases") or 0
        row["errorMessages"] = c.get("errorMessages") or 0
    _save_json(ip, idx)


# ---------------------------------------------- 版本可用度逐日口径重算（口径变更后的归档修复）
# 口径（lib/va_caliber）：分母 = 当天有运行**开始或结束**（去重）→ 跨午夜运行的开始日也进分母；
# 分子 = 当天有 iva=true 的运行**结束**。归档里写死的 vaDetail 一旦口径升级就会失真，
# 这里按磁盘上已经归档好的 pipeline.json runHistory 就地重算，不联网、不重新取证。
OL_SKIP = ("CANCELED", "CANCELLED")     # openlibing 侧的取消状态
# 同一运行跨日会有多份副本，只认结束时间最晚的权威副本（口径见模块 docstring）
def _scan_archive():
    """返回 (union, entries, channels)：
    union    {key: {rn: run}}   各流水线整区间运行清单（跨日副本去重，取 end 最晚）
    entries  {day: {key: entry}} 各归档日 _day.json 的流水线条目
    channels {key: 'community' | 'openlibing'}
    """
    union, entries, channels = {}, {}, {}
    for day, day_dir in iter_archive_days():
        for it in (_load_json(day_dir / "_day.json") or {}).get("pipelines") or []:
            key = it.get("key") or ("%s|%s" % (it.get("component"), it.get("pipeline")))
            entries.setdefault(day, {})[key] = it
            channels[key] = "community" if it.get("channel") == "community" else "openlibing"
        for comp, pipe, adir in iter_scoped_pipelines(day_dir):
            doc = pipeline_doc.load(adir)
            if not doc:
                continue
            key = doc.get("key") or ("%s|%s" % (comp, pipe))
            m = union.setdefault(key, {})
            rh = ((doc.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
            for h in rh:
                rn = h.get("rn")
                cur = m.get(rn)
                if cur is None or str(h.get("end") or "") > str(cur.get("end") or ""):
                    m[rn] = h
    return union, entries, channels


def _synth_from(template, vd):
    """当天只有运行「开始」、没有任何运行「结束」：补一条轻量条目进分母（分子 0）。"""
    e = json.loads(json.dumps(template, ensure_ascii=False))
    e["vaDetail"] = {"availDays": int(vd.get("availDays") or 0),
                     "daysInPeriod": int(vd.get("daysInPeriod") or 0)}
    e["runsToday"] = 0
    e["failedRunsToday"] = 0
    e["records"] = 0
    e["runNumbers"] = []
    e["tasks"] = e["cases"] = e["errorMessages"] = 0
    e["evidenceFiles"] = 0
    e["byCategory"] = {}
    e["note"] = ("当日仅启动、未结束（跨午夜运行）：计入版本可用度分母，当天不计可用")
    return e


def _refresh_day_counts(day):
    """按当日 _day.json 的流水线条目重算日级计数（补 synth 条目后必须同步）。"""
    p = archive_day_dir(day) / "_day.json"
    d = _load_json(p) or {}
    pipes = d.get("pipelines") or []
    counts = d.setdefault("counts", {})
    counts.update({
        "components": len({x.get("component") for x in pipes}),
        "pipelines": len(pipes),
        "records": sum(int(x.get("records") or 0) for x in pipes),
        "tasks": sum(int(x.get("tasks") or 0) for x in pipes),
        "cases": sum(int(x.get("cases") or 0) for x in pipes),
        "errorMessages": sum(int(x.get("errorMessages") or 0) for x in pipes),
        "evidenceFiles": sum(int(x.get("evidenceFiles") or 0) for x in pipes),
    })
    _save_json(p, d)


def recalib_va(apply=False):
    """按新口径重算归档里每条 openlibing 流水线的逐日 vaDetail（社区条目不动，另有重建工具）。

    只改 vaDetail 与流水线级 vaRate，其余字段（records/runNumbers/path/platform/dims …）
    一律保留；跨午夜开始日缺条目时补一条 synth 条目（与第 7 步归档同口径）。
    """
    days = [day for day, _ in iter_archive_days()]
    if not days:
        print("!! 归档区为空，无可重算")
        return 0
    scope = set(days)
    union, entries, channels = _scan_archive()
    changes, synths = [], []
    for key in sorted(union):
        if channels.get(key) == "community":
            continue
        runs = [{"status": h.get("status"), "start": h.get("start"),
                 "end": h.get("end"), "iva": h.get("iva") is True}
                for h in union[key].values()]
        vm = va_caliber.day_va(runs, skip_statuses=OL_SKIP, days_in_scope=scope)
        a = sum(1 for v in vm.values() if v.get("availDays"))
        n = sum(1 for v in vm.values() if v.get("daysInPeriod"))
        for day in sorted(vm):
            v = vm[day]
            exp = {"availDays": int(v.get("availDays") or 0),
                   "daysInPeriod": int(v.get("daysInPeriod") or 0)}
            if not exp["daysInPeriod"]:
                continue
            ent = (entries.get(day) or {}).get(key)
            if ent is None:
                synths.append((day, key, exp))
                continue
            cur = ent.get("vaDetail") or {}
            if (int(cur.get("availDays") or 0) != exp["availDays"]
                    or int(cur.get("daysInPeriod") or 0) != exp["daysInPeriod"]):
                changes.append((day, key, cur, exp,
                                (a / float(n)) if n > 0 else None, ent.get("rateRule")))
    print("== 版本可用度逐日口径重算（分母 = 当天有运行开始或结束）==")
    print("需要更新 vaDetail 的条目：%d 条" % len(changes))
    for day, key, cur, exp, rate, rule in changes:
        print("  %s %-52s %s -> %s" % (day, key, cur, exp))
    print("需要新补 synth 条目：%d 条" % len(synths))
    for day, key, exp in synths:
        print("  %s %-52s %s" % (day, key, exp))
    if not changes and not synths:
        print("结论：归档逐日口径已与当前口径一致，无需改动")
        return 0
    if not apply:
        print("（dry-run，未改动任何文件；加 --apply 就地写回）")
        return 0
    touched = set()
    for day, key, cur, exp, rate, rule in changes:
        p = archive_day_dir(day) / "_day.json"
        d = _load_json(p) or {}
        for it in d.get("pipelines") or []:
            k = it.get("key") or ("%s|%s" % (it.get("component"), it.get("pipeline")))
            if k != key:
                continue
            it["vaDetail"] = dict(exp)
            if rule == "runs" and rate is not None:
                it["vaRate"] = rate
        _save_json(p, d)
        touched.add(day)
    for day, key, exp in synths:
        p = archive_day_dir(day) / "_day.json"
        d = _load_json(p) or {}
        template = None
        for d2 in sorted(days, reverse=True):        # 取该流水线已有的条目当模板
            template = (entries.get(d2) or {}).get(key)
            if template is not None:
                break
        if template is None:
            continue
        (d.setdefault("pipelines", [])).append(_synth_from(template, exp))
        _save_json(p, d)
        touched.add(day)
    for day in sorted(touched):
        _refresh_day_counts(day)
    _refresh_index()
    print("== 已重算 %d 个归档日（更新 %d 条 + 新增 %d 条）=="
          % (len(touched), len(changes), len(synths)))
    return 0


def main():
    ap = argparse.ArgumentParser(description="清理同一 pipelineRunId 的跨日陈旧副本 / 重算版本可用度口径")
    ap.add_argument("--apply", action="store_true", help="就地写回（默认只扫描，不改任何文件）")
    ap.add_argument("--recalib-va", action="store_true",
                    help="按当前版本可用度口径重算归档逐日 vaDetail（口径变更后的历史修复）")
    args = ap.parse_args()
    if args.recalib_va:
        return recalib_va(apply=args.apply)

    dups = scan()
    keeps, drops = plan(dups)
    print("== 跨日陈旧副本自检 ==")
    print("同一 pipelineRunId 出现在多个归档日的运行：%d 组（应只保留结束时间最晚的一份）"
          % len(dups))
    for k in keeps:
        print("  保留 %s %s/%s #%s %s（end %s）"
              % (k["day"], k["component"], k["pipeline"], k["rn"], k["status"], k["end"]))
    for x in drops:
        print("  删除 %s %s/%s #%s %s（end %s，陈旧快照）"
              % (x["day"], x["component"], x["pipeline"], x["rn"], x["status"], x["end"]))
    if not drops:
        print("结论：无跨日陈旧副本，归档一致")
        return 0
    if not args.apply:
        print("（dry-run，未改动任何文件；加 --apply 就地清理）")
        return 0

    by_key = {}
    dir_of = {}
    for x in drops:
        k = (x["day"], x["component"], x["pipeline"])
        by_key.setdefault(k, []).append(x["rid"])
        dir_of[k] = x["dir"]           # 用扫描记下的真实目录（目录名经 safe_name 规整过）
    patches_by_day = {}
    for (day, comp, pipe), rids in sorted(by_key.items()):
        info = _recompute_pipeline(dir_of[(day, comp, pipe)], day, rids)
        if info is not None:
            patches_by_day.setdefault(day, {})[(comp, pipe)] = info
    for day, patches in patches_by_day.items():
        _recompute_day(day, patches)
    _refresh_index()
    print("== 已就地清理 %d 条陈旧副本，重算 %d 个归档日汇总 =="
          % (len(drops), len(patches_by_day)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
