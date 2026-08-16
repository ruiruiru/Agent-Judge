# A2.3 Publication Figure Specification

No final publication figure is generated in Stage A2.3. Every mark below must be produced later only from the listed frozen fields.

## Figure 1 — Study and blind-first evaluation pipeline

- Source artifacts: `artifacts/a1_11_evidence_registry.csv`, `artifacts/a1_9_run_summary.json`, `artifacts/a1_10a_run_summary.json`, `artifacts/a1_10_run_summary.json`.
- Exact fields: stage/commit/artifact provenance; frozen method and threshold records; blind-prediction hash; label-unlock sequence.
- Evidence status: `INTEGRITY_ONLY` and protocol provenance.
- Axes / labels: left-to-right stages — grouped dev evidence → method freeze → blind inference → one-time label unlock → frozen scoring → A2 diagnostics.
- Allowed caption: models, roles, thresholds, and blind prediction bytes were frozen before official-test labels/metrics were available.
- Prohibited interpretation: unseen-benchmark, arbitrary-agent, or joint task/model OOD generalization.

## Figure 2 — Official held-out AP lift and frozen 95% CI

- Source artifact: `artifacts/a2_3_table_1_main_heldout_results.csv` (exactly mapped from A1.11).
- Exact fields: `target`, `AP_lift`, `AP_lift_CI_low`, `AP_lift_CI_high`, `claim_status`, `scope`.
- Evidence status: Success and Looping `CONFIRMATORY_SUPPORTED`; Side Effect `EXPLORATORY_SUPPORTED`.
- Axes / labels: x-axis target; y-axis pooled AP lift; zero reference line; Side Effect visibly labeled exploratory.
- Allowed caption: frozen structural evaluators retain confirmatory held-out predictive signal for Success and Looping on official held-out tasks/trajectories within evaluated benchmark families; Side Effect is exploratory.
- Prohibited interpretation: Side Effect confirmation, calibration, unseen-benchmark generalization, or benchmark pairwise superiority.

## Figure 3 — Efficiency and representation complexity

- Source artifact: `artifacts/a2_3_table_2_efficiency_tradeoff.csv` (exactly mapped from A2.1).
- Exact fields: `method`, `dimension`, `device`, `extraction_ms_per_trajectory`, `inference_ms_per_trajectory`, `representation_size_bytes`, `classifier_size_bytes`, `encoder_size_bytes`, `peak_cpu_rss_mb`, `peak_gpu_vram_mb`, `environment_specific`.
- Evidence status: `EFFICIENCY_BENCHMARK`; environment-specific.
- Axes / labels: separate panels for extraction latency (log scale), representation bytes (log scale), and representation dimension; annotate CPU/GPU devices rather than merging resource domains.
- Allowed caption: B2 required substantially lower representation and extraction cost than B4 under the recorded environment.
- Prohibited interpretation: universal efficiency, cross-hardware superiority, or a cross-target accuracy–efficiency frontier.

## Figure 4 — Structural interpretation and dev uncertainty

- Source artifacts: `artifacts/a2_3_table_3_dev_representation_summary.csv`, `artifacts/a2_2_feature_group_evidence.csv`, `artifacts/a2_2_structural_coefficients.csv`.
- Exact fields: Table 3 `target`, `method_or_comparison`, `point_estimate`, `CI_low_95`, `CI_high_95`, `evidence_status`; A2.2 `feature_group`, `point_estimate`, `uncertainty_status`; coefficient `feature`, `standardized_coefficient`, `absolute_rank`.
- Evidence status: `DEV_ONLY` and `POST_FREEZE_DIAGNOSTIC`.
- Axes / labels: coefficient panel uses signed standardized coefficient; feature-group panel uses frozen delta and interval/status where available; explicitly mark missing A1.6 uncertainty.
- Allowed caption: frozen associations and ablations identify predictive structural patterns under the dev protocol; several comparisons remain uncertain.
- Prohibited interpretation: causal feature importance, equivalence, dense semantic necessity/unnecessity, or confirmatory upgrade.

## Figure 5 — Success error taxonomy

- Source artifacts: `artifacts/a2_2_error_case_manifest.csv`, `artifacts/a2_2_error_case_notes.csv`, and summary `artifacts/a2_3_table_5_interpretability_error_summary.csv`.
- Exact fields: `error_type`, `case_role`, `primary_code`, `secondary_code`, `representation_boundary`, `semantic_understanding_needed`, `evidence_status`.
- Evidence status: `POST_FREEZE_DESCRIPTIVE`.
- Axes / labels: compact taxonomy/tree or case matrix; distinguish FP/FN and borderline/median/high-confidence selection roles; do not plot category frequency as prevalence.
- Allowed caption: deterministic cases illustrate where execution morphology diverges from semantic task completion.
- Prohibited interpretation: population prevalence, exhaustive taxonomy, causal mechanism, or post-hoc model modification.

## Appendix alternative

The frozen benchmark heterogeneity table may replace Figure 5 or appear in the appendix. If plotted, use `target`, `benchmark`, `AP`, and `evidence_status` from `artifacts/a2_3_table_4_benchmark_heterogeneity.csv`; every caption and panel must say `DESCRIPTIVE_ONLY`, with no pairwise significance marks.
