import json, re, os, html, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive")
STATE = os.path.dirname(os.path.abspath(__file__))

def load_ev(rel):
    p = os.path.normpath(os.path.join(ROOT, rel))
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)

def get_lines(ev, fname):
    if ev is None:
        return None
    files = ev.get("files", {}) if isinstance(ev, dict) else {}
    ent = files.get(fname)
    if ent is None:
        return None
    if isinstance(ent, dict):
        return ent.get("lines")
    if isinstance(ent, list):
        return ent
    if isinstance(ent, str):
        return ent.splitlines()
    return None

def strip(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return s.strip()

def grep_section(out, title, ev_rel, file_pred, patterns, cap_per_file=14, cap_total=60, exclude=None):
    out.append("\n########## %s ##########" % title)
    ev = load_ev(ev_rel)
    if ev is None:
        out.append("  !! evidence not found: %s" % ev_rel)
        return
    files = ev.get("files", {}) if isinstance(ev, dict) else {}
    total = 0
    for fname in sorted(files.keys()):
        if not file_pred(fname):
            continue
        lines = get_lines(ev, fname)
        if not lines:
            continue
        hits = []
        for i, ln in enumerate(lines, 1):
            t = strip(ln)
            if not t:
                continue
            if exclude and re.search(exclude, t):
                continue
            for pat in patterns:
                if re.search(pat, t):
                    hits.append((i, t))
                    break
            if len(hits) >= cap_per_file:
                break
        if hits:
            out.append("  -- %s" % fname)
            for i, t in hits:
                out.append("     L%d  %s" % (i, t[:240]))
                total += 1
            if total >= cap_total:
                out.append("  ...(cap reached)")
                return

RX_ERR = r"(AssertionError|assert |aisbench case failed|EngineDeadError|TimeoutError|ConnectionError|Killed|Watchdog|abort|OOM|CUDA out)"
RX_EXIT = r"(exit code: [0-9]+|##\[error\])"

out = []

# vllm-ascend 11-06 #16450 / #16451
grep_section(out, "V16450 (vllm a3 11-06 run 42063861754)",
             r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
             lambda f: f.startswith("github_logs/gh_42063861754"),
             [RX_ERR, r"(assert |Accuracy|accuracy|TPOT|throughput|baseline)"], cap_per_file=10, cap_total=50,
             exclude=r"DeprecationWarning|node:[0-9]+\) \[DEP0169\]")
grep_section(out, "V16451 (vllm a3 11-06 run 42099201193)",
             r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
             lambda f: f.startswith("github_logs/gh_42099201193"),
             [RX_ERR, r"(assert |Accuracy|accuracy|TPOT|throughput|baseline)"], cap_per_file=10, cap_total=50,
             exclude=r"DeprecationWarning|node:[0-9]+\) \[DEP0169\]")

# Triton 11-06 #104
grep_section(out, "TRITON104",
             r"2026\2026-11\2026-11-06\Triton_Ascend\Ascend\pipeline.evidence.json",
             lambda f: f.startswith("job_logs/"),
             [r"(?i)(fatal|exception|traceback|错误信息|执行失败|-> FAILED|git|clone|error)"],
             cap_per_file=30, cap_total=80,
             exclude=r"RUNNING\(运行中\)\s*\|\s*已等待|INIT\(初始化\)\s*\|")

# boostkit Bigdata 11-10 #11
grep_section(out, "BIGDATA11",
             r"2026\2026-11\2026-11-10\boostkit\Bigdata\pipeline.evidence.json",
             lambda f: f.startswith("job_logs/"),
             [r"(?i)(error|失败|exception|caused by|build failure|fatal)"],
             cap_per_file=40, cap_total=90)

# SgLang 11-06
SGL06 = r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json"
grep_section(out, "SGL2079 (run 42047810705)",
             SGL06, lambda f: f.startswith("github_logs/gh_42047810705"),
             [r"(AssertionError|assert |ImportError|ModuleNotFoundError|TimeoutError|ConfigMap|hit rate|TPOT|run_unittest_files|exited|OpenAI Responses|Scheduler hit)"],
             cap_per_file=10, cap_total=50, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2081 (run 42061473997)",
             SGL06, lambda f: f.startswith("github_logs/gh_42061473997"),
             [r"(Traceback|AssertionError|assert |ImportError|Error|exit code|OpenAI Responses)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2083 (run 42068311537)",
             SGL06, lambda f: f.startswith("github_logs/gh_42068311537"),
             [r"(AssertionError|assert |ERROR|OpenAI|exit code)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2084 (run 42068844392)",
             SGL06, lambda f: f.startswith("github_logs/gh_42068844392"),
             [r"(assert|Accuracy|accuracy|score|exit code|ERROR|Traceback)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2087 (run 42144867602)",
             SGL06, lambda f: f.startswith("github_logs/gh_42144867602"),
             [r"(Traceback|AssertionError|assert |ImportError|Error|exit code|OpenAI Responses)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2088 (run 42159951566)",
             SGL06, lambda f: f.startswith("github_logs/gh_42159951566"),
             [r"(Traceback|AssertionError|assert |ImportError|Error|exit code|OpenAI Responses)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2093 (run 42199356561)",
             SGL06, lambda f: f.startswith("github_logs/gh_42199356561"),
             [r"(Traceback|AssertionError|ImportError|ModuleNotFoundError|ERROR|assert |OpenAI|exit code)"],
             cap_per_file=12, cap_total=45, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2094 (run 42202191521)",
             SGL06, lambda f: f.startswith("github_logs/gh_42202191521"),
             [r"(Traceback|AssertionError|ERROR|assert |OpenAI|exit code)"],
             cap_per_file=12, cap_total=45, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2095 (run 42204167966)",
             SGL06, lambda f: f.startswith("github_logs/gh_42204167966"),
             [r"(Traceback|Error|assert |OpenAI|FileNotFound|exit code)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2096 (run 42208857568)",
             SGL06, lambda f: f.startswith("github_logs/gh_42208857568"),
             [r"(Traceback|AssertionError|assert |ImportError|Error|exit code|OpenAI Responses|FileNotFound)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2099 (run 42212286289)",
             SGL06, lambda f: f.startswith("github_logs/gh_42212286289"),
             [r"(Traceback|AssertionError|assert |ImportError|Error|exit code|OpenAI Responses)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2101 (run 42220261231)",
             SGL06, lambda f: f.startswith("github_logs/gh_42220261231"),
             [r"(assert|Accuracy|accuracy|score|exit code|ERROR|Traceback)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")

# SgLang 11-09
SGL09 = r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json"
grep_section(out, "SGL2124 (run 42498125758)",
             SGL09, lambda f: f.startswith("github_logs/gh_42498125758"),
             [r"(Scheduler hit an exception|AssertionError|assert |ImportError|ModuleNotFoundError|ERROR|OpenAI|HYBM|InitDramSegment|exit code)"],
             cap_per_file=10, cap_total=45, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2126 (run 42503749318)",
             SGL09, lambda f: f.startswith("github_logs/gh_42503749318"),
             [r"(assert|Accuracy|accuracy|score|exit code|ERROR|Traceback)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2127 (run 42509098847)",
             SGL09, lambda f: f.startswith("github_logs/gh_42509098847"),
             [r"(assert|Accuracy|accuracy|score|exit code|ERROR|Traceback)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2129 (run 42608919924)",
             SGL09, lambda f: f.startswith("github_logs/gh_42608919924"),
             [r"(Traceback|AssertionError|assert |ImportError|Error|exit code|OpenAI Responses)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2130 (run 42611183075)",
             SGL09, lambda f: f.startswith("github_logs/gh_42611183075"),
             [r"(Traceback|AssertionError|ERROR|assert |OpenAI|exit code)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")
grep_section(out, "SGL2133 (run 42620485286)",
             SGL09, lambda f: f.startswith("github_logs/gh_42620485286"),
             [r"(Traceback|AssertionError|ERROR|assert |OpenAI|exit code)"],
             cap_per_file=12, cap_total=40, exclude=r"DeprecationWarning|\[DEP0169\]")

# MindIE 11-06 #117 / 11-09 #120
grep_section(out, "MIE117 (11-06 case_0000)",
             r"2026\2026-11\2026-11-06\MindIE\MindIE-Motor\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(TimeoutError|超时|kubectl|NotFound|等待|pod.*(?:Succeeded|Failed|Running)|restartCount|CrashLoop)"],
             cap_per_file=40, cap_total=90)
grep_section(out, "MIE120 (11-09 case_0000)",
             r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(TimeoutError|超时|kubectl|NotFound|等待|restartCount|CrashLoop|ERROR)"],
             cap_per_file=40, cap_total=90)

# ops-nn 11-09 #168/#169
grep_section(out, "OPSNN (11-09)",
             r"2026\2026-11\2026-11-09\Ascend-CANN\ops-nn\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(accuracy not passed|error_msg|VERIFY|FakeQuant|diff=|max_diff|Failed)"],
             cap_per_file=10, cap_total=40)

# ops-transformer 11-09 #165/#166, 11-10 #167
grep_section(out, "OPSTR09 (11-09 tiling/hccl)",
             r"2026\2026-11\2026-11-09\Ascend-CANN\ops-transformer\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(topkNum|probs dimension|tiling|561002|error code|hcclCommInitRootInfoConfig|InitDramSegment)"],
             cap_per_file=8, cap_total=40)
grep_section(out, "OPSTR10 (11-10 tiling)",
             r"2026\2026-11\2026-11-10\Ascend-CANN\ops-transformer\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(topkNum|probs dimension|tiling|561002|error code|accuracy not passed)"],
             cap_per_file=8, cap_total=40)

# ops-transformer 11-06 #159-162 (HCCL)
grep_section(out, "OPSTR06 (11-06 hccl)",
             r"2026\2026-11\2026-11-06\Ascend-CANN\ops-transformer\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(hcclCommInitRootInfoConfig|error code|topkNum|probs dimension|tiling|561002|InitDramSegment)"],
             cap_per_file=8, cap_total=40)

# atb 11-09 #179
grep_section(out, "ATB179 (11-09 job log)",
             r"2026\2026-11\2026-11-09\Ascend-CANN\atb\pipeline.evidence.json",
             lambda f: f.startswith("job_logs/"),
             [r"(apply_env_res|allocation|queued|provisioning|executor|ERROR|失败|exit code|超时)"],
             cap_per_file=40, cap_total=80)

# shmem 11-09 / 11-10
grep_section(out, "SHMEM09 (11-09 case + job)",
             r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/") or f.startswith("job_logs/"),
             [r"(COMPUTE_TASK_INFO|ERROR|allgather|assert|apply_env_res|allocation|queued|executor|失败)"],
             cap_per_file=16, cap_total=70)
grep_section(out, "SHMEM10 (11-10 case + job)",
             r"2026\2026-11\2026-11-10\Ascend-CANN\shmem\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/") or f.startswith("job_logs/"),
             [r"(COMPUTE_TASK_INFO|ERROR|allgather|assert|apply_env_res|allocation|rejected|executor|失败)"],
             cap_per_file=16, cap_total=70)

# ops-math 11-06 #136
grep_section(out, "OPSMATH136 (11-06)",
             r"2026\2026-11\2026-11-06\Ascend-CANN\ops-math\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(accuracy not passed|MessageFactory|AttributeError|error_msg)"],
             cap_per_file=6, cap_total=45)

# MindStudio msot 11-06
grep_section(out, "MSOT (11-06)",
             r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.evidence.json",
             lambda f: f.startswith("case_logs/"),
             [r"(误报|越界|dynamic 输入|运行失败|assert )"],
             cap_per_file=8, cap_total=40)

# Record JSON dump for records without evidence
out.append("\n########## RECORD-DUMP (no-evidence records) ##########")
DUMPS = [
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.json", ["2091", "2100"]),
    (r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.json", ["2125", "2128", "2132", "2133"]),
    (r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.json", ["264"]),
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.json", ["121", "124"]),
]
for rel, ids in DUMPS:
    p = os.path.normpath(os.path.join(ROOT, rel))
    if not os.path.exists(p):
        out.append("  !! not found %s" % rel)
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    for rec in data.get("records", []):
        rid = rec.get("runId") or rec.get("id") or ""
        rid_s = str(rid)
        if not any(rid_s.endswith(i) or ("#%s" % i) == rid_s.split("|")[-1] for i in ids):
            continue
        out.append("  -- record %s status=%s end=%s" % (rid, rec.get("status"), rec.get("endTime") or rec.get("end")))
        for t in (rec.get("tasks") or []):
            out.append("     task: %s | status=%s | log=%s" % (t.get("name"), t.get("status"), t.get("log")))
        ke = rec.get("keyError")
        if ke:
            if isinstance(ke, list):
                for k in ke[:6]:
                    out.append("     keyError: %s" % str(k)[:240])
            else:
                out.append("     keyError: %s" % str(ke)[:240])
        tr = rec.get("testResults")
        if tr:
            out.append("     testResults: %s" % json.dumps(tr, ensure_ascii=False)[:600])
        for extra in ("failedTaskType", "runUrl", "url"):
            if rec.get(extra):
                out.append("     %s: %s" % (extra, str(rec.get(extra))[:200]))

dst = os.path.join(STATE, "_digest.txt")
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("written %s, %d lines" % (dst, len(out)))
