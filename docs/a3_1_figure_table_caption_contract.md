# A3.1 Figure and Table Caption Contract

These captions describe frozen evidence only. They do not authorize new claims or manuscript prose.

## Boundary vocabulary

- `confirmatory`: Success and Looping official held-out signal within evaluated benchmark families.
- `exploratory`: Side Effect remains low-support and non-confirmatory.
- `DEV_ONLY`: A1.2-A1.7 representation, robustness, ablation, and uncertainty evidence.
- `DESCRIPTIVE_ONLY`: benchmark heterogeneity without pairwise inference.
- `environment-specific`: A2.1 timings and resources on the recorded CPU/GPU environment.
- `illustrative-not-prevalence`: deterministic selected error cases do not estimate population frequencies.

## Frozen captions

### Table1_Main_Heldout_Results

Official held-out tasks/trajectories within evaluated benchmark families using frozen thresholds. Success and Looping are confirmatory; Side Effect is exploratory and low-support.

### Table2_Efficiency_Complexity

Environment-specific efficiency and representation measurements. B2 used CPU and B4 used CUDA on an NVIDIA GeForce RTX 5070; no cross-target AP comparison is implied.

### Table3_Dev_Representation_Robustness

DEV_ONLY grouped, LOBO, model-only, ablation, uncertainty, and dense-representation evidence. Exploratory development rows remain exploratory and no held-out upgrade is implied.

### Table4_Benchmark_Heterogeneity

DESCRIPTIVE_ONLY per-family AP and F1. No significance testing, winner ranking, or pairwise superiority is shown.

### Table5_Interpretability_Failure_Summary

Associative coefficients and metadata diagnostics with deterministic illustrative error cases. Coefficients are not causal effects and case counts are not prevalence estimates.

### Fig1_Study_Pipeline

Blind-first study pipeline. Method roles and thresholds were frozen before blind prediction, label unlock, and held-out confirmation; A2 diagnostics occur only post-freeze.

### Fig2_Heldout_AP_Lift_CI

Confirmatory held-out AP lift and frozen 95% confidence intervals for Success and Looping on official held-out tasks/trajectories within evaluated benchmark families.

### Fig3_Efficiency_Complexity

Representation dimension, warm extraction latency, and representation storage under the measured environment only: B2 CPU and B4 CUDA on an NVIDIA GeForce RTX 5070.

### Fig4_Structural_Interpretation

Top-five signed standardized coefficients for frozen Success and Looping structural models. Coefficients are associative, diagnostic, and not causal effects.

### Fig5_Success_Failure_Boundaries

Six deterministic illustrative Success errors selected under the frozen A2.2 protocol. The cards illustrate representation boundaries and are not a prevalence estimate.

### FigS1_SideEffect_Exploratory_AP_Lift

EXPLORATORY held-out Side Effect AP lift and frozen 95% confidence interval. Low support and the preregistered exploratory role prohibit confirmatory interpretation.

### FigS2_Benchmark_Heterogeneity

DESCRIPTIVE_ONLY AP by evaluated benchmark family. No significance marks, winner ranking, or pairwise inference are shown; Side Effect remains exploratory.
