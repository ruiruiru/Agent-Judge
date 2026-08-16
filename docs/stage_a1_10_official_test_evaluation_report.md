# Stage A1.10 official test evaluation report

## Stage determination

`PASS`

Technical PASS does not imply that a scientific claim is confirmed.

## Blind-before-label provenance

- A1.10a commit: `cead3cbaa362da4a9918dab32e41b58fffb987d9`
- A1.10b preregistration commit: `042866147e7b4a0c930eeb120d6e642cb34773a7`
- A1.10b pre-unlock fix commit: `3f0bc4da460652a74ae4767ff6d482fd4116ec9f`
- A1.10b pre-unlock integrity commit: `85cb71a49c9c25c9284562afad751f975d787608`
- A1.10b result commit: `recorded_by_enclosing_result_commit`
- Frozen blind prediction SHA-256: `a3a232484716ee455a604f03ffd40e6f734a1925ffdfb93e4a3d04118de27c3d`
- Label unlock UTC: `2026-08-09T04:18:26.082790+00:00`
- Label unlock commit state: `85cb71a49c9c25c9284562afad751f975d787608`
- Pre-unlock Git clean: `true`
- Blind predictions changed after unlock: `false`

## Join integrity

- Joined rows: 3318
- Duplicate predictions / labels: 0 / 0
- Unmatched predictions / labels: 0 / 0
- Silent drops / metadata mismatches: 0 / 0

## Target results

| Target | Role | Eligible | Positive | Negative | Prevalence | Task groups | AP | AP lift | F1 | AP-lift 95% CI | Grade |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| success | confirmatory_primary | 1097 | 291 | 806 | 0.265269 | 300 | 0.654836 | 0.389567 | 0.682099 | [0.326806, 0.455411] | CONFIRMED_HELDOUT_SIGNAL |
| looping | confirmatory_primary | 1095 | 577 | 518 | 0.526941 | 300 | 0.921769 | 0.394829 | 0.876987 | [0.360965, 0.428598] | CONFIRMED_HELDOUT_SIGNAL |
| side_effect | exploratory_only | 1102 | 71 | 1031 | 0.064428 | 300 | 0.107279 | 0.042851 | 0.168582 | [0.021245, 0.079200] | EXPLORATORY_TEST_RESULT |

Side Effect remains `EXPLORATORY_TEST_RESULT` regardless of its numerical result.

## Bootstrap integrity

- Draws per target: 10000
- RNG: `numpy.random.Generator(numpy.random.PCG64(2027))`
- Unit: `(benchmark_original, normalized_task_id)` task-group cluster.
- Sampling: within `benchmark_group_primary`; all model trajectories in a sampled task group move together.
- Label stratification: `false`
- Invalid redraw: `false`

## Descriptive benchmark results

| Target | Benchmark | AP | F1 |
|---|---|---:|---:|
| success | assistantbench | 0.356643 | 0.312500 |
| success | visualwebarena | 0.653714 | 0.655367 |
| success | webarena | 0.642390 | 0.692015 |
| success | workarena | 0.674782 | 0.761364 |
| looping | assistantbench | 0.712685 | 0.773585 |
| looping | visualwebarena | 0.869255 | 0.863469 |
| looping | webarena | 0.930541 | 0.852941 |
| looping | workarena | 0.963169 | 0.908795 |
| side_effect | assistantbench | 0.044366 | 0.000000 |
| side_effect | visualwebarena | 0.136418 | 0.198582 |
| side_effect | webarena | 0.102407 | 0.153846 |
| side_effect | workarena | 0.116510 | 0.114286 |

| Target | Macro Benchmark AP | Macro Benchmark F1 | Valid Benchmarks |
|---|---:|---:|---:|
| success | 0.581882 | 0.605312 | 4 |
| looping | 0.868913 | 0.849697 | 4 |
| side_effect | 0.099925 | 0.116678 | 4 |

Complete per-Benchmark secondary metrics are preserved in
`artifacts/a1_10_benchmark_metrics.csv`. All twelve cells contain both classes;
the frozen single-class NA policy nevertheless remained active and no value was
imputed.

## Claim boundary

Only FC1 and FC2 use the mechanical confirmatory grading rule. FE1 remains exploratory. No dev-only comparison, mechanism claim, unseen-Benchmark claim, or joint task/model OOD claim was upgraded.

## Post-unlock integrity

- Re-inference / embedding regeneration / estimator refit: `0 / 0 / 0`
- Threshold / eligibility / metric / bootstrap changes: `0 / 0 / 0 / 0`
- Fusion / calibration / test-driven tuning: `0 / 0 / 0`
- Independent verification: `PASS` (recorded after report generation).
- Tests: A1.10b/A1.10a/label-contract/bootstrap `90/90`; A1.9 provenance/model `30/30`.
- Warning: the first machine preflight stopped before label-source access on a
  Python boolean-literal serialization error. It was preserved, fixed in the
  independent commit above, and the complete pre-unlock gate reran from clean
  Git before the one-time unlock.
- Git clean: verified immediately after the enclosing result commit.

## Frozen output hashes

- benchmark_metrics: `79c648cf77a607d333842bdf2a32d5df8a8c983e4772dcef0cde8af442f786ff`
- bootstrap_draw_metrics: `4a621b4f2559395e0ab0f48585db54202ced08f4000726a12ccf21414886c883`
- bootstrap_summary: `78a2775124b35799d139106a707955f7508f1e1a6d9bb9c120d56c5d7ffcfbea`
- confirmatory_grade: `d284b40c6bf9d601c23bc45bd7f528c491c58c1418496b152ab8013d26380b52`
- final_claim_status: `6f570e791ca4ca283651bd0a6f29d81b40cde5a1aa8d1a118ffa3770699d4e9f`
- scored_predictions: `22883f32ad22ecd2de6e7a3056a0f165d7aa4c03ab4ec847a535dbff7defb704`
- target_metrics: `e88f657af33b47cb42ad562ae3342716f25f41cc69dbdd5d35cecf51504d6231`

## Stop boundary

A1.10 is complete. No next Stage was entered; further progression requires a new human decision.
