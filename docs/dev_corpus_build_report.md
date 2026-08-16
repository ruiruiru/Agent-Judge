# Stage A1.0 Full Dev Leak-Safe Corpus Build

## Stage decision

**PASS_WITH_CONDITIONS**

This is an evidence recommendation only; the research lead retains the stage-gate decision.

## Directly observed facts

- Source: `McGill-NLP/agent-reward-bench` at fixed revision `b6d17e646009d6cb63d5dd7be78807b680693f61`.
- The identifier-only dev allowlist contains 196 unique trajectories; 196 map to one unique JSON path.
- Only individual `cleaned/.../*.json` resolve URLs were used. No repository snapshot, test trajectory, judgment, screenshot, image, video, or HTML payload was downloaded.
- Target labels remain only in `artifacts/dev_analysis_index.csv`; corpus construction receives identifier metadata only.

## Computed processing evidence

- Downloaded or verified/reused: 196/196; parsed: 196; cleaned: 196; all three views: 196.
- Network downloads: 180 completed files / 3,604,302,207 payload bytes; total transferred 3,621,079,423 bytes, including 16,777,216 bytes from one interrupted `.part`; verified prior probes: 16 files.
- Fixed-revision raw scope: 3,647,118,724 bytes; peak Stage A1 cache: 111,492,761 bytes; residual raw cache: 0 bytes.
- Compact files: cleaned 24,174,170 bytes; primary 21,584,687; error ablation 21,510,212; reasoning sensitivity 22,718,603.
- Steps: 3,812; per trajectory min/median/mean/max = 2/23.0/19.449/31.
- Empty action/observation/focused-element steps: 196/0/4.
- Reasoning: 196/196 trajectories and 3616 steps.
- Natural errors: 86/196 trajectories and 307 steps.
- Terminal action/observation: 196/196 and 196/196 trajectories.
- Termination signals: `{"null": 125, "report_infeasible": 10, "send_msg_to_user": 61}`.
- Screenshot references were observed in 196 trajectories, but no screenshot payload was accessed.
- Schema drift: 4 path/type groups and 12477 occurrences; unknowns are excluded from every view.

## Grouped step-length statistics

### benchmark_original

| Group | N | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|---:|
| assistantbench | 24 | 5 | 22.0 | 19.167 | 31 |
| visualwebarena | 24 | 2 | 7.5 | 12.875 | 31 |
| webarena | 88 | 2 | 12.0 | 16.989 | 31 |
| workarena | 60 | 7 | 31.0 | 25.800 | 31 |

### benchmark_split_namespace

| Group | N | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|---:|
| assistantbench | 24 | 5 | 22.0 | 19.167 | 31 |
| visualwebarena | 24 | 2 | 7.5 | 12.875 | 31 |
| webarena | 88 | 2 | 12.0 | 16.989 | 31 |
| workarena_l1 | 8 | 13 | 24.5 | 22.625 | 31 |
| workarena_l2 | 52 | 7 | 31.0 | 26.288 | 31 |

### model_name

| Group | N | Min | Median | Mean | Max |
|---|---:|---:|---:|---:|---:|
| GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct | 51 | 2 | 31 | 22.569 | 31 |
| GenericAgent-anthropic_claude-3.7-sonnet | 51 | 2 | 10 | 15.294 | 31 |
| GenericAgent-gpt-4o-2024-11-20 | 51 | 2 | 13 | 18.000 | 31 |
| GenericAgent-meta-llama_Llama-3.3-70B-Instruct | 43 | 4 | 31 | 22.395 | 31 |

Label-conditioned length statistics were not computed: A1.0 physically isolates target labels and explicitly prohibits label/text association analysis.

## Leakage validation

- `outcome_keys_absent_from_input_bearing_cleaned_fields`: **PASS**
- `labels_absent_from_all_corpus_files`: **PASS**
- `identity_metadata_not_serialized`: **PASS**
- `reasoning_only_in_sensitivity_view`: **PASS**
- `natural_error_absent_from_error_ablation`: **PASS**
- `terminal_not_duplicated_in_serialized_text`: **PASS**
- `unknown_fields_rejected_from_all_views`: **PASS**
- `test_content_not_accessed`: **PASS**
- `root_identity_fields_excluded_by_provenance`: **PASS**

## Risk judgments

- 4 schema-drift path/type groups are excluded and require manual review.
- 8 trajectories contain literal identity tokens inside frozen allowlisted natural content; root identity fields are excluded, but shortcut sensitivity requires review.

No field whitelist, label rule, benchmark grouping, or input view was changed. No feature extraction, model call, training, baseline, or predictive metric was run.
The Stage A1.0 test module covers all 20 required verification categories, including an actual 196-record corpus leakage scan.

## Unconfirmed questions

- The research lead must decide whether the documented conditions are acceptable before any baseline stage starts.
- Predictive usefulness remains untested by design.
