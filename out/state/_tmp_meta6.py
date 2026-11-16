import os, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_meta6_out.txt")
buf = []

rel = r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json"
p = os.path.join(ROOT, rel)
with open(p, "r", encoding="utf-8", errors="replace") as f:
    data = json.load(f)
recs = data.get("records", [])
buf.append("records: %d" % len(recs))
for i, rec in enumerate(recs):
    buf.append("[%d] keys=%s" % (i, list(rec.keys())[:20]))
    buf.append("    runId=%r status=%r" % (rec.get("runId"), rec.get("status")))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
