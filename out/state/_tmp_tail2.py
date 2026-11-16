import json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
p = os.path.join(ROOT, r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json")
with open(p, "r", encoding="utf-8", errors="replace") as f:
    ev = json.load(f)
files = ev.get("files") or {}
for name in ("github_logs/gh_42197450049/127824197172_nightly-1-npu-a3 _ run (0).txt",
             "github_logs/gh_42197450049/127824197865_nightly-perf-16-npu-a3 _ nightly-perf-16-npu-a3.txt",
             "github_logs/gh_42197450049/127824197899_nightly-acc-16-npu-a3 _ nightly-acc-16-npu-a3.txt"):
    meta = files.get(name) or {}
    lines = meta.get("lines") or []
    print("===== %s (%d lines) =====" % (name, len(lines)))
    for i, l in enumerate(lines):
        if ("ModuleNotFoundError" in l or "No module named" in l or "ImportError" in l
                or "Traceback" in l or "error" in l.lower() or "failed" in l.lower() or "FAILED" in l):
            print("  L%d %s" % (i + 1, l[:230]))
    print()
