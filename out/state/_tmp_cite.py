import json, sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

TASKS = [
    ("Ascend-CANN|ops-math#136", [r"accuracy not passed"]),
    ("Ascend-CANN|ops-transformer#159", [r"error code is 4", r"hcclCommInitRootInfoConfig", r"accuracy not passed", r"topkNum"]),
    ("Ascend-CANN|ops-transformer#160", [r"error code is 4", r"hcclCommInitRootInfoConfig", r"accuracy not passed", r"topkNum"]),
    ("Ascend-CANN|ops-transformer#161", [r"error code is 4", r"hcclCommInitRootInfoConfig", r"accuracy not passed", r"topkNum"]),
    ("Ascend-CANN|ops-transformer#162", [r"error code is 4", r"hcclCommInitRootInfoConfig", r"accuracy not passed", r"topkNum"]),
    ("Ascend-CANN|shmem#137", [r"COMPUTE_TASK_INFO run failed", r"FAILED due to ERROR"]),
    ("HPCKit|hmpi#210", [r"Authentication failed"]),
    ("HPCKit|kpex#139", [r"Authentication failed"]),
    ("HPCKit|kudnn#224", [r"Authentication failed"]),
    ("HPCKit|kupl#297", [r"Authentication failed"]),
    ("HPCKit|kupl#298", [r"Authentication failed"]),
    ("HPCKit|kupl#299", [r"Authentication failed"]),
    ("HPCKit|kuqcd#198", [r"Authentication failed"]),
    ("MindIE|MindIE-Motor#117", [r"TimeoutError", r"服务启动超时", r"coordinator"]),
    ("MindStudio|msot#261", [r"误报", r"Test FAILED"]),
    ("MindStudio|msot#262", [r"多 dynamic 输入运行失败", r"pytorch_to_toolkit 001 运行失败", r"Test FAILED"]),
    ("MindStudio|msot#263", [r"误报", r"Test FAILED"]),
    ("MindStudio|msot#264", [r"取消", r"停止", r"CANCEL"]),
    ("Triton_Ascend|Ascend#104", [r"run#516", r"FAILED", r"Build_a3a5_arm"]),
    ("SgLang|nightly-test-npu.yml#2079", [r"AssertionError", r"exit code", r"error"]),
    ("SgLang|nightly-test-npu.yml#2081", [r"exit code: 255", r"OpenAI Responses API"]),
    ("SgLang|nightly-test-npu.yml#2083", [r"exit code", r"AssertionError"]),
    ("SgLang|nightly-test-npu.yml#2084", [r"exit code", r"AssertionError"]),
    ("SgLang|nightly-test-npu.yml#2085", [r"InitDramSegment", r"libhcom"]),
    ("SgLang|nightly-test-npu.yml#2086", [r"libhcom", r"InitDramSegment"]),
    ("SgLang|nightly-test-npu.yml#2087", [r"exit code: 255", r"OpenAI Responses API"]),
    ("SgLang|nightly-test-npu.yml#2088", [r"OpenAI Responses API", r"exit code"]),
    ("SgLang|nightly-test-npu.yml#2091", [r"error", r"fail"]),
    ("SgLang|nightly-test-npu.yml#2092", [r"ModuleNotFoundError"]),
    ("SgLang|nightly-test-npu.yml#2093", [r"error", r"Traceback"]),
    ("SgLang|nightly-test-npu.yml#2094", [r"exit code", r"error"]),
    ("SgLang|nightly-test-npu.yml#2095", [r"FileNotFoundError", r"exit code: 255"]),
    ("SgLang|nightly-test-npu.yml#2096", [r"exit code: 255", r"OpenAI Responses API"]),
    ("SgLang|nightly-test-npu.yml#2099", [r"OpenAI Responses API", r"exit code"]),
    ("SgLang|nightly-test-npu.yml#2100", [r"error", r"fail"]),
    ("SgLang|nightly-test-npu.yml#2101", [r"exit code", r"AssertionError"]),
    ("vllm-ascend|a3.yaml#16450", [r"exit code", r"error", r"Upload failed"]),
    ("vllm-ascend|a3.yaml#16451", [r"exit code", r"error", r"Upload failed"]),
    ("Ascend-CANN|atb#179", [r"apply_env_res", r"Environment allocation", r"executor"]),
    ("Ascend-CANN|ops-nn#168", [r"accuracy not passed"]),
    ("Ascend-CANN|ops-nn#169", [r"accuracy not passed"]),
    ("Ascend-CANN|ops-transformer#165", [r"topkNum", r"error code is 4", r"accuracy not passed"]),
    ("Ascend-CANN|ops-transformer#166", [r"topkNum", r"error code is 4", r"accuracy not passed"]),
    ("Ascend-CANN|shmem#140", [r"FAILED due to ERROR", r"COMPUTE_TASK_INFO"]),
    ("Ascend-CANN|shmem#141", [r"apply_env_res", r"executor"]),
    ("Ascend-CANN|shmem#142", [r"FAILED due to ERROR", r"COMPUTE_TASK_INFO"]),
    ("HPCKit|hmpi#213", [r"Authentication failed"]),
    ("HPCKit|kpex#142", [r"Authentication failed"]),
    ("HPCKit|kudnn#227", [r"Authentication failed"]),
    ("HPCKit|kupl#306", [r"Authentication failed"]),
    ("HPCKit|kuqcd#201", [r"Authentication failed"]),
    ("MindIE|MindIE-Motor#120", [r"TimeoutError", r"服务启动超时", r"coordinator"]),
    ("MindIE|MindIE-Motor#121", [r"停止"]),
    ("MindIE|MindIE-Motor#124", [r"停止"]),
    ("SgLang|nightly-test-npu.yml#2124", [r"exit code: 255", r"OpenAI Responses API", r"Scheduler hit an exception"]),
    ("SgLang|nightly-test-npu.yml#2125", [r"error", r"exit code"]),
    ("SgLang|nightly-test-npu.yml#2126", [r"exit code", r"error"]),
    ("SgLang|nightly-test-npu.yml#2127", [r"exit code", r"error"]),
    ("SgLang|nightly-test-npu.yml#2128", [r"error", r"fail"]),
    ("SgLang|nightly-test-npu.yml#2129", [r"OpenAI Responses API", r"exit code"]),
    ("SgLang|nightly-test-npu.yml#2130", [r"exit code", r"error"]),
    ("SgLang|nightly-test-npu.yml#2132", [r"error", r"fail"]),
    ("SgLang|nightly-test-npu.yml#2133", [r"exit code", r"error"]),
    ("Ascend-CANN|ops-transformer#167", [r"topkNum", r"accuracy not passed"]),
    ("Ascend-CANN|shmem#143", [r"FAILED due to ERROR", r"COMPUTE_TASK_INFO"]),
    ("Ascend-CANN|shmem#144", [r"FAILED due to ERROR", r"COMPUTE_TASK_INFO"]),
    ("Ascend-CANN|shmem#145", [r"allocation rejected", r"executor"]),
    ("HPCKit|kuqcd#202", [r"Authentication failed"]),
    ("boostkit|Bigdata#11", [r"failed", r"构建失败"]),
]

ROOT = r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\archive\2026\2026-11"

out = open(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\state\_cites_all.txt", "w", encoding="utf-8")

for rid, pats in TASKS:
    comp, rest = rid.split("|", 1)
    pipe, build = rest.rsplit("#", 1)
    for day in ("2026-11-06", "2026-11-09", "2026-11-10"):
        d = os.path.join(ROOT, day, comp, pipe)
        if os.path.isdir(d):
            break
    else:
        out.write(f"### {rid} -- DIR NOT FOUND\n")
        continue
    ev = os.path.join(d, "pipeline.evidence.json")
    if not os.path.exists(ev):
        out.write(f"### {rid} -- NO EVIDENCE FILE ({d})\n")
        continue
    try:
        doc = json.load(open(ev, encoding="utf-8"))
    except Exception as e:
        out.write(f"### {rid} -- EVIDENCE LOAD FAIL: {e}\n")
        continue
    files = doc.get("files") or {}
    out.write(f"### {rid} ({len(files)} files)\n")
    compiled = [re.compile(p) for p in pats]
    for key, val in files.items():
        if isinstance(val, dict):
            lines = val.get("lines") or []
        elif isinstance(val, str):
            lines = val.split("\n")
        else:
            continue
        for i, l in enumerate(lines, 1):
            for c in compiled:
                if c.search(l):
                    out.write(f"  {key}:L{i}\t{l.strip()[:200]}\n")
                    break
    out.flush()
out.write("== done\n")
out.close()
print("done")
