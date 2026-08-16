# Stage A1.9 final method freeze and test preregistration report

## Stage determination

`PASS_WITH_CONDITIONS`

All final-dev selection, model-freeze, reload, count, hash, and zero-test-access guards passed. The condition is scientific: Side Effect remains exploratory-only. This report does not authorize or execute A1.10.

## Commits and A1.8 readiness

- A1.9a preregistration commit: `4944df46be45d8ad52d57a051e04b59c4a1a82ee`
- A1.9b experiment commit: recorded by the enclosing result commit.
- A1.8: `PASS_WITH_CONDITIONS` and `READY_FOR_FINAL_METHOD_FREEZE`, hash-verified before fitting.

## Frozen methods and dev selection

| Target | Method | Role | Final config | Threshold | OOF AP | OOF F1 | Model SHA-256 |
|---|---|---|---|---:|---:|---:|---|
| success | `FINAL_SUCCESS_B2` | `confirmatory_primary` | C=10.0, class_weight=balanced | 0.55 | 0.546543 | 0.661290 | `afbdb0a60205d7c6bd40232a8c8a1b1ad3b0910d6b65fecf894cca1a040123c1` |
| looping | `FINAL_LOOPING_B2` | `confirmatory_primary` | C=1.0, class_weight=balanced | 0.55 | 0.914081 | 0.910995 | `862b7ff2b0cbcb5faf88908f5fe5824c7f4e52c2c21521e41bb5fb71b011660c` |
| side_effect | `FINAL_SIDE_EFFECT_B4` | `exploratory_only` | C=10.0, class_weight=balanced | 0.40 | 0.189878 | 0.325581 | `5eb29646c10a8193b8492ffe26a41a63414dc9da884890813273c43d17a7de59` |

Success and Looping use the full frozen 13-feature StandardScaler + LogisticRegression pipeline. S6 is auxiliary only. Side Effect uses the already-frozen A1.7 1024-d embedding and LogisticRegression without StandardScaler; no Qwen forward occurred.

## Completeness and reload

- all-config OOF: 3498/3498
- selected-config OOF: 583/583
- config rows: 18/18
- threshold rows: 57/57
- Logistic Regression fits: 93/93
- final model artifacts: 3/3
- All three joblib artifacts reload and reproduce full-dev prediction hashes exactly.

## Training environment

- Python `3.14.6`, Windows 11 AMD64, CPU-only final selection/refit.
- Frozen baseline dependencies: joblib `1.5.3`, NumPy `2.5.1`, PyYAML `6.0.3`, scikit-learn `1.9.0`, SciPy `1.18.0`, threadpoolctl `3.6.0`.
- The frozen A1.7 embedding was read as an input artifact; no semantic-model environment or GPU forward was invoked in A1.9.

## Final claim freeze

FC1 Success and FC2 Looping are confirmatory-primary held-out official-task signal claims. FE1 Side Effect is permanently exploratory-only and cannot be upgraded from a high test score. B2/B3 or B4 relative superiority, termination/repetition mechanisms, A1.4 model-only transfer, and representation hierarchy remain dev-only.

## Frozen A1.10 blind-first opening

A1.10a requires new human approval. It may read identifiers and raw test content, but not labels or eligibility; it must produce all three methods' blind probabilities/labels, freeze SHA-256, commit the blind artifact, and return to a clean Git state. The counts 1106 trajectories and 3318 target rows are prior provenance only until identifier-only confirmation. Only then may A1.10b unlock labels/eligibility once and perform join-plus-scoring.

## Final test metrics, bootstrap, and grade

Success/Looping primary point metrics are pooled AP, pooled AP lift, and positive F1 at the frozen dev threshold. Primary uncertainty is pooled AP-lift 95% task-group cluster bootstrap CI: 10000 PCG64 draws, seed 2027, clusters sampled with replacement within benchmark_group_primary, no label stratification, no trajectory bootstrap, and no invalid redraw. A positive lift with CI lower > 0 is CONFIRMED_HELDOUT_SIGNAL; positive lift with CI crossing 0 is DIRECTIONAL_BUT_NOT_CONFIRMED; point <= 0 is NOT_CONFIRMED. Side Effect is always EXPLORATORY_TEST_RESULT.

After label unlock, threshold/config/feature/model/embedding/pooling/calibration/fusion and eligibility changes are permanently prohibited for the confirmatory result.

## Integrity, boundaries, and stop

- Test access: `{"content": 0, "eligibility": 0, "embeddings": 0, "features": 0, "labels": 0, "manifest": 0, "metrics": 0, "predictions": 0}`
- Prohibited experiments: `{"b3_final_method": 0, "embedding_regeneration": 0, "fusion": 0, "joint_ood": 0, "llm_judge": 0, "new_model_family": 0, "qwen_forward": 0, "s6_final_method": 0, "second_embedding_model": 0, "secondary_lobo": 0}`
- Warnings: 93 known scikit-learn `penalty='l2'` FutureWarnings; convergence warnings: 0.
- Independent recomputation: `PASS`.

Recommendation: the technical A1.9 freeze is complete, so human review may authorize A1.10. Do not open test automatically. Stop here.
