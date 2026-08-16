# A3.3 Related Work Integration Contract

Only citation keys in `artifacts/a3_2_citation_registry.csv` are permitted. No new search or uncatalogued citation may enter the manuscript.

| Paragraph role | Allowed citation keys | Allowed comparison wording | Forbidden comparison wording |
|---|---|---|---|
| Trajectory/outcome judges and benchmarks | `lu2025agentrewardbench`; `pmlr-v267-zhuge25a`; `lin2026cuarewardbench` | Different evaluation roles, targets, information access, and protocols; AgentRewardBench is partially comparable. | Numeric leaderboard; outperform; same protocol; independent external validation. |
| Process/reward/step evaluation | `chae2025webshepherd`; `xia-etal-2025-agentrm`; `zhang2026webarbiter`; `fan2026agentprocessbench`; `pmlr-v267-miao25b`; `chung2026did` | Context for learned reward, step/process, and semantic-state diagnosis; WebStep is context-only; Similar uses its canonical identity. | Equivalent target; direct head-to-head; replacement claim. |
| Structural/graph evaluation | `qian2025webgrapheval` | WebGraphEval is partially comparable and aggregates action graphs across trajectories; THIS_WORK uses per-trajectory fixed-dimensional morphology. | First structural evaluator; outperforms WebGraphEval; direct numeric comparison. |
| THIS_WORK positioning | all ten verified keys as needed | `lightweight fixed-dimensional structural signals for outcome-oriented web-agent trajectory evaluation under a frozen blind-held-out protocol` | Firstness; no prior work; nobody has studied; SOTA; LLM-judge replacement; unseen-benchmark generalization. |

`DIRECTLY_COMPARABLE = 0`

`NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`
