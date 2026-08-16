# Stage A1.11：Final Evidence Consolidation、Claim Freeze 与 Paper Evidence Package

## 1. 阶段定位

Stage A1.10 已完成 official held-out test 的 blind-first final evaluation，并给出：

```text
PASS
```

A1.10 已冻结的核心结果：

### Success

```text
role = confirmatory_primary
eligible = 1097
positive = 291
negative = 806
prevalence = 0.265269
AP = 0.654836
AP lift = 0.389567
F1 = 0.682099
AP-lift 95% CI = [0.326806, 0.455411]
grade = CONFIRMED_HELDOUT_SIGNAL
```

### Looping

```text
role = confirmatory_primary
eligible = 1095
positive = 577
negative = 518
prevalence = 0.526941
AP = 0.921769
AP lift = 0.394829
F1 = 0.876987
AP-lift 95% CI = [0.360965, 0.428598]
grade = CONFIRMED_HELDOUT_SIGNAL
```

### Side Effect

```text
role = exploratory_only
eligible = 1102
positive = 71
negative = 1031
prevalence = 0.064428
AP = 0.107279
AP lift = 0.042851
F1 = 0.168582
AP-lift 95% CI = [0.021245, 0.079200]
grade = EXPLORATORY_TEST_RESULT
```

A1.10 已确认：

```text
blind-before-label provenance = valid
blind predictions changed after unlock = false
join integrity = complete
post-unlock re-inference = 0
embedding regeneration = 0
estimator refit = 0
threshold change = 0
eligibility change = 0
metric change = 0
bootstrap change = 0
test-driven tuning = 0
```

Stage A1.11 不再回答：

> “有没有 held-out signal？”

这个问题对 Success 与 Looping 已经由 A1.10 回答。

Stage A1.11 的唯一目的：

> 将 A0.x–A1.10 的正式证据、commit、hash、机器结果、阶段结论与 claim 边界整合成一套论文级、可审计、不可随意扩张的最终证据包，并冻结后续论文可以写什么、不能写什么。

本阶段是：

```text
evidence consolidation
claim audit
paper evidence freeze
```

不是：

```text
新实验
新模型
test tuning
机制探索
外部泛化实验
论文全文写作
```

---

## 2. 阶段目标

A1.11 必须完成六件事：

### G1. 全链路 provenance audit

建立：

```text
A0.x
→ A1.0
→ A1.1
→ A1.2
→ A1.3
→ A1.4
→ A1.5
→ A1.6
→ A1.7
→ A1.8
→ A1.9
→ A1.10a
→ A1.10b
```

的完整证据链。

每个 Stage 至少记录：

```text
stage id
stage determination
formal report
machine artifact
preregistration / taskbook（若存在）
result commit
fix commits
key hashes
key sample counts
key scientific conclusion
known conditions / warnings
claim role
```

不得只依赖人工记忆。

### G2. Final claim matrix

把所有潜在论文 claim 分成：

```text
CONFIRMATORY_SUPPORTED
EXPLORATORY_SUPPORTED
DEV_ONLY
DESCRIPTIVE_ONLY
NOT_SUPPORTED
PROHIBITED_OVERCLAIM
```

每条 claim 必须能追溯到：

```text
specific stage
specific artifact
specific metric/result
specific commit/hash
```

### G3. Final evidence hierarchy

明确区分：

```text
开发阶段证据
外部/LOBO robustness 证据
消融证据
semantic representation 证据
uncertainty 证据
official blind test 证据
```

禁止把不同证据层级混成同一个结论。

### G4. Paper-ready result tables

生成论文主结果所需的冻结表格数据源。

至少包括：

```text
Main Held-out Test Results
Per-Benchmark Test Results
Dev Selection Summary
Ablation Summary
LOBO / External Evaluation Summary
Final Claim Status
```

只能从已有 frozen artifacts 读取并整理。

不得重新训练或选择。

### G5. Paper figure specification

确定：

```text
哪些图必须画
每张图回答什么问题
使用哪个 frozen artifact
横纵轴是什么
caption 应强调什么
哪些比较不能画成 confirmatory
```

本阶段只冻结 figure specification，不要求生成最终投稿级图片。

### G6. A2 决策建议

A1.11 最后必须根据现有证据缺口给出：

```text
A2 是否需要
A2 的目的是什么
哪些是必须补
哪些是加分项
哪些不值得继续
```

但不得自动执行 A2。

---

## 3. A1.10 frozen provenance

A1.11 必须把下列状态作为不可修改输入。

### A1.10a

```text
result commit:
cead3cbaa362da4a9918dab32e41b58fffb987d9

fix commit:
100966969bf36c968051dea7fbbb675c1814b7cd
```

Blind prediction SHA-256：

```text
a3a232484716ee455a604f03ffd40e6f734a1925ffdfb93e4a3d04118de27c3d
```

A1.10a：

```text
labels = 0
eligibility = 0
metrics = 0
```

### A1.10b

```text
preregistration commit:
042866147e7b4a0c930eeb120d6e642cb34773a7

pre-unlock fix commit:
3f0bc4da460652a74ae4767ff6d482fd4116ec9f

pre-unlock integrity commit:
85cb71a49c9c25c9284562afad751f975d787608

result commit:
53d81eb17e1be52e55489f5fbdf1f72018c5a349
```

Label unlock UTC：

```text
2026-08-09T04:18:26.082790+00:00
```

Scored predictions SHA-256：

```text
22883f32ad22ecd2de6e7a3056a0f165d7aa4c03ab4ec847a535dbff7defb704
```

---

## 4. 其他必须保留的关键 provenance

### Data

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

### A1.8 claim matrix

```text
SHA-256:
264678a325f1680c8cfdad3631e6f5209a29a91e6ab8dd5b9683adb857810590
```

### A1.9

```text
A1.9a:
4944df46be45d8ad52d57a051e04b59c4a1a82ee

A1.9b:
8f96a6f032ee9b4dd0272164d60230303612043b
```

### A1.10 taskbook docs-only commit

```text
ce31d8767de3fa45d436191ab8faf6aff126eb0d
```

---

## 5. Git gate

开始前：

```text
git status --porcelain
```

必须为空。

记录：

```text
branch
HEAD
A1.10b result commit
```

如果 dirty：

```text
STOP
```

---

## 6. 本阶段允许与禁止

只允许：

```text
读取已有正式 reports
读取已有 machine artifacts
读取已有 frozen CSV/JSON
读取已有 Git commits / blobs / hashes
做 deterministic consistency checks
做表格整理
做 claim classification
做 provenance mapping
生成新的 docs / CSV / JSON summary
```

禁止：

```text
下载新数据
重新打开远程数据源
重新训练
重新 embedding
重新 inference
重新 score test
重新 bootstrap
重新选择 threshold
重新选择 model
重新定义 eligibility
重新定义 metric
新增 benchmark
新增 dataset
新增 LLM Judge
新增 classifier
新增 fusion
新增 calibration
```

---

## 7. 禁止重新计算 A1.10 核心结果

A1.11 必须优先读取 A1.10 frozen outputs：

```text
a1_10_target_metrics.csv
a1_10_benchmark_metrics.csv
a1_10_bootstrap_summary.csv
a1_10_confirmatory_grade.csv
a1_10_final_claim_status.csv
a1_10_run_summary.json
```

若路径不同，只允许通过 A1.10 正式 report / summary 定位。

不得：

```text
从 labels + predictions 重新计算 AP
重新跑 10000 bootstrap
重新生成 grade
```

允许：

```text
byte/hash verification
CSV ↔ JSON ↔ report 数值一致性 verification
```

---

## 8. Evidence registry

生成：

```text
artifacts/a1_11_evidence_registry.csv
artifacts/a1_11_evidence_registry.json
```

每条 evidence 至少包含：

```text
evidence_id
stage
evidence_type
target
artifact_path
artifact_sha256
commit
metric_name
metric_value
uncertainty
sample_n
task_group_n
benchmark_scope
model_scope
claim_role
scientific_status
notes
```

`evidence_type` 建议限定：

```text
DATA_CONTRACT
DEV_BASELINE
LOBO
MODEL_TRANSFER
ABLATION
UNCERTAINTY
DENSE_SEMANTICS
METHOD_FREEZE
BLIND_TEST
INTEGRITY
LIMITATION
```

不得把无法定位正式 artifact 的数字登记为正式 evidence。

---

## 9. Final claim matrix

生成：

```text
artifacts/a1_11_final_claim_matrix.csv
docs/a1_11_final_claim_ledger.md
```

每条 claim 至少包含：

```text
claim_id
claim_text
status
target
scope
supporting_evidence_ids
contradicting_or_limiting_evidence
allowed_paper_section
required_qualifier
prohibited_extension
```

---

## 10. 必须冻结的核心 claims

### FC1 — Success held-out signal

状态：

```text
CONFIRMATORY_SUPPORTED
```

允许核心语义：

> Frozen structural trajectory features retain predictive signal for Success on untouched official held-out tasks/trajectories within the evaluated benchmark families.

绑定：

```text
AP = 0.654836
AP lift = 0.389567
95% CI = [0.326806, 0.455411]
F1 = 0.682099
grade = CONFIRMED_HELDOUT_SIGNAL
```

必须限定：

```text
existing benchmark families
official held-out tasks/trajectories
```

禁止扩张到：

```text
unseen benchmark generalization
arbitrary web agents
new datasets
joint task/model OOD
universal success judging
causal mechanism
```

### FC2 — Looping held-out signal

状态：

```text
CONFIRMATORY_SUPPORTED
```

允许核心语义：

> Frozen structural trajectory features retain strong predictive signal for Looping on untouched official held-out tasks/trajectories within the evaluated benchmark families.

绑定：

```text
AP = 0.921769
AP lift = 0.394829
95% CI = [0.360965, 0.428598]
F1 = 0.876987
grade = CONFIRMED_HELDOUT_SIGNAL
```

禁止扩张范围同 FC1。

### FE1 — Side Effect

状态：

```text
EXPLORATORY_SUPPORTED
```

必须表述：

```text
exploratory
low-support
not confirmatory
```

允许记录：

```text
AP = 0.107279
AP lift = 0.042851
95% CI = [0.021245, 0.079200]
F1 = 0.168582
```

不能写：

```text
confirmed Side Effect detector
confirmatory held-out Side Effect claim
```

---

## 11. 必须保留为 DEV_ONLY 的 claims

至少包括：

```text
B2 > B3
B4 > B2/B3
dense semantics superiority
termination feature = Success causal mechanism
repetition feature = Looping causal mechanism
S6 superiority / replacement claim
A1.4 model-only transfer as final generalization claim
complexity hierarchy
representation hierarchy
```

如果 A1.2–A1.7 支持描述趋势，可标：

```text
DEV_ONLY
```

不得因 A1.10 test 高分而升级。

---

## 12. 必须标记的 PROHIBITED_OVERCLAIM

至少包括：

```text
Our method generalizes to unseen benchmarks.
Our method generalizes to arbitrary agents.
Our method establishes joint task-and-model OOD robustness.
Structural features causally determine success.
Dense semantics are unnecessary in general.
Simple models are universally better than complex models.
Side Effect is confirmed.
The system is a universal Agent Judge.
```

必须说明禁止原因。

---

## 13. Benchmark heterogeneity

A1.10 per-Benchmark results 只能作为：

```text
DESCRIPTIVE_ONLY
```

### Success

```text
assistantbench: AP 0.356643 / F1 0.312500
visualwebarena: AP 0.653714 / F1 0.655367
webarena: AP 0.642390 / F1 0.692015
workarena: AP 0.674782 / F1 0.761364
```

### Looping

```text
assistantbench: AP 0.712685 / F1 0.773585
visualwebarena: AP 0.869255 / F1 0.863469
webarena: AP 0.930541 / F1 0.852941
workarena: AP 0.963169 / F1 0.908795
```

### Side Effect

```text
assistantbench: AP 0.044366 / F1 0.000000
visualwebarena: AP 0.136418 / F1 0.198582
webarena: AP 0.102407 / F1 0.153846
workarena: AP 0.116510 / F1 0.114286
```

允许：

> signal strength is heterogeneous across benchmark families.

禁止在没有预注册 inferential test 的情况下写：

```text
Benchmark A significantly outperforms Benchmark B.
```

---

## 14. Main paper table freeze

生成：

```text
artifacts/a1_11_table_main_test_results.csv
```

字段：

```text
Target
Role
Eligible
Positive
Negative
Prevalence
Final Method
Threshold
AP
AP Lift
F1
AP-lift 95% CI Lower
AP-lift 95% CI Upper
Final Grade
```

所有数字必须 exact 对齐 A1.10 frozen outputs。

machine artifact 保留原值；展示层可另行规定小数位。

---

## 15. Per-Benchmark table freeze

生成：

```text
artifacts/a1_11_table_benchmark_results.csv
```

至少包含：

```text
Target
Benchmark
AP
F1
Role
Interpretation
```

其中：

```text
Interpretation = DESCRIPTIVE_ONLY
```

---

## 16. Dev evidence summary

从 A1.2–A1.9 正式 artifacts 提取论文所需最小 dev evidence。

至少总结：

```text
minimal grouped baselines
external/LOBO evaluation
ablation
uncertainty
dense semantics
final method freeze
```

生成：

```text
artifacts/a1_11_dev_evidence_summary.csv
```

保留原来的：

```text
PASS / PASS_WITH_CONDITIONS
support level
claim boundary
```

不得把 exploratory evidence 改写成 confirmatory evidence。

---

## 17. Figure specification

生成：

```text
docs/a1_11_paper_figure_spec.md
```

至少规划：

### Figure 1 — Evaluation protocol

回答：

> 如何从 dev selection 走到 blind official test？

强调：

```text
dev-only selection
A1.9 method freeze
A1.10a prediction-before-label
A1.10b one-time unlock
```

### Figure 2 — Final held-out AP lift with 95% CI

对象：

```text
Success
Looping
Side Effect
```

要求：

- Success / Looping 标 confirmatory；
- Side Effect 明确 exploratory；
- 使用 A1.10 frozen AP-lift CI；
- 不重新 bootstrap。

### Figure 3 — Per-Benchmark descriptive performance

候选：

```text
AP by target × benchmark
```

caption 必须注明：

```text
descriptive heterogeneity
not a preregistered pairwise significance comparison
```

### Figure 4 — Dev representation / ablation evidence

只有 A1.2–A1.7 frozen evidence 足够清晰时纳入。

必须标：

```text
dev-only
```

---

## 18. Paper results outline

生成：

```text
docs/a1_11_paper_results_outline.md
```

只写结果章节结构，不写完整论文。

建议：

```text
R1. Development-stage signal discovery
R2. Robustness across grouped folds / held-out benchmark domains
R3. Structural ablations and uncertainty
R4. Dense semantic representation comparison
R5. Final method freeze and blind evaluation protocol
R6. Official held-out Success result
R7. Official held-out Looping result
R8. Exploratory Side Effect result
R9. Benchmark heterogeneity
R10. Claim boundaries and limitations
```

每节绑定：

```text
source artifact
figure/table
allowed claim
forbidden interpretation
```

---

## 19. Limitations freeze

生成：

```text
docs/a1_11_limitations_ledger.md
```

至少包含：

### L1. Benchmark-family scope

不能声明：

```text
unseen-Benchmark generalization
```

### L2. Agent/model scope

当前 test 不是严格：

```text
joint unseen task + unseen model OOD
```

### L3. Side Effect support

保留：

```text
development positive support low
exploratory-only
```

### L4. Label / construct limitations

只能陈述已有 data-contract / annotation evidence 支持的限制。

不得凭主观感觉新增事实。

### L5. Prediction ≠ causation

结构 feature 可预测不等于因果机制。

### L6. Benchmark heterogeneity

Success 在不同 benchmark family 上差异明显，应作为外部有效性限制和后续方向。

---

## 20. A2 gap analysis

生成：

```text
docs/a1_11_a2_gap_analysis.md
```

按：

```text
MUST
SHOULD
OPTIONAL
DO_NOT_PRIORITIZE
```

评估：

### 候选 A：外部有效性验证

> 是否需要真正独立 benchmark / dataset 支持跨 benchmark 泛化？

### 候选 B：轻量机制验证

> 是否值得对 Success / Looping 核心 structural signal 做更严格机制分析？

### 候选 C：论文整合

> 现有证据是否已足够开始论文主体写作？

### 候选 D：继续堆复杂模型

默认优先级低。

除非 evidence gap 明确要求，否则不建议为了追分继续：

```text
fusion
larger embedding
LLM Judge
complex classifier
```

---

## 21. Final claim freeze hash

对：

```text
artifacts/a1_11_final_claim_matrix.csv
```

计算 SHA-256。

作为后续论文写作的 claim contract。

后续 manuscript 不得在没有新 Stage 审批时：

```text
新增 confirmatory claim
扩大 scope
删除 limitation
把 exploratory 改 confirmatory
```

---

## 22. Machine summary

生成：

```text
artifacts/a1_11_run_summary.json
```

至少包含：

```text
stage
determination
head_before
result_commit
input_reports
input_machine_artifacts
verified_commits
verified_hashes
evidence_registry_rows
claim_count_by_status
core_confirmatory_claims
exploratory_claims
dev_only_claims
prohibited_overclaims
main_table_hash
final_claim_matrix_hash
warnings
inconsistencies
new_experiments_executed
model_fits
inference_runs
embedding_runs
test_metric_recomputations
git_clean
next_stage_recommendation
```

要求：

```text
new_experiments_executed = 0
model_fits = 0
inference_runs = 0
embedding_runs = 0
test_metric_recomputations = 0
```

---

## 23. 正式报告

生成：

```text
docs/stage_a1_11_final_evidence_consolidation_report.md
```

至少包含：

1. 阶段判定；
2. 输入 provenance；
3. A0–A1.10 audit completeness；
4. evidence registry completeness；
5. FC1 Success final status；
6. FC2 Looping final status；
7. FE1 Side Effect final status；
8. dev-only claims；
9. prohibited overclaims；
10. benchmark heterogeneity；
11. main table freeze；
12. figure specification；
13. limitations ledger；
14. final claim matrix SHA；
15. A2 gap analysis；
16. warnings / inconsistencies；
17. no-new-experiment guard；
18. tests / verifiers；
19. Git status；
20. 下一阶段建议。

---

## 24. 建议 commits

### A1.11a

先提交任务书 / 执行协议：

```text
chore: preregister final evidence consolidation
```

要求：

```text
docs-only
no result artifacts
```

### A1.11b

完成整合后：

```text
analysis: freeze final evidence and paper claims
```

不得 amend A1.11a。

纯实现错误：

```text
独立 fix commit
```

不得隐藏。

---

## 25. 高效执行约束

A1.11 不应成为长时间 LLM agent loop。

优先：

```text
一次性本地 deterministic audit script
→ 读取 frozen files
→ 输出 registry / consistency summary
→ Codex 只审查 summary 和异常
```

禁止：

```text
逐文件人工轮询
反复读取相同大型 artifact
无意义长日志
```

原则：

> LLM 负责协议执行、异常判断和证据审计；机械解析、hash、表格整理由本地脚本一次性完成。

---

## 26. 一致性检查

至少检查：

### A1.10

```text
report
run_summary
target_metrics
benchmark_metrics
bootstrap_summary
confirmatory_grade
final_claim_status
```

核心数值完全一致。

### A1.9 ↔ A1.10

```text
final methods
thresholds
model hashes
roles
```

完全一致。

### A1.8 ↔ A1.9

claim freeze provenance 一致。

### A1.2–A1.7

只提取正式 report / machine artifacts 已支持的结论。

发现任何核心冲突：

```text
STOP
```

不得自行挑选一个值。

---

## 27. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

必须满足：

1. Git start clean；
2. A0–A1.10 formal provenance 可解析；
3. A1.10 confirmatory metrics 一致；
4. blind-before-label provenance 无冲突；
5. final method / threshold / hash 一致；
6. evidence registry 完成；
7. final claim matrix 完成；
8. FC1/FC2 保持 confirmatory-supported；
9. FE1 保持 exploratory；
10. dev-only claims 未升级；
11. prohibited overclaims 已列明；
12. limitations ledger 完成；
13. paper table/figure specs 完成；
14. A2 gap analysis 完成；
15. new experiments = 0；
16. model fits = 0；
17. inference = 0；
18. embedding = 0；
19. test metric recomputation = 0；
20. result commit 独立；
21. Git final clean。

成功后：

```text
READY_FOR_A2_DESIGN_REVIEW
```

### PASS_WITH_CONDITIONS

只允许用于：

```text
非核心文档缺口
非阻塞历史 warning
某些早期 Stage provenance 只能部分解析
```

前提是 A1.10 核心 evidence chain 无冲突。

### STOP

包括：

```text
A1.10 数值冲突
blind prediction provenance 冲突
model hash / threshold 冲突
核心 artifact 缺失
claim matrix 擅自升级
report 与 machine artifact 无法解释地不一致
Git provenance 无法确认
```

---

## 28. 最终汇报

Codex 最终必须汇报：

1. 阶段判定；
2. A1.11a commit；
3. A1.11b commit；
4. fix commits；
5. 是否 amend；
6. A0–A1.10 provenance audit 覆盖；
7. evidence registry rows；
8. final claim matrix rows；
9. claim status counts；
10. FC1 Success status；
11. FC1 exact supporting metrics；
12. FC2 Looping status；
13. FC2 exact supporting metrics；
14. FE1 Side Effect status；
15. FE1 exact supporting metrics；
16. dev-only claim count；
17. prohibited overclaim count；
18. benchmark heterogeneity summary；
19. final claim matrix SHA；
20. main test table SHA；
21. limitations count；
22. A2 gap recommendation；
23. new experiments = 0；
24. model fits = 0；
25. inference runs = 0；
26. embedding runs = 0；
27. test metric recomputations = 0；
28. warnings / inconsistencies；
29. tests/verifiers；
30. Git status；
31. report path；
32. machine summary path；
33. final state：

```text
READY_FOR_A2_DESIGN_REVIEW
```

完成后立即停止。

不得自动执行 A2。
