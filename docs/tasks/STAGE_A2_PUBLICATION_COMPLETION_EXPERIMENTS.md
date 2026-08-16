# Stage A2：Publication Completion Experiments

## 1. 阶段定位

Stage A1.11 已完成：

```text
PASS
READY_FOR_A2_DESIGN_REVIEW
```

A1.11 已冻结：

```text
A0–A1.10 provenance coverage = 17/17
Evidence registry = 90 rows
Final claim matrix = 25 rows
Core inconsistencies = 0
```

Final claim matrix SHA-256：

```text
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

Main test table SHA-256：

```text
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

Stage A2 的唯一目标：

> 以 SCI 二/三区期刊投稿为唯一 KPI，补齐论文最需要的效率证据、解释性、错误分析、混杂控制与 baseline 完整性。

本阶段不是继续寻找新核心结论，不是追求更高 AP，不是模型竞赛。

---

## 2. 论文核心定位

冻结研究问题：

> How far can lightweight, task-agnostic structural signals support web-agent trajectory evaluation?

论文方法逻辑：

```text
Agent trajectory
→ structural representation
→ lightweight evaluator
→ Success / Looping / Side Effect
```

Logistic Regression 只是低容量 measurement model，不作为独立算法创新。

A2 必须服务以下论文贡献：

1. lightweight structural trajectory representation；
2. grouped / cross-domain / ablation / uncertainty 证据；
3. blind official held-out confirmation；
4. representation complexity 与 efficiency tradeoff；
5. interpretability、failure modes 与适用边界。

---

## 3. A1 frozen claims

### FC1 Success

```text
status = CONFIRMATORY_SUPPORTED
AP = 0.654836
AP lift = 0.389567
F1 = 0.682099
95% CI = [0.326806, 0.455411]
scope = official held-out tasks/trajectories within evaluated benchmark families
```

### FC2 Looping

```text
status = CONFIRMATORY_SUPPORTED
AP = 0.921769
AP lift = 0.394829
F1 = 0.876987
95% CI = [0.360965, 0.428598]
scope = official held-out tasks/trajectories within evaluated benchmark families
```

### FE1 Side Effect

```text
status = EXPLORATORY_SUPPORTED
AP = 0.107279
AP lift = 0.042851
F1 = 0.168582
95% CI = [0.021245, 0.079200]
role = exploratory_only
```

A2 不得修改以上身份或 scope。

---

## 4. Pre-stage claim contract gate

开始前必须核验：

```text
artifacts/a1_11_final_claim_matrix.csv
SHA-256 =
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

以及：

```text
artifacts/a1_11_table_main_test_results.csv
SHA-256 =
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

若不一致：

```text
STOP
```

A2 新分析只能标记为：

```text
EFFICIENCY_BENCHMARK
POST_FREEZE_DIAGNOSTIC
POST_FREEZE_DESCRIPTIVE
```

不得创建新的 confirmatory claim。

---

## 5. Git gate

开始前：

```text
git status --porcelain
```

必须为空。

如果本任务书尚未被 Git 跟踪：

```text
STOP
```

先做独立 docs-only preregistration commit。

不得在 dirty tree 上开始 A2。

---

# A2.1 Efficiency & Cost Benchmark

## 6. 目标

回答：

> Structural B2 与 dense semantic B4 在表示维度、特征构建成本、模型大小、运行时间和硬件需求上相差多少？

Accuracy/AP 只能引用 A1 frozen artifacts，不得重新计算 A1.10 test metrics。

---

## 7. 比较对象

### B2 structural

```text
dimension = 13
representation = frozen full structural features
hardware = CPU-capable
```

### B4 dense semantic

```text
dimension = 1024
encoder = Qwen/Qwen3-Embedding-0.6B
revision =
97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3
```

不得换 encoder、tokenizer、chunking、pooling 或 dtype 规则。

---

## 8. Efficiency benchmark 数据

优先使用：

```text
196 frozen dev trajectories
```

原因：

- 四 benchmark 均覆盖；
- 不需要重新碰 official test scientific evaluation；
- 数据量足够做 runtime benchmark；
- 成本可控。

必须复用已冻结 dev cleaned inputs。

不得下载新数据。

---

## 9. Efficiency 测量项

至少记录：

### Representation

```text
dimension
serialized representation size
model artifact size
```

### Structural extraction

```text
total wall time
ms/trajectory
peak process RSS
CPU-only viability
```

### Dense semantic extraction

```text
model load time
warm extraction time
ms/trajectory
peak CPU RSS
peak GPU VRAM
device
batch size
dtype
```

### Classifier inference

```text
total wall time
ms/trajectory
```

只能：

```text
load frozen model
predict_proba
```

不得 fit。

### End-to-end

分开报告：

```text
cold-start
warm extraction + inference
classifier-only after representation
```

不得混淆。

---

## 10. Efficiency 重复规则

B2：

```text
warmup = 1
measured repetitions = 5
```

B4：

```text
warmup = 1
measured repetitions = 3
```

正式结果报告：

```text
median
```

同时保留所有 raw runs。

不得只报告 best run。

---

## 11. Efficiency 环境

必须记录：

```text
OS
Python
CPU
RAM
GPU
CUDA
PyTorch
transformers
NumPy
scikit-learn
thread counts
batch size
dtype
```

B4 GPU benchmark 必须确认：

```text
device = cuda
```

如果实际落在 CPU：

```text
STOP B4 efficiency benchmark
```

---

## 12. A2.1 输出

```text
artifacts/a2_1_efficiency_raw.csv
artifacts/a2_1_efficiency_summary.csv
artifacts/a2_1_efficiency_relative_cost.csv
docs/a2_1_efficiency_report.md
```

relative cost 可计算：

```text
B4/B2 dimension ratio
B4/B2 extraction-time ratio
B4/B2 representation-size ratio
B4/B2 peak-memory ratio
```

性能列只能 join frozen A1 evidence。

---

# A2.2 Interpretability、Error Analysis 与 Confounder Audit

## 13. Feature interpretation

读取 frozen：

```text
FINAL_SUCCESS_B2
FINAL_LOOPING_B2
```

允许读取：

```text
StandardScaler parameters
LogisticRegression coefficients
```

不得 refit。

生成：

```text
artifacts/a2_2_structural_coefficients.csv
```

字段：

```text
target
feature
standardized_coefficient
absolute_rank
sign
feature_group
interpretation_note
```

必须注明：

```text
coefficient != causal effect
```

---

## 14. Feature-group synthesis

只整理：

```text
A1.5 ablation
A1.6 uncertainty
```

已冻结结果。

生成：

```text
artifacts/a2_2_feature_group_evidence.csv
```

结构组：

```text
activity / volume
error
termination
repetition
```

每个 target 记录：

```text
supported dependency
uncertain dependency
CI/support status
allowed interpretation
forbidden causal wording
```

不得重跑 A1.5/A1.6。

---

## 15. Error analysis

使用：

```text
A1.10 frozen scored predictions
```

不得重新 inference。

正文重点：

```text
Success = primary
Looping = secondary
Side Effect = optional
```

Success 与 Looping 各自从：

```text
False Positive
False Negative
```

各选 3 条。

固定选择规则：

```text
E1 = error confidence 最接近 frozen threshold
E2 = error set 中位 confidence
E3 = 离 frozen threshold 最远
```

tie：

```text
trajectory_key lexical order
```

因此核心案例：

```text
Success = 6
Looping = 6
Total = 12
```

不得 cherry-pick。

---

## 16. Error case coding

允许检查 frozen cleaned trajectory 中：

```text
goal
actions
observations
focused_element
natural error
termination
repetition pattern
```

禁止引入泄漏字段。

建议 descriptive categories：

```text
long-but-unsuccessful
short-but-successful
repetitive-but-progressing
non-repetitive failure
explicit-error recovery
termination mismatch
structurally-normal semantic failure
other
unclear
```

生成：

```text
artifacts/a2_2_error_case_manifest.csv
artifacts/a2_2_error_case_notes.csv
docs/a2_2_error_analysis.md
```

Error analysis 只允许：

```text
POST_FREEZE_DESCRIPTIVE
```

不得反向修改模型。

---

## 17. Metadata confounder baseline

新增一个轻量 diagnostic，只在 dev 上执行：

> benchmark/model metadata 在不看 trajectory structure 时，能预测多少？

特征只能：

```text
benchmark_group_primary one-hot
model_name one-hot
```

禁止：

```text
task_id
trajectory_id
structural features
reward/label-derived features
```

模型固定：

```text
LogisticRegression
C = 1
class_weight = balanced
threshold = 0.5
```

使用：

```text
A1.1 frozen grouped folds
```

不允许 C search、threshold tuning、feature selection。

Primary：

```text
pooled AP
```

Secondary：

```text
positive F1 @ 0.5
```

身份：

```text
POST_FREEZE_DIAGNOSTIC
```

不得访问 official test 做 model selection。

生成：

```text
artifacts/a2_2_metadata_baseline_predictions.csv
artifacts/a2_2_metadata_baseline_summary.csv
```

---

## 18. Confounder 解释边界

允许：

```text
metadata alone contains some predictive signal
structural B2 is descriptively stronger/weaker than metadata-only on frozen dev protocol
```

若没有预注册 paired inference，不得写：

```text
B2 significantly outperforms metadata-only
```

不得升级 FC1/FC2。

---

# A2.3 Baseline Completeness & Paper Completion

## 19. Baseline audit

从冻结 artifacts 中整理：

```text
B0
B1
B2
B3
B4
S0–S6
```

具体含义必须读取仓库 registry，不得凭记忆猜。

生成：

```text
artifacts/a2_3_baseline_completeness_matrix.csv
```

字段至少：

```text
method_id
representation
model_family
feature_dim
semantic_model
dev_evaluated
LOBO_evaluated
model_transfer_evaluated
ablation_role
uncertainty_available
official_test_role
claim_status
paper_role
```

---

## 20. Baseline hierarchy

分层：

```text
Tier 0 — trivial / minimal control
Tier 1 — lightweight structural
Tier 2 — alternative structural / text representation
Tier 3 — dense semantic
Tier 4 — published external LLM/process evaluators
```

Tier 4 只作为 literature context。

若本地没有正式核验数字：

```text
needs_literature_verification = true
```

不得伪造或把不同 split 的跨论文数字当 head-to-head comparison。

---

## 21. Paper-ready tables

生成：

```text
artifacts/a2_table_1_main_heldout_results.csv
artifacts/a2_table_2_efficiency_tradeoff.csv
artifacts/a2_table_3_dev_representation_summary.csv
artifacts/a2_table_4_benchmark_heterogeneity.csv
artifacts/a2_table_5_error_analysis_summary.csv
```

A1 scientific metrics：

```text
只能 exact join frozen values
```

每行新增：

```text
evidence_status
```

可选值：

```text
CONFIRMATORY_SUPPORTED
EXPLORATORY_SUPPORTED
DEV_ONLY
DESCRIPTIVE_ONLY
EFFICIENCY_BENCHMARK
POST_FREEZE_DIAGNOSTIC
POST_FREEZE_DESCRIPTIVE
```

---

## 22. Figure specification

生成：

```text
docs/a2_publication_figure_spec.md
```

正文候选最多 4–5 张核心图：

```text
Fig.1 Evaluation pipeline / study design
Fig.2 Official held-out AP lift + 95% CI
Fig.3 Efficiency / complexity tradeoff
Fig.4 Feature-group / coefficient interpretation
Fig.5 Benchmark heterogeneity or error taxonomy
```

不得为了图多而制造低价值图。

---

## 23. Publication story freeze

生成：

```text
docs/a2_publication_results_story.md
```

只冻结论文故事，不写完整 manuscript。

至少包括：

```text
3–5 title candidates
one-sentence problem statement
3–4 contributions
RQ1–RQ6
results order
main tables
main figures
allowed wording
forbidden wording
remaining evidence gaps
```

推荐核心叙事：

> We systematically investigate how far lightweight, task-agnostic structural signals can support web-agent trajectory evaluation. Across grouped development analyses and a blind official held-out evaluation, structural signals provide reliable predictive value for Success and Looping while requiring substantially lower representation and computation complexity than dense semantic encoding. Post-hoc analyses characterize which structural dimensions matter, where the evaluator fails, and the scope within which these signals should be interpreted.

禁止：

```text
universal Agent Judge
causal mechanism
unseen-benchmark generalization
universal replacement for LLM judges
```

---

# Optional External Validation Gate

## 24. 身份

真正独立 benchmark/dataset：

```text
SHOULD
不是 A2 PASS 的默认 MUST
```

A2.1–A2.3 完成后输出：

```text
A2_EXTERNAL_VALIDATION_DECISION
```

只能：

```text
DO_NOW
DEFER_TO_REVISION
NOT_WORTH_COST
```

---

## 25. DO_NOW 条件

只有同时满足：

1. 公开合法、可固定 revision；
2. 有与 Success 足够兼容的 label；
3. 可复用现有 13-feature extractor；
4. 无需重构核心方法；
5. 工作量不会明显拖延投稿；
6. 不需要将 A1.10 official test 当 dev；
7. 可以独立 preregister；

才建议：

```text
DO_NOW
```

否则：

```text
DEFER_TO_REVISION
```

或：

```text
NOT_WORTH_COST
```

A2 不得自动执行 external validation。

---

## 26. A2 全局禁止事项

禁止：

```text
修改 A1 final method
修改 A1 threshold
修改 A1 eligibility
重算/替换 A1.10 confirmatory metrics
重新选择 B2/B4 winner
用 test error analysis 调模型
official test tuning
fusion
第二 embedding 模型搜索
大型 classifier search
新 LLM Judge 系统
为提高 test AP 增加 feature
把 post-freeze diagnostic 升级 confirmatory
```

A1.10 labels 已解锁，因此允许读取 frozen scored predictions 做 descriptive error analysis，但所有相关结论必须标：

```text
POST_FREEZE_DESCRIPTIVE
```

---

## 27. 输出 artifacts

至少：

### A2.1

```text
artifacts/a2_1_efficiency_raw.csv
artifacts/a2_1_efficiency_summary.csv
artifacts/a2_1_efficiency_relative_cost.csv
docs/a2_1_efficiency_report.md
```

### A2.2

```text
artifacts/a2_2_structural_coefficients.csv
artifacts/a2_2_feature_group_evidence.csv
artifacts/a2_2_error_case_manifest.csv
artifacts/a2_2_error_case_notes.csv
artifacts/a2_2_metadata_baseline_predictions.csv
artifacts/a2_2_metadata_baseline_summary.csv
docs/a2_2_error_analysis.md
docs/a2_2_interpretability_and_confounder_report.md
```

### A2.3

```text
artifacts/a2_3_baseline_completeness_matrix.csv
artifacts/a2_table_1_main_heldout_results.csv
artifacts/a2_table_2_efficiency_tradeoff.csv
artifacts/a2_table_3_dev_representation_summary.csv
artifacts/a2_table_4_benchmark_heterogeneity.csv
artifacts/a2_table_5_error_analysis_summary.csv
docs/a2_publication_figure_spec.md
docs/a2_publication_results_story.md
```

### Final

```text
artifacts/a2_run_summary.json
docs/stage_a2_publication_completion_report.md
```

---

## 28. Commit discipline

如果 taskbook 尚未 tracked：

```text
chore: preregister publication completion experiments
```

提交后 STOP，下一轮再正式执行。

实现代码建议独立：

```text
chore: implement publication completion diagnostics
```

最终结果：

```text
analysis: complete publication evidence package
```

不得 amend。

Fix commits 必须独立保留。

---

## 29. Codex token / runtime discipline

机械长任务必须：

```text
Codex 写 deterministic script
→ 本地脚本一次执行
→ compact progress
→ Codex 只读取 summary
```

禁止：

```text
逐 trajectory agent 轮询
大量终端全文进入上下文
反复读取大型 CSV
```

Qwen benchmark：

```text
每 20–50 条打印一次进度
```

即可。

---

## 30. A2 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS 必须满足

A2.1：

```text
efficiency benchmark complete
B2/B4 runtime/memory/complexity 可比较
environment 完整
A1.10 metrics 未重算
```

A2.2：

```text
coefficients / feature-group synthesis complete
deterministic error cases complete
metadata-only dev baseline complete
no test-driven tuning
non-causal interpretation preserved
```

A2.3：

```text
baseline completeness matrix complete
paper tables complete
figure specification complete
publication story complete
```

Overall：

```text
A1.11 claim matrix hash unchanged
A1 claims unchanged
official-test tuning = 0
external validation decision complete
Git clean
```

成功后：

```text
READY_FOR_A3_PAPER_ARTIFACT_FREEZE
```

---

### PASS_WITH_CONDITIONS

允许：

```text
B4 某项资源测量受环境限制
部分 error case = unclear
Tier 4 literature numbers 待写作阶段核验
external validation = DEFER_TO_REVISION
```

前提是 A2.1–A2.3 主体已完成。

---

### STOP

包括：

```text
claim matrix hash mismatch
A1.10 metric conflict
official test 调参
final model/threshold/eligibility 被修改
error analysis 反向影响模型
metadata baseline 使用 test 做选择
效率环境不可解释
核心 provenance 不一致
```

---

## 31. 最终报告

生成：

```text
docs/stage_a2_publication_completion_report.md
```

至少包含：

1. 阶段判定；
2. commits；
3. A1.11 claim contract；
4. efficiency setup；
5. B2/B4 efficiency；
6. efficiency ratios；
7. coefficient interpretation；
8. feature-group synthesis；
9. Success error analysis；
10. Looping error analysis；
11. metadata confounder baseline；
12. baseline completeness；
13. publication tables；
14. figure specification；
15. publication story；
16. external validation decision；
17. warnings；
18. tests/verifiers；
19. Git status；
20. next state。

---

## 32. 最终汇报

Codex 最终必须汇报：

```text
阶段判定

prereg commit
implementation commit
result commit
fix commits
amend

A1.11 claim matrix SHA verified

A2.1:
B2/B4 dimensions
B2/B4 extraction ms/trajectory
B2/B4 inference ms/trajectory
representation/model sizes
peak CPU RSS
peak GPU VRAM
relative cost ratios
environment

A2.2:
Success top coefficients
Looping top coefficients
feature-group synthesis
Success FP/FN cases
Looping FP/FN cases
metadata-only dev AP/F1
diagnostic status

A2.3:
baseline completeness
paper table hashes
figure spec
publication story

External validation decision

A1 metric recomputations = 0
A1 threshold changes = 0
A1 model changes = 0
official-test tuning = 0

warnings
tests/verifiers
Git status

report path
machine summary path

READY_FOR_A3_PAPER_ARTIFACT_FREEZE
```

完成后停止。

不得自动执行 A3。
