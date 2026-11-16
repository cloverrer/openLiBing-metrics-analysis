# -*- coding: utf-8 -*-
"""汇总 _rc_detail.txt 每节（记录）的证据文件与关键错误行，供合成 conclusions 用。"""
import io
import re

SRC = r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\state\_rc_detail.txt"
OUT = r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca\out\state\_cites_final.txt"

KEY = re.compile(
    r"accuracy not passed|error code|HCCL|hcclComm|tiling|Authentication failed|git clone test_cases|"
    r"Environment allocation|apply_env_res|Timeout|timeout|服务启动|停止|误报|越界|permission|does not exist|"
    r"ModuleNotFoundError|AssertionError|TypeError|FileNotFoundError|RuntimeError|EngineDeadError|"
    r"is not running|Scheduler hit an exception|exit code|FAILED|Failed|failed|失败|COMPUTE_TASK_INFO|"
    r"Upload failed|package_upload|依赖任务失败|构建失败|ERR99999|Decode transfer|ConfigMap|Build_a3a5|404|"
    r"topkNum|shape must be|GetWorkspaceSize|acc_pass_result|Test failed|测试失败|ERROR|Error",
)

lines = io.open(SRC, encoding="utf-8", errors="replace").read().splitlines()
sections = [i for i, l in enumerate(lines) if l.startswith("===== ")]

out = []
for si, start in enumerate(sections):
    end = sections[si + 1] if si + 1 < len(sections) else len(lines)
    header = lines[start]
    out.append(header)
    cur_file = None
    shown = 0
    for l in lines[start + 1:end]:
        if l.strip().startswith("-- "):
            cur_file = l.strip()[3:].split(" (")[0]
            shown = 0
            out.append("  FILE " + cur_file)
        else:
            m = re.match(r"\s*L(\d+)\t(.*)", l)
            if not m:
                continue
            body = m.group(2)
            if KEY.search(body) and shown < 6:
                out.append("    L%s\t%s" % (m.group(1), body[:170]))
                shown += 1
    out.append("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(out))
print("written", len(sections), "sections,", len(out), "lines")
