# -*- coding: utf-8 -*-
"""按行窗口读证据原文（只读）—— 第 8 步（AI）取证的唯一入口。

背景：证据原文（job_logs/ case_logs/ github_logs/）已逐行内嵌进流水线目录的
`pipeline.evidence.json`，磁盘上没有散文件了。所以「读日志第 138 行」不能再
`sed -n 138p job_logs/x.log`，要走这个脚本 —— 它按**原始行号**取行，行号与各步
JSON 里的引用（`job_logs/x.log:L138`）完全一致，取到的正文可以直接写进 cites。

用法:
  python tools/read_evidence.py --record "组件|流水线#构建号" --list
  python tools/read_evidence.py --record "组件|流水线#构建号" --path job_logs/01_x.log --lines 120-200
  python tools/read_evidence.py --dir archive/2026/2026-11/2026-11-06/A/B --grep "error|failed" --ctx 2
  python tools/read_evidence.py --record "..." "job_logs/01_x.log:L138"   # 与 cites 写法一致

输出纪律：单次回显 ≤ 100 行（--max 默认 80），避免输出过长中断；行号列左侧的 L 为原始行号。
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import pipeline_doc  # noqa: E402
from lib.paths import (ARCHIVE_ROOT, OUT_DIR, iter_archive_days,  # noqa: E402
                       iter_scoped_pipelines, rel)

DEFAULT_MAX = 80            # 单次最多回显行数
GREP_MAX = 30               # --grep 最多命中条数
LINE_CHAR_MAX = 600         # 单行最长回显字符（压缩过的 html 一行能顶几千字）
LIST_MAX = 60               # --list 最多列出证据份数
CITE_RE = re.compile(r"^(?P<path>.+?):L?(?P<l1>\d+)(?:\s*[-~]\s*L?(?P<l2>\d+))?$")


def norm_id(s):
    """recordId 归一化：「组件|流水线#构建号」，同时容忍 / 与空白写法。"""
    return str(s or "").replace("/", "|").replace(" ", "")


def resolve_dir(spec):
    """把 --dir / --record 解析成流水线目录（找不到返回 None）。

    目录可以写成三种样子：绝对路径、相对 cwd 的路径、相对 out/ 的路径
    （也就是 verify/list_pending 打印的 `archive/2026/…` 那种写法）。
    """
    if not spec:
        return None
    p = Path(spec)
    cands = [p] if p.is_absolute() else [p, ROOT / p, OUT_DIR / p, ARCHIVE_ROOT / p]
    for cand in cands:
        if cand.is_dir() and pipeline_doc.path_of(cand).is_file():
            return cand.resolve()
    if "#" not in str(spec) and "|" not in str(spec):
        return None
    want = norm_id(spec)
    for _date, day_dir in iter_archive_days():
        for _comp, _pipe, pdir in iter_scoped_pipelines(day_dir):
            doc = pipeline_doc.load(pdir) or {}
            for rec in doc.get("records") or []:
                if norm_id(rec.get("recordId")) == want:
                    return pdir
    return None


def parse_lines(s):
    """把 '120' / '120-200' / 'L120-L200' 解析成 (l1, l2, l2 是否给了)。"""
    nums = [int(x) for x in re.findall(r"\d+", str(s or ""))]
    if not nums:
        return 1, None, False
    if len(nums) == 1:
        return nums[0], None, False
    return nums[0], nums[1], True


def ev_entries(pdir):
    """{相对路径: 条目}：优先内嵌正文，老归档退回磁盘清单。"""
    ent = pipeline_doc.evidence_entries(pdir)
    if ent:
        return ent
    out = {}
    for pre in pipeline_doc.EVIDENCE_PREFIX:
        d = Path(pdir) / pre.rstrip("/")
        if not d.is_dir():
            continue
        for f in sorted(d.rglob("*")):
            if f.is_file():
                try:
                    n = len(f.read_text(encoding="utf-8", errors="replace").splitlines())
                except OSError:
                    n = 0
                out[f.relative_to(pdir).as_posix()] = {"lineCount": n, "bytes": f.stat().st_size}
    return out


def read_window(pdir, rel_path, l1, l2, max_lines):
    """取原文第 l1~l2 行，返回 (行列表, 起始行号, 总行数, 实际截止行号)。"""
    rel_path = str(rel_path or "").replace("\\", "/").strip().lstrip("./")
    text, ok = pipeline_doc.evidence_window(pdir, rel_path, l1, l2, max_lines=max_lines)
    if ok:
        lines = text.split("\n")
        total = pipeline_doc.evidence_line_count(pdir, rel_path)
        return lines, l1, total, l1 + len(lines) - 1
    # 老归档：正文还在磁盘
    p = Path(pdir) / rel_path
    if not p.is_file():
        return None, l1, 0, l1 - 1
    try:
        raw = p.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return None, l1, 0, l1 - 1
    if raw and raw[-1] == "":
        raw = raw[:-1]
    total = len(raw)
    if l1 > total:
        return None, l1, total, l1 - 1
    end = min(l2 or l1, total, l1 + max(1, max_lines) - 1)
    return raw[l1 - 1:end], l1, total, end


def cut(s, n=LINE_CHAR_MAX):
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "…"


def print_rows(rows, start, total, end):
    for i, line in enumerate(rows, start):
        print("L%-6d| %s" % (i, cut(line)))
    print("… 第 %d~%d 行 / 共 %d 行（引用写法：<相对路径>:L%d）"
          % (start, end, total, start))


def cmd_list(pdir, rows):
    print("== 证据清单: %s（%d 份）" % (rel(pdir), len(rows)))
    if not rows:
        print("   （本目录没有证据正文）")
        return 0
    print("%-58s %8s %10s" % ("相对路径（可直接写进 cites）", "行数", "字节"))
    for k in sorted(rows)[:LIST_MAX]:
        v = rows[k] or {}
        print("%-58s %8s %10s" % (cut(k, 58), v.get("lineCount") or 0, v.get("bytes") or 0))
    if len(rows) > LIST_MAX:
        print("… 共 %d 份，已列前 %d 份（--grep 直接在全部证据里搜）" % (len(rows), LIST_MAX))
    return 0


def cmd_grep(pdir, rows, pattern, ctx, max_lines):
    try:
        rx = re.compile(pattern)
    except re.error as exc:
        print("!! 正则不合法: %s" % exc)
        return 1
    print("== 证据检索: %s（%d 份 / 正则 %r）" % (rel(pdir), len(rows), pattern))
    hits = 0
    for k in sorted(rows):
        total = int((rows[k] or {}).get("lineCount") or 0)
        if not total:
            continue
        step = max(1, max_lines)
        pos = 1
        while pos <= total and hits < GREP_MAX:
            got, start, tot, end = read_window(pdir, k, pos, min(pos + step - 1, total), step)
            if not got:
                break
            for off, line in enumerate(got):
                if hits >= GREP_MAX:
                    break
                if rx.search(line):
                    hits += 1
                    no = start + off
                    print("[%s:L%d] %s" % (k, no, cut(line, 200)))
                    if ctx:
                        lo, hi = max(1, no - ctx), min(tot, no + ctx)
                        around, _s, _t, _e = read_window(pdir, k, lo, hi, 2 * ctx + 1)
                        for j, near in enumerate(around or [], lo):
                            print("    L%-6d| %s" % (j, cut(near, 200)))
                    break
            pos = end + 1
        if hits >= GREP_MAX:
            break
    if not hits:
        print("（没有命中「%s」；--list 看有哪些证据文件）" % pattern)
    else:
        print("… 共命中 %d 处（上限 %d）；取上下文用 --path + --lines 再读" % (hits, GREP_MAX))
    return 0


def main():
    ap = argparse.ArgumentParser(description="按行窗口读归档里的证据原文（内嵌在 pipeline.evidence.json）")
    ap.add_argument("cite", nargs="?", help="与 cites 同写法：job_logs/x.log:L138 或 job_logs/x.log:10-40")
    ap.add_argument("--record", dest="record", help="recordId（组件|流水线#构建号）")
    ap.add_argument("--dir", dest="dir", help="流水线目录（归档路径或绝对路径）")
    ap.add_argument("--path", help="证据相对路径（job_logs/… / case_logs/… / github_logs/…）")
    ap.add_argument("--lines", default="1", help="行窗口：138 / 120-200 / L120-L200（默认第 1 行起）")
    ap.add_argument("--grep", help="在证据里按正则搜行号（配合 --path 可只搜一份）")
    ap.add_argument("--ctx", type=int, default=0, help="--grep 时额外回显的上下文行数")
    ap.add_argument("--max", type=int, default=DEFAULT_MAX, help="单次最多回显行数（默认 %d）" % DEFAULT_MAX)
    ap.add_argument("--list", action="store_true", help="只列证据清单（路径/行数/字节）")
    args = ap.parse_args()

    spec = args.dir or args.record
    rel_path, l1, l2 = args.path, None, None
    if args.cite:
        m = CITE_RE.match(args.cite.strip())
        if not m:
            print("!! 引用写法不对：应形如 job_logs/x.log:L138（收到 %r）" % args.cite)
            return 1
        rel_path = m.group("path")
        l1 = int(m.group("l1"))
        l2 = int(m.group("l2") or l1)
    if l1 is None:
        l1, l2, _given = parse_lines(args.lines)
    pdir = resolve_dir(spec) if spec else None
    if spec and not pdir:
        print("!! 找不到流水线目录: %s（用 python tools/list_pending.py 查 recordId）" % spec)
        return 1
    if pdir is None:
        # 没给目录时按引用里的路径在归档里找（一份证据可能被同目录多处引用，命中即用）
        if not rel_path:
            print("!! 需要 --record / --dir 指定流水线目录（或给一个 cites 引用）")
            return 1
        for _date, day_dir in iter_archive_days():
            for _comp, _pipe, cand in iter_scoped_pipelines(day_dir):
                if pipeline_doc.evidence_line_count(cand, rel_path) > 0:
                    pdir = cand
                    break
            if pdir:
                break
        if not pdir:
            print("!! 全归档里都没有这份证据: %s" % rel_path)
            return 1

    rows = ev_entries(pdir)
    if args.grep:
        # --path 给了就只搜那一份，没给就搜本目录全部证据
        scope = ({rel_path.replace("\\", "/").strip(): rows[rel_path.replace("\\", "/").strip()]}
                 if rel_path and rel_path.replace("\\", "/").strip() in rows else rows)
        if rel_path and scope is rows:
            print("!! 本目录没有这份证据: %s（--list 看可用路径）" % rel_path)
            return 1
        return cmd_grep(pdir, scope, args.grep, args.ctx, args.max)
    if args.list or not rel_path:
        return cmd_list(pdir, rows)

    rel_path = rel_path.replace("\\", "/").strip()
    got, start, total, end = read_window(pdir, rel_path, l1, l2, args.max)
    if got is None:
        print("!! 取不到证据正文: %s（共 %d 行；--list 看可用路径）" % (rel_path, total))
        return 1
    print("== %s : L%d~L%d（共 %d 行，本目录 %s）" % (rel_path, start, end, total, rel(pdir)))
    print_rows(got, start, total, end)
    return 0


if __name__ == "__main__":
    sys.exit(main())
