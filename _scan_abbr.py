import re
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

for f in [r"out\html\index.html", r"out\html\detail.html"]:
    src = open(f, encoding="utf-8").read()
    # 可见文本节点与 title 属性里的 VA / BS（排除 JS 标识符）
    txt_hits = re.findall(r">([^<>]*\b(?:VA|BS)\b[^<>]*)<", src)
    ttl_hits = re.findall(r'title="([^"]*\b(?:VA|BS)\b[^"]*)"', src)
    print(f, "-> text:", [t.strip()[:60] for t in txt_hits][:8])
    print(f, "-> title:", [t.strip()[:60] for t in ttl_hits][:8])
