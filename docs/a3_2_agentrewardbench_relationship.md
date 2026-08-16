# A3.2 AgentRewardBench Relationship Contract

## 1. Original research object

AgentRewardBench constructs and expert-validates a benchmark for evaluating automatic judgments of complete web-agent trajectories. Its benchmark has three binary dimensions—success, side effects, and repetition—and its paper evaluates prompted LLM judges and a rule-based success signal against expert labels. The canonical primary records are the [COLM 2025 OpenReview page](https://openreview.net/forum?id=fQcUZMPIvu) and [arXiv:2504.08942](https://arxiv.org/abs/2504.08942).

## 2. What THIS_WORK reuses

THIS_WORK reuses the released AgentRewardBench trajectory data, expert labels, target meanings, source-benchmark identities, and official 196-development / 1106-test split. It does not modify expert labels. The official test portion was used only after the separately frozen blind-inference and unlock sequence recorded in earlier project stages.

## 3. What THIS_WORK does not reuse

THIS_WORK does not reuse the original paper's prompted LLM-judge outputs as its model, does not train an LLM/VLM reward model, and does not treat the original rule-based success signal as its final evaluator. It does not create new expert annotations, source tasks, or benchmark families.

## 4. Added research question

The added question is whether lightweight, task-agnostic structural representations can support dimension-aware trajectory evaluation under benchmark shift, and what their frozen held-out behavior, efficiency, and interpretability boundaries look like. This differs from comparing prompted LLM judges on the benchmark, although both studies share the same underlying data and labels.

## 5. Why this is not a simple rerun

The project preregistered grouped development protocols, lightweight structural candidate families, frozen selection rules, blind-first official-test execution, confidence intervals, efficiency measurements, and structural diagnostics. Those are distinct methods and estimands from the original paper's judge comparison. The distinction supports a separate evaluator study, not a new benchmark claim.

## 6. External-validity limit created by shared data

Using AgentRewardBench data means the result is evidence within that benchmark and its represented source families. It is not independent external validation of AgentRewardBench, and it does not establish performance on a newly collected external benchmark. THIS_WORK does not create a new benchmark.

The required boundary is:

```text
blind held-out within evaluated benchmark families
!=
independent external benchmark validation
```

## 7. What the official blind held-out can and cannot show

It can show that, under the frozen protocol, model and threshold choices were made without accessing the official held-out labels and that the final estimators were evaluated on previously unopened examples from the represented benchmark families.

It cannot show independent external benchmark validation, transfer to unseen benchmark families, or generalization to arbitrary web-agent distributions. Therefore paper text must use “official blind held-out within the evaluated benchmark families” and must not use “generalizes to unseen benchmarks.”

## Frozen paper-facing conclusion

AgentRewardBench is both the data source and the closest trajectory-judge context. Its relationship to THIS_WORK is `PARTIALLY_COMPARABLE`: dataset, split, targets, and trajectory unit overlap, but method role, information access, model scale, and primary evaluation framing differ. No cross-paper numeric ranking is authorized.
