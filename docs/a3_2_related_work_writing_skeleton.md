# A3.2 Related Work Writing Skeleton

This file is a citation-constrained skeleton, not manuscript prose. It follows the targeted closest-work addendum and permits attribute comparison only.

## A. Trajectory / outcome evaluators

Claim bullets:

- AgentRewardBench defines expert Success, Side Effect, and Repetition labels for complete web-agent trajectories and evaluates automatic LLM judges.
- Agent-as-a-Judge is an active agentic evaluator for code-agent requirement completion with richer workspace access.
- CUARewardBench jointly studies outcome and process reward models for screenshot-based computer-use agents.
- THIS_WORK reuses AgentRewardBench data; this is not an independent external benchmark and not new benchmark construction.

Citation keys: `lu2025agentrewardbench`, `pmlr-v267-zhuge25a`, `lin2026cuarewardbench`.

Allowed wording: “closest outcome-evaluation contexts,” “partially comparable,” “different information access and evaluation units.”

Forbidden wording: “outperforms LLM judges,” “new benchmark,” “independent external validation,” or any cross-paper numeric ranking.

## B. Process / reward / step-level evaluators

Claim bullets:

- Web-Shepherd and WebArbiter train web-specific step reward models and use them for candidate-action assessment or reward-guided search.
- AgentRM uses reward modeling to select trajectories at test time across heterogeneous agent tasks.
- AgentProcessBench diagnoses human-labeled step effectiveness and error propagation.
- *Boosting Virtual Agent Learning and Reasoning: A Step-Wise, Multi-Dimensional, and Generalist Reward Model with Benchmark* proposes the model Similar and studies trained multimodal step-wise reward modeling across five dimensions for virtual agents.
- *Where Did It Go Wrong? Process-Level Evaluation of Web Agents with Semantic State Tracking* introduces WebStep, whose semantic MDP traces support exploration/execution metrics, skill analysis, and trajectory bifurcation diagnosis without a trained evaluator.
- WebStep is semantic-state process diagnosis in a purpose-built environment, not outcome-label prediction from lightweight trajectory morphology.

Citation keys: `chae2025webshepherd`, `xia-etal-2025-agentrm`, `zhang2026webarbiter`, `fan2026agentprocessbench`, `pmlr-v267-miao25b`, `chung2026did`.

Allowed wording: “contextual comparison,” “step-level process reward,” “semantic-state process diagnosis,” “failure localization,” “test-time search role.”

Forbidden wording: “replaces PRMs,” “outperforms WebStep,” “first process-aware evaluator,” or numeric head-to-head claims.

## C. Structural / graph / trajectory-analysis approaches

Claim bullets:

- *WebGraphEval: Multi-Turn Trajectory Evaluation for Web Agents using Graph Representation* aggregates canonicalized actions from many WebArena trajectories into weighted action graphs.
- WebGraphEval uses reward propagation, success-weighted edge statistics, necessity labels, path inflation, redundancy, and graph complexity for structural and cross-agent analysis.
- This makes WebGraphEval the closest audited structural-evaluation analogue and `PARTIALLY_COMPARABLE`, but not directly comparable: it aggregates different WebArena runs, relies on LLM annotations, reports graph/efficiency analyses, and has no equivalent AgentRewardBench split or blind-first protocol.

Citation key: `qian2025webgrapheval`.

Allowed wording: “structural trajectory evaluation,” “graph-based multi-path analysis,” “closest structural analogue,” “partially comparable.”

Forbidden wording: “first structural web-agent evaluator,” “first trajectory-structure evaluator,” “outperforms WebGraphEval,” or any performance leaderboard.

## D. THIS_WORK positioning

Claim bullets:

- Freeze the contribution as **lightweight fixed-dimensional structural signals for outcome-oriented web-agent trajectory evaluation under a frozen blind-held-out protocol** within the studied AgentRewardBench setting.
- Distinguish single-trajectory expert-label prediction from WebGraphEval's cross-trajectory graph aggregation and WebStep's instrumented semantic-state process diagnosis.
- State Success and Looping as confirmatory and Side Effect as exploratory.
- Mention cost and interpretability characterization without implying semantic-model superiority.
- State `NO_VALID_CROSS_PAPER_HEAD_TO_HEAD` internally; translate in prose as “we do not report a cross-paper performance ranking because no audited work met the comparability gate.”

Citation keys: cite the relevant prior-work keys above and the project's frozen evidence artifacts; do not invent an external citation for internal results.

Allowed wording: “systematic study of lightweight fixed-dimensional structural trajectory signals,” “task-agnostic structural representation within the studied benchmark setting,” “blind-first frozen held-out evaluation.”

Forbidden wording: “state of the art,” “generalizes to unseen benchmarks,” “independent external validation,” any firstness claim, or upgrading exploratory evidence.
