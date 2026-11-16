# -*- coding: utf-8 -*-
"""漏分析专项审计（只读）：把「运行状态为 FAILED/CANCELED」的全部记录，
按当日切片口径重算它是否影响当日指标，找出「本该分析却没进入分析链路」的记录。

判定（当日切片，取 _day.json 的 vaDetail/bsDetail）：
  aff_va = 流水线含 va 维度 且 当日版本不可用（vaDetail.availDays == 0）
  aff_bs = 流水线含 bs 维度 且 当日编译未全过（bsDetail.buildPassCount < buildCount）
           且 该次运行自身 bc>0 且 bpc<bc
  应分析 = aff_va or aff_bs
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import day_pipeline_scope, iter_archive_days  # noqa: E402


def main():
    rows = []
    for date, day_dir in iter_archive_days():
        day = json.loads((day_dir / "_day.json").read_text(encoding="utf-8"))
        lvl = {(e.get("component"), e.get("pipeline")): e for e in (day.get("pipelines") or [])}
        allowed = day_pipeline_scope(day_dir)
        for comp in sorted(p for p in day_dir.iterdir() if p.is_dir()):
            if comp.name.startswith("_"):
                continue
            for pipe in sorted(p for p in comp.iterdir() if p.is_dir()):
                if allowed is not None and (comp.name, pipe.name) not in allowed:
                    continue
                if not pipeline_doc.path_of(pipe).is_file():
                    continue
                e = lvl.get((comp.name, pipe.name)) or {}
                vd, bd = e.get("vaDetail") or {}, e.get("bsDetail") or {}
                dims = e.get("dims") or []
                d_va = vd.get("availDays")
                d_bc, d_bpc = bd.get("buildCount"), bd.get("buildPassCount")
                doc = pipeline_doc.load(pipe) or {}
                s2 = ((doc.get("steps") or {}).get("step_2_runs") or {})
                runs = {r.get("rid"): r for r in (s2.get("runHistory") or [])}
                for rec in doc.get("records") or []:
                    st = str(rec.get("status") or "").upper()
                    if st not in ("FAILED", "CANCELED"):
                        continue
                    cat = (rec.get("verdict") or {}).get("category") or "--"
                    an = (rec.get("analysis") or {}).get("status")
                    run = runs.get(rec.get("pipelineRunId")) or {}
                    bc, bpc = run.get("bc"), run.get("bpc")
                    aff_va = ("va" in dims) and d_va == 0
                    aff_bs = (("bs" in dims) and isinstance(d_bc, int) and isinstance(d_bpc, int)
                              and d_bc > 0 and d_bpc < d_bc
                              and isinstance(bc, int) and isinstance(bpc, int) and bc > 0 and bpc < bc)
                    should = aff_va or aff_bs
                    rows.append({
                        "date": date, "comp": comp.name, "pipe": pipe.name,
                        "bn": rec.get("buildNumber"), "st": st, "cat": cat, "an": an,
                        "where": "va+bs" if (aff_va and aff_bs) else "va" if aff_va else "bs" if aff_bs else "都不进",
                        "should": should, "dims": ",".join(dims),
                        "d_va": d_va, "d_bs": "%s/%s" % (d_bpc, d_bc), "bc": bc, "bpc": bpc,
                    })
    print("FAILED/CANCELED 记录共 %d 条" % len(rows))
    print("  归档分类分布:", dict(Counter(r["cat"] for r in rows)))
    print("  归属分布:", dict(Counter(r["where"] for r in rows)))
    print()
    miss = [r for r in rows if r["should"] and r["an"] != "done"]
    print("== 应分析但现状不是 done（真·漏分析 / 待补分析）: %d ==" % len(miss))
    for r in sorted(miss, key=lambda x: (x["date"], x["comp"], x["pipe"], x["bn"])):
        print("  %s %s/%s #%s cat=%s st=%s 归属=%s dims=%s 当日可用=%s 当日编译=%s 运行编译=%s/%s"
              % (r["date"], r["comp"], r["pipe"], r["bn"], r["cat"], r["an"], r["where"],
                 r["dims"], r["d_va"], r["d_bs"], r["bpc"], r["bc"]))
    print()
    over = [r for r in rows if (not r["should"]) and r["an"] == "done"]
    print("== 不影响当日指标却做了分析（多分析，页面会多显示）: %d ==" % len(over))
    for r in sorted(over, key=lambda x: (x["date"], x["comp"], x["pipe"], x["bn"])):
        print("  %s %s/%s #%s cat=%s 归属=%s dims=%s 当日可用=%s 当日编译=%s 运行编译=%s/%s"
              % (r["date"], r["comp"], r["pipe"], r["bn"], r["cat"], r["where"],
                 r["dims"], r["d_va"], r["d_bs"], r["bpc"], r["bc"]))
    print()
    dropped = [r for r in rows if r["cat"] == "success"]
    print("== 失败运行却被判「执行成功」（不进取证/分析链路，无证据）: %d ==" % len(dropped))
    print("  按流水线:", dict(Counter("%s/%s" % (r["comp"], r["pipe"]) for r in dropped)))
    print("  其中影响当日指标(真漏) :", sum(1 for r in dropped if r["should"]))


if __name__ == "__main__":
    main()
