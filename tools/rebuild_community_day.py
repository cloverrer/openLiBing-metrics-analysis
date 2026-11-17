# -*- coding: utf-8 -*-
"""通用重建：按磁盘上已归档的 pipeline.json，全量重算社区流水线的 _day.json 条目。

为什么需要这个工具（两个历史问题都由它一次性收敛）：
  1) 「社区失败记录整体不展示」：社区采集早期版本会先把当日 channel=community 的条目整体
     清掉、再追加本次采集的 key，非采集日的社区条目就被误删了（11-10/11-12/11-13 的
     openGauss/openEuler 就是这样丢的）。页面「执行记录」弹窗逐日读 _day.json，
     读不到条目就读不到对应流水线的 runHistory，失败记录整段消失。
  2) 「版本可用度口径调整」：口径改成「当天开始执行、当天没执行完 → 当天算不可用；
     就算成功也只把可用记到结束日；当天完全没开始执行才不计入分母」，
     历史归档里写死的 vaDetail 需要按新口径重算（口径实现见 lib/va_caliber.py）。

本工具**只读磁盘上已经归档好的 pipeline.json**，重新组装 _day.json 条目：
不联网、不重新取证、不改动 pipeline.json / 证据文件，因此可以反复安全重跑。

用法:
  python tools/rebuild_community_day.py                              # 用 config.json 的 date_range
  python tools/rebuild_community_day.py --start 2026-11-10 --end 2026-11-16
  python tools/rebuild_community_day.py --dry-run                    # 只打印将要写入的条目
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import ARCHIVE_ROOT, rel  # noqa: E402
from lib.va_caliber import day_bs_detail, day_va  # noqa: E402

CONFIG = ROOT / "config.json"

# 不计入任何统计的状态：Jenkins 的 aborted、openLiBing 的 canceled
SKIP = ("ABORTED", "CANCELED", "CANCELLED")
FAILED = ("FAILED", "FAILURE")


def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def window_from_config(args):
    cfg = load_json(CONFIG, {}) or {}
    rng = cfg.get("date_range") or {}
    start = args.start or rng.get("start")
    end = args.end or rng.get("end")
    if not start or not end:
        raise SystemExit("!! 未指定区间：请用 --start/--end，或先在 config.json 里填 date_range")
    return start, end


def window_days(start, end):
    import datetime
    s = datetime.date.fromisoformat(start)
    e = datetime.date.fromisoformat(end)
    out = []
    cur = s
    while cur <= e:
        out.append(cur.isoformat())
        cur += datetime.timedelta(days=1)
    return out


def scan(start, end):
    """返回 {day: {key: payload}}，只收 channel=community 的 pipeline.json。"""
    out = {}
    if not ARCHIVE_ROOT.exists():
        return out
    for y in sorted(ARCHIVE_ROOT.iterdir()):
        if not (y.is_dir() and y.name.isdigit()):
            continue
        for ym in sorted(y.iterdir()):
            if not ym.is_dir():
                continue
            for d in sorted(ym.iterdir()):
                day = d.name
                if not d.is_dir() or not (start <= day <= end):
                    continue
                for comp in sorted(d.iterdir()):
                    if not comp.is_dir() or comp.name.startswith("_"):
                        continue
                    for pipe in sorted(comp.iterdir()):
                        pj = pipe / "pipeline.json"
                        if not pj.is_file():
                            continue
                        j = load_json(pj, {}) or {}
                        if j.get("channel") != "community":
                            continue
                        key = j.get("key") or ("%s|%s" % (comp.name, pipe.name))
                        out.setdefault(day, {})[key] = j
    return out


def union_runs(by_day):
    """按 key 合并整区间运行清单。

    同一次运行跨午夜会被两天各存一份，早的那份是运行途中的陈旧快照
    （状态/结束时间都还是旧的）；同一 rn 只保留结束时间最新的那条。
    """
    acc = {}
    for _day, entries in by_day.items():
        for key, payload in entries.items():
            rh = ((payload.get("steps") or {}).get("step_2_runs") or {}).get("runHistory") or []
            m = acc.setdefault(key, {})
            for h in rh:
                rn = h.get("rn")
                if rn is None:
                    continue
                cur = m.get(rn)
                if cur is None or str(h.get("end") or "") > str(cur.get("end") or ""):
                    m[rn] = h
    return {k: list(v.values()) for k, v in acc.items()}


def entry_from(payload, day, va, bs, runs_total):
    """一天一条的 _day.json 条目：当天切片（运行/记录数）+ 新口径逐日 vaDetail/bsDetail。"""
    comp = payload.get("component")
    pipe = payload.get("pipeline")
    steps = payload.get("steps") or {}
    lights = steps.get("step_1_lights") or {}
    plmeta = lights.get("pipeline") or {}
    sel = lights.get("selection") or {}
    rh = (steps.get("step_2_runs") or {}).get("runHistory") or []
    logc = (steps.get("step_5_logs") or {}).get("counts") or {}
    cnt = payload.get("counts") or {}
    recs = payload.get("records") or []
    pdir = ARCHIVE_ROOT / day[:4] / day[:7] / day / comp / pipe
    bc = int((bs or {}).get("buildCount") or 0)
    bpc = int((bs or {}).get("buildPassCount") or 0)
    return {
        "component": comp,
        "pipeline": pipe,
        "pipelineName": payload.get("pipelineName") or plmeta.get("pipelineName") or pipe,
        "platform": payload.get("platform"),
        "pipelineId": plmeta.get("pipelineId"),
        "key": payload.get("key") or ("%s|%s" % (comp, pipe)),
        "channel": "community",
        "dims": list(plmeta.get("dims") or ["va", "bs"]),
        "rateRule": sel.get("rateRule") or "days",
        "vaDetail": {"availDays": int((va or {}).get("availDays") or 0),
                     "daysInPeriod": int((va or {}).get("daysInPeriod") or 0)},
        "bsDetail": {"buildPassCount": bpc, "buildCount": bc},
        "vaRate": 1.0 if (va or {}).get("availDays") else 0.0,
        "bsRate": (bpc / float(bc)) if bc else None,
        "vaRule": "days",
        "bsAgg": "mean",
        "runsInPeriod": int(runs_total),
        "runsToday": len(rh),
        "failedRunsToday": sum(1 for h in rh if str(h.get("status") or "").upper() in FAILED),
        "path": rel(pdir),
        "manifest": rel(pdir / "pipeline.json"),
        "file": rel(pdir / "pipeline.json"),
        "layout": payload.get("schema") or "pipeline/1",
        "records": int(cnt.get("records") or len(recs)),
        "runNumbers": [r.get("buildNumber") for r in recs],
        "tasks": int(cnt.get("tasks") or 0),
        "cases": int(cnt.get("cases") or 0),
        "errorMessages": int(cnt.get("errorMessages") or 0),
        "evidenceFiles": int(logc.get("logFiles") or 0),
        "byCategory": {},
        "note": None,
    }


def synth_from(template, day, va):
    """当天只有运行「开始」、没有任何运行「结束」的日子：补一条轻量条目进分母（分子 0）。"""
    e = dict(template)
    e["vaDetail"] = {"availDays": int((va or {}).get("availDays") or 0),
                     "daysInPeriod": int((va or {}).get("daysInPeriod") or 0)}
    e["vaRate"] = 1.0 if (va or {}).get("availDays") else 0.0
    e["runsToday"] = 0
    e["failedRunsToday"] = 0
    e["records"] = 0
    e["runNumbers"] = []
    e["tasks"] = 0
    e["cases"] = 0
    e["errorMessages"] = 0
    e["evidenceFiles"] = 0
    e["byCategory"] = {}
    e["note"] = "当日仅启动、未结束：计入分母但不计可用（跨午夜运行）"
    return e


def write_day(day, entries, dry=False):
    """把当日 _day.json 里**全部** channel=community 条目替换成重算结果，其余条目原样保留。"""
    p = ARCHIVE_ROOT / day[:4] / day[:7] / day / "_day.json"
    d = load_json(p, {}) or {}
    keep = [x for x in (d.get("pipelines") or [])
            if not (isinstance(x, dict) and x.get("channel") == "community")]
    pipes = keep + list(entries)
    counts = d.get("counts") or {}
    counts.update({
        "components": len({x.get("component") for x in pipes}),
        "pipelines": len(pipes),
        "records": sum(int(x.get("records") or 0) for x in pipes),
        "tasks": sum(int(x.get("tasks") or 0) for x in pipes),
        "cases": sum(int(x.get("cases") or 0) for x in pipes),
        "errorMessages": sum(int(x.get("errorMessages") or 0) for x in pipes),
        "evidenceFiles": sum(int(x.get("evidenceFiles") or 0) for x in pipes),
    })
    d.setdefault("date", day)
    d["pipelines"] = pipes
    d["counts"] = counts
    if dry:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def merge_index(days):
    """刷新 out/archive/_index.json 的计数（以当日 _day.json 为准重算），不改 days[] 日期清单。"""
    p = ARCHIVE_ROOT / "_index.json"
    d = load_json(p, {}) or {}
    prods = load_json(ARCHIVE_ROOT / "_products.json", {}) or {}
    d["productCount"] = len(prods.get("products") or [])
    for item in (d.get("days") or []):
        day = item.get("date")
        if day not in days:
            continue
        dd = load_json(ARCHIVE_ROOT / day[:4] / day[:7] / day / "_day.json", {}) or {}
        c = dd.get("counts") or {}
        for k in ("components", "pipelines", "records", "tasks", "cases", "errorMessages"):
            if k in c:
                item[k] = c[k]
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    start, end = window_from_config(args)
    scope = set(window_days(start, end))
    print("== 社区条目重建：%s ~ %s" % (start, end))

    by_day = scan(start, end)
    if not by_day:
        raise SystemExit("!! 区间内没有社区归档，无需重建")
    runs_by = union_runs(by_day)

    day_entries = {}
    for key in sorted(runs_by):
        runs = runs_by[key]
        dva = day_va(runs, skip_statuses=SKIP, days_in_scope=scope)
        dbs = day_bs_detail(runs, skip_statuses=SKIP)
        days_with_art = sorted(d for d in by_day if key in by_day[d])
        template = None
        if days_with_art:
            d0 = days_with_art[-1]
            template = entry_from(by_day[d0][key], d0, dva.get(d0), dbs.get(d0), len(runs))
        for day in sorted(set(days_with_art) | set(dva)):
            if day in by_day and key in by_day[day]:
                e = entry_from(by_day[day][key], day, dva.get(day), dbs.get(day), len(runs))
            elif template is not None:
                e = synth_from(template, day, dva.get(day))
            else:
                continue
            day_entries.setdefault(day, []).append(e)
        exec_days = sum(1 for v in dva.values() if v.get("daysInPeriod"))
        ok_days = sum(1 for v in dva.values() if v.get("availDays"))
        print("  %-64s 运行 %-3d 执行日 %d 可用日 %d%s" % (
            key, len(runs), exec_days, ok_days,
            "（无可用）" if exec_days and not ok_days else ""))
        if not exec_days:
            print("      !! 该流水线区间内没有可计入的执行日（全是 aborted/canceled）")

    for day in sorted(day_entries):
        write_day(day, day_entries[day], dry=args.dry_run)
    if not args.dry_run:
        merge_index(set(day_entries))
    print("\n== 完成：%d 个归档日被重算%s" % (len(day_entries), "（dry-run，未落盘）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
