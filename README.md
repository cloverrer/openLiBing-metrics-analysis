# openLiBing 工程运营看板 · 夜间指标取证与根因分析

> 把 openLiBing 工程运营看板（eCDashboard）的 nightly 指标取下来 → 逐层归档取证 → AI 定根因 → 产出可交付的静态看板页面。

---

## 在线看板

**https://cloverrer.github.io/openLiBing-metrics-analysis/out/html/**

这是本项目提供的 GitHub 地址（GitHub Pages 渲染仓库 `master` 分支的 `out/html/`）。

页面是**运行时读归档**的静态壳：HTML 本身不含业务数据，打开时去拉同仓库里的 `out/archive/`。因此改完数据只要重新生成一次页面并推到仓库，地址上的内容就自动更新，无需另外部署。

> 仓库根目录的 `.nojekyll` 是必需的——关闭 Jekyll 处理后，以 `_` 开头的归档文件（`_day.json` / `_index.json` / `_products.json`）才不会被过滤掉。

---

## 这是什么

一言以蔽之：**脚本负责取数与归档，AI 只负责中间的根因结论。**

原始指标来自 openLiBing 看板（HPC 各开源组件的 nightly 流水线），本流程把每条流水线当天的执行记录全部留存下来，对失败/取消的运行逐条取证（失败任务、报错点、日志原文行号），再由 AI 定性与定位，最终生成可回看、可逐条核对证据的看板页面。

产出物是 `out/archive/`（逐层归档的数据与证据）+ `out/html/`（展示页）。

---

## 快速开始

### 环境要求

- **Python 3.10**（实测 3.10.11；纯标准库，无第三方依赖，无需 pip install）
- **Chrome / Edge**：采集走 CDP 调试端口，脚本会在端口不通时自动拉起浏览器并复用日常登录态，不需要手动「先开浏览器再跑」
- 已登录 openLiBing 看板

### 三段流程（一次跑完，中间不能停）

```powershell
# 第 1 段 取数归档（脚本）：采集 + 取证 + 归档 + 出静态壳
python run_pipeline.py

# 第 2 段 AI 根因（agent 执行，脚本不做）
python tools/digest_pending.py                      # 唯一输入：清单 + 每条记录的取证包（纯文本，带行号）
#   AI 按 agent/agent_task.md 写结论到 out/state/analysis_result.txt
python tools/write_analysis.py --file out/state/analysis_result.txt --dry-run
python tools/write_analysis.py --file out/state/analysis_result.txt

# 第 3 段 重出页面（脚本）
python run_pipeline.py --only step9
```

### 完成判据（三条同时满足才算跑完）

1. `python tools/list_pending.py --strict` 退出码 `0`（还有待分析记录时以退出码 `2` 报「流程未完成」）
2. `python run_pipeline.py --only step9` 已执行
3. 归档与页面生成均无报错

退出码说明：`0` = 采集完成，必须接着做第 2 段；`42` = 当天无任何待分析数据，是唯一允许提前结束的情况；其他非 `0` = 按日志修好后用 `--from stepN` 续跑。

---

## 命令行参数

| 参数 | 说明 |
|---|---|
| （无参） | 全流程：默认取「前一个工作日」单日、全部产品、全部流水线（含达标） |
| `--start / --end` | 指定分析区间，如 `--start 2026-11-10 --end 2026-11-16` |
| `--products` | 限定产品，如 `--products MindStudio,Ascend-CANN` |
| `--from stepN` | 从指定步骤续跑，前面步骤的产物直接复用 |
| `--only stepN` | 只跑单步（支持 `--only 4` / `--only testreport` 这类写法） |
| `--fresh` | 跳过增量缓存，全部重新抓取 |
| `--retries N` | 每步失败自动重试次数（默认 1，适配无人值守） |
| `--serve` | 起本地 HTTP 服务预览展示页（`127.0.0.1:8765`） |
| `--no-launch-browser` | 采集前不自动拉起 Chrome（已手工开好调试端口时） |

终端只透传步骤头与 `!!` 错误行，完整输出落在 `out/state/run_pipeline.log`。查看实时进度：

```powershell
Get-Content out\state\run_pipeline.log -Tail 50 -Wait
```

---

## 采集步骤一览

| 步骤 | 内容 |
|---|---|
| 第 1 步 | 夜间统计与待分析圈定（看板一级汇总） |
| 第 2 步 | 【N2】执行记录圈定（区间内全部运行，成功也留存） |
| 第 3 步 | 【T4】失败任务分流（github 平台转第 5c 步） |
| 第 4 步 | 【T6】测试用例取证 |
| 第 5 步 | 【T5】任务日志取证 |
| 第 5b 步 | 【T7】buildflow 子任务下钻 |
| 第 5c 步 | 【GitHub】github 平台运行日志取证 |
| 第 6 步 | 证据合并 → 逐条执行记录 |
| 第 7 步 | 逐层归档（日期 / 组件 / 流水线） |
| 第 7b 步 | 社区 Nightly 采集（openGauss / openEuler / UBS Core） |
| 第 8 步 | **AI 根因分析（agent 执行，不是脚本步骤）** |
| 第 9 步 | 生成展示页（静态壳 → `out/html/`） |

第 7b 步排在第 7 步之后、第 9 步之前，是因为社区流水线产出的是与 openLiBing 侧同一套归档 schema，而 `_day.json` / `_products.json` / `_index.json` 都是第 7 步整体重建的产物——社区数据必须在其之后并入，否则第 7 步重跑会把社区条目冲掉。

---

## 目录结构

```
run_pipeline.py          全流程唯一入口
config.json              主配置（区间、产品、口径、浏览器、缓存、鉴权）
community_sources.json   三个社区源定义（openGauss / openEuler / UBS Core）
SKILL.md                 流程说明书（三段流程、完成判据、口径约束）
agent/                   AI 分析口径：agent_task.md + analysis_profile.json
steps/                   各采集与出页步骤（step_1 … step_9）
lib/                     公共库：browser / cdp_exec / cache / paths /
                         pipeline_doc / pipeline_ids / ui / va_caliber / workdays
tools/                   取数辅助、根因写回、归档维护与校验工具
tpl/                     页面模板
docs/                    采集实现参考（改采集代码时才需要看）
out/
  archive/               逐层归档（最终交付物，只增不删）
  html/                  第 9 步产出的静态壳（index.html / detail.html）
  work/                  第 1~6 步中间产物（归档后即可丢弃）
  state/                 run_pipeline.log 与增量采集缓存
```

---

## 归档结构

```
out/archive/<年>/<年-月>/<日>/<开源组件名>/<流水线名>/
    pipeline.json              一条流水线一天一份：各步正文 + 记录全文 + 清单
    pipeline.evidence.json     证据原文（逐行内嵌，按行号取用）
```

- 归档日 = 该执行的**结束时间**所在日期；同一条流水线在不同日期分别建目录，互不覆盖。
- `pipeline.json` 里 `records[]` 一条一个元素，每条记录就是一个最小分析单位；成功运行标 `analysis.status='na'`（只留存、不进 AI 队列），失败/取消且非达标指标才标 `pending`。
- 证据原文逐行内嵌在 `pipeline.evidence.json` 的 `lines[]` 里，行号与原文件一致，磁盘上没有散日志。按行窗口取用：

```powershell
python tools/read_evidence.py --record "组件|流水线#构建号" --list
python tools/read_evidence.py --record "组件|流水线#构建号" "job_logs/x.log:L138"
python tools/read_evidence.py --record "组件|流水线#构建号" --grep "ERROR|fatal" --ctx 2
```

---

## 口径与规则

**日期归属**：所有日期归属、筛选、归档一律取**执行结束时间**（openLiBing N2 `pipelineRunEndtime` / GitHub `run.updated_at`），与页面日期筛选组件保持一致。

**版本可用度**：可用日 ÷ 该流水线有执行记录的天数。当天有运行**开始或结束**才算有执行记录；跨午夜运行的开始日也进分母；成功只把可用状态记录到结束日；流水线当日完全没启动则当日不进分母。**被中断的运行（Jenkins `ABORTED`、openLiBing `CANCELED`）同样算「执行过」→ 进分母，但永不计可用**：当日只有这类运行，就是「当日没有版本可用」（分母 1、分子 0），而不是「没跑过」。组件级 = 各流水线可用度之和 ÷ 条数（一次运行都没有的流水线不进均值）。

**编译成功率**：Σ`buildPassCount` / Σ`buildCount`。**github 平台流水线不计算编译成功率**（不采集、不展示）。

**社区流水线**：openGauss / openEuler / UBS Core 走 `lib/va_caliber.py` 的集中判定逻辑，与 openLiBing 侧同一套口径；社区版本可用度不要求测试用例通过率 100%。

**增量缓存**：默认开启。上一次已取证的运行（构建列表 / 用例日志 / 全量日志 / 解析结果）直接复用，仅补抓新运行；复用前会校准运行状态（重试/重跑导致状态或结束时间变更的条目自动重抓），`--fresh` 可强制全量重抓。

**数据保留**：不设滚动清理，`out/archive/` 只增不删，每日归档长期保留供回看。

---

## 常用工具

| 工具 | 用途 |
|---|---|
| `tools/list_pending.py --strict` | 待分析清单 / 交付前门禁（有待分析记录时退出码 2） |
| `tools/digest_pending.py` | 生成待分析记录的纯文本取证包（AI 的唯一输入） |
| `tools/write_analysis.py` | AI 根因结论写回归档（第 8 步的唯一出口） |
| `tools/read_evidence.py` | 按行窗口读证据原文 |
| `tools/verify_archive.py` | 归档自检：逐层核对「每条结论都能落到证据」 |
| `tools/collect_community_nightly.py` | 社区 Nightly 采集（第 7b 步调用的实现） |
| `tools/reconcile_superseded.py` | 跨日陈旧副本清理（同一 `pipelineRunId` 只留结束时间最晚的副本） |
| `tools/normalize_analysis.py` | 分析状态归一（让 `analysis.status` 与当日切片口径对齐） |
| `tools/rebuild_community_day.py` | 按已归档 `pipeline.json` 全量重算社区流水线的 `_day.json` |
| `tools/rederive_community_errors.py` | 用已归档控制台日志离线重算社区的 `errorMessages` |
| `tools/merge_archive.py` | 把归档收成「一个目录两份文件」（历史迁移用） |

---

## 配置

**`config.json`**（在 git 里，随仓库公开）：

| 段 | 作用 |
|---|---|
| `date_range` | 分析区间。留空则取「前一个工作日」单日（自动跳过周末与法定节假日） |
| `products` | 产品范围，空数组 = 全部产品（由看板一级汇总接口自动发现） |
| `analysis_policy` | 按产品的口径例外（`always_analyze` / `scheduled_only`） |
| `workday_overrides` | 工作日筛查兜底（自动拉取法定节假日与调休，API 不可达时回退） |
| `chrome` | 浏览器自举：调试端口、profile、起始页、并发与超时 |
| `collect` | 各接口分页大小、重试、并发、日志截取阈值 |
| `cache` | 增量采集缓存开关与路径 |
| `github` | GitHub API 鉴权与仓库映射 |

**凭据不要写进 `config.json`**——该文件在 git 里且仓库公开，`ghp_` 开头的 token 会被 GitHub secret scanning 自动吊销。token 放 `config.local.json`（已 gitignore）或环境变量 `RCA_GH_TOKEN`。

---

## 交付前检查

```powershell
python tools/list_pending.py --strict    # 退出码 0：无待分析记录
python tools/verify_archive.py           # 结论：归档中每条结论都能落到证据
python run_pipeline.py --only step9      # 重出页面
```

改口径只改 `config.json`；改采集逻辑看 `steps/step_*.py` 头部 docstring 与 `docs/采集实现参考.md`；完整流程说明见 `SKILL.md`。
