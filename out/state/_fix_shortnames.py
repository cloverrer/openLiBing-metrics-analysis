# -*- coding: utf-8 -*-
"""把 out/work 采集产物里的短名对齐到身份注册表（只改短名，不动 pipelineName）。

背景：out/work 里的短名还是旧版「按当日采集集合现算」的结果 ——
  openUBMC~f35034（应为 openUBMC）、Agentsdk（应为 Agentsdk~5992cb，否则与
  AgentSDK 在 Windows 上共用同一个目录互相覆盖）。
短名只出现在 4 种位置：精确值 / "组件|短名" / "组件|短名#构建号" / 路径段 "/短名"。
pipelineName（..._pipeline_Agentsdk）必须原样保留，所以不做裸串替换。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORK = ROOT / "out" / "work"

RENAME = {
    "openUBMC~f35034": "openUBMC",
    "Agentsdk": "Agentsdk~5992cb",
}


def fix(s, old, new):
    if old not in s:
        return s
    if s == old:
        return new
    s = s.replace("|" + old, "|" + new)                      # 组件|短名、组件|短名#构建号
    s = re.sub(r"(?<=/)" + re.escape(old) + r"(?=/|$)", new, s)   # 路径段
    return s


def walk(o, fn):
    if isinstance(o, str):
        return fn(o)
    if isinstance(o, list):
        return [walk(x, fn) for x in o]
    if isinstance(o, dict):
        return {walk(k, fn) if isinstance(k, str) else k: walk(v, fn) for k, v in o.items()}
    return o


def main():
    total = 0
    for p in sorted(WORK.glob("*.json")):
        raw = p.read_text(encoding="utf-8")
        if not any(k in raw for k in RENAME):
            continue
        obj = json.loads(raw)
        hits = [0]

        def fn(s):
            for old, new in RENAME.items():
                ns = fix(s, old, new)
                if ns != s:
                    hits[0] += 1
                    s = ns
            return s

        obj = walk(obj, fn)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  %-32s 改写 %d 处" % (p.name, hits[0]))
        total += hits[0]
    print("合计改写 %d 处" % total)


if __name__ == "__main__":
    main()
