# Stage A1.6：Group-Aware Bootstrap 不确定性与稳定性分析

## 一、阶段定位

Stage A1.5 已完成并通过人工阶段门审查，判定：

```text
PASS_WITH_CONDITIONS
```

A1.5 commits：

```text
fa9ef0771ea44a720ed8b900199a75ef3c863379
chore: preregister structural mechanism ablations

e4fd9aba83cc6ed3b01b1f624c666b6cc7fce3ca
experiment: run structural mechanism ablations
```

A1.5 已确认：

- S0_full13 精确复现 A1.3 B2；
- Success 的 termination 存在中等预测依赖，但不是单一 shortcut；
- Success 的 termination+repetition 三项可保留大部分结构 AP lift；
- Looping 去掉直接 repetition 统计后仍保留大部分 AP lift；
- Looping 的 termination+repetition 三项已经足以产生极强排序信号；
- Side Effect 的结构基线总体没有正 AP lift，且仅有 12 个正例。

Stage A1.6 不训练任何新模型。

本阶段只使用已经冻结的外部预测，回答：

> A1.3 / A1.5 中观察到的跨 Benchmark AP/F1 及消融差异，在按 task group 考虑样本相关性的情况下有多大不确定性？这些差异是否可能主要来自当前 dev 样本的偶然波动？

本阶段是：

```text
统计不确定性 / 稳定性分析
```

不是：

```text
新模型实验
显著性挖掘
test评估
```

---

## 二、唯一主协议

唯一主协议继续是：

```text
A1.3 primary four-group LOBO
```

原因：

- A1.3 是当前主要的跨 Benchmark 泛化协议；
- A1.4 LOMO 为 model-only 探索性分析，所有 held-out 任务均存在训练侧 counterpart；
- A1.6 的核心目标是量化“跨 Benchmark 结论”的不确定性。

本阶段不得重新训练 A1.3 或 A1.5 模型。

不得重新生成预测。

不得重新选择配置或阈值。

---

## 三、固定数据版本

继续使用：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

不得修改：

- 官方 dev/test split；
- 标签；
- eligibility；
- trajectory_key；
- group_key；
- primary LOBO manifest；
- A1.3 predictions；
- A1.5 predictions；
- selected thresholds；
- selected configs。

---

## 四、必须先读取

至少读取：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/evaluation_protocol.md

docs/stage_a1_3_primary_lobo_report.md
docs/stage_a1_4_leave_one_model_out_report.md
docs/stage_a1_5_structural_mechanism_ablation_report.md

artifacts/dev_analysis_index.csv
artifacts/lobo_primary_manifest.csv

artifacts/a1_3_lobo_predictions.csv
artifacts/a1_3_lobo_domain_metrics.csv
artifacts/a1_3_lobo_macro_metrics.csv
artifacts/a1_3_lobo_pooled_metrics.csv
artifacts/a1_3_lobo_run_summary.json

artifacts/a1_5_external_predictions.csv
artifacts/a1_5_domain_metrics.csv
artifacts/a1_5_macro_metrics.csv
artifacts/a1_5_pooled_metrics.csv
artifacts/a1_5_structural_ablation_deltas.csv
artifacts/a1_5_run_summary.json

configs/stage_a1_3_lobo_execution.yaml
configs/stage_a1_5_structural_ablation.yaml

research/01_DECISION_LOG.md
```

如果 A1.3 或 A1.5 正式产物的精确路径不同，只允许通过对应机器摘要解析。

不得使用：

```text
临时运行文件
失败运行结果
旧版预测
手工复制的CSV
test
```

---

## 五、本阶段绝对禁止模型训练

A1.6 正式脚本不得调用：

```python
.fit()
.fit_transform()
partial_fit()
```

不得实例化或训练：

```text
LogisticRegression
DummyClassifier
StandardScaler用于拟合
TfidfVectorizer用于拟合
任何 sklearn estimator
任何深度学习模型
任何 LLM Judge
```

允许使用：

```text
NumPy
pandas
scikit-learn.metrics
标准统计函数
```

仅对冻结预测做：

```text
join
group-aware resampling
metric recomputation
paired delta
confidence interval
summary
```

如果正式运行发现任何模型 `.fit()` 调用：

```text
STOP
```

---

## 六、Bootstrap 为什么按 task group，而不是按 trajectory

同一个 task 可能由多个 Agent/model 执行。

这些 trajectory 不是完全独立样本。

因此不得直接逐 trajectory bootstrap。

Bootstrap 最小重采样单位固定为：

```text
group_key = (
    benchmark_original,
    normalized_task_id
)
```

同一个 `group_key` 内的所有 eligible trajectory 必须作为一个 cluster 一起被抽中或一起不被抽中。

这称为：

```text
task-group-aware cluster bootstrap
```

目的：

> 避免把同一任务下的多条 Agent 轨迹误当成完全独立样本，从而人为缩窄置信区间。

---

## 七、Bootstrap 层级

Primary LOBO 有四个 held-out Benchmark。

Bootstrap 必须在：

```text
target × held_out_group
```

内部独立进行 task-group cluster resampling。

不得把四个 Benchmark 的 group_key 放进一个池里直接抽样。

### 每个 bootstrap draw

对每个：

```text
target × held_out_group
```

执行：

1. 取得该 held-out group 中所有唯一 `group_key`；
2. 假设原始有 G 个 group；
3. 从这 G 个 group 中有放回抽取 G 次；
4. 某 group 被抽中 k 次，则该 group 下所有 trajectory 在该 draw 中复制 k 次；
5. 给复制样本生成 bootstrap-only instance id；
6. 不修改 true label、probability、predicted label；
7. 使用完全相同的 draw 同时评价所有待比较方法。

这样保证 paired comparison。

---

## 八、固定 Bootstrap 参数

固定：

```text
n_bootstrap_draws = 10000
random_seed = 2026
rng = numpy.random.Generator(numpy.random.PCG64(2026))
confidence_level = 0.95
interval_method = percentile
```

95% percentile CI：

```text
2.5th percentile
97.5th percentile
```

不得在看到结果后切换：

```text
BCa
basic bootstrap
studentized bootstrap
不同seed
更多/更少draws
```

如果存在实现问题，只能按异常处理规则整体作废后重新运行。

---

## 九、固定 draw registry

A1.6a 必须先生成并冻结：

```text
artifacts/a1_6_bootstrap_draw_registry.csv
```

至少包含：

```text
target
held_out_group
bootstrap_id
draw_position
sampled_group_key
sampled_group_occurrence
```

要求：

- 10000 个 bootstrap_id；
- 每个 target × held_out_group 的每个 draw 抽取 group 数等于原始 group 数；
- 同一 target × held_out_group 的 registry 被所有模型/variant 共用；
- registry 生成后正式统计阶段不得重新随机。

同时保存：

```text
artifacts/a1_6_bootstrap_registry_summary.json
```

记录：

```text
seed
rng
n_draws
每target/domain原始group数
registry_sha256
```

---

## 十、单一类别 bootstrap draw 的处理

AP、ROC-AUC、正类 F1 等指标要求 bootstrap sample 中存在必要类别。

对于某个 bootstrap draw：

### 如果原始 held-out domain 本身为 mixed-class

但重采样后变成：

```text
all-negative
```

或：

```text
all-positive
```

则该 draw 对需要双类别的指标：

```text
metric_status = invalid_single_class_resample
```

不得：

- 填0；
- 填0.5；
- 重抽直到有效；
- 删除后偷偷补足到10000个有效draw。

必须保留：

```text
fixed_draw_count = 10000
valid_draw_count
invalid_draw_count
valid_draw_fraction
```

CI 只使用固定10000 draw中有效的 metric values。

### 原始单一类别 domain

已知：

```text
Side Effect / AssistantBench
```

原始就是：

```text
24 negative
0 positive
```

因此：

- 不计算 AP/F1 bootstrap CI；
- 保留 false-positive rate / specificity 等诊断；
- 不进入 mixed-domain macro AP/F1；
- 不因为 bootstrap 生成伪正类。

---

## 十一、Bootstrap 主要 estimand

### 11.1 Per-domain metric distribution

对每个：

```text
target × method × held_out_group
```

计算：

```text
AP
F1
AP lift = AP - bootstrap sample prevalence
```

并报告：

```text
point estimate
bootstrap median
95% CI
valid_draw_fraction
```

### 11.2 Macro-over-domain metric distribution

对每个 bootstrap_id：

1. 在每个 mixed held-out domain 计算该 draw 的 metric；
2. 只对该 bootstrap_id 中 metric 有效的 mixed domains 求 macro mean；
3. 同时记录 valid_domain_count；
4. 如果该 target 在该 draw 中有效 mixed domains 少于2个，则 macro metric 记为 invalid。

得到：

```text
macro AP distribution
macro F1 distribution
macro AP-lift distribution
```

### 11.3 Pooled LOBO metric distribution

作为 secondary estimand：

1. 每个 held-out domain 分别 cluster bootstrap；
2. 将同一 bootstrap_id 的四个 held-out domain resampled predictions 拼接；
3. 计算 pooled AP/F1。

必须明确：

> 各 held-out Benchmark 对应独立训练模型，其概率尺度可能不同，因此 pooled AP CI 仅作为辅助结果，主要推断优先看 per-domain 与 macro。

---

## 十二、冻结方法集合

### A1.3 baseline methods

从 A1.3 读取：

```text
B0
B1
B2
B3
```

三个 target 全部计算 uncertainty summary。

但 primary scientific comparisons 只包含本任务书明确列出的项目。

### A1.5 structural variants

从 A1.5 读取：

```text
S0
S1
S2
S3
S4
S5
S6
```

三个 target 都可生成 CI summary。

但 primary paired delta 只运行预注册集合，不得穷举全部 pairwise comparisons。

---

## 十三、A1.3 与 A1.5 对齐验证

A1.5：

```text
S0_full13
```

必须与 A1.3：

```text
B2_structural_lr
```

逐行完全一致。

A1.6a 必须重新验证：

```text
trajectory_key
target
held_out_group
true_label
predicted_probability
selected_threshold
predicted_label
selected_config_id
```

要求：

```text
keys完全一致
labels完全一致
config完全一致
threshold完全一致
probability最大误差 = 0
prediction完全一致
```

任一不一致：

```text
STOP
```

不得继续 bootstrap。

---

## 十四、Primary scientific comparisons

只允许以下 primary paired comparisons。

所有 paired delta 必须：

> 在完全相同的 bootstrap draw 上计算 method A − method B。

### P1：Success B2 跨 Benchmark 信号

比较：

```text
Success / B2 AP lift
```

目标：

> B2 的跨 Benchmark AP lift 在 group-aware bootstrap 下是否稳定为正。

主要 estimand：

```text
macro AP lift
```

辅助：

```text
per-domain AP lift
pooled AP lift
```

### P2：Success B2 vs B3

paired delta：

```text
B2 - B3
```

指标：

```text
macro AP
macro F1
```

目标：

> A1.3 中“结构比文本更稳”的方向是否有稳定支持，还是当前差异可能来自小样本波动。

### P3：Success termination ablation

paired delta：

```text
S1_no_termination - S0_full13
```

主要：

```text
macro AP
```

辅助：

```text
pooled AP
macro F1
```

目标：

> 删除 termination 后的性能变化区间。

### P4：Success minimal structural sufficiency

paired delta：

```text
S6_termination_repetition_only - S0_full13
```

主要：

```text
macro AP
```

辅助：

```text
pooled AP
macro F1
```

目标：

> 仅3个特征与full13之间差异是否稳定。

### P5：Looping B2 跨 Benchmark 信号

比较：

```text
Looping / B2 macro AP lift
```

目标：

> Looping 的结构信号是否在 group-aware bootstrap 下仍稳定为正。

### P6：Looping repetition ablation

paired delta：

```text
S2_no_repetition - S0_full13
```

主要：

```text
macro AP
```

辅助：

```text
pooled AP
macro F1
```

目标：

> 删除两个直接 repetition 特征后，AP下降是否稳定存在。

### P7：Looping minimal structural sufficiency

paired delta：

```text
S6_termination_repetition_only - S0_full13
```

主要：

```text
macro AP
```

辅助：

```text
pooled AP
macro F1
```

目标：

> 3特征模型看似更高的 AP 是否具有稳定方向，或只是样本波动。

### P8：Side Effect B3 低支持诊断

不做“显著优于”主张。

报告：

```text
B3 per-domain AP CI
B3 macro AP CI
valid draw fraction
CI width
```

目标：

> 量化仅12个正例导致的不确定性。

不得因为某个 CI 下界 > prevalence 就升级 Side Effect 主结论。

---

## 十五、禁止额外 pairwise 挖掘

不得新增：

```text
S3 vs S4
S1 vs S2
所有7 variants两两比较
所有B0-B3两两比较
按结果挑最好variant后再bootstrap
```

A1.6 可以对所有方法输出单方法 CI，但 paired delta 的 primary inference 仅限 P1–P8。

其它比较如确有必要，只能标记：

```text
exploratory_descriptive_only
```

不得写进 primary conclusion。

---

## 十六、置信区间解释规则

本阶段不运行 p-value。

不写：

```text
statistically significant
显著
p < 0.05
```

统一使用：

```text
95% group-aware bootstrap confidence interval
```

### 对 positive signal（AP lift）

如果：

```text
95% CI lower bound > 0
```

且：

```text
valid_draw_fraction >= 0.95
```

标记：

```text
stable_positive_under_bootstrap
```

如果 point estimate > 0，但 CI 包含 0：

```text
directional_but_uncertain
```

如果 point estimate ≤ 0：

```text
no_positive_point_signal
```

如果：

```text
valid_draw_fraction < 0.80
```

则无论点估计如何，标记：

```text
low_support_unstable
```

### 对 paired delta（A − B）

如果：

```text
CI upper < 0
```

：

```text
stable_drop_for_A_vs_B
```

如果：

```text
CI lower > 0
```

：

```text
stable_gain_for_A_vs_B
```

如果 CI 包含 0：

```text
difference_uncertain
```

如果 valid_draw_fraction < 0.80：

```text
low_support_unstable
```

这些标签仅描述 bootstrap 稳定性，不代表因果或正式假设检验。

---

## 十七、Side Effect 特殊规则

Side Effect 总共只有：

```text
12 positives
```

且 primary LOBO：

```text
AssistantBench = 24 negative / 0 positive
VisualWebArena = 2 positives
WebArena = 8 positives
WorkArena = 2 positives
```

因此必须重点报告：

```text
每domain invalid single-class bootstrap draw数量
valid_draw_fraction
AP CI宽度
F1 CI宽度
```

如果 VisualWebArena / WorkArena 大量 bootstrap draw 变成全负：

这是数据支持不足的结果，不是脚本错误。

不得：

- 采用 stratified bootstrap 强行保证正类；
- 逐 trajectory 重采样；
- 重抽直到10000个有效draw；
- 用 smooth / pseudo-count 人工补正类。

Side Effect 的 A1.6 结论优先回答：

> 当前数据是否足以给出稳定不确定性区间？

而不是：

> 模型是否已被证明有效。

---

## 十八、Point estimate 回归检查

A1.6 正式 bootstrap 前必须从冻结 prediction 文件重新计算原始 point estimates。

要求：

### A1.3

重新计算：

```text
domain AP/F1
macro AP/F1
pooled AP/F1
```

与正式 A1.3 结果：

```text
absolute error <= 1e-12
```

### A1.5

重新计算：

```text
S0–S6 domain/macro/pooled AP/F1
```

与正式 A1.5：

```text
absolute error <= 1e-12
```

如果任一核心 point estimate 不一致：

```text
STOP
```

不得运行 bootstrap。

---

## 十九、输出文件

生成：

```text
artifacts/a1_6_bootstrap_draw_registry.csv
artifacts/a1_6_bootstrap_registry_summary.json

artifacts/a1_6_single_method_bootstrap_summary.csv
artifacts/a1_6_primary_paired_delta_summary.csv
artifacts/a1_6_domain_bootstrap_summary.csv
artifacts/a1_6_macro_bootstrap_summary.csv
artifacts/a1_6_pooled_bootstrap_summary.csv
artifacts/a1_6_side_effect_support_diagnostics.csv

artifacts/a1_6_primary_bootstrap_draw_metrics.parquet
artifacts/a1_6_run_summary.json

docs/stage_a1_6_group_aware_bootstrap_report.md
```

### 关于 bootstrap draw 明细

10000 draws × 多方法可能较大。

允许：

```text
Parquet
```

保存 draw-level metrics。

不得为了节省空间只保存 CI 而删除 draw-level primary comparison metrics。

至少必须可从 draw-level 文件复算：

```text
P1–P8 的95% CI
median
valid_draw_fraction
paired deltas
```

---

## 二十、主摘要表

正式报告至少包含一张 primary inference 表：

```text
comparison_id
target
estimand
point_estimate
bootstrap_median
ci_lower_95
ci_upper_95
valid_draw_fraction
bootstrap_grade
interpretation
```

P1–P8 全部列出。

---

## 二十一、完整性检查

必须验证：

1. A1.3 predictions 哈希一致；
2. A1.5 predictions 哈希一致；
3. primary LOBO manifest 哈希一致；
4. A1.5 S0 == A1.3 B2；
5. point estimates 全部精确复现；
6. bootstrap seed 固定2026；
7. draw count 恰好10000；
8. registry 在方法间完全共享；
9. resampling unit 是 group_key；
10. group cluster 不被拆散；
11. resampling 在 held-out domain 内进行；
12. 不跨 domain 混抽 group；
13. 不训练模型；
14. 不重新选 config；
15. 不重新选 threshold；
16. 不访问 test；
17. 不运行禁止实验；
18. CI 能由 draw-level metrics 复算；
19. paired delta 使用完全相同 bootstrap draw；
20. invalid single-class draw 没有被补抽替换；
21. Git 最终干净。

---

## 二十二、测试要求

A1.6a 至少新增并通过以下测试。

### Source regression

1. A1.3 prediction keys 唯一；
2. A1.5 prediction keys 唯一；
3. S0与A1.3 B2逐行相等；
4. A1.3 point metrics误差≤1e-12；
5. A1.5 point metrics误差≤1e-12。

### Bootstrap registry

6. seed固定2026；
7. PCG64固定；
8. draw数10000；
9. 每target/domain每draw抽取group数等于原始group数；
10. 有放回抽样可出现重复group；
11. 同一group所有trajectory一起复制；
12. 不同方法共享相同registry；
13. 不同target/domain不混抽；
14. registry重复生成逐字节一致。

### Metrics

15. AP使用average_precision_score；
16. F1以1为正类；
17. prevalence来自bootstrap sample；
18. AP lift使用bootstrap AP - bootstrap prevalence；
19. invalid single-class draw不填0或0.5；
20. valid_draw_fraction计算正确；
21. percentile CI使用2.5/97.5；
22. macro draw少于2个有效mixed domains时为invalid；
23. pooled draw按同bootstrap_id拼接domain；
24. paired delta逐draw相减；
25. paired methods必须使用同一draw。

### Side Effect

26. AssistantBench不计算AP/F1 CI；
27. VisualWebArena/WorkArena允许出现invalid resample；
28. 不进行stratified bootstrap；
29. 不补抽无效draw；
30. support diagnostics完整。

### Training boundary

31. 正式脚本不调用`.fit()`；
32. 不调用`.fit_transform()`；
33. 不调用`partial_fit()`；
34. 不实例化训练模型；
35. 不读取raw trajectory构造新特征；
36. 不修改任何预测概率。

### Output

37. P1–P8全部存在；
38. primary paired delta CI可由draw-level文件复算；
39. single-method CI可复算；
40. bootstrap grade由冻结规则自动产生；
41. 不存在结果后新增comparison；
42. 重复运行输出确定；
43. 核心哈希运行前后一致；
44. test访问0；
45. Git干净。

---

## 二十三、两阶段执行与 Git 提交

### A1.6a：预注册与 registry 冻结

在任何正式 bootstrap metric 计算前完成：

- 读取所有前置文件；
- 哈希核验；
- A1.3/A1.5 point estimate回归检查代码；
- S0/B2一致性检查；
- bootstrap algorithm；
- seed/RNG；
- P1–P8；
- CI规则；
- invalid draw规则；
- Side Effect规则；
- 测试；
- draw registry。

允许生成 registry。

不得正式计算 P1–P8 CI 后再改规则。

生成：

```text
configs/stage_a1_6_bootstrap.yaml
artifacts/a1_6_prerun_integrity.json
artifacts/a1_6_bootstrap_draw_registry.csv
artifacts/a1_6_bootstrap_registry_summary.json
scripts/run_stage_a1_6_group_bootstrap.py
tests/test_stage_a1_6_group_bootstrap.py
```

更新：

```text
research/01_DECISION_LOG.md
```

提交：

```text
chore: preregister group-aware bootstrap uncertainty
```

### A1.6b：正式统计运行

运行前：

```text
git status
```

必须干净。

顺序：

1. 重新执行 source/hash guards；
2. 重新复算 A1.3/A1.5 point estimates；
3. 检查 S0 == B2；
4. 读取冻结 bootstrap registry；
5. 正式计算10000 draws；
6. 输出 single-method CI；
7. 输出 P1–P8 paired delta CI；
8. 输出 Side Effect support diagnostics；
9. 独立复算 CI；
10. 生成正式报告。

正式结果提交：

```text
analysis: run group-aware bootstrap uncertainty
```

不得 amend A1.6a。

---

## 二十四、异常处理

### Pre-analysis guard failure

如果任何正式 bootstrap CI 计算前出现：

```text
hash mismatch
point estimate mismatch
S0/B2 mismatch
registry mismatch
schema mismatch
```

立即：

```text
STOP
```

允许独立修复提交，但必须重新从 A1.6a registry 冻结开始。

### 正式统计后实现错误

若计算 P1–P8 后发现实现错误：

1. 当前全部 A1.6 统计结果作废；
2. 保留失败日志；
3. 不得选择性保留某些CI；
4. 独立修复提交；
5. 使用同一冻结设计原则重新生成 registry；
6. 从10000 draws全部重跑；
7. 决策日志记录原因。

---

## 二十五、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

技术上必须：

1. A1.6a提交存在；
2. A1.3/A1.5 point estimates完全复现；
3. S0==A1.3 B2；
4. bootstrap registry冻结；
5. 10000 draws完成；
6. group-aware cluster正确；
7. P1–P8完成；
8. invalid draws正确保留；
9. paired delta正确；
10. CI可复算；
11. 没有模型训练；
12. test访问0；
13. 禁止实验0；
14. 测试全部通过；
15. 哈希不变；
16. Git干净；
17. 正式分析独立提交。

### PASS_WITH_CONDITIONS

例如：

- Side Effect valid bootstrap fraction低；
- 某 primary comparison CI很宽；
- 某点估计方向在bootstrap中不稳定；
- CI跨0；
- 少量Benchmark样本导致不确定性较大。

这些不是技术失败。

### STOP

包括：

- 逐trajectory bootstrap；
- group cluster被拆散；
- 跨Benchmark混抽group；
- 使用stratified bootstrap强制正类；
- 无效draw被补抽；
- 训练新模型；
- 重新选择config/threshold；
- point estimate无法复现；
- S0与B2不一致；
- test被访问；
- 结果后修改P1–P8；
- CI无法从draw-level复算；
- 只报告有利CI。

---

## 二十六、正式报告

生成：

```text
docs/stage_a1_6_group_aware_bootstrap_report.md
```

至少包含：

1. 阶段判定；
2. A1.6 commits；
3. 固定数据与来源哈希；
4. 为什么使用 task-group cluster bootstrap；
5. 为什么不逐trajectory bootstrap；
6. bootstrap seed、RNG、draw count；
7. invalid single-class resample处理；
8. A1.3/A1.5 point estimate复现；
9. S0/B2一致性；
10. P1–P8 primary inference table；
11. Success B2 AP lift CI；
12. Success B2 vs B3 paired CI；
13. Success termination ablation CI；
14. Success S6 vs S0 CI；
15. Looping B2 AP lift CI；
16. Looping repetition ablation CI；
17. Looping S6 vs S0 CI；
18. Side Effect bootstrap support diagnostics；
19. per-domain uncertainty；
20. macro uncertainty；
21. pooled uncertainty及概率尺度限制；
22. 哪些结论 stable；
23. 哪些只是 directional but uncertain；
24. 哪些 low-support；
25. 不使用p-value的说明；
26. 不代表因果的说明；
27. 没有新模型训练；
28. test访问0；
29. 禁止实验0；
30. 对下一阶段的证据摘要；
31. 明确停止等待人工阶段门审查。

---

## 二十七、最终汇报

Codex 最终必须汇报：

1. 阶段判定；
2. A1.6a/A1.6b及任何修复commit；
3. A1.3/A1.5 point estimate是否精确复现；
4. S0==A1.3 B2是否通过；
5. bootstrap seed/RNG/draw count；
6. 各target/domain group数；
7. P1–P8 point estimate / median / 95% CI；
8. P1–P8 valid_draw_fraction；
9. P1–P8 bootstrap grade；
10. Success B2/B3 paired结果；
11. Success S1/S6 vs S0结果；
12. Looping S2/S6 vs S0结果；
13. Side Effect invalid draw数量与valid fraction；
14. per-domain/macro/pooled CI摘要；
15. draw-level产物完整性；
16. 是否存在任何 `.fit()`；
17. test访问=0；
18. 禁止实验=0；
19. 定向测试/全仓测试；
20. 运行前后哈希；
21. Git status；
22. 正式报告与机器摘要路径。

完成后必须停止。

不得自动进入：

```text
复杂模型
B2+B3 fusion
secondary LOBO
joint OOD
test
```
