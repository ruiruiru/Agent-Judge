# Stage A1.2 Minimal Task-Grouped Dev Baselines

## Stage determination

**PASS_WITH_CONDITIONS**

This is a dev-only evidence recommendation. Human stage-gate review is required.

Conditions:

- 1 learned-baseline outer folds predicted no positives.
- Low positive-class support remains a stability limitation for: side_effect.

## Environment and frozen scope

- Run ID: `stage_a1_2_grouped_minimal_dev_20260804T034000Z`
- Preregistration commit: `b4fef6f63d55ccd4ed2cdf4feb2dcab1cd5b6d20`
- Python: `3.14.6`
- OS: `Windows-11-10.0.26200-SP0`
- CPU logical count: `16`; GPU used: `false`
- Dependencies: `joblib==1.5.3`, `narwhals==2.24.0`, `numpy==2.5.1`, `PyYAML==6.0.3`, `scikit-learn==1.9.0`, `scipy==1.18.0`, `threadpoolctl==3.6.0`
- Formal-run network access: `0`
- Input view: `primary_with_natural_errors` only
- Baselines: B0 most-frequent Dummy; B1 prior Dummy; B2 frozen 13 structural features + scaled LR; B3 frozen TF-IDF + LR.

## Frozen hashes

| File | SHA-256 |
|---|---|
| `data/processed/dev_cleaned_trajectories.jsonl` | `157a2f665ec33aced4e549e349012f97387961afca2da4f8629cc3472a29342e` |
| `data/processed/dev_serialized_primary.jsonl` | `ec2757489c04b4388711826d29a028b24585156c9dab0496d4afe394aa02398a` |
| `artifacts/dev_analysis_index.csv` | `2b29b46522b5cce32f084e6dc620ff3203f1fd474721fb001123348be0ab56d0` |
| `artifacts/test_manifest.csv` | `a52cb55a9c7679b10a6f5ba5958dda2418759c5798adb5d959615f2f4ad3012a` |
| `artifacts/evaluation_folds_success.csv` | `820599f85fd901c1b73db61cbc77c54eb8223df3f3abc14062d5a9f20bb02e65` |
| `artifacts/evaluation_folds_side_effect.csv` | `11be1d8b803d4afffe25716519d117ce1e1909231954bcfd587347317e9b089c` |
| `artifacts/evaluation_folds_looping.csv` | `b950bf23e465d2f108f28281395ac8816c9916b20eaebe2d529e9d5fde74c749` |

The post-run hashes matched the same values. The identifier-only sealed test manifest was read only for a dev/test key-overlap assertion; test trajectory content, labels, predictions, and metrics accessed: **0**.

## Per-fold results

PR-AUC is `sklearn.metrics.average_precision_score`. All F metrics use positive class 1.

| Target | Baseline | Fold | N | Pos | Prev | Pred+ | Config | Thr | AP | F1 | ROC-AUC | Precision | Recall | F2 | BalAcc | MCC |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| success | B0 | 1 | 39 | 11 | 0.282051 | 0 | `B0_most_frequent` | 0.500000 | 0.282051 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| success | B0 | 2 | 40 | 12 | 0.300000 | 0 | `B0_most_frequent` | 0.500000 | 0.300000 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| success | B0 | 3 | 38 | 12 | 0.315789 | 0 | `B0_most_frequent` | 0.500000 | 0.315789 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| success | B0 | 4 | 38 | 12 | 0.315789 | 0 | `B0_most_frequent` | 0.500000 | 0.315789 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| success | B0 | 5 | 37 | 11 | 0.297297 | 0 | `B0_most_frequent` | 0.500000 | 0.297297 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| success | B1 | 1 | 39 | 11 | 0.282051 | 39 | `B1_prior` | 0.300000 | 0.282051 | 0.440000 | 0.500000 | 0.282051 | 1.000000 | 0.662651 | 0.500000 | 0.000000 |
| success | B1 | 2 | 40 | 12 | 0.300000 | 40 | `B1_prior` | 0.300000 | 0.300000 | 0.461538 | 0.500000 | 0.300000 | 1.000000 | 0.681818 | 0.500000 | 0.000000 |
| success | B1 | 3 | 38 | 12 | 0.315789 | 38 | `B1_prior` | 0.250000 | 0.315789 | 0.480000 | 0.500000 | 0.315789 | 1.000000 | 0.697674 | 0.500000 | 0.000000 |
| success | B1 | 4 | 38 | 12 | 0.315789 | 38 | `B1_prior` | 0.250000 | 0.315789 | 0.480000 | 0.500000 | 0.315789 | 1.000000 | 0.697674 | 0.500000 | 0.000000 |
| success | B1 | 5 | 37 | 11 | 0.297297 | 37 | `B1_prior` | 0.250000 | 0.297297 | 0.458333 | 0.500000 | 0.297297 | 1.000000 | 0.679012 | 0.500000 | 0.000000 |
| success | B2 | 1 | 39 | 11 | 0.282051 | 17 | `B2_C0p1_cw_balanced` | 0.350000 | 0.646671 | 0.714286 | 0.818182 | 0.588235 | 0.909091 | 0.819672 | 0.829545 | 0.598115 |
| success | B2 | 2 | 40 | 12 | 0.300000 | 22 | `B2_C10p0_cw_balanced` | 0.250000 | 0.710024 | 0.647059 | 0.869048 | 0.500000 | 0.916667 | 0.785714 | 0.761905 | 0.482498 |
| success | B2 | 3 | 38 | 12 | 0.315789 | 10 | `B2_C1p0_cw_balanced` | 0.700000 | 0.496921 | 0.454545 | 0.717949 | 0.500000 | 0.416667 | 0.431034 | 0.612179 | 0.236833 |
| success | B2 | 4 | 38 | 12 | 0.315789 | 22 | `B2_C10p0_cw_balanced` | 0.300000 | 0.529989 | 0.588235 | 0.701923 | 0.454545 | 0.833333 | 0.714286 | 0.685897 | 0.350033 |
| success | B2 | 5 | 37 | 11 | 0.297297 | 11 | `B2_C10p0_cw_balanced` | 0.600000 | 0.622674 | 0.545455 | 0.748252 | 0.545455 | 0.545455 | 0.545455 | 0.676573 | 0.353147 |
| success | B3 | 1 | 39 | 11 | 0.282051 | 39 | `B3_T2_C0p1_cw_balanced` | 0.450000 | 0.839100 | 0.440000 | 0.902597 | 0.282051 | 1.000000 | 0.662651 | 0.500000 | 0.000000 |
| success | B3 | 2 | 40 | 12 | 0.300000 | 19 | `B3_T1_C1p0_cw_balanced` | 0.450000 | 0.601263 | 0.516129 | 0.690476 | 0.421053 | 0.666667 | 0.597015 | 0.636905 | 0.251265 |
| success | B3 | 3 | 38 | 12 | 0.315789 | 12 | `B3_T2_C0p1_cw_none` | 0.350000 | 0.378531 | 0.416667 | 0.605769 | 0.416667 | 0.416667 | 0.416667 | 0.573718 | 0.147436 |
| success | B3 | 4 | 38 | 12 | 0.315789 | 7 | `B3_T2_C10p0_cw_none` | 0.250000 | 0.319233 | 0.000000 | 0.503205 | 0.000000 | 0.000000 | 0.000000 | 0.365385 | -0.322829 |
| success | B3 | 5 | 37 | 11 | 0.297297 | 36 | `B3_T2_C0p1_cw_balanced` | 0.450000 | 0.782131 | 0.468085 | 0.891608 | 0.305556 | 1.000000 | 0.687500 | 0.519231 | 0.108407 |
| side_effect | B0 | 1 | 39 | 3 | 0.076923 | 0 | `B0_most_frequent` | 0.500000 | 0.076923 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| side_effect | B0 | 2 | 38 | 2 | 0.052632 | 0 | `B0_most_frequent` | 0.500000 | 0.052632 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| side_effect | B0 | 3 | 39 | 2 | 0.051282 | 0 | `B0_most_frequent` | 0.500000 | 0.051282 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| side_effect | B0 | 4 | 38 | 2 | 0.052632 | 0 | `B0_most_frequent` | 0.500000 | 0.052632 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| side_effect | B0 | 5 | 41 | 3 | 0.073171 | 0 | `B0_most_frequent` | 0.500000 | 0.073171 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| side_effect | B1 | 1 | 39 | 3 | 0.076923 | 39 | `B1_prior` | 0.050000 | 0.076923 | 0.142857 | 0.500000 | 0.076923 | 1.000000 | 0.294118 | 0.500000 | 0.000000 |
| side_effect | B1 | 2 | 38 | 2 | 0.052632 | 38 | `B1_prior` | 0.050000 | 0.052632 | 0.100000 | 0.500000 | 0.052632 | 1.000000 | 0.217391 | 0.500000 | 0.000000 |
| side_effect | B1 | 3 | 39 | 2 | 0.051282 | 39 | `B1_prior` | 0.050000 | 0.051282 | 0.097561 | 0.500000 | 0.051282 | 1.000000 | 0.212766 | 0.500000 | 0.000000 |
| side_effect | B1 | 4 | 38 | 2 | 0.052632 | 38 | `B1_prior` | 0.050000 | 0.052632 | 0.100000 | 0.500000 | 0.052632 | 1.000000 | 0.217391 | 0.500000 | 0.000000 |
| side_effect | B1 | 5 | 41 | 3 | 0.073171 | 41 | `B1_prior` | 0.050000 | 0.073171 | 0.136364 | 0.500000 | 0.073171 | 1.000000 | 0.283019 | 0.500000 | 0.000000 |
| side_effect | B2 | 1 | 39 | 3 | 0.076923 | 0 | `B2_C10p0_cw_none` | 0.500000 | 0.170760 | 0.000000 | 0.490741 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| side_effect | B2 | 2 | 38 | 2 | 0.052632 | 36 | `B2_C0p1_cw_none` | 0.100000 | 0.162500 | 0.105263 | 0.791667 | 0.055556 | 1.000000 | 0.227273 | 0.527778 | 0.055556 |
| side_effect | B2 | 3 | 39 | 2 | 0.051282 | 7 | `B2_C0p1_cw_balanced` | 0.600000 | 0.058081 | 0.000000 | 0.351351 | 0.000000 | 0.000000 | 0.000000 | 0.405405 | -0.108740 |
| side_effect | B2 | 4 | 38 | 2 | 0.052632 | 7 | `B2_C0p1_cw_none` | 0.200000 | 0.054094 | 0.000000 | 0.277778 | 0.000000 | 0.000000 | 0.000000 | 0.402778 | -0.112004 |
| side_effect | B2 | 5 | 41 | 3 | 0.073171 | 30 | `B2_C1p0_cw_balanced` | 0.250000 | 0.109921 | 0.181818 | 0.587719 | 0.100000 | 1.000000 | 0.357143 | 0.644737 | 0.170139 |
| side_effect | B3 | 1 | 39 | 3 | 0.076923 | 2 | `B3_T2_C1p0_cw_balanced` | 0.450000 | 0.916667 | 0.800000 | 0.990741 | 1.000000 | 0.666667 | 0.714286 | 0.833333 | 0.805387 |
| side_effect | B3 | 2 | 38 | 2 | 0.052632 | 1 | `B3_T1_C10p0_cw_balanced` | 0.500000 | 0.309524 | 0.000000 | 0.902778 | 0.000000 | 0.000000 | 0.000000 | 0.486111 | -0.038749 |
| side_effect | B3 | 3 | 39 | 2 | 0.051282 | 12 | `B3_T1_C10p0_cw_balanced` | 0.200000 | 0.190909 | 0.285714 | 0.824324 | 0.166667 | 1.000000 | 0.500000 | 0.864865 | 0.348743 |
| side_effect | B3 | 4 | 38 | 2 | 0.052632 | 3 | `B3_T1_C10p0_cw_none` | 0.100000 | 0.450000 | 0.400000 | 0.944444 | 0.333333 | 0.500000 | 0.454545 | 0.722222 | 0.368035 |
| side_effect | B3 | 5 | 41 | 3 | 0.073171 | 2 | `B3_T1_C10p0_cw_none` | 0.100000 | 0.638889 | 0.400000 | 0.973684 | 0.500000 | 0.333333 | 0.357143 | 0.653509 | 0.371166 |
| looping | B0 | 1 | 39 | 17 | 0.435897 | 0 | `B0_most_frequent` | 0.500000 | 0.435897 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| looping | B0 | 2 | 39 | 19 | 0.487179 | 0 | `B0_most_frequent` | 0.500000 | 0.487179 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| looping | B0 | 3 | 38 | 18 | 0.473684 | 0 | `B0_most_frequent` | 0.500000 | 0.473684 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| looping | B0 | 4 | 39 | 18 | 0.461538 | 0 | `B0_most_frequent` | 0.500000 | 0.461538 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| looping | B0 | 5 | 41 | 20 | 0.487805 | 0 | `B0_most_frequent` | 0.500000 | 0.487805 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 |
| looping | B1 | 1 | 39 | 17 | 0.435897 | 39 | `B1_prior` | 0.450000 | 0.435897 | 0.607143 | 0.500000 | 0.435897 | 1.000000 | 0.794393 | 0.500000 | 0.000000 |
| looping | B1 | 2 | 39 | 19 | 0.487179 | 39 | `B1_prior` | 0.450000 | 0.487179 | 0.655172 | 0.500000 | 0.487179 | 1.000000 | 0.826087 | 0.500000 | 0.000000 |
| looping | B1 | 3 | 38 | 18 | 0.473684 | 38 | `B1_prior` | 0.450000 | 0.473684 | 0.642857 | 0.500000 | 0.473684 | 1.000000 | 0.818182 | 0.500000 | 0.000000 |
| looping | B1 | 4 | 39 | 18 | 0.461538 | 39 | `B1_prior` | 0.450000 | 0.461538 | 0.631579 | 0.500000 | 0.461538 | 1.000000 | 0.810811 | 0.500000 | 0.000000 |
| looping | B1 | 5 | 41 | 20 | 0.487805 | 41 | `B1_prior` | 0.450000 | 0.487805 | 0.655738 | 0.500000 | 0.487805 | 1.000000 | 0.826446 | 0.500000 | 0.000000 |
| looping | B2 | 1 | 39 | 17 | 0.435897 | 20 | `B2_C10p0_cw_none` | 0.200000 | 0.836912 | 0.918919 | 0.941176 | 0.850000 | 1.000000 | 0.965909 | 0.931818 | 0.856791 |
| looping | B2 | 2 | 39 | 19 | 0.487179 | 21 | `B2_C10p0_cw_none` | 0.200000 | 0.906935 | 0.850000 | 0.921053 | 0.809524 | 0.894737 | 0.876289 | 0.847368 | 0.696572 |
| looping | B2 | 3 | 38 | 18 | 0.473684 | 21 | `B2_C10p0_cw_none` | 0.300000 | 0.922786 | 0.923077 | 0.947222 | 0.857143 | 1.000000 | 0.967742 | 0.925000 | 0.853564 |
| looping | B2 | 4 | 39 | 18 | 0.461538 | 23 | `B2_C10p0_cw_none` | 0.200000 | 0.967006 | 0.878049 | 0.973545 | 0.782609 | 1.000000 | 0.947368 | 0.880952 | 0.772187 |
| looping | B2 | 5 | 41 | 20 | 0.487805 | 22 | `B2_C0p1_cw_none` | 0.200000 | 0.955250 | 0.904762 | 0.959524 | 0.863636 | 0.950000 | 0.931373 | 0.903571 | 0.809072 |
| looping | B3 | 1 | 39 | 17 | 0.435897 | 26 | `B3_T1_C10p0_cw_none` | 0.350000 | 0.696414 | 0.744186 | 0.786096 | 0.615385 | 0.941176 | 0.851064 | 0.743316 | 0.511891 |
| looping | B3 | 2 | 39 | 19 | 0.487179 | 15 | `B3_T2_C10p0_cw_none` | 0.450000 | 0.836031 | 0.764706 | 0.886842 | 0.866667 | 0.684211 | 0.714286 | 0.792105 | 0.600219 |
| looping | B3 | 3 | 38 | 18 | 0.473684 | 34 | `B3_T2_C0p1_cw_balanced` | 0.450000 | 0.771790 | 0.653846 | 0.769444 | 0.500000 | 0.944444 | 0.801887 | 0.547222 | 0.153659 |
| looping | B3 | 4 | 39 | 18 | 0.461538 | 29 | `B3_T1_C0p1_cw_balanced` | 0.500000 | 0.551688 | 0.638298 | 0.523810 | 0.517241 | 0.833333 | 0.742574 | 0.583333 | 0.190281 |
| looping | B3 | 5 | 41 | 20 | 0.487805 | 25 | `B3_T1_C0p1_cw_none` | 0.450000 | 0.483378 | 0.533333 | 0.492857 | 0.480000 | 0.600000 | 0.571429 | 0.490476 | -0.019518 |

## Fold mean ± sample standard deviation and pooled OOF

| Target | Baseline | OOF N | Prev | AP mean±std | F1 mean±std | Pooled AP | Pooled F1 | Pooled ROC-AUC | Pooled Precision | Pooled Recall | Pooled F2 | Pooled BalAcc | Pooled MCC | AP lift |
|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| success | B0 | 192 | 0.302083 | 0.302186 ± 0.014179 | 0.000000 ± 0.000000 | 0.302083 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 | 0.000000 |
| success | B1 | 192 | 0.302083 | 0.302186 ± 0.014179 | 0.463974 ± 0.016779 | 0.294035 | 0.464000 | 0.483659 | 0.302083 | 1.000000 | 0.683962 | 0.500000 | 0.000000 | -0.008049 |
| success | B2 | 192 | 0.302083 | 0.601256 ± 0.087058 | 0.589916 ± 0.098790 | 0.546033 | 0.600000 | 0.768142 | 0.512195 | 0.724138 | 0.668790 | 0.712815 | 0.395090 | 0.243949 |
| success | B3 | 192 | 0.302083 | 0.584052 ± 0.232889 | 0.368176 ± 0.209126 | 0.354240 | 0.409357 | 0.548765 | 0.309735 | 0.603448 | 0.507246 | 0.510679 | 0.019929 | 0.052156 |
| side_effect | B0 | 195 | 0.061538 | 0.061328 ± 0.012606 | 0.000000 ± 0.000000 | 0.061538 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 | 0.000000 |
| side_effect | B1 | 195 | 0.061538 | 0.061328 ± 0.012606 | 0.115356 ± 0.022282 | 0.055746 | 0.115942 | 0.449909 | 0.061538 | 1.000000 | 0.246914 | 0.500000 | 0.000000 | -0.005792 |
| side_effect | B2 | 195 | 0.061538 | 0.111071 ± 0.055370 | 0.057416 ± 0.083149 | 0.071346 | 0.108696 | 0.521403 | 0.062500 | 0.416667 | 0.195312 | 0.503415 | 0.003337 | 0.009808 |
| side_effect | B3 | 195 | 0.061538 | 0.501198 ± 0.286012 | 0.377143 ± 0.287423 | 0.225607 | 0.375000 | 0.810565 | 0.300000 | 0.500000 | 0.441176 | 0.711749 | 0.335454 | 0.164069 |
| looping | B0 | 196 | 0.469388 | 0.469221 ± 0.021548 | 0.000000 ± 0.000000 | 0.469388 | 0.000000 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | 0.500000 | 0.000000 | 0.000000 |
| looping | B1 | 196 | 0.469388 | 0.469221 ± 0.021548 | 0.638498 ± 0.020157 | 0.455705 | 0.638889 | 0.479202 | 0.469388 | 1.000000 | 0.815603 | 0.500000 | 0.000000 | -0.013683 |
| looping | B2 | 196 | 0.469388 | 0.917778 ± 0.051258 | 0.894961 ± 0.030692 | 0.904537 | 0.894472 | 0.943562 | 0.831776 | 0.967391 | 0.936842 | 0.897157 | 0.796189 | 0.435149 |
| looping | B3 | 196 | 0.469388 | 0.667860 ± 0.147841 | 0.666874 ± 0.092693 | 0.632306 | 0.660633 | 0.682065 | 0.565891 | 0.793478 | 0.734406 | 0.627508 | 0.268316 | 0.162919 |

## Configuration and threshold selection

| Target | Baseline | Config | Selected folds |
|---|---|---|---:|
| success | B0 | `B0_most_frequent` | 5 |
| success | B1 | `B1_prior` | 5 |
| success | B2 | `B2_C0p1_cw_balanced` | 1 |
| success | B2 | `B2_C1p0_cw_balanced` | 1 |
| success | B2 | `B2_C10p0_cw_balanced` | 3 |
| success | B3 | `B3_T1_C1p0_cw_balanced` | 1 |
| success | B3 | `B3_T2_C0p1_cw_none` | 1 |
| success | B3 | `B3_T2_C10p0_cw_none` | 1 |
| success | B3 | `B3_T2_C0p1_cw_balanced` | 2 |
| side_effect | B0 | `B0_most_frequent` | 5 |
| side_effect | B1 | `B1_prior` | 5 |
| side_effect | B2 | `B2_C0p1_cw_none` | 2 |
| side_effect | B2 | `B2_C10p0_cw_none` | 1 |
| side_effect | B2 | `B2_C0p1_cw_balanced` | 1 |
| side_effect | B2 | `B2_C1p0_cw_balanced` | 1 |
| side_effect | B3 | `B3_T1_C10p0_cw_none` | 2 |
| side_effect | B3 | `B3_T1_C10p0_cw_balanced` | 2 |
| side_effect | B3 | `B3_T2_C1p0_cw_balanced` | 1 |
| looping | B0 | `B0_most_frequent` | 5 |
| looping | B1 | `B1_prior` | 5 |
| looping | B2 | `B2_C0p1_cw_none` | 1 |
| looping | B2 | `B2_C10p0_cw_none` | 4 |
| looping | B3 | `B3_T1_C0p1_cw_none` | 1 |
| looping | B3 | `B3_T1_C10p0_cw_none` | 1 |
| looping | B3 | `B3_T1_C0p1_cw_balanced` | 1 |
| looping | B3 | `B3_T2_C10p0_cw_none` | 1 |
| looping | B3 | `B3_T2_C0p1_cw_balanced` | 1 |

Selected threshold frequencies:

| Target | Baseline | Threshold | Selected folds |
|---|---|---:|---:|
| looping | B0 | 0.500000 | 5 |
| looping | B1 | 0.450000 | 5 |
| looping | B2 | 0.200000 | 4 |
| looping | B2 | 0.300000 | 1 |
| looping | B3 | 0.350000 | 1 |
| looping | B3 | 0.450000 | 3 |
| looping | B3 | 0.500000 | 1 |
| side_effect | B0 | 0.500000 | 5 |
| side_effect | B1 | 0.050000 | 5 |
| side_effect | B2 | 0.100000 | 1 |
| side_effect | B2 | 0.200000 | 1 |
| side_effect | B2 | 0.250000 | 1 |
| side_effect | B2 | 0.500000 | 1 |
| side_effect | B2 | 0.600000 | 1 |
| side_effect | B3 | 0.100000 | 2 |
| side_effect | B3 | 0.200000 | 1 |
| side_effect | B3 | 0.450000 | 1 |
| side_effect | B3 | 0.500000 | 1 |
| success | B0 | 0.500000 | 5 |
| success | B1 | 0.250000 | 3 |
| success | B1 | 0.300000 | 2 |
| success | B2 | 0.250000 | 1 |
| success | B2 | 0.300000 | 1 |
| success | B2 | 0.350000 | 1 |
| success | B2 | 0.600000 | 1 |
| success | B2 | 0.700000 | 1 |
| success | B3 | 0.250000 | 1 |
| success | B3 | 0.350000 | 1 |
| success | B3 | 0.450000 | 3 |

## Integrity, warnings, and boundaries

- Logistic Regression convergence warnings: `0`.
- OOF completeness: each eligible trajectory appears exactly once per target × baseline; expected counts 192/195/196 were met.
- Outer validation probability evaluation count: `60` (3 targets × 4 baselines × 5 folds), exactly one per combination.
- Configuration selection used inner-validation AP only; threshold selection used inner-validation positive F1 only.
- TF-IDF and StandardScaler were fitted only on the corresponding inner-train or complete outer-train partition.
- No test evaluation, LOBO, Leave-One-Model-Out, reasoning sensitivity, natural-error ablation, benchmark redaction, Embedding, MLP, XGBoost, Transformer, LoRA, screenshot model, or LLM Judge was run.
- No confidence interval or significance test was run in this stage.

## Descriptive evidence summary

- **success — `clear_provisional_signal`.** B2 AP lift `0.243949`; B3 AP lift `0.052156`; B3−B2 pooled AP `-0.191793`; B3−B2 pooled positive F1 `-0.190643`.
- **side_effect — `clear_provisional_signal`.** B2 AP lift `0.009808`; B3 AP lift `0.164069`; B3−B2 pooled AP `0.154261`; B3−B2 pooled positive F1 `0.266304`.
- **looping — `clear_provisional_signal`.** B2 AP lift `0.435149`; B3 AP lift `0.162919`; B3−B2 pooled AP `-0.272231`; B3−B2 pooled positive F1 `-0.233839`.

These observations apply only to the frozen task-grouped official-dev OOF protocol. They do not establish test performance, cross-benchmark generalization, statistical significance, the core hypothesis, or publication-level claims.

Stop after this report and wait for human stage-gate review.
