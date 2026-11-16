import os, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_win6_out.txt")
buf = []

def grep_file_lines(rel, pats, cap=4):
    p = os.path.join(ROOT, rel)
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for pat in pats:
        rx = re.compile(pat)
        hits = []
        for i, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append((i, line.strip()[:280]))
        buf.append("  [%s] %s -> %d hits" % (os.path.basename(rel), pat, len(hits)))
        for i, l in hits[:cap]:
            buf.append("    L%d : %s" % (i, l))

# shmem 11-06 #137 allgather failure
grep_file_lines(r"2026\2026-11\2026-11-06\Ascend-CANN\shmem\pipeline.evidence.json",
                [r"测试失败", r"COMPUTE_TASK_INFO", r"allgather_pes8"], 3)

# Triton 104: real failure after 404
grep_file_lines(r"2026\2026-11\2026-11-06\Triton_Ascend\Ascend\pipeline.evidence.json",
                [r"Build_a3a5_arm.*FAILED|任务 \[Build", r"ERROR 404", r"exit code 8", r"npu_ir"], 4)

# MindStudio msot 261/262/263 job failure signature
grep_file_lines(r"2026\2026-11\2026-11-06\MindStudio\msot\pipeline.evidence.json",
                [r"工具发生误报|工具产生误报", r"多 dynamic 输入运行失败", r"pytorch_to_toolkit 001 运行失败", r"path.*does not have permission", r"no such file or directory"], 2)

# vllm 16450/16451 worker pending
grep_file_lines(r"2026\2026-11\2026-11-06\vllm-ascend\a3.yaml\pipeline.evidence.json",
                [r"Timeout reached", r"Insufficient", r"phase=Pending", r"not less than or equal"], 3)

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(buf) + "\n")
print("written", len(buf), "lines")
