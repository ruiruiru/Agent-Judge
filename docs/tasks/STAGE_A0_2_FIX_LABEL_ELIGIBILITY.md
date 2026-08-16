# Stage A0.2-Fix：修正标签有效性与主实验资格判定

Stage A0.2 的分析单位、重复记录折叠、Benchmark 分组和 test 封存主体已完成。

当前发现阻塞性问题：报告中的“有效轨迹数”与重复分歧及 Unsure 排除策略不一致。

本任务只允许核查并修正标签资格判定，不得下载完整轨迹、构建特征、训练模型或运行基线。

## 一、核查当前实现

读取：

```text
docs/analysis_unit_policy.md
artifacts/duplicate_annotation_audit.csv
artifacts/dev_analysis_index.csv
artifacts/analysis_index_summary.json
scripts/build_analysis_index.py
tests/test_build_analysis_index.py
research/01_DECISION_LOG.md
```

检查以下问题：

1. `duplicate_disagreement` 对应的目标标签是否仍保留了 primary 值；
2. `contains_unsure` 对应的目标标签是否仍保留了 0 或 1；
3. 当前“有效轨迹数”的计算条件是什么；
4. 后续训练是否可能仅通过 `label.notna()` 纳入分歧样本；
5. `*_status` 和 `*_label` 是否存在语义不一致。

在报告中明确指出根因。

## 二、主实验标签规则

对每个目标分别处理：

```text
success
side_effect
looping
```

### 可以进入主实验

仅允许：

```text
single_annotation
duplicate_agreement
```

且标签必须是明确的二分类值 0 或 1。

### 不得进入主实验

以下状态对应的主实验标签必须设置为空值：

```text
duplicate_disagreement
contains_unsure
```

不得使用：

* CSV 首次出现的 primary 标签；
* 随机标注者标签；
* 多数投票处理两个标注者的一比一分歧；
* 将 Unsure 转换为 0 或 1。

官方 primary 标签可以保留在审计文件中，用于说明官方评分实现，但不得作为主实验训练标签。

## 三、明确区分三个概念

每个目标至少需要以下字段：

```text
<target>_label
<target>_status
<target>_eligible_main
```

规则如下：

```text
single_annotation:
    label = 0 或 1
    eligible_main = true

duplicate_agreement:
    label = 一致的 0 或 1
    eligible_main = true

duplicate_disagreement:
    label = 空值
    eligible_main = false

contains_unsure:
    label = 空值
    eligible_main = false
```

可以在 `duplicate_annotation_audit.csv` 中额外保留：

```text
<target>_primary_label_audit_only
```

但该字段不得出现在训练接口中，也不得用于计算主实验样本数和正类率。

## 四、重新计算统计

基于 1,302 条唯一轨迹，重新报告：

1. 单标注轨迹数；
2. 重复一致轨迹数；
3. 重复分歧轨迹数；
4. 含 Unsure 轨迹数；
5. 每个目标的主实验有效轨迹数；
6. 每个目标被排除的唯一轨迹数；
7. 每个目标排除后的正负类数量和正类率；
8. dev 内每个目标的有效轨迹数；
9. 每个 `benchmark_group_primary` 的有效样本和类别分布；
10. 每个模型的有效样本和类别分布。

按照当前报告中的互斥状态数量，预期主实验有效轨迹数应为：

```text
Success:     1302 - 12 - 1 = 1289
Side Effect: 1302 - 4 - 1  = 1297
Looping:     1302 - 11     = 1291
```

如果重新计算结果不是上述数字，必须逐条说明：

* 状态是否存在重叠；
* 哪些轨迹产生重叠；
* 为什么不能直接相减；
* 最终去重后的排除数量。

不得为了符合预期数字而硬编码统计。

## 五、增加强制断言

在脚本和测试中加入：

```text
eligible_main == true  -> label 必须为 0 或 1
eligible_main == false -> label 必须为空
duplicate_disagreement -> eligible_main 必须为 false
contains_unsure        -> eligible_main 必须为 false
```

并验证：

```text
有效唯一轨迹数 + 被排除唯一轨迹数 = 1302
```

该等式按每个目标分别验证。

同时继续验证：

* `trajectory_key` 唯一；
* dev 分析索引无重复；
* test manifest 不含任何标签、资格状态或原始标注值；
* 重复生成结果完全一致。

## 六、检查下游误用风险

搜索整个项目，检查是否存在：

```text
dropna(label)
label.notna()
fillna(0)
fillna(1)
primary_label
first()
iloc[0]
```

等可能让分歧标注重新进入训练的逻辑。

当前如果尚无训练代码，也要在 `docs/analysis_unit_policy.md` 中明确规定：

```text
后续任何训练集构建必须同时要求：
<target>_eligible_main == true
并且
<target>_label in {0, 1}
```

不得只依赖标签非空。

## 七、更新产物

至少更新：

```text
docs/analysis_unit_policy.md
artifacts/dev_analysis_index.csv
artifacts/analysis_index_summary.json
scripts/build_analysis_index.py
tests/test_build_analysis_index.py
research/01_DECISION_LOG.md
```

如有必要，同步更新：

```text
artifacts/duplicate_annotation_audit.csv
```

不得向 `test_manifest.csv` 添加任何标签或标签状态。

## 八、阶段判定

修正完成后，只能给出：

```text
PASS
STOP
```

PASS 条件：

1. 分歧和 Unsure 标签在主实验索引中均为空；
2. 对应 `eligible_main` 均为 false；
3. 有效样本数与状态统计一致；
4. 正类率基于排除后的唯一轨迹计算；
5. 测试能够阻止分歧样本进入训练；
6. test manifest 继续保持无标签；
7. 未进入完整轨迹下载、特征工程或模型实验。

## 九、提交

运行全部测试并汇报：

* 问题根因；
* 修正前后有效样本数；
* 修正后的类别分布；
* 测试结果；
* 修改文件；
* `git status`。

创建新的 Git commit：

```text
fix: enforce consensus label eligibility
```

不要 amend 或覆盖 Stage A0.2 原提交，以保留完整审计历史。
