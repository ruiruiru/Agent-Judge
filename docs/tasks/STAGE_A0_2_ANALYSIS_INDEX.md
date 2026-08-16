# Stage A0.2：冻结分析单位、重复标注策略与 Benchmark 分组

Stage A0.1 已完成并提交。

本阶段只处理元数据层面的分析单位、重复标注和 Benchmark 分组，不得下载完整轨迹、进行特征工程、训练模型或运行基线。

## 一、读取现有研究产物

必须先读取并遵守：

```text
docs/data_contract.md
artifacts/source_manifest.json
artifacts/metadata_audit.json
artifacts/label_distribution.csv
research/01_DECISION_LOG.md
```

不得修改 Stage A0.1 已经固定的数据版本、标签含义和官方 dev/test 划分。

## 二、确认唯一轨迹主键

根据现有元数据，明确能够唯一标识一条轨迹的字段组合。

不得凭经验猜测主键。

需要检查：

1. 当前“唯一轨迹 1,302 条”使用了哪些字段；
2. 相同主键的记录是否确实只表示第二标注者；
3. 是否存在同一任务和模型对应多次独立运行；
4. 是否存在路径、trajectory ID、run ID 或其他可区分字段；
5. 当前主键是否可能错误地合并不同轨迹。

在报告中明确记录最终采用的：

```text
trajectory_key
```

如果无法从官方字段中可靠确定唯一轨迹主键，立即停止并汇报，不得继续生成分析索引。

## 三、审计重复标注

针对每条唯一轨迹和每个目标标签，分别归类为：

```text
single_annotation
duplicate_agreement
duplicate_disagreement
contains_unsure
```

分别审计：

```text
trajectory_success
trajectory_side_effect
trajectory_looping
```

生成逐轨迹审计表，至少包含：

```text
trajectory_key
benchmark
task_id
model_name
annotator_count
success_values
side_effect_values
looping_values
success_status
side_effect_status
looping_status
```

同时检查官方代码、README 或数据说明中是否存在以下规则：

* 主标注者；
* adjudicated label；
* 标注者优先级；
* 官方合并方式；
* 对分歧标注的推荐处理。

只有官方材料明确说明时，才能使用官方规则。不得根据 CSV 行顺序假定第一行为主标注。

## 四、冻结主实验标签处理规则

如官方不存在明确的 adjudication 或主标注规则，主实验采用以下保守策略。

### 单标注轨迹

有效二分类标签正常保留。

### 多标注且完全一致

折叠为一条唯一轨迹，只保留一个标签，不得因为存在两个标注者而重复计权。

### 多标注存在分歧

对发生分歧的目标标签设为不可用，并从该目标的训练与评价中排除。

排除必须按目标分别执行。

例如：

* Success 存在分歧；
* Looping 完全一致；

则该轨迹只从 Success 数据中排除，仍可用于 Looping。

### 含 Unsure

只要某目标的标注集合中出现 `Unsure`，主实验中该轨迹的对应目标标签设为不可用。

不得将 `Unsure` 映射为 0 或 1。

### 禁止事项

不得：

* 通过多数投票解决两个标注者的一比一分歧；
* 随机选择其中一个标注；
* 使用 CSV 第一行作为默认真值；
* 把重复标注当成两条独立轨迹；
* 因一个目标存在分歧而删除该轨迹的全部其他目标。

## 五、建立 Benchmark 命名空间

每条轨迹必须同时保留三种字段。

### 原始标注字段

```text
benchmark_original
```

保持 annotations.csv 中的原始值，例如：

```text
workarena
```

### 官方 split 命名空间

```text
benchmark_split_namespace
```

根据 `splits.csv` 映射，例如：

```text
workarena_l1
workarena_l2
```

不得仅根据任务名称字符串猜测，必须使用官方映射。

### 主实验 Benchmark 分组

```text
benchmark_group_primary
```

主实验暂定采用四个环境级 Benchmark，并将：

```text
workarena_l1
workarena_l2
```

合并为：

```text
workarena
```

理由是主实验研究跨 Benchmark 泛化，不应把同一环境的两个难度或任务层级默认当成两个完全独立领域。

其他 Benchmark 保持原命名。

### 敏感性分析分组

额外生成：

```text
benchmark_group_secondary
```

该字段保留五个官方 split 命名空间，将：

```text
workarena_l1
workarena_l2
```

作为两个独立组。

该分组暂时只作为后续敏感性分析候选，不得替代主实验分组。

## 六、检查 WorkArena 映射

必须报告：

1. WorkArena L1 和 L2 的任务数量；
2. 两组是否存在重复 task_id；
3. 每组包含的唯一轨迹数；
4. 每组涉及哪些模型；
5. 三个标签在两组中的有效正负类数量；
6. 合并前后对类别分布的影响；
7. 是否发现 L1/L2 实际并非难度或任务层级，而是其他语义。

如果官方材料表明 L1/L2 不是同一 Benchmark 的子层级，应停止并汇报，不得继续冻结四组主方案。

## 七、生成分析索引

建立一行对应一条唯一轨迹的元数据索引。

至少包含：

```text
trajectory_key
benchmark_original
benchmark_split_namespace
benchmark_group_primary
benchmark_group_secondary
task_id
model_name
official_split
annotation_count
success_label
success_status
side_effect_label
side_effect_status
looping_label
looping_status
```

标签不可用时使用缺失值，并通过对应的 `*_status` 说明原因。

不得把同一条轨迹拆成三行，也不得为第二标注者创建额外训练样本。

## 八、test 封存

Stage A0.1 已经为了数据审计查看过 test 的聚合标签分布。必须在决策日志中记录：

```text
Test labels received aggregate, audit-only exposure during Stage A0.1.
No model, feature, threshold, hyperparameter, or research decision was tuned using test performance.
```

从本阶段结束后：

* 只生成带标签的 dev 分析索引；
* test 清单默认只保留标识符和分组信息；
* 不在常规开发文件中输出逐条 test 标签；
* 不运行任何 test 指标；
* 不根据 test 类别分布修改模型、阈值或特征。

完整 test 标签只能由最终锁定的评价流程读取。

## 九、统计输出

分别报告三个目标在以下范围内的有效样本数：

```text
dev
test
每个 benchmark_group_primary
每个 benchmark_group_secondary
每个模型
```

同时报告：

* 单标注数量；
* 重复一致数量；
* 重复分歧数量；
* 含 Unsure 数量；
* 折叠重复记录前后的行数；
* 每个目标最终可用的唯一轨迹数；
* 每个目标的正类率。

不得进行重采样、类别加权或阈值选择。

## 十、产物

生成：

```text
docs/analysis_unit_policy.md
artifacts/duplicate_annotation_audit.csv
artifacts/dev_analysis_index.csv
artifacts/test_manifest.csv
artifacts/analysis_index_summary.json
scripts/build_analysis_index.py
```

其中：

* `dev_analysis_index.csv` 可以包含经过固定规则处理后的 dev 标签；
* `test_manifest.csv` 不得包含三个目标的逐条标签；
* `duplicate_annotation_audit.csv` 仅用于审计，不得直接作为训练数据；
* 脚本必须从固定版本的原始小文件可复现生成全部产物。

## 十一、阶段判定

完成后给出以下结论之一：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

通过条件：

1. 唯一轨迹主键明确；
2. 重复标注可以无歧义地折叠；
3. 分歧标签可以按目标排除；
4. 所有轨迹能够映射 Benchmark 分组；
5. dev 分析索引中不存在重复轨迹；
6. test manifest 不包含逐条目标标签；
7. 没有进入完整轨迹下载或模型实验。

## 十二、约束

本阶段禁止：

* 下载完整 Hugging Face 数据；
* 下载截图；
* 解析完整轨迹内容；
* 构建文本、图像或结构特征；
* 训练任何分类器或 Judge；
* 运行基线；
* 计算 test 模型指标；
* 重采样或生成合成样本；
* 修改研究假设；
* 根据类别不平衡提前选择模型。

## 十三、提交

完成后：

1. 更新决策日志；
2. 展示所有生成文件；
3. 汇报审计统计与异常；
4. 执行测试，验证分析索引可重复生成；
5. 执行 `git status`；
6. 提交一次 Git commit：

```text
chore: freeze analysis unit and benchmark groups
```
