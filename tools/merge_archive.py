# -*- coding: utf-8 -*-
"""把流水线归档收成「一个目录两份文件」：pipeline.json + pipeline.evidence.json。

两档合并各管一半，可分开跑、也可一次跑完：

  A 档（JSON）   `_manifest.json` + 8 份 step + `records/run_*.json` -> `pipeline.json`
                 （schema=pipeline/1），并把 `analysis.cites` 里指向老文件的引用改写成
                 `pipeline.json:L<行号>`，同步 `_day.json` 的 `pipelines[].manifest`

  B 档（证据）   `job_logs/` `case_logs/` `github_logs/` 下的原文逐行内嵌进
                 `pipeline.evidence.json`（schema=pipeline-evidence/1），
                 然后删掉这几个散文件目录 —— 键仍是原相对路径、行号仍是原文行号，
                 所以各步 JSON / 执行记录 / AI 结论里的 `文件:行号` 一个字都不用改

一次采集里同一条流水线会落 9 份 JSON 外加若干条记录、再外加几十份日志/报告 ——
一天 49 条流水线就是 500 多个文件。本脚本既是 A/B 两档的迁移工具，采集之后也可手动补跑。

删除前可用 --backup 打一份 zip；不想删证据散文件就用 --keep-evidence-files。

用法::

  python tools/merge_archive.py --dry-run                 # 只算账，不落盘
  python tools/merge_archive.py --backup                  # 先打 zip 备份再合并全部
  python tools/merge_archive.py --date 2026-11-11 --backup
  python tools/merge_archive.py --keep-legacy             # 合并但保留老 JSON（对比用）
  python tools/merge_archive.py --keep-evidence-files     # 证据进了 JSON，但散文件不删
  python tools/merge_archive.py --only evidence           # 只做证据合并（JSON 已合并过）
  python tools/merge_archive.py --force                   # 已有 pipeline.json 也重算覆盖
"""
import argparse
import datetime
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc                                   # noqa: E402
from lib.paths import (ARCHIVE_ROOT, STATE_DIR, iter_archive_days,  # noqa: E402
                       iter_archive_pipelines, iter_scoped_pipelines, rel)

# 引用形态：'records/run_137.json' / 'records/run_168.json:L59' / '命中 records/run_168.json:L59'
# 前缀允许是完整相对路径，尾部允许带行号或行号区间（:L59 / :59 / :L59-72 / :59-72）。
REC_RE = re.compile(r"(?:[^\s\"'，。；、]*/)?records/run_(\d+)\.json(?::L?(\d+)(?:[-~]L?(\d+))?)?")
# 步骤文件 / 清单引用只在「整串就是引用」时改写，不碰正文里顺手提到的字样
STEP_TAIL_RE = re.compile(r"(?:^|/)(step_[0-9a-z_]+)\.json$")
MAN_TAIL_RE = re.compile(r"(?:^|/)(_manifest\.json)$")


# ------------------------------------------------------------------ 读老结构
def read_legacy(pdir):
    """读一个老结构目录，返回 (manifest, steps, [(源文件, 记录)], [将被删除的文件])。"""
    pdir = Path(pdir)
    man, man_files = {}, []
    mp = pdir / "_manifest.json"
    if mp.is_file():
        try:
            man = json.loads(mp.read_text(encoding="utf-8"))
            man_files.append(mp)
        except (ValueError, OSError):
            man = {}
    steps, step_files = {}, []
    for fname, step in pipeline_doc.LEGACY_FILES:
        f = pdir / fname
        if not f.is_file():
            continue
        try:
            steps[step] = json.loads(f.read_text(encoding="utf-8"))
            step_files.append(f)
        except (ValueError, OSError):
            continue
    pairs, rec_files = [], []
    rdir = pdir / "records"
    if rdir.is_dir():
        for f in sorted(rdir.glob("run_*.json")):
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            pairs.append((f, rec))
            rec_files.append(f)
    return man, steps, pairs, man_files + step_files + rec_files


# ------------------------------------------------------------------ 引用改写
def _line_of(lines, needle):
    for i, line in enumerate(lines):
        if needle in line:
            return i + 1
    return None


def rewrite_cites(payload, rec_src):
    """把 `records/run_*.json[:L…]` 引用改写成 `pipeline.json:L<行号>`，返回 (payload, 统计)。

    `rec_src` 是 run -> (记录 dict, 老文件各行原文)。行号怎么算准：老文件顶部有 12 行
    `_doc`（合并时剥掉），所以「老文件第 n 行」要先减掉这段头部，再对齐到合并后的
    「记录起始行 + 记录内第 k 行」。换算完逐行比对两边去空白内容，对不上就退回该记录
    的 `recordId` 行 —— 宁可粗一点，也不给一个指错的锚。
    """
    lines = json.dumps(payload, ensure_ascii=False, indent=1).split("\n")
    where = {}                       # recordId -> (起始行, 记录内各行, recordId 行)
    for rec in payload.get("records") or []:
        rid = rec.get("recordId")
        if rid in (None, ""):
            continue
        mark = '"recordId": ' + json.dumps(rid, ensure_ascii=False)
        body = json.dumps(rec, ensure_ascii=False, indent=1).split("\n")
        idx = next((i + 1 for i, ln in enumerate(body) if mark in ln), None)
        at = _line_of(lines, mark)
        if not idx or not at:
            continue
        start = at - (idx - 1)
        if start < 1 or lines[start - 1].strip() != "{":
            start = at
        where[rid] = (start, body, at)
    step_line = {name: _line_of(lines, '"%s": {' % name)
                 for name in (payload.get("steps") or {})}

    stat = {"cites": 0, "left": 0}

    def anchor(rec, inner, run):
        """记录内的锚点行：给了行号就换算到合并后的同一行，否则指 recordId 行。"""
        info = where.get((rec or {}).get("recordId"))
        if not info:
            return None
        start, body, at = info
        if not inner:
            return at
        n = int(inner)
        src = (rec_src.get(run) or (None, None))[1]
        if not src or not (1 <= n <= len(src)):
            return at
        head = len(src) - len(body) + 1        # 老文件里被 _doc 占掉的头部行数
        k = n - head + 1                       # 换算成「记录内第几行」
        if 1 <= k <= len(body) and src[n - 1].strip() == body[k - 1].strip():
            return start + k - 1
        return at

    def fix_str(s):
        def sub(m):
            run = int(m.group(1))
            rec = (rec_src.get(run) or (None,))[0]
            ln = anchor(rec, m.group(2), run) if rec else None
            if not ln:
                stat["left"] += 1
                return m.group(0)
            stat["cites"] += 1
            return "pipeline.json:L%d" % ln

        s2 = REC_RE.sub(sub, s)
        m = STEP_TAIL_RE.search(s2)
        if m and not REC_RE.search(s):
            ln = step_line.get(m.group(1))
            if ln:
                stat["cites"] += 1
                return "pipeline.json:L%d" % ln
            return s2
        if MAN_TAIL_RE.search(s2) and not REC_RE.search(s):
            stat["cites"] += 1
            return "pipeline.json:L1"
        return s2

    def walk(obj):
        if isinstance(obj, str):
            return fix_str(obj)
        if isinstance(obj, list):
            for i, v in enumerate(obj):
                obj[i] = walk(v)
            return obj
        if isinstance(obj, dict):
            for k, v in obj.items():
                obj[k] = walk(v)
            return obj
        return obj

    return walk(payload), stat


# ------------------------------------------------------------------ 备份
class Backup:
    """把即将删除的老 JSON 打进一个 zip（条目路径相对 out/archive/）。"""

    def __init__(self, enabled):
        self.enabled = enabled
        self.zf = None
        self.path = None
        self.n = 0
        self.bytes = 0

    def add(self, files):
        if not self.enabled or not files:
            return
        if self.zf is None:
            STATE_DIR.joinpath("backup").mkdir(parents=True, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.path = STATE_DIR / "backup" / ("archive-merge-%s.zip" % ts)
            self.zf = zipfile.ZipFile(str(self.path), "w", zipfile.ZIP_DEFLATED)
        for f in files:
            try:
                arc = Path(f).resolve().relative_to(ARCHIVE_ROOT.resolve()).as_posix()
            except ValueError:
                arc = Path(f).as_posix()
            self.zf.write(str(f), arc)
            self.n += 1
            self.bytes += Path(f).stat().st_size

    def close(self):
        if self.zf is not None:
            self.zf.close()
            self.zf = None


# ------------------------------------------------------------------ 单目录合并
def merge_one(pdir, dry_run=False, backup=None, keep_legacy=False, force=False):
    """合并一个流水线目录，返回统计 dict（无需合并时返回 None）。"""
    pdir = Path(pdir)
    if pipeline_doc.has_pipeline(pdir) and not force:
        return {"skip": "already"}
    man, steps, pairs, old_files = read_legacy(pdir)
    if not steps and not pairs:
        return None

    rec_src, recs = {}, []
    for f, rec in pairs:
        recs.append(rec)
        try:
            run = int(f.stem.split("_")[1])
        except (IndexError, ValueError):
            continue
        # 老文件原文（含顶部 _doc）留作行号换算的基准，合并后就地消失
        try:
            rec_src[run] = (rec, f.read_text(encoding="utf-8").split("\n"))
        except OSError:
            rec_src[run] = (rec, None)

    payload = pipeline_doc.assemble(man, steps, recs)
    payload, stat = rewrite_cites(payload, rec_src)
    payload.setdefault("source", {})
    if isinstance(payload["source"], dict):
        payload["source"]["merge"] = {
            "from": "9 份 JSON + records/run_<构建号>.json",
            "to": pipeline_doc.NAME,
            "files": len(old_files),
            "layout": "见本文件 steps / stepIndex / records",
        }

    before = len(old_files)
    before_bytes = sum(f.stat().st_size for f in old_files)
    after_bytes = len(json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8"))

    if not dry_run:
        if backup is not None:
            backup.add(old_files)
        pipeline_doc.save(pdir, payload)
        if not keep_legacy:
            for f in old_files:
                try:
                    f.unlink()
                except OSError:
                    pass
            rdir = pdir / "records"
            if rdir.is_dir() and not any(rdir.iterdir()):
                try:
                    rdir.rmdir()
                except OSError:
                    pass

    return {"files": before, "bytes": before_bytes, "after": after_bytes,
            "cites": stat["cites"], "left": stat["left"], "records": len(recs)}


# ------------------------------------------------------------------ 证据合并（B 档）
def evidence_files_of(pdir):
    """列出流水线目录下证据目录里的全部文件（相对路径，正斜杠）。"""
    pdir = Path(pdir)
    out = []
    for pre in pipeline_doc.EVIDENCE_PREFIX:
        d = pdir / pre.rstrip("/")
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if f.is_file():
                out.append(f.relative_to(pdir).as_posix())
    return out


def merge_evidence(pdir, dry_run=False, backup=None, keep_files=False):
    """把证据原文内嵌进 pipeline.evidence.json，再删掉散文件（没有证据时返回 None）。

    删除的**唯一**前提是「该路径的正文确实已在内嵌文档里，且能逐字节还原（sha1 对得上）」
    —— 逐份核对后再删，任何一份没内嵌成功或校验不过就留在磁盘上并计入 `kept`，
    绝不为了目录整洁丢原文。
    """
    pdir = Path(pdir)
    rel_paths = evidence_files_of(pdir)
    if not rel_paths:
        return None
    before_bytes = sum((pdir / rp).stat().st_size for rp in rel_paths)
    st = {"files": len(rel_paths), "bytes": before_bytes, "embedded": None,
          "lines": 0, "missing": [], "kept": [], "deleted": 0}
    if dry_run:
        return st

    nf, nb, nl, miss = pipeline_doc.embed_evidence(pdir, rel_paths)
    st.update({"embedded": nf, "embeddedBytes": nb, "lines": nl, "missing": miss})
    ok = [rp for rp in rel_paths
          if rp not in miss and pipeline_doc.evidence_verified(pdir, rp)]
    st["kept"] = [rp for rp in rel_paths if rp not in ok]
    if keep_files:
        return st

    if backup is not None:
        backup.add([pdir / rp for rp in ok])
    for rp in ok:
        try:
            (pdir / rp).unlink()
            st["deleted"] += 1
        except OSError:
            st["kept"].append(rp)
    # 清空目录（先深后浅，非空就留着，不硬删）
    for pre in pipeline_doc.EVIDENCE_PREFIX:
        d = pdir / pre.rstrip("/")
        if not d.is_dir():
            continue
        subs = sorted((x for x in d.rglob("*") if x.is_dir()),
                      key=lambda x: len(x.parts), reverse=True)
        for sub in subs:
            try:
                sub.rmdir()
            except OSError:
                pass
        try:
            d.rmdir()
        except OSError:
            pass
    return st


# ------------------------------------------------------------------ 日汇总同步
def sync_day(day_dir, dry_run=False):
    """把 _day.json 里 pipelines[].manifest 指到 pipeline.json；返回改动条数。

    dry-run 时 pipeline.json 还没写出来，按「有 _manifest.json 就等着被合并」判断。
    """
    p = Path(day_dir) / "_day.json"
    if not p.is_file():
        return 0
    try:
        dj = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return 0
    n = 0
    for item in dj.get("pipelines") or []:
        if not isinstance(item, dict):
            continue
        # item["path"] 形如 archive/2026/2026-11/2026-11-06/<组件>/<流水线>
        parts = [x for x in str(item.get("path") or "").replace("\\", "/").split("/") if x]
        if len(parts) < 2:
            continue
        pdir = Path(day_dir) / parts[-2] / parts[-1]
        if not pipeline_doc.has_pipeline(pdir):
            if not (dry_run and (pdir / "_manifest.json").is_file()):
                continue
        want = rel(pipeline_doc.path_of(pdir))
        if item.get("manifest") != want or item.get("file") != want:
            item["manifest"] = want
            item["file"] = want
            item["layout"] = pipeline_doc.SCHEMA
            n += 1
    if n and not dry_run:
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(dj, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(p))
    return n


# ------------------------------------------------------------------ 主流程
def main():
    ap = argparse.ArgumentParser(description="流水线归档合并（JSON + 证据原文 -> 两份文件）")
    ap.add_argument("--date", help="只处理某一天（yyyy-mm-dd）")
    ap.add_argument("--dry-run", action="store_true", help="只算账，不写盘不删文件")
    ap.add_argument("--backup", action="store_true", help="删除前把老文件打包到 out/state/backup/")
    ap.add_argument("--keep-legacy", action="store_true", help="合并后保留老 JSON")
    ap.add_argument("--keep-evidence-files", action="store_true",
                    help="证据内嵌进 JSON，但保留 job_logs/ case_logs/ github_logs/ 散文件")
    ap.add_argument("--only", choices=("all", "json", "evidence"), default="all",
                    help="只做其中一档（json=A 档，evidence=B 档），默认两档都做")
    ap.add_argument("--force", action="store_true", help="已有 pipeline.json 也重算覆盖")
    args = ap.parse_args()
    do_json = args.only in ("all", "json")
    do_ev = args.only in ("all", "evidence")

    backup = Backup(args.backup)
    tot = {"days": 0, "pipes": 0, "skip": 0, "files": 0, "after": 0,
           "bytes": 0, "afterBytes": 0, "records": 0, "cites": 0, "left": 0, "dayFix": 0,
           "evDirs": 0, "evFiles": 0, "evBytes": 0, "evLines": 0, "evDeleted": 0,
           "evMissing": 0, "evKept": 0}
    rows, ev_rows = [], []
    try:
        for date, day_dir in iter_archive_days():
            if args.date and date != args.date:
                continue
            tot["days"] += 1
            scoped = {(c, p) for c, p, _ in iter_scoped_pipelines(day_dir)}
            for comp, pipe, pdir in iter_archive_pipelines(day_dir):
                if do_json:
                    st = merge_one(pdir, dry_run=args.dry_run, backup=backup,
                                   keep_legacy=args.keep_legacy, force=args.force)
                    if st and st.get("skip"):
                        tot["skip"] += 1
                    elif st:
                        tot["pipes"] += 1
                        tot["files"] += st["files"]
                        tot["after"] += 1
                        tot["bytes"] += st["bytes"]
                        tot["afterBytes"] += st["after"]
                        tot["records"] += st["records"]
                        tot["cites"] += st["cites"]
                        tot["left"] += st["left"]
                        rows.append((date, comp, pipe, st["files"],
                                     "stale" if (comp, pipe) not in scoped else "",
                                     st["cites"]))
                if do_ev:
                    es = merge_evidence(pdir, dry_run=args.dry_run, backup=backup,
                                        keep_files=args.keep_evidence_files)
                    if not es:
                        continue
                    tot["evDirs"] += 1
                    tot["evFiles"] += es["files"]
                    tot["evBytes"] += es["bytes"]
                    tot["evLines"] += es["lines"] or 0
                    tot["evDeleted"] += es["deleted"]
                    tot["evMissing"] += len(es["missing"])
                    tot["evKept"] += len(es["kept"])
                    if es["missing"] or es["kept"]:
                        ev_rows.append((date, comp, pipe, len(es["missing"]),
                                        len(es["kept"])))
            n = sync_day(day_dir, dry_run=args.dry_run)
            tot["dayFix"] += n
            if n:
                rows.append((date, "-", "_day.json", 0, "manifest->pipeline.json", n))
    finally:
        backup.close()

    print("== 归档合并%s ==" % ("（dry-run，未落盘）" if args.dry_run else ""))
    print("日目录 %d | 合并流水线 %d 个 | 已合并跳过 %d 个 | 执行记录 %d 条"
          % (tot["days"], tot["pipes"], tot["skip"], tot["records"]))
    if do_json:
        print("JSON 文件 %d -> %d 个（少 %d）| 体积 %.2f MB -> %.2f MB（省 %.2f MB）"
              % (tot["files"], tot["after"], tot["files"] - tot["after"],
                 tot["bytes"] / 1048576.0, tot["afterBytes"] / 1048576.0,
                 (tot["bytes"] - tot["afterBytes"]) / 1048576.0))
        print("引用改写 %d 处（未定位 %d 处）| _day.json 修正 %d 条"
              % (tot["cites"], tot["left"], tot["dayFix"]))
    if do_ev:
        print("证据目录 %d 个 | 证据文件 %d 份（%.2f MB / %d 行）| 内嵌后删除 %d 份"
              % (tot["evDirs"], tot["evFiles"], tot["evBytes"] / 1048576.0,
                 tot["evLines"], tot["evDeleted"]))
        if args.keep_evidence_files:
            print("已按 --keep-evidence-files 保留证据散文件")
        elif args.dry_run:
            print("dry-run：以上为待内嵌的账，未写盘、未删文件")
        elif tot["evMissing"] or tot["evKept"]:
            print("!! 未内嵌 %d 份 / 保留未删 %d 份（正文没进 JSON 的原文一律留在磁盘）"
                  % (tot["evMissing"], tot["evKept"]))
            for r in ev_rows[:10]:
                print("  %s %-14s %-22s 未内嵌 %d / 保留 %d" % r)
        elif tot["evFiles"]:
            print("核对通过：证据原文全部内嵌且 sha1 可逐字节还原，散文件已清理")
    if backup.path:
        print("备份: %s（%d 个文件，%.2f MB）"
              % (backup.path, backup.n, backup.bytes / 1048576.0))
    if args.dry_run and rows:
        print("-- 明细（前 20 条）--")
        for r in rows[:20]:
            print("  %s %-14s %-22s %2d -> 1 %s %s"
                  % (r[0], r[1], r[2], r[3], r[4], ("改写引用 %d" % r[5]) if r[5] else ""))
        if len(rows) > 20:
            print("  ... 其余 %d 条" % (len(rows) - 20))
    return 0


if __name__ == "__main__":
    sys.exit(main())
