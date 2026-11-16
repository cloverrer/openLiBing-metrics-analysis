# -*- coding: utf-8 -*-
"""只读探针：打印 SgLang（或指定组件）pending 记录的 github 元数据与证据清单。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402

AR = ROOT / "out" / "archive"


def main():
    day = sys.argv[1]
    want = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    day_dir = AR / day[:4] / day[:7] / day
    for comp in sorted(day_dir.iterdir()):
        if not comp.is_dir() or comp.name.startswith("_"):
            continue
        if want and want not in comp.name.lower():
            continue
        for pipe in sorted(comp.iterdir()):
            if not (pipe / "pipeline.json").is_file():
                continue
            doc = pipeline_doc.load(pipe) or {}
            for rec in doc.get("records") or []:
                if (rec.get("analysis") or {}).get("status") != "pending":
                    continue
                print("=" * 60)
                print("REC", rec.get("recordId"), "| ftt=", rec.get("failedTaskType"))
                ev = rec.get("evidence") or {}
                print("  files:", len(ev.get("files") or []), "missing:", json.dumps(ev.get("missing"), ensure_ascii=False))
                gh = ev.get("github") or {}
                if gh:
                    print("  github runId:", gh.get("runId"), "| title:", gh.get("displayTitle"),
                          "| mode:", gh.get("mode"), "| total:", gh.get("totalJobs"))
                    for j in (gh.get("failedJobs") or []):
                        print("    FAILJOB:", json.dumps(j, ensure_ascii=False)[:220])
                    print("    gh missing:", json.dumps(gh.get("missing"), ensure_ascii=False)[:300])
                    print("    gh note:", json.dumps(gh.get("evidenceNote"), ensure_ascii=False)[:300])
                for f in (ev.get("files") or []):
                    print("    file:", f)


if __name__ == "__main__":
    main()
