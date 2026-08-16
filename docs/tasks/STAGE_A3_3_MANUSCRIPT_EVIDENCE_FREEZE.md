# Stage A3.3：Manuscript Evidence Freeze & Writing Readiness

## 1. 阶段定位

A3.3 是正式 manuscript 写作之前的最后一个 evidence-freeze 阶段。

目标不是直接写完整论文，而是：

> 将 A1–A3.2 的 frozen scientific evidence、figures、tables、literature positioning、limitations 和 claim boundaries 映射到 manuscript 的每一个 section，形成一套“写作时只能从这里取证”的 manuscript evidence package。

A3.3 完成后进入：

```text
READY_FOR_MANUSCRIPT_DRAFTING
```

本阶段不做：

```text
new experiment
new metric computation
new literature expansion
new figure generation
full manuscript prose
journal submission formatting
```

完成后必须：

```text
STOP
WAIT_FOR_HUMAN_A3_3_REVIEW
```

不得自动开始完整论文写作。

---

## 2. A3.3 只回答六个问题

1. Abstract 中允许出现哪些数字和 claim？
2. Introduction 中 gap、motivation、contribution 如何与 A3.2 verified literature 对齐？
3. Methods 中哪些 protocol/model/split/leakage-control/freeze details 必须出现？
4. Results 每个 subsection 对应哪张 frozen table/figure/evidence？
5. Discussion/Limitations 中哪些解释允许、哪些属于 overclaim？
6. Appendix/Supplementary 应放哪些 dev-only、descriptive、exploratory、diagnostic evidence？

---

## 3. Hard gates

正式执行前必须全部通过。

### 3.1 Git

```text
git status --porcelain
```

必须为空。

### 3.2 A3.1 result

```text
e17bf7c6c1974d8a96ab7e7814b0a21ec827a082
```

必须可解析。

### 3.3 A3.2 result

```text
ef37dee92ef319b2f7d39367e757919a898fbfdb
```

必须可解析。

### 3.4 A3.2 closest-work addendum gate

A3.3 不允许仅基于当前 A3.2 主体直接执行。

必须存在一个独立、已人工批准的 A3.2 targeted closest-work addendum，至少完成：

```text
WebGraphEval verification
WebStep verification
"Similar" canonical identity resolution
novelty-positioning recheck
comparability recheck
citation/BibTeX update if needed
```

并且最终明确：

```text
A3_2_CLOSEST_WORK_ADDENDUM = PASS or PASS_WITH_CONDITIONS
```

若 addendum 尚未完成：

```text
STOP
BLOCKED_BY_A3_2_ADDENDUM
```

不得继续 A3.3。

### 3.5 A1.11 claim matrix

必须 exact match：

```text
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

### 3.6 Frozen claims

必须仍为：

```text
Success = CONFIRMATORY_SUPPORTED
Looping = CONFIRMATORY_SUPPORTED
Side Effect = EXPLORATORY_SUPPORTED
```

### 3.7 A3.1 figures/tables

必须能解析 A3.1 final artifact registry，并确认 manuscript-facing figures/tables hashes 未漂移。

任一 hard gate 失败：

```text
STOP
```

---

## 4. Preregistration gate

如果：

```text
docs/tasks/STAGE_A3_3_MANUSCRIPT_EVIDENCE_FREEZE.md
```

尚未 Git tracked：

只允许提交：

```text
chore: preregister A3.3 manuscript evidence freeze
```

然后：

```text
STOP
```

不得在同一轮继续执行。

---

## 5. Scientific-operation counters

整个 A3.3 必须保持：

```text
new_model_fits = 0
new_inference_runs = 0
new_embedding_runs = 0
A1_metric_recomputations = 0
bootstrap_reruns = 0
new_significance_tests = 0
threshold_changes = 0
eligibility_changes = 0
final_model_changes = 0
official_test_tuning = 0
external_dataset_downloads = 0
external_dataset_runs = 0
new_literature_searches = 0
new_scientific_figures = 0
```

允许：

```text
evidence mapping
citation mapping
section outlining
claim wording normalization
table/figure placement
display-value reuse
document generation
hash verification
```

---

# Part I — Manuscript Evidence Registry

## 6. 生成

```text
artifacts/a3_3_manuscript_evidence_registry.csv
```

字段至少：

```text
evidence_id
source_stage
source_artifact
source_row_or_claim_id
target
evidence_type
evidence_status
exact_value
display_value
allowed_sections
primary_or_secondary
allowed_wording
forbidden_wording
table_id
figure_id
citation_keys
limitations_required
verified
```

不得创建新的科学 evidence status。

---

# Part II — Manuscript Section Contract

## 7. 生成

```text
docs/a3_3_manuscript_section_contract.md
```

冻结 manuscript 的 section-level evidence 规则。

---

## 8. Abstract contract

Abstract 只允许：

- 一句研究问题；
- 一句 lightweight structural representation + frozen blind-held-out protocol；
- Success / Looping 的 confirmatory 核心结果；
- 最多一句 environment-qualified efficiency statement；
- 一句限定在 evaluated benchmark families 的结论。

Side Effect 默认不进入 abstract 主结果。

禁止：

```text
unseen benchmark generalization
SOTA
outperforms LLM judges
universal evaluator
external validation
causal mechanism
```

---

# Part III — Introduction Contract

## 9. Introduction 四个逻辑块

### I1 — Problem
Web-agent evaluation 需要超越单一 terminal outcome / expensive semantic judge 的替代视角。

### I2 — Gap
已有工作覆盖 LLM/agent judges、reward models、process reward models、trajectory/process evaluation；本文只允许声称一个由 A3.2 + addendum 支持的 narrow gap。

禁止：

```text
no prior work
first
nobody has studied
```

### I3 — Our question

> How far can lightweight, task-agnostic structural trajectory signals support web-agent evaluation?

### I4 — Contributions

最多 4 条：

1. systematic study of lightweight structural trajectory signals；
2. blind-first frozen held-out evidence for Success / Looping；
3. efficiency and representation-complexity characterization；
4. interpretability/confounder/failure-boundary diagnostics。

生成：

```text
artifacts/a3_3_introduction_claim_map.csv
```

---

# Part IV — Methods Contract

## 10. 生成

```text
docs/a3_3_methods_contract.md
artifacts/a3_3_methods_source_map.csv
```

必须覆盖：

```text
M1 Data provenance
M2 Eligibility / labels
M3 Leakage-safe representation
M4 B2 13 structural features
M5 B0/B1/B3/B4 comparator roles
M6 Grouped development / LOBO / model transfer
M7 Final method / threshold freeze
M8 Blind held-out protocol
M9 A2 post-freeze diagnostics
```

必须明确：

```text
A2 diagnostics are post-freeze
```

不得把 A2 diagnostics 写成参与 final model selection。

---

# Part V — Results Contract

## 11. Results 顺序冻结

```text
R1 Development evidence
R2 Robustness / representation comparison
R3 Blind held-out confirmation
R4 Efficiency
R5 Interpretability / confounder
R6 Failure boundaries / benchmark heterogeneity
```

Success first，Looping second，Side Effect exploratory。

生成：

```text
artifacts/a3_3_results_evidence_map.csv
```

字段至少：

```text
result_section
question_answered
primary_evidence_ids
secondary_evidence_ids
table_ids
figure_ids
allowed_numeric_claims
allowed_interpretation
required_caveats
forbidden_claims
```

---

# Part VI — Figure / Table Placement Freeze

## 12. 生成

```text
docs/a3_3_figure_table_placement.md
```

正文默认：

```text
Table 1 — Main Held-out Results
Table 2 — Efficiency / Complexity
Table 3 — Dev Representation / Robustness
Table 5 — Interpretability / Failure Summary

Fig 1 — Study Pipeline
Fig 2 — Held-out AP Lift + CI
Fig 3 — Efficiency / Complexity
Fig 4 — Structural Interpretation
Fig 5 — Success Failure Boundaries
```

Appendix 默认：

```text
Table 4 — Benchmark Heterogeneity
Fig S1 — Side Effect exploratory
Fig S2 — Benchmark heterogeneity
Related Work positioning table
```

允许 MAIN_TEXT ↔ APPENDIX placement 调整，但不得改数据、caption 科学含义或 evidence status。

---

# Part VII — Discussion Contract

## 13. 生成

```text
docs/a3_3_discussion_contract.md
```

必须覆盖：

```text
D1 What the results support
D2 Why lightweight structure may help — hypothesis only
D3 morphology != task semantics
D4 metadata confounding not fully ruled out
D5 efficiency under measured environment
D6 relation to existing evaluators using verified A3.2 positioning
```

禁止 causal mechanism 和 “replacement for LLM judges”。

---

# Part VIII — Limitations Freeze

## 14. 生成

```text
docs/a3_3_manuscript_limitations_contract.md
```

必须继承 A2.3 limitations，至少包括：

1. evaluated benchmark families 内的 external validity；
2. Side Effect low support；
3. benchmark heterogeneity；
4. dev-only relative comparisons；
5. non-causal ablations；
6. correlated coefficients；
7. metadata confounding not fully ruled out；
8. environment-specific timing；
9. morphology != semantic understanding；
10. no calibration/deployment evidence；
11. no independent external benchmark validation；
12. Tier-4 cross-paper comparison limited by protocol mismatch。

不得删除旧 limitation。

---

# Part IX — Related Work Integration

## 15. 生成

```text
docs/a3_3_related_work_integration_contract.md
```

只能使用 A3.2 + addendum verified citation registry。

不得新增搜索。

每段记录：

```text
allowed citation keys
allowed comparison wording
forbidden comparison wording
```

---

# Part X — Appendix / Supplementary Freeze

## 16. 生成

```text
docs/a3_3_appendix_plan.md
```

至少：

```text
A Data provenance / cleaning / eligibility
B Full baseline definitions
C Grouped dev / LOBO / model transfer
D Ablation + uncertainty
E Dense semantic representation
F Blind-test protocol / integrity
G Benchmark heterogeneity
H Side Effect exploratory
I Efficiency environment details
J Interpretability / metadata / error cases
K Related Work positioning table
```

---

# Part XI — Claim Ledger

## 17. 生成

```text
artifacts/a3_3_claim_ledger.csv
```

字段：

```text
claim_id
manuscript_section
claim_text_template
claim_strength
target
evidence_ids
citation_keys
allowed
required_caveat
forbidden_variant
status
```

`status` 只能：

```text
APPROVED
APPROVED_WITH_CAVEAT
FORBIDDEN
```

---

# Part XII — Numeric Consistency Map

## 18. 生成

```text
artifacts/a3_3_numeric_consistency_map.csv
```

记录所有 manuscript-facing 核心数字：

```text
metric_name
target
exact_value
display_value
source_artifact
table_id
figure_id
allowed_sections
rounding_rule
verified
```

必须保证 Abstract / Results / Tables / Figures / Discussion 使用同一个 frozen display value。

---

# Part XIII — Manuscript Skeleton

## 19. 生成

```text
paper/manuscript/MANUSCRIPT_SKELETON.md
```

只包含：

```text
Title placeholder
Abstract bullet slots
1 Introduction
2 Related Work
3 Data / Problem Setup
4 Method
5 Experimental Protocol
6 Results
7 Discussion
8 Limitations
9 Conclusion
References
Appendix map
```

每个 subsection 只能放：

```text
purpose
claim IDs
evidence IDs
citation keys
table/figure refs
required caveats
```

不得自动写完整 prose。

---

# Part XIV — Abstract Evidence Card

## 20. 生成

```text
docs/a3_3_abstract_evidence_card.md
```

冻结：

```text
problem sentence scope
method sentence scope
Success result
Looping result
optional efficiency sentence
conclusion scope
forbidden abstract claims
```

---

# Part XV — Contribution Freeze

## 21. 生成

```text
docs/a3_3_contribution_contract.md
```

最终贡献不得超过 4 条。

每条：

```text
contribution_id
wording
evidence_support
literature_positioning_support
scope
forbidden_upgrade
```

禁止无证据升级 method novelty / benchmark novelty / SOTA / firstness。

---

# Part XVI — Manuscript Readiness Audit

## 22. 生成

```text
artifacts/a3_3_manuscript_readiness_checklist.csv
```

至少检查：

```text
abstract evidence complete
introduction gap verified
contributions frozen
methods provenance complete
results evidence mapped
tables placed
figures placed
discussion claims bounded
limitations complete
related work citations verified
appendix planned
numeric consistency complete
Side Effect exploratory everywhere
blind held-out != external validation everywhere
no unsupported firstness
no unsupported SOTA
no unsupported causality
no cross-paper invalid ranking
```

状态只能：

```text
PASS
FAIL
N/A
```

Scientific FAIL 必须为 0。

---

# Part XVII — Machine Summary / Report

## 23. 生成

```text
artifacts/a3_3_run_summary.json
docs/stage_a3_3_manuscript_evidence_freeze_report.md
```

Machine summary 至少包含：

```text
stage_determination
input_commits
input_hashes
evidence_registry_count
claim_ledger_count
approved_claim_count
approved_with_caveat_count
forbidden_claim_count
numeric_map_count
manuscript_sections_mapped
tables_mapped
figures_mapped
citations_mapped
limitations_count
readiness_pass_count
readiness_fail_count
output_hashes

new_model_fits
new_inference_runs
new_embedding_runs
A1_metric_recomputations
bootstrap_reruns
new_significance_tests
threshold_changes
eligibility_changes
final_model_changes
official_test_tuning
external_dataset_downloads
external_dataset_runs
new_literature_searches
new_scientific_figures
```

---

# 24. Tests / Verifiers

至少验证：

1. Git start clean；
2. A3.1 result reachable；
3. A3.2 result reachable；
4. A3.2 closest-work addendum approved；
5. A1.11 claim matrix exact；
6. A3.1 artifact hashes stable；
7. no new literature search；
8. no new scientific computation；
9. no metric recomputation；
10. evidence registry sources all exist；
11. Abstract uses only confirmatory evidence；
12. Side Effect exploratory everywhere；
13. all Results numbers map to frozen values；
14. all figure/table refs exist；
15. AgentRewardBench provenance consistent；
16. blind held-out != external validation；
17. Related Work only uses verified citations；
18. no DIRECTLY_COMPARABLE claim if A3.2 says none；
19. no SOTA / firstness / replacement claim；
20. limitations count >= frozen A2.3 ledger；
21. contribution count <= 4；
22. manuscript skeleton contains no full drafted prose；
23. numeric consistency exact；
24. readiness checklist has no scientific FAIL；
25. Git final clean。

---

# 25. Commit discipline

## A3.3a — prereg

```text
chore: preregister A3.3 manuscript evidence freeze
```

仅 taskbook，然后 STOP。

## A3.3b — implementation

```text
chore: implement A3.3 manuscript evidence mapping
```

## A3.3c — result

```text
docs: freeze A3.3 manuscript evidence package
```

不得 amend。

任何 fix 必须独立 commit。

---

# 26. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

要求：

```text
A3.2 addendum approved
all hard gates pass
manuscript evidence registry complete
section contracts complete
results map complete
claim ledger complete
numeric consistency complete
manuscript skeleton complete
appendix plan complete
readiness audit has no scientific FAIL
all scientific-operation counters = 0
Git final clean
```

### PASS_WITH_CONDITIONS

仅允许：

```text
journal-specific word limit 未确定
journal-specific section naming 未确定
final title 未选择
minor prose-order decisions remain
```

不得存在 scientific uncertainty 未映射。

### STOP

包括：

```text
A3.2 addendum missing
source hash drift
unsupported claim
numeric inconsistency
literature contradiction
Side Effect status drift
external-validation overclaim
new scientific computation
new literature expansion
Git provenance unclear
```

---

# 27. 最终状态

若 PASS / PASS_WITH_CONDITIONS：

```text
MANUSCRIPT_EVIDENCE_FROZEN
READY_FOR_MANUSCRIPT_DRAFTING
WAIT_FOR_HUMAN_A3_3_REVIEW
```

然后立即 STOP。

不得自动开始完整 manuscript。

---

# 28. Codex 最终汇报必须包含

```text
阶段判定

A3.3 prereg commit
implementation commit
result commit
fix commits
amend

A3.1 result verification
A3.2 result verification
A3.2 addendum verification
A1.11 claim matrix verification

evidence registry count
claim ledger count
APPROVED count
APPROVED_WITH_CAVEAT count
FORBIDDEN count
numeric consistency entries
limitations count
citations mapped
tables mapped
figures mapped

Abstract evidence card status
Introduction contract status
Methods contract status
Results map status
Discussion contract status
Limitations contract status
Related Work integration status
Appendix plan status
Contribution contract status
Manuscript skeleton status

readiness PASS count
readiness FAIL count

new_model_fits = 0
new_inference_runs = 0
new_embedding_runs = 0
A1_metric_recomputations = 0
bootstrap_reruns = 0
new_significance_tests = 0
threshold_changes = 0
eligibility_changes = 0
final_model_changes = 0
official_test_tuning = 0
external_dataset_downloads = 0
external_dataset_runs = 0
new_literature_searches = 0
new_scientific_figures = 0

warnings
Git status

report path
machine summary path
manuscript skeleton path
claim ledger path
numeric consistency map path
readiness checklist path

MANUSCRIPT_EVIDENCE_FROZEN
READY_FOR_MANUSCRIPT_DRAFTING
WAIT_FOR_HUMAN_A3_3_REVIEW
```

然后立即 STOP。
