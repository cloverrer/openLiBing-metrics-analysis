# -*- coding: utf-8 -*-
"""统计待提交内容：修改的分布 + 未跟踪的分布（正式 vs 调试临时）。"""
import subprocess
from collections import Counter

r = subprocess.run(["git", "-c", "core.quotepath=false", "status", "--short"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
mods, untracked = [], []
for ln in r.stdout.splitlines():
    if len(ln) <= 3:
        continue
    st, path = ln[:2], ln[3:].strip('"')
    if st == " M":
        mods.append(path)
    elif st == "??":
        untracked.append(path)

def top(paths, n=3, width=40):
    c = Counter()
    for p in paths:
        parts = p.split("/")
        key = "/".join(parts[:n]) if len(parts) > n else p
        c[key] += 1
    return c

print("=== 修改 (%d) ===" % len(mods))
for k, v in top(mods, 2).most_common(15):
    print("  %5d  %s" % (v, k))

print("=== 未跟踪 (%d) ===" % len(untracked))
for k, v in top(untracked, 2).most_common(20):
    print("  %5d  %s" % (v, k))
