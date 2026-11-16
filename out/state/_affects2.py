# -*- coding: utf-8 -*-
"""离线核对「记录级维度影响」判定（只读）。**当日值**取 _day.json 的 vaRate/bsRate。

口径（用户确认）：不影响当日该维度指标的运行，不进对应页面。
  dim=va ：当日该流水线版本不可用（当日 vaRate<1）→ 该日失败数据进版本可用度页；
           当日版本可用（=1）→ 当日的失败数据一律不展示。
  dim=bs ：该次运行编译未通过（bc>0 且 bpc<bc）→ 进构建成功率页；
           编译通过 / 没编译（github、bc=0）→ 不展示。
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import day_pipeline_scope, iter_archive_days  # noqa: E402


def num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


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
                day_va, day_bs = num(e.get("vaRate")), num(e.get("bsRate"))
                dims = e.get("dims") or []
                doc = pipeline_doc.load(pipe) or {}
                s2 = ((doc.get("steps") or {}).get("step_2_runs") or {})
                runs = {r.get("rid"): r for r in (s2.get("runHistory") or [])}
                for rec in doc.get("records") or []:
                    cat = (rec.get("verdict") or {}).get("category") or "--"
                    if cat == "success":
                        continue
                    run = runs.get(rec.get("pipelineRunId")) or {}
                    bc, bpc = run.get("bc"), run.get("bpc")
                    aff_va = ("va" in dims) and day_va is not None and day_va < 1
                    aff_bs = ("bs" in dims) and bc is not None and bc > 0 and bpc is not None and bpc < bc
                    rows.append({
                        "date": date, "comp": comp.name, "pipe": pipe.name,
                        "bn": rec.get("buildNumber"), "cat": cat,
                        "an": (rec.get("analysis") or {}).get("status"),
                        "dims": ",".join(dims), "day_va": day_va, "day_bs": day_bs,
                        "bc": bc, "bpc": bpc,
                        "where": "va+bs" if (aff_va and aff_bs) else "va" if aff_va else "bs" if aff_bs else "都不进",
                    })
    c = Counter(r["where"] for r in rows)
    print("失败/取消记录共 %d 条，按当日口径归属：%s" % (len(rows), dict(c)))
    print()
    print("%-11s %-30s %-6s %-15s %-6s %-8s %-7s %-7s %-5s %-5s %s"
          % ("日期", "组件/流水线", "构建号", "归档分类", "已分析", "dims", "当日VA", "当日BS", "bc", "bpc", "归属"))
    for r in sorted(rows, key=lambda x: (x["date"], x["comp"], x["pipe"], x["bn"])):
        print("%-11s %-30s %-6s %-15s %-6s %-8s %-7s %-7s %-5s %-5s %s"
              % (r["date"], (r["comp"] + "/" + r["pipe"])[:30], r["bn"], r["cat"], r["an"],
                 r["dims"], r["day_va"], r["day_bs"], r["bc"], r["bpc"], r["where"]))
    print()
    print("== 与现有 analysis.status 是否一致 ==")
    bad = [r for r in rows if (r["where"] != "都不进") != (r["an"] == "done")]
    print("  不一致 %d 条：" % len(bad))
    for r in sorted(bad, key=lambda x: (x["date"], x["comp"], x["pipe"])):
        want = "应分析(done)" if r["where"] != "都不进" else "应豁免(na)"
        print("    %s %s/%s #%s cat=%s 归属=%s 当日VA=%s 当日BS=%s bc=%s bpc=%s 现状=%s → %s"
              % (r["date"], r["comp"], r["pipe"], r["bn"], r["cat"], r["where"],
                 r["day_va"], r["day_bs"], r["bc"], r["bpc"], r["an"], want))


if __name__ == "__main__":
    main()
