# Stage A1.2：运行 Task-Grouped 第一轮最小基线

Stage A1.1 及其协议补丁已经通过。

本阶段是项目第一次运行真实预测实验，只允许在冻结的 dev task-grouped 五折划分上运行 B0–B3 最小基线。

本阶段禁止访问 test，禁止运行 LOBO、Leave-One-Model-Out、reasoning 敏感性、自然错误消融、大语言模型 Judge、Embedding 模型或 Transformer 微调。

---

## 一、前置状态

必须继续使用固定数据版本：

```text
GitHub commit:
f838338886d723d40b586309465a38277803d9e6

Hugging Face revision:
b6d17e646009d6cb63d5dd7be78807b680693f61
```

必须先读取：

```text
docs/data_contract.md
docs/analysis_unit_policy.md
docs/input_contract.md
docs/dev_corpus_build_report.md
docs/evaluation_protocol.md
docs/pre_baseline_audit_report.md

artifacts/dev_analysis_index.csv
artifacts/dev_corpus_summary.json
artifacts/pre_baseline_summary.json

artifacts/evaluation_folds_success.csv
artifacts/evaluation_folds_side_effect.csv
artifacts/evaluation_folds_looping.csv

configs/evaluation_protocol.yaml
configs/baseline_registry.yaml

research/01_DECISION_LOG.md
```

正式输入固定为：

```text
data/processed/dev_cleaned_trajectories.jsonl
data/processed/dev_serialized_primary.jsonl
```

不得使用：

```text
data/processed/dev_serialized_error_ablation.jsonl
data/processed/dev_serialized_reasoning_sensitivity.jsonl
```

---

## 二、本阶段目标

本阶段只回答：

1. 多数类和先验基线能达到什么水平；
2. 仅使用轻量结构统计是否存在预测信号；
3. 使用无泄漏轨迹文本的 TF-IDF 是否存在预测信号；
4. Success、Side Effect、Looping 三个任务的难度是否不同；
5. 文本基线相对于结构基线和类别先验是否获得稳定提升；
6. 当前最小实验是否值得进入后续 LOBO、消融或更复杂模型阶段。

本阶段结果仅代表：

```text
官方 dev
+
task-grouped 五折 OOF 评估
```

不得表述为最终 test 性能或跨 Benchmark 泛化能力。

---

## 三、不可修改的评估划分

后续实验唯一权威划分为：

```text
artifacts/evaluation_folds_success.csv
artifacts/evaluation_folds_side_effect.csv
artifacts/evaluation_folds_looping.csv
```

实际划分算法记录为：

```text
custom_deterministic_grouped_stratification_v1
```

该算法实现：

```text
group-aware
approximate stratification
deterministic
```

本阶段不得：

* 调用新的划分器；
* 重新生成 fold；
* 使用 scikit-learn 重新构造 StratifiedGroupKFold；
* 修改任何轨迹的 outer fold；
* 修改 inner train / inner validation；
* 将同一任务拆到不同 fold；
* 根据模型结果调整 fold。

运行前必须校验三个 fold manifest 的冻结 SHA-256。

如 SHA-256 不匹配，立即停止，不得运行模型。

---

## 四、目标数据

分别运行三个独立二分类任务。

### Success

预期：

```text
有效样本：192
正类：58
负类：134
外层 folds：5
```

资格条件：

```text
success_eligible_main == true
success_label in {0, 1}
```

### Side Effect

预期：

```text
有效样本：195
正类：12
负类：183
外层 folds：5
```

资格条件：

```text
side_effect_eligible_main == true
side_effect_label in {0, 1}
```

正类表示存在副作用，不得反转。

### Looping

预期：

```text
有效样本：196
正类：92
负类：104
外层 folds：5
```

资格条件：

```text
looping_eligible_main == true
looping_label in {0, 1}
```

每个目标必须单独连接标签。

不得使用：

* primary audit label；
* duplicate disagreement；
* Unsure；
* 不符合 `eligible_main` 的标签；
* test标签；
* 聚合 test 分布。

---

## 五、输入与标签连接

输入只能通过：

```text
trajectory_key
```

与：

```text
artifacts/dev_analysis_index.csv
```

连接。

必须验证：

1. 输入中的 `trajectory_key` 唯一；
2. 标签索引中的 `trajectory_key` 唯一；
3. 每个目标连接后的样本数符合预期；
4. 所有样本均属于官方 dev；
5. 不包含任何 test trajectory key；
6. 输入文本自身不含标签；
7. 标签不参与文本构建或结构特征提取；
8. 不得根据标签修改、截断或筛选输入。

---

## 六、运行环境

当前环境此前未安装 scikit-learn。

允许为本阶段创建项目本地独立环境，例如：

```text
.venv-baselines/
```

该目录必须加入 `.gitignore`。

只允许安装运行本阶段所必需的依赖，例如：

```text
scikit-learn
PyYAML
```

及其自动解析的必要依赖。

要求：

1. 不升级或修改项目无关依赖；
2. 不安装深度学习框架；
3. 不安装大语言模型或 Embedding 依赖；
4. 不使用 GPU；
5. 正式运行过程中不访问网络；
6. 记录 Python 版本、操作系统和所有依赖精确版本；
7. 将独立环境的精确依赖冻结到：

```text
requirements/baseline-lock.txt
```

生成：

```text
artifacts/baseline_environment.json
```

如果依赖无法安全安装，判定为 STOP，不得自行实现未经审查的替代分类器。

---

## 七、两阶段执行与提交约束

Stage A1.2 必须分为两个子阶段。

### A1.2a：运行前冻结

在任何真实 dev 模型训练前完成：

* 运行配置；
* 特征定义；
* 候选超参数；
* 选择规则；
* 阈值规则；
* 指标实现；
* 结果文件格式；
* 测试；
* manifest及输入哈希验证。

只允许使用合成数据运行单元测试，不得在真实 dev 上调用 `.fit()`。

完成后创建提交：

```text
chore: preregister minimal grouped baselines
```

### A1.2b：正式执行

运行前确认：

```text
git status
```

工作区必须干净。

正式开始后：

* 不得修改代码；
* 不得修改运行配置；
* 不得修改候选超参数；
* 不得修改特征；
* 不得修改指标；
* 不得修改阈值候选；
* 不得修改 fold。

如发现实现错误：

1. 立即停止；
2. 保留失败日志；
3. 不得查看或选择性汇报已有结果；
4. 创建单独修正提交；
5. 从头重新执行全部目标和基线；
6. 在决策日志记录原因。

不得一边查看结果一边修改模型。

正式结果完成后创建提交：

```text
experiment: run grouped minimal dev baselines
```

不得 amend 运行前冻结提交。

---

## 八、第一轮基线

只运行四个基线：

```text
B0_dummy_most_frequent
B1_dummy_prior
B2_structural_lr
B3_tfidf_lr
```

不得临时添加第五个模型。

---

## 九、B0：多数类基线

实现：

```python
DummyClassifier(
    strategy="most_frequent"
)
```

要求：

* 每个外层 fold 只根据 outer train 拟合；
* inner阶段不得访问 outer validation；
* 正类概率必须通过 `predict_proba` 的类别索引获取；
* 不得手工使用完整 dev 类别比例；
* 使用统一阈值选择流程；
* 保存全部 OOF 概率。

B0用于建立类别不平衡下的最低参照。

---

## 十、B1：先验概率基线

实现：

```python
DummyClassifier(
    strategy="prior"
)
```

要求：

* 类别先验只能来自相应训练部分；
* 不得使用完整 dev 正类率；
* 使用概率和统一阈值流程生成预测；
* 不得使用随机 stratified dummy 代替；
* 运行必须确定性。

B1用于确认仅凭训练集正类先验能够达到的 PR-AUC 和阈值表现。

---

## 十一、B2：轻量结构特征 Logistic Regression

B2只能读取：

```text
data/processed/dev_cleaned_trajectories.jsonl
```

不得读取标签、身份字段或原始大文件来构造特征。

### 冻结结构特征

严格使用以下特征及顺序：

```text
1. step_count
2. nonempty_action_count
3. nonempty_observation_count
4. nonempty_focused_element_count
5. natural_error_step_count
6. natural_error_step_ratio
7. has_explicit_termination_signal
8. action_char_count_total
9. observation_char_count_total
10. action_char_count_mean_nonempty
11. observation_char_count_mean_nonempty
12. unique_action_ratio
13. consecutive_duplicate_action_count
```

### 特征定义

#### step_count

`steps[]` 的实际步骤数。

#### nonempty_action_count

非空 action 的步骤数量。

#### nonempty_observation_count

非空 observation 的步骤数量。

#### nonempty_focused_element_count

非空 focused_element 的步骤数量。

#### natural_error_step_count

`last_action_error` 非空的步骤数量。

#### natural_error_step_ratio

```text
natural_error_step_count / step_count
```

如果 `step_count == 0`，固定为0。

#### has_explicit_termination_signal

原始轨迹存在冻结批准的：

```text
send_msg_to_user
report_infeasible
```

时为1，否则为0。

不得根据最后一步、reward或标签补齐。

#### action_char_count_total

所有非空 action 原始文本字符数之和。

#### observation_char_count_total

所有非空 observation 原始文本字符数之和。

#### action_char_count_mean_nonempty

```text
action_char_count_total / nonempty_action_count
```

分母为0时固定为0。

#### observation_char_count_mean_nonempty

```text
observation_char_count_total / nonempty_observation_count
```

分母为0时固定为0。

#### unique_action_ratio

对非空 action 执行：

```text
去除首尾空白
折叠连续空白
保持原始字符大小写
```

然后计算：

```text
唯一 action 数 / 非空 action 数
```

无非空 action 时固定为0。

#### consecutive_duplicate_action_count

相邻两个非空 action 经上述空白标准化后完全相同的次数。

不得使用语义相似模型或 Embedding 判断重复。

### 禁止的结构特征

不得使用：

* benchmark；
* model_name；
* agent；
* experiment；
* task_id；
* trajectory_key编码；
* 文件路径；
* reward；
* summary_info；
* reasoning存在性或长度；
* test统计；
* 标签条件统计；
* 原始annotation；
* 截图数量或路径；
* terminal最后一步文本的重复副本。

### B2处理流程

使用：

```text
StandardScaler
+
LogisticRegression
```

`StandardScaler` 只能在相应训练部分拟合。

不得在完整 dev 上提前拟合缩放器。

Logistic Regression固定：

```text
penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026
```

候选：

```text
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共6个候选配置。

---

## 十二、B3：TF-IDF Logistic Regression

B3只能读取：

```text
data/processed/dev_serialized_primary.jsonl
```

即：

```text
primary_with_natural_errors
```

不得使用 reasoning、error ablation、身份字段或原始JSON。

### 冻结 TF-IDF 配置

只允许两个候选文本表示。

#### T1：word unigram

```text
ngram_range = (1, 1)
```

#### T2：word unigram + bigram

```text
ngram_range = (1, 2)
```

两者共同固定：

```text
lowercase = true
strip_accents = unicode
min_df = 2
max_df = 1.0
max_features = 20000
sublinear_tf = true
norm = l2
use_idf = true
smooth_idf = true
token_pattern = (?u)\b\w\w+\b
```

不得加入：

* char n-gram；
* 自定义停用词；
* 词干化；
* 词形还原；
* 中文分词器；
* 语义Embedding；
* 文本摘要；
* 文本截断；
* 标签条件词表；
* 全dev预拟合词表。

TF-IDF必须在每个训练部分单独拟合。

inner validation 和 outer validation 中独有的词不得进入训练词表。

### Logistic Regression

固定：

```text
penalty = l2
solver = liblinear
max_iter = 5000
fit_intercept = true
random_state = 2026
```

候选：

```text
TF-IDF ∈ {T1, T2}
C ∈ {0.1, 1.0, 10.0}
class_weight ∈ {None, balanced}
```

共12个候选配置。

不得根据 outer validation 结果增加配置。

---

## 十三、每个外层 fold 的固定执行顺序

对每个：

```text
target × baseline × outer_fold
```

严格执行：

```text
1. 读取冻结 manifest
2. 取得 inner_train
3. 取得 inner_validation
4. 在 inner_train 拟合候选配置
5. 在 inner_validation 计算 PR-AUC
6. 选择 inner validation PR-AUC 最高的配置
7. 在选中配置的 inner validation 概率上选择分类阈值
8. 使用选中配置在完整 outer_train 重新拟合
9. 使用已冻结阈值在 outer_validation 评估一次
10. 保存 outer validation 概率和指标
```

不得在步骤9后返回修改步骤4—7。

---

## 十四、超参数选择

模型配置选择指标固定为：

```text
inner validation PR-AUC
```

本项目中的 PR-AUC 实现固定为：

```python
sklearn.metrics.average_precision_score
```

报告中应同时标注：

```text
PR-AUC / Average Precision
```

不得在同一实验中切换为梯形积分 PR 曲线面积。

### 配置同分处理

如果多个配置 inner PR-AUC 完全相同，固定采用更简单配置。

#### B2优先级

1. `class_weight=None` 优先于 `balanced`；
2. 更小的 C 优先：

```text
0.1 → 1.0 → 10.0
```

3. 最后按 `config_id` 字典序。

#### B3优先级

1. unigram优先于 unigram+bigram；
2. `class_weight=None` 优先于 `balanced`；
3. C优先级：

```text
0.1 → 1.0 → 10.0
```

4. 最后按 `config_id` 字典序。

不得人工挑选同分配置。

---

## 十五、阈值选择

配置选定后，只能在相应：

```text
inner_validation
```

上选择阈值。

候选固定为：

```text
0.05, 0.10, 0.15, ..., 0.95
```

目标固定为：

```text
正类 F1 最大
```

平局规则：

1. Recall更高者优先；
2. Recall相同时，更接近0.5者优先；
3. 仍相同时，数值更小者优先。

不得使用 outer validation 重新选阈值。

阈值来自 inner 模型后，即使模型在完整 outer_train 上重新拟合，也必须保留该阈值。

---

## 十六、预测概率

所有模型必须输出：

```text
P(y=1)
```

必须通过模型的：

```python
classes_
```

定位正类1对应的概率列。

不得假定正类概率永远位于固定列。

所有概率必须：

* 为有限值；
* 范围在 `[0, 1]`；
* 与 trajectory_key 一一对应；
* 不得四舍五入后再计算指标。

---

## 十七、指标

### 主指标

```text
PR-AUC / Average Precision
正类 F1
```

### 辅助指标

```text
ROC-AUC
Precision
Recall
F2
Balanced Accuracy
Matthews Correlation Coefficient
```

### 实现规则

* Precision、Recall、F1、F2以1为正类；
* 无正类预测时，Precision和F类指标使用 `zero_division=0`；
* outer fold已经冻结为同时包含正负类；
* 不得将无法计算指标擅自填充为0.5。

每个 fold还要报告：

```text
正类数
负类数
正类率
预测正类数
选择的配置
选择的阈值
```

---

## 十八、三种汇总结果

每个：

```text
target × baseline
```

必须同时报告：

### 1. 每fold原始指标

五个 outer fold逐项保存。

### 2. Fold mean ± standard deviation

标准差固定使用：

```text
sample standard deviation
ddof = 1
```

不得只报告最好fold。

### 3. Pooled OOF指标

合并全部五个 outer validation 预测。

要求：

* 每条有效dev轨迹恰好出现一次；
* 不得重复；
* 不得遗漏；
* 每条样本使用所属fold冻结的阈值；
* PR-AUC和ROC-AUC使用原始预测概率；
* F1等阈值指标使用所属fold预测标签。

预期每个基线的OOF数量：

```text
Success: 192
Side Effect: 195
Looping: 196
```

---

## 十九、描述性信号统计

允许额外报告：

```text
正类 prevalence
pooled OOF AP
AP absolute lift = AP - prevalence
B3 pooled AP - B2 pooled AP
B3 pooled F1 - B2 pooled F1
```

这些只用于描述，不用于本阶段继续调参。

不得：

* 根据AP lift临时增加模型；
* 根据B3结果修改词表；
* 根据某目标结果更换指标；
* 声称统计显著；
* 声称达到跨域泛化；
* 声称超过现有论文。

本阶段不进行显著性检验或置信区间计算。

---

## 二十、输出预测文件

生成：

```text
artifacts/a1_2_oof_predictions.csv
```

至少包含：

```text
trajectory_key
group_key
target
baseline_id
outer_fold
true_label
predicted_probability
selected_threshold
predicted_label
selected_config_id
```

不得包含 test 数据。

每个：

```text
target × baseline × trajectory_key
```

必须唯一。

---

## 二十一、选择过程记录

生成：

```text
artifacts/a1_2_inner_config_selection.csv
```

至少包含：

```text
target
baseline_id
outer_fold
config_id
inner_train_size
inner_validation_size
inner_pr_auc
selected
tie_break_rank
```

生成：

```text
artifacts/a1_2_threshold_selection.csv
```

至少包含：

```text
target
baseline_id
outer_fold
config_id
threshold
inner_f1
inner_precision
inner_recall
selected
```

不得只保存最终配置而删除候选轨迹。

---

## 二十二、结构特征产物

生成标签无关的：

```text
artifacts/dev_structural_features.csv
```

只包含：

```text
trajectory_key
13个冻结结构特征
content_sha256
```

不得包含：

* 标签；
* eligible_main；
* benchmark；
* model_name；
* fold；
* task ID；
* test信息。

结构特征必须在连接标签之前生成。

---

## 二十三、指标产物

生成：

```text
artifacts/a1_2_fold_metrics.csv
artifacts/a1_2_pooled_metrics.csv
artifacts/a1_2_config_frequency.csv
artifacts/a1_2_run_summary.json
```

### fold metrics

每行对应：

```text
target × baseline × outer_fold
```

### pooled metrics

每行对应：

```text
target × baseline
```

### config frequency

报告每个候选配置在五个outer fold中被选中的次数。

不得据此在本阶段删除某些候选配置后重跑。

---

## 二十四、正式报告

生成：

```text
docs/stage_a1_2_minimal_baseline_report.md
```

报告至少包含：

1. 运行环境；
2. 输入、标签和manifest哈希；
3. B0–B3定义；
4. 每个目标的样本和类别分布；
5. 每fold结果；
6. mean ± std；
7. pooled OOF结果；
8. 选中配置和阈值分布；
9. AP相对prevalence的描述性提升；
10. B2与B3的描述性比较；
11. 收敛警告和异常；
12. 实验限制；
13. 未访问test声明；
14. 未运行LOBO、消融或复杂模型声明；
15. 对下一阶段的证据摘要。

不得只展示表现最好的模型。

---

## 二十五、结果解释边界

报告可以写：

```text
在冻结的task-grouped dev OOF协议下观察到……
```

不得写：

```text
模型已经证明能够泛化到新Benchmark
模型达到最终性能
方法在test上有效
论文假设已经成立
```

### 结果信号分级

本阶段可以为每个目标给出以下描述性标签：

```text
clear_provisional_signal
weak_or_mixed_signal
no_obvious_signal
```

但必须依据预先固定的描述规则。

#### clear_provisional_signal

同时满足：

1. B2或B3 pooled OOF AP 高于该目标 prevalence；
2. B2或B3正类F1高于Dummy基线；
3. 提升不只来自单个fold；
4. 不存在数据、划分或实现异常。

#### weak_or_mixed_signal

例如：

* AP略高于prevalence但fold波动较大；
* F1改善但PR-AUC没有稳定改善；
* B2有效但B3无改善；
* B3只在部分fold明显改善。

#### no_obvious_signal

B2和B3均未稳定超过先验或多数类参考。

该标签不得自动触发新模型训练，必须等待人工阶段门审查。

---

## 二十六、禁止运行的实验

本阶段禁止：

* 任何test评估；
* 四组或五组LOBO；
* Leave-One-Model-Out；
* reasoning敏感性；
* error ablation；
* benchmark literal redaction；
* Embedding；
* MLP；
* Random Forest；
* XGBoost；
* Transformer微调；
* LoRA；
* LLM-as-a-Judge；
* 截图或多模态输入；
* 新增结构特征；
* char n-gram；
* 无限超参数搜索；
* 阈值使用outer validation选择；
* 查看结果后改变指标。

---

## 二十七、运行时完整性检查

正式运行前必须验证：

1. Git工作区干净；
2. A1.2a冻结提交存在；
3. fold manifest哈希正确；
4. 正式输入哈希正确；
5. 标签索引哈希正确；
6. test access配置为false；
7. baseline列表恰好为B0–B3；
8. 输入视图恰好为primary；
9. 没有LOBO运行参数；
10. 没有reasoning或error ablation路径；
11. 真实运行代码与A1.2a提交一致。

运行后再次验证：

* fold文件未被修改；
* 正式语料未被修改；
* 标签索引未被修改；
* test manifest未被修改；
* 输入哈希保持不变。

---

## 二十八、测试要求

运行前至少新增并通过以下测试。

### 数据与划分

1. 三个fold manifest哈希匹配冻结值；
2. 三个目标样本数符合192、195、196；
3. 所有样本均来自dev；
4. 不存在test trajectory key；
5. 同一group_key不跨outer train/validation；
6. 同一group_key不跨inner train/validation；
7. 每条轨迹恰好进入一次outer validation。

### 结构特征

8. 结构特征提取函数不接收标签；
9. 特征表不含标签、Benchmark、模型或fold；
10. 特征顺序恰好为冻结的13项；
11. 缺失分母时比例固定为0；
12. terminal只使用explicit termination signal；
13. 不使用reasoning；
14. 不使用metadata作为特征。

### TF-IDF

15. TF-IDF只在训练部分拟合；
16. validation独有的合成token不会进入训练词表；
17. 不使用全dev词表；
18. 配置只包含冻结的T1和T2；
19. 不存在char n-gram或Embedding。

### 嵌套选择

20. 配置只使用inner validation PR-AUC选择；
21. outer validation不能进入配置选择函数；
22. 阈值只使用inner validation选择；
23. 阈值候选恰好为0.05至0.95；
24. 配置同分规则确定；
25. 阈值同分规则确定。

### 预测与指标

26. 正类概率通过classes_定位；
27. 所有概率有限且位于[0,1]；
28. PR-AUC使用average_precision_score；
29. F类指标以1为正类；
30. pooled OOF每条轨迹恰好一次；
31. fold mean/std和pooled指标可由预测文件重新计算；
32. 不得只保留最好fold。

### 边界

33. baseline列表恰好B0–B3；
34. 不运行LOBO；
35. 不运行reasoning或error消融；
36. 不访问test；
37. 不修改正式语料；
38. 不修改fold；
39. 不修改标签资格；
40. 合成数据重复运行结果确定。

A1.2a测试只能使用合成数据，不得在真实dev上拟合模型。

正式运行后：

```text
A1.2定向测试：全部通过
全仓回归测试：全部通过
```

---

## 二十九、异常处理

### 收敛警告

任何 Logistic Regression convergence warning 必须：

* 显式记录；
* 不得静默忽略；
* 不得运行后临时增加 `max_iter`；
* 不得只重跑失败fold。

如果冻结的 `max_iter=5000` 仍未收敛：

```text
PASS_WITH_CONDITIONS
```

并报告涉及的目标、基线、fold和配置。

### 单次运行中断

允许从未完成状态恢复，但必须保证：

* 已完成预测不可被选择性修改；
* 恢复后输出与完整重跑一致；
* 不得只重跑表现差的fold；
* 记录中断原因。

### 实现错误

如果模型运行后发现代码错误：

* 判定当前运行无效；
* 不得保留或引用结果；
* 记录错误；
* 修正后从全部目标、全部基线、全部fold重新运行。

---

## 三十、阶段判定

完成后给出：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

### PASS

必须满足：

1. A1.2a运行前冻结提交存在；
2. B0–B3全部完成；
3. 三个目标五折全部完成；
4. OOF覆盖准确；
5. 无重复、无遗漏；
6. fold和输入哈希未变；
7. 所有选择只使用inner validation；
8. outer validation只评估一次；
9. test访问为0；
10. 未运行禁止实验；
11. 所有指标可以从预测文件复算；
12. 结果确定性复现；
13. 定向和全仓测试全部通过；
14. Git工作区干净；
15. 形成独立正式结果提交。

### PASS_WITH_CONDITIONS

例如：

* 个别Logistic Regression配置出现收敛警告；
* 某目标结果波动很大；
* Side Effect因正类数量少导致指标不稳定；
* 某基线在部分fold产生全负预测；
* 结果有效，但不足以支持继续扩大实验。

性能较低本身不等于技术失败。

### STOP

出现：

* fold或正式输入发生变化；
* 使用outer validation选择配置或阈值；
* test被访问；
* 同一任务跨训练和验证；
* OOF重复或遗漏；
* 标签进入输入或特征；
* TF-IDF在完整dev上拟合；
* 运行后修改配置并继续混用结果；
* 只报告最好fold；
* 结果无法确定性复现；
* 正式语料或标签资格被修改。

---

## 三十一、产物

### A1.2a运行前冻结

生成：

```text
configs/stage_a1_2_execution.yaml
requirements/baseline-lock.txt
artifacts/baseline_environment.json
artifacts/a1_2_prerun_integrity.json
scripts/run_stage_a1_2_baselines.py
tests/test_stage_a1_2_baselines.py
```

更新：

```text
research/01_DECISION_LOG.md
.gitignore
```

提交：

```text
chore: preregister minimal grouped baselines
```

### A1.2b正式运行

生成：

```text
artifacts/dev_structural_features.csv
artifacts/a1_2_inner_config_selection.csv
artifacts/a1_2_threshold_selection.csv
artifacts/a1_2_oof_predictions.csv
artifacts/a1_2_fold_metrics.csv
artifacts/a1_2_pooled_metrics.csv
artifacts/a1_2_config_frequency.csv
artifacts/a1_2_run_summary.json
docs/stage_a1_2_minimal_baseline_report.md
```

更新：

```text
research/01_DECISION_LOG.md
```

提交：

```text
experiment: run grouped minimal dev baselines
```

不得覆盖或amend运行前冻结提交。

---

## 三十二、最终汇报

完成后必须汇报：

1. 阶段判定；
2. 两个Git commit；
3. 运行环境和依赖；
4. manifest及输入哈希验证；
5. B0–B3是否全部完成；
6. 三个目标的每fold指标；
7. mean ± std；
8. pooled OOF指标；
9. AP相对于prevalence的提升；
10. 选中配置频率；
11. 选中阈值分布；
12. 收敛警告；
13. OOF覆盖验证；
14. test访问情况；
15. 禁止实验未执行声明；
16. 定向测试和全仓测试；
17. Git status；
18. 对三个目标分别给出描述性信号分级。

Stage A1.2结果提交后必须停止，等待人工阶段门审查。

不得自动进入LOBO、消融、reasoning、复杂模型或test评估。
