# -*- coding: utf-8 -*-
"""诊断：导出 MindCluster / boostkit 各流水线跨日运行与可用度明细。"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARCH = os.path.join(ROOT, "out", "archive", "2026", "2026-11")


def load(p):
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    comp = sys.argv[1] if len(sys.argv) > 1 else "MindCluster"
    days = sorted(os.listdir(ARCH))
    pipes = {}
    for d in days:
        base = os.path.join(ARCH, d, comp)
        if not os.path.isdir(base):
            continue
        for p in sorted(os.listdir(base)):
            pj = os.path.join(base, p, "pipeline.json")
            if not os.path.exists(pj):
                continue
            j = load(pj)
            key = j.get("key") or p
            entry = pipes.setdefault(key, {"name": j.get("pipelineName") or p,
                                           "platform": j.get("platform"),
                                           "dims": None, "days": {}})
            for r in j.get("records", []):
                entry["days"].setdefault(d, []).append({
                    "rn": r.get("buildNumber"), "status": r.get("status"),
                    "start": r.get("startedAt"), "end": r.get("endedAt"),
                    "iva": ((r.get("light") or {}).get("vaRate")),
                    "track": ((r.get("light") or {}).get("track")),
                })
    for d in days:
        pj = os.path.join(ARCH, d, "_day.json")
        j = load(pj)
        for pl in j.get("pipelines", []):
            if pl.get("component") != comp:
                continue
            e = pipes.setdefault(pl.get("key"), {"name": pl.get("pipelineName"),
                                                 "platform": pl.get("platform"),
                                                 "dims": pl.get("dims"), "days": {}})
            e["dims"] = pl.get("dims")
    print("==== %s ====" % comp)
    for key, e in pipes.items():
        print("\n## %s | %s | dims=%s" % (key, e["name"], e["dims"]))
        for d in days:
            rs = e["days"].get(d)
            if rs is None:
                continue
            for r in rs:
                print("   %s rn=%-5s %-10s %s ~ %s va=%s track=%s"
                      % (d, r["rn"], r["status"], r["start"], r["end"], r["iva"], r["track"]))


if __name__ == "__main__":
    main()
