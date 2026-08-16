# Stage A1.4 Leave-One-Model-Out report

## Stage determination

`PASS_WITH_CONDITIONS`

All technical completeness and isolation checks passed. The determination remains conditional because one model has partial Benchmark coverage, external train/validation intentionally share tasks, Side Effect has only 12 positives, and LOMO is exploratory.

## Scope and provenance

- A1.4a preregistration commit: `84bf9da03c12c4bbe28f57e42b31de71e8cb1041`
- A1.4b experiment commit: `91e6b195dc63bae8c82728a126945abd0d5d2b68`
- Official dev; B0-B3; primary_with_natural_errors only.
- test access: 0 in every category; prohibited experiments executed: 0.
- This is model-only holdout. It is not joint task/model OOD because external train and validation intentionally share group_key.

## Exact held-out models

- `GenericAgent-anthropic_claude-3.7-sonnet`
- `GenericAgent-gpt-4o-2024-11-20`
- `GenericAgent-meta-llama_Llama-3.3-70B-Instruct`
- `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct`

## Coverage and external class/group statistics

| Target | Held-out model | coverage | train n/neg/pos | valid n/tasks/neg/pos | overlap groups | valid-only groups | counterpart rate | inner folds |
|---|---|---|---:|---:|---:|---:|---:|---:|
| success | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 141/103/38 | 51/51/31/20 | 51 | 0 | 1.000000 | 5 |
| success | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 145/101/44 | 47/47/33/14 | 47 | 0 | 1.000000 | 5 |
| success | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 149/101/48 | 43/43/33/10 | 43 | 0 | 1.000000 | 5 |
| success | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 141/97/44 | 51/51/37/14 | 51 | 0 | 1.000000 | 5 |
| side_effect | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 144/134/10 | 51/51/49/2 | 51 | 0 | 1.000000 | 5 |
| side_effect | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 145/135/10 | 50/50/48/2 | 50 | 0 | 1.000000 | 5 |
| side_effect | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 152/143/9 | 43/43/40/3 | 43 | 0 | 1.000000 | 5 |
| side_effect | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 144/137/7 | 51/51/46/5 | 51 | 0 | 1.000000 | 5 |
| looping | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 145/67/78 | 51/51/37/14 | 51 | 0 | 1.000000 | 5 |
| looping | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 145/74/71 | 51/51/30/21 | 51 | 0 | 1.000000 | 5 |
| looping | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 153/88/65 | 43/43/16/27 | 43 | 0 | 1.000000 | 5 |
| looping | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 145/83/62 | 51/51/21/30 | 51 | 0 | 1.000000 | 5 |

The exact Meta-Llama manifest model is the sole partial-coverage model and has no VisualWebArena trajectories. Full-coverage-model macro results therefore use the other three models.

## 48 held-out-model units

| Target | Baseline | Held-out model | coverage | n/neg/pos | prevalence | AP | AP lift | F1 | config | threshold |
|---|---|---|---|---:|---:|---:|---:|---:|---|---:|
| success | B0 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/31/20 | 0.392157 | 0.392157 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| success | B1 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/31/20 | 0.392157 | 0.392157 | 0.000000 | 0.563380 | `B1_prior` | 0.250000 |
| success | B2 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/31/20 | 0.392157 | 0.503360 | 0.111203 | 0.529412 | `B2_C1p0_cw_balanced` | 0.700000 |
| success | B3 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/31/20 | 0.392157 | 0.887742 | 0.495585 | 0.780488 | `B3_T1_C10p0_cw_none` | 0.200000 |
| success | B0 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 47/33/14 | 0.297872 | 0.297872 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| success | B1 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 47/33/14 | 0.297872 | 0.297872 | 0.000000 | 0.459016 | `B1_prior` | 0.250000 |
| success | B2 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 47/33/14 | 0.297872 | 0.829041 | 0.531169 | 0.736842 | `B2_C10p0_cw_balanced` | 0.350000 |
| success | B3 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 47/33/14 | 0.297872 | 0.805893 | 0.508021 | 0.666667 | `B3_T1_C10p0_cw_balanced` | 0.250000 |
| success | B0 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/33/10 | 0.232558 | 0.232558 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| success | B1 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/33/10 | 0.232558 | 0.232558 | 0.000000 | 0.377358 | `B1_prior` | 0.300000 |
| success | B2 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/33/10 | 0.232558 | 0.406881 | 0.174323 | 0.500000 | `B2_C1p0_cw_balanced` | 0.350000 |
| success | B3 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/33/10 | 0.232558 | 0.866200 | 0.633642 | 0.740741 | `B3_T1_C10p0_cw_none` | 0.250000 |
| success | B0 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.274510 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| success | B1 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.274510 | 0.000000 | 0.430769 | `B1_prior` | 0.300000 |
| success | B2 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.705357 | 0.430848 | 0.692308 | `B2_C10p0_cw_balanced` | 0.550000 |
| success | B3 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.881986 | 0.607476 | 0.777778 | `B3_T1_C10p0_cw_balanced` | 0.300000 |
| side_effect | B0 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/49/2 | 0.039216 | 0.039216 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| side_effect | B1 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/49/2 | 0.039216 | 0.039216 | 0.000000 | 0.075472 | `B1_prior` | 0.050000 |
| side_effect | B2 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/49/2 | 0.039216 | 0.150000 | 0.110784 | 0.080000 | `B2_C10p0_cw_none` | 0.050000 |
| side_effect | B3 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/49/2 | 0.039216 | 1.000000 | 0.960784 | 0.500000 | `B3_T2_C10p0_cw_none` | 0.100000 |
| side_effect | B0 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 50/48/2 | 0.040000 | 0.040000 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| side_effect | B1 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 50/48/2 | 0.040000 | 0.040000 | 0.000000 | 0.076923 | `B1_prior` | 0.050000 |
| side_effect | B2 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 50/48/2 | 0.040000 | 0.095819 | 0.055819 | 0.071429 | `B2_C10p0_cw_none` | 0.050000 |
| side_effect | B3 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 50/48/2 | 0.040000 | 0.183333 | 0.143333 | 0.250000 | `B3_T2_C1p0_cw_balanced` | 0.450000 |
| side_effect | B0 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/40/3 | 0.069767 | 0.069767 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| side_effect | B1 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/40/3 | 0.069767 | 0.069767 | 0.000000 | 0.130435 | `B1_prior` | 0.050000 |
| side_effect | B2 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/40/3 | 0.069767 | 0.103781 | 0.034014 | 0.105263 | `B2_C1p0_cw_none` | 0.100000 |
| side_effect | B3 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/40/3 | 0.069767 | 0.777778 | 0.708010 | 0.444444 | `B3_T2_C1p0_cw_none` | 0.100000 |
| side_effect | B0 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/46/5 | 0.098039 | 0.098039 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| side_effect | B1 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/46/5 | 0.098039 | 0.098039 | 0.000000 | 0.000000 | `B1_prior` | 0.050000 |
| side_effect | B2 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/46/5 | 0.098039 | 0.105348 | 0.007308 | 0.000000 | `B2_C0p1_cw_none` | 0.200000 |
| side_effect | B3 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/46/5 | 0.098039 | 0.529412 | 0.431373 | 0.333333 | `B3_T1_C1p0_cw_none` | 0.100000 |
| looping | B0 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.274510 | 0.000000 | 0.430769 | `B0_most_frequent` | 0.500000 |
| looping | B1 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.274510 | 0.000000 | 0.430769 | `B1_prior` | 0.500000 |
| looping | B2 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.908394 | 0.633884 | 0.848485 | `B2_C10p0_cw_balanced` | 0.200000 |
| looping | B3 | `GenericAgent-anthropic_claude-3.7-sonnet` | full_primary_benchmark_coverage | 51/37/14 | 0.274510 | 0.597122 | 0.322612 | 0.577778 | `B3_T2_C10p0_cw_balanced` | 0.250000 |
| looping | B0 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 51/30/21 | 0.411765 | 0.411765 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| looping | B1 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 51/30/21 | 0.411765 | 0.411765 | 0.000000 | 0.583333 | `B1_prior` | 0.450000 |
| looping | B2 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 51/30/21 | 0.411765 | 0.947819 | 0.536055 | 0.909091 | `B2_C1p0_cw_none` | 0.450000 |
| looping | B3 | `GenericAgent-gpt-4o-2024-11-20` | full_primary_benchmark_coverage | 51/30/21 | 0.411765 | 0.807131 | 0.395366 | 0.792453 | `B3_T1_C10p0_cw_none` | 0.250000 |
| looping | B0 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/16/27 | 0.627907 | 0.627907 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| looping | B1 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/16/27 | 0.627907 | 0.627907 | 0.000000 | 0.771429 | `B1_prior` | 0.400000 |
| looping | B2 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/16/27 | 0.627907 | 0.951556 | 0.323649 | 0.923077 | `B2_C1p0_cw_none` | 0.600000 |
| looping | B3 | `GenericAgent-meta-llama_Llama-3.3-70B-Instruct` | partial_primary_benchmark_coverage | 43/16/27 | 0.627907 | 0.923937 | 0.296030 | 0.857143 | `B3_T2_C1p0_cw_balanced` | 0.400000 |
| looping | B0 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/21/30 | 0.588235 | 0.588235 | 0.000000 | 0.000000 | `B0_most_frequent` | 0.500000 |
| looping | B1 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/21/30 | 0.588235 | 0.588235 | 0.000000 | 0.740741 | `B1_prior` | 0.400000 |
| looping | B2 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/21/30 | 0.588235 | 0.850613 | 0.262378 | 0.903226 | `B2_C1p0_cw_balanced` | 0.350000 |
| looping | B3 | `GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct` | full_primary_benchmark_coverage | 51/21/30 | 0.588235 | 0.817659 | 0.229424 | 0.800000 | `B3_T1_C10p0_cw_balanced` | 0.250000 |

## All-model and full-coverage-model macro

| Target | Baseline | models full/partial | all AP mean±std | full AP mean±std | all F1 mean±std | full F1 mean±std |
|---|---|---:|---:|---:|---:|---:|
| success | B0 | 3/1 | 0.299274 ± 0.067561 | 0.321513 ± 0.062285 | 0.000000 ± 0.000000 | 0.000000 ± 0.000000 |
| success | B1 | 3/1 | 0.299274 ± 0.067561 | 0.321513 ± 0.062285 | 0.457631 ± 0.078209 | 0.484389 ± 0.069852 |
| success | B2 | 3/1 | 0.611160 ± 0.191221 | 0.679253 ± 0.164403 | 0.614640 ± 0.117433 | 0.652854 ± 0.109198 |
| success | B3 | 3/1 | 0.860455 ± 0.037497 | 0.858540 ± 0.045685 | 0.741418 ± 0.053031 | 0.741644 ± 0.064946 |
| side_effect | B0 | 3/1 | 0.061756 ± 0.028060 | 0.059085 ± 0.033738 | 0.000000 ± 0.000000 | 0.000000 ± 0.000000 |
| side_effect | B1 | 3/1 | 0.061756 ± 0.028060 | 0.059085 ± 0.033738 | 0.070707 ± 0.053629 | 0.050798 ± 0.043999 |
| side_effect | B2 | 3/1 | 0.113737 ± 0.024533 | 0.117056 ± 0.028926 | 0.064173 ± 0.045128 | 0.050476 ± 0.043923 |
| side_effect | B3 | 3/1 | 0.622631 ± 0.350309 | 0.570915 ± 0.409912 | 0.381944 ± 0.111976 | 0.361111 ± 0.127294 |
| looping | B0 | 3/1 | 0.475604 ± 0.163703 | 0.424837 ± 0.157271 | 0.107692 ± 0.215385 | 0.143590 ± 0.248705 |
| looping | B1 | 3/1 | 0.475604 ± 0.163703 | 0.424837 ± 0.157271 | 0.631568 ± 0.157190 | 0.584948 ± 0.154992 |
| looping | B2 | 3/1 | 0.914595 ± 0.046912 | 0.902275 ± 0.048891 | 0.895970 ± 0.032733 | 0.886934 ± 0.033427 |
| looping | B3 | 3/1 | 0.786462 ± 0.136808 | 0.740637 ± 0.124399 | 0.756843 ± 0.122821 | 0.723410 ± 0.126178 |

## Pooled LOMO and A1.2/A1.3 deltas

| Target | Baseline | n | prevalence | LOMO AP | LOMO F1 | ΔAP vs A1.2 | ΔF1 vs A1.2 | ΔAP vs A1.3 | ΔF1 vs A1.3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| success | B0 | 192 | 0.302083 | 0.302083 | 0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| success | B1 | 192 | 0.302083 | 0.270944 | 0.464000 | -0.023091 | +0.000000 | +0.008116 | +0.000000 |
| success | B2 | 192 | 0.302083 | 0.554719 | 0.619048 | +0.008687 | +0.019048 | +0.093356 | +0.078167 |
| success | B3 | 192 | 0.302083 | 0.822173 | 0.741259 | +0.467934 | +0.331902 | +0.524226 | +0.321904 |
| side_effect | B0 | 195 | 0.061538 | 0.061538 | 0.000000 | +0.000000 | +0.000000 | +0.000000 | +0.000000 |
| side_effect | B1 | 195 | 0.061538 | 0.050930 | 0.089744 | -0.004816 | -0.026198 | -0.001824 | +0.023077 |
| side_effect | B2 | 195 | 0.061538 | 0.086395 | 0.071429 | +0.015049 | -0.037267 | +0.044706 | +0.009573 |
| side_effect | B3 | 195 | 0.061538 | 0.279834 | 0.378378 | +0.054226 | +0.003378 | +0.232302 | +0.217664 |
| looping | B0 | 196 | 0.469388 | 0.439732 | 0.195804 | -0.029655 | +0.195804 | -0.009976 | -0.215307 |
| looping | B1 | 196 | 0.469388 | 0.396387 | 0.638889 | -0.059318 | +0.000000 | -0.039729 | +0.000000 |
| looping | B2 | 196 | 0.469388 | 0.886717 | 0.900524 | -0.017820 | +0.006051 | +0.050677 | +0.016101 |
| looping | B3 | 196 | 0.469388 | 0.732255 | 0.767123 | +0.099948 | +0.106490 | +0.065300 | +0.127718 |

## Model × Benchmark diagnostics

The machine-readable diagnostic has 192 rows: `{"no_coverage": 12, "ok": 136, "single_class_negative": 44}`. Single-class and no-coverage cells leave AP/F1 blank; the 0-sample Meta-Llama/VisualWebArena cells are marked `no_coverage`.

## Configuration, threshold, literal, and warning audit

- Selected configurations: `[{"baseline_id": "B0", "config_id": "B0_most_frequent", "count": 4, "target": "looping"}, {"baseline_id": "B1", "config_id": "B1_prior", "count": 4, "target": "looping"}, {"baseline_id": "B2", "config_id": "B2_C10p0_cw_balanced", "count": 1, "target": "looping"}, {"baseline_id": "B2", "config_id": "B2_C1p0_cw_balanced", "count": 1, "target": "looping"}, {"baseline_id": "B2", "config_id": "B2_C1p0_cw_none", "count": 2, "target": "looping"}, {"baseline_id": "B3", "config_id": "B3_T1_C10p0_cw_balanced", "count": 1, "target": "looping"}, {"baseline_id": "B3", "config_id": "B3_T1_C10p0_cw_none", "count": 1, "target": "looping"}, {"baseline_id": "B3", "config_id": "B3_T2_C10p0_cw_balanced", "count": 1, "target": "looping"}, {"baseline_id": "B3", "config_id": "B3_T2_C1p0_cw_balanced", "count": 1, "target": "looping"}, {"baseline_id": "B0", "config_id": "B0_most_frequent", "count": 4, "target": "side_effect"}, {"baseline_id": "B1", "config_id": "B1_prior", "count": 4, "target": "side_effect"}, {"baseline_id": "B2", "config_id": "B2_C0p1_cw_none", "count": 1, "target": "side_effect"}, {"baseline_id": "B2", "config_id": "B2_C10p0_cw_none", "count": 2, "target": "side_effect"}, {"baseline_id": "B2", "config_id": "B2_C1p0_cw_none", "count": 1, "target": "side_effect"}, {"baseline_id": "B3", "config_id": "B3_T1_C1p0_cw_none", "count": 1, "target": "side_effect"}, {"baseline_id": "B3", "config_id": "B3_T2_C10p0_cw_none", "count": 1, "target": "side_effect"}, {"baseline_id": "B3", "config_id": "B3_T2_C1p0_cw_balanced", "count": 1, "target": "side_effect"}, {"baseline_id": "B3", "config_id": "B3_T2_C1p0_cw_none", "count": 1, "target": "side_effect"}, {"baseline_id": "B0", "config_id": "B0_most_frequent", "count": 4, "target": "success"}, {"baseline_id": "B1", "config_id": "B1_prior", "count": 4, "target": "success"}, {"baseline_id": "B2", "config_id": "B2_C10p0_cw_balanced", "count": 2, "target": "success"}, {"baseline_id": "B2", "config_id": "B2_C1p0_cw_balanced", "count": 2, "target": "success"}, {"baseline_id": "B3", "config_id": "B3_T1_C10p0_cw_balanced", "count": 2, "target": "success"}, {"baseline_id": "B3", "config_id": "B3_T1_C10p0_cw_none", "count": 2, "target": "success"}]`
- Selected thresholds: `[{"baseline_id": "B0", "count": 4, "target": "looping", "threshold": 0.5}, {"baseline_id": "B1", "count": 2, "target": "looping", "threshold": 0.4}, {"baseline_id": "B1", "count": 1, "target": "looping", "threshold": 0.45}, {"baseline_id": "B1", "count": 1, "target": "looping", "threshold": 0.5}, {"baseline_id": "B2", "count": 1, "target": "looping", "threshold": 0.2}, {"baseline_id": "B2", "count": 1, "target": "looping", "threshold": 0.35}, {"baseline_id": "B2", "count": 1, "target": "looping", "threshold": 0.45}, {"baseline_id": "B2", "count": 1, "target": "looping", "threshold": 0.6}, {"baseline_id": "B3", "count": 3, "target": "looping", "threshold": 0.25}, {"baseline_id": "B3", "count": 1, "target": "looping", "threshold": 0.4}, {"baseline_id": "B0", "count": 4, "target": "side_effect", "threshold": 0.5}, {"baseline_id": "B1", "count": 4, "target": "side_effect", "threshold": 0.05}, {"baseline_id": "B2", "count": 2, "target": "side_effect", "threshold": 0.05}, {"baseline_id": "B2", "count": 1, "target": "side_effect", "threshold": 0.1}, {"baseline_id": "B2", "count": 1, "target": "side_effect", "threshold": 0.2}, {"baseline_id": "B3", "count": 3, "target": "side_effect", "threshold": 0.1}, {"baseline_id": "B3", "count": 1, "target": "side_effect", "threshold": 0.45}, {"baseline_id": "B0", "count": 4, "target": "success", "threshold": 0.5}, {"baseline_id": "B1", "count": 2, "target": "success", "threshold": 0.25}, {"baseline_id": "B1", "count": 2, "target": "success", "threshold": 0.3}, {"baseline_id": "B2", "count": 2, "target": "success", "threshold": 0.35}, {"baseline_id": "B2", "count": 1, "target": "success", "threshold": 0.55}, {"baseline_id": "B2", "count": 1, "target": "success", "threshold": 0.7}, {"baseline_id": "B3", "count": 1, "target": "success", "threshold": 0.2}, {"baseline_id": "B3", "count": 2, "target": "success", "threshold": 0.25}, {"baseline_id": "B3", "count": 1, "target": "success", "threshold": 0.3}]`
- Model literal audit: `{"affected_trajectory_count": 0, "audit_row_count": 196, "candidate_rules": "exact manifest model plus unique aliases derived from manifest strings", "literal_occurrence_count": 0, "metadata_or_serializer_injection_detected": false, "redaction_performed": false, "trajectory_count": 196}`
- Warnings: 1104 total; convergence warnings: 0.

## Completeness and integrity

- External predictions: 2332/2332.
- Selected inner OOF predictions: 6996/6996.
- Configuration rows: 240/240; threshold rows: 912/912; model metrics: 48/48.
- Frozen hashes before/after identical: True.
- test access: 0; prohibited experiments: none; network: 0; GPU: 0.

## Cross-model signal grades

- success: `robust_cross_model_signal`
- side_effect: `robust_cross_model_signal`
- looping: `robust_cross_model_signal`

## Interpretation and stop boundary

The external task overlap is expected by design: every held-out trajectory has a training-side trajectory for the same group_key from another model. Results support only exploratory cross-model generalization, not simultaneous cross-task and cross-model OOD generalization.

Stop after A1.4. Do not begin A1.5, ablations, fusion, complex models, or test evaluation without a new human stage-gate approval.
