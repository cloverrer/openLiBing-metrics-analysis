import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

QUERIES = [
    ("hmpi210", r"2026\2026-11\2026-11-06\HPCKit\hmpi\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kpex139", r"2026\2026-11\2026-11-06\HPCKit\kpex\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kudnn224", r"2026\2026-11\2026-11-06\HPCKit\kudnn\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kupl297", r"2026\2026-11\2026-11-06\HPCKit\kupl\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("hmpi213", r"2026\2026-11\2026-11-09\HPCKit\hmpi\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kpex142", r"2026\2026-11\2026-11-09\HPCKit\kpex\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kudnn227", r"2026\2026-11\2026-11-09\HPCKit\kudnn\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kupl306", r"2026\2026-11\2026-11-09\HPCKit\kupl\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kuqcd201", r"2026\2026-11\2026-11-09\HPCKit\kuqcd\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("kuqcd202", r"2026\2026-11\2026-11-10\HPCKit\kuqcd\pipeline.evidence.json", r"fatal: Authentication failed", 2),
    ("bigdata-obs", r"2026\2026-11\2026-11-10\boostkit\Bigdata\pipeline.evidence.json", r"DEV.CB.02202002|AccessDenied|Access Denied|status 403", 4),
    ("shmem141-queue", r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json", r"Environment allocation failed", 2),
    ("shmem145", r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json", r"Environment allocation failed|COMPUTE_TASK_INFO run", 3),
    ("atb179", r"2026\2026-11\2026-11-09\Ascend-CANN\atb\pipeline.evidence.json", r"Environment allocation failed|executor. main.py fail", 3),
    ("opstr166-hccl", r"2026\2026-11\2026-11-09\Ascend-CANN\ops-transformer\pipeline.evidence.json", r"hcclCommInitRootInfoConfig|topkNum", 4),
    ("opsnn168", r"2026\2026-11\2026-11-09\Ascend-CANN\ops-nn\pipeline.evidence.json", r"accuracy not passed", 3),
    ("sgl2125-pod", r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json", r"is not running|exit code 137", 4),
    ("sgl2130-err", r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json", r"AssertionError: 40.1|exit code: 137", 4),
    ("vllm16450", r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json", r"Performance verification failed|EngineDeadError|aisbench case failed", 6),
]

for name, rel, pat, cap in QUERIES:
    p = os.path.join(ROOT, rel)
    print("=" * 60)
    print("##", name)
    if not os.path.exists(p):
        print("  !! file not found:", rel)
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
