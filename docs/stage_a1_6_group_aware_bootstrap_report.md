# Stage A1.6 group-aware bootstrap uncertainty report

## Stage determination

`PASS_WITH_CONDITIONS`

The analysis used only frozen A1.3/A1.5 external dev predictions. No model was trained, no prediction/config/threshold was regenerated or reselected, and test access was zero.

## Provenance and frozen protocol

- A1.6a preregistration commit: `d7b851c48581a6c7c6220ab0dfc851b92a32162e`
- A1.6b result commit: recorded by the enclosing result commit.
- GitHub commit: `f838338886d723d40b586309465a38277803d9e6`
- Hugging Face revision: `b6d17e646009d6cb63d5dd7be78807b680693f61`
- Bootstrap unit: `group_key=(benchmark_original, normalized_task_id)`.
- Sampling strata: `target × held_out_group`; Benchmark groups were never pooled into one sampling urn.
- Every selected task group replicates all eligible trajectories in that cluster.
- Seed/RNG/draws: `2026` / `numpy.random.Generator(numpy.random.PCG64(2026))` / `10000`.
- Interval: 95% percentile CI (2.5th, 97.5th percentiles). No BCa/basic/studentized switch.
- Sampling is not stratified. Invalid single-class draws are retained, never redrawn, imputed, or replaced.
- AP lift uses each bootstrap draw's own prevalence.

Task-group clustering avoids treating multiple model trajectories for one task as independent observations, which would artificially narrow intervals.

## Pre-analysis guards

- A1.3 point-estimate maximum error: `5.551e-17`.
- A1.5 point-estimate maximum error: `1.110e-16`.
- S0 vs A1.3 B2 maximum probability error: `0.000e+00`; all required keys/labels/configs/thresholds/predicted labels exact.
- Formal script estimator-training calls: `0`.

## Group counts

| Target | AssistantBench | VisualWebArena | WebArena | WorkArena |
|---|---:|---:|---:|---:|
| success | 6 | 8 | 22 | 15 |
| side_effect | 6 | 8 | 22 | 15 |
| looping | 6 | 8 | 22 | 15 |

## P1-P8 primary inference

| ID | Target | Estimand | Role | Point | Median | 95% CI | Valid fraction | Grade |
|---|---|---|---|---:|---:|---|---:|---|
| P1 | success | B2 macro_ap_lift | primary | 0.180405 | 0.209451 | [0.108398, 0.343576] | 1.000000 | `stable_positive_under_bootstrap` |
| P2 | success | B2 − B3 macro_ap_delta_A_minus_B | primary | 0.056953 | 0.052473 | [-0.120281, 0.255753] | 1.000000 | `difference_uncertain` |
| P2 | success | B2 − B3 macro_f1_delta_A_minus_B | primary | 0.125360 | 0.127533 | [-0.004539, 0.272120] | 1.000000 | `difference_uncertain` |
| P3 | success | S1_no_termination − S0_full13 macro_ap_delta_A_minus_B | primary | 0.038348 | 0.031503 | [-0.052110, 0.116438] | 1.000000 | `difference_uncertain` |
| P3 | success | S1_no_termination − S0_full13 pooled_ap_delta_A_minus_B | auxiliary | -0.034939 | -0.032916 | [-0.112303, 0.027128] | 1.000000 | `difference_uncertain` |
| P3 | success | S1_no_termination − S0_full13 macro_f1_delta_A_minus_B | auxiliary | 0.009000 | 0.010118 | [-0.108982, 0.096493] | 1.000000 | `difference_uncertain` |
| P4 | success | S6_termination_repetition_only − S0_full13 macro_ap_delta_A_minus_B | primary | 0.031789 | 0.018444 | [-0.065368, 0.097810] | 1.000000 | `difference_uncertain` |
| P4 | success | S6_termination_repetition_only − S0_full13 pooled_ap_delta_A_minus_B | auxiliary | -0.015252 | -0.022560 | [-0.143619, 0.087696] | 1.000000 | `difference_uncertain` |
| P4 | success | S6_termination_repetition_only − S0_full13 macro_f1_delta_A_minus_B | auxiliary | 0.065743 | 0.065192 | [-0.005232, 0.143886] | 1.000000 | `difference_uncertain` |
| P5 | looping | B2 macro_ap_lift | primary | 0.404061 | 0.416514 | [0.333629, 0.505652] | 1.000000 | `stable_positive_under_bootstrap` |
| P6 | looping | S2_no_repetition − S0_full13 macro_ap_delta_A_minus_B | primary | -0.031698 | -0.029716 | [-0.080426, -0.004079] | 1.000000 | `stable_drop_for_A_vs_B` |
| P6 | looping | S2_no_repetition − S0_full13 pooled_ap_delta_A_minus_B | auxiliary | -0.042332 | -0.036348 | [-0.078731, 0.014406] | 1.000000 | `difference_uncertain` |
| P6 | looping | S2_no_repetition − S0_full13 macro_f1_delta_A_minus_B | auxiliary | 0.005986 | 0.005755 | [-0.007481, 0.019544] | 1.000000 | `difference_uncertain` |
| P7 | looping | S6_termination_repetition_only − S0_full13 macro_ap_delta_A_minus_B | primary | 0.050515 | 0.045056 | [-0.018899, 0.115324] | 1.000000 | `difference_uncertain` |
| P7 | looping | S6_termination_repetition_only − S0_full13 pooled_ap_delta_A_minus_B | auxiliary | 0.077492 | 0.072380 | [-0.002522, 0.166052] | 1.000000 | `difference_uncertain` |
| P7 | looping | S6_termination_repetition_only − S0_full13 macro_f1_delta_A_minus_B | auxiliary | -0.017446 | -0.017229 | [-0.128077, 0.042794] | 1.000000 | `difference_uncertain` |
| P8 | side_effect | B3 macro_ap | primary | 0.111941 | 0.153788 | [0.072163, 0.349988] | 0.985500 | `support_diagnostic_only` |

These labels describe bootstrap stability only. They are not causal claims or formal hypothesis tests; no p-values or significance terminology are used.

## Side Effect support diagnostics

Side Effect has only 12 positives. AssistantBench is originally 24 negative / 0 positive and therefore has no AP/F1 CI. VisualWebArena and WorkArena all-negative resamples are retained as low-support evidence.

| Method | Domain | Metric | Pos/neg | Invalid draws | Valid fraction | 95% CI | Width |
|---|---|---|---:|---:|---:|---|---:|
| B3 | assistantbench | ap | 0/24 | 10000 | 0.000000 | [NA, NA] | NA |
| B3 | assistantbench | f1 | 0/24 | 10000 | 0.000000 | [NA, NA] | NA |
| B3 | visualwebarena | ap | 2/22 | 944 | 0.905600 | [0.071429, 0.500000] | 0.428571 |
| B3 | visualwebarena | f1 | 2/22 | 944 | 0.905600 | [0.000000, 0.470588] | 0.470588 |
| B3 | webarena | ap | 8/79 | 131 | 0.986900 | [0.039380, 0.550000] | 0.510620 |
| B3 | webarena | f1 | 8/79 | 131 | 0.986900 | [0.022472, 0.333333] | 0.310861 |
| B3 | workarena | ap | 2/58 | 1186 | 0.881400 | [0.025641, 0.146098] | 0.120457 |
| B3 | workarena | f1 | 2/58 | 1186 | 0.881400 | [0.000000, 0.000000] | 0.000000 |

## Per-domain, macro, and pooled uncertainty

Complete single-method per-domain, macro, and pooled AP/F1/AP-lift point estimates, medians, percentile intervals, invalid counts, and valid fractions are preserved in the three dedicated CSV artifacts and their combined single-method summary.

Pooled LOBO intervals are secondary because the four held-out Benchmarks were evaluated by independently trained models whose probability scales may differ. Primary interpretation prioritizes per-domain and macro distributions.

## Integrity and boundaries

- Fixed draw registry SHA-256: `3f875ca8a32fdb99c5754c69daac741b960ac84e742c1eabd4135bb246420a0f`.
- Draw-level primary Parquet SHA-256: `29c49cc42901c680d691666db0f9336d935c820f3f06e5f35663b83de61edbaa`.
- Draw-level rows: `170000`; every preregistered estimand has exactly 10000 fixed draws.
- Paired deltas use the same target/domain registry and bootstrap_id for A and B.
- CI/median/valid fractions were independently recomputed from the draw-level Parquet.
- test access: 0; prohibited experiments: 0; network during formal analysis: 0; GPU: 0.
- No complex model, fusion, secondary LOBO, LOMO, joint OOD, trajectory bootstrap, stratified bootstrap, invalid redraw, or test experiment was run.

## Stage recommendation and stop

`PASS_WITH_CONDITIONS`. Conditions reflect interval width, direction uncertainty, or low Side Effect support rather than a technical failure.

Stop here and wait for human stage-gate review. Do not enter complex models, fusion, secondary LOBO, joint OOD, or test.
