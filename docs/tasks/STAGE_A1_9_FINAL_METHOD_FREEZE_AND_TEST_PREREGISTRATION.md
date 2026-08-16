# Stage A1.9：Final Method Freeze & Test Preregistration

## 1. 阶段定位

Stage A1.8 已完成证据总审计，并给出：

```text
PASS_WITH_CONDITIONS
READY_FOR_FINAL_METHOD_FREEZE
```

A1.8 已确认：

- Success：B2 structural LR 是 primary candidate；跨 Benchmark 结构信号稳定。
- Looping：B2 structural LR 是 primary candidate；结构信号稳定，repetition 有稳定增量但不是全部来源。
- Side Effect：B4 dense embedding LR 仅 exploratory-only；当前仅 12 个正例，不具备强 confirmatory 资格。
- 不再有需要通过继续 dev 探索才能解决的 blocking evidence gap。
- A1.2–A1.7 均属于 dev-driven method selection，因此在访问 test 前必须冻结最终方法。

Stage A1.9 的唯一目的：

> 在完全不访问 test 内容、标签、预测或指标的前提下，把最终方法、dev-only 最终配置选择、阈值、模型文件、test 处理算法、test 指标、bootstrap、claim 边界和“一次性开封”顺序全部冻结。

本阶段不是 final test。

本阶段完成后仍需人工审批，才可进入 Stage A1.10。

---

## 2. 绝对边界

A1.9 允许：

```text
读取 A1.1–A1.8 已冻结 dev 产物
在 dev 上按本任务书运行最终配置选择
在全部 eligible dev 上 fit 最终模型
冻结最终模型文件和 hashes
写 test 前预注册协议
```

A1.9 禁止：

```text
读取 test manifest
读取 test trajectory 内容
读取 test annotation/label/eligibility
生成任何 test feature / embedding
生成任何 test prediction
计算任何 test metric
根据 test 修改 feature/config/threshold/model
新增模型族
fusion
第二 embedding 模型
LLM Judge
secondary LOBO
joint OOD
```

A1.9 test access count 必须为：

```text
manifest = 0
content = 0
labels = 0
eligibility = 0
features = 0
embeddings = 0
predictions = 0
metrics = 0
```

---

## 3. 固定数据版本

继续固定：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

Qwen embedding 模型继续固定：

```text
Qwen/Qwen3-Embedding-0.6B
immutable revision:
97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3

model.safetensors SHA-256:
0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd
```

不得升级或替换。

---

## 4. 必须先读取

至少读取：

```text
research/01_DECISION_LOG.md

docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/evaluation_protocol.md

docs/stage_a1_2_minimal_baseline_report.md
docs/stage_a1_3_primary_lobo_report.md
docs/stage_a1_4_leave_one_model_out_report.md
docs/stage_a1_5_structural_mechanism_ablation_report.md
docs/stage_a1_6_group_aware_bootstrap_report.md
docs/stage_a1_7_frozen_dense_semantic_baseline_report.md
docs/stage_a1_8_evidence_audit_report.md

artifacts/a1_8_claim_matrix.csv
artifacts/a1_8_evidence_registry.csv
artifacts/a1_8_remaining_evidence_decision.json
artifacts/a1_8_run_summary.json

artifacts/dev_analysis_index.csv
artifacts/dev_structural_features.csv
artifacts/a1_7_qwen3_embedding_0p6b.npy
artifacts/a1_7_embedding_index.csv
artifacts/a1_7_embedding_extraction_summary.json

artifacts/evaluation_folds_success.csv
artifacts/evaluation_folds_side_effect.csv
artifacts/evaluation_folds_looping.csv

configs/baseline_registry.yaml
configs/evaluation_protocol.yaml
requirements/baseline-lock.txt
requirements/semantic-lock.txt
```

若精确路径不同，只允许通过正式 machine summary 解析。

不得用临时/失败/旧版文件替代。

---

## 5. Final method freeze proposal（现在变成正式冻结候选）

### 5.1 Success

```text
method_id = FINAL_SUCCESS_B2
model family = B2 structural Logistic Regression
role = confirmatory_primary
```

输入固定为 A1.2/A1.3 的 13 个结构特征：

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

### 5.2 Looping

```text
method_id = FINAL_LOOPING_B2
model family = B2 structural Logistic Regression
role = confirmatory_primary
```

同样使用全部 13 个冻结结构特征。

不得把 S6 三特征替代为 final confirmatory method。

S6 只保留 dev-only auxiliary 证据，不进入 final test 主方法。

### 5.3 Side Effect

```text
method_id = FINAL_SIDE_EFFECT_B4
model family = B4 Qwen3 frozen dense embedding + Logistic Regression
role = exploratory_only
confirmatory_eligible = false
```

输入固定为 A1.7 的 1024 维冻结 dense trajectory embedding。

A1.9 只在已冻结 dev embeddings 上选择最终 LR config/threshold。

A1.10 对 test 的 embedding extraction 必须原样使用 A1.7 的 tokenizer/chunking/pooling 规则。

无论 final test 结果多高，Side Effect 都不得在本研究中自动升级成 confirmatory claim。

---

## 6. 为什么 A1.9 还需要一次 dev-only final config selection

A1.3/A1.7 的 LOBO 每个 held-out Benchmark 都独立选择 config 和 threshold。

final test 只允许一个最终模型，因此必须在 test 开封前，把：

```text
一个 config
一个 threshold
一个 fitted model
```

冻结下来。

这不是新增研究模型，而是把已选定的模型族变成唯一可用于 final test 的 deployable specification。

本阶段不得再比较新的 feature family 或 model family。

---

## 7. 最终 dev selection folds

唯一允许使用的 final selection folds：

```text
A1.1 frozen 5-fold grouped evaluation folds
```

分别读取：

```text
artifacts/evaluation_folds_success.csv
artifacts/evaluation_folds_side_effect.csv
artifacts/evaluation_folds_looping.csv
```

要求：

```text
group_key = (benchmark_original, normalized_task_id)
seed = 2026
同 task 跨 model 不得跨 fold
每条 eligible dev trajectory 恰好一次 OOF
```

不得重新生成 folds。

不得改 fold 数。

如果 fold 文件与 A1.1 formal evidence 不一致：

```text
STOP
```

---

## 8. Final B2 selection protocol（Success / Looping）

候选固定：

```text
StandardScaler
+
LogisticRegression

penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026

C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共 6 configs。

### 8.1 OOF config selection

对每个 target：

```text
Success
Looping
```

对每个 6 configs：

1. 使用 A1.1 frozen 5-fold grouped folds；
2. 每 fold 的 scaler 只 fit 当前 fold train；
3. LR 只 fit 当前 fold train；
4. 输出 validation P(y=1)；
5. 合并为全 dev pooled OOF predictions；
6. 每条 eligible trajectory 恰好出现一次。

以：

```text
Average Precision
```

选择 config。

Tie-break 固定：

1. `class_weight=None`；
2. 更小 C：0.1 → 1 → 10；
3. config_id 字典序。

不得看 test。

### 8.2 Final threshold

selected config 的 pooled OOF probabilities 上：

```text
threshold ∈ {0.05, 0.10, ..., 0.95}
```

最大化：

```text
positive-class F1
```

Tie-break：

1. higher recall；
2. closer to 0.5；
3. smaller threshold。

### 8.3 Final refit

配置与阈值冻结后：

```text
StandardScaler fit on ALL eligible dev
LR fit on ALL eligible dev
```

生成最终 frozen pipeline。

Success expected dev rows：

```text
192
```

Looping expected dev rows：

```text
196
```

---

## 9. Final B4 selection protocol（Side Effect exploratory）

只允许读取 A1.7 已冻结：

```text
196 × 1024 embedding matrix
```

再通过 trajectory_key 连接 Side Effect eligibility。

Side Effect expected eligible dev：

```text
195
```

Classifier：

```text
LogisticRegression
penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026
NO StandardScaler
```

候选：

```text
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共 6 configs。

使用 A1.1 Side Effect frozen 5-fold grouped folds。

Config / threshold 规则与第 8 节完全相同。

最后在全部 195 eligible dev embeddings 上 fit 一个 final LR。

不得重新生成 dev embedding。

不得重新 forward Qwen model。

---

## 10. A1.9 预期 dev fit 数

每 target：

```text
6 configs × 5 folds = 30 CV fits
+ 1 final full-dev fit
= 31 fits
```

3 targets：

```text
93 Logistic Regression final-selection fits
```

其中：

```text
Success B2 = 31
Looping B2 = 31
Side Effect B4 = 31
```

这是 A1.9 唯一允许的 estimator training。

不得新增任何 fit。

---

## 11. Final selection 输出完整性

### All-config OOF predictions

6 configs × eligible dev：

```text
Success: 6 × 192 = 1152
Side Effect: 6 × 195 = 1170
Looping: 6 × 196 = 1176
Total = 3498 rows
```

### Selected-config OOF predictions

```text
192 + 195 + 196 = 583 rows
```

### Config summary

```text
3 targets × 6 configs = 18 rows
```

### Threshold summary

```text
3 × 19 = 57 rows
```

### Final frozen models

```text
3
```

任一数量不一致：

```text
STOP
```

---

## 12. 最终模型 artifact

保存：

```text
artifacts/final_models/final_success_b2.joblib
artifacts/final_models/final_looping_b2.joblib
artifacts/final_models/final_side_effect_b4.joblib
```

以及：

```text
artifacts/a1_9_final_model_manifest.json
```

每个模型必须记录：

```text
method_id
target
role
input_contract
feature/embedding hash
dev eligibility count
selection fold hash
selected config
selected threshold
training environment
training commit
artifact SHA-256
```

Side Effect manifest 额外记录 Qwen full revision、weight SHA、embedding extraction contract。

---

## 13. Claim freeze

生成：

```text
artifacts/a1_9_final_claim_freeze.csv
```

至少冻结以下 claim role。

### Confirmatory claims eligible for final test

#### FC1 Success

```text
Frozen B2 structural classifier retains predictive signal on the untouched official test split.
```

中文允许表述：

> 冻结的轻量结构模型在完全未参与方法选择的官方 test 上仍具有 Success 预测信号。

#### FC2 Looping

```text
Frozen B2 structural classifier retains predictive signal on the untouched official test split.
```

### Exploratory-only

#### FE1 Side Effect

> 冻结 dense semantic baseline 在官方 test 上的 Side Effect 表现仅作探索性描述，不承担 confirmatory claim。

### Dev-only claims，不由 test 自动升级

继续保持：

```text
B2 vs B3 relative superiority
B4 vs B2/B3 relative superiority
termination mechanism
repetition mechanism
A1.4 model-only transfer
representation complexity hierarchy
```

A1.10 不得因为 test 某个数值漂亮而修改这些 claim role。

---

## 14. Final test 的正确解释范围

Official test 若与 dev 来自相同 benchmark families：

A1.10 只能直接确认：

```text
held-out official tasks / trajectories
```

不能把 test 结果描述成：

```text
new unseen Benchmark generalization
joint task+model OOD
new dataset transfer
cross-annotation-policy transfer
```

Primary LOBO 的跨 Benchmark 结论仍来自 dev 的冻结 grouped analysis。

Final test 的价值是：

> 在完全未参与方法选择的官方 holdout split 上确认 final method 是否保留预测信号。

---

## 15. Stage A1.10 的 test 开封顺序（A1.9 必须预注册）

A1.9 不执行下列操作，只冻结流程。

### A1.10a：Blind Test Inference

人工明确批准后才可开始。

允许读取：

```text
test identifiers
test raw trajectory content
```

仍禁止读取：

```text
test labels
annotations
eligibility flags
result metrics
```

A1.10a 必须：

1. 用 A0/A1 冻结映射定位全部 official test trajectories；
2. 用 A0.4/A1.0 同一 whitelist 构建 test primary input；
3. 用 A1.2 同一结构 feature extractor 构建 test B2 features；
4. 用 A1.7 同一 pinned Qwen/token/chunk/pooling 规则生成 test B4 embeddings；
5. 对每条 test trajectory 生成：
   - Success B2 probability + frozen label；
   - Looping B2 probability + frozen label；
   - Side Effect B4 probability + frozen label；
6. 不读取任何 test label；
7. 冻结 blind predictions；
8. 计算 SHA-256；
9. commit blind predictions；
10. Git clean。

在 blind prediction commit 之前：

```text
test label access 必须仍然 = 0
```

### Blind predictions expected row count

A0.2 已记录 official test trajectories：

```text
1106
```

若 A1.10a 在 identifier-only manifest 中确认仍为 1106，则：

```text
3 targets × 1106 = 3318 blind prediction rows
```

如果官方 frozen manifest 实际 count 与 A0.2 provenance 冲突：

```text
STOP
```

不得自行删轨迹。

---

## 16. A1.10b：One-time Label Unlock & Scoring

只有在：

```text
blind prediction artifact 已提交
hash 已冻结
Git clean
```

后，才允许首次访问 official test labels / eligibility。

解锁后：

1. 不得重新运行模型选择；
2. 不得修改 features；
3. 不得修改 embeddings；
4. 不得修改 config；
5. 不得修改 threshold；
6. 不得覆盖 blind prediction probabilities；
7. 只通过 trajectory_key join labels；
8. 按冻结 `<target>_eligible_main` 规则过滤对应 target 的正式评分集合；
9. 计算预注册 metrics；
10. 做预注册 group-aware bootstrap；
11. 生成一次性 final test report。

任何标签解锁后的方法修改：

```text
final confirmatory test INVALID
```

不得“修一下再跑”。

---

## 17. Final test primary metrics

### Success / Looping confirmatory

Primary point metrics：

```text
pooled Average Precision
pooled AP lift = AP - test prevalence
positive-class F1 at frozen dev threshold
```

Primary uncertainty estimand：

```text
pooled AP lift 95% task-group cluster bootstrap CI
```

Secondary：

```text
Precision
Recall
F2
ROC-AUC
Balanced Accuracy
MCC
per-Benchmark AP/F1
macro Benchmark AP/F1
```

由于 final test 对每个 target 使用同一个 full-dev fitted model：

> pooled probability scale 是统一的，因此 pooled AP 是合法 primary summary。

### Side Effect exploratory

同样计算上述指标，但：

```text
role = exploratory_only
```

不得进入 confirmatory pass/fail。

---

## 18. Final test bootstrap

A1.10b 预注册固定：

```text
n_draws = 10000
seed = 2027
rng = numpy.random.Generator(numpy.random.PCG64(2027))
CI = percentile 95%
```

Resampling unit：

```text
group_key = (benchmark_original, normalized_task_id)
```

为保持 test benchmark composition：

```text
within benchmark_group_primary strata
cluster bootstrap task groups with replacement
```

同一 group 下所有 model trajectories 一起复制。

不得逐 trajectory bootstrap。

不得 stratify by label。

不得遇到 invalid draw 就补抽。

Side Effect 单类 draw 保留并报告 valid fraction。

---

## 19. Final confirmatory grading rule

### Success / Looping

若：

```text
pooled AP lift point > 0
AND
95% cluster-bootstrap CI lower bound > 0
```

则：

```text
CONFIRMED_HELDOUT_SIGNAL
```

若：

```text
point > 0
但 CI 包含 0
```

则：

```text
DIRECTIONAL_BUT_NOT_CONFIRMED
```

若：

```text
point <= 0
```

则：

```text
NOT_CONFIRMED
```

F1、per-Benchmark、macro metrics 只用于描述，不改变 primary confirmatory grade。

不得创建 test 后的新 success criterion。

### Side Effect

固定只有：

```text
EXPLORATORY_TEST_RESULT
```

不根据 test 表现升级为 confirmatory。

---

## 20. Test 后禁止事项

一旦 A1.10b labels 解锁：

永久禁止为了改善 final result：

```text
改 threshold
改 C
改 class_weight
改 structural feature
改 Qwen revision
改 chunking/pooling
加入 calibration
加入 fusion
加入第二 embedding
加入 LLM Judge
删不利 Benchmark
删不利 trajectory
改 eligibility
改 primary metric
重新定义 success criterion
```

如果 final test 不理想：

> 如实报告，不得继续 tuning 后重新把同一 test 当 confirmatory test。

---

## 21. A1.9a：Preregistration commit

在任何 A1.9 real-dev `.fit()` 前完成：

- 读取 A1.8 claim matrix；
- 确认 READY_FOR_FINAL_METHOD_FREEZE；
- 冻结 3 个 final methods；
- 冻结 A1.1 5-fold selection folds；
- 冻结 config grids；
- 冻结 threshold rules；
- 冻结 final refit protocol；
- 冻结 A1.10 blind-first test opening；
- 冻结 metrics/bootstrap/confirmatory rules；
- 编写脚本与测试；
- test access 保持 0。

生成：

```text
configs/stage_a1_9_final_freeze.yaml
artifacts/a1_9_prerun_integrity.json
artifacts/a1_9_test_preregistration.json
artifacts/a1_9_final_claim_freeze.csv
scripts/run_stage_a1_9_final_freeze.py
tests/test_stage_a1_9_final_freeze.py
```

更新：

```text
research/01_DECISION_LOG.md
```

提交：

```text
chore: preregister final method freeze and test protocol
```

不得 amend。

---

## 22. A1.9b：Final dev selection & model freeze

运行前：

```text
git status clean
```

顺序固定：

1. source/hash guards；
2. test access audit = 0；
3. 运行 Success B2 final dev selection；
4. 运行 Looping B2 final dev selection；
5. 运行 Side Effect B4 final dev selection；
6. 冻结 config/threshold；
7. fit 3 个 full-dev final models；
8. 保存 model artifacts；
9. 计算 hashes；
10. 独立复算 dev OOF selection metrics；
11. 验证 fit count；
12. 验证没有 test access；
13. 生成正式 freeze report。

正式提交：

```text
experiment: freeze final dev-selected models before test
```

不得 amend A1.9a。

---

## 23. A1.9 输出

生成：

```text
artifacts/a1_9_all_config_oof_predictions.csv
artifacts/a1_9_selected_oof_predictions.csv
artifacts/a1_9_final_config_selection.csv
artifacts/a1_9_final_threshold_selection.csv

artifacts/final_models/final_success_b2.joblib
artifacts/final_models/final_looping_b2.joblib
artifacts/final_models/final_side_effect_b4.joblib

artifacts/a1_9_final_model_manifest.json
artifacts/a1_9_final_claim_freeze.csv
artifacts/a1_9_test_preregistration.json
artifacts/a1_9_run_summary.json

docs/stage_a1_9_final_method_freeze_report.md
```

---

## 24. A1.9 测试要求

至少验证：

### Provenance

1. A1.8 decision = READY_FOR_FINAL_METHOD_FREEZE；
2. A1.8 claim matrix hash一致；
3. structural feature hash一致；
4. A1.7 dev embedding hash一致；
5. A1.1 folds hashes一致；
6. baseline/semantic locks未修改。

### Method registry

7. 只有3个 final methods；
8. Success=B2；
9. Looping=B2；
10. Side Effect=B4 exploratory-only；
11. S6不进入final confirmatory；
12. 无B3 final method；
13. 无fusion；
14. 无第二embedding；
15. 无LLM Judge。

### Final selection

16. 每target恰好6 configs；
17. 使用 frozen 5 folds；
18. group_key不跨fold；
19. 每eligible dev每config恰好一次OOF；
20. config只按OOF AP选择；
21. tie-break固定；
22. threshold恰好19个；
23. threshold只使用selected-config OOF；
24. final refit使用全部eligible dev；
25. B2 scaler只在train fold/full dev fit；
26. B4不使用StandardScaler；
27. positive probability通过classes_定位。

### Counts

28. all-config OOF=3498；
29. selected OOF=583；
30. config rows=18；
31. threshold rows=57；
32. final model artifacts=3；
33. estimator fits=93。

### Final artifacts

34. 3个model均可重新load；
35. reload预测与保存前一致；
36. model hash记录；
37. thresholds记录；
38. training row counts正确；
39. input hashes记录。

### Test preregistration

40. blind inference before label unlock；
41. blind prediction commit before labels；
42. expected 1106 test trajectories only treated as prior provenance until A1.10 identifier check；
43. labels解锁后禁止模型修改；
44. Success/Looping primary metric固定pooled AP lift；
45. bootstrap seed=2027；
46. group-aware within-benchmark cluster bootstrap；
47. Side Effect固定exploratory-only；
48. confirmatory grading rule固定。

### Boundaries

49. A1.9 test manifest access=0；
50. test content access=0；
51. test label access=0；
52. test prediction=0；
53. test metric=0；
54. 新模型=0；
55. Git最终clean。

---

## 25. 异常处理

### Pre-fit failure

如果在 A1.9 第一次 real-dev `.fit()` 前发现：

```text
hash mismatch
fold mismatch
claim matrix conflict
config protocol conflict
```

立即 STOP。

允许独立 fix commit 后重新从 A1.9a guard 开始。

### Post-fit implementation error

若 A1.9 任意 real-dev `.fit()` 后发现实现错误：

1. 全部 A1.9 final selection/model artifacts 作废；
2. 保留失败日志；
3. 独立 fix commit；
4. 从三个 target 的全部 93 fits 重新运行；
5. 不得选择性保留某target。

### Any test access

如果 A1.9 期间发生任何 test manifest/content/label/prediction/metric access：

```text
STOP
```

必须人工审查是否污染 final confirmatory protocol。

不得自行继续。

---

## 26. 阶段判定

A1.9 最终：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS / PASS_WITH_CONDITIONS 技术必要条件

必须全部满足：

1. A1.9a prereg commit存在；
2. A1.8 ready decision已核验；
3. final method registry只有3项；
4. 3498 all-config OOF完整；
5. 583 selected OOF完整；
6. 18 config rows；
7. 57 threshold rows；
8. 93 fits；
9. 3 final model artifacts可reload；
10. model hashes冻结；
11. test preregistration完整；
12. test access所有类别=0；
13. 禁止实验=0；
14. tests通过；
15. Git clean；
16. A1.9b独立commit。

条件可来自：

```text
Side Effect仍exploratory-only
最终OOF threshold在不同Benchmark可能表现不均
已知FutureWarning
```

### STOP

包括：

- 改final method family；
- 改fold；
- 用test选config/threshold；
- 新增模型；
- test被访问；
- 数量不完整；
- model无法reload复现；
- test protocol未冻结。

---

## 27. 正式报告

生成：

```text
docs/stage_a1_9_final_method_freeze_report.md
```

至少包含：

1. 阶段判定；
2. A1.9 commits；
3. A1.8 ready decision provenance；
4. final method registry；
5. 3 target 的 final dev selection protocol；
6. selected configs；
7. selected thresholds；
8. final OOF AP/F1；
9. final model hashes；
10. training counts；
11. environment；
12. Side Effect exploratory role；
13. final claim freeze；
14. A1.10 blind-first opening protocol；
15. final test primary metrics；
16. final bootstrap；
17. confirmatory grading；
18. test 后永久禁止事项；
19. test access=0；
20. 是否建议人工授权 A1.10；
21. 明确停止。

---

## 28. 最终汇报

Codex 最终必须汇报：

1. 阶段判定；
2. A1.9a/A1.9b及任何fix commits；
3. A1.8 ready decision核验；
4. Success final config/threshold；
5. Looping final config/threshold；
6. Side Effect final config/threshold及exploratory-only标记；
7. 三个target final OOF AP/F1；
8. 3498 all-config OOF；
9. 583 selected OOF；
10. 18 config rows；
11. 57 threshold rows；
12. 93 fit count；
13. 3 final model artifacts及SHA；
14. reload复现；
15. final claim freeze；
16. A1.10 blind inference→commit→label unlock顺序；
17. final test metric/bootstrap规则；
18. confirmatory grading；
19. test manifest/content/labels/predictions/metrics全部访问0；
20. 禁止实验0；
21. tests；
22. hashes；
23. Git status；
24. 正式报告/机器摘要路径；
25. 是否建议人工授权 Stage A1.10。

完成后立即停止。

不得自动打开 test。
