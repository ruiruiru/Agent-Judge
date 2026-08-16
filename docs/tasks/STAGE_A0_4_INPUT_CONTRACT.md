# Stage A0.4：冻结无泄漏输入契约与紧凑轨迹表示

Stage A0.3 已完成，判定为 PASS_WITH_CONDITIONS。

本阶段只使用现有的16条 dev 探针轨迹，建立共享解析器、字段白名单、泄漏隔离规则和紧凑轨迹表示。

不得继续下载新的轨迹，不得下载 test 或截图，不得建立全量 dev 数据集，不得调用模型、提取嵌入、训练分类器或运行基线。

## 一、读取前置产物

必须先读取：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/trajectory_schema_probe.md
artifacts/dev_analysis_index.csv
artifacts/dev_probe_manifest.csv
artifacts/trajectory_field_inventory.csv
artifacts/leakage_risk_register.csv
artifacts/trajectory_probe_summary.json
research/01_DECISION_LOG.md
```

只能处理现有：

```text
data/raw_probe/
```

中的16条 dev 探针轨迹。

## 二、本阶段目标

本阶段只回答：

1. 哪些原始字段允许进入主实验输入；
2. 哪些字段只能作为分组元数据；
3. 哪些字段必须永久排除；
4. 如何统一四个 Benchmark 的轨迹结构；
5. 如何表示不存在独立 final_response 的轨迹；
6. reasoning、错误信息和身份字段如何处理；
7. 清洗后的轨迹能压缩到多大；
8. 后续是否可以流式构建全部 dev 紧凑语料。

本阶段不得回答模型性能问题。

## 三、采用字段白名单，而不是只使用黑名单

主实验输入必须采用明确的字段白名单。

不得采用：

```text
读取全部字段
然后只删除 cum_reward 和 cum_raw_reward
```

这种实现容易在官方数据新增字段或嵌套字段时重新引入泄漏。

必须根据 Stage A0.3 的字段清单，逐项定义：

```text
允许进入主输入
仅作为元数据
仅用于敏感性分析
永久排除
需要人工复核
```

未知字段默认不得进入主输入。

## 四、永久排除字段

至少永久排除：

```text
summary_info.cum_reward
summary_info.cum_raw_reward
```

同时递归检查字段名及语义中包含以下内容的字段：

```text
reward
raw_reward
score
success
successful
passed
failure
side_effect
looping
repetitiveness
annotation
human_judgment
judge_result
ground_truth
label
```

不得仅依靠字段名判断。

如果字段名称正常，但值实际表达官方评分、人工判断或目标标签，也必须排除。

永久排除字段：

* 不得写入任何模型输入文本；
* 不得写入结构特征；
* 不得用于截断、排序或样本选择；
* 不得用于决定是否保留某一步；
* 不得作为缺失值填充依据。

原始字段是否存在可以记录在审计报告中，但不得进入训练接口。

## 五、身份和实验元数据

以下字段只能作为分析元数据：

```text
benchmark
benchmark_original
benchmark_group_primary
benchmark_group_secondary
agent
model
model_name
experiment
exp_name
task_id
trajectory_key
official_split
repository_path
```

主实验序列化输入中不得出现这些字段的名称和值。

这些元数据只允许用于：

* 数据连接；
* Benchmark 分组；
* LOBO 划分；
* 模型分组统计；
* 错误分析；
* 敏感性实验。

后续可以单独设计“加入身份字段”的 shortcut 对照实验，但不得把它作为主实验。

## 六、Reasoning 处理

原始 `reasoning` 字段必须保留其存在性审计，但主实验输入默认不包含 reasoning 文本。

原因：

1. 不同模型的 reasoning 可用性不同；
2. reasoning 的存在、长度和风格可能泄露模型身份；
3. 部分轨迹 reasoning 为空；
4. 主实验应优先判断动作和环境反馈，而不是模型自述。

建立两个候选视图：

```text
primary_no_reasoning
sensitivity_with_reasoning
```

本阶段可以在探针数据上生成两个紧凑表示，但不得训练或比较指标。

对于缺失 reasoning：

* 保持缺失；
* 不得填充“无推理”等人工文本；
* 不得从 action 或 observation 推测 reasoning。

## 七、错误与自然结果信息

以下字段或语义可能属于正常轨迹证据：

```text
error
error_message
last_action_error
tool_error
action_failure
observation 中自然出现的失败提示
```

它们不属于官方标签本身，可以暂时保留在主实验候选输入中。

但必须同时建立：

```text
primary_with_natural_errors
ablation_without_error_fields
```

注意：

* 官方评分器产生的失败结论必须永久排除；
* 工具或环境自然返回的错误可以保留；
* agent 自己声称“任务完成”不等于官方成功标签，但需记录为可能的结果代理；
* 不得根据错误字段删除整条轨迹。

本阶段只建立表示和审计，不运行消融实验。

## 八、截图与图像字段

所有以下内容不得进入当前文本主实验：

```text
截图文件
图像二进制
base64 图像
截图绝对路径
截图仓库路径
图像占位符原文
```

可以保留一个布尔元数据：

```text
has_screenshot_reference
```

但不得把具体截图路径序列化给模型。

不得因为某一步缺少图像内容而删除该步骤。

## 九、统一轨迹结构

建立共享 cleaned-schema，建议至少包括：

```text
trajectory_key
metadata
task
steps
terminal
quality_flags
```

### metadata

仅用于数据管理，不进入主实验模型输入：

```text
benchmark_group_primary
benchmark_group_secondary
model_name
task_id
official_split
source_revision
source_path
source_sha256
```

### task

根据实际字段确认并记录：

```text
instruction
context
```

没有的字段保持为空，不得推测。

### steps

每一步采用统一结构：

```text
step_index
action
observation
tool_name
tool_input
tool_output
focused_element
error
```

只保留原始数据中实际存在且通过白名单审计的字段。

允许字段为空。

`focused_element` 在 WorkArena 中允许空值，不得因空值解析失败，也不得填充伪造元素。

### terminal

不得创建虚假的 `final_response`。

建立：

```text
last_nonempty_action
last_nonempty_observation
last_step_index
termination_signal
```

其中：

* `last_nonempty_action` 必须来自原始最后一个非空 action；
* `last_nonempty_observation` 必须来自原始最后一个非空 observation；
* `termination_signal` 只有原始数据明确存在终止语义时才填写；
* 不得通过 reward 或标签推断 termination_signal；
* 不得把最后一步默认解释为成功。

### quality_flags

至少包括：

```text
has_task_instruction
has_steps
has_action
has_observation
has_reasoning
has_natural_error
has_screenshot_reference
has_terminal_action
has_terminal_observation
unknown_fields_present
```

这些字段用于质量审计，不代表标签。

## 十、主输入序列化格式

定义确定性的主实验文本序列化规则，例如：

```text
[TASK]
...

[STEP 1]
ACTION:
...
OBSERVATION:
...
TOOL:
...

[STEP 2]
...
```

必须满足：

1. 不包含标签；
2. 不包含 reward；
3. 不包含 Benchmark、模型或实验名称；
4. 不包含原始文件路径；
5. 不包含截图路径；
6. 不包含 reasoning；
7. 步骤顺序保持不变；
8. 空字段直接省略，不使用带有模型身份特征的特殊填充值；
9. 同一原始轨迹重复运行产生完全一致的输出；
10. 文本与结构化 JSON 使用同一字段白名单。

同时生成：

```text
primary_with_natural_errors
ablation_without_error_fields
sensitivity_with_reasoning
```

三个视图。

不得生成带 reward 或身份字段的视图。

## 十一、标签与输入物理隔离

清洗后的输入文件不得包含：

```text
success_label
side_effect_label
looping_label
eligible_main
annotation status
原始标注值
```

标签只能通过 `trajectory_key` 从：

```text
artifacts/dev_analysis_index.csv
```

独立连接。

要求输入构建器的函数接口不得接收标签值。

例如不得设计为：

```python
build_input(trajectory, label)
```

应类似：

```python
build_input(raw_trajectory, input_view)
```

标签连接应在后续数据加载阶段单独完成。

## 十二、生成探针紧凑数据

基于现有16条探针生成：

```text
artifacts/probe_cleaned_trajectories.jsonl
artifacts/probe_serialized_inputs.jsonl
```

每条记录必须可通过 `trajectory_key` 对应原始探针，但不得复制完整原始轨迹中的无关内容。

分别统计：

* 原始文件总字节；
* 清洗后结构化 JSONL 字节；
* 三种序列化视图字节；
* 每条轨迹原始大小；
* 每条轨迹清洗后大小；
* 每个字段类别贡献的字符数；
* 步骤数量；
* 空 action 数；
* 空 observation 数；
* reasoning 可用率；
* error 字段可用率；
* 截图引用率；
* 未知字段数量。

不得为了压缩体积而进行语义摘要或调用模型。

## 十三、未知字段处理

如果解析过程中发现 Stage A0.3 未登记的新字段：

1. 默认不进入输入；
2. 写入未知字段审计；
3. 记录字段路径、类型、出现次数和短样例；
4. 人工分类为白名单、元数据、敏感性、永久排除或待复核；
5. 未完成分类前不得进入主输入。

生成：

```text
artifacts/input_field_policy.csv
```

至少包含：

```text
field_path
observed_type
policy_class
included_in_primary
included_in_error_ablation
included_in_reasoning_sensitivity
justification
risk_notes
```

## 十四、全量 dev 紧凑构建计划

基于16条探针的实际压缩率和官方文件树，估算：

1. 196条 dev 原始轨迹总下载量；
2. 清洗后结构化语料预计体积；
3. 三种输入视图预计体积；
4. 单文件平均解析内存；
5. 是否可以逐文件流式下载、验证、解析、写入后释放；
6. 是否必须永久保留3.65GB原始数据；
7. 下载失败或中断时如何断点恢复；
8. 如何保证固定 revision 和哈希；
9. 如何避免任何 test 文件进入流水线。

优先提出：

```text
固定 revision逐文件下载
-> 校验
-> 解析
-> 写入紧凑格式
-> 释放原始文件或进入可清理缓存
```

不得在本阶段执行全量下载。

## 十五、测试要求

至少新增以下测试：

1. 16条输入全部来自现有 dev 探针；
2. 清洗后 `trajectory_key` 唯一；
3. 输入构建函数不接收标签；
4. 输出中不存在 `cum_reward` 和 `cum_raw_reward`；
5. 输出中不存在任何 reward、label、judge 或 annotation 语义字段；
6. 主输入中不存在 Benchmark、模型、agent 或 experiment 名称；
7. 主输入中不存在截图路径；
8. primary 视图中不存在 reasoning；
9. reasoning sensitivity 只在原始 reasoning 存在时使用；
10. error ablation 确实删除自然错误字段；
11. 不存在虚构的 final_response；
12. terminal 字段只来自原始非空字段；
13. WorkArena 的空 focused_element 可以正常解析；
14. 未知字段默认被拒绝进入输入；
15. 重复运行输出逐字节一致；
16. test manifest 中的轨迹无法进入构建器；
17. 原始探针目录不被 Git 跟踪。

## 十六、产物

生成：

```text
docs/input_contract.md
artifacts/input_field_policy.csv
artifacts/probe_cleaned_trajectories.jsonl
artifacts/probe_serialized_inputs.jsonl
artifacts/input_contract_summary.json
scripts/build_cleaned_probe.py
tests/test_build_cleaned_probe.py
```

更新：

```text
research/01_DECISION_LOG.md
.gitignore
```

如需修改已有探针文档，只允许补充，不得改写历史审计结论。

## 十七、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

满足：

* 共享 adapter 能处理全部16条探针；
* 输入白名单明确；
* reward 和标签完全隔离；
* 身份字段不进入主输入；
* reasoning 不进入主输入；
* 不需要虚构 final_response；
* 紧凑结构可以稳定生成；
* 全量 dev 可以通过流式方式构建；
* 不依赖截图；
* 测试全部通过。

### PASS_WITH_CONDITIONS

例如：

* 少量字段仍需人工确认；
* terminal 语义只能部分恢复；
* 某些自然错误信息需要后续消融；
* 部分轨迹缺少 action 或 observation，但仍可显式记录。

### STOP

例如：

* reward 无法从输入可靠剥离；
* 原始字段与标签语义无法区分；
* 共享 adapter 无法稳定生成；
* 大量轨迹必须依赖截图；
* 标签或 test 数据无法与输入构建过程隔离。

## 十八、禁止事项

本阶段禁止：

* 下载新的 dev 文件；
* 下载 test；
* 下载截图；
* 构建全部196条 dev 语料；
* 提取 TF-IDF、embedding 或其他正式特征；
* 调用任何模型；
* 训练分类器；
* 运行基线；
* 计算 Accuracy、F1、AUROC 或其他预测指标；
* 根据探针标签改变字段策略；
* 根据标签相关性挑选输入字段。

## 十九、提交

完成后汇报：

* 阶段判定；
* 最终字段白名单；
* 永久排除字段；
* 三种输入视图；
* terminal 表示方式；
* 原始与清洗后体积；
* 未知字段；
* 测试结果；
* 修改文件；
* commit；
* git status。

创建新提交：

```text
chore: freeze leak-safe trajectory input contract
```

不得 amend 或覆盖历史提交。
