# Stage A0.3：最小 Dev 轨迹探针与标签泄漏审计

Stage A0.2 及标签资格修正已经通过。

本阶段只允许从固定版本中下载少量 dev 轨迹，用于验证文件定位、数据结构、解析可行性和潜在标签泄漏。

不得下载完整数据集、下载测试集轨迹、构建正式特征、训练模型或运行基线。

## 一、固定前置条件

必须沿用 Stage A0.1 固定的数据来源：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

必须先读取：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
artifacts/source_manifest.json
artifacts/dev_analysis_index.csv
artifacts/test_manifest.csv
artifacts/analysis_index_summary.json
research/01_DECISION_LOG.md
```

不得改变标签映射、分析主键、重复标注策略、Benchmark 分组或官方 dev/test 划分。

## 二、本阶段研究问题

只回答以下问题：

1. 唯一轨迹主键能否可靠映射到 Hugging Face 中的实际文件；
2. 不同 Benchmark 和模型的轨迹是否具有统一或可归一化的结构；
3. 一条轨迹中有哪些文本、动作、观察、工具调用和元数据字段；
4. 是否可以在不使用截图的情况下解析基本轨迹；
5. 哪些字段可能直接或间接泄露 Success、Side Effect 或 Looping 标签；
6. 后续最小实验需要下载哪些文件，预计数据量多大。

本阶段不得回答模型效果问题。

## 三、仅使用 dev

所有探针轨迹必须来自：

```text
artifacts/dev_analysis_index.csv
```

严禁：

* 下载 test 轨迹；
* 根据 test manifest 定位原始文件；
* 查看 test 的标签或轨迹内容；
* 将 test 用于解析调试。

脚本中必须加入断言：

```text
official_split == "dev"
```

只要发现样本不是 dev，必须立即拒绝下载或解析。

## 四、探针样本选择

目标选择不超过 24 条唯一 dev 轨迹。

### 第一部分：覆盖性样本

优先覆盖所有实际存在的：

```text
benchmark_group_primary × model_name
```

组合。

每个组合最多选择一条轨迹，目标是检查不同 Benchmark 和不同模型是否产生不同文件结构。

### 第二部分：标签现象补充样本

在剩余名额内，从 dev 主实验有效样本中补充：

* Success 正类与负类；
* Side Effect 正类与负类；
* Looping 正类与负类；
* 长轨迹候选；
* 短轨迹候选。

Side Effect 正类较少，可以有意识地纳入少量 dev 正类，但不得修改或重采样完整开发集。

### 样本选择要求

* 必须确定性选择；
* 固定随机种子或使用明确排序规则；
* 不得重复 trajectory_key；
* 不得选取 `eligible_main == false` 的目标作为标签现象代表；
* 样本选择规则必须记录并可重复生成。

生成：

```text
artifacts/dev_probe_manifest.csv
```

至少包含：

```text
trajectory_key
benchmark_original
benchmark_split_namespace
benchmark_group_primary
model_name
task_id
selection_reason
expected_repository_path
download_status
local_relative_path
file_size_bytes
sha256
```

探针 manifest 可以包含 dev 标签，但标签不得写入原始下载目录或作为轨迹内容的一部分。

## 五、先查询文件树，再下载

第一步只使用 Hugging Face API 查询固定 revision 下的文件列表和元数据。

必须明确：

1. 轨迹文件位于哪些目录；
2. trajectory_key 如何映射至文件路径；
3. 一个轨迹是否对应一个文件或多个文件；
4. 文件是否为 JSON、JSONL、压缩包或其他格式；
5. 是否依赖截图、HTML、日志或额外资源；
6. 是否存在相同任务和模型的路径歧义。

不得通过模糊匹配自动选择多个候选文件。

如果任何 trajectory_key 对应：

* 零个候选文件；
* 多个无法消歧的候选文件；
* 与当前主键冲突的多个独立运行；

必须记录并停止该样本的下载，不得猜测。

## 六、下载限制

只允许下载探针清单中的必要文本或结构化轨迹文件。

禁止下载：

```text
screenshots
images
videos
完整数据目录
test 轨迹
无关 judgment 文件
完整压缩数据包
```

如轨迹文件包含截图路径，只记录截图引用，不下载截图。

总下载量上限：

```text
200 MB
```

超过上限时必须停止，并汇报是哪些文件造成超限。

下载文件保存至类似：

```text
data/raw_probe/
```

该目录必须加入 `.gitignore`，原始数据不得提交 Git。

所有下载文件必须记录：

* 固定 revision；
* 仓库相对路径；
* 文件大小；
* SHA-256；
* 下载状态。

## 七、原始结构审计

对每条成功下载的轨迹进行递归字段枚举。

至少记录：

```text
field_path
observed_type
example_value_redacted
presence_count
benchmark
model_name
possible_semantic_role
```

生成：

```text
artifacts/trajectory_field_inventory.csv
```

`example_value_redacted` 只能保留短片段，不得复制完整轨迹内容。

需要识别的结构至少包括：

* task instruction；
* system prompt；
* agent message；
* assistant reasoning或其可见替代字段；
* action；
* tool call；
* tool result；
* observation；
* environment state；
* final response；
* timestamps；
* token or step count；
* model metadata；
* benchmark metadata；
* screenshot references；
* reward、score、success 或 judge 信息。

不得因为字段名不同就强行合并，必须先记录原始结构，再提出统一表示建议。

## 八、标签泄漏审计

对所有字段路径和短样例检查三类风险。

### 一级：直接标签泄漏

包括但不限于：

```text
success
successful
failure
passed
side_effect
looping
repetitiveness
ground_truth_label
annotation
human_judgment
judge_result
reward
score
task_reward
```

如果字段直接表示实验目标或官方判断，后续模型输入必须排除。

### 二级：强结果代理

包括但不限于：

* 环境明确返回 task completed；
* benchmark 自带最终评分；
* 自动评测器的通过/失败结果；
* 成功状态代码；
* 人工评价文本；
* 根据完整答案生成的 summary；
* 与标签同步生成的 judgment 文件。

这些字段是否可用于研究必须单独论证，默认不得进入输入特征。

### 三级：可能合理但需要说明的结果信息

例如：

* 最终页面状态；
* 工具报错；
* agent 自己声称“已完成”；
* 重复动作本身；
* 环境自然产生的成功提示。

这类信息可能是轨迹的正常组成部分，不一定属于泄漏，但必须记录其来源和实验使用原则。

生成：

```text
artifacts/leakage_risk_register.csv
```

至少包含：

```text
field_path
risk_level
risk_type
affected_target
observed_in_benchmarks
observed_in_models
recommended_action
justification
```

`recommended_action` 只能使用：

```text
exclude
retain
retain_with_ablation
manual_review_required
```

本阶段只提出建议，不实现特征过滤器。

## 九、判断最小统一轨迹表示是否可行

提出一个仅用于后续实施的候选统一结构，例如：

```text
trajectory_id
benchmark
task_instruction
steps[]
steps[].action
steps[].observation
steps[].tool_name
steps[].tool_input
steps[].tool_output
final_response
metadata
```

必须明确：

* 哪些字段所有 Benchmark 都有；
* 哪些字段仅部分 Benchmark 有；
* 哪些字段可选；
* 哪些字段禁止进入模型输入；
* 是否需要 Benchmark 专用解析器；
* 是否能够暂时忽略截图；
* 仅文本和结构数据能覆盖多少探针轨迹。

本阶段不得正式生成全量统一数据集。

## 十、解析完整性检查

对每条探针轨迹报告：

```text
path_resolved
downloaded
json_parseable
trajectory_nonempty
task_instruction_found
steps_found
action_found
observation_found
final_response_found
screenshot_reference_found
direct_leakage_found
strong_proxy_found
```

同时统计：

* 成功定位文件数量；
* 成功下载数量；
* 成功解析数量；
* 每个 Benchmark 的解析成功率；
* 每个模型的解析成功率；
* 需要专用解析器的结构数量；
* 仅文本即可解析的轨迹比例；
* 包含截图引用的比例；
* 包含直接标签泄漏字段的比例。

不得将解析失败的轨迹静默删除。

## 十一、建议的后续数据范围

基于探针结果估算：

1. 下载全部 dev 文本轨迹所需文件数和体积；
2. 是否必须下载截图；
3. 是否必须下载 judgments；
4. 后续最小基线需要哪些文件类型；
5. 哪些目录应永久禁止进入特征；
6. 是否需要为不同 Benchmark 编写独立 adapter。

这里只允许做文件级估算和技术建议，不得开始全量下载。

## 十二、产物

生成：

```text
docs/trajectory_schema_probe.md
artifacts/dev_probe_manifest.csv
artifacts/trajectory_field_inventory.csv
artifacts/leakage_risk_register.csv
artifacts/trajectory_probe_summary.json
scripts/probe_dev_trajectories.py
tests/test_probe_dev_trajectories.py
```

原始探针数据保存在：

```text
data/raw_probe/
```

并由 `.gitignore` 排除。

## 十三、测试要求

至少测试：

1. 探针样本全部来自 dev；
2. trajectory_key 唯一；
3. 样本选择结果确定；
4. 下载路径全部固定到指定 HF revision；
5. test manifest 中的轨迹无法被脚本下载；
6. 下载总量不会超过200 MB；
7. 原始探针文件不被 Git 跟踪；
8. 字段枚举结果重复生成一致；
9. 解析失败会被显式记录；
10. 泄漏字段不会被误标记为安全输入。

测试不得访问 test 标签或 test 轨迹。

## 十四、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

满足：

* 大部分探针轨迹能够唯一定位并解析；
* 轨迹结构能够统一或通过少量 adapter 统一；
* 标签泄漏字段可以明确识别并隔离；
* 最小实验暂时不依赖截图；
* 后续 dev 数据范围可以可靠估算。

### PASS_WITH_CONDITIONS

例如：

* 少数 Benchmark 需要独立 adapter；
* 部分字段语义仍需人工确认；
* 个别轨迹定位失败；
* 截图不是当前基线必需，但后续可能需要。

### STOP

例如：

* 主键无法映射实际轨迹；
* 大量轨迹无法解析；
* 输入内容和标签无法可靠分离；
* 必须下载完整38GB数据才能进行最小验证；
* dev/test 在文件层面无法安全隔离。

## 十五、禁止事项

本阶段禁止：

* 下载任何 test 轨迹；
* 下载完整数据集；
* 下载截图；
* 构建正式训练数据；
* 提取正式模型特征；
* 调用嵌入模型或大语言模型；
* 训练分类器；
* 运行基线；
* 计算预测指标；
* 调整研究假设；
* 根据探针标签尝试获得高性能。

## 十六、提交

完成后：

1. 更新决策日志；
2. 展示所有产物；
3. 汇报下载文件数和总大小；
4. 汇报解析成功率与结构差异；
5. 汇报所有泄漏风险；
6. 运行全部测试；
7. 执行 `git status`；
8. 创建 Git commit：

```text
chore: probe dev trajectory schema and leakage
```

不得 amend 或覆盖历史提交。
