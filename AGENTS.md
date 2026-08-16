# AGENTS.md

## 1. Project identity

This repository is the research workspace for:

**D9-R1: Dimension-Aware Lightweight Evaluation of Web-Agent Trajectories under Benchmark Shift**

The project studies whether different Web Agent trajectory-quality dimensions require different structural and semantic evidence, and whether a lightweight dimension-aware evaluator can generalize across benchmarks.

This repository is a scientific research project, not a general software product. Scientific validity, reproducibility, traceability, and stage-gate discipline take priority over implementation speed.

## 2. Authoritative documents

Before doing any work, read these documents in order:

1. `research/00_RESEARCH_CHARTER.md`
2. `research/01_DECISION_LOG.md`
3. The currently approved task under `research/tasks/`
4. The relevant configuration under `configs/`
5. Existing reports and experiment registry entries related to the task

The research charter defines the long-term question and boundaries.
The approved task file defines the current authorized work.

If the task file conflicts with the research charter, stop and report the conflict. Do not choose one silently.

## 3. Current research state

- Direction: `D9-R1`
- Core hypothesis: `H1`
- Current stage: minimum pilot preparation
- Authorized first work: repository initialization only
- Complex neural models: prohibited
- Online Web Agent environments: prohibited
- Paid LLM judge APIs: prohibited
- Expert-label modification: prohibited
- Next decision point: after workspace review
- Human approval is required before crossing any stage gate

Update this section only after explicit human approval and record the change in `research/01_DECISION_LOG.md`.

## 4. Role boundaries

Codex may:

- inspect repository files;
- initialize approved directory structures;
- implement approved data parsing and audit code;
- implement approved lightweight baselines;
- add tests;
- run approved experiments;
- save configurations, logs, predictions, metrics, and reports;
- fix implementation bugs without changing the research protocol;
- document ambiguity, failure, and negative results.

Codex may not:

- redefine the research question;
- invent a new core hypothesis;
- modify expert labels;
- remove a label because its result is poor;
- change the data split protocol;
- use the test set for feature, model, threshold, or fusion-weight selection;
- lower a stage-gate threshold;
- add unapproved models, APIs, datasets, labels, or online environments;
- continue beyond a failed or conditional stage gate without human approval;
- announce that the research direction is successful;
- claim novelty, publication readiness, or state of the art;
- discard or overwrite negative results.

## 5. Scientific non-negotiables

### Data integrity

- Never modify files in `data/raw/`.
- Version processed data under `data/processed/<version>/`.
- Record source URL, download date, revision or commit, and SHA256 for important raw files.
- Parsing failures must be logged; never silently skip them.
- Do not guess ambiguous field or label mappings.
- Keep identical or related task trajectories grouped according to the approved protocol.

### Evaluation integrity

- Do not use ordinary random splitting when it can leak the same `task_id` across folds.
- Prefer `StratifiedGroupKFold` or `GroupKFold` using the approved grouping key.
- For Leave-One-Benchmark-Out evaluation, the held-out benchmark is test-only.
- Fit TF-IDF vocabulary, preprocessing, feature selection, threshold selection, and fusion weights only on training or validation data.
- Report all approved labels, folds, held-out benchmarks, and seeds.
- Accuracy is auxiliary when labels are imbalanced; report the approved F1, PR-AUC, AUROC, and confidence intervals.
- Preserve out-of-fold or held-out predictions required to reproduce metrics.

### Reproducibility

Every formal run must preserve:

- configuration;
- exact command;
- Git commit;
- environment and dependency versions;
- data version;
- split version;
- random seed;
- thresholds;
- feature definitions;
- predictions;
- metrics;
- stdout/stderr log;
- concise run summary.

Do not overwrite an existing run directory.

### Negative results

- Save failed runs and negative findings.
- Distinguish implementation failure from hypothesis failure.
- Do not reinterpret a failed primary result as success based on an unplanned secondary metric.
- Any post-hoc exploratory analysis must be labeled exploratory.

## 6. Stage-gate behavior

At the end of each approved stage, generate a decision report with exactly one recommendation:

- `GO`
- `CONDITIONAL GO`
- `NO-GO`

Codex may compute evidence and draft the report, but the human research lead makes the decision.

- `GO`: stop after producing approved deliverables and wait for the next task.
- `CONDITIONAL GO`: stop, preserve outputs, list unmet conditions, and wait for approval.
- `NO-GO`: stop after producing the failure report. Do not expand the experiment.

## 7. Repository layout

```text
Agent-Judge/
├─ AGENTS.md
├─ README.md
├─ research/
│  ├─ 00_RESEARCH_CHARTER.md
│  ├─ 01_DECISION_LOG.md
│  ├─ 02_EXPERIMENT_REGISTRY.csv
│  ├─ 03_CLAIM_EVIDENCE_MAP.md
│  ├─ 04_REVIEW_CHECKLIST.md
│  └─ tasks/
│     └─ 001_MINIMUM_PILOT.md
├─ configs/
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ splits/
├─ src/
│  ├─ data/
│  ├─ features/
│  ├─ models/
│  └─ evaluation/
├─ scripts/
├─ tests/
├─ runs/
└─ reports/
```

Keep raw data, processed data, code, configurations, run outputs, and reports separate.

## 8. Coding standards

- Use Python 3.10 or newer.
- Use type annotations for public functions.
- Add docstrings to non-trivial public functions.
- Write tests for parsers, label mappings, split logic, feature calculations, and metric calculations.
- Do not hard-code machine-specific absolute paths.
- Command-line scripts should accept `--config` where appropriate.
- Return a non-zero exit code on fatal errors.
- Log to both terminal and file for formal runs.
- Keep dependencies minimal and record every new dependency.
- Prefer simple, inspectable implementations during the pilot.
- Do not add neural frameworks during the pilot unless explicitly approved.

## 9. Verification before completion

Before declaring a task complete:

1. Review the approved task again.
2. Confirm every requested deliverable exists.
3. Run relevant tests.
4. Confirm no raw data was modified.
5. Confirm no test leakage occurred.
6. Confirm formal runs are registered.
7. Confirm negative results and failures were preserved.
8. Review the diff for unauthorized scope changes.
9. Summarize what was completed, what was not, and why.
10. List absolute paths to important outputs.

Do not respond only with “completed”.

## 10. Ambiguity and conflict protocol

When requirements conflict, a field is ambiguous, data are missing, or a scientific rule cannot be satisfied:

1. Stop the affected work.
2. Preserve all current outputs.
3. Record the issue in a report.
4. Explain the scientific consequence.
5. Do not invent a workaround that changes the approved protocol.
6. Request human approval.

Implementation details may be resolved autonomously only when they do not alter the scientific question, data meaning, evaluation protocol, or stage gate.

## 11. Long-task planning

For multi-step work, work that modifies multiple modules, or substantial execution:

- inspect the repository and authoritative documents first;
- produce a concise execution plan;
- identify milestones, tests, deliverables, and stop conditions;
- do not begin implementation until the prompt explicitly authorizes implementation;
- keep the task report updated as discoveries are made.

The approved file under `research/tasks/` remains the authoritative experiment specification.
