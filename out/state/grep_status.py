import re

for f in ["step_6_records.py", "step_7_archive.py"]:
    src = open(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\steps" + "\\" + f, encoding="utf-8").read()
    for m in re.finditer(r'pending|"na"|analysis\s*=|analysisStatus|"status"', src):
        ln = src[: m.start()].count("\n") + 1
        line = src.splitlines()[ln - 1].strip()
        print("%s %d: %s" % (f, ln, line[:120]))
