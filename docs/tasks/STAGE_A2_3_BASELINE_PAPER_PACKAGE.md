# Stage A2.3：Baseline Completeness、Paper Tables 与 Publication Story Freeze

## 1. 阶段定位

Stage A2.2 已完成：

```text
PASS_WITH_CONDITIONS
WAIT_FOR_HUMAN_A2_2_REVIEW
```

A2.3 是 Stage A2 最后一个 publication-completion 子阶段。

本轮**不做新模型实验**。唯一目标：

> 将 A1 + A2.1 + A2.2 已冻结的证据整理成一套可直接进入论文写作和 A3 artifact freeze 的“论文结果包”。

完成后必须：

```text
STOP
WAIT_FOR_HUMAN_A2_3_REVIEW
```

不得自动执行 A3、external validation 或完整 manuscript 写作。

---

## 2. 本阶段只回答四个问题

1. 当前论文已经覆盖哪些 baseline / representation / robustness setting？
2. 哪些结果进入正文、附录、discussion 或 limitation？
3. 如何把 predictive signal → robustness → blind test → efficiency → interpretability 串成完整论文故事？
4. external validation 现在应 `DO_NOW`、`DEFER_TO_REVISION` 还是 `NOT_WORTH_COST`？

---

## 3. 科研身份

A2.3 仅属于：

```text
EVIDENCE_CONSOLIDATION
PAPER_ARTIFACT_PREPARATION
CLAIM_MAPPING
```

不是：

```text
new experiment
new model selection
new confirmatory test
new statistical discovery
```

---

## 4. Frozen hard gates

开始前必须核验：

```text
git status --porcelain
```

必须为空。

核验：

```text
artifacts/a1_11_final_claim_matrix.csv
SHA-256 =
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

```text
artifacts/a1_11_table_main_test_results.csv
SHA-256 =
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

Commit 必须可解析：

```text
A2.1 result =
b4e4a6ab95d8191f1bef91dab9844bef48f00a8d

A2.2 result =
a57befbb027d2544d32e3e0cde906c2edf13d385
```

Frozen claim identities 必须仍为：

```text
FC1 Success = CONFIRMATORY_SUPPORTED
FC2 Looping = CONFIRMATORY_SUPPORTED
FE1 Side Effect = EXPLORATORY_SUPPORTED
```

任一不一致：

```text
STOP
```

---

## 5. Preregistration gate

如果：

```text
docs/tasks/STAGE_A2_3_BASELINE_PAPER_PACKAGE.md
```

尚未被 Git 跟踪：

```text
STOP
```

只允许创建独立 docs-only prereg commit：

```text
chore: preregister A2.3 paper evidence package
```

然后结束本轮。

不得 prereg 后继续执行。

---

# Part I — Baseline Completeness Audit

## 6. 必须审计的方法

至少包括：

```text
B0
B1
B2
B3
B4
S0
S1
S2
S3
S4
S5
S6
```

如仓库存在其他正式 A1 baseline，也必须纳入。

**方法定义必须从 frozen repository artifacts 读取，不得凭记忆填写。**

---

## 7. Baseline hierarchy

映射为：

```text
Tier 0 — trivial / minimal control
Tier 1 — lightweight structural
Tier 2 — alternative lightweight / text representation
Tier 3 — dense semantic representation
Tier 4 — published external evaluator context
```

Tier 4 不是本项目 head-to-head experiment。

本阶段不允许 Codex 自行从互联网抓取未经人工核验的论文数字。

若本地没有可靠数字：

```text
needs_literature_verification = true
```

不得猜测、不得跨不同 split 做直接性能优劣结论。

---

## 8. Baseline completeness matrix

生成：

```text
artifacts/a2_3_baseline_completeness_matrix.csv
```

至少字段：

```text
method_id
method_name
tier
representation_type
feature_or_embedding_dim
classifier_or_evaluator
semantic_encoder
dev_evaluated
grouped_cv
lobo_evaluated
leave_one_model_out
ablation_role
uncertainty_available
official_test_role
final_method_role
target_scope
evidence_status
source_stage
source_artifact
paper_role
notes
```

不得创建新的 confirmatory status。

---

# Part II — Evidence-to-Paper Mapping

## 9. 生成

```text
artifacts/a2_3_evidence_to_paper_map.csv
```

每条 evidence 必须映射到：

```text
MAIN_TEXT
APPENDIX
DISCUSSION_ONLY
LIMITATION_ONLY
DO_NOT_USE
```

字段至少：

```text
evidence_id
claim_or_result
target
source_stage
source_artifact
evidence_status
recommended_location
recommended_table_or_figure
allowed_wording
forbidden_wording
reason
```

---

## 10. 正文结果顺序

冻结为：

```text
R1 Held-out predictive evidence
R2 Development robustness / representation evidence
R3 Efficiency
R4 Interpretability / confounder / failure boundaries
```

Target priority：

```text
Success = primary
Looping = strong supporting target
Side Effect = exploratory / secondary
```

---

# Part III — Paper-ready Tables

## 11. Table 1：Main Held-out Results

生成：

```text
artifacts/a2_3_table_1_main_heldout_results.csv
```

必须从 A1.11 frozen table **exact join**，不得重新计算。

至少：

```text
target
final_method
eligible_n
positive_n
negative_n
prevalence
AP
AP_lift
F1
AP_lift_CI_low
AP_lift_CI_high
claim_status
scope
```

---

## 12. Table 2：Efficiency / Complexity

生成：

```text
artifacts/a2_3_table_2_efficiency_tradeoff.csv
```

从 A2.1 exact join：

```text
method
dimension
device
cold_start
extraction_ms_per_trajectory
inference_ms_per_trajectory
representation_size
classifier_size
encoder_size
peak_cpu_rss
peak_gpu_vram
relative_cost
environment_specific
```

必须：

```text
environment_specific = true
```

禁止把 Success B2 test AP 与 Side Effect B4 test AP 拼成同-target accuracy-efficiency comparison。

---

## 13. Table 3：Dev Representation / Robustness

生成：

```text
artifacts/a2_3_table_3_dev_representation_summary.csv
```

只整理 A1.2–A1.7 frozen evidence，例如：

```text
target
method
representation
grouped_dev_AP
grouped_dev_F1
LOBO_summary
model_transfer_summary
uncertainty_summary
evidence_status
source
```

不得重跑实验。

---

## 14. Table 4：Benchmark Heterogeneity

生成：

```text
artifacts/a2_3_table_4_benchmark_heterogeneity.csv
```

从 A1.10/A1.11 frozen benchmark table exact join。

全部保持：

```text
DESCRIPTIVE_ONLY
```

禁止 benchmark 间显著优劣表述。

---

## 15. Table 5：Interpretability / Failure Summary

生成：

```text
artifacts/a2_3_table_5_interpretability_error_summary.csv
```

来源：

```text
A2.2 coefficients
A1.5/A1.6 feature-group synthesis
A2.2 metadata baseline
A2.2 deterministic error analysis
```

建议字段：

```text
target
top_structural_signals
metadata_AP
metadata_AP_lift
frozen_B2_dev_AP
main_failure_modes
main_interpretation
evidence_status
```

不得把 coefficient 当 causal importance。

---

# Part IV — Figure Specification

## 16. 只冻结图规格，不生成最终 publication figures

生成：

```text
docs/a2_3_publication_figure_spec.md
```

正文最多 5 张候选：

```text
Fig 1 — Study / evaluation pipeline
Fig 2 — Official held-out AP lift + 95% CI
Fig 3 — Efficiency / representation complexity
Fig 4 — Structural interpretation
Fig 5 — Error taxonomy OR benchmark heterogeneity
```

另一张可放 appendix。

每张图必须写清：

```text
source artifacts
exact fields
evidence status
axes / labels
caption boundaries
prohibited interpretation
```

---

# Part V — Publication Story Freeze

## 17. 生成

```text
docs/a2_3_publication_results_story.md
```

这不是完整 manuscript。

必须包含：

1. 3–5 个 title candidates；
2. one-sentence problem；
3. one-sentence main finding；
4. 3–4 条 contributions；
5. RQ1–RQ6；
6. Results section 顺序；
7. main tables；
8. main figures；
9. allowed claims；
10. prohibited claims；
11. limitations；
12. appendix plan；
13. remaining work。

---

## 18. 推荐核心 story

必须以 frozen evidence 为依据，允许大意为：

> We systematically investigate how far lightweight, task-agnostic structural signals can support web-agent trajectory evaluation. Structural representations retain confirmatory held-out predictive signal for Success and Looping on official held-out tasks within the evaluated benchmark families, while being substantially cheaper to construct than dense semantic embeddings under the measured environment. Post-freeze diagnostics show that benchmark/model metadata contains some signal but does not descriptively account for the full B2 performance, and deterministic error cases expose limits where execution morphology diverges from task semantics.

不得扩大 scope。

---

## 19. RQ freeze

```text
RQ1
Do lightweight structural trajectory signals contain predictive information for agent evaluation?

RQ2
How robust are these signals across grouped tasks, benchmarks, and model shifts within the development evidence?

RQ3
Which structural feature groups contribute most consistently?

RQ4
Does dense semantic representation provide stable gains over lightweight structural representation in the studied dev regime?

RQ5
Do frozen structural evaluators retain signal on the official blind held-out test?

RQ6
What are the efficiency advantages, confounding risks, and characteristic failure modes of structural evaluation?
```

不得添加 unseen-benchmark RQ，除非未来独立 stage 真正执行 external validation。

---

# Part VI — Claim Language Freeze

## 20. Allowed

Success / Looping：

```text
confirmatory held-out predictive signal
official held-out tasks/trajectories
within evaluated benchmark families
```

Side Effect：

```text
exploratory
low-support
not confirmatory
```

Efficiency：

```text
under the recorded environment
substantially lower representation/extraction cost
```

Metadata audit：

```text
metadata contains non-trivial signal
B2 is descriptively higher on frozen dev
confounding cannot be fully excluded
```

Error analysis：

```text
illustrates failure modes
shows limits of morphology-only evaluation
```

---

## 21. Prohibited

至少：

```text
unseen-benchmark generalization
arbitrary-agent generalization
joint task/model OOD generalization
universal Agent Judge
universal LLM Judge replacement
causal mechanism
feature X causes Success
dense semantics are generally unnecessary
structural models are universally more efficient
Side Effect confirmed
benchmark pairwise superiority
metadata confounding completely ruled out
B2 significantly beats metadata-only
```

---

# Part VII — Limitations Freeze

## 22. 生成

```text
docs/a2_3_final_limitations_ledger.md
```

至少包含：

1. external validity limited to evaluated benchmark families；
2. Side Effect low support；
3. benchmark heterogeneity；
4. dev-only relative method comparisons；
5. ablations are not causal；
6. coefficient interpretation affected by correlated structural features；
7. metadata confounding not fully ruled out；
8. A2.1 timing environment-specific；
9. structural morphology != semantic task understanding；
10. no calibration / deployment evidence。

必须继承 A1.11 limitations，不得删除旧 limitation 美化论文。

---

# Part VIII — External Validation Decision

## 23. 只做决策，不执行实验

生成：

```text
docs/a2_3_external_validation_decision.md
```

只能：

```text
DO_NOW
DEFER_TO_REVISION
NOT_WORTH_COST
```

### DO_NOW

仅当同时满足：

```text
公开且 revision/license 可固定
trajectory format 可解析
Success label 高度兼容
13-feature extractor 可直接复用或只需轻量 adapter
无需修改 frozen method
预计成本低
不会明显拖延投稿
```

### DEFER_TO_REVISION

适用于：

```text
潜在价值高
但需要新 adapter / label mapping /较大数据处理
当前论文证据已足够形成完整主线
```

### NOT_WORTH_COST

适用于：

```text
label 不兼容
trajectory 不可获得
需要改变研究问题
无法形成公平 external validation
```

文档必须写：

```text
decision
rationale
publication value
implementation cost
scientific risks
reviewer criticism addressed
what it would NOT prove
revisit trigger
```

不得自动下载/运行 external dataset。

---

# Part IX — Publication Package Index

## 24. 生成

```text
artifacts/a2_3_publication_package_index.csv
```

至少字段：

```text
artifact
source_stage
role
evidence_status
paper_location
sha256
verified
```

覆盖：

```text
A1.11 main test
A1.11 benchmark table
A1 dev evidence
A2.1 efficiency
A2.2 coefficients
A2.2 metadata audit
A2.2 error analysis
A2.3 tables
A2.3 story
A2.3 figure spec
A2.3 limitations
external validation decision
```

---

# Part X — Machine Summary / Report

## 25. 输出

```text
artifacts/a2_3_run_summary.json
docs/stage_a2_3_baseline_paper_package_report.md
```

Machine summary 至少记录：

```text
stage_determination
input_commits
input_hashes
output_hashes
baseline_count
table_count
claim_status_counts
external_validation_decision

new_model_fits
new_inference_runs
new_embedding_runs
A1_metric_recomputations
bootstrap_reruns
threshold_changes
eligibility_changes
final_model_changes
official_test_tuning
```

本阶段预期全部科学计算计数为：

```text
new_model_fits = 0
new_inference_runs = 0
new_embedding_runs = 0
A1_metric_recomputations = 0
bootstrap_reruns = 0
threshold_changes = 0
eligibility_changes = 0
final_model_changes = 0
official_test_tuning = 0
```

---

## 26. Tests / verifiers

至少验证：

1. Git start clean；
2. A1.11 claim matrix SHA exact；
3. A1.11 main table SHA exact；
4. A2.1 result reachable；
5. A2.2 result reachable；
6. no new model fit；
7. no inference；
8. no embedding；
9. no A1 metric recomputation；
10. no bootstrap rerun；
11. no threshold/eligibility/final-model changes；
12. Table 1 exact join；
13. Table 2 A2.1 exact join；
14. Table 4 exact benchmark join；
15. A2.2 metadata exact join；
16. A2.2 error counts exact；
17. evidence status preserved；
18. Side Effect still exploratory；
19. benchmark heterogeneity still descriptive；
20. prohibited claims present；
21. package-index hashes valid；
22. summary ↔ outputs consistent。

---

## 27. Commit discipline

### A2.3a — prereg

```text
chore: preregister A2.3 paper evidence package
```

仅 taskbook，然后 STOP。

### A2.3b — implementation

若需要 consolidation script：

```text
chore: implement A2.3 paper package builder
```

### A2.3c — result

```text
analysis: freeze A2 publication evidence package
```

不得 amend。

Fix 必须独立提交并保留 failure provenance。

---

## 28. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

必须满足：

```text
baseline completeness complete
evidence-to-paper map complete
Table 1–5 complete
figure spec complete
publication story complete
limitations ledger complete
external validation decision complete
package index complete

all scientific-operation counters = 0
Git final clean
```

### PASS_WITH_CONDITIONS

允许：

```text
Tier 4 = NEEDS_LITERATURE_VERIFICATION
external validation = DEFER_TO_REVISION
少量 appendix placement 待人工调整
```

不得存在 scientific inconsistency。

### STOP

包括：

```text
frozen hash mismatch
A1/A2 source conflict
new scientific computation detected
claim status upgraded
Side Effect upgraded
benchmark heterogeneity 被推断显著性
external dataset 被自动执行
Git provenance 不清
```

---

## 29. 最终汇报

必须汇报：

```text
阶段判定

A2.3 prereg commit
implementation commit
result commit
fix commits
amend

claim matrix SHA
main test table SHA
A2.1 result verification
A2.2 result verification

baseline count
baseline hierarchy
Tier 4 literature verification status

Table 1 hash
Table 2 hash
Table 3 hash
Table 4 hash
Table 5 hash

MAIN_TEXT evidence count
APPENDIX evidence count
DISCUSSION_ONLY count
LIMITATION_ONLY count
DO_NOT_USE count

title candidates
one-sentence problem
one-sentence finding
contributions
RQ1–RQ6
main figure plan

external validation decision
external validation rationale

limitations count

new_model_fits = 0
new_inference_runs = 0
new_embedding_runs = 0
A1_metric_recomputations = 0
bootstrap_reruns = 0
threshold_changes = 0
eligibility_changes = 0
final_model_changes = 0
official_test_tuning = 0

warnings
tests/verifiers
Git status

report path
machine summary path
publication story path
figure spec path
external validation decision path
package index path

WAIT_FOR_HUMAN_A2_3_REVIEW
```

完成后立即停止。

不得自动执行 A3。
