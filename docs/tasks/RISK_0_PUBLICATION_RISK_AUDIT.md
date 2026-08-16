# RISK-0：Publication Risk & Competitiveness Audit

## 0. Stage purpose

本阶段位于 `MANUSCRIPT_EVIDENCE_FROZEN / READY_FOR_MANUSCRIPT_DRAFTING` 之后、正式论文写作之前。

目标：**仅基于仓库持久化证据，对项目进行独立、保守、可追溯的投稿风险审计。**

必须分别回答：

1. **Scientific Validity (SVS)：这项研究站不站得住？**
2. **Publication Competitiveness (PCS)：站得住以后，是否形成了一篇有竞争力的期刊论文？**

严禁把 SVS 与 PCS 平均成一个“论文总分”。

最终必须输出：

- Scientific Validity Score (SVS)
- Core Publication Competitiveness Score (Core PCS)
- Target-specific PCS（仅当 prereg 前已有冻结目标期刊 dossier 时）
- Scientific Critical Risks
- Publication Critical Risks
- Major / Moderate / Minor Risk Register
- Reviewer Objection Matrix
- `GO / GO_WITH_MITIGATION / NO_GO`

本阶段不是录用率预测，不得给伪精确接受概率。

---

# 1. Audit principles

## 1.1 Repository-only evidence

事实依据只能来自 Git 仓库持久化资产：

- preregistrations / taskbooks
- formal stage reports
- machine summaries
- claim/evidence registries
- numeric consistency maps
- Git commits / hashes
- prediction artifacts
- tables / figures
- literature / citation registries
- limitations ledgers
- manuscript evidence package
- source code / verifier outputs

禁止使用：

- ChatGPT 聊天记录
- 模型记忆
- 未持久化口头说明
- “根据上下文应该是”
- 无来源补全

仓库无法支持的事实必须标为 `NOT_VERIFIED`，不得猜测。

## 1.2 Evidence-first

执行顺序冻结为：

```text
Phase 1  Repository Evidence Inventory（只取证，不评分）
Phase 2  Scientific Validity Primary Audit
Phase 3  Publication Competitiveness Primary Audit
Phase 4  Critical Risk Audit
Phase 5  Adversarial Re-review
Phase 6  Conservative Score Reconciliation
Phase 7  Final Publication Assessment
```

## 1.3 No rubric drift

本 taskbook 的指标、权重、0–4 anchors、caps、Critical Risk 定义、decision thresholds 一经 preregister 即冻结，不得根据实际结果临时调整。

## 1.4 No new science / no new literature

全部必须为 0：

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

PC1–PC5 只能使用 A3.2 / A3.2-addendum 已验证 literature assets。

如果没有 prereg 前冻结的 target-journal dossier：

```text
PC6 = NOT_SCORED
Target-specific PCS = NOT_AVAILABLE
```

不得在 RISK-0 临时上网挑期刊或扩张文献。

---

# 2. Hard gates

正式审计前必须验证：

```text
git status --porcelain = clean
A3.3 result = 152f03134f2a9c62cafbb380c625766d4c6b197a
A3.2 addendum result = bb9dc52467f58769f833e501aa5fa96cb1be9937
A1.11 final claim matrix SHA = 2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
Success = CONFIRMATORY_SUPPORTED
Looping = CONFIRMATORY_SUPPORTED
Side Effect = EXPLORATORY_SUPPORTED
MANUSCRIPT_EVIDENCE_FROZEN
READY_FOR_MANUSCRIPT_DRAFTING
```

任一失败：`STOP`。

---

# 3. Preregistration gate

如果：

```text
docs/tasks/RISK_0_PUBLICATION_RISK_AUDIT.md
```

尚未 Git tracked，只允许：

```text
git add docs/tasks/RISK_0_PUBLICATION_RISK_AUDIT.md
git commit -m "chore: preregister RISK-0 publication audit"
STOP
```

不得同轮开始审计。

---

# 4. Universal scoring protocol

所有 SV / PC 子项统一使用 `0/1/2/3/4`。

| Score | Frozen definition |
|---:|---|
| 4 | 有直接、完整、可追溯证据；达到该子项预定义的强/最佳实践水平 |
| 3 | 基本成立；有轻微限制，但不实质削弱核心结论/竞争力 |
| 2 | 部分成立；存在实质限制，是明确短板，但不足以直接推翻核心研究 |
| 1 | 明显薄弱；构成 Major concern |
| 0 | 缺失、存在反证、或构成严重有效性/发表障碍 |

每个子项评分前必须记录：

```text
Evidence Status:
VERIFIED / PARTIALLY_VERIFIED / NOT_VERIFIED / CONTRADICTED / NOT_APPLICABLE

Evidence Confidence:
HIGH / MEDIUM / LOW

Judgment Type:
EVIDENCE_DRIVEN / MIXED / EXPERT_JUDGMENT
```

`Score = 4` 必须存在持久化直接 supporting evidence。

不得因为：

- 总体印象好
- 做了很多实验
- Git 很规范
- metric 数值高

而自动给与该事实无关的高分。

---

# 5. Scientific Validity Score (SVS) — 100

| Dimension | Weight |
|---|---:|
| SV1 Research Design Validity | 15 |
| SV2 Data & Label Validity | 15 |
| SV3 Protocol & Independence | 20 |
| SV4 Evaluation & Statistical Validity | 20 |
| SV5 Robustness & Conclusion Boundaries | 15 |
| SV6 Claim–Evidence & Reproducibility | 15 |

## SV1 — Research Design Validity (15)

**Question:** 研究问题与实验设计在逻辑上是否真正对应？

| Subcriterion | Internal weight |
|---|---:|
| SV1.1 Research Question Clarity & Falsifiability | 20% |
| SV1.2 Construct Validity | 20% |
| SV1.3 Design–Question Alignment | 25% |
| SV1.4 Alternative-Explanation Control | 20% |
| SV1.5 Inference & Scope Alignment | 15% |

### SV1.1 Research Question Clarity & Falsifiability
4：问题明确、具体、可证伪，有稳定支持/不支持边界。  
3：问题清楚且基本可证伪，但部分边界后续才收紧。  
2：方向明确但较宽，有明显 post-hoc 解释空间。  
1：问题主要由结果反推，很难定义失败。  
0：无稳定研究问题。

### SV1.2 Construct Validity
审 labels、representation、proxy/shortcut、construct overlap、outcome/process/morphology 是否匹配。  
4：核心 constructs 明确，measurement 高度一致，并主动处理 overlap。  
3：总体合理，但存在已知 proxy/overlap 且已限定。  
2：明显 proxy 或定义模糊。  
1：核心变量与声称概念严重错位。  
0：measurement 无法合理代表研究对象。

### SV1.3 Design–Question Alignment
4：设计与核心问题直接对应，无关键 inference gap。  
3：主要问题可回答，部分次级问题证据有限。  
2：只能回答核心问题一部分。  
1：大部分 evidence 与问题间接相关。  
0：实验实际回答另一个问题。

### SV1.4 Alternative-Explanation Control
至少审：trajectory length、benchmark identity、model identity、metadata、termination cue、error frequency、label prevalence、task difficulty、repetition overlap、semantic leakage。  
4：主要替代解释系统识别、测试或 bounded。  
3：关键 confounders 已处理，但仍有合理残余解释。  
2：只处理部分明显 confounders。  
1：核心 interpretation 可能主要由 shortcut 解释。  
0：存在足以推翻核心 interpretation 的强替代解释。

### SV1.5 Inference & Scope Alignment
必须区分：

```text
prediction ≠ understanding
association ≠ causality
blind held-out ≠ independent external validation
evaluated benchmark families ≠ unseen benchmarks
dev comparison ≠ confirmatory superiority
exploratory ≠ confirmatory
```

4：claims 与 design 支持范围严格匹配。  
3：总体克制，仅少量措辞需限定。  
2：若干 overreach 但可通过 claim 修订。  
1：核心 narrative 超过设计支持范围。  
0：主要结论无法由设计推出。

**SV1 caps**：

- 核心 research question 无法由当前实验回答：`SV1 ≤ 7.5/15`
- 核心 confirmatory claim 存在不可仅靠措辞修复的 inference overreach：`SV1 ≤ 9/15`

---

## SV2 — Data & Label Validity (15)

**Question:** 数据、样本、标签和 eligibility 是否足以承载论文结论？

| Subcriterion | Internal weight |
|---|---:|
| SV2.1 Data Provenance & Version Integrity | 20% |
| SV2.2 Sampling & Coverage Validity | 20% |
| SV2.3 Label Definition & Operationalization | 20% |
| SV2.4 Label Quality & Consistency | 25% |
| SV2.5 Eligibility, Missingness & Class Support | 15% |

审计要点：

- **SV2.1**：来源、Git/HF revision、版本固定、provenance、可重建性。
- **SV2.2**：benchmark/task/model coverage、选择偏差、dev/test coverage、样本量与 claim 强度匹配。
- **SV2.3**：label operational definition、outcome/process/side-effect construct、definition drift。
- **SV2.4**：duplicate annotations、disagreement、invalid labels、consistency/QC、系统噪声。
- **SV2.5**：eligibility、missingness、class imbalance、rare positives、single-class subgroup、exploratory downgrade。

**SV2 caps**：

- 核心 target label 定义无法可靠确定：该 target confirmatory validity 不得完整 credit。
- 核心结论主要依赖严重低支持 target：`SV2 ≤ 9/15`
- 系统性数据/标签错误足以改变主结论：`Scientific Critical Risk`

---

## SV3 — Protocol & Independence (20)

**Question:** 正式结果是否真正来自独立、冻结、无泄漏评估？

| Subcriterion | Internal weight |
|---|---:|
| SV3.1 Development/Test Separation | 15% |
| SV3.2 Group Leakage Control | 15% |
| SV3.3 Preregistration Discipline | 15% |
| SV3.4 Model / Threshold / Eligibility Freeze | 15% |
| SV3.5 Blind Prediction & Label-Unlock Integrity | 20% |
| SV3.6 Post-Test Tuning Control | 10% |
| SV3.7 Protocol Provenance & Auditability | 10% |

审计要点：

- **SV3.1**：dev/test 严格分离；test 信息是否进入开发。
- **SV3.2**：task/trajectory duplicates、group overlap、CV grouping、独立单位。
- **SV3.3**：protocol/metrics/model selection/threshold/bootstrap/stage gates 是否结果前冻结。
- **SV3.4**：final model/hyperparameters/threshold/eligibility/input representation 是否 test 前冻结。
- **SV3.5**：pre-unlock predictions、prediction hash、unlock timestamp、freeze 后 scoring。
- **SV3.6**：test 后是否调 threshold、换模型、改 eligibility/metric/subset、反复重跑。
- **SV3.7**：commits/machine summaries/predictions/hashes/reports 是否证明时间顺序。

**SV3 caps**：

- test-label info 进入正式 model/threshold/eligibility selection：`SV3 ≤ 8/20` + Critical Risk
- 明确 post-unlock tuning 用于 confirmatory result：`SV3 ≤ 6/20` + Critical Risk
- blind 时间顺序无法证明：`SV3.5 ≤ 2/4`

---

## SV4 — Evaluation & Statistical Validity (20)

**Question:** 评价指标和统计证据是否正确支持结论？

| Subcriterion | Internal weight |
|---|---:|
| SV4.1 Metric–Target Alignment | 15% |
| SV4.2 Baseline & Comparator Fairness | 15% |
| SV4.3 Evaluation Unit & Aggregation Validity | 15% |
| SV4.4 Uncertainty & Statistical Inference | 20% |
| SV4.5 Ablation / Sensitivity Validity | 15% |
| SV4.6 Threshold / Class-Imbalance Treatment | 10% |
| SV4.7 Statistical Interpretation Discipline | 10% |

审计要点：

- **SV4.1**：primary metrics、imbalance、prevalence、metric interpretation。
- **SV4.2**：baseline 合理性、公平信息访问、是否故意弱 comparator。
- **SV4.3**：trajectory/task/group 单位、pooled/macro、clustered data、benchmark aggregation。
- **SV4.4**：CI/bootstrap/cluster unit/seeds/variance/claim 对应。
- **SV4.5**：ablation 是否公平、是否重调参、是否误写因果机制。
- **SV4.6**：class weighting、frozen threshold、positive F1、rare class、threshold leakage。
- **SV4.7**：禁止把 CI 跨零写显著、AP lift 写因果、pooled 写成 every benchmark、descriptive 写 significance。

**SV4 caps**：

- primary metric 无法回答核心 claim：`SV4 ≤ 10/20`
- confirmatory inference 使用错误独立单位且可能改变结论：`Scientific Critical Risk`

---

## SV5 — Robustness & Conclusion Boundaries (15)

**Question:** 结果是否稳定，以及结论边界是否被诚实限定？

| Subcriterion | Internal weight |
|---|---:|
| SV5.1 Resampling / Fold Stability | 20% |
| SV5.2 Benchmark / Domain Robustness | 25% |
| SV5.3 Model / Agent Robustness | 15% |
| SV5.4 Representation / Specification Robustness | 15% |
| SV5.5 Failure-Boundary Characterization | 10% |
| SV5.6 External-Validity Discipline | 15% |

审计要点：

- fold variance / OOF / pooled discrepancy / 单 fold 驱动
- benchmark heterogeneity / LOBO / domain failures
- leave-one-model / multi-agent/model
- alternative representations / ablations / dense comparator / specification sensitivity
- FP/FN / error taxonomy / failure boundaries
- evaluated benchmark families vs unseen benchmark vs independent external dataset vs deployment

**SV5 caps**：

- 核心结果仅单 benchmark/agent 成立却写一般结论：`SV5 ≤ 7.5/15`
- 缺少 independent external validation **本身不自动低分**；正确限定 scope 时仍可高分。

---

## SV6 — Claim–Evidence & Reproducibility (15)

**Question:** 每个重要 claim 能否追溯到证据，关键结果能否合理复现？

| Subcriterion | Internal weight |
|---|---:|
| SV6.1 Claim–Evidence Traceability | 25% |
| SV6.2 Artifact & Git Provenance | 20% |
| SV6.3 Computational Reproducibility | 20% |
| SV6.4 Numeric Consistency | 15% |
| SV6.5 Negative Evidence & Limitation Preservation | 10% |
| SV6.6 Independent Auditability | 10% |

审计要点：

- claim → evidence → artifact → source result
- confirmatory/exploratory/dev-only/descriptive/forbidden 状态
- Git/taskbook/machine artifact/report/SHA/prediction/figure/table source
- code/environment/dependency/seed/data revision/configuration
- machine/report/table/figure/manuscript numeric consistency
- negative evidence、弱结果、limitations 是否保留
- 独立 reviewer 能否只靠 repo 重建证据链

**SV6 caps**：

- 核心 result 无法追溯到 machine artifact：`SV6 ≤ 9/15`
- 关键数值无法复现或 provenance 不清：Major / Critical Risk
- 选择性隐藏与 narrative 冲突的重要结果：`SV6 ≤ 7.5/15`

---

# 6. SVS computation and interpretation

每个一级维度：

```text
SV_k = DimensionWeight × Σ(InternalWeight_i × Score_i / 4)
```

最终：

```text
SVS = SV1 + SV2 + SV3 + SV4 + SV5 + SV6
```

| SVS | Interpretation |
|---:|---|
| 90–100 | Very Strong |
| 80–89.9 | Strong |
| 70–79.9 | Generally Sound, material limitations |
| 60–69.9 | Borderline / substantial concerns |
| 50–59.9 | Weak scientific foundation |
| <50 | Not scientifically ready |

Critical Risk Gate 优先于总分。

---

# 7. Scientific Critical Risk Gate

每项状态只能：`ABSENT / POSSIBLE / CONFIRMED`。

- **CR1**：关键数据/标签系统性错误，足以改变核心结论。
- **CR2**：train/dev/test 或 task-group leakage 足以污染核心结果。
- **CR3**：test-label info 进入正式 model/threshold/eligibility selection。
- **CR4**：post-unlock tuning 被用作正式 confirmatory result。
- **CR5**：primary statistical analysis 存在足以改变主要结论的结构性错误。
- **CR6**：核心 confirmatory result 无法追溯或无法合理复现。
- **CR7**：核心 manuscript claim 与 frozen evidence 直接矛盾。

任何 `CONFIRMED`：Scientific Validity Decision 不得为 PASS。

---

# 8. Publication Competitiveness Score (PCS) — 100

假设 Scientific Validity 成立，PCS 回答：

> 工作是否有足够差异化、意义、证据深度、故事和审稿防御能力，使期刊有合理理由接收？

| Dimension | Weight |
|---|---:|
| PC1 Novelty & Differentiation | 25 |
| PC2 Scientific Significance | 20 |
| PC3 Evidence Completeness | 15 |
| PC4 Story & Contribution Coherence | 15 |
| PC5 Reviewer Defensibility | 15 |
| PC6 Journal Fit & Presentation Readiness | 10 |

## PC1 — Novelty & Differentiation (25)

| Subcriterion | Internal weight |
|---|---:|
| PC1.1 Problem Novelty | 20% |
| PC1.2 Method / Representation Differentiation | 20% |
| PC1.3 Evaluation / Protocol Differentiation | 20% |
| PC1.4 Empirical Insight Novelty | 25% |
| PC1.5 Closest-Work Separation | 15% |

- **PC1.1**：研究问题是否存在新的、非平凡切面。
- **PC1.2**：representation/information access/complexity/task dependence/semantic-vs-structural/trajectory-vs-step/training requirement 的真实差异。简单模型不得自动扣分。
- **PC1.3**：evaluation design 是否不仅规范，而且产生已有工作没有提供的可信 evidence。
- **PC1.4**：是否得到清晰、非显然、值得领域知道的新 empirical insight。
- **PC1.5**：对 closest work 做 adversarial separation：question/representation/target/unit/access/protocol/new knowledge。

**PC1 caps**：

- closest work 已覆盖 same question + same core approach + same evaluation purpose，新增仅 minor variation：`PC1 ≤ 10/25`
- 无法明确回答“本文新增了什么知识”：`PC1 ≤ 15/25`
- novelty 主要靠包装/命名：`PC1 ≤ 8/25` + Publication Major Risk

---

## PC2 — Scientific Significance (20)

| Subcriterion | Internal weight |
|---|---:|
| PC2.1 Importance of the Research Problem | 20% |
| PC2.2 Importance of the Main Finding | 25% |
| PC2.3 General Scientific Usefulness | 20% |
| PC2.4 Insight / Surprise Value | 20% |
| PC2.5 Field Relevance & Timeliness | 15% |

- **PC2.1**：问题是否真正值得解决，而不只是热门。
- **PC2.2**：main finding 告诉领域什么以前不知道/不确定的知识；单纯 metric 高不算 significance。
- **PC2.3**：是否能帮助 evaluator design、benchmark design、agent diagnostics、future research、systems engineering、evaluation methodology。
- **PC2.4**：reviewer 是否会认为结果值得记住，而不是“模型能工作”。
- **PC2.5**：使用冻结 literature assets 判断领域相关性和时效性。

**PC2 caps**：

- 只能得到“标准方法在某数据集有效”：`PC2 ≤ 10/20`
- 问题高度 niche 且无法说明领域意义：`PC2 ≤ 12/20`

---

## PC3 — Evidence Completeness (15)

| Subcriterion | Internal weight |
|---|---:|
| PC3.1 Core-result Evidence Depth | 25% |
| PC3.2 Baseline / Comparator Completeness | 15% |
| PC3.3 Robustness Evidence | 20% |
| PC3.4 Mechanism / Interpretation Evidence | 15% |
| PC3.5 Efficiency / Practical Characterization | 10% |
| PC3.6 Failure / Negative Evidence Coverage | 15% |

审：

- development → robustness → held-out confirmation → uncertainty
- baseline/comparator 是否足够排除 trivial explanation
- fold/benchmark/model/specification robustness
- 哪些信号相关、什么时候失效、confounder/failure boundary
- lightweight/efficiency claim 是否有 cost evidence
- weak target / negative comparison / heterogeneity / failures / limitations 是否被覆盖

若 manuscript 完全无 efficiency claim，PC3.5 可 `N/A`，其余内部权重重新归一化并记录原因。

**PC3 caps**：

- 只有主结果、无 robustness/uncertainty/failure analysis：`PC3 ≤ 8/15`
- 核心结论主要靠单一 experiment：`PC3 ≤ 6/15`

---

## PC4 — Story & Contribution Coherence (15)

| Subcriterion | Internal weight |
|---|---:|
| PC4.1 Central Narrative Clarity | 25% |
| PC4.2 Contribution Independence | 20% |
| PC4.3 Evidence-to-Contribution Alignment | 20% |
| PC4.4 Section-level Coherence | 15% |
| PC4.5 Claim Compression / Message Efficiency | 20% |

审：

- 是否能用一句话稳定解释中心问题
- contributions 是否相关但不重复
- 每条 contribution 是否有 direct evidence
- Introduction/Related Work/Methods/Results/Discussion 是否同一主线
- 是否能压缩成 2–4 个清晰 takeaway

**PC4 caps**：

- 无稳定 central thesis：`PC4 ≤ 8/15`
- contributions 高度重复：`PC4 ≤ 10/15`
- 只有靠 overclaim 才能让 narrative 成立：`PC4 ≤ 7/15` + Publication Major Risk

---

## PC5 — Reviewer Defensibility (15)

| Subcriterion | Internal weight |
|---|---:|
| PC5.1 Obvious Objection Coverage | 25% |
| PC5.2 Novelty Attack Resistance | 20% |
| PC5.3 Method-Simplicity Defense | 15% |
| PC5.4 External-Validity Defense | 15% |
| PC5.5 Weak-result / Limitation Defense | 15% |
| PC5.6 Evidence Transparency | 10% |

必须建立 Reviewer Objection Matrix，状态只能：

```text
ADDRESSED_BY_EVIDENCE
BOUNDED_BY_LIMITATION
PARTIALLY_RESOLVED
UNRESOLVED_MAJOR
```

重点模拟：

- “novelty 太弱 / 这不是 X 已经做过了吗？”
- “只是 LR + handcrafted features”
- “结构特征只是 shortcut”
- “没有 independent external benchmark”
- “Side Effect 太弱”
- “Looping 与 repetition 定义重叠”
- “metadata confounding”
- “benchmark heterogeneity”
- “dense semantics comparison 不够”
- “baseline 不够”
- “blind held-out 不是 unseen external validation”

**PC5 caps**：

- 存在一个无 evidence / bounded limitation 可防守、足以推翻核心贡献的 reviewer objection：`PC5 ≤ 7.5/15`
- ≥3 个 unresolved major objections：`PC5 ≤ 9/15`

---

## PC6 — Journal Fit & Presentation Readiness (10)

PC6 必须针对 prereg 前冻结的具体目标期刊。

| Subcriterion | Internal weight |
|---|---:|
| PC6.1 Scope Fit | 30% |
| PC6.2 Contribution-Level Fit | 20% |
| PC6.3 Article Depth / Workload Fit | 15% |
| PC6.4 Audience Fit | 15% |
| PC6.5 Manuscript Asset Readiness | 10% |
| PC6.6 Editorial / Formatting Readiness | 10% |

若无冻结 target-journal dossier：整个 PC6=`NOT_SCORED`，不得自行选刊。

**PC6 caps**：

- scope 明显不匹配：`PC6 ≤ 4/10`
- scope 匹配但 contribution type 明显错位：`PC6 ≤ 6/10`

---

# 9. PCS computation

## 9.1 Core PCS

无 target journal 时：

```text
Core PCS Raw = PC1 + PC2 + PC3 + PC4 + PC5   # max 90
Core PCS Normalized = Core PCS Raw / 90 × 100
PC6 = NOT_SCORED
```

## 9.2 Target-specific PCS

只有存在冻结 journal dossier 时：

```text
Target PCS = PC1 + PC2 + PC3 + PC4 + PC5 + PC6
```

| PCS | Interpretation |
|---:|---|
| 90–100 | Very Strong Competitiveness |
| 80–89.9 | Strong |
| 70–79.9 | Competitive, with identifiable risks |
| 60–69.9 | Borderline |
| 50–59.9 | Weak |
| <50 | Poor publication competitiveness |

以上均不是 acceptance probability。

---

# 10. Publication Critical Risk Gate

每项状态：`ABSENT / POSSIBLE / CONFIRMED`。

- **PCR1** Substantial Prior-Work Overlap：closest work 已基本覆盖核心贡献且无法建立实质 differentiation。
- **PCR2** No Defensible Contribution：无法明确至少一个有 evidence 支持的新增贡献。
- **PCR3** Journal Scope Mismatch：仅在 PC6 被执行时适用。
- **PCR4** Core Narrative Requires Overclaim：必须夸大 novelty/external validity/SOTA 等才能让论文故事成立。
- **PCR5** Fatal Reviewer Objection：存在无法通过 evidence、scope limitation 或论证防守且足以推翻核心贡献的 reviewer objection。

任何 `CONFIRMED`：最终 Publication Decision 不得为 GO。

---

# 11. Phase 1 — Evidence Inventory

正式评分前生成：

```text
artifacts/risk_0_evidence_inventory.csv
```

字段至少：

```text
evidence_id
source_stage
source_path
source_commit
source_hash_or_identifier
evidence_type
supports_sv
supports_pc
summary
direct_or_indirect
verified
notes
```

Evidence Inventory 完成前，**禁止创建任何 score**。

---

# 12. Phase 2/3 — Primary Audit

生成：

```text
artifacts/risk_0_primary_scores.csv
```

必须包含全部 69 个 SV/PC 子项（PC6 即使未评分也必须保留 6 行并标 `NOT_SCORED/NOT_APPLICABLE`）。

字段：

```text
criterion_id
dimension
criterion_name
dimension_weight
internal_weight
evidence_status
evidence_confidence
judgment_type
primary_score_0_4
evidence_ids
supporting_reason
limitation
cap_triggered
cap_rule
risk_ids
```

---

# 13. Critical Risk Register

生成：

```text
artifacts/risk_0_critical_risks.csv
```

CR1–CR7、PCR1–PCR5 全部必须出现，即使 `ABSENT`。

字段：

```text
risk_id
risk_family
risk_definition
status
severity
evidence_ids
reason
score_impact
decision_impact
mitigable_by_writing
mitigable_without_new_experiment
notes
```

---

# 14. Reviewer Objection Matrix

生成：

```text
artifacts/risk_0_reviewer_objections.csv
```

至少主动审查：

```text
novelty too weak
method too simple
handcrafted-feature shortcut
construct overlap
metadata confounding
Looping/repetition overlap
Side Effect low support
no independent external benchmark
benchmark heterogeneity
dense semantics comparison limitations
baseline sufficiency
statistical support
blind-heldout scope
cross-paper comparability
practical relevance
```

字段：

```text
objection_id
objection
severity
evidence_response
status
remaining_vulnerability
publication_impact
```

---

# 15. Phase 5 — Adversarial Re-review

Primary Audit 完成后，第二遍假设：

> 你是一个希望拒稿的 reviewer，专门寻找能够降低高分的真实 counterevidence。

生成：

```text
artifacts/risk_0_adversarial_scores.csv
```

字段至少：

```text
criterion_id
primary_score_0_4
adversarial_score_0_4
counterevidence_ids
attack_argument
score_change_reason
```

不得为了“显得严格”机械扣分；只有真实 counterevidence、遗漏限制或合理 reviewer attack 才允许降低。

---

# 16. Phase 6 — Conservative Reconciliation

生成：

```text
artifacts/risk_0_final_scores.csv
```

默认：

```text
final_subscore = min(primary_score, adversarial_score)
```

如果发现 primary audit 有 factual error，需要向上修正：

```text
AUDIT_CORRECTION_REQUIRED
```

不得在同一正式 run 静默调高；必须独立 fix commit。

所有 dimension 必须先给 raw score，再应用 cap：

```text
raw_dimension_score
cap_triggered
cap_value
final_dimension_score
```

---

# 17. Evidence Coverage

分别计算：

```text
SV Evidence Coverage
PC Evidence Coverage
```

同时报告：

```text
verified_direct_count
verified_indirect_count
partially_verified_count
not_verified_count
contradicted_count
not_applicable_count
```

可使用：

```text
Coverage = (VERIFIED + 0.5 × PARTIALLY_VERIFIED) / applicable criteria
```

但不得只报告百分比而隐藏 counts。

---

# 18. Non-critical Risk Register

生成：

```text
artifacts/risk_0_risk_register.csv
```

风险等级：

- **MAJOR**：合理 reviewer 可据此显著降低接收可能，并影响核心贡献/有效性。
- **MODERATE**：不会单独推翻论文，但必须 mitigation。
- **MINOR**：主要是写作、呈现、补充说明或非核心限制。

---

# 19. Final Publication Decision — frozen rule

只允许：

```text
GO
GO_WITH_MITIGATION
NO_GO
```

## NO_GO
任一满足：

```text
任一 Scientific Critical Risk = CONFIRMED
或 任一 Publication Critical Risk = CONFIRMED
或 SVS < 70
或 Core PCS Normalized < 60
```

## GO_WITH_MITIGATION
满足：

```text
无 CONFIRMED Critical Risk
SVS ≥ 70
Core PCS Normalized ≥ 60
```

但存在任一：

```text
POSSIBLE Critical Risk
unresolved MAJOR risk
SVS < 80
Core PCS Normalized < 70
```

## GO
必须全部满足：

```text
无 CONFIRMED/POSSIBLE Critical Risk
SVS ≥ 80
Core PCS Normalized ≥ 70
无足以威胁 central contribution 的 unresolved MAJOR risk
```

`GO` 仅表示：当前证据支持进入 manuscript drafting / journal targeting，不需要先回到实验阶段；不代表保证录用。

若 PC6 未评分，只能给 `GENERAL_JOURNAL_PUBLICATION_DECISION`，不得声称具体 Q1/Q2/Q3 接收判断。

---

# 20. Required report

生成：

```text
docs/risk_0_publication_risk_audit_report.md
```

必须包含：

1. Executive Summary
2. SVS + SV1–SV6 raw/cap/final/confidence/evidence/weakness
3. Core PCS + PC1–PC6 raw/cap/final/confidence/evidence/weakness
4. CR1–CR7 / PCR1–PCR5
5. Reviewer Objection Matrix
6. Major / Moderate / Minor Risk Register
7. Primary vs Adversarial score changes
8. Evidence Coverage
9. Primary bottleneck
10. `GO / GO_WITH_MITIGATION / NO_GO`
11. What Would Change the Decision?

`What Would Change the Decision?` 只分类为：

```text
writing mitigation
positioning mitigation
journal-selection mitigation
new experiment required
```

不得自动执行 mitigation。

---

# 21. Machine summary

生成：

```text
artifacts/risk_0_run_summary.json
```

至少包含：

```text
stage_determination
svs
sv_evidence_coverage
sv1 sv2 sv3 sv4 sv5 sv6
core_pcs_raw
core_pcs_normalized
pc_evidence_coverage
pc1 pc2 pc3 pc4 pc5
pc6_status
pc6_score
target_specific_pcs
scientific_critical_absent
scientific_critical_possible
scientific_critical_confirmed
publication_critical_absent
publication_critical_possible
publication_critical_confirmed
major_risk_count
moderate_risk_count
minor_risk_count
reviewer_objection_count
unresolved_major_objection_count
final_publication_decision
primary_bottleneck
output_hashes
all scientific-operation counters
```

---

# 22. Verifiers / tests

至少验证：

1. Git start clean
2. A3.3 result reachable
3. A3.2 addendum result reachable
4. A1.11 claim matrix exact
5. frozen claim statuses exact
6. evidence inventory 在评分前生成
7. 69 个子项全部存在
8. applicable score ∈ {0,1,2,3,4}
9. 每项有 evidence status/confidence/judgment type
10. score=4 有持久化 evidence
11. SV/PC weights exact
12. caps 先 raw 后 apply
13. CR1–CR7 全部存在
14. PCR1–PCR5 全部存在
15. Reviewer Objection Matrix 非空且含 mandatory objections
16. adversarial audit 已执行
17. final subscore obeys conservative reconciliation
18. SVS formula exact
19. Core PCS formula exact
20. 无 target dossier 时 PC6=NOT_SCORED
21. no web / no new literature
22. all scientific-operation counters = 0
23. final decision obeys frozen thresholds
24. report ↔ machine summary exact
25. final Git clean

---

# 23. Commit discipline

## RISK-0a — prereg

```text
chore: preregister RISK-0 publication audit
```

只提交 taskbook，然后 STOP。

## RISK-0b — implementation

```text
chore: implement RISK-0 publication audit
```

## RISK-0c — result

```text
docs: finalize RISK-0 publication risk audit
```

不得 amend。任何 fix 必须独立 commit。

---

# 24. Stage determination

只能：`PASS / PASS_WITH_CONDITIONS / STOP`。

## PASS

要求：hard gates、evidence inventory、所有 applicable subcriteria、critical risks、adversarial review、reconciliation、risk register、reviewer objections、final decision 全部完成；所有 scientific counters=0；无新 literature；Git clean。

## PASS_WITH_CONDITIONS

仅允许非结构性条件，例如：

- PC6 未评分（未冻结目标期刊）
- 少量 confidence=MEDIUM/LOW，但已透明记录
- journal-specific risk 留待后续 RISK-0J

不得隐藏 unresolved scientific contradiction。

## STOP

包括：artifact drift、critical provenance unavailable、rubric mismatch、score 在 evidence inventory 前生成、new science、new literature、silent rubric change、Git provenance unclear。

---

# 25. Final state

完成后必须：

```text
RISK_0_AUDIT_COMPLETE
PUBLICATION_DECISION = GO / GO_WITH_MITIGATION / NO_GO
WAIT_FOR_HUMAN_RISK_0_REVIEW
```

然后立即 STOP。不得自动开始 manuscript drafting。
