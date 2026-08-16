# Stage A1.1 Pre-Baseline Audit

## Stage decision

**PASS_WITH_CONDITIONS**

This is an evidence recommendation. Human approval is required before any baseline execution.

## Non-destructive protocol clarification (2026-08-04)

- The actual A1.1 splitter is `custom_deterministic_grouped_stratification_v1`; scikit-learn `StratifiedGroupKFold` was not called and equivalence is not claimed.
- The three ordinary fold manifests are immutable and hash-locked. Their committed bytes, not a future splitter invocation, are the sole partition authority.
- Primary LOBO, sensitivity LOBO, and Leave-One-Model-Out manifests are also hash-locked and unchanged by this clarification.
- Candidate configurations are selected on inner-validation PR-AUC; the selected configuration's threshold is then selected on inner-validation positive F1. It is refit on complete outer train before exactly one outer-validation evaluation.
- Reporting retains raw per-fold metrics and mean ± standard deviation, and additionally reports pooled OOF metrics from exactly one outer-validation prediction per eligible trajectory.
- Single-class LOBO holdouts use `NA` for ordinary predictive metrics. Only predicted-positive rate, mean probability, and—when negatives exist—FPR and specificity are permitted.
- `python scripts/verify_evaluation_protocol.py` is a mandatory read-only preflight before any later baseline starts.

## Group-key audit

- Base dev task groups: 51; group-size distribution: `{"3": 8, "4": 43}`.
- Groups with all four models: 43; partial model coverage: 8.
- Cross-benchmark normalized-task-ID collisions: 0; the benchmark component remains mandatory.

## Terminal terminology correction

- `last_nonempty_action`: 196/196. It is only the last nonempty action and does not imply success or normal termination.
- `last_nonempty_observation`: 196/196.
- `explicit_termination_signal`: 71/196, limited to `send_msg_to_user` and `report_infeasible`.
- The historical cleaned field `termination_signal` is a non-destructive alias for `explicit_termination_signal`.

## Four-group schema-drift review

| Field | Type | Occurrences | Trajectories | Current policy | Decision |
|---|---|---:|---:|---|---|
| `$.steps[].axtree_obj.nodes[].name.sources[].invalid` | bool | 475 | 6 | default_reject_unregistered_path | keep_excluded |
| `$.steps[].axtree_obj.nodes[].name.sources[].nativeSourceValue.relatedNodes[].idref` | str | 11796 | 47 | default_reject_unregistered_path | keep_excluded |
| `$.steps[].axtree_obj.nodes[].value.value` | int | 205 | 13 | unapproved_type_variant_of:manual_review | keep_excluded |
| `$.steps[].stats.n_retry` | int | 1 | 1 | unapproved_type_variant_of:metadata_only | keep_excluded |

All four remain excluded. They are raw accessibility-tree internals or metadata type variants; `axtree_pruned` and the shared cleaned schema remain intact. The field whitelist was not expanded.

## WorkArena literal provenance

- Affected trajectories: 8; audited field rows: 139; literal occurrences: 458.
- Field distribution: `{"$.goal": 4, "$.steps[].action": 4, "$.steps[].axtree_pruned": 450}`.
- Every occurrence originates from frozen allowlisted task/environment text. Metadata mutation leaves serialization byte-identical, so no serializer injection was found.
- Natural text is retained unchanged. A uniform `benchmark_literal_redacted` view is only a future sensitivity candidate and was not generated.

## Natural errors and reasoning

- Natural errors: 86/196 trajectories and 307 steps. Primary/error-ablation differences occur in exactly 86 trajectories.
- Reasoning: 196/196 trajectories and 3616 steps; it remains sensitivity-only.

## Leave-One-Model-Out feasibility

- Status: **exploratory_only**.
- The meta-llama source lacks VisualWebArena coverage, so not every held-out model validation domain covers all four primary Benchmarks. Training domains still retain all primary Benchmarks; detailed per-target class counts are machine-readable.

## Conditions and stop boundary

- Primary LOBO held-out domains without both classes: side_effect:assistantbench.
- Sensitivity LOBO held-out domains without both classes: side_effect:assistantbench, side_effect:workarena_l1.
- Leave-One-Model-Out is exploratory because model coverage is incomplete across primary Benchmarks.
- Four schema-drift groups remain excluded pending research-lead approval; no whitelist expansion occurred.
- Eight trajectories retain natural `workarena` literals; a uniform redaction sensitivity remains optional and ungenerated.

No Dummy, TF-IDF, Logistic Regression, other estimator, prediction probability, or predictive metric was run. Test remains sealed.
