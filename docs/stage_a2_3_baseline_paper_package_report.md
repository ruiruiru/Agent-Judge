# Stage A2.3 Baseline Completeness and Paper Package Report

## Stage determination

`PASS_WITH_CONDITIONS`

Conditions: all three Tier 4 literature-context entries require human verification before manuscript use, and external validation is `DEFER_TO_REVISION`. No scientific inconsistency is present.

## Provenance gates

- A2.3 prereg commit: `409807cf1dce736bc9e6a97ff6698de18b024b6f`
- A2.1 result commit: `b4e4a6ab95d8191f1bef91dab9844bef48f00a8d` (verified reachable)
- A2.2 result commit: `a57befbb027d2544d32e3e0cde906c2edf13d385` (verified reachable)
- Implementation commit: `583ef6eec683151f08b458b1976da62b36accc9f`
- Result commit: `recorded_by_enclosing_result_commit`
- Fix commits: `d4b734feedd2ba1882b604e761efa85af2e40a6b`
- Amend: none
- A1.11 claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175` (verified)
- A1.11 main test table SHA-256: `c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947` (verified)
- Frozen claims: FC1/FC2 `CONFIRMATORY_SUPPORTED`; FE1 `EXPLORATORY_SUPPORTED`.

## Baseline completeness

- Total rows: 15 (12 frozen local methods/variants + 3 literature-context entries).
- Tier 0: B0, B1.
- Tier 1: B2 and S0–S6.
- Tier 2: B3.
- Tier 3: B4.
- Tier 4: Web-Shepherd, Agent-RewardBench, AgentRM — all `NEEDS_LITERATURE_VERIFICATION`; no performance number or head-to-head claim was added.

## Paper tables

- Table 1 SHA-256: `297a1f59c34fc7f29864d722e8e2a233945dba061527848e31b4d7411b2964a5`; exact A1.11 held-out mapping.
- Table 2 SHA-256: `bbf36c09827819fbf49aaa7487db66b34077052d8a29cb093c72001bee66f02a`; exact A2.1 efficiency mapping with no cross-target performance join.
- Table 3 SHA-256: `f0e15e670e3f9592c167c57adaf41a63d56bce0fc9bc37a1945a8ed3f3431c1e`; 18 A1.2–A1.7 frozen dev-evidence rows.
- Table 4 SHA-256: `de0cbc94d114eab5677d1ff620a5f0d976883ae8515d3cb24e873f9f213ac511`; all rows `DESCRIPTIVE_ONLY`.
- Table 5 SHA-256: `037a8b3200377093bf1abb5ea0cf9b82db74fb162e27971690d10f7d9cdf4a0f`; A2.2 associations, metadata, and deterministic failures only.

## Evidence placement counts

- MAIN_TEXT: 7
- APPENDIX: 6
- DISCUSSION_ONLY: 5
- LIMITATION_ONLY: 10
- DO_NOT_USE: 15

Frozen claim-status counts: `{"CONFIRMATORY_SUPPORTED": 2, "DESCRIPTIVE_ONLY": 3, "DEV_ONLY": 9, "EXPLORATORY_SUPPORTED": 1, "NOT_SUPPORTED": 2, "PROHIBITED_OVERCLAIM": 8}`.

## Frozen title candidates

- Lightweight Structural Signals for Web-Agent Trajectory Evaluation: Blind Held-Out Evidence and Failure Boundaries
- How Far Can Structure Go? Efficient Web-Agent Trajectory Evaluation under Frozen Held-Out Testing
- Evidence, Efficiency, and Limits of Structural Web-Agent Trajectory Evaluation
- Dimension-Aware Lightweight Evaluation of Web-Agent Trajectories under Benchmark Shift

## Problem and main finding

- Problem: Web-agent trajectory evaluation needs evidence beyond terminal outcomes, but it is unclear how far inexpensive task-agnostic structural signals remain predictive under grouped development and blind held-out evaluation.
- Finding: Frozen lightweight structural evaluators retained confirmatory held-out predictive signal for Success and Looping on official held-out tasks/trajectories within the evaluated benchmark families, with substantially lower measured representation/extraction cost than B4 under the recorded environment, while diagnostics expose unresolved confounding and semantic failure boundaries.

## Contributions

1. Blind-first grouped and held-out evaluation of lightweight structural evidence.
2. Confirmatory Success/Looping evidence with exploratory-only Side Effect retained.
3. Environment-qualified representation/extraction efficiency evidence.
4. Associational, confounder, and deterministic error boundaries without causal promotion.

## RQ1–RQ6

- RQ1: Do lightweight structural trajectory signals contain predictive information for agent evaluation?
- RQ2: How robust are these signals across grouped tasks, benchmarks, and model shifts within the development evidence?
- RQ3: Which structural feature groups contribute most consistently?
- RQ4: Does dense semantic representation provide stable gains over lightweight structural representation in the studied dev regime?
- RQ5: Do frozen structural evaluators retain signal on the official blind held-out test?
- RQ6: What are the efficiency advantages, confounding risks, and characteristic failure modes of structural evaluation?

## Main figure plan

1. Study and blind-first evaluation pipeline.
2. Official held-out AP lift with frozen 95% CI.
3. Efficiency and representation complexity.
4. Structural interpretation and dev uncertainty.
5. Success error taxonomy; benchmark heterogeneity is the appendix alternative.

## External validation

- Decision: `DEFER_TO_REVISION`.
- Rationale: potential external-validity value is high, but compatible labels, accessible trajectories, immutable source terms, and extractor/adapter reuse require a new audited stage and would materially delay the current bounded submission package.
- No external dataset was accessed or executed.

## Limitations

- Final ledger count: 12.
- All eight A1.11 limitations are retained; A2.3 adds coefficient-correlation, metadata-confounding, environment-specific timing, and morphology-versus-semantics boundaries.

## Scientific operation counters

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

## Verification

- Frozen SHA/commit/claim gates passed.
- Table 1 exact mapping passed.
- Table 2 A2.1 exact mapping passed.
- Table 4 exact benchmark mapping passed.
- A2.2 metadata strings and deterministic error counts passed.
- Package-index hashes passed.
- Output summary consistency passed.
- Side Effect remains exploratory; benchmark heterogeneity remains descriptive.
- Static forbidden-operation AST guards are provided in `tests/test_stage_a2_3_publication_package.py`.

## Warnings

- Tier 4 definitions and any comparable numbers require human literature verification.
- External validation is deferred, not executed.
- One A2.2 high-confidence Looping FN remains `UNCLEAR`.
- Several dev representation/ablation intervals remain uncertain or unavailable.
- The first A2.3 build omitted the required machine-summary `claim_status_counts` field; all outputs from that invocation were invalidated and rebuilt after an independent fix commit.

`WAIT_FOR_HUMAN_A2_3_REVIEW`
