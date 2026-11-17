import sys
from pathlib import Path
sys.path.insert(0, str(Path(r".")))
from lib import pipeline_doc
pdir = Path("out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml")
ent = pipeline_doc.evidence_entries(pdir)
for gh in ["43868335184","43870381982","43874714626","43888687387","43892530840"]:
    for k in sorted(ent):
        if gh in k:
            print(k)
