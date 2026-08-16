# Stage A1.4：运行 Leave-One-Model-Out 跨 Agent 模型最小基线

## 1. 阶段定位

Stage A1.3 已完成人工阶段门审查：

```text
PASS_WITH_CONDITIONS
```

A1.3 相关提交：

```text
6b98e03537360d8e60e5ccf3ca4c5ea7b51a652d
chore: preregister primary lobo baselines

6027d5e5af29a1b0143bb04024084a6c4209529e
fix: normalize primary lobo preregistration bytes

346bb4b3d4a90fc51c1e099618c3b7592fa76b99
experiment: run primary lobo baselines
```

A1.3 的主要结论：

```text
Success：B2 结构信号跨四个主 Benchmark 保留；
Side Effect：B3 只呈现局部/域特定信号；
Looping：B2 信号稳定，但重复类特征与标签定义较接近。
```

A1.4 只运行：

```text
Leave-One-Model-Out（LOMO）
+
B0–B3 原始最小基线
+
官方 dev
```

核心问题：

> A1.2/A1.3 中的信号，能否迁移到一个训练时完全没见过的 Agent/model？

本阶段禁止运行：

```text
secondary LOBO
结构特征消融
reasoning 敏感性
自然错误消融
B2+B3 融合
Embedding
MLP / Random Forest / XGBoost
Transformer / LLM Judge
test
```

---

## 2. 重要解释边界

LOMO 的外部留出依据是：

```text
model_name
```

同一个任务通常由多个 model 分别执行。因此外部训练和验证中，可能存在相同 `group_key`，但对应不同 model 的轨迹。

这在本阶段是**有意允许的**，因为本阶段只隔离 model 身份。

因此 A1.4 只能检验：

```text
跨 Agent/model 泛化
```

不能宣称：

```text
同时跨任务和跨 Agent/model 泛化
联合 OOD 泛化
```

不得擅自把本阶段改成“任务+模型双重留出”。

报告必须统计：

```text
held-out model 的任务组数
外部训练/验证重叠的 group_key 数
仅在 held-out model 出现的 group_key 数
有训练侧同任务对应物的 held-out 轨迹比例
```

外部训练/验证允许相同 `group_key`；但训练域内部的 inner folds 仍必须严格按 `group_key` 分组。

---

## 3. 固定数据版本

继续使用：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

不得修改：

* 官方 dev/test split；
* 标签与 eligibility；
* trajectory_key；
* group_key；
* model_name；
* 主输入视图；
* B0–B3 定义。

---

## 4. 必须先读取

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/dev_corpus_build_report.md
docs/evaluation_protocol.md
docs/pre_baseline_audit_report.md
docs/stage_a1_2_minimal_baseline_report.md
docs/stage_a1_3_primary_lobo_report.md

artifacts/dev_analysis_index.csv
artifacts/pre_baseline_summary.json
artifacts/leave_one_model_out_manifest.csv
artifacts/dev_structural_features.csv

artifacts/a1_2_run_summary.json
artifacts/a1_2_pooled_metrics.csv

artifacts/a1_3_lobo_run_summary.json
artifacts/a1_3_lobo_domain_metrics.csv
artifacts/a1_3_lobo_pooled_metrics.csv
artifacts/a1_3_lobo_predictions.csv

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
configs/stage_a1_2_execution.yaml
configs/stage_a1_3_lobo_execution.yaml

requirements/baseline-lock.txt
artifacts/baseline_environment.json
research/01_DECISION_LOG.md
```

如果 A1.3 产物名略有不同，只允许从正式机器摘要中解析路径，不得使用临时或失败运行产物替代。

---

## 5. 正式输入

B2：

```text
artifacts/dev_structural_features.csv
```

B3：

```text
data/processed/dev_serialized_primary.jsonl
```

标签、model 和分组信息只能通过：

```text
trajectory_key
+
artifacts/dev_analysis_index.csv
+
artifacts/leave_one_model_out_manifest.csv
```

连接。

不得使用：

```text
dev_serialized_error_ablation.jsonl
dev_serialized_reasoning_sensitivity.jsonl
lobo_primary_manifest.csv 作为 A1.4 外部划分
lobo_secondary_manifest.csv 作为 A1.4 外部划分
test 内容或标签
```

A1.2/A1.3 结果只能在 A1.4 正式完成后用于描述性比较，不能参与配置或阈值选择。

---

## 6. LOMO manifest 与模型集合

唯一权威划分：

```text
artifacts/leave_one_model_out_manifest.csv
```

具体 model 名称必须从 manifest 读取，不得凭记忆硬编码。

运行前必须验证：

1. dev 中恰好存在4个 model；
2. 每条 eligible trajectory 只属于1个 model；
3. 每个 `target × held_out_model` 均有外部验证样本；
4. 每个外部训练集含正负类；
5. 每个外部验证集含正负类；
6. 每条 eligible trajectory 对每个 baseline 恰好作为一次 held-out model 预测；
7. model_name 不进入 B2/B3 输入；
8. 不含 test trajectory key。

如果第1–6项任一不满足：

```text
STOP
```

不得删掉某个 model 后把实验包装成完整 LOMO。

三个目标总样本必须仍为：

```text
Success：192
Side Effect：195
Looping：196
```

---

## 7. Model 覆盖审计

A1.4a 生成：

```text
artifacts/a1_4_lomo_coverage_matrix.csv
```

至少包含：

```text
target
held_out_model
benchmark_group_primary
trajectory_count
task_group_count
negative_count
positive_count
coverage_present
class_status
```

每个 held-out model 标记：

```text
full_primary_benchmark_coverage
partial_primary_benchmark_coverage
```

必须核验 A1.1 已记录的条件：

```text
Meta-Llama 对应的精确 model_name 缺少 VisualWebArena 覆盖
```

精确 model 字符串以 manifest 为准。

如果实际 manifest 与先前审计不一致：

```text
STOP
```

对 partial-coverage model：

* 仍运行完整 held-out model 评估；
* 单独标记为探索性；
* 不得把差异解释成纯 model 差异；
* 不得从其他 split 补齐；
* 主结论优先基于 full-coverage models。

---

## 8. Model 字面值审计

A1.4a 对 B3 主文本执行标签无关审计，生成：

```text
artifacts/a1_4_model_literal_audit.csv
```

至少包含：

```text
trajectory_key
model_name
matched_literal
match_type
source_field
review_status
```

检查：

1. 精确 model_name 是否出现在文本；
2. 无歧义 model alias 是否出现；
3. model identity 是否由 metadata/序列化器注入；
4. 是否只是自然任务内容。

若 model identity 被 metadata 或序列化器系统性注入：

```text
STOP
```

不得临时 redaction 后继续。

若只是少量自然文本提及：保留输入不变，完整报告，并至少判为 `PASS_WITH_CONDITIONS`。

---

## 9. 外部隔离

对每个：

```text
target × held_out_model
```

必须满足：

1. held-out model 全部 eligible 轨迹只进入 external validation；
2. held-out model 不进入训练；
3. held-out model 文本不进入 TF-IDF fit；
4. held-out model 特征不进入 StandardScaler fit；
5. held-out 标签不进入配置选择；
6. held-out 标签不进入阈值选择；
7. held-out 类别比例不参与 class_weight；
8. model_name 不进入输入；
9. 每个 held-out model 只正式评估一次；
10. 不得根据外部结果改配置后重评。

---

## 10. 基线保持不变

只运行：

```text
B0_dummy_most_frequent
B1_dummy_prior
B2_structural_lr
B3_tfidf_lr
```

不得添加第五个模型。

不得直接复用 A1.2/A1.3 已选出的配置或阈值。每个 held-out model 都必须只用另外三个 model 的训练数据重新选择。

### B2

继续复用冻结的13项结构特征及顺序：

```text
step_count
nonempty_action_count
nonempty_observation_count
nonempty_focused_element_count
natural_error_step_count
natural_error_step_ratio
has_explicit_termination_signal
action_char_count_total
observation_char_count_total
action_char_count_mean_nonempty
observation_char_count_mean_nonempty
unique_action_ratio
consecutive_duplicate_action_count
```

模型：

```text
StandardScaler + LogisticRegression
```

候选：

```text
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

### B3

只允许：

```text
T1：word unigram
T2：word unigram + bigram
```

TF-IDF 与 Logistic Regression 全部配置必须与 A1.2/A1.3 一致。

候选共12个：

```text
T1/T2 × C{0.1,1,10} × class_weight{None,balanced}
```

---

## 11. Inner folds

A1.4a 生成：

```text
artifacts/a1_4_lomo_inner_folds.csv
```

对每个 `target × held_out_model`，只在其他三个 model 的轨迹中生成 inner folds。

训练域内部固定按：

```text
group_key = (benchmark_original, normalized_task_id)
```

分组。

使用：

```text
custom_deterministic_grouped_stratification_v1
split_seed = 2026
```

按以下顺序选择最大可行 fold 数：

```text
5 → 4 → 3 → 2
```

可行条件：

1. 每个 inner train/validation 都含正负类；
2. group_key 不跨 inner train/validation；
3. 每条外部训练轨迹恰好作为一次 inner validation；
4. 输出逐字节可复现。

2-fold 仍不可行：

```text
STOP
```

不得复制正类、拆任务组或手工移动样本。

---

## 12. 配置和阈值选择

每个候选配置：

1. 在各 inner train 拟合；
2. 在 inner validation 输出 `P(y=1)`；
3. 合并 pooled inner OOF；
4. 每条外部训练轨迹恰好出现一次；
5. 用 pooled inner OOF Average Precision 选择配置。

B2 同分：

```text
class_weight=None 优先
更小 C 优先
config_id 字典序
```

B3 同分：

```text
T1 优先
class_weight=None 优先
更小 C 优先
config_id 字典序
```

配置选定后，只用 selected config 的 pooled inner OOF 选择阈值：

```text
0.05, 0.10, ..., 0.95
```

目标：正类 F1 最大。

阈值同分：

1. Recall 更高；
2. 更接近0.5；
3. 数值更小。

然后在全部外部训练轨迹上重拟合，对 held-out model 评估一次。

---

## 13. 指标

每个 `target × baseline × held_out_model` 报告：

主指标：

```text
PR-AUC / Average Precision
正类 F1
```

辅助指标：

```text
ROC-AUC
Precision
Recall
F2
Balanced Accuracy
MCC
```

基础统计：

```text
held_out_model
coverage_status
trajectory_count
task_group_count
negative_count
positive_count
prevalence
predicted_positive_count
predicted_positive_rate
selected_config_id
selected_threshold
inner_n_splits
```

描述性差值：

```text
AP lift = AP - held-out prevalence
B2/B3 相对 B0/B1 的 AP/F1 差值
```

---

## 14. Model × Benchmark 诊断

生成：

```text
artifacts/a1_4_lomo_model_benchmark_diagnostics.csv
```

每行：

```text
target × baseline × held_out_model × benchmark_group_primary
```

至少报告：

```text
n
neg/pos
prevalence
metric_status
AP
F1
predicted_positive_count
probability_mean/median/max
```

单一类别 cell：双类别指标写缺失，不得填0或0.5。

缺失 Benchmark：

```text
metric_status = no_coverage
```

不得伪造0样本性能。

该诊断只用于解释覆盖混杂，不参与选择。

---

## 15. 汇总与预期行数

### Held-out model 原始指标

```text
3 targets × 4 baselines × 4 models = 48 rows
```

### Macro

每个 target × baseline 同时报告：

```text
all-model macro mean ± sample std
full-coverage-model macro mean ± sample std
full/partial model count
```

标准差固定 `ddof=1`。

### Pooled LOMO

每条 eligible dev trajectory 恰好作为一次 held-out model 外部预测。

每个 baseline：

```text
Success 192
Side Effect 195
Looping 196
合计 583
```

四个 baseline：

```text
external predictions = 2332
```

其他预期：

```text
selected inner OOF predictions = 6996
config selection = 240
threshold selection = 912
held-out model metrics = 48
```

任一数量不符：

```text
STOP
```

---

## 16. 与 A1.2/A1.3 比较

正式运行完成后生成：

```text
artifacts/a1_4_lomo_comparison.csv
```

每个 target × baseline 报告：

```text
A1.2 task-grouped pooled AP/F1
A1.3 benchmark-held-out pooled AP/F1
A1.4 model-held-out pooled AP/F1
A1.4-A1.2
A1.4-A1.3
```

同时报告：

```text
最佳 held-out model
最差 held-out model
model 间 sample std
full-coverage models 的最差结果
```

不同 held-out model 使用不同训练模型，概率尺度可能不同，因此必须同时展示 per-model、macro 和 pooled，不能只看 pooled。

不得声称统计显著。

---

## 17. 信号分级

每个目标给出：

```text
robust_cross_model_signal
partial_or_model_specific_signal
no_cross_model_signal
not_assessable
```

### robust_cross_model_signal

至少一个 B2/B3 满足：

1. pooled LOMO AP 高于总体 prevalence；
2. pooled F1 高于 B0、B1；
3. 在所有 full-coverage held-out models 中，AP 高于该 model prevalence，F1 高于该 model 的两个 Dummy；
4. partial-coverage model 没有无法解释的反向崩塌；
5. 无数据、实现、选择或 identity 注入异常。

### partial_or_model_specific_signal

包括：

* 只在部分 model 有效；
* full-coverage models 方向不一致；
* model 间波动大；
* AP 有提升但 F1 不稳定；
* Side Effect 只在个别 model 有局部信号。

### no_cross_model_signal

B2/B3 均未在多数 full-coverage models 超过 prevalence 和 Dummy。

### not_assessable

full-coverage models 少于2个或关键单元不可计算。

---

## 18. 三个目标的关注点

### Success

重点判断 B2 的跨 Benchmark 结构信号是否也跨 model。

### Side Effect

保持降级表达；必须报告每个 held-out model 的正例数和未预测正类单元。不得因单个 model 的高 AP 宣称通用信号。

### Looping

即使 B2 很高，也只能说明重复/长度结构跨 model 保留。是否属于深层机制必须留到 A1.5 消融。

---

## 19. 两阶段提交

### A1.4a：运行前冻结

真实 dev 上允许：

```text
manifest/覆盖/类别统计
group_key重叠统计
model literal audit
inner fold生成
哈希
```

不得调用真实 dev 模型 `.fit()`。

生成：

```text
configs/stage_a1_4_lomo_execution.yaml
artifacts/a1_4_lomo_prerun_integrity.json
artifacts/a1_4_lomo_coverage_matrix.csv
artifacts/a1_4_model_literal_audit.csv
artifacts/a1_4_lomo_inner_folds.csv
scripts/run_stage_a1_4_lomo.py
tests/test_stage_a1_4_lomo.py
```

提交：

```text
chore: preregister leave-one-model-out baselines
```

### A1.4b：正式运行

运行前工作区必须干净。正式开始后不得修改代码、配置、manifest、特征、候选配置、fold、阈值、指标或分级规则。

若 pre-fit 守卫失败：必须证明0次 `.fit()`、0条预测，保留日志，独立修复提交后从头运行。

若任何 `.fit()` 后发现实现错误：全部 A1.4 结果作废，独立修复提交，从所有目标/model/baseline 从头运行。

正式提交：

```text
experiment: run leave-one-model-out baselines
```

不得 amend A1.4a 或历史提交。

---

## 20. 正式产物

```text
artifacts/a1_4_lomo_inner_config_selection.csv
artifacts/a1_4_lomo_inner_selected_oof_predictions.csv
artifacts/a1_4_lomo_threshold_selection.csv
artifacts/a1_4_lomo_predictions.csv
artifacts/a1_4_lomo_model_metrics.csv
artifacts/a1_4_lomo_model_benchmark_diagnostics.csv
artifacts/a1_4_lomo_macro_metrics.csv
artifacts/a1_4_lomo_pooled_metrics.csv
artifacts/a1_4_lomo_config_frequency.csv
artifacts/a1_4_lomo_comparison.csv
artifacts/a1_4_lomo_run_summary.json
docs/stage_a1_4_leave_one_model_out_report.md
```

External predictions 至少包含：

```text
trajectory_key
group_key
target
baseline_id
held_out_model
benchmark_group_primary
true_label
predicted_probability
selected_threshold
predicted_label
selected_config_id
inner_n_splits
coverage_status
```

每个 `target × baseline × trajectory_key` 必须唯一。

---

## 21. 环境

复用 A1.2/A1.3 冻结环境：

```text
Windows 11 10.0.26200
Python 3.14.6
scikit-learn 1.9.0
NumPy 2.5.1
SciPy 1.18.0
PyYAML 6.0.3
CPU-only
GPU 0
network 0
```

精确值必须从 lock、environment 和 A1.3 summary 复核。

环境变化：

```text
STOP
```

已知 `penalty='l2'` FutureWarning 继续计数，不得为消除警告改变模型语义。任何 convergence warning 必须完整记录。

---

## 22. 最低测试要求

A1.4a 至少测试：

1. 恰好4个 held-out model，名称来自 manifest；
2. 每个 target 总样本为192/195/196；
3. 每个 target × model 外部 train/validation 均含正负类；
4. coverage matrix 可复算，Meta-Llama/VisualWebArena 条件得到核验；
5. held-out model 不进入训练、词表、scaler、class_weight、配置或阈值选择；
6. 外部相同 group_key 允许重叠并正确统计；
7. inner folds 按 group_key 隔离；
8. inner n_splits 按5→4→3→2取最大可行；
9. B0–B3、B2 13项特征、B2 6个候选、B3 12个候选保持一致；
10. 配置只由 pooled inner OOF AP 选择；
11. 阈值只由 selected config 的 pooled inner OOF 选择；
12. model identity metadata 注入触发 STOP；
13. external predictions 2332；
14. selected inner OOF 6996；
15. config selection 240；
16. threshold selection 912；
17. model metrics 48；
18. 单类/no-coverage诊断不伪填指标；
19. 全部指标可复算；
20. 不运行禁止实验、不访问 test；
21. 运行前后哈希一致；
22. 重复运行确定；
23. 最终 Git 工作区干净。

运行前模型行为测试只能使用合成数据。

---

## 23. 阶段判定

输出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### 技术通过条件

* 12个 `target × held_out_model` 和 B0–B3 全部完成；
* 48个外部单元完整；
* 2332 external predictions、6996 selected inner OOF 完整唯一；
* held-out model 未参与训练或选择；
* coverage/literal audit 完成；
* 哈希不变、test访问0、指标可复算；
* 测试全部通过、结果可复现、Git干净；
* 有独立 A1.4a/A1.4b 提交。

### PASS_WITH_CONDITIONS

包括：

* 已知 model 的主 Benchmark 覆盖不完整；
* 相同任务按设计跨外部 train/validation；
* Side Effect 正类极少；
* 某些 held-out model 不预测正类；
* model 间波动大；
* 少量自然文本 model literal；
* FutureWarning 保留；
* 结果只支持探索性跨 model 结论。

由于 LOMO 在 A1.1 中仅为附加探索性分析，且存在 partial Benchmark coverage，本阶段科研判定原则上至少为：

```text
PASS_WITH_CONDITIONS
```

### STOP

包括：

* held-out model 进入训练或选择；
* 擅自改成联合 task+model holdout；
* manifest/核心哈希变化；
* model identity 被 metadata 注入；
* 直接复用 A1.2/A1.3 配置或阈值；
* 静默少跑 model；
* 预测重复或遗漏；
* 单类/no-coverage指标伪填；
* test被访问；
* 正式运行后改代码并混用结果；
* 结果无法复算或复现；
* 只报告最好 held-out model。

---

## 24. 正式报告与最终汇报

正式报告：

```text
docs/stage_a1_4_leave_one_model_out_report.md
```

最终必须汇报：

1. 阶段判定；
2. A1.4 commits；
3. 四个精确 held-out model；
4. coverage matrix 与 partial coverage；
5. 每个 target × model 的 n/tasks/neg/pos；
6. 外部 group_key 重叠统计；
7. inner fold数；
8. 48个外部单元结果；
9. all-model macro；
10. full-coverage-model macro；
11. pooled LOMO AP/F1；
12. 相对 A1.2/A1.3 的差值；
13. model × Benchmark 诊断；
14. 配置与阈值分布；
15. 2332 external predictions；
16. 6996 selected inner OOF；
17. model literal audit；
18. 警告与异常；
19. test访问为0；
20. 禁止实验未运行；
21. 定向测试和全仓回归；
22. 运行前后哈希；
23. Git status；
24. 三个目标的跨 model 信号分级；
25. 正式报告和机器摘要路径。

完成后必须停止，不得自动进入 A1.5、复杂模型或 test。
