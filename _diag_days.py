# -*- coding: utf-8 -*-
"""按日列出失败/取消记录的归属与取证/分析状态，定位漏分析模式。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.dim_affects import affects_of, day_avail_of  # noqa: E402
from lib.paths import day_pipeline_scope, iter_archive_days  # noqa: E402

FAIL = {"FAILED", "CANCELED", "CANCELLED"}
for d, ddir in iter_archive_days():
    scope = day_pipeline_scope(ddir)
    n_fail = n_aff = n_ev = 0
    rows = []
    for comp in sorted(ddir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            if not pipe.is_dir():
                continue
            if scope is not None and (comp.name, pipe.name) not in scope:
                continue
            doc = pipeline_doc.load(pipe) or {}
            steps = doc.get("steps") or {}
            dims = ((steps.get("step_1_lights") or {}).get("pipeline") or {}).get("dims") or []
            rh = (steps.get("step_2_runs") or {}).get("runHistory") or []
            da = day_avail_of(rh, d)
            rb = {str(h.get("rn")): h for h in rh}
            for r in doc.get("records") or []:
                if str(r.get("status") or "").upper() not in FAIL:
                    continue
                n_fail += 1
                run = rb.get(str(r.get("buildNumber")))
                aff = affects_of(dims, da, run)
                has_ev = bool(((r.get("evidence") or {}).get("files")) or
                              (r.get("tasks") or []))
                an = (r.get("analysis") or {}).get("status")
                if aff:
                    n_aff += 1
                if has_ev:
                    n_ev += 1
                if aff and an != "done":
                    rows.append("   LEAK %s/%s#%s aff=%s status=%s ev=%s" %
                                (comp.name, pipe.name, r.get("buildNumber"),
                                 "/".join(aff), an, has_ev))
    print("== %s  失败/取消 %d | 影响指标 %d | 有证据 %d" % (d, n_fail, n_aff, n_ev))
    for x in rows:
        print(x)
