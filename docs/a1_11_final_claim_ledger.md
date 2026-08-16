# A1.11 Final Claim Ledger

Final claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175`

This hash is the claim contract for manuscript drafting. Without a newly approved Stage, the manuscript must not add a confirmatory claim, enlarge claim scope, remove a frozen limitation, or promote exploratory evidence to confirmatory status.

| Claim | Status | Target | Allowed claim / boundary | Required qualifier | Prohibited extension |
|---|---|---|---|---|---|
| FC1 | CONFIRMATORY_SUPPORTED | Success | Frozen structural trajectory features retain predictive signal for Success on untouched official held-out tasks/trajectories within the evaluated benchmark families. | frozen structural features; official held-out; evaluated benchmark families | unseen benchmark; arbitrary agents; joint task/model OOD; universal judging; causality |
| FC2 | CONFIRMATORY_SUPPORTED | Looping | Frozen structural trajectory features retain strong predictive signal for Looping on untouched official held-out tasks/trajectories within the evaluated benchmark families. | frozen structural features; official held-out; evaluated benchmark families | unseen benchmark; arbitrary agents; joint task/model OOD; universal judging; causality |
| FE1 | EXPLORATORY_SUPPORTED | Side Effect | The frozen dense semantic Side Effect model showed positive exploratory held-out signal. | exploratory_only; low-support; not confirmatory | confirmed detector; confirmatory Side Effect claim; general deployment claim |
| FD1 | DEV_ONLY | Success | B2 is better than B3 for Success. | point-estimate trend; paired difference uncertain; dev-only | stable or significant superiority; held-out comparative claim |
| FD2 | DEV_ONLY | Success | B4 is better than B2/B3 for Success. | no clear incremental AP gain; dev-only | stable dense superiority; official-test comparative claim |
| FD3 | DEV_ONLY | All | Dense semantics are superior to lightweight representations. | empirical dev pattern; target-dependent | general superiority or necessity |
| FD4 | DEV_ONLY | Success | Termination features are the Success mechanism. | predictive dependency only; dev-only | causal or dominant mechanism |
| FD5 | DEV_ONLY | Looping | Repetition features are the Looping mechanism. | stable predictive increment; non-causal; dev-only | complete or causal mechanism |
| FD6 | DEV_ONLY | Success; Looping | S6 can replace the full S0 structural representation. | competitive point estimates; no equivalence claim | proven replacement or equivalence |
| FD7 | DEV_ONLY | All | A1.4 establishes final cross-model generalization. | model-only transfer; exploratory; same-task condition | joint task/model OOD or arbitrary-Agent generalization |
| FD8 | DEV_ONLY | All | A universal model-complexity hierarchy is established. | no clear uniform hierarchy; dev-only | simple or complex models universally superior |
| FD9 | DEV_ONLY | All | A fixed cross-dimension representation hierarchy is established. | different empirical relationships; no fixed hierarchy | universal information hierarchy or causal theory |
| DH1 | DESCRIPTIVE_ONLY | Success | Success performance varies across the four evaluated benchmark families. | descriptive heterogeneity only | Benchmark A significantly outperforms Benchmark B |
| DH2 | DESCRIPTIVE_ONLY | Looping | Looping performance varies across the four evaluated benchmark families. | descriptive heterogeneity only | Benchmark A significantly outperforms Benchmark B |
| DH3 | DESCRIPTIVE_ONLY | Side Effect | Side Effect performance varies across the four evaluated benchmark families. | descriptive heterogeneity only | Benchmark A significantly outperforms Benchmark B |
| NS1 | NOT_SUPPORTED | All | The frozen scores are calibrated probabilities suitable for operational decisions. | predictive ranking/classification evidence only | calibrated risk or deployment safety |
| NS2 | NOT_SUPPORTED | All | A1.10 establishes pairwise statistical differences between benchmark families. | descriptive variation only | significantly better or worse benchmark claims |
| PO1 | PROHIBITED_OVERCLAIM | All | Our method generalizes to unseen benchmarks. | must not be asserted as a supported finding | Our method generalizes to unseen benchmarks. |
| PO2 | PROHIBITED_OVERCLAIM | All | Our method generalizes to arbitrary agents. | must not be asserted as a supported finding | Our method generalizes to arbitrary agents. |
| PO3 | PROHIBITED_OVERCLAIM | All | Our method establishes joint task-and-model OOD robustness. | must not be asserted as a supported finding | Our method establishes joint task-and-model OOD robustness. |
| PO4 | PROHIBITED_OVERCLAIM | All | Structural features causally determine Success or Looping. | must not be asserted as a supported finding | Structural features causally determine Success or Looping. |
| PO5 | PROHIBITED_OVERCLAIM | All | The system is a universal Agent Judge. | must not be asserted as a supported finding | The system is a universal Agent Judge. |
| PO6 | PROHIBITED_OVERCLAIM | All | Side Effect is a confirmed held-out detector. | must not be asserted as a supported finding | Side Effect is a confirmed held-out detector. |
| PO7 | PROHIBITED_OVERCLAIM | All | Simple models universally outperform complex models. | must not be asserted as a supported finding | Simple models universally outperform complex models. |
| PO8 | PROHIBITED_OVERCLAIM | All | Dense semantics are generally unnecessary. | must not be asserted as a supported finding | Dense semantics are generally unnecessary. |

## Core frozen metrics

- FC1 Success: AP 0.654836; AP lift 0.389567; F1 0.682099; AP-lift 95% CI [0.326806, 0.455411].
- FC2 Looping: AP 0.921769; AP lift 0.394829; F1 0.876987; AP-lift 95% CI [0.360965, 0.428598].
- FE1 Side Effect: AP 0.107279; AP lift 0.042851; F1 0.168582; AP-lift 95% CI [0.021245, 0.079200]; exploratory_only, low-support, not confirmatory.
