# -*- coding: utf-8 -*-
"""只读探针：按签名对每条 pending 记录的失败用例日志分类计数。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day = sys.argv[1]
    want = sys.argv[2] if len(sys.argv) > 2 else ""
    outp = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    sigs = {
        "HCCL": r"hcclCommInitRootInfoConfig",
        "tiling": r"must equal probs dimension",
        "dtype": r"AclNN_Parameter_Error",
        "msprof": r"COMPUTE_TASK_INFO run",
    }
    buf = []
    P = lambda s: buf.append(s)  # noqa: E731
    day_dir = AR / day[:4] / day[:7] / day
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        if want and want.lower() not in comp.name.lower():
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            evf = pipe / "pipeline.evidence.json"
            files = (load(evf).get("files") or {}) if evf.is_file() else {}
            for rec in doc.get("records") or []:
                if (rec.get("analysis") or {}).get("status") != "pending":
                    continue
                logs = set()
                for t in rec.get("tasks") or []:
                    for c in t.get("cases") or []:
                        if str(c.get("state") or "").lower() in ("failed", "fail", "error") and c.get("localLog"):
                            logs.add(str(c["localLog"]))
                agg = {k: [] for k in sigs}
                other = []
                for lp in sorted(logs):
                    ent = files.get(lp)
                    if not ent:
                        continue
                    text = "\n".join(str(x) for x in (ent.get("lines") or []))
                    hit = False
                    for k, pat in sigs.items():
                        if re.search(pat, text):
                            agg[k].append(lp)
                            hit = True
                    if not hit:
                        other.append(lp)
                P("RID=%s  failCases=%d" % (rec.get("recordId"), len(logs)))
                for k in sigs:
                    P("   %-8s %d  %s" % (k, len(agg[k]), ",".join(x.split("/")[-1] for x in agg[k])))
                if other:
                    P("   other    %d  %s" % (len(other), ",".join(x.split("/")[-1] for x in other)))
    text = "\n".join(buf) + "\n"
    if outp:
        outp.write_text(text, encoding="utf-8")
        sys.stdout.write("written %d lines -> %s\n" % (len(buf), outp))
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))


main()
