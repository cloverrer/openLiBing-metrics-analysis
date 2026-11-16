import subprocess, sys, io, os

root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
p = subprocess.run([sys.executable, os.path.join(root, "tools", "list_pending.py"), "--all", "--limit", "0"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=root)
out = p.stdout + p.stderr
lines = []
for ln in out.splitlines():
    s = ln.rstrip()
    if not s:
        continue
    parts = s.split()
    if parts[0].isdigit() and len(parts) >= 5:
        lines.append("|".join(parts[:6]))
dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pend_ids.txt")
with open(dst, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("total", len(lines))
