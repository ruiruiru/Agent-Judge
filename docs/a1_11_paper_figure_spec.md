# A1.11 Paper Figure Specification

## Figure 1 — Blind-first evaluation protocol

- Question: how did development-only selection lead to an untouched official held-out evaluation?
- Source: `artifacts/a1_9_run_summary.json`, `artifacts/a1_10a_run_summary.json`, `artifacts/a1_10_run_summary.json`.
- Layout: left-to-right protocol timeline: dev-only grouped selection → A1.9 method/threshold/hash freeze → A1.10a identifier/content-only inference → blind prediction commit/hash → one-time label unlock → A1.10b frozen scoring.
- Caption emphasis: labels, eligibility, and metrics were unavailable when blind predictions were generated; blind prediction bytes were unchanged after unlock.
- Forbidden interpretation: the protocol does not establish unseen-benchmark or joint task/model OOD generalization.

## Figure 2 — Final held-out AP lift with frozen 95% CI

- Question: which targets retain positive signal above their held-out prevalence?
- Source: `artifacts/a1_10_bootstrap_summary.csv` and `artifacts/a1_10_confirmatory_grade.csv`.
- Marks: one point and frozen percentile interval per target; no new bootstrap.
- X-axis: target. Y-axis: pooled AP lift. Reference line: zero.
- Status encoding: Success and Looping are confirmatory; Side Effect is visually and textually marked exploratory-only.
- Caption emphasis: official held-out tasks/trajectories within evaluated benchmark families.

## Figure 3 — Per-benchmark descriptive AP

- Question: how does observed signal strength vary across evaluated benchmark families?
- Source: `artifacts/a1_10_benchmark_metrics.csv` or the frozen copy `artifacts/a1_11_table_benchmark_results.csv`.
- X-axis: benchmark family. Y-axis: AP. Facet or color: target.
- Caption requirement: descriptive heterogeneity only; not a preregistered pairwise significance comparison.
- Forbidden annotation: significance stars, pairwise p-values, or claims that one benchmark significantly outperforms another.

## Figure 4 — Development representation and ablation evidence

- Question: what development-stage evidence motivated the frozen target-specific methods?
- Source: `artifacts/a1_6_primary_paired_delta_summary.csv`, `artifacts/a1_7_bootstrap_primary_summary.csv`, and `artifacts/a1_11_dev_evidence_summary.csv`.
- Suggested panels: Success B2/B3/B4 paired estimates; Looping repetition ablation; Side Effect support diagnostic.
- Status label: `DEV_ONLY` on the figure and in the caption.
- Caption emphasis: several comparative intervals cross zero; ablations are predictive, not causal; Side Effect dev support is sparse.
