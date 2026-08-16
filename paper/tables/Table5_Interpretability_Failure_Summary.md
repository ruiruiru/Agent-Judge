# Table 5. Interpretability and failure summary

Associative/diagnostic coefficients are not causal effects. Metadata comparison is descriptive. Error cases are deterministic illustrations, not prevalence estimates.

| Target | Top signed structural signals | Metadata AP | Metadata AP lift | Frozen B2 dev AP | Deterministic illustrative cases | Interpretation | Evidence status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Success | observation_char_count_total: -2.204<br>observation_char_count_mean_nonempty: 1.879<br>action_char_count_total: 0.732<br>has_explicit_termination_signal: -0.610<br>unique_action_ratio: 0.520 | 0.371 | 0.069 | 0.547 | LONG_BUT_UNSUCCESSFUL:2; REPETITIVE_BUT_PROGRESSING:1; SHORT_BUT_SUCCESSFUL:1; TERMINATION_MISMATCH:2 | Associations and deterministic cases delimit where task-agnostic structure tracks execution morphology but misses semantic completion; coefficients are not causal importance. | DEV_ONLY;POST_FREEZE_DIAGNOSTIC;POST_FREEZE_DESCRIPTIVE |
| Looping | observation_char_count_mean_nonempty: -0.830<br>nonempty_action_count: 0.695<br>nonempty_observation_count: 0.695<br>step_count: 0.695<br>nonempty_focused_element_count: 0.670 | 0.569 | 0.099 | 0.914 | EXPLICIT_ERROR_RECOVERY:1; NON_REPETITIVE_FAILURE:2; OTHER:1; REPETITIVE_BUT_PROGRESSING:1; UNCLEAR:1 | Associations and deterministic cases distinguish literal action repetition from progress and semantic cycling; coefficients are not causal importance. | DEV_ONLY;POST_FREEZE_DIAGNOSTIC;POST_FREEZE_DESCRIPTIVE |
