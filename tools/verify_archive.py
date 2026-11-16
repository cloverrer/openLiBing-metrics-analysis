# -*- coding: utf-8 -*-
"""归档自检 —— 逐层核对 out/archive/ 是否「每条结论都能落到证据」。

用途: 归档完成后或交付前跑一遍，把可被挑战的点提前暴露：
  1) 结构层：<年>/<年-月>/<日>/<组件>/<流水线>/ 目录命名是否合规；
  2) 清单层：_day.json / pipeline.json 是否可解析，stepIndex 登记的每一步正文是否都在；
  3) 记录层：records[] 每条记录的 date 是否等于所在日期目录（防止日期归属错层）；
  4) 证据层：JSON 里引用的证据相对路径（job_logs/ case_logs/ github_logs/）在本目录的
     `pipeline.evidence.json` 里是否有正文，且引用的行号没有超出该证据的总行数。

一条流水线归档已合并成两份文件：pipeline.json（清单+每步正文+逐条记录）与
pipeline.evidence.json（证据原文逐行内嵌）。还没合并的老归档（_manifest.json +
step_*.json + records/run_*.json + 证据散文件）由 pipeline_doc.load() 就地拼成同样的
结构，两种布局走同一套校验 —— 证据只有在「JSON 里没有正文、磁盘上也没有文件」时才算缺失。

用法:
  python tools/verify_archive.py                  # 校验全部归档
  python tools/verify_archive.py --date 2026-11-03
  python tools/verify_archive.py --component MindStudio
  python tools/verify_archive.py --json out/state/verify_archive.json   # 另存机器可读报告
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.dim_affects import affects_of, day_avail_of  # noqa: E402
from lib.paths import (ARCHIVE_ROOT, DATE_FIELD, iter_archive_days,  # noqa: E402
                       iter_scoped_pipelines, rel, stale_pipeline_dirs)

EVIDENCE_PREFIX = pipeline_doc.EVIDENCE_PREFIX
DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
JSON_SUFFIX = ".json"
# 引用里的行号定位后缀：:L138 / :138 / :L10-L20 / :10-L20
CITE_LINE_RE = re.compile(r":L?\d+(?:-L?\d+)?$")
FAIL_STATUS = {"FAILED", "CANCELED", "CANCELLED"}


def cite_lines(where):
    """把行号定位串解析成行号列表：'L138' -> [138]；'L10-L20' -> [10, 20]。"""
    out = []
    for part in re.findall(r"\d+", str(where or "")):
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def split_ref(s):
    """把证据引用拆成 (文件相对路径, 行号定位)：'job_logs/x.log:L138' -> ('job_logs/x.log', 'L138')。"""
    s = str(s or "")
    m = CITE_LINE_RE.search(s)
    if m:
        return s[:m.start()], s[m.start() + 1:]
    return s, ""


def load_json(p):
    return json.loads(p.read_text(encoding="utf-8"))


def iter_strings(obj, key=None):
    """递归产出 JSON 结构里的所有字符串。

    `_manifest.json` 的 evidence.renamed[] 里 `from` 是**改名前的原始路径**（归档里
    本来就不该存在），只校验 `to`（改名后的实际文件），否则会自造误报。
    """
    if isinstance(obj, str):
        if key != "from":
            yield obj
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_strings(v, key)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, k)


def check_analysis(pdir, doc, day, stats):
    """分析完整性：失败/取消记录里「影响当日指标」的必须有根因，堵住静默漏分析。

    归属与 steps/step_6_records.py、页面 JS 同一口径（lib/dim_affects）：
      记录自带 light.affects 时直接采信（新归档）；
      缺该字段（老归档 / 手工改过）就地用 runHistory + 当日可用性重算，口径完全一致。
    失败记录命中任一维度却 analysis.status != done（或根因为空）＝漏分析；
    反过来不影响任何维度却 pending / 已有根因＝多分析。两类都算问题，交付前必须先清零。
    """
    problems = []
    recs = doc.get("records") or []
    if not any(str(r.get("status") or "").upper() in FAIL_STATUS for r in recs):
        return problems
    steps = doc.get("steps") or {}
    dims = ((steps.get("step_1_lights") or {}).get("pipeline") or {}).get("dims") or []
    run_history = (steps.get("step_2_runs") or {}).get("runHistory") or []
    day_avail = day_avail_of(run_history, day)
    run_by_rn = {str(h.get("rn")): h for h in run_history}
    for rec in recs:
        if str(rec.get("status") or "").upper() not in FAIL_STATUS:
            continue
        rid = rec.get("recordId")
        lt = rec.get("light") or {}
        aff = lt.get("affects")
        if not isinstance(aff, list):
            aff = affects_of(dims, day_avail, run_by_rn.get(str(rec.get("buildNumber"))))
        an = rec.get("analysis") or {}
        st = an.get("status") or ""
        root = str(an.get("rootCause") or "").strip()
        if aff:
            if st == "na":
                stats["analysisLeak"] += 1
                problems.append({"path": rel(pdir), "issue":
                                 "漏分析 %s：影响当日 %s 指标，却标为 analysis.status=na"
                                 % (rid, "/".join(aff))})
            elif st == "pending":
                stats["analysisPending"] += 1
                problems.append({"path": rel(pdir), "issue":
                                 "待分析未完成 %s：影响当日 %s 指标，仍为 pending" % (rid, "/".join(aff))})
            elif st == "done" and not root:
                stats["analysisLeak"] += 1
                problems.append({"path": rel(pdir), "issue":
                                 "根因为空 %s：status=done 但 rootCause 为空" % rid})
        elif st == "pending":
            stats["analysisExtra"] += 1
            problems.append({"path": rel(pdir), "issue":
                             "多分析 %s：不影响当日任何维度指标，却标为 pending" % rid})
        elif st == "done":
            stats["analysisExtra"] += 1
            problems.append({"path": rel(pdir), "issue":
                             "多分析 %s：不影响当日任何维度指标，却已有根因（应为 na）" % rid})
    return problems


def check_pipeline_dir(pdir):
    """校验单个 <组件>/<流水线>/ 目录，返回问题列表。"""
    problems, stats = [], {"records": 0, "evidenceRefs": 0, "evidenceMissing": 0,
                           "analysisLeak": 0, "analysisExtra": 0, "analysisPending": 0}
    day = pdir.parent.parent.name
    doc = pipeline_doc.load(pdir)
    if doc is None:
        problems.append({"path": rel(pdir),
                         "issue": "缺少 %s（也没有可拼装的老结构 _manifest.json）" % pipeline_doc.NAME})
        return problems, stats
    # 老归档（还没合并）也统一按同一套字段校验，只是落盘位置不同
    legacy = (doc.get("layout") == "legacy")
    src = rel(pdir / "_manifest.json") if legacy else rel(pipeline_doc.path_of(pdir))

    if doc.get("date") != day:
        problems.append({"path": src,
                         "issue": "归档 date=%r 与目录日期 %r 不一致（日期口径应为 %s）"
                                  % (doc.get("date"), day, DATE_FIELD)})

    # 清单层：stepIndex 登记了哪几步，正文就必须在 steps 里（老归档则查那 8 份文件是否还在）
    steps = doc.get("steps") or {}
    for st in doc.get("stepIndex") or []:
        name = st.get("step")
        if legacy:
            f = pdir / (st.get("file") or "")
            if not st.get("file") or not f.exists():
                problems.append({"path": rel(pdir),
                                 "issue": "清单登记的第 %s 步文件缺失: %r"
                                          % (name, st.get("file"))})
        elif name not in steps:
            problems.append({"path": src,
                             "issue": "stepIndex 登记的第 %s 步正文缺失（steps 里没有该键）" % name})

    # 记录层：records[] 就是记录全文（老归档已由 load() 从 records/run_*.json 拼好）
    recs = doc.get("records") or []
    stats["records"] = len(recs)
    for rec in recs:
        rid = rec.get("recordId")
        if rec.get("date") != day:
            problems.append({"path": src,
                             "issue": "记录 recordId=%r 的 date=%r 与目录日期 %r 不一致"
                                      % (rid, rec.get("date"), day)})

    # 老归档额外对一遍账：清单登记过的记录、磁盘上多出来的记录文件，都不许出现
    if legacy:
        try:
            man = load_json(pdir / "_manifest.json")
        except Exception:                                      # noqa: BLE001
            man = {}
        listed = {r.get("recordId") for r in man.get("records") or []}
        rdir = pdir / "records"
        on_disk = set()
        for rf in sorted(rdir.glob("run_*.json")) if rdir.exists() else []:
            try:
                on_disk.add(load_json(rf).get("recordId"))
            except Exception:                                  # noqa: BLE001
                problems.append({"path": rel(rf), "issue": "记录不可解析"})
        for rid in sorted(x for x in listed - on_disk if x):
            problems.append({"path": rel(pdir), "issue": "清单有记录但文件不存在: %s" % rid})
        for rid in sorted(x for x in on_disk - listed if x):
            problems.append({"path": rel(pdir), "issue": "有记录文件但清单未登记: %s" % rid})

    # 分析完整性：失败运行该有根因的必须有（堵住静默漏分析），见 check_analysis
    problems += check_analysis(pdir, doc, day, stats)

    # 证据层：归档里引用的证据路径，正文要么在同一目录的 pipeline.evidence.json 里，
    # 要么（还没合并的老归档）还在磁盘上 —— 两处都没有才算缺失。
    # 引用写法是「相对路径 + 行号定位」：job_logs/x.log:L138 / case_logs/y.html:L1662
    # 行号只是定位指针，不是路径的一部分，校验前必须剥掉，否则会把全部引用误判为缺失。
    refs = {}
    for jf in sorted(pdir.rglob("*" + JSON_SUFFIX)):
        if JSON_SUFFIX != jf.suffix:
            continue
        if jf.name == pipeline_doc.EVIDENCE_NAME:
            continue          # 证据文档自身是正文，不是引用来源（其 _doc 里有散文路径）
        try:
            payload = load_json(jf)
        except Exception:                                       # noqa: BLE001
            continue
        for s in iter_strings(payload):
            if s.startswith(EVIDENCE_PREFIX):
                base, where = split_ref(s)
                refs.setdefault(base, set()).add(where)
    stats["evidenceRefs"] = len(refs)
    ev_entries = pipeline_doc.evidence_entries(pdir) if refs else {}
    for ref in sorted(refs):
        ent = ev_entries.get(ref)
        try:
            n_lines = int((ent or {}).get("lineCount") or len((ent or {}).get("lines") or []))
        except (TypeError, ValueError):
            n_lines = 0
        if n_lines > 0:                                        # 已内嵌：正文在 JSON 里
            over = sorted({ln for w in refs[ref] for ln in cite_lines(w) if ln > n_lines})
            if over:
                stats["evidenceMissing"] += 1
                problems.append({"path": rel(pdir),
                                 "issue": "证据行号超出总行数: %s 只有 %d 行，引用到第 %s 行"
                                          % (ref, n_lines, "、".join(str(x) for x in over))})
            continue
        if (pdir / ref).exists():                              # 未合并的老归档：正文还在磁盘
            continue
        stats["evidenceMissing"] += 1
        where = sorted(x for x in refs[ref] if x)
        problems.append({"path": rel(pdir),
                         "issue": "证据正文缺失: %s（%d 处引用%s；pipeline.evidence.json 与磁盘都没有）"
                                  % (ref, len(where) or 1,
                                     "，如 " + where[0] if where else "")})
    return problems, stats


def main():
    ap = argparse.ArgumentParser(description="out/archive 归档自检")
    ap.add_argument("--date", help="只校验某一天（yyyy-mm-dd）")
    ap.add_argument("--component", help="只校验某个开源组件")
    ap.add_argument("--json", help="把报告另存为 JSON（相对路径按仓库根解析）")
    args = ap.parse_args()

    problems = []
    stale = []
    tot = {"days": 0, "pipelines": 0, "records": 0, "evidenceRefs": 0, "evidenceMissing": 0,
           "analysisLeak": 0, "analysisExtra": 0, "analysisPending": 0}
    for date, day_dir in iter_archive_days():
        if args.date and date != args.date:
            continue
        tot["days"] += 1
        dj = day_dir / "_day.json"
        if not dj.exists():
            problems.append({"path": rel(day_dir), "issue": "缺少 _day.json"})
        else:
            try:
                load_json(dj)
            except Exception as exc:                           # noqa: BLE001
                problems.append({"path": rel(dj), "issue": "日汇总不可解析: %s" % exc})
        if not DATE_DIR_RE.match(day_dir.name):
            problems.append({"path": rel(day_dir), "issue": "日期目录命名不合规"})
        for comp, pipe, pdir in stale_pipeline_dirs(day_dir):
            if not args.component or comp == args.component:
                stale.append(dict(path=rel(pdir), date=date, component=comp, pipeline=pipe))
        for comp, pipe, pdir in iter_scoped_pipelines(day_dir):
            if args.component and comp != args.component:
                continue
            tot["pipelines"] += 1
            ps, stats = check_pipeline_dir(pdir)
            problems += ps
            for k in ("records", "evidenceRefs", "evidenceMissing",
                      "analysisLeak", "analysisExtra", "analysisPending"):
                tot[k] += stats[k]

    ok = not problems
    print("== 归档自检 ==")
    print("日目录 %d | 流水线目录 %d | 执行记录 %d 条 | 证据引用 %d 个（缺失 %d）"
          % (tot["days"], tot["pipelines"], tot["records"],
             tot["evidenceRefs"], tot["evidenceMissing"]))
    print("分析完整性: 漏分析 %d | 多分析 %d | 待分析未完成 %d（三类都必须为 0）"
          % (tot["analysisLeak"], tot["analysisExtra"], tot["analysisPending"]))
    if stale:
        print("注: %d 个目录不在当日 _day.json 口径内（旧版本/改名前残留），已跳过不计: %s"
              % (len(stale), ", ".join(s["path"] for s in stale[:5])
                 + ("…" if len(stale) > 5 else "")))
    print("结论: %s" % ("通过（结构与证据可逐条核对）" if ok else "发现 %d 个问题" % len(problems)))
    for p in problems[:30]:
        print("  !! %s -> %s" % (p["path"], p["issue"]))
    if len(problems) > 30:
        print("  ... 其余 %d 个问题见 JSON 报告" % (len(problems) - 30))

    if args.json:
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / args.json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"totals": tot, "ok": ok, "stale": stale,
                                   "problems": problems},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        print("报告: %s" % out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
