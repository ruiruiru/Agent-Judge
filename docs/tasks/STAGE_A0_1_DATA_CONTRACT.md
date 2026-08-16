# Stage A0.1：锁定 AgentRewardBench 数据来源与标签契约

上一轮因缺少固定版本、许可证、官方 split 和标签映射而停止。现在授权执行“仅元数据审计”，不得进入数据建模或训练阶段。

## 一、固定来源

### GitHub 代码版本

* Repository：`https://github.com/McGill-NLP/agent-reward-bench`
* 固定 commit：

```text
f838338886d723d40b586309465a38277803d9e6
```

所有从 GitHub 获取的文件必须基于该 commit，不得继续使用浮动的 `main`。

### Hugging Face 数据版本

Repository：

```text
McGill-NLP/agent-reward-bench
```

允许通过以下方式执行一次仅元数据查询：

```python
from huggingface_hub import HfApi

info = HfApi().dataset_info(
    repo_id="McGill-NLP/agent-reward-bench",
    revision="main",
)
print(info.sha)
```

将返回的完整 SHA 作为本项目固定的 Hugging Face revision，并写入来源清单。

本阶段不得下载 `cleaned/`、`judgments/`、`screenshots/` 等大型目录。

## 二、官方元数据文件

只允许获取或读取以下小文件：

```text
agent_reward_bench/data/annotations.csv
agent_reward_bench/data/splits.csv
README.md
```

如本地安装包或仓库中已经存在这些文件，优先读取本地固定 commit 版本。

## 三、固定标签字段和映射

人工标注字段：

```text
trajectory_success
trajectory_side_effect
trajectory_optimality
trajectory_looping
```

本研究第一阶段只使用以下三个二分类目标：

### Success

```text
字段：trajectory_success
Successful   -> 1
Unsuccessful -> 0
Unsure       -> 缺失值，排除
```

### Side Effect

```text
字段：trajectory_side_effect
Yes    -> 1
No     -> 0
Unsure -> 缺失值，排除
```

这里正类表示“存在副作用”，不得反转成安全标签。

### Repetitiveness / Looping

```text
字段：trajectory_looping
Yes -> 1
No  -> 0
```

任务书中的 Repetitiveness/Looping 统一对应官方字段 `trajectory_looping`。

### Optimality

`trajectory_optimality` 暂时只进行分布审计，不用于当前二分类实验，也不得擅自合并成二分类标签。

## 四、官方数据划分

必须使用：

```text
agent_reward_bench/data/splits.csv
```

通过规范化后的 `task_id` 连接人工标注和 split。

只允许：

```text
dev
test
```

不得自行随机划分，不得改变官方 dev/test，不得查看 test 结果来制定方法。

如果任何标注记录不能匹配 `splits.csv`，必须在报告中列出，不得猜测其归属。

## 五、本阶段需要执行的审计

检查并记录：

1. GitHub 完整 commit。
2. Hugging Face 完整 revision SHA。
3. 数据集 Terms of Use 原文位置及许可证状态。
4. `annotations.csv` 的列名、总行数和唯一轨迹数。
5. 每个标签字段的所有原始取值及数量。
6. 每个 benchmark 的样本数量。
7. 每个模型的样本数量。
8. 重复的 `(benchmark, task_id, model_name)` 是否来自第二标注者。
9. `splits.csv` 中 dev/test 的任务数量。
10. 所有标注任务是否能够映射到官方 split。
11. 是否存在空值、未知值、拼写异常或未定义标签。
12. 不同标签在 dev/test 和 benchmark 内的正负类分布。

## 六、产物

生成：

```text
docs/data_contract.md
artifacts/source_manifest.json
artifacts/metadata_audit.json
artifacts/label_distribution.csv
scripts/audit_agent_reward_bench_metadata.py
```

`source_manifest.json` 至少包含：

```json
{
  "github_repository": "",
  "github_commit": "",
  "huggingface_repository": "",
  "huggingface_revision": "",
  "license_status": "",
  "terms_of_use_url": "",
  "annotations_file": "",
  "splits_file": "",
  "file_sha256": {}
}
```

`docs/data_contract.md` 必须明确写出：

* 数据来源；
* 固定版本；
* 官方 split；
* 三个目标字段；
* 标签映射；
* Unsure 处理方法；
* 重复标注处理原则；
* test 封存原则；
* 当前已知限制。

## 七、约束

本阶段禁止：

* 下载完整 Hugging Face 数据集；
* 下载截图或完整轨迹；
* 编写特征工程代码；
* 训练或调用任何模型；
* 运行基线；
* 修改研究假设；
* 自行创建新的 train/dev/test；
* 猜测无法确认的字段；
* 删除或覆盖已有科研文件。

若元数据查询失败，只记录失败原因并停止，不得回退到浮动版本。

完成后：

1. 更新研究日志；
2. 展示生成文件；
3. 汇报所有审计统计和异常；
4. 执行 `git status`；
5. 提交一次 Git commit：

```text
chore: lock AgentRewardBench data contract
```
