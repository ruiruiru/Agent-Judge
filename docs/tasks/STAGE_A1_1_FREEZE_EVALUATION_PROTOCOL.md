# Stage A1.1：冻结评估协议、任务分组与基线实验边界

Stage A1.0 已完成，完整 dev 无泄漏语料已成功构建。

本阶段只允许审计并冻结后续基线实验所使用的数据资格、任务分组、交叉验证、跨 Benchmark 评估、阈值选择、指标和统计报告规则。

本阶段不得提取正式特征、调用模型、训练分类器、运行预测基线或报告模型性能。

---

## 一、固定前置版本与产物

必须继续使用已经冻结的数据来源：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

必须先读取并遵守：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/trajectory_schema_probe.md
docs/input_contract.md
docs/dev_corpus_build_report.md

artifacts/source_manifest.json
artifacts/dev_analysis_index.csv
artifacts/test_manifest.csv
artifacts/analysis_index_summary.json
artifacts/dev_corpus_summary.json
artifacts/dev_corpus_manifest.csv
artifacts/dev_schema_drift.csv
artifacts/input_field_policy.csv

research/01_DECISION_LOG.md
```

正式 dev 输入语料位于：

```text
data/processed/dev_cleaned_trajectories.jsonl
data/processed/dev_serialized_primary.jsonl
data/processed/dev_serialized_error_ablation.jsonl
data/processed/dev_serialized_reasoning_sensitivity.jsonl
```

不得修改：

* 官方 dev/test 划分；
* 唯一轨迹主键；
* 重复标注处理规则；
* 三个目标标签含义；
* 主实验资格规则；
* Benchmark 主分组和敏感性分组；
* 输入字段白名单；
* 永久泄漏排除规则；
* 三种冻结输入视图；
* test 封存原则。

---

## 二、本阶段目标

本阶段只回答以下问题：

1. 后续每个目标实际有多少条可用 dev 轨迹；
2. 同一任务下不同模型生成的轨迹如何绑定在同一数据分组；
3. 普通开发评估采用什么任务分组交叉验证；
4. 跨 Benchmark 泛化采用什么 LOBO 协议；
5. 阈值、超参数和模型选择只能使用哪些数据；
6. 三个目标分别使用哪些主指标和辅助指标；
7. 类别不平衡如何报告，但不在本阶段决定重采样；
8. 第一轮基线允许使用哪些输入视图和模型；
9. terminal、结构漂移和自然文本中的 Benchmark 字面值如何处理；
10. 何种结果允许进入下一阶段，何种结果要求停止或修正。

本阶段不得回答任何模型是否有效的问题。

---

## 三、目标定义与主实验资格

主实验目标固定为三个独立二分类任务：

### Success

```text
字段：success_label
正类：1，轨迹成功
负类：0，轨迹未成功
```

### Side Effect

```text
字段：side_effect_label
正类：1，存在副作用
负类：0，不存在副作用
```

不得反转成“安全”为正类。

### Looping

```text
字段：looping_label
正类：1，存在循环或重复行为
负类：0，不存在循环或重复行为
```

每个目标必须独立筛选。

一条轨迹能够进入某个目标的主实验，必须同时满足：

```text
<target>_eligible_main == true
<target>_label in {0, 1}
```

不得只依赖：

```text
label.notna()
dropna(label)
```

不得使用：

* duplicate_disagreement；
* contains_unsure；
* primary label 审计字段；
* 官方 CSV 第一条标注；
* 人工临时重标注；
* 多数投票处理一比一分歧。

同一轨迹可以在一个目标中被排除，在另一个目标中继续使用。

---

## 四、冻结样本连接规则

正式输入只能通过：

```text
trajectory_key
```

与：

```text
artifacts/dev_analysis_index.csv
```

连接标签和分组信息。

连接后必须验证：

1. 每个输入文件中 `trajectory_key` 唯一；
2. 每个目标的数据集中 `trajectory_key` 唯一；
3. 所有进入实验的轨迹均来自官方 dev；
4. 没有任何 test trajectory key；
5. 输入文件本身不包含标签；
6. 标签只在实验数据加载阶段连接；
7. 三种输入视图对应完全相同的轨迹集合；
8. 不允许根据标签选择或修改输入文本。

任何无法连接的轨迹必须显式报告，不得静默删除。

---

## 五、任务分组键

普通交叉验证不得按单条轨迹随机切分。

固定任务分组键为：

```text
group_key = (
    benchmark_original,
    normalized_task_id
)
```

同一 `group_key` 下不同模型生成的全部轨迹必须进入同一个 fold。

原因：

* 同一任务通常有相同或高度相似的 goal；
* 同一任务可能由多个模型分别执行；
* 若按轨迹随机切分，模型可能通过记忆任务文本获得虚高结果；
* 任务级分组可以防止同一任务跨越训练和验证数据。

必须检查：

1. 每个 `group_key` 包含多少条轨迹；
2. 是否通常对应四个模型；
3. 是否存在同一任务仅有部分模型；
4. 是否有异常大组；
5. 是否存在相同 `normalized_task_id` 跨不同 Benchmark；
6. 将 `benchmark_original` 纳入分组键后是否能够消除命名碰撞。

不得将 `model_name` 纳入 group key，因为同一任务的不同模型轨迹必须绑定。

---

## 六、普通开发评估协议

普通开发评估采用：

```text
StratifiedGroupKFold
```

按 `group_key` 分组，同时尽可能维持目标标签比例。

### 默认 fold 数

优先尝试：

```text
n_splits = 5
```

但必须对三个目标分别验证可行性。

每个 fold 必须满足：

1. train 和 validation 的 `group_key` 完全不重叠；
2. validation 至少包含一个正类和一个负类；
3. train 至少包含一个正类和一个负类；
4. 每条轨迹恰好作为 validation 出现一次；
5. 同一任务的所有模型轨迹位于同一 fold；
6. fold 生成过程固定随机种子并可确定性复现。

### Side Effect 的特殊检查

Side Effect 正类率低，必须额外检查：

* 正类任务组数量；
* 每个 fold 的正类轨迹数量；
* 每个 fold 的正类任务组数量；
* 5-fold 是否会产生正类过少或无正类的 fold。

如果5-fold不可行，可降为：

```text
n_splits = 4
```

仍不可行时可降为：

```text
n_splits = 3
```

必须选择三个目标分别可行的最大合理 fold 数。

不得为了三个目标形式统一，而强制使用会产生无正类验证集的 fold 数。

不得通过复制正类、拆分同一任务组或将同一任务放入多个 fold 来解决问题。

### 随机种子

split 生成固定使用：

```text
split_seed = 2026
```

如果后续需要多随机种子评估模型稳定性，模型随机种子必须与数据 split 种子区分。

本阶段只冻结 split，不运行模型。

---

## 七、交叉验证内部的数据层级

后续每一个外层 validation fold 的训练部分必须进一步划分为：

```text
inner_train
inner_validation
```

内层划分同样必须按 `group_key` 分组。

用途仅限：

* 选择分类阈值；
* 选择预注册的有限超参数；
* 选择 early stopping 轮数；
* 在预注册候选中选择模型配置。

禁止使用外层 validation：

* 调整分类阈值；
* 挑选特征；
* 修改文本清洗方式；
* 决定正则化范围；
* 选择类别权重；
* 反复试验后挑选最好配置。

### 推荐嵌套规则

每个外层 fold 内：

```text
outer_train
    ├── inner_train
    └── inner_validation

outer_validation
```

`inner_train` 与 `inner_validation` 仍必须保持任务组隔离。

如果完整嵌套交叉验证对当前最小基线实现过重，可以采用：

```text
固定外层 task-grouped folds
+
在 outer_train 内固定一次 group-aware inner split
```

但该规则必须在模型运行前冻结，并对所有模型一致使用。

---

## 八、阈值选择规则

不得默认所有任务都使用0.5阈值后再根据外层结果修改。

每个目标、每个外层 fold、每个模型配置的分类阈值只能通过该 fold 的：

```text
inner_validation
```

选择。

阈值候选范围必须预先固定，例如：

```text
0.05, 0.10, 0.15, ..., 0.95
```

或者使用模型在 inner validation 上产生的唯一预测概率值作为候选切点。

必须明确记录阈值选择目标。

### 主阈值目标

建议：

```text
最大化正类 F1
```

### Side Effect 附加报告

由于 Side Effect 正类稀少，额外报告：

```text
F2
Recall
Precision
```

但不得在看到外层结果后临时把阈值目标从F1改成F2。

可以预注册两套不同用途：

```text
主分析阈值：最大化正类F1
安全敏感性阈值：最大化F2
```

如果采用两套阈值，必须从一开始对所有模型统一执行，并明确主次关系。

### 平局处理

若多个阈值得分相同，固定选择规则：

1. 优先更高 Recall；
2. Recall 相同时选择更接近0.5的阈值；
3. 仍相同时选择数值更小的阈值。

不得人工挑选。

---

## 九、主指标与辅助指标

不得将 Accuracy 作为核心指标，尤其是 Side Effect。

### 三个目标共同的主指标

```text
PR-AUC
正类 F1
```

PR-AUC为阈值无关指标。

正类F1为阈值相关指标，阈值必须按前述内层规则选择。

### 共同辅助指标

```text
ROC-AUC
Precision
Recall
F2
Balanced Accuracy
Matthews Correlation Coefficient
```

### 必须报告的基础统计

每个外层 fold 均必须报告：

```text
正类数量
负类数量
正类率
任务组数量
预测为正类的数量
选择的阈值
```

### 汇总规则

跨 fold 汇总至少报告：

```text
mean
standard deviation
每个fold的原始值
```

不得只报告最好 fold。

对于无法计算的指标，例如某 fold 意外缺少某一类别：

* 必须标记为不可计算；
* 不得填充为0.5、0或1；
* 原则上应在 split 冻结阶段阻止该情况发生。

---

## 十、概率校准与预测输出

第一轮最小基线不要求额外进行概率校准。

未经预注册，不得在运行结果后临时加入：

```text
Platt scaling
isotonic regression
temperature scaling
```

每条外层 validation 预测必须保存：

```text
trajectory_key
group_key
target
fold_id
true_label
predicted_probability
selected_threshold
predicted_label
model_id
input_view
```

不得保存 test 预测。

预测文件必须支持重新计算全部指标。

---

## 十一、LOBO 跨 Benchmark 协议

主实验 Benchmark 分组固定使用：

```text
benchmark_group_primary
```

共四组。

主 LOBO 协议：

```text
每次留出一个 benchmark_group_primary 作为外部验证域
其余三个 Benchmark 作为训练域
```

共进行四次：

```text
LOBO-1
LOBO-2
LOBO-3
LOBO-4
```

### LOBO 数据规则

1. 留出 Benchmark 的所有任务和轨迹不得进入训练；
2. 训练域内部的阈值和超参数选择仍按 group-aware inner split 完成；
3. 留出 Benchmark 只用于一次外部评估；
4. 不得根据留出 Benchmark 结果修改模型后重新评估同一 Benchmark；
5. 不得将 Benchmark 名称、模型名称或 experiment 名称放入输入；
6. 每个目标分别执行 LOBO；
7. 如果某个留出域中某目标缺少正类或负类，必须显式报告该指标不可计算。

### WorkArena 敏感性协议

额外保留：

```text
benchmark_group_secondary
```

共五组，其中：

```text
workarena_l1
workarena_l2
```

独立。

五组 LOBO 只能作为敏感性分析，不替代四组主实验。

本阶段只生成和审计 LOBO manifest，不训练模型。

---

## 十二、模型身份泛化的附加划分

为检查模型是否只学习某个 agent/model 的行为风格，生成一个候选：

```text
Leave-One-Model-Out
```

分组依据：

```text
model_name
```

该协议只作为后续附加泛化分析候选。

本阶段需要检查：

* 四个模型是否覆盖所有主 Benchmark；
* 每个模型在三个目标中的有效样本和正类数量；
* 留出某个模型后训练域是否仍覆盖所有 Benchmark；
* 每个留出模型验证集是否同时包含正负类。

如果覆盖不足，将其标记为探索性分析，不得包装成主结论。

不得在本阶段运行 Leave-One-Model-Out 模型实验。

---

## 十三、输入视图冻结

第一轮最小基线只允许使用：

```text
primary_with_natural_errors
```

对应：

```text
data/processed/dev_serialized_primary.jsonl
```

第一轮不得同时比较多个输入视图，避免在同一批数据上过早做大量选择。

以下视图暂不进入第一轮基线：

```text
ablation_without_error_fields
sensitivity_with_reasoning
```

它们只在主基线协议稳定后用于预注册消融或敏感性分析。

不得在第一轮加入：

* Benchmark身份；
* 模型身份；
* experiment身份；
* reward；
* summary_info；
* reasoning；
* 截图；
* test内容。

---

## 十四、第一轮允许的基线范围

本阶段只冻结基线清单，不运行。

第一轮最小基线建议限定为：

### B0：多数类基线

```text
DummyClassifier(strategy="most_frequent")
```

目的：确认类别不平衡下的最低参考点。

### B1：先验随机基线

```text
DummyClassifier(strategy="prior")
```

目的：提供按训练集类别先验随机预测的参考。

### B2：轻量结构统计 + Logistic Regression

候选结构特征只能来自无泄漏 cleaned-schema，例如：

```text
步骤数量
非空action数量
非空observation数量
focused_element非空数量
自然错误步骤数量
显式termination_signal是否存在
action文本总长度
observation文本总长度
平均每步action长度
平均每步observation长度
重复action比例
```

本阶段只登记候选，不正式实现。

任何结构特征不得使用：

* reward；
* 标签；
* Benchmark身份；
* 模型身份；
* 文件路径；
* test统计；
* 标签条件统计。

### B3：TF-IDF + Logistic Regression

输入：

```text
primary_with_natural_errors
```

候选配置必须提前限制，例如：

```text
word n-gram: (1, 2)
min_df: 2
max_features: 20,000 或更低
class_weight: None 或 balanced
regularization C: 小型固定候选集合
```

不得在看到外层验证结果后无限扩展超参数搜索。

### 暂不允许

第一轮不得直接使用：

* 大语言模型 Judge；
* Embedding + MLP；
* Transformer微调；
* LoRA；
* XGBoost大规模调参；
* 图神经网络；
* 多模态截图模型；
* 人工提示词逐样本判断；
* test评估。

---

## 十五、超参数预算

每个基线的候选超参数空间必须在训练前写入配置文件。

第一轮总候选配置应保持极小。

建议：

```text
Logistic Regression C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

TF-IDF配置原则上固定，只允许最多两个预注册版本。

例如：

```text
word_unigram
word_unigram_bigram
```

不得在外层验证结果出来后加入：

```text
char n-gram
更多max_features
新的正则化器
新的文本预处理
新的分词器
```

除非结束第一轮并创建新的明确实验阶段。

---

## 十六、类别不平衡处理边界

本阶段只允许统计和冻结候选规则，不进行重采样。

第一轮允许比较：

```text
class_weight = None
class_weight = balanced
```

不得使用：

* SMOTE；
* 随机过采样；
* 随机欠采样；
* 合成轨迹；
* 复制少数类文本；
* 根据完整 dev 正类率设计 fold 外权重；
* 根据外层验证表现决定是否平衡。

类别权重只能根据每个 outer fold 的训练部分自动计算。

---

## 十七、Terminal术语修正

必须在报告、代码和后续统计中明确区分：

```text
last_nonempty_action
last_nonempty_observation
explicit_termination_signal
```

不得继续使用含糊的：

```text
terminal action coverage
```

代替多个概念。

基于A1.0当前结果应核查并记录：

```text
last_nonempty_action coverage: 196/196
last_nonempty_observation coverage: 196/196
explicit_termination_signal coverage: 71/196
```

其中：

* `last_nonempty_action` 只是最后一个非空动作；
* 不表示任务成功；
* 不表示正常结束；
* 不等于显式终止动作。

`explicit_termination_signal` 仅包括输入契约中批准的：

```text
send_msg_to_user
report_infeasible
```

不得通过最后一步、reward或标签补齐。

如果当前产物使用了不准确字段名，应只修正文档、统计名称或非破坏性字段别名，不得改变原始序列化内容。

---

## 十八、结构漂移人工审计

必须读取：

```text
artifacts/dev_schema_drift.csv
```

对当前报告中的：

```text
4组结构漂移
12,477次出现
```

逐项审计。

每组至少报告：

```text
field_path
observed_type
occurrence_count
trajectory_count
benchmark_distribution
model_distribution
short_redacted_example
current_policy
semantic_assessment
final_decision
```

`final_decision` 只能使用：

```text
keep_excluded
approve_as_metadata
approve_for_future_sensitivity
requires_parser_fix
STOP
```

重点检查：

1. 是否只是已知但未进入白名单的冗余字段；
2. 是否包含与现有白名单字段等价的有用语义；
3. 是否只集中出现在某个 Benchmark；
4. 排除后是否会系统性损失某个 Benchmark 的核心轨迹信息；
5. 是否存在结果泄漏或身份捷径；
6. 是否需要回到输入契约阶段修正 adapter。

未经人工批准，不得将结构漂移字段加入任何输入。

---

## 十九、自然文本中的 Benchmark 字面值审计

A1.0发现8条WorkArena轨迹的自然文本中出现字面值：

```text
workarena
```

必须检查这些字面值出现在哪些白名单字段中：

```text
goal
action
observation
focused_element
last_action_error
```

每条至少记录：

```text
trajectory_key
field_path
step_index
redacted_context
source_is_natural_text
source_is_injected_metadata
```

处理规则：

### 如果来自原始任务或环境自然文本

主实验保留，不得静默删除或替换。

原因是：

* 它属于轨迹真实内容；
* 删除可能改变任务语义；
* 不能仅因它恰好与Benchmark名称相同就自动判为泄漏。

### 如果由序列化器或元数据拼接注入

必须修正序列化器并重新生成受影响输入。

### 敏感性候选

可以规划一个后续：

```text
benchmark_literal_redacted
```

敏感性视图，但本阶段不生成、不训练。

不得只针对WorkArena人工修改文本而不对其他Benchmark执行相同规则。

---

## 二十、自然错误字段状态

A1.0发现：

```text
86/196条轨迹包含自然错误
共307个步骤
```

因此：

```text
ablation_without_error_fields
```

具备后续消融资格。

本阶段只需确认：

1. 自然错误不是官方评分器结果；
2. `last_action_error` 来自环境或工具自然反馈；
3. 错误字段未被用于样本选择或标签映射；
4. error ablation 与 primary 的唯一区别符合输入契约；
5. 两种视图的 trajectory key 和步骤顺序一致。

不得在第一轮最小基线中同时使用错误消融挑选最佳方案。

---

## 二十一、Reasoning视图状态

Reasoning覆盖：

```text
196/196条轨迹
3616个步骤
```

但 reasoning 仍只能作为敏感性分析。

必须继续遵守：

* 主基线不使用reasoning；
* 不根据reasoning长度选择样本；
* 不将reasoning存在性作为结构特征；
* 不因reasoning完整覆盖就升级为主输入；
* reasoning敏感性必须在主协议冻结后单独运行。

---

## 二十二、生成冻结的数据划分文件

必须生成确定性的普通交叉验证 manifest。

建议：

```text
artifacts/evaluation_folds_success.csv
artifacts/evaluation_folds_side_effect.csv
artifacts/evaluation_folds_looping.csv
```

至少包含：

```text
trajectory_key
group_key
target
label
outer_fold
outer_role
inner_fold_or_split
benchmark_group_primary
benchmark_group_secondary
model_name
```

这些文件属于评估管理产物，可以包含 dev 标签，但不得写入模型输入目录。

同时生成 LOBO manifest：

```text
artifacts/lobo_primary_manifest.csv
artifacts/lobo_secondary_manifest.csv
```

至少包含：

```text
trajectory_key
target
label
held_out_group
role
benchmark_group_primary
benchmark_group_secondary
group_key
model_name
```

以及模型留出候选清单：

```text
artifacts/leave_one_model_out_manifest.csv
```

---

## 二十三、配置文件

生成机器可读配置：

```text
configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
```

`evaluation_protocol.yaml` 至少包含：

```yaml
split_seed: 2026

targets:
  - success
  - side_effect
  - looping

group_key:
  - benchmark_original
  - normalized_task_id

outer_cv:
  type: StratifiedGroupKFold
  folds_by_target: {}

inner_split:
  group_aware: true

threshold:
  primary_objective: positive_f1
  candidates: []

metrics:
  primary:
    - pr_auc
    - positive_f1
  secondary:
    - roc_auc
    - precision
    - recall
    - f2
    - balanced_accuracy
    - mcc

primary_input_view: primary_with_natural_errors

test_access:
  allowed: false
```

`baseline_registry.yaml` 只登记允许的第一轮基线及有限超参数，不执行。

---

## 二十四、测试要求

至少新增以下测试：

1. 三个目标只包含 `eligible_main == true` 且标签为0/1的轨迹；
2. 每个目标中 `trajectory_key` 唯一；
3. 所有轨迹均来自官方dev；
4. 没有test trajectory key；
5. 同一 `group_key` 不跨外层fold；
6. 同一 `group_key` 不跨inner train和inner validation；
7. 每条轨迹恰好作为outer validation出现一次；
8. 每个fold的train和validation均包含正负类；
9. Side Effect fold数是满足类别约束的最大合理值；
10. split使用固定seed并确定性复现；
11. 三种目标的fold文件逐字节可重复生成；
12. LOBO中留出Benchmark不进入训练；
13. 四组主LOBO与五组敏感性LOBO严格分离；
14. WorkArena L1/L2主分析中合并、敏感性中分离；
15. 模型名称不进入主输入；
16. Benchmark名称不由元数据注入主输入；
17. terminal术语统计区分last action与explicit signal；
18. 结构漂移字段未进入白名单；
19. primary和error ablation只在自然错误字段上存在预期差异；
20. 第一轮基线注册表不包含LLM、Embedding或Transformer训练；
21. 阈值选择配置不允许访问outer validation；
22. test访问配置固定为false；
23. 所有划分文件不修改正式语料；
24. 重复运行所有输出确定。

---

## 二十五、阶段产物

生成：

```text
docs/evaluation_protocol.md
docs/pre_baseline_audit_report.md

artifacts/evaluation_folds_success.csv
artifacts/evaluation_folds_side_effect.csv
artifacts/evaluation_folds_looping.csv
artifacts/lobo_primary_manifest.csv
artifacts/lobo_secondary_manifest.csv
artifacts/leave_one_model_out_manifest.csv
artifacts/pre_baseline_summary.json
artifacts/schema_drift_review.csv
artifacts/benchmark_literal_audit.csv

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml

scripts/build_evaluation_protocol.py
tests/test_build_evaluation_protocol.py
```

更新：

```text
research/01_DECISION_LOG.md
```

如果terminal仅存在命名不准确，可以同步补充：

```text
docs/input_contract.md
docs/dev_corpus_build_report.md
```

不得改写历史数据结果，只能增加澄清说明。

---

## 二十六、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

必须满足：

1. 三个目标的有效dev样本完全明确；
2. task-grouped fold可稳定生成；
3. 同一任务绝不跨训练和验证；
4. 每个fold包含可计算指标所需的正负类；
5. Side Effect采用可行的最大合理fold数；
6. 四组主LOBO manifest正确；
7. 五组敏感性LOBO manifest正确；
8. 阈值和超参数选择规则已冻结；
9. 主指标和辅助指标已冻结；
10. 第一轮基线范围已冻结；
11. terminal术语冲突已澄清；
12. 四组结构漂移完成审计；
13. 8条workarena字面值来源已确认；
14. test保持完全封存；
15. 未运行任何模型或预测指标；
16. 测试全部通过。

### PASS_WITH_CONDITIONS

例如：

* Side Effect只能使用3-fold或4-fold；
* 某个LOBO留出域缺少某类标签；
* Leave-One-Model-Out覆盖不足，只能作为探索性分析；
* 某些自然文本中的Benchmark字面值需要后续敏感性分析；
* 结构漂移字段保持排除，但其语义仍需进一步说明。

上述条件不得影响普通task-grouped主基线的有效性。

### STOP

包括：

* 同一任务无法可靠分组；
* 同一任务仍会跨train和validation；
* 多个fold缺少正类或负类；
* dev输入和标签无法可靠连接；
* 结构漂移表明主白名单删除了关键轨迹语义；
* Benchmark或模型身份由序列化器注入输入；
* test数据被访问；
* 评估协议无法确定性复现；
* 已经运行模型后才制定指标或阈值规则。

---

## 二十七、本阶段禁止事项

本阶段禁止：

* 提取TF-IDF；
* 提取Embedding；
* 调用大语言模型；
* 训练Logistic Regression；
* 运行DummyClassifier；
* 运行任何预测基线；
* 生成模型概率；
* 计算F1、PR-AUC或AUROC模型结果；
* 查看test轨迹或test标签；
* 修改输入白名单；
* 根据标签相关性挑选结构字段；
* 修改官方dev/test；
* 将同一任务拆分到多个fold；
* 根据未来外层验证结果修改指标；
* 根据外层结果追加超参数；
* 运行reasoning或error消融；
* 手工删除难样本或异常样本。

允许计算的仅包括：

* 数据数量；
* 标签分布；
* 分组数量；
* fold类别覆盖；
* 结构审计统计；
* 划分完整性统计。

---

## 二十八、提交

完成后必须汇报：

* 阶段判定；
* 三个目标的有效样本数和类别分布；
* 每个目标采用的fold数；
* 每个fold的轨迹数、任务组数和正负类数量；
* group key审计；
* 四组主LOBO分布；
* 五组敏感性LOBO分布；
* Leave-One-Model-Out可行性；
* terminal术语修正结果；
* 四组结构漂移审计结果；
* 8条workarena字面值的来源；
* 第一轮冻结基线；
* 测试结果；
* 修改文件；
* commit；
* git status。

创建新提交：

```text
chore: freeze grouped evaluation protocol
```

不得amend或覆盖历史提交。

本阶段完成并获得人工批准前，不得进入任何基线运行。
