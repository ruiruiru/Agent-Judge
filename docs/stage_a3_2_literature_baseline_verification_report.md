# Stage A3.2 Literature and Baseline Verification Report

## Stage determination

`PASS_WITH_CONDITIONS`

The complete preregistered evidence package exists and no scientific operation was performed. Conditions are: no audited work meets the strict direct-comparability gate; CUARewardBench has versioned result values between arXiv v1 and its later official ICML 2026 OpenReview record; and some 2026 works have no verified proceedings DOI/pages or remain preprints. Missing metadata is left blank rather than inferred.

## Commits

- A3.2 preregistration: `f2cced39b237f7cb5759214e8401cf3bee2ab696`
- A3.1 result: `e17bf7c6c1974d8a96ab7e7814b0a21ec827a082`
- A2.3 result: `ad0576c488fafed243b464e0b8f903e9bb233b43`
- implementation: `ea2acfd489e950614452a07f8192a8f809ed7070`
- fix commits: `[]`
- result: `recorded_by_enclosing_result_commit`
- amend: `false`

## Frozen gates

- Git at formal start: clean.
- A3.1 and A2.3 result commits: reachable.
- A1.11 claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175`.
- Success: `CONFIRMATORY_SUPPORTED`.
- Looping: `CONFIRMATORY_SUPPORTED`.
- Side Effect: `EXPLORATORY_SUPPORTED`.

## Cutoff and source policy

- freshness window: `2024-01-01` through `2026-08-14`.
- search cutoff date: `2026-08-14`.
- final facts use peer-reviewed proceedings/publisher records, official paper or arXiv records, and official project repositories.
- search results were used only for discovery. No search snippet, blog, news item, survey, Scholar snippet, or generated summary is final evidence.
- every extracted number has a primary-source section/table/page/abstract location in `artifacts/a3_2_verified_result_claims.csv`.

## Mandatory Tier-4 verification

### AgentRewardBench

Canonical identity verified through the [COLM 2025 OpenReview record](https://openreview.net/forum?id=fQcUZMPIvu) and [official arXiv record](https://arxiv.org/abs/2504.08942). It constructs an expert-annotated web-trajectory benchmark and evaluates prompted LLM judges. THIS_WORK reuses the data, labels, targets, source-family identities, and official split, but studies frozen lightweight structural evaluators. Classification: `PARTIALLY_COMPARABLE`.

### Web-Shepherd

Canonical identity verified through the [NeurIPS 2025 proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/5bac36213824c6e0b0a173df8e2276a6-Abstract-Conference.html) and [official arXiv record](https://arxiv.org/abs/2505.15277). It trains text/vision step-level PRMs with preference/checklist supervision and uses rewards for action assessment and guided search. Classification: `CONTEXT_ONLY`.

### AgentRM

Canonical identity, venue, pages, and DOI verified through the [ACL Anthology](https://aclanthology.org/2025.acl-long.945/). It trains an 8B reward model to select rollouts through Best-of-N or beam search across mixed agent tasks. Classification: `CONTEXT_ONLY`.

## Bounded freshness scan

Seven additional 2025-2026 candidates were primary-source reviewed:

- included: Agent-as-a-Judge, Similar, CUARewardBench, WebArbiter, AgentProcessBench;
- reviewed but not paper-facing included: AgentPRM, ToolPRMBench.

The latter two remain in the verified registry for auditability. The five-work inclusion cap was reached after adding closer outcome/trajectory and multidimensional evaluation works. No newly found work changed the conservative core positioning. The stopping rule is satisfied; search expansion stopped and this package is not an exhaustive survey.

## Comparability audit

Every work was checked on dataset, split, target, trajectory versus step unit, input/information access, evaluation unit, metric, training data, judge/reward role, and test-time use.

- `DIRECTLY_COMPARABLE`: 0
- `PARTIALLY_COMPARABLE`: 2
- `CONTEXT_ONLY`: 8
- `NOT_COMPARABLE`: 0

AgentRewardBench shares data/split/targets with THIS_WORK but differs in method role, semantic access, and judge-evaluation framing. CUARewardBench is a close outcome/process analogue but uses OSWorld screenshots, VLM reward models, different units and metrics. All other works are step/reward/search, agentic-code-judge, or mixed-task contexts.

## Numeric-comparison decision

`NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`

No paper-facing performance ranking is authorized. The Related Work table compares properties only.

## AgentRewardBench relationship

The dedicated contract is `docs/a3_2_agentrewardbench_relationship.md`. Its frozen conclusion is:

```text
blind held-out within evaluated benchmark families
!=
independent external benchmark validation
```

THIS_WORK does not create a new benchmark and does not establish generalization to unseen benchmark families.

## Positioning and novelty

Allowed scope-limited formulations include:

- systematic study of lightweight structural trajectory signals;
- blind-first frozen held-out evaluation within evaluated benchmark families;
- cost and interpretability characterization;
- task-agnostic structural representation within the studied benchmark setting.

Prohibited formulations include all eight phrases in `docs/a3_2_positioning_and_novelty_contract.md`, including firstness, state-of-the-art, LLM-judge replacement/superiority, and unseen-benchmark generalization claims. Side Effect remains exploratory.

## Citation and paper-facing artifacts

- citation registry: 8 verified paper-facing citations;
- BibTeX: 8 matching entries;
- positioning table: Markdown and LaTeX attribute tables generated, with no numeric cross-paper ranking;
- writing skeleton: three constrained paragraph plans generated; no full Related Work section or manuscript was written.

## Verification statuses

- `VERIFIED_PRIMARY`: 9
- `VERIFIED_WITH_LIMITATION`: 1
- `IDENTITY_ONLY`: 0
- `UNRESOLVED`: 0

The single limitation is CUARewardBench version drift: paper-facing result values come only from the later official ICML 2026 OpenReview record; earlier arXiv v1 values are not mixed into the claim.

## Unresolved items

None at the identity level. Absent DOI/pages or repository fields for preprints are recorded as blank or not verified. They are not guessed.

## Scientific-operation counters

- `new_model_fits = 0`
- `new_inference_runs = 0`
- `new_embedding_runs = 0`
- `A1_metric_recomputations = 0`
- `bootstrap_reruns = 0`
- `new_significance_tests = 0`
- `threshold_changes = 0`
- `eligibility_changes = 0`
- `final_model_changes = 0`
- `official_test_tuning = 0`
- `external_dataset_downloads = 0`
- `external_dataset_runs = 0`

## Verifiers

- dependency-light implementation tests;
- frozen-commit reachability and exact claim-matrix hash checks;
- registry schema, canonical identity, primary-source, result-location, comparability, citation/BibTeX, relationship-boundary, stopping-rule, and zero-counter checks;
- final output-hash and Git-clean verification after the result commit.

## Important outputs

- `artifacts/a3_2_verified_literature_registry.csv`
- `artifacts/a3_2_verified_result_claims.csv`
- `artifacts/a3_2_positioning_matrix.csv`
- `artifacts/a3_2_citation_registry.csv`
- `artifacts/a3_2_literature_search_log.csv`
- `paper/references/a3_2_verified_related_work.bib`
- `paper/tables/Table_Related_Work_Positioning.md`
- `paper/tables/Table_Related_Work_Positioning.tex`
- `docs/a3_2_related_work_writing_skeleton.md`

## Next state

`WAIT_FOR_HUMAN_A3_2_REVIEW`

STOP. Do not enter A3.3 automatically.
