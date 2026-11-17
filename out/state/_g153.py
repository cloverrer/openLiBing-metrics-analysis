# -*- coding: utf-8 -*-
import re
p = r"out/work/job_logs/41_os_153_Build_A3_image.log"
txt = open(p, encoding="utf-8", errors="replace").read()
print("len", len(txt))
for kw in ["chmod", "Ascend-cann-A3-ops", "No such file", "ERROR", "Cannot", "make", "error:"]:
    idxs = [m.start() for m in re.finditer(re.escape(kw), txt)]
    print("=== ", kw, len(idxs))
    for i in idxs[:3]:
        print(repr(txt[max(0, i - 200):i + 200]))
