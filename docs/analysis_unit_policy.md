# Stage A0.2 Analysis Unit and Benchmark Group Policy

## Stage decision

**PASS**

Stage A0.2 freezes metadata analysis units and grouping only. It does not authorize full trajectory download, feature engineering, baselines, training, or model evaluation.

Known limitations retained for later research-lead review:

1. The official primary annotation is operationally defined by fixed CSV encounter order, not by an adjudication record or a documented annotator-quality hierarchy.
2. WorkArena L1/L2 are retained separately for sensitivity analysis because the official scorer names them WorkArena and WorkArena++, even though both are levels in the same WorkArena/ServiceNow environment.
3. Aggregate test-label exposure occurred for audit only; no test labels may enter regular development files or method decisions.

## Frozen trajectory unit

`trajectory_key = (benchmark_original, normalized_task_id, model_name)`

The serialized index key is `benchmark_original::normalized_task_id::model_name`. Across 1,408 annotation rows this yields **1302** unique trajectories. Every repeated key has exactly two distinct annotators, one `exp_name`, and one raw task ID. No key contains evidence of multiple independent runs, and the official CSV exposes no separate trajectory ID, run ID, or path field.

`exp_name` is retained as metadata but is not added to the key because it is constant within every key and identifies benchmark/model experiment groups rather than distinguishing trajectories.

## Official annotation rule and frozen resolution

The fixed official utility labels the first occurrence of `(benchmark, model_name, task_id)` as primary and later occurrences as secondary. The fixed scorer evaluates human labels from primary records. Evidence:

- [Official annotator utility](https://github.com/McGill-NLP/agent-reward-bench/blob/f838338886d723d40b586309465a38277803d9e6/agent_reward_bench/judge/utils.py)
- [Official scoring script](https://github.com/McGill-NLP/agent-reward-bench/blob/f838338886d723d40b586309465a38277803d9e6/scripts/score_judgments.py)

Frozen A0.2-Fix behavior:

- One row becomes `single_annotation`.
- Repeated equal values become `duplicate_agreement` and are folded to one trajectory.
- Repeated unequal values become `duplicate_disagreement`; the main-experiment label is empty and `eligible_main` is false.
- Any annotation set containing `Unsure` becomes `contains_unsure` and that target is unavailable.
- Resolution is target-specific. No trajectory is removed from other targets because one target is unavailable or disputed.
- No voting, random selection, relabeling, or duplicate weighting is permitted.
- The fixed official primary value is retained only as `<target>_primary_label_audit_only` in the audit file. It never appears in the dev training interface.

| Target | Single | Duplicate agreement | Duplicate disagreement | Contains Unsure | Valid trajectories | Positive rate |
|---|---|---|---|---|---|---|
| success | 1196 | 93 | 12 | 1 | 1289 | 0.270753 |
| side_effect | 1195 | 102 | 4 | 1 | 1297 | 0.063994 |
| looping | 1196 | 95 | 11 | 0 | 1291 | 0.518203 |

`duplicate_annotation_audit.csv` is audit-only. It must never be used directly as training data.

Every future training-set constructor must require both `<target>_eligible_main == true` and `<target>_label in {0, 1}`. Checking only that a label is non-empty is prohibited.

## Downstream misuse audit

The Stage A0.2-Fix repository scan found no training implementation using `dropna`, `notna`, `fillna(0/1)`, `first()`, or `iloc[0]` to select target labels. References to `primary_label` are confined to the explicitly audit-only field and tests that prevent it from entering `test_manifest.csv`. No training code exists at this stage.

## Benchmark namespaces

Every trajectory retains:

- `benchmark_original`: the annotation value.
- `benchmark_split_namespace`: the official `splits.csv` value.
- `benchmark_group_primary`: four environment-level groups, merging `workarena_l1` and `workarena_l2` into `workarena`.
- `benchmark_group_secondary`: five official split namespaces, retaining WorkArena L1/L2 separately.

The fixed official WorkArena processing code selects L2 with a `level == l2` field, while the scorer names the two groups WorkArena and WorkArena++. Both are backed by the WorkArena ServiceNow environment. The four-group merge is therefore frozen for the primary cross-environment analysis, while the official five-way split remains mandatory as a sensitivity grouping.

| Namespace | Tasks | Unique trajectories | Models |
|---|---|---|---|
| workarena_l1 | 18 | 72 | 4 |
| workarena_l2 | 100 | 400 | 4 |

WorkArena L1/L2 overlapping normalized task IDs: **0**.

## Analysis index files

- `dev_analysis_index.csv`: one labeled row per unique dev trajectory after fixed resolution.
- `test_manifest.csv`: identifiers and grouping metadata only; it contains no target labels, raw values, or target statuses.
- `duplicate_annotation_audit.csv`: one audit row per unique trajectory, including raw annotation sets and statuses.

## Test sealing

Test labels received aggregate, audit-only exposure during Stage A0.1. No model, feature, threshold, hyperparameter, or research decision was tuned using test performance.

After Stage A0.2, routine development may use only the labeled dev analysis index. The test manifest contains identifiers and grouping fields only. Complete test labels may be read only by a future final, locked evaluation flow explicitly approved by the research lead.

## Reproducibility and limitations

- Inputs are the A0.1 files pinned by `artifacts/source_manifest.json`; hashes are verified before indexing.
- Output generation is deterministic and requires no network access.
- The primary-label rule is official but position-based and not adjudicated; it is retained for audit only and is not a main-experiment eligibility rule.
- This stage does not establish full-trajectory availability, parsing success, feature validity, leakage safety, or readiness for model experiments.
