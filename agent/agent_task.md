# 第 8 步【agent 执行】AI 根因分析任务书

> 采集、归档、出页、按周期筛数据、**日志抓取**全部由脚本完成（`python run_pipeline.py`；
> 社区数据源由 `python tools/collect_community_nightly.py` 按 `community_sources.json` 通用采集）。
> **AI 只做本文件描述的这一步**：读一份纯文本取证包 → 写纯文本根因结论 → 交给
> `tools/write_analysis.py` 写回。页面由第 9 步脚本生成，**AI 不写 HTML、不改数据、不抓接口、
> 不为单条流水线写一次性脚本**。

## 〇、一次交互做完（AI 的标准动作，就三步）

```powershell
python tools/digest_pending.py            # 1) 唯一输入：清单 + 每条记录的失败任务、报错点、证据原文（带行号）
# 2) 按下面的格式写 out/state/analysis_result.txt（纯文本块，见「四、输出格式」）
python tools/write_analysis.py --file out/state/analysis_result.txt --dry-run   # 3) 校验
python tools/write_analysis.py --file out/state/analysis_result.txt             #    写回
python run_pipeline.py --only step9                                            #    重出页面
```

**不要**逐条 `--show`、逐条 `--grep` 往返：`digest_pending.py` 已经把每条记录的报错点与
对应原文行打好包，读一遍就够。只有某条确实需要再往下挖时才用
`python tools/digest_pending.py --record "组件|流水线#构建号" --ev-lines 60`
或 `tools/read_evidence.py`（两者都按行窗口取，不会刷屏）。

## 一、输入（全部只读）

| 来源 | 作用 | 怎么拿 |
|---|---|---|
| `python tools/digest_pending.py` 的输出 | **唯一主输入**：每条待分析记录的失败任务、报错点、证据原文行（带原始行号）、失败用例、记录位置 | 直接跑，一次拿全；记录多时 `--max-records` / `--record` 分批 |
| `out/archive/<年>/<年-月>/<日>/<组件>/<流水线>/pipeline.json` 的 `records[]` | 单条执行记录（分析的最小单位） | `python tools/list_pending.py --show <recordId>` 打印记录位置（`…/pipeline.json records[N]`） |
| 同目录 `pipeline.evidence.json` 的 `files` 键 | 证据原文（`job_logs/*.log`、`case_logs/*.html`、`github_logs/gh_<runId>/` 三类已逐行内嵌，磁盘上没有散文件了） | 记录内 `tasks[].logFile` / `errorLines`、`subTasks[].logFile`、`tasks[].cases[].localLog` 给出的路径就是 `files` 的键；取正文用 `python tools/read_evidence.py`（见输出纪律） |
| `agent/analysis_profile.json` | 可变量：定性分类、置信度、措辞规则、维度定义 | 直接读（小文件） |

## 二、分析范围（脚本已定，不要自行扩大）

- **只分析 `analysis.status=pending` 的记录**（`list_pending.py` 默认就只列这些）。
- `analysis.status=na` 的记录**不要分析**：它是成功运行，或当日两指标都为 1 的达标日。
- **vllm-ascend** 的口径已在采集阶段处理：不看板值是否为 1、按 `(scheduled)` 运行重算，只采定时运行。分析时按记录里的实际值走，不要另立规则。
- 清单里有几条就分析几条，不跳、不合并、不按流水线打包。

## 三、执行流程

```powershell
python tools/digest_pending.py                    # 1) 纯文本取证包：清单 + 报错点 + 证据原文（一次拿全）
# 2) 写结论到 out/state/analysis_result.txt（纯文本块，格式见下一节）
python tools/write_analysis.py --file out/state/analysis_result.txt --dry-run
python tools/write_analysis.py --file out/state/analysis_result.txt
# 3) 重生成页面（不重采集）
python run_pipeline.py --only step9
```

**批量模式（一次交互出全部结论）**：常规夜间流程本来就是「清单里几条就一次分析几条」。重分析已 `analysis.status=done` 的旧数据时，脚本会拦下这些条目，必须加 `--force` 才允许覆盖：

```powershell
python tools/write_analysis.py --file out/state/rean_result.txt --dry-run --force
python tools/write_analysis.py --file out/state/rean_result.txt --force
```

不要把一次批量任务拆成多轮对话（每轮只回几条）——证据都已落在归档里，读完取证包后一次性写完所有块，字段与单条模式完全一致。

## 四、输出格式（唯一交付物）

写一个 `out/state/analysis_result.txt`：**每条记录一个文本块，纯文本、不用 JSON**（`根因` / `建议` 直接多行写，空行分段，不转义换行）。块头一行 `=== 组件|流水线#构建号`，其余按 `键: 值` 逐行写；键写到下一个 `键:` 或下一个 `===` 为止。下面两条示例取自真实案例，分别对应「单一成因」与「有共性、分两类」两种写法：

```
=== HPCKit|kuqcd#210
分类: 权限问题
简述: 执行机上拉代码的凭据失效了
错误: fatal: Authentication failed for 'https://gitcode.com/kunpengcompute/hpckit-autotest.git/'
根因: 失败在用例代码拉取环节：构建第一步 clone 用例库 hpckit-autotest 时就鉴权失败，git 直接退出，用例一条都没执行，所以不是被测组件的问题——执行机上的 gitcode 凭据失效（token 过期或没有该私有仓读权限）就是本条的唯一原因。
建议: 换掉执行机上的 gitcode 凭据：换一个未过期、且有该私有仓读权限的 token 或部署公钥，然后在同一节点手工 clone 一次，确认能正常取到分支。同类问题成批出现时（同一处鉴权失败导致的多条流水线）一次改配置覆盖即可。

验证方式：重跑该流水线，要求 clone 成功、测试任务能拉起用例且 total 大于 0、用例通过率 100%。
引用: job_logs/03_kuqcd_210_build.log:L138

=== Ascend-CANN|ops-transformer#165
分类: 基础设施/平台
简述: 多卡机器的通信域建不起来
错误: HCCL function error: hcclCommInitRootInfoConfig(...): invalid ranktable
根因: 冒烟 job 由 4 个 pytest 分片串行执行 98 个用例，其中 19 个失败让退出码变成 1，冒烟阶段判 FAILED，后面的「归档」阶段停在 INIT。

第一类（15 个用例，MC2 多卡通信类算子）：从 aclnnMatmulAlltoAll 开始 HCCL 通信域初始化失败，之后被测试框架统一记成 accuracy not passed，覆盖 MatmulAlltoAll / AllGatherMatmul / MatmulAllReduce / MoeDistributeDispatch 等全部 MC2 用例，因此更像多卡环境的 HCCL 通信域（ranktable / IP / 端口 / 驱动）问题，而非单个算子逻辑缺陷。

第二类（4 个用例，MoeTokenUnpermuteWithEpGrad）：tiling 里对 grad 输出形状做了断言，这 4 个用例的数据不满足该约束直接失败，与通信无关。
建议: 先查多卡环境的 HCCL 通信域：核对 ranktable、device IP 与端口、HCCL 版本与驱动是否一致，再在已知正常的同型号节点上单独复跑 aclnnMatmulAlltoAll、aclnnAllGatherMatmul 各一次——换节点后不再报 HCCL 错，问题就在环境而不在算子。

MoeTokenUnpermuteWithEpGrad 这一类单独修：对齐 tiling 里 grad 输出形状的断言与该 4 个用例的实际 shape，用例数据变更过就更新用例，是算子回归就改 tiling 的约束逻辑。

验证方式：重跑上述 19 个用例，要求全部通过、日志中不再出现 HCCL function error，冒烟阶段退出码为 0、「归档」阶段能正常执行。
引用: job_logs/02_ops-transformer_165_smoke.log:L902, job_logs/02_ops-transformer_165_smoke.log:L1383
```

字段要求（中英文键名都认，写中文最省事）：

| 键 | 必填 | 要求 |
|---|---|---|
| `=== <recordId>` | **必填** | 直接用清单里打印的原值（`组件\|流水线#构建号`，`/` 写法也兼容） |
| `错误` | **必填** | 一句话报错原文：AI 从本次执行的日志与测试报告里筛出的「最有价值报错点」，即决定这次失败的那一行。页面的「错误信息」列直接展示它，所以要给真实报错原文（封装码还原成底层报错），不要带「首次出现 03:25:16 · 全日志 1590 处」这类统计修饰（规模只在根因里一句话概括）；兜底的汇总行（如 `19 failed, 63 passed`、`exit code 1`）不算关键报错，除非日志里确实没有更具体的失败点 |
| `分类` | **必填** | 问题分类：沿用参考仓的 10 类根因，只能选一个 —— `代码编译错误` / `单元测试失败` / `依赖/环境缺失` / `网络/下载失败` / `资源不足` / `超时` / `权限问题` / `配置/参数错误` / `基础设施/平台` / `无法判定`。页面「问题分类」列把这一项染色展示（一列色标扫下来就能分堆），写错或漏写整条会被写回脚本拒绝。判据见下节「问题分类：十选一」 |
| `简述` | 选填 | 一句话说清「具体故障点」——页面上不进「问题分类」列，只作为「定性」列在根因正文抽不出词时的兜底。40 字以内，专业通俗，如「执行机 gitcode 凭据失效，clone 被鉴权拒绝」「集群 A3 NPU 资源不足，作业调度超时」 |
| `根因` | **必填** | 根因正文（写法见下节）：**先判断这条是单一成因还是有共性、分属多类** —— 单一成因就 1~2 句「在哪一步失败 → 为什么 → 所以问题在谁那边」，不分段、不分类；确有共性且成因不同才分段写「第 N 类（M 个用例，共性）：」。正文里**不写报错码**（`DEV-CODECI-35002`、`error code is 4`）、**不写 `文件名:行号`**、不写时间线流水账、不写「已排除的干扰项」（确有易混淆告警、一句话能说清时才补）。**每段（尤其分类段与结论段）开头先给一句专业、通俗的定性结论**——直接点明故障机理与责任方（「执行机 gitcode 凭据失效，用例库 clone 被鉴权拒绝」「集群 A3 NPU 资源不足，作业等待调度超时」「测试框架性能数据导出失败，导致用例被误判失败」），再展开因果。**措辞要专业通俗：既不堆砌术语，也不写成「XX坏了」这类口语**——用工程语言陈述现象与机理（「凭据失效」「资源不足导致调度超时」「接口返回 NotFound」「性能吞吐未达基线阈值」），让读者一眼看懂是什么问题、该谁处理 |
| `建议` | **必填** | 修复建议，**默认两段**：一段「动手做什么」（换哪个凭据 / 改哪个配置 / 修哪处代码，写到能直接动手），一段以 `验证方式：` 开头写通过标准。根因分了几类的，每类一段动作，验证方式仍收尾。禁止分点序号，禁止"建议排查""建议关注"这类空话 |
| `引用` | **必填** | `文件名:行号`，逗号/空格分隔，来自全量日志/用例日志/github 日志；**只供页面「证据」弹窗定位原始行，正文里不再写**。`错误` 那句话必须能在其中某一条引用的行里找到（写回脚本会逐行核对，对不上会整条拒绝） |

脚本强制校验：`根因` 为空、`分类` 缺失或不在十类白名单、`recordId` 找不到、记录不是 `pending`（且未加 `--force`）、`错误` 与 `引用` 对不上（引用的文件都能读、却没有一行包含这句话）的条目会报错整条跳过，不会静默写入。重分析已 `done` 的旧数据时必须加 `--force`，否则每条都会被判为「只有 pending 才需要写回」而跳过。老归档若已有 JSON 格式的结论文件（`analysis_result.json`），写回脚本同样能识别，两种格式可混用。

### rootCause 的写法：先判断要不要分类，再给「原因 + 谁的问题」

页面把 `rootCause` / `advice` 按 `\n` 切成逐段渲染（空行 = 段间距）。根因要回答的是「**为什么会这样、该谁去修**」，不是「**看到了哪些报错**」。**长短不是评优标准——一条能说清就绝不写第二条。**

第一步：判这一条属于哪种情况

| 情况 | 怎么写 |
|---|---|
| 原因单一且明确（凭据失效 / 没有权限 / 用例库拉不下来 / 资源或磁盘不足 / 某条编译命令报错 / 某个 shape 断言不过） | 一段话、1~2 句：**在哪一步失败 → 为什么 → 所以问题在谁那边**。不分类、不分段、不铺时间线、不贴报错栈 |
| 失败原因确有共性、且分属两三类不同成因（报错签名或机制明显不同） | 第一段一句总述失败链，之后每类一段，段首「第 N 类（M 个用例，共性）：」，冒号后一句话说清该类成因 |
| 证据只到任务类型这一层（无任务日志、无用例明细） | 一段话写清证据止于哪一层 + 按任务类型给的判定，不猜、不铺陈 |

```
【反例，不允许 —— 一条明确的「没权限」写成一页】
第一类（用例仓拉取鉴权失败）：01:11:48.112 日志报 fatal: Authentication failed for '…'，紧接着脚本自己打印
[ERROR] git clone test_cases code fail，01:11:48.273 以 script returned exit code 1 退出…（xx.log:L138、L140）
第二类（封装码不具备诊断价值）：job 与 step 层都只留了 {"errorMessage":"构建任务执行失败!","errorCode":"DEV-CODECI-35002"}…
已排除的干扰项：…
——一条「凭据失效」被拆成两类、贴了三处出处、还分析了封装码，读者要多读十行才看到结论

【正例，同一个问题】
失败在用例代码拉取环节：测试任务第一步 clone 用例库时就鉴权失败，用例一条都没执行，所以不是被测组件的缺陷，
问题在执行机上的 gitcode 凭据（token 过期或没有该私有仓读权限）。
```

硬性要求：

1. **不写报错码**：`DEV-CODECI-35002`、`error code is 4`、`561002` 这类码对读者没有信息量，改成它代表的机制（「鉴权失败」「通信域初始化失败」「tiling 形状断言不过」）
2. **不写 `文件名:行号`**：原始位置只写进 `cites`，页面的「证据」弹窗会展示；正文里出现路径或行号一律视为不合格
3. **不为了显得严谨而拆类**：单一成因拆成「第一类/第二类」是最常见的多余输出；分类只在成因确实不同、且各自覆盖多条用例时才用，类数不超过 3
4. 不写「已排除的干扰项」段；确有易混淆告警、一句话能说清时才在末尾补半句（「日志末尾的 timeout 是中止的连带结果，不是独立故障」）
5. 不铺时间线流水账（「01:11:48.112… 01:11:48.273… 01:11:52…」）；排队类根因必须给起止与等待时长，但也只写这几个点，不逐点贴出处
6. 段内不换行，段与段之间只用一个 `\n\n`；不用 `一、二、三`、不写「分析过程：」「判定依据：」这类标签、不写 markdown（`**` `-` `1.` 表格）
7. 推断只能基于日志里出现的现象，不确定的写「更像 / 疑似」，不得当事实陈述；证据缺失就写明止于哪一层，不用推断替代
8. 「定性」列由页面从正文抽句子逐条列出（有「第 N 类（M 个用例…）」就每类一条，没有就取结论段，**只有一条时不带编号**）：抽的是「更像 X，而非 Y」里的 X 和「凭据/配置/版本…失效」「资源不足导致…超时」这类**故障机理短语**，所以**每段开头先写一句 10~20 字的专业定性**（「执行机 gitcode 凭据失效」「集群 NPU 资源不足，作业调度超时」「性能数据导出失败，用例被误判」），再展开因果；结论埋在长句尾部的，这一列会截成半句话。**禁止「XX坏了」「XX拉不下来」这类口语**——专业术语能一句话说清的直接用术语；分类段括号里的标签只有带故障机理信号词才会被当作原因（「共性：宿主 pinned 内存耗尽」），纯粹的分组名（「量化变体」）会被跳过

### 问题分类：十选一（`issueType`）

一句话：**分类只回答「哪一类问题」，定性回答「具体坏在哪」**。分类进「问题分类」列（一个色标），定性和细节都写在 `rootCause` 正文里。

这 10 类直接沿用参考仓 `Daily_Availability_Check_for_Ascend` 的根因类别口径（类别名、判据、典型日志特征都对齐），不再自定义别的标签：

上一版的六个大类（环境问题 / 用例问题 / 业务Bug / 调度问题 / 工具问题 / 工程问题）已废弃：写回脚本对其中五个会自动折算到最接近的一类（用例问题→单元测试失败、环境问题→依赖/环境缺失、调度问题与工具问题→基础设施/平台、工程问题→配置/参数错误、待判定→无法判定），只有 `业务Bug` 因为横跨「编译错」与「单测/精度错」不再折算、会直接被拒，所以新写的结论一律按下面十类自己判。

| 分类 | 什么时候选它 | 典型日志证据 |
|---|---|---|
| `代码编译错误` | 被测代码/依赖在编译、构建环节就挂了 | `error:`、`undefined reference`、`syntax error`、编译目标 FAILED、`make` 退出码非 0 |
| `单元测试失败` | 用例跑起来了，但在断言、结果校验、精度比对上失败 | `FAILED test_xxx`、`AssertionError`、pytest 汇总行、`check point(...) not in ret`、精度比对不过 |
| `依赖/环境缺失` | 缺包、缺命令、缺镜像，机器上没准备好就跑 | `No module named`、`command not found`、`package not found`、镜像拉不下来、`pip install` 失败 |
| `网络/下载失败` | 拉代码、拉数据、访问外部服务时网络不通 | `Connection timed out`、`Could not resolve host`、`404 Not Found`、`Connection reset` |
| `资源不足` | 机器上的资源被占满/不够分 | `No space left on device`、`Out of memory`、`OOM`、`Killed`、`Insufficient huawei.com/Ascend*` |
| `超时` | 跑到时限被掐断，或等待某状态等到超时 | `timeout`、`exceeded the time limit`、`timeout !!! the status of pod is not Running`、执行被终止 |
| `权限问题` | 被鉴权/授权挡住，操作本身没错 | `Permission denied`、`403 Forbidden`、`Authentication failed`、token 过期、没有私有仓读权限 |
| `配置/参数错误` | 流水线参数、作业配置、命令行参数写错 | `invalid config`、`missing required parameter`、`illegal argument`、`invalid ranktable`、阶段编排/通知配置错 |
| `基础设施/平台` | 平台侧出问题：runner 失联、pod 驱逐、调度不上、平台接口报错 | runner 失联、pod 驱逐 / 持续 Pending 未调度、`internal server error`、调度器异常 |
| `无法判定` | 日志里没有有效错误特征，如实写明，不要猜 | 只有封装码、日志为空 / 被截断，且已按任务类型排除过 |

判断顺序（避免摇摆）：先看失败点在哪一步 —— 编译/构建阶段 → `代码编译错误`；缺包缺命令缺镜像 → `依赖/环境缺失`；网络/下载 → `网络/下载失败`；被鉴权挡住 → `权限问题`；资源/磁盘/内存 → `资源不足`；跑到时限 → `超时`；平台侧（runner、pod、调度）→ `基础设施/平台`；参数/配置写错 → `配置/参数错误`；都不是，用例跑起来了才失败 → `单元测试失败`；证据不足以判断 → `无法判定`。

**混合成因只选一个主因**：一条记录里既有平台问题、又有少量用例断言失败，`issueType` 取覆盖用例数最多 / 决定这次失败的那一类（上例 19 个失败用例中 15 个是通信域 → `基础设施/平台`），其余成因在 `rootCause` 里分段写清，不要为凑分类硬拆两个标签。

### advice 的写法：动手做什么 + 怎么算修好

`advice` 是「拿去就能做」的动作，不是问题清单。**默认两段，段间空一行**：

1. **动作段**：换哪个凭据 / 改哪个配置项 / 修哪处代码，写到能直接动手（「换一个未过期且有该私有仓读权限的 token，并在同一节点手工 clone 一次确认能取到分支」）
2. **验证方式**：以 `验证方式：` 开头 —— 复跑什么、通过标准是什么（用例数 > 0 且通过率 100%、退出码为 0、日志里不再出现某个现象）

根因分了几类的，动作段按类各写一段，最后一段仍是验证方式；只有一类就只写一段动作，**不要为了凑结构硬拆成四段**。

硬性要求：

1. 不出现「一、」「二、」「1.」这类序号，靠分段和「若…再…」体现次序
2. 每个动作都要可执行、可判定，不写「建议排查」「建议关注」
3. 与 `rootCause` 的归组对应：根因里分了几类，建议里就有对应的动作；根因只有一条，建议就不要展开成排查清单
4. 「验证方式」不能只写「重跑验证」，必须有明确的通过标准
5. 唯一值得多写的一句：同一处配置/凭据导致同批多条流水线时，补「同批 XX#N、YY#N 同一原因，一次改配置覆盖」——写在这一段末尾，不单独成段

## 五、输出纪律（硬性——防「输出过长，请输入继续」中断）

1. **禁止整读大文件**：`pipeline.json`（含当日该流水线全部记录与证据引用）、`pipeline.evidence.json`（证据原文，单目录最大几十 MB）一律按行窗口读。证据原文只能用 `tools/read_evidence.py` 取（它读的就是内嵌正文，自带回显上限），不要用整文件读取命令：

   ```powershell
   python tools/read_evidence.py --record "HPCKit|kuqcd#210" --list                                  # 该次执行有哪些证据、各多少行
   python tools/read_evidence.py --record "HPCKit|kuqcd#210" "job_logs/03_kuqcd_210_build.log:L138"  # 取第 138 行（与 cites 同写法）
   python tools/read_evidence.py --record "HPCKit|kuqcd#210" --path job_logs/03_kuqcd_210_build.log --lines 120-200   # 取一段
   python tools/read_evidence.py --record "HPCKit|kuqcd#210" --grep "ERROR|fatal" --ctx 2            # 直接搜报错，带上下文
   ```

2. **一次拿全，别逐条往返**：主输入只有 `python tools/digest_pending.py`（清单 + 报错点 + 证据原文已打好包）；只有某条确实要再往下挖，才按行窗口补读，不做「每轮只看一条」的循环
3. **单条命令回显 ≤100 行**：可能刷屏的命令加 `| Select-Object -Last 40` 或重定向到临时文件再读尾部
4. **不粘贴大段日志**：对话只回结论，原始行只写进 `引用`（正文里不再出现 `文件名:行号`）
5. **不向用户提问等待**：夜间无人值守，数据有缺口就按现有证据定性并在 `rootCause` 里注明"证据不完整"

## 六、取证与定性规则

1. **封装码不算结论，也不进正文**：`DEV-CODECI-35002` 等只说明"失败在云构建层"。先查整 job 全量日志里的真实报错（调度失败、环境拉起、资源不足、命令报错都能看到原文），只有确实无有效报错时才定性"平台/基础设施"并注明日志无有效报错；正文里写机制（「鉴权失败」「调度未申请到资源」），不写码本身。
2. **buildflow 任务（`subTasks` 非空）必须下钻失败子任务**：整 job 日志只有 `build_flow` 调度层记录（如 `Follow jobs are failed`），真实编译报错在 `subTasks[].errorLines` 与 `subTasks[].logFile`。
3. **test 任务**：以 `cases[]` 的 `description`（断言消息）+ `errorMessages`（带 `line`）为准，用例日志原文在 `localLog`；失败用例状态字段是 `state` 不是 `status`。
4. **github 平台任务（`platform=github`）**：`evidenceNote` 非空表示 GitHub 侧日志未留存（blob 404），按 `githubJob.conclusion` / 时长 / 失败步骤定性并注明证据不完整，**不得虚构日志内容**；测试 job 先看 `testResults`（`failedModels` / `aisbenchFailed` / `pytestFailed`），根因要定位到具体用例或模型。
5. **证据止于「任务类型」这一层**：`tasks` 为空或 `counts.logTasks=0`（如 hcomm / shmem / MindIE-Motor 类）时，先看记录里的 `ftt`（服务端 `failedTaskType`，如「测试任务」「构建任务」）与 `status`，**服务端已经给出失败类型时不得判成"证据缺失"**（记录里的 `verdict.category` 是脚本按规则打的分档标签，页面不展示；`issueType` 仍要按十类自己判）：
   - `ftt` 非空：含「测试」→ `单元测试失败`，含「构建/编译」→ `代码编译错误`，含「部署/环境」→ `依赖/环境缺失`，含「取消」→ `基础设施/平台`；`rootCause` 就写一句「失败在<类型>阶段，平台侧未留存任务日志与失败用例明细，证据止于任务类型这一层」
   - `status=CANCELED`：`issueType` 写 `基础设施/平台`，`rootCause` 写「运行被取消（CANCELED）」，并说明取消发生在哪个失败任务类型执行期间
   - 只有 `ftt` 为空、`status` 也不是 CANCELED 且无任何日志/用例时，才写 `无法判定`，结论写「该运行无任何任务日志与用例落盘，仅能从运行状态判定失败」
6. **排队类根因只给几个时间点**：申请开始、放弃/失败时间与等待时长（按起止时间差算，不得用"轮询次数×间隔"推算），一到两句写清；`文件名:行号` 只进 `cites`，正文不贴。禁止只写"资源调度失败"。
7. **指标异常类**：当日版本可用度非 1 且运行日志无失败时，检查是否"无成功运行 / 用例通过率未达 100% / 运行被取消"，按实际值定性。
8. **不得虚构**：日志没写的只能写"疑似/待核对"，不能当事实。
9. **每条都要给 `issueType`**：十选一（见上文「问题分类：十选一」），判不出就写 `无法判定`。这一项是页面「问题分类」列的唯一来源，也是写回脚本的硬门槛 —— 漏写或写进这十个值以外，整条会被拒绝写入；`issueDetail` 是选填的一句话兜底，不用重复 `rootCause` 里的细节。

## 七、可变配置（改 `agent/analysis_profile.json` 即可，不改代码）

| 想改什么 | 改哪一节 |
|---|---|
| 十类根因的判据与举例（`issueType` 白名单本身在 `tools/write_analysis.py` 里，改类别要连代码和 `steps/step_9_pages.py` 的配色一起改） | `analysis.classification` |
| 置信度标准 | `analysis.confidence_rules` |
| 措辞硬性规则（含根因/建议写法） | `analysis.wording_rules` |
| 双维度指标定义与灯色 | `analysis.dimensions` |
| 失败任务类型（`ftt`）定性口径 | `analysis.deep_dive.failed_task_type_policy` |
| buildflow 子任务下钻规则 | `analysis.deep_dive.subtask_drilldown` |
| github 平台取证口径 | `analysis.deep_dive.github_evidence` |
| 排队类时间线举证要求 | `analysis.deep_dive.pending_timeline` |
| 封装错误码清单 | `analysis.wrapper_codes` |
| 附加专项关注点 | `analysis.extra_focus`（逐条执行） |

分析配置只影响 AI 的判断口径，不改动 `out/archive/` 下任何已归档数据，可对同一份证据反复重分析。
