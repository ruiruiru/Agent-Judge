# AgentRewardBench Data Contract — Stage A0.1

## Scope and evidence status

This document locks metadata only. No full trajectories, judgments, screenshots, features, models, baselines, or test-set model results were downloaded or produced.

- Direct observations: official repository identifiers, revisions, CSV schemas, raw label values, Terms of Use location, and file hashes.
- Computed statistics: row counts, unique trajectory/task counts, distributions, duplicate-annotation checks, and split joins.
- Risk judgments: absence of a standard license identifier, duplicate-label disagreement, and benchmark namespace differences.
- Unconfirmed questions: how repeated human annotations should eventually be aggregated and which benchmark namespace should define LOBO. Neither is decided in Stage A0.1.

## Fixed sources

- GitHub repository: [https://github.com/McGill-NLP/agent-reward-bench](https://github.com/McGill-NLP/agent-reward-bench)
- GitHub commit: `f838338886d723d40b586309465a38277803d9e6`
- Hugging Face repository: `https://huggingface.co/datasets/McGill-NLP/agent-reward-bench`
- Hugging Face revision: `b6d17e646009d6cb63d5dd7be78807b680693f61`
- Metadata retrieval time (UTC): `2026-08-02T08:16:12.784189+00:00`

## License and Terms of Use

- License status: **No standard license identifier declared; custom Terms of Use apply**
- Terms of Use original location: [https://huggingface.co/datasets/McGill-NLP/agent-reward-bench/blob/b6d17e646009d6cb63d5dd7be78807b680693f61/README.md#terms-of-use](https://huggingface.co/datasets/McGill-NLP/agent-reward-bench/blob/b6d17e646009d6cb63d5dd7be78807b680693f61/README.md#terms-of-use)
- The fixed Hugging Face card contains a `Terms of Use` section. Its card metadata does not declare a standard `license` identifier. This audit records that fact and does not infer a legal license.

## Official metadata files

| File | Bytes | SHA256 |
|---|---|---|
| annotations.csv | 265137 | `155be0e6530d190c14a056f0195aaafa081c2a45a36e8f72b922c9fdc6838367` |
| splits.csv | 19149 | `42bfeef886c1d7b216d31a6c8e9f7af58a6c4bd4d236df9f230e24c558c2499d` |
| README.md | 3819 | `e16adf817e3950441d70c7bb1bb3f44bd8dc65344938247f23fea4aaff9f654e` |

## Official split contract

The official split file is `agent_reward_bench/data/splits.csv`. Only `dev` and `test` are accepted. Stage A0.1 computes aggregate metadata for both as explicitly required, but does not use test data for feature, model, threshold, or method selection.

Task IDs are normalized only by trimming/lowercasing and removing the observed annotation-only markers `.improved.` and `.resized.`. This maps all annotation rows to official split tasks; no unmatched task is assigned by guesswork.

| Split | Rows | Unique tasks |
|---|---|---|
| dev | 51 | 51 |
| test | 300 | 300 |

## Target labels

| Research target | Official field | Exact mapping |
|---|---|---|
| Success | `trajectory_success` | `Successful` → 1, `Unsuccessful` → 0, `Unsure` → missing/excluded |
| Side Effect | `trajectory_side_effect` | `Yes` → 1, `No` → 0, `Unsure` → missing/excluded |
| Repetitiveness / Looping | `trajectory_looping` | `Yes` → 1, `No` → 0 |

`trajectory_optimality` is distribution-audited only. It is not converted to a binary target.

| Target | Positive | Negative | Unsure excluded | Unknown | Positive rate among valid |
|---|---|---|---|---|---|
| Success | 395 | 1012 | 1 | 0 | 0.280739 |
| Side Effect | 91 | 1316 | 1 | 0 | 0.064677 |
| Repetitiveness / Looping | 711 | 697 | 0 | 0 | 0.504972 |

## Annotation and benchmark identity

- Annotation rows: **1408**
- Unique trajectories: **1302**, using `(benchmark, normalized_task_id, model_name)`.
- Unique normalized tasks: **351**
- Annotation benchmarks: **4**
- Split-file benchmark namespaces: **5**
- Models: **4**

| Annotation benchmark | Annotation rows | Unique trajectories |
|---|---|---|
| assistantbench | 132 | 132 |
| visualwebarena | 300 | 300 |
| webarena | 501 | 398 |
| workarena | 475 | 472 |

The annotations use `workarena`, while the split file distinguishes `workarena_l1` and `workarena_l2`. Both observed fields are preserved. Stage A0.1 does not choose which namespace later LOBO evaluation must use.

## Repeated annotation policy

Repeated `(benchmark, normalized_task_id, model_name)` keys are retained as separate human annotation rows. They are not treated as independent trajectories for the unique-trajectory count, and they are not voted, averaged, deleted, or relabeled. A later aggregation rule requires explicit approval.

- Duplicate trajectory groups: **106**
- Extra annotation rows: **106**
- All repeated groups have distinct annotators: **True**
- All repeated groups share one `exp_name`: **True**
- Per-label disagreement groups: `{"Success": 13, "Side Effect": 4, "Repetitiveness / Looping": 11, "Optimality": 42}`

## Test sealing principle

The official `test` assignments are immutable. This metadata audit reports only required aggregate counts and label distributions. Test records must not inform feature design, preprocessing, model selection, threshold selection, fusion weights, or protocol changes.

## Known limitations and stop conditions

- No standard license identifier is declared; the custom Terms of Use must be reviewed by the research lead.
- Duplicate human labels sometimes disagree; no aggregation policy is authorized yet.
- Annotation and split benchmark namespaces differ for WorkArena; a later evaluation contract must resolve the LOBO grouping field without consulting model results.
- This contract does not establish trajectory-field availability, parsing success, leakage safety, or Stage A/Stage B readiness because full trajectories were outside A0.1 scope.
