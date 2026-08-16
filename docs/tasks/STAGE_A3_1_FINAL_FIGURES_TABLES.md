# Stage A3.1：Final Figures、Final Tables 与 Visual Artifact Freeze

## 1. 阶段定位

Stage A2 已完成 publication-completion evidence package。

A2.3 最终状态：

```text
PASS_WITH_CONDITIONS
WAIT_FOR_HUMAN_A2_3_REVIEW
```

A2.3 条件仅为：

```text
Tier 4 literature entries = NEEDS_LITERATURE_VERIFICATION
external validation = DEFER_TO_REVISION
```

无科学不一致。

A3.1 是 Stage A3 的第一个可执行小阶段。

本轮只做：

> 将 A2.3 已冻结的 paper-ready 数据真正渲染成最终论文 Figure / Table artifacts，并冻结视觉样式、展示精度、caption 边界、源数据映射与哈希。

本轮不做：

```text
A3.2 literature verification
A3.3 manuscript evidence freeze
完整 manuscript 写作
新实验
external validation
```

完成后必须：

```text
STOP
WAIT_FOR_HUMAN_A3_1_REVIEW
```

---

## 2. A3.1 唯一目标

A3.1 不再回答新的科研问题，只解决论文生产问题：

1. 最终正文/附录应该使用哪些图表；
2. 图表中的每个数字能否追溯到 frozen artifact；
3. 图表是否清楚、诚实、可打印、可缩放；
4. display rounding 是否与 exact machine values 分离；
5. 图表是否严格遵守 A1/A2 claim boundaries。

---

## 3. 科研身份

A3.1 仅属于：

```text
VISUAL_ARTIFACT_GENERATION
TABLE_RENDERING
DISPLAY_FORMATTING
SOURCE_TRACEABILITY
ARTIFACT_FREEZE
```

不属于：

```text
new scientific analysis
new metric computation
new model comparison
new statistical inference
```

---

## 4. Pre-stage hard gates

正式执行前必须核验：

### 4.1 Git

```text
git status --porcelain
```

必须为空。

### 4.2 A1.11 claim matrix

```text
artifacts/a1_11_final_claim_matrix.csv
SHA-256 =
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

### 4.3 A1.11 main test table

```text
artifacts/a1_11_table_main_test_results.csv
SHA-256 =
c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947
```

### 4.4 A2.3 result commit

必须可解析：

```text
ad0576c488fafed243b464e0b8f903e9bb233b43
```

### 4.5 A2.3 frozen table hashes

必须 exact match：

```text
Table 1:
297a1f59c34fc7f29864d722e8e2a233945dba061527848e31b4d7411b2964a5

Table 2:
bbf36c09827819fbf49aaa7487db66b34077052d8a29cb093c72001bee66f02a

Table 3:
f0e15e670e3f9592c167c57adaf41a63d56bce0fc9bc37a1945a8ed3f3431c1e

Table 4:
de0cbc94d114eab5677d1ff620a5f0d976883ae8515d3cb24e873f9f213ac511

Table 5:
037a8b3200377093bf1abb5ea0cf9b82db74fb162e27971690d10f7d9cdf4a0f
```

### 4.6 A2.3 paper package

必须存在且可解析：

```text
docs/a2_3_publication_results_story.md
docs/a2_3_publication_figure_spec.md
docs/a2_3_final_limitations_ledger.md
artifacts/a2_3_publication_package_index.csv
```

### 4.7 Frozen claim identities

必须仍为：

```text
Success = CONFIRMATORY_SUPPORTED
Looping = CONFIRMATORY_SUPPORTED
Side Effect = EXPLORATORY_SUPPORTED
```

任一 hard gate 失败：

```text
STOP
```

---

## 5. Preregistration gate

如果：

```text
docs/tasks/STAGE_A3_1_FINAL_FIGURES_TABLES.md
```

尚未被 Git 跟踪：

```text
STOP
```

本轮只允许创建独立 docs-only prereg commit：

```text
chore: preregister A3.1 final figures and tables
```

然后立即停止。

不得在同一轮继续渲染图表。

---

## 6. 科学操作零计数

整个 A3.1 必须保持：

```text
new_model_fits = 0
new_inference_runs = 0
new_embedding_runs = 0
A1_metric_recomputations = 0
bootstrap_reruns = 0
new_significance_tests = 0
threshold_changes = 0
eligibility_changes = 0
final_model_changes = 0
official_test_tuning = 0
external_dataset_runs = 0
```

允许的数值操作仅限：

```text
formatting
unit conversion
sorting for presentation
plot coordinate placement
rounding for display
```

不得重新计算任何科学指标。

---

# Part I — Input Manifest 与 Display Contract

## 7. Input manifest

生成：

```text
artifacts/a3_1_input_manifest.json
```

记录 A3.1 使用的所有 source artifacts：

```text
path
source_stage
sha256
role
evidence_status
verified
```

至少覆盖：

```text
A1.11 claim matrix
A1.11 main test table
A1.11 benchmark results
A2.3 Table 1–5
A2.1 efficiency summary / relative cost
A2.2 coefficients
A2.2 feature-group evidence
A2.2 metadata summary
A2.2 error manifest / notes
A2.3 evidence-to-paper map
A2.3 figure spec
A2.3 limitations
```

---

## 8. Display precision contract

生成：

```text
artifacts/a3_1_display_contract.json
```

机器源数据保留 exact values。

论文展示值仅格式化：

### Predictive metrics

```text
AP
F1
prevalence
AP lift
CI endpoints
```

显示：

```text
3 decimal places
```

### Efficiency

- latency < 1 ms：最多 4 significant digits；
- latency >= 1 ms：最多 3 significant digits；
- ratios：3 significant digits；
- memory / storage：最多 3 significant digits；
- dimension：integer。

### Coefficients

```text
3 decimal places
```

### Counts

```text
integer
```

任何 display rounding：

```text
不得写回 machine source CSV
```

生成：

```text
artifacts/a3_1_display_value_map.csv
```

必须同时保留：

```text
exact_value
display_value
```

---

# Part II — Final Table Rendering

## 9. 数据源

A3.1 不创建新的科学 table dataset。

唯一数据源为：

```text
artifacts/a2_3_table_1_main_heldout_results.csv
artifacts/a2_3_table_2_efficiency_tradeoff.csv
artifacts/a2_3_table_3_dev_representation_summary.csv
artifacts/a2_3_table_4_benchmark_heterogeneity.csv
artifacts/a2_3_table_5_interpretability_error_summary.csv
```

必须 exact read。

---

## 10. 输出目录

创建：

```text
paper/tables/
```

每张表至少生成：

```text
.tex
.md
```

CSV machine source 不复制成新的科学源。

---

## 11. Table 1 — Main Held-out Results

输出：

```text
paper/tables/Table1_Main_Heldout_Results.tex
paper/tables/Table1_Main_Heldout_Results.md
```

正文主表。

Target 顺序：

```text
Success
Looping
Side Effect
```

必须视觉上区分：

```text
Success / Looping = confirmatory
Side Effect = exploratory
```

Caption contract 必须包含：

```text
official held-out tasks/trajectories
within evaluated benchmark families
Side Effect exploratory
frozen thresholds
```

---

## 12. Table 2 — Efficiency / Complexity

输出：

```text
paper/tables/Table2_Efficiency_Complexity.tex
paper/tables/Table2_Efficiency_Complexity.md
```

必须注明：

```text
measured environment
B2 CPU
B4 CUDA
environment-specific timing
```

表中不得加入跨 target predictive performance comparison。

---

## 13. Table 3 — Dev Representation / Robustness

输出：

```text
paper/tables/Table3_Dev_Representation_Robustness.tex
paper/tables/Table3_Dev_Representation_Robustness.md
```

证据状态必须显式：

```text
DEV_ONLY
```

如果表过宽：

```text
允许拆成 Table3a / Table3b
```

但不得删除核心 evidence status。

---

## 14. Table 4 — Benchmark Heterogeneity

输出：

```text
paper/tables/Table4_Benchmark_Heterogeneity.tex
paper/tables/Table4_Benchmark_Heterogeneity.md
```

必须明确：

```text
DESCRIPTIVE_ONLY
```

不得使用：
- winner；
- best benchmark；
- significantly higher/lower。

---

## 15. Table 5 — Interpretability / Failure Summary

输出：

```text
paper/tables/Table5_Interpretability_Failure_Summary.tex
paper/tables/Table5_Interpretability_Failure_Summary.md
```

Success 放第一行/第一块。

必须注明：

```text
coefficients = associative / diagnostic
metadata comparison = descriptive
error cases = deterministic illustrative cases, not prevalence estimates
```

---

# Part III — Figure Style Contract

## 16. Figure output formats

创建：

```text
paper/figures/
```

每张正式 figure 至少输出：

```text
PDF vector
SVG vector
PNG preview >= 300 dpi
```

PDF/SVG 为 manuscript source of truth。

PNG 仅用于预览。

---

## 17. Journal-neutral visual style

由于目标期刊尚未最终选择，本阶段使用 journal-neutral style。

必须：

- 白底；
- 不使用 3D；
- 不使用阴影特效；
- 不使用渐变；
- 不依赖颜色 alone 区分类别；
- 使用 marker / line style / hatch / text labels 等冗余编码；
- 黑白打印仍可理解；
- 缩放后字号仍可读；
- 轴标签清晰；
- 不在 figure 内放长段结论；
- 不在 figure 内放论文式大标题；
- caption 在独立 contract 中管理。

必须记录实际字体：

```text
artifacts/a3_1_visual_style.json
```

不得嵌入或分发字体文件。

---

## 18. Figure dimensions

使用 journal-neutral 尺寸：

```text
single-column candidate width ≈ 3.4 in
double-column candidate width ≈ 7.0 in
```

多 panel figures 优先：

```text
7.0 in width
```

未来针对具体 journal 允许无科学内容的 resize/reflow。

---

# Part IV — Final Figures

## 19. Figure 1 — Study / Blind-first Pipeline

输出：

```text
paper/figures/Fig1_Study_Pipeline.pdf
paper/figures/Fig1_Study_Pipeline.svg
paper/figures/Fig1_Study_Pipeline.png
```

内容来自 frozen protocol：

```text
raw trajectories
→ leakage-safe cleaned representation
→ grouped dev evaluation
→ method freeze
→ blind prediction
→ label unlock
→ confirmatory held-out evaluation
→ post-freeze A2 efficiency / diagnostics
```

不得画出不存在的训练阶段。

A2 diagnostics 必须视觉上位于 confirmatory pipeline 之后。

---

## 20. Figure 2 — Held-out AP Lift + Frozen 95% CI

输出：

```text
paper/figures/Fig2_Heldout_AP_Lift_CI.pdf
paper/figures/Fig2_Heldout_AP_Lift_CI.svg
paper/figures/Fig2_Heldout_AP_Lift_CI.png
```

Main panel 只：

```text
Success
Looping
```

绘制：

```text
AP lift
frozen 95% CI
zero reference line
```

Side Effect 单独生成附录版：

```text
paper/figures/FigS1_SideEffect_Exploratory_AP_Lift.pdf
paper/figures/FigS1_SideEffect_Exploratory_AP_Lift.svg
paper/figures/FigS1_SideEffect_Exploratory_AP_Lift.png
```

并明确：

```text
EXPLORATORY
```

不得与 FC1/FC2 使用完全相同的 confirmatory visual language。

---

## 21. Figure 3 — Efficiency / Representation Complexity

输出：

```text
paper/figures/Fig3_Efficiency_Complexity.pdf
paper/figures/Fig3_Efficiency_Complexity.svg
paper/figures/Fig3_Efficiency_Complexity.png
```

推荐 3-panel：

### Panel A

```text
Representation dimension
B2 = 13
B4 = 1024
```

### Panel B

```text
Warm extraction ms/trajectory
```

使用 log scale。

### Panel C

```text
Representation storage
```

可使用 log scale。

Caption/annotation 必须注明：

```text
B2 = CPU
B4 = CUDA RTX 5070
timing is environment-specific
```

不得把 classifier-only inference 作为主视觉。

不得写：

```text
B2 universally 176,469× faster
```

只能限定为：

```text
under the measured environment
```

---

## 22. Figure 4 — Structural Interpretation

输出：

```text
paper/figures/Fig4_Structural_Interpretation.pdf
paper/figures/Fig4_Structural_Interpretation.svg
paper/figures/Fig4_Structural_Interpretation.png
```

推荐 2-panel：

### Panel A — Success

```text
Top-5 frozen standardized coefficients by absolute magnitude
```

### Panel B — Looping

同上。

必须保留 coefficient sign。

必须注明：

```text
associative model coefficients
not causal effects
```

---

## 23. Figure 5 — Success Failure Boundaries

输出：

```text
paper/figures/Fig5_Success_Failure_Boundaries.pdf
paper/figures/Fig5_Success_Failure_Boundaries.svg
paper/figures/Fig5_Success_Failure_Boundaries.png
```

禁止做 failure frequency 柱状图。

原因：

> Success error analysis 仅为 deterministic selected 3 FP + 3 FN，不是总体 prevalence sample。

Figure 5 必须是：

```text
illustrative schematic / case taxonomy
```

可用 6 个 case cards 或按已冻结 primary codes 组织。

必须显式标：

```text
6 deterministic illustrative Success errors
not a prevalence estimate
```

不得计算或暗示 failure-mode prevalence。

---

## 24. Appendix Figure — Benchmark Heterogeneity

生成：

```text
paper/figures/FigS2_Benchmark_Heterogeneity.pdf
paper/figures/FigS2_Benchmark_Heterogeneity.svg
paper/figures/FigS2_Benchmark_Heterogeneity.png
```

只绘制 frozen benchmark results。

必须标：

```text
DESCRIPTIVE_ONLY
```

不得加显著性星号、winner rank、pairwise claims。

---

# Part V — Figure Data Manifest

## 25. 生成

```text
artifacts/a3_1_figure_data_manifest.csv
```

每个 plotted datum 至少：

```text
figure_id
panel
series
label
exact_value
display_value
source_artifact
source_row_key
evidence_status
```

Figure 1 schematic 可记录：

```text
value_type = protocol_text
```

Figure 5 case schematic 可记录：

```text
trajectory_key
error_type
case_role
primary_code
source_artifact
```

---

# Part VI — Caption Contract

## 26. 生成

```text
docs/a3_1_figure_table_caption_contract.md
```

为所有 Figure / Table 生成短 caption draft。

Caption 必须：

- 描述展示内容；
- 标明 evidence status；
- 标明关键 scope；
- 标明 environment-specific / dev-only / descriptive / exploratory 边界。

不得在 caption 中引入新的 claim。

---

# Part VII — Visual / Table QA

## 27. Automatic QA

至少验证：

### Data integrity

1. Figure plotted values exact-match source；
2. Table rendered values map to source exact values；
3. rounding follows display contract；
4. no source row silently dropped；
5. Side Effect status preserved；
6. Table 4 remains descriptive；
7. Figure 2 CI values exactly frozen；
8. Figure 3 efficiency source exact；
9. Figure 4 coefficients exact；
10. Figure 5 contains exactly 6 Success error cases。

### Visual QA

11. no clipped labels；
12. no overlapping tick labels；
13. legends visible；
14. raster previews >= 300 dpi；
15. PDF/SVG generated；
16. font recorded；
17. figure dimensions recorded；
18. no blank figure；
19. no 3D / gradient；
20. grayscale/readability check documented。

---

## 28. Human-review contact sheet

生成：

```text
paper/figures/A3_1_Figure_Contact_Sheet.pdf
paper/tables/A3_1_Table_Preview.md
```

Contact sheet 仅用于人工 review，不是论文 artifact。

---

# Part VIII — Artifact Registry / Summary

## 29. Artifact registry

生成：

```text
artifacts/a3_1_artifact_registry.csv
```

字段至少：

```text
artifact_id
artifact_path
artifact_type
paper_role
source_artifacts
sha256
evidence_status
display_contract_version
verified
```

---

## 30. Machine summary

生成：

```text
artifacts/a3_1_run_summary.json
```

至少包含：

```text
stage_determination
input_hashes
output_hashes
figures_generated
tables_generated
appendix_figures_generated
display_contract
visual_style
qa_results

new_model_fits
new_inference_runs
new_embedding_runs
A1_metric_recomputations
bootstrap_reruns
new_significance_tests
threshold_changes
eligibility_changes
final_model_changes
official_test_tuning
external_dataset_runs
```

---

## 31. Stage report

生成：

```text
docs/stage_a3_1_final_figures_tables_report.md
```

至少包含：

1. 阶段判定；
2. commits；
3. frozen gates；
4. input manifest；
5. display contract；
6. visual style；
7. Table 1–5；
8. Figure 1–5；
9. appendix figures；
10. caption contract；
11. QA；
12. artifact registry；
13. warnings；
14. counters；
15. Git condition；
16. next state。

---

## 32. 禁止事项

A3.1 禁止：

```text
任何模型 fit
任何 inference
任何 embedding
重算 AP/F1/AP lift/prevalence/CI
重新 bootstrap
新增显著性检验
重新选择 threshold
修改 eligibility
修改 final model
official-test tuning
外部数据下载/执行
Tier 4 literature verification
修改 A2.3 publication story 的科学 claim
完整 manuscript 写作
根据图形“看起来不好看”删除不利数据
用图形美化隐藏 Side Effect / benchmark heterogeneity
```

---

## 33. Commit discipline

### A3.1a — prereg

```text
chore: preregister A3.1 final figures and tables
```

仅 taskbook，然后 STOP。

### A3.1b — implementation

建议：

```text
chore: implement A3.1 paper artifact renderer
```

### A3.1c — result

```text
docs: freeze A3.1 final figures and tables
```

不得 amend。

如实现失败：

```text
独立 fix commit
```

并保留 failure provenance。

---

## 34. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

必须满足：

```text
all frozen gates pass
5 source paper tables rendered
5 main figures rendered
appendix figures rendered
figure/table source manifests complete
display contract complete
caption contract complete
QA complete
artifact registry complete
all scientific-operation counters = 0
Git final clean
```

### PASS_WITH_CONDITIONS

允许：

```text
某个格式需后续针对具体期刊 resize
Tier 4 caption context 仍待 A3.2 文献核验
少量非科学视觉细节待人工选版
```

不得有数据或 claim inconsistency。

### STOP

包括：

```text
source hash mismatch
plotted value mismatch
table value mismatch
scientific metric recomputation
claim status drift
Side Effect visual misclassification
benchmark heterogeneity 被暗示显著性
Figure 5 被画成 prevalence estimate
Git provenance 不清
```

---

## 35. 最终汇报

Codex 必须汇报：

```text
阶段判定

A3.1 prereg commit
implementation commit
result commit
fix commits
amend

A1.11 claim matrix SHA
A1.11 main table SHA
A2.3 result verification
A2.3 Table 1–5 SHA verification

display contract
visual style / font
figure dimensions

Table 1–5 output paths + hashes

Fig1 path + hash
Fig2 path + hash
Fig3 path + hash
Fig4 path + hash
Fig5 path + hash
FigS1 path + hash
FigS2 path + hash

figure-data manifest status
caption contract status
contact sheet status
artifact registry status

QA passed / failed checks

new_model_fits = 0
new_inference_runs = 0
new_embedding_runs = 0
A1_metric_recomputations = 0
bootstrap_reruns = 0
new_significance_tests = 0
threshold_changes = 0
eligibility_changes = 0
final_model_changes = 0
official_test_tuning = 0
external_dataset_runs = 0

warnings
Git status

report path
machine summary path

WAIT_FOR_HUMAN_A3_1_REVIEW
```

完成后立即停止。

不得自动执行 A3.2。
