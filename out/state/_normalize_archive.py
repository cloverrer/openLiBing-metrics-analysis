# -*- coding: utf-8 -*-
"""【一次性】把已有 out/archive/ 按 pipelineId 归并，清掉不再采集的残留，并播种身份注册表。

背景（用户反馈「openUBMC 流水线条数不对」）:
  旧版短名按「当次采集集合」现算，集合一变短名就变 —— 同一条 pipelineId
  (440c2100…, Nightly-CI-Version-pipeline_openUBMC) 在 11-10/11/12 落成目录 openUBMC、
  在 11-13 落成 openUBMC~f35034；首页按 key 做区间 union 就把 1 条算成 2 条。
  另外 MindCluster 的 AgentSDK / Agentsdk 只差大小写，在 Windows 上共用同一个目录，
  两条流水线互相覆盖；VisionSDK / RAGSDK 已从看板消失但残留着 0 运行的空壳目录。

本脚本只改归档层（不重新采集、不重新生成原始数据）:
  1) 扫描各归档日的流水线目录，读出真实身份 (product, pipelineId, pipelineName)；
  2) 用 lib/pipeline_ids.assign_short_names 算出**跨日唯一且稳定**的短名
     （历史目录名优先保留，尽量不产生改名）；
  3) 目录名与规范短名不一致的改名（含仅大小写不同的改名）；
  4) 重写各日 _day.json：补 pipelineId、按规范短名更新 pipeline/key/path，
     丢弃「已不在采集清单且区间内 0 运行」的残留条目；同期把计数重算回写；
  5) 补一份零运行流水线的占位目录（目录被同名流水线覆盖而丢的那条）；
  6) 播种 out/archive/_pipelines.json 身份注册表，供第 1 步后续沿用。
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import (ARCHIVE_ROOT, PIPELINES_NAME, doc, iter_archive_days,  # noqa: E402
                       iter_archive_pipelines, rel)
from lib.pipeline_ids import assign_short_names  # noqa: E402

WORK = ROOT / "out" / "work"


def read_identity(pdir):
    """从 pipeline.json 读流水线真实身份：(product, pipelineId, pipelineName, platform)。"""
    d = pipeline_doc.load(pdir)
    if not d:
        return None
    pl = ((d.get("steps") or {}).get("step_1_lights") or {}).get("pipeline") or {}
    if not pl.get("pipelineId"):
        return None
    return (pl.get("product") or pdir.parent.name, str(pl.get("pipelineId")),
            pl.get("pipelineName") or "", pl.get("platform") or "")


def main():
    cur = json.loads((WORK / "step_1_bad_pipelines.json").read_text(encoding="utf-8"))
    active = collections.defaultdict(dict)           # product -> {pid: name}
    for b in cur.get("pipelines") or []:
        active[b["product"]][str(b["pipelineId"])] = b.get("pipelineName") or ""
    name_to_pid = collections.defaultdict(dict)      # (product, name) -> pid
    for prod, ids in active.items():
        for pid, nm in ids.items():
            name_to_pid[prod][nm] = pid

    # ---- 1) 扫描归档，建立「pid -> 出现过的目录名」与目录清单
    seen_names = collections.defaultdict(dict)        # product -> {pid: [dir 名, ...]}
    ident_meta = {}                                   # pid -> (pipelineName, platform)
    day_dirs = []                                     # (date, day_dir, [(comp, pdir_name, pdir)])
    for date, day_dir in iter_archive_days():
        items = []
        for comp, pname_dir, pdir in iter_archive_pipelines(day_dir):
            items.append((comp, pname_dir, pdir))
            ident = read_identity(pdir)
            if ident:
                prod, pid = ident[0], ident[1]
                seen_names[prod].setdefault(pid, [])
                if pname_dir not in seen_names[prod][pid]:
                    seen_names[prod][pid].append(pname_dir)
                ident_meta.setdefault(pid, (ident[2], ident[3]))
        day_dirs.append((date, day_dir, items))

    # ---- 2) 历史目录名优先做 sticky（按日期升序 = 先出现者优先），再算规范短名
    canonical, sticky_all = {}, {}
    for prod in sorted(set(active) | set(seen_names)):
        used, sticky = set(), {}
        for pid, names in seen_names.get(prod, {}).items():
            for nm in names:
                if nm.lower() not in used:
                    sticky[pid] = nm
                    used.add(nm.lower())
                    break
        pairs = [(pid, nm) for pid, nm in active.get(prod, {}).items()]
        pairs += [(pid, names[0]) for pid, names in seen_names.get(prod, {}).items()
                  if all(str(p) != pid for p in active.get(prod, {}))]
        canonical[prod] = assign_short_names(pairs, sticky)
        sticky_all[prod] = sticky

    renames, created = [], []
    for date, day_dir, items in day_dirs:
        for comp, dirname, pdir in items:
            ident = read_identity(pdir)
            if not ident:
                continue
            prod, pid, pname, platform = ident
            want = canonical.get(prod, {}).get(pid)
            if want and want != dirname:
                renames.append((date, comp, dirname, want, pid, pname))
    print("计划改名 %d 个目录：" % len(renames))
    for r in renames:
        print("   %s %s: %s -> %s" % (r[0], r[1], r[2], r[3]))

    # ---- 3) 执行改名（先改成临时名，避开 A->B / B->A 与仅大小写差异的冲突）
    for date, comp, old, new, pid, pname in renames:
        comp_dir = ARCHIVE_ROOT / date[:4] / date[:7] / date / comp
        src, dst = comp_dir / old, comp_dir / new
        tmp = comp_dir / ("__tmp__%s" % abs(hash((old, new))))
        src.rename(tmp)
        if dst.exists():
            raise RuntimeError("改名目标已存在: %s" % dst)
        tmp.rename(dst)
    print("改名完成")

    # ---- 4) 重写各日 _day.json
    total_drop = 0
    for date, day_dir, items in day_dirs:
        dj = day_dir / "_day.json"
        if not dj.is_file():
            continue
        day = json.loads(dj.read_text(encoding="utf-8"))
        keep = []
        for e in day.get("pipelines") or []:
            prod = e.get("component")
            enm = e.get("pipelineName")
            # 目录里那条流水线的真实身份（按 path 定位，避免被同名条目蒙混）
            pdir = ROOT / "out" / e.get("path", "")
            ident = read_identity(pdir) if pdir.is_dir() else None
            if ident and (not enm or ident[2] == enm):
                pid = ident[1]
            else:
                # 条目是「同目录被同名流水线覆盖」产生的幻影：按 pipelineName 找它的真实 id
                pid = name_to_pid.get(prod, {}).get(enm)
                if not pid:
                    print("  !! 无法定位流水线身份，丢弃条目: %s %s/%s"
                          % (date, prod, e.get("pipeline")))
                    total_drop += 1
                    continue
            e = dict(e, pipelineId=pid)
            if pid not in active.get(prod, {}) and not e.get("runsInPeriod"):
                total_drop += 1                     # 已不在采集清单且 0 运行：残留，丢弃
                continue
            want = canonical.get(prod, {}).get(pid)
            if want:
                e["pipeline"] = want
                e["key"] = "%s|%s" % (prod, want)
                base = "archive/%s/%s/%s/%s/%s" % (date[:4], date[:7], date, prod, want)
                e["path"] = base
                e["manifest"] = base + "/pipeline.json"
                e["file"] = base + "/pipeline.json"
            keep.append(e)
        day["pipelines"] = keep
        cats = collections.Counter()
        for p in keep:
            for k, v in (p.get("byCategory") or {}).items():
                cats[k] += v
        day["counts"] = {
            "components": len({p["component"] for p in keep}),
            "pipelines": len(keep),
            "records": sum(p.get("records") or 0 for p in keep),
            "tasks": sum(p.get("tasks") or 0 for p in keep),
            "cases": sum(p.get("cases") or 0 for p in keep),
            "errorMessages": sum(p.get("errorMessages") or 0 for p in keep),
            "evidenceFiles": sum(p.get("evidenceFiles") or 0 for p in keep),
            "byCategory": dict(cats),
        }
        day["_doc"]["criteria"] = ("当日（按执行结束时间）全部被点灯流水线的执行记录索引；"
                                   "流水线身份按 pipelineId 归并（短名跨日稳定）")
        dj.write_text(json.dumps(day, ensure_ascii=False, indent=1), encoding="utf-8")
        print("%s: 保留 %d 条流水线条目" % (date, len(keep)))
    print("丢弃残留条目 %d 条" % total_drop)

    # ---- 5) 补零运行流水线的占位目录（目录被同名流水线覆盖而丢的那条）
    for date, day_dir, items in day_dirs:
        dj = day_dir / "_day.json"
        if not dj.is_file():
            continue
        day = json.loads(dj.read_text(encoding="utf-8"))
        have = {}
        for comp, pname_dir, pdir in iter_archive_pipelines(day_dir):
            ident = read_identity(pdir)
            if ident:
                have[(comp, ident[1])] = pname_dir
        for e in day.get("pipelines") or []:
            prod, pid = e.get("component"), e.get("pipelineId")
            if not prod or not pid or (prod, pid) in have:
                continue
            want = canonical.get(prod, {}).get(pid)
            if not want:
                continue
            pdir = day_dir / prod / want
            steps = {}
            for step in ("step_1_lights", "step_2_runs", "step_3_tasks", "step_4_cases",
                         "step_5_logs", "step_5b_subtasks", "step_5c_github", "step_6_records"):
                dcm = doc(step)
                steps[step] = {"_doc": dict(dcm, component=prod, pipeline=want, date=date)}
            steps["step_1_lights"]["pipeline"] = {
                "key": e.get("key"), "product": prod, "pipelineName": e.get("pipelineName"),
                "pipelineShortName": want, "pipelineId": pid,
                "platform": e.get("platform"), "dims": e.get("dims") or [],
                "rateRule": "runs", "recompute": True, "scheduledOnly": False,
            }
            steps["step_1_lights"]["selection"] = {
                "inBadPipelines": True, "dims": e.get("dims") or [], "rateRule": "runs",
                "reason": "补录占位：该流水线与另一条同名流水线（仅大小写不同）在 Windows 上"
                          "共用同一个归档目录，原占位文件被覆盖，此处按身份补回",
            }
            payload = pipeline_doc.assemble({
                "_doc": doc("step_7_archive", title="流水线归档（单文件）",
                            component=prod, pipeline=want, date=date),
                "date": date, "component": prod, "pipeline": want,
                "pipelineName": e.get("pipelineName"), "platform": e.get("platform"),
                "key": e.get("key"),
                "dateBasis": {"field": "pipelineRunEndtime", "rule": "", "value": date, "runs": []},
                "counts": {"records": 0, "tasks": 0, "cases": 0, "errorMessages": 0},
                "evidence": {"files": 0, "bytes": 0, "lines": 0, "missing": []},
                "source": {"workDir": "out/work", "generatedAt": day.get("generatedAt") or "",
                           "note": "由 out/state/_normalize_archive.py 按身份补录"},
                "steps": [{"step": s} for s in steps],
            }, steps, [])
            pdir.mkdir(parents=True, exist_ok=True)
            pipeline_doc.save(pdir, payload)
            created.append((date, prod, want, pid))
    print("补录占位目录 %d 个：%s" % (len(created), created))

    # ---- 6) 重建 _index.json 与播种身份注册表
    days = []
    for date, day_dir in iter_archive_days():
        dj = day_dir / "_day.json"
        counts, pipes = {}, []
        if dj.is_file():
            d = json.loads(dj.read_text(encoding="utf-8"))
            counts, pipes = d.get("counts") or {}, d.get("pipelines") or []
        days.append({"date": date, "path": rel(day_dir),
                     "components": counts.get("components") or len({p["component"] for p in pipes}),
                     "pipelines": counts.get("pipelines") or len(pipes),
                     "records": counts.get("records") or 0,
                     "tasks": counts.get("tasks") or 0,
                     "cases": counts.get("cases") or 0,
                     "errorMessages": counts.get("errorMessages") or 0})
    idx_p = ARCHIVE_ROOT / "_index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.is_file() else {}
    idx["days"] = days
    idx["dayCount"] = len(days)
    idx["_doc"]["criteria"] = ("按执行结束时间分层归档的日期清单，逐层可查；"
                               "流水线身份按 pipelineId 归并（短名跨日稳定）")
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")

    reg = {}
    for prod in sorted(set(active) | set(seen_names)):
        reg[prod] = {}
        for pid, nm in active.get(prod, {}).items():
            reg[prod][pid] = {"short": canonical[prod][pid], "pipelineName": nm,
                              "platform": "", "firstSeen": "", "lastSeen": ""}
        for pid, names in seen_names.get(prod, {}).items():
            if pid in reg[prod]:
                continue
            reg[prod][pid] = {"short": sticky.get(pid) or canonical[prod].get(pid),
                              "pipelineName": "", "platform": "", "firstSeen": "", "lastSeen": ""}
    (ARCHIVE_ROOT / PIPELINES_NAME).write_text(json.dumps(
        {"_doc": {"step": "step_1_nightly", "title": "流水线身份注册表",
                  "criteria": "每个开源组件下 pipelineId -> 唯一短名的持久映射"
                              "（跨次运行累积、只增不删）"},
         "generatedAt": "", "productCount": len(reg),
         "pipelineCount": sum(len(v) for v in reg.values()),
         "products": reg}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("注册表 -> out/archive/%s（%d 个产品 / %d 条流水线）"
          % (PIPELINES_NAME, len(reg), sum(len(v) for v in reg.values())))


if __name__ == "__main__":
    main()
