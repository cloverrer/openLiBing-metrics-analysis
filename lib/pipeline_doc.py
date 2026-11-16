# -*- coding: utf-8 -*-
"""流水线归档「单文件」读写（schema=pipeline/1）。

一次采集里，同一条流水线在同一个归档日会产出 9 份 JSON（`_manifest.json` + `step_1~6`）
外加 `records/run_<构建号>.json` 若干份 —— 一天 49 条流水线就是 500 多个文件，翻查、
传输、备份都被切得很碎。本模块把「同一个流水线目录」的全部内容装进一份 `pipeline.json`::

  <日>/<组件>/<流水线>/pipeline.json
    _doc / schema                       本文件是什么、按什么口径合并
    date / component / pipeline / …     目录身份（与原 _manifest.json 一致）
    dateBasis                           日期归属依据（执行结束时间 + 当日运行清单）
    steps{step_1_lights: …}             每步正文 = 原 step_1_lights.json … step_6_records.json
    stepIndex[]                         每步标题/来源/口径/日期字段/字节数 = 原 _manifest 的 steps[]
    records[]                           逐条执行记录全文 = 原 records/run_<构建号>.json
    counts / evidence / source          原 _manifest.json 的对应字段
  证据原文（job_logs/ case_logs/ github_logs/ 下的日志/报告）收进同目录的
  `pipeline.evidence.json`，一个流水线目录只剩这两份文件，正文一行都不改。

为什么原文要单独一份、不塞进 pipeline.json：页面首屏只 fetch pipeline.json，
证据正文可能有几十 MB（单目录最大 67 MB），塞进去会拖慢首屏；而原文只在
「按行号取证据」时才需要 —— 取数统一走 `evidence_window()`。

为什么仍然「逐条可核对」：`steps` 里的正文与原来那 8 份文件一字不差；`stepIndex`
保留了每一步的来源与口径；`records[]` 就是原来每条记录文件的全文（只少了一层重复的
`_doc`，题头统一放在 `steps.step_6_records._doc`）。

兼容：`load()` 同时认老结构（`_manifest.json` + `step_*.json` + `records/run_*.json`），
读不到 `pipeline.json` 时就地拼出同样的结构 —— 迁移期工具与页面都不用分支判断。
"""
import hashlib
import json
import os
from pathlib import Path

NAME = "pipeline.json"
SCHEMA = "pipeline/1"
EVIDENCE_NAME = "pipeline.evidence.json"
EVIDENCE_SCHEMA = "pipeline-evidence/1"
# 证据文件所在目录（相对流水线目录 / 采集工作目录）；各类引用都以这三个前缀开头
EVIDENCE_PREFIX = ("job_logs/", "case_logs/", "github_logs/")

# 老结构的 8 份步骤文件（顺序即 stepIndex 顺序）
LEGACY_FILES = [
    ("step_1_lights.json", "step_1_lights"),
    ("step_2_runs.json", "step_2_runs"),
    ("step_3_tasks.json", "step_3_tasks"),
    ("step_4_cases.json", "step_4_cases"),
    ("step_5_logs.json", "step_5_logs"),
    ("step_5b_subtasks.json", "step_5b_subtasks"),
    ("step_5c_github.json", "step_5c_github"),
    ("step_6_records.json", "step_6_records"),
]


def path_of(pdir):
    """某流水线目录的 pipeline.json 路径。"""
    return Path(pdir) / NAME


def has_pipeline(pdir):
    return path_of(pdir).is_file()


def _load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load(pdir):
    """读一个流水线目录，返回统一结构（dict）；读不到任何内容时返回 None。

    新结构直接返回 `pipeline.json`；老结构（迁移前 / 尚未合并的旧归档）按同样的字段
    就地拼装，调用方拿到的永远是 `{"steps": {...}, "records": [...]}` 这一套。
    """
    pdir = Path(pdir)
    p = path_of(pdir)
    if p.is_file():
        try:
            doc = _load_json(p)
        except (ValueError, OSError):
            return None
        doc.setdefault("steps", {})
        doc.setdefault("records", [])
        return doc

    man_p = pdir / "_manifest.json"
    man = {}
    if man_p.is_file():
        try:
            man = _load_json(man_p)
        except (ValueError, OSError):
            man = {}
    steps, index = {}, []
    for fname, step in LEGACY_FILES:
        f = pdir / fname
        if not f.is_file():
            continue
        try:
            steps[step] = _load_json(f)
        except (ValueError, OSError):
            continue
        index.append({"step": step, "file": fname, "bytes": f.stat().st_size})
    recs = []
    for f in sorted((pdir / "records").glob("run_*.json")) if (pdir / "records").is_dir() else []:
        try:
            rec = _load_json(f)
        except (ValueError, OSError):
            continue
        rec.pop("_doc", None)
        recs.append(rec)
    if not steps and not recs and not man:
        return None
    out = dict(man)
    out.pop("steps", None)
    out.pop("records", None)
    out.update({"schema": SCHEMA, "steps": steps, "stepIndex": index, "records": recs,
                "layout": "legacy"})
    return out


def records(pdir):
    """某流水线目录的全部执行记录（新老结构通用）。"""
    doc = load(pdir) or {}
    return doc.get("records") or []


def step(doc, name):
    """取某一步正文；老归档刚从文件拼出来的也走这里。"""
    return ((doc or {}).get("steps") or {}).get(name) or {}


def save(pdir, payload):
    """原子写回 pipeline.json（先写 .tmp 再替换，避免中断留下半个文件）。"""
    p = path_of(pdir)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(p))
    return p


# ---- 证据正文：pipeline.evidence.json ----------------------------------------
# 结构::
#
#   {"_doc": {...}, "schema": "pipeline-evidence/1",
#    "date"/"component"/"pipeline": 目录身份,
#    "pathBase": "files 的键 = 相对本目录的证据路径",
#    "lineBase": 1,
#    "files": {"job_logs/xx.log": {"bytes":…, "lineCount":…, "sha1":…,
#                                   "eol": true, "lines": ["第1行", "第2行", …]}},
#    "counts": {"files":…, "bytes":…, "lines":…}}
#
# 行号口径与采集时完全一致（1 起）：`lines[N-1]` 就是原文第 N 行，所以各步正文、
# 执行记录、AI 结论里的 `文件:行号` 引用不用改一个字就能对上原文。
_EV_CACHE = {}          # {路径字符串: ((mtime_ns, size), doc)}；大目录正文几十 MB，只留最近几份
_EV_CACHE_MAX = 2


def evidence_path_of(pdir):
    """某流水线目录的 pipeline.evidence.json 路径。"""
    return Path(pdir) / EVIDENCE_NAME


def has_evidence(pdir):
    return evidence_path_of(pdir).is_file()


def _load_evidence_cached(p):
    p = Path(p)
    try:
        st = p.stat()
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size)
    hit = _EV_CACHE.get(str(p))
    if hit and hit[0] == key:
        return hit[1]
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(doc, dict):
        return None
    _EV_CACHE[str(p)] = (key, doc)
    while len(_EV_CACHE) > _EV_CACHE_MAX:
        _EV_CACHE.pop(next(iter(_EV_CACHE)))
    return doc


def load_evidence(pdir):
    """读证据文档；没有或不可解析时返回空壳 `{"files": {}}`（调用方不用分支）。

    注意：返回的是缓存里的那一份对象，改完要走 `save_evidence()` 落盘（它会清缓存）。
    """
    doc = _load_evidence_cached(evidence_path_of(pdir))
    if doc is None:
        return {"schema": EVIDENCE_SCHEMA, "files": {}, "counts": {"files": 0, "bytes": 0, "lines": 0}}
    doc.setdefault("files", {})
    return doc


def save_evidence(pdir, doc):
    """原子写回 pipeline.evidence.json。"""
    p = evidence_path_of(pdir)
    doc.setdefault("schema", EVIDENCE_SCHEMA)
    files = doc.setdefault("files", {})
    doc["counts"] = {
        "files": len(files),
        "bytes": sum(int((v or {}).get("bytes") or 0) for v in files.values()),
        "lines": sum(len((v or {}).get("lines") or []) for v in files.values()),
    }
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(str(tmp), str(p))
    _EV_CACHE.pop(str(p), None)
    return p


def evidence_entries(pdir):
    """某目录内嵌证据的 {相对路径: 条目}（条目含正文，慎用于页面/汇总）。"""
    return load_evidence(pdir).get("files") or {}


def evidence_index(pdir):
    """轻量清单：{相对路径: {bytes, lineCount, sha1}}，不含正文。"""
    return {k: {kk: vv for kk, vv in (v or {}).items() if kk != "lines"}
            for k, v in evidence_entries(pdir).items()}


def evidence_join(entry):
    """把内嵌条目还原成原文（与归档前的文件逐字节一致，可用来校验 sha1）。"""
    lines = (entry or {}).get("lines") or []
    text = "\n".join(str(x) for x in lines)
    if (entry or {}).get("eol"):
        text += "\n"
    return text


def evidence_window(pdir, rel_path, l1=1, l2=None, max_lines=80):
    """按原始行号取内嵌证据的第 l1~l2 行，返回 (正文, 是否取到)。

    这是「证据进 JSON」之后**唯一**的取原文入口：write_analysis 的 keyError 对账、
    归档自检、第 8 步按行窗口取证都走这里，避免各处自己解析 JSON。
    越界按实际范围裁剪（l1 超出总行数 → 取不到）。
    """
    rel_path = str(rel_path or "").replace("\\", "/").strip()
    if not rel_path:
        return None, False
    ent = evidence_entries(pdir).get(rel_path)
    if not isinstance(ent, dict):
        return None, False
    lines = ent.get("lines")
    if not isinstance(lines, list) or not lines:
        return None, False
    try:
        l1 = max(1, int(l1))
    except (TypeError, ValueError):
        l1 = 1
    try:
        l2 = int(l2) if l2 is not None else l1
    except (TypeError, ValueError):
        l2 = l1
    if l2 < l1:
        l2 = l1
    if max_lines and l2 - l1 + 1 > max_lines:
        l2 = l1 + max_lines - 1
    n = len(lines)
    if l1 > n:
        return None, False
    l2 = min(l2, n)
    # 回显/比对时去掉行尾的 \r（Windows 日志常见 CRLF）：行号与内容不变，
    # 逐字节还原走 evidence_join()，那里一个字符都不动。
    return "\n".join(str(x).rstrip("\r") for x in lines[l1 - 1:l2]), True


def evidence_line_count(pdir, rel_path):
    """某份内嵌证据的总行数（取不到返回 0），自检用来判断「行号是否可达」。"""
    ent = evidence_entries(pdir).get(str(rel_path or "").replace("\\", "/"))
    if not isinstance(ent, dict):
        return 0
    try:
        return int(ent.get("lineCount") or len(ent.get("lines") or []))
    except (TypeError, ValueError):
        return 0


def evidence_key_ok(rel_path):
    """该路径是否属于证据目录（job_logs/ case_logs/ github_logs/，且不含 ..）。"""
    rp = str(rel_path or "").replace("\\", "/")
    return rp.startswith(EVIDENCE_PREFIX) and ".." not in rp.split("/")


def evidence_verified(pdir, rel_path):
    """内嵌正文能否逐字节还原（还原后 sha1 与归档时一致）——删散文件前的最后一道闸。"""
    ent = evidence_entries(pdir).get(str(rel_path or "").replace("\\", "/"))
    if not isinstance(ent, dict):
        return False
    try:
        raw = evidence_join(ent).encode("utf-8")
    except (UnicodeEncodeError, TypeError):
        return False
    return hashlib.sha1(raw).hexdigest() == ent.get("sha1")


def embed_evidence(pdir, rel_paths, src_root=None, step="step_7_archive"):
    """把证据原文逐行内嵌进 `<流水线目录>/pipeline.evidence.json`；返回
    (份数, 字节数, 行数, 缺失列表)，三个计数都是**本目录累积全量**（含此前已内嵌的）。

    `src_root` 是证据文件的实际所在目录：采集时传 out/（正文还在工作目录里），
    存量合并时不传（正文就在流水线目录里，已经归位）。三条约定：

      1) 键 = 原样保留证据的相对路径，不缩短、不改名 —— 正文不进文件系统，就不再受
         Windows 260 字符路径上限约束，各步 JSON 里的引用一个字都不用改；
      2) 只增不删：已内嵌的正文不再读源文件（out/work 可能已被清空），历史证据永不
         删除，保证每条历史结论都还能回到原文；
      3) 无损：`lines` 是原文逐行内容，`eol` 记尾换行，`sha1` 记原文哈希 ——
         用 `evidence_join()` 还原后与原文件逐字节一致。
    """
    pdir = Path(pdir)
    root = Path(src_root) if src_root else pdir
    ev = load_evidence(pdir)
    files = ev.setdefault("files", {})
    dirty = False
    missing = []
    for rp in sorted({str(p) for p in rel_paths if p}):
        rp = rp.replace("\\", "/")
        # 只收本目录内的证据（防止 ../ 或绝对路径写进归档）
        if not evidence_key_ok(rp):
            continue
        ent = files.get(rp)
        if isinstance(ent, dict) and ent.get("lines") is not None:
            continue                                   # 已内嵌（含上一次重跑）→ 幂等跳过
        src = root / rp
        if not src.is_file():
            missing.append(rp)
            continue
        raw = src.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:                      # 归档要能逐行看，非 UTF-8 字节按替换符落
            text = raw.decode("utf-8", "replace")
        lines = text.split("\n")
        eol = bool(lines) and lines[-1] == ""
        if eol:
            lines = lines[:-1]
        files[rp] = {"bytes": len(raw), "lineCount": len(lines), "eol": eol,
                     "sha1": hashlib.sha1(raw).hexdigest(), "lines": lines}
        dirty = True
    if dirty:
        ev.setdefault("schema", EVIDENCE_SCHEMA)
        ev["_doc"] = {
            "step": step,
            "title": "证据原文（单文件）",
            "source": "job_logs/ case_logs/ github_logs/ 下的原始文件逐行内嵌",
            "criteria": "files 的键 = 相对本流水线目录的证据路径（与各步 JSON 里的引用一致）；"
                        "values.lines 是原文逐行内容（1 起，行号与原文件相同）；"
                        "bytes/sha1/eol 可无损还原并校验",
            "date": pdir.parent.parent.name,
            "component": pdir.parent.name,
            "pipeline": pdir.name,
        }
        ev["pathBase"] = "files 的键相对本流水线目录（与 pipeline.json 里 logFile/cites 的写法一致）"
        ev["lineBase"] = 1
        ev["date"] = pdir.parent.parent.name
        ev["component"] = pdir.parent.name
        ev["pipeline"] = pdir.name
        save_evidence(pdir, ev)
    counts = ev.get("counts") or {}
    return (int(counts.get("files") or 0), int(counts.get("bytes") or 0),
            int(counts.get("lines") or 0), missing)


def assemble(manifest, steps, records):
    """把「原 _manifest.json + 各步正文 + 各条记录」拼成 pipeline/1 结构。

    manifest 沿用第 7 步原来那份清单的字段（date/component/pipeline/pipelineName/
    platform/key/dateBasis/counts/evidence/source），这里只把 `steps[]` 的 file 换成
    内嵌正文、把 `records[]` 的 file 换成记录全文。
    """
    man = dict(manifest or {})
    index = []
    for st in man.pop("steps", []) or []:
        name = st.get("step")
        body = steps.get(name)
        if body is None:
            continue
        item = {"step": name, "bytes": 0}
        item.update({k: v for k, v in st.items() if k not in ("file", "step", "bytes")})
        index.append(item)
    recs = []
    for rec in records or []:
        rec = dict(rec)
        rec.pop("_doc", None)          # 每条一份题头纯属重复，统一看 steps.step_6_records._doc
        recs.append(rec)
    step6 = dict(steps.get("step_6_records") or {})
    step6.pop("records", None)          # 正文只放 records[]，不在这里再存一份
    step6.pop("recordFiles", None)
    step6["pathBase"] = "记录正文在本文件顶层 records[]（不再拆 records/run_<构建号>.json）"
    step6["recordDoc"] = ("单条执行记录：任务/用例/错误信息/证据/定性/置信度/构建编号"
                          "（每条记录不再单独带 _doc，题头见本字段）")
    step6.setdefault("counts", {})
    step6["counts"] = dict(step6["counts"], records=len(recs))
    body = dict(steps)
    body["step_6_records"] = step6

    out = {
        "_doc": {
            "step": "step_7_archive",
            "title": "流水线归档（单文件）",
            "source": (man.get("_doc") or {}).get("source") or "第 1~6 步中间产物（out/work/）",
            "criteria": "同一条流水线在同一个归档日的全部内容装进两份文件："
                        "每步正文见 steps，逐条执行记录见 records，证据原文见同目录 "
                        "pipeline.evidence.json 的 files（键=相对本目录的路径，行号 1 起）",
            "dateField": (man.get("dateBasis") or {}).get("field") or "pipelineRunEndtime",
            "generatedAt": (man.get("_doc") or {}).get("generatedAt"),
            "component": man.get("component"),
            "pipeline": man.get("pipeline"),
            "date": man.get("date"),
            "recordCount": len(recs),
        },
        "schema": SCHEMA,
    }
    for k in ("date", "component", "pipeline", "pipelineName", "platform", "key",
              "dateBasis", "counts", "evidence", "source", "pathBase"):
        if k in man:
            out[k] = man[k]
    out["steps"] = body
    out["stepIndex"] = index
    out["records"] = recs
    out.setdefault("pathBase", "steps.* / records[] 相对本文件；证据正文见 "
                                "pipeline.evidence.json 的 files（键=相对本目录的路径）")
    for item in out["stepIndex"]:
        item["bytes"] = len(json.dumps(body.get(item["step"]), ensure_ascii=False).encode("utf-8"))
    return out


def update_record(pdir, record_id, mutate):
    """把 record_id 对应的记录改掉并落盘，返回 (是否找到, 落盘路径)。

    新结构直接改 `pipeline.json` 里的 records[]；老结构改 `records/run_*.json`，
    并同步 `step_6_records.json` 的副本 —— 两种布局的「写回」只在这里实现一次。
    """
    pdir = Path(pdir)
    p = path_of(pdir)
    if p.is_file():
        doc = _load_json(p)
        for rec in doc.get("records") or []:
            if str(rec.get("recordId")) == str(record_id):
                mutate(rec)
                save(pdir, doc)
                return True, p
        return False, p
    # ---- 老结构
    for f in sorted((pdir / "records").glob("run_*.json")) if (pdir / "records").is_dir() else []:
        rec = _load_json(f)
        if str(rec.get("recordId")) != str(record_id):
            continue
        mutate(rec)
        tmp = f.with_suffix(f.suffix + ".tmp")
        tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(f))
        agg = pdir / "step_6_records.json"
        if agg.is_file():
            try:
                box = _load_json(agg)
                for i, r in enumerate(box.get("records") or []):
                    if str(r.get("recordId")) == str(record_id):
                        box["records"][i] = {**rec}
                        break
                tmp2 = agg.with_suffix(agg.suffix + ".tmp")
                tmp2.write_text(json.dumps(box, ensure_ascii=False, indent=1), encoding="utf-8")
                os.replace(str(tmp2), str(agg))
            except (ValueError, OSError):
                pass
        return True, f
    return False, pdir / "records"
