# Stage A1.3：运行主四组 LOBO 跨 Benchmark 最小基线

## 一、阶段定位

Stage A1.2 已通过人工阶段门审查，判定为：

```text
PASS_WITH_CONDITIONS
```

已完成提交：

```text
b4fef6f63d55ccd4ed2cdf4feb2dcab1cd5b6d20
chore: preregister minimal grouped baselines

179ce02640a8e6e15411348b57fd8d7725047364
experiment: run grouped minimal dev baselines
```

A1.2 只证明在冻结的官方 dev、task-grouped 五折 OOF 协议下存在初步预测信号，尚未证明能够泛化到未参与训练的 Benchmark。

Stage A1.3 只运行：

```text
主四组 benchmark_group_primary LOBO
+
B0–B3 原始最小基线
```

本阶段不得运行五组敏感性 LOBO、Leave-One-Model-Out、输入消融、Reasoning 敏感性、复杂模型或 test。

本阶段的核心问题是：

> A1.2 中观察到的结构与文本信号，能否迁移到一个完全未参与训练的 Benchmark？

---

## 二、固定数据版本

必须继续使用：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

不得更新 GitHub 数据版本、Hugging Face revision、标签或官方 split。

---

## 三、必须先读取的文件

执行前必须读取并遵守：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/dev_corpus_build_report.md
docs/evaluation_protocol.md
docs/pre_baseline_audit_report.md
docs/stage_a1_2_minimal_baseline_report.md

artifacts/dev_analysis_index.csv
artifacts/dev_corpus_summary.json
artifacts/pre_baseline_summary.json
artifacts/lobo_primary_manifest.csv
artifacts/lobo_secondary_manifest.csv
artifacts/a1_2_run_summary.json
artifacts/a1_2_pooled_metrics.csv
artifacts/dev_structural_features.csv

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
configs/stage_a1_2_execution.yaml

requirements/baseline-lock.txt
artifacts/baseline_environment.json

research/01_DECISION_LOG.md
```

正式输入继续固定为：

```text
B2:
artifacts/dev_structural_features.csv

B3:
data/processed/dev_serialized_primary.jsonl
```

标签和分组信息只能通过：

```text
trajectory_key
+
artifacts/dev_analysis_index.csv
+
artifacts/lobo_primary_manifest.csv
```

连接。

不得使用：

```text
data/processed/dev_serialized_error_ablation.jsonl
data/processed/dev_serialized_reasoning_sensitivity.jsonl
artifacts/lobo_secondary_manifest.csv
artifacts/leave_one_model_out_manifest.csv
```

`lobo_secondary_manifest.csv` 只允许读取其哈希或确认未使用，不得据此运行模型。

---

## 四、本阶段只回答的问题

本阶段只回答：

1. B0–B3 在完全留出一个 Benchmark 时还能达到什么性能；
2. A1.2 的结构信号是否跨 Benchmark 保留；
3. A1.2 的 TF-IDF 文本信号是否依赖 Benchmark 特定词汇或格式；
4. Success、Side Effect、Looping 的跨域难度是否不同；
5. 哪些目标表现为稳定跨域信号，哪些只在部分 Benchmark 有效；
6. LOBO 与 A1.2 task-grouped OOF 之间存在多大的描述性性能下降；
7. 当前证据是否值得进入后续敏感性实验或模型升级。

不得回答：

```text
最终 test 性能
真实部署性能
超过已有论文
统计显著性
因果关系
所有 Web Agent 环境中的普遍泛化能力
```

---

## 五、主四组 LOBO 定义

主分组字段固定为：

```text
benchmark_group_primary
```

语义上预期包含四组：

```text
AssistantBench
VisualWebArena
WebArena
WorkArena
```

具体字符串值、大小写和顺序以：

```text
artifacts/lobo_primary_manifest.csv
```

为唯一权威。

每次运行：

```text
三个 Benchmark：训练域
一个 Benchmark：完全留出外部验证域
```

共四个 held-out domain。

对每个：

```text
target × baseline × held_out_group
```

只允许进行一次正式外部评估。

不得根据外部验证结果：

* 改配置；
* 改阈值；
* 改特征；
* 改词表；
* 改标签；
* 改样本；
* 改 held-out 分组；
* 重跑并挑最好版本。

---

## 六、预期 LOBO 样本统计

运行前必须根据 manifest 独立复算并验证以下预期。

表中格式为：

```text
轨迹数 / 任务组数 / 负类数 / 正类数
```

### Success

| 留出域 | 预期 |
|---|---:|
| AssistantBench | 24 / 6 / 22 / 2 |
| VisualWebArena | 24 / 8 / 12 / 12 |
| WebArena | 84 / 22 / 59 / 25 |
| WorkArena | 60 / 15 / 41 / 19 |

合计：

```text
192 / 51 / 134 / 58
```

### Side Effect

| 留出域 | 预期 |
|---|---:|
| AssistantBench | 24 / 6 / 24 / 0 |
| VisualWebArena | 24 / 8 / 22 / 2 |
| WebArena | 87 / 22 / 79 / 8 |
| WorkArena | 60 / 15 / 58 / 2 |

合计：

```text
195 / 51 / 183 / 12
```

### Looping

| 留出域 | 预期 |
|---|---:|
| AssistantBench | 24 / 6 / 13 / 11 |
| VisualWebArena | 24 / 8 / 17 / 7 |
| WebArena | 88 / 22 / 51 / 37 |
| WorkArena | 60 / 15 / 23 / 37 |

合计：

```text
196 / 51 / 104 / 92
```

如果 manifest 实际值与上述预期不一致：

```text
立即 STOP
```

不得自行修复、删样本或重建 LOBO manifest。

---

## 七、外部训练与验证隔离

每个 held-out group 必须满足：

1. held-out group 的全部轨迹只能进入 external validation；
2. held-out group 的全部任务组不得进入训练；
3. held-out group 的标签不得进入配置选择和阈值选择接口；
4. held-out group 的文本不得参与 TF-IDF 词表拟合；
5. held-out group 的结构特征不得参与 StandardScaler 拟合；
6. held-out group 的类别比例不得用于 class_weight；
7. held-out group 的 Benchmark 名称不得进入输入；
8. 训练域和验证域的 `group_key` 必须完全不重叠；
9. 每条有效轨迹在同一 target × baseline 下恰好作为一次外部验证样本；
10. test 轨迹、标签、预测和统计访问必须为 0。

允许读取 held-out group 的 identifier、标签和分组字段，仅用于：

```text
冻结 manifest 校验
正式外部指标计算
结果分组
```

不得将其传入训练、配置选择或阈值选择函数。

---

## 八、基线必须保持不变

只运行：

```text
B0_dummy_most_frequent
B1_dummy_prior
B2_structural_lr
B3_tfidf_lr
```

不得添加：

```text
B4
B2+B3 融合
规则系统
Embedding
XGBoost
MLP
Transformer
LLM Judge
```

B0–B3 的定义、特征、预处理、候选配置、同分规则和随机种子必须与 A1.2 完全一致。

不得直接复用 A1.2 某个 fold 选出的最佳配置或阈值。

原因：

> LOBO 的训练域已经变化，配置和阈值必须仅在当前三个训练 Benchmark 内重新选择。

---

## 九、B2 输入与处理

B2 必须优先复用已经生成并冻结的：

```text
artifacts/dev_structural_features.csv
```

运行前必须校验其 SHA-256 与 A1.2 记录一致。

不得重新定义、增加、删除或重新排序13个结构特征：

```text
1. step_count
2. nonempty_action_count
3. nonempty_observation_count
4. nonempty_focused_element_count
5. natural_error_step_count
6. natural_error_step_ratio
7. has_explicit_termination_signal
8. action_char_count_total
9. observation_char_count_total
10. action_char_count_mean_nonempty
11. observation_char_count_mean_nonempty
12. unique_action_ratio
13. consecutive_duplicate_action_count
```

模型继续固定为：

```text
StandardScaler
+
LogisticRegression
```

Logistic Regression 语义必须与 A1.2 一致：

```text
penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026
```

候选配置仍为：

```text
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共6个。

`StandardScaler` 必须在每个 inner train 或最终三个训练域上单独拟合。

不得在完整 dev 或 held-out group 上提前拟合。

---

## 十、B3 输入与处理

B3 只能读取：

```text
data/processed/dev_serialized_primary.jsonl
```

文本表示仍只允许：

```text
T1：word unigram
T2：word unigram + bigram
```

共同配置必须与 A1.2 一致：

```text
lowercase = true
strip_accents = unicode
min_df = 2
max_df = 1.0
max_features = 20000
sublinear_tf = true
norm = l2
use_idf = true
smooth_idf = true
token_pattern = (?u)\b\w\w+\b
```

Logistic Regression 与 A1.2 保持相同。

候选配置仍为：

```text
TF-IDF ∈ {T1, T2}
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共12个。

TF-IDF 必须在每个 inner train 或最终三个训练域上单独拟合。

held-out group 独有词不得进入词表。

---

## 十一、LOBO 内层选择协议

A1.3 必须在正式训练前生成并冻结：

```text
artifacts/a1_3_lobo_inner_folds.csv
```

### 11.1 内层数据范围

对每个：

```text
target × held_out_group
```

只在 role=train 的三个训练域中生成 group-aware inner folds。

外部 held-out rows 的 `inner_fold` 必须为空。

### 11.2 分组键

固定使用：

```text
group_key = (
    benchmark_original,
    normalized_task_id
)
```

同一任务的不同模型轨迹必须位于同一 inner fold。

### 11.3 内层 fold 数

必须复用仓库中已经冻结的：

```text
custom_deterministic_grouped_stratification_v1
```

固定：

```text
split_seed = 2026
```

对每个 target × held_out_group，按以下顺序寻找最大可行 fold 数：

```text
5 → 4 → 3 → 2
```

“可行”必须同时满足：

1. 每个 inner validation 含正类和负类；
2. 每个对应 inner train 含正类和负类；
3. group_key 不跨 inner train/validation；
4. 每条训练域轨迹恰好作为一次 inner validation；
5. 结果可确定性逐字节复现。

如果2-fold仍不可行：

```text
该 target × held_out_group 判定为 NOT_RUN_INSUFFICIENT_INNER_CLASS_SUPPORT
```

不得复制少数类、拆分任务组或手工移动样本。

若任何 Success 或 Looping 单元不可运行，整体阶段 STOP。

若仅 Side Effect 单元因少数类无法运行，整体阶段至少为 PASS_WITH_CONDITIONS，并等待人工审查，不得自行改变协议。

### 11.4 内层配置评估

对每个候选配置：

1. 在每个 inner train 拟合；
2. 在对应 inner validation 输出 `P(y=1)`；
3. 合并该配置的全部 inner OOF 概率；
4. 每条训练域轨迹恰好出现一次；
5. 以 pooled inner OOF Average Precision 作为配置选择分数。

不得使用：

```text
held-out domain AP
held-out domain F1
A1.2 最佳配置
完整 dev AP
单个最好 inner fold
```

进行配置选择。

---

## 十二、配置选择规则

配置选择指标固定为：

```python
sklearn.metrics.average_precision_score
```

即：

```text
pooled inner OOF PR-AUC / Average Precision
```

### B2 同分优先级

1. `class_weight=None`；
2. `C=0.1`；
3. `C=1.0`；
4. `C=10.0`；
5. `config_id` 字典序。

### B3 同分优先级

1. T1 unigram；
2. T2 unigram+bigram；
3. `class_weight=None`；
4. 更小的 C；
5. `config_id` 字典序。

不得人工挑选同分配置。

B0、B1 只有固定配置，但仍必须走统一的 inner OOF 阈值选择流程。

---

## 十三、阈值选择规则

配置选定后，只能使用该配置的：

```text
pooled inner OOF probabilities
```

选择阈值。

候选固定为：

```text
0.05, 0.10, 0.15, ..., 0.95
```

主目标固定为：

```text
正类 F1 最大
```

同分规则：

1. Recall 更高；
2. 更接近 0.5；
3. 数值更小。

选择完成后：

1. 使用选定配置在全部三个训练 Benchmark 上重新拟合；
2. 保留冻结阈值；
3. 在 held-out Benchmark 上评估一次。

不得在看到 held-out 结果后修改阈值。

---

## 十四、预测概率规则

所有模型必须输出：

```text
P(y=1)
```

必须通过：

```python
model.classes_
```

定位正类1对应的概率列。

所有概率必须：

* 有限；
* 位于 `[0,1]`；
* 保留原始精度；
* 与 trajectory_key 一一对应；
* 不得先四舍五入再算指标。

---

## 十五、单一类别 held-out domain 的特殊规则

已知：

```text
Side Effect / AssistantBench
```

外部留出域预期为：

```text
24个负类
0个正类
```

这不是代码错误，但无法评价正类排序和识别能力。

该单元必须：

```text
metric_status = single_class_negative
```

以下指标必须写为缺失值，并附明确原因：

```text
PR-AUC / AP
ROC-AUC
正类 Precision
正类 Recall
正类 F1
F2
Balanced Accuracy
MCC
AP lift
```

不得填为：

```text
0
0.5
1
```

必须额外报告：

```text
held_out_size
negative_count
predicted_positive_count
predicted_positive_rate
false_positive_count
false_positive_rate
specificity
probability_mean
probability_median
probability_max
```

如果未来意外出现全正类 held-out domain，同理标记：

```text
single_class_positive
```

并报告正类覆盖诊断，不得伪造双类别指标。

单一类别 domain：

* 保留预测文件；
* 保留诊断统计；
* 不进入 mixed-class domain 的 AP/F1 macro mean；
* 不按0分参与平均；
* 仍可进入全目标 pooled LOBO 汇总，因为四个 domain 合并后总体包含正负类。

---

## 十六、外部指标

对于同时包含正负类的 held-out domain，报告：

### 主指标

```text
PR-AUC / Average Precision
正类 F1
```

### 辅助指标

```text
ROC-AUC
Precision
Recall
F2
Balanced Accuracy
Matthews Correlation Coefficient
```

### 基础统计

```text
held_out_group
轨迹数
任务组数
正类数
负类数
prevalence
预测正类数
预测正类率
选中配置
选中阈值
inner_n_splits
metric_status
```

每个 domain 还要报告：

```text
AP lift = held-out AP - held-out prevalence
B2/B3 相对于 B0/B1 的 AP 与 F1 差值
```

只用于描述，不用于继续调参。

---

## 十七、三层汇总

### 17.1 每个 held-out domain 原始结果

每行：

```text
target × baseline × held_out_group
```

预期：

```text
3 targets × 4 baselines × 4 groups = 48 rows
```

单一类别单元仍保留一行，但部分指标为缺失。

### 17.2 Mixed-class domain macro mean ± std

对每个：

```text
target × baseline
```

只对可计算的 mixed-class held-out domains 汇总：

```text
macro mean
sample std，ddof=1
valid_domain_count
excluded_single_class_domain_count
```

不得把单一类别 domain 当0加入平均。

### 17.3 Pooled LOBO 结果

合并四个 held-out domain 的外部预测。

每个：

```text
target × baseline
```

要求：

* 每条有效 dev 轨迹恰好作为一次 held-out 外部预测；
* 每条样本使用对应 held-out run 冻结的配置和阈值；
* AP 和 ROC-AUC 使用原始概率；
* F1等阈值指标使用对应预测标签；
* 不得重复、遗漏或使用训练域预测。

预期每个 baseline：

```text
Success：192
Side Effect：195
Looping：196
合计：583
```

四个 baseline 合计外部预测行数：

```text
2332
```

---

## 十八、与 A1.2 的描述性比较

允许读取：

```text
artifacts/a1_2_pooled_metrics.csv
artifacts/a1_2_run_summary.json
```

仅用于正式 LOBO 完成后的报告比较。

对每个 target × baseline 报告：

```text
LOBO pooled AP - A1.2 pooled OOF AP
LOBO pooled F1 - A1.2 pooled OOF F1
```

同时报告：

```text
最差 held-out domain AP/F1
最佳 held-out domain AP/F1
domain 间标准差
B2/B3 超过两个 Dummy 的 mixed-class domain 数
```

这些差值不是严格配对显著性检验。

不得写成：

```text
性能显著下降
性能显著提升
```

除非未来单独预注册并运行统计检验。

---

## 十九、信号分级

每个目标给出一个描述性标签：

```text
robust_cross_benchmark_signal
partial_or_domain_specific_signal
no_cross_benchmark_signal
not_assessable
```

### robust_cross_benchmark_signal

至少一个 B2 或 B3 同时满足：

1. pooled LOBO AP 高于该目标总体 prevalence；
2. pooled LOBO F1 高于 B0、B1 pooled F1；
3. 在至少75%的 mixed-class held-out domains 中：
   * AP 高于该 domain prevalence；
   * F1 高于该 domain 的 B0、B1；
4. 不存在数据、实现或隔离异常。

### partial_or_domain_specific_signal

例如：

* pooled LOBO 有提升，但只在部分 domain 有效；
* domain 间波动很大；
* AP 有提升而 F1 不稳定；
* B2 和 B3 在不同 domain 表现相反；
* Side Effect 因少数类只能得到脆弱证据。

### no_cross_benchmark_signal

B2、B3 均未在多数 mixed-class domains 稳定超过 prevalence 和 Dummy。

### not_assessable

可计算的 mixed-class held-out domains 少于2个。

该分级不得自动触发下一阶段。

---

## 二十、两阶段执行与 Git 提交

Stage A1.3 必须分为两个独立子阶段。

### A1.3a：运行前冻结

在任何真实 LOBO 模型 `.fit()` 之前完成：

* 本任务书入库；
* LOBO 执行配置；
* inner folds；
* 选择规则；
* 阈值规则；
* 单一类别处理；
* 输出 schema；
* 完整测试；
* 输入和 manifest 哈希；
* 禁止项检查。

允许使用真实 dev 标签生成和审计分组 manifest。

不允许在真实 dev 上训练模型。

生成：

```text
configs/stage_a1_3_lobo_execution.yaml
artifacts/a1_3_lobo_prerun_integrity.json
artifacts/a1_3_lobo_inner_folds.csv
scripts/run_stage_a1_3_primary_lobo.py
tests/test_stage_a1_3_primary_lobo.py
```

更新：

```text
research/01_DECISION_LOG.md
```

提交：

```text
chore: preregister primary lobo baselines
```

不得 amend A1.2 提交。

### A1.3b：正式运行

运行前确认：

```text
git status
```

必须干净。

正式运行开始后不得修改：

* 脚本；
* 配置；
* manifest；
* 特征；
* 候选超参数；
* 阈值；
* 指标；
* 单一类别处理；
* 结果分级规则。

如发现实现错误：

1. 立即停止；
2. 保留失败日志；
3. 当前运行整体作废；
4. 不得挑选性保留部分 held-out 结果；
5. 创建独立修正提交；
6. 从12个 target × held-out 组合、全部 B0–B3 从头重跑；
7. 记录原因。

正式结果完成后提交：

```text
experiment: run primary lobo baselines
```

不得 amend 预注册提交。

---

## 二十一、输出产物

生成：

```text
artifacts/a1_3_lobo_inner_config_selection.csv
artifacts/a1_3_lobo_inner_selected_oof_predictions.csv
artifacts/a1_3_lobo_threshold_selection.csv
artifacts/a1_3_lobo_predictions.csv
artifacts/a1_3_lobo_domain_metrics.csv
artifacts/a1_3_lobo_macro_metrics.csv
artifacts/a1_3_lobo_pooled_metrics.csv
artifacts/a1_3_lobo_config_frequency.csv
artifacts/a1_3_lobo_comparison_to_a1_2.csv
artifacts/a1_3_lobo_run_summary.json
docs/stage_a1_3_primary_lobo_report.md
```

### inner config selection

每行：

```text
target
held_out_group
baseline_id
config_id
inner_n_splits
inner_oof_size
inner_oof_pr_auc
selected
tie_break_rank
```

预期配置汇总行数：

```text
每个 target × held_out_group：
B0 1 + B1 1 + B2 6 + B3 12 = 20

3 × 4 × 20 = 240 rows
```

### threshold selection

每个 target × baseline × held_out_group 的选中配置测试19个阈值。

预期：

```text
3 × 4 × 4 × 19 = 912 rows
```

### external predictions

至少包含：

```text
trajectory_key
group_key
target
baseline_id
held_out_group
true_label
predicted_probability
selected_threshold
predicted_label
selected_config_id
inner_n_splits
```

预期：

```text
2332 rows
```

每个：

```text
target × baseline × trajectory_key
```

必须唯一。

---

## 二十二、运行环境

优先复用 A1.2 的独立环境和：

```text
requirements/baseline-lock.txt
artifacts/baseline_environment.json
```

不得升级依赖。

正式运行：

```text
CPU-only
network access = 0
GPU = 0
```

如果环境版本发生变化：

```text
STOP
```

除非先创建新的明确环境冻结阶段并获得人工批准。

A1.2 中出现的 scikit-learn `penalty='l2'` FutureWarning：

* 可以继续记录；
* 不属于 convergence warning；
* 不得为了消除警告临时改变模型语义；
* 不得只重跑警告单元。

任何 convergence warning 必须记录 target、baseline、held-out group、inner fold 和 config。

不得运行后临时增加 `max_iter`。

---

## 二十三、运行前完整性检查

至少验证：

1. 固定 GitHub commit 和 HF revision 未变化；
2. A1.2 两个提交存在；
3. A1.2 正式产物存在且哈希一致；
4. `lobo_primary_manifest.csv` 哈希一致；
5. `dev_structural_features.csv` 哈希一致；
6. primary serialized input 哈希一致；
7. 标签索引哈希一致；
8. test manifest 哈希一致；
9. 四个 held-out group 数量正确；
10. 三个目标的样本和类别统计正确；
11. Side Effect / AssistantBench 为24负、0正；
12. 每条轨迹只属于一个 held-out group；
13. role=train 与 role=held_out 无重叠；
14. baseline列表恰好B0–B3；
15. 输入视图恰好primary；
16. 未引用 secondary LOBO、LOMO、reasoning、error ablation；
17. test access 配置固定为false；
18. 正式代码与 A1.3a 提交一致；
19. 工作区干净。

任一关键哈希不匹配：

```text
STOP
```

---

## 二十四、测试要求

A1.3a 至少新增并通过以下测试。

### Manifest 与隔离

1. 主 LOBO 恰好四个 held-out group；
2. 每个 target 的样本统计符合预期；
3. 每条轨迹在每个 target 中只属于一个 held-out group；
4. held-out group 不进入外部训练；
5. held-out group 文本不进入 TF-IDF fit；
6. held-out group 特征不进入 StandardScaler fit；
7. held-out 标签不进入选择函数；
8. group_key 不跨 inner train/validation；
9. group_key 不跨外部训练/验证；
10. 每条训练域轨迹在 inner OOF 中恰好一次；
11. 每条有效轨迹在 external predictions 中恰好一次；
12. WorkArena L1/L2 在主 LOBO 中合并；
13. secondary LOBO manifest 未用于运行；
14. test trajectory key 不存在于运行集合。

### 模型与特征

15. baseline列表恰好B0–B3；
16. B2特征恰好13项且顺序一致；
17. B2复用 frozen structural features；
18. B3只使用 primary text；
19. Benchmark、model、task ID 不进入输入；
20. B2候选恰好6个；
21. B3候选恰好12个；
22. TF-IDF只含T1/T2；
23. 不存在char n-gram、Embedding或新增特征；
24. scaler与TF-IDF只在训练部分拟合。

### 选择与阈值

25. inner fold数按5→4→3→2选择最大可行值；
26. inner folds确定性复现；
27. 配置选择只使用 pooled inner OOF AP；
28. tie-break规则确定；
29. 阈值候选恰好0.05至0.95；
30. 阈值只使用选中配置的 pooled inner OOF；
31. held-out 结果不能进入配置或阈值选择；
32. A1.2最佳配置和阈值不被直接复用。

### 指标与输出

33. 正类概率通过 `classes_` 定位；
34. 所有概率有限且位于[0,1]；
35. mixed-class AP 使用 `average_precision_score`；
36. 单一类别 domain 的双类别指标为缺失；
37. 单一类别 domain 不按0进入 macro mean；
38. Side Effect / AssistantBench 诊断字段完整；
39. domain metrics 预期48行；
40. config selection 预期240行；
41. threshold selection 预期912行；
42. external predictions 预期2332行；
43. pooled LOBO 每条轨迹恰好一次；
44. 所有指标能从预测文件复算；
45. sample std 使用 `ddof=1`；
46. 重复运行输出确定。

### 边界

47. 不运行五组 secondary LOBO；
48. 不运行 Leave-One-Model-Out；
49. 不运行 reasoning/error 消融；
50. 不运行 B2+B3 融合或复杂模型；
51. 不访问 test 内容、标签、预测或指标；
52. 不修改 A1.2 产物；
53. 不修改正式语料、标签资格或 LOBO manifest；
54. 正式运行前后哈希一致；
55. Git工作区最终干净。

运行前测试只能使用合成数据验证模型行为。

允许使用真实 manifest 做：

```text
样本统计
分组完整性
哈希
inner fold生成
```

但在 A1.3a 提交前不得对真实 dev 调用模型 `.fit()`。

---

## 二十五、解释边界

允许写：

```text
在冻结的四组 primary LOBO dev 协议下观察到……
```

允许描述：

```text
结构信号在若干 held-out Benchmark 中保留
文本信号表现出明显 domain dependence
LOBO pooled 指标低于 task-grouped OOF
```

不得写：

```text
模型已经实现通用 Web Agent 评估
模型在 test 上有效
模型可以部署
模型证明了因果机制
模型已经超过论文方法
```

LOBO 仍然使用官方 dev。

---

## 二十六、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

技术上必须满足：

1. A1.3a 预注册提交存在；
2. 12个 target × held-out group 全部完成；
3. B0–B3全部完成；
4. 48个外部评估单元全部有预测；
5. 2332条外部预测完整唯一；
6. held-out domain 完全未参与训练和选择；
7. inner OOF选择完整；
8. 单一类别 domain 正确处理；
9. 所有哈希不变；
10. test访问为0；
11. 所有指标可复算；
12. 所有测试通过；
13. 结果可确定性复现；
14. Git工作区干净；
15. 正式结果独立提交。

### PASS_WITH_CONDITIONS

包括但不限于：

* 已知 Side Effect / AssistantBench 单一负类；
* Side Effect 因12个正类导致 domain 指标剧烈波动；
* 某个模型在某个 held-out domain 不预测正类；
* FutureWarning 保留；
* LOBO 性能明显低于 task-grouped OOF；
* 信号只在部分 Benchmark 保留；
* 结果有效但不足以支持模型升级。

由于 Side Effect / AssistantBench 已知为单一类别，本阶段科研判定原则上至少应为：

```text
PASS_WITH_CONDITIONS
```

除非该目标被预先从本阶段移除；本任务书不允许移除。

### STOP

出现：

* held-out Benchmark 参与训练、词表、缩放器、配置或阈值选择；
* 使用 held-out 结果调参后重评同一 domain；
* LOBO manifest 或输入哈希变化；
* 重新定义 B0–B3；
* 复用 A1.2 外层最佳配置作为 LOBO 固定最佳配置；
* 单一类别 AP/F1 被伪填为0或0.5；
* external predictions 重复或遗漏；
* 使用 secondary LOBO、LOMO、reasoning/error 输入；
* test被访问；
* 正式运行后修改代码并混用结果；
* 结果不能复现；
* 只报告最好 Benchmark。

---

## 二十七、正式报告

生成：

```text
docs/stage_a1_3_primary_lobo_report.md
```

至少包含：

1. 阶段判定；
2. 两个 Git commit；
3. 运行环境；
4. 输入、标签、manifest和A1.2产物哈希；
5. 四个 held-out group 样本统计；
6. inner fold数和可行性；
7. B0–B3定义；
8. 每个 target × baseline × held-out group 指标；
9. 单一类别 domain 处理；
10. macro mean±std；
11. pooled LOBO结果；
12. held-out prevalence 与 AP lift；
13. 配置和阈值分布；
14. 与 A1.2 pooled OOF 的描述性差值；
15. 最佳和最差 domain；
16. FutureWarning、convergence warning 和异常；
17. test访问为0声明；
18. 禁止实验未执行声明；
19. 三个目标的跨 Benchmark 信号分级；
20. 下一阶段证据摘要；
21. 明确停止并等待人工阶段门审查。

不得只展示最好的模型或 Benchmark。

---

## 二十八、最终汇报格式

Codex 完成后必须汇报：

1. `PASS / PASS_WITH_CONDITIONS / STOP`；
2. A1.3a 和 A1.3b 两个独立 commit；
3. 四个 held-out group；
4. inner fold数；
5. 48个外部单元是否完成；
6. 每个 target 的 B0–B3 domain 结果；
7. macro mean±std；
8. pooled LOBO AP/F1；
9. 与 A1.2 的 AP/F1 差值；
10. Side Effect / AssistantBench 单一类别诊断；
11. 配置和阈值分布；
12. 2332条预测完整性；
13. 警告与异常；
14. test访问情况；
15. 禁止实验未执行声明；
16. 定向测试和全仓回归；
17. 输入与manifest运行前后哈希；
18. Git status；
19. 三个目标的跨 Benchmark 信号分级；
20. 正式报告和机器摘要路径。

完成后必须停止。

不得自动进入：

```text
五组敏感性 LOBO
Leave-One-Model-Out
输入消融
Reasoning
复杂模型
test
```
