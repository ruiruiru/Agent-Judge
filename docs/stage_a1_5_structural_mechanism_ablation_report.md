# Stage A1.5 structural mechanism ablation report

## Stage determination

`PASS_WITH_CONDITIONS`

All technical completeness checks passed. Interpretation remains conditional because Side Effect has only 12 positives and one single-class held-out domain, known scikit-learn FutureWarnings are retained, and dependency grades are descriptive rather than causal.

## Scope and provenance

- A1.5a preregistration commit: `fa9ef0771ea44a720ed8b900199a75ef3c863379`
- A1.5b experiment commit: recorded by the enclosing result commit.
- GitHub commit: `f838338886d723d40b586309465a38277803d9e6`
- Hugging Face revision: `b6d17e646009d6cb63d5dd7be78807b680693f61`
- Official dev structural features only; A1.3 primary four-group LOBO outer manifest and frozen inner folds reused byte-for-byte.
- test access: 0 in every category; prohibited experiments executed: 0.

## Frozen feature groups

- `G1_activity_volume`: `step_count`, `nonempty_action_count`, `nonempty_observation_count`, `nonempty_focused_element_count`, `action_char_count_total`, `observation_char_count_total`, `action_char_count_mean_nonempty`, `observation_char_count_mean_nonempty`
- `G2_error`: `natural_error_step_count`, `natural_error_step_ratio`
- `G3_termination`: `has_explicit_termination_signal`
- `G4_repetition`: `unique_action_ratio`, `consecutive_duplicate_action_count`

## Frozen variants

- `S0_full13` (13 features): step_count, nonempty_action_count, nonempty_observation_count, nonempty_focused_element_count, natural_error_step_count, natural_error_step_ratio, has_explicit_termination_signal, action_char_count_total, observation_char_count_total, action_char_count_mean_nonempty, observation_char_count_mean_nonempty, unique_action_ratio, consecutive_duplicate_action_count
- `S1_no_termination` (12 features): step_count, nonempty_action_count, nonempty_observation_count, nonempty_focused_element_count, natural_error_step_count, natural_error_step_ratio, action_char_count_total, observation_char_count_total, action_char_count_mean_nonempty, observation_char_count_mean_nonempty, unique_action_ratio, consecutive_duplicate_action_count
- `S2_no_repetition` (11 features): step_count, nonempty_action_count, nonempty_observation_count, nonempty_focused_element_count, natural_error_step_count, natural_error_step_ratio, has_explicit_termination_signal, action_char_count_total, observation_char_count_total, action_char_count_mean_nonempty, observation_char_count_mean_nonempty
- `S3_no_activity_volume` (5 features): natural_error_step_count, natural_error_step_ratio, has_explicit_termination_signal, unique_action_ratio, consecutive_duplicate_action_count
- `S4_no_error` (11 features): step_count, nonempty_action_count, nonempty_observation_count, nonempty_focused_element_count, has_explicit_termination_signal, action_char_count_total, observation_char_count_total, action_char_count_mean_nonempty, observation_char_count_mean_nonempty, unique_action_ratio, consecutive_duplicate_action_count
- `S5_no_termination_or_repetition` (10 features): step_count, nonempty_action_count, nonempty_observation_count, nonempty_focused_element_count, natural_error_step_count, natural_error_step_ratio, action_char_count_total, observation_char_count_total, action_char_count_mean_nonempty, observation_char_count_mean_nonempty
- `S6_termination_repetition_only` (3 features): has_explicit_termination_signal, unique_action_ratio, consecutive_duplicate_action_count

## S0 positive control

S0 exactly reproduced A1.3 B2: config `True`, threshold `True`, labels `True`; maximum probability error `0.000e+00` and maximum metric error `0.000e+00` (tolerance `1.0e-12`).

## Macro and pooled results

| Target | Variant | Macro AP | Macro F1 | Pooled AP | Pooled F1 | AP lift | Retained AP-lift ratio | Grade |
|---|---|---:|---:|---:|---:|---:|---:|---|
| success | S0_full13 | 0.479810 | 0.517304 | 0.461363 | 0.540881 | 0.159280 | 1.000000 | `reference` |
| success | S1_no_termination | 0.518158 | 0.526305 | 0.426425 | 0.554054 | 0.124341 | 0.780647 | `moderate_dependency` |
| success | S2_no_repetition | 0.504851 | 0.551159 | 0.447848 | 0.567376 | 0.145764 | 0.915145 | `limited_dependency` |
| success | S3_no_activity_volume | 0.645246 | 0.589168 | 0.433250 | 0.600000 | 0.131167 | 0.823500 | `limited_dependency` |
| success | S4_no_error | 0.495941 | 0.518921 | 0.522821 | 0.544304 | 0.220738 | 1.385848 | `limited_dependency` |
| success | S5_no_termination_or_repetition | 0.497688 | 0.544083 | 0.414663 | 0.577778 | 0.112579 | 0.706802 | `limited_dependency` |
| success | S6_termination_repetition_only | 0.511599 | 0.583047 | 0.446111 | 0.586667 | 0.144028 | 0.904244 | `sufficiency_only_not_dependency_grade` |
| side_effect | S0_full13 | 0.060443 | 0.069801 | 0.041690 | 0.061856 | -0.019849 | NA | `reference` |
| side_effect | S1_no_termination | 0.060626 | 0.058957 | 0.046420 | 0.051724 | -0.015118 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S2_no_repetition | 0.055211 | 0.013072 | 0.041465 | 0.019048 | -0.020074 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S3_no_activity_volume | 0.066427 | 0.031746 | 0.042797 | 0.058824 | -0.018741 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S4_no_error | 0.063533 | 0.052525 | 0.052986 | 0.044444 | -0.008553 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S5_no_termination_or_repetition | 0.057264 | 0.021505 | 0.040136 | 0.032787 | -0.021403 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S6_termination_repetition_only | 0.061163 | 0.018018 | 0.044298 | 0.022472 | -0.017240 | NA | `sufficiency_only_not_dependency_grade` |
| looping | S0_full13 | 0.850841 | 0.864520 | 0.836040 | 0.884422 | 0.366652 | 1.000000 | `reference` |
| looping | S1_no_termination | 0.849795 | 0.894628 | 0.828100 | 0.907216 | 0.358712 | 0.978346 | `limited_dependency` |
| looping | S2_no_repetition | 0.819144 | 0.870506 | 0.793707 | 0.892308 | 0.324319 | 0.884544 | `limited_dependency` |
| looping | S3_no_activity_volume | 0.899706 | 0.825096 | 0.886636 | 0.834225 | 0.417248 | 1.137996 | `limited_dependency` |
| looping | S4_no_error | 0.858544 | 0.876334 | 0.821639 | 0.902564 | 0.352251 | 0.960723 | `limited_dependency` |
| looping | S5_no_termination_or_repetition | 0.817893 | 0.868353 | 0.801668 | 0.890052 | 0.332280 | 0.906256 | `limited_dependency` |
| looping | S6_termination_repetition_only | 0.901356 | 0.847074 | 0.913531 | 0.840426 | 0.444143 | 1.211350 | `sufficiency_only_not_dependency_grade` |

## Domain results

| Target | Variant | Held-out | status | prevalence | AP | F1 | config | threshold |
|---|---|---|---|---:|---:|---:|---|---:|
| success | S0_full13 | assistantbench | ok | 0.083333 | 0.100490 | 0.173913 | `B2_C10p0_cw_balanced` | 0.250000 |
| success | S0_full13 | visualwebarena | ok | 0.500000 | 0.702655 | 0.727273 | `B2_C10p0_cw_balanced` | 0.700000 |
| success | S0_full13 | webarena | ok | 0.297619 | 0.406794 | 0.563380 | `B2_C1p0_cw_balanced` | 0.350000 |
| success | S0_full13 | workarena | ok | 0.316667 | 0.709300 | 0.604651 | `B2_C1p0_cw_balanced` | 0.300000 |
| side_effect | S0_full13 | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C0p1_cw_none` | 0.200000 |
| side_effect | S0_full13 | visualwebarena | ok | 0.083333 | 0.080952 | 0.153846 | `B2_C0p1_cw_none` | 0.100000 |
| side_effect | S0_full13 | webarena | ok | 0.091954 | 0.069881 | 0.055556 | `B2_C10p0_cw_balanced` | 0.450000 |
| side_effect | S0_full13 | workarena | ok | 0.033333 | 0.030496 | 0.000000 | `B2_C0p1_cw_balanced` | 0.550000 |
| looping | S0_full13 | assistantbench | ok | 0.458333 | 0.788064 | 0.869565 | `B2_C1p0_cw_balanced` | 0.350000 |
| looping | S0_full13 | visualwebarena | ok | 0.291667 | 0.924036 | 0.800000 | `B2_C1p0_cw_balanced` | 0.600000 |
| looping | S0_full13 | webarena | ok | 0.420455 | 0.920488 | 0.886076 | `B2_C10p0_cw_balanced` | 0.150000 |
| looping | S0_full13 | workarena | ok | 0.616667 | 0.770777 | 0.902439 | `B2_C0p1_cw_balanced` | 0.600000 |
| success | S1_no_termination | assistantbench | ok | 0.083333 | 0.326923 | 0.250000 | `B2_C10p0_cw_balanced` | 0.450000 |
| success | S1_no_termination | visualwebarena | ok | 0.500000 | 0.680754 | 0.814815 | `B2_C10p0_cw_balanced` | 0.500000 |
| success | S1_no_termination | webarena | ok | 0.297619 | 0.387967 | 0.555556 | `B2_C1p0_cw_none` | 0.300000 |
| success | S1_no_termination | workarena | ok | 0.316667 | 0.676988 | 0.484848 | `B2_C1p0_cw_balanced` | 0.500000 |
| side_effect | S1_no_termination | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C0p1_cw_none` | 0.150000 |
| side_effect | S1_no_termination | visualwebarena | ok | 0.083333 | 0.074866 | 0.095238 | `B2_C0p1_cw_none` | 0.150000 |
| side_effect | S1_no_termination | webarena | ok | 0.091954 | 0.072221 | 0.081633 | `B2_C10p0_cw_balanced` | 0.400000 |
| side_effect | S1_no_termination | workarena | ok | 0.033333 | 0.034790 | 0.000000 | `B2_C0p1_cw_balanced` | 0.500000 |
| looping | S1_no_termination | assistantbench | ok | 0.458333 | 0.788064 | 0.869565 | `B2_C1p0_cw_balanced` | 0.350000 |
| looping | S1_no_termination | visualwebarena | ok | 0.291667 | 0.924036 | 0.875000 | `B2_C0p1_cw_none` | 0.350000 |
| looping | S1_no_termination | webarena | ok | 0.420455 | 0.915629 | 0.931507 | `B2_C10p0_cw_balanced` | 0.400000 |
| looping | S1_no_termination | workarena | ok | 0.616667 | 0.771452 | 0.902439 | `B2_C0p1_cw_balanced` | 0.650000 |
| success | S2_no_repetition | assistantbench | ok | 0.083333 | 0.104278 | 0.181818 | `B2_C1p0_cw_balanced` | 0.300000 |
| success | S2_no_repetition | visualwebarena | ok | 0.500000 | 0.706821 | 0.888889 | `B2_C10p0_cw_none` | 0.250000 |
| success | S2_no_repetition | webarena | ok | 0.297619 | 0.402831 | 0.562500 | `B2_C1p0_cw_none` | 0.400000 |
| success | S2_no_repetition | workarena | ok | 0.316667 | 0.805475 | 0.571429 | `B2_C10p0_cw_balanced` | 0.550000 |
| side_effect | S2_no_repetition | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C0p1_cw_none` | 0.200000 |
| side_effect | S2_no_repetition | visualwebarena | ok | 0.083333 | 0.069444 | 0.000000 | `B2_C10p0_cw_balanced` | 0.550000 |
| side_effect | S2_no_repetition | webarena | ok | 0.091954 | 0.067466 | 0.000000 | `B2_C10p0_cw_balanced` | 0.750000 |
| side_effect | S2_no_repetition | workarena | ok | 0.033333 | 0.028723 | 0.039216 | `B2_C1p0_cw_balanced` | 0.100000 |
| looping | S2_no_repetition | assistantbench | ok | 0.458333 | 0.788064 | 0.869565 | `B2_C1p0_cw_balanced` | 0.200000 |
| looping | S2_no_repetition | visualwebarena | ok | 0.291667 | 0.880159 | 0.800000 | `B2_C10p0_cw_none` | 0.500000 |
| looping | S2_no_repetition | webarena | ok | 0.420455 | 0.867384 | 0.931507 | `B2_C10p0_cw_none` | 0.550000 |
| looping | S2_no_repetition | workarena | ok | 0.616667 | 0.740968 | 0.880952 | `B2_C0p1_cw_balanced` | 0.550000 |
| success | S3_no_activity_volume | assistantbench | ok | 0.083333 | 0.583333 | 0.285714 | `B2_C0p1_cw_balanced` | 0.450000 |
| success | S3_no_activity_volume | visualwebarena | ok | 0.500000 | 0.845238 | 0.857143 | `B2_C10p0_cw_none` | 0.200000 |
| success | S3_no_activity_volume | webarena | ok | 0.297619 | 0.410180 | 0.526316 | `B2_C10p0_cw_none` | 0.250000 |
| success | S3_no_activity_volume | workarena | ok | 0.316667 | 0.742234 | 0.687500 | `B2_C1p0_cw_balanced` | 0.550000 |
| side_effect | S3_no_activity_volume | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C0p1_cw_balanced` | 0.650000 |
| side_effect | S3_no_activity_volume | visualwebarena | ok | 0.083333 | 0.102381 | 0.000000 | `B2_C1p0_cw_balanced` | 0.700000 |
| side_effect | S3_no_activity_volume | webarena | ok | 0.091954 | 0.069313 | 0.095238 | `B2_C10p0_cw_balanced` | 0.350000 |
| side_effect | S3_no_activity_volume | workarena | ok | 0.033333 | 0.027587 | 0.000000 | `B2_C0p1_cw_balanced` | 0.650000 |
| looping | S3_no_activity_volume | assistantbench | ok | 0.458333 | 0.825437 | 0.869565 | `B2_C0p1_cw_none` | 0.450000 |
| looping | S3_no_activity_volume | visualwebarena | ok | 0.291667 | 0.909354 | 0.769231 | `B2_C0p1_cw_none` | 0.550000 |
| looping | S3_no_activity_volume | webarena | ok | 0.420455 | 0.911258 | 0.794118 | `B2_C0p1_cw_balanced` | 0.450000 |
| looping | S3_no_activity_volume | workarena | ok | 0.616667 | 0.952773 | 0.867470 | `B2_C0p1_cw_none` | 0.350000 |
| success | S4_no_error | assistantbench | ok | 0.083333 | 0.145833 | 0.222222 | `B2_C10p0_cw_balanced` | 0.300000 |
| success | S4_no_error | visualwebarena | ok | 0.500000 | 0.702655 | 0.727273 | `B2_C10p0_cw_balanced` | 0.550000 |
| success | S4_no_error | webarena | ok | 0.297619 | 0.430675 | 0.542857 | `B2_C1p0_cw_none` | 0.250000 |
| success | S4_no_error | workarena | ok | 0.316667 | 0.704600 | 0.583333 | `B2_C10p0_cw_balanced` | 0.100000 |
| side_effect | S4_no_error | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C10p0_cw_none` | 0.100000 |
| side_effect | S4_no_error | visualwebarena | ok | 0.083333 | 0.073935 | 0.090909 | `B2_C0p1_cw_none` | 0.150000 |
| side_effect | S4_no_error | webarena | ok | 0.091954 | 0.081437 | 0.066667 | `B2_C10p0_cw_balanced` | 0.500000 |
| side_effect | S4_no_error | workarena | ok | 0.033333 | 0.035227 | 0.000000 | `B2_C1p0_cw_none` | 0.100000 |
| looping | S4_no_error | assistantbench | ok | 0.458333 | 0.825437 | 0.869565 | `B2_C1p0_cw_balanced` | 0.350000 |
| looping | S4_no_error | visualwebarena | ok | 0.291667 | 0.908730 | 0.800000 | `B2_C1p0_cw_none` | 0.450000 |
| looping | S4_no_error | webarena | ok | 0.420455 | 0.936012 | 0.933333 | `B2_C1p0_cw_balanced` | 0.250000 |
| looping | S4_no_error | workarena | ok | 0.616667 | 0.763995 | 0.902439 | `B2_C0p1_cw_none` | 0.600000 |
| success | S5_no_termination_or_repetition | assistantbench | ok | 0.083333 | 0.138889 | 0.266667 | `B2_C0p1_cw_balanced` | 0.350000 |
| success | S5_no_termination_or_repetition | visualwebarena | ok | 0.500000 | 0.666369 | 0.750000 | `B2_C10p0_cw_balanced` | 0.600000 |
| success | S5_no_termination_or_repetition | webarena | ok | 0.297619 | 0.408970 | 0.588235 | `B2_C10p0_cw_none` | 0.350000 |
| success | S5_no_termination_or_repetition | workarena | ok | 0.316667 | 0.776525 | 0.571429 | `B2_C10p0_cw_none` | 0.250000 |
| side_effect | S5_no_termination_or_repetition | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C0p1_cw_balanced` | 0.500000 |
| side_effect | S5_no_termination_or_repetition | visualwebarena | ok | 0.083333 | 0.075000 | 0.000000 | `B2_C10p0_cw_balanced` | 0.550000 |
| side_effect | S5_no_termination_or_repetition | webarena | ok | 0.091954 | 0.069132 | 0.000000 | `B2_C10p0_cw_balanced` | 0.700000 |
| side_effect | S5_no_termination_or_repetition | workarena | ok | 0.033333 | 0.027661 | 0.064516 | `B2_C0p1_cw_balanced` | 0.250000 |
| looping | S5_no_termination_or_repetition | assistantbench | ok | 0.458333 | 0.788064 | 0.869565 | `B2_C1p0_cw_balanced` | 0.200000 |
| looping | S5_no_termination_or_repetition | visualwebarena | ok | 0.291667 | 0.895465 | 0.800000 | `B2_C1p0_cw_none` | 0.450000 |
| looping | S5_no_termination_or_repetition | webarena | ok | 0.420455 | 0.842047 | 0.901408 | `B2_C1p0_cw_balanced` | 0.600000 |
| looping | S5_no_termination_or_repetition | workarena | ok | 0.616667 | 0.745998 | 0.902439 | `B2_C10p0_cw_none` | 0.650000 |
| success | S6_termination_repetition_only | assistantbench | ok | 0.083333 | 0.128788 | 0.285714 | `B2_C1p0_cw_balanced` | 0.400000 |
| success | S6_termination_repetition_only | visualwebarena | ok | 0.500000 | 0.752976 | 0.846154 | `B2_C10p0_cw_none` | 0.300000 |
| success | S6_termination_repetition_only | webarena | ok | 0.297619 | 0.416525 | 0.512821 | `B2_C1p0_cw_none` | 0.250000 |
| success | S6_termination_repetition_only | workarena | ok | 0.316667 | 0.748106 | 0.687500 | `B2_C10p0_cw_balanced` | 0.600000 |
| side_effect | S6_termination_repetition_only | assistantbench | single_class_negative | 0.000000 | NA | NA | `B2_C0p1_cw_balanced` | 0.450000 |
| side_effect | S6_termination_repetition_only | visualwebarena | ok | 0.083333 | 0.080409 | 0.000000 | `B2_C0p1_cw_balanced` | 0.550000 |
| side_effect | S6_termination_repetition_only | webarena | ok | 0.091954 | 0.073796 | 0.054054 | `B2_C10p0_cw_balanced` | 0.550000 |
| side_effect | S6_termination_repetition_only | workarena | ok | 0.033333 | 0.029285 | 0.000000 | `B2_C10p0_cw_balanced` | 0.450000 |
| looping | S6_termination_repetition_only | assistantbench | ok | 0.458333 | 0.851592 | 0.869565 | `B2_C0p1_cw_balanced` | 0.400000 |
| looping | S6_termination_repetition_only | visualwebarena | ok | 0.291667 | 0.909354 | 0.857143 | `B2_C0p1_cw_none` | 0.500000 |
| looping | S6_termination_repetition_only | webarena | ok | 0.420455 | 0.890785 | 0.794118 | `B2_C0p1_cw_none` | 0.400000 |
| looping | S6_termination_repetition_only | workarena | ok | 0.616667 | 0.953694 | 0.867470 | `B2_C0p1_cw_none` | 0.350000 |

## Deltas relative to S0

| Target | Variant | Macro ΔAP | Macro ΔF1 | Pooled ΔAP | Pooled ΔF1 | Retained ratio | Grade |
|---|---|---:|---:|---:|---:|---:|---|
| success | S0_full13 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 1.000000 | `reference` |
| success | S1_no_termination | +0.038348 | +0.009000 | -0.034939 | +0.013174 | 0.780647 | `moderate_dependency` |
| success | S2_no_repetition | +0.025042 | +0.033855 | -0.013516 | +0.026495 | 0.915145 | `limited_dependency` |
| success | S3_no_activity_volume | +0.165436 | +0.071864 | -0.028113 | +0.059119 | 0.823500 | `limited_dependency` |
| success | S4_no_error | +0.016131 | +0.001617 | +0.061458 | +0.003423 | 1.385848 | `limited_dependency` |
| success | S5_no_termination_or_repetition | +0.017879 | +0.026778 | -0.046701 | +0.036897 | 0.706802 | `limited_dependency` |
| success | S6_termination_repetition_only | +0.031789 | +0.065743 | -0.015252 | +0.045786 | 0.904244 | `sufficiency_only_not_dependency_grade` |
| side_effect | S0_full13 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | NA | `reference` |
| side_effect | S1_no_termination | +0.000183 | -0.010844 | +0.004730 | -0.010132 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S2_no_repetition | -0.005232 | -0.056729 | -0.000225 | -0.042808 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S3_no_activity_volume | +0.005984 | -0.038055 | +0.001108 | -0.003032 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S4_no_error | +0.003090 | -0.017275 | +0.011296 | -0.017411 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S5_no_termination_or_repetition | -0.003178 | -0.048295 | -0.001554 | -0.029069 | NA | `not_assessable_nonpositive_s0_ap_lift` |
| side_effect | S6_termination_repetition_only | +0.000720 | -0.051783 | +0.002608 | -0.039384 | NA | `sufficiency_only_not_dependency_grade` |
| looping | S0_full13 | +0.000000 | +0.000000 | +0.000000 | +0.000000 | 1.000000 | `reference` |
| looping | S1_no_termination | -0.001046 | +0.030108 | -0.007939 | +0.022794 | 0.978346 | `limited_dependency` |
| looping | S2_no_repetition | -0.031698 | +0.005986 | -0.042332 | +0.007886 | 0.884544 | `limited_dependency` |
| looping | S3_no_activity_volume | +0.048864 | -0.039424 | +0.050597 | -0.050198 | 1.137996 | `limited_dependency` |
| looping | S4_no_error | +0.007702 | +0.011814 | -0.014401 | +0.018142 | 0.960723 | `limited_dependency` |
| looping | S5_no_termination_or_repetition | -0.032948 | +0.003833 | -0.034371 | +0.005630 | 0.906256 | `limited_dependency` |
| looping | S6_termination_repetition_only | +0.050515 | -0.017446 | +0.077492 | -0.043997 | 1.211350 | `sufficiency_only_not_dependency_grade` |

## Registered mechanism questions

### Success

- `S1_no_termination`: retained AP-lift ratio 0.780647; pooled ΔAP -0.034939; pooled ΔF1 +0.013174; `moderate_dependency`.
- `S2_no_repetition`: retained AP-lift ratio 0.915145; pooled ΔAP -0.013516; pooled ΔF1 +0.026495; `limited_dependency`.
- `S5_no_termination_or_repetition`: retained AP-lift ratio 0.706802; pooled ΔAP -0.046701; pooled ΔF1 +0.036897; `limited_dependency`.
- `S6_termination_repetition_only`: retained AP-lift ratio 0.904244; pooled ΔAP -0.015252; pooled ΔF1 +0.045786; `sufficiency_only_not_dependency_grade`.

### Looping

- `S2_no_repetition`: retained AP-lift ratio 0.884544; pooled ΔAP -0.042332; pooled ΔF1 +0.007886; `limited_dependency`.
- `S5_no_termination_or_repetition`: retained AP-lift ratio 0.906256; pooled ΔAP -0.034371; pooled ΔF1 +0.005630; `limited_dependency`.
- `S6_termination_repetition_only`: retained AP-lift ratio 1.211350; pooled ΔAP +0.077492; pooled ΔF1 -0.043997; `sufficiency_only_not_dependency_grade`.

## Side Effect diagnostic

Side Effect remains diagnostic only: 12 positives overall, and AssistantBench contains 24 negatives and 0 positives. Dual-class metrics are missing rather than imputed.

| Variant | predicted positives | FPR | specificity | probability mean/max |
|---|---:|---:|---:|---:|
| S0_full13 | 15 | 0.625000 | 0.375000 | 0.221229/0.366183 |
| S1_no_termination | 24 | 1.000000 | 0.000000 | 0.220435/0.384883 |
| S2_no_repetition | 20 | 0.833333 | 0.166667 | 0.228953/0.387053 |
| S3_no_activity_volume | 4 | 0.166667 | 0.833333 | 0.509609/0.931899 |
| S4_no_error | 20 | 0.833333 | 0.166667 | 0.133935/0.267409 |
| S5_no_termination_or_repetition | 23 | 0.958333 | 0.041667 | 0.664979/0.957310 |
| S6_termination_repetition_only | 13 | 0.541667 | 0.458333 | 0.474506/0.578624 |

## Integrity, warnings, and boundaries

- External predictions: 4081/4081.
- Selected inner OOF predictions: 12243/12243.
- Configuration rows: 504/504; threshold rows: 1596/1596.
- Domain metrics: 84/84; pooled metrics: 21/21.
- Warnings: 2562 total; convergence warnings: 0.
- Frozen hashes before/after identical: `True`.
- test content/labels/predictions/metrics access: 0; test manifest access: 0.
- B3/TF-IDF, fusion, new features, single-feature exhaustive search, SHAP, permutation importance, secondary LOBO, LOMO, joint OOD, reasoning/error input, complex models, LLM Judge, and test experiments executed: 0.
- These are frozen-protocol predictive dependencies, not causal feature effects or significance tests.

## Stage recommendation and stop

`PASS_WITH_CONDITIONS`. The completed evidence is suitable for human review of whether a later uncertainty-analysis stage should be authorized. A1.5 stops here and does not automatically enter Bootstrap, significance testing, fusion, complex models, secondary LOBO, joint OOD, or test.
