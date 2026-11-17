# -*- coding: utf-8 -*-
"""批量摘要 23 条待分析记录的关键字段，便于逐条定性。只读。"""
import json
import builtins
from pathlib import Path

ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
OUT = open(ROOT / "out/state/_dump16.txt", "w", encoding="utf-8")


def print(*a, **k):  # noqa: A001
    k["file"] = OUT
    return builtins.print(*a, **k)


pend = json.loads((ROOT / "out/state/pending.json").read_text(encoding="utf-8"))
recs = pend["records"]


def load_rec(item):
    parts = item["file"].rsplit(" records[", 1)
    p = ROOT / "out" / parts[0]
    doc = json.loads(p.read_text(encoding="utf-8"))
    idx = int(parts[1].rstrip("]"))
    return doc["records"][idx], p


for it in recs:
    rec, p = load_rec(it)
    print("=" * 100)
    print("### %s | %s" % (it["recordId"], it["component"]))
    print("status=%s  verdict=%s" % (rec.get("status"), json.dumps(rec.get("verdict"), ensure_ascii=False)))
    for t in (rec.get("tasks") or []):
        print("  - task type=%s job=%s" % (t.get("type"), t.get("jobName")))
        for k in ("evidenceNote", "summary", "emptyTestResult", "download", "truncated"):
            if t.get(k) not in (None, False, "", []):
                print("      %s=%s" % (k, t.get(k)))
        if t.get("logFile"):
            print("      logFile=%s lines=%s bytes=%s" % (t.get("logFile"), t.get("logLines"), t.get("logBytes")))
        if t.get("stepErrMsgs"):
            print("      stepErrMsgs=%s" % json.dumps(t.get("stepErrMsgs"), ensure_ascii=False)[:400])
        for el in (t.get("errorLines") or [])[:8]:
            print("      errLine=%s" % json.dumps(el, ensure_ascii=False)[:300])
        for c in (t.get("cases") or [])[:10]:
            print("      case=%s state=%s" % (c.get("name"), c.get("state")))
            for em in (c.get("errorMessages") or [])[:3]:
                print("          em=%s" % (str(em)[:300]))
            if c.get("localLog"):
                print("          localLog=%s" % c.get("localLog"))
        for s in (t.get("subTasks") or [])[:12]:
            print("      sub job=%s type=%s" % (s.get("jobName"), s.get("type")))
            for el in (s.get("errorLines") or [])[:4]:
                print("          subErr=%s" % json.dumps(el, ensure_ascii=False)[:250])
            if s.get("logFile"):
                print("          subLog=%s" % s.get("logFile"))
    print("")

OUT.close()
