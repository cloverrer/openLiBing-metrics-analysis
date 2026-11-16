# -*- coding: utf-8 -*-
"""核验暂存区：统计已暂存的删除条目数，并列出仍在工作区未暂存的删除。"""
import subprocess

def gstat():
    r = subprocess.run(["git", "-c", "core.quotepath=false", "status", "--short"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.splitlines()

staged_del, unstaged_del = [], []
for ln in gstat():
    if len(ln) <= 3:
        continue
    st, path = ln[:2], ln[3:].strip('"')
    if st == "D ":
        staged_del.append(path)
    elif st == " D":
        unstaged_del.append(path)

print("staged deletions:", len(staged_del))
print("unstaged deletions:", len(unstaged_del))
for p in unstaged_del[:5]:
    print("  still-unstaged:", p)

# 交叉核对：用 git ls-files --deleted 独立验证
r = subprocess.run(["git", "-c", "core.quotepath=false", "ls-files", "--deleted"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
ls = [x for x in r.stdout.splitlines() if x.strip()]
print("ls-files --deleted:", len(ls))
missing = [p for p in ls if p not in set(staged_del)]
print("missing from stage:", len(missing))
for p in missing[:8]:
    print("  missing:", p)
