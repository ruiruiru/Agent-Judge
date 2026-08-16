# Stage A2.1：Efficiency & Cost Benchmark

## 1. 阶段定位

本任务书是 Stage A2 Master Plan 的第一个可执行子阶段。

本轮只执行：

```text
A2.1 — Efficiency & Cost Benchmark
```

不执行：

```text
A2.2
A2.3
external validation
A3
```

完成 A2.1 后必须：

```text
STOP
WAIT_FOR_HUMAN_A2_1_REVIEW
```

---

## 2. 科研目的

当前论文希望使用：

```text
lightweight structural trajectory evaluation
```

作为核心方法定位。

A2.1 的唯一科研问题：

> Frozen 13-dimensional structural representation B2，相比 frozen 1024-dimensional dense semantic representation B4，在表示复杂度、计算时间、内存/显存和硬件需求上到底便宜多少？

本阶段只验证：

```text
efficiency / cost
```

不重新验证：

```text
predictive performance
generalization
model superiority
```

---

## 3. Frozen claim contract

开始前必须核验：

```text
artifacts/a1_11_final_claim_matrix.csv
SHA-256 =
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

以及：

```text
artifacts/a1_11_table_main_test_results.csv
SHA-256 =
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

Frozen claim identities：

```text
Success = CONFIRMATORY_SUPPORTED
Looping = CONFIRMATORY_SUPPORTED
Side Effect = EXPLORATORY_SUPPORTED
```

A2.1 无权改变它们。

---

## 4. Git gate

开始前：

```text
git status --porcelain
```

必须为空。

如果本 A2.1 taskbook 尚未被 Git 跟踪：

```text
STOP
```

只允许先做独立 docs-only preregistration commit，例如：

```text
chore: preregister A2.1 efficiency benchmark
```

然后停止。

不得在同一轮继续 benchmark。

---

## 5. Benchmark 对象

### B2 — Structural

必须使用 frozen 13-feature structural representation。

```text
dimension = 13
```

必须沿用 A1 已冻结 extractor contract。

不得：

```text
新增 feature
删除 feature
修改 feature definition
修改 cleaning contract
```

---

### B4 — Dense semantic

必须使用 frozen：

```text
Qwen/Qwen3-Embedding-0.6B
revision =
97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3

embedding dimension = 1024
```

必须沿用 A1.7 frozen semantic extraction contract。

禁止修改：

```text
model
revision
tokenizer
serialization
chunking
pooling
normalization
dtype policy
```

---

## 6. Benchmark 数据

Primary efficiency corpus：

```text
196 frozen dev trajectories
```

必须复用现有 frozen cleaned dev inputs。

不得：

```text
下载新数据
重新访问远程原始数据
使用 test labels
以 official test 作为 timing 主样本
```

Efficiency benchmark 与标签无关。

---

## 7. 严禁重新计算科学指标

A2.1 不允许：

```text
重新计算 Success AP
重新计算 Looping AP
重新计算 Side Effect AP
重新计算 F1
重新计算 AP lift
重新 bootstrap
重新 grade
```

如果 efficiency table 需要 performance context：

> 必须从 A1.11 frozen evidence/table exact join。

因此必须满足：

```text
A1 metric recomputations = 0
```

---

## 8. 测量原则

Efficiency benchmark 必须区分：

### 8.1 Representation complexity

记录：

```text
dimension
serialized representation bytes
serialized representation MB
```

### 8.2 Model artifact complexity

记录：

```text
frozen classifier artifact size
semantic encoder weight size（若本地可直接核验）
```

不要把 encoder weight 和 classifier artifact 混成同一列。

### 8.3 Cold-start

记录：

```text
process/model initialization + first usable output
```

B2 与 B4 分开。

### 8.4 Warm representation extraction

记录：

```text
total seconds
ms / trajectory
```

### 8.5 Frozen classifier inference

在 representation 已存在情况下记录：

```text
total seconds
ms / trajectory
```

只允许：

```text
load
predict_proba
```

禁止：

```text
fit
partial_fit
retraining
```

### 8.6 Memory

记录：

```text
peak process RSS MB
```

B4 另外记录：

```text
peak GPU allocated MB
peak GPU reserved MB
或等价可复现 VRAM measure
```

必须在 report 中说明具体测量方法。

---

## 9. 重复规则

### B2

```text
warmup runs = 1
measured runs = 5
```

### B4

```text
warmup runs = 1
measured runs = 3
```

正式 summary 使用：

```text
median
```

同时保留所有 raw runs。

禁止：

```text
只报告最快一次
删除慢 run
根据结果追加/减少 repetitions
```

---

## 10. GPU gate

B4 正式 timing 前必须确认：

```text
torch.cuda.is_available() = true
实际 embedding device = cuda
```

记录 GPU 型号。

如果 B4 实际运行在 CPU：

```text
STOP
```

不得将 CPU B4 timing 写入正式 efficiency comparison。

---

## 11. 环境冻结记录

必须生成 machine-readable environment snapshot，至少记录：

```text
timestamp
OS
Python
CPU
logical CPU count
RAM
GPU
GPU driver
CUDA runtime
PyTorch
transformers
NumPy
scikit-learn
thread environment variables
batch size
dtype
```

输出：

```text
artifacts/a2_1_environment.json
```

---

## 12. Timing implementation

优先实现一个 deterministic local benchmark script。

建议：

```text
scripts/run_a2_1_efficiency_benchmark.py
```

要求：

- 一次性读取 frozen dev inputs；
- compact logging；
- 不逐 trajectory 输出；
- Qwen 每 20–50 条最多打印一次进度；
- timing 区间定义明确；
- raw timing 自动保存；
- 异常立即非零退出。

不得依赖 Codex 每条轮询。

---

## 13. 输出文件

必须生成：

```text
artifacts/a2_1_environment.json
artifacts/a2_1_efficiency_raw.csv
artifacts/a2_1_efficiency_summary.csv
artifacts/a2_1_efficiency_relative_cost.csv
artifacts/a2_1_run_summary.json
docs/stage_a2_1_efficiency_benchmark_report.md
```

---

## 14. Raw CSV 最低字段

至少：

```text
method
phase
run_type
run_index
trajectory_count
dimension
device
total_seconds
ms_per_trajectory
peak_cpu_rss_mb
peak_gpu_allocated_mb
peak_gpu_reserved_mb
status
notes
```

---

## 15. Summary 最低字段

至少：

```text
method
representation
dimension
device
measured_repetitions
median_extraction_ms_per_trajectory
median_inference_ms_per_trajectory
cold_start_seconds
representation_size_mb
classifier_artifact_size_mb
semantic_encoder_size_mb
peak_cpu_rss_mb
peak_gpu_vram_mb
evidence_status
```

其中：

```text
evidence_status = EFFICIENCY_BENCHMARK
```

---

## 16. Relative-cost 表

至少计算：

```text
dimension_ratio_B4_over_B2
representation_size_ratio_B4_over_B2
extraction_time_ratio_B4_over_B2
classifier_inference_ratio_B4_over_B2
peak_memory_ratio_B4_over_B2
```

如果某项不可合法比较：

```text
NA
```

并说明原因。

不得为了生成 ratio 而伪造 denominator。

---

## 17. Performance context

允许在 report 中引用 frozen A1 结果，例如：

```text
Success final held-out AP = 0.654836
Looping final held-out AP = 0.921769
```

但必须注明：

```text
source = A1 frozen artifact
not recomputed in A2.1
```

不得使用 A2.1 efficiency benchmark 改写：

```text
B2 > B4 confirmatory
```

A2.1 不产生新的 predictive-performance superiority claim。

---

## 18. 允许的论文结论

如果数据支持，允许写：

> B2 uses substantially lower-dimensional representations and substantially lower extraction compute than B4 under the measured environment.

允许描述：

```text
X× lower dimension
X× lower extraction time
X× lower representation storage
CPU-capable vs GPU-backed dense encoder
```

---

## 19. 禁止结论

不得写：

```text
B2 is universally more efficient on all hardware.
B2 universally replaces semantic evaluators.
B2 is scientifically superior to B4.
Dense semantics are unnecessary.
Efficiency proves better generalization.
```

本阶段只测：

```text
measured computational cost under the recorded environment
```

---

## 20. Tests / guards

至少添加或执行验证：

1. claim matrix SHA guard；
2. main test table SHA guard；
3. B2 dimension = 13；
4. B4 dimension = 1024；
5. B4 revision guard；
6. no `.fit(` in A2.1 benchmark path；
7. no test-label access；
8. no A1 metric recomputation path；
9. repetitions exact；
10. raw → summary median consistency；
11. relative-cost arithmetic consistency；
12. output schema；
13. deterministic non-timing metadata/hash fields。

Timing 数值本身不要求 byte-identical rerun。

---

## 21. Commit discipline

### A2.1a — preregistration

如果尚未完成：

```text
chore: preregister A2.1 efficiency benchmark
```

仅 taskbook / config / tests。

### A2.1b — implementation

建议：

```text
chore: implement A2.1 efficiency benchmark
```

### A2.1c — results

```text
analysis: record A2.1 efficiency benchmark
```

不得 amend。

出现实现问题：

```text
独立 fix commit
```

必须保留失败 provenance。

---

## 22. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

必须满足：

```text
Git start clean
claim matrix SHA correct
main test table SHA correct
196 frozen dev trajectories complete
B2 13-d benchmark complete
B4 1024-d CUDA benchmark complete
environment recorded
raw timing complete
summary complete
relative cost complete
A1 metric recomputations = 0
model fits = 0
A1 model changes = 0
A1 threshold changes = 0
official-test tuning = 0
Git final clean
```

### PASS_WITH_CONDITIONS

只允许非核心问题，例如：

```text
某个跨平台 memory metric 不可获得
encoder disk size 只能从冻结文件统计
minor timing noise
```

必须保证主要 runtime / dimension / device comparison 可解释。

### STOP

包括：

```text
B4 not on CUDA
frozen artifact hash mismatch
B2/B4 contract mismatch
new fit detected
A1 metric recomputation detected
test-label dependency
timing implementation 不可解释
Git provenance 不清
```

---

## 23. 最终汇报

必须汇报：

```text
阶段判定

A2.1 prereg commit
implementation commit
result commit
fix commits
amend

A1.11 claim matrix SHA verification
main test table SHA verification

benchmark trajectory count

B2:
dimension
device
cold-start
median extraction ms/trajectory
median inference ms/trajectory
representation size
classifier size
peak CPU RSS

B4:
dimension
device
model revision
cold-start
median extraction ms/trajectory
median inference ms/trajectory
representation size
classifier size
semantic encoder size
peak CPU RSS
peak GPU VRAM

relative ratios

A1 metric recomputations = 0
model fits = 0
A1 model changes = 0
A1 threshold changes = 0
official-test tuning = 0

warnings
tests/verifiers
Git status

report path
machine summary path

WAIT_FOR_HUMAN_A2_1_REVIEW
```

完成后立即停止。

不得执行 A2.2。
