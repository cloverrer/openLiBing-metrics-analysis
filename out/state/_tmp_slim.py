# -*- coding: utf-8 -*-
import re, io

SRC = r"out\state\_cites_final.txt"
DST = r"out\state\_cites_slim.txt"

keep_re = re.compile(
    r"ERROR|error|ailed|Timeout|超时|Authentication|ccuracy|hccl|Module|"
    r"Environment|ssert|xception|exit code|停止|msprof|COMPUTE_TASK|topkNum|tiling|"
    r"coordinator|Pending|HYBM|Import|OBS|hit rate|Decode|allocat|FAIL|fatal|"
    r"服务|启动|EngineDead|not passed|Environment allocation",
    re.IGNORECASE,
)
drop_re = re.compile(r"td style=|<a href=|msg-scroll\">Total Task")

out = []
with io.open(SRC, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        s = line.rstrip("\n")
        if s.startswith("=====") or s.startswith("  FILE"):
            out.append(s)
        elif drop_re.search(s):
            continue
        elif keep_re.search(s):
            out.append(s)

with io.open(DST, "w", encoding="utf-8") as f:
    f.write("\n".join(out))

print("lines:", len(out))
