# Stage A1.11 Final Evidence Consolidation Report

## 1. Stage determination

`PASS`

Final state after the independent result commit and clean-tree verification: `READY_FOR_A2_DESIGN_REVIEW`.

## 2. Git and input provenance

- Branch: `master`
- Clean start HEAD / A1.11a: `c0d82fb1b89eddc8a8f0765183e51808b9268616`
- A1.11a parent / A1.10b result: `53d81eb17e1be52e55489f5fbdf1f72018c5a349`
- A1.10a result: `cead3cbaa362da4a9918dab32e41b58fffb987d9`
- A1.10a fix: `100966969bf36c968051dea7fbbb675c1814b7cd`
- A1.10b preregistration: `042866147e7b4a0c930eeb120d6e642cb34773a7`
- A1.10b pre-unlock fix: `3f0bc4da460652a74ae4767ff6d482fd4116ec9f`
- A1.10b pre-unlock integrity: `85cb71a49c9c25c9284562afad751f975d787608`
- A1.9a / A1.9b: `4944df46be45d8ad52d57a051e04b59c4a1a82ee` / `8f96a6f032ee9b4dd0272164d60230303612043b`
- GitHub / Hugging Face revisions: `f838338886d723d40b586309465a38277803d9e6` / `b6d17e646009d6cb63d5dd7be78807b680693f61`
- Blind / scored prediction SHA-256: `a3a232484716ee455a604f03ffd40e6f734a1925ffdfb93e4a3d04118de27c3d` / `22883f32ad22ecd2de6e7a3056a0f165d7aa4c03ab4ec847a535dbff7defb704`
- A1.8 claim matrix SHA-256: `264678a325f1680c8cfdad3631e6f5209a29a91e6ab8dd5b9683adb857810590`
- A1.11 fix commits: `11e86d5a2eb7006cf3faaef30ba0e495a86b5638;4534678a3eba2716d4b93f6f406c9e3af1dad7ff;4729517292f83dd310c760daf182d27a0ef8a8ea`
- A1.11b result commit: `recorded_by_enclosing_result_commit`; no amend.

## 3. A0-A1.10 provenance coverage

Coverage is 17/17 stage units: A0.1, A0.2, A0.2-Fix, A0.3, A0.4, A1.0, A1.1, A1.2, A1.3, A1.4, A1.5, A1.6, A1.7, A1.8, A1.9, A1.10a, A1.10b. Every unit records a determination, taskbook, formal report, machine artifact, result commit, fix commits where applicable, sample scope, scientific conclusion, warning boundary, and current artifact SHA-256. 37 unique commits and 38 frozen A1.2-A1.7 sources were directly verified. The existing A1.8 audit's 277 report/artifact checks remain intact.

## 4. A1.9-A1.10 consistency and blind provenance

- Three final methods, roles, thresholds, and model hashes match exactly across A1.9 and A1.10 pre-unlock artifacts.
- A1.10 target metrics, bootstrap summaries, grades, final claim status, JSON summary, and 21 rounded report values agree.
- Blind prediction bytes are identical before and after label unlock.
- Join integrity is complete at 3,318 rows with zero duplicates, unmatched rows, silent drops, or metadata mismatches.
- No test metric was recomputed in A1.11; the script only compared frozen fields and hashes.

## 5. Evidence registry and final claim matrix

- Evidence registry rows: 90
- Final claim matrix rows: 25
- Claim status counts: {"CONFIRMATORY_SUPPORTED": 2, "DESCRIPTIVE_ONLY": 3, "DEV_ONLY": 9, "EXPLORATORY_SUPPORTED": 1, "NOT_SUPPORTED": 2, "PROHIBITED_OVERCLAIM": 8}
- Final claim matrix SHA-256: `2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175`

The claim matrix SHA is the manuscript claim contract. Without a newly approved Stage, manuscript work may not add a confirmatory claim, enlarge scope, delete a limitation, or promote exploratory evidence.

## 6. Frozen final claims

### FC1 — Success

- Status: `CONFIRMATORY_SUPPORTED`
- AP: `0.654836`; AP lift: `0.389567`; F1: `0.682099`
- AP-lift 95% CI: `[0.326806, 0.455411]`
- Scope: official held-out tasks/trajectories within evaluated benchmark families.

### FC2 — Looping

- Status: `CONFIRMATORY_SUPPORTED`
- AP: `0.921769`; AP lift: `0.394829`; F1: `0.876987`
- AP-lift 95% CI: `[0.360965, 0.428598]`
- Scope: official held-out tasks/trajectories within evaluated benchmark families.

### FE1 — Side Effect

- Status: `EXPLORATORY_SUPPORTED`
- AP: `0.107279`; AP lift: `0.042851`; F1: `0.168582`
- AP-lift 95% CI: `[0.021245, 0.079200]`
- Required language: `exploratory_only`, low-support, not confirmatory.

## 7. Dev-only and prohibited claims

- Dev-only claims: 9; none upgraded from development evidence.
- Prohibited overclaims: 8.
- Not-supported claims: 2.
- Descriptive-only benchmark heterogeneity claims: 3.

## 8. Benchmark heterogeneity

Observed AP/F1 varies across assistantbench, visualwebarena, webarena, and workarena for all three targets. These rows are frozen as `DESCRIPTIVE_ONLY`; no preregistered pairwise inferential comparison supports wording that one benchmark significantly outperforms another.

## 9. Paper package

- Main held-out table SHA-256: `c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947`
- Per-benchmark table: `artifacts/a1_11_table_benchmark_results.csv`
- Dev evidence summary: `artifacts/a1_11_dev_evidence_summary.csv`
- Figure specification: `docs/a1_11_paper_figure_spec.md`
- Results outline: `docs/a1_11_paper_results_outline.md`
- Limitations ledger: `docs/a1_11_limitations_ledger.md` (8 frozen limitations)

## 10. A2 gap recommendation

The evidence is sufficient to start manuscript drafting now. The largest persuasive-evidence gap is a truly independent external benchmark/dataset for unseen-benchmark validity; mechanism validity is secondary. A2 design review should prioritize external validation, then lightweight mechanism validation, and should not prioritize additional model complexity.

## 11. Warnings and inconsistencies

Warnings retained: Side Effect low dev support; benchmark heterogeneity; A1.4 model-only transfer; non-causal ablations; no standard dataset license identifier; no calibration or deployment evidence. Core inconsistencies: none.

## 12. No-new-experiment guard

```text
new experiments = 0
model fits = 0
inference runs = 0
embedding runs = 0
test metric recomputations = 0
bootstrap reruns = 0
threshold changes = 0
eligibility changes = 0
model changes = 0
```

## 13. Tests and final Git condition

The deterministic consolidation script, static forbidden-operation guard, output-schema tests, exact core-metric checks, hash verification, claim-status checks, and rerun byte-stability checks must pass before commit. The enclosing independent A1.11b commit is not amended; final `git status --porcelain` must be empty.

## 14. Next stage

`READY_FOR_A2_DESIGN_REVIEW`

Stop. Do not execute A2 automatically.
