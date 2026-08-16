# Stage A0.4 Leak-Safe Trajectory Input Contract

## Stage decision

**PASS_WITH_CONDITIONS**

This contract was derived only from the 16 existing dev probe JSON files. No network access, new trajectory download, feature extraction, model call, training, baseline, or predictive metric was used.

## Frozen whitelist

Primary input admits only:

- `goal` → `task.instruction`;
- `steps[].action` → `steps[].action`;
- `steps[].axtree_pruned` → `steps[].observation`;
- `steps[].focused_element` → `steps[].focused_element`;
- `steps[].last_action_error` → `steps[].error` in the primary/error-preserving views.

`steps[].reasoning` is sensitivity-only. Missing values remain null and are never imputed. Tool fields and task context remain null because no separate approved raw source field exists.

## Permanent exclusions

- The complete `summary_info` subtree, including `cum_reward` and `cum_raw_reward`;
- every field with official reward/score/label/judge/annotation semantics;
- screenshot paths, image placeholders, image payloads, and base64 content;
- any future unknown field until explicitly reviewed and approved.

Excluded fields cannot affect step retention, truncation, ordering, selection, missing-value handling, structure features, or text.

## Identity, reasoning, and natural errors

Benchmark, task, agent, model, experiment, split, repository path, and trajectory key are management metadata only. They do not appear inside any serialized view. Reasoning is excluded from both primary views and appears only when the raw step contains it in `sensitivity_with_reasoning`.

Natural tool/environment errors from `last_action_error` remain in `primary_with_natural_errors` and `sensitivity_with_reasoning`; `ablation_without_error_fields` removes that explicit field without deleting a step or rewriting observation text.

## Shared cleaned schema and terminal mapping

```text
trajectory_key
metadata (management only)
task {instruction, context}
steps[] {step_index, action, observation, tool_name, tool_input, tool_output, focused_element, error, reasoning}
terminal {last_nonempty_action, last_nonempty_observation, last_step_index, termination_signal}
quality_flags
```

Terminal action and observation are exact copies of the last nonempty allowlisted raw fields. `termination_signal` records only the literal action name `send_msg_to_user` or `report_infeasible`; it is null otherwise. It never represents inferred success or failure, and no `final_response` field is invented.

## Three frozen serialized views

1. `primary_with_natural_errors`: task, actions, pruned observations, focused elements, natural error fields, and terminal evidence; no reasoning.
2. `ablation_without_error_fields`: the same contract with explicit natural error fields removed; no reasoning.
3. `sensitivity_with_reasoning`: the primary view plus raw reasoning where present.

All omit empty fields and preserve original step order. Structured JSON and text share the same source whitelist.

## Measured probe statistics

- Raw: 42,816,517 bytes across 16 files.
- Compact structured JSONL: 420,490 bytes (0.9821% of raw).
- Serialized JSONL container: 1,132,584 bytes.
- View text bytes: primary 330,697; error ablation 327,149; reasoning sensitivity 357,072.
- Steps: 114; empty actions: 16; empty observations: 0.
- Reasoning trajectory availability: 100.00%; natural-error trajectory availability: 6.25%; screenshot-reference rate: 100.00%.
- Explicit terminal signal coverage: 50.00%; no signal is inferred for the remainder.
- Average parsed-object memory estimate: 11,790,543 bytes; maximum: 32,578,825 bytes.
- New fields relative to A0.3 inventory: 0.

## Full-dev streaming plan (not executed)

The fixed tree estimates 196 dev JSON files and 3,647,118,724 raw bytes. Probe ratios project approximately 35,817,415 compact structured bytes. Projected view text bytes are recorded in the machine-readable summary.

Use a dev-key allowlist and fixed revision, then process one file at a time: download to a `.part` cache, verify size/SHA256, parse, whitelist, write one compact record, and release or move the verified raw file to a recoverable cache. Resume from a manifest only after rechecking hashes. The full 3.65 GB need not be committed or permanently retained locally, but revision, path, size, and hash records must be permanent. Test keys are rejected before path resolution or file access.

## Conditions and unresolved semantics

- Explicit terminal action semantics are present for only part of the probe; null remains the required representation elsewhere.
- Natural error fields occur in a minority of trajectories and remain subject to the frozen error-field ablation.

No model-readiness or performance conclusion is made in this stage.
