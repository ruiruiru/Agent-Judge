# D9-R1 最小预实验执行任务书

## 1. 交付对象

本任务书交给 Codex 执行。

项目方向：

> **D9-R1：面向跨 Benchmark 泛化的维度感知轻量 Web Agent 轨迹裁判**

本任务是最小预实验，不是完整论文实现。

---

## 2. 总体目标

本任务只验证一个问题：

> **Agent 轨迹的结构信号与文本语义信号，是否对不同评价标签呈现不同、可重复的贡献，并在未见 Benchmark 上保留一定泛化能力？**

本任务不要求提出最终模型，不要求超过最强 LLM Judge，也不允许进入复杂神经模型。

---

## 3. 核心假设

### H1

`Success`、`Side Effect` 和 `Repetitiveness/Looping` 对结构与语义证据的依赖不同。

预期：

- `Repetitiveness/Looping` 更依赖结构特征；
- `Success` 更依赖任务和轨迹语义；
- `Side Effect` 可能需要结构与语义共同作用；
- 标签专属融合优于统一固定融合或至少表现出不同最优权重。

### 反证条件

若出现以下情况，不得进入复杂模型：

- 所有标签都由同一种输入取得最好结果；
- 结构与文本没有稳定互补作用；
- Leave-One-Benchmark-Out 全部接近 Majority；
- 模型主要依赖 Benchmark ID、Agent ID 或轨迹长度；
- 标签和字段无法可靠解析。

---

## 4. 强制原则

1. 先完成数据审计。审计门槛未通过时立即停止，不训练模型。
2. 不覆盖原始数据。
3. 不修改专家标签。
4. 不使用普通随机切分造成 `task_id` 泄漏。
5. 测试折不得参与阈值、融合权重、特征或模型选择。
6. 所有运行必须保存配置、日志、预测、指标和环境信息。
7. 不只报告最好结果。
8. 不新增 GPT、Claude、Gemini 等 API 调用。
9. 不训练或微调 Qwen、DeBERTa、MiniLM 等神经模型。
10. 不擅自添加新标签或删除表现不好的标签。
11. 不运行 WebArena、BrowserGym 或在线浏览器环境。
12. 字段不明确时记录问题，不猜测。
13. 阶段门槛未通过时，不得继续堆模型。
14. 不声称 SOTA。

---

## 5. 数据来源

优先使用官方 AgentRewardBench：

- GitHub：`https://github.com/McGill-NLP/agent-reward-bench`
- Hugging Face：`https://huggingface.co/datasets/McGill-NLP/agent-reward-bench`

要求：

- 记录下载日期；
- 记录 Git commit 或数据 revision；
- 对关键原始文件计算 SHA256；
- 原始文件只读保存；
- 处理后数据单独版本化。

目录：

```text
data/
├─ raw/agent_reward_bench/
├─ processed/v1/
└─ splits/v1/
```

---

## 6. 建议工程目录

```text
d9-r1/
├─ README.md
├─ configs/
│  └─ pilot.yaml
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ splits/
├─ src/
│  ├─ data/
│  │  ├─ loader.py
│  │  ├─ schema.py
│  │  └─ parser.py
│  ├─ features/
│  │  ├─ structural.py
│  │  └─ text.py
│  ├─ models/
│  │  ├─ baselines.py
│  │  └─ fusion.py
│  └─ evaluation/
│     ├─ metrics.py
│     ├─ bootstrap.py
│     └─ protocols.py
├─ scripts/
│  ├─ download_data.py
│  ├─ audit_data.py
│  ├─ build_processed_dataset.py
│  ├─ run_grouped_cv.py
│  ├─ run_lobo.py
│  ├─ run_shortcut_baselines.py
│  └─ build_pilot_report.py
├─ tests/
├─ runs/
└─ reports/
```

优先复用官方字段定义，不重新发明标签解释。

---

# 阶段 A：数据下载与审计

## 7. 基本规模审计

输出：

- 总轨迹数；
- 唯一 `task_id` 数；
- Benchmark 数；
- Agent/model 来源数；
- 每个 Benchmark 样本量；
- 每个 Agent/model 来源样本量。

---

## 8. 标签审计

对每个候选标签输出：

- 官方字段名；
- 数据类型；
- 唯一值；
- 缺失数量；
- 正类数量；
- 负类数量；
- 正类比例；
- 按 Benchmark 的标签分布；
- 按 Agent/model 的标签分布。

初始候选：

- `Success`
- `Side Effect`
- `Repetitiveness/Looping`
- `Optimality` 仅审计，不自动进入训练。

如果字段名不同，必须生成：

```text
reports/label_mapping.md
```

内容：

```text
研究标签 -> 官方字段 -> 值映射 -> 依据
```

不得自行猜测标签值。

---

## 9. 轨迹字段审计

确认是否可读取：

- 任务描述；
- `task_id`；
- Benchmark ID；
- Agent/model ID；
- 动作序列；
- 观察序列；
- 工具返回；
- 最终答案或最终状态；
- 截图；
- 轨迹步数；
- 终止原因。

处理后的统一 Schema：

```text
trajectory_id
task_id
benchmark_id
agent_id
task_text
steps[]
final_text
labels{}
metadata{}
```

每个 `step` 至少尽量标准化为：

```text
step_index
observation
action
tool_result
metadata
```

无法映射的字段必须记录。

---

## 10. 重复与泄漏审计

检查：

- 完全重复轨迹；
- 完全重复任务；
- 同一 `task_id` 的多轨迹；
- 相同任务文本但不同 `task_id`；
- 不同 Benchmark 是否共享任务；
- 可能的重复最终状态；
- 同一任务是否由不同 Agent 产生多条轨迹。

重点确认：

> 相同任务的多条轨迹必须进入同一数据折。

---

## 11. 长度与格式审计

统计：

- 每条轨迹步数；
- 总字符数；
- 总词数或近似 token 数；
- 每步 observation 长度；
- 每步 action 长度；
- 不同 Benchmark 的长度分布；
- 极端长轨迹；
- 空轨迹；
- 解析失败比例；
- 截图依赖比例。

---

## 12. 标签与来源相关性风险

检查：

- 每个 Benchmark 的标签基率；
- 每个 Agent/model 的标签基率；
- 步数与标签关系；
- 文本长度与标签关系；
- 仅用 Benchmark ID 是否可预测标签；
- 仅用 Agent ID 是否可预测标签；
- 仅用步数或总长度是否可预测标签。

此处只做初步风险诊断，不作为正式主结果。

---

## 13. 阶段 A 产物

必须生成：

```text
reports/data_audit.md
reports/data_audit.json
reports/label_mapping.md
reports/trajectory_schema.md
reports/benchmark_statistics.csv
reports/agent_statistics.csv
reports/label_distribution.csv
reports/length_statistics.csv
reports/duplicate_and_leakage_audit.md
reports/parsing_failures.csv
data/processed/v1/trajectories.parquet
data/processed/v1/data_manifest.json
```

`data_manifest.json` 至少包含：

- 数据来源；
- 下载时间；
- revision/commit；
- 原始文件 SHA256；
- 处理脚本；
- 处理后样本数；
- 解析失败数；
- 字段映射；
- 数据版本。

---

## 14. 阶段 A 门槛

只有同时满足以下条件才进入阶段 B：

1. 至少两个目标标签拥有足够正负样本；
2. 至少三个 Benchmark 可用于跨域测试；
3. `task_id` 或等价分组键可获得；
4. 轨迹文本和动作序列可稳定解析；
5. 总解析成功率不低于 95%；
6. 不存在无法修复的严重标签冲突；
7. 不存在不可避免的任务泄漏；
8. 至少一个结构相关标签和一个语义相关标签具备合理研究可能性。

完成后生成：

```text
reports/PILOT_STAGE_A_DECISION.md
```

结论只能是：

- `GO`
- `CONDITIONAL GO`
- `NO-GO`

若为 `NO-GO`，停止执行。

若为 `CONDITIONAL GO`，等待人工批准后再进入阶段 B。

---

# 阶段 B：最小信号验证

仅在阶段 A 为 `GO`，或 `CONDITIONAL GO` 获得人工批准后执行。

## 15. 初始目标标签

默认：

1. `Success`
2. `Side Effect`
3. `Repetitiveness/Looping`

若某标签不可用，Codex 不得自行删除。必须在阶段 A 报告中提出，由研究负责人批准后修改配置。

---

## 16. 数据划分协议

### P1：Task-grouped 交叉验证

优先：

- `StratifiedGroupKFold`；
- 若不适用，则 `GroupKFold`。

要求：

- 相同 `task_id` 的所有轨迹进入同一折；
- 禁止普通随机样本切分；
- 优先 5 折；
- 少数类不足时允许 3 折，但必须记录原因；
- 每个标签独立检查折内分布。

### P2：Leave-One-Benchmark-Out

每次：

- 一个完整 Benchmark 作为测试域；
- 其余 Benchmark 用于训练；
- 从训练域内部按 `task_id` 划分验证集；
- 测试域不得参与阈值和融合权重选择。

每个可用 Benchmark 轮流作为测试域。

---

## 17. 模型组

### B0：Majority

每个标签独立预测训练集多数类。

### B1：身份与捷径基线

分别使用：

- Benchmark ID only；
- Agent ID only；
- Step count only；
- Length-only features。

用途：

- 检查标签是否被来源和长度轻易预测。

### B2：结构模型

模型：

- Logistic Regression；
- XGBoost，如依赖已安装且稳定；
- 否则使用 HistGradientBoosting 或 RandomForest。

第一版结构特征：

#### 长度

- 总步数；
- 总文本长度；
- 平均 observation 长度；
- 平均 action 长度；
- 最终文本长度。

#### 动作分布

- 唯一动作类型数；
- 各动作类型比例；
- 工具调用次数；
- 导航、点击、输入、搜索、返回等动作比例；
- 未知动作比例。

#### 重复性

- 连续相同动作次数；
- 最大连续重复长度；
- 重复动作比例；
- 相同动作 n-gram 重复率；
- 最后 3/5 步重复率；
- 近似相同 action 文本比例。

#### 错误与停滞

- 工具错误次数；
- 空 observation 次数；
- 无状态变化次数，如能可靠计算；
- 终止原因；
- 是否达到最大步数；
- 最后若干步是否无新增信息。

生成：

```text
reports/structural_feature_dictionary.md
```

写清每个特征的定义、公式和缺失处理。

### B3：文本模型

模型：

- TF-IDF；
- Logistic Regression。

文本视图至少比较：

- `task_only`
- `task + actions`
- `task + final`
- `task + actions + final`
- `full_text`，仅在长度可控时

要求：

- TF-IDF 词表只在训练折拟合；
- 不使用截图；
- 不使用神经编码器；
- 不将 Benchmark ID 或 Agent ID 主动加入文本。

### B4：统一拼接

将结构特征和 TF-IDF 特征拼接，训练 Logistic Regression。

用途：

- 检查“全量统一表示”是否有效。

### B5：标签专属晚期融合

分别获得：

- `p_structure,y`
- `p_text,y`

对每个标签：

```text
p_y = alpha_y * p_text,y + (1 - alpha_y) * p_structure,y
```

要求：

- `alpha_y` 只在训练折内部验证集选择；
- 搜索范围固定为 `{0.0, 0.1, ..., 1.0}`；
- 每折保存各标签的 `alpha_y`；
- 不得根据测试折调整。

B5 只是最小假设验证，不是最终论文方法。

---

## 18. 类别不平衡处理

第一版只允许：

- 无权重；
- `class_weight="balanced"`。

暂不允许：

- SMOTE；
- 复杂过采样；
- 合成样本；
- 人工扩充标签。

必须比较 weighted 与 unweighted。

---

## 19. 阈值选择

每个标签比较：

- 默认阈值 0.5；
- 验证集优化阈值。

默认优化目标：

- Positive-class F1。

测试折不得参与阈值选择。

每折阈值必须保存到：

```text
thresholds.json
```

---

## 20. 主要指标

每个标签：

- Positive-class F1；
- Macro-F1；
- Precision；
- Recall；
- PR-AUC；
- AUROC；
- Accuracy，仅辅助；
- Confusion Matrix；
- 预测正类比例。

跨折：

- mean；
- std；
- Bootstrap 95% CI。

整体：

- 标签平均 Macro-F1；
- 标签平均 PR-AUC；
- LOBO 平均；
- 每个 Benchmark 独立结果。

---

## 21. 关键比较

必须回答：

1. 结构模型是否超过 Majority？
2. 文本模型是否超过 Majority？
3. 不同标签的最佳视图是否不同？
4. 统一拼接是否优于最佳单视图？
5. 标签专属融合是否比统一拼接更稳定？
6. LOBO 中标签专属融合是否在多数留出域超过 Majority？
7. 身份与长度基线是否接近完整模型？
8. 去除长度特征后，主要结果是否明显崩溃？

---

## 22. 捷径消融

至少执行：

- Full structural；
- Structural without length；
- Length only；
- Benchmark ID only；
- Agent ID only；
- Text without source identifiers；
- 完整模型去除来源身份信息。

如无法从文本中可靠删除来源标记，必须记录。

---

## 23. 随机种子

使用：

```text
13, 21, 42, 87, 100
```

若模型完全确定，可减少重复训练，但数据划分、Bootstrap 和任何随机过程仍需固定并记录。

禁止只报告最佳种子。

---

## 24. 配置文件

创建：

```text
configs/pilot.yaml
```

至少包含：

```yaml
project: D9-R1
hypothesis: H1
data:
  version: v1
  group_key: task_id
  benchmark_key: benchmark_id
labels:
  - success
  - side_effect
  - looping
protocols:
  grouped_cv_folds: 5
  run_lobo: true
seeds: [13, 21, 42, 87, 100]
thresholds:
  mode: validation_optimized
  objective: positive_f1
fusion:
  alphas: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
```

字段可根据官方数据映射调整，但必须记录调整依据。

---

## 25. 正式运行产物

每个运行：

```text
runs/<run_id>/
├─ config.yaml
├─ command.txt
├─ git_commit.txt
├─ environment.txt
├─ metrics.json
├─ fold_metrics.csv
├─ predictions.csv
├─ thresholds.json
├─ feature_columns.json
├─ stdout.log
└─ summary.md
```

创建：

```text
research/02_EXPERIMENT_REGISTRY.csv
```

字段：

```text
run_id
experiment_name
hypothesis_id
git_commit
data_version
split_version
config_path
seed
protocol
model
start_time
end_time
hardware
status
primary_metric
output_path
notes
```

---

## 26. 最终报告

生成：

```text
reports/D9_R1_MINIMUM_PILOT_REPORT.md
```

报告结构：

1. Executive Summary
2. Data Audit
3. Label Definitions
4. Parsing and Leakage Risks
5. Evaluation Protocols
6. Majority and Shortcut Baselines
7. Structural Results
8. Text Results
9. Unified Concatenation Results
10. Dimension-Aware Fusion Results
11. Task-grouped CV
12. Leave-One-Benchmark-Out
13. Shortcut and Length Ablations
14. Error Analysis
15. Limitations
16. Stage Decision

另生成：

```text
reports/pilot_summary.csv
reports/pilot_all_metrics.csv
reports/pilot_lobo_metrics.csv
reports/pilot_grouped_cv_metrics.csv
reports/pilot_shortcut_metrics.csv
reports/pilot_error_cases.md
```

---

## 27. 阶段决策门槛

### GO

满足大部分条件：

1. 至少两个标签稳定超过 Majority；
2. 结构模型对至少一个标签有明显信号；
3. 文本模型对至少一个不同标签有明显信号；
4. 不同标签的最佳视图确实不同；
5. 标签专属融合在至少两个标签上优于或稳定匹配最佳单视图；
6. LOBO 中多数留出域超过 Majority；
7. 去除身份和纯长度捷径后，主要结论仍成立；
8. 结果在多折或多种子下稳定。

### CONDITIONAL GO

典型情况：

- 同分布有效，但跨 Benchmark 明显下降；
- 只有两个标签可学；
- 融合无稳定增益，但维度差异明显；
- 身份或长度影响较强，但并非全部解释。

可考虑收缩为：

> Web Agent 轻量轨迹裁判中的 Benchmark Shift、维度差异与捷径学习分析。

### NO-GO

出现以下情况时停止：

- 只有一个标签可学；
- 结构、文本和融合没有明确差异；
- LOBO 全部接近 Majority；
- 身份或长度基线接近完整模型；
- 标签严重不一致；
- 解析失败或泄漏无法解决；
- 结果只在个别折或个别 Benchmark 成立。

---

## 28. 严格禁止事项

Codex 不得：

- 调用付费 LLM API；
- 引入大型神经模型；
- 修改专家标签；
- 看测试结果后调整阈值或融合权重；
- 普通随机切分相同任务的轨迹；
- 删除表现不好的标签；
- 只报告最优模型或最优种子；
- 覆盖历史运行；
- 自动宣布方向成功；
- 门槛未通过时继续训练复杂模型；
- 遗漏 Majority、身份或长度基线；
- 使用测试 Benchmark 拟合 TF-IDF 词表；
- 在报告中声称 SOTA。

---

## 29. 代码质量要求

- Python 3.10+；
- 使用类型注解；
- 关键函数有 docstring；
- 数据解析和特征计算有单元测试；
- 命令行入口支持 `--config`；
- 路径不硬编码用户目录；
- 错误时返回非零退出码；
- 不静默跳过解析失败；
- 日志同时写入文件和终端；
- 所有图表可由脚本重新生成；
- 依赖尽量少；
- 新增依赖写入 `requirements.txt`。

建议最小依赖：

```text
pandas
numpy
scikit-learn
scipy
pyyaml
matplotlib
pyarrow
tqdm
```

XGBoost 可选，不应成为任务完成的阻塞项。

---

## 30. 推荐执行顺序

严格按顺序：

1. 初始化项目目录；
2. 下载并固定数据版本；
3. 编写字段与标签映射；
4. 完成数据审计；
5. 生成阶段 A 决策报告；
6. 仅在门槛通过后构建处理数据；
7. 建立 Task-grouped 划分；
8. 建立 LOBO 协议；
9. 运行 Majority；
10. 运行身份和长度捷径基线；
11. 运行结构 LR；
12. 运行结构树模型；
13. 运行 TF-IDF + LR；
14. 运行统一拼接；
15. 运行标签专属晚期融合；
16. 做长度和身份消融；
17. 汇总 OOF 与 LOBO 结果；
18. 计算 Bootstrap CI；
19. 完成错误分析；
20. 生成最终预实验报告；
21. 给出 `GO / CONDITIONAL GO / NO-GO`，等待人工批准。

---

## 31. Codex 最终回复格式

Codex 完成后必须回复：

1. 实际执行到哪个阶段；
2. 是否遇到字段或标签歧义；
3. 数据审计结论；
4. 是否进入模型阶段；
5. 主要指标摘要；
6. 捷径基线摘要；
7. LOBO 摘要；
8. 未完成项；
9. 最终阶段建议；
10. 所有关键产物的本地绝对路径。

不得只回复“任务已完成”。
