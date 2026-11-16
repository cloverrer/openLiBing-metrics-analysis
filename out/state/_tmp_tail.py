import json, os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "archive"))

DUMPS = [
    (r"2026\2026-11\2026-11-10\boostkit\Bigdata\pipeline.evidence.json",
     ["22_Bigdata_11_Build_Gluten_OmniOperator_openEuler22.03_JDK8",
      "23_Bigdata_11_Build_Gluten_OmniOperator_openEuler24.03_JDK17"], "BD11 build subjobs"),
    (r"2026\2026-11\2026-11-09\Ascend-CANN\shmem\pipeline.evidence.json",
     ["02_shmem_141_Test_shmem"], "shmem141"),
    (r"2026\2026-11\2026-11-09\MindIE\MindIE-Motor\pipeline.evidence.json", [], "mie109 (list files)"),
    (r"2026\2026-11\2026-11-06\SgLang\nightly-test-npu.yml\pipeline.evidence.json",
     ["01_SgLang_2092", "02_SgLang_2092", "03_SgLang_2092"], "sgl2092"),
]

for rel, wants, label in DUMPS:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("!! not found:", rel)
        continue
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        ev = json.load(f)
    files = ev.get("files") or {}
    print("##### %s -> %d files" % (label, len(files)))
    for name, meta in files.items():
        if not wants:
            print("   -", name)
            continue
        if not any(w in name for w in wants):
            continue
        lines = meta.get("lines") if isinstance(meta, dict) else None
        if lines is None:
            print("   -", name, "| keys:", list(meta.keys()))
            continue
        cl = [l for l in lines]
        print("  ===== %s (%d lines) tail40 =====" % (name, len(cl)))
        for i, l in enumerate(cl[-40:]):
            print("    L%d %s" % (len(cl) - 40 + i + 1, (l if isinstance(l, str) else json.dumps(l, ensure_ascii=False))[:200]))
