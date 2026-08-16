# Paper Claims Allowed and Forbidden

本文件由A1.8冻结claim matrix生成；machine-readable CSV为权威来源。

## C1 — SUPPORTED

允许中文：轻量结构轨迹特征在Primary LOBO下为Success预测提供了稳定的跨Benchmark信号。

Allowed English: Lightweight structural trajectory features provide stable cross-Benchmark signal for Success prediction under Primary LOBO.

禁止中文：结构特征解决了所有Benchmark上的Success预测。

Forbidden English: Structural features solve Success prediction across all Benchmarks.

依据：A1.3 B2跨四域为正；A1.6 P1 macro AP lift 95% CI严格大于0。

## C2 — INSUFFICIENT_EVIDENCE

允许中文：B2的点估计更高，但配对bootstrap区间跨0。

Allowed English: B2 had a higher point estimate under Primary LOBO, but the paired bootstrap interval included zero.

禁止中文：B2显著优于B3；B2稳定优于B3。

Forbidden English: B2 is significantly or stably better than B3.

依据：A1.6 P2的macro AP与F1配对区间均跨0。

## C3 — INSUFFICIENT_EVIDENCE

允许中文：Termination携带预测信息，但group-aware bootstrap未显示删除它会稳定降低性能。

Allowed English: Termination carries predictive information, but removing it did not produce a stable degradation under group-aware bootstrap.

禁止中文：Success主要由termination决定；termination导致Success。

Forbidden English: Success is mainly determined or caused by termination.

依据：A1.5点估计依赖与A1.6 P3跨0区间必须联合解释，且不得作因果表述。

## C4 — SUPPORTED_WITH_CONDITIONS

允许中文：三特征表示与完整结构集合高度竞争，但配对差异仍不确定。

Allowed English: A three-feature representation was highly competitive with the full structural set; the paired difference remained uncertain.

禁止中文：三特征与full13等价；已经证明两者一样好。

Forbidden English: The three-feature representation is equivalent to or proven as good as full13.

依据：A1.5 S6点估计接近/高于S0；A1.6 P4的AP/F1配对区间跨0，因此只能写competitive。

## C5 — SUPPORTED

允许中文：Dense embedding为Success提供了稳定的跨Benchmark信号。

Allowed English: Frozen dense embeddings provide stable cross-Benchmark signal for Success.

禁止中文：Dense embedding稳定优于所有轻量基线。

Forbidden English: Dense embeddings stably outperform all lightweight baselines.

依据：A1.7 Q1 macro AP lift 95% CI严格大于0。

## C6 — INSUFFICIENT_EVIDENCE

允许中文：Dense embedding产生强跨Benchmark信号，但未显示相对冻结轻量基线的明确AP增量。

Allowed English: Dense embeddings produced strong cross-Benchmark signal but no clear incremental AP gain over frozen lightweight baselines.

禁止中文：Dense embedding稳定优于B2/B3。

Forbidden English: Dense embeddings stably outperform B2 and B3.

依据：Q2/Q3 AP区间跨0，且Q3 macro F1显示B4相对B2稳定下降。

## C7 — SUPPORTED

允许中文：轻量结构特征为Looping提供了稳定的跨Benchmark信号。

Allowed English: Lightweight structural trajectory features provide stable cross-Benchmark signal for Looping.

禁止中文：Looping结构模型对所有数据都已解决。

Forbidden English: The structural model solves Looping on all data.

依据：A1.3 B2在四域保持强信号；A1.6 P5 macro AP lift区间严格大于0。

## C8 — SUPPORTED

允许中文：直接repetition特征具有稳定增量；删除后剩余结构模型仍然很强。

Allowed English: Direct repetition features add stable incremental value, while the remaining structural model stays strong after their removal.

禁止中文：Looping完全由重复特征决定。

Forbidden English: Looping is entirely determined by repetition features.

依据：A1.6 P6 macro AP差值区间严格小于0，但S2本身仍保留高macro AP。

## C9 — INSUFFICIENT_EVIDENCE

允许中文：没有发现dense semantic表示相对轻量结构基线增加Looping跨Benchmark价值的明确证据。

Allowed English: No clear evidence was found that dense semantic representations add cross-Benchmark value over the lightweight structural baseline for Looping.

禁止中文：复杂语义表示对Looping是必要的。

Forbidden English: Dense semantic representations are necessary for Looping.

依据：A1.7 Q5 B4-B2 macro AP区间跨0，点估计为负。

## C10 — PROHIBITED

允许中文：现有结构证据未建立Side Effect的robust跨Benchmark预测。

Allowed English: Current structural evidence does not establish robust cross-Benchmark Side Effect prediction.

禁止中文：Side Effect结构信号robust；Side Effect已由结构特征解决。

Forbidden English: Side Effect has a robust structural signal or is solved by structural features.

依据：A1.3/A1.5 B2/S0 AP lift非正且支持稀疏，不能升级为robust claim。

## C11 — DESCRIPTIVE_ONLY

允许中文：语义表示显示有希望的Side Effect点估计，但因dev仅12个正轨迹，统计支持很弱。

Allowed English: Semantic representations showed promising point estimates for Side Effect, but statistical support is weak because only 12 positive dev trajectories are available.

禁止中文：Side Effect已robust；Side Effect已经解决。

Forbidden English: Side Effect has robust cross-Benchmark generalization or is solved.

依据：A1.2 B3和A1.7 B4仅为苗头；Q4是support-diagnostic-only，CI宽且存在单类域。

## C12 — SUPPORTED_WITH_CONDITIONS

允许中文：当底层任务在训练侧已有表示时，信号可以转移到held-out Agent model。

Allowed English: Signals transferred to held-out Agent models when the underlying tasks were represented on the training side.

禁止中文：A1.4证明同时泛化到新模型和新任务；joint task+model OOD。

Forbidden English: A1.4 proves simultaneous new-model and new-task or joint task-model OOD generalization.

依据：A1.4 model-only LOMO显示信号，但external counterpart rate为100%，因此仅限same-task条件。

## C13 — PROHIBITED

允许中文：增加表示复杂度没有带来跨target清晰且一致的跨Benchmark优势。

Allowed English: Increasing representation complexity did not yield a clear, uniform cross-Benchmark advantage across targets.

禁止中文：模型越复杂越好。

Forbidden English: More complex models are always better.

依据：Success增量不确定且F1可稳定下降；Looping无明确增量；Side Effect仅descriptive。

## C14 — SUPPORTED_WITH_CONDITIONS

允许中文：三个评价维度与结构和语义表示呈现不同的经验关系。

Allowed English: The three evaluation dimensions exhibit different empirical relationships with structural and semantic representations.

禁止中文：我们证明了不同维度存在固定的信息复杂度层级；这是因果机制。

Forbidden English: We prove a fixed information-complexity hierarchy or a causal mechanism across dimensions.

依据：Success、Looping具有不同的稳定结构/语义证据模式；Side Effect只能作为稀疏支持下的异质性限制，不能宣称固定层级。
