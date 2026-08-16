# D9-R1 Review Checklist

## Data integrity

- [ ] Raw data are immutable and source provenance is recorded.
- [ ] Parsing failures are recorded without silent omission.
- [ ] Field and label mappings are evidence-based and unambiguous.

## Leakage and test-set protection

- [ ] Related trajectories are grouped by the approved key.
- [ ] No random split can leak a shared task across folds.
- [ ] Test data were not used for feature, model, threshold, or fusion selection.
- [ ] Leave-One-Benchmark-Out test benchmarks remain test-only.

## Reproducibility

- [ ] Each formal run preserves configuration, command, Git revision, environment, data/split versions, seed, outputs, and logs.
- [ ] Formal run directories are not overwritten.

## Negative results

- [ ] Failed runs and negative findings are preserved.
- [ ] Exploratory results are clearly identified.

## Scope and authorization

- [ ] Approved task was reviewed before execution.
- [ ] No unauthorized data, labels, models, APIs, or online environments were used.
- [ ] No stage gate was crossed without human approval.
