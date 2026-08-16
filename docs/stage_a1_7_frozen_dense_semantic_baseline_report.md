# Stage A1.7 frozen dense semantic baseline report

## Stage determination

`PASS_WITH_CONDITIONS`

All technical completeness guards passed. Interpretation remains conditional because Side Effect has only 12 positives and one single-class held-out domain.

## Provenance and model freeze

- A1.7a preregistration commit: `e776c16710fd18c1462808a044f911e40061c5c3`
- Independent verifier fix commit: `676ab5efe4f05a2cd5552421510058e5d7553859`; the first post-fit B4 invocation was fully invalidated and archived before all 12 cells were rerun.
- A1.7b experiment commit: recorded by the enclosing result commit.
- Post-result Git byte-policy fix: recorded by the enclosing fix commit; `.npy` and `.parquet` are stored as binary, with formal working-tree bytes and scientific values unchanged.
- Data GitHub revision: `f838338886d723d40b586309465a38277803d9e6`
- Data Hugging Face revision: `b6d17e646009d6cb63d5dd7be78807b680693f61`
- Model: `Qwen/Qwen3-Embedding-0.6B`; requested revision `97b0c61`; immutable revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`.
- `model.safetensors` SHA-256: `0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd`.
- Semantic environment: Python 3.12.13; torch 2.7.1+cu128; CUDA 12.8; GPU NVIDIA GeForce RTX 5070; transformers 4.53.3.

## Tokenization, chunking, pooling, and determinism

Payload is `tokenizer.encode(text, add_special_tokens=False)`, split in-order into non-overlapping payload chunks of at most 8191 tokens, with exactly one tokenizer EOS appended. There is no truncation.
Each chunk uses the last EOS hidden state, float32 L2 normalization, payload-token-count weighted mean, and final trajectory L2 normalization.
- Payload tokens min/median/mean/p95/max: 1933/21164.500000/35260.729592/115367.000000/160577.
- Chunk count min/median/mean/p95/max: 1/3.000000/4.821429/15.000000/20.
- Total payload tokens/chunks and multi-chunk trajectories: 6911103/945/142.
- Fixed 16-probe minimum cosine: `1.000000000`; maximum absolute difference: `0.000e+00`; PASS.

## Frozen embeddings and B4

- Matrix: `196 × 1024`, float32, finite, L2-normalized; SHA-256 `26a52ea14c7538c87527bd129880ff795e10640355474688e6297a9407ad7037`.
- Classifier: LogisticRegression, L2/liblinear, max_iter=5000, random_state=2026, no StandardScaler; C={0.1,1,10} × class_weight={None,balanced}.
- Selected config distribution: `[{"target": "looping", "config_id": "B4_C0p1_cw_balanced", "count": 1}, {"target": "looping", "config_id": "B4_C10p0_cw_balanced", "count": 2}, {"target": "looping", "config_id": "B4_C10p0_cw_none", "count": 1}, {"target": "side_effect", "config_id": "B4_C10p0_cw_balanced", "count": 1}, {"target": "side_effect", "config_id": "B4_C10p0_cw_none", "count": 1}, {"target": "side_effect", "config_id": "B4_C1p0_cw_balanced", "count": 2}, {"target": "success", "config_id": "B4_C10p0_cw_balanced", "count": 2}, {"target": "success", "config_id": "B4_C1p0_cw_balanced", "count": 2}]`.
- Selected threshold distribution: `[{"target": "looping", "threshold": 0.25, "count": 1}, {"target": "looping", "threshold": 0.3, "count": 1}, {"target": "looping", "threshold": 0.5, "count": 2}, {"target": "side_effect", "threshold": 0.1, "count": 1}, {"target": "side_effect", "threshold": 0.2, "count": 1}, {"target": "side_effect", "threshold": 0.45, "count": 1}, {"target": "side_effect", "threshold": 0.5, "count": 1}, {"target": "success", "threshold": 0.35, "count": 2}, {"target": "success", "threshold": 0.5, "count": 1}, {"target": "success", "threshold": 0.55, "count": 1}]`.

## Four-domain B4 results

| Target | Held-out | Status | Pos/Neg | AP | AP lift | F1 | Config | Threshold |
|---|---|---|---:|---:|---:|---:|---|---:|
| success | assistantbench | ok | 2/22 | 0.297619 | 0.214286 | 0.142857 | `B4_C1p0_cw_balanced` | 0.500000 |
| success | visualwebarena | ok | 12/12 | 0.647507 | 0.147507 | 0.727273 | `B4_C10p0_cw_balanced` | 0.350000 |
| success | webarena | ok | 25/59 | 0.507026 | 0.209407 | 0.567568 | `B4_C10p0_cw_balanced` | 0.350000 |
| success | workarena | ok | 19/41 | 0.725948 | 0.409281 | 0.190476 | `B4_C1p0_cw_balanced` | 0.550000 |
| side_effect | assistantbench | single_class_negative | 0/24 | NA | NA | NA | `B4_C10p0_cw_none` | 0.100000 |
| side_effect | visualwebarena | ok | 2/22 | 0.103175 | 0.019841 | 0.105263 | `B4_C1p0_cw_balanced` | 0.450000 |
| side_effect | webarena | ok | 8/79 | 0.111423 | 0.019469 | 0.064516 | `B4_C1p0_cw_balanced` | 0.500000 |
| side_effect | workarena | ok | 2/58 | 0.225000 | 0.191667 | 0.222222 | `B4_C10p0_cw_balanced` | 0.200000 |
| looping | assistantbench | ok | 11/13 | 0.788064 | 0.329730 | 0.800000 | `B4_C10p0_cw_balanced` | 0.500000 |
| looping | visualwebarena | ok | 7/17 | 0.791667 | 0.500000 | 0.700000 | `B4_C10p0_cw_balanced` | 0.250000 |
| looping | webarena | ok | 37/51 | 0.855320 | 0.434865 | 0.831461 | `B4_C10p0_cw_none` | 0.300000 |
| looping | workarena | ok | 37/23 | 0.743354 | 0.126687 | 0.795699 | `B4_C0p1_cw_balanced` | 0.500000 |

## Macro and pooled results

| Target | Macro AP | Macro F1 | Pooled AP | Pooled F1 |
|---|---:|---:|---:|---:|
| success | 0.544525 | 0.407043 | 0.497306 | 0.507042 |
| side_effect | 0.146532 | 0.130667 | 0.100231 | 0.115942 |
| looping | 0.794601 | 0.781790 | 0.775973 | 0.801802 |

## Frozen A1.3 comparisons

| Target | B4−B2 macro AP/F1 | B4−B3 macro AP/F1 | B4−B2 pooled AP/F1 | B4−B3 pooled AP/F1 |
|---|---:|---:|---:|---:|
| success | 0.064715/-0.110261 | 0.121668/0.015099 | 0.035943/-0.033838 | 0.199359/0.087687 |
| side_effect | 0.086090/0.060867 | 0.034591/0.013921 | 0.058541/0.054086 | 0.052699/-0.044772 |
| looping | -0.056240/-0.082730 | 0.090404/0.150924 | -0.060067/-0.082620 | 0.109018/0.162397 |

## Q1–Q5 fixed group-aware bootstrap

| ID | Target | Estimand | Role | Point | Median | 95% CI | Valid | Invalid | Grade |
|---|---|---|---|---:|---:|---|---:|---:|---|
| Q1 | success | B4_dense_embedding_lr macro_ap_lift | primary | 0.245120 | 0.269188 | [0.164990, 0.381854] | 1.000000 | 0 | `stable_positive_under_bootstrap` |
| Q2 | success | B4_dense_embedding_lr−B3 macro_ap_delta_A_minus_B | primary | 0.121668 | 0.105772 | [-0.013206, 0.271618] | 1.000000 | 0 | `difference_uncertain` |
| Q2 | success | B4_dense_embedding_lr−B3 macro_f1_delta_A_minus_B | primary | 0.015099 | 0.013633 | [-0.089392, 0.130178] | 1.000000 | 0 | `difference_uncertain` |
| Q3 | success | B4_dense_embedding_lr−B2 macro_ap_delta_A_minus_B | primary | 0.064715 | 0.056224 | [-0.061181, 0.167226] | 1.000000 | 0 | `difference_uncertain` |
| Q3 | success | B4_dense_embedding_lr−B2 macro_f1_delta_A_minus_B | primary | -0.110261 | -0.112669 | [-0.223897, -0.000848] | 1.000000 | 0 | `stable_drop_for_A_vs_B` |
| Q4 | side_effect | B4_dense_embedding_lr macro_ap | support_diagnostic_only | 0.146532 | 0.191240 | [0.081094, 0.478352] | 0.985500 | 145 | `support_diagnostic_only` |
| Q4 | side_effect | B4_dense_embedding_lr pooled_ap | support_diagnostic_only | 0.100231 | 0.106813 | [0.036924, 0.229248] | 0.999900 | 1 | `support_diagnostic_only` |
| Q4 | side_effect | B4_dense_embedding_lr−B3 macro_ap_delta_A_minus_B | support_diagnostic_only | 0.034591 | 0.042341 | [-0.185464, 0.324753] | 0.985500 | 145 | `support_diagnostic_only` |
| Q5 | looping | B4_dense_embedding_lr−B2 macro_ap_delta_A_minus_B | secondary_complexity_control | -0.056240 | -0.056140 | [-0.166089, 0.054840] | 1.000000 | 0 | `difference_uncertain` |
| Q4 | side_effect | B4_dense_embedding_lr domain_ap (assistantbench) | support_diagnostic_only | NA | NA | [NA, NA] | 0.000000 | 10000 | `support_diagnostic_only` |
| Q4 | side_effect | B4_dense_embedding_lr domain_ap (visualwebarena) | support_diagnostic_only | 0.103175 | 0.125641 | [0.045455, 0.500000] | 0.905600 | 944 | `support_diagnostic_only` |
| Q4 | side_effect | B4_dense_embedding_lr domain_ap (webarena) | support_diagnostic_only | 0.111423 | 0.120162 | [0.025000, 0.295548] | 0.986900 | 131 | `support_diagnostic_only` |
| Q4 | side_effect | B4_dense_embedding_lr domain_ap (workarena) | support_diagnostic_only | 0.225000 | 0.265152 | [0.083333, 1.000000] | 0.881400 | 1186 | `support_diagnostic_only` |

## Frozen conclusions

- Success: `dense_semantic_signal_without_clear_incremental_gain`.
- Side Effect: `promising_low_support_semantic_signal`; role remains `support_diagnostic_only`, with 12 total positives and AssistantBench 0/24.
- Looping: `semantic_complexity_not_needed`; role remains `secondary_complexity_control`.

## Integrity and boundaries

- External predictions: 583/583; selected inner OOF: 1749/1749; configs: 72/72; thresholds: 228/228.
- A1.6 registry reused byte-for-byte: `3f875ca8a32fdb99c5754c69daac741b960ac84e742c1eabd4135bb246420a0f`; new registry generated: 0.
- Frozen hashes identical before/after: `True`.
- Fine-tune=0; quantization=0; fusion=0; second embedding model=0; new classifier family=0.
- Formal network=0; local_files_only=true; test content/labels/predictions/metrics access=0; prohibited experiments=0.
- Tests: `293 repository tests PASS; independent B4 result recomputation PASS; independent embedding integrity verification PASS`.

## Stage recommendation and stop

`PASS_WITH_CONDITIONS`. The A1.7 evidence is complete and awaits human review. Do not enter fusion, a second embedding model, LLM Judge, secondary LOBO, joint OOD, or test.
