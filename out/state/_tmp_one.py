import json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\MindIE\MindIE-Motor\pipeline.json")
with open(p, "r", encoding="utf-8", errors="replace") as f:
    data = json.load(f)
rec = data["records"][0]
print(json.dumps(rec, ensure_ascii=False, indent=1)[:4000])
