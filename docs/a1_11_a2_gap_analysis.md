# A1.11 A2 Gap Analysis

## Bottom line

The current evidence is sufficient to begin the manuscript body now: FC1 and FC2 have frozen blind held-out support, FE1 has an explicitly exploratory role, and the provenance and claim boundaries are auditable. The largest remaining evidence gap is external validity: there is no truly independent benchmark/dataset that can support an unseen-benchmark claim. A secondary gap is mechanism validity; current feature and ablation evidence is predictive rather than causal.

## MUST

- Begin the manuscript body using the A1.11 claim matrix as the binding claim contract.
- Preserve FC1/FC2 scope, FE1 exploratory status, all limitations, and the descriptive-only benchmark interpretation.
- Require a new approved Stage before any new experiment or claim expansion.

## SHOULD

- Design, but do not yet execute, a genuinely independent external benchmark/dataset validation if unseen-benchmark generalization is important to the paper's intended contribution.
- Design a lightweight mechanism-validation stage for the Success termination and Looping repetition signals, with explicit non-causal alternatives and preregistered tests.

## OPTIONAL

- Add a separately approved joint task/model OOD study if arbitrary-Agent robustness is central to the target venue.
- Add frozen-artifact error taxonomy or efficiency presentation that does not alter claims or rerun test inference.

## DO_NOT_PRIORITIZE

- Additional complex classifiers, fusion, larger or second embedding models, calibration, or an LLM Judge merely to chase score gains.
- New benchmarks or datasets without a preregistered external-validity question and stage gate.

## Recommendation

Start paper writing now. For A2 design review, prioritize independent external validation first and targeted mechanism validation second; do not prioritize additional model complexity.
