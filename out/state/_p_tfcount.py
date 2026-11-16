# -*- coding: utf-8 -*-
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    day = sys.argv[1]
    comp = sys.argv[2]
    pipe = sys.argv[3]
    base = AR / day[:4] / day[:7] / day / comp / pipe
    ev = load(base / "pipeline.evidence.json")
    files = ev.get("files") or {}
    pats = {
        "hcclCommInitRootInfoConfig": re.compile(r"hcclCommInitRootInfoConfig"),
        "ERR02200_dist_hccl": re.compile(r"ERR02200 DIST call hccl api"),
        "topkNum_must_equal": re.compile(r"topkNum \(\d+\) must equal probs dimension"),
        "accuracy_not_passed": re.compile(r"accuracy not passed"),
        "run_failed_opp": re.compile(r"run opp failed"),
        "dist_run_failed": re.compile(r"dist run_failed"),
    }
    counts = {k: 0 for k in pats}
    per_case = {}
    for name, body in files.items():
        if not name.startswith("case_logs/"):
            continue
        lines = body.get("lines") if isinstance(body, dict) else body
        txt = "\n".join(str(x) for x in (lines or []))
        hit = [k for k, rx in pats.items() if rx.search(txt)]
        per_case[name] = hit
        for h in hit:
            counts[h] += 1
    print("== per-pattern case-file hit counts (%s #%s) ==" % (comp, pipe))
    for k, v in counts.items():
        print("  %-28s %d" % (k, v))
    print("== per case file ==")
    for n in sorted(per_case):
        print("  %s -> %s" % (n, ",".join(per_case[n]) or "-"))

main()
