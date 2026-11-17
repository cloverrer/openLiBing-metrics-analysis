# -*- coding: utf-8 -*-
"""查看一条社区 pipeline.json 的关键字段，确认重建 _day.json 条目所需信息齐全。"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    path = sys.argv[1]
    j = json.load(io.open(os.path.join(ROOT, path), encoding="utf-8"))
    print("top:", {k: j.get(k) for k in ("date", "component", "pipeline", "pipelineName",
                                         "platform", "key", "channel", "schema")})
    print("counts:", j.get("counts"))
    st = j.get("steps") or {}
    print("steps:", list(st.keys()))
    s1 = st.get("step_1_lights") or {}
    print("s1 keys:", list(s1.keys()))
    print("s1.pipeline:", s1.get("pipeline"))
    print("s1.selection:", s1.get("selection"))
    rh = (st.get("step_2_runs") or {}).get("runHistory")
    print("runHistory:", json.dumps(rh, ensure_ascii=False)[:600])
    recs = j.get("records") or []
    print("records:", len(recs))
    if recs:
        print("rec0 keys:", sorted(recs[0].keys()))


if __name__ == "__main__":
    main()
