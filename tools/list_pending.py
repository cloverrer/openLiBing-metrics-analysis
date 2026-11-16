# -*- coding: utf-8 -*-
"""待 AI 分析清单（只读）—— 第 8 步（AI）的唯一入口索引。

职责划分：
  脚本负责「哪些记录需要分析」+「每条记录的证据在哪」；
  AI 只负责读证据、写根因（写回用 tools/write_analysis.py），不碰筛选逻辑。

口径（与 steps/step_6_records.py 一致）：
  analysis.status=pending → 需要 AI 分析（非 1 指标的失败/取消运行）；
  analysis.status=na      → 不做 AI 分析（成功运行 / 当日两指标都为 1 的达标日）。
  vllm-ascend 的指标在第 2 步已按 scheduled 运行重算，达标判定用的就是重算值。
  遍历口径以当日 _day.json 的 pipelines 为准：磁盘上多出的旧目录（改名前/旧版本残留）
  会跳过并提示，不参与 pending 统计，也不需要手工删目录。

用法:
  python tools/list_pending.py                     # 最近一个归档日的待分析记录
  python tools/list_pending.py --date 2026-11-06   # 指定归档日
  python tools/list_pending.py --all               # 全部归档日的待分析记录
  python tools/list_pending.py --status na         # 反向查看被排除的记录
  python tools/list_pending.py --show <recordId>   # 单条记录的分析输入摘要（不含日志正文）
  python tools/list_pending.py --json out/state/pending.json   # 另存机器可读清单
  python tools/list_pending.py --strict            # 独立重算「应分析集合」，有 pending/漏分析/多分析即退出码 2

输出纪律：单次回显 ≤ 100 行（超出只提示总数，用 --date/--limit 收窄），避免触发输出过长中断。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.dim_affects import affects_of, day_avail_of  # noqa: E402
from lib.paths import (ARCHIVE_ROOT, day_pipeline_scope, iter_archive_days,  # noqa: E402
                       rel, stale_pipeline_dirs)

DEFAULT_LIMIT = 40
SHOW_LIST_MAX = 12          # --show 时每类列表最多打印条数
SHOW_TEXT_MAX = 200         # --show 时单条文本截断长度
FAIL_STATUS = {"FAILED", "CANCELED", "CANCELLED"}


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def iter_records(day_dir, allowed=None):
    """遍历某归档日的全部单条记录：(组件目录名, 流水线目录名, 记录, 所在文件, 序号)。

    记录正文现在都在 `pipeline.json` 的 `records[]` 里（老归档退回 `records/run_*.json`）；
    序号用于把定位串写成 `pipeline.json records[3]`，翻查时一眼能找到。

    allowed 非空时只遍历集合内的 (组件, 流水线) 目录。
    """
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            if not pipe.is_dir():
                continue
            if allowed is not None and (comp.name, pipe.name) not in allowed:
                continue
            pdoc = pipeline_doc.path_of(pipe)
            if pdoc.is_file():
                doc = pipeline_doc.load(pipe) or {}
                for i, rec in enumerate(doc.get("records") or []):
                    yield comp.name, pipe.name, rec, pdoc, i, doc
                continue
            rd = pipe / "records"
            if not rd.is_dir():
                continue
            for f in sorted(rd.glob("run_*.json")):
                try:
                    rec = load_json(f)
                except (ValueError, OSError) as exc:
                    print("!! 记录读取失败 %s: %s" % (rel(f), exc))
                    continue
                yield comp.name, pipe.name, rec, f, None, None


def where(x):
    """记录在归档里的定位串：新结构是 `pipeline.json records[3]`，老归档是记录文件本身。"""
    src = rel(x["file"])
    return src if x.get("index") is None else "%s records[%d]" % (src, x["index"])


def rec_affects(rec, doc, day):
    """一条记录实际影响的维度（"va"/"bs" 子集）。

    新归档直接采信 step_6 写下的 light.affects；缺该字段（老归档）就地按同一份当日口径
    重算（lib/dim_affects），保证与 step_6 / verify_archive / 页面完全一致。
    只对失败/取消记录判归属：成功运行不参与分析，归属恒为空。
    """
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


def collect(dates, status, stale=None):
    """按日期收集指定 analysis.status 的记录。

    遍历口径以当日 _day.json 为准；磁盘上多出的历史残留目录不计入，
    其路径追加到 stale（传空列表时）供调用方提示。
    """
    got = []
    for d in dates:
        day_dir = ARCHIVE_ROOT / d[:4] / d[:7] / d
        if not day_dir.is_dir():
            continue
        allowed = day_pipeline_scope(day_dir)
        if stale is not None:
            for comp, pipe, _ in stale_pipeline_dirs(day_dir):
                stale.append("%s/%s/%s" % (d, comp, pipe))
        for comp, pipe, rec, f, idx, doc in iter_records(day_dir, allowed):
            an = rec.get("analysis") or {}
            if not status or status == "all":
                pass  # 不过滤
            elif status == "pending":
                if an.get("status") != "pending":
                    continue
            elif status == "na":
                if an.get("status") != "na":
                    continue
            elif an.get("status") != status:
                continue
            got.append({"date": d, "component": comp, "pipeline": pipe,
                        "record": rec, "file": f, "index": idx,
                        "affects": rec_affects(rec, doc, d)})
    got.sort(key=lambda x: (x["date"], x["component"], x["pipeline"],
                            int(x["record"].get("buildNumber") or 0)))
    return got


def audit(rows):
    """独立重算「应分析集合」，找出漏分析 / 多分析。

    - 漏分析   : 影响当日某维度指标，却是 na（或 done 但根因为空）—— 正是要堵的静默漏项
    - 待分析   : 影响当日指标但仍是 pending（流程没跑完）
    - 多分析   : 不影响当日任何维度指标，却 pending / 已有根因（口径漂移的自证）
    """
    leak, pending, extra = [], [], []
    for x in rows:
        rec = x["record"]
        an = rec.get("analysis") or {}
        st = an.get("status") or ""
        root = str(an.get("rootCause") or "").strip()
        aff = x.get("affects") or []
        if aff:
            if st == "na":
                leak.append(x)
            elif st == "pending":
                pending.append(x)
            elif st == "done" and not root:
                leak.append(x)
        elif st in ("pending", "done"):
            extra.append(x)
    return leak, pending, extra


def lights_text(rec):
    lt = rec.get("light") or {}
    def pct(v):
        try:
            return "%.0f%%" % (float(v) * 100)
        except (TypeError, ValueError):
            return "--"
    return "VA %s / BS %s" % (pct(lt.get("vaRate")), pct(lt.get("bsRate")))


def pad(s, n):
    """按显示宽度左对齐（中文按 2 列计，避免表格错位）。"""
    s = str(s)
    w = sum(2 if ord(c) > 127 else 1 for c in s)
    return s + " " * max(0, n - w) if w <= n else cut(s, n)


def cut(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:max(0, n - 1)] + "…"


def cmd_list(args):
    days = [d for d, _ in iter_archive_days()]
    if args.date:
        days = [args.date]
    elif not args.all and not args.strict and days:
        # 展示态默认只看最近归档日；--strict 是完成判据的机器校验，必须覆盖全部归档日——
        # 否则老归档日里的漏分析/多分析（本工具的主要拦截目标）根本扫不到，会静默漏过。
        days = days[-1:]
    if not days:
        print("!! 没有归档日目录（先跑 python run_pipeline.py）")
        return 1

    stale = []
    rows = collect(days, args.status, stale=stale)
    label = ("待 AI 根因分析" if args.status == "pending" else "不做 AI 分析" if args.status == "na"
             else "全部记录" if not args.status else args.status)
    scope = "全部归档日" if (args.all or args.date or args.strict) else "最近归档日"
    print("== %s：%d 条（%s %s；口径：只分析非 1 指标，vllm-ascend 用重算值）"
          % (label, len(rows), scope, (days[0] if len(days) == 1 else "%s~%s" % (days[0], days[-1]))))
    if stale:
        print("   注：%d 个目录不在当日 _day.json 口径内（旧版本/改名前残留），已跳过不计：%s"
              % (len(stale), ", ".join(stale[:5]) + ("…" if len(stale) > 5 else "")))
    if not rows:
        print("   （无）")
    else:
        shown = rows if args.limit <= 0 else rows[:args.limit]
        # 「归档分类 / 规则置信度」只给排查用：页面的「问题分类」列读 AI 写的 issueType，
        # 「定性」列从 AI 根因正文抽句，都不再展示这两个值
        print("%-4s %-18s %-26s %-7s %-19s %-17s %-6s %s"
              % ("#", "组件", "流水线", "构建号", "结束时间", "归档分类", "规则置信度", "记录位置"))
        for i, x in enumerate(shown, 1):
            rec = x["record"]
            v = rec.get("verdict") or {}
            print("%-4d %s %s %-7s %-19s %s %-6s %s"
                  % (i, pad(x["component"], 18), pad(x["pipeline"], 26),
                     str(rec.get("buildNumber")), pad(rec.get("endedAt") or "--", 19),
                     pad(v.get("category") or "--", 17),
                     str(v.get("confidence") if v.get("confidence") is not None else "--"),
                     where(x)))
        if len(shown) < len(rows):
            print("… 共 %d 条，已显示前 %d 条（--limit 0 显示全部 / --date 收窄日期）"
                  % (len(rows), len(shown)))

    rc = 0
    if args.strict:
        # 严格模式：供「完成判据」做机器校验。不只拦 pending —— 还要独立重算「应分析集合」，
        # 把「影响当日指标却标成 na / 根因为空」的静默漏分析一并拦下（这类原来能悄悄通过）。
        all_rows = collect(days, "")
        leak, pending, extra = audit(all_rows)
        if pending:
            print("!! 流程未完成：%d 条影响当日指标却仍是待分析（pending），"
                  "做完并 --only step9 收尾后才算跑完" % len(pending))
            for x in pending[:20]:
                print("   %s %s/%s #%s 影响=%s"
                      % (x["date"], x["component"], x["pipeline"],
                         x["record"].get("buildNumber"), "/".join(x["affects"])))
        if leak:
            print("!! 漏分析 %d 条（影响当日指标，却标为 na 或 done 但根因为空）：" % len(leak))
            for x in leak[:20]:
                print("   %s %s/%s #%s 影响=%s status=%s"
                      % (x["date"], x["component"], x["pipeline"],
                         x["record"].get("buildNumber"), "/".join(x["affects"]),
                         (x["record"].get("analysis") or {}).get("status")))
        if extra:
            print("!! 多分析 %d 条（不影响当日任何维度指标，却已分析）：" % len(extra))
            for x in extra[:20]:
                print("   %s %s/%s #%s status=%s"
                      % (x["date"], x["component"], x["pipeline"],
                         x["record"].get("buildNumber"),
                         (x["record"].get("analysis") or {}).get("status")))
        if leak or pending or extra:
            rc = 2
        else:
            print("== 分析完整性校验通过：无待分析 / 无漏分析 / 无多分析（%d 条记录）"
                  % len(all_rows))

    if args.json:
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = [{"date": x["date"], "component": x["component"],
                    "pipeline": x["pipeline"], "recordId": x["record"].get("recordId"),
                    "buildNumber": x["record"].get("buildNumber"),
                    "file": where(x)} for x in rows]
        out.write_text(json.dumps({"_doc": "待 AI 分析清单（tools/list_pending.py 产出）",
                                   "status": args.status, "count": len(payload),
                                   "records": payload}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        print("== 清单已另存: %s" % rel(out))
    return rc


def norm_id(s):
    """recordId 归一化：真身是「组件|流水线#构建号」，同时容忍 / 与空白写法。"""
    return str(s or "").replace("/", "|").replace(" ", "")


def show_one(args):
    days = [args.date] if args.date else [d for d, _ in iter_archive_days()]
    rows = collect(days, "")  # 空状态 = 不过滤
    want = norm_id(args.show)
    hit = [x for x in rows if norm_id(x["record"].get("recordId")) == want]
    if not hit:
        # 退化为按构建号匹配（唯一时直接命中）
        hit = [x for x in rows if str(x["record"].get("buildNumber")) == str(args.show).lstrip("#")]
    if not hit:
        print("!! 未找到记录 %s（用 python tools/list_pending.py 查看可用 recordId）" % args.show)
        return 1
    if len(hit) > 1:
        print("!! 构建号 %s 命中 %d 条，请改用完整 recordId：" % (args.show, len(hit)))
        for x in hit:
            print("   %s  (%s)" % (x["record"].get("recordId"), where(x)))
        return 1

    rec = hit[0]["record"]
    v = rec.get("verdict") or {}
    an = rec.get("analysis") or {}
    ev = rec.get("evidence") or {}
    print("== 记录分析输入: %s" % rec.get("recordId"))
    print("  组件/流水线 : %s / %s（%s）" % (hit[0]["component"], hit[0]["pipeline"],
                                            rec.get("pipelineName")))
    print("  构建号/状态 : #%s %s（失败任务类型 %s）"
          % (rec.get("buildNumber"), rec.get("status"), rec.get("failedTaskType") or "--"))
    print("  起止时间    : %s → %s（归属日期 %s，按执行结束时间）"
          % (rec.get("startedAt") or "--", rec.get("endedAt") or "--", rec.get("date")))
    print("  指标        : %s（track=%s）" % (lights_text(rec), (rec.get("light") or {}).get("track")))
    print("  归档分类    : %s（规则置信度 %s，页面不展示；分类列读 AI 的 issueType，定性列从根因正文抽句）"
          % (v.get("category"), v.get("confidence")))
    for b in (v.get("basis") or [])[:SHOW_LIST_MAX]:
        print("    · %s" % cut(b, SHOW_TEXT_MAX))
    print("  AI 状态     : %s（pending=待分析 / na=不做分析）" % an.get("status"))
    print("  计数        : %s" % json.dumps(rec.get("counts") or {}, ensure_ascii=False))
    missing = ev.get("missing") or []
    if missing:
        print("  证据缺口    : %s" % ", ".join(missing))
    tasks = rec.get("tasks") or []
    print("  任务/证据   : %d 个" % len(tasks))
    for t in tasks[:SHOW_LIST_MAX]:
        print("    · [%s] %s | 日志 %s | 错误行 %d"
              % (t.get("type"), t.get("jobName"), t.get("logFile") or "--",
                 len(t.get("errorLines") or [])))
    errs = rec.get("errorMessages") or []
    print("  错误信息    : %d 条（行号可直接回日志原文核对）" % len(errs))
    for e in errs[:SHOW_LIST_MAX]:
        print("    · %s%s | %s" % (e.get("source") or "", ":" + str(e.get("line") or ""),
                                   cut(e.get("text") or e.get("message") or "", SHOW_TEXT_MAX)))
    cases = rec.get("cases") or []
    if cases:
        print("  失败用例    : %d 条" % len(cases))
        for c in cases[:SHOW_LIST_MAX]:
            first = ((c.get("errorMessages") or [{}])[0] or {})
            print("    · %s [%s] %s" % (c.get("name"), c.get("state"),
                                        cut(first.get("text") or first.get("message") or "",
                                            SHOW_TEXT_MAX)))
    print("  记录位置    : %s（全文，含完整证据清单）" % where(hit[0]))
    return 0


def main():
    ap = argparse.ArgumentParser(description="列出待 AI 分析的记录 / 单条记录的分析输入")
    ap.add_argument("--date", help="归档日 yyyy-mm-dd（默认最近一个归档日）")
    ap.add_argument("--all", action="store_true", help="全部归档日")
    ap.add_argument("--status", default="pending",
                    help="analysis.status 过滤：pending(默认) / na / all")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="最多显示条数（0=全部，默认 %d）" % DEFAULT_LIMIT)
    ap.add_argument("--show", help="打印单条记录的分析输入（recordId 或构建号）")
    ap.add_argument("--json", help="把清单另存为 JSON（相对技能根目录或绝对路径）")
    ap.add_argument("--strict", action="store_true",
                    help="严格模式：独立重算应分析集合，存在待分析 / 漏分析 / 多分析时以退出码 2 结束")
    args = ap.parse_args()
    if args.status in ("all", "*"):
        args.status = ""
    return show_one(args) if args.show else cmd_list(args)


if __name__ == "__main__":
    sys.exit(main())
