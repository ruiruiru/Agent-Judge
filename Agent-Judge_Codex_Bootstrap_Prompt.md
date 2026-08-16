# Agent-Judge：Codex 首次初始化提示词

将下面整段提示词粘贴给 Codex。第一次只初始化科研工作空间，不下载数据、不训练模型、不执行最小预实验。

---

你现在位于一个新建的 `Agent-Judge` 项目根目录。

本次任务仅用于初始化专业、可审计、可复现的科研工作空间。不要下载数据，不要训练模型，不要运行实验。

请严格按以下步骤执行：

1. 首先确认当前工作目录和 Git 仓库根目录。
2. 读取根目录的 `AGENTS.md`。
3. 检查以下两个来源文件是否已经放入项目：
   - D9-R1 科研总纲
   - D9-R1 最小预实验任务书
4. 将科研总纲原样保存为：
   - `research/00_RESEARCH_CHARTER.md`
5. 将最小预实验任务书原样保存为：
   - `research/tasks/001_MINIMUM_PILOT.md`
6. 不得改写、缩写、总结、补充或重新解释这两个文件。
7. 初始化以下目录和空模板：
   - `research/01_DECISION_LOG.md`
   - `research/02_EXPERIMENT_REGISTRY.csv`
   - `research/03_CLAIM_EVIDENCE_MAP.md`
   - `research/04_REVIEW_CHECKLIST.md`
   - `configs/`
   - `data/raw/`
   - `data/processed/`
   - `data/splits/`
   - `src/data/`
   - `src/features/`
   - `src/models/`
   - `src/evaluation/`
   - `scripts/`
   - `tests/`
   - `runs/`
   - `reports/`
8. 创建一个简洁的 `README.md`，只说明：
   - 项目名称；
   - 当前阶段；
   - 权威文档读取顺序；
   - 目录说明；
   - 当前禁止执行数据下载和模型训练。
9. 在 `research/01_DECISION_LOG.md` 中记录：
   - D9-R1 已由研究负责人批准进入最小预实验准备阶段；
   - 当前尚未批准正式执行数据下载和模型训练；
   - 下一决策点是工作空间人工审查。
10. 在 `research/02_EXPERIMENT_REGISTRY.csv` 中只写表头，不写虚构实验。
11. 在 `research/03_CLAIM_EVIDENCE_MAP.md` 中建立空模板，不填写未经实验支持的结论。
12. 在 `research/04_REVIEW_CHECKLIST.md` 中建立数据完整性、泄漏、测试集、复现性、负结果和越权检查项。
13. 如项目尚未初始化 Git，请初始化 Git；不要配置远程仓库。
14. 添加适合 Python 科研项目的 `.gitignore`，但不要忽略：
   - 配置文件；
   - 小型结果摘要；
   - 实验登记表；
   - 报告；
   - 研究文档。
15. 完成后运行一次结构检查，确认所有文件路径存在。
16. 不要开始 `001_MINIMUM_PILOT.md` 中的数据下载、数据审计或模型实验。

完成后请只汇报：

- 实际创建和移动的文件；
- 是否原样保留两份权威文档；
- 当前 Git 状态；
- 发现的冲突或缺失；
- 需要人工检查的事项；
- 项目根目录绝对路径。

不要只回复“初始化完成”。
