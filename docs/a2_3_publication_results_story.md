# A2.3 Publication Results Story

This document freezes the results narrative; it is not a manuscript.

## Title candidates

1. Lightweight Structural Signals for Web-Agent Trajectory Evaluation: Blind Held-Out Evidence and Failure Boundaries
2. How Far Can Structure Go? Efficient Web-Agent Trajectory Evaluation under Frozen Held-Out Testing
3. Evidence, Efficiency, and Limits of Structural Web-Agent Trajectory Evaluation
4. Dimension-Aware Lightweight Evaluation of Web-Agent Trajectories under Benchmark Shift

## One-sentence problem

Web-agent trajectory evaluation needs evidence beyond terminal outcomes, but it is unclear how far inexpensive task-agnostic structural signals remain predictive under grouped development and blind held-out evaluation.

## One-sentence main finding

Frozen lightweight structural evaluators retained confirmatory held-out predictive signal for Success and Looping on official held-out tasks/trajectories within the evaluated benchmark families, with substantially lower measured representation/extraction cost than the frozen dense semantic comparator under the recorded environment, while metadata diagnostics and deterministic errors expose unresolved confounding and semantic failure boundaries.

## Contributions

1. A staged, blind-first evaluation of task-agnostic structural trajectory evidence with grouped development protocols and frozen official held-out scoring.
2. Target-specific evidence showing confirmatory Success and Looping signal, while preserving Side Effect as exploratory and low-support.
3. An environment-qualified efficiency comparison between frozen 13-dimensional structural and 1,024-dimensional dense semantic representations, without cross-target performance–efficiency fabrication.
4. Post-freeze associational, metadata-confounder, and deterministic error diagnostics that delimit what morphology-only evaluation can and cannot support.

## Frozen research questions

### RQ1

Do lightweight structural trajectory signals contain predictive information for agent evaluation?

### RQ2

How robust are these signals across grouped tasks, benchmarks, and model shifts within the development evidence?

### RQ3

Which structural feature groups contribute most consistently?

### RQ4

Does dense semantic representation provide stable gains over lightweight structural representation in the studied dev regime?

### RQ5

Do frozen structural evaluators retain signal on the official blind held-out test?

### RQ6

What are the efficiency advantages, confounding risks, and characteristic failure modes of structural evaluation?

## Results section order

1. **R1 — Held-out predictive evidence.** Lead with Success, then Looping, then explicitly exploratory Side Effect using Table 1 and Figure 2.
2. **R2 — Development robustness and representation evidence.** Summarize grouped, LOBO, same-task model-only transfer, ablation, and dense semantic comparisons as dev-only evidence using Table 3 and Figure 4.
3. **R3 — Efficiency.** Present the exact A2.1 cost table and environment boundaries using Table 2 and Figure 3.
4. **R4 — Interpretability, confounders, and failure boundaries.** Present associational coefficients, feature-group evidence, metadata diagnostics, and deterministic cases using Table 5 and Figure 5; place descriptive benchmark heterogeneity in Table 4/appendix.

## Main tables

- Table 1: official held-out results — main text.
- Table 2: efficiency and representation cost — main text.
- Table 3: A1.2–A1.7 dev representation/robustness evidence — condensed main text, full appendix.
- Table 4: benchmark heterogeneity — appendix, `DESCRIPTIVE_ONLY`.
- Table 5: interpretability/confounder/error summary — main text, with detailed coefficients and cases in appendix.

## Main figures

- Figure 1: study and blind-first evaluation pipeline.
- Figure 2: held-out AP lift with frozen 95% CI.
- Figure 3: efficiency and representation complexity under the recorded environment.
- Figure 4: structural interpretation and dev uncertainty.
- Figure 5: Success error taxonomy; benchmark heterogeneity is the appendix alternative.

## Allowed claims

- Success and Looping show **confirmatory held-out predictive signal** on official held-out tasks/trajectories **within evaluated benchmark families**.
- Side Effect is exploratory, low-support, and non-confirmatory.
- B2 has substantially lower representation/extraction cost than B4 under the recorded environment.
- Metadata contains non-trivial signal; frozen B2 dev AP is descriptively higher, but confounding cannot be fully excluded.
- Deterministic cases illustrate failure modes where structural morphology diverges from semantic task completion or progress.
- Development ablations and coefficients support predictive-association wording only.

## Prohibited claims

- unseen-benchmark generalization
- joint task/model OOD generalization
- universal Agent Judge
- universal LLM Judge replacement
- causal mechanism
- dense semantics are generally unnecessary
- structural models are universally more efficient
- metadata confounding completely ruled out
- B2 significantly beats metadata-only
- benchmark pairwise superiority
- Side Effect confirmed

## Limitations

The paper must retain all items in `docs/a2_3_final_limitations_ledger.md`, including evaluated-family external validity, Side Effect support, benchmark heterogeneity, dev-only comparisons, non-causal ablations, coefficient correlation, unresolved metadata confounding, environment-specific timing, morphology-versus-semantics, and missing calibration/deployment evidence.

## Appendix plan

- Full baseline completeness hierarchy, including Tier 4 entries marked for literature verification.
- Full A1.2–A1.7 dev evidence and uncertainty table.
- Per-benchmark descriptive table/plot with no pairwise significance language.
- Full standardized coefficient and feature-group evidence tables.
- All 12 deterministic error cases, retaining `UNCLEAR` and evidence sufficiency notes.
- Provenance and package-index hashes; frozen claim/evidence map.

## Remaining work

- Human literature verification for Tier 4 definitions and any comparable numbers before manuscript use.
- Human A2.3 review and placement decisions.
- Full manuscript writing only under a separate authorization.
- External validation only after a separately approved adapter/data/label audit; current decision is `DEFER_TO_REVISION`.
- A3 artifact freeze only after a new human stage-gate decision.
