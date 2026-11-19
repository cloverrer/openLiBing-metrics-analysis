# 夜间指标根因分析 — 日报（分析日 2026-11-19）

## 一、分析日期与范围
- 分析对象：前一个工作日 **2026-11-19**（自动跳过周末与法定节假日；`config.json` 的 `date_range` 留空，由脚本推导）。
- 归档区间：`2026-11-19 ~ 2026-11-19`（归档库累计口径 2026-11-10 ~ 2026-11-19，共 8 个归档日）。

## 二、覆盖范围与数据量
- 覆盖组件：**15** 个（含 openGauss / openEuler / UBS Core 三个社区组件）；当日流水线 **55** 条。
- 执行记录：当日 **76** 条（归档全量 682 条）；归档全量流水线目录 428 个，证据引用 231 个（缺失 0）。
- 当日记录按状态：完成 47、成功 8、失败 19、取消 2；其中进入 AI 根因分析范围的共 **15** 条（3 条 MindSpeed、3 条 MindStudio、1 条 openGauss、8 条 SgLang）。

## 三、版本可用度 / 编译成功率概览
- **版本可用度**：未达 100% 的组件共 4 个 —— **SgLang 0%**（唯一流水线 `nightly-test-npu.yml` 当日 8 次运行全部失败）、**MindStudio 83%**（`msprof` 当日 3 次运行全部失败）、**MindSpeed 89%**（`DrivingSDK_master` 当日 3 次运行全部失败）、**openGauss 86%**（`autobuild-opengauss-openeuler24.03-arm` 构建中断）；其余 11 个组件均为 100%。
- **编译成功率**：参与该口径的组件中仅 **openGauss 为 86%**（社区均值口径，7 条构建流水线中 24.03-arm 一条失败），其余组件均为 100%；github 平台（SgLang、vllm-ascend、MindSpeed 部分流水线）与 openEuler 不参与编译成功率口径。
- 低分项：`SgLang / nightly-test-npu.yml`、`MindStudio / msprof`、`MindSpeed / DrivingSDK_master`、`openGauss / autobuild-opengauss-openeuler24.03-arm`。

## 四、失败/取消运行根因摘要
当日共 19 条失败 + 2 条取消运行。按采集口径，15 条影响版本可用度/编译成功率维度、需做根因分析，结论按问题分类汇总如下：

| 问题分类 | 条数 | 运行 | 定性摘要 |
| --- | --- | --- | --- |
| 基础设施/平台 | 5 | `MindSpeed / DrivingSDK_master#2/#3/#4`；`SgLang / nightly-test-npu.yml#2271`、`#2275` | DrivingSDK 3 次运行在非构建类阶段（「其他任务」）失败、构建本身成功，归档无任务日志可查，问题落在编排调度类环节；SgLang 两次运行均在零时长~半分钟内即失败，未产生任何任务与日志，属平台侧异常。 |
| 依赖/环境缺失 | 4 | `MindStudio / msprof#280`；`SgLang / nightly-test-npu.yml#2272/#2273/#2274` | msprof 制作 a2/a3 aarch64 镜像时，每日构建批次 `20261119_1200` 缺 `mspti/aarch64` 依赖包，镜像构建中断；SgLang 三次运行测试脚本引用的 Ascend 自定义算子运行环境缺失（`libhcom.so` / `set_env.bash` 等）。 |
| 单元测试失败 | 3 | `MindStudio / msprof#281`；`SgLang / nightly-test-npu.yml#2268`、`#2269` | msprof `Test_msprof_smoke_A3_large_model` 4 条 PTA profiling 用例校验 `ascend_pt` 产物时抛 AssertionError；SgLang 分别出现多条 NPU 用例断言失败（HiCache 缓存未命中）与多条 PD 分离用例 prefill/解码失败。 |
| 资源不足 | 2 | `MindStudio / msprof#279`；`openGauss / autobuild-opengauss-openeuler24.03-arm#767` | msprof 冒烟测试申请的 A2/A3 设备环境排队约 1.5 小时后被拒绝分配，用例一条未跑；openGauss 编译后期构建机磁盘写满（No space left on device）导致编译中断。 |
| 配置/参数错误 | 1 | `SgLang / nightly-test-npu.yml#2276` | 采样算子 `markov_sample_step_triton()` 收到非预期关键字参数 `softcap`，调度器崩溃。 |

其余 6 条失败/取消运行按口径判定为豁免、不在应分析集合内（不影响当日两项指标）：
- **豁免 6 条**：`MindSpeed / MindSpeed-A3_master#3`（取消）、`UBS Core / Nightly-CI-Version-pipeline_BeiMing#269`（社区口径）、`vllm-ascend / a2.yaml#15575`、`a2.yaml#15581`、`a3.yaml#16602`、`a3.yaml#16615`。

## 五、校验结论
- `python tools/list_pending.py --strict`：退出码 **0**，待分析 0 条，分析完整性校验通过（682 条记录无漏分析/多分析）。
- `python tools/verify_archive.py`：**通过**（8 个归档日、428 个流水线目录、682 条执行记录、231 个证据引用缺失 0；漏分析/多分析/待分析未完成均为 0）。
- 三段流程均已完成：取数归档（退出码 0）→ AI 根因（15/15 写回成功）→ 重出页面（首页 72.0 KB、二级页 132.9 KB）。

## 六、提交与推送
- 本地提交已完成：`bde836d up to 11.19`（工作区已干净）。
- **推送失败（未完成）**：连续两次 `git push origin master` 均因网络不通失败，未能推到远端，GitHub Pages 在线看板本次不会更新。
  - 第 1 次：`fatal: unable to access 'https://github.com/cloverrer/openLiBing-metrics-analysis.git/': Recv failure: Connection was reset`（退出码 128）。
  - 第 2 次：`fatal: unable to access 'https://github.com/cloverrer/openLiBing-metrics-analysis.git/': Failed to connect to github.com port 443 after 21058 ms: Could not connect to server`（退出码 128）。
  - 处置：非远端拒绝（无新提交），本地提交已就绪；待网络恢复后执行 `git push origin master` 即可完成发布，未使用任何强推、未改动 git 配置。

