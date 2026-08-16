# Stage A1.8：研究证据总审计与 Paper Claim Matrix

## 1. 阶段定位

Stage A1.7 已完成并通过人工阶段门审查，判定：

```text
PASS_WITH_CONDITIONS
```

截至 A1.7，项目已经完成以下证据链：

```text
A1.2  最小 baseline：有没有信号
A1.3  Primary LOBO：能否跨 Benchmark
A1.4  LOMO：能否跨 Agent/model（model-only，任务已见）
A1.5  Structural ablation：结构信号靠什么
A1.6  Group-aware bootstrap：这些差异稳不稳
A1.7  Frozen dense semantics：复杂语义表示有没有稳定增量
```

因此 A1.8 **不是新的模型实验阶段**。

A1.8 只做：

> 把 A1.2–A1.7 的正式证据统一收口，明确论文里哪些结论可以写、哪些只能保守写、哪些不能写，并决定是否已经满足“最终方法冻结 / test 前准备”的条件。

本阶段不得新增任何模型、预测、阈值、特征或新的 bootstrap comparison。

---

## 2. A1.8 的核心问题

A1.8 必须回答：

1. 当前每个 scientific claim 的最强支持证据来自哪个 Stage；
2. 每个 claim 的证据等级是什么；
3. 哪些 claim 被后续 Stage 降级或修正；
4. Success、Side Effect、Looping 三个 target 各自最可靠的论文结论是什么；
5. 哪些表述属于过度结论，论文中必须禁止；
6. 当前是否还缺“阻塞投稿主线”的关键 dev 实验；
7. 如果不存在阻塞实验，是否可进入“最终方法冻结 / test 前预注册”；
8. 最终 test 前，每个 target 应冻结哪个候选方法、什么角色；
9. 哪些结果只能作为 exploratory / diagnostic / auxiliary；
10. 当前论文故事是否足够连贯，还是还存在无法解释的关键矛盾。

---

## 3. 本阶段绝对禁止

不得运行：

```text
任何 .fit()
任何 embedding forward
任何新 prediction
任何新 threshold selection
任何新 config selection
任何新 feature engineering
任何新 ablation
任何新 bootstrap pairwise comparison
任何新 seed
任何 fusion
第二 embedding 模型
LLM Judge
secondary LOBO
新 LOMO
joint task+model OOD
test
```

A1.8 是 evidence audit，不是 score hunting。

---

## 4. 必须读取的正式来源

优先级：

```text
machine-readable artifact > formal stage report > human summary
```

至少读取：

### A1.2

```text
artifacts/a1_2_run_summary.json
artifacts/a1_2_*metrics*.csv
artifacts/a1_2_*predictions*.csv
正式 A1.2 report
```

### A1.3

```text
artifacts/a1_3_lobo_run_summary.json
artifacts/a1_3_lobo_domain_metrics.csv
artifacts/a1_3_lobo_macro_metrics.csv
artifacts/a1_3_lobo_pooled_metrics.csv
artifacts/a1_3_lobo_predictions.csv
docs/stage_a1_3_primary_lobo_report.md
```

### A1.4

```text
artifacts/a1_4_lomo_run_summary.json
artifacts/a1_4_lomo_model_metrics.csv
artifacts/a1_4_lomo_macro_metrics.csv
artifacts/a1_4_lomo_pooled_metrics.csv
artifacts/a1_4_lomo_coverage_matrix.csv
docs/stage_a1_4_leave_one_model_out_report.md
```

### A1.5

```text
artifacts/a1_5_run_summary.json
artifacts/a1_5_domain_metrics.csv
artifacts/a1_5_macro_metrics.csv
artifacts/a1_5_pooled_metrics.csv
artifacts/a1_5_structural_ablation_deltas.csv
docs/stage_a1_5_structural_mechanism_ablation_report.md
```

### A1.6

```text
artifacts/a1_6_run_summary.json
artifacts/a1_6_primary_paired_delta_summary.csv
artifacts/a1_6_domain_bootstrap_summary.csv
artifacts/a1_6_macro_bootstrap_summary.csv
artifacts/a1_6_pooled_bootstrap_summary.csv
docs/stage_a1_6_group_aware_bootstrap_report.md
```

### A1.7

```text
artifacts/a1_7_run_summary.json
artifacts/a1_7_domain_metrics.csv
artifacts/a1_7_macro_metrics.csv
artifacts/a1_7_pooled_metrics.csv
artifacts/a1_7_comparison_to_a1_3.csv
artifacts/a1_7_bootstrap_primary_summary.csv
docs/stage_a1_7_frozen_dense_semantic_baseline_report.md
```

### Protocol / provenance

```text
artifacts/lobo_primary_manifest.csv
artifacts/leave_one_model_out_manifest.csv
configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
research/01_DECISION_LOG.md
```

如果精确路径不同，只允许通过对应 stage machine summary 解析正式路径。

不得读取 test 内容、test label、test prediction 或 test metric。

---

## 5. 源文件一致性审计

A1.8a 在生成 claim matrix 前必须检查：

1. A1.2–A1.7 formal reports 存在；
2. A1.2–A1.7 machine summaries 存在；
3. 每个正式 stage commit 能从 Git 历史定位；
4. 正式 report 中若存在 `recorded by enclosing result commit`，必须从 Git 历史补齐 exact SHA；
5. A1.3 B2 与 A1.5 S0 的一致性结论保持成立；
6. A1.6 point-estimate regression guard 保持成立；
7. A1.7 B2/B3 frozen comparison 的 source values 与 A1.3 一致；
8. test access 记录始终为 0；
9. 所有正式 stage 的禁止实验计数保持 0；
10. 若 machine summary 与 formal report 数值冲突：`STOP`，不得自行选择有利数字。

A1.8 可以做纯文档 SHA 补全，但不得修改科学数值。

---

## 6. Evidence Registry

生成：

```text
artifacts/a1_8_evidence_registry.csv
```

每行对应一个“可引用证据单元”。

至少包含：

```text
evidence_id
stage_id
target
protocol
method_or_variant
metric_or_estimand
point_estimate
ci_lower
ci_upper
valid_fraction
sample_size
positive_count
support_role
source_artifact
source_row_key
formal_commit
notes
```

`support_role` 只能从以下取值：

```text
primary
secondary
exploratory
diagnostic
integrity_only
```

不得把 exploratory/diagnostic 自动升级为 primary。

---

## 7. Claim Matrix

生成：

```text
artifacts/a1_8_claim_matrix.csv
```

每行一个 scientific claim。

字段至少：

```text
claim_id
target
claim_short
claim_precise
claim_level
best_supporting_evidence_ids
counterevidence_or_limitation_ids
allowed_wording_cn
allowed_wording_en
forbidden_wording_cn
forbidden_wording_en
paper_section
status
reason
```

### status 只允许：

```text
SUPPORTED
SUPPORTED_WITH_CONDITIONS
DESCRIPTIVE_ONLY
INSUFFICIENT_EVIDENCE
PROHIBITED
```

### claim_level 只允许：

```text
core
supporting
auxiliary
limitation
```

---

## 8. 必须审计的核心 claims

至少包含以下 claims，不得遗漏。

### C1 Success：跨 Benchmark 结构信号存在

候选表述：

> Lightweight structural trajectory features provide stable cross-Benchmark signal for Success prediction under Primary LOBO.

必须使用 A1.3 + A1.6 支持。

预期状态：

```text
SUPPORTED
```

除非源文件与当前记录冲突。

---

### C2 Success：B2 稳定优于 B3

A1.6 已显示 B2-B3 paired CI 跨 0。

预期：

```text
INSUFFICIENT_EVIDENCE
```

禁止写：

```text
结构特征显著优于TF-IDF
B2稳定优于B3
```

允许写：

> B2 had a higher point estimate under Primary LOBO, but the paired bootstrap interval included zero.

---

### C3 Success：termination 是主要决定因素

A1.5 point dependency + A1.6 uncertainty 必须联合解释。

预期：

```text
INSUFFICIENT_EVIDENCE
```

允许：

> Termination carries predictive information, but removing it did not produce a stable degradation under group-aware bootstrap.

禁止：

```text
Success主要由termination决定
termination导致Success
```

---

### C4 Success：极简3特征足以匹配 full13

A1.5 S6 点估计接近，A1.6 S6-S0 CI 跨0。

预期：

```text
SUPPORTED_WITH_CONDITIONS
```

允许：

> A three-feature representation was highly competitive with the full structural set; the paired difference remained uncertain.

不得写“等价”“证明一样好”。

---

### C5 Success：Dense semantics 有稳定跨 Benchmark 信号

A1.7 Q1。

预期：

```text
SUPPORTED
```

---

### C6 Success：Dense semantics 稳定优于 B2/B3

A1.7 Q2/Q3 AP CI 跨0；Q3 F1 反而稳定下降。

预期：

```text
INSUFFICIENT_EVIDENCE
```

允许：

> Dense embeddings produced strong cross-Benchmark signal but no clear incremental AP gain over frozen lightweight baselines.

---

### C7 Looping：结构信号稳定跨 Benchmark

A1.3 + A1.6 P5。

预期：

```text
SUPPORTED
```

---

### C8 Looping：直接 repetition 特征有稳定增量

A1.6 P6 macro AP CI < 0。

预期：

```text
SUPPORTED
```

但必须同时包含：

> 删除 repetition 后剩余模型仍然很强。

禁止写：

```text
Looping完全由重复特征决定
```

---

### C9 Looping：复杂语义表示是必要的

A1.7 未显示 B4 稳定优于 B2。

预期：

```text
INSUFFICIENT_EVIDENCE
```

更合适 supporting claim：

> No clear evidence was found that dense semantic representations add cross-Benchmark value over the lightweight structural baseline for Looping.

---

### C10 Side Effect：结构特征可以稳定预测

A1.3/A1.5 不支持。

预期：

```text
PROHIBITED
```

---

### C11 Side Effect：语义表示有潜力

A1.2 B3、A1.7 B4 可作为苗头，但只有12 positives，CI宽。

预期：

```text
DESCRIPTIVE_ONLY
```

允许：

> Semantic representations showed promising point estimates for Side Effect, but statistical support is weak because only 12 positive dev trajectories are available.

禁止：

```text
Side Effect已实现robust cross-Benchmark generalization
Side Effect已经解决
```

---

### C12 Cross-model：信号跨 Agent/model

A1.4 是 model-only holdout，但 external train/valid 共享 task group。

预期：

```text
SUPPORTED_WITH_CONDITIONS
```

允许：

> Signals transferred to held-out Agent models when the underlying tasks were represented on the training side.

禁止：

```text
同时泛化到新模型和新任务
joint task+model OOD
```

---

### C13 “模型越复杂越好”

A1.7 不支持。

预期：

```text
PROHIBITED
```

允许更弱的结论：

> Increasing representation complexity did not yield a clear, uniform cross-Benchmark advantage across targets.

---

### C14 不同评价维度需要不同信息复杂度

这是综合性论文 thesis，不是单一实验结果。

必须引用：

```text
Success: B2/B4
Looping: B2/S6/B4
Side Effect: B2/B3/B4 + sparse positives
```

预期：

```text
SUPPORTED_WITH_CONDITIONS
```

允许：

> The three evaluation dimensions exhibit different empirical relationships with structural and semantic representations.

禁止：

```text
我们证明了不同维度存在固定的信息复杂度层级
```

---

## 9. Threats-to-Validity Matrix

生成：

```text
artifacts/a1_8_threats_to_validity.csv
```

至少包含：

```text
threat_id
category
description
affected_claims
severity
mitigated_by
remaining_risk
paper_wording
blocking_for_test
```

必须审计：

### T1 小 dev 数据

约 196 trajectories / 51 task groups。

### T2 Side Effect 仅12 positives

最高优先级 limitation。

### T3 Side Effect / AssistantBench 单一负类域

### T4 A1.4 LOMO 同任务 counterpart=100%

不能解释 joint task+model OOD。

### T5 Primary LOBO 仅4个 Benchmark group

macro 只有4个域。

### T6 Probability calibration / threshold transfer

A1.7 Success WorkArena AP高但F1低，只能描述为 threshold-transfer/calibration-like symptom；未经专门 calibration 实验不得下结论。

### T7 Looping 与结构代理变量概念接近

虽 A1.5/A1.6 排除了“完全由 repetition 两项决定”，仍需作为 construct-validity limitation。

### T8 Dense embedding pooling 是工程近似

超长 trajectory 采用 chunk + weighted pooling，不等价于完整160k-token全上下文理解。

### T9 Dev-driven method selection

A1.2–A1.7 都是开发阶段，最终方法必须在 test 前冻结。

### T10 单一数据集 / annotation source

不得把结论扩展到所有 Agent benchmark / 所有 Judge 数据。

---

## 10. Paper Contribution Matrix

生成：

```text
artifacts/a1_8_paper_contribution_matrix.csv
```

至少分成：

```text
Contribution 1: empirical cross-Benchmark signal characterization
Contribution 2: representation complexity comparison
Contribution 3: target-specific evidence requirements / heterogeneity
Contribution 4: rigorous grouped evaluation + uncertainty methodology
```

每个 contribution 必须列：

```text
supporting claims
supporting stages
strongest metric evidence
key limitation
reviewer challenge
response supported by current evidence
```

如果某 contribution 无法由现有证据支持，标记：

```text
DROP_FROM_PAPER
```

不得为了“凑贡献”创造新表述。

---

## 11. Final Candidate Method Freeze Proposal

A1.8 需要生成：

```text
artifacts/a1_8_final_method_freeze_proposal.csv
```

但 **A1.8 只提出 freeze proposal，不访问 test**。

必须分别给 Success / Side Effect / Looping 指定：

```text
candidate_method
role
selection_rationale
known_limitation
eligible_for_confirmatory_test
```

### Success 默认提案

优先候选：

```text
B2 structural LR
```

理由：

- A1.6 stable positive cross-Benchmark signal；
- B4 没有稳定 AP 增量；
- B4 macro F1 相对 B2 稳定下降；
- B2 更简单、可解释、成本低。

如果 Codex 从正式 artifacts 发现与以上不一致，STOP，不得自行改候选。

### Looping 默认提案

优先候选：

```text
B2 structural LR
```

理由：

- 强、稳定跨 Benchmark；
- repetition 增量真实但不是全部；
- B4 没有明确增量。

S6 只作为 compact auxiliary method，不自动替代 B2 primary。

### Side Effect 默认提案

角色固定：

```text
exploratory-only
```

候选方法可提案为：

```text
B4 dense embedding LR
```

但必须注明：

- 仅12 positives；
- B4 vs B3 不确定；
- 不能作为强 confirmatory claim。

`eligible_for_confirmatory_test` 默认：

```text
false_or_exploratory_only
```

除非后续人工阶段门明确批准。

---

## 12. Paper Table / Figure Plan

生成：

```text
artifacts/a1_8_paper_table_figure_plan.csv
```

只做规划，不生成经过美化的最终论文图。

至少建议：

### Table 1 — Dataset / target support

- target counts
- positives
- task groups
- Benchmark coverage
- Side Effect sparsity

### Table 2 — Primary LOBO baselines

- B0–B4
- Success / Side Effect / Looping
- macro AP/F1
- role / caveat

### Table 3 — Structural ablation

- S0/S1/S2/S5/S6
- Success / Looping
- delta AP
- bootstrap interpretation

### Figure 1 — Evidence map

Target × representation family：

```text
structural
TF-IDF
Dense semantic
```

展示 point + CI / support role。

### Figure 2 — Cross-Benchmark uncertainty

重点：

```text
Success B2 AP lift
Looping B2 AP lift
Looping no-repetition delta
Success B4-B2 / B4-B3 uncertainty
```

不得绘制暗示 Side Effect 已 robust 的图。

---

## 13. Reviewer Attack List

生成：

```text
artifacts/a1_8_reviewer_attack_matrix.csv
```

至少包含以下 reviewer challenge：

1. “196条太少。”
2. “Side Effect 只有12个正例，结论不可信。”
3. “Looping 特征是不是标签定义泄漏？”
4. “LOMO 同任务出现，不是真正 OOD。”
5. “为什么不用更大的 LLM Judge？”
6. “B4 为什么没有稳定赢 B2？”
7. “是否只是 Benchmark identity / model identity shortcut？”
8. “为什么 pooled AP 可以比较不同 held-out models？”
9. “为什么不用 test 调参？”
10. “Dense embedding 对160k-token轨迹使用 chunk pooling，会不会损失信息？”

每项必须给：

```text
current_evidence_response
remaining_weakness
needs_new_experiment
```

不得编造实验来回答 reviewer。

---

## 14. Remaining Evidence Decision Gate

生成：

```text
artifacts/a1_8_remaining_evidence_decision.json
```

只允许以下结论之一：

### READY_FOR_FINAL_METHOD_FREEZE

含义：

> 当前 dev 证据已经足够决定最终方法；继续堆 dev 实验的边际价值低。下一阶段可进行最终 test 前预注册与方法冻结。

### ONE_BLOCKING_DEV_EXPERIMENT_REMAINS

必须明确：

```text
exact_question
why_blocking
minimal_experiment
why_existing_evidence_cannot_answer
```

只能有 **一个** blocking experiment。

不得列“最好再做十个实验”。

### NOT_READY_RESEARCH_DIRECTION_WEAK

只有在核心主张本身不再成立时才能使用。

---

## 15. 推荐判据

如果以下都成立：

1. Success stable cross-Benchmark structural signal；
2. Looping stable cross-Benchmark structural signal；
3. A1.6 uncertainty 已完成；
4. B4 已完成 semantic complexity check；
5. 没有 unresolved leakage / protocol error；
6. test 始终封存；
7. 剩余问题主要是 limitation 而非“主结果是真是假”；

则默认：

```text
READY_FOR_FINAL_METHOD_FREEZE
```

Side Effect 稀疏本身不应强迫无限追加 dev 实验；更合理做法是降低其论文角色。

---

## 16. A1.8a：预注册 Evidence Audit

在生成最终 claim status 前：

1. 编写 audit config；
2. 冻结 claim list C1–C14；
3. 冻结 status taxonomy；
4. 冻结 threat list T1–T10；
5. 冻结 final-method proposal rule；
6. 冻结 remaining-evidence decision rule；
7. 编写 parser / verifier；
8. 编写 tests；
9. 不读取 test。

生成：

```text
configs/stage_a1_8_evidence_audit.yaml
scripts/run_stage_a1_8_evidence_audit.py
tests/test_stage_a1_8_evidence_audit.py
artifacts/a1_8_prerun_integrity.json
```

提交：

```text
chore: preregister paper evidence audit
```

A1.8a 不得根据最终 claim matrix 临时新增/删除 claim。

---

## 17. A1.8b：正式 Evidence Audit

运行前：

```text
git status
```

必须 clean。

正式流程：

1. source/path/hash guard；
2. formal commit resolution；
3. evidence registry；
4. C1–C14 claim adjudication；
5. threats-to-validity matrix；
6. contribution matrix；
7. final-method freeze proposal；
8. table/figure plan；
9. reviewer attack matrix；
10. remaining-evidence decision；
11. formal report；
12. independent verifier；
13. repository tests。

提交：

```text
analysis: consolidate paper evidence and claims
```

不得 amend A1.8a。

---

## 18. 自动判定边界

A1.8 可以自动根据冻结规则标记 claim status。

但不得自动：

```text
访问 test
开始最终 test
新增模型
改变论文 target 主次
删除不利结果
```

最终是否进入 test 前 freeze，必须等待人工阶段门。

---

## 19. 测试要求

至少新增并通过：

1. A1.2–A1.7 正式机器摘要全部可定位；
2. A1.2–A1.7 正式报告全部可定位；
3. exact commits 可解析；
4. machine summary/report 核心指标一致；
5. A1.3 B2/A1.5 S0 consistency 仍成立；
6. A1.6 point regression guard 仍成立；
7. A1.7 frozen B2/B3 source values 一致；
8. claim list 恰好包含 C1–C14；
9. status 只能使用冻结枚举；
10. 每个 SUPPORTED claim 至少有一个 primary evidence；
11. 每个 SUPPORTED_WITH_CONDITIONS claim 有 limitation；
12. DESCRIPTIVE_ONLY 不进入 core contribution；
13. PROHIBITED claim 必须存在 forbidden wording；
14. Side Effect robust wording 必须被禁止；
15. LOMO joint-OOD wording 必须被禁止；
16. causal wording 必须被禁止；
17. “B4稳定优于B2/B3”必须被禁止；
18. threat list至少T1–T10；
19. final-method proposal三个 target 恰好各一行；
20. Success primary proposal=B2；
21. Looping primary proposal=B2；
22. Side Effect role=exploratory-only；
23. remaining-evidence decision 只能三选一；
24. 不存在 `.fit()`；
25. 不存在模型 forward；
26. 不生成 prediction；
27. 不生成新 bootstrap draws；
28. test access=0；
29. 禁止实验=0；
30. Git最终 clean。

---

## 20. 输出产物

生成：

```text
artifacts/a1_8_evidence_registry.csv
artifacts/a1_8_claim_matrix.csv
artifacts/a1_8_threats_to_validity.csv
artifacts/a1_8_paper_contribution_matrix.csv
artifacts/a1_8_final_method_freeze_proposal.csv
artifacts/a1_8_paper_table_figure_plan.csv
artifacts/a1_8_reviewer_attack_matrix.csv
artifacts/a1_8_remaining_evidence_decision.json
artifacts/a1_8_run_summary.json

docs/stage_a1_8_evidence_audit_report.md
docs/paper_claims_allowed_and_forbidden.md
docs/paper_evidence_snapshot_a1_8.md
```

---

## 21. 正式报告必须包含

`docs/stage_a1_8_evidence_audit_report.md` 至少包含：

1. 阶段判定；
2. A1.8 commits；
3. A1.2–A1.7 evidence chain；
4. source/provenance audit；
5. C1–C14 claim matrix；
6. 核心 claim 的 allowed wording；
7. 核心 prohibited wording；
8. Success 当前最强结论；
9. Side Effect 当前最强结论；
10. Looping 当前最强结论；
11. A1.4 cross-model 解释边界；
12. A1.5/A1.6 对 shortcut 解释的修正；
13. A1.7 对“复杂度升级”的结论；
14. threats to validity；
15. contribution matrix；
16. reviewer attacks；
17. final method freeze proposal；
18. remaining evidence decision；
19. 是否建议进入最终方法冻结；
20. test访问=0；
21. 禁止实验=0；
22. 明确停止等待人工审查。

---

## 22. 阶段判定

### PASS

技术上：

- 所有正式来源一致；
- C1–C14全部裁决；
- threats/contributions/reviewer attacks 完整；
- final-method proposal 完整；
- remaining-evidence decision 唯一；
- 无新模型/新统计自由度；
- test=0；
- Git clean。

### PASS_WITH_CONDITIONS

例如：

- 某些 claim 必须降级；
- Side Effect 只能 exploratory；
- 某 contribution 必须删除；
- reviewer challenge 仍有无法完全解决的 limitation。

这不代表技术失败。

### STOP

包括：

- 正式 artifacts 数值冲突；
- commit/provenance 无法追溯；
- claim matrix 偷偷省略不利证据；
- 把 exploratory 升级成 primary；
- 生成新模型结果；
- 新 bootstrap 挖掘；
- test访问。

---

## 23. 最终汇报

Codex 最终必须汇报：

1. 阶段判定；
2. A1.8a/A1.8b及任何fix commit；
3. A1.2–A1.7 provenance audit结果；
4. C1–C14最终 status；
5. 5条最强可写 claim；
6. 5条明确禁止 claim；
7. Success 最终证据摘要；
8. Side Effect 最终证据摘要；
9. Looping 最终证据摘要；
10. threats-to-validity top 5；
11. contribution matrix保留/删除项；
12. reviewer attack top 5；
13. final-method freeze proposal；
14. remaining-evidence decision；
15. 是否建议进入 final method freeze；
16. 是否存在任何 `.fit()` / model forward / new prediction；
17. test访问=0；
18. 禁止实验=0；
19. tests；
20. Git status；
21. 正式报告和机器摘要路径。

完成后必须停止。

不得自动开始 final test 或任何新模型实验。
