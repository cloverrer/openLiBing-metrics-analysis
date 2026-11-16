import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

QUERIES = [
    ("vllm16450-tpot", r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
     r"TPOT|not passed|AssertionError|throughput|Throughput|target", 10),
    ("vllm16450-fail", r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
     r"aisbench case failed|The following|✗ exit|FAIL_TAG.*✗|Process completed with exit code", 8),
    ("atb179b", r"2026\2026-11\2026-11-09\Ascend-CANN\atb\pipeline.evidence.json",
     r"Environment allocation failed|apply_env_res.*'status': 'failed'|queued'", 5),
    ("msot264-meta", r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.evidence.json",
     r"cancelled|aborted|Cancel|取消", 5),
]

for name, rel, pat, cap in QUERIES:
    p = os.path.join(ROOT, rel)
    print("=" * 60)
    print("##", name)
    if not os.path.exists(p):
        print("  !! not found")
        continue
    rx = re.compile(pat)
    shown = 0
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f, 1):
            if rx.search(line):
                print("  L%d : %s" % (i, line.strip()[:240]))
                shown += 1
                if shown >= cap:
                    break
    if shown == 0:
        print("  (no match)")
