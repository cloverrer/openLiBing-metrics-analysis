import json, sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\archive\2026\2026-11"
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10"]
OUT = open(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\state\_rc_detail.txt", "w", encoding="utf-8")

# 针对每条记录自身的证据文件提取失败特征
PAT = re.compile(r"✗ |##\[error\]|AssertionError|ModuleNotFoundError|ImportError|FileNotFoundError|TimeoutError|EngineDeadError|InitDramSegment|libhcom|Scheduler hit an exception|OpenAI Responses API.*init failed|hcclCommInitRootInfoConfig|topkNum|accuracy not passed|COMPUTE_TASK_INFO|Environment allocation|allocation rejected|apply_env_res|Authentication failed|服务启动超时|误报|运行失败|构建失败|failed|FAILED|error code")

def load_ev(pdir):
    ev = os.path.join(pdir, "pipeline.evidence.json")
    if not os.path.exists(ev):
        return {}
    try:
        return json.load(open(ev, encoding="utf-8")).get("files") or {}
    except Exception:
        return {}

for day in DAYS:
    for comp in sorted(os.listdir(os.path.join(ROOT, day))):
        cdir = os.path.join(ROOT, day, comp)
        if not os.path.isdir(cdir):
            continue
        for pipe in sorted(os.listdir(cdir)):
            pdir = os.path.join(cdir, pipe)
            pj = os.path.join(pdir, "pipeline.json")
            if not os.path.exists(pj):
                continue
            doc = json.load(open(pj, encoding="utf-8"))
            ev = load_ev(pdir)
            for i, rec in enumerate(doc.get("records") or []):
                st = (rec.get("analysis") or {}).get("status")
                if st and st != "pending":
                    continue
                rid = rec.get("recordId")
                files = set()
                def walk(o, depth=0):
                    if depth > 6:
                        return
                    if isinstance(o, dict):
                        for k, v in o.items():
                            if isinstance(v, str) and (v.startswith("job_logs/") or v.startswith("github_logs/") or v.startswith("case_logs/")):
                                files.add(v.split(":")[0])
                            else:
                                walk(v, depth + 1)
                    elif isinstance(o, list):
                        for v in o:
                            walk(v, depth + 1)
                walk(rec)
                OUT.write(f"===== {day} | {rid} | rec[{i}] | {len(files)} files\n")
                if not files:
                    # 无证据文件时打印记录自带的关键字段
                    tr = rec.get("testResults") or {}
                    OUT.write(f"  [record fields] keys={list(rec.keys())}\n")
                    OUT.write(f"  [verdict] {json.dumps(rec.get('verdict'), ensure_ascii=False)[:400]}\n")
                    if tr:
                        OUT.write(f"  [testResults] {json.dumps(tr, ensure_ascii=False)[:600]}\n")
                    continue
                for fn in sorted(files):
                    val = ev.get(fn)
                    if val is None:
                        OUT.write(f"  !! {fn} NOT IN EVIDENCE\n")
                        continue
                    lines = val.get("lines") if isinstance(val, dict) else (val.split("\n") if isinstance(val, str) else [])
                    hits = []
                    for li, l in enumerate(lines, 1):
                        if PAT.search(l):
                            hits.append((li, l.strip()[:220]))
                    OUT.write(f"  -- {fn} ({len(lines)} lines, {len(hits)} hits)\n")
                    for li, l in hits[:18]:
                        OUT.write(f"     L{li}\t{l}\n")
                    if len(hits) > 18:
                        OUT.write(f"     ... +{len(hits)-18} more\n")
                OUT.flush()
OUT.close()
print("done")
