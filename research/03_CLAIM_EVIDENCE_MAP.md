# D9-R1 Claim–Evidence Map

| Claim ID | Candidate claim | Required evidence | Evidence location | Status | Notes |
|---|---|---|---|---|---|
| C1 |  |  |  | Unassessed |  |
| FC1 | Frozen Success B2 retains predictive signal on official held-out tasks and trajectories within the existing benchmark families. | Frozen blind probabilities; pooled AP lift above zero; 95% within-benchmark task-group cluster-bootstrap lower bound above zero. | `artifacts/a1_10_target_metrics.csv`; `artifacts/a1_10_bootstrap_summary.csv`; `artifacts/a1_10_confirmatory_grade.csv` | CONFIRMED_HELDOUT_SIGNAL | Scope excludes unseen-Benchmark and joint task/model OOD generalization. |
| FC2 | Frozen Looping B2 retains predictive signal on official held-out tasks and trajectories within the existing benchmark families. | Frozen blind probabilities; pooled AP lift above zero; 95% within-benchmark task-group cluster-bootstrap lower bound above zero. | `artifacts/a1_10_target_metrics.csv`; `artifacts/a1_10_bootstrap_summary.csv`; `artifacts/a1_10_confirmatory_grade.csv` | CONFIRMED_HELDOUT_SIGNAL | Scope excludes unseen-Benchmark and joint task/model OOD generalization. |
| FE1 | Frozen Side Effect B4 official-test result. | Frozen blind probabilities and preregistered exploratory metrics/uncertainty. | `artifacts/a1_10_target_metrics.csv`; `artifacts/a1_10_bootstrap_summary.csv`; `artifacts/a1_10_confirmatory_grade.csv` | EXPLORATORY_TEST_RESULT | Must not be upgraded to a confirmatory claim regardless of numerical performance. |
