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
