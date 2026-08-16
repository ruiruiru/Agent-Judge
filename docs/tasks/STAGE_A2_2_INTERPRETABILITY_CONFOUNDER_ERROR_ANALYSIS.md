# Stage A2.2：Interpretability、Confounder Audit 与 Deterministic Error Analysis

## 1. 阶段定位

Stage A2.1 已完成：

```text
PASS
WAIT_FOR_HUMAN_A2_1_REVIEW
```

A2.1 已确认：
- B2：13 dimensions，CPU；
- B4：1024 dimensions，CUDA；
- B4/B2 warm extraction cost ratio：约 176469.135088×；
- B4/B2 representation storage ratio：约 39.145086×；
- B4/B2 dimension ratio：约 78.769231×；
- A1 metric recomputations：0；
- model fits：0；
- official-test access/tuning：0。

Stage A2.2 不再研究 efficiency。

本轮只回答三个问题：

1. Frozen B2 structural evaluator 主要依赖哪些结构特征？
2. 这些结构信号是否可能只是 benchmark / model metadata 的 proxy？
3. Success / Looping 的典型错误属于哪些可描述的 failure modes？

完成后必须：

```text
STOP
WAIT_FOR_HUMAN_A2_2_REVIEW
```

不得执行 A2.3、external validation 或 A3。

---

## 2. 科研身份

A2.2 的全部新增分析身份固定为：

```text
POST_FREEZE_DIAGNOSTIC
POST_FREEZE_DESCRIPTIVE
```

A2.2 不产生新的 confirmatory claim。

A1.11 frozen claim contract 保持：

```text
FC1 Success = CONFIRMATORY_SUPPORTED
FC2 Looping = CONFIRMATORY_SUPPORTED
FE1 Side Effect = EXPLORATORY_SUPPORTED
```

---

## 3. Pre-stage hard gates

开始前必须核验：

### 3.1 Git

```text
git status --porcelain
```

必须为空。

### 3.2 A1.11 final claim matrix

```text
artifacts/a1_11_final_claim_matrix.csv
SHA-256 =
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

### 3.3 A1.11 main test table

```text
artifacts/a1_11_table_main_test_results.csv
SHA-256 =
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

### 3.4 A2.1 result commit

必须可解析：

```text
b4e4a6ab95d8191f1bef91dab9844bef48f00a8d
```

A2.1 implementation：

```text
0708df64d11b6ed64d9fd6f4104f4c2de5dc8bba
```

A2.1 fix：

```text
a67f6451dd2fb39388337c58b3fda5439290bd35
```

任一核心 gate 不满足：

```text
STOP
```

---

## 4. Preregistration gate

如果本任务书：

```text
docs/tasks/STAGE_A2_2_INTERPRETABILITY_CONFOUNDER_ERROR_ANALYSIS.md
```

尚未被 Git 跟踪：

```text
STOP
```

仅允许创建独立 docs-only preregistration commit：

```text
chore: preregister A2.2 interpretability and confounder audit
```

然后结束本轮。

不得在 prereg-only 同一轮继续分析。

---

# Part I — Frozen B2 Interpretability

## 5. 目标

解释 final structural model 在 frozen state 下：
- 哪些 feature coefficient 最大；
- 方向是什么；
- 对应哪个结构组；
- 与 A1.5/A1.6 的 ablation/uncertainty 是否一致。

本部分不重新训练任何模型。

---

## 6. 允许读取的 final models

只允许读取：

```text
FINAL_SUCCESS_B2
FINAL_LOOPING_B2
```

必须从 A1.9/A1.10 frozen artifact registry 定位。

允许读取：

```text
StandardScaler.mean_
StandardScaler.scale_
LogisticRegression.coef_
LogisticRegression.intercept_
```

禁止：

```text
fit
partial_fit
cross_validate
hyperparameter search
threshold tuning
```

---

## 7. Frozen 13 structural features

必须读取仓库 frozen schema，不得凭记忆手写。

预期数量：

```text
13
```

如实际 frozen schema 不是 13：

```text
STOP
```

每个 feature 必须记录：

```text
feature_name
feature_group
standardized_coefficient
sign
absolute_coefficient
absolute_rank
```

---

## 8. Coefficient interpretation

生成：

```text
artifacts/a2_2_structural_coefficients.csv
```

至少包含：

```text
target
feature
feature_group
standardized_coefficient
absolute_coefficient
absolute_rank
sign
interpretation_note
evidence_status
```

其中：

```text
evidence_status = POST_FREEZE_DIAGNOSTIC
```

只允许解释为：
- positive association within frozen LR；
- negative association within frozen LR；
- larger absolute model weight。

禁止解释为：
- causal effect；
- causal mechanism；
- feature X causes success；
- feature Y causes looping。

---

# Part II — Frozen Feature-Group Evidence Synthesis

## 9. 目标

把 A1.5 / A1.6 已冻结的 feature-group evidence 整理成论文可用解释。

结构组必须从 frozen artifacts 读取并核验。

预期：

```text
activity / volume
error
termination
repetition
```

---

## 10. 禁止重新跑 A1.5 / A1.6

不得：
- 重新 ablation；
- 重新 bootstrap；
- 重新训练 S0–S6；
- 重新生成 A1.6 CI。

只能读取 frozen results。

生成：

```text
artifacts/a2_2_feature_group_evidence.csv
```

字段至少：

```text
target
feature_group
frozen_variant_or_comparison
effect_direction
uncertainty_status
source_stage
source_artifact
allowed_interpretation
forbidden_interpretation
evidence_status
```

其中：

```text
evidence_status = DEV_ONLY
```

---

# Part III — Metadata Confounder Audit

## 11. 科研问题

新增一个非常轻量的 dev-only diagnostic：

> 如果完全不看 trajectory structure，只知道 benchmark 和 agent/model identity，本身能预测多少 Success / Looping？

目的：

> 检查 structural B2 的 signal 是否可能主要由 obvious metadata proxy 解释。

这不是新的 final model。

---

## 12. 数据与 split

只允许使用：

```text
frozen dev trajectories
A1.1 frozen grouped folds
```

目标：

```text
Success
Looping
```

Side Effect 默认不运行。

不得使用 official test 来训练、调参或选择 metadata model。

---

## 13. Metadata features

唯一允许：

```text
benchmark_group_primary
model_name
```

编码：

```text
OneHotEncoder(handle_unknown="ignore")
```

禁止：

```text
normalized_task_id
task_id
trajectory_key
trajectory length
任何 B2 structural feature
goal text
actions
observations
reward
label-derived statistics
```

---

## 14. Metadata model contract

固定：

```text
LogisticRegression
C = 1
class_weight = "balanced"
threshold = 0.5
```

solver / max_iter 必须沿用仓库现有稳定 LogisticRegression contract；若存在多个实现，以 A1 baseline implementation 为准，并在 config 中记录。

禁止：

```text
C search
solver search
threshold tuning
feature selection
interaction search
```

---

## 15. Metadata evaluation

严格使用：

```text
A1.1 frozen grouped folds
```

每个 dev eligible trajectory 只能获得一条 OOF prediction。

Primary：

```text
pooled AP
```

Secondary：

```text
positive-class F1 @ 0.5
```

同时报告：

```text
prevalence
AP lift = pooled AP - prevalence
```

这里 AP lift 仅：

```text
POST_FREEZE_DIAGNOSTIC
```

不得纳入 A1 confirmatory grade。

---

## 16. B2 reference

需要比较 metadata-only 与 B2 时：

```text
只读取 frozen A1 B2 dev prediction / metric
```

不得重算 B2。

允许表述：

> Metadata-only baseline contains / does not contain appreciable predictive signal.

> Frozen B2 is descriptively higher/lower than metadata-only under the dev protocol.

禁止：

```text
B2 significantly outperforms metadata-only
```

本任务书不注册新的显著性检验。

---

## 17. Metadata outputs

生成：

```text
artifacts/a2_2_metadata_baseline_predictions.csv
artifacts/a2_2_metadata_baseline_summary.csv
artifacts/a2_2_metadata_config.json
```

predictions 至少：

```text
target
fold
trajectory_key
true_label
predicted_probability
predicted_label
benchmark_group_primary
model_name
```

summary 至少：

```text
target
eligible_n
positive_n
negative_n
prevalence
pooled_ap
ap_lift
f1_at_0_5
b2_frozen_dev_ap
b2_frozen_dev_f1
evidence_status
```

其中：

```text
evidence_status = POST_FREEZE_DIAGNOSTIC
```

---

# Part IV — Deterministic Error Analysis

## 18. 目标

解释 frozen final evaluator：

```text
什么时候会错？
错误是否与结构信号的边界一致？
```

只做：

```text
Success
Looping
```

Success 为正文 primary；Looping 为 secondary / sanity analysis。

---

## 19. 数据来源

只使用：

```text
A1.10 frozen scored predictions
```

以及对应 frozen cleaned trajectory representation。

不得：
- 重新 inference；
- 重新 embedding；
- 重新计算 probability；
- 修改 predicted label。

---

## 20. Error set 定义

按 A1.10 frozen：

```text
true_label
predicted_label
predicted_probability
frozen threshold
```

分别得到：

```text
False Positive
False Negative
```

---

## 21. 固定案例选择规则

每个 target、每个 error type：

```text
3 cases
```

因此：

```text
Success FP = 3
Success FN = 3
Looping FP = 3
Looping FN = 3
Total = 12
```

选择规则固定：

### Case A — Borderline

```text
abs(probability - threshold) 最小
```

### Case B — Median-error confidence

按：

```text
abs(probability - threshold)
```

升序排列，选择中位位置。

偶数时选择较低 index。

### Case C — High-confidence error

```text
abs(probability - threshold) 最大
```

Tie：

```text
trajectory_key lexical ascending
```

不得人工替换案例。

---

## 22. Error-case manifest

生成：

```text
artifacts/a2_2_error_case_manifest.csv
```

字段至少：

```text
target
error_type
case_role
trajectory_key
benchmark
model_name
true_label
predicted_label
probability
threshold
distance_from_threshold
selection_rank
```

---

## 23. 允许检查的 trajectory 内容

只允许读取 frozen cleaned / leakage-safe fields：

```text
goal
steps[].action
steps[].observation
steps[].focused_element
steps[].last_action_error
terminal structure/index
repetition-related structural pattern
```

不得读取：

```text
reward
cum_reward
cum_raw_reward
judge
annotation
success/failure outcome fields
summary_info 中结果语义
任何 A0.4 永久禁止字段
```

---

## 24. Error coding taxonomy

优先使用固定 taxonomy：

```text
LONG_BUT_UNSUCCESSFUL
SHORT_BUT_SUCCESSFUL
REPETITIVE_BUT_PROGRESSING
NON_REPETITIVE_FAILURE
EXPLICIT_ERROR_RECOVERY
TERMINATION_MISMATCH
STRUCTURALLY_NORMAL_SEMANTIC_FAILURE
OTHER
UNCLEAR
```

每个案例：

```text
primary_code = exactly one
secondary_code = optional one
```

如证据不够：

```text
UNCLEAR
```

不得硬猜。

---

## 25. Error notes

生成：

```text
artifacts/a2_2_error_case_notes.csv
docs/a2_2_error_analysis.md
```

每个案例至少回答：

1. 结构模型为什么可能作出该 prediction？
2. 真标签与结构 prediction 冲突在哪里？
3. 这是结构 representation 的哪种边界？
4. 是否需要 semantic task understanding 才容易解决？
5. 证据是否足够，还是 UNCLEAR？

只允许 descriptive interpretation。

---

# Part V — Paper-facing Synthesis

## 26. A2.2 主结论结构

生成：

```text
docs/a2_2_interpretability_and_confounder_report.md
```

必须按以下顺序：

### 26.1 Success
- top coefficients；
- A1.5/A1.6 feature-group evidence；
- metadata-only dev signal；
- deterministic FP/FN examples；
- allowed interpretation；
- limitations。

### 26.2 Looping
同上，但作为 secondary。

### 26.3 Combined implication

具体措辞必须由实际结果决定，不得预设 metadata baseline 一定弱。

---

## 27. Success 优先原则

如果篇幅有限：

```text
Success > Looping
```

不得因为 Looping 数字更漂亮而让其压过 Success 的论文位置。

---

## 28. 禁止事项

A2.2 禁止：

```text
修改 B2 feature set
修改 final model
修改 final threshold
重新训练 final B2
重新生成 test predictions
重新 embedding
重新 score A1.10
official-test tuning
根据 error case 增加 feature
根据 error case 修改模型
把 metadata baseline 当新的 final model
把 coefficient 当 causal effect
把 post-hoc error analysis 当 confirmatory evidence
执行 A2.3
执行 external validation
执行 A3
```

---

## 29. Scope counters

machine summary 必须包含：

```text
final_model_fits = 0
final_model_changes = 0
final_threshold_changes = 0
test_inference_runs = 0
embedding_runs = 0
A1_metric_recomputations = 0
official_test_tuning = 0

metadata_diagnostic_fits = expected_nonzero
```

必须明确区分：

> metadata_diagnostic_fits 是预注册的 dev-only diagnostic，不是 final model refit。

---

## 30. Implementation discipline

建议新增：

```text
scripts/run_a2_2_metadata_confounder_audit.py
scripts/build_a2_2_interpretability_package.py
```

error-case selection 必须 deterministic script 完成。

Codex 只分析最终 12 个固定案例。

不得让 Codex 自己浏览大量 error 后挑喜欢的样本。

---

## 31. Token / runtime discipline

Metadata baseline 很小，应一次性本地运行。

Error analysis：

```text
只读取 12 个固定案例
```

禁止：
- 遍历全部 test trajectory 做自由文本分析；
- 把全部 trajectory 文本打印进 Codex 上下文。

终端日志保持 compact。

---

## 32. Required outputs

至少生成：

```text
artifacts/a2_2_structural_coefficients.csv
artifacts/a2_2_feature_group_evidence.csv
artifacts/a2_2_metadata_config.json
artifacts/a2_2_metadata_baseline_predictions.csv
artifacts/a2_2_metadata_baseline_summary.csv
artifacts/a2_2_error_case_manifest.csv
artifacts/a2_2_error_case_notes.csv
artifacts/a2_2_run_summary.json

docs/a2_2_error_analysis.md
docs/a2_2_interpretability_and_confounder_report.md
docs/stage_a2_2_interpretability_confounder_error_analysis_report.md
```

---

## 33. Tests / verifiers

至少验证：

1. Git start clean；
2. claim matrix SHA；
3. main table SHA；
4. A2.1 result commit reachable；
5. B2 frozen schema = 13；
6. final model hashes unchanged；
7. no final-model fit path；
8. metadata features only benchmark + model；
9. metadata uses A1.1 grouped folds；
10. no test use in metadata model；
11. exactly one OOF prediction per eligible dev trajectory；
12. error manifest exactly 12 rows；
13. deterministic case selection；
14. no banned trajectory fields in error package；
15. no test re-inference；
16. no A1 metric recomputation；
17. output schemas；
18. summary ↔ artifact consistency。

---

## 34. Commit discipline

### A2.2a — prereg

```text
chore: preregister A2.2 interpretability and confounder audit
```

### A2.2b — implementation

```text
chore: implement A2.2 diagnostics
```

### A2.2c — result

```text
analysis: record A2.2 interpretability and confounder findings
```

不得 amend。

实现错误：

```text
独立 fix commit
```

失败 provenance 必须保留。

---

## 35. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS 必须满足

```text
Git start clean
A1 frozen hashes correct
Success coefficients complete
Looping coefficients complete
A1.5/A1.6 synthesis complete
metadata-only Success dev baseline complete
metadata-only Looping dev baseline complete
deterministic 12-case manifest complete
error notes complete
no final model refit
no test re-inference
no A1 metric recomputation
no official-test tuning
A2.3 not executed
Git final clean
```

### PASS_WITH_CONDITIONS

允许：
- 某些 error cases = UNCLEAR；
- metadata baseline 某 fold 存在 warning 但结果完整可解释；
- 个别 coefficient interpretation 只能保守描述。

### STOP

包括：
- frozen hash mismatch；
- final model changed；
- test-driven tuning；
- metadata baseline 使用 test；
- error cases 非 deterministic 选择；
- banned leakage field 被读取；
- A1 metric 被重算；
- 核心 artifact 无法解释；
- Git provenance 不清。

---

## 36. 最终汇报

Codex 必须汇报：

```text
阶段判定

A2.2 prereg commit
implementation commit
result commit
fix commits
amend

A1.11 claim matrix SHA verification
main test table SHA verification
A2.1 result commit verification

Success:
top 5 absolute coefficients
feature-group synthesis
metadata-only pooled AP
metadata-only AP lift
metadata-only F1@0.5
frozen B2 dev reference
FP case count
FN case count
main error codes

Looping:
top 5 absolute coefficients
feature-group synthesis
metadata-only pooled AP
metadata-only AP lift
metadata-only F1@0.5
frozen B2 dev reference
FP case count
FN case count
main error codes

final_model_fits = 0
final_model_changes = 0
final_threshold_changes = 0
test_inference_runs = 0
embedding_runs = 0
A1_metric_recomputations = 0
official_test_tuning = 0
metadata_diagnostic_fits = <value>

warnings
tests/verifiers
Git status

report path
machine summary path

WAIT_FOR_HUMAN_A2_2_REVIEW
```

完成后立即停止。

不得执行 A2.3。
