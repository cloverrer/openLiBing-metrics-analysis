# -*- coding: utf-8 -*-
"""离线核对「记录级维度影响」判定（只读，不改归档）。

口径（用户确认）：
  数据都是根据指标来的 —— 不影响当日该维度指标的运行，不进对应页面。
  dim=bs ：该次运行编译未通过（bc>0 且 bpc<bc）才影响编译成功率 → 才在构建成功率页展示；
           编译通过 / 没编译（github、bc=0）都不展示。
  dim=va ：当日该流水线版本不可用（versionAvailabilityRate<1）才影响版本可用度 → 才在版本可用度页展示；
           当日版本可用（=1）时，当日失败数据一律不展示。

输出：每条失败/取消记录在 dim=va / dim=bs 上的归属（va / bs / 都不进）。
"""
import json
import sys
from collections import Counter, defaultdict
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
        allowed = day_pipeline_scope(day_dir)
        for comp in sorted(p for p in day_dir.iterdir() if p.is_dir()):
            if comp.name.startswith("_"):
                continue
            for pipe in sorted(p for p in comp.iterdir() if p.is_dir()):
                if allowed is not None and (comp.name, pipe.name) not in allowed:
                    continue
                if not pipeline_doc.path_of(pipe).is_file():
                    continue
                doc = pipeline_doc.load(pipe) or {}
                s2 = ((doc.get("steps") or {}).get("step_2_runs") or {})
                runs = {r.get("rid"): r for r in (s2.get("runHistory") or [])}
                for i, rec in enumerate(doc.get("records") or []):
                    v = rec.get("verdict") or {}
                    cat = v.get("category") or "--"
                    if cat == "success":
                        continue                       # 成功运行不参与本核对
                    lt = rec.get("light") or {}
                    dims = lt.get("dims") or []
                    day_va = num(lt.get("vaRate"))
                    run = runs.get(rec.get("pipelineRunId")) or {}
                    bc, bpc, iva = run.get("bc"), run.get("bpc"), run.get("iva")
                    aff_va = ("va" in dims) and day_va is not None and day_va < 1
                    aff_bs = ("bs" in dims) and bc is not None and bc > 0 and bpc is not None and bpc < bc
                    rows.append({
                        "date": date, "comp": comp.name, "pipe": pipe.name,
                        "bn": rec.get("buildNumber"), "cat": cat, "an": (rec.get("analysis") or {}).get("status"),
                        "dims": dims, "day_va": day_va, "day_bs": num(lt.get("bsRate")),
                        "bc": bc, "bpc": bpc, "iva": iva,
                        "aff_va": aff_va, "aff_bs": aff_bs,
                        "where": "va+bs" if (aff_va and aff_bs) else "va" if aff_va else "bs" if aff_bs else "都不进",
                    })
    c = Counter(r["where"] for r in rows)
    print("失败/取消记录共 %d 条，按维度归属：%s" % (len(rows), dict(c)))
    print()
    print("%-11s %-30s %-6s %-15s %-9s %-4s %-9s %-5s %-5s %-5s %s"
          % ("日期", "组件/流水线", "构建号", "归档分类", "已分析", "dims", "当日VA", "bc", "bpc", "iva", "归属"))
    for r in sorted(rows, key=lambda x: (x["date"], x["comp"], x["pipe"], x["bn"])):
        print("%-11s %-30s %-6s %-15s %-9s %-4s %-9s %-5s %-5s %-5s %s"
              % (r["date"], (r["comp"] + "/" + r["pipe"])[:30], r["bn"], r["cat"], r["an"],
                 ",".join(r["dims"]), r["day_va"], r["bc"], r["bpc"], r["iva"], r["where"]))
    print()
    print("== 按归属抽样核对 ==")
    for w in ("va+bs", "va", "bs", "都不进"):
        sel = [r for r in rows if r["where"] == w]
        print("  %-6s %d 条" % (w, len(sel)))
    print()
    print("== 会从页面上消失（都不进）的记录 ==")
    for r in sorted(rows, key=lambda x: (x["date"], x["comp"], x["pipe"])):
        if r["where"] != "都不进":
            continue
        print("  %s %s/%s #%s  cat=%s  当日VA=%s 当日BS=%s  bc=%s bpc=%s iva=%s  analysis=%s"
              % (r["date"], r["comp"], r["pipe"], r["bn"], r["cat"],
                 r["day_va"], r["day_bs"], r["bc"], r["bpc"], r["iva"], r["an"]))


if __name__ == "__main__":
    main()
