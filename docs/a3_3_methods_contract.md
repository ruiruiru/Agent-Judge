# A3.3 Methods Contract

## Required method blocks

| ID | Topic | Selection role | Required boundary |
|---|---|---|---|
| M1 | Data provenance | development evidence | Do not imply a new benchmark or modified expert labels. |
| M2 | Eligibility / labels | development and frozen test contract | Side Effect is exploratory; do not infer missing labels. |
| M3 | Leakage-safe representation | method freeze | Natural-text collisions were not censored; morphology is not semantics. |
| M4 | B2 13 structural features | method freeze | Do not call the ordinary classifier itself novel. |
| M5 | B0/B1/B3/B4 comparator roles | development evidence only | Relative method comparisons are dev-only. |
| M6 | Grouped development / LOBO / model transfer | development evidence | LOBO/model transfer did not select the final method from official test and is not joint OOD. |
| M7 | Final method / threshold freeze | method freeze | No official-test tuning or post-freeze selection. |
| M8 | Blind held-out protocol | blind held-out test | Blind held-out is not independent external benchmark validation. |
| M9 | A2 post-freeze diagnostics | post-freeze diagnostics | A2 diagnostics did not participate in final method or threshold selection. |

## Temporal separation contract

```text
development evidence
-> method and threshold freeze
-> blind held-out prediction freeze
-> one-time held-out scoring
-> post-freeze A2 diagnostics
```

A2 efficiency, coefficient, metadata, and deterministic-error diagnostics are post-freeze. They did not select, tune, calibrate, or change the final model, threshold, eligibility, or official-test protocol.

## Forbidden method wording

- A2 diagnostics selected the final method.
- Official held-out results selected features, configurations, or thresholds.
- LOBO or model-transfer evidence establishes independent external or joint OOD validation.
- The Logistic Regression classifier itself is a novel model.
