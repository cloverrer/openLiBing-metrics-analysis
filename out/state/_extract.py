import re, pathlib
for name in ("index.html","detail.html"):
    p = pathlib.Path("out/html")/name
    if not p.exists(): continue
    html = p.read_text(encoding="utf-8")
    for i, m in enumerate(re.findall(r"<script>([\s\S]*?)</script>", html)):
        pathlib.Path("out/state/_chk_%s_%d.js" % (name.split(".")[0], i)).write_text(m, encoding="utf-8")
        print("wrote", name, i, len(m))
