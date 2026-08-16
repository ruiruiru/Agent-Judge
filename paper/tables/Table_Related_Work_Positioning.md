# Related-Work Positioning

This is an attribute comparison, not a performance leaderboard. `NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`.

| Work | Evaluation level | Web-specific | Signal type | Task-agnostic | Large semantic model required | Training required | Primary use | Directly comparable? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AgentRewardBench | Trajectory | Yes | Expert dimensions + prompted judge outputs | Within five web families | Yes for judges | No dedicated judge training | Benchmark and judge evaluation | No — partial only |
| Agent-as-a-Judge | Requirement + task | No, code agents | Agentic judgments | No | Yes | No dedicated reward training | Evaluate generated code/workspaces | No — context only |
| CUARewardBench | Trajectory + key step | Yes, computer use | Outcome/process reward | Within OSWorld | Yes | Yes for proposed models | Benchmark reward models | No — partial only |
| Web-Shepherd | Step + search trajectory | Yes | Process reward | Across selected web tasks | Yes | Yes | Guide web-agent search | No — context only |
| AgentRM | Trajectory candidate | Partly | Reward score | Across heterogeneous tasks | Yes | Yes | Best-of-N / beam selection | No — context only |
| WebArbiter | Step + search trajectory | Yes | Reasoned process reward | Across selected web tasks | Yes | Yes | Rank actions and guide search | No — context only |
| AgentProcessBench | Step | Partly | Human ternary process labels | Across four tool-agent datasets | Yes for judges | No for benchmark | Diagnose process errors | No — context only |
| Boosting Virtual Agent Learning and Reasoning: A Step-Wise, Multi-Dimensional, and Generalist Reward Model with Benchmark | Step and dimension | Partly | Multidimensional reward | Across virtual-agent platforms | Yes | Yes | Train/evaluate Similar step reward models | No — context only |
| WebGraphEval: Multi-Turn Trajectory Evaluation for Web Agents using Graph Representation | Cross-multi-trajectory graph | Yes | Weighted action graph + success/necessity annotations | WebArena tasks across six agents | Yes for annotations | No evaluator training | Structural, efficiency, and cross-agent analysis | No — partial only |
| Where Did It Go Wrong? Process-Level Evaluation of Web Agents with Semantic State Tracking (WebStep) | Trajectory + step/skill | Yes | Deterministic semantic-MDP trace | Ten self-hosted WebStep sites | No model-based evaluator | No evaluator training | Process diagnosis and failure localization | No — context only |
| THIS_WORK | Trajectory | Yes within studied families | Lightweight structural label prediction | Within studied benchmark setting | No | Yes, lightweight frozen candidates | Offline dimension-aware evaluation | Self; no external direct match |

Notes: This remains an attribute comparison only, not a performance leaderboard. THIS_WORK reuses AgentRewardBench data and therefore is not an independent external validation. Side Effect remains exploratory. Blank bibliographic fields and version limitations are recorded in the citation and literature registries.
