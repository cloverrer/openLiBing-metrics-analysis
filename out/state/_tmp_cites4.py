import os, re, json

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cites4_out.txt")
buf = []

def grep_file_lines(rel, pats, cap=3):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        buf.append("  !! missing " + rel)
        return
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for pat in pats:
        rx = re.compile(pat)
        hits = []
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append((i, line.strip()[:260]))
        buf.append("  [%s|%s] %s -> %d hits" % (rel.split("\\")[-2], os.path.basename(rel), pat, len(hits)))
        for i, l in hits[:cap]:
            buf.append("    L%d : %s" % (i, l))

# SgLang 11-09 evidence: 2124/2126/2127/2129/2130/2133 signatures
grep_file_lines(r"2026\2026-11\2026-11-09\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
                [r"run_unittest_files\(\) got an unexpected keyword", r"ModuleNotFoundError: No module named", r"AssertionError: 40.1 not less than", r"Scheduler hit an exception", r"is not running, status: Succeeded", r"Timeout: Failed to get complete node information"], 2)

# SgLang 11-06 evidence: 2079/2081/2083/2084/2087/2088/2093-2096/2099/2101
grep_file_lines(r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
                [r"run_unittest_files\(\) got an unexpected keyword", r"AssertionError: 0.849", r"AssertionError: 47.9", r"AssertionError: 58.34", r"AssertionError: 39.9", r"can't multiply sequence", r"FileNotFoundError.*test_npu_de", r"not running, status: Succeeded", r"Timeout: Failed to get complete node", r"Could not find a version that satisfies", r"ERR99999", r"Decode transfer failed"], 2)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
