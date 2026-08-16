# A3.2 Verified Related-Work Taxonomy

Cutoff: `2026-08-14`. This taxonomy is bounded, primary-source verified, and not an exhaustive survey.

## A. Outcome and trajectory evaluators

- **AgentRewardBench** (`PARTIALLY_COMPARABLE`) constructs expert labels for success, side effects, and repetition over full web-agent trajectories and evaluates automatic LLM judges. THIS_WORK uses this dataset but studies frozen lightweight structural evaluators rather than prompted judges.
- **Agent-as-a-Judge** (`CONTEXT_ONLY`) uses an active agentic evaluator with workspace/code access to judge hierarchical requirements for code-generation agents. Its evaluation domain, access, unit, and metric differ.
- **CUARewardBench** (`PARTIALLY_COMPARABLE`) evaluates trajectory-level outcome reward models and key-step process reward models for screenshot-based computer-use agents. Its OSWorld data, VLM access, mixed unit, and precision/NPV framing prevent direct comparison.

## B. Reward models and step/process verification

- **Web-Shepherd** (`CONTEXT_ONLY`) trains web process reward models on step preferences/checklists and uses rewards for guided search.
- **AgentRM** (`CONTEXT_ONLY`) trains a reward model to select agent rollouts through Best-of-N or beam search across heterogeneous tasks.
- **WebArbiter** (`CONTEXT_ONLY`) trains a reasoning-first web process reward model for candidate-action ranking and reward-guided search.
- **AgentProcessBench** (`CONTEXT_ONLY`) provides human ternary step-effectiveness labels and first-error diagnostics across tool-agent datasets.
- **Similar** (`CONTEXT_ONLY`) trains multimodal step-wise reward models over five process dimensions in virtual-agent environments.
- **AgentPRM** and **ToolPRMBench** were primary-source reviewed but excluded from the five-work paper-facing addition cap. They remain in the registry as context-only step/process works.

## C. THIS_WORK

THIS_WORK is a systematic study of lightweight, dimension-aware structural signals for full-trajectory classification within the AgentRewardBench setting. It uses frozen expert labels and a blind-first held-out protocol; Success and Looping are confirmatory, while Side Effect remains exploratory. It includes efficiency and interpretability characterization without adding new models or results in A3.2.

## Boundary map

- An **LLM judge** consumes semantic trajectory content and is prompted or deployed to make an evaluation judgment. THIS_WORK's final candidates are lightweight trained estimators over frozen structural representations.
- A **reward model** supplies a scalar or preference signal to rank policy outputs. THIS_WORK reports offline trajectory-label prediction and is not used to optimize or select agent actions.
- A **process reward model (PRM)** scores intermediate steps and often guides test-time search. THIS_WORK's evaluation unit is the complete trajectory and A3.2 performs no search or inference.
- **Benchmark construction** creates or curates tasks/labels. THIS_WORK reuses AgentRewardBench and makes no new benchmark claim.
- A **task-specific rule evaluator** encodes environment-specific success conditions. THIS_WORK studies task-agnostic structural representation within the evaluated setting, although that scope does not imply unseen-benchmark generalization.

## Comparability outcome

No audited work satisfies the full same-task, same-target, same-unit, same-split, compatible-metric, and compatible-information-access gate. Consequently:

`NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`
