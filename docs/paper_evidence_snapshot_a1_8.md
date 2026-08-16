# Paper Evidence Snapshot A1.8

## Frozen decision

`READY_FOR_FINAL_METHOD_FREEZE`

## Key machine-readable evidence

| Evidence | Target | Estimand | Point | 95% CI | Role |
|---|---|---|---:|---|---|
| E_A16_P1_SUCCESS_MACRO_AP_LIFT | success | macro_ap_lift | 0.180405 | [0.108398, 0.343576] | primary |
| E_A16_P5_LOOPING_MACRO_AP_LIFT | looping | macro_ap_lift | 0.404061 | [0.333629, 0.505652] | primary |
| E_A16_P6_LOOPING_MACRO_AP | looping | macro_ap_delta_A_minus_B | -0.031698 | [-0.080426, -0.004079] | primary |
| E_A17_Q1_SUCCESS_MACRO_AP_LIFT | success | macro_ap_lift | 0.245120 | [0.164990, 0.381854] | primary |
| E_A17_Q3_SUCCESS_MACRO_F1_DELTA | success | macro_f1_delta_A_minus_B | -0.110261 | [-0.223897, -0.000848] | primary |
| E_A17_Q4_SIDE_EFFECT_MACRO_AP | side_effect | macro_ap | 0.146532 | [0.081094, 0.478352] | diagnostic |
| E_A17_Q5_LOOPING_MACRO_AP_DELTA | looping | macro_ap_delta_A_minus_B | -0.056240 | [-0.166089, 0.054840] | secondary |

## Interpretation boundary

- Stability labels are frozen bootstrap interpretations, not p-values or causal claims.
- Side Effect remains descriptive/exploratory because it has 12 positives and one all-negative domain.
- A1.4 is model-only transfer with same-task counterparts, not joint task-model OOD.
- Test access in A1.8: 0.
