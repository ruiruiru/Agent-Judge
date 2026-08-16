# Stage A1.3 primary four-group LOBO report

## Stage decision

`PASS_WITH_CONDITIONS` — all technical completeness checks passed; the preregistered single-class Side Effect / AssistantBench cell requires conditional interpretation.

## Scope and provenance

- A1.3a preregistration commit: `6b98e03537360d8e60e5ccf3ca4c5ea7b51a652d`
- Required independent byte-normalization correction: `6027d5e5af29a1b0143bb04024084a6c4209529e`
- The first formal invocation stopped before any estimator fit and produced zero predictions; its invalidation log is preserved under `runs/a1_3_primary_lobo_failed_20260804T135000Z_6b98e035/FAILED_PRERUN.json`.
- A1.3b experiment commit: recorded by the enclosing result commit
- Official dev only; primary_with_natural_errors only; B0–B3 only.
- test trajectory/label/prediction/metric access: 0; identifier-only overlap checks: 1.
- Secondary LOBO, LOMO, reasoning/error sensitivity, fusion, complex models, and test evaluation were not run.

## Environment

- Python 3.14.6; CPU-only; GPU 0; network access 0.
- Dependencies: `{"PyYAML": "6.0.3", "joblib": "1.5.3", "narwhals": "2.24.0", "numpy": "2.5.1", "scikit-learn": "1.9.0", "scipy": "1.18.0", "threadpoolctl": "3.6.0"}`

## Held-out statistics and inner folds

| Target | Held-out | n | tasks | neg | pos | inner folds |
|---|---:|---:|---:|---:|---:|---:|
| success | assistantbench | 24 | 6 | 22 | 2 | 5 |
| success | visualwebarena | 24 | 8 | 12 | 12 | 5 |
| success | webarena | 84 | 22 | 59 | 25 | 5 |
| success | workarena | 60 | 15 | 41 | 19 | 5 |
| side_effect | assistantbench | 24 | 6 | 24 | 0 | 5 |
| side_effect | visualwebarena | 24 | 8 | 22 | 2 | 5 |
| side_effect | webarena | 87 | 22 | 79 | 8 | 4 |
| side_effect | workarena | 60 | 15 | 58 | 2 | 5 |
| looping | assistantbench | 24 | 6 | 13 | 11 | 5 |
| looping | visualwebarena | 24 | 8 | 17 | 7 | 5 |
| looping | webarena | 88 | 22 | 51 | 37 | 5 |
| looping | workarena | 60 | 15 | 23 | 37 | 5 |

## Domain results

AP is sklearn average_precision_score. Blank dual-class metrics are intentional for single-class domains.

| Target | Baseline | Held-out | status | prev | AP | AP lift | F1 | threshold | config |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| success | B0 | assistantbench | ok | 0.083333 | 0.083333 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| success | B1 | assistantbench | ok | 0.083333 | 0.083333 | 0.000000 | 0.153846 | 0.300000 | B1_prior |
| success | B2 | assistantbench | ok | 0.083333 | 0.100490 | 0.017157 | 0.173913 | 0.250000 | B2_C10p0_cw_balanced |
| success | B3 | assistantbench | ok | 0.083333 | 0.250000 | 0.166667 | 0.153846 | 0.050000 | B3_T1_C10p0_cw_balanced |
| success | B0 | visualwebarena | ok | 0.500000 | 0.500000 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| success | B1 | visualwebarena | ok | 0.500000 | 0.500000 | 0.000000 | 0.666667 | 0.250000 | B1_prior |
| success | B2 | visualwebarena | ok | 0.500000 | 0.702655 | 0.202655 | 0.727273 | 0.700000 | B2_C10p0_cw_balanced |
| success | B3 | visualwebarena | ok | 0.500000 | 0.377988 | -0.122012 | 0.628571 | 0.250000 | B3_T2_C1p0_cw_none |
| success | B0 | webarena | ok | 0.297619 | 0.297619 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| success | B1 | webarena | ok | 0.297619 | 0.297619 | 0.000000 | 0.458716 | 0.250000 | B1_prior |
| success | B2 | webarena | ok | 0.297619 | 0.406794 | 0.109175 | 0.563380 | 0.350000 | B2_C1p0_cw_balanced |
| success | B3 | webarena | ok | 0.297619 | 0.325077 | 0.027458 | 0.304348 | 0.300000 | B3_T1_C1p0_cw_none |
| success | B0 | workarena | ok | 0.316667 | 0.316667 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| success | B1 | workarena | ok | 0.316667 | 0.316667 | 0.000000 | 0.481013 | 0.250000 | B1_prior |
| success | B2 | workarena | ok | 0.316667 | 0.709300 | 0.392633 | 0.604651 | 0.300000 | B2_C1p0_cw_balanced |
| success | B3 | workarena | ok | 0.316667 | 0.738362 | 0.421695 | 0.481013 | 0.200000 | B3_T2_C1p0_cw_none |
| side_effect | B0 | assistantbench | single_class_negative | 0.000000 |  |  |  | 0.500000 | B0_most_frequent |
| side_effect | B1 | assistantbench | single_class_negative | 0.000000 |  |  |  | 0.050000 | B1_prior |
| side_effect | B2 | assistantbench | single_class_negative | 0.000000 |  |  |  | 0.200000 | B2_C0p1_cw_none |
| side_effect | B3 | assistantbench | single_class_negative | 0.000000 |  |  |  | 0.300000 | B3_T2_C1p0_cw_balanced |
| side_effect | B0 | visualwebarena | ok | 0.083333 | 0.083333 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| side_effect | B1 | visualwebarena | ok | 0.083333 | 0.083333 | 0.000000 | 0.153846 | 0.050000 | B1_prior |
| side_effect | B2 | visualwebarena | ok | 0.083333 | 0.080952 | -0.002381 | 0.153846 | 0.100000 | B2_C0p1_cw_none |
| side_effect | B3 | visualwebarena | ok | 0.083333 | 0.153409 | 0.070076 | 0.181818 | 0.100000 | B3_T1_C1p0_cw_none |
| side_effect | B0 | webarena | ok | 0.091954 | 0.091954 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| side_effect | B1 | webarena | ok | 0.091954 | 0.091954 | 0.000000 | 0.000000 | 0.500000 | B1_prior |
| side_effect | B2 | webarena | ok | 0.091954 | 0.069881 | -0.022073 | 0.055556 | 0.450000 | B2_C10p0_cw_balanced |
| side_effect | B3 | webarena | ok | 0.091954 | 0.130827 | 0.038873 | 0.168421 | 0.050000 | B3_T1_C1p0_cw_none |
| side_effect | B0 | workarena | ok | 0.033333 | 0.033333 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| side_effect | B1 | workarena | ok | 0.033333 | 0.033333 | 0.000000 | 0.064516 | 0.050000 | B1_prior |
| side_effect | B2 | workarena | ok | 0.033333 | 0.030496 | -0.002838 | 0.000000 | 0.550000 | B2_C0p1_cw_balanced |
| side_effect | B3 | workarena | ok | 0.033333 | 0.051587 | 0.018254 | 0.000000 | 0.400000 | B3_T2_C1p0_cw_balanced |
| looping | B0 | assistantbench | ok | 0.458333 | 0.458333 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| looping | B1 | assistantbench | ok | 0.458333 | 0.458333 | 0.000000 | 0.628571 | 0.450000 | B1_prior |
| looping | B2 | assistantbench | ok | 0.458333 | 0.788064 | 0.329730 | 0.869565 | 0.350000 | B2_C1p0_cw_balanced |
| looping | B3 | assistantbench | ok | 0.458333 | 0.860463 | 0.402130 | 0.628571 | 0.400000 | B3_T1_C1p0_cw_balanced |
| looping | B0 | visualwebarena | ok | 0.291667 | 0.291667 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| looping | B1 | visualwebarena | ok | 0.291667 | 0.291667 | 0.000000 | 0.451613 | 0.450000 | B1_prior |
| looping | B2 | visualwebarena | ok | 0.291667 | 0.924036 | 0.632370 | 0.800000 | 0.600000 | B2_C1p0_cw_balanced |
| looping | B3 | visualwebarena | ok | 0.291667 | 0.614379 | 0.322712 | 0.583333 | 0.300000 | B3_T2_C10p0_cw_balanced |
| looping | B0 | webarena | ok | 0.420455 | 0.420455 | 0.000000 | 0.592000 | 0.500000 | B0_most_frequent |
| looping | B1 | webarena | ok | 0.420455 | 0.420455 | 0.000000 | 0.592000 | 0.500000 | B1_prior |
| looping | B2 | webarena | ok | 0.420455 | 0.920488 | 0.500033 | 0.886076 | 0.150000 | B2_C10p0_cw_balanced |
| looping | B3 | webarena | ok | 0.420455 | 0.576962 | 0.156507 | 0.548673 | 0.300000 | B3_T1_C10p0_cw_balanced |
| looping | B0 | workarena | ok | 0.616667 | 0.616667 | 0.000000 | 0.000000 | 0.500000 | B0_most_frequent |
| looping | B1 | workarena | ok | 0.616667 | 0.616667 | 0.000000 | 0.762887 | 0.350000 | B1_prior |
| looping | B2 | workarena | ok | 0.616667 | 0.770777 | 0.154111 | 0.902439 | 0.600000 | B2_C0p1_cw_balanced |
| looping | B3 | workarena | ok | 0.616667 | 0.764985 | 0.148318 | 0.762887 | 0.350000 | B3_T1_C10p0_cw_balanced |

## Mixed-domain macro mean ± sample std

| Target | Baseline | valid/excluded | AP | F1 |
|---|---|---:|---:|---:|
| success | B0 | 4/0 | 0.299405 ± 0.170515 | 0.000000 ± 0.000000 |
| success | B1 | 4/0 | 0.299405 ± 0.170515 | 0.440060 ± 0.212363 |
| success | B2 | 4/0 | 0.479810 ± 0.289563 | 0.517304 ± 0.239274 |
| success | B3 | 4/0 | 0.422857 ± 0.216792 | 0.391945 ± 0.206793 |
| side_effect | B0 | 3/1 | 0.069540 ± 0.031651 | 0.000000 ± 0.000000 |
| side_effect | B1 | 3/1 | 0.069540 ± 0.031651 | 0.072787 ± 0.077256 |
| side_effect | B2 | 3/1 | 0.060443 ± 0.026519 | 0.069801 ± 0.077906 |
| side_effect | B3 | 3/1 | 0.111941 ± 0.053474 | 0.116746 ± 0.101327 |
| looping | B0 | 4/0 | 0.446780 ± 0.133851 | 0.148000 ± 0.296000 |
| looping | B1 | 4/0 | 0.446780 ± 0.133851 | 0.608768 ± 0.127963 |
| looping | B2 | 4/0 | 0.850841 ± 0.082784 | 0.864520 ± 0.045058 |
| looping | B3 | 4/0 | 0.704197 ± 0.132124 | 0.630866 ± 0.093897 |

## Pooled LOBO and A1.2 descriptive deltas

| Target | Baseline | prevalence | LOBO AP | AP lift | LOBO F1 | ΔAP vs A1.2 | ΔF1 vs A1.2 |
|---|---|---:|---:|---:|---:|---:|---:|
| success | B0 | 0.302083 | 0.302083 | 0.000000 | 0.000000 | +0.000000 | +0.000000 |
| success | B1 | 0.302083 | 0.262828 | -0.039255 | 0.464000 | -0.031206 | +0.000000 |
| success | B2 | 0.302083 | 0.461363 | 0.159280 | 0.540881 | -0.084669 | -0.059119 |
| success | B3 | 0.302083 | 0.297947 | -0.004136 | 0.419355 | -0.056293 | +0.009998 |
| side_effect | B0 | 0.061538 | 0.061538 | 0.000000 | 0.000000 | +0.000000 | +0.000000 |
| side_effect | B1 | 0.061538 | 0.052754 | -0.008784 | 0.066667 | -0.002992 | -0.049275 |
| side_effect | B2 | 0.061538 | 0.041690 | -0.019849 | 0.061856 | -0.029657 | -0.046840 |
| side_effect | B3 | 0.061538 | 0.047532 | -0.014006 | 0.160714 | -0.178075 | -0.214286 |
| looping | B0 | 0.469388 | 0.449708 | -0.019680 | 0.411111 | -0.019680 | +0.411111 |
| looping | B1 | 0.469388 | 0.436116 | -0.033272 | 0.638889 | -0.019589 | +0.000000 |
| looping | B2 | 0.469388 | 0.836040 | 0.366652 | 0.884422 | -0.068497 | -0.010050 |
| looping | B3 | 0.469388 | 0.666955 | 0.197567 | 0.639405 | +0.034648 | -0.021228 |

## Side Effect / AssistantBench diagnostic

All four cells contain 24 negatives and 0 positives. AP, ROC-AUC, positive precision/recall/F1/F2, balanced accuracy, MCC, and AP lift are missing—not zero-filled.

| Baseline | predicted positives | false-positive rate | specificity | probability mean/median/max |
|---|---:|---:|---:|---:|
| B0 | 0 | 0.000000 | 1.000000 | 0.000000/0.000000/0.000000 |
| B1 | 24 | 1.000000 | 0.000000 | 0.070175/0.070175/0.070175 |
| B2 | 15 | 0.625000 | 0.375000 | 0.221229/0.205724/0.366183 |
| B3 | 4 | 0.166667 | 0.833333 | 0.286578/0.287472/0.338174 |

## Integrity, warnings, and signals

- External prediction coverage: 2332/2332, unique and complete.
- Inner configuration rows: 240/240; threshold rows: 912/912.
- Warnings: 1086 total; convergence warnings: 0.
- Frozen hashes before/after match: True.
- All 1,086 warnings are the preregistered scikit-learn `penalty='l2'` FutureWarning; convergence warnings: 0.

### Core frozen hashes (identical before and after)

| Artifact | SHA-256 |
|---|---|
| primary LOBO manifest | `16735afc8defd5d91bf2d23ba7773a1f0515feafc238ad1cec2df0dc530b0191` |
| frozen structural features | `2dcd9f5a5a22c40d318f2a7fe1303cdcc0c27832d2ab443c0f3dbe2a1f631556` |
| primary serialized input | `ec2757489c04b4388711826d29a028b24585156c9dab0496d4afe394aa02398a` |
| label index | `2b29b46522b5cce32f084e6dc620ff3203f1fd474721fb001123348be0ab56d0` |
| sealed test identifier manifest | `a52cb55a9c7679b10a6f5ba5958dda2418759c5798adb5d959615f2f4ad3012a` |
| A1.2 pooled metrics | `8ce01c2be0cf73e94c1a5fc085d28d92fd57bf40f450e4dfbd33f8912d5713bc` |
| corrected A1.3 script | `2a4dae0910e64cbe310fd5c631ed0f688fcdbd7bc4f7151cfe814287d8107714` |
| corrected A1.3 config | `d681a09aa7106a9679a5640b751af1000080afddc198433d4f8891ec32541549` |
| frozen A1.3 inner folds | `22c02eabc7e3fca84b920069d430b484d9c6c52c475d711b9190d920a5347b35` |

### Selected configuration and threshold distributions

- Success — B0/B1 fixed 4/4; B2: `C=1 balanced` 2, `C=10 balanced` 2; B3: `T1 C=1 none` 1, `T1 C=10 balanced` 1, `T2 C=1 none` 2. Thresholds: B0 `0.50×4`; B1 `0.25×3, 0.30×1`; B2 `0.25/0.30/0.35/0.70×1`; B3 `0.05/0.20/0.25/0.30×1`.
- Side Effect — B0/B1 fixed 4/4; B2: `C=0.1 none` 2, `C=0.1 balanced` 1, `C=10 balanced` 1; B3: `T1 C=1 none` 2, `T2 C=1 balanced` 2. Thresholds: B0 `0.50×4`; B1 `0.05×3, 0.50×1`; B2 `0.10/0.20/0.45/0.55×1`; B3 `0.05/0.10/0.30/0.40×1`.
- Looping — B0/B1 fixed 4/4; B2: `C=0.1 balanced` 1, `C=1 balanced` 2, `C=10 balanced` 1; B3: `T1 C=1 balanced` 1, `T1 C=10 balanced` 2, `T2 C=10 balanced` 1. Thresholds: B0 `0.50×4`; B1 `0.35×1, 0.45×2, 0.50×1`; B2 `0.15×1, 0.35×1, 0.60×2`; B3 `0.30×2, 0.35×1, 0.40×1`.

- success: `robust_cross_benchmark_signal`
- side_effect: `partial_or_domain_specific_signal`
- looping: `robust_cross_benchmark_signal`

## Stop condition

The formal A1.3 results are complete. Stop here and wait for human stage-gate review; do not begin another experiment.
