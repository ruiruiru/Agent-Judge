# Stage A2.2 Interpretability, Confounder, and Error Analysis Report

## Stage determination

`PASS_WITH_CONDITIONS`

Conditions are limited to descriptive uncertainty: one high-confidence Looping FN remains `UNCLEAR`, several feature-group comparisons were not registered for A1.6 bootstrap, and the ten metadata fits emitted the known scikit-learn `penalty='l2'` deprecation warning. Outputs are complete and no convergence warning occurred.

## Provenance gates

- A2.2 preregistration commit: `587ffec6a1c19ee8948e795044032365d84acc74`
- Parent / A2.1 result: `b4e4a6ab95d8191f1bef91dab9844bef48f00a8d`
- Implementation commit: `ce2a40d0263e522d1a0f4e1482a8694a75aba1e2`
- Result commit: recorded by the enclosing result commit
- Fix commits: none
- Amend: none
- A1.11 claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175` (verified)
- A1.11 main test table SHA-256: `c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947` (verified)
- Formal analysis started from clean implementation commit.

## Deliverables

- 26 frozen standardized coefficient rows: 13 each for Success and Looping.
- 10 frozen A1.5/A1.6 feature-group synthesis rows.
- 388 metadata-only OOF predictions: Success 192 and Looping 196, exactly once per eligible trajectory.
- 10 preregistered dev-only metadata fits: five frozen A1.1 outer folds per target.
- 12 deterministic errors: three FP and three FN per target.
- 12 descriptive notes using only the leakage-safe content allowlist.

## Headline results

### Success

- Top absolute coefficients: total observation characters (-2.203634), mean nonempty observation characters (+1.879461), total action characters (+0.732222), explicit termination signal (-0.609879), and unique-action ratio (+0.520337).
- Metadata AP / lift / F1@0.5: 0.370591 / +0.068508 / 0.433566.
- Frozen B2 dev AP / F1: 0.546543 / 0.661290, read without recomputation.
- Error cases: 3 FP and 3 FN. Main codes include `LONG_BUT_UNSUCCESSFUL`, `TERMINATION_MISMATCH`, `SHORT_BUT_SUCCESSFUL`, and `REPETITIVE_BUT_PROGRESSING`.

### Looping

- Top absolute coefficients: mean nonempty observation characters (-0.830314), nonempty action count (+0.695160), nonempty observation count (+0.695160), step count (+0.695160), and nonempty focused-element count (+0.669540).
- Metadata AP / lift / F1@0.5: 0.568699 / +0.099311 / 0.565445.
- Frozen B2 dev AP / F1: 0.914081 / 0.910995, read without recomputation.
- Error cases: 3 FP and 3 FN. Main codes include `EXPLICIT_ERROR_RECOVERY`, `NON_REPETITIVE_FAILURE`, `REPETITIVE_BUT_PROGRESSING`, `OTHER`, and `UNCLEAR`.

## Scope counters

```text
final_model_fits = 0
final_model_changes = 0
final_threshold_changes = 0
test_inference_runs = 0
embedding_runs = 0
A1_metric_recomputations = 0
official_test_tuning = 0
metadata_diagnostic_fits = 10
```

The ten fits are the preregistered dev-only metadata diagnostic, not a final-model refit.

## Verification status

- Frozen input hashes, two final B2 model hashes, and 13-feature schema verified.
- Metadata input fields fixed to `benchmark_group_primary` and `model_name`.
- Frozen A1.1 grouped-fold coverage and group isolation verified.
- Metadata script contains only the authorized fit/predict-probability path and no A1.10 input.
- Interpretability package contains no fit, partial-fit, transform-fit, predict, or predict-probability call.
- Error selection is deterministic and the manifest contains exactly 12 rows.
- Selected content package contains only allowlisted fields.
- A2.3, external validation, and A3 counters remain zero.

## Warnings and interpretation boundary

- Ten identical scikit-learn `penalty='l2'` deprecation warnings; no convergence warning and no result omission.
- Metadata contains predictive signal for both targets. B2 is descriptively higher, but no new significance test or confirmatory claim is made.
- Coefficients are associations within frozen LR, not causal effects.
- Error analysis is `POST_FREEZE_DESCRIPTIVE`; metadata analysis is `POST_FREEZE_DIAGNOSTIC`.

`WAIT_FOR_HUMAN_A2_2_REVIEW`
