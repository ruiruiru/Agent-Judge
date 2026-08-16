# A2.2 Deterministic Error Analysis

## Scope and selection

This analysis is `POST_FREEZE_DESCRIPTIVE`. It uses only frozen A1.10 scored predictions for `FINAL_SUCCESS_B2` and `FINAL_LOOPING_B2`; no inference, probability recomputation, threshold change, or model change occurred.

For each target and error type, a deterministic script selected:

1. the minimum absolute distance from the frozen threshold;
2. the lower median after ascending distance sort;
3. the maximum distance, with `trajectory_key` lexical ascending for ties.

The manifest contains exactly 12 cases: three FP and three FN for each target. Only the selected cases' allowlisted goal, action, observation, focused element, natural error, terminal structure, and repetition pattern were inspected. Reward, cumulative reward, judge, annotation, outcome-summary, and other A0.4-banned fields were not read into the analysis package.

## Success cases

| Error | Role | Probability | Primary code | Secondary code | Descriptive finding |
|---|---|---:|---|---|---|
| FP | borderline | 0.552893 | `LONG_BUT_UNSUCCESSFUL` | `STRUCTURALLY_NORMAL_SEMANTIC_FAILURE` | Repeated search/scroll activity ends at a visible network-security block. Activity and observation volume cannot identify blocked semantic completion. |
| FP | median | 0.749250 | `TERMINATION_MISMATCH` | `STRUCTURALLY_NORMAL_SEMANTIC_FAILURE` | The trajectory reaches restaurant results but never sends the requested answer to the user. |
| FP | high-confidence | 0.998642 | `LONG_BUT_UNSUCCESSFUL` | `UNCLEAR` | Large action-text volume and repeated terminal-form messages look completion-like, but the allowlisted fields cannot establish whether the proposed investment set is correct. |
| FN | borderline | 0.547943 | `SHORT_BUT_SUCCESSFUL` | — | One page interaction followed by a direct answer succeeds in only three recorded steps. |
| FN | median | 0.260528 | `TERMINATION_MISMATCH` | `OTHER` | The page exposes the requested bicycle time, but the terminal message says it is still waiting; the frozen label nevertheless records success. |
| FN | high-confidence | 0.057163 | `REPETITIVE_BUT_PROGRESSING` | `EXPLICIT_ERROR_RECOVERY` | A long cyclic click sequence with five errors resembles failure, yet the frozen label indicates accepted progress/completion. |

Success errors show the central limitation of task-agnostic structure: structural volume can be high when semantic completion fails, while a short path can be fully sufficient. Terminal-form actions also do not guarantee answer correctness, and reaching a correct page state is not identical to communicating a complete answer.

## Looping cases

| Error | Role | Probability | Primary code | Secondary code | Descriptive finding |
|---|---|---:|---|---|---|
| FP | borderline | 0.564269 | `EXPLICIT_ERROR_RECOVERY` | `REPETITIVE_BUT_PROGRESSING` | Nine interaction errors and retries resemble looping, but the actions move through different filter fields. |
| FP | median | 0.860450 | `NON_REPETITIVE_FAILURE` | `STRUCTURALLY_NORMAL_SEMANTIC_FAILURE` | Repeated query reformulations form a long failure without consecutive identical actions; the frozen label remains non-looping. |
| FP | high-confidence | 0.985032 | `REPETITIVE_BUT_PROGRESSING` | — | The same click is repeated while the visible listing position can advance, so identical actions need not mean unchanged state. |
| FN | borderline | 0.540037 | `OTHER` | `TERMINATION_MISMATCH` | A six-`noop` stalled suffix is diluted by earlier varied shopping actions and moderate total length. |
| FN | median | 0.193782 | `NON_REPETITIVE_FAILURE` | `EXPLICIT_ERROR_RECOVERY` | A semantic search cycle alternates different fill/click strings and therefore evades literal duplicate-action features. |
| FN | high-confidence | 0.009260 | `UNCLEAR` | — | The allowlisted trace is short, linear, error-free, and ends at an order-status view; it does not expose why the frozen Looping label is positive. |

Looping errors separate action repetition from state repetition. Identical actions can still advance pagination, while a semantic cycle can use different action strings and identifiers. Localized terminal stalls can also be hidden by earlier diverse activity.

## Evidence boundary

- `UNCLEAR` is retained when the allowlisted fields do not support a stronger explanation.
- These cases were selected for confidence-position coverage, not prevalence estimation.
- The taxonomy is descriptive and post-freeze; it does not alter features, models, thresholds, predictions, or A1 claims.
- Success is the primary paper-facing analysis. Looping is secondary diagnostic evidence.

Sources: `artifacts/a2_2_error_case_manifest.csv` and `artifacts/a2_2_error_case_notes.csv`.
