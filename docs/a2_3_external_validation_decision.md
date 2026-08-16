# A2.3 External Validation Decision

## Decision

`DEFER_TO_REVISION`

## Rationale

An independent public dataset could materially address the strongest remaining external-validity criticism, but the current local record does not yet verify compatible Success labels, trajectory availability, immutable revision/license terms, or direct reuse of the frozen 13-feature extractor. Establishing those facts requires a new data-contract and adapter stage. The current A1/A2 evidence already supports a bounded submission story, so performing that work now would create material schedule and scope risk.

## Decision factors

| Factor | Current assessment |
|---|---|
| Label compatibility | Not yet verified; a new explicit mapping audit is required. |
| Trajectory availability | Candidate literature entry points exist, but usable trajectory fields are not locally verified. |
| Extractor reuse | Plausible but unverified; no claim of zero-adapter reuse. |
| Adapter cost | Potentially material because field semantics and termination/error structure must be audited. |
| Scientific value | High for independent-dataset external validity if a compatible source is found. |
| Submission delay | Likely non-trivial relative to the already complete bounded evidence story. |
| Scope gain | Would test transfer to another dataset/annotation policy; it would not automatically establish universal generalization. |

## Publication value

The primary value is a direct response to reviewer concern that all current evidence comes from one dataset and its evaluated benchmark families. A clean compatible validation could strengthen external validity in a revision.

## Implementation cost

A new stage would need source/revision/license freezing, label-contract audit, trajectory-schema audit, leakage review, extractor compatibility tests, a frozen adapter if necessary, and a preregistered evaluation protocol. None is authorized or executed in A2.3.

## Scientific risks

- Incompatible label semantics could make the result uninterpretable.
- Missing or transformed trajectories could prevent faithful 13-feature extraction.
- Adapter choices could inadvertently change the frozen method.
- A rushed validation could encourage test-driven mapping or unsupported cross-paper comparisons.

## Reviewer criticism addressed

If executed cleanly, it would address the criticism that current held-out evidence is confined to AgentRewardBench and its covered benchmark families.

## What it would NOT prove

It would not by itself prove arbitrary unseen-benchmark generalization, arbitrary-agent generalization, joint task/model OOD robustness, universal Agent Judge validity, universal replacement of LLM judges, calibration, deployment safety, or causal mechanisms.

## Revisit trigger

Revisit after submission or reviewer request if a public source has: a fixed revision/license, accessible trajectories, a highly compatible Success label, direct or lightweight-adapter compatibility with the frozen extractor, and a separately approved preregistration that forbids method changes and tuning.

No external dataset was downloaded, adapted, or evaluated in A2.3.
