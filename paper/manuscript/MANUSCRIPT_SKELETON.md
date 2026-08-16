# Title Placeholder

- Purpose: Human-selected title slot.
- Claim IDs: RW_NOVELTY.
- Evidence IDs: RW_NOVELTY.
- Citation keys: none.
- Table/Figure refs: none.
- Required caveats: No firstness, SOTA, or external-validation upgrade.

## Abstract bullet slots

- Purpose: Problem, method, Success, Looping, optional efficiency, bounded conclusion.
- Claim IDs: I1_PROBLEM; RW_NOVELTY; FC1; FC2; EFF1 optional; PROTO_BLIND_SCOPE.
- Evidence IDs: M4_B2_FEATURES; M8_BLIND_HELDOUT; FC1; FC2; E_A21_EFFICIENCY optional.
- Citation keys: none.
- Table/Figure refs: Table 1; Fig 2; Table 2/Fig 3 optional.
- Required caveats: Success first; Looping second; Side Effect excluded by default; evaluated benchmark families only.

## 1 Introduction

- Purpose: I1 Problem; I2 Gap; I3 Question; I4 Contributions.
- Claim IDs: I1_PROBLEM; RW_NOVELTY; I3_QUESTION; C1-C4.
- Evidence IDs: FC1; FC2; FE1; RW_NOVELTY; RW_WEBGRAPHEVAL; RW_WEBSTEP; RW_NO_HEAD_TO_HEAD.
- Citation keys: all ten verified A3.2 + addendum keys as mapped.
- Table/Figure refs: none.
- Required caveats: Narrow positioning only; no firstness, SOTA, or judge replacement.

## 2 Related Work

- Purpose: Trajectory/outcome; process/reward/step; structural/graph; THIS_WORK boundary.
- Claim IDs: RW_WEBGRAPHEVAL; RW_WEBSTEP; RW_SIMILAR; RW_NO_HEAD_TO_HEAD.
- Evidence IDs: LIT_*; RW_NOVELTY; RW_WEBGRAPHEVAL; RW_WEBSTEP; RW_SIMILAR_IDENTITY; RW_NO_HEAD_TO_HEAD.
- Citation keys: ten keys in artifacts/a3_2_citation_registry.csv.
- Table/Figure refs: Related Work positioning table.
- Required caveats: DIRECTLY_COMPARABLE=0; property comparison only.

## 3 Data / Problem Setup

- Purpose: Provenance, targets, eligibility, leakage-safe inputs.
- Claim IDs: PROTO_BLIND_SCOPE.
- Evidence IDs: M1_DATA_PROVENANCE; M2_ELIGIBILITY; M3_LEAKAGE_SAFE.
- Citation keys: lu2025agentrewardbench.
- Table/Figure refs: Fig 1.
- Required caveats: Reused benchmark and labels; no label modification; Side Effect low support.

## 4 Method

- Purpose: Frozen B2 representation and comparator roles.
- Claim IDs: C1.
- Evidence IDs: M4_B2_FEATURES; M5_COMPARATORS.
- Citation keys: none.
- Table/Figure refs: Fig 1; Table 3 appendix detail.
- Required caveats: Classifier itself is not the novelty; relative comparisons are dev-only.

## 5 Experimental Protocol

- Purpose: Grouped development, method freeze, blind held-out, post-freeze diagnostics.
- Claim IDs: PROTO_BLIND_SCOPE; PROTO_A2_POSTFREEZE.
- Evidence IDs: M6_GROUPED_PROTOCOL; M7_FINAL_FREEZE; M8_BLIND_HELDOUT; M9_POST_FREEZE_DIAGNOSTICS.
- Citation keys: none.
- Table/Figure refs: Fig 1.
- Required caveats: A2 did not select the method; blind held-out is not external validation.

## 6 Results

### R1 Development evidence

- Purpose: Frozen dev signal and selection context.
- Claim IDs: FD1; FD4; FD5.
- Evidence IDs: results map R1 primary/secondary IDs.
- Citation keys: none.
- Table/Figure refs: Table 3; Fig 4.
- Required caveats: Dev-only; Success first; Looping second; Side Effect exploratory.

### R2 Robustness / representation

- Purpose: Grouped, LOBO, model-transfer, ablation, dense evidence.
- Claim IDs: FD1; FD2; FD4; FD5; forbidden boundaries FD3; FD6-FD9.
- Evidence IDs: results map R2 primary/secondary IDs.
- Citation keys: none.
- Table/Figure refs: Table 3; Fig 4.
- Required caveats: No universal hierarchy; no joint OOD; non-causal.

### R3 Blind held-out confirmation

- Purpose: Frozen official held-out evidence.
- Claim IDs: FC1; FC2; FE1.
- Evidence IDs: FC1; FC2; FE1; M8_BLIND_HELDOUT.
- Citation keys: none.
- Table/Figure refs: Table 1; Fig 2; Fig S1.
- Required caveats: Success first; Looping second; Side Effect exploratory; evaluated families only.

### R4 Efficiency

- Purpose: Measured representation/extraction cost.
- Claim IDs: EFF1.
- Evidence IDs: E_A21_EFFICIENCY.
- Citation keys: none.
- Table/Figure refs: Table 2; Fig 3.
- Required caveats: Recorded environment and resource domains.

### R5 Interpretability / confounder

- Purpose: Associations and metadata risk.
- Claim IDs: DIAG_METADATA; FD4; FD5.
- Evidence IDs: A2.2 coefficient and metadata IDs.
- Citation keys: none.
- Table/Figure refs: Table 5; Fig 4.
- Required caveats: Post-freeze; non-causal; confounding not fully ruled out.

### R6 Failure boundaries / heterogeneity

- Purpose: Morphology/semantics cases and descriptive family variation.
- Claim IDs: DIAG_MORPH_SEM; DH1-DH3.
- Evidence IDs: A2.2 error IDs; DH1-DH3.
- Citation keys: none.
- Table/Figure refs: Table 5; Table 4; Fig 5; Fig S2.
- Required caveats: Illustrative cases; descriptive heterogeneity; no pairwise inference.

## 7 Discussion

- Purpose: D1-D6 bounded interpretation.
- Claim IDs: FC1; FC2; DIAG_METADATA; DIAG_MORPH_SEM; EFF1; RW_NO_HEAD_TO_HEAD.
- Evidence IDs: mapped Results evidence and verified A3.2 positioning.
- Citation keys: mapped verified keys only.
- Table/Figure refs: Table 1-5; Fig 2-5 as needed.
- Required caveats: Hypothesis, not mechanism; morphology != semantics; environment-specific; no replacement claim.

## 8 Limitations

- Purpose: Retain all frozen limitations.
- Claim IDs: LIM01-LIM14.
- Evidence IDs: LIM_A23_01-LIM_A23_10; M8_BLIND_HELDOUT; RW_NO_HEAD_TO_HEAD.
- Citation keys: A3.2 keys only if context is needed.
- Table/Figure refs: Table 4; Fig S1; Fig S2.
- Required caveats: No item may be weakened or presented as resolved.

## 9 Conclusion

- Purpose: Bounded Success/Looping evidence and limits.
- Claim IDs: FC1; FC2; PROTO_BLIND_SCOPE.
- Evidence IDs: FC1; FC2; M8_BLIND_HELDOUT.
- Citation keys: none.
- Table/Figure refs: none.
- Required caveats: No new numbers, Side Effect confirmation, external validation, SOTA, firstness, or replacement.

## References

- Purpose: Render only verified cited entries.
- Claim IDs: none.
- Evidence IDs: LIT_*.
- Citation keys: ten keys in artifacts/a3_2_citation_registry.csv.
- Table/Figure refs: none.
- Required caveats: No uncatalogued citation.

## Appendix map

- Purpose: Appendix A-K placement.
- Claim IDs: mapped per docs/a3_3_appendix_plan.md.
- Evidence IDs: M1-M9; FD1-FD9; FE1; DH1-DH3; A2 diagnostics; LIT_*.
- Citation keys: verified keys only.
- Table/Figure refs: Table 3 full; Table 4; Related Work table; Fig S1; Fig S2.
- Required caveats: Preserve dev-only, descriptive, exploratory, diagnostic, and environment-specific statuses.
