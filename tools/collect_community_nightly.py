# -*- coding: utf-8 -*-
"""Jenkins 社区 Nightly 采集与归档（openGauss / openEuler）—— 版本可用度 + 编译成功率。

口径完全参考 pr-ci-board（社区 Nightly 看护看板）：
  流水线版本可用度 = 窗口内成功天数 ÷ 窗口内有执行记录的天数（未执行的天数不计入分母）
  组件版本可用度   = 各流水线版本可用度之和 ÷ 流水线条数
  流水线编译成功率 = 窗口内成功次数 ÷ 构建次数
  组件编译成功率   = 各流水线编译成功率之和 ÷ 流水线条数
  aborted 与采集时仍在进行中的构建不计入任何统计（次数与天数均排除，纯 aborted 的日子视为未执行）；
  构建按北京时间（UTC+8）自然日归组（按构建结束时间 = 开始时间 + 耗时；耗时缺失时退回开始时间）。
  停用/待启用的流水线由 community_sources.json 的 tasks 清单决定，不在清单内的一律不采集。

产出（与 openLiBing 侧同一套归档 schema，页面与二级页、根因分析链路都无需分支）：
  out/archive/<年>/<年-月>/<日>/<社区名>/<流水线名>/pipeline.json
  out/archive/<年>/<年-月>/<日>/<社区名>/<流水线名>/pipeline.evidence.json  （失败构建控制台日志逐行内嵌）
  并把社区流水线并入当日 _day.json.pipelines[]、把社区并入 out/archive/_products.json。

数据源（两个站点结构不同，取数方式随之不同）：
  openGauss  jenkins.opengauss.org，buildHistory/ajax 页面解析（作业级 api/json 被反爬拦截返回 418），
             匿名仅 403/418，需 Basic 认证（凭据见 config.local.json 的 jenkins.openGauss）。
  openEuler  ci.openeuler.openatom.cn，作业级 api/json（HTML 页面对匿名访问返回 403）。

用法:
  python tools/collect_community_nightly.py                            # 默认取 config.json 的 date_range
  python tools/collect_community_nightly.py --start 2026-11-10 --end 2026-11-13
  python tools/collect_community_nightly.py --community openGauss       # 只采集指定社区
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.dim_affects import affects_of  # noqa: E402
from lib.paths import ARCHIVE_ROOT, archive_dir, doc, rel, safe_name  # noqa: E402
from lib.va_caliber import day_bs_detail, day_va  # noqa: E402

PRODUCTS_NAME = "_products.json"

SOURCES = ROOT / "community_sources.json"
CONFIG = ROOT / "config.json"
CONFIG_LOCAL = ROOT / "config.local.json"

BJ = datetime.timezone(datetime.timedelta(hours=8))
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120"}

# 中断的构建（aborted/canceled）：版本可用度里算「执行过」→ 进分母但永不计可用；
# 编译次数（bs）里不计入（没产出编译结果）。进行中构建不归档、不进任何统计。
OK_RESULTS = {"SUCCESS", "SUCCESS"}
SKIP_RESULTS = {"ABORTED"}
# 控制台日志中判定为「普通报错行」的关键字（大小写不敏感）。
# 注意不要用裸 `error` 当关键字：编译日志里 `.../error.cpp.o`、`elog.cpp: In function` 这类
# 只含 "error" 的源码路径会被大面积误命中，把真正的报错挤出证据列表。
ERR_PAT = re.compile(
    r"(?i)(failed|failure|fatal|exception|traceback|"
    r"no space left|permission denied|cannot |not found|no such file|"
    r"timed out|timeout|connection refused|package .* not found|"
    r"make(\[[0-9]+\])?: \*\*\*|npm ERR|undefined reference|segmentation fault|"
    r"\[error\]|\berror:)")
# 决定性证据：磁盘写满、写盘失败、段错误、流水线失败收尾等 —— 必须优先入选，
# 不能被日志前段的高频噪音挤出 60 行名额。
HARD_PAT = re.compile(
    r"(?i)(no space left on device|wrote only \d+ of|disk quota exceeded|\benospc\b|"
    r"cannot create (regular )?file|cannot create directory|upload package to obs failed|"
    r"segmentation fault|marked build as failure|finished: failure|\[error\]|\berror:)")
# 已知噪音：与失败根因无关的高频行，一律不当作证据（但命中 HARD_PAT 的行永不被丢弃）
NOISE_PAT = re.compile(
    r"(Failed to set locale, defaulting to C\.UTF-8"          # 构建容器的 locale 提示
    r"|\bETA\b"                                               # 下载/解压进度条
    r"|^\s*-- "                                               # CMake 探测/安装信息
    r"|\bwarning:\s"                                          # 编译器/工具警告（不是失败原因）
    r"|fatal error in future CMake"                           # CMake 弃用告警续行
    r"|^\s*/\S*/(?:g\+\+|gcc|cc|clang\+\+)\b"                 # 编译命令行
    r"|\.(?:c|cc|cpp|cxx|h|hpp):\d+(?::\d+)?:"                # 编译器诊断定位
    r"|:\s*In function\b)")                                   # 编译器诊断续行
# 硬性噪音：这些行根本不是日志正文（源码/补丁清单回显、进度条），即使同时命中 HARD_PAT 也不采集
NOT_LOG_PAT = re.compile(r"(^\s*\d+\s*\||^\s*\[\s*\d+%\]|^\s*\(\d+-\d+/\d+\))")
MAX_ERR_LINES = 60


# ------------------------------------------------------------------ 配置与工具
def load_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (ValueError, OSError):
        return default


def window_from_config(args):
    """区间取值：--start/--end > 环境变量 RCA_START/RCA_END（run_pipeline 传入）> config.date_range。"""
    cfg = load_json(CONFIG, {}) or {}
    dr = cfg.get("date_range") or {}
    start = (args.start or os.environ.get("RCA_START")
             or str(dr.get("start") or "").strip())
    end = (args.end or os.environ.get("RCA_END")
           or str(dr.get("end") or "").strip())
    if not start or not end:
        raise SystemExit("!! 未指定区间（--start/--end）且 config.date_range 为空")
    return start, end


def auth_headers(cid, comm):
    """构造 Jenkins 认证头：环境变量 > config.local.json 的 jenkins.<local_key> > 无（匿名）。"""
    a = comm.get("auth") or {}
    if not a:
        return {}, "匿名"
    lk = a.get("local_key") or cid
    user = os.environ.get(a.get("user_env") or "") or ""
    token = os.environ.get(a.get("token_env") or "") or ""
    if not (user and token):
        loc = (load_json(CONFIG_LOCAL, {}) or {}).get("jenkins") or {}
        ent = loc.get(lk) or {}
        user = user or ent.get("user") or ""
        token = token or ent.get("token") or ""
    if not (user and token):
        return {}, "匿名（未配置凭据）"
    raw = ("%s:%s" % (user, token)).encode("utf-8")
    return {"Authorization": "Basic " + base64.b64encode(raw).decode()}, user


def http_get(url, headers=None, timeout=60):
    h = dict(UA)
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    try:
        return urllib.request.urlopen(req, context=ctx, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return "HTTP %s" % e.code
    except Exception as e:                                          # noqa: BLE001
        return "ERR %s %s" % (type(e).__name__, e)


def bj_day(ms):
    return datetime.datetime.fromtimestamp(ms / 1000.0, BJ)


def norm_result(v):
    """把两站点五花八门的结果串归一化为 SUCCESS / FAILED / ABORTED / RUNNING。"""
    s = str(v or "").strip().upper()
    if s in ("SUCCESS", "SUCCESSFUL"):
        return "SUCCESS"
    if s in ("FAILURE", "FAILED", "UNSTABLE"):
        return "FAILED"
    if s in ("ABORTED", "ABORT", "CANCELED", "CANCELLED"):
        return "ABORTED"
    return "RUNNING"


def window_days(start, end):
    """采集窗口内的自然日集合（版本可用度新口径的 scope：窗口外的日子不归档、不计数）。"""
    s = datetime.datetime.fromisoformat(start).date()
    e = datetime.datetime.fromisoformat(end).date()
    out = set()
    cur = s
    while cur <= e:
        out.add(cur.isoformat())
        cur += datetime.timedelta(days=1)
    return out


def jenkins_run(b):
    """Jenkins 构建 → 统一运行字典（跨午夜运行开始日/结束日都会用到，故两个时间都给足）。"""
    ts, dur = b.get("ts"), b.get("dur_ms")
    end_ms = (ts or 0) + (dur or 0) if ts else 0
    return {
        "status": b.get("result"),
        "start": bj_day(ts).strftime("%Y-%m-%dT%H:%M:%S") if ts else "",
        "end": bj_day(end_ms).strftime("%Y-%m-%dT%H:%M:%S") if end_ms else "",
        "iva": b.get("result") == "SUCCESS",
    }


def synth_day_entry(template, day, va, reason):
    """为「当天只开始、没有结束」的日子补一条 _day.json 条目。

    归档目录与 pipeline.json 仍只在**结束日**落（记录归属于结束日），这里只补一条轻量条目，
    让页面按统计区间累加 vaDetail 时能把「当天开始执行、当天没执行完」的那一天算进分母
    （分子为 0 → 该天不可用）。path 指向模板条目（同一条流水线带整区间 runHistory 的那份归档），
    弹窗按构建号去重，不会重复展示。
    """
    e = dict(template)
    e["vaDetail"] = {"availDays": int(va.get("availDays") or 0),
                     "daysInPeriod": int(va.get("daysInPeriod") or 0)}
    e["runsToday"] = 0
    e["failedRunsToday"] = 0
    e["records"] = 0
    e["runNumbers"] = []
    e["tasks"] = e["cases"] = e["errorMessages"] = 0
    e["byCategory"] = {}
    e["note"] = reason
    return e


# ------------------------------------------------------------------ 取数：两种站点
def fetch_jobs_ajax(base, job, headers, pages=2):
    """openGauss 走 buildHistory/ajax 页面解析：每次 25 条，翻页取更早的构建。"""
    builds, seen = [], set()
    url = "%s/job/%s/buildHistory/ajax" % (base, job)
    for _ in range(pages):
        r = http_get(url, headers)
        if r.startswith(("HTTP", "ERR")):
            print("    !! %s 取数失败: %s" % (job, r[:60]))
            break
        seg = re.split(r'<div page-entry-id="(-?\d+)" class="app-builds-container__item">', r)
        page_nums = []
        for i in range(2, len(seg), 2):
            body = seg[i]
            mnum = re.search(r'href="/job/' + re.escape(job) + r'/(\d+)/console"', body)
            if not mnum:
                continue
            num = int(mnum.group(1))
            if num in seen:
                continue
            mres = re.search(r'tooltip="([^"]+)"\s+href="/job/', body)
            mts = re.search(r'time="(\d+)"', body)
            mdur = re.search(r'tooltip="Took ([^"]+)"', body)
            seen.add(num)
            page_nums.append(num)
            builds.append({"number": num, "result": norm_result(mres.group(1) if mres else "?"),
                           "ts": int(mts.group(1)) if mts else None,
                           "dur_ms": parse_dur(mdur.group(1) if mdur else None)})
        if not page_nums:
            break
        url = "%s/job/%s/buildHistory/ajax?after=%d" % (base, job, min(page_nums))
    return sorted(builds, key=lambda b: b["number"])


def fetch_jobs_api(base, job, headers):
    """openEuler 走作业级 api/json（HTML 页面对匿名 403）。"""
    url = "%s/job/%s/api/json?tree=builds[number,result,timestamp,duration]{0,60}" % (base, job)
    r = http_get(url, headers)
    if r.startswith(("HTTP", "ERR")):
        print("    !! %s 取数失败: %s" % (job, r[:60]))
        return []
    try:
        d = json.loads(r)
    except ValueError:
        print("    !! %s 返回无法解析为 JSON" % job)
        return []
    out = []
    for b in d.get("builds", []):
        if b.get("number") is None or b.get("timestamp") is None:
            continue
        out.append({"number": int(b["number"]), "result": norm_result(b.get("result")),
                    "ts": int(b["timestamp"]), "dur_ms": int(b.get("duration") or 0)})
    return sorted(out, key=lambda b: b["number"])


def parse_dur(s):
    """'46 min' / '1 hr 0 min' / '51 ms' / '2.3 sec' -> 毫秒；解析不了返回 0。"""
    if not s:
        return 0
    total = 0.0
    for val, unit in re.findall(r"([\d.]+)\s*(ms|sec|min|hr|day)", s):
        v = float(val)
        total += v * {"ms": 1, "sec": 1000, "min": 60000, "hr": 3600000, "day": 86400000}[unit]
    return int(total)


def fetch_console(base, job, num, headers):
    return http_get("%s/job/%s/%d/consoleText" % (base, job, num), headers, timeout=120)


def build_url(base, job, num):
    return "%s/job/%s/%d/" % (base, job, num)


# 已选证据的去重键：把「带数字 / 路径 / 后缀」的具体 token 归一化成 #，纯单词主体保留。
# 例：11 条只有包名不同的 `buildopengauss.sh: line 143: <包名>.sha256: No space left on device`
# 归一化成同一条，只留一个代表；而 `gzip:` / `tee:` / `tar:` / `cp:` 这些命令名是纯单词，
# 会保留下来，不同工具写盘失败的证据不会被误并成一条。
_ERR_KEY = re.compile(r"[A-Za-z0-9_\-]*[0-9/.\-][A-Za-z0-9_./\-]*")


def err_key(s):
    return _ERR_KEY.sub("#", s)


# ------------------------------------------------------------------ 证据与错误行
def error_lines(text):
    """挑「证据行」：返回 [(行号, 原文)]（最多 MAX_ERR_LINES 行，按行号升序）。

    取值口径（都是踩过的坑）：
      1) 不能从头取满 MAX_ERR_LINES 就停。openGauss 那份 4 万行日志前段全是
         `Failed to set locale, defaulting to C.UTF-8` 之类噪音，60 个名额在 L3000 前
         就被占满，真正在 L39xxx 的 `No space left on device` 一条都进不来 ——
         页面上就表现为「根因写着磁盘写满，证据弹窗里全是 locale 警告」。
      2) 报错与中止原因都在尾部（Upload failed / marked build as failure /
         Finished: FAILURE），所以**从尾往前取**，先保证把结束原因收进来。
      3) 命中行分两档：HARD_PAT（决定性证据：写盘失败、段错误、流水线失败收尾）优先，
         其它命中行次之；NOISE_PAT 命中的噪音行直接丢弃。
      4) 同一报错会重复几十上百行（`cp: cannot create regular file './..._92_662.sql'`、
         `objcopy ... copying 'xxx.so'`、`buildopengauss.sh: line 143: <包名>.sha256` 都只差
         文件名/数字），按 err_key() 归一化后去重，把 60 个名额留给不同种类的报错。
    """
    hard, soft, seen_h, seen_s = [], [], set(), set()
    for i, line in enumerate((text or "").split("\n"), 1):
        s = line.rstrip("\r")
        if not s.strip() or NOT_LOG_PAT.search(s):
            continue
        is_hard = bool(HARD_PAT.search(s))
        if not is_hard:                      # 硬证据永不被噪音规则丢弃
            if NOISE_PAT.search(s) or not ERR_PAT.search(s):
                continue
        key = err_key(s)
        seen = seen_h if is_hard else seen_s
        if key in seen:
            continue
        seen.add(key)
        (hard if is_hard else soft).append((i, s))
    picked = (hard[::-1] + soft[::-1])[:MAX_ERR_LINES]
    return sorted(picked, key=lambda x: x[0])


def put_evidence(pdir, rel_path, text):
    """把证据原文逐行写进 pipeline.evidence.json（幂等覆盖）；返回 (bytes, lineCount)。"""
    ev = pipeline_doc.load_evidence(pdir)
    files = ev.setdefault("files", {})
    raw = (text or "").encode("utf-8")
    lines = (text or "").split("\n")
    eol = bool(lines) and lines[-1] == ""
    if eol:
        lines = lines[:-1]
    files[rel_path] = {"bytes": len(raw), "lineCount": len(lines), "eol": eol,
                       "sha1": hashlib.sha1(raw).hexdigest(), "lines": lines}
    pipeline_doc.save_evidence(pdir, ev)
    return len(raw), len(lines)


# ------------------------------------------------------------------ 组装一条流水线一天
def build_pipeline_day(comm, task, day, day_builds, all_builds, headers):
    """组装社区某流水线在某一天的归档：pipeline.json + 证据，返回 _day.json 需要的条目。"""
    cid = comm["id"]
    job = task["job"]
    label = task.get("label") or job
    base = comm["jenkins_base"].rstrip("/")
    arch = archive_dir(day, cid, safe_name(job))
    if arch.exists():                       # 同日重跑：整体重建，不残留上次的日志/记录
        for f in arch.glob("*.json"):
            f.unlink()
    arch.mkdir(parents=True, exist_ok=True)

    non_aborted = [b for b in day_builds if b["result"] != "ABORTED"]
    day_ok = any(b["result"] == "SUCCESS" for b in day_builds)
    day_avail = 1 if day_ok else 0
    day_bc = len(non_aborted)
    day_bpc = sum(1 for b in non_aborted if b["result"] == "SUCCESS")

    run_history, records, ev_files, ev_lines = [], [], 0, 0
    for b in day_builds:
        num = b["number"]
        st = b["result"]
        end_ms = (b["ts"] or 0) + (b["dur_ms"] or 0) if b["ts"] else 0
        started = bj_day(b["ts"]).strftime("%Y-%m-%dT%H:%M:%S") if b["ts"] else ""
        ended = bj_day(end_ms).strftime("%Y-%m-%dT%H:%M:%S") if end_ms else started
        run_history.append({
            "rn": num, "rid": "jenkins:%s:%s:%d" % (cid, job, num),
            "status": st, "start": started, "end": ended,
            "iva": st == "SUCCESS",
            "bc": 0 if st == "ABORTED" else 1,
            "bpc": 1 if st == "SUCCESS" else 0,
        })

    for b in day_builds:
        num, st = b["number"], b["result"]
        end_ms = (b["ts"] or 0) + (b["dur_ms"] or 0) if b["ts"] else 0
        started = bj_day(b["ts"]).strftime("%Y-%m-%dT%H:%M:%S") if b["ts"] else ""
        ended = bj_day(end_ms).strftime("%Y-%m-%dT%H:%M:%S") if end_ms else started
        rec = {
            "recordId": "%s|%s#%d" % (cid, safe_name(job), num),
            "date": day, "component": cid, "pipeline": safe_name(job), "pipelineName": label,
            "platform": "jenkins",
            "buildNumber": num,
            "pipelineRunId": "jenkins:%s:%s:%d" % (cid, job, num),
            "status": st,
            "failedTaskType": ("版本构建任务" if st == "FAILED" else None),
            "startedAt": started, "endedAt": ended,
            "dateBasis": {"field": "buildEndtime",
                          "value": ended,
                          "rule": "按构建结束时间（开始时间+耗时）归属北京自然日"},
            "links": {"jenkins": build_url(base, job, num), "detail": None,
                      "openlibing": None, "github": None},
            "tasks": [], "cases": [], "errorMessages": [],
            "verdict": {"category": "na", "text": "", "confidence": None, "basis": []},
            "suggestions": [],
            "analysis": {"status": "na"},
            "counts": {"tasks": 0, "testTasks": 0, "logTasks": 0, "buildTasks": 0,
                       "cases": 0, "errorMessages": 0, "evidenceFiles": 0},
        }
        if st == "FAILED":
            text = fetch_console(base, job, num, headers)
            if text.startswith(("HTTP", "ERR")):
                text = ""
                print("    !! %s#%d 控制台日志取不到: %s" % (job, num, text[:40]))
            rel_path = "job_logs/%s_%s_%d.log" % (cid, safe_name(job), num)
            nbytes, nlines = put_evidence(arch, rel_path, text)
            ev_files += 1
            ev_lines += nlines
            errs = error_lines(text)
            rec["tasks"] = [{
                "jobName": job, "type": "log", "fallback": False,
                "logFile": rel_path, "logBytes": nbytes, "logLines": nlines,
                "download": "consoleText", "truncated": False, "excerpt": None,
                "stepErrMsgs": [], "jobErrMsg": "构建结束状态 FAILURE",
                "errorLines": ["L%d: %s" % (ln, tx) for ln, tx in errs],
                "subTasks": [],
            }]
            rec["errorMessages"] = [{"task": job, "source": rel_path, "line": ln,
                                     "level": "LOG", "text": tx} for ln, tx in errs]
            rec["counts"].update({"tasks": 1, "logTasks": 1, "errorMessages": len(errs),
                                  "evidenceFiles": 1})
            rec["verdict"] = {"category": "build_failed", "text": "构建失败（含错误日志）",
                              "confidence": 0.5,
                              "basis": ["构建结束状态 FAILURE", "控制台日志命中错误行 %d 行" % len(errs)]}
            run = {"rn": num, "bc": 1, "bpc": 0}
            aff = affects_of(["va", "bs"], day_avail, run)
            rec["light"] = {"vaRate": None, "bsRate": 0.0, "dims": ["va", "bs"],
                            "track": "va", "affects": aff}
            rec["analysis"] = {"status": "pending" if aff else "na"}
        else:
            rec["light"] = {"vaRate": 1.0 if st == "SUCCESS" else None, "bsRate": None,
                            "dims": ["va", "bs"], "track": "va", "affects": []}
        records.append(rec)

    steps = {
        "step_1_lights": {
            "_doc": doc("step_1_lights", component=cid, pipeline=safe_name(job), date=day,
                        criteria="社区 Nightly 流水线点灯依据（口径参考 pr-ci-board）"),
            "pipeline": {"product": cid, "pipelineShortName": safe_name(job),
                         "pipelineName": label, "platform": "jenkins",
                         "dims": ["va", "bs"], "pipelineId": "jenkins:%s:%s" % (cid, job),
                         "scheduledOnly": False},
            "selection": {"inBadPipelines": True, "dims": ["va", "bs"], "rateRule": "days",
                          "reason": "社区 Nightly 采集：当日 %d 次构建（成功 %d、失败 %d、aborted %d），"
                                    "版本可用度按「成功天数÷有执行天数」、编译成功率按「成功次数÷构建次数」统计"
                                    % (len(day_builds), day_bpc,
                                       sum(1 for x in day_builds if x["result"] == "FAILED"),
                                       sum(1 for x in day_builds if x["result"] == "ABORTED"))},
        },
        "step_2_runs": {
            "_doc": doc("step_2_runs", component=cid, pipeline=safe_name(job), date=day,
                        criteria="当日构建清单（按构建结束时间归属北京自然日）"),
            "date": day, "runHistory": run_history,
            "runs": [{"rn": h["rn"], "status": h["status"], "start": h["start"], "end": h["end"],
                      "included": True, "reason": "结束时间在归档日内"} for h in run_history],
            "failedRuns": [h for h in run_history if h["status"] == "FAILED"],
            "keptRuns": len(run_history),
            "keptFailedRuns": sum(1 for h in run_history if h["status"] == "FAILED"),
        },
        "step_5_logs": {
            "_doc": doc("step_5_logs", component=cid, pipeline=safe_name(job), date=day,
                        criteria="失败构建控制台日志取证（consoleText 整份内嵌）"),
            "results": [t for r in records for t in (r.get("tasks") or [])],
            "errors": [],
            "counts": {"tasks": sum(1 for r in records if r["status"] == "FAILED"),
                       "logFiles": ev_files, "errorLines": ev_lines},
        },
        "step_6_records": {
            "_doc": doc("step_6_records", component=cid, pipeline=safe_name(job), date=day,
                        criteria="以「一次构建」为最小单位合并记录（社区 Nightly）"),
            "date": day, "component": safe_name(cid), "pipeline": safe_name(job),
            "counts": {"records": len(records),
                       "tasks": sum(r["counts"]["tasks"] for r in records),
                       "cases": 0,
                       "errorMessages": sum(r["counts"]["errorMessages"] for r in records)},
        },
    }
    steps_meta, index = [], []
    for step in ("step_1_lights", "step_2_runs", "step_5_logs", "step_6_records"):
        dcm = steps[step]["_doc"]
        steps_meta.append({"step": step, "title": dcm["title"], "source": dcm["source"],
                           "criteria": dcm["criteria"], "dateField": dcm["dateField"]})
    manifest = {
        "date": day, "component": safe_name(cid), "pipeline": safe_name(job),
        "pipelineName": label, "platform": "jenkins",
        "key": "%s|%s" % (cid, safe_name(job)),
        "channel": "community",
        "dateBasis": {"field": "buildEndtime", "value": day,
                      "rule": "按构建结束时间归属北京自然日",
                      "runs": [{"rn": h["rn"], "status": h["status"], "endedAt": h["end"]}
                               for h in run_history]},
        "steps": steps_meta,
        "counts": steps["step_6_records"]["counts"],
        "evidence": {"pathBase": "证据正文在 pipeline.evidence.json 的 files（键=相对本目录路径），行号 1 起",
                     "rule": "控制台日志逐行内嵌，bytes/sha1/eol 可无损还原"},
        "source": {"step": "tools/collect_community_nightly.py", "generatedAt": now_str(),
                   "note": comm.get("source_note")},
    }
    payload = pipeline_doc.assemble(manifest, steps, records)
    payload["channel"] = "community"
    pipeline_doc.save(arch, payload)

    return {
        "component": safe_name(cid), "pipeline": safe_name(job), "pipelineName": label,
        "platform": "jenkins", "pipelineId": "jenkins:%s:%s" % (cid, job),
        "key": "%s|%s" % (cid, safe_name(job)),
        "channel": "community",
        "dims": ["va", "bs"],
        "rateRule": "days",
        "vaDetail": {"availDays": day_avail, "daysInPeriod": 1},
        "bsDetail": {"buildPassCount": day_bpc, "buildCount": day_bc},
        "vaRate": (day_ok / 1.0) if day_avail else 0.0,
        "bsRate": (day_bpc / float(day_bc)) if day_bc else None,
        "vaRule": "days", "bsAgg": "mean",
        "runsInPeriod": len(all_builds),
        "runsToday": len(day_builds),
        "failedRunsToday": sum(1 for b in day_builds if b["result"] == "FAILED"),
        "path": rel(arch),
        "manifest": rel(pipeline_doc.path_of(arch)),
        "file": rel(pipeline_doc.path_of(arch)),
        "layout": pipeline_doc.SCHEMA,
        "records": len(records),
        "runNumbers": [r["buildNumber"] for r in records],
        "tasks": sum(r["counts"]["tasks"] for r in records),
        "cases": 0,
        "errorMessages": sum(r["counts"]["errorMessages"] for r in records),
        "evidenceFiles": ev_files,
        "byCategory": {},
        "note": None,
    }


def merge_index(days):
    """社区并入后刷新 archive/_index.json 的计数：组件总数与各归档日的
    components/pipelines/records/tasks/cases/errorMessages 一律以当日 _day.json 为准重算。

    _index.json 由第 7 步产出，社区数据是在其之后并入的（社区采集独立于 openlibing 采集链路），
    只刷新计数、不动 days[] 的日期清单与 path，保证索引与归档内容仍然自洽。
    """
    p = ARCHIVE_ROOT / "_index.json"
    d = load_json(p, {}) or {}
    prods = load_json(ARCHIVE_ROOT / PRODUCTS_NAME, {}) or {}
    d["productCount"] = len(prods.get("products") or [])
    d["dayCount"] = len(d.get("days") or [])
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


def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------- 取数：openLiBing 侧社区流水线
# 部分社区流水线的 nightly 直接跑在 openLiBing 平台上（如 UBS Core），取数端与 Jenkins 站点完全不同：
#   执行记录 → N2（POST /gateway/openlibing-ops/manage/common/detail, category=nightly-dashboard-detail）
#   失败任务 → T4（pipeline-run/detail 任务图谱）；任务名 test 开头走 T6（测试报告），其余走 T5（任务日志）
# 这里复用仓库既有采集模板（tpl/step_2_dashboard.js、step_3_details.js、step_4_testreport.js、
# step_5_logs.js）与 lib/cdp_exec.run_page_js，不另写接口实现；
# 归档结构、口径与页面渲染和 Jenkins 社区完全一致（rateRule=days、channel=community、
# 增量并入当日 _day.json 与 _products.json）。
FAIL_STATUS = {"FAILED", "CANCELED", "CANCELLED"}
SKIP_JOB_STATUS = {"UNSELECTED", "CANCELED", "IGNORED", "INIT"}
OL_LOG_DIR = "job_logs"
OL_SAN_RE = re.compile(r'[\\/:*?"<>|\s]+')


def _ol_san(s):
    return OL_SAN_RE.sub("_", str(s or "")).strip("._")[:80] or "job"


def _ol_s6():
    """延迟导入第 6 步的记录组装工具：定性/置信度/证据展平沿用同一条规则，不另写一份。"""
    p = str(ROOT / "steps")
    if p not in sys.path:
        sys.path.insert(0, p)
    import step_6_records
    return step_6_records


def _ol_err_lines(text):
    """日志文本 → 证据行（'L<行号>: 原文'），口径与 Jenkins 社区一致（尾部优先 + 归一化去重）。"""
    return ["L%d: %s" % (ln, tx) for ln, tx in error_lines(text)]


def _ol_n2(cfg, short, key, pc, start, end):
    """N2 执行记录 → 区间内运行清单（同 pipelineRunNumber 保留结束时间最新一条）。"""
    from lib.cdp_exec import run_page_js
    coll = cfg.get("collect") or {}
    ch = cfg.get("chrome") or {}
    out = run_page_js(
        "step_2_dashboard.js",
        {"startDate": start, "endDate": end,
         "pageSize": coll.get("n2_page_size", 100),
         "delay": ch.get("inter_request_delay_ms", 250),
         "conc": ch.get("request_concurrency", 4),
         "maxTry": coll.get("detail_retry_times", 3),
         "retryBackoffMs": coll.get("detail_retry_backoff_ms") or [1000, 2000],
         "pipelines": [{"key": key, "pipelineId": pc["pipelineId"],
                        "projectId": pc["projectId"]}]},
        "ol_community_n2_%s.json" % short, cfg, "N2")
    resp = (out.get("dash") or {}).get(key) or {}
    if resp.get("code") != 200:
        print("      !! N2 接口失败（code=%s），无执行记录" % resp.get("code"))
        return None
    latest = {}
    for r in (resp.get("data") or {}).get("records") or []:
        try:
            rn = int(r.get("pipelineRunNumber"))
        except (TypeError, ValueError):
            continue
        et = r.get("pipelineRunEndtime") or ""
        if rn not in latest or et > latest[rn]["et"]:
            ftt = r.get("failedTaskType")
            latest[rn] = {
                "rn": rn, "et": et, "rid": r.get("pipelineRunId"),
                "status": r.get("pipelineStatus"),
                "start": r.get("pipelineRunStarttime") or "",
                "iva": r.get("isVersionAvailable"),
                "bc": r.get("buildCount"), "bpc": r.get("buildPassCount"),
                "cpr": r.get("casePassRate"),
                "ftt": None if ftt in (None, "流水线未失败") else ftt,
            }
    return sorted([m for m in latest.values() if start <= (m["et"] or "")[:10] <= end],
                  key=lambda m: m["et"])


def _ol_evidence(cfg, short, label, key, pc, need):
    """失败运行取证：T4 任务分流 → T6（test 路线）/ T5（log 路线 + 空测试结果回退）。

    返回 (test_items, fetch_log_items, t6_idx, t5_idx)；后两者按 (rid, jobId) 索引模板原始返回。
    """
    from lib.cdp_exec import run_page_js
    coll = cfg.get("collect") or {}
    ch = cfg.get("chrome") or {}
    delay = ch.get("inter_request_delay_ms", 250)
    conc = ch.get("request_concurrency", 4)
    backoff = coll.get("detail_retry_backoff_ms") or [1000, 2000]
    pid, proj = pc["pipelineId"], pc["projectId"]

    runs_param = [{"key": key, "rn": m["rn"], "st": m["start"], "status": m["status"],
                   "track": "va", "dims": m["affects"],
                   "projectId": proj, "pipelineId": pid, "pipelineRunId": m["rid"]}
                  for m in need]
    out = run_page_js("step_3_details.js",
                      {"runs": runs_param, "delay": delay, "conc": conc,
                       "retry": coll.get("t4_retry_times", 2), "backoffMs": backoff[-1]},
                      "ol_community_t4_%s.json" % short, cfg, "T4")

    test_items, log_items = [], []
    for d in out.get("details") or []:
        if d.get("code") != 200 or not d.get("data"):
            print("      !! T4 取证失败 rn=%s：%s" % (d.get("rn"), d.get("err") or d.get("code")))
            continue
        m = next((x for x in need if x["rn"] == d.get("rn")), None) or {}
        for st in d["data"].get("stages") or []:
            for job in st.get("jobs") or []:
                if job.get("status") != "FAILED":
                    continue
                bad = [s for s in (job.get("steps") or [])
                       if s.get("status") not in ("COMPLETED", None)]
                if not bad or not job.get("id"):
                    continue
                jn = job.get("name") or ""
                item = {
                    "key": key, "pipeline": short, "pipelineName": label,
                    "projectId": proj, "pipelineId": pid,
                    "rid": d["rid"], "rn": d["rn"],
                    "st": m.get("start") or "", "status": m.get("status"),
                    "jobId": job.get("id"), "jobName": jn,
                    "stepIds": [s.get("id") for s in bad],
                    "steps": [{"id": s.get("id"), "name": s.get("name"),
                               "status": s.get("status"), "errMsg": s.get("message")}
                              for s in bad],
                    "jobErrMsg": job.get("message"),
                }
                # 分流口径：任务名含 test（不区分大小写）→ test 路线，其余 → log 路线。
                # UBS Core 的任务命名形如 Build_ubs-* / Deploy_Test_* / Test_BeiMing：
                # 除 build 外其余任务名都带 test 字样，均按 test 任务处理。
                (test_items if "test" in jn.lower() else log_items).append(item)

    t6 = {}
    if test_items:
        out = run_page_js("step_4_testreport.js",
                          {"items": test_items, "pageSize": coll.get("t6_page_size", 100),
                           "delay": delay, "conc": conc,
                           "maxTry": coll.get("detail_retry_times", 3),
                           "retryBackoffMs": backoff},
                          "ol_community_t6_%s.json" % short, cfg, "T6")
        for r in out.get("results") or []:
            src = next((x for x in test_items
                        if x["rid"] == r["rid"] and x["jobId"] == r["jobId"]), None) or {}
            t6[(r["rid"], r["jobId"])] = dict(
                r, jobName=src.get("jobName"), steps=src.get("steps") or [],
                jobErrMsg=src.get("jobErrMsg"))

    # log 路线任务 + 「测试结果为空 / 无用例」的 test 任务（回退整 job 日志，口径同第 5 步）
    fetch = [dict(it, route="log", fallback=False) for it in log_items]
    for it in test_items:
        r = t6.get((it["rid"], it["jobId"]))
        if r is None or r.get("empty") or not (r.get("failedCases") or []):
            fetch.append(dict(it, route="log", fallback=True))

    t5 = {}
    if fetch:
        out = run_page_js("step_5_logs.js",
                          {"items": fetch, "logLimit": coll.get("t5_log_limit", 300),
                           "maxErrLines": 40, "delay": delay, "conc": conc,
                           "maxTry": coll.get("detail_retry_times", 3),
                           "retryBackoffMs": backoff},
                          "ol_community_t5_%s.json" % short, cfg, "T5")
        for r in out.get("results") or []:
            src = next((x for x in fetch
                        if x["rid"] == r["rid"] and x["jobId"] == r["jobId"]), None) or {}
            t5[(r["rid"], r["jobId"])] = dict(
                r, jobName=src.get("jobName"), steps=src.get("steps") or [],
                jobErrMsg=src.get("jobErrMsg"),
                fallback=bool(src.get("fallback")))

    return test_items, fetch, t6, t5


def _ol_tasks(arch, cid, short, it_list, t6, t5):
    """把模板原始返回组装成记录里的 tasks[]（test 任务带失败用例，log 任务带日志证据）。"""
    tasks = []
    for it in it_list:
        k = (it["rid"], it["jobId"])
        step_errs = [s.get("errMsg") for s in it.get("steps") or [] if s.get("errMsg")]
        r6 = t6.get(k)
        r5 = t5.get(k)
        if r6 is not None:
            cases = []
            for c in r6.get("failedCases") or []:
                cases.append({
                    "name": c.get("name"), "state": c.get("state"),
                    "description": c.get("description"),
                    "beginTime": c.get("beginTime"), "endTime": c.get("endTime"),
                    "logUrl": c.get("resultDownloadUrl"),
                    "localLog": None, "errorMessages": [], "deepHits": [],
                })
            # 回退整 job 日志的 test 任务：步骤级错误信息统一由下面的 log 任务承载，
            # 这里留空，避免同一批 stepErrMsgs 在两处重复计入错误信息清单
            tasks.append({"jobName": it["jobName"], "type": "test",
                          "summary": r6.get("summary"), "cases": cases,
                          "emptyTestResult": bool(r6.get("empty")),
                          "stepErrMsgs": [] if r5 is not None else step_errs})
        if r5 is None:
            # log 路线的任务确实没取到日志才落一条空证据提示；
            # test 路线（报告非空、未回退日志）不在此列，避免凭空多出一个 log 任务
            if it.get("route") != "test":
                tasks.append({"jobName": it["jobName"], "type": "log",
                              "fallback": bool(it.get("fallback")),
                              "logFile": None, "errorLines": [],
                              "stepErrMsgs": step_errs, "jobErrMsg": it.get("jobErrMsg"),
                              "subTasks": [],
                              "evidenceNote": "任务日志未能导出（导出接口失败且分页兜底未取到）"})
            continue
        text = r5.get("logTail") or ""
        rel_path = "%s/%s_%s_%s_%s.log" % (OL_LOG_DIR, safe_name(cid), short,
                                           it["rn"], _ol_san(it["jobName"]))
        nbytes, nlines = put_evidence(arch, rel_path, text)
        tasks.append({"jobName": it["jobName"], "type": "log",
                      "fallback": bool(it.get("fallback")),
                      "logFile": rel_path, "logBytes": nbytes, "logLines": nlines,
                      "download": "paging",
                      "truncated": bool(r5.get("has_more")) or len(text) >= 4000,
                      "excerpt": None,
                      "stepErrMsgs": step_errs, "jobErrMsg": it.get("jobErrMsg"),
                      "errorLines": _ol_err_lines(text), "subTasks": []})
    return tasks


def collect_openlibing_community(comm, start, end, day_entries, prod_acc, scope):
    """openLiBing 侧社区流水线采集并归档（与 Jenkins 社区同归并口径）。

    scope = 采集窗口内的自然日集合，逐日 vaDetail 只认窗口内的日子（窗口外的开始日不进分母）。
    """
    cid = comm["id"]
    cfg = load_json(CONFIG, {}) or {}
    pipe_rates, pipe_bs = [], []
    for pc in comm.get("pipelines") or []:
        label = pc["label"]
        short = safe_name(label)
        key = "%s|%s" % (cid, short)
        runs = _ol_n2(cfg, short, key, pc, start, end)
        print("   %s（pipelineId=%s / projectId=%s）" % (label, pc["pipelineId"], pc["projectId"]))
        if runs is None:
            continue
        print("      区间内 %d 次运行 %s" % (
            len(runs), [(m["rn"], m["status"], m["et"][:16]) for m in runs]))
        if not runs:
            continue

        by_day = {}
        for m in runs:
            by_day.setdefault(m["et"][:10], []).append(m)
        # 日可用口径（双指标）：当天任一次运行 isVersionAvailable=true → 当天可用
        day_avail = {d: (1 if any(x["iva"] is True for x in ms) else 0)
                     for d, ms in by_day.items()}
        # 记录级维度归属：与 step_6 / 页面 / 两个校验工具共用 lib/dim_affects 的同一份口径
        need = []
        for d in sorted(by_day):
            for m in by_day[d]:
                m["day"] = d
                m["affects"] = (affects_of(["va", "bs"], day_avail[d],
                                           {"bc": m["bc"], "bpc": m["bpc"]})
                                if str(m["status"]).upper() in FAIL_STATUS else [])
                if m["affects"]:
                    need.append(m)
        print("      需取证运行 %d 次（当日不可用→va；本次编译未全过→bs）：%s"
              % (len(need), [(m["rn"], m["affects"]) for m in need]))

        t6, t5 = {}, {}
        if need:
            _, _, t6, t5 = _ol_evidence(cfg, short, label, key, pc, need)

        exec_days = ok_days = bc = bpc = 0
        # 版本可用度新口径：开始日进分母、跨午夜开始日记不可用、成功只记结束日
        ol_runs = [{"status": m["status"], "start": m["start"], "end": m["et"],
                    "iva": m["iva"] is True,
                    "bc": m["bc"], "bpc": m["bpc"]} for m in runs]
        dva = day_va(ol_runs, never_avail_statuses=(
            "ABORTED", "CANCELED", "CANCELLED"), days_in_scope=scope)
        dbs = day_bs_detail(ol_runs, skip_statuses=("CANCELED", "CANCELLED"))
        last_entry = None
        for d in sorted(set(by_day) | set(dva)):
            if d in by_day:
                ms = by_day[d]
                non_cancel = [m for m in ms if str(m["status"]).upper() not in ("CANCELED", "CANCELLED")]
                day_bc = sum(int(m["bc"] or 0) for m in non_cancel)
                day_bpc = sum(int(m["bpc"] or 0) for m in non_cancel)
                need_day = [m for m in need if m["day"] == d]
                entry = _build_ol_day(cid, short, label, key, pc, d, ms, non_cancel,
                                      day_avail[d], day_bc, day_bpc, need_day, t6, t5, len(runs))
                entry["vaDetail"] = dva.get(d) or {"availDays": 0, "daysInPeriod": 0}
                entry["bsDetail"] = dbs.get(d) or {"buildPassCount": 0, "buildCount": 0}
                last_entry = entry
            elif last_entry is not None:
                entry = synth_day_entry(last_entry, d, dva.get(d) or {},
                                        "当日仅启动、未结束：计入分母但不计可用（跨午夜运行）")
            else:
                continue
            day_entries.setdefault(d, []).append(entry)
        exec_days = sum(1 for v in dva.values() if v.get("daysInPeriod"))
        ok_days = sum(1 for v in dva.values() if v.get("availDays"))
        bc = sum(v.get("buildCount") or 0 for v in dbs.values())
        bpc = sum(v.get("buildPassCount") or 0 for v in dbs.values())
        print("      → 执行 %d 天 / 成功 %d 天（可用度 %s）｜构建 %d 次 / 成功 %d 次（编译成功率 %s）"
              % (exec_days, ok_days,
                 "%.1f%%" % (100.0 * ok_days / exec_days) if exec_days else "--",
                 bc, bpc, "%.1f%%" % (100.0 * bpc / bc) if bc else "--"))

    va = sum(pipe_rates) / len(pipe_rates) if pipe_rates else None
    bs = sum(pipe_bs) / len(pipe_bs) if pipe_bs else None
    prod_acc[cid] = {
        "name": cid, "projectId": None, "channel": "community",
        "versionAvailabilityRate": va, "buildSuccessRate": bs,
        "pipelineCount": len(comm.get("pipelines") or []),
        "badPipelineCount": sum(1 for r in pipe_rates if r < 1) + sum(1 for r in pipe_bs if r < 1),
        "analyze": True, "rateRule": "days", "bsAgg": "mean", "recompute": True,
        "firstSeen": now_str(), "lastSeen": now_str(),
    }
    print("   == 组件 %s：版本可用度 %s ｜ 编译成功率 %s" %
          (cid, "%.1f%%" % (100 * va) if va is not None else "--",
           "%.1f%%" % (100 * bs) if bs is not None else "--"))


def _build_ol_day(cid, short, label, key, pc, day, day_runs, non_cancel,
                  day_avail, day_bc, day_bpc, need_day, t6, t5, runs_in_period):
    """组装 openLiBing 社区某流水线某一天的归档（pipeline.json + 证据），返回 _day.json 条目。"""
    s6 = _ol_s6()
    pid, proj = pc["pipelineId"], pc["projectId"]
    arch = archive_dir(day, cid, short)
    if arch.exists():                       # 同日重跑：整体重建，不残留上次的日志/记录
        for f in list(arch.glob("*.json")):
            f.unlink()
    arch.mkdir(parents=True, exist_ok=True)

    def _link(rid):
        return ("https://www.openlibing.com/apps/pipelineDetail"
                "?pipelineId=%s&projectId=%s&pipelineRunId=%s" % (pid, proj, rid))

    # 取证顺序保持 T6（test 路线）在前、T5 在后，与第 4/5 步一致
    tasks_by_rid = {}
    for m in need_day:
        ordered = [k for k in t6 if k[0] == m["rid"]] + [k for k in t5 if k[0] == m["rid"]]
        seen, item_list = set(), []
        for k in ordered:
            if k in seen:
                continue
            seen.add(k)
            src = t5.get(k) or t6.get(k) or {}
            item_list.append({"rid": k[0], "rn": m["rn"], "jobId": k[1],
                              "route": "test" if k in t6 else "log",
                              "jobName": src.get("jobName"),
                              "steps": src.get("steps") or [],
                              "jobErrMsg": src.get("jobErrMsg"),
                              "fallback": bool(src.get("fallback"))})
        tasks_by_rid[m["rid"]] = _ol_tasks(arch, cid, short, item_list, t6, t5)

    run_history, records = [], []
    for m in sorted(day_runs, key=lambda x: x["rn"]):
        rid, rn, st = m["rid"], m["rn"], str(m["status"] or "")
        run_history.append({
            "rn": rn, "rid": rid, "status": st,
            "start": (m["start"] or "").replace(" ", "T"),
            "end": (m["et"] or "").replace(" ", "T"),
            "iva": m["iva"] is True,
            "bc": m["bc"], "bpc": m["bpc"], "ftt": m["ftt"],
            "url": _link(rid),
        })
    for m in sorted(day_runs, key=lambda x: x["rn"]):
        rid, rn, st = m["rid"], m["rn"], str(m["status"] or "")
        started = (m["start"] or "").replace(" ", "T")
        ended = (m["et"] or "").replace(" ", "T")
        aff = m["affects"]
        fail_like = st.upper() in FAIL_STATUS
        tasks = tasks_by_rid.get(rid, [])
        if aff:
            category, basis = s6.classify({"ftt": m["ftt"], "status": st}, tasks)
            score, why = s6.confidence_of({"status": st}, tasks, basis)
            track = "va" if "va" in aff else "bs"
        elif fail_like:
            category = "waived"
            basis = ["运行状态 %s，当日版本可用且本次运行没有编译失败，"
                     "既不影响版本可用度也不影响编译成功率，不做根因分析" % st]
            score, why, track = 1.0, [], "-"
        else:
            category = "success"
            basis = ["运行状态 %s，任务未失败，无需根因分析" % st]
            score, why, track = 1.0, [], "-"
        cases = s6.flatten_cases(tasks)
        errors = s6.flatten_errors(tasks)
        files = s6.evidence_files(tasks)
        analysis = ({"status": "pending", "rootCause": None, "advice": None,
                     "cites": [], "updatedAt": None, "source": None}
                    if aff else
                    {"status": "na", "rootCause": None, "advice": None,
                     "cites": [], "updatedAt": None, "source": None})
        records.append({
            "recordId": "%s#%s" % (key, rn),
            "date": day, "component": safe_name(cid), "pipeline": short,
            "pipelineName": label, "platform": pc.get("platform") or "openlibing",
            "buildNumber": rn, "pipelineRunId": rid, "status": st,
            "failedTaskType": m["ftt"],
            "startedAt": started, "endedAt": ended,
            "dateBasis": {"field": "pipelineRunEndtime", "value": ended,
                          "rule": "按执行结束时间归属自然日（同运行多条评估记录保留最新一条）"},
            "light": {"vaRate": None, "bsRate": None,
                      "dims": ["va", "bs"], "track": track, "affects": aff},
            "links": {"openlibing": _link(rid), "detail": None, "github": None},
            "tasks": tasks, "cases": cases, "errorMessages": errors,
            "evidence": {"files": files,
                         "missing": sorted({t["jobName"] for t in tasks
                                            if not t.get("logFile") and not t.get("cases")}),
                         "github": None},
            "counts": {"tasks": len(tasks),
                       "testTasks": sum(1 for t in tasks if t.get("type") == "test"),
                       "logTasks": sum(1 for t in tasks if t.get("type") == "log"),
                       "buildTasks": sum(1 for t in tasks
                                         if (t.get("jobName") or "").lower().startswith("build")),
                       "cases": len(cases), "errorMessages": len(errors),
                       "evidenceFiles": len(files)},
            "verdict": {"category": category, "text": s6.CATEGORY_TEXT[category],
                        "confidence": score,
                        "level": "高" if score >= 0.75 else ("中" if score >= 0.5 else "低"),
                        "basis": basis + why},
            "suggestions": [],
            "analysis": analysis,
        })

    steps = {
        "step_1_lights": {
            "_doc": doc("step_1_lights", component=cid, pipeline=short, date=day,
                        criteria="openLiBing 侧社区 Nightly 流水线点灯依据"),
            "pipeline": {"product": cid, "pipelineShortName": short,
                         "pipelineName": label, "platform": pc.get("platform") or "openlibing",
                         "dims": ["va", "bs"],
                         "pipelineId": "openlibing:%s:%s" % (cid, pid),
                         "scheduledOnly": False},
            "selection": {"inBadPipelines": True, "dims": ["va", "bs"], "rateRule": "days",
                          "reason": "openLiBing 侧社区采集：当日 %d 次运行，"
                                    "版本可用度按「成功天数÷有执行天数」、"
                                    "编译成功率按「Σ编译成功次数÷Σ编译次数」统计" % len(day_runs)},
        },
        "step_2_runs": {
            "_doc": doc("step_2_runs", component=cid, pipeline=short, date=day,
                        criteria="N2 nightly-dashboard-detail 逐运行明细（按结束时间归属）"),
            "date": day, "runHistory": run_history,
            "runs": [{"rn": h["rn"], "status": h["status"], "start": h["start"],
                      "end": h["end"], "included": True, "reason": "结束时间在归档日内"}
                     for h in run_history],
            "failedRuns": [h for h in run_history if str(h["status"]).upper() in FAIL_STATUS],
            "keptRuns": len(run_history),
            "keptFailedRuns": sum(1 for h in run_history
                                  if str(h["status"]).upper() in FAIL_STATUS),
        },
        "step_3_tasks": {
            "_doc": doc("step_3_tasks", component=cid, pipeline=short, date=day,
                        criteria="T4 任务图谱分流：任务名 test 开头 → T6，其余 → T5"),
            "results": [], "counts": {"tasks": sum(len(v) for v in tasks_by_rid.values())},
        },
        "step_5_logs": {
            "_doc": doc("step_5_logs", component=cid, pipeline=short, date=day,
                        criteria="T5 任务日志取证（导出失败自动回退分页接口）"),
            "results": [t for r in records for t in (r.get("tasks") or [])
                        if t.get("type") == "log"],
            "errors": [],
            "counts": {"tasks": sum(1 for r in records for t in r.get("tasks") or []
                                    if t.get("type") == "log"),
                       "logFiles": sum(1 for r in records for t in r.get("tasks") or []
                                       if t.get("logFile")),
                       "errorLines": sum(len(t.get("errorLines") or []) for r in records
                                         for t in r.get("tasks") or [])},
        },
        "step_6_records": {
            "_doc": doc("step_6_records", component=cid, pipeline=short, date=day,
                        criteria="以「一次运行」为最小单位合并记录（openLiBing 社区）"),
            "date": day, "component": safe_name(cid), "pipeline": short,
            "counts": {"records": len(records),
                       "tasks": sum(r["counts"]["tasks"] for r in records),
                       "cases": sum(r["counts"]["cases"] for r in records),
                       "errorMessages": sum(r["counts"]["errorMessages"] for r in records)},
        },
    }
    steps_meta = []
    for step in ("step_1_lights", "step_2_runs", "step_3_tasks", "step_5_logs", "step_6_records"):
        dcm = steps[step]["_doc"]
        steps_meta.append({"step": step, "title": dcm["title"], "source": dcm["source"],
                           "criteria": dcm["criteria"], "dateField": dcm["dateField"]})
    manifest = {
        "date": day, "component": safe_name(cid), "pipeline": short, "pipelineName": label,
        "platform": pc.get("platform") or "openlibing",
        "key": key, "channel": "community",
        "dateBasis": {"field": "pipelineRunEndtime", "value": day,
                      "rule": "按执行结束时间归属自然日（同运行多条评估记录保留最新一条）",
                      "runs": [{"rn": h["rn"], "status": h["status"], "endedAt": h["end"]}
                               for h in run_history]},
        "steps": steps_meta,
        "counts": steps["step_6_records"]["counts"],
        "evidence": {"pathBase": "证据正文在 pipeline.evidence.json 的 files（键=相对本目录路径），行号 1 起",
                     "rule": "任务日志逐行内嵌，bytes/sha1/eol 可无损还原"},
        "source": {"step": "tools/collect_community_nightly.py", "generatedAt": now_str(),
                   "note": comm_note(pc)},
    }
    payload = pipeline_doc.assemble(manifest, steps, records)
    payload["channel"] = "community"
    pipeline_doc.save(arch, payload)

    return {
        "component": safe_name(cid), "pipeline": short, "pipelineName": label,
        "platform": pc.get("platform") or "openlibing",
        "pipelineId": "openlibing:%s:%s" % (cid, pid), "key": key, "channel": "community",
        "dims": ["va", "bs"], "rateRule": "days",
        "vaDetail": {"availDays": day_avail, "daysInPeriod": 1},
        "bsDetail": {"buildPassCount": day_bpc, "buildCount": day_bc},
        "vaRate": float(day_avail),
        "bsRate": (day_bpc / float(day_bc)) if day_bc else None,
        "vaRule": "days", "bsAgg": "mean",
        "runsInPeriod": runs_in_period, "runsToday": len(day_runs),
        "failedRunsToday": sum(1 for m in day_runs
                               if str(m["status"]).upper() in FAIL_STATUS),
        "path": rel(arch), "manifest": rel(pipeline_doc.path_of(arch)),
        "file": rel(pipeline_doc.path_of(arch)), "layout": pipeline_doc.SCHEMA,
        "records": len(records),
        "runNumbers": [r["buildNumber"] for r in records],
        "tasks": sum(r["counts"]["tasks"] for r in records),
        "cases": sum(r["counts"]["cases"] for r in records),
        "errorMessages": sum(r["counts"]["errorMessages"] for r in records),
        "evidenceFiles": sum(r["counts"]["evidenceFiles"] for r in records),
        "byCategory": {}, "note": None,
    }


def comm_note(pc):
    return pc.get("source_note") or "openLiBing 侧社区流水线（N2 执行记录 + T4/T6/T5 任务取证）"


# ------------------------------------------------------------------ 归档合并
def merge_day(day, entries):
    """把社区流水线条目并入当日 _day.json.pipelines[]。

    只替换**本次采到的那些 key**（同 key 覆盖），其余既有条目一律保留 ——
    社区采集常常只覆盖少数几天（例如补采失败日），若把当日所有 channel=community 的
    条目先整体清掉，非采集日的社区流水线就会从 _day.json 里消失，页面「执行记录」弹窗
    逐日读不到这些流水线的 runHistory，表现为「社区失败记录整体不展示」。
    """
    day_dir = ARCHIVE_ROOT / day[:4] / day[:7] / day
    p = day_dir / "_day.json"
    d = load_json(p, {}) or {}
    by_key = {e["key"] for e in entries}
    pipes = [x for x in (d.get("pipelines") or [])
             if not (isinstance(x, dict) and x.get("channel") == "community"
                     and x.get("key") in by_key)]
    pipes = pipes + list(entries)
    d.setdefault("date", day)
    d["pipelines"] = pipes
    counts = d.get("counts") or {}
    counts["components"] = len({x.get("component") for x in pipes})
    counts["pipelines"] = len(pipes)
    counts["records"] = sum(int(x.get("records") or 0) for x in pipes)
    counts["tasks"] = sum(int(x.get("tasks") or 0) for x in pipes)
    counts["cases"] = sum(int(x.get("cases") or 0) for x in pipes)
    counts["errorMessages"] = sum(int(x.get("errorMessages") or 0) for x in pipes)
    d["counts"] = counts
    day_dir.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def merge_products(prods):
    """把社区并入 out/archive/_products.json（同 name 覆盖，社区条目标 channel=community）。"""
    p = ARCHIVE_ROOT / PRODUCTS_NAME
    d = load_json(p, {}) or {}
    items = [x for x in (d.get("products") or [])
             if not (isinstance(x, dict) and x.get("name") in prods)]
    items += list(prods.values())
    d["products"] = sorted(items, key=lambda x: str(x.get("name")).lower())
    d["count"] = len(d["products"])
    d.setdefault("generatedAt", now_str())
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ 主流程
def run(start, end, community=None):
    """按区间 [start, end] 采集社区 Nightly 并归档（供 CLI 与第 7b 步共用）。

    community 指定时只采集该社区；缺省采集 community_sources.json 里的全部社区。
    产出与第 7 步同层：归档目录 + 并入当日 _day.json + 刷新 _products.json / _index.json。
    """
    src = load_json(SOURCES, {}) or {}
    comms = [c for c in (src.get("communities") or [])
             if not community or c.get("id") == community]
    if not comms:
        raise SystemExit("!! community_sources.json 里没有匹配的社区")
    print("== 社区 Nightly 采集：%s ~ %s ｜ %d 个社区" %
          (start, end, len(comms)))
    scope = window_days(start, end)

    day_entries, prod_acc = {}, {}
    for comm in comms:
        cid = comm.get("id")
        mode = comm.get("fetch_mode") or "ajax"
        print("\n-- 社区 %s（%s ｜ %s）" % (cid, comm.get("jenkins_base") or "openLiBing", mode))
        if mode == "openlibing":              # openLiBing 侧社区流水线：走 N2/T4/T6/T5 采集链路
            collect_openlibing_community(comm, start, end, day_entries, prod_acc, scope)
            continue
        base = comm["jenkins_base"].rstrip("/")
        headers, auth_note = auth_headers(cid, comm)
        print("   （认证 %s）" % auth_note)
        tasks = {t["job"]: t for t in (comm.get("tasks") or [])}
        pipe_rates, pipe_bs = [], []
        for job, task in tasks.items():
            builds = (fetch_jobs_api(base, job, headers) if mode == "api"
                      else fetch_jobs_ajax(base, job, headers))
            in_win = [b for b in builds if b.get("ts")
                      and start <= bj_day(b["ts"]).strftime("%Y-%m-%d") <= end]
            print("   %s：历史 %d 条，区间内 %d 条 %s" %
                  (job, len(builds), len(in_win),
                   [(b["number"], b["result"], bj_day(b["ts"]).strftime("%m-%d %H:%M")) for b in in_win]))
            if builds and not in_win:
                oldest = bj_day(builds[0]["ts"]).strftime("%Y-%m-%d") if builds[0].get("ts") else "?"
                print("      !! 区间内无构建（最早可回溯 %s，可能历史不足或区间外）" % oldest)
            by_day = {}
            for b in in_win:
                by_day.setdefault(bj_day((b["ts"] or 0) + (b["dur_ms"] or 0)
                                         if b["ts"] else 0).strftime("%Y-%m-%d"), []).append(b)
            # 版本可用度新口径：开始日进分母、跨午夜开始日记不可用、成功只记结束日；
            # 纯开始日（当天没有任何构建结束）补一条轻量条目，归档仍在结束日。
            runs = [jenkins_run(b) for b in in_win]
            dva = day_va(runs, never_avail_statuses=SKIP_RESULTS, days_in_scope=scope)
            dbs = day_bs_detail(runs, skip_statuses=SKIP_RESULTS)
            last_entry = None
            for day in sorted(set(by_day) | set(dva)):
                if day in by_day:
                    entry = build_pipeline_day(comm, task, day, by_day[day], in_win, headers)
                    entry["vaDetail"] = dva.get(day) or {"availDays": 0, "daysInPeriod": 0}
                    entry["bsDetail"] = dbs.get(day) or {"buildPassCount": 0, "buildCount": 0}
                    last_entry = entry
                elif last_entry is not None:
                    entry = synth_day_entry(last_entry, day, dva.get(day) or {},
                                            "当日仅启动、未结束：计入分母但不计可用（跨午夜运行）")
                else:
                    continue
                day_entries.setdefault(day, []).append(entry)
            # 走势统计（写入 _products.json 的社区组件比率用，与逐日 vaDetail 同一口径）
            exec_days = sum(1 for d in dva.values() if d.get("daysInPeriod"))
            ok_days = sum(1 for d in dva.values() if d.get("availDays"))
            bc = sum(d.get("buildCount") or 0 for d in dbs.values())
            bpc = sum(d.get("buildPassCount") or 0 for d in dbs.values())
            if exec_days:
                pipe_rates.append(ok_days / exec_days)
            if bc:
                pipe_bs.append(bpc / float(bc))
            print("      → 执行 %d 天 / 成功 %d 天（可用度 %s）｜构建 %d 次 / 成功 %d 次（编译成功率 %s）"
                  % (exec_days, ok_days,
                     "%.1f%%" % (100.0 * ok_days / exec_days) if exec_days else "--",
                     bc, bpc, "%.1f%%" % (100.0 * bpc / bc) if bc else "--"))
        va = sum(pipe_rates) / len(pipe_rates) if pipe_rates else None
        bs = sum(pipe_bs) / len(pipe_bs) if pipe_bs else None
        prod_acc[cid] = {
            "name": cid, "projectId": None, "channel": "community",
            "versionAvailabilityRate": va, "buildSuccessRate": bs,
            "pipelineCount": len(tasks),
            "badPipelineCount": sum(1 for r in pipe_rates if r < 1) + sum(1 for r in pipe_bs if r < 1),
            "analyze": True, "rateRule": "days", "bsAgg": "mean", "recompute": True,
            "firstSeen": now_str(), "lastSeen": now_str(),
        }
        print("   == 组件 %s：版本可用度 %s ｜ 编译成功率 %s" %
              (cid, "%.1f%%" % (100 * va) if va is not None else "--",
               "%.1f%%" % (100 * bs) if bs is not None else "--"))

    for day, entries in sorted(day_entries.items()):
        merge_day(day, entries)
    if prod_acc:
        merge_products(prod_acc)
    merge_index(set(day_entries))
    print("\n== 归档完成：%d 个归档日被更新，%d 个社区组件并入 _products.json"
          % (len(day_entries), len(prod_acc)))
    return day_entries, prod_acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--community", help="只采集指定社区（缺省为全部）")
    args = ap.parse_args()
    start, end = window_from_config(args)
    run(start, end, args.community)


if __name__ == "__main__":
    main()
