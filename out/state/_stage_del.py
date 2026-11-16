# -*- coding: utf-8 -*-
"""把 git status 里所有「工作区删除」的文件精确暂存，供第一次提交使用。"""
import subprocess, sys

r = subprocess.run(["git", "-c", "core.quotepath=false", "status", "--short"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
deleted = []
for ln in r.stdout.splitlines():
    if len(ln) > 3 and ln[0] == " " and ln[1] == "D":
        deleted.append(ln[3:].strip('"'))

print("deleted count:", len(deleted))
if deleted:
    # 分批 add，避免命令行过长
    B = 300
    for i in range(0, len(deleted), B):
        batch = deleted[i:i + B]
        a = subprocess.run(["git", "add", "--"] + batch, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
        if a.returncode != 0:
            print("ADD FAIL:", a.stderr[:500]); sys.exit(1)
    print("staged ok")
