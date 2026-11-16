import json, os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

def ev_lines(rel_path, patterns, max_hits=12, window=0):
    p = os.path.join(ROOT, rel_path)
    if not os.path.exists(p):
        print("  !! not found:", rel_path)
        return
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    rx = re.compile(patterns)
    hits = 0
    for idx, line in enumerate(lines):
        if rx.search(line):
            print("     L%d %s" % (idx + 1, line.strip()[:260]))
            hits += 1
            if hits >= max_hits:
                break

targets = [
    ("vllm#16450", r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
     "aisbench case failed|FAIL_TAG_|EngineDeadError|exit code: 1"),
    ("vllm#16451", r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
     "aisbench case failed|FAIL_TAG_|EngineDeadError|exit code: 1"),
    ("shmem#140/142 11-09", r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json",
     "COMPUTE_TASK_INFO|msprof|FAILED due to|error|Error|ERROR"),
    ("shmem#143/144 11-10", r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json",
     "COMPUTE_TASK_INFO|msprof|FAILED due to|error|Error|ERROR"),
    ("SgLang#2125 11-09", r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
     "aisbench|FAIL|error|Error|ERROR|timeout|Timeout|exit code"),
    ("SgLang#2129 11-09", r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
     "AssertionError|exit code|FAIL_TAG"),
    ("msot#264 11-06", r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.evidence.json",
     "Message:|AssertionError|error|failed"),
]

for name, rel, pat in targets:
    print("=" * 66)
    print("##", name)
    ev_lines(rel, pat, max_hits=14)
