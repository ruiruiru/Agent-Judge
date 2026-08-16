# Stage A1.10：Blind-First Official Test Evaluation

## 1. 阶段定位

Stage A1.9 已完成 Final Method Freeze & Test Preregistration，并给出：

```text
PASS_WITH_CONDITIONS
```

A1.9 已确认：

- Success 最终方法已冻结为 `FINAL_SUCCESS_B2`；
- Looping 最终方法已冻结为 `FINAL_LOOPING_B2`；
- Side Effect 最终方法已冻结为 `FINAL_SIDE_EFFECT_B4`，且永久 `exploratory_only`；
- final config、threshold、fitted model artifacts、model hashes 已冻结；
- final claim roles 已冻结；
- final test metrics、bootstrap、grading rule 已冻结；
- test opening 顺序已冻结为：
  - A1.10a blind inference；
  - blind prediction hash + commit；
  - Git clean；
  - 人工再次审批；
  - A1.10b one-time label unlock + scoring；
- A1.9 结束时 test access 全部为 0。

A1.9 commits：

```text
A1.9a:
4944df46be45d8ad52d57a051e04b59c4a1a82ee
chore: preregister final method freeze and test protocol

A1.9b:
8f96a6f032ee9b4dd0272164d60230303612043b
experiment: freeze final dev-selected models before test
```

A1.8 claim matrix SHA-256：

```text
264678a325f1680c8cfdad3631e6f5209a29a91e6ab8dd5b9683adb857810590
```

Stage A1.10 的唯一目的：

> 在完全冻结方法、配置、阈值、模型、评价规则和 claim 边界之后，对 untouched official test 执行一次 blind-first final evaluation，判断 Success 与 Looping 的 held-out predictive signal 是否在完全未参与方法选择的官方 test 上得到确认。

本阶段不是继续开发模型。

本阶段不是新一轮 dev tuning。

本阶段不允许根据 test 结果调整任何 confirmatory 方法。

---

## 2. 两级人工阶段门

A1.10 必须拆成两个不可合并的子阶段：

```text
A1.10a
Blind Test Inference & Prediction Freeze

人工审查

A1.10b
One-time Label Unlock & Final Scoring
```

当前首次执行 A1.10 时：

```text
只授权 A1.10a
```

A1.10a 完成后必须停止，并返回：

```text
READY_FOR_TEST_LABEL_UNLOCK_REVIEW
```

只有研究负责人再次明确授权：

```text
AUTHORIZE A1.10b TEST LABEL UNLOCK
```

才能执行 A1.10b。

不得因为 A1.10a 技术通过而自动进入 A1.10b。

---

## 3. 固定数据与模型版本

继续固定官方数据：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

Side Effect embedding 模型继续固定：

```text
Qwen/Qwen3-Embedding-0.6B

immutable revision:
97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3

model.safetensors SHA-256:
0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd
```

不得升级、替换或重新选择模型 revision。

---

## 4. A1.9 冻结状态必须先核验

A1.10a 打开任何 test content 前，必须核验：

```text
A1.9 stage determination = PASS_WITH_CONDITIONS
```

并读取至少：

```text
research/01_DECISION_LOG.md

docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/evaluation_protocol.md

docs/stage_a1_9_final_method_freeze_report.md

artifacts/a1_9_run_summary.json
artifacts/a1_9_final_model_manifest.json
artifacts/a1_9_final_claim_freeze.csv
artifacts/a1_9_test_preregistration.json

artifacts/final_models/final_success_b2.joblib
artifacts/final_models/final_looping_b2.joblib
artifacts/final_models/final_side_effect_b4.joblib

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
requirements/baseline-lock.txt
requirements/semantic-lock.txt
```

若精确路径不同，只允许通过 A1.9 正式 machine summary / manifest 解析。

不得使用：

```text
临时模型
旧模型
失败模型
未提交模型
alternate model
```

---

## 5. A1.10 开始前 Git gate

任何 test 内容访问前：

```text
git status --porcelain
```

必须为空。

同时记录：

```text
current branch
HEAD commit
A1.9a commit
A1.9b commit
A1.9 model manifest hash
A1.9 test preregistration hash
A1.9 final claim freeze hash
```

如果 working tree 不 clean：

```text
STOP
```

不得先打开 test 再清理。

---

## 6. Final methods 已永久冻结

### 6.1 Success

```text
method_id = FINAL_SUCCESS_B2
role = confirmatory_primary
model family = structural Logistic Regression
input = frozen full 13-feature structural representation
pipeline = StandardScaler + LogisticRegression

C = 10
class_weight = balanced
threshold = 0.55
```

A1.9 final OOF：

```text
AP = 0.546543
F1 = 0.661290
```

Model SHA-256：

```text
afbdb0a60205d7c6bd40232a8c8a1b1ad3b0910d6b65fecf894cca1a040123c1
```

---

### 6.2 Looping

```text
method_id = FINAL_LOOPING_B2
role = confirmatory_primary
model family = structural Logistic Regression
input = frozen full 13-feature structural representation
pipeline = StandardScaler + LogisticRegression

C = 1
class_weight = balanced
threshold = 0.55
```

A1.9 final OOF：

```text
AP = 0.914081
F1 = 0.910995
```

Model SHA-256：

```text
862b7ff2b0cbcb5faf88908f5fe5824c7f4e52c2c21521e41bb5fb71b011660c
```

---

### 6.3 Side Effect

```text
method_id = FINAL_SIDE_EFFECT_B4
role = exploratory_only
confirmatory_eligible = false

model family =
Qwen3 frozen dense trajectory embedding
+
Logistic Regression

NO StandardScaler

C = 10
class_weight = balanced
threshold = 0.40
```

A1.9 final OOF：

```text
AP = 0.189878
F1 = 0.325581
```

Model SHA-256：

```text
5eb29646c10a8193b8492ffe26a41a63414dc9da884890813273c43d17a7de59
```

无论 final test 结果多高：

```text
Side Effect role 永远 = exploratory_only
```

不得升级。

---

## 7. Final model hash guard

打开 test content 前必须独立重新计算：

```text
final_success_b2.joblib SHA-256
final_looping_b2.joblib SHA-256
final_side_effect_b4.joblib SHA-256
```

必须与第 6 节完全一致。

任一 hash mismatch：

```text
STOP
```

不得 reload 后重新保存。

不得重新 fit。

不得创建“等价替代模型”。

---

## 8. A1.10a 绝对边界

A1.10a 允许访问：

```text
test identifiers
test raw trajectory content
不含 outcome 的必要 benchmark/task/model metadata
```

A1.10a 允许生成：

```text
test primary cleaned input
test B2 structural features
test B4 frozen embeddings
test blind probabilities
test frozen-threshold predicted labels
blind prediction artifacts
hashes
integrity reports
```

A1.10a 仍然绝对禁止读取：

```text
test annotation
test Success label
test Side Effect label
test Looping label
test eligibility
test judge output
test outcome/reward-derived target information
test metrics
```

A1.10a 禁止：

```text
AP
F1
AP lift
ROC-AUC
bootstrap
任何与真实 label 相关的诊断
```

---

## 9. Test access counters

A1.10a 开始前：

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

A1.10a 完成时允许：

```text
manifest > 0
content > 0
features > 0
embeddings > 0
predictions > 0
```

但必须保持：

```text
labels = 0
eligibility = 0
metrics = 0
```

任何 A1.10a label / eligibility / metric access：

```text
STOP
FINAL TEST CONTAMINATION REVIEW REQUIRED
```

不得自行继续。

---

## 10. Identifier-only manifest 首次开封

A1.10a 首先只建立 official test identifier universe。

A0.2 的 prior provenance 是：

```text
1106 official test trajectories
```

但在 A1.10a 实际确认前：

> 1106 只能视为 prior count，不得直接当作本次 observed count。

必须检查：

1. test trajectory identifier 总数；
2. unique trajectory identifier 总数；
3. duplicate identifier 数；
4. benchmark_original 分布；
5. benchmark_group_primary 分布；
6. normalized_task_id / task-group 分布；
7. model_name 分布；
8. raw trajectory mapping 覆盖；
9. identifier → raw content 映射唯一性。

如果本次实际 frozen manifest 仍为：

```text
1106 trajectories
```

则预期：

```text
3 × 1106 = 3318 blind prediction rows
```

如果 count 与 A0.2 provenance 冲突：

```text
STOP
```

先报告差异。

不得自行：

```text
删轨迹
补轨迹
重定义 test universe
```

---

## 11. A1.10a input 构建

必须使用 A0.4 / A1.0 已冻结的 trajectory cleaning / whitelist 规则。

允许字段仍限定为已冻结 input contract。

必须继续排除：

```text
summary_info
cum_reward
cum_raw_reward
reward
score
label
judge
annotation
success
failure
side effect
looping
任何结果语义字段
截图/图像相关字段
未知未白名单字段
```

不得因为 test 某字段缺失而使用：

```text
reward
label
最后一步结果
人工判断
```

补推字段。

---

## 12. Success / Looping test B2 feature extraction

Success 与 Looping 必须复用 A1.2 冻结的同一结构 feature extractor。

13 个 feature 顺序固定：

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

要求：

```text
feature count = 13
feature order exact match
missing semantics 与 dev 一致
terminal semantics 与 dev 一致
error semantics 与 dev 一致
```

不得：

```text
增加 feature
删除 feature
改 feature 定义
改 feature 顺序
test-only normalization
label-guided repair
```

---

## 13. Side Effect test B4 embedding extraction

A1.10a 必须按照 A1.7 已冻结的 semantic extraction contract，对 official test raw trajectory content 生成 test embeddings。

固定：

```text
Qwen/Qwen3-Embedding-0.6B
revision =
97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3

weight SHA-256 =
0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd
```

必须原样复用 A1.7：

```text
tokenizer
serialization
chunking
truncation
pooling
embedding dimensionality
normalization（若 A1.7 contract 有）
batch inference semantics
```

test embedding dimensionality 必须：

```text
1024
```

允许：

```text
为 official test 执行一次冻结规则下的 Qwen forward
```

禁止：

```text
重新生成 dev embedding
改变 Qwen revision
改变权重
改变 tokenizer
改变 serialization
改变 chunk size
改变 overlap
改变 pooling
改变 normalization
第二 embedding 模型
embedding ensemble
fusion
```

如果 A1.7 的正式 extraction contract 无法唯一复现：

```text
STOP
```

不得根据 test 表现选择一种实现。

---

## 14. A1.10a 禁止任何 estimator fit

A1.10a 必须：

```text
estimator fits = 0
```

只能：

```text
load frozen joblib
transform
predict_proba
apply frozen threshold
```

不得：

```text
.fit()
.partial_fit()
calibration fit
threshold fit
scaler refit
```

Success/Looping 的 `StandardScaler` 必须来自 frozen joblib pipeline。

不得在 test 上重新 fit scaler。

---

## 15. Blind prediction schema

对每条 official test trajectory、每个 target，生成一行。

至少包含：

```text
trajectory_key
benchmark_original
benchmark_group_primary
normalized_task_id
model_name

target
method_id
role
model_sha256

probability
frozen_threshold
predicted_label

row_key
inference_status
```

其中：

```text
row_key = deterministic unique key
```

Blind artifact 绝对不得包含：

```text
true_label
eligibility
annotation
judge result
reward
metric
```

---

## 16. Blind prediction 完整性

如果 identifier manifest 确认为 1106：

```text
Success = 1106 rows
Looping = 1106 rows
Side Effect = 1106 rows
Total = 3318 rows
```

否则使用本次已核验的实际 trajectory count：

```text
Total = 3 × observed_test_trajectory_count
```

必须验证：

1. 每 `(trajectory_key, target)` 恰好一行；
2. 无 duplicate row_key；
3. 无 missing probability；
4. probability 全部 finite；
5. probability ∈ [0,1]；
6. threshold：
   - Success = 0.55；
   - Looping = 0.55；
   - Side Effect = 0.40；
7. predicted_label 与 frozen threshold 机械一致；
8. method_id 与 target 对应正确；
9. model SHA 与 A1.9 一致；
10. blind artifact 无 label / eligibility 字段。

任一失败：

```text
STOP
```

不得先开 label 再调查。

---

## 17. A1.10a 必须生成的正式 artifacts

建议生成：

```text
artifacts/a1_10a_test_identifier_manifest.csv
artifacts/a1_10a_test_structural_features.csv
artifacts/a1_10a_test_qwen3_embedding_0p6b.npy
artifacts/a1_10a_test_embedding_index.csv

artifacts/a1_10a_blind_predictions.csv
artifacts/a1_10a_blind_prediction_manifest.json
artifacts/a1_10a_run_summary.json

docs/stage_a1_10a_blind_test_inference_report.md
```

如果仓库已有更严格一致的命名约定，可按既有约定调整路径，但不得改变科学内容。

Machine manifest 至少记录：

```text
data revision
A1.9 commits
A1.9 preregistration hash
claim freeze hash
3 final model hashes
test identifier manifest hash
test feature hash
test embedding hash
blind prediction hash
observed trajectory count
prediction row count
thresholds
test access counters
prohibited experiment counters
runtime environment
warnings
```

---

## 18. Blind prediction hash freeze

A1.10a 必须对以下关键产物计算 SHA-256：

```text
test identifier manifest
test structural features
test embedding artifact
blind prediction artifact
blind prediction manifest
```

其中最关键的是：

```text
blind prediction SHA-256
```

该 hash 一旦进入正式 commit：

> A1.10b 只能读取这份 frozen blind prediction，不得重算后替换。

---

## 19. A1.10a 独立复核

在 commit 前至少验证：

### Provenance

1. A1.9a commit 正确；
2. A1.9b commit 正确；
3. A1.8 claim matrix SHA 正确；
4. data commit/revision 正确；
5. Qwen revision/weight hash 正确。

### Models

6. Success model hash 正确；
7. Looping model hash 正确；
8. Side Effect model hash 正确；
9. 三模型均可 reload；
10. estimator fit count = 0。

### Inputs

11. test identifier 唯一；
12. raw mapping 完整；
13. B2 feature schema = frozen 13；
14. B4 embedding dim = 1024；
15. 无泄漏字段进入 input。

### Predictions

16. 每 trajectory × target 一行；
17. row_key 唯一；
18. probability 合法；
19. thresholds 完全冻结；
20. blind predictions 无 labels；
21. blind predictions 无 eligibility；
22. prediction SHA 已记录。

### Boundaries

23. label access = 0；
24. eligibility access = 0；
25. metric access = 0；
26. threshold tuning = 0；
27. model fit = 0；
28. calibration = 0；
29. fusion = 0；
30. second embedding = 0；
31. LLM Judge = 0。

---

## 20. A1.10a commit

A1.10a 所有 blind artifacts 与正式报告完成后提交：

```text
experiment: freeze blind official test predictions
```

不得 amend A1.9 commits。

若在 A1.10a commit 前发现 implementation bug：

- 可以修复；
- 必须保留 bug/fix provenance；
- 若 bug 发生在未访问 labels 的 blind inference 内，可独立 fix commit 后从 frozen raw test inputs 重新生成 blind predictions；
- label / eligibility 必须仍保持 0。

如果 label/eligibility 已被访问，则不适用普通 fix：

```text
STOP + contamination review
```

---

## 21. A1.10a 最终 Git gate

提交后：

```text
git status --porcelain
```

必须为空。

记录：

```text
A1.10a commit SHA
blind prediction SHA-256
identifier manifest SHA-256
test feature SHA-256
test embedding SHA-256
```

成功状态：

```text
READY_FOR_TEST_LABEL_UNLOCK_REVIEW
```

随后立即停止。

不得自动执行 A1.10b。

---

# A1.10b：One-time Label Unlock & Final Scoring

## 22. A1.10b 人工授权

只有收到研究负责人明确指令：

```text
AUTHORIZE A1.10b TEST LABEL UNLOCK
```

才能继续。

任何近似表达如果存在歧义：

```text
STOP
```

不得默认授权。

---

## 23. A1.10b pre-unlock guard

第一次读取 labels / eligibility 前必须重新验证：

1. A1.10a commit 存在；
2. A1.10a blind prediction SHA 与 committed blob 一致；
3. working tree clean；
4. 三个 final model hashes 未变化；
5. thresholds 未变化；
6. test feature / embedding hashes 未变化；
7. blind prediction artifact 在 A1.10a commit 后未变化；
8. A1.10a report 明确：
   - labels=0；
   - eligibility=0；
   - metrics=0。

任一失败：

```text
STOP
```

不得解锁 labels。

---

## 24. One-time labels / eligibility unlock

通过第 23 节 gate 后，首次允许读取：

```text
official test labels
official test eligibility
```

解锁后只允许：

```text
join
filter by frozen eligibility
score
bootstrap
report
```

不得覆盖：

```text
blind probabilities
blind predicted labels
blind thresholds
blind feature/embedding artifacts
```

---

## 25. Join 规则

只允许通过冻结 identifier：

```text
trajectory_key
```

或 A1.9/A0.x 已正式冻结的等价唯一 key join。

必须验证：

1. blind prediction row 有且仅有一个匹配 label row；
2. 无 duplicate prediction；
3. 无 duplicate target label；
4. 无 silent drop；
5. unmatched prediction count；
6. unmatched label count；
7. target-specific eligibility count；
8. benchmark/task-group 字段一致。

任何 join ambiguity：

```text
STOP
```

不得用人工猜测修补。

---

## 26. Eligibility

正式评分只使用冻结：

```text
<target>_eligible_main
```

不得根据 test 表现：

```text
删轨迹
改 eligibility
改 unsure handling
改 duplicate annotation policy
```

必须报告每个 target：

```text
eligible N
positive N
negative N
prevalence
task-group N
benchmark distribution
```

---

## 27. Final test primary metrics

### Success / Looping

Primary point metrics 固定：

```text
pooled Average Precision
pooled AP lift = AP - test prevalence
positive-class F1 at frozen dev threshold
```

Frozen thresholds：

```text
Success = 0.55
Looping = 0.55
```

Primary uncertainty：

```text
pooled AP lift 95% task-group cluster bootstrap CI
```

Secondary descriptive metrics 可按 A1.9 preregistration 计算：

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

但 secondary metrics：

```text
不得改变 confirmatory grade
```

---

## 28. Side Effect final test

Side Effect 使用：

```text
FINAL_SIDE_EFFECT_B4
threshold = 0.40
```

可计算预注册指标与不确定性。

但正式角色固定：

```text
EXPLORATORY_TEST_RESULT
```

即使：

```text
AP 很高
AP lift CI > 0
F1 很高
```

也不得升级成：

```text
CONFIRMED_HELDOUT_SIGNAL
confirmatory_primary
```

---

## 29. Frozen bootstrap

Success / Looping primary uncertainty 固定：

```text
n_draws = 10000
seed = 2027
rng = numpy.random.Generator(
    numpy.random.PCG64(2027)
)

CI = percentile 95%
```

Resampling unit：

```text
group_key =
(benchmark_original, normalized_task_id)
```

Sampling：

```text
within benchmark_group_primary strata
cluster bootstrap task groups with replacement
```

同一 task group 下所有 model trajectories 必须一起复制。

禁止：

```text
trajectory-level bootstrap
label stratification
按结果重新定义 strata
invalid draw 后补抽
改变 seed
改变 draws
```

不得为了得到显著结果修改 bootstrap。

---

## 30. Confirmatory grading rule

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
pooled AP lift point > 0
但 95% CI 包含或触及 0
```

则：

```text
DIRECTIONAL_BUT_NOT_CONFIRMED
```

若：

```text
pooled AP lift point <= 0
```

则：

```text
NOT_CONFIRMED
```

必须机械执行。

不得根据：

```text
F1 很高
某个 Benchmark 很高
macro 很高
ROC-AUC 很高
```

改变 grade。

---

## 31. Final claim 边界

A1.10 允许最终确认的核心 claim 只有：

### FC1 Success

> 冻结的 B2 structural classifier 在完全未参与方法选择的 official held-out test tasks/trajectories 上是否保留预测信号。

### FC2 Looping

> 冻结的 B2 structural classifier 在完全未参与方法选择的 official held-out test tasks/trajectories 上是否保留预测信号。

A1.10 不得自动升级以下 dev-only claims：

```text
B2 稳定优于 B3
B4 稳定优于 B2/B3
termination 是 Success 机制
repetition 是 Looping 的全部机制
A1.4 model-only transfer = joint task+model OOD
复杂模型一定更好
representation complexity hierarchy
new Benchmark generalization
new dataset transfer
```

Official test 若仍来自相同 benchmark families：

> A1.10 是 official held-out task/trajectory confirmation，不是 unseen-Benchmark generalization。

---

## 32. Labels 解锁后的永久禁止事项

从 A1.10b 第一次 label unlock 开始，永久禁止为了改善 final result：

```text
改 threshold
改 C
改 class_weight
改 model
改 structural feature
改 feature order
改 Qwen revision
改 tokenizer
改 serialization
改 chunking
改 pooling
改 embedding normalization
重新生成“更好”的 test embedding
加入 calibration
加入 fusion
加入第二 embedding
加入 LLM Judge
改 eligibility
删不利 Benchmark
删不利 trajectory
改 primary metric
改 bootstrap
改 success criterion
```

如果 final test 不理想：

> 如实报告。

不得 tuning 后再次把相同 official test 当 confirmatory test。

---

## 33. A1.10b 输出 artifacts

建议生成：

```text
artifacts/a1_10_test_scored_predictions.csv
artifacts/a1_10_target_metrics.csv
artifacts/a1_10_benchmark_metrics.csv
artifacts/a1_10_bootstrap_summary.csv
artifacts/a1_10_confirmatory_grade.csv
artifacts/a1_10_final_claim_status.csv
artifacts/a1_10_run_summary.json

docs/stage_a1_10_official_test_evaluation_report.md
```

blind artifact 必须继续保留，不得覆盖：

```text
artifacts/a1_10a_blind_predictions.csv
```

---

## 34. A1.10b commit

A1.10b 完成后独立提交：

```text
analysis: score frozen blind official test predictions
```

不得 amend A1.10a。

不得 squash A1.10a 与 A1.10b，使 blind-before-label provenance 消失。

提交后：

```text
git status --porcelain
```

必须为空。

---

## 35. A1.10 异常处理

### A. Pre-test guard failure

若 test content 打开前发现：

```text
dirty Git
model hash mismatch
data revision mismatch
Qwen revision/hash mismatch
A1.9 preregistration mismatch
claim freeze mismatch
```

立即：

```text
STOP
```

不得打开 test。

---

### B. A1.10a identifier conflict

若 observed test count / mapping 与 frozen provenance 冲突：

```text
STOP
```

报告：

```text
expected
observed
difference
affected identifiers
```

不得自行改 test universe。

---

### C. A1.10a implementation error before labels

若 labels/eligibility 从未访问，可以：

1. 保留失败日志；
2. 独立 fix commit；
3. 重新执行完整 blind inference；
4. 重新冻结 blind prediction hash；
5. test labels/eligibility/metrics 继续保持 0。

不得选择性只重跑表现“异常”的 target，因为没有 label 可判断表现。

---

### D. A1.10a accidental label access

任何 A1.10a label / eligibility access：

```text
STOP
FINAL TEST CONTAMINATION REVIEW REQUIRED
```

不得自行继续 A1.10b。

---

### E. A1.10b join failure

label unlock 后若：

```text
join ambiguity
duplicate label
missing prediction
eligibility mismatch
```

立即停止评分。

允许做纯数据完整性审计。

不得重算模型预测来“修复结果”。

---

### F. A1.10b scoring implementation bug

如果 blind predictions 未改变，且 bug 只存在于：

```text
join
metric calculation
bootstrap implementation
reporting
```

则：

- 保留原始失败日志；
- 独立 fix commit；
- 只能从 frozen blind predictions + frozen labels/eligibility 重新 scoring；
- 不得重新 inference；
- 不得改 protocol。

如果修复需要改变已冻结 metric/bootstrap 定义：

```text
STOP
```

人工审查。

---

## 36. A1.10a 阶段判定

A1.10a 最终只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS / PASS_WITH_CONDITIONS 技术必要条件

必须全部满足：

1. A1.9 commits 已核验；
2. A1.9 model hashes 全部一致；
3. A1.9 preregistration / claim freeze hash 一致；
4. Git 在 test opening 前 clean；
5. identifier-only manifest 已核验；
6. test raw mapping 完整；
7. B2 13-feature schema 完全冻结；
8. B4 使用冻结 Qwen extraction contract；
9. estimator fits = 0；
10. blind predictions 完整；
11. thresholds 完全冻结；
12. blind artifact 无 label；
13. blind artifact 无 eligibility；
14. blind prediction hash 已冻结；
15. labels access = 0；
16. eligibility access = 0；
17. metrics access = 0；
18. 禁止实验 = 0；
19. A1.10a 独立 commit；
20. Git 最终 clean；
21. 明确停止，不执行 A1.10b。

成功后状态：

```text
READY_FOR_TEST_LABEL_UNLOCK_REVIEW
```

### STOP 包括

- frozen hash mismatch；
- test universe 冲突；
- input contract 无法复现；
- Qwen frozen extraction 无法复现；
- estimator 被重新 fit；
- threshold 被修改；
- blind predictions 不完整；
- label/eligibility 被提前访问；
- Git provenance 无法建立。

---

## 37. A1.10b 阶段判定

A1.10b 完成后：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

技术 PASS 不等于 scientific claim 必须 confirmed。

例如完全合法的结果可以是：

```text
A1.10 technical PASS

Success = NOT_CONFIRMED
Looping = CONFIRMED_HELDOUT_SIGNAL
Side Effect = EXPLORATORY_TEST_RESULT
```

也可以：

```text
Success = NOT_CONFIRMED
Looping = NOT_CONFIRMED
```

只要 protocol 完整，A1.10 仍可技术 PASS。

不得把 scientific negative result 误判为 implementation failure。

---

## 38. A1.10a 正式报告

生成：

```text
docs/stage_a1_10a_blind_test_inference_report.md
```

至少包含：

1. 阶段判定；
2. A1.10a commit；
3. A1.9a/A1.9b provenance；
4. data revision；
5. Qwen revision/hash；
6. 3 final model hashes；
7. test identifier observed count；
8. benchmark/task-group/model distribution；
9. raw trajectory coverage；
10. B2 test feature count/schema；
11. B4 test embedding count/dim；
12. blind prediction row counts；
13. thresholds；
14. blind prediction SHA；
15. identifier/features/embedding SHA；
16. estimator fit count=0；
17. labels access=0；
18. eligibility access=0；
19. metrics access=0；
20. prohibited experiments=0；
21. warnings；
22. tests/verifiers；
23. Git clean；
24. `READY_FOR_TEST_LABEL_UNLOCK_REVIEW`；
25. 明确停止等待人工审查。

---

## 39. A1.10 最终正式报告

A1.10b 完成后生成：

```text
docs/stage_a1_10_official_test_evaluation_report.md
```

至少包含：

1. 阶段判定；
2. A1.10a/A1.10b commits；
3. blind-before-label provenance；
4. blind prediction SHA；
5. label unlock 时间点/commit state；
6. join integrity；
7. Success eligible N / positives / prevalence；
8. Looping eligible N / positives / prevalence；
9. Side Effect eligible N / positives / prevalence；
10. Success pooled AP；
11. Success AP lift；
12. Success frozen-threshold F1；
13. Success AP-lift 95% CI；
14. Success final grade；
15. Looping pooled AP；
16. Looping AP lift；
17. Looping frozen-threshold F1；
18. Looping AP-lift 95% CI；
19. Looping final grade；
20. Side Effect exploratory metrics；
21. Side Effect `EXPLORATORY_TEST_RESULT`；
22. bootstrap protocol完整性；
23. per-Benchmark / macro descriptive results；
24. FC1/FC2/FE1 final claim status；
25. dev-only claims 未升级；
26. test 后无 tuning；
27. warnings；
28. tests/verifiers；
29. Git clean；
30. 后续是否进入论文整合/外部验证阶段由人工决定。

---

## 40. A1.10a 最终汇报

Codex 在当前首次执行时必须最终汇报：

1. 阶段判定；
2. A1.10a commit；
3. 是否有 fix commit；
4. 是否 amend；
5. A1.9a/A1.9b hash 核验；
6. A1.8 claim matrix SHA 核验；
7. data revision 核验；
8. Qwen revision/weight hash 核验；
9. Success model hash；
10. Looping model hash；
11. Side Effect model hash；
12. observed test trajectory count；
13. expected/actual blind prediction rows；
14. benchmark/task-group/model coverage；
15. duplicate/missing identifier；
16. B2 feature schema；
17. B4 embedding rows/dim；
18. estimator fits=0；
19. Success threshold=0.55；
20. Looping threshold=0.55；
21. Side Effect threshold=0.40；
22. blind prediction SHA；
23. identifier manifest SHA；
24. feature SHA；
25. embedding SHA；
26. labels access=0；
27. eligibility access=0；
28. metrics access=0；
29. prohibited experiments=0；
30. warnings；
31. tests/verifiers；
32. Git status；
33. report/summary paths；
34. 最终状态：

```text
READY_FOR_TEST_LABEL_UNLOCK_REVIEW
```

完成后立即停止。

**绝对不得自动执行 A1.10b。**

---

## 41. A1.10b 最终汇报

只有第二次人工授权后才使用。

Codex 最终必须汇报：

1. A1.10b authorization；
2. A1.10a blind SHA 再核验；
3. pre-unlock Git clean；
4. label/eligibility unlock 已发生；
5. blind predictions 未改变；
6. join integrity；
7. 三个 target eligible counts；
8. 三个 target prevalence；
9. Success AP/AP lift/F1；
10. Success bootstrap CI；
11. Success grade；
12. Looping AP/AP lift/F1；
13. Looping bootstrap CI；
14. Looping grade；
15. Side Effect exploratory metrics；
16. Side Effect role 仍 exploratory-only；
17. bootstrap draws=10000；
18. PCG64 seed=2027；
19. within-benchmark task-group cluster bootstrap；
20. no label stratification；
21. no invalid redraw；
22. dev-only claims 未升级；
23. post-unlock tuning=0；
24. tests/verifiers；
25. A1.10b commit；
26. Git clean；
27. final report / machine summary paths；
28. final claim table。

完成后立即停止。

不得自动进入 A1.11。
