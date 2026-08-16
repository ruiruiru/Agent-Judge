# Stage A3.2：Literature、Tier-4 Baseline 与 Related-Work Verification

## 1. 阶段定位

A3.1 已完成最终图表生成与视觉冻结，A3.2 只做**文献核验与论文定位冻结**。

唯一目标：

> 将 A2.3 中 `NEEDS_LITERATURE_VERIFICATION` 的 Tier-4 context，以及少量真正接近本研究的问题，核验成可引用、可定位、可比较、且边界清楚的 Related Work evidence package。

本轮不运行模型，不下载 external validation dataset，不改 A1/A2/A3.1 的任何科学结果。

完成后必须：

```text
STOP
WAIT_FOR_HUMAN_A3_2_REVIEW
```

不得自动进入 A3.3。

---

## 2. 只回答五个问题

1. Web-Shepherd、AgentRewardBench、AgentRM 的 canonical identity 和正式来源是什么？
2. 它们分别在评价 trajectory outcome、step/process quality、reward modeling、LLM/agent judging 还是 test-time search？
3. 哪些结果只能 contextual comparison，哪些才可能 direct head-to-head？
4. 截至执行日，2025–2026 是否出现必须进入 Related Work 的更接近工作？
5. THIS_WORK 应如何在不夸大的情况下冻结 novelty / positioning？

---

## 3. 科研身份

A3.2 仅属于：

```text
PRIMARY_SOURCE_VERIFICATION
RELATED_WORK_AUDIT
COMPARABILITY_CLASSIFICATION
CITATION_FREEZE
POSITIONING_FREEZE
```

不是新实验、新 benchmark、新显著性比较或 external validation。

---

## 4. Frozen gates

开始前必须验证：

```text
git status --porcelain
```

必须为空。

必须可解析：

```text
A3.1 result = e17bf7c6c1974d8a96ab7e7814b0a21ec827a082
A2.3 result = ad0576c488fafed243b464e0b8f903e9bb233b43
```

A1.11 claim matrix：

```text
SHA-256 = 2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

Frozen claims 必须仍为：

```text
Success = CONFIRMATORY_SUPPORTED
Looping = CONFIRMATORY_SUPPORTED
Side Effect = EXPLORATORY_SUPPORTED
```

任一 gate 失败：`STOP`。

---

## 5. Preregistration gate

如果：

```text
docs/tasks/STAGE_A3_2_LITERATURE_BASELINE_VERIFICATION.md
```

尚未 Git tracked，本轮只允许：

```text
chore: preregister A3.2 literature verification
```

然后立即 `STOP`，不得同轮继续搜索。

---

## 6. 科学操作零计数

整个 A3.2 必须保持：

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
```

允许：web literature search、primary-source reading、bibliographic extraction、table/figure location、citation normalization、qualitative comparability classification。

---

# Part I — Primary-source policy

## 7. 最终事实只允许 primary sources

优先级：

```text
1. peer-reviewed publisher / proceedings
2. official paper PDF
3. official arXiv page / HTML / PDF
4. official project page / repository
```

以下只能用于发现候选，不能成为最终事实依据：

```text
search snippets
blog/news
secondary survey
Google Scholar / Semantic Scholar snippets
Reddit
LLM-generated summaries
```

关键字段必须回到 primary source 核验。

---

## 8. Search cutoff

记录：

```text
literature_search_cutoff_date
```

执行一次 bounded freshness scan：

```text
2024-01-01 → execution date
```

重点 2025–2026，不得无限扩张。

---

# Part II — Mandatory Tier-4 verification

## 9. 必核验三项

### 9.1 AgentRewardBench

Seed：

```text
AgentRewardBench: Evaluating Automatic Evaluations of Web Agent Trajectories
arXiv:2504.08942
```

必须明确区分：

```text
their benchmark contribution
their LLM-judge evaluation
our structural evaluator study
```

本项目使用其数据，因此不得称为“独立于 AgentRewardBench 的新 benchmark”。

### 9.2 Web-Shepherd

Seed：

```text
Web-Shepherd: Advancing PRMs for Reinforcing Web Agents
arXiv:2505.15277
```

核验：step vs trajectory、PRM、training objective、input modality、benchmark、metric、test-time/reward-guided role。

### 9.3 AgentRM

Seed：

```text
AgentRM: Enhancing Agent Generalization with Reward Modeling
arXiv:2502.18407
```

核验：reward-model scope、agent task types、training、test-time search、web relevance、direct comparability。

以上 seed identity 必须重新由 primary source 验证。

---

# Part III — Bounded closest-work freshness scan

## 10. 最多新增 5 篇 included closest works

优先核验候选：

```text
Agent-as-a-Judge: Evaluate Agents with Agents
AgentPRM: Process Reward Models for LLM Agents via Step-Wise Promise and Progress
ToolPRMBench: Evaluating and Advancing Process Reward Models for Tool-using Agents
WebArbiter: A Principle-Guided Reasoning Process Reward Model for Web Agents
AgentProcessBench: Diagnosing Step-Level Process Quality in Tool-Using Agents
```

若截至 cutoff 发现更接近论文，可替换候选，但最终 included additional works <= 5。

### Inclusion rule

至少满足一项：

```text
A. evaluates full agent trajectories
B. evaluates web-agent execution quality
C. evaluates success/failure/side effects/repetition or close analogue
D. proposes automated judge/reward/verifier for agent trajectories
E. studies process/trajectory evaluation with direct conceptual relevance
```

否则：`EXCLUDED_NOT_CLOSE`。

---

# Part IV — Verified literature registry

## 11. 输出

```text
artifacts/a3_2_verified_literature_registry.csv
```

字段至少：

```text
work_id
canonical_title
authors
year
venue_or_status
primary_source_type
primary_source_identifier
primary_source_url
version_or_revision
verified_date
research_object
evaluation_granularity
input_representation
output_signal
training_required
uses_llm_or_vlm
uses_reward_model
uses_rule_based_eval
web_agent_specific
trajectory_level
step_level
benchmarks
policy_models
reported_metrics
reported_main_result
result_source_location
code_available
data_available
comparability_class
paper_role
verification_status
notes
```

`verification_status` 只能：

```text
VERIFIED_PRIMARY
VERIFIED_WITH_LIMITATION
IDENTITY_ONLY
EXCLUDED_NOT_CLOSE
UNRESOLVED
```

---

# Part V — Comparability audit

## 12. Comparability class

每篇只能：

```text
DIRECTLY_COMPARABLE
PARTIALLY_COMPARABLE
CONTEXT_ONLY
NOT_COMPARABLE
```

`DIRECTLY_COMPARABLE` 必须高度匹配：

```text
same/equivalent task
same target
same evaluation unit
same benchmark/split
compatible metric
compatible information access
```

必须逐项核验：dataset、split、target、trajectory vs step、input access、evaluation unit、metric、training data、judge/reward role、test-time usage。

不得因为 metric 名字相同就认为可比。

---

## 13. Cross-paper numeric gate

只有 `DIRECTLY_COMPARABLE` 才允许进入 paper-facing numeric head-to-head candidate。

如果没有：

```text
NO_VALID_CROSS_PAPER_HEAD_TO_HEAD
```

这是合法结果，不得硬凑排行榜。

---

# Part VI — Verified result extraction

## 14. 每篇最多抽取 3 条 relevant results

生成：

```text
artifacts/a3_2_verified_result_claims.csv
```

字段：

```text
work_id
result_id
claim_type
verbatim_location
paraphrased_result
metric
value
dataset
split
evaluation_unit
scope
comparability_class
allowed_use
forbidden_use
primary_source_identifier
```

`verbatim_location` 只记录 section/table/figure/page 定位，不复制长段原文。

所有数字必须能定位到 primary source。

---

# Part VII — AgentRewardBench relationship

## 15. 单独生成

```text
docs/a3_2_agentrewardbench_relationship.md
```

必须回答：

1. AgentRewardBench 原论文研究问题；
2. 本项目复用了什么；
3. 本项目没有复用什么；
4. 本项目新增研究问题；
5. 为什么不是简单重跑原论文；
6. 共享 dataset 对 external-validity claim 的限制；
7. official blind held-out 在本文内部能证明什么、不能证明什么。

必须明确：

```text
blind held-out within evaluated benchmark families
!=
independent external benchmark validation
```

---

# Part VIII — Positioning matrix

## 16. 输出

```text
artifacts/a3_2_positioning_matrix.csv
```

维度建议：

```text
work
web_agent_specific
trajectory_level
step_level
task_agnostic
requires_large_semantic_model
requires_training
human_annotation_role
success_evaluation
side_effect_evaluation
repetition_or_process_failure
blind_heldout_protocol
efficiency_analysis
interpretability_diagnostics
main_goal
comparability
```

必须包含 `THIS_WORK`，其字段只能来自 frozen project evidence。

---

# Part IX — Related-work taxonomy

## 17. 输出

```text
docs/a3_2_related_work_taxonomy.md
```

建议分：

```text
A. Outcome / trajectory evaluators
B. Process reward models / step-level verification
C. THIS_WORK — lightweight task-agnostic structural trajectory evaluation
```

实际分类以 primary-source audit 为准。

必须解释 THIS_WORK 与 LLM judge、reward model、PRM、benchmark construction、task-specific rule evaluator 的区别。

---

# Part X — Positioning / novelty freeze

## 18. 输出

```text
docs/a3_2_positioning_and_novelty_contract.md
```

### Allowed wording

仅在证据支持时允许：

```text
systematic study of lightweight structural trajectory signals
blind-first frozen held-out evaluation
cost / interpretability characterization
task-agnostic structural representation within the studied benchmark setting
```

### Forbidden wording

至少：

```text
first automatic evaluator for agents
first web-agent trajectory evaluator
first reward model for web agents
state of the art
outperforms LLM judges
replaces LLM judges
generalizes to unseen benchmarks
first process-aware evaluator
```

除非 primary-source audit + frozen project evidence 明确支持，否则禁止。

---

# Part XI — Citation freeze

## 19. Citation registry

生成：

```text
artifacts/a3_2_citation_registry.csv
```

字段：

```text
citation_key
work_id
canonical_title
authors
year
venue
doi
arxiv_id
primary_url
bibtex_source
verification_status
paper_sections
```

## 20. BibTeX

生成：

```text
paper/references/a3_2_verified_related_work.bib
```

BibTeX 仅来自 publisher/proceedings/arXiv official metadata。

不得猜 DOI、pages、volume、venue。

无正式 venue 就按 arXiv/preprint。

---

# Part XII — Paper-facing positioning table

## 21. 输出

```text
paper/tables/Table_Related_Work_Positioning.md
paper/tables/Table_Related_Work_Positioning.tex
```

默认只做属性对比，不放性能数字。

建议列：

```text
Work
Evaluation level
Web-specific
Signal type
Task-agnostic
Large semantic model required
Training required
Primary use
Directly comparable?
```

不得把 CONTEXT_ONLY work 做成性能排行榜。

---

# Part XIII — Related Work writing skeleton

## 22. 输出

```text
docs/a3_2_related_work_writing_skeleton.md
```

不是完整正文，只生成：

```text
Paragraph 1 — trajectory / outcome evaluators
Paragraph 2 — reward/process models
Paragraph 3 — gap and THIS_WORK positioning
```

每段仅含：claim bullets、citation keys、allowed wording、forbidden wording。

---

# Part XIV — Search completeness / stopping rule

## 23. Search log

生成：

```text
artifacts/a3_2_literature_search_log.csv
```

字段至少：query、date、source、candidate、included_or_excluded、reason。

## 24. 强制停止规则

达到以下条件后停止扩张：

```text
3 mandatory Tier-4 works verified
+
at least 3 recent closest-work candidates reviewed
+
no newly found work materially changes THIS_WORK positioning
+
maximum 5 additional included closest works
```

不得追求 exhaustive survey。

---

# Part XV — Summary / report

## 25. Machine summary

生成：

```text
artifacts/a3_2_run_summary.json
```

至少：

```text
stage_determination
search_cutoff_date
mandatory_works_verified
additional_candidates_reviewed
additional_works_included
verified_primary_count
verified_with_limitation_count
identity_only_count
unresolved_count
directly_comparable_count
partially_comparable_count
context_only_count
not_comparable_count
cross_paper_head_to_head_status
citation_count
bibtex_count
input_hashes
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
```

## 26. Stage report

生成：

```text
docs/stage_a3_2_literature_baseline_verification_report.md
```

至少覆盖：阶段判定、commits、cutoff、source policy、mandatory 3、freshness scan、comparability、numeric-comparison decision、AgentRewardBench relationship、positioning、novelty contract、citation registry、Related Work table、unresolved items、counters、Git、next state。

---

# 27. Tests / verifiers

至少验证：

1. Git start clean；
2. A3.1/A2.3 result reachable；
3. claim matrix SHA exact；
4. mandatory 3 都有 primary source；
5. every included work 有 canonical identity；
6. every reported number 有 primary-source location；
7. search snippet 未作为 final evidence；
8. 无 invented DOI/venue/pages；
9. comparability class valid；
10. CONTEXT_ONLY 不进入 numeric ranking；
11. AgentRewardBench relationship 文档存在；
12. blind held-out != external validation 明确；
13. THIS_WORK positioning 只使用 frozen claims；
14. prohibited novelty claims 已冻结；
15. citation registry ↔ BibTeX consistent；
16. Related Work table 无无效 numeric head-to-head；
17. stopping rule satisfied；
18. no external dataset download/run；
19. scientific-operation counters 全 0；
20. Git final clean。

---

# 28. Commit discipline

### A3.2a — prereg

```text
chore: preregister A3.2 literature verification
```

仅 taskbook，然后 STOP。

### A3.2b — implementation

```text
chore: implement A3.2 literature verification registry
```

### A3.2c — result

```text
docs: freeze A3.2 related-work evidence
```

不得 amend；fix 独立 commit，保留 provenance。

---

# 29. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

mandatory Tier-4、bounded freshness scan、registry、comparability audit、AgentRewardBench relationship、positioning matrix、novelty contract、citation registry/BibTeX、Related Work table、writing skeleton 全部完成；科学计数全 0；Git clean。

### PASS_WITH_CONDITIONS

允许：

```text
2026 preprint 尚无正式 venue
个别 DOI 不存在
某篇仅 IDENTITY_ONLY
无 DIRECTLY_COMPARABLE cross-paper baseline
```

只要如实记录。

### STOP

包括：primary-source contradiction、mandatory identity unresolved、snippet 当 final evidence、unsupported number/bibliography、invalid ranking、claim/novelty upgrade、external dataset execution、scientific computation、Git provenance 不清。

---

# 30. 最终汇报

Codex 必须汇报：

```text
阶段判定

A3.2 prereg commit
implementation commit
result commit
fix commits
amend

search cutoff date
mandatory works verified
additional candidates reviewed
additional works included

VERIFIED_PRIMARY count
VERIFIED_WITH_LIMITATION count
IDENTITY_ONLY count
UNRESOLVED count

DIRECTLY_COMPARABLE count
PARTIALLY_COMPARABLE count
CONTEXT_ONLY count
NOT_COMPARABLE count

cross-paper head-to-head status
AgentRewardBench relationship conclusion
positioning summary
allowed novelty claims
prohibited novelty claims
citation registry count
BibTeX count
Related Work table status
writing skeleton status

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

tests/verifiers
warnings
Git status

report path
registry path
positioning matrix path
novelty contract path
citation registry path
BibTeX path
Related Work table path
writing skeleton path

WAIT_FOR_HUMAN_A3_2_REVIEW
```

然后立即停止，不得自动执行 A3.3。
