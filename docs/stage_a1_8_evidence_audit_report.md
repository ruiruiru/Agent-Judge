# Stage A1.8 Evidence Audit and Paper Claim Matrix

## 阶段判定

`PASS_WITH_CONDITIONS`

技术审计通过；条件来自claim降级、Side Effect仅能exploratory、四域/小样本/单一数据源等未消失的限制，而不是实现失败。A1.8不构成test授权。

## A1.8 commits

- A1.8a preregistration commit: `d2f0b84c6247c95cc599b28784c5a2db10ad947f`
- A1.8b evidence result commit: `ddc3f9b6ef89ada12b7393fc31c5b57dbb7118f0`

## A1.2-A1.7 evidence chain and provenance

- A1.2: prereg `b4fef6f63d55ccd4ed2cdf4feb2dcab1cd5b6d20`; formal result `179ce02640a8e6e15411348b57fd8d7725047364`
- A1.3: prereg `6b98e03537360d8e60e5ccf3ca4c5ea7b51a652d`; formal result `346bb4b3d4a90fc51c1e099618c3b7592fa76b99`
- A1.4: prereg `84bf9da03c12c4bbe28f57e42b31de71e8cb1041`; formal result `91e6b195dc63bae8c82728a126945abd0d5d2b68`
- A1.5: prereg `fa9ef0771ea44a720ed8b900199a75ef3c863379`; formal result `e4fd9aba83cc6ed3b01b1f624c666b6cc7fce3ca`
- A1.6: prereg `d7b851c48581a6c7c6220ab0dfc851b92a32162e`; formal result `040d081d3359f75f1303f4c24d7f8be79b5da75d`
- A1.7: prereg `e776c16710fd18c1462808a044f911e40061c5c3`; formal result `e24066fa27c027c60e2ac35b8305ea3d4a585493`

- Source priority: machine-readable artifact > formal stage report > human summary.
- Formal sources, paths, hashes, and commits: PASS.
- Machine summary/report core numeric consistency: PASS (277 checked values).
- A1.3 B2 / A1.5 S0: exact across 583 prediction rows.
- A1.6 point regression: PASS at tolerance `1e-12`.
- A1.7 frozen B2/B3 source values: PASS at tolerance `1e-12`.
- All formal-stage test-content/label/prediction/metric access: 0.
- All formal-stage prohibited-experiment records: 0.

## C1-C14 claim matrix

| Claim | Target | Status | Allowed wording |
|---|---|---|---|
| C1 | success | SUPPORTED | 轻量结构轨迹特征在Primary LOBO下为Success预测提供了稳定的跨Benchmark信号。 |
| C2 | success | INSUFFICIENT_EVIDENCE | B2的点估计更高，但配对bootstrap区间跨0。 |
| C3 | success | INSUFFICIENT_EVIDENCE | Termination携带预测信息，但group-aware bootstrap未显示删除它会稳定降低性能。 |
| C4 | success | SUPPORTED_WITH_CONDITIONS | 三特征表示与完整结构集合高度竞争，但配对差异仍不确定。 |
| C5 | success | SUPPORTED | Dense embedding为Success提供了稳定的跨Benchmark信号。 |
| C6 | success | INSUFFICIENT_EVIDENCE | Dense embedding产生强跨Benchmark信号，但未显示相对冻结轻量基线的明确AP增量。 |
| C7 | looping | SUPPORTED | 轻量结构特征为Looping提供了稳定的跨Benchmark信号。 |
| C8 | looping | SUPPORTED | 直接repetition特征具有稳定增量；删除后剩余结构模型仍然很强。 |
| C9 | looping | INSUFFICIENT_EVIDENCE | 没有发现dense semantic表示相对轻量结构基线增加Looping跨Benchmark价值的明确证据。 |
| C10 | side_effect | PROHIBITED | 现有结构证据未建立Side Effect的robust跨Benchmark预测。 |
| C11 | side_effect | DESCRIPTIVE_ONLY | 语义表示显示有希望的Side Effect点估计，但因dev仅12个正轨迹，统计支持很弱。 |
| C12 | cross_model | SUPPORTED_WITH_CONDITIONS | 当底层任务在训练侧已有表示时，信号可以转移到held-out Agent model。 |
| C13 | all | PROHIBITED | 增加表示复杂度没有带来跨target清晰且一致的跨Benchmark优势。 |
| C14 | all | SUPPORTED_WITH_CONDITIONS | 三个评价维度与结构和语义表示呈现不同的经验关系。 |

## 明确禁止的表述

- 结构特征解决了所有Benchmark上的Success预测。
- B2显著优于B3；B2稳定优于B3。
- Success主要由termination决定；termination导致Success。
- 三特征与full13等价；已经证明两者一样好。
- Dense embedding稳定优于所有轻量基线。
- Dense embedding稳定优于B2/B3。
- Looping结构模型对所有数据都已解决。
- Looping完全由重复特征决定。
- 复杂语义表示对Looping是必要的。
- Side Effect结构信号robust；Side Effect已由结构特征解决。
- Side Effect已robust；Side Effect已经解决。
- A1.4证明同时泛化到新模型和新任务；joint task+model OOD。
- 模型越复杂越好。
- 我们证明了不同维度存在固定的信息复杂度层级；这是因果机制。

这些禁止项覆盖：B2显著优于B3、Dense embedding稳定优于B2/B3、Success主要由termination决定、Looping完全由重复特征决定、Side Effect已robust/solved、A1.4证明joint task+model OOD、模型越复杂越好，以及任何因果机制表述。

## 三个target的最强结论

- Success：B2结构LR和B4 dense embedding各自都有稳定跨Benchmark信号；没有证据支持B4相对B2/B3的稳定AP增量，且B4相对B2 macro F1稳定下降。三特征S6与full13高度竞争，但不能写等价。
- Side Effect：结构证据不robust；B3/B4仅显示语义潜力。因仅12个正例且AssistantBench为全负，全部结论必须保持descriptive/exploratory。
- Looping：B2结构LR具有强且稳定的跨Benchmark信号；直接repetition特征有稳定增量，但删除后剩余结构模型仍强，不能写“完全由重复决定”；B4无明确增量。

## A1.4 cross-model解释边界

A1.4只支持model-only、same-task-counterpart条件下的跨Agent/model转移。external task-group counterpart rate为100%，因此不能解释joint task+model OOD。

## A1.5/A1.6对shortcut解释的修正

消融点估计不能升级成机制或因果结论。A1.6显示删除termination的差异不稳定；Looping删除repetition的macro AP稳定下降，但残余模型仍强。

## A1.7对复杂度升级的结论

Dense semantic表示可提供Success信号，但增加表示复杂度没有跨target产生清晰、统一的跨Benchmark优势。Side Effect只能作为低支持描述，Looping不需要dense语义来建立当前主线。

## Threats to validity

| ID | Severity | Threat | Remaining risk |
|---|---|---|---|
| T1 | high | Dev set is about 196 trajectories across only 51 task groups. | Intervals and domain estimates may remain unstable. |
| T2 | critical | Side Effect has only 12 positive dev trajectories. | No strong Side Effect claim is supportable. |
| T3 | high | Side Effect AssistantBench is an all-negative held-out domain. | Cross-domain Side Effect behavior cannot be assessed uniformly. |
| T4 | critical | A1.4 model holdouts have 100% same-task counterparts on the training side. | Joint new-task and new-model generalization remains unknown. |
| T5 | high | Primary LOBO contains only four Benchmark groups. | Four-domain macro estimates have limited domain-level degrees of freedom. |
| T6 | medium | High AP but low F1 in Success WorkArena resembles threshold-transfer or calibration symptoms. | Cause is untested because no calibration experiment was run. |
| T7 | high | Direct repetition features are conceptually close to the Looping construct. | Some predictive signal may reflect a close structural proxy to the annotation definition. |
| T8 | medium | Long trajectories use non-overlap chunking and weighted pooling rather than one full-context embedding pass. | Cross-chunk interactions may be lost. |
| T9 | critical | A1.2-A1.7 are dev-driven method-selection stages. | Dev evidence is selection evidence, not final confirmatory evidence. |
| T10 | high | All evidence uses one dataset and annotation source. | Transfer to other Judge datasets and annotation policies is unknown. |

## Contribution matrix

| ID | Paper status | Contribution | Key limitation |
|---|---|---|---|
| K1 | KEEP_WITH_CONDITIONS | Empirical cross-Benchmark signal characterization | Only four Benchmark groups and one dataset. |
| K2 | KEEP_WITH_CONDITIONS | Representation complexity comparison | One dense encoder and approximate chunk pooling. |
| K3 | KEEP_WITH_CONDITIONS | Target-specific empirical evidence heterogeneity | Side Effect sparsity prevents a symmetric three-target conclusion. |
| K4 | KEEP | Rigorous grouped evaluation and uncertainty methodology | Methodology does not compensate for limited domain and positive support. |

没有为了凑贡献新增表述；K1-K4均保留，其中K1-K3带条件，K4保留。无DROP_FROM_PAPER项；C11不进入core contribution。

## Reviewer attacks

| ID | Attack | Current evidence response | Remaining weakness |
|---|---|---|---|
| R1 | 196 trajectories are too few. | The protocol groups 51 tasks, uses four-domain LOBO, preserves per-domain results, and applies task-cluster bootstrap. | Small data and four domains limit precision and external validity. |
| R2 | Side Effect has only 12 positives, so its conclusion is unreliable. | Agreed for strong claims: all Side Effect evidence is diagnostic/descriptive and the final role is exploratory-only. | No current statistic can create missing positive support. |
| R3 | Looping features leak the label definition. | No-repetition ablation stays strong, while P6 shows a stable but limited repetition increment; full dependence is rejected. | Repetition remains construct-adjacent and cannot be treated as a causal mechanism. |
| R4 | LOMO is not true OOD because the same tasks appear in training. | Correct; A1.4 is explicitly model-only with 100% task counterparts and supports only conditional cross-model transfer. | Joint task-model OOD remains unanswered. |
| R5 | Why not use a larger LLM Judge? | The research question is lightweight, interpretable evidence under Benchmark shift; paid/large Judge methods are outside the preregistered scope. | The work does not claim superiority over large LLM Judges. |
| R6 | Why did B4 not stably beat B2? | Q2/Q3 show uncertain AP increments and Q3 shows a stable Success macro-F1 drop, so complexity alone is not uniformly beneficial. | Only one dense encoder and one pooling design were frozen. |
| R7 | Are results only Benchmark/model identity shortcuts? | Identity fields are excluded from frozen inputs; Primary LOBO holds out full Benchmark groups; model-literal injection audit is zero. | Natural text can still contain domain-specific content and LOMO shares tasks. |
| R8 | Why compare pooled AP across held-out models? | Pooled metrics are secondary; primary cross-model interpretation uses per-model and macro results because probability scales may differ. | Cross-model probability calibration is not established. |
| R9 | Why not tune on test? | Test tuning would invalidate confirmatory evidence; configs and thresholds are selected only inside development training folds and must be frozen before test. | Final confirmatory performance is not yet known. |
| R10 | Chunk pooling may lose information in trajectories up to 160k tokens. | A1.7 uses no truncation, deterministic non-overlap chunks, last-EOS pooling, and payload-weighted normalization. | Cross-chunk interactions are approximated rather than jointly encoded. |

## Final method freeze proposal

| Target | Candidate | Role | Confirmatory eligibility |
|---|---|---|---|
| success | B2 structural LR | primary candidate | true_after_human_freeze_approval |
| side_effect | B4 dense embedding LR | exploratory-only | false_or_exploratory_only |
| looping | B2 structural LR | primary candidate | true_after_human_freeze_approval |

## Remaining evidence decision

`READY_FOR_FINAL_METHOD_FREEZE`

Success和Looping的稳定跨Benchmark结构信号已由A1.6确认；B4已完成冻结语义复杂度检查；没有未解决的泄漏或协议错误；剩余问题主要是limitations而非主结果真伪。Side Effect通过降低论文角色处理，不以12 positives为理由无限追加dev实验。

## 是否建议进入final method freeze

建议进入**人工审批的final method freeze / test前预注册**。这不是自动进入test的授权。

## 执行边界与停止

- estimator fit count: 0
- model forward count: 0
- new prediction count: 0
- new threshold/config selection count: 0
- new bootstrap draw count: 0
- test access count: 0
- prohibited experiment count: 0

A1.8完成后立即停止，等待人工阶段门审查；不得自动开始final test或任何新模型实验。
