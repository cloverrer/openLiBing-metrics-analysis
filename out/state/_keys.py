# -*- coding: utf-8 -*-
"""只读：输出指定记录的顶层键与关键子对象键（结构探察）。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AR = ROOT / "out" / "archive"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    day, want = sys.argv[1], sys.argv[2].replace("/", "|")
    outp = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(__file__).parent / "_keys.txt"
    day_dir = AR / day[:4] / day[:7] / day
    out = []
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        for pipe in sorted(comp.iterdir()):
            pj = pipe / "pipeline.json"
            if not pj.is_file():
                continue
            doc = load(pj)
            out.append("PIPE=%s topkeys=%s" % (pipe.name, sorted(doc.keys())))
            for rec in doc.get("records") or []:
                if str(rec.get("recordId")).replace("/", "|") != want:
                    continue
                out.append("REC keys=%s" % sorted(rec.keys()))
                for k, v in rec.items():
                    if isinstance(v, dict):
                        out.append("  %s(dict).keys=%s" % (k, sorted(v.keys())))
                    elif isinstance(v, list):
                        out.append("  %s(list) len=%d" % (k, len(v)))
                        if v and isinstance(v[0], dict):
                            out.append("    [0].keys=%s" % sorted(v[0].keys()))
                            out.append("    [0]=%s" % json.dumps(v[0], ensure_ascii=False)[:1500])
                    else:
                        out.append("  %s=%s" % (k, str(v)[:200]))
                    if k == "githubMeta":
                        out.append("    githubMeta=%s" % json.dumps(v, ensure_ascii=False)[:4000])
    outp.write_text("\n".join(out) + "\n", encoding="utf-8")
    sys.stdout.write("wrote -> %s\n" % outp)


main()
