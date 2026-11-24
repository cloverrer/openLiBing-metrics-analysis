# 夜间指标根因分析 — 日报（分析日 2026-11-23）

## 一、分析日期与范围
- 分析对象：前一个工作日 **2026-11-23**（自动跳过周末与法定节假日；`config.json` 的 `date_range` 留空，由脚本推导）。
- 归档区间：`2026-11-23 ~ 2026-11-23`（归档库累计口径 2026-11-10 ~ 2026-11-23，共 10 个归档日）。

## 二、覆盖范围与数据量
- 覆盖组件：**15** 个（含 openGauss / openEuler / UBS Core 三个社区组件）；当日流水线 **54** 条。
- 执行记录：当日 **62** 条（归档全量 816 条）；归档全量流水线目录 536 个，证据引用 317 个（缺失 0）；当日内嵌证据文件 71 份。
- 当日记录按状态：成功 47（完成 40、成功 7）、失败 14、取消 1；其中进入 AI 根因分析范围的共 **13** 条。

## 三、版本可用度 / 编译成功率概览
- **版本可用度**：未达 100% 的组件共 5 个 —— **SgLang 0%**（`nightly-test-npu.yml` 当日 6 次运行全部失败）、**MindStudio 16.7%**（`msprof`、`msprobe`、`msserviceprofiler`、`msmemscope`、`msmodelslim` 五条流水线当日运行全部未达标）、**MindIE 50%**（`MindIE-SD` 当日 1 次运行失败）、**MindSpeed 80%**（`DrivingSDK_master` 未达标）、**openGauss 85.7%**（`openEuler 24.03 arm` 构建失败）；其余 10 个组件均为 100%。
- **编译成功率**：参与该口径的组件中仅 **openGauss 85.7%**（`autobuild-opengauss-openeuler24.03-arm` 当日构建失败）未达 100%；github 平台（SgLang）与 openEuler 不参与编译成功率口径；其余组件均为 100%。
- 低分项（流水线级）：`MindIE / Nightly-CI-Component-pipeline_MindIE-SD`、`MindStudio / Nightly-CI-Component-pipeline_msprof|msprobe|msserviceprofiler|msmemscope|msmodelslim`、`MindSpeed / Nightly-CI-Component-pipeline_DrivingSDK_master`、`SgLang / nightly-test-npu.yml`、`openGauss / openEuler 24.03 arm`。

## 四、失败/取消运行根因摘要
当日共 15 条失败/取消运行。按采集口径，13 条影响版本可用度/编译成功率维度、需做根因分析，结论按问题分类汇总如下：

| 问题分类 | 条数 | 运行 | 定性摘要 |
| --- | --- | --- | --- |
| 资源不足 | 5 | `MindStudio / msmemscope#275`、`msprobe#277`、`SgLang / nightly-test-npu.yml#2285`、`#2289`、`openGauss / autobuild-opengauss-openeuler24.03-arm#768` | 三型资源类失败：①`msmemscope`/`msprobe` 申请 A2/A3 单机 8 卡环境，每 30 秒轮询一次共 179 次（约 90 分钟）始终 queued、可用节点 0，框架判定环境分配失败、退出码 1；②`SgLang#2285` 执行机主机内存不够，scheduler 准备 prefill 批次时 `torch_npu` 抛 OutOfMemoryError 被信号终止，`#2289` 是 DeepSeek-R1-0528-W8A8 权重占满显存，`--mem-fraction-static=0.68` 下无剩余显存分配 KV 缓存，框架要求提到 0.709 以上；③`openGauss#768` 构建机磁盘写满，汇编器写目标文件报 No space left on device，打包上传同样因空间不足失败。 |
| 基础设施/平台 | 3 | `SgLang / nightly-test-npu.yml#2290`、`#2291`、`#2295` | 三次运行均由代码提交触发但在运行平台侧未创建任何作业：作业总数为 0、无失败作业清单，开始与结束时间同刻（14:42:31 / 14:52:43 / 19:36:50），工作流在启动阶段即结束，取证确认取不到日志，失败点无法定位、证据不完整。 |
| 依赖/环境缺失 | 2 | `MindIE / MindIE-SD#126`、`MindStudio / msmodelslim#280` | `MindIE-SD#126` 5 条冒烟用例全部卡在导入阶段：hunyuanvideo 缺 `imageio`，Qwen-Image-Edit/flux/Wan2.2-TI2V/Wan2.2-T2V 缺 `diffusers`，均报模块缺失；`msmodelslim#280` 是 k8s_652 的 2 条量化用例安装依赖时 torch 版本校验失败（环境 cp311/torch 2.10.0+cpu，SD 场景要求 pt2.9.0），另有 k8s_A3、k8s_2_A3 两个任务排队 179 次后环境分配失败。 |
| 单元测试失败 | 2 | `MindStudio / msprof#286`、`msserviceprofiler#259` | `msprof#286` 用例 `test_dynolog_monitor_and_trace` 在 A2/A3 两条大模型用例日志里均未匹配到预期模式（dynolog 进程加载 json 成功、iteration 1），框架抛 RuntimeError 判失败；`msserviceprofiler#259` 6 条 vLLM 性能采集用例在解析结果校验环节失败，落盘目录实际文件与预期清单不一致（缺少或多余解析文件）。 |
| 超时 | 1 | `SgLang / nightly-test-npu.yml#2292` | 用例文件 `test_npu_speculative_moe_a2a_backend.py` 达到单文件 3600 秒时限仍未通过（passed=false、elapsed=3600），作业非零退出、整条运行判失败。 |

其余 2 条失败运行按口径判定为豁免、不在应分析集合内（不影响当日两项指标）：
- **豁免 2 条**：`Triton_Ascend / Ascend#144`、`UBS Core / Nightly-CI-Version-pipeline_BeiMing#277`。

## 五、校验结论
- `python tools/list_pending.py --strict`：退出码 **0**，待分析 0 条，分析完整性校验通过（816 条记录无漏分析/多分析）。
- `python tools/verify_archive.py`：**通过**（10 个归档日、536 个流水线目录、816 条执行记录、317 个证据引用缺失 0；漏分析/多分析/待分析未完成均为 0）。
- 三段流程均已完成：取数归档（退出码 0）→ AI 根因（13/13 写回成功）→ 重出页面（首页 72.0 KB、二级页 132.9 KB）。

## 六、提交与推送
- 本地提交：`680b769 up to 11.23`。
- 远端推送：**成功**（`0f76891..680b769  master -> master`），GitHub Pages 在线看板已更新；未使用任何强推、未改动 git 配置。
