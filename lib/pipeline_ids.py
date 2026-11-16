# -*- coding: utf-8 -*-
"""流水线身份与唯一短名 —— 采集（第 1 步）、归档（第 7 步）与存量归并共用同一份规则。

为什么需要一层「注册表」:
  短名（pipelineShortName）不是展示字段，而是**数据主键的一半**：
  key = "<产品>|<短名>"，同时是归档目录第二层、recordId 前缀与缓存键的一半。
  如果短名按「当次采集到的集合」现算，集合一变（今天多了一条同名流水线、明天少一条）
  短名就会跟着变 —— 同一条 pipelineId 在 11-10 落成目录 `openUBMC`、在 11-13 落成
  `openUBMC~f35034`，首页按 key 做区间 union 时就会被算成两条流水线（用户反馈的
  「openUBMC 流水线条数不对」）。

规则（三条，从上到下）:
  1) 已登记过的 pipelineId 一律沿用注册表里的短名，**永不改名**（跨日稳定的根）。
  2) 新出现的 pipelineId 依次尝试：末段 -> 去公共前缀的全名 -> 全名~sha1(name|id) 前 6 位，
     取第一个未被占用的。
  3) 占用判定**大小写不敏感**：Windows 文件系统不区分大小写，`Agentsdk` 与 `AgentSDK`
     会落到同一个归档目录互相覆盖（同一天两条流水线只剩一条的数据），必须当成同名。
  新流水线按 pipelineId 排序后再分配，保证同一批输入每次算出的短名完全一致。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.paths import ARCHIVE_ROOT, PIPELINES_NAME  # noqa: E402

# 看板统一前缀：Nightly-CI-Component-pipeline_<组件> / Nightly-CI-Version-pipeline_<组件>
_PIPELINE_PREFIX = re.compile(r"^nightly-ci-[a-z]+-pipeline_", re.I)


def short_tail(pname):
    """默认短名：pipelineName 末段（保持历史归档目录名不变，不做无谓迁移）。"""
    return pname.rsplit("_", 1)[-1] or pname


def short_full(pname):
    """冲突时退一步：去掉看板公共前缀的全名（github 工作流文件名本就无前缀，原样保留）。"""
    m = _PIPELINE_PREFIX.match(pname)
    return (pname[m.end():] if m else pname) or pname


def hash_suffix(pname, pid):
    """兜底后缀：不同 id 的同名流水线必须落到不同目录，否则执行记录会互相覆盖。"""
    return hashlib.sha1(("%s|%s" % (pname or "", pid)).encode("utf-8")).hexdigest()[:6]


def assign_short_names(pairs, sticky=None):
    """[(pipelineId, pipelineName)] -> {pipelineId: 唯一短名}。

    pairs 是**该产品的全量身份集合**（注册表历史 ∪ 本次采集），不是当次采集集合——
    只有全量集合才能保证「今天多一条同名流水线」不会把昨天的短名改掉。
    sticky = {pipelineId: 已登记短名}：命中的一律沿用。
    """
    pairs = [(str(pid), pname or "") for pid, pname in pairs]
    sticky = {str(k): v for k, v in (sticky or {}).items() if v}
    out, used = {}, set()
    for pid, pname in pairs:
        s = sticky.get(pid)
        if s and s.lower() not in used:          # 历史短名优先，冲突时留给下面重新分配
            out[pid] = s
            used.add(s.lower())
    fresh = sorted([(pid, pname) for pid, pname in pairs if pid not in out],
                   key=lambda x: x[0])
    for pid, pname in fresh:
        tail = short_tail(pname) if pname else "pipeline_%s" % pid
        full = short_full(pname) if pname else tail
        for cand in (tail, full, "%s~%s" % (full, hash_suffix(pname, pid))):
            if cand.lower() not in used:
                out[pid] = cand
                used.add(cand.lower())
                break
        else:
            out[pid] = "%s~%s" % (full, hash_suffix(pname, pid))
    return out


def registry_path(archive_root=None):
    return Path(archive_root or ARCHIVE_ROOT) / PIPELINES_NAME


def load_registry(archive_root=None):
    """读流水线身份注册表：{产品: {pipelineId: {pipelineName, platform, short, firstSeen, lastSeen}}}。"""
    p = registry_path(archive_root)
    if not p.is_file():
        return {}
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    out = {}
    for prod, items in (doc.get("products") or {}).items():
        if isinstance(items, dict):
            out[prod] = {str(pid): v for pid, v in items.items() if isinstance(v, dict)}
    return out


def save_registry(products, archive_root=None, generated_at=None):
    """整份覆盖写回注册表（跨次运行只增不删：短名一旦登记就不再变）。"""
    path = registry_path(archive_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_doc": {
            "step": "step_1_nightly",
            "title": "流水线身份注册表",
            "criteria": "每个开源组件下 pipelineId -> 唯一短名的持久映射（跨次运行累积、"
                        "只增不删）：短名同时是归档目录名与页面聚合键的一半，"
                        "已登记的一律沿用，保证同一条流水线跨日不会换目录 / 换 key",
            "generatedAt": generated_at or "",
            "pathBase": "products.<开源组件名>.<pipelineId> = {pipelineName, platform, short, "
                        "firstSeen, lastSeen}",
        },
        "generatedAt": generated_at or "",
        "productCount": len(products),
        "pipelineCount": sum(len(v) for v in products.values()),
        "products": {k: dict(sorted(v.items())) for k, v in sorted(products.items())},
    }
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path
