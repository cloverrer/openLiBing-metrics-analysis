# -*- coding: utf-8 -*-
"""第 7 步 逐层归档 —— 把 out/work/ 的采集结果按「日期 / 开源组件 / 流水线」落到 out/archive/。

归档布局（数据与 HTML 完全隔离；日期一律按【执行结束时间】归属）::

  out/archive/<yyyy>/<yyyy-mm>/<yyyy-mm-dd>/
    _day.json                      当日汇总：产品点灯 + 每个（组件/流水线）的记录数
    <开源组件名>/<流水线名>/
      pipeline.json                一条流水线一天的全部内容（见下）
      pipeline.evidence.json       证据原文（job_logs/ case_logs/ github_logs/ 全文，见下）

`pipeline.json`（schema=pipeline/1，读写见 lib/pipeline_doc.py）一份顶原来的 9 份::

  _doc / schema                    本文件是什么、按什么口径合并
  steps{step_1_lights …}           每步正文 = 原 step_1_lights.json … step_6_records.json
                                   （点灯依据 / 执行圈定 / 失败任务分流 / 失败用例 /
                                    整 job 日志取证 / 子任务下钻 / github 证据 / 记录计数）
  stepIndex[]                      每步标题/来源/口径/日期字段/字节数 = 原 _manifest.json 的 steps[]
  records[]                        逐条执行记录全文 = 原 records/run_<构建号>.json（最小分析单位）
  counts / evidence / source       原 _manifest.json 的对应字段

`pipeline.evidence.json`（schema=pipeline-evidence/1）一份顶原来的几十份散文件::

  files{相对路径: {bytes, lineCount, sha1, eol, lines[]}}
     键 = 相对本目录的证据路径（job_logs/… 、case_logs/…、github_logs/gh_<rid>/…），
     lines[] 就是原文逐行内容（1 起，与原文件同一行号），可无损还原并校验 sha1
  counts{files, bytes, lines}       本目录内嵌证据的份数/字节数/总行数
  pathBase / lineBase               键的相对基准、行号起点
  为什么单独一份：一个流水线目录的证据正文可能几十 MB，塞进 pipeline.json 会拖慢页面首屏
  （页面只 fetch pipeline.json）；原文只在按行号取证据时才读（统一走 evidence_window()）。

口径说明:
  1) 归档日 = 该执行的结束时间（pipelineRunEndtime / github run.updated_at）所在日期；
     同一条流水线在不同日期分别建目录，互不覆盖；同一日期重跑会重建 pipeline.json
     （不残留旧记录），但**证据正文保留**（out/work 只是本次执行的工作区，归档副本才是
     长期可核对的原文；只增不删，累积在 pipeline.evidence.json 里）。
  2) 所有 JSON 内的 logFile / localLog 都是**相对本流水线目录**的证据路径，也就是
     pipeline.evidence.json 的 files 键；按「路径:行号」取原文即可核对（行号与原文件一致）。
  3) 日目录来源 = 第 2 步 runHistory（区间内**全部运行**，成功 + 失败），
     保证「每天的全部构建记录」都归档；只有失败/取消运行才走第 3~5c 步取证。
  4) 版本可用度 / 编译成功率一律按 runHistory 重算
     （版本可用度 = 可用日 ÷ 该流水线有执行记录的天数，当天有运行**开始或结束**才算有执行记录，
      跨午夜运行的开始日也进分母；组件级 = 各流水线可用度之和 ÷ 条数；
      编译成功率 = Σbpc/Σbc），覆盖看板返回值；区间内一次运行都没有的流水线退回看板值
     （rateRule=dashboard），也不进组件级均值。
  5) 区间内被采集但一次运行都没有的流水线，也会在区间结束日留一份「无运行」说明，避免被质疑漏查。
"""
import datetime
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc, va_caliber  # noqa: E402
from lib.cache import load_cache, save_cache  # noqa: E402
from lib.cdp_exec import OUT_DIR, load_config, load_json, save_json  # noqa: E402
from lib.paths import (ARCHIVE_ROOT, DATE_FIELD, DATE_RULE, archive_day_dir,  # noqa: E402
                       archive_dir, date_of, doc, iter_archive_days,
                       rel, safe_name)

STEP_FILES = [
    # 每步在 STEP_DOCS 中的键（顺序即 stepIndex 顺序；正文统一进 pipeline.json 的 steps）
    "step_1_lights",
    "step_2_runs",
    "step_3_tasks",
    "step_4_cases",
    "step_5_logs",
    "step_5b_subtasks",
    "step_5c_github",
    "step_6_records",
]
INDEX_NAME = "_index.json"
PRODUCTS_NAME = "_products.json"
# 证据文件在 out/ 下的顶层目录（归档时按原相对路径内嵌进 pipeline.evidence.json）
EVIDENCE_PREFIX = pipeline_doc.EVIDENCE_PREFIX


def load_opt(name):
    p = OUT_DIR / name
    return load_json(p) if p.exists() else None


def va_map_of(info, scope):
    """把某流水线的 runHistory 折算成逐日 vaDetail（统一口径，见 lib/va_caliber）。

    口径：当天有运行**开始或结束** → daysInPeriod=1（去重）；当天有 iva=true 的运行**结束**
    → availDays=1。跨午夜运行时开始日 +1 天分母、结束日 +1 天分子，保证「当天启动了」的日子
    不会被漏掉（只有当天完全没启动 / 没跑过的日子才不进分母）。取消运行不计入任何统计。
    scope 限定可计入的日子（= 区间内的工作日），窗口外的开始日不进分母。
    """
    runs = [{"status": h.get("status"), "start": h.get("start"), "end": h.get("end"),
             "iva": h.get("iva") is True} for h in (info.get("runHistory") or [])]
    return va_caliber.day_va(runs, skip_statuses=("CANCELED", "CANCELLED"),
                             days_in_scope=scope)


def recompute_rates(s2, meta_idx, va_maps):
    """版本可用度一律按采集到的执行记录重算（不看板值）。

    口径（与用户确认一致）：
      流水线级 分子 = 可用日：当日有 iva=true 的运行**结束**即算「当天有可用版本」；
              分母 = **该流水线在区间内有执行记录的天数**：当天有运行**开始或结束**就 +1
                     （去重；只有当天完全没启动 / 没跑过的日子才不进分母）。例：一条流水线
                     只在 2 个工作日跑过、其中 1 天可用 → 1/2 = 50%，而不是 1/5。
      组件级   = 该组件各流水线版本可用度的**算术平均**（Σ流水线可用度 ÷ 流水线条数）。
    区间内一次运行都没有的流水线不参与重算，也不进组件级均值（否则等于把「没跑」当成
    「不可用」，会把组件分拉低）；写归档时这类流水线的比率给 null（rateRule=none），
    页面显示 --，而不是拿看板上的 0.0 顶替（那个 0 会被页面对照成「无执行记录 0%」）。
    返回 (pip_rate, prod_rate, prod_detail, wd_count)。
    """
    meta = s2.get("_meta") or {}
    wds = [str(x) for x in (meta.get("workdays") or [])]
    wd_n = len(wds)
    if not wd_n:
        try:
            wd_n = int(meta.get("workdayCount") or 0)
        except (TypeError, ValueError):
            wd_n = 0

    pip_rate, prod_pipes = {}, {}
    for key, b in meta_idx.items():
        vm = va_maps.get(key) or {}
        a = sum(1 for v in vm.values() if v.get("availDays"))
        n = sum(1 for v in vm.values() if v.get("daysInPeriod"))
        if n <= 0:
            continue                      # 区间内无任何运行记录：不重算，退回看板值
        rate = min(1.0, a / float(n))     # 可用日 / 有执行记录的天数（开始日或结束日）
        pip_rate[key] = rate
        prod_pipes.setdefault(b.get("product"), []).append(rate)
    prod_rate, prod_detail = {}, {}
    for prod, rates in prod_pipes.items():
        ssum = sum(rates)
        avg = ssum / len(rates)
        prod_rate[prod] = avg
        prod_detail[prod] = {
            "pipelineCount": len(rates), "sumRate": ssum, "avgRate": avg,
            "workdayCount": wd_n,
            "rule": "组件级 = 各流水线版本可用度之和 / 流水线条数"
                    "（流水线级 = 可用日 / 该流水线有执行记录的天数；当天有运行开始或结束才算"
                    "「有执行记录」，跨午夜运行的开始日也进分母；当日有 iva=true 的运行结束才算"
                    "可用日；当天完全没启动、没跑过的日子不进分母；区间内无运行记录的流水线"
                    "不参与均值）",
        }
    return pip_rate, prod_rate, prod_detail, wd_n


def recompute_bs(s2, meta_idx):
    """编译成功率同样按采集到的全部运行重算（不看板值）：ΣbuildPassCount / ΣbuildCount。

    github 平台流水线服务端不返回 Build* 口径（bc/bpc 为 null），不参与重算，
    退回看板值（rateRule=dashboard）。区间内没有任何编译次数的流水线同样不重算。
    返回 (pip_bs, prod_bs, prod_detail)：prod_detail 里带分子/分母，
    供页面在统计区间一变时直接用 Σ编译通过/Σ编译次数 重算，而不是拿逐日比率做算术平均。
    """
    pip_bs, prod_acc = {}, {}
    for key, b in meta_idx.items():
        info = s2.get(key) or {}
        bc = bpc = 0
        for h in info.get("runHistory") or []:
            if h.get("bc") is None or h.get("bpc") is None:
                continue
            bc += h.get("bc") or 0
            bpc += h.get("bpc") or 0
        if bc <= 0:
            continue
        pip_bs[key] = min(1.0, bpc / float(bc))
        acc = prod_acc.setdefault(b.get("product"), [0, 0])
        acc[0] += bpc
        acc[1] += bc
    prod_bs, prod_detail = {}, {}
    for prod, (p, c) in prod_acc.items():
        prod_bs[prod] = (p / float(c)) if c else None
        prod_detail[prod] = {"buildPassCount": p, "buildCount": c,
                             "rule": "按采集到的全部运行重算：Σ编译通过 / Σ编译次数"
                                     "（不看板 buildSuccess；github 平台无该口径不参与）"}
    return pip_bs, prod_bs, prod_detail


def group_rows(rows, key_field="key", rn_field="rn", fields=("key", "rn", "jobName", "reason")):
    """把证据行按 (流水线 key, 构建号) 建索引。
    step_3 的 skipped 是 (key, rn, jobName, 原因) 元组，这里统一补成字典再建索引，
    保证归档里写出的仍是「哪条流水线/哪个任务/为什么跳过」可读结构。"""
    out = {}
    for r in rows or []:
        if not isinstance(r, dict):
            vals = list(r)
            r = dict(zip(fields, vals + [None] * max(0, len(fields) - len(vals))))
        out.setdefault((r.get(key_field), r.get(rn_field)), []).append(r)
    return out


def pick(idx, key, rns):
    """按构建号集合取某流水线的证据行（保持原顺序）。"""
    out = []
    for rn in rns:
        out.extend(idx.get((key, rn)) or [])
    return out


def norm_paths(row):
    """收集证据行里引用的落盘文件（相对 out/ 的路径）。"""
    files = []
    lf = row.get("logFile")
    if lf:
        files.append(lf)
    ll = row.get("localLog")                                   # 用例日志行 / 用例级错误行
    if ll:
        files.append(ll)
    ex = row.get("excerpt")
    if ex:
        files.append(ex if "/" in ex else "job_logs/" + ex)
    for c in row.get("failedCases") or []:
        if c.get("localLog"):
            files.append(c["localLog"])
    for st in row.get("subTasks") or []:
        if st.get("logFile"):
            files.append(st["logFile"])
    for j in row.get("jobs") or []:
        if j.get("logFile"):
            files.append(j["logFile"])
    for sf in row.get("systemLogs") or []:
        files.append(sf)
    # 分析结论里的引用（analysis.cites[].file）：同样是相对 out/ 的证据路径，
    # 不收集就会漏归档、导致结论无证据可查（结论一律由第 7 步 agent 现场分析，无缓存复用）。
    for holder in (row.get("analysis"),):
        for c in (holder or {}).get("cites") or []:
            if isinstance(c, dict) and c.get("file"):
                files.append(c["file"])
    return files


def collect_refs(obj, acc=None):
    """递归收集对象里**所有**指向证据文件的相对路径（相对 out/）。

    执行记录是嵌套结构（analysis.cites[].file、subTasks[].logFile …），逐字段列举极易漏；
    job_logs/ case_logs/ github_logs/ 下的字符串都算证据引用，一律随记录归档。
    """
    if acc is None:
        acc = []
    if isinstance(obj, str):
        if obj.startswith(EVIDENCE_PREFIX):
            acc.append(obj)
    elif isinstance(obj, list):
        for v in obj:
            collect_refs(v, acc)
    elif isinstance(obj, dict):
        for v in obj.values():
            collect_refs(v, acc)
    return acc


def embed_evidence(arch, rel_paths):
    """把证据原文内嵌进 `<流水线目录>/pipeline.evidence.json`（不再落散文件）。

    正文这时还在采集工作目录 out/ 下，所以 src_root=OUT_DIR；实现与口径统一在
    `pipeline_doc.embed_evidence()`（存量合并 tools/merge_archive.py 走同一份代码，
    区别只是那时证据已经归位到流水线目录里）。

    返回 (份数, 字节数, 行数, 缺失列表)：前三个都是**本目录累积**的全量（含前一次
    重跑已内嵌的），缺失只记本次要不到正文的路径。
    """
    return pipeline_doc.embed_evidence(arch, rel_paths, src_root=OUT_DIR)


def update_cache_archive_dir(cfg, rid_to_dir):
    """把归档目录回写进增量缓存条目（下次复用校验优先在归档区命中）。"""
    try:
        cache = load_cache(cfg)
    except Exception as exc:                                  # noqa: BLE001
        print("!! 缓存读取失败，跳过 archiveDir 回写: %s" % exc)
        return 0
    n = 0
    for entry in (cache.get("runs") or {}).values():
        d = rid_to_dir.get((entry.get("key"), entry.get("rid")))
        if d and entry.get("archiveDir") != d:
            entry["archiveDir"] = d
            n += 1
    if n:
        save_cache(cfg, cache)
    return n


def build_products(products, now):
    """重建 out/archive/_products.json：全部开源组件清单（跨次运行累加，只增不删）。

    products 传第 2 步之后的产品清单（比率已按采集到的运行重算过），
    这样 _products.json 与 _day.json 的口径一致，不会一个看板值一个自算值。
    为什么要单独落一份：
      _day.json.products 只能覆盖「当次运行下钻到的产品」，当天没有待分析流水线的产品
      （第 1 步 analyze=false）根本不会进归档日；而首页要求「列出全部开源组件，没有待
      分析流水线的显示 0」。所以组件全集必须由**产品发现接口**（第 1 步
      step_1_products.json，对每个 target 都记一条）落到归档层，页面再叠加各归档日数据。
      页面不允许自己猜产品名：数据唯一来源就是归档。
    """
    path = ARCHIVE_ROOT / PRODUCTS_NAME
    old = {}
    if path.exists():
        try:
            for p in load_json(path).get("products") or []:
                if p.get("name"):
                    old[p["name"]] = p
        except Exception as exc:                               # noqa: BLE001
            print("!! 旧产品清单读取失败，按本次重建: %s" % exc)
    seen = {}
    for p in products or []:
        name = p.get("product")
        if not name:
            continue
        prev = old.get(name) or {}
        seen[name] = {
            "name": name,
            "projectId": p.get("projectId") or prev.get("projectId"),
            "versionAvailabilityRate": p.get("versionAvailabilityRate"),
            "buildSuccessRate": p.get("buildSuccessRate"),
            "pipelineCount": p.get("pipelineCount"),
            "badPipelineCount": p.get("badPipelineCount"),
            "analyze": bool(p.get("analyze")),
            "rateRule": p.get("rateRule") or "dashboard",
            "recompute": bool(p.get("recompute")),
            "firstSeen": prev.get("firstSeen") or now,
            "lastSeen": now,
        }
    for name, prev in old.items():                             # 本次未发现的老产品保留
        seen.setdefault(name, dict(prev, lastSeen=prev.get("lastSeen") or now))
    prods = sorted(seen.values(), key=lambda x: str(x.get("name")).lower())
    save_json(path, {
        "_doc": doc("step_7_archive", title="开源组件全量清单",
                    criteria="看板产品发现接口返回的全部开源组件（含当日无待分析流水线的产品），"
                             "跨次运行累加、只增不删"),
        "generatedAt": now, "count": len(prods),
        "source": {"step": "step_1_nightly", "file": "step_1_products.json",
                   "note": "第 1 步对每个产品都写一条（analyze=false 也写），不在归档日内过滤"},
        "products": prods,
    })
    return prods


def build_index(now, product_count=0):
    """重建 out/archive/_index.json：已归档日期清单（便于按日期逐层查询）。"""
    days = []
    for date, day_dir in iter_archive_days():
        dj = day_dir / "_day.json"
        counts, pipes = {}, []
        if dj.exists():
            try:
                d = load_json(dj)
                counts = d.get("counts") or {}
                pipes = d.get("pipelines") or []
            except Exception:                                  # noqa: BLE001
                pass
        days.append({
            "date": date, "path": rel(day_dir),
            "components": counts.get("components") or
                          len({p.get("component") for p in pipes}),
            "pipelines": counts.get("pipelines") or len(pipes),
            "records": counts.get("records") or 0,
            "tasks": counts.get("tasks") or 0,
            "cases": counts.get("cases") or 0,
            "errorMessages": counts.get("errorMessages") or 0,
        })
    save_json(ARCHIVE_ROOT / INDEX_NAME, {
        "_doc": doc("step_7_archive", title="归档索引",
                    criteria="按执行结束时间分层归档的日期清单，逐层可查", indexType="day"),
        "generatedAt": now, "dayCount": len(days),
        "productCount": product_count,
        "productsFile": PRODUCTS_NAME,
        "days": days,
    })
    return days


def main():
    cfg = load_config()
    s1p = load_json(OUT_DIR / "step_1_products.json")
    s1b = load_json(OUT_DIR / "step_1_bad_pipelines.json")
    s2 = load_json(OUT_DIR / "step_2_failed_runs.json")
    s3 = load_opt("step_3_params.json") or {}
    s4 = load_opt("step_4_test_evidence.json") or {"results": [], "errors": []}
    case_errors = load_opt("step_4_case_errors.json") or []
    s5 = load_opt("step_5_log_evidence.json") or {"results": [], "errors": []}
    s5c = load_opt("step_5c_github_evidence.json") or {"results": [], "errors": []}
    s6 = load_json(OUT_DIR / "step_6_records.json")

    date_range = s1p.get("dateRange") or {}
    dr_end = date_of(date_range.get("end")) or ""
    prod_idx = {p["product"]: p for p in s1p.get("products") or []}
    all_products = s1p.get("products") or []
    meta_idx = {b["key"]: b for b in s1b.get("pipelines") or []}

    # 比率一律按采集到的全部运行重算（版本可用度 / 编译成功率），覆盖看板返回值
    # 版本可用度分母 = 该流水线在区间内有执行记录的天数（当天有运行开始或结束才算，没启动的日子不进分母）；
    # 编译成功率分母 = Σ编译次数。分子分母一起写进归档：
    # 首页统计区间一变，页面直接按新区间的逐日分子/分母重算，不必回头重新采集
    wd_days = [str(x) for x in ((s2.get("_meta") or {}).get("workdays") or [])]
    va_scope = set(wd_days) or None
    va_maps = {k: va_map_of(s2.get(k) or {}, va_scope) for k in meta_idx}
    pip_rate, prod_rate, prod_detail, wd_n = recompute_rates(s2, meta_idx, va_maps)
    pip_bs, prod_bs, prod_detail_bs = recompute_bs(s2, meta_idx)
    if prod_rate or prod_bs:
        prod_idx = dict(prod_idx)
        for prod in set(prod_rate) | set(prod_bs):
            base = dict(prod_idx.get(prod) or {"product": prod})
            if (prod_rate.get(prod) is not None):
                base["versionAvailabilityRate"] = prod_rate[prod]
                base["versionAvailabilityDetail"] = prod_detail.get(prod)
            if (prod_bs.get(prod) is not None):
                base["buildSuccessRate"] = prod_bs[prod]
                base["buildSuccessDetail"] = prod_detail_bs.get(prod)
            base["rateRule"] = "runs"
            base["recompute"] = True
            prod_idx[prod] = base
        all_products = [prod_idx.get(p.get("product"), p) for p in s1p.get("products") or []]

    idx3_test = group_rows(s3.get("test"))
    idx3_log = group_rows(s3.get("log"))
    idx3_skip = group_rows(s3.get("skipped"))
    idx4 = group_rows(s4.get("results"))
    idx5 = group_rows(s5.get("results"))
    idx5c = group_rows(s5c.get("results"))
    err3 = group_rows(s3.get("errors"))
    err4 = group_rows(s4.get("errors"))
    err5 = group_rows(s5.get("errors"))
    err5c = group_rows(s5c.get("errors"))

    # 用例日志 -> (key, rn)：让 case_errors 能挂到对应执行上
    url_run = {}
    for r in s4.get("results") or []:
        for c in r.get("failedCases") or []:
            u = c.get("resultDownloadUrl")
            if u:
                url_run[u] = (r.get("key"), r.get("rn"))
    ce_by_run = {}
    for e in case_errors or []:
        k = url_run.get(e.get("url"))
        if k:
            ce_by_run.setdefault(k, []).append(e)

    rec_by_key, rec_by_key_date = {}, {}
    for r in s6.get("records") or []:
        key = r["recordId"].rsplit("#", 1)[0]
        rec_by_key.setdefault(key, []).append(r)
        rec_by_key_date.setdefault((key, r["date"]), []).append(r)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    day_buckets = {}
    rid_to_dir = {}
    n_dirs = 0
    n_rebuilt = 0
    n_log_files = 0
    n_log_bytes = 0
    n_log_lines = 0
    missing_logs = []
    no_run_pipelines = []

    for key, b in meta_idx.items():
        info = s2.get(key) or {"failedRuns": [], "days": {}, "runHistory": []}
        # 逐日版本可用度口径（lib/va_caliber）：当天有运行开始或结束就进分母，
        # 跨午夜运行的开始日也会有一条逐日记录（见下方 synth 条目）
        va_map = va_maps.get(key) or {}
        # 日目录来源 = 区间内**全部运行**（成功 + 失败）：每天的所有构建记录都要归档，
        # 不能只落失败的，否则「每天记录完整」和按运行重算比率都无从谈起
        runs_by_date = {}
        for h in info.get("runHistory") or []:
            d = date_of(h.get("end"))
            if not d:
                print("!! %s#%s 无结束时间，无法按结束时间归档，已跳过" % (key, h.get("rn")))
                continue
            runs_by_date.setdefault(d, []).append(h)
        # 取证范围（失败/取消）单独建索引：只有它们有第 3~5c 步证据
        failed_by_date = {}
        for fr in info.get("failedRuns") or []:
            fd = date_of(fr.get("endISO"))
            if fd:
                failed_by_date.setdefault(fd, []).append(fr)
        if not runs_by_date:
            # 区间内该流水线一次运行都没有：留一份说明，避免被质疑漏查
            if not dr_end:
                continue
            runs_by_date[dr_end] = []
            no_run_pipelines.append("%s/%s" % (b["product"], b["pipelineShortName"]))

        product = b["product"]
        pipeline = b["pipelineShortName"]
        last_entry = None
        for d in sorted(runs_by_date):
            runs_today = runs_by_date[d]
            failed_today = failed_by_date.get(d) or []
            all_rns = [h["rn"] for h in runs_today]            # 当日全部运行（归档+重算口径）
            rns = [fr["rn"] for fr in failed_today]            # 当日待取证运行（失败/取消）
            arch = archive_dir(d, product, pipeline)
            if arch.exists():
                # 同日重跑只重建 pipeline.json 与清理 records/：证据原文目录（job_logs/
                # case_logs/ github_logs/）**保留**。归档区只增不删：历史证据一旦删掉就再也补不回来
                # （结论会失去可核对性），所以这里不设任何滚动清理。
                for f in arch.glob("*.json"):
                    f.unlink()
                rec_dir = arch / "records"
                if rec_dir.exists():
                    shutil.rmtree(rec_dir)
                n_rebuilt += 1
            arch.mkdir(parents=True, exist_ok=True)
            n_dirs += 1
            steps = {}                  # 每一步正文先进内存，最后一次性落成 pipeline.json

            # ---- 证据正文先进归档：确定性内容先落定，后面每一步写出的 JSON
            #      只引用「证据文档里确有的路径」，行号即原文行号
            res4 = pick(idx4, key, rns)
            res5 = pick(idx5, key, rns)
            res5c = pick(idx5c, key, rns)
            ce_rows = [e for rn in rns for e in (ce_by_run.get((key, rn)) or [])]
            recs = rec_by_key_date.get((key, d)) or []
            paths = []
            for r in res4 + res5 + res5c:
                paths += norm_paths(r)
            for e in ce_rows:
                paths += norm_paths(e)
            for obj in (res4, res5, res5c, ce_rows, recs):      # 整棵扫描，兜住嵌套引用
                paths += collect_refs(obj)
            nf, nb, nl, miss = embed_evidence(arch, paths)
            n_log_files += nf
            n_log_bytes += nb
            n_log_lines += nl
            missing_logs += ["%s/%s/%s: %s" % (product, pipeline, d, m) for m in miss]

            # ---- 第 1 步：点灯依据
            step1 = {
                "_doc": doc("step_1_lights", component=product,
                            pipeline=pipeline, date=d),
                "dateRange": date_range,
                "product": prod_idx.get(product),
                "pipeline": b,
                "selection": {
                    "inBadPipelines": True,
                    "dims": b.get("dims") or [],
                    "rateRule": "runs",
                    "reason": ("全量采集：该流水线区间内共 %d 次运行（当日 %d 次），"
                               "其中 %d 次失败/取消进入根因取证；版本可用度与编译成功率"
                               "一律按全部运行逐日重算（不看板返回值）%s"
                               % (len(info.get("runHistory") or []), len(all_rns), len(rns),
                                  "；仅采集定时任务运行（含 PR 的运行不计、不分析）"
                                  if b.get("scheduledOnly") else "")),
                },
            }
            steps["step_1_lights"] = step1

            # ---- 第 2 步：执行圈定（含同日之外执行的排除原因）
            included = set(all_rns)
            failed_set = set(rns)
            runs_view = []
            for h in info.get("runHistory") or []:
                hd = date_of(str(h.get("end") or "").replace(" ", "T"))
                rn = h.get("rn")
                if rn in included:
                    reason = ("结束时间在归档日内，纳入当日待分析（失败/取消，取证）"
                              if rn in failed_set else
                              "结束时间在归档日内，纳入当日归档记录（成功运行，只记录不取证）")
                elif hd:
                    reason = "结束时间属 %s，已归档到该日期目录" % hd
                else:
                    reason = "无结束时间，按口径不纳入任何日期"
                runs_view.append({
                    "rn": rn, "pipelineRunId": h.get("rid"),
                    "start": h.get("start"), "end": h.get("end"),
                    "status": h.get("status"), "endedDate": hd,
                    "included": rn in included, "reason": reason,
                })
            step2 = {
                "_doc": doc("step_2_runs", component=product, pipeline=pipeline, date=d),
                "dateRange": date_range, "date": d,
                "dateBasis": {"field": DATE_FIELD, "rule": DATE_RULE},
                # failedRuns = 当日进入取证的运行（失败/取消）；runs = 当日全部运行（含成功）
                "failedRuns": failed_today,
                # days 的键是"月-日"（MM-DD），归档日期是 YYYY-MM-DD，两种写法都兼容
                "days": {k: v for k, v in (info.get("days") or {}).items()
                         if str(k) in (d, d[5:])},
                "runs": runs_view,
                "runHistory": info.get("runHistory") or [],
                "meta": s2.get("_meta") or {},
                "keptRuns": len(all_rns),
                "keptFailedRuns": len(rns),
                "excludedRuns": len([x for x in runs_view if not x["included"]]),
                "note": ("当日全部 %d 次运行均为成功，只归档记录、无需根因分析" % len(all_rns)
                         if all_rns and not rns else
                         ("当日无任何运行记录（流水线被采集，但区间内没有执行）"
                          if not all_rns else None)),
            }
            steps["step_2_runs"] = step2

            # ---- 第 3 步：失败任务分流
            tasks_test = pick(idx3_test, key, rns)
            tasks_log = pick(idx3_log, key, rns)
            step3 = {
                "_doc": doc("step_3_tasks", component=product, pipeline=pipeline, date=d),
                "test": tasks_test, "log": tasks_log,
                "skipped": pick(idx3_skip, key, rns),
                "errors": pick(err3, key, rns),
                "counts": {"test": len(tasks_test), "log": len(tasks_log),
                           "skipped": len(pick(idx3_skip, key, rns))},
            }
            steps["step_3_tasks"] = step3

            # ---- 第 4 步：失败用例与用例级错误
            step4 = {
                "_doc": doc("step_4_cases", component=product, pipeline=pipeline, date=d),
                "results": res4,
                "caseErrors": ce_rows,
                "errors": pick(err4, key, rns),
                "counts": {
                    "tasks": len(res4),
                    "failedCases": sum(len(r.get("failedCases") or []) for r in res4),
                    "caseLogs": sum(1 for e in ce_rows if e.get("downloadStatus") == "ok"),
                    "caseErrors": sum(len(e.get("errors") or []) for e in ce_rows),
                },
            }
            steps["step_4_cases"] = step4

            # ---- 第 5 步 / 5b / 5c
            step5 = {
                "_doc": doc("step_5_logs", component=product, pipeline=pipeline, date=d),
                "results": res5,
                "errors": pick(err5, key, rns),
                "counts": {"tasks": len(res5),
                           "logFiles": sum(1 for r in res5 if r.get("logFile")),
                           "errorLines": sum(len(r.get("errorLines") or []) for r in res5)},
            }
            steps["step_5_logs"] = step5

            subs = [{"rn": r.get("rn"), "jobName": r.get("jobName"),
                     "subTasks": r.get("subTasks") or []}
                    for r in res5 if r.get("subTasks")]
            step5b = {
                "_doc": doc("step_5b_subtasks", component=product,
                            pipeline=pipeline, date=d),
                "items": subs,
                "counts": {"tasks": len(subs),
                           "subTasks": sum(len(x["subTasks"]) for x in subs),
                           "failed": sum(1 for x in subs for st in x["subTasks"]
                                         if st.get("status") == "FAILURE"),
                           "logs": sum(1 for x in subs for st in x["subTasks"]
                                       if st.get("logFile"))},
            }
            steps["step_5b_subtasks"] = step5b

            step5c = {
                "_doc": doc("step_5c_github", component=product,
                            pipeline=pipeline, date=d),
                "results": res5c,
                "errors": pick(err5c, key, rns),
                "counts": {"runs": len(res5c),
                           "jobs": sum(len(r.get("jobs") or []) for r in res5c),
                           "missing": sum(len(r.get("missing") or []) for r in res5c)},
            }
            steps["step_5c_github"] = step5c

            # ---- 第 6 步：逐条执行记录（正文统一放 pipeline.json 的顶层 records[]）
            #      归档不再拆 records/run_<rn>.json：一条流水线一天就是一份文件，
            #      逐条记录仍是完整全文（只少一层重复的 _doc 题头）
            for rec in recs:
                rid_to_dir[(key, rec.get("pipelineRunId"))] = rel(arch)
            step6 = {
                "_doc": doc("step_6_records", component=product, pipeline=pipeline,
                            date=d, recordCount=len(recs)),
                "date": d, "component": safe_name(product), "pipeline": safe_name(pipeline),
                "counts": {"records": len(recs),
                           "tasks": sum((r.get("counts") or {}).get("tasks") or 0 for r in recs),
                           "cases": sum((r.get("counts") or {}).get("cases") or 0 for r in recs),
                           "errorMessages": sum((r.get("counts") or {}).get("errorMessages") or 0
                                                for r in recs)},
            }
            steps["step_6_records"] = step6

            # ---- 清单（stepIndex）：每一步的标题/来源/口径/日期字段，正文在 steps 里
            steps_meta = []
            for step in STEP_FILES:
                dcm = doc(step)
                steps_meta.append({
                    "step": step, "title": dcm["title"],
                    "source": dcm["source"], "criteria": dcm["criteria"],
                    "dateField": dcm["dateField"],
                })
            manifest = {
                "_doc": doc("step_7_archive", title="流水线归档（单文件）",
                            component=product, pipeline=pipeline, date=d,
                            criteria="本目录一份 pipeline.json：每步正文（steps）、逐条执行记录（records）、"
                                     "证据文件与计数，逐条可核对"),
                "date": d, "component": safe_name(product),
                "pipeline": safe_name(pipeline),
                "pipelineName": b.get("pipelineName"), "platform": b.get("platform"),
                "key": key,
                "dateBasis": {"field": DATE_FIELD, "rule": DATE_RULE, "value": d,
                              "runs": [{"rn": h.get("rn"), "status": h.get("status"),
                                        "endedAt": h.get("end")}
                                       for h in runs_by_date[d]]},
                "steps": steps_meta,
                "pathBase": "steps[].正文 / records[] 均在本文件；证据正文见同目录 "
                            "pipeline.evidence.json 的 files；本目录路径见 _day.json 与 _index.json",
                "counts": {
                    "records": len(recs),
                    "tasks": sum((r.get("counts") or {}).get("tasks") or 0 for r in recs),
                    "cases": sum((r.get("counts") or {}).get("cases") or 0 for r in recs),
                    "errorMessages": sum((r.get("counts") or {}).get("errorMessages") or 0
                                         for r in recs),
                },
                "evidence": {"files": nf, "bytes": nb, "lines": nl,
                             "missing": miss,
                             "pathBase": "证据正文在 pipeline.evidence.json 的 files，"
                                         "键 = 相对本目录的证据路径（与 steps/records 里 "
                                         "logFile / cites 的写法完全一致），行号 1 起与原文件相同",
                             "rule": "证据原文逐行内嵌（lines[] + eol + sha1 可无损还原）；"
                                     "只增不删：重跑不会删掉已归档的历史证据；"
                                     "files/bytes/lines 是本目录累积全量，不是本次新增"},
                "source": {"workDir": rel(OUT_DIR), "generatedAt": now,
                           "note": "由 steps/step_7_archive.py 从第 1~6 步产物逐层归档"},
            }
            # ---- 落盘：清单 + 各步正文 + 逐条记录 → 一份 pipeline.json（原子写）
            payload = pipeline_doc.assemble(manifest, steps, recs)
            pipeline_doc.save(arch, payload)

            bucket = day_buckets.setdefault(d, {"pipelines": []})
            # 当日分子/分母：统计区间一变，页面按「Σ分子/Σ分母」就地重算，
            # 不需要重新采集，也不是拿逐日比率做算术平均
            n_runs_period = len(info.get("runHistory") or [])
            day_vd = va_map.get(d) or {"availDays": 0, "daysInPeriod": 0}
            day_bc = sum((h.get("bc") or 0) for h in runs_today
                         if h.get("bc") is not None)
            day_bpc = sum((h.get("bpc") or 0) for h in runs_today
                          if h.get("bpc") is not None)
            bucket["pipelines"].append({
                "component": safe_name(product), "pipeline": safe_name(pipeline),
                "pipelineName": b.get("pipelineName"), "platform": b.get("platform"),
                # pipelineId 是流水线的真实身份：页面按「组件 + pipelineId」归并同一条流水线，
                # 短名（目录名）只是它在磁盘上的落点，跨版本改过名也不能被当成两条流水线
                "pipelineId": b.get("pipelineId"),
                "key": key,
                "dims": b.get("dims") or [],
                # 流水线级比率（不是产品级）：二级页「组件级流水线清单」按维度只显示一个数字，
                # 必须能就地取到，否则页面只能去猜或退回产品级比率（会误导）。
                # 全量采集后一律按 runHistory 重算（版本可用度 = 可用日 ÷ 该流水线有执行记录的天数，
                # 组件级 = 各流水线可用度之和 ÷ 条数；编译成功率 = Σbpc/Σbc）；
                # 区间内无运行时才退回看板值（rateRule=dashboard）；
                # **区间内一次运行都没有**（runsInPeriod=0，如 RAGSDK / VisionSDK 只有看板配置）
                # 时连看板值也不写：那种 0.0 表示「压根没跑」而不是「跑了但全不可用」，
                # 页面收进平均会把「无执行记录」显示成 0.00%（用户反馈的问题），
                # 所以这里写 null → 页面显示 --，且不参与组件级平均
                "vaRate": (pip_rate[key] if key in pip_rate
                           else (b.get("versionAvailabilityRate") if n_runs_period else None)),
                "bsRate": (pip_bs[key] if key in pip_bs
                           else (b.get("buildSuccessRate") if n_runs_period else None)),
                "rateRule": ("runs" if (key in pip_rate or key in pip_bs)
                             else ("dashboard" if n_runs_period else "none")),
                # 当日分子/分母（供页面按统计区间重算）：
                # 分子 availDays = 当天有 iva=true 的运行结束；分母 daysInPeriod = 当天有运行
                # **开始或结束**就记 1（去重）。当日完全没启动 / 没跑过 → 不进分母。
                "vaDetail": {"availDays": int(day_vd.get("availDays") or 0),
                             "daysInPeriod": int(day_vd.get("daysInPeriod") or 0)},
                "bsDetail": {"buildPassCount": day_bpc, "buildCount": day_bc},
                "runsInPeriod": n_runs_period,
                "runsToday": len(all_rns),
                "failedRunsToday": len(rns),
                "path": rel(arch),
                # 该目录唯一的数据文件（原来指 _manifest.json）；file/layout 与
                # tools/merge_archive.py 的 sync_day 写出的一致，避免同一份 _day.json
                # 因来源不同（本次采集 / 历史合并）字段对不上
                "manifest": rel(pipeline_doc.path_of(arch)),
                "file": rel(pipeline_doc.path_of(arch)),
                "layout": pipeline_doc.SCHEMA,
                "records": len(recs),
                "runNumbers": [r.get("buildNumber") for r in recs],
                "tasks": sum((r.get("counts") or {}).get("tasks") or 0 for r in recs),
                "cases": sum((r.get("counts") or {}).get("cases") or 0 for r in recs),
                "errorMessages": sum((r.get("counts") or {}).get("errorMessages") or 0
                                     for r in recs),
                "evidenceFiles": nf,
                "byCategory": {},
                "note": (None if recs else
                         ("当日无任何运行记录（该流水线区间内无执行）" if not all_rns
                          else "当日 %d 次运行均无可归档记录" % len(all_rns))),
            })
            cats = bucket["pipelines"][-1]["byCategory"]
            for r in recs:
                c = (r.get("verdict") or {}).get("category") or "unknown"
                cats[c] = cats.get(c, 0) + 1
            last_entry = bucket["pipelines"][-1]

        # 跨午夜运行：当天只「开始」、没「结束」的日子没有归档目录（记录归属结束日），
        # 但按口径当天确实有执行 → 补一条轻量条目进当日 _day.json，让页面按统计区间累加
        # vaDetail 时能把开始日算进版本可用度分母（分子为 0 → 该天不可用）。
        # vaDetail.availDays/daysInPeriod、records、runNumbers 都按「当天没有结束的运行」置零，
        # 弹窗按构建号去重，不会重复展示。path 指向模板条目（该流水线带整区间 runHistory 的归档）
        if last_entry is not None:
            for d in sorted(va_map):
                if d in runs_by_date:
                    continue
                vd = va_map[d] or {}
                if not vd.get("daysInPeriod"):
                    continue
                synth = dict(last_entry)
                synth["vaDetail"] = {"availDays": int(vd.get("availDays") or 0),
                                     "daysInPeriod": int(vd.get("daysInPeriod") or 0)}
                synth["bsDetail"] = {"buildPassCount": 0, "buildCount": 0}
                synth["runsToday"] = synth["failedRunsToday"] = 0
                synth["records"] = 0
                synth["runNumbers"] = []
                synth["tasks"] = synth["cases"] = synth["errorMessages"] = 0
                synth["byCategory"] = {}
                synth["evidenceFiles"] = 0
                synth["note"] = ("当日仅启动、未结束（跨午夜运行）：计入版本可用度分母，"
                                 "当天不计可用")
                day_buckets.setdefault(d, {"pipelines": []})["pipelines"].append(synth)

    # ---- 日级汇总
    for d, bucket in sorted(day_buckets.items()):
        day_dir = archive_day_dir(d)
        pipes = bucket["pipelines"]
        cats = {}
        for p in pipes:
            for k, v in p["byCategory"].items():
                cats[k] = cats.get(k, 0) + v
        payload = {
            "_doc": doc("step_7_archive", title="归档日汇总", date=d, dayType="day",
                        criteria="当日（按执行结束时间）全部被点灯流水线的执行记录索引"),
            "date": d,
            "dateBasis": {"field": DATE_FIELD, "rule": DATE_RULE, "value": d},
            "dateRange": date_range,
            # 全量产品（含当日没有待分析流水线的）：首页要求「列出全部开源组件」，
            # 不能按 analyze 过滤，否则当天无异常的产品会整行消失。analyze 字段保留以便区分。
            "products": all_products,
            "productsAnalyzed": [p.get("product") for p in all_products if p.get("analyze")],
            # 工作日日历：保留下来供工具与展示层参考（顶部「工作日 N 天」、
            # tools/reconcile_superseded.py 的兜底）。版本可用度的分母已改为
            # 「该流水线有执行记录的天数」，这份日历不再参与分母计算。
            "workdays": wd_days,
            "workdayCount": wd_n,
            "pipelines": pipes,
            "counts": {
                "components": len({p["component"] for p in pipes}),
                "pipelines": len(pipes),
                "records": sum(p["records"] for p in pipes),
                "tasks": sum(p["tasks"] for p in pipes),
                "cases": sum(p["cases"] for p in pipes),
                "errorMessages": sum(p["errorMessages"] for p in pipes),
                "evidenceFiles": sum(p["evidenceFiles"] for p in pipes),
                "byCategory": cats,
            },
            "generatedAt": now,
        }
        save_json(day_dir / "_day.json", payload)

    prods = build_products(all_products, now)
    days = build_index(now, len(prods))
    n_cache = update_cache_archive_dir(cfg, rid_to_dir)

    n_records = sum(p["records"] for b in day_buckets.values() for p in b["pipelines"])
    print("== 第 7 步 逐层归档（年/年-月/日/开源组件/流水线）==")
    print("归档 %d 个日目录 / %d 个流水线目录（重建 %d 个）| 执行记录 %d 条"
          % (len(day_buckets), n_dirs, n_rebuilt, n_records))
    print("证据原文内嵌 %d 份（%.1f MB / %d 行）| 缺失 %d 个引用"
          % (n_log_files, n_log_bytes / 1048576.0, n_log_lines, len(missing_logs)))
    if missing_logs:
        for m in missing_logs[:10]:
            print("  !! 证据缺失: %s" % m)
    if no_run_pipelines:
        print("已全量采集但区间内一次运行都没有的流水线 %d 条（已在区间结束日留说明）: %s"
              % (len(no_run_pipelines), "、".join(no_run_pipelines[:5])))
    print("缓存 archiveDir 回写 %d 条 | 归档索引 %d 天" % (n_cache, len(days)))
    print("开源组件全量清单 %d 个（含当日无待分析流水线的）: %s"
          % (len(prods), "、".join(str(p.get("name")) for p in prods)))
    print("-> out/archive/<年>/<年-月>/<日>/<开源组件名>/<流水线名>/")


if __name__ == "__main__":
    main()
