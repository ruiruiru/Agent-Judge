# Stage A1.7：冻结 Dense Semantic Baseline（Primary LOBO）

## 1. 阶段定位

Stage A1.6 已完成人工阶段门审查：`PASS_WITH_CONDITIONS`。

A1.6 已确认：Success / B2 与 Looping / B2 的跨 Benchmark macro AP lift 在 task-group-aware bootstrap 下稳定为正；Looping 删除 repetition 特征后 macro AP 稳定下降；Success 的 B2 vs B3、termination 消融和 3 特征 vs full13 差异仍存在明显不确定性；Side Effect 仅有 12 个正例，跨域统计支持不足。

因此 A1.7 不再继续结构消融，也不访问 test。本阶段只回答一个新问题：

> 将浅层 TF-IDF 表示升级为冻结的现代 dense semantic embedding 后，跨 Benchmark 的 Agent trajectory 判断是否获得稳定增益？

本阶段只新增一个模型族：

```text
B4_dense_embedding_lr
```

不得新增第二个 embedding 模型、不得微调 embedding 模型、不得做融合。

---

## 2. 冻结 embedding 模型

唯一模型：

```text
Qwen/Qwen3-Embedding-0.6B
Hugging Face revision = 97b0c61
```

A1.7a 必须将短 revision 解析为完整 immutable commit SHA，并记录到正式配置和机器摘要。

预期权重：

```text
model.safetensors
SHA-256 = 0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd
```

若实际 SHA-256 不一致：`STOP`。

方法定位：0.6B、32K context、默认 1024 维，作为“比 TF-IDF 强一档、但远小于 LLM Judge”的冻结语义表示基线。

本阶段不得比较 Qwen3 4B/8B、BGE、E5、OpenAI Embeddings 或其它 embedding 模型。

---

## 3. 研究目标

### Primary：Success

回答：

1. B4 在 Primary LOBO 下是否存在稳定正的 macro AP lift；
2. B4 是否稳定优于 A1.3 B3 TF-IDF；
3. B4 是否稳定优于 A1.3 B2 structural LR；
4. 如果不能稳定优于 B2/B3，是否说明当前更复杂语义表示没有明确跨 Benchmark 增益。

### Diagnostic：Side Effect

回答：

1. B4 是否出现比 B3 更有希望的语义点估计；
2. 由于仅 12 个正例，其 CI / valid fraction 是否仍很宽；
3. 不得把任何高 AP 自动升级为 robust Side Effect 结论。

### Secondary：Looping

回答：dense semantics 是否提供超过 B2 structural LR 的明显价值。Looping 只作为复杂度负控制 / secondary result。

---

## 4. 禁止回答

A1.7 不得回答：最终 test 性能、LLM Judge 是否更强、embedding 微调是否有效、B2+B4 fusion 是否有效、joint task+model OOD、secondary LOBO、最终部署性能、因果机制。

---

## 5. 固定数据版本

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face Agent Reward Bench revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

不得修改 dev/test split、labels、eligibility、trajectory_key、group_key、benchmark_group_primary、primary serialized input、A1.3 Primary LOBO outer manifest、A1.3 inner folds。

---

## 6. 必须先读取

至少读取：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/evaluation_protocol.md
docs/stage_a1_3_primary_lobo_report.md
docs/stage_a1_5_structural_mechanism_ablation_report.md
docs/stage_a1_6_group_aware_bootstrap_report.md

data/processed/dev_serialized_primary.jsonl
artifacts/dev_analysis_index.csv
artifacts/lobo_primary_manifest.csv
artifacts/a1_3_lobo_inner_folds.csv

artifacts/a1_3_lobo_predictions.csv
artifacts/a1_3_lobo_domain_metrics.csv
artifacts/a1_3_lobo_macro_metrics.csv
artifacts/a1_3_lobo_pooled_metrics.csv
artifacts/a1_3_lobo_run_summary.json

artifacts/a1_6_bootstrap_draw_registry.csv
artifacts/a1_6_bootstrap_registry_summary.json
artifacts/a1_6_run_summary.json

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml
configs/stage_a1_3_lobo_execution.yaml
configs/stage_a1_6_bootstrap.yaml

research/01_DECISION_LOG.md
```

若正式产物路径不同，只允许通过对应机器摘要解析。不得使用失败运行、旧版文件、临时预测或 test。

---

## 7. 唯一输入视图

B4 唯一文本输入：

```text
data/processed/dev_serialized_primary.jsonl
```

与 A1.3 B3 使用同一 primary view。

不得使用 reasoning sensitivity、error ablation、raw screenshot/image、summary_info、reward、annotation、model_name metadata、benchmark identity prefix 或任何新字段。

Embedding 必须：

```text
label-blind
target-blind
benchmark-blind
```

Success / Side Effect / Looping 共用同一份 trajectory embedding。不得为不同 target 创建不同 prompt 或 embedding。

---

## 8. 无 prompt 规则

A1.7 不使用任何 task instruction / prompt。

禁止：

```text
Judge whether this trajectory succeeded
Detect side effects
Detect looping
query prompt
target-specific prompt
benchmark-specific prompt
```

输入仅为冻结 primary trajectory text 本身。本阶段只测试 pretrained dense semantic representation，不允许 prompt engineering 引入新的任务监督自由度。

---

## 9. 模型获取与网络边界

### A1.7a

网络仅允许：

1. 获取指定 revision 的 Qwen3-Embedding-0.6B snapshot；
2. 解析完整 commit SHA；
3. 准备独立 semantic inference 环境。

下载后必须记录所有关键 snapshot 文件 SHA-256，并验证 `model.safetensors` SHA。

生成：

```text
artifacts/a1_7_embedding_model_manifest.json
requirements/semantic-lock.txt
```

不得修改：

```text
requirements/baseline-lock.txt
artifacts/baseline_environment.json
```

### A1.7b

正式 embedding inference 与分类实验：

```text
network = 0
local_files_only = true
```

若正式运行尝试联网：`STOP`。

---

## 10. 独立环境

不得为了 Qwen embedding 升级 A1.2–A1.6 baseline 环境。创建独立 semantic environment，并冻结：

```text
requirements/semantic-lock.txt
artifacts/a1_7_semantic_environment.json
```

最低要求：

```text
transformers >= 4.51.0
torch with Qwen3 support
numpy
safetensors
```

记录精确 Python、torch、CUDA runtime、GPU、transformers、tokenizers、safetensors、numpy。

Classifier 阶段继续使用既有 baseline sklearn 环境。

---

## 11. Tokenization 与长轨迹策略

不得静默截断。统一 tokenizer-aware non-overlapping chunking。

### 11.1 Payload tokenization

```python
tokenizer.encode(text, add_special_tokens=False)
```

`eos_token_id` 必须唯一可用，否则 `STOP`。

### 11.2 Chunk

固定：

```text
max_model_tokens = 8192
payload_tokens_per_chunk = 8191
overlap = 0
每个 chunk 末尾 exactly one eos_token_id
```

按原始 token 顺序切分，每个 chunk：

```text
chunk_input_ids = payload_chunk + [eos_token_id]
attention_mask = all ones
```

不得只取 head/tail，不得 head-tail 截断，不得调 overlap，不得结果后改 chunk size。

### 11.3 Token audit

A1.7a 在任何真实 dev 神经 embedding forward 前生成：

```text
artifacts/a1_7_tokenization_audit.csv
```

至少：trajectory_key、payload_token_count、chunk_count、min/max chunk payload tokens；并汇总 token/chunk 的 min/median/mean/p95/max。Token audit 不读取 labels。

---

## 12. Embedding 推理算法

使用 pinned snapshot，本地离线加载：

```text
AutoTokenizer
AutoModel
model.eval()
torch.inference_mode()
```

禁止 fine-tune、backward、optimizer。

### 12.1 Chunk embedding

每个 chunk：

1. forward；
2. 取最后一个 token（EOS）的 last hidden state；
3. cast float32；
4. L2 normalize。

输出维度不是 1024：`STOP`。

### 12.2 Trajectory embedding

每个 chunk 权重 = 该 chunk 的 payload token count。

```text
trajectory = token-count-weighted mean(normalized chunk embeddings)
trajectory = L2 normalize(trajectory)
```

最终：

```text
shape = [196, 1024]
dtype = float32
finite = true
L2 norm ≈ 1
```

禁止 max pooling、learned pooling、attention pooling、target-specific pooling。

---

## 13. GPU 与确定性

Embedding inference 允许 GPU。

必须：

```text
random seed = 2026
model.eval()
torch.inference_mode()
TF32 disabled
```

若可行启用 deterministic algorithms。

禁止 4-bit/8-bit/GPTQ/AWQ/bitsandbytes quantization。

### Determinism probe

正式全量 inference 前，在固定 16 条 probe trajectories 上连续运行两次：

```text
cosine similarity >= 0.999999
max absolute difference <= 1e-5
```

失败：`STOP`。

---

## 14. Embedding 产物冻结

正式生成：

```text
artifacts/a1_7_qwen3_embedding_0p6b.npy
artifacts/a1_7_embedding_index.csv
artifacts/a1_7_embedding_extraction_summary.json
```

Index 至少：row_index、trajectory_key、payload_token_count、chunk_count、embedding_norm。

不得保存 labels 到 embedding 文件。

验证：196 unique keys、1024 dims、无 NaN/Inf、norm 合格。生成一次后计算 SHA-256，之后分类只能读取冻结 embedding；不得因分类结果不好重新生成。

---

## 15. B4 分类器

```text
baseline_id = B4_dense_embedding_lr
input = 1024-d L2-normalized frozen embedding
```

分类器：

```text
LogisticRegression
penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026
NO StandardScaler
```

候选固定：

```text
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共 6 configs。不得加其它 C、solver、SVM、MLP、XGBoost、fine-tuning。

---

## 16. Primary LOBO 复用

唯一 outer manifest：

```text
artifacts/lobo_primary_manifest.csv
```

唯一 inner folds：

```text
artifacts/a1_3_lobo_inner_folds.csv
```

不得重新生成。

冻结 pretrained embedding extractor 与 dev labels 无关，因此可以先对全部 196 trajectory 生成 embedding；但 downstream LR 的 fit / selection 必须严格遵守 LOBO。

---

## 17. Config 与 threshold 选择

完全沿用 A1.3：

### Config

对 6 个候选，用 frozen inner folds 生成 pooled inner OOF，以 `average_precision_score` 选最佳 config。

Tie-break：

1. class_weight=None；
2. 更小 C；
3. config_id 字典序。

### Threshold

候选：

```text
0.05, 0.10, ..., 0.95
```

在 selected config 的 pooled inner OOF 上最大化 positive F1。

Tie-break：higher recall > closer to 0.5 > smaller threshold。

然后在全部三个训练 Benchmark refit LR，external held-out 只评估一次。

---

## 18. Targets 与单类处理

三个 target 全部运行：Success、Side Effect、Looping。

预期：

```text
Success = 192
Side Effect = 195
Looping = 196
```

Side Effect / AssistantBench 仍为 24 negative / 0 positive：

```text
metric_status = single_class_negative
```

双类别指标为 NA，不得填 0/0.5。

---

## 19. 预期行数

```text
embeddings = 196 × 1024
external predictions = 583
selected inner OOF = 1749
config selection = 72
threshold selection = 228
domain metrics = 12
macro metrics = 3
pooled metrics = 3
```

任一关键数量不一致：`STOP`。

---

## 20. 指标

Mixed-class domain：

Primary：Average Precision、positive F1。

Auxiliary：ROC-AUC、Precision、Recall、F2、Balanced Accuracy、MCC、AP lift。

三层汇总：per-domain、mixed-domain macro mean ± sample std (`ddof=1`)、pooled LOBO。

Pooled 仍是 secondary interpretation，因为四个 held-out Benchmark 使用独立训练 LR，概率尺度可能不同。

---

## 21. 与 A1.3 frozen baselines 比较

不得重跑 B0–B3。直接读取正式 A1.3 B2/B3。

生成：

```text
artifacts/a1_7_comparison_to_a1_3.csv
```

至少包含 target、method、macro AP/F1、pooled AP/F1、AP lift、B4-B2、B4-B3。

---

## 22. 复用 A1.6 Bootstrap registry

必须原样复用：

```text
artifacts/a1_6_bootstrap_draw_registry.csv
```

不得生成新 seed 或新 registry。

Bootstrap 仍为：10000 draws、task-group cluster、在 target × held_out_group 内抽样、percentile 95% CI。不得 trajectory bootstrap、stratified bootstrap、invalid redraw、BCa、新 seed。

---

## 23. A1.7 Primary inference

### Q1 Success：B4 semantic signal

```text
B4 macro AP lift
```

### Q2 Success：B4 vs B3

```text
B4 - B3 macro AP
B4 - B3 macro F1
```

回答 dense semantics 是否稳定优于 TF-IDF。

### Q3 Success：B4 vs B2

```text
B4 - B2 macro AP
B4 - B2 macro F1
```

回答 dense semantics 是否稳定优于当前结构 baseline。

### Q4 Side Effect：support diagnostic only

报告：B4 per-domain/macro/pooled AP CI、valid fraction、invalid single-class draws、B4-B3 macro AP paired CI。

固定 role：

```text
support_diagnostic_only
```

无论多高不得自动升级为 robust。

### Q5 Looping：secondary complexity control

```text
B4 - B2 macro AP
```

固定 role：

```text
secondary_complexity_control
```

---

## 24. 冻结结论规则

### Success

若 Q1 CI lower >0 且 Q2 AP CI lower >0：

```text
dense_semantics_add_value_over_tfidf
```

若再满足 Q3 AP CI lower >0：

```text
dense_semantics_outperform_current_lightweight_baselines
```

若 Q1 positive，但 Q2/Q3 跨0：

```text
dense_semantic_signal_without_clear_incremental_gain
```

若 Q1 CI 包含0：

```text
dense_semantic_cross_benchmark_signal_uncertain
```

### Side Effect

最多：

```text
promising_low_support_semantic_signal
```

或：

```text
no_clear_semantic_improvement
```

不得使用 robust/solved/generalizable。

### Looping

只给：

```text
semantic_complexity_not_needed
```

或：

```text
semantic_additional_signal_descriptive
```

---

## 25. A1.7a：预注册与环境冻结

在任何真实 dev 神经 embedding forward 前完成。

允许：下载 pinned model、环境安装、tokenizer-only token audit、synthetic tests、固定16条 probe determinism test（不得读取 labels）。

生成：

```text
configs/stage_a1_7_dense_semantic.yaml
requirements/semantic-lock.txt
artifacts/a1_7_embedding_model_manifest.json
artifacts/a1_7_semantic_environment.json
artifacts/a1_7_tokenization_audit.csv
artifacts/a1_7_prerun_integrity.json
scripts/extract_stage_a1_7_embeddings.py
scripts/run_stage_a1_7_dense_semantic.py
tests/test_stage_a1_7_dense_semantic.py
```

更新 `research/01_DECISION_LOG.md`。

提交：

```text
chore: preregister frozen dense semantic baseline
```

A1.7a 前不得对全部 dev 做正式 embedding，不得在真实 labels 上 `.fit()`。

---

## 26. A1.7b：正式运行

开始前 Git clean。

顺序：

1. hash/model/env guards；
2. network=0；
3. local_files_only=true；
4. 全量196条生成一次 embedding；
5. 冻结 embedding hash；
6. 使用 baseline sklearn 环境运行 B4 nested Primary LOBO；
7. 583 external predictions；
8. 12 domain / 3 macro / 3 pooled；
9. 与 A1.3 B2/B3 比较；
10. 复用 A1.6 registry 计算 Q1–Q5；
11. 独立复算；
12. 测试；
13. 正式报告。

提交：

```text
experiment: run frozen dense semantic baseline
```

不得 amend A1.7a。

---

## 27. 异常处理

### Pre-inference guard failure

revision/hash/input/env/determinism 失败：`STOP`。

允许独立 fix commit 后从 guard 重来。

### 全量 embedding 后发现错误

chunking/pooling/model/input 错误：全部 A1.7 embedding/B4 结果作废，保留失败日志，独立 fix commit，从全量 embedding 重新开始。

### B4 `.fit()` 后发现错误

全部 B4 结果作废并完整重跑；若涉及 embedding，embedding 同时作废。

不得选择性保留有利 domain。

---

## 28. 测试要求

至少验证：

### Model/environment
1. repo_id精确；
2. revision精确并解析完整SHA；
3. model.safetensors SHA精确；
4. license metadata记录；
5. transformers支持Qwen3；
6. baseline env未修改；
7. semantic env冻结；
8. A1.7b network=0；
9. local_files_only=true。

### Input
10. primary text hash与A1.3一致；
11. 196 trajectory唯一；
12. label不进入embedding；
13. 无target prompt；
14. 无benchmark prefix；
15. 无model_name prefix；
16. reasoning/error view未读取。

### Token/embedding
17. payload add_special_tokens=False；
18. chunk payload<=8191；
19. 每chunk exactly one EOS；
20. overlap=0；
21. 顺序保持；
22. 不静默truncate；
23. last EOS pooling；
24. chunk L2 normalize；
25. token-count weighted mean；
26. final L2 normalize；
27. dimension=1024；
28. float32；
29. no NaN/Inf；
30. 196 embeddings；
31. determinism probe达标；
32. quantization=0。

### LOBO
33. outer manifest与A1.3一致；
34. inner folds与A1.3一致；
35. B4恰好6 configs；
36. LR语义固定；
37. no StandardScaler；
38. config只由inner OOF AP；
39. threshold只由selected inner OOF；
40. heldout labels不参与选择；
41. positive probability由classes_定位。

### Counts
42. external predictions=583；
43. selected inner OOF=1749；
44. config rows=72；
45. threshold rows=228；
46. domain metrics=12；
47. macro=3；
48. pooled=3；
49. target×trajectory external prediction唯一。

### Bootstrap
50. 原样使用A1.6 registry；
51. 无新seed；
52. paired comparison使用相同draw；
53. invalid draw不补抽；
54. Q1–Q5齐全；
55. Side Effect Q4固定diagnostic；
56. CI可复算。

### Boundaries
57. 第二embedding模型=0；
58. fine-tune=0；
59. fusion=0；
60. secondary LOBO=0；
61. 新LOMO=0；
62. joint OOD=0；
63. LLM Judge=0；
64. test访问=0；
65. 核心输入hash不变；
66. Git clean。

---

## 29. 输出产物

```text
artifacts/a1_7_embedding_model_manifest.json
artifacts/a1_7_semantic_environment.json
artifacts/a1_7_tokenization_audit.csv
artifacts/a1_7_qwen3_embedding_0p6b.npy
artifacts/a1_7_embedding_index.csv
artifacts/a1_7_embedding_extraction_summary.json
artifacts/a1_7_inner_config_selection.csv
artifacts/a1_7_inner_selected_oof_predictions.csv
artifacts/a1_7_threshold_selection.csv
artifacts/a1_7_external_predictions.csv
artifacts/a1_7_domain_metrics.csv
artifacts/a1_7_macro_metrics.csv
artifacts/a1_7_pooled_metrics.csv
artifacts/a1_7_comparison_to_a1_3.csv
artifacts/a1_7_bootstrap_primary_summary.csv
artifacts/a1_7_bootstrap_draw_metrics.parquet
artifacts/a1_7_run_summary.json
docs/stage_a1_7_frozen_dense_semantic_baseline_report.md
```

---

## 30. 阶段判定

最终：`PASS` / `PASS_WITH_CONDITIONS` / `STOP`。

### Technical PASS

必须满足：A1.7a prereg commit；pinned model revision/hash；embedding label-blind；196×1024 embeddings；583 external predictions；1749 inner OOF；72 config；228 threshold；outer/inner未变化；Q1–Q5完成；A1.6 registry原样复用；CI可复算；test=0；禁止实验=0；测试通过；hash不变；Git clean；A1.7b独立commit。

### PASS_WITH_CONDITIONS

包括：Success B4有信号但无稳定增益；B4/B2/B3 CI跨0；Side Effect仍低支持；个别domain失效；GPU数值存在允许范围内极小差异；Looping不从dense semantics获益。

### STOP

包括：model revision/hash错误；target-specific prompt；label进入embedding；silent truncation；fine-tuning；held-out label进入选择；outer/inner改变；bootstrap换registry；新增第二embedding；fusion；test访问；预测缺失/重复；正式运行后改方法混用结果。

---

## 31. 正式报告

生成：

```text
docs/stage_a1_7_frozen_dense_semantic_baseline_report.md
```

至少包含：阶段判定；commits；数据revision；embedding model完整revision/weight SHA；semantic环境；chunking/pooling；token/chunk分布；determinism audit；embedding hash；B4定义；12个domain结果；macro/pooled；B2/B3 frozen comparison；Q1–Q5 bootstrap CI；Success semantic incremental gain；Side Effect low-support diagnostic；Looping complexity control；fine-tune/fusion/第二模型均0；正式network=0；test=0；测试和完整性；论文主线影响；停止等待人工审查。

---

## 32. 最终汇报

Codex 最终必须汇报：

1. 阶段判定；
2. A1.7 commits；
3. 完整 model revision 和 weight SHA；
4. semantic env；
5. token/chunk统计；
6. 196×1024 embedding完整性和hash；
7. determinism probe；
8. B4 config/threshold分布；
9. 三个target四domain结果；
10. macro/pooled AP/F1；
11. B4 vs B2/B3 point delta；
12. Q1–Q5 point/median/95%CI/valid fraction/grade；
13. Side Effect support；
14. 583 external predictions；
15. 1749 inner OOF；
16. 72 config rows；
17. 228 threshold rows；
18. fine-tune=0；
19. 正式network=0；
20. test访问=0；
21. 禁止实验=0；
22. 测试；
23. 运行前后hash；
24. Git status；
25. 正式报告与机器摘要路径。

完成后必须停止。不得自动进入 fusion、第二embedding模型、LLM Judge、secondary LOBO、joint OOD 或 test。
