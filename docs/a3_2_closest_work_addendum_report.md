# Stage A3.2 Addendum — Targeted Closest-Work Coverage and Positioning Patch

## Stage determination

`PASS_WITH_CONDITIONS`

The targeted primary-source audit verified WebGraphEval and WebStep, resolved the canonical identity behind “Similar,” rechecked every comparability class, and patched the paper-facing positioning package. No work satisfies the strict direct-comparability gate. Conditions are limited to source status and availability: WebGraphEval is an arXiv v1 NeurIPS 2025 workshop paper; WebStep is arXiv v2 with an official COLM 2026 reference while its project page still marks code and data as coming soon. Missing DOI/pages/volume/publisher fields were left blank rather than inferred.

## Provenance and hard gates

- formal start: clean `a57040bf3314b446772ada355143298a24d4ff14`;
- A3.2 result: `ef37dee92ef319b2f7d39367e757919a898fbfdb`, reachable;
- A3.3 preregistration: `b85c93f17a3e90f20bca5162817111c5bc1ac70a`, reachable and an ancestor;
- A3.3 taskbook: `docs/tasks/STAGE_A3_3_MANUSCRIPT_EVIDENCE_FREEZE.md`, present and unchanged;
- A1.11 claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175`, exact;
- frozen claims: Success `CONFIRMATORY_SUPPORTED`, Looping `CONFIRMATORY_SUPPORTED`, Side Effect `EXPLORATORY_SUPPORTED`;
- implementation commit: `a5029c5` (`chore: implement A3.2 closest-work verification patch`);
- result commit: `recorded_by_enclosing_result_commit`;
- fix commits: none;
- amend: false.

The search boundary remained exact: WebGraphEval, WebStep / *Where Did It Go Wrong?*, and the primary-source chain needed to resolve Similar. No freshness scan was reopened and no unrelated candidate was added.

## WebGraphEval verification

### Canonical identity

- title: *WebGraphEval: Multi-Turn Trajectory Evaluation for Web Agents using Graph Representation*;
- authors: Yaoyao Qian, Yuanli Wang, Jinda Zhang, Yun Zong, Meixu Chen, Hanhan Zhou, Jindan Huang, Yifan Zeng, Xinyu Hu, Chan Hee Song, Danqing Zhang;
- year/status: 2025; NeurIPS 2025 Workshop on Multi-Turn Interactions in Large Language Models;
- identifier/version: `arXiv:2510.19205`, v1;
- primary source: [official arXiv record](https://arxiv.org/abs/2510.19205) and [official arXiv HTML paper](https://arxiv.org/html/2510.19205v1).

### Research object and method

WebGraphEval converts textual action descriptions and URLs into canonical actions, merges them into weighted directed graphs, and aggregates multiple trajectories from different agents for each task. It applies reward propagation, success-weighted edge statistics, action-necessity annotation, path-optimality/step-inflation measures, graph complexity, and cross-agent behavioral analysis. The paper evaluates 4,768 trajectories from six agent frameworks on 812 WebArena tasks. It does not train an evaluator, but it does use LLM inference for action canonicalization, terminal-success judging, and necessity annotation.

**Does WebGraphEval study structural trajectory evaluation? `YES`.** Graph representation and structural analysis are central rather than incidental.

### Comparability with THIS_WORK

| Dimension | WebGraphEval | THIS_WORK | Equivalent? |
| --- | --- | --- | --- |
| Representation | Weighted action graph aggregated across trajectories | Fixed-dimensional structural features per trajectory | No |
| Target | Efficiency, redundancy, necessity, success-conditioned graph structure, strategy overlap | Expert Success, Looping, exploratory Side Effect labels | No |
| Evaluation unit | Task graph and agent profile, with constituent trajectories/actions | Individual trajectory | No |
| Benchmark/split | Different WebArena runs; no equivalent frozen split | AgentRewardBench official dev/test with frozen grouped development and blind-first heldout | No |
| Metric | Graph/edge statistics, success rate, path inflation, necessity, complexity | AP/AP lift, F1, and frozen task-group bootstrap evidence | No |
| Information access | Action text/URLs plus LLM canonicalization, success judging, and necessity labels | Frozen leak-safe trajectory morphology; no large semantic model for B2 | No |
| Training | No learned evaluator; LLM inference/annotation required | Lightweight frozen Logistic Regression candidates | No |
| Goal | Structural multi-path analysis, efficiency diagnosis, cross-agent comparison | Offline outcome-dimension prediction | Partly related, not equivalent |
| Blind-heldout protocol | No equivalent protocol | Frozen blind-first official heldout | No |

Comparability: `PARTIALLY_COMPARABLE`. WebGraphEval is the closest audited structural-evaluation analogue, but the strict numeric gate fails on target, unit, data/split, metric, access, training role, and protocol.

## WebStep verification

### Canonical identity

- title: *Where Did It Go Wrong? Process-Level Evaluation of Web Agents with Semantic State Tracking*;
- benchmark name: WebStep;
- authors: Jiwan Chung, JiHyuk Byun, Vibhav Vineet, Seon Joo Kim;
- year/status: 2026; COLM 2026;
- identifier/version: `arXiv:2606.15673`, v2 (4 August 2026);
- primary sources: [official arXiv record](https://arxiv.org/abs/2606.15673), [official arXiv HTML paper](https://arxiv.org/html/2606.15673v2), and [official project page](https://jiwanchung.github.io/webstep/).

### Research object and method

WebStep contains 1,800 task instances across ten deterministic self-hosted websites. Each site exposes a semantic MDP dual behind the GUI: agents receive GUI observations, while the environment records high-level semantic states and transitions. The evaluator requires no model training and derives terminal success, exploration success, execution success, information coverage, skill invocation, GUI/semantic step efficiency, and shared-state trajectory bifurcations deterministically from the semantic trace. Bifurcation analysis localizes wrong branches, delayed commits, and premature commits. Six existing agents are evaluated; their own models and APIs are not evaluator training.

**Does WebStep directly evaluate the same target/protocol as THIS_WORK? `NO`.**

### Comparability with THIS_WORK

| Dimension | WebStep | THIS_WORK | Equivalent? |
| --- | --- | --- | --- |
| Representation | Environment-instrumented semantic MDP states/actions | Lightweight fixed-dimensional trajectory morphology | No |
| Target | Exploration/execution process, skills, efficiency, and failure localization | Expert outcome dimensions: Success, Looping, exploratory Side Effect | No |
| Evaluation unit | Trajectory summaries plus step/skill/bifurcation diagnostics | Individual trajectory classification | No |
| Benchmark | Purpose-built WebStep sites and tasks | AgentRewardBench benchmark families | No |
| Metric | Terminal/exploration/execution SR, coverage, steps, skill/bifurcation distributions | AP/AP lift, F1, frozen bootstrap evidence | No |
| Training | No evaluator training | Lightweight frozen classifier training | No |
| Information access | Privileged semantic environment state recorded behind GUI | Frozen leak-safe trajectory structural fields | No |
| Evaluation role | Diagnose how and where existing agents fail | Predict offline trajectory-quality dimensions | No |
| Blind-heldout protocol | No equivalent protocol | Frozen blind-first official heldout | No |

Comparability: `CONTEXT_ONLY`. WebStep is a close process-evaluation context, but semantic-state diagnosis and failure localization are not the same target or protocol as lightweight structural outcome evaluation.

## “Similar” canonical identity resolution

- old label/title: `Similar` / *Evaluating and Advancing Multimodal Large Language Models as Step-wise Reward Models in AI Agents*;
- canonical title: *Boosting Virtual Agent Learning and Reasoning: A Step-Wise, Multi-Dimensional, and Generalist Reward Model with Benchmark*;
- authors: Bingchen Miao, Yang Wu, Minghe Gao, Qifan Yu, Wendong Bu, Wenqiao Zhang, Yunfei Li, Siliang Tang, Tat-Seng Chua, Juncheng Li;
- year: 2025;
- primary identifier: `PMLR:v267/miao25b; arXiv:2503.18665`;
- primary URL: [official PMLR proceedings](https://proceedings.mlr.press/v267/miao25b.html);
- citation key: `pmlr-v267-miao25b`;
- work ID: `similar_srm`;
- official repository: [antgroup/Similar](https://github.com/antgroup/Similar);
- resolution: `RESOLVED_CANONICAL_IDENTITY`.

PMLR, arXiv, and the official repository agree on the canonical paper title and authors. “Similar” is the proposed step-wise reward model name, which explains the old shorthand label. This is one existing work, so no duplicate citation was created. Its comparability remains `CONTEXT_ONLY`.

## Comparability and head-to-head recheck

| Class | Before | After |
| --- | ---: | ---: |
| `DIRECTLY_COMPARABLE` | 0 | 0 |
| `PARTIALLY_COMPARABLE` | 2 | 3 |
| `CONTEXT_ONLY` | 8 | 9 |
| `NOT_COMPARABLE` | 0 | 0 |

The only class changes are the additions: WebGraphEval is partial and WebStep is context-only. Similar's identity correction leaves its class unchanged.

Head-to-head before: `NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`.

Head-to-head after: `NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`.

No work simultaneously matches target, evaluation unit, benchmark/split, metric, information access, and evaluation role. The paper-facing table therefore remains an attribute comparison and not a performance leaderboard.

## Novelty and positioning patch

Before: “systematic study of lightweight structural trajectory signals,” scoped to AgentRewardBench.

After: **“lightweight fixed-dimensional structural signals for outcome-oriented web-agent trajectory evaluation under a frozen blind-held-out protocol.”**

The contract now explicitly separates THIS_WORK from WebGraphEval's cross-trajectory graph aggregation and WebStep's privileged semantic-MDP process diagnosis. It prohibits structural firstness, claims of outperforming either closest work, SOTA, LLM-judge replacement, unseen-benchmark generalization, and independent external validation.

## Citation and paper-facing patch

- citation registry: 8 -> 10 rows;
- BibTeX: 8 -> 10 entries;
- WebGraphEval and WebStep added from official primary metadata;
- Similar title canonicalized in place with the existing work ID and citation key;
- no DOI/pages/volume/publisher was guessed for WebGraphEval or WebStep;
- Markdown and LaTeX Related Work tables updated with canonical titles and attribute-only comparison;
- writing skeleton updated to trajectory/outcome, process/reward/step, structural/graph, and THIS_WORK categories.

## Files patched

- `artifacts/a3_2_verified_literature_registry.csv`
- `artifacts/a3_2_positioning_matrix.csv`
- `artifacts/a3_2_citation_registry.csv`
- `paper/references/a3_2_verified_related_work.bib`
- `docs/a3_2_positioning_and_novelty_contract.md`
- `paper/tables/Table_Related_Work_Positioning.md`
- `paper/tables/Table_Related_Work_Positioning.tex`
- `docs/a3_2_related_work_writing_skeleton.md`
- `artifacts/a3_2_addendum_closest_work_patch.csv`
- `artifacts/a3_2_addendum_run_summary.json`
- `docs/a3_2_closest_work_addendum_report.md`
- addendum verifier and dependency-light tests.

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
- `new_scientific_figures = 0`

## Verification and warnings

The independent addendum verifier checks commit reachability, A3.3 taskbook immutability, exact claim-matrix hash, frozen claim states, canonical identities, primary-source URLs, comparability counts, absence of a direct-comparison upgrade, citation/BibTeX key equality, canonical paper-facing names, patch-registry completeness, machine-summary hashes, zero counters, and changed-file scope.

Warnings/conditions:

1. WebGraphEval is verified from arXiv v1 and its stated NeurIPS 2025 workshop status; no proceedings DOI/pages were inferred.
2. WebStep is verified from arXiv v2, its COLM 2026 journal reference, and the official project page; code and dataset remain announced as coming soon.
3. The original A3.2 verifier remains a frozen baseline verifier with its preregistered five-work cap and eight-citation expectation; this addendum uses a separate verifier rather than rewriting that historical contract.

## A3.3 unblock recommendation

`A3_2_CLOSEST_WORK_ADDENDUM = PASS_WITH_CONDITIONS`

`A3_3_FORMAL_EXECUTION = AUTHORIZED`

`WAIT_FOR_HUMAN_A3_2_ADDENDUM_REVIEW`

STOP. Do not execute A3.3 in this run.
