# Stage A2.1 Efficiency & Cost Benchmark Report

## Stage determination

`PASS`

This report measures computational cost only under the recorded machine. It does not select a model or recompute scientific performance.

## Frozen gates

- Claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175` (verified)
- Main table SHA-256: `c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947` (verified)
- Corpus: 196 frozen dev trajectories
- B2: 13 dimensions, frozen structural extractor, CPU
- B4: 1024 dimensions, revision `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, device `cuda:0`
- Model fits / A1 metric recomputations / official-test access or tuning: 0

## Measurement definitions

- Cold start: fresh process, frozen input load, initialization, and first usable output.
- Warm extraction: full corpus after one excluded warmup. B4 includes tokenization and encoder forwards.
- Classifier inference: existing representation; reload is outside timed `predict_proba`.
- Storage: both matrices serialized as NumPy `.npy`; B2 float64, B4 float32.
- CPU peak: Windows peak working set. GPU peak: PyTorch reserved memory.

## Efficiency results

| Method | Dim | Device | Cold s | Extraction ms/traj | Inference ms/traj | Repr MiB | Classifier MiB | Encoder MiB | CPU RSS MiB | GPU VRAM MiB |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B2 | 13 | cpu | 0.957790 | 0.013432 | 0.000703 | 0.019562 | 0.001129 | NA | 155.098 | NA |
| B4 | 1024 | cuda:0 | 7.880716 | 2370.268617 | 0.001803 | 0.765747 | 0.008141 | 1136.385 | 2163.023 | 1536.000 |

B4 model load: 1.970331 s. Encoder is the pinned weight file; full snapshot is 1151.553 MiB.

## Relative cost (B4 / B2)

- Dimension: 78.769231x
- Representation storage: 39.145086x
- Warm extraction: 176469.135088x
- Classifier-only inference: 2.566449x
- Peak CPU RSS: 13.946203x

Ratios apply only to this environment. They do not establish predictive superiority or universal hardware superiority.

## Frozen A1 context (exact artifact read; not recomputed)

| Target | Frozen method | Frozen AP string | Frozen grade |
|---|---|---:|---|
| Success | FINAL_SUCCESS_B2 | 0.65483617599915878 | CONFIRMED_HELDOUT_SIGNAL |
| Looping | FINAL_LOOPING_B2 | 0.92176938453725654 | CONFIRMED_HELDOUT_SIGNAL |
| Side Effect | FINAL_SIDE_EFFECT_B4 | 0.10727900983026536 | EXPLORATORY_TEST_RESULT |

Source: `artifacts/a1_11_table_main_test_results.csv` at the verified hash above. No A1 metric function was called.

## Repetitions and scope

- B2: 1 warmup + 5 measured extraction and inference runs.
- B4: 1 warmup + 3 measured extraction and inference runs.
- Summary: median; no fastest-run selection.
- Formal commit: `a67f6451dd2fb39388337c58b3fda5439290bd35`
- Run directory: `runs/a2_1_efficiency_20260809T095033Z_a67f6451`
- A1 metric recomputations = 0; model fits = 0; A1 model/threshold changes = 0.
- Official-test access/tuning = 0; A2.2/A2.3/external validation/A3 = 0.

## Limitations

- Timing is environment-specific and may reflect OS background activity.
- The tokenizer emitted a model-max-length advisory for a 146,534-token payload. The full token list was retained and deterministically split into frozen 8,191-payload-token chunks before each forward pass; there was no truncation or over-length model input.
- B2 inference uses frozen `FINAL_SUCCESS_B2`; B4 uses frozen `FINAL_SIDE_EFFECT_B4`.
- The additional frozen Looping B2 artifact is size-audited, not used to fabricate another timing result.
- CPU RSS and GPU reserved memory are different resource domains and are separate.

`WAIT_FOR_HUMAN_A2_1_REVIEW`
