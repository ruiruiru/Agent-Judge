# A1.11 Paper Results Outline

| Section | Frozen source | Table / figure | Allowed claim | Forbidden interpretation |
|---|---|---|---|---|
| R1. Development-stage signal discovery | `artifacts/a1_2_pooled_metrics.csv` | Dev evidence summary | Report target-specific dev signal patterns. | Confirmatory or held-out claims. |
| R2. Grouped-fold and held-out-family robustness | `artifacts/a1_3_lobo_macro_metrics.csv` | Dev evidence summary | Success and Looping show dev LOBO signal. | Generalization to unseen benchmark datasets. |
| R3. Structural ablations and uncertainty | `artifacts/a1_6_primary_paired_delta_summary.csv` | Figure 4 | Repetition features add predictive value for Looping under the frozen dev protocol. | Causal mechanism or untested equivalence. |
| R4. Dense semantic comparison | `artifacts/a1_7_bootstrap_primary_summary.csv` | Figure 4 | Dense Success signal exists; relative gains are mostly uncertain. | Universal dense superiority or necessity. |
| R5. Final freeze and blind protocol | `artifacts/a1_9_run_summary.json`; `artifacts/a1_10a_run_summary.json` | Figure 1 | Models, thresholds, roles, and blind predictions were frozen before labels. | Test-driven selection or tuning. |
| R6. Official held-out Success | `artifacts/a1_11_table_main_test_results.csv` | Main table; Figure 2 | FC1 within evaluated benchmark families. | Unseen-benchmark, arbitrary-Agent, joint OOD, or causal claims. |
| R7. Official held-out Looping | `artifacts/a1_11_table_main_test_results.csv` | Main table; Figure 2 | FC2 within evaluated benchmark families. | Universal Looping judge or causal explanation. |
| R8. Exploratory Side Effect | `artifacts/a1_11_table_main_test_results.csv` | Main table; Figure 2 | FE1 as exploratory, low-support, non-confirmatory evidence. | Confirmed Side Effect detector. |
| R9. Benchmark heterogeneity | `artifacts/a1_11_table_benchmark_results.csv` | Figure 3 | Performance varies descriptively across families. | Pairwise statistical superiority. |
| R10. Claim boundaries and limitations | `artifacts/a1_11_final_claim_matrix.csv`; `docs/a1_11_limitations_ledger.md` | Claim ledger | State frozen scope and negative evidence. | Removing limitations or promoting claims without a new Stage. |
