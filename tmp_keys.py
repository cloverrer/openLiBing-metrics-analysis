import sys, json
from pathlib import Path
ROOT = Path(r".")
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc
pdir = Path("out/archive/2026/2026-11/2026-11-16/SgLang/nightly-test-npu.yml")
ent = pipeline_doc.evidence_entries(pdir)
for k in sorted(ent):
    if "43868335184" in k or "43870381982" in k or "43874714626" in k or "43888687387" in k or "43892530840" in k:
        print(repr(k), ent[k])
