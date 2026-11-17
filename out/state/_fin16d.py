# -*- coding: utf-8 -*-
import io, json, sys
from pathlib import Path
ROOT = Path(r"c:\Users\Administrator\Downloads\openlibing看板导出与不达标分析_参考包\openlibing-nightly-rca")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa
OUT = io.open(ROOT / "out/state/_fin16d.txt", "w", encoding="utf-8", newline="\n")

p = ROOT / "out/archive/2026/2026-11/2026-11-16/MindCluster/Agentsdk~5992cb"
OUT.write("### files: %s\n" % [x.name for x in p.iterdir()])
doc = pipeline_doc.load(p / "pipeline.json") or {}
OUT.write("### doc keys: %s\n" % sorted(doc.keys()))
OUT.write(json.dumps(doc, ensure_ascii=False)[:3000])
OUT.write("\n")
OUT.close()
print("done")
