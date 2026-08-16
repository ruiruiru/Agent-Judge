# Stage A2 Master Plan：Publication Completion Experiments

> 本文件是 A2 总体规划，不是一次性交给 Codex 执行的任务书。
>
> A2 必须按“小任务书 → 执行 → STOP → 人工审查 → 下一小节”的阶段门机制推进。

## 1. 总目标

A2 的唯一 KPI：

> 以 SCI 二/三区期刊投稿为目标，补齐现有 Agent-Judge 工作的论文完整度，而不是继续开放式寻找新模型或追求更高 test AP。

A1 已完成核心科学验证；A2 只做 publication completion。

## 2. Frozen claim contract

A1.11 final claim matrix SHA-256：

```text
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

A1.11 main test table SHA-256：

```text
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

Frozen claim identities：

```text
FC1 Success = CONFIRMATORY_SUPPORTED
FC2 Looping = CONFIRMATORY_SUPPORTED
FE1 Side Effect = EXPLORATORY_SUPPORTED
```

任何 A2 子阶段都不得修改以上 claim、scope、threshold、eligibility、final model 或 A1.10 confirmatory metrics。

## 3. A2 子阶段

### A2.1 — Efficiency & Cost Benchmark

目的：

> 把“lightweight”从定性描述变成可量化证据。

比较：

```text
B2 structural representation = 13 dimensions
B4 dense semantic representation = 1024 dimensions
```

测量：

- representation size；
- model size；
- extraction runtime；
- classifier inference runtime；
- CPU memory；
- GPU VRAM；
- cold/warm cost；
- B4/B2 relative cost ratio。

A2.1 完成后：

```text
STOP
WAIT_FOR_HUMAN_A2_1_REVIEW
```

不得自动执行 A2.2。

---

### A2.2 — Interpretability, Error Analysis & Confounder Audit

仅在 A2.1 人工通过后单独 preregister。

候选内容：

- frozen B2 coefficients；
- A1.5/A1.6 feature-group synthesis；
- deterministic Success / Looping FP/FN case analysis；
- metadata-only dev diagnostic baseline。

A2.2 完成后必须再次 STOP。

---

### A2.3 — Baseline Completeness & Paper Package

仅在 A2.2 人工通过后单独 preregister。

候选内容：

- baseline completeness matrix；
- paper-ready tables；
- publication figure specification；
- results story；
- external validation decision。

A2.3 完成后：

```text
READY_FOR_A3_PAPER_ARTIFACT_FREEZE
```

---

## 4. Optional external validation

独立 external benchmark/dataset 不是 A2 默认必做项。

只在 A2.3 决策：

```text
DO_NOW
DEFER_TO_REVISION
NOT_WORTH_COST
```

不得由 A2.1/A2.2 自动启动。

## 5. 全局禁止

整个 A2 禁止：

```text
修改 A1 final model
修改 A1 threshold
修改 eligibility
重算/替换 A1.10 confirmatory metrics
official-test tuning
根据 test error 修改模型
fusion
第二 embedding 模型搜索
大型 classifier search
新 LLM Judge 系统
为提升 official-test AP 增加新 feature
把 post-freeze diagnostic 升级为 confirmatory
```

## 6. 执行原则

A2 必须维持：

```text
一个小任务书
→ 独立 prereg commit
→ 单一明确执行目标
→ 独立 result commit
→ Git clean
→ STOP
→ 人工审查
```

不得跨子阶段连续执行。
