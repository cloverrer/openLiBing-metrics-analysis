import json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\archive\2026\2026-11"
DAYS = ["2026-11-06", "2026-11-09", "2026-11-10"]

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
            for i, rec in enumerate(doc.get("records") or []):
                st = (rec.get("analysis") or {}).get("status")
                if st and st != "pending":
                    continue
                rid = rec.get("recordId")
                # 收集该记录关联的日志文件（从 tasks / testResults 等字段）
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
                print(f"{day}|{rid}|rec[{i}]|{sorted(files)}")
print("== done")
