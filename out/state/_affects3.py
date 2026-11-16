# -*- coding: utf-8 -*-
"""离线核对「记录级维度影响」判定（只读）。**当日值**取 _day.json 的 vaDetail/bsDetail。

口径（用户确认）：不影响当日该维度指标的运行，不进对应页面。
  dim=va ：当日版本不可用（vaDetail.availDays==0，当日无 iva=true 的运行）→ 该日失败运行进版本可用度页；
           当日版本可用（availDays==1）→ 当日的失败数据一律不展示。
  dim=bs ：当日编译未全过（bsDetail.buildPassCount < buildCount）且该次运行自身 bc>0 且 bpc<bc
           → 进构建成功率页；编译通过 / 没编译（github）→ 不展示。
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
                vd = e.get("vaDetail") or {}
                bd = e.get("bsDetail") or {}
                dims = e.get("dims") or []
                d_va = vd.get("availDays")
                d_bc, d_bpc = bd.get("buildCount"), bd.get("buildPassCount")
                doc = pipeline_doc.load(pipe) or {}
                s2 = ((doc.get("steps") or {}).get("step_2_runs") or {})
                runs = {r.get("rid"): r for r in (s2.get("runHistory") or [])}
                for rec in doc.get("records") or []:
                    cat = (rec.get("verdict") or {}).get("category") or "--"
                    if cat == "success":
                        continue
                    run = runs.get(rec.get("pipelineRunId")) or {}
                    bc, bpc = run.get("bc"), run.get("bpc")
                    aff_va = ("va" in dims) and d_va == 0
                    aff_bs = (("bs" in dims) and isinstance(d_bc, int) and isinstance(d_bpc, int)
                              and d_bc > 0 and d_bpc < d_bc
                              and bc is not None and bpc is not None and bc > 0 and bpc < bc)
                    rows.append({
                        "date": date, "comp": comp.name, "pipe": pipe.name,
                        "bn": rec.get("buildNumber"), "cat": cat,
                        "an": (rec.get("analysis") or {}).get("status"),
                        "dims": ",".join(dims), "d_va": d_va, "d_bc": d_bc, "d_bpc": d_bpc,
                        "bc": bc, "bpc": bpc,
                        "where": "va+bs" if (aff_va and aff_bs) else "va" if aff_va else "bs" if aff_bs else "都不进",
                    })
    c = Counter(r["where"] for r in rows)
    print("失败/取消记录共 %d 条，按当日切片口径归属：%s" % (len(rows), dict(c)))
    print()
    print("%-11s %-30s %-6s %-15s %-6s %-8s %-7s %-9s %-5s %-5s %s"
          % ("日期", "组件/流水线", "构建号", "归档分类", "已分析", "dims", "当日可用", "当日编译", "bc", "bpc", "归属"))
    for r in sorted(rows, key=lambda x: (x["date"], x["comp"], x["pipe"], x["bn"])):
        print("%-11s %-30s %-6s %-15s %-6s %-8s %-7s %-9s %-5s %-5s %s"
              % (r["date"], (r["comp"] + "/" + r["pipe"])[:30], r["bn"], r["cat"], r["an"],
                 r["dims"], r["d_va"], "%s/%s" % (r["d_bpc"], r["d_bc"]), r["bc"], r["bpc"], r["where"]))
    print()
    print("== 与现有 analysis.status 是否一致（应分析 ⟺ done）==")
    bad = [r for r in rows if (r["where"] != "都不进") != (r["an"] == "done")]
    print("  不一致 %d 条：" % len(bad))
    for r in sorted(bad, key=lambda x: (x["date"], x["comp"], x["pipe"])):
        print("    %s %s/%s #%s cat=%s 归属=%s 当日可用=%s 当日编译=%s/%s 运行bc=%s/bpc=%s 现状=%s"
              % (r["date"], r["comp"], r["pipe"], r["bn"], r["cat"], r["where"],
                 r["d_va"], r["d_bpc"], r["d_bc"], r["bc"], r["bpc"], r["an"]))


if __name__ == "__main__":
    main()
