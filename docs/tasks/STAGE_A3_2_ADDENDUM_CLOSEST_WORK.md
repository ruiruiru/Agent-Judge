# Stage A3.2 Addendum：Targeted Closest-Work Coverage & Positioning Patch

## 1. 阶段定位

A3.2 主体已完成：

```text
PASS_WITH_CONDITIONS
```

A3.3 也已完成 preregistration：

```text
A3.3 prereg commit =
b85c93f17a3e90f20bca5162817111c5bc1ac70a
```

但 A3.3 formal execution 被以下依赖阻塞：

```text
A3.2 targeted closest-work addendum
```

本 addendum 的唯一目的：

> 在不重新开放整个 literature search 的前提下，补齐最接近 THIS_WORK 的文献覆盖，并确认 A3.2 的 comparability 与 novelty positioning 是否需要收窄。

本轮只处理：

```text
1. WebGraphEval
2. WebStep / Where Did It Go Wrong?
3. “Similar” canonical identity resolution
```

可选：

```text
如果上面三项的 primary source 明确指向另一个更相关 canonical work，
仅允许为 identity resolution 跟随该 primary-source chain，
不得重新扩张搜索。
```

完成后必须：

```text
STOP
WAIT_FOR_HUMAN_A3_2_ADDENDUM_REVIEW
```

不得自动执行 A3.3。

---

# 2. 本补丁只回答四个问题

## Q1
WebGraphEval 是否真正属于“结构化 Web-Agent trajectory evaluation”这一 closest-work 范畴？

## Q2
WebStep 是否真正属于“process-level / trajectory-level web-agent evaluation”这一 closest-work 范畴？

## Q3
A3.2 registry 中的 `Similar` 到底是哪篇 canonical paper？

## Q4
补齐这三项后：

```text
DIRECTLY_COMPARABLE 是否仍为 0？
NO_VALID_CROSS_PAPER_HEAD_TO_HEAD 是否仍成立？
THIS_WORK novelty wording 是否需要收窄？
```

---

# 3. 科研身份

本 addendum 仅属于：

```text
TARGETED_PRIMARY_SOURCE_VERIFICATION
CLOSEST_WORK_COVERAGE_PATCH
COMPARABILITY_RECHECK
POSITIONING_RECHECK
CITATION_REGISTRY_PATCH
```

不属于：

```text
new literature survey
new experiment
new benchmark
new metric comparison
new model
new scientific claim
```

---

# 4. Hard gates

正式执行前必须验证：

## 4.1 Git clean

```text
git status --porcelain
```

必须为空。

## 4.2 A3.2 result

必须可解析：

```text
ef37dee92ef319b2f7d39367e757919a898fbfdb
```

## 4.3 A3.3 prereg

必须可解析并保持为历史祖先：

```text
b85c93f17a3e90f20bca5162817111c5bc1ac70a
```

A3.3 taskbook：

```text
docs/tasks/STAGE_A3_3_MANUSCRIPT_EVIDENCE_FREEZE.md
```

必须存在且本 addendum **不得修改**。

## 4.4 A1.11 claim matrix

必须 exact match：

```text
2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175
```

## 4.5 A3.2 current conclusions

开始前必须确认当前 A3.2 仍为：

```text
DIRECTLY_COMPARABLE = 0
NO_VALID_CROSS_PAPER_HEAD_TO_HEAD
```

以及：

```text
Success = CONFIRMATORY_SUPPORTED
Looping = CONFIRMATORY_SUPPORTED
Side Effect = EXPLORATORY_SUPPORTED
```

任一 hard gate 不一致：

```text
STOP
```

---

# 5. Preregistration gate

如果：

```text
docs/tasks/STAGE_A3_2_ADDENDUM_CLOSEST_WORK.md
```

尚未被 Git 跟踪：

只允许创建独立 prereg commit：

```text
chore: preregister A3.2 closest-work addendum
```

然后立即：

```text
STOP
```

不得在同一轮继续文献核验。

---

# 6. Scientific-operation counters

整个补丁必须保持：

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
external_dataset_downloads = 0
external_dataset_runs = 0
new_scientific_figures = 0
```

允许：

```text
targeted web literature lookup
primary-source reading
canonical identity resolution
citation metadata verification
qualitative comparability audit
registry/document patching
```

---

# Part I — Primary-source policy

## 7. 最终事实只能来自 primary sources

允许：

```text
peer-reviewed proceedings / publisher
official paper PDF
official arXiv page / PDF
official OpenReview record
official project/repository
```

禁止将以下作为最终证据：

```text
search snippets
blogs
news
survey summaries
Google Scholar snippets
Semantic Scholar snippets
LLM-generated summaries
```

搜索结果只允许用于定位 primary source。

---

# Part II — WebGraphEval verification

## 8. Mandatory work A

核验：

```text
WebGraphEval
```

必须确认：

```text
canonical_title
authors
year
venue_or_status
primary_identifier
primary_url
version
research_object
evaluation_granularity
trajectory representation
whether graph/structure is central
whether web-agent specific
benchmarks
targets / metrics
training requirement
evaluation purpose
```

特别回答：

```text
Does WebGraphEval study structural trajectory evaluation?
```

机器状态只能：

```text
YES
PARTIALLY
NO
```

并提供 primary-source location。

---

## 9. 与 THIS_WORK 的区别必须逐项审计

至少比较：

```text
representation:
graph / sequence / fixed-dimensional features

evaluation unit:
trajectory / aggregate / step

target:
outcome / redundancy / efficiency / process / other

learning:
trained evaluator / descriptive metric / classifier

information access:
task semantics / trajectory text / structure only

benchmark:
same or different

metric:
same or different

goal:
prediction / diagnosis / ranking / analysis

blind-heldout protocol:
yes / no / not comparable
```

最终分类只能：

```text
DIRECTLY_COMPARABLE
PARTIALLY_COMPARABLE
CONTEXT_ONLY
NOT_COMPARABLE
```

---

# Part III — WebStep verification

## 10. Mandatory work B

核验：

```text
WebStep / Where Did It Go Wrong?
```

必须确认：

```text
canonical_title
authors
year
venue_or_status
primary_identifier
primary_url
version
benchmark/data
process-level or trajectory-level
semantic-state representation
failure localization / diagnosis role
metrics
training requirement
information access
```

特别回答：

```text
Does WebStep directly evaluate the same target/protocol as THIS_WORK?
```

只能：

```text
YES
PARTIALLY
NO
```

---

## 11. 与 THIS_WORK 的区别必须审计

至少比较：

```text
semantic state vs morphology
process diagnosis vs outcome prediction
step-level vs trajectory-level
benchmark
target
metric
training requirement
information access
blind-heldout protocol
```

并给出 comparability class。

---

# Part IV — Resolve “Similar”

## 12. Mandatory identity resolution

读取当前：

```text
artifacts/a3_2_verified_literature_registry.csv
artifacts/a3_2_citation_registry.csv
paper/references/a3_2_verified_related_work.bib
docs/stage_a3_2_literature_baseline_verification_report.md
```

定位 `Similar` 所对应的原记录。

必须解析：

```text
canonical_title
authors
year
primary_identifier
primary_url
citation_key
registry work_id
why it was labeled "Similar"
```

最终只能：

```text
RESOLVED_CANONICAL_IDENTITY
DUPLICATE_ALIAS
INVALID_PLACEHOLDER
UNRESOLVED
```

如果是：

### RESOLVED_CANONICAL_IDENTITY
统一改为 canonical title / work_id。

### DUPLICATE_ALIAS
删除重复 alias，但保留 provenance 说明。

### INVALID_PLACEHOLDER
从 paper-facing registry / citation / table 中移除，并保留 patch log。

### UNRESOLVED
阶段：

```text
STOP
```

不得猜测身份。

---

# Part V — Comparability recheck

## 13. 更新后的完整 comparability audit

只基于：

```text
原 A3.2 included works
+
WebGraphEval
+
WebStep
+
resolved Similar identity
```

不得加入新的开放式候选。

生成/更新：

```text
artifacts/a3_2_verified_literature_registry.csv
artifacts/a3_2_positioning_matrix.csv
```

必须重新统计：

```text
DIRECTLY_COMPARABLE
PARTIALLY_COMPARABLE
CONTEXT_ONLY
NOT_COMPARABLE
```

---

## 14. Head-to-head gate

只有满足全部条件：

```text
same/equivalent target
same/equivalent evaluation unit
same/equivalent benchmark/split
compatible metric
compatible information access
compatible evaluation role
```

才允许：

```text
DIRECTLY_COMPARABLE
```

如果仍然为 0：

```text
NO_VALID_CROSS_PAPER_HEAD_TO_HEAD
```

继续冻结。

不得因为“都是 trajectory evaluation”就升级为直接可比。

---

# Part VI — Novelty / positioning recheck

## 15. 更新

```text
docs/a3_2_positioning_and_novelty_contract.md
```

必须专门加入：

```text
WebGraphEval boundary
WebStep boundary
```

---

## 16. 推荐 positioning

如果 primary-source audit 支持，优先收窄为：

> lightweight fixed-dimensional structural signals for outcome-oriented web-agent trajectory evaluation under a frozen blind-held-out protocol

也可根据核验结果进一步调整。

不得继续使用过宽且可能冲突的：

```text
first structural web-agent trajectory evaluator
first structural trajectory evaluation
first lightweight agent evaluator
```

---

## 17. Allowed / forbidden wording

至少重新审计：

### Candidate allowed wording

```text
systematic study of lightweight fixed-dimensional structural trajectory signals
outcome-oriented structural trajectory evaluation
blind-first frozen held-out evaluation
cost / interpretability characterization
task-agnostic structural representation within the studied benchmark setting
```

### Forbidden

```text
first structural web-agent evaluator
first trajectory-structure evaluator
state of the art
outperforms WebGraphEval
outperforms WebStep
replaces LLM judges
generalizes to unseen benchmarks
independent external validation
```

除非 strict evidence 明确支持，否则禁止。

---

# Part VII — Citation / BibTeX patch

## 18. 更新

```text
artifacts/a3_2_citation_registry.csv
paper/references/a3_2_verified_related_work.bib
```

加入：

```text
WebGraphEval
WebStep
```

如 `Similar` 被解析为已存在 work：

```text
不得重复 citation
```

所有 BibTeX 字段必须来自 primary metadata。

不得猜：

```text
DOI
pages
volume
venue
publisher
```

---

# Part VIII — Related Work positioning table patch

## 19. 更新

```text
paper/tables/Table_Related_Work_Positioning.md
paper/tables/Table_Related_Work_Positioning.tex
```

必须加入：

```text
WebGraphEval
WebStep
```

`Similar` 必须替换为 canonical identity 或移除。

表仍然默认：

```text
attribute comparison only
```

不得加入无效跨论文性能排行榜。

---

# Part IX — Writing skeleton patch

## 20. 更新

```text
docs/a3_2_related_work_writing_skeleton.md
```

建议 taxonomy：

```text
A. trajectory / outcome evaluators
B. process / reward / step-level evaluators
C. structural / graph / trajectory-analysis approaches
D. THIS_WORK positioning
```

WebGraphEval / WebStep 必须进入正确类别。

---

# Part X — Addendum-specific outputs

## 21. 新增 patch registry

生成：

```text
artifacts/a3_2_addendum_closest_work_patch.csv
```

字段至少：

```text
item
action
old_value
new_value
source
reason
comparability_before
comparability_after
paper_facing_effect
verified
```

---

## 22. 新增 addendum report

生成：

```text
docs/a3_2_closest_work_addendum_report.md
```

必须回答：

1. WebGraphEval verified identity；
2. WebGraphEval comparability；
3. WebStep verified identity；
4. WebStep comparability；
5. Similar resolution；
6. comparability counts before/after；
7. head-to-head status before/after；
8. novelty wording before/after；
9. citations added/removed；
10. files patched；
11. scientific counters；
12. Git condition；
13. A3.3 unblock recommendation。

---

## 23. 新增 machine summary

生成：

```text
artifacts/a3_2_addendum_run_summary.json
```

至少：

```text
stage_determination
webgrapheval_status
webstep_status
similar_resolution_status
directly_comparable_before
directly_comparable_after
partially_comparable_before
partially_comparable_after
context_only_before
context_only_after
head_to_head_before
head_to_head_after
novelty_changed
citation_count_before
citation_count_after
bibtex_count_before
bibtex_count_after
patched_files
output_hashes

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
external_dataset_downloads
external_dataset_runs
new_scientific_figures
```

---

# Part XI — Search boundary

## 24. 严格禁止开放式扩张

本补丁最多允许检索：

```text
WebGraphEval
WebStep / Where Did It Go Wrong?
Similar identity resolution
```

允许为确认 canonical identity 跟随：

```text
official proceedings
official arXiv
official OpenReview
official project/repository
```

不得：

```text
再找 10 篇新文章
重做 A3.2 freshness scan
新增 unrelated candidate
为了丰富 Related Work 扩充 survey
```

如果发现新 work：

```text
只记录到 notes，不纳入本补丁
```

除非它是 WebGraphEval/WebStep 的 canonical replacement。

---

# 25. Tests / verifiers

至少验证：

1. Git start clean；
2. A3.2 result reachable；
3. A3.3 prereg reachable；
4. A3.3 taskbook unchanged；
5. A1.11 claim matrix exact；
6. current A3.2 baseline counts loadable；
7. WebGraphEval primary identity verified；
8. WebStep primary identity verified；
9. Similar resolved or STOP；
10. every patched bibliographic field primary-sourced；
11. no search snippet as final evidence；
12. no unsupported DOI/venue/pages；
13. comparability class valid；
14. no invalid DIRECTLY_COMPARABLE upgrade；
15. no invalid numeric head-to-head；
16. positioning contract patched；
17. citation registry ↔ BibTeX consistent；
18. Related Work table uses canonical names；
19. A3.2 writing skeleton patched；
20. no scientific result changed；
21. all scientific-operation counters = 0；
22. Git final clean。

---

# 26. Commit discipline

## A3.2-addendum-a — prereg

```text
chore: preregister A3.2 closest-work addendum
```

仅 taskbook。

然后 STOP。

## A3.2-addendum-b — implementation/result

建议一个 implementation commit：

```text
chore: implement A3.2 closest-work verification patch
```

随后 result commit：

```text
docs: finalize A3.2 closest-work addendum
```

不得 amend。

如修复：

```text
独立 fix commit
```

保留 provenance。

---

# 27. 阶段判定

只能：

```text
PASS
PASS_WITH_CONDITIONS
STOP
```

## PASS

要求：

```text
WebGraphEval verified
WebStep verified
Similar resolved
comparability rechecked
head-to-head gate rechecked
novelty contract updated
citation/BibTeX updated
Related Work table updated
writing skeleton updated
all scientific counters = 0
Git clean
```

## PASS_WITH_CONDITIONS

允许：

```text
WebGraphEval/WebStep 为 preprint
无 DOI/pages
venue 尚未正式确定
```

只要 canonical identity 和 primary source 已核验。

## STOP

包括：

```text
Similar unresolved
primary-source contradiction
unsupported bibliographic field
invalid comparability upgrade
claim/novelty overreach
open-ended literature expansion
A3.3 taskbook modified
scientific result changed
Git provenance unclear
```

---

# 28. A3.3 unblock gate

补丁通过后必须明确输出：

```text
A3_2_CLOSEST_WORK_ADDENDUM = PASS or PASS_WITH_CONDITIONS
```

并给：

```text
A3_3_FORMAL_EXECUTION =
AUTHORIZED
```

或：

```text
A3_3_FORMAL_EXECUTION =
NOT_AUTHORIZED
```

只有前者才可在下一轮执行 A3.3。

不得本轮自动执行 A3.3。

---

# 29. 最终汇报

Codex 必须汇报：

```text
阶段判定

addendum prereg commit
implementation commit
result commit
fix commits
amend

A3.2 result verification
A3.3 prereg verification
A3.3 taskbook unchanged
A1.11 claim matrix verification

WebGraphEval:
canonical identity
verification status
comparability class
THIS_WORK boundary

WebStep:
canonical identity
verification status
comparability class
THIS_WORK boundary

Similar:
old label
canonical identity
resolution status

comparability counts before
comparability counts after

head-to-head status before
head-to-head status after

novelty wording before
novelty wording after

citation count before/after
BibTeX count before/after
Related Work table status
writing skeleton status

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
external_dataset_downloads = 0
external_dataset_runs = 0
new_scientific_figures = 0

tests/verifiers
warnings
Git status

addendum report path
machine summary path
patch registry path

A3_2_CLOSEST_WORK_ADDENDUM = ...
A3_3_FORMAL_EXECUTION = ...

WAIT_FOR_HUMAN_A3_2_ADDENDUM_REVIEW
```

然后立即 STOP。

不得自动执行 A3.3。
