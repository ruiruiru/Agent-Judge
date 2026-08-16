# Stage A1.1 Frozen Grouped Evaluation Protocol

## Scope

This document freezes dev-only data eligibility and evaluation management. No feature extraction, estimator, prediction, threshold optimization, or model metric was run in A1.1.

## Target eligibility and outer folds

| Target | Eligible | Negative | Positive | Task groups | Positive task groups | Outer folds |
|---|---:|---:|---:|---:|---:|---:|
| success | 192 | 134 | 58 | 51 | 24 | 5 |
| side_effect | 195 | 183 | 12 | 51 | 8 | 5 |
| looping | 196 | 104 | 92 | 51 | 39 | 5 |

Eligibility requires both `<target>_eligible_main == true` and a binary main label. Labels join the frozen input only through `trajectory_key`.

The frozen group key is `(benchmark_original, normalized_task_id)`. The actual splitter was `custom_deterministic_grouped_stratification_v1`. It did **not** call scikit-learn `StratifiedGroupKFold`, and no claim of byte-for-byte or algorithmic equivalence to that class is made. No trajectory-level random split is permitted.

### Immutable manifest authority

The following committed bytes are the sole authority for every later ordinary-CV run. They must not be regenerated, even if scikit-learn is installed later. Baseline startup must run `python scripts/verify_evaluation_protocol.py` and stop on any missing file or SHA-256 mismatch.

| Target | Authoritative manifest | SHA-256 |
|---|---|---|
| success | `artifacts/evaluation_folds_success.csv` | `820599f85fd901c1b73db61cbc77c54eb8223df3f3abc14062d5a9f20bb02e65` |
| side_effect | `artifacts/evaluation_folds_side_effect.csv` | `11be1d8b803d4afffe25716519d117ce1e1909231954bcfd587347317e9b089c` |
| looping | `artifacts/evaluation_folds_looping.csv` | `b950bf23e465d2f108f28281395ac8816c9916b20eaebe2d529e9d5fde74c749` |

The primary LOBO, sensitivity LOBO, and Leave-One-Model-Out manifests are likewise hash-locked in `configs/evaluation_protocol.yaml`; this patch does not alter their membership or bytes.

## Outer and fixed inner split statistics

Cells use `trajectories/task_groups/negative/positive`.

| Target | Fold | Train N/G/0/1 | Validation N/G/0/1 | Inner train N/G/0/1 | Inner validation N/G/0/1 |
|---|---:|---|---|---|---|
| success | 1 | 153/41/106/47 | 39/10/28/11 | 123/33/86/37 | 30/8/20/10 |
| success | 2 | 152/40/106/46 | 40/11/28/12 | 121/32/84/37 | 31/8/22/9 |
| success | 3 | 154/41/108/46 | 38/10/26/12 | 124/33/88/36 | 30/8/20/10 |
| success | 4 | 154/41/108/46 | 38/10/26/12 | 124/33/87/37 | 30/8/21/9 |
| success | 5 | 155/41/108/47 | 37/10/26/11 | 125/33/88/37 | 30/8/20/10 |
| side_effect | 1 | 156/41/147/9 | 39/10/36/3 | 126/33/119/7 | 30/8/28/2 |
| side_effect | 2 | 157/41/147/10 | 38/10/36/2 | 126/33/117/9 | 31/8/30/1 |
| side_effect | 3 | 156/41/146/10 | 39/10/37/2 | 126/33/118/8 | 30/8/28/2 |
| side_effect | 4 | 157/41/147/10 | 38/10/36/2 | 126/33/119/7 | 31/8/28/3 |
| side_effect | 5 | 154/40/145/9 | 41/11/38/3 | 123/32/115/8 | 31/8/30/1 |
| looping | 1 | 157/41/82/75 | 39/10/22/17 | 126/33/65/61 | 31/8/17/14 |
| looping | 2 | 157/41/84/73 | 39/10/20/19 | 126/33/67/59 | 31/8/17/14 |
| looping | 3 | 158/41/84/74 | 38/10/20/18 | 127/33/67/60 | 31/8/17/14 |
| looping | 4 | 157/41/83/74 | 39/10/21/18 | 126/33/66/60 | 31/8/17/14 |
| looping | 5 | 155/40/83/72 | 41/11/21/20 | 124/32/66/58 | 31/8/17/14 |

Each outer training pool has one frozen group-aware inner validation partition. Outer validation is forbidden for any selection.

For every target, outer fold, baseline, and registered candidate set, execution order is frozen as follows:

1. Fit every pre-registered candidate configuration on `inner_train`.
2. Score candidates on `inner_validation` and select the configuration with maximum PR-AUC; ties use predeclared registry order.
3. For the selected configuration only, select the classification threshold on the same `inner_validation` by positive-class F1 and the frozen threshold tie-break.
4. Refit the selected configuration from scratch on the complete `outer_train` using only that configuration.
5. Apply the frozen threshold and evaluate `outer_validation` exactly once. Do not return to selection after seeing this result.

## Thresholds and metrics

- Threshold candidates: `0.05, 0.10, ..., 0.95`.
- Primary threshold objective: positive-class F1 on inner validation only.
- Tie-break: higher recall, then closest to 0.5, then smaller threshold.
- Primary metrics: PR-AUC and positive-class F1.
- Secondary metrics: ROC-AUC, precision, recall, F2, balanced accuracy, and MCC.
- Side Effect F2 is auxiliary reporting, not a post-hoc threshold objective.
- Uncomputable metrics are marked not computable and never imputed.
- Pooled OOF reporting concatenates the five disjoint outer-validation prediction sets so that every eligible trajectory appears exactly once. Compute pooled OOF metrics on that concatenation, using each fold's frozen threshold for its predicted labels.
- Pooled OOF metrics are reported separately from every fold's raw metrics and fold-level mean ± standard deviation; pooled OOF is not a substitute for fold dispersion.

### Single-class LOBO policy

If a LOBO held-out domain lacks either class, ordinary predictive metrics—including PR-AUC, ROC-AUC, positive F1, precision, recall, F2, balanced accuracy, MCC, and accuracy—must be recorded as `NA`, never `0`, `0.5`, or `1`.

Only the following descriptive outputs are permitted: predicted-positive rate, mean predicted probability, and, when negative examples exist, False Positive Rate and Specificity. If negatives do not exist, FPR and Specificity are also `NA`.

This rule currently applies to Side Effect for primary AssistantBench and sensitivity AssistantBench/WorkArena L1.

## Four-group primary LOBO

| Target | Held out | Train N/G/0/1 | Validation N/G/0/1 | Both classes | Inner feasible |
|---|---|---|---|---|---|
| success | assistantbench | 168/45/112/56 | 24/6/22/2 | True | True |
| success | visualwebarena | 168/43/122/46 | 24/8/12/12 | True | True |
| success | webarena | 108/29/75/33 | 84/22/59/25 | True | True |
| success | workarena | 132/36/93/39 | 60/15/41/19 | True | True |
| side_effect | assistantbench | 171/45/159/12 | 24/6/24/0 | False | True |
| side_effect | visualwebarena | 171/43/161/10 | 24/8/22/2 | True | True |
| side_effect | webarena | 108/29/104/4 | 87/22/79/8 | True | True |
| side_effect | workarena | 135/36/125/10 | 60/15/58/2 | True | True |
| looping | assistantbench | 172/45/91/81 | 24/6/13/11 | True | True |
| looping | visualwebarena | 172/43/87/85 | 24/8/17/7 | True | True |
| looping | webarena | 108/29/53/55 | 88/22/51/37 | True | True |
| looping | workarena | 136/36/81/55 | 60/15/23/37 | True | True |

## Five-group sensitivity LOBO

| Target | Held out | Train N/G/0/1 | Validation N/G/0/1 | Both classes | Inner feasible |
|---|---|---|---|---|---|
| success | assistantbench | 168/45/112/56 | 24/6/22/2 | True | True |
| success | visualwebarena | 168/43/122/46 | 24/8/12/12 | True | True |
| success | webarena | 108/29/75/33 | 84/22/59/25 | True | True |
| success | workarena_l1 | 184/49/130/54 | 8/2/4/4 | True | True |
| success | workarena_l2 | 140/38/97/43 | 52/13/37/15 | True | True |
| side_effect | assistantbench | 171/45/159/12 | 24/6/24/0 | False | True |
| side_effect | visualwebarena | 171/43/161/10 | 24/8/22/2 | True | True |
| side_effect | webarena | 108/29/104/4 | 87/22/79/8 | True | True |
| side_effect | workarena_l1 | 187/49/175/12 | 8/2/8/0 | False | True |
| side_effect | workarena_l2 | 143/38/133/10 | 52/13/50/2 | True | True |
| looping | assistantbench | 172/45/91/81 | 24/6/13/11 | True | True |
| looping | visualwebarena | 172/43/87/85 | 24/8/17/7 | True | True |
| looping | webarena | 108/29/53/55 | 88/22/51/37 | True | True |
| looping | workarena_l1 | 188/49/100/88 | 8/2/4/4 | True | True |
| looping | workarena_l2 | 144/38/85/59 | 52/13/19/33 | True | True |

Primary LOBO merges WorkArena L1/L2 under `workarena`; sensitivity LOBO keeps `workarena_l1` and `workarena_l2` separate.

## First-round baseline boundary

Registered only, not executed: B0 most-frequent Dummy; B1 prior Dummy; B2 leak-safe structural statistics + Logistic Regression; B3 primary-view TF-IDF + Logistic Regression. The finite spaces are frozen in `configs/baseline_registry.yaml`.

Only `primary_with_natural_errors` is permitted in the first round. Reasoning and error ablation remain later pre-registered sensitivity analyses.

## Test sealing

Test trajectory content, labels, predictions, and metrics remain inaccessible. The identifier-only sealed manifest is read solely to assert zero key overlap.
