# -*- coding: utf-8 -*-
import io, re

t = io.open(r"out\state\_cites_slim.txt", encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
parts = re.split(r"(?m)^(===== .+)$", t)
secs = []
for i in range(1, len(parts), 2):
    secs.append((parts[i], parts[i + 1]))

out = []
for head, body in secs:
    if "2026-11-10" in head:
        out.append(head)
        out.append(body.rstrip())
        out.append("")

with io.open(r"out\state\_win10.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("sections:", sum(1 for h, _ in secs if "2026-11-10" in h), "total:", len(secs))
