# Stage A1.10a blind official-test inference report

## Stage determination

`PASS`

This is blind inference only. No test labels, eligibility, or metrics were accessed.

## Provenance

- Formal start commit: `d32f9e215f27425ce907493344e4c65c835e91f6`
- Implementation fix commit: `100966969bf36c968051dea7fbbb675c1814b7cd`
- A1.9a: `4944df46be45d8ad52d57a051e04b59c4a1a82ee`
- A1.9b: `8f96a6f032ee9b4dd0272164d60230303612043b`
- A1.10a result commit: `recorded_by_enclosing_result_commit`
- A1.8 claim matrix SHA-256: `264678a325f1680c8cfdad3631e6f5209a29a91e6ab8dd5b9683adb857810590`
- GitHub data commit: `f838338886d723d40b586309465a38277803d9e6`
- Hugging Face revision: `b6d17e646009d6cb63d5dd7be78807b680693f61`
- Qwen revision: `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`
- Qwen weight SHA-256: `0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd`

## Coverage and frozen representations

- Test trajectories: 1106
- Task groups: 300
- Benchmarks: {"assistantbench": 108, "visualwebarena": 276, "webarena": 310, "workarena": 412}
- Models: {"GenericAgent-Qwen_Qwen2.5-VL-72B-Instruct": 300, "GenericAgent-anthropic_claude-3.7-sonnet": 300, "GenericAgent-gpt-4o-2024-11-20": 300, "GenericAgent-meta-llama_Llama-3.3-70B-Instruct": 206}
- Duplicate identifiers: 0
- Missing raw mappings: 0
- B2 feature rows/schema: 1106 / 13
- B4 embedding rows/dim: 1106 / 1024
- Blind prediction rows: 3318

## Frozen methods

- Success: threshold 0.55; model `afbdb0a60205d7c6bd40232a8c8a1b1ad3b0910d6b65fecf894cca1a040123c1`
- Looping: threshold 0.55; model `862b7ff2b0cbcb5faf88908f5fe5824c7f4e52c2c21521e41bb5fb71b011660c`
- Side Effect: threshold 0.40; exploratory-only; model `5eb29646c10a8193b8492ffe26a41a63414dc9da884890813273c43d17a7de59`
- Estimator fits: 0

## Frozen artifact hashes

- Identifier manifest: `97a1366ec31efd7bfe86d8f2a5e95c85cc248bd22ead5dfe47993c79aeb4d550`
- Structural features: `e39994f35815b2b5131e0b1bf1e5e81c86e430a1f6bdfe1fc9448a5b847faa6d`
- Test embedding: `8590b9cb6129bc79181febeaa18e709551743fd271e579c5c78f833edf4b1c42`
- Blind predictions: `a3a232484716ee455a604f03ffd40e6f734a1925ffdfb93e4a3d04118de27c3d`
- Blind prediction manifest: `f0289ca40e138390d00920cf28a59721aa48f0a11305a79f33eb66022aa050a0`

## Access and prohibited-operation guards

- Test access: `{"content": 1106, "eligibility": 0, "embeddings": 1106, "features": 1106, "labels": 0, "manifest": 1106, "metrics": 0, "predictions": 3318}`
- Prohibited experiments: `{"b3_final_method": 0, "calibration": 0, "config_selection": 0, "dev_embedding_regeneration": 0, "estimator_refit": 0, "feature_change": 0, "fusion": 0, "label_guided_debugging": 0, "llm_judge": 0, "new_model_family": 0, "s6_final_method": 0, "second_embedding_model": 0, "threshold_tuning": 0}`
- Warnings: 11 total: 8 excluded schema-drift groups; 1 semantic-environment
  startup error before model load/forward, recovered by the independent fix
  commit and a full embedding-stage restart; 1 tokenizer full-sequence length
  notice, while actual frozen chunks remained at a maximum of 8191 payload
  tokens; and 1 historical A1.7 test error from its stale preregistered root
  `.gitattributes` hash after the approved A1.9 change. The root file has no
  working-tree diff and SHA-256
  `0b086feed48cc07464050bd29afa61a9d6b68aa678f74853b0a8656f2f51faf6`.
- Failure provenance: `artifacts/a1_10a_implementation_failures.json`
- Independent verification: `PASS`

## Verification and Git gate

- A1.10a tests: 20/20 passed.
- Frozen adapter/baseline tests: 38/38 passed.
- A1.9 provenance/model tests: 30/30 passed.
- A1.7 semantic-contract tests: 48/49 passed; the sole historical attribute
  guard error is documented above and is not an A1.10a regression.
- Independent structural/probability verifier: `PASS`; maximum probability
  absolute error 0; estimator-fit AST count 0.
- Git clean: verified immediately after the enclosing A1.10a result commit.

## Stop boundary

`READY_FOR_TEST_LABEL_UNLOCK_REVIEW`

A1.10b was not authorized or executed. Stop and await human review.
