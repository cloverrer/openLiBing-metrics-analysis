# 夜间指标根因分析 — 日报（分析日 2026-11-20）

## 一、分析日期与范围
- 分析对象：前一个工作日 **2026-11-20**（自动跳过周末与法定节假日；`config.json` 的 `date_range` 留空，由脚本推导）。
- 归档区间：`2026-11-20 ~ 2026-11-20`（归档库累计口径 2026-11-10 ~ 2026-11-20，共 9 个归档日）。

## 二、覆盖范围与数据量
- 覆盖组件：**15** 个（含 openGauss / openEuler / UBS Core 三个社区组件）；当日流水线 **54** 条。
- 执行记录：当日 **72** 条（归档全量 754 条）；归档全量流水线目录 482 个，证据引用 245 个（缺失 0）。
- 当日记录按状态：完成 52、成功 7、失败 13（无取消）；其中进入 AI 根因分析范围的共 **6** 条（2 条 vllm-ascend、1 条 MindIE、1 条 MindSpeed、1 条 boostkit、1 条 UBS Core）。

## 三、版本可用度 / 编译成功率概览
- **版本可用度**：未达 100% 的组件共 4 个 —— **MindIE 50%**（`MindIE-Motor` 当日 1 次运行失败）、**vllm-ascend 50%**（`a3.yaml` 当日 2 次运行全部失败）、**MindSpeed 75%**（`DrivingSDK_master` 与 `MindSpeed-MM_master` 各 1 条未达标）、**MindCluster 83.3%**（`MultimodalSDK` 未达标）；其余 11 个组件均为 100%。
- **编译成功率**：参与该口径的组件中仅 **boostkit 为 90%**（`Ultrascan` 当日 2 次构建 1 次失败）；github 平台（SgLang、vllm-ascend 及 MindSpeed/MindStudio 的部分流水线）与 openEuler 不参与编译成功率口径；其余组件均为 100%。
- 低分项（流水线级）：`MindIE / MindIE-Motor`、`MindSpeed / DrivingSDK_master`、`MindSpeed / MindSpeed-MM_master`、`MindCluster / MultimodalSDK`、`vllm-ascend / a3.yaml`、`boostkit / Ultrascan`；另 `UBS Core / Nightly-CI-Version-pipeline_BeiMing` 编译成功率为 96.3%。

## 四、失败/取消运行根因摘要
当日共 13 条失败运行。按采集口径，6 条影响版本可用度/编译成功率维度、需做根因分析，结论按问题分类汇总如下：

| 问题分类 | 条数 | 运行 | 定性摘要 |
| --- | --- | --- | --- |
| 单元测试失败 | 2 | `vllm-ascend / a3.yaml#16615`、`#16616` | 四个并发作业的 AISBench 精度用例全部在「响应异常校验（response anomaly）」环节被判失败：Kimi-K3 / Kimi-K2.6 作业里响应异常检测工具因被测模型使用 TikTokenTokenizer、工具却按 HuggingFace 接口取 `backend_tokenizer` 属性而抛 AttributeError 崩溃；QWEN3 / GLM-5.3 作业则是检出异常响应占比超阈值（gsm8k 62.93% / aime2025 10.00%）被判失败。 |
| 基础设施/平台 | 1 | `UBS Core / Nightly-CI-Version-pipeline_BeiMing#270` | 失败点在构建子步骤 `Build_ubs-io-dfc`：子任务返回失败，外层框架只带出「任务执行失败」而未见底层原因；归档在构建/测试两侧各只取到一份极短的框架日志，子任务真实日志缺失。 |
| 超时 | 1 | `MindIE / MindIE-Motor#140` | 用例 `test_pymotor_ras_p_redundant` 在环境准备阶段失败：部署 PyMotor 服务后等待就绪，一直未拿到成功日志，框架报「服务启动超时，未找到成功日志!」，随后用例被判 FAILED。 |
| 网络/下载失败 | 1 | `boostkit / Ultrascan#321` | 构建执行 `yum install sqlite sqlite-devel` 时，openEuler 22.03-LTS-SP4 的 update 源元数据拉取失败——两个镜像均报 Curl error 28（30s 连接超时）、其中一个校验和不匹配，最终 `repomd.xml` 下载失败、脚本以退出码 1 结束。 |
| 配置/参数错误 | 1 | `MindSpeed / DrivingSDK_master#81` | 用例 `test_003_sparse4d` 的结果提取脚本在配置里找不到 `expert_model_parallel_size` 参数，性能值提取为 0，框架报「无法获取性能结果」，用例判失败。 |

其余 7 条失败运行按口径判定为豁免、不在应分析集合内（不影响当日两项指标）：
- **豁免 7 条**：`MindStudio / msprobe`、`MindStudio / msmemscope`、`vllm-ascend / a2.yaml`、`SgLang / nightly-test-npu.yml`（2 条）、`UBS Core / Nightly-CI-Version-pipeline_BeiMing`（另一次）、`Triton_Ascend / Ascend`。

## 五、校验结论
- `python tools/list_pending.py --strict`：退出码 **0**，待分析 0 条，分析完整性校验通过（754 条记录无漏分析/多分析）。
- `python tools/verify_archive.py`：**通过**（9 个归档日、482 个流水线目录、754 条执行记录、245 个证据引用缺失 0；漏分析/多分析/待分析未完成均为 0）。
- 三段流程均已完成：取数归档（退出码 0）→ AI 根因（6/6 写回成功）→ 重出页面（首页 72.0 KB、二级页 132.9 KB）。

## 六、提交与推送
- （本段落盘时补记：本地提交与远端推送结果。）
