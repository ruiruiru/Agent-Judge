# D9-R1 科研总纲

## 1. 项目名称

**D9-R1：面向跨 Benchmark 泛化的维度感知轻量 Web Agent 轨迹裁判**

英文暂定名：

> **Dimension-Aware Lightweight Evaluation of Web-Agent Trajectories under Benchmark Shift**

---

## 2. 文档定位

本文件是 D9-R1 整个科研过程的总指引，用于约束：

- 研究问题；
- 核心假设；
- 实验边界；
- 数据和评价协议；
- 阶段门槛；
- 证据要求；
- 论文主张。

它不是最终论文，也不是一次性实现清单。后续每个阶段都应在本总纲之下单独编写 Codex 任务书，并由研究负责人批准后执行。

---

## 3. 总体科研原则

1. 先验证研究假设，再扩大模型、数据和工程规模。
2. 每个结论必须能追溯到数据版本、划分、配置、代码版本、随机种子和原始结果。
3. GPT 负责假设设计、协议审查、结果解释和对抗性评审。
4. Codex 只按冻结规格实施，不得擅自改变研究问题、标签、测试协议、主要指标或验收门槛。
5. 测试数据不得用于阈值、特征、模型或融合权重选择。
6. 所有负结果必须保存，不得只保留最佳结果。
7. 每个阶段结束必须给出 `GO / CONDITIONAL GO / NO-GO`。
8. 最终方向、创新点、阶段结论和论文主张由研究负责人批准。
9. 不以复杂模型本身作为创新。
10. 不为了使故事成立而移动实验门槛。

---

## 4. 研究背景

Web Agent 和工具调用 Agent 通过多步轨迹完成任务。轨迹通常包含：

- 用户任务；
- 页面或环境观察；
- Agent 动作；
- 工具调用和返回；
- 中间计划；
- 最终答案或环境状态。

仅看最终成功率不能完整反映轨迹质量。一条轨迹可能最终成功，但同时存在：

- 重复操作；
- 无效步骤；
- 意外副作用；
- 忽略用户限制；
- 低效率路径；
- 对特定 Benchmark 格式的依赖。

现有评价方式包括：

- 程序化规则；
- 人工评价；
- LLM-as-a-Judge；
- Agent-as-a-Judge；
- 轨迹级 Reward Model；
- 步骤级 Process Reward Model。

它们分别面临规则不灵活、人工昂贵、强模型成本高、长轨迹判断不稳定、跨 Benchmark 泛化不足和训练成本过高等问题。

D9-R1 不尝试建立新的大型 Benchmark，也不直接训练大型 PRM。项目聚焦：

> 利用公开专家标注轨迹，研究不同质量维度所需的评价证据是否存在系统差异，以及轻量裁判能否在未见 Benchmark 上保持有效评价。

---

## 5. 核心研究问题

### 5.1 主问题

> **Agent 轨迹的不同质量维度，是否依赖不同类型的结构与语义证据；针对不同标签选择证据的维度感知轻量裁判，能否比统一表示模型获得更好的跨 Benchmark 泛化？**

### 5.2 子问题

1. `Success`、`Side Effect` 和 `Repetitiveness/Looping` 的可学习性是否不同？
2. 哪些标签主要依赖结构信息，哪些主要依赖语义信息？
3. 结构特征和文本特征是否具有稳定互补价值？
4. 对所有标签使用统一表示，是否会产生多任务负迁移？
5. 在未见 Benchmark 上，轻量裁判是否仍优于 Majority 和简单规则？
6. 模型是否利用轨迹长度、Benchmark 身份或 Agent 身份等捷径？
7. 标签专属融合是否优于统一融合？

---

## 6. 核心假设与反证条件

### 6.1 核心假设 H1

> `Success`、`Side Effect` 和 `Repetitiveness/Looping` 对轨迹结构与语义信息的依赖存在系统性差异；标签专属的证据选择与融合，会比统一文本、统一结构或简单全量拼接方法获得更好的跨 Benchmark 泛化。

### 6.2 若 H1 成立，预期观察到

- `Repetitiveness/Looping` 对重复动作、连续相同动作、状态无变化等结构特征更敏感；
- `Success` 更依赖任务目标、动作语义和最终状态；
- `Side Effect` 更依赖用户约束与执行动作之间的语义关系；
- 不同标签的最佳输入视图或融合权重不同；
- 标签专属融合至少在两个标签上优于最佳单视图或统一融合；
- Leave-One-Benchmark-Out 中多数留出域仍优于 Majority；
- 去除 Benchmark ID、Agent ID 和纯长度特征后，主要结论仍成立。

### 6.3 反证条件

出现以下情况时，不得继续把 H1 当作已支持结论：

- 所有标签都由同一种特征视图取得最好结果；
- 结构与语义没有稳定互补作用；
- 标签专属融合不优于统一模型；
- 跨 Benchmark 测试全部接近 Majority；
- 性能主要由 Benchmark ID、Agent ID 或轨迹长度解释；
- 标签定义或样本量不足以支持统计结论；
- 结果仅在单一折、单一种子或单一 Benchmark 上成立。

---

## 7. 初始研究边界

### 7.1 初始数据

首选主数据：

- **AgentRewardBench**
- 约 1,302 条 Web Agent 轨迹；
- 多个 Web Agent Benchmark 来源；
- 专家轨迹评价标签。

初始候选标签：

1. `Success`
2. `Side Effect`
3. `Repetitiveness / Looping`

`Optimality` 只在数据审计阶段检查，是否纳入需人工批准。

### 7.2 预实验允许的方法

- Majority；
- 简单规则；
- Logistic Regression；
- TF-IDF；
- XGBoost、LightGBM 或 sklearn 树模型；
- 结构特征；
- 文本特征；
- 标签专属晚期融合；
- Bootstrap 置信区间；
- Task-grouped 划分；
- Leave-One-Benchmark-Out。

### 7.3 预实验禁止的方法

- GPT、Claude、Gemini 等付费 Judge；
- 强模型回退；
- Qwen 或 DeBERTa 微调；
- 大型多任务网络；
- 步骤级 PRM；
- 在线 WebArena；
- 自建大规模数据；
- 弱监督错误位置；
- 人工修改专家标签；
- 依据测试结果反复改特征；
- 只报告最好种子。

---

## 8. 候选研究贡献

以下贡献只有获得实验支持后才能写入论文。

### C1：维度差异分析

系统分析不同 Web Agent 轨迹评价维度对结构证据和语义证据的依赖差异。

### C2：维度感知轻量裁判

设计标签专属的证据选择或融合机制，而不是对所有标签使用同一种统一表示。

### C3：跨 Benchmark 泛化协议

采用 Task-grouped 与 Leave-One-Benchmark-Out 协议，评估 Benchmark Shift 下的可靠性。

### C4：捷径学习诊断

分析轨迹长度、Benchmark 身份、Agent 身份和格式模板对评价结果的影响。

### C5：可选可靠性增强

仅在主线成立后再考虑：

- 概率校准；
- 选择性预测；
- 强模型或人工复核；
- 错误类型诊断。

---

## 9. 整体科研阶段

### 阶段 0：研究问题冻结

目标：

- 确认问题、假设、反证条件和研究边界；
- 审查与最接近工作的差异；
- 确认三个月内可完成。

产物：

- 本科研总纲；
- 决策日志；
- 文献矩阵；
- Claim–Evidence 初始映射。

当前状态：**已批准进入阶段 1。**

### 阶段 1：数据与标签审计

检查：

- 样本量；
- 每个 Benchmark 样本量；
- 标签分布；
- 标签缺失和冲突；
- 相同 `task_id` 的多轨迹；
- 轨迹长度；
- 动作和观察字段；
- 截图依赖；
- Benchmark ID 与标签相关性；
- Agent ID 与标签相关性；
- 仅凭长度预测的风险。

产物：

```text
reports/data_audit.md
reports/data_audit.json
reports/label_distribution.csv
reports/benchmark_statistics.csv
reports/trajectory_schema.md
reports/leakage_risk.md
```

继续门槛：

- 至少两个目标标签具有足够正负样本；
- 可以按 `task_id` 分组；
- 至少三个 Benchmark 可用于跨域测试；
- 标签与字段可统一解析；
- 无无法修复的严重泄漏。

### 阶段 2：强而简单的信号基线

基线：

1. Majority；
2. 简单规则；
3. 结构特征 + LR/树模型；
4. TF-IDF + LR；
5. 统一拼接；
6. 标签专属晚期融合。

协议：

- Task-grouped CV；
- Leave-One-Benchmark-Out；
- Bootstrap 95% CI；
- 分标签、分 Benchmark 报告。

继续门槛：

- 至少两个标签具有稳定信号；
- 至少一个结构主导标签和一个语义主导标签；
- 多数留出域超过 Majority；
- 结论不是由单一来源驱动。

### 阶段 3：维度感知方法设计

仅在阶段 2 通过后进行。

候选：

- 标签专属特征门控；
- 标签专属融合权重；
- 共享骨干 + 标签适配器；
- 结构—语义双分支；
- 防止多任务负迁移的参数或损失设计。

要求：

- 每次只加入一种机制；
- 每个机制必须有对应消融；
- 主要价值必须在跨 Benchmark 条件下体现。

### 阶段 4：论文级验证

至少包括：

- 多随机种子；
- 置信区间；
- 统计显著性；
- 单任务与多任务比较；
- 结构、文本和融合消融；
- 标签专属与统一模型比较；
- Leave-One-Benchmark-Out；
- Leave-One-Agent-Out，如数据允许；
- 长度、Benchmark、Agent 身份捷径诊断；
- 错误分析；
- 成本、延迟和模型规模。

### 阶段 5：应用增强

主线成立后才考虑：

- 选择性人工复核；
- 选择性强 Judge；
- 弱监督错误定位；
- Retry/rollback；
- 在线 Agent 评价。

这些不得替代主线贡献。

### 阶段 6：论文冻结与投稿

要求：

- 代码、数据划分和主结果冻结；
- 所有表格可由脚本自动生成；
- 每个论文主张映射到结果文件；
- 完成支持性评审和拒稿式对抗评审；
- 明确报告局限与负结果；
- 不无依据声称 SOTA。

---

## 10. 评价协议

### 10.1 划分原则

禁止普通随机切分导致任务泄漏。

优先：

- `StratifiedGroupKFold`；
- 或 `GroupKFold`；
- 分组键为 `task_id`；
- 相同任务的不同轨迹必须进入同一折。

跨域：

- Leave-One-Benchmark-Out；
- 一个完整 Benchmark 作为测试域；
- 阈值和模型选择只能使用其余 Benchmark。

### 10.2 主要指标

每个标签：

- Positive-class F1；
- Macro-F1；
- PR-AUC；
- AUROC；
- Precision；
- Recall；
- Confusion Matrix；
- Bootstrap 95% CI。

整体：

- 标签平均 Macro-F1；
- 标签平均 PR-AUC；
- LOBO 平均；
- 每个 Benchmark 独立结果。

类别不平衡时，PR-AUC 与正类 F1 优先于 Accuracy。

### 10.3 阈值规则

- 阈值只在训练折内部验证集选择；
- 测试折不得参与选择；
- 多标签允许标签专属阈值；
- 所有阈值和融合权重必须保存。

---

## 11. 捷径学习诊断

至少包括：

1. 仅轨迹长度；
2. 仅 Benchmark ID；
3. 仅 Agent ID；
4. 仅任务文本；
5. 去除长度相关特征；
6. 去除 Benchmark 和 Agent 身份信息；
7. 各 Benchmark 标签基率比较；
8. 错误样本按来源分析。

如果身份或长度基线接近完整模型：

- 不得声称模型学习了轨迹质量；
- 必须重新设计协议或收缩结论。

---

## 12. 研究角色分工

### 研究负责人

负责：

- 批准方向；
- 冻结假设；
- 批准 Codex 任务；
- 查看原始结果；
- 作出阶段决策；
- 批准论文主张。

### GPT

负责：

- 将问题转化为可证伪假设；
- 审查文献；
- 设计协议、基线、消融和门槛；
- 基于原始结果解释；
- 进行对抗性评审；
- 不替代证据下结论。

### Codex

负责：

- 按任务书下载和解析数据；
- 实现指定代码；
- 运行指定实验；
- 保存配置、日志、预测和结果；
- 不擅自改变标签、划分、指标与目标；
- 遇到不明确字段时停止并记录，不猜测。

---

## 13. 项目目录建议

```text
d9-r1/
├─ README.md
├─ research/
│  ├─ 00_RESEARCH_CHARTER.md
│  ├─ 01_DECISION_LOG.md
│  ├─ 02_EXPERIMENT_REGISTRY.csv
│  ├─ 03_CLAIM_EVIDENCE_MAP.md
│  └─ 04_REVIEW_CHECKLIST.md
├─ configs/
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ splits/
├─ src/
│  ├─ data/
│  ├─ features/
│  ├─ models/
│  └─ evaluation/
├─ scripts/
├─ runs/
├─ reports/
├─ tests/
└─ requirements.txt
```

---

## 14. 可复现要求

每次运行必须记录：

- `run_id`
- `hypothesis_id`
- `git_commit`
- `data_version`
- `split_version`
- `config_path`
- `random_seed`
- `model`
- `hardware`
- `start_time`
- `end_time`
- `primary_metrics`
- `output_path`
- `status`
- `notes`

每个正式运行目录至少包含：

```text
config.yaml
command.txt
environment.txt
metrics.json
predictions.csv
stdout.log
summary.md
```

---

## 15. 阶段决策规则

### GO

- 核心指标达到预设门槛；
- 多折或多种子稳定；
- 强简单基线被稳定超过；
- 无严重泄漏或捷径；
- 存在清晰的下一步研究问题。

### CONDITIONAL GO

- 存在可学习信号；
- 但跨域、标签覆盖或稳定性不足；
- 需要缩小论文主张或修改非核心实现。

### NO-GO

- 核心假设不受支持；
- 数据或标签无法支撑；
- 结果由泄漏或捷径驱动；
- 简单强基线无法被稳定超过；
- 继续研究需要更换核心问题。

---

## 16. 风险清单

### R1：标签不平衡

应对：

- 正类 F1 和 PR-AUC；
- 类别权重；
- Bootstrap CI；
- 不把过采样当作新信息。

### R2：数据规模小

应对：

- 简单模型优先；
- Grouped CV；
- 多折和置信区间；
- 不过度微调大型网络。

### R3：Benchmark Shift 过强

应对：

- 将其作为研究现象；
- 分析来源差异；
- 不强行宣称通用 Judge；
- 必要时收缩为 Benchmark Shift 与捷径学习研究。

### R4：标签语义不同

应对：

- 标签专属视图；
- 单任务与多任务对照；
- 不预设所有标签共享同一种表示。

### R5：创新性不足

应对：

- 核心放在维度差异、跨 Benchmark 泛化和捷径诊断；
- 不把普通分类器本身作为创新；
- 最终方法必须由预实验发现驱动。

---

## 17. 论文结构候选

1. Introduction
2. Related Work
3. Problem Definition
4. Dataset and Evaluation Protocol
5. Evidence-Dimension Analysis
6. Dimension-Aware Lightweight Judge
7. Experiments
8. Cross-Benchmark and Shortcut Analysis
9. Error Analysis
10. Efficiency and Limitations
11. Conclusion

该结构在阶段 3 后再正式冻结。

---

## 18. 当前状态

```text
方向：D9-R1
状态：APPROVED FOR MINIMUM PILOT
核心假设：H1
当前阶段：阶段 1，数据审计与最小信号验证
是否允许复杂模型：否
是否允许在线 Web 环境：否
是否允许强 Judge 回退：否
下一决策点：最小预实验完成后
```

---

## 19. 主要参考入口

- AgentRewardBench
  - https://arxiv.org/abs/2504.08942
  - https://agent-reward-bench.github.io/
  - https://github.com/McGill-NLP/agent-reward-bench
  - https://huggingface.co/datasets/McGill-NLP/agent-reward-bench
- Web-Shepherd
  - https://arxiv.org/abs/2505.15277
- Agent-RewardBench
  - https://aclanthology.org/2025.acl-long.857/
- AgentRM
  - https://aclanthology.org/2025.acl-long.945/
- Plan-RewardBench
  - https://arxiv.org/abs/2604.08178

这些入口用于确定研究边界，不替代后续正式文献核验。
