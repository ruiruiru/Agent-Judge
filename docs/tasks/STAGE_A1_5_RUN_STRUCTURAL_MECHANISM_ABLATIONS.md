# Stage A1.5：结构机制消融（Primary LOBO）

## 一、阶段定位

Stage A1.4 已完成人工阶段门审查，判定：

```text
PASS_WITH_CONDITIONS
```

A1.4 的核心结果是：

- Success：跨 model 信号存在；在 model-only holdout、任务已见条件下，B3 文本模型很强；
- Side Effect：按预注册规则满足 cross-model signal，但仅 12 个正例，统计支持很弱；
- Looping：B2/B3 跨 model 信号稳定；
- A1.4 不是 joint task+model OOD，所有 held-out trajectory 都存在训练侧同任务 counterpart。

因此下一阶段不再扩展新的泛化维度，也不增加复杂模型。

Stage A1.5 只回答：

> A1.3 中 B2 的跨 Benchmark 结构信号，到底由哪些冻结结构特征组支撑？

本阶段使用 A1.3 的主四组 Primary LOBO 作为唯一主评估协议，因为跨 Benchmark 是当前更严格、更接近论文主问题的泛化场景。

本阶段只运行：

```text
官方 dev
+
benchmark_group_primary 四组 LOBO
+
B2 structural logistic regression 的预注册特征消融
```

不得运行：

```text
test
secondary 五组 LOBO
LOMO
joint task+model holdout
reasoning sensitivity
error ablation input view
B2+B3 fusion
TF-IDF 新实验
Embedding
MLP
Random Forest
XGBoost
Transformer
LLM Judge
```

---

## 二、核心研究问题

A1.5 只回答以下问题：

1. Success 的跨 Benchmark B2 信号是否主要由 `has_explicit_termination_signal` 支撑；
2. Success 去掉 repetition 特征后是否仍保留明显信号；
3. Looping 的强 B2 结果是否主要由直接重复统计：
   - `unique_action_ratio`
   - `consecutive_duplicate_action_count`
   支撑；
4. Looping 去掉 repetition 特征后是否仍有剩余的通用过程信号；
5. activity/volume、error、termination、repetition 四类结构信息各自贡献多大；
6. `termination + repetition` 三个高可解释特征单独使用时，能保留多少 B2 信号；
7. Side Effect 的结构模型是否继续表现为弱信号，仅作为诊断，不作为主要机制结论；
8. 当前结果是否支持进入下一阶段的统计不确定性分析或更复杂模型比较。

本阶段不得回答：

```text
最终 test 性能
因果机制
结构特征“导致”成功或循环
复杂模型是否优于轻量模型
联合跨任务+跨模型泛化
统计显著性
```

本阶段的“机制”只表示：

> 在冻结预测协议下，模型性能对某组结构特征的依赖程度。

不表示因果机制。

---

## 三、固定数据版本

继续使用：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

不得修改官方 dev/test split、标签、eligibility、trajectory_key、group_key、benchmark_group_primary、冻结结构特征、B2 模型族、指标和阈值候选。

---

## 四、必须先读取

至少读取：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/evaluation_protocol.md
docs/stage_a1_2_minimal_baseline_report.md
docs/stage_a1_3_primary_lobo_report.md
docs/stage_a1_4_leave_one_model_out_report.md

artifacts/dev_analysis_index.csv
artifacts/dev_structural_features.csv
artifacts/lobo_primary_manifest.csv
artifacts/a1_3_lobo_inner_folds.csv
artifacts/a1_3_lobo_predictions.csv
artifacts/a1_3_lobo_domain_metrics.csv
artifacts/a1_3_lobo_macro_metrics.csv
artifacts/a1_3_lobo_pooled_metrics.csv
artifacts/a1_3_lobo_run_summary.json
artifacts/a1_4_lomo_run_summary.json

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
configs/stage_a1_3_lobo_execution.yaml
requirements/baseline-lock.txt
artifacts/baseline_environment.json
research/01_DECISION_LOG.md
```

如果 A1.3 某产物精确文件名不同，只允许通过 `artifacts/a1_3_lobo_run_summary.json` 解析正式路径。不得使用临时、失败、旧版或手工修改的结果。

---

## 五、唯一正式输入

本阶段模型只允许读取：

```text
artifacts/dev_structural_features.csv
```

标签和 LOBO role 只能通过：

```text
trajectory_key
+
artifacts/dev_analysis_index.csv
+
artifacts/lobo_primary_manifest.csv
```

连接。

不得读取：

```text
primary text
reasoning
error-ablation text
benchmark literal
model_name
task_id
trajectory_key encoding
reward
summary_info
annotation
test
```

A1.5 是纯结构机制实验。

---

## 六、冻结的13个结构特征

顺序固定：

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

不得新增、重新定义、重排或从 raw JSON 重新提取。

---

## 七、预注册特征组

### G1_activity_volume

```text
step_count
nonempty_action_count
nonempty_observation_count
nonempty_focused_element_count
action_char_count_total
observation_char_count_total
action_char_count_mean_nonempty
observation_char_count_mean_nonempty
```

索引：`1,2,3,4,8,9,10,11`。

### G2_error

```text
natural_error_step_count
natural_error_step_ratio
```

索引：`5,6`。

### G3_termination

```text
has_explicit_termination_signal
```

索引：`7`。

### G4_repetition

```text
unique_action_ratio
consecutive_duplicate_action_count
```

索引：`12,13`。

四组必须互斥且并集等于全部13项。

---

## 八、预注册消融变体

只允许以下7个 structural variants：

### S0_full13
全部13项。作为正控制，必须复现 A1.3 B2。

### S1_no_termination
删除 G3，仅保留其余12项。

核心问题：Success 是否高度依赖显式 termination。

### S2_no_repetition
删除 G4，仅保留其余11项。

核心问题：Looping 去掉直接重复统计后还能剩多少。

### S3_no_activity_volume
删除 G1，只保留 G2+G3+G4，共5项。

### S4_no_error
删除 G2，保留其余11项。

### S5_no_termination_or_repetition
删除 G3+G4，只保留 G1+G2，共10项。

### S6_termination_repetition_only
只保留 G3+G4，共3项：

```text
has_explicit_termination_signal
unique_action_ratio
consecutive_duplicate_action_count
```

不得临时新增 S7/S8、逐特征13项穷举、任意组合、自动 feature selection、L1、SHAP、Permutation importance、PCA 或手工规则。

---

## 九、唯一主评估协议：复用 A1.3 Primary LOBO

必须严格复用：

```text
artifacts/lobo_primary_manifest.csv
artifacts/a1_3_lobo_inner_folds.csv
```

不得重新生成 outer role 或 inner folds。

每个 `target × variant × held_out_group`：

1. 外部 train/validation 与 A1.3 完全相同；
2. inner folds 与 A1.3 完全相同；
3. 唯一允许改变的是输入 feature subset；
4. 其它条件全部固定。

四个 held-out group 以 manifest 为唯一权威，语义上为 AssistantBench、VisualWebArena、WebArena、WorkArena。

---

## 十、目标数据与已知条件

继续使用：

```text
Success:     n=192, neg=134, pos=58
Side Effect: n=195, neg=183, pos=12
Looping:     n=196, neg=104, pos=92
```

Primary LOBO 分布必须与 A1.3 完全一致。

已知：

```text
Side Effect / AssistantBench = 24 negative / 0 positive
```

如任何 held-out 统计与 A1.3 正式报告不同：

```text
STOP
```

---

## 十一、模型保持为 B2 Logistic Regression

所有 S0–S6 都使用：

```text
StandardScaler
+
LogisticRegression
```

固定：

```text
penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026
```

候选：

```text
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

每个 variant 恰好6个候选。

不得复用 S0/A1.3 的最佳配置或阈值；每个 variant 必须独立使用自己的 inner OOF 选择配置和阈值。

---

## 十二、配置选择与阈值

对每个 `target × variant × held_out_group × config`：

1. inner train 拟合 scaler；
2. inner train 拟合 LR；
3. inner validation 输出 `P(y=1)`；
4. 合并全部 inner validation；
5. 每条外部训练轨迹恰好出现一次；
6. pooled inner OOF Average Precision 选择配置。

指标：

```python
sklearn.metrics.average_precision_score
```

同分规则：

1. `class_weight=None`；
2. `C=0.1 → 1.0 → 10.0`；
3. `config_id` 字典序。

阈值只在 selected config pooled inner OOF 上选：

```text
0.05, 0.10, ..., 0.95
```

目标正类F1最大；平局规则：Recall更高 → 更接近0.5 → 数值更小。

held-out Benchmark 不得参与任何配置或阈值选择。

---

## 十三、S0 正控制复现要求

`S0_full13` 必须复现 A1.3 正式 B2。

至少比较：

```text
selected_config_id
selected_threshold
external predicted_probability
external predicted_label
domain AP/F1
macro AP/F1
pooled AP/F1
```

要求：

- config 和 threshold 完全一致；
- predicted_label 完全一致；
- probability 绝对误差 ≤ 1e-12；
- metrics 绝对误差 ≤ 1e-12。

任一不满足：

```text
STOP
```

不得继续解释 S1–S6。

---

## 十四、指标与单类域

Mixed-class held-out domain 报告：

```text
PR-AUC / Average Precision
正类 F1
ROC-AUC
Precision
Recall
F2
Balanced Accuracy
MCC
prevalence
AP lift
predicted_positive_count
selected_config_id
selected_threshold
```

Side Effect / AssistantBench：

```text
metric_status = single_class_negative
```

双类别指标保持缺失，不得填0、0.5或1；继续报告 false-positive 诊断。

---

## 十五、三层汇总与预期行数

### Domain metrics

```text
3 targets × 7 variants × 4 groups = 84 rows
```

### Macro

每个 `target × variant` 报告 mixed-domain mean ± sample std（ddof=1）。

### Pooled LOBO

每个 variant：

```text
Success 192
Side Effect 195
Looping 196
总计 583
```

7 variants：

```text
4081 external predictions
```

### Selected inner OOF

每个 variant：

```text
3 × (192+195+196) = 1749
```

7 variants：

```text
12243
```

### Config selection

```text
3 × 4 × 7 × 6 = 504
```

### Threshold selection

```text
3 × 4 × 7 × 19 = 1596
```

### Pooled metrics

```text
3 × 7 = 21
```

任一关键数量不符：STOP。

---

## 十六、核心消融差值

生成：

```text
artifacts/a1_5_structural_ablation_deltas.csv
```

每个 `target × held_out_group × variant` 相对 S0：

```text
delta_AP = variant_AP - S0_AP
delta_F1 = variant_F1 - S0_F1
delta_AP_lift = variant_AP_lift - S0_AP_lift
```

每个 `target × variant` 同时计算：

```text
macro_delta_AP
macro_delta_F1
pooled_delta_AP
pooled_delta_F1
retained_AP_lift_ratio
```

定义：

```text
retained_AP_lift_ratio = variant pooled AP lift / S0 pooled AP lift
```

仅当 S0 pooled AP lift > 0 时计算；variant AP lift ≤ 0 时固定为0；S0 AP lift ≤0 时为 NA。

---

## 十七、预注册机制解释规则

这些规则只用于描述，不是显著性检验。

### strong_dependency

删除某组后同时满足：

1. pooled AP lift 保留比例 < 0.50；
2. 至少3/4 mixed-class held-out domains AP下降；
3. 至少2个 domain 的 AP 绝对下降 ≥0.05。

### moderate_dependency

```text
0.50 ≤ retained AP lift ratio < 0.80
```

且多数 mixed domains AP下降。

### limited_dependency

```text
retained AP lift ratio ≥ 0.80
```

或 domain 方向混合、没有一致下降。

Side Effect 不允许据此包装成可靠因果或强机制结论，只能做 exploratory structural dependency。

---

## 十八、Success 的重点判断

重点比较：

```text
S0_full13
S1_no_termination
S2_no_repetition
S5_no_termination_or_repetition
S6_termination_repetition_only
```

### Termination dependency

若 S1 仍保留 ≥80% 的 S0 pooled AP lift，且至少3/4 mixed domains AP高于 prevalence：

> 显式 termination 不是 Success 跨 Benchmark 结构信号的唯一主来源。

若保留 <50%：

> Success B2 对显式 termination 高度依赖。

不得写“termination 导致成功”。

### Termination+repetition sufficiency

若 S6 保留 ≥80% S0 AP lift：

> B2 大部分 Success 信号可由 termination/repetition 三个高可解释特征解释。

若明显低于80%：

> activity/volume/error 中存在重要额外信息。

---

## 十九、Looping 的重点判断

重点比较：

```text
S0_full13
S2_no_repetition
S5_no_termination_or_repetition
S6_termination_repetition_only
```

若 S2 保留 <50% S0 pooled AP lift：

> Looping B2 高性能主要依赖直接 repetition statistics。

若 S2 仍保留 ≥80%：

> 除直接 repetition 统计外，还有强烈的其它结构信号。

50%–80%：

> repetition 重要但不是唯一来源。

若 S6 单独保留 ≥80% S0 AP lift：

> 当前 Looping 很大程度可被极简结构检测器解决。

这会降低把 Looping 作为核心创新任务的必要性，但不属于实验失败。

---

## 二十、Side Effect 解释边界

Side Effect 总正例仅12，且 AssistantBench 为单一负类域。

因此：

- S0–S6 全部运行；
- 只做结构信号诊断；
- 不因单个高 AP 宣称机制；
- 不把消融波动解释为可靠 feature importance；
- 不根据 Side Effect 结构消融触发模型升级。

---

## 二十一、两阶段执行与 Git 提交

### A1.5a：运行前冻结

真实 dev 上任何模型 `.fit()` 前完成：

- 核验 A1.3/A1.4 commits；
- 核验 structural features、primary LOBO manifest、A1.3 inner folds；
- 冻结四个 feature groups；
- 冻结七个 variants；
- 冻结模型、配置、阈值和解释规则；
- 编写脚本和测试；
- 完成哈希检查。

真实 dev 只允许做 manifest/feature schema/hash/inner-fold reuse audit，不得 `.fit()`。

生成：

```text
configs/stage_a1_5_structural_ablation.yaml
artifacts/a1_5_prerun_integrity.json
artifacts/a1_5_feature_group_registry.csv
scripts/run_stage_a1_5_structural_ablation.py
tests/test_stage_a1_5_structural_ablation.py
```

更新：

```text
research/01_DECISION_LOG.md
```

提交：

```text
chore: preregister structural mechanism ablations
```

### A1.5b：正式执行

运行前 `git status` 必须干净。

正式第一步只跑 S0 正控制。S0 不复现 A1.3 B2 则 STOP；通过后才运行 S1–S6。

正式结果提交：

```text
experiment: run structural mechanism ablations
```

不得 amend A1.5a。

---

## 二十二、异常处理

Pre-fit hash/schema/line-ending 守卫失败：

- 保留失败日志；
- 证明0次 `.fit()`、0正式预测；
- 允许独立修复提交；
- 从 S0 重新开始。

任何 `.fit()` 后发现实现错误：

1. 全部 A1.5 结果作废；
2. 保留失败日志；
3. 不得选择性保留好结果；
4. 独立修复提交；
5. 从 S0 完整重跑。

已知 `penalty='l2'` FutureWarning 继续计数记录；不得为了消除 warning 改模型语义。Convergence warning 必须记录，不得临时修改 max_iter。

---

## 二十三、输出产物

生成：

```text
artifacts/a1_5_feature_group_registry.csv
artifacts/a1_5_inner_config_selection.csv
artifacts/a1_5_inner_selected_oof_predictions.csv
artifacts/a1_5_threshold_selection.csv
artifacts/a1_5_external_predictions.csv
artifacts/a1_5_domain_metrics.csv
artifacts/a1_5_macro_metrics.csv
artifacts/a1_5_pooled_metrics.csv
artifacts/a1_5_structural_ablation_deltas.csv
artifacts/a1_5_config_frequency.csv
artifacts/a1_5_run_summary.json
docs/stage_a1_5_structural_mechanism_ablation_report.md
```

Feature registry 至少包含：

```text
variant_id
feature_name
feature_group
included
feature_order
```

External predictions 至少包含：

```text
trajectory_key
group_key
target
variant_id
held_out_group
true_label
predicted_probability
selected_threshold
predicted_label
selected_config_id
```

每个 `target × variant × trajectory_key` 唯一。

---

## 二十四、测试要求

A1.5a 至少新增并通过以下测试：

1. structural features 哈希与 A1.3 一致；
2. 13列名称与顺序完全一致；
3. 四个 feature group 完整、互斥、并集为13项；
4. S0恰好13项；
5. S1只删termination；
6. S2只删repetition；
7. S3只保留error+termination+repetition；
8. S4只删error；
9. S5只保留activity+error；
10. S6只保留termination+repetition；
11. 不存在额外 variant；
12. 不读取文本字段；
13. primary LOBO manifest哈希一致；
14. A1.3 inner folds哈希一致；
15. 不重新生成 inner folds；
16. held-out统计与A1.3一致；
17. test key不进入；
18. 所有variant只用 StandardScaler+LR；
19. 每个variant恰好6个config；
20. 配置只由 pooled inner OOF AP选择；
21. threshold恰好19个；
22. held-out不参与选择；
23. S0 config/threshold/labels完全复现；
24. S0 probabilities/metrics误差≤1e-12；
25. S0失败时阻止S1–S6；
26. external predictions=4081；
27. selected inner OOF=12243；
28. config selection=504；
29. threshold selection=1596；
30. domain metrics=84；
31. pooled metrics=21；
32. 每个target×variant×trajectory唯一；
33. 指标可独立复算；
34. macro std使用ddof=1；
35. Side Effect/AssistantBench双类别指标缺失；
36. retained AP lift ratio正确；
37. 机制分级只由冻结规则产生；
38. 重复运行结果确定；
39. 不运行B3新实验；
40. 不运行secondary LOBO；
41. 不运行LOMO；
42. 不运行joint OOD；
43. 不运行reasoning/error input；
44. 不运行fusion/复杂模型；
45. test内容/标签/预测/指标访问=0；
46. 不修改A1.2/A1.3/A1.4正式产物；
47. 核心哈希运行前后一致；
48. Git最终干净。

---

## 二十五、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### 技术 PASS 条件

1. A1.5a 预注册提交存在；
2. S0 精确复现 A1.3 B2；
3. S0–S6 全部完成；
4. 84个外部单元完整；
5. 4081 external predictions 完整唯一；
6. 12243 selected inner OOF 完整；
7. 选择只用 inner OOF；
8. outer/inner splits未变化；
9. test访问=0；
10. 禁止实验=0；
11. 指标可复算；
12. 测试全部通过；
13. 哈希不变；
14. Git干净；
15. 正式结果独立提交。

### PASS_WITH_CONDITIONS

例如：

- Side Effect 少数类波动；
- 某 ablation 某 domain 不预测正类；
- FutureWarning 保留；
- 某 feature dependency 明显 domain-dependent；
- 只能支持描述性 dependency，不能支持因果结论。

### STOP

包括：

- S0无法复现A1.3 B2；
- structural feature哈希改变；
- feature group/variant临时修改；
- inner folds重新生成；
- held-out参与配置或阈值选择；
- 新增模型或新特征；
- test被访问；
- 预测重复/遗漏；
- 指标无法复算；
- 正式运行后改代码并混用结果。

---

## 二十六、正式报告

生成：

```text
docs/stage_a1_5_structural_mechanism_ablation_report.md
```

至少包含：

1. 阶段判定；
2. A1.5 commits；
3. 环境与固定版本；
4. 输入及哈希；
5. A1.3 outer/inner split复用证明；
6. 四个 feature group；
7. 七个 variants；
8. S0正控制复现；
9. Success 所有 domain/macro/pooled 结果；
10. Looping 所有 domain/macro/pooled 结果；
11. Side Effect diagnostic；
12. 各 variant 对 S0 的 AP/F1差值；
13. retained AP lift ratio；
14. Success termination dependency；
15. Success termination+repetition sufficiency；
16. Looping repetition dependency；
17. Looping termination+repetition sufficiency；
18. activity/volume 与 error 的影响；
19. domain dependence；
20. warning与异常；
21. test访问=0；
22. 禁止实验未运行；
23. 非因果解释限制；
24. 对论文主线的证据摘要；
25. 是否建议进入下一阶段；
26. 明确停止等待人工审查。

---

## 二十七、最终汇报

Codex 最终必须汇报：

1. 阶段判定；
2. A1.5a/A1.5b及任何修复commit；
3. S0是否精确复现A1.3 B2；
4. 四个feature groups；
5. 七个variants；
6. 每个 target × variant 的 macro AP/F1；
7. pooled AP/F1；
8. Success 的 S1/S2/S5/S6 与 S0 差值；
9. Looping 的 S2/S5/S6 与 S0 差值；
10. retained AP lift ratio；
11. frozen dependency classification；
12. Side Effect diagnostic；
13. 4081 external predictions完整性；
14. 12243 inner OOF完整性；
15. config/threshold行数；
16. warnings；
17. test访问=0；
18. 禁止实验=0；
19. 定向测试/全仓测试；
20. 运行前后哈希；
21. Git status；
22. 正式报告与机器摘要路径。

完成后必须停止。

不得自动进入：

```text
统计显著性/Bootstrap
复杂模型
融合
secondary LOBO
joint OOD
test
```
