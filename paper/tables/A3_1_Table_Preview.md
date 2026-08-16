# A3.1 Table Preview

Human-review preview only. Machine-exact values remain in the frozen A2.3 CSV sources and the A3.1 display-value map.

# Table 1. Main held-out results

Official held-out tasks/trajectories within evaluated benchmark families using frozen thresholds. Success and Looping are confirmatory; Side Effect is exploratory.

| Target | Frozen method | N | Positive | Negative | Prevalence | AP | AP lift | F1 | AP-lift 95% CI | Evidence status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Success | FINAL_SUCCESS_B2 | 1097 | 291 | 806 | 0.265 | 0.655 | 0.390 | 0.682 | [0.327, 0.455] | CONFIRMATORY_SUPPORTED |
| Looping | FINAL_LOOPING_B2 | 1095 | 577 | 518 | 0.527 | 0.922 | 0.395 | 0.877 | [0.361, 0.429] | CONFIRMATORY_SUPPORTED |
| Side Effect | FINAL_SIDE_EFFECT_B4 | 1102 | 71 | 1031 | 0.064 | 0.107 | 0.043 | 0.169 | [0.021, 0.079] | EXPLORATORY_SUPPORTED |

---

# Table 2. Efficiency and complexity

Environment-specific measurements only: B2 used CPU and B4 used CUDA on an NVIDIA GeForce RTX 5070. No cross-target AP comparison is implied.

| Method | Representation | Dim. | Measured device | Warm extraction / traj. | Classifier inference / traj. | Representation storage | Classifier | Encoder | Peak CPU RSS | Peak GPU VRAM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B2 | frozen structural full13 | 13 | CPU | 0.01343 ms | 0.0007026 ms | 20.0 KiB | 1.16 KiB | NA | 155 MiB | NA |
| B4 | frozen Qwen3 dense semantic | 1024 | CUDA RTX 5070 | 2.37e3 ms | 0.001803 ms | 784 KiB | 8.34 KiB | 1.16e6 KiB | 2.16e3 MiB | 1.54e3 MiB |

---

# Table 3. Development representation and robustness evidence

**DEV_ONLY** - All entries are DEV_ONLY. Exploratory development rows retain their original EXPLORATORY_DEV status; no held-out or confirmatory upgrade is made.

| Stage | Target | Evidence area | Representation/comparison | Metric | Estimate | Frozen 95% CI | Source status | Claim boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1.2 | Success | Minimal grouped baselines | full structural | pooled AP | 0.546 | NA | DEV_ONLY | provisional dev signal |
| A1.2 | Side Effect | Minimal grouped baselines | TF-IDF sparse text | pooled AP | 0.226 | NA | EXPLORATORY_DEV | low-support dev signal |
| A1.2 | Looping | Minimal grouped baselines | full structural | pooled AP | 0.905 | NA | DEV_ONLY | provisional dev signal |
| A1.3 | Success | External / LOBO | full structural | macro AP | 0.480 | NA | DEV_ONLY | dev-only cross-family evidence |
| A1.3 | Side Effect | External / LOBO | TF-IDF sparse text | macro AP | 0.112 | NA | EXPLORATORY_DEV | diagnostic; sparse support |
| A1.3 | Looping | External / LOBO | full structural | macro AP | 0.851 | NA | DEV_ONLY | dev-only cross-family evidence |
| A1.4 | Success | Model-only transfer | TF-IDF sparse text | all-model macro AP | 0.860 | NA | EXPLORATORY_DEV | same-task model-only transfer |
| A1.4 | Side Effect | Model-only transfer | TF-IDF sparse text | all-model macro AP | 0.623 | NA | EXPLORATORY_DEV | exploratory and low-support |
| A1.4 | Looping | Model-only transfer | full structural | all-model macro AP | 0.915 | NA | EXPLORATORY_DEV | same-task model-only transfer |
| A1.5 | Success | Structural ablation | termination + repetition structural subset | macro AP | 0.512 | NA | DEV_ONLY | competitive point estimate; not equivalence |
| A1.5 | Looping | Structural ablation | structural without repetition group | macro AP | 0.819 | NA | DEV_ONLY | predictive dependency; non-causal |
| A1.6 | Success | Uncertainty | full structural positive-signal uncertainty | macro_ap_lift | 0.180 | [0.108, 0.344] | DEV_ONLY | stable positive dev LOBO signal |
| A1.6 | Success | Uncertainty | B2 versus B3 uncertainty | macro_ap_delta_A_minus_B | 0.057 | [-0.120, 0.256] | DEV_ONLY | B2-B3 difference uncertain |
| A1.6 | Looping | Uncertainty | full structural positive-signal uncertainty | macro_ap_lift | 0.404 | [0.334, 0.506] | DEV_ONLY | stable positive dev LOBO signal |
| A1.6 | Looping | Uncertainty | repetition-group ablation uncertainty | macro_ap_delta_A_minus_B | -0.032 | [-0.080, -0.004] | DEV_ONLY | stable repetition-feature increment; non-causal |
| A1.7 | Success | Dense semantics | dense semantic positive-signal uncertainty | macro_ap_lift | 0.245 | [0.165, 0.382] | DEV_ONLY | stable positive signal; no stable relative gain |
| A1.7 | Side Effect | Dense semantics | dense semantic support diagnostic | macro_ap | 0.147 | [0.081, 0.478] | EXPLORATORY_DEV | support diagnostic only |
| A1.7 | Looping | Dense semantics | dense semantic versus structural uncertainty | macro_ap_delta_A_minus_B | -0.056 | [-0.166, 0.055] | DEV_ONLY | relative difference uncertain |

---

# Table 4. Benchmark heterogeneity

**DESCRIPTIVE_ONLY** - DESCRIPTIVE_ONLY benchmark heterogeneity. No winner ranking, significance mark, or pairwise inference is authorized.

| Target | Benchmark family | AP | F1 | Role | Evidence status |
| --- | --- | --- | --- | --- | --- |
| Success | assistantbench | 0.357 | 0.313 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Success | visualwebarena | 0.654 | 0.655 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Success | webarena | 0.642 | 0.692 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Success | workarena | 0.675 | 0.761 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Looping | assistantbench | 0.713 | 0.774 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Looping | visualwebarena | 0.869 | 0.863 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Looping | webarena | 0.931 | 0.853 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Looping | workarena | 0.963 | 0.909 | confirmatory_primary | DESCRIPTIVE_ONLY |
| Side Effect | assistantbench | 0.044 | 0.000 | exploratory_only | DESCRIPTIVE_ONLY |
| Side Effect | visualwebarena | 0.136 | 0.199 | exploratory_only | DESCRIPTIVE_ONLY |
| Side Effect | webarena | 0.102 | 0.154 | exploratory_only | DESCRIPTIVE_ONLY |
| Side Effect | workarena | 0.117 | 0.114 | exploratory_only | DESCRIPTIVE_ONLY |

---

# Table 5. Interpretability and failure summary

Associative/diagnostic coefficients are not causal effects. Metadata comparison is descriptive. Error cases are deterministic illustrations, not prevalence estimates.

| Target | Top signed structural signals | Metadata AP | Metadata AP lift | Frozen B2 dev AP | Deterministic illustrative cases | Interpretation | Evidence status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Success | observation_char_count_total: -2.204<br>observation_char_count_mean_nonempty: 1.879<br>action_char_count_total: 0.732<br>has_explicit_termination_signal: -0.610<br>unique_action_ratio: 0.520 | 0.371 | 0.069 | 0.547 | LONG_BUT_UNSUCCESSFUL:2; REPETITIVE_BUT_PROGRESSING:1; SHORT_BUT_SUCCESSFUL:1; TERMINATION_MISMATCH:2 | Associations and deterministic cases delimit where task-agnostic structure tracks execution morphology but misses semantic completion; coefficients are not causal importance. | DEV_ONLY;POST_FREEZE_DIAGNOSTIC;POST_FREEZE_DESCRIPTIVE |
| Looping | observation_char_count_mean_nonempty: -0.830<br>nonempty_action_count: 0.695<br>nonempty_observation_count: 0.695<br>step_count: 0.695<br>nonempty_focused_element_count: 0.670 | 0.569 | 0.099 | 0.914 | EXPLICIT_ERROR_RECOVERY:1; NON_REPETITIVE_FAILURE:2; OTHER:1; REPETITIVE_BUT_PROGRESSING:1; UNCLEAR:1 | Associations and deterministic cases distinguish literal action repetition from progress and semantic cycling; coefficients are not causal importance. | DEV_ONLY;POST_FREEZE_DIAGNOSTIC;POST_FREEZE_DESCRIPTIVE |

---
