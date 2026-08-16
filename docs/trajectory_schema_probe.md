# Stage A0.3 Minimal Dev Trajectory Probe

## Stage decision

**PASS_WITH_CONDITIONS**

This probe used only fixed-revision dev JSON trajectories. It did not download test trajectories, screenshots, judgments, or the full dataset, and it did not construct features or run models/baselines.

## Direct observations

- Fixed Hugging Face revision: `b6d17e646009d6cb63d5dd7be78807b680693f61`.
- Trajectories are individual JSON files below `cleaned/<benchmark>/<model>/<run>/`.
- `judgments/` is a separate tree and was neither queried for sample mapping nor downloaded.
- Selected/downloaded files: 16; bytes: 42816517 (limit 209715200).
- No screenshot/image/video file was downloaded.

## Computed audit statistics

- Exact dev path mapping: 196/196 (100.00%).
- Probe JSON parsing: 16/16 (100.00%).
- Screenshot references: 16/16 (100.00%); referenced assets were not downloaded.
- Direct outcome/label fields: 16/16 trajectories.
- Strong outcome proxies: 0/16 trajectories.

## Raw structure differences and adapter recommendation

All probed benchmark families share the same direct root and `steps[]` field sets. Use one shared cleaned-schema adapter with benchmark/model-aware null and semantic guards, emitting this small common contract:

```text
trajectory_id, benchmark, task_instruction, steps[]
steps[].action, steps[].observation, steps[].tool_name
steps[].tool_input, steps[].tool_output, final_response, metadata
```

Observed differences are type-level rather than separate top-level schemas: `focused_element` is additionally nullable in WorkArena, while action/reasoning availability can vary by individual trajectory or model. No explicit final-response field was observed. Outcome/judgment/reward/score fields are forbidden model inputs. Screenshot paths and removed image placeholders remain optional metadata; the minimal text probe does not require image files.

## Leakage isolation

- `$.summary_info.cum_raw_reward` — level_1, `exclude` (direct_label_or_official_outcome).
- `$.summary_info.cum_reward` — level_1, `exclude` (direct_label_or_official_outcome).
- `$.agent` — level_3, `retain_with_ablation` (benchmark_or_agent_identity_shortcut).
- `$.benchmark` — level_3, `retain_with_ablation` (benchmark_or_agent_identity_shortcut).
- `$.experiment` — level_3, `retain_with_ablation` (benchmark_or_agent_identity_shortcut).
- `$.flags.obs.use_error_logs` — level_3, `retain_with_ablation` (natural_trajectory_outcome_information).
- `$.flags.obs.use_past_error_logs` — level_3, `retain_with_ablation` (natural_trajectory_outcome_information).
- `$.model` — level_3, `retain_with_ablation` (benchmark_or_agent_identity_shortcut).
- `$.steps[].last_action_error` — level_3, `retain_with_ablation` (natural_trajectory_outcome_information).

## Risk judgments

- A shared output contract and shared cleaned-schema adapter are feasible, with guarded normalization for nullable and semantically benchmark-specific values.
- Natural action repetition and environment/tool errors are legitimate trajectory evidence, not automatically labels; retain them with an explicit leakage/ablation policy.
- Direct official outcomes and strong evaluator proxies must remain isolated from future model inputs.

## Unconfirmed questions

- Whether screenshot content is required for later non-minimal research remains untested because screenshots were prohibited here.
- Field semantics marked `unclassified` require adapter-level confirmation before any full dev transformation.
- This schema probe does not establish predictive value or model performance.
