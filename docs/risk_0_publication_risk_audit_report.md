# RISK-0 Publication Risk & Competitiveness Audit Report

## 1. Executive Summary

Stage determination: `PASS_WITH_CONDITIONS`.

This repository-grounded audit finds that the frozen study is scientifically strong enough to support manuscript drafting, but its general journal publication competitiveness remains conditional. The two confirmatory claims are traceable, blind-before-label, group-aware, statistically supported, and carefully bounded. The main publication bottleneck is not result integrity; it is the narrowness and defensibility of novelty in relation to AgentRewardBench and WebGraphEval, compounded by the absence of an independent external benchmark and the construct overlap between Looping and repetition morphology.

- Scientific Validity Score (SVS): **84.8125 / 100** (`Strong`).
- Core Publication Competitiveness Score: **57.7500 / 90**.
- Core PCS Normalized: **64.1667 / 100** (`Borderline`).
- PC6: `NOT_SCORED`.
- Target-specific PCS: `NOT_AVAILABLE`.
- Final general-journal publication decision: **`GO_WITH_MITIGATION`**.

`GO_WITH_MITIGATION` is not an acceptance probability. It means the repository contains enough evidence to proceed to manuscript drafting without first returning to the experiment stage, provided the frozen scope and the major risks below are handled transparently.

## 2. Audit Scope, Sequence, and Hard Gates

The audit used only committed repository assets. It did not use conversation history, model memory, web search, new literature, unsupported inference, or unpersisted explanations.

Frozen sequence:

1. Phase 1 evidence inventory was created first with 48 committed sources.
2. Primary Scientific Validity audit.
3. Primary Publication Competitiveness audit.
4. Scientific and publication critical-risk audit.
5. Reviewer Objection Matrix.
6. Independent adversarial re-review.
7. Conservative reconciliation and frozen decision rule.

Hard gates passed:

- Clean formal start from implementation commit.
- RISK-0 preregistration: `3a82dfbc44854a0c14f875ec260d6dafc8bf5302`.
- A3.3 result: `152f03134f2a9c62cafbb380c625766d4c6b197a`, reachable.
- A3.2 closest-work addendum result: `bb9dc52467f58769f833e501aa5fa96cb1be9937`, reachable.
- A1.11 claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175`, exact.
- Success: `CONFIRMATORY_SUPPORTED`.
- Looping: `CONFIRMATORY_SUPPORTED`.
- Side Effect: `EXPLORATORY_SUPPORTED`.
- `MANUSCRIPT_EVIDENCE_FROZEN` and `READY_FOR_MANUSCRIPT_DRAFTING` are both present in the committed A3.3 package.

## 3. Scientific Validity Score

All dimensions report the score derived from reconciled subcriteria before and after any dimension cap. No SV cap was triggered.

| Dimension | Primary raw | Adversarial raw | Cap | Final | Confidence | Main evidence | Main weakness |
|---|---:|---:|---|---:|---|---|---|
| SV1 Research Design Validity | 11.8125 | 10.8750 | none | **10.8750 / 15** | HIGH | Charter; input contract; A1.8/A1.11 claims; A2.2 diagnostics; A3.3 contracts | Original H1 is broader than the final structural-signal paper question; metadata and construct-overlap accounts remain. |
| SV2 Data & Label Validity | 10.5000 | 10.5000 | none | **10.5000 / 15** | HIGH | A0.1 source/label contract; A0.2 eligibility; A1.0 corpus; A1.1 support counts | No adjudication study; one dataset; Side Effect has 12 positive dev examples and remains exploratory. |
| SV3 Protocol & Independence | 19.2500 | 19.2500 | none | **19.2500 / 20** | HIGH | Frozen grouped protocol; A1.9 method freeze; A1.10a blind predictions; A1.10b unlock and verification | A0.1 included aggregate audit-only test-label exposure, although no selection link is recorded. |
| SV4 Evaluation & Statistical Validity | 18.5000 | 18.5000 | none | **18.5000 / 20** | HIGH | Nested selection; task-group bootstrap; official held-out intervals; exact independent verification | Comparator breadth is limited and several ablation/relative contrasts remain uncertain or descriptive. |
| SV5 Robustness & Conclusion Boundaries | 12.0000 | 10.6875 | none | **10.6875 / 15** | HIGH | Grouped OOF; LOBO; exploratory LOMO; ablations; dense control; official per-family results; error cases | No independent external or joint-OOD validation; benchmark heterogeneity; only 12 deterministic error cases. |
| SV6 Claim-Evidence & Reproducibility | 15.0000 | 15.0000 | none | **15.0000 / 15** | HIGH | A1.11 evidence registry; A3.1 artifact registry; A3.3 claim/numeric/readiness maps; hashes and verifiers | External source/hardware availability can drift; final manuscript prose is not yet written. |

**SVS = 84.8125 / 100.**

The scientific result is not a claim of semantic understanding, causal mechanism, unseen-benchmark generalization, arbitrary-agent robustness, joint task/model OOD generalization, calibration, or deployment safety.

## 4. Publication Competitiveness Score

PC1-PC5 use only the frozen A3.2 and closest-work-addendum literature package for literature-dependent judgments. PC6 is not scored because no target-journal dossier was frozen before RISK-0.

| Dimension | Primary raw | Adversarial raw | Cap | Final | Confidence | Main evidence | Main weakness |
|---|---:|---:|---|---:|---|---|---|
| PC1 Novelty & Differentiation | 17.5000 | 14.6875 | none | **14.6875 / 25** | HIGH | A3.2 registry/positioning matrix; closest-work addendum; novelty contract | AgentRewardBench shares data/targets and WebGraphEval studies structural trajectories; defensible novelty is narrow. |
| PC2 Scientific Significance | 13.5000 | 12.5000 | none | **12.5000 / 20** | MEDIUM | Held-out signals; efficiency evidence; verified field context | The main finding may appear unsurprising and does not establish comparative superiority or deployment utility. |
| PC3 Evidence Completeness | 12.5625 | 11.2500 | none | **11.2500 / 15** | HIGH | Grouped development; LOBO/LOMO; ablations; dense control; blind test; uncertainty; efficiency; failures | One dense specification; no direct LLM/cross-paper comparator; no external or joint-OOD validation. |
| PC4 Story & Contribution Coherence | 12.0000 | 10.3125 | none | **10.3125 / 15** | MEDIUM | A2.3 story; A3.3 section/claim/contribution contracts | The final narrow structural thesis is visibly smaller than the original dimension-aware benchmark-shift H1 and is caveat-heavy. |
| PC5 Reviewer Defensibility | 11.8125 | 10.3125 | **9.0000** | **9.0000 / 15** | HIGH | Frozen reviewer attacks; limitations; literature boundary; transparent negatives | Three unresolved major objections trigger the preregistered `PC5 <= 9` cap. |
| PC6 Journal Fit & Presentation | not scored | not scored | n/a | **NOT_SCORED** | HIGH | No preregistration-era journal dossier exists | Scope, audience, article depth, and editorial readiness cannot be scored generically. |

- Core PCS Raw = **57.7500 / 90**.
- Core PCS Normalized = **64.1667 / 100**.
- Target-specific PCS = **`NOT_AVAILABLE`**.

## 5. Evidence Coverage

Coverage uses the frozen formula `(VERIFIED + 0.5 * PARTIALLY_VERIFIED) / applicable criteria`. Counts refer to rubric subcriteria, not inventory rows.

### SV Evidence Coverage

- Applicable criteria: 36.
- VERIFIED direct: 22.
- VERIFIED indirect: 0.
- PARTIALLY_VERIFIED: 14.
- NOT_VERIFIED: 0.
- CONTRADICTED: 0.
- NOT_APPLICABLE: 0.
- **Coverage: 80.5556%** (`29 / 36`).

### PC Evidence Coverage

- Applicable criteria: 27.
- VERIFIED direct: 6.
- VERIFIED indirect: 0.
- PARTIALLY_VERIFIED: 21.
- NOT_VERIFIED: 0.
- CONTRADICTED: 0.
- NOT_APPLICABLE: 6 PC6 criteria.
- **Coverage: 61.1111%** (`16.5 / 27`).

The lower PC coverage reflects that novelty, significance, narrative strength, and reviewer defensibility necessarily combine repository evidence with bounded expert judgment. It is not missing scientific-result provenance.

## 6. Scientific Critical Risks

| Risk | Status | Audit finding |
|---|---|---|
| CR1 systematic data/label error | `ABSENT` | Disagreements and Unsure cases are excluded target-wise; no remaining systematic error capable of reversing the core claims is identified. |
| CR2 leakage | `ABSENT` | Task grouping, input exclusions, blind prediction timing, and independent verification are intact. |
| CR3 test labels entered selection | `ABSENT` | Final models, thresholds, representations, and eligibility were frozen before unlock. |
| CR4 post-unlock tuning | `ABSENT` | All post-unlock tuning and recomputation counters are zero. |
| CR5 structural statistical error | `ABSENT` | Cluster units, fixed draws, invalid-draw handling, joins, metrics, and report values are independently verified. |
| CR6 untraceable confirmatory result | `ABSENT` | FC1/FC2 trace through machine metrics, predictions, hashes, commits, and registries. |
| CR7 manuscript claim contradicts evidence | `ABSENT` | The frozen ledger retains claim status and all mandatory scope boundaries. |

Scientific critical counts: `ABSENT=7`, `POSSIBLE=0`, `CONFIRMED=0`.

## 7. Publication Critical Risks

| Risk | Status | Audit finding |
|---|---|---|
| PCR1 substantial prior-work overlap | `POSSIBLE` | Meaningful differences from AgentRewardBench and WebGraphEval exist, but the residual novelty is narrow and may be judged incremental. |
| PCR2 no defensible contribution | `ABSENT` | Four bounded evidence-supported contributions exist. |
| PCR3 journal scope mismatch | `ABSENT` / not applicable | PC6 was not executed and no journal-specific decision is made. |
| PCR4 narrative requires overclaim | `ABSENT` | A narrow paper remains coherent without firstness, SOTA, unseen-benchmark, causal, or LLM-replacement claims. |
| PCR5 fatal reviewer objection | `ABSENT` | Major objections remain, but none presently invalidates every narrow contribution when the frozen limitations are retained. |

Publication critical counts: `ABSENT=4`, `POSSIBLE=1`, `CONFIRMED=0`.

## 8. Reviewer Objection Matrix

| Objection | Status | Remaining vulnerability |
|---|---|---|
| novelty too weak | `UNRESOLVED_MAJOR` | Narrow differentiation; no firstness or cross-paper performance advantage. |
| method too simple | `PARTIALLY_RESOLVED` | Empirical/efficiency framing helps, but LR plus handcrafted features remains technically modest. |
| handcrafted-feature shortcut | `PARTIALLY_RESOLVED` | Identity leakage is excluded, but task difficulty and semantic shortcut accounts remain. |
| construct overlap | `PARTIALLY_RESOLVED` | Official labels are operationalized, but construct validity is not independently established. |
| metadata confounding | `PARTIALLY_RESOLVED` | Metadata-only dev signal remains and B2 is only descriptively higher. |
| Looping/repetition overlap | `UNRESOLVED_MAJOR` | Repetition features directly mirror the Looping target and can appear tautological. |
| Side Effect low support | `BOUNDED_BY_LIMITATION` | Exploratory-only status is correct, but it cannot support a three-target confirmatory story. |
| no independent external benchmark | `UNRESOLVED_MAJOR` | Within-family blind held-out evidence does not establish unseen-family transfer. |
| benchmark heterogeneity | `PARTIALLY_RESOLVED` | Per-family results are transparent, but AssistantBench is weaker and pairwise inference is absent. |
| dense semantics comparison limitations | `PARTIALLY_RESOLVED` | One encoder/pooling design cannot establish a universal complexity hierarchy. |
| baseline sufficiency | `PARTIALLY_RESOLVED` | Local tiers are solid, but no protocol-equivalent LLM/cross-paper comparator exists. |
| statistical support | `ADDRESSED_BY_EVIDENCE` | Core signals have clustered intervals and independent checks; relative claims remain bounded. |
| blind-heldout scope | `BOUNDED_BY_LIMITATION` | Strict blind integrity is not independent external validation. |
| cross-paper comparability | `BOUNDED_BY_LIMITATION` | Property comparison is valid, but no performance leaderboard is available. |
| practical relevance | `PARTIALLY_RESOLVED` | Cost and error diagnostics exist; calibration, deployment, and intervention evidence do not. |

- Reviewer objections: **15**.
- Unresolved major objections: **3**.
- The three unresolved major objections are novelty, Looping/repetition overlap, and independent external validation.

## 9. Non-Critical Risk Register

- Major risks: **3**.
- Moderate risks: **9**.
- Minor risks: **3**.

Major risks are the narrow closest-work differentiation, missing independent external validation, and Looping/repetition construct overlap. Moderate risks cover narrative narrowing, metadata confounding, low Side Effect support, benchmark heterogeneity, one-specification dense comparison, incomplete model/agent robustness, label/adjudication limits, absent calibration/deployment evidence, and associational mechanism evidence. Minor risks cover the missing target-journal dossier, journal-specific formatting/title work, and environment-specific efficiency measurements.

The machine-readable register at `artifacts/risk_0_risk_register.csv` provides evidence IDs, mitigation category, required action, and whether a new experiment would be needed.

## 10. Primary vs Adversarial Re-review

The adversarial pass lowered only criteria with concrete counterevidence or a legitimate rejection-oriented attack.

| Criterion | Primary | Adversarial/final | Reason |
|---|---:|---:|---|
| SV1.3 | 3 | 2 | Final evidence answers a narrower question than the original H1. |
| SV5.2 | 3 | 2 | Within-family confirmation and heterogeneity limit broad domain robustness. |
| SV5.5 | 3 | 2 | Failure evidence is illustrative rather than systematic. |
| PC1.1 | 3 | 2 | Same-data and structurally close prior work narrow problem novelty. |
| PC1.4 | 3 | 2 | Looping/repetition and metadata accounts reduce insight surprise. |
| PC2.4 | 2 | 1 | The main signal may be viewed as careful validation of an expected simple-method finding. |
| PC3.2 | 3 | 2 | One dense specification and no protocol-equivalent judge comparison. |
| PC3.3 | 3 | 2 | No external or joint-OOD validation. |
| PC4.1 | 3 | 2 | Visible narrative narrowing from the original research program. |
| PC4.5 | 3 | 2 | Fourteen limitations and numerous forbidden upgrades make compression difficult. |
| PC5.1 | 4 | 3 | Objections are covered but three remain unresolved major concerns. |
| PC5.4 | 3 | 2 | Scope language bounds rather than answers external validity. |

Aggregate changes:

- Primary SVS: `87.0625`; final SVS: `84.8125`; change: `-2.2500`.
- Primary Core PCS raw: `67.3750`; final Core PCS raw: `57.7500`; change: `-9.6250`.
- Primary Core PCS normalized: `74.8611`; final: `64.1667`; change: `-10.6944` points.
- PC5 adversarial raw was `10.3125`; the frozen `>=3 unresolved major objections` cap reduced final PC5 to `9.0000`.
- No adversarial score was increased. No `AUDIT_CORRECTION_REQUIRED` event occurred.

## 11. Primary Bottleneck

**Primary bottleneck: novelty and contribution differentiation under the closest-work landscape.**

The evidence package is unusually strong in protocol integrity and traceability, but its publication case cannot rely on algorithmic novelty, firstness, SOTA, LLM-judge replacement, or unseen-benchmark superiority. AgentRewardBench already supplies the expert trajectory-label setting, and WebGraphEval is a close structural-evaluation analogue. The defensible contribution is therefore the combination of lightweight fixed-dimensional outcome prediction, frozen blind-held-out protocol, cost characterization, and transparent limits. Whether that combination is sufficiently novel is the central reviewer risk.

## 12. Final Publication Decision

### `GO_WITH_MITIGATION`

Frozen-rule application:

- Confirmed critical risks: none.
- SVS = `84.8125`, above 70 and 80.
- Core PCS Normalized = `64.1667`, above 60 but below 70.
- A `POSSIBLE` publication critical risk exists (`PCR1`).
- Three unresolved major objections and three major non-critical risks exist.

The result therefore cannot be `NO_GO`, because there is no confirmed critical risk and both numeric floors pass. It cannot be `GO`, because `PCR1` is possible, unresolved major risks exist, and Core PCS is below 70. The frozen decision is `GO_WITH_MITIGATION`.

## 13. What Would Change the Decision?

### writing mitigation

- State the narrowed structural-signal research question in the title, abstract, and introduction.
- Keep Success and Looping as the only confirmatory targets; keep Side Effect exploratory and low-support.
- Preserve metadata, label, heterogeneity, mechanism, calibration, and deployment limitations verbatim in substance.
- Avoid causal, semantic-understanding, universal judge, arbitrary-agent, and joint-OOD wording.

### positioning mitigation

- Use the exact A3.2/A3.3 positioning against AgentRewardBench, WebGraphEval, and WebStep.
- Lead with new empirical knowledge and protocol evidence rather than method firstness.
- Treat WebGraphEval as partially comparable and prohibit cross-paper performance ranking.
- Explain why method simplicity is a research object and efficiency advantage, not the novelty claim itself.

### journal-selection mitigation

- Freeze a target-journal dossier before any target-specific PCS or Q-tier judgment.
- Check scope, contribution type, audience, article depth, word limits, section names, and formatting only after that freeze.
- Do not infer journal fit from the general Core PCS.

### new experiment required

- A compatible, separately preregistered independent external benchmark is the clearest path to remove the external-validity major risk.
- A stronger construct-validity or representation control would be required to resolve Looping/repetition overlap rather than merely bound it.
- Calibration, selective prediction, or deployment experiments would be required before practical decision-support claims.

RISK-0 does not authorize any of these experiments or mitigation actions automatically.

## 14. Scientific-Operation Counters

All counters are zero:

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

## 15. Required Artifacts and Stop State

- Evidence inventory: `artifacts/risk_0_evidence_inventory.csv`.
- Primary scores: `artifacts/risk_0_primary_scores.csv`.
- Adversarial scores: `artifacts/risk_0_adversarial_scores.csv`.
- Final scores: `artifacts/risk_0_final_scores.csv`.
- Critical risks: `artifacts/risk_0_critical_risks.csv`.
- Reviewer objections: `artifacts/risk_0_reviewer_objections.csv`.
- Risk register: `artifacts/risk_0_risk_register.csv`.
- Machine summary: `artifacts/risk_0_run_summary.json`.

`RISK_0_AUDIT_COMPLETE`

`PUBLICATION_DECISION = GO_WITH_MITIGATION`

`WAIT_FOR_HUMAN_RISK_0_REVIEW`

STOP. Do not begin manuscript drafting automatically.
