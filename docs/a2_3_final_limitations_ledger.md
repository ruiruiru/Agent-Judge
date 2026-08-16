# A2.3 Final Limitations Ledger

All A1.11 limitations remain active. A2.3 adds specificity but does not delete, weaken, or resolve them.

| ID | Frozen limitation | Evidence consequence | Manuscript requirement | Inheritance / source |
|---|---|---|---|---|
| L1 | External validity is limited to evaluated benchmark families. | Official held-out rows are new tasks/trajectories from existing benchmark families, not a truly independent unseen benchmark. | Do not claim unseen-benchmark generalization. | A1.11 L1 |
| L2 | Agent/model scope is limited. | A1.4 is same-task model-only transfer; official test is not joint task/model OOD. | Do not claim arbitrary-agent or joint task/model OOD robustness. | A1.11 L2 |
| L3 | Side Effect has low support. | Only 12 eligible positive dev trajectories supported the exploratory freeze. | Always label Side Effect exploratory, low-support, and non-confirmatory. | A1.11 L3 |
| L4 | Label and construct limitations remain. | Consensus exclusions, the audit-only official-primary rule, and the missing standard license identifier constrain interpretation. | State documented data-contract limitations without inventing construct facts. | A1.11 L4 |
| L5 | Prediction and ablation are not causation. | Structural associations and removal deltas do not identify mechanisms. | Use predictive-association language only. | A1.11 L5 |
| L6 | Benchmark heterogeneity is descriptive. | AP/F1 vary across evaluated families without preregistered pairwise tests. | Treat heterogeneity as an external-validity limitation; do not assert benchmark pairwise superiority. | A1.11 L6 |
| L7 | Relative method comparisons are development-only and partly uncertain. | Several B2/B3/B4 and S6/S0 intervals cross zero; one Success B4–B2 F1 contrast is a stable drop. | Do not assert a universal representation or complexity hierarchy. | A1.11 L7 |
| L8 | Calibration and deployment evidence are absent. | Calibration, selective prediction, online behavior, and deployment utility were not evaluated. | Do not present scores as calibrated risk or deployment-safety evidence. | A1.11 L8 |
| L9 | Coefficient interpretation is limited by correlated structural features. | Standardized LR coefficients can redistribute association among correlated counts and lengths. | Do not rank coefficients as isolated or causal importance. | A2.2 coefficients |
| L10 | Metadata confounding is not fully ruled out. | Benchmark/model metadata contains non-trivial dev signal; frozen B2 is only descriptively higher. | Do not say confounding is eliminated or that B2 significantly beats metadata-only. | A2.2 metadata audit |
| L11 | Efficiency timing is environment-specific. | B2 and B4 used different devices/resource domains under one recorded machine; background and hardware conditions may matter. | Qualify all timing/storage/memory claims with the recorded environment and do not universalize them. | A2.1 efficiency benchmark |
| L12 | Structural morphology is not semantic task understanding. | Short successful traces, long semantic failures, productive repetition, and semantic cycles expose representation boundaries. | Present deterministic errors as illustrations, not prevalence estimates or proof that semantics are unnecessary. | A2.2 deterministic error analysis |

Changing or removing any item requires a newly approved stage.
