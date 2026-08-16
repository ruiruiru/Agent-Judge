# A3.2 Positioning and Novelty Contract

## Frozen positioning

Within the studied AgentRewardBench setting, THIS_WORK studies **lightweight fixed-dimensional structural signals for outcome-oriented web-agent trajectory evaluation under a frozen blind-held-out protocol**. It predicts expert Success, Looping, and Side Effect labels from trajectory morphology, with Side Effect remaining exploratory. The contribution is a systematic structural-evidence study with efficiency and interpretability characterization, not a new benchmark, graph evaluator, semantic process environment, LLM judge, reward model, or process-reward training method.

Evidence status remains frozen:

- Success: `CONFIRMATORY_SUPPORTED`
- Looping: `CONFIRMATORY_SUPPORTED`
- Side Effect: `EXPLORATORY_SUPPORTED`

## Allowed wording

Paper text may use the following formulations, with the stated scope:

- “a systematic study of lightweight structural trajectory signals”;
- “a blind-first frozen held-out evaluation within the evaluated AgentRewardBench families”;
- “cost and interpretability characterization of the frozen lightweight evaluators”;
- “a task-agnostic structural representation within the studied benchmark setting”;
- “dimension-aware structural evidence differs across Success, Looping, and exploratory Side Effect evaluation.”

These formulations describe the frozen project evidence. They do not establish priority over all prior work or external generalization.

## Prohibited wording

The following claims are frozen as prohibited because the primary-source audit and project evidence do not support them:

- “first automatic evaluator for agents”
- “first web-agent trajectory evaluator”
- “first reward model for web agents”
- “state of the art”
- “outperforms LLM judges”
- “replaces LLM judges”
- “generalizes to unseen benchmarks”
- “first process-aware evaluator”
- “first structural web-agent evaluator”
- “first trajectory-structure evaluator”
- “outperforms WebGraphEval”
- “outperforms WebStep”
- “unseen-benchmark generalization”

Also prohibited are “new benchmark,” “independent external validation,” and any conversion of Side Effect from exploratory to confirmatory.

## Numeric-comparison contract

Only `DIRECTLY_COMPARABLE` work could enter a paper-facing numeric head-to-head. The verified registry contains zero such works. The frozen status is:

`NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`

Related Work and the positioning table must therefore compare attributes, problem roles, access, and evaluation units—not performance numbers across papers.

## WebGraphEval boundary

WebGraphEval is `PARTIALLY_COMPARABLE` and does study structural trajectory evaluation (`YES`). It canonicalizes action descriptions and URLs, aggregates 4,768 trajectories from six agents into per-task weighted action graphs, and analyzes success-conditioned edges, reward propagation, necessity, redundancy, path inflation, graph complexity, and cross-agent strategies. Its evaluation object is therefore structurally close to THIS_WORK.

The numerical protocols are not equivalent. WebGraphEval aggregates multiple WebArena trajectories into graph- and agent-level analyses; it does not predict AgentRewardBench expert dimensions for individual held-out trajectories. It uses LLM inference for action canonicalization, terminal-success judgment, and necessity annotation; uses different trajectories and no equivalent frozen split; reports graph, efficiency, and behavioral statistics; and does not implement THIS_WORK's blind-first held-out protocol. It cannot enter a numeric head-to-head with THIS_WORK.

## WebStep boundary

WebStep is `CONTEXT_ONLY` and does not evaluate the same target/protocol as THIS_WORK (`NO`). Its purpose-built deterministic websites expose a semantic MDP dual that records high-level states and transitions behind the GUI. Terminal, exploration, and execution success, information coverage, skill invocation, step efficiency, and trajectory bifurcations are derived from those semantic traces without manual or model-based process judgment.

This is semantic-state process diagnosis and failure localization, not lightweight structural outcome-label prediction. WebStep uses a different benchmark, environment instrumentation, state representation, unit mix, metrics, and evaluation role; it evaluates existing agent policies rather than training an offline trajectory-label classifier; and it has no equivalent AgentRewardBench blind-heldout protocol. It therefore provides process-evaluation context, not a cross-paper performance baseline.

## Closest-work boundary

AgentRewardBench, CUARewardBench, and WebGraphEval are `PARTIALLY_COMPARABLE`. WebStep and the remaining paper-facing works are `CONTEXT_ONLY`. The canonical paper represented previously by the label “Similar” is *Boosting Virtual Agent Learning and Reasoning: A Step-Wise, Multi-Dimensional, and Generalist Reward Model with Benchmark* and remains `CONTEXT_ONLY`.

Shared structure language or similar metrics do not override differences in dataset, split, target, unit, semantic access, training data, reward/judge role, or test-time usage. The updated verified registry still contains zero `DIRECTLY_COMPARABLE` works, so `NO_VALID_CROSS_PAPER_HEAD_TO_HEAD` remains frozen.
