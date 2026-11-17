# -*- coding: utf-8 -*-
"""待分析记录的纯文本取证包（只读）—— 第 8 步（AI）的唯一输入。

一条命令把「清单 + 每条记录的失败任务 + 关键报错行 + 少量上下文」压成一份**纯文本**，
AI 只读这一份、只写一份纯文本结论，不再逐条 `--show` / `--grep` 往返（省交互轮次、省 token）：

    python tools/digest_pending.py                       # 直接看回显（推荐，AI 一次拿到全部输入）
    python tools/digest_pending.py --out out/state/pending_digest.txt
    python tools/digest_pending.py --record "组件|流水线#构建号"   # 只打一条（深挖某条时用）
    python tools/digest_pending.py --max-records 8 --ev-lines 24  # 记录多时分批

输出纪律：
  · 证据行一律带**原始行号**（`job_logs/x.log:L902`），可直接写进结论的 cites；
  · 默认每条记录最多展开 3 个报错点、合计 12 行原文、末尾附 5 条失败用例；
    记录多时用 `--max-records` / `--record` 分批，不要整读 pipeline.json / evidence.json。
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import list_pending as lp                      # noqa: E402  复用清单口径（唯一真相）
import read_evidence as rv                      # noqa: E402  复用行窗口取数
from lib.paths import ARCHIVE_ROOT              # noqa: E402

MSG_MAX = 3          # 每条记录展开几个报错点
EV_CTX = 2           # 报错点上下各取几行
EV_MAX = 12          # 每条记录合计最多回显几行原文
TAIL_LINES = 14      # 任务有日志但抽不出定位行时，附日志尾部行数
TEXT_MAX = 200       # 单行最长字符
CASE_MAX = 5         # 列出几条失败用例
HEAD = """\
# ===== 待 AI 根因分析 · 纯文本取证包 =====
# 分析只做两件事：① 定位（哪一行原文是失败点，写进 cites）② 定性（分类 + 根因 + 建议）。
# 结论写成纯文本块（比 JSON 省 token，不用转义换行），交给 write_analysis.py 写回：
#
#   === 组件|流水线#构建号
#   分类: 十选一（见下）
#   简述: 40 字以内「是什么坏了」
#   错误: 最能说明问题的那行报错原文（必须能在「引用」那一行里找到）
#   根因: 自由多行文本：在哪失败 → 为什么 → 所以谁去修
#   建议: 动手做什么 + 空行 + 验证方式：复跑什么、通过标准是什么
#   引用: job_logs/x.log:L902, job_logs/x.log:L910
#
#   python tools/write_analysis.py --file out/state/analysis_result.txt --dry-run
#   python tools/write_analysis.py --file out/state/analysis_result.txt
#   分类白名单：代码编译错误 / 单元测试失败 / 依赖/环境缺失 / 网络/下载失败 / 资源不足 /
#               超时 / 权限问题 / 配置/参数错误 / 基础设施/平台 / 无法判定
# ===========================================
"""


def cut(s, n=TEXT_MAX):
    s = str("" if s is None else s).replace("\r", " ").replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


def pipe_dir(x):
    d = x["date"]
    return ARCHIVE_ROOT / d[:4] / d[:7] / d / x["component"] / x["pipeline"]


def focus_points(rec):
    """报错点：优先「有行号 + 来自任务日志」的，其次用例/子任务，最后只有正文的封装文案。

    返回 [{label, level, source, line, text}]（已去重、已按优先级排序）。
    """
    msgs = rec.get("errorMessages") or []
    rank = {"LOG": 0, "ERROR": 1, "CASE": 2, "SUBTASK": 3, "STEP": 8, "JOB": 9}
    pts, seen = [], set()
    for m in msgs:
        if not isinstance(m, dict):
            continue
        src = str(m.get("source") or "").strip()
        line = m.get("line")
        text = str(m.get("text") or m.get("message") or "").strip()
        if not text:
            continue
        key = (src, line, text[:60])
        if key in seen:
            continue
        seen.add(key)
        pts.append({"level": str(m.get("level") or ""), "source": src,
                    "line": line if isinstance(line, int) else None,
                    "case": m.get("case"), "subTask": m.get("subTask"),
                    "task": m.get("task"), "text": text})
    pts.sort(key=lambda p: (rank.get(p["level"], 5), 0 if p["line"] else 1))
    return pts


def merge_ranges(lines, ctx):
    """把若干目标行的 [行-ctx, 行+ctx] 合并成不重叠的区间，避免同一段原文反复回显。"""
    rs = sorted((max(1, ln - ctx), ln + ctx) for ln in sorted(set(lines)))
    out = []
    for a, b in rs:
        if out and a <= out[-1][1] + 1:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def ev_source(pdir, src, targets, budget):
    """读同一份日志上多个报错点的上下文（区间已合并）；返回 (行文本列表, 消耗行数)。"""
    out, used = [], 0
    for a, b in merge_ranges(targets, EV_CTX):
        if used >= budget:
            out.append("    … 本记录证据行已达上限 %d 行（深挖用 --record + tools/read_evidence.py）"
                       % budget)
            break
        want = min(b - a + 1, budget - used)
        lines, st, total, end = rv.read_window(pdir, src, a, a + want - 1, want)
        if not lines:
            continue
        out.append("    · %s:L%d~L%d（该文件共 %d 行）" % (src, st, st + len(lines) - 1, total))
        out += ["    L%-6d| %s" % (n, cut(t)) for n, t in enumerate(lines, st)]
        used += len(lines)
    return out, used


def tail_block(pdir, src, budget):
    total = rv.pipeline_doc.evidence_line_count(pdir, src)
    if total <= 0 or budget <= 0:
        return [], 0
    start = max(1, total - min(TAIL_LINES, budget) + 1)
    lines, st, _t, _e = rv.read_window(pdir, src, start, total, total - start + 1)
    if not lines:
        return [], 0
    out = ["    · %s（该任务无定位行，附日志尾部 L%d~L%d / 共 %d 行）"
           % (src, st, st + len(lines) - 1, total)]
    out += ["    L%-6d| %s" % (n, cut(t)) for n, t in enumerate(lines, st)]
    return out, len(lines)


def one_block(i, n, x, ev_lines):
    rec = x["record"]
    pdir = pipe_dir(x)
    lt = rec.get("light") or {}
    dims = "/".join(x.get("affects") or []) or "--"
    va = lt.get("vaRate")
    bs = lt.get("bsRate")
    fmt = lambda v: ("--" if v is None else "%.0f%%" % (float(v) * 100))
    out = ["─" * 100,
           "[%d/%d] %s" % (i, n, rec.get("recordId")),
           "  组件/流水线: %s / %s（%s）" % (x["component"], x["pipeline"], rec.get("pipelineName") or "--"),
           "  构建/状态  : #%s %s · 失败任务类型=%s · 归属日 %s"
           % (rec.get("buildNumber"), rec.get("status"),
              rec.get("failedTaskType") or "--", rec.get("date")),
           "  起止时间   : %s → %s" % (rec.get("startedAt") or "--", rec.get("endedAt") or "--"),
           "  影响维度   : %s（当日指标 版本可用度 %s / 构建成功率 %s，track=%s）"
           % (dims, fmt(va), fmt(bs), lt.get("track") or "--"),
           "  计数       : %s" % json.dumps(rec.get("counts") or {}, ensure_ascii=False)]
    v = rec.get("verdict") or {}
    if v.get("category"):
        out.append("  规则分类   : %s（仅供参考，页面分类列读你写的 issueType）" % v.get("category"))

    tasks = rec.get("tasks") or []
    if tasks:
        out.append("  失败任务   :")
        for t in tasks:
            out.append("    [%s] %s → %s%s"
                       % (t.get("type") or "--", t.get("jobName") or "--",
                          t.get("logFile") or "--",
                          "（抽取报错行 %d 条）" % len(t.get("errorLines") or [])
                          if t.get("errorLines") else ""))

    pts = focus_points(rec)
    if pts:
        out.append("  报错点（原文见下，可直接写进 cites）:")
        for p in pts[:MSG_MAX + 4]:
            loc = "%s:%s" % (p["source"], ("L%s" % p["line"]) if p["line"] else "-")
            tag = p["level"] + ("·%s" % p["case"] if p.get("case") else "")
            out.append("    · %-18s %s  %s" % (tag, cut(loc, 60), cut(p["text"], 150)))

    # ---- 证据原文：按日志文件归并报错点的上下文区间；没有定位行的任务补日志尾部
    by_src = {}
    for p in pts:
        if p["line"] and p["source"]:
            by_src.setdefault(p["source"], []).append(p["line"])
    ev, used = [], 0
    for src, targets in by_src.items():
        if used >= ev_lines:
            break
        got, n_used = ev_source(pdir, src, targets, ev_lines - used)
        ev += got
        used += n_used
    for t in tasks:
        lf = t.get("logFile")
        if lf and lf not in by_src and used < ev_lines:
            got, n_used = tail_block(pdir, lf, ev_lines - used)
            ev += got
            used += n_used
    if ev:
        out.append("  证据原文（行号即原文行号，可直接写进 cites）:")
        out += ev
    else:
        out.append("  证据原文   : 本记录没有可读的证据文件（按记录里的任务清单与错误信息定性）")

    cases = rec.get("cases") or []
    if cases:
        out.append("  失败用例（%d 条，列前 %d）:" % (len(cases), CASE_MAX))
        for c in cases[:CASE_MAX]:
            first = ((c.get("errorMessages") or [{}])[0] or {})
            out.append("    - %s [%s] %s"
                       % (cut(c.get("name"), 70), c.get("state") or "--",
                          cut(first.get("text") or first.get("message") or first.get("msg") or "", 140)))
    missing = ((rec.get("evidence") or {}).get("missing")) or []
    if missing:
        out.append("  证据缺口   : %s（取证不全，定性时说明证据不完整）" % ", ".join(missing[:6]))
    out.append("  记录位置   : %s" % lp.where(x))
    return out


def main():
    ap = argparse.ArgumentParser(description="把待分析记录打成纯文本取证包（AI 的唯一输入）")
    ap.add_argument("--date", help="归档日 yyyy-mm-dd（默认最近一个归档日；--all 用全部）")
    ap.add_argument("--all", action="store_true", help="全部归档日")
    ap.add_argument("--record", help="只打这一条（recordId 或构建号）")
    ap.add_argument("--status", default="pending",
                    help="analysis.status 过滤（默认 pending；排查时可给 done/all）")
    ap.add_argument("--max-records", type=int, default=40, help="最多打几条（默认 40）")
    ap.add_argument("--ev-lines", type=int, default=EV_MAX, help="每条记录最多回显多少行原文")
    ap.add_argument("--out", help="同时另存到这个文件（相对技能根目录或绝对路径）")
    args = ap.parse_args()

    days = [d for d, _ in lp.iter_archive_days()]
    if args.date:
        days = [args.date]
    elif not args.all and days:
        days = days[-1:]
    rows = lp.collect(days, args.status)
    if args.record:
        want = lp.norm_id(args.record)
        rows = [x for x in rows if lp.norm_id(x["record"].get("recordId")) == want
                or str(x["record"].get("buildNumber")) == str(args.record).lstrip("#")]
    shown = rows if args.max_records <= 0 else rows[:args.max_records]

    scope = "全部归档日" if (args.all or args.date) else "最近归档日"
    head = [HEAD,
            "# 归档范围: %s %s   analysis.status=%s 的记录: %d 条（本次打印 %d 条）"
            % (scope, (days[0] if len(days) <= 1 else "%s~%s" % (days[0], days[-1])),
               args.status or "全部", len(rows), len(shown))]
    body = []
    for i, x in enumerate(shown, 1):
        body += one_block(i, len(rows), x, args.ev_lines)
    foot = ["─" * 100]
    if len(shown) < len(rows):
        foot.append("# 还有 %d 条未打印：用 --max-records 0 全打，或 --record 逐条深挖"
                    % (len(rows) - len(shown)))
    if not rows:
        foot.append("# 当前没有待分析记录（list_pending.py --strict 退出码 0 时即为这种情况）")
    text = "\n".join(head + body + foot)

    if args.out:
        p = Path(args.out)
        if not p.is_absolute():
            p = ROOT / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print("== 取证包已另存: %s" % p)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
