# A2.2 Interpretability and Confounder Report

## Evidence identity

All new evidence is either `POST_FREEZE_DIAGNOSTIC` or `POST_FREEZE_DESCRIPTIVE`. Frozen model coefficients describe associations inside the fitted standardized logistic regression; they are not causal effects. A1.5/A1.6 evidence remains dev-only under its frozen protocol. The metadata baseline is a preregistered dev-only diagnostic and is not a new final model.

## 1. Success

### Frozen B2 coefficients

Top five absolute standardized coefficients:

| Rank | Feature | Group | Coefficient | Direction |
|---:|---|---|---:|---|
| 1 | `observation_char_count_total` | activity/volume | -2.203634 | negative association |
| 2 | `observation_char_count_mean_nonempty` | activity/volume | +1.879461 | positive association |
| 3 | `action_char_count_total` | activity/volume | +0.732222 | positive association |
| 4 | `has_explicit_termination_signal` | termination | -0.609879 | negative association |
| 5 | `unique_action_ratio` | repetition | +0.520337 | positive association |

The paired presence of large total- and mean-observation weights with opposite signs is consistent with a multivariable linear decision surface, not independent feature importance. Correlated counts and lengths make one-at-a-time causal readings invalid.

### Frozen feature-group synthesis

| Frozen comparison | Pooled AP delta vs S0 | A1.5 description | A1.6 uncertainty |
|---|---:|---|---|
| remove termination | -0.034939 | moderate dependency | macro-AP difference uncertain |
| remove repetition | -0.013516 | limited dependency | not bootstrapped in A1.6 |
| remove activity/volume | -0.028113 | limited dependency | not bootstrapped in A1.6 |
| remove error features | +0.061458 | limited dependency | not bootstrapped in A1.6 |
| termination+repetition only | -0.015252 | sufficiency-only comparison | macro-AP difference uncertain |

The frozen ablations give modest descriptive dependence on termination and weaker individual dependence on repetition/activity. Removing error features increased pooled AP in this frozen comparison, so error features cannot be described as a stable positive contributor. The registered A1.6 comparisons do not turn the Success group effects into stable paired differences.

### Metadata-only dev diagnostic

| Eligible n | Prevalence | Metadata AP | AP lift | F1@0.5 | Frozen B2 dev AP | Frozen B2 dev F1 |
|---:|---:|---:|---:|---:|---:|---:|
| 192 | 0.302083 | 0.370591 | +0.068508 | 0.433566 | 0.546543 | 0.661290 |

Benchmark and model identity alone contain nonzero predictive signal on frozen dev. Frozen B2 is descriptively higher by 0.175951 AP and 0.227724 F1 under the corresponding frozen dev protocol. No significance test was preregistered, so this does not prove that B2 is free of metadata confounding; it does show that the observed B2 dev performance is not numerically reproduced by the two-field identity baseline.

### Deterministic errors

The three Success FPs include a network-blocked long trajectory, a result page without a user-facing answer, and a high-confidence trajectory dominated by repeated terminal messages whose semantic correctness is unavailable. The three FNs include a three-step successful answer, a page-state/terminal-message mismatch, and a long repetitive path with explicit errors that nevertheless has a positive frozen label.

Allowed interpretation: task-agnostic structure can correlate with task completion because completion often leaves patterns in activity volume, termination, and action diversity. It fails when those proxies diverge from semantic correctness, efficient short completion, state progress, or answer handoff.

## 2. Looping

### Frozen B2 coefficients

Top five absolute standardized coefficients:

| Rank | Feature | Group | Coefficient | Direction |
|---:|---|---|---:|---|
| 1 | `observation_char_count_mean_nonempty` | activity/volume | -0.830314 | negative association |
| 2 | `nonempty_action_count` | activity/volume | +0.695160 | positive association |
| 3 | `nonempty_observation_count` | activity/volume | +0.695160 | positive association |
| 4 | `step_count` | activity/volume | +0.695160 | positive association |
| 5 | `nonempty_focused_element_count` | activity/volume | +0.669540 | positive association |

`consecutive_duplicate_action_count` ranks sixth (+0.499198) and `unique_action_ratio` ranks eleventh (-0.307211). The coefficient ranking therefore reflects both trajectory volume and repetition, while group ablations provide the stronger evidence about repetition dependence.

### Frozen feature-group synthesis

| Frozen comparison | Pooled AP delta vs S0 | A1.5 description | A1.6 uncertainty |
|---|---:|---|---|
| remove termination | -0.007939 | limited dependency | not bootstrapped in A1.6 |
| remove repetition | -0.042332 | limited dependency | stable macro-AP drop for removal |
| remove activity/volume | +0.050597 | limited dependency | not bootstrapped in A1.6 |
| remove error features | -0.014401 | limited dependency | not bootstrapped in A1.6 |
| termination+repetition only | +0.077492 | sufficiency-only comparison | macro-AP difference uncertain |

The strongest frozen group-specific uncertainty result is the stable macro-AP drop when repetition features are removed. The termination+repetition-only variant is descriptively competitive in pooled AP, but its registered macro difference remains uncertain and is a sufficiency comparison, not a dependency grade.

### Metadata-only dev diagnostic

| Eligible n | Prevalence | Metadata AP | AP lift | F1@0.5 | Frozen B2 dev AP | Frozen B2 dev F1 |
|---:|---:|---:|---:|---:|---:|---:|
| 196 | 0.469388 | 0.568699 | +0.099311 | 0.565445 | 0.914081 | 0.910995 |

Metadata identity has appreciable dev signal, but frozen B2 is descriptively higher by 0.345382 AP and 0.345550 F1. This is a descriptive comparison only. It does not eliminate other benchmark/model proxies or establish an identity-invariant mechanism.

### Deterministic errors

Looping FPs show explicit-error recovery, long non-consecutive search failure, and identical clicks that plausibly advance pagination. FNs show a localized repeated-`noop` suffix, a semantic cycle expressed through different strings/IDs, and one short trace whose positive Looping label is not explainable from the allowlisted evidence and remains `UNCLEAR`.

## 3. Combined implication

The metadata audit answers the narrow confounder question conservatively: benchmark/model identity predicts both targets above prevalence, so obvious metadata signal exists. However, it is substantially below frozen B2 on the recorded dev metrics. Together with the frozen ablations, the results are consistent with B2 using structural signal beyond these two identity fields, but they do not prove absence of confounding.

The error analysis explains why Success remains the primary interpretability target. Structural evidence can proxy task completion, yet its limits are inherently semantic: correctness of a final answer, whether a reached state satisfies the goal, whether repeated actions still change state, and whether a short path is sufficient. Looping is more structurally aligned, especially through repetition-group evidence, but literal action repetition is still not equivalent to state stagnation.

## Limitations

- Coefficients are conditional model weights under correlated standardized features, not causal or standalone importance measures.
- A1.5/A1.6 and the A2.2 metadata baseline use frozen dev protocols; no new confirmatory claim is created.
- The metadata diagnostic includes only `benchmark_group_primary` and `model_name`; it cannot exclude all possible proxies.
- Twelve deterministic errors cover confidence positions, not population frequencies.
- One selected case is `UNCLEAR`, and no prohibited field was consulted to resolve it.

Machine sources: `artifacts/a2_2_structural_coefficients.csv`, `artifacts/a2_2_feature_group_evidence.csv`, `artifacts/a2_2_metadata_baseline_summary.csv`, `artifacts/a2_2_error_case_manifest.csv`, and `artifacts/a2_2_error_case_notes.csv`.
