# Stage A1.0：流式构建完整 Dev 无泄漏轨迹语料

Stage A0 已完成。

本阶段允许从固定 Hugging Face revision 下载全部196条 dev 文本轨迹，按照已经冻结的输入契约逐文件校验、解析、清洗和压缩。

本阶段不得下载 test、截图或无关文件，不得提取模型特征、训练模型或运行基线。

## 一、固定版本与前置文件

必须继续使用：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

必须先读取并遵守：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/trajectory_schema_probe.md
docs/input_contract.md

artifacts/source_manifest.json
artifacts/dev_analysis_index.csv
artifacts/test_manifest.csv
artifacts/dev_probe_manifest.csv
artifacts/input_field_policy.csv
artifacts/input_contract_summary.json

research/01_DECISION_LOG.md
```

不得修改：

* 标签定义；
* 重复标注处理规则；
* 官方dev/test；
* Benchmark主分组；
* 字段白名单；
* 永久排除字段；
* 三种输入视图；
* reasoning和自然错误处理规则。

## 二、本阶段目标

只回答：

1. 196条dev轨迹能否全部稳定下载和解析；
2. 全量dev是否出现探针阶段未发现的新字段或结构；
3. 共享cleaned-schema是否适用于全部dev；
4. 全量清洗后语料有多大；
5. 三种输入视图的完整覆盖情况；
6. 各Benchmark、模型和标签对应的轨迹长度分布；
7. 正式开发语料是否可以进入基线阶段。

不得回答模型效果问题。

## 三、数据范围

唯一允许下载的轨迹必须来自：

```text
artifacts/dev_analysis_index.csv
```

预期唯一轨迹数：

```text
196
```

脚本必须在下载前验证：

```text
official_split == "dev"
trajectory_key 唯一
repository_path 唯一且可解析
```

严禁：

* 根据test manifest定位或下载文件；
* 下载任何test轨迹；
* 下载截图、图像、视频或HTML资源；
* 下载judgment或人工标注文件作为轨迹输入；
* 使用Hugging Face整库snapshot下载；
* 下载包含无关文件的完整压缩包。

## 四、流式构建流程

必须逐文件执行：

```text
读取下一条dev manifest
→ 固定revision下载单个JSON
→ 校验文件大小和SHA-256
→ 解析JSON
→ 执行字段白名单和泄漏检查
→ 转换为cleaned-schema
→ 生成三种序列化输入
→ 写入临时输出
→ 记录处理状态
→ 释放原始对象和内存
→ 删除或保留在被忽略的临时缓存
```

不得先将整个3.65GB数据全部加载进内存。

不得一次性将196条原始JSON合并后再解析。

## 五、下载与断点恢复

建立确定性的处理状态文件。

每条轨迹至少记录：

```text
trajectory_key
repository_path
source_revision
expected_size_bytes
actual_size_bytes
source_sha256
download_status
parse_status
clean_status
view_status
attempt_count
error_type
error_message
processed_at
```

支持中断后恢复：

* 已完成且SHA一致的轨迹不得重复处理；
* 下载不完整的临时文件不得当作成功；
* 失败记录不得静默跳过；
* 恢复后最终输出必须与一次性完整执行逐字节一致。

允许使用类似目录：

```text
data/dev_download_cache/
data/dev_build_temp/
```

这些目录必须被 `.gitignore` 排除。

## 六、原始文件保留策略

默认优先采用：

```text
下载单文件
→ 校验
→ 清洗
→ 写入紧凑数据
→ 删除本地原始副本
```

必须长期保留：

* 固定revision；
* 仓库路径；
* 原始文件大小；
* 原始SHA-256；
* 处理状态；
* 清洗后输出。

不得提交原始轨迹到Git。

如果Hugging Face本地缓存无法安全按文件清理，应明确记录实际磁盘占用，不得声称已经删除。

## 七、严格遵守输入契约

主白名单仅允许使用：

```text
goal
steps[].action
steps[].axtree_pruned
steps[].focused_element
steps[].last_action_error
```

reasoning仅允许进入：

```text
sensitivity_with_reasoning
```

永久排除：

```text
summary_info
cum_reward
cum_raw_reward
所有reward、score、label、judge、annotation、success、
failure、side effect、looping等结果语义字段
截图路径
图像占位符
图像内容
base64
未批准的新字段
```

身份信息只能作为管理元数据，三种输入文本不得包含：

```text
benchmark
agent
model
experiment
task_id
trajectory_key
split
repository_path
```

## 八、未知字段和结构漂移

对196条轨迹执行递归字段检查。

如果发现不在：

```text
artifacts/input_field_policy.csv
```

中的新字段：

1. 默认拒绝进入所有输入视图；
2. 记录字段路径、类型、出现数量和短样例；
3. 记录涉及的Benchmark和模型；
4. 标记为 `manual_review_required`；
5. 不得自动扩展白名单；
6. 不得因为未知字段而删除整条轨迹。

如果新字段影响基础解析，可以继续处理已知白名单字段，但阶段判定必须为 `PASS_WITH_CONDITIONS`。

如果出现与当前cleaned-schema完全不兼容的结构，停止该轨迹并显式报告。

## 九、Terminal规则

继续生成：

```text
last_nonempty_action
last_nonempty_observation
last_step_index
termination_signal
```

其中：

* 只能来自原始字段；
* 缺失必须保持null；
* 不得从reward、标签或任务结果推断；
* `termination_signal` 仅识别已批准的原始动作；
* 不得创建 `final_response`；
* 不得把terminal字段再次序列化为重复文本。

如果最后一个有效action或observation已经出现在steps中，terminal只用于结构化索引和质量审计。

## 十、生成正式语料

生成一行一条唯一轨迹的：

```text
data/processed/dev_cleaned_trajectories.jsonl
data/processed/dev_serialized_primary.jsonl
data/processed/dev_serialized_error_ablation.jsonl
data/processed/dev_serialized_reasoning_sensitivity.jsonl
```

建议每个序列化文件至少包含：

```text
trajectory_key
input_view
serialized_text
content_sha256
```

不得包含标签。

标签继续独立保存在：

```text
artifacts/dev_analysis_index.csv
```

后续只能通过 `trajectory_key` 连接。

## 十一、输入和标签物理隔离

构建语料的脚本接口不得接收：

```text
success_label
side_effect_label
looping_label
eligible_main
annotation status
```

不得根据标签：

* 截断轨迹；
* 选择步骤；
* 删除错误；
* 改变序列化格式；
* 选择输入字段；
* 设置最大长度；
* 决定是否保留样本。

本阶段可以读取 `dev_analysis_index.csv` 中的标识符和路径信息，但构建函数不得访问目标标签列。

## 十二、完整性统计

必须报告：

### 文件处理

* dev预期轨迹数；
* 成功定位数；
* 成功下载数；
* 成功校验数；
* 成功解析数；
* 成功清洗数；
* 三种视图成功生成数；
* 失败和跳过数量；
* 原始总字节；
* 实际下载字节；
* 本地缓存峰值占用。

### 结构

* 总步骤数；
* 每条轨迹步骤数的最小值、中位数、平均值、最大值；
* 空action数量；
* 空observation数量；
* 空focused_element数量；
* reasoning可用轨迹数及步骤数；
* 自然错误可用轨迹数及步骤数；
* terminal action覆盖率；
* terminal observation覆盖率；
* termination signal种类和数量；
* 截图引用轨迹数；
* 未知字段数量。

### 紧凑体积

分别报告：

* cleaned结构化JSONL体积；
* primary体积；
* error ablation体积；
* reasoning sensitivity体积；
* 原始到cleaned压缩率；
* 原始到各视图压缩率。

### 分组统计

可以通过 `trajectory_key` 在统计阶段连接非标签元数据，分别报告：

* 每个Benchmark的轨迹数和长度；
* 每个模型的轨迹数和长度；
* WorkArena L1/L2的轨迹数和长度。

不得在本阶段计算标签与文本字段的相关性。

## 十三、自然错误消融资格检查

报告完整196条dev中：

```text
has_natural_error == true
```

的：

* 轨迹数量；
* 步骤数量；
* Benchmark分布；
* 模型分布。

阶段内只进行覆盖统计。

如果自然错误轨迹极少，不删除该视图，但在报告中标记：

```text
error ablation may be underpowered
```

不得根据数量决定模型结果或研究结论。

## 十四、输出产物

生成：

```text
docs/dev_corpus_build_report.md

artifacts/dev_corpus_manifest.csv
artifacts/dev_corpus_summary.json
artifacts/dev_schema_drift.csv
artifacts/dev_build_failures.csv

data/processed/dev_cleaned_trajectories.jsonl
data/processed/dev_serialized_primary.jsonl
data/processed/dev_serialized_error_ablation.jsonl
data/processed/dev_serialized_reasoning_sensitivity.jsonl

scripts/build_full_dev_corpus.py
tests/test_build_full_dev_corpus.py
```

更新：

```text
research/01_DECISION_LOG.md
.gitignore
```

大型生成文件是否提交Git，必须依据仓库现有数据管理规则决定。不得擅自提交超大文件。

## 十五、测试要求

至少验证：

1. 输入清单恰好包含196条唯一dev轨迹；
2. 不包含test trajectory key；
3. 所有下载均固定到指定HF revision；
4. 不使用整库snapshot下载；
5. 共享adapter处理所有成功轨迹；
6. 输出中不存在summary_info；
7. 输出中不存在reward或标签语义字段；
8. 三种输入文本不包含身份字段；
9. primary和error ablation不包含reasoning；
10. reasoning视图只使用原始存在的reasoning；
11. error ablation删除自然错误字段；
12. terminal不重复序列化最后一步；
13. 缺失terminal保持null；
14. 未知字段默认拒绝；
15. 标签列无法进入构建函数；
16. 每种视图trajectory key唯一；
17. 三种视图与cleaned结构数量一致；
18. 中断恢复后的输出逐字节一致；
19. 原始缓存不被Git跟踪；
20. 重复完整执行输出确定。

## 十六、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

满足：

* 196条dev全部唯一定位；
* 全部成功解析和清洗；
* 未发现阻塞性结构漂移；
* reward和标签完全隔离；
* 三种视图完整生成；
* test未被访问；
* 流式构建可重复；
* 正式语料可以进入基线阶段。

### PASS_WITH_CONDITIONS

例如：

* 少量轨迹下载或解析失败；
* 出现未进入输入的新字段；
* 部分terminal持续缺失；
* 自然错误样本过少；
* 个别结构需要显式空值处理。

### STOP

例如：

* 大量dev无法解析；
* 出现无法隔离的结果泄漏；
* 共享adapter无法覆盖主要Benchmark；
* test文件被访问；
* 标签进入输入构建过程；
* 清洗结果无法确定性复现。

## 十七、禁止事项

本阶段禁止：

* 下载test；
* 下载截图；
* 下载完整HF仓库；
* 修改字段白名单；
* 修改标签策略；
* 进行TF-IDF、BM25或Embedding提取；
* 调用大语言模型；
* 训练分类器；
* 运行预测基线；
* 计算Accuracy、F1、AUROC等模型指标；
* 根据标签分布修改输入；
* 根据样本内容手工挑选“好样本”。

## 十八、提交

完成后汇报：

* 阶段判定；
* 196条处理覆盖率；
* 实际下载体积；
* 清洗后体积；
* 结构漂移；
* terminal覆盖率；
* reasoning与自然错误覆盖率；
* 泄漏检查；
* 测试结果；
* 修改文件；
* commit；
* git status。

创建新提交：

```text
chore: build leak-safe full dev corpus
```

不得amend或覆盖历史提交。
