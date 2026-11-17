# -*- coding: utf-8 -*-
"""查 N2 原始 dash：某组件各流水线在区间内的全部原始记录（含无结束时间的进行中运行）。"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "out", "work", "step_2_dash_raw.json")


def main():
    needle = sys.argv[1]
    d = json.load(io.open(RAW, encoding="utf-8"))
    for key, resp in d.items():
        if needle not in key:
            continue
        recs = ((resp or {}).get("data") or {}).get("records") or []
        print("### %s  code=%s  records=%d" % (key, (resp or {}).get("code"), len(recs)))
        for r in recs:
            print("   rn=%s status=%s start=%s end=%s iva=%s bc=%s bpc=%s cpr=%s" % (
                r.get("pipelineRunNumber"), r.get("pipelineStatus"),
                r.get("pipelineRunStarttime"), r.get("pipelineRunEndtime"),
                r.get("isVersionAvailable"), r.get("buildCount"),
                r.get("buildPassCount"), r.get("casePassRate")))


if __name__ == "__main__":
    main()
