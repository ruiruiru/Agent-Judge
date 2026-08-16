# A1.11 Limitations Ledger

| ID | Frozen limitation | Evidence consequence | Manuscript requirement |
|---|---|---|---|
| L1 | Benchmark-family scope | The official holdout contains tasks/trajectories from evaluated benchmark families, not a truly independent unseen benchmark. | Do not claim unseen-benchmark generalization. |
| L2 | Agent/model scope | A1.4 holds out Agent model names while the same underlying tasks remain represented on the training side; the official test is not joint task/model OOD. | Do not claim arbitrary-Agent or joint OOD robustness. |
| L3 | Side Effect support | Side Effect had 12 eligible positive dev trajectories and was frozen as exploratory-only before test. | Always say exploratory_only, low-support, and not confirmatory. |
| L4 | Label and construct limitations | The data contract records consensus exclusions, an audit-only official primary rule, and no standard license identifier. | Describe only documented annotation/data-contract limitations; do not invent construct facts. |
| L5 | Prediction is not causation | Structural prediction and ablation effects do not identify causal mechanisms. | Use predictive-association language for termination and repetition features. |
| L6 | Benchmark heterogeneity | Success and the other targets show materially different descriptive AP/F1 across families. | Treat this as an external-validity limitation and future-work motivation, not pairwise significance. |
| L7 | Comparative representation uncertainty | Several B2/B3/B4 and S6/S0 paired intervals cross zero; one Success B4-B2 F1 contrast is a stable drop. | Do not assert a universal representation or complexity hierarchy. |
| L8 | Operational validity | Calibration, selective prediction, deployment utility, and online behavior were not evaluated. | Do not present scores as calibrated risk or deployment safety evidence. |

These limitations are part of the final claim contract. Removing or weakening one requires a newly approved Stage.
