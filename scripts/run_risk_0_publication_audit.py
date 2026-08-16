"""Build the RISK-0 evidence inventory and verify frozen audit outputs.

This module never fits a model, runs inference, recomputes A1 metrics, searches
literature, or creates scientific figures.  The inventory phase is deliberately
separate from result verification so that no score artifact is needed before
the repository evidence inventory exists.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PREREG_COMMIT = "3a82dfbc44854a0c14f875ec260d6dafc8bf5302"
A3_3_RESULT = "152f03134f2a9c62cafbb380c625766d4c6b197a"
A3_2_ADDENDUM_RESULT = "bb9dc52467f58769f833e501aa5fa96cb1be9937"
A1_11_CLAIM_MATRIX_SHA256 = "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175"

COUNTER_NAMES = (
    "new_model_fits",
    "new_inference_runs",
    "new_embedding_runs",
    "A1_metric_recomputations",
    "bootstrap_reruns",
    "new_significance_tests",
    "threshold_changes",
    "eligibility_changes",
    "final_model_changes",
    "official_test_tuning",
    "external_dataset_downloads",
    "external_dataset_runs",
    "new_literature_searches",
    "new_scientific_figures",
)

DIMENSION_WEIGHTS = {
    "SV1": 15.0,
    "SV2": 15.0,
    "SV3": 20.0,
    "SV4": 20.0,
    "SV5": 15.0,
    "SV6": 15.0,
    "PC1": 25.0,
    "PC2": 20.0,
    "PC3": 15.0,
    "PC4": 15.0,
    "PC5": 15.0,
    "PC6": 10.0,
}

CRITERIA: dict[str, tuple[str, float, str]] = {
    "SV1.1": ("SV1", 0.20, "Research Question Clarity & Falsifiability"),
    "SV1.2": ("SV1", 0.20, "Construct Validity"),
    "SV1.3": ("SV1", 0.25, "Design-Question Alignment"),
    "SV1.4": ("SV1", 0.20, "Alternative-Explanation Control"),
    "SV1.5": ("SV1", 0.15, "Inference & Scope Alignment"),
    "SV2.1": ("SV2", 0.20, "Data Provenance & Version Integrity"),
    "SV2.2": ("SV2", 0.20, "Sampling & Coverage Validity"),
    "SV2.3": ("SV2", 0.20, "Label Definition & Operationalization"),
    "SV2.4": ("SV2", 0.25, "Label Quality & Consistency"),
    "SV2.5": ("SV2", 0.15, "Eligibility, Missingness & Class Support"),
    "SV3.1": ("SV3", 0.15, "Development/Test Separation"),
    "SV3.2": ("SV3", 0.15, "Group Leakage Control"),
    "SV3.3": ("SV3", 0.15, "Preregistration Discipline"),
    "SV3.4": ("SV3", 0.15, "Model / Threshold / Eligibility Freeze"),
    "SV3.5": ("SV3", 0.20, "Blind Prediction & Label-Unlock Integrity"),
    "SV3.6": ("SV3", 0.10, "Post-Test Tuning Control"),
    "SV3.7": ("SV3", 0.10, "Protocol Provenance & Auditability"),
    "SV4.1": ("SV4", 0.15, "Metric-Target Alignment"),
    "SV4.2": ("SV4", 0.15, "Baseline & Comparator Fairness"),
    "SV4.3": ("SV4", 0.15, "Evaluation Unit & Aggregation Validity"),
    "SV4.4": ("SV4", 0.20, "Uncertainty & Statistical Inference"),
    "SV4.5": ("SV4", 0.15, "Ablation / Sensitivity Validity"),
    "SV4.6": ("SV4", 0.10, "Threshold / Class-Imbalance Treatment"),
    "SV4.7": ("SV4", 0.10, "Statistical Interpretation Discipline"),
    "SV5.1": ("SV5", 0.20, "Resampling / Fold Stability"),
    "SV5.2": ("SV5", 0.25, "Benchmark / Domain Robustness"),
    "SV5.3": ("SV5", 0.15, "Model / Agent Robustness"),
    "SV5.4": ("SV5", 0.15, "Representation / Specification Robustness"),
    "SV5.5": ("SV5", 0.10, "Failure-Boundary Characterization"),
    "SV5.6": ("SV5", 0.15, "External-Validity Discipline"),
    "SV6.1": ("SV6", 0.25, "Claim-Evidence Traceability"),
    "SV6.2": ("SV6", 0.20, "Artifact & Git Provenance"),
    "SV6.3": ("SV6", 0.20, "Computational Reproducibility"),
    "SV6.4": ("SV6", 0.15, "Numeric Consistency"),
    "SV6.5": ("SV6", 0.10, "Negative Evidence & Limitation Preservation"),
    "SV6.6": ("SV6", 0.10, "Independent Auditability"),
    "PC1.1": ("PC1", 0.20, "Problem Novelty"),
    "PC1.2": ("PC1", 0.20, "Method / Representation Differentiation"),
    "PC1.3": ("PC1", 0.20, "Evaluation / Protocol Differentiation"),
    "PC1.4": ("PC1", 0.25, "Empirical Insight Novelty"),
    "PC1.5": ("PC1", 0.15, "Closest-Work Separation"),
    "PC2.1": ("PC2", 0.20, "Importance of the Research Problem"),
    "PC2.2": ("PC2", 0.25, "Importance of the Main Finding"),
    "PC2.3": ("PC2", 0.20, "General Scientific Usefulness"),
    "PC2.4": ("PC2", 0.20, "Insight / Surprise Value"),
    "PC2.5": ("PC2", 0.15, "Field Relevance & Timeliness"),
    "PC3.1": ("PC3", 0.25, "Core-result Evidence Depth"),
    "PC3.2": ("PC3", 0.15, "Baseline / Comparator Completeness"),
    "PC3.3": ("PC3", 0.20, "Robustness Evidence"),
    "PC3.4": ("PC3", 0.15, "Mechanism / Interpretation Evidence"),
    "PC3.5": ("PC3", 0.10, "Efficiency / Practical Characterization"),
    "PC3.6": ("PC3", 0.15, "Failure / Negative Evidence Coverage"),
    "PC4.1": ("PC4", 0.25, "Central Narrative Clarity"),
    "PC4.2": ("PC4", 0.20, "Contribution Independence"),
    "PC4.3": ("PC4", 0.20, "Evidence-to-Contribution Alignment"),
    "PC4.4": ("PC4", 0.15, "Section-level Coherence"),
    "PC4.5": ("PC4", 0.20, "Claim Compression / Message Efficiency"),
    "PC5.1": ("PC5", 0.25, "Obvious Objection Coverage"),
    "PC5.2": ("PC5", 0.20, "Novelty Attack Resistance"),
    "PC5.3": ("PC5", 0.15, "Method-Simplicity Defense"),
    "PC5.4": ("PC5", 0.15, "External-Validity Defense"),
    "PC5.5": ("PC5", 0.15, "Weak-result / Limitation Defense"),
    "PC5.6": ("PC5", 0.10, "Evidence Transparency"),
    "PC6.1": ("PC6", 0.30, "Scope Fit"),
    "PC6.2": ("PC6", 0.20, "Contribution-Level Fit"),
    "PC6.3": ("PC6", 0.15, "Article Depth / Workload Fit"),
    "PC6.4": ("PC6", 0.15, "Audience Fit"),
    "PC6.5": ("PC6", 0.10, "Manuscript Asset Readiness"),
    "PC6.6": ("PC6", 0.10, "Editorial / Formatting Readiness"),
}

MANDATORY_OBJECTIONS = (
    "novelty too weak",
    "method too simple",
    "handcrafted-feature shortcut",
    "construct overlap",
    "metadata confounding",
    "Looping/repetition overlap",
    "Side Effect low support",
    "no independent external benchmark",
    "benchmark heterogeneity",
    "dense semantics comparison limitations",
    "baseline sufficiency",
    "statistical support",
    "blind-heldout scope",
    "cross-paper comparability",
    "practical relevance",
)


@dataclass(frozen=True)
class InventorySpec:
    evidence_id: str
    source_stage: str
    source_path: str
    evidence_type: str
    supports_sv: str
    supports_pc: str
    summary: str
    direct_or_indirect: str = "DIRECT"
    notes: str = ""


INVENTORY_SPECS = (
    InventorySpec("R0E001", "CHARTER", "research/00_RESEARCH_CHARTER.md", "research_contract", "SV1;SV5", "PC2;PC4", "Frozen research question, H1, falsification conditions, protocol boundaries, and candidate contributions."),
    InventorySpec("R0E002", "A0.1", "docs/data_contract.md", "data_contract", "SV2;SV3", "PC3;PC5", "Pinned source revisions, label mappings, split contract, duplicate disagreements, license limitation, and test-sealing principle."),
    InventorySpec("R0E003", "A0.2", "docs/analysis_unit_policy.md", "analysis_unit_contract", "SV2;SV3", "PC3;PC5", "Frozen trajectory key, disagreement exclusions, eligibility rule, benchmark namespaces, and audit-only primary-label boundary."),
    InventorySpec("R0E004", "A0.4", "docs/input_contract.md", "input_contract", "SV1;SV2;SV3", "PC3;PC5", "Leak-safe input whitelist, permanent exclusions, identity isolation, view definitions, and non-inferred terminal semantics."),
    InventorySpec("R0E005", "A1.0", "docs/dev_corpus_build_report.md", "formal_report", "SV2;SV3;SV6", "PC3", "Complete 196-trajectory dev build, fixed revision, parsing coverage, leakage checks, excluded drift, and identity-token warning."),
    InventorySpec("R0E006", "A1.1", "docs/evaluation_protocol.md", "protocol_contract", "SV3;SV4", "PC3;PC5", "Frozen task-grouped folds, nested selection, threshold, metric, LOBO, single-class, and test-sealing rules."),
    InventorySpec("R0E007", "A1.1", "docs/pre_baseline_audit_report.md", "formal_report", "SV1;SV2;SV3", "PC3;PC5", "Group-key audit, drift review, natural errors, WorkArena literals, LOMO feasibility, and held-out class-support conditions."),
    InventorySpec("R0E008", "A1.2", "docs/stage_a1_2_minimal_baseline_report.md", "formal_report", "SV4;SV5;SV6", "PC3;PC5", "Grouped baseline execution, OOF coverage, selection verification, and Side Effect support boundary."),
    InventorySpec("R0E009", "A1.3", "docs/stage_a1_3_primary_lobo_report.md", "formal_report", "SV4;SV5;SV6", "PC3;PC5", "Primary four-family LOBO baselines, complete predictions, and single-class Side Effect handling."),
    InventorySpec("R0E010", "A1.4", "docs/stage_a1_4_leave_one_model_out_report.md", "formal_report", "SV5;SV6", "PC3;PC5", "Exploratory model-only transfer with incomplete cross-benchmark model coverage and explicit scope boundary."),
    InventorySpec("R0E011", "A1.5", "docs/stage_a1_5_structural_mechanism_ablation_report.md", "formal_report", "SV1;SV4;SV5", "PC3;PC5", "Frozen structural group ablations, exact S0 reproduction, descriptive dependencies, and Side Effect non-assessability."),
    InventorySpec("R0E012", "A1.6", "docs/stage_a1_6_group_aware_bootstrap_report.md", "formal_report", "SV4;SV5;SV6", "PC3;PC5", "Task-group cluster bootstrap, stable and uncertain contrasts, invalid-draw accounting, and non-significance interpretation."),
    InventorySpec("R0E013", "A1.7", "docs/stage_a1_7_frozen_dense_semantic_baseline_report.md", "formal_report", "SV4;SV5;SV6", "PC3;PC5", "Single frozen dense encoder comparison, stable Success signal, uncertain relative AP gains, stable F1 drop, and Side Effect diagnostic."),
    InventorySpec("R0E014", "A1.8", "docs/stage_a1_8_evidence_audit_report.md", "evidence_audit", "SV1;SV4;SV5;SV6", "PC3;PC4;PC5", "Evidence-only claim audit preserving unsupported, dev-only, descriptive, and prohibited interpretations."),
    InventorySpec("R0E015", "A1.9", "docs/stage_a1_9_final_method_freeze_report.md", "formal_report", "SV3;SV6", "PC3;PC5", "Final method, configuration, threshold, fit budget, model hash, role, and claim freeze before test access."),
    InventorySpec("R0E016", "A1.10a", "docs/stage_a1_10a_blind_test_inference_report.md", "formal_report", "SV3;SV6", "PC3;PC5", "Blind inference, zero-fit predictions, hash freeze, label-access counters, and preserved pre-inference fix."),
    InventorySpec("R0E017", "A1.10b", "docs/stage_a1_10_official_test_evaluation_report.md", "formal_report", "SV3;SV4;SV5;SV6", "PC3;PC5", "Blind-before-label provenance, join integrity, confirmatory held-out signals, bootstrap integrity, heterogeneity, and post-unlock zero tuning."),
    InventorySpec("R0E018", "A1.10b", "artifacts/a1_10_independent_verification.json", "independent_verification", "SV3;SV4;SV6", "PC3;PC5", "Independent frozen-result verification for official-test scoring and provenance."),
    InventorySpec("R0E019", "A1.11", "docs/stage_a1_11_final_evidence_consolidation_report.md", "evidence_consolidation", "SV1;SV3;SV4;SV5;SV6", "PC3;PC4;PC5", "Complete A0-A1.10 provenance, final claims, evidence gaps, warnings, and no-new-experiment guard."),
    InventorySpec("R0E020", "A1.11", "artifacts/a1_11_final_claim_matrix.csv", "claim_matrix", "SV1;SV5;SV6", "PC3;PC4;PC5", "Frozen 25-row manuscript claim contract with confirmatory, exploratory, dev-only, descriptive, unsupported, and prohibited statuses."),
    InventorySpec("R0E021", "A1.11", "artifacts/a1_11_evidence_registry.csv", "evidence_registry", "SV4;SV5;SV6", "PC3;PC5", "Ninety-row evidence registry tracing formal metrics and limitations to source artifacts and commits."),
    InventorySpec("R0E022", "A1.11", "docs/a1_11_limitations_ledger.md", "limitations_ledger", "SV1;SV2;SV5;SV6", "PC3;PC5", "Frozen eight-item limitation ledger covering external validity, labels, causality, heterogeneity, relative comparisons, and deployment."),
    InventorySpec("R0E023", "A2.1", "docs/stage_a2_1_efficiency_benchmark_report.md", "formal_report", "SV6", "PC2;PC3;PC5", "Environment-specific B2/B4 extraction, storage, memory, and inference characterization with no A1 performance recomputation."),
    InventorySpec("R0E024", "A2.1", "artifacts/a2_1_run_summary.json", "machine_summary", "SV6", "PC3;PC5", "Machine-readable efficiency results, hashes, repetitions, provenance, and scientific-operation counters."),
    InventorySpec("R0E025", "A2.2", "docs/stage_a2_2_interpretability_confounder_error_analysis_report.md", "formal_report", "SV1;SV4;SV5;SV6", "PC3;PC5", "Post-freeze coefficients, metadata-only diagnostic signal, deterministic error cases, and explicit non-causal scope."),
    InventorySpec("R0E026", "A2.2", "docs/a2_2_error_analysis.md", "error_analysis", "SV1;SV5", "PC3;PC5", "Deterministic Success/Looping FP/FN cases illustrating morphology-semantic and productive-repetition boundaries."),
    InventorySpec("R0E027", "A2.3", "docs/stage_a2_3_baseline_paper_package_report.md", "publication_package", "SV5;SV6", "PC1;PC2;PC3;PC4;PC5", "Baseline completeness, paper story, contributions, external-validation deferral, warnings, and package verification."),
    InventorySpec("R0E028", "A2.3", "artifacts/a2_3_baseline_completeness_matrix.csv", "baseline_registry", "SV4;SV5", "PC3;PC5", "Frozen local baseline tiers and literature-context boundaries."),
    InventorySpec("R0E029", "A2.3", "docs/a2_3_final_limitations_ledger.md", "limitations_ledger", "SV1;SV2;SV5;SV6", "PC3;PC4;PC5", "Twelve retained limitations including metadata confounding, low Side Effect support, no deployment evidence, and environment-specific timing."),
    InventorySpec("R0E030", "A3.1", "docs/stage_a3_1_final_figures_tables_report.md", "formal_report", "SV6", "PC3;PC4;PC5", "Final paper tables/figures, exact hashes, visual QA, claim boundaries, and zero scientific counters."),
    InventorySpec("R0E031", "A3.1", "artifacts/a3_1_artifact_registry.csv", "artifact_registry", "SV6", "PC3;PC4", "Thirty-three paper-facing artifacts with exact source and output hashes."),
    InventorySpec("R0E032", "A3.2", "docs/stage_a3_2_literature_baseline_verification_report.md", "literature_audit", "SV6", "PC1;PC2;PC3;PC5", "Frozen primary-source literature audit, zero directly comparable works, and no valid numeric cross-paper head-to-head."),
    InventorySpec("R0E033", "A3.2", "artifacts/a3_2_verified_literature_registry.csv", "literature_registry", "SV6", "PC1;PC2;PC5", "Primary-source verified identities, source status, comparability, and unresolved metadata without inference."),
    InventorySpec("R0E034", "A3.2", "artifacts/a3_2_positioning_matrix.csv", "positioning_matrix", "SV1;SV5", "PC1;PC2;PC5", "Property-only comparison across verified works and THIS_WORK."),
    InventorySpec("R0E035", "A3.2_ADDENDUM", "docs/a3_2_closest_work_addendum_report.md", "closest_work_audit", "SV6", "PC1;PC2;PC5", "Targeted WebGraphEval/WebStep audit, Similar identity resolution, and closest-work comparability recheck."),
    InventorySpec("R0E036", "A3.2_ADDENDUM", "artifacts/a3_2_addendum_run_summary.json", "machine_summary", "SV6", "PC1;PC5", "Machine-readable addendum gates, comparability counts, hashes, and zero scientific counters."),
    InventorySpec("R0E037", "A3.2", "docs/a3_2_positioning_and_novelty_contract.md", "positioning_contract", "SV1;SV5", "PC1;PC2;PC4;PC5", "Narrow structural-signal positioning, allowed/prohibited novelty wording, and closest-work boundaries."),
    InventorySpec("R0E038", "A3.3", "docs/stage_a3_3_manuscript_evidence_freeze_report.md", "formal_report", "SV5;SV6", "PC3;PC4;PC5", "Frozen manuscript evidence package, 310 evidence rows, 58 claim-ledger rows, 150 numeric mappings, and readiness status."),
    InventorySpec("R0E039", "A3.3", "artifacts/a3_3_run_summary.json", "machine_summary", "SV6", "PC3;PC4;PC5", "Machine-readable evidence-freeze gates, counts, hashes, zero counters, and drafting readiness."),
    InventorySpec("R0E040", "A3.3", "artifacts/a3_3_manuscript_evidence_registry.csv", "manuscript_evidence_registry", "SV5;SV6", "PC1;PC2;PC3;PC4;PC5", "310-row manuscript evidence registry linking claims, numbers, sources, citations, sections, and caveats."),
    InventorySpec("R0E041", "A3.3", "artifacts/a3_3_claim_ledger.csv", "claim_ledger", "SV1;SV5;SV6", "PC1;PC4;PC5", "Fifty-eight approved, caveated, and forbidden manuscript claims with evidence and scope boundaries."),
    InventorySpec("R0E042", "A3.3", "artifacts/a3_3_numeric_consistency_map.csv", "numeric_consistency_map", "SV6", "PC3;PC4;PC5", "One hundred fifty frozen manuscript display values copied from A3.1 with exact verification."),
    InventorySpec("R0E043", "A3.3", "artifacts/a3_3_manuscript_readiness_checklist.csv", "readiness_checklist", "SV6", "PC3;PC4;PC5", "Twenty-five passed readiness checks spanning evidence, claims, boundaries, citations, numeric consistency, and counters."),
    InventorySpec("R0E044", "A3.3", "docs/a3_3_contribution_contract.md", "contribution_contract", "SV1;SV6", "PC1;PC2;PC4;PC5", "Four frozen contributions, support, scope, and forbidden upgrades."),
    InventorySpec("R0E045", "A3.3", "docs/a3_3_manuscript_limitations_contract.md", "limitations_contract", "SV1;SV2;SV5;SV6", "PC3;PC4;PC5", "Fourteen mandatory manuscript limitations including no independent external validation and protocol-mismatched cross-paper comparison."),
    InventorySpec("R0E046", "A3.3", "docs/a3_3_discussion_contract.md", "discussion_contract", "SV1;SV5;SV6", "PC2;PC4;PC5", "Discussion roles and mandatory boundaries for prediction, causality, semantics, confounding, efficiency, and related work."),
    InventorySpec("R0E047", "A3.3", "docs/a3_3_related_work_integration_contract.md", "related_work_contract", "SV6", "PC1;PC2;PC4;PC5", "Verified citation-only integration and property-comparison boundary."),
    InventorySpec("R0E048", "PROVENANCE", "artifacts/source_manifest.json", "source_manifest", "SV2;SV6", "PC3", "Pinned raw metadata sources, revisions, retrieval metadata, and hashes."),
)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str, root: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _reachable(commit: str, root: Path = ROOT) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0


def hard_gates(root: Path = ROOT, require_clean: bool = True) -> dict[str, object]:
    if require_clean and _git("status", "--porcelain", root=root):
        raise RuntimeError("RISK-0 hard gate failed: Git working tree is not clean")
    if not _reachable(PREREG_COMMIT, root):
        raise RuntimeError("RISK-0 hard gate failed: preregistration is not reachable")
    if not _reachable(A3_3_RESULT, root):
        raise RuntimeError("RISK-0 hard gate failed: A3.3 result is not reachable")
    if not _reachable(A3_2_ADDENDUM_RESULT, root):
        raise RuntimeError("RISK-0 hard gate failed: A3.2 addendum result is not reachable")
    matrix = root / "artifacts" / "a1_11_final_claim_matrix.csv"
    if sha256_path(matrix) != A1_11_CLAIM_MATRIX_SHA256:
        raise RuntimeError("RISK-0 hard gate failed: A1.11 claim matrix hash drift")
    rows = read_csv(matrix)
    frozen = {row["target"]: row["status"] for row in rows[:3]}
    expected = {
        "Success": "CONFIRMATORY_SUPPORTED",
        "Looping": "CONFIRMATORY_SUPPORTED",
        "Side Effect": "EXPLORATORY_SUPPORTED",
    }
    if frozen != expected:
        raise RuntimeError(f"RISK-0 hard gate failed: frozen claims {frozen!r}")
    summary = json.loads((root / "artifacts" / "a3_3_run_summary.json").read_text(encoding="utf-8"))
    if not summary.get("manuscript_evidence_frozen") or not summary.get("ready_for_manuscript_drafting"):
        raise RuntimeError("RISK-0 hard gate failed: A3.3 final state missing")
    return {
        "head": _git("rev-parse", "HEAD", root=root),
        "preregistration": PREREG_COMMIT,
        "a3_3_result": A3_3_RESULT,
        "a3_2_addendum_result": A3_2_ADDENDUM_RESULT,
        "a1_11_claim_matrix_sha256": A1_11_CLAIM_MATRIX_SHA256,
        "claims": expected,
        "manuscript_evidence_frozen": True,
        "ready_for_manuscript_drafting": True,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_inventory(
    root: Path = ROOT,
    output_root: Path | None = None,
    *,
    require_clean: bool = True,
) -> list[dict[str, str]]:
    """Generate Phase-1 evidence inventory without creating score artifacts."""
    hard_gates(root, require_clean=require_clean)
    output_root = output_root or root
    rows: list[dict[str, str]] = []
    for spec in INVENTORY_SPECS:
        source = root / spec.source_path
        if not source.is_file():
            raise RuntimeError(f"Missing inventory source: {spec.source_path}")
        source_commit = _git("log", "-1", "--format=%H", "--", spec.source_path, root=root)
        if not source_commit:
            raise RuntimeError(f"Untracked inventory source: {spec.source_path}")
        rows.append(
            {
                "evidence_id": spec.evidence_id,
                "source_stage": spec.source_stage,
                "source_path": spec.source_path,
                "source_commit": source_commit,
                "source_hash_or_identifier": sha256_path(source),
                "evidence_type": spec.evidence_type,
                "supports_sv": spec.supports_sv,
                "supports_pc": spec.supports_pc,
                "summary": spec.summary,
                "direct_or_indirect": spec.direct_or_indirect,
                "verified": "true",
                "notes": spec.notes,
            }
        )
    write_csv(
        output_root / "artifacts" / "risk_0_evidence_inventory.csv",
        (
            "evidence_id",
            "source_stage",
            "source_path",
            "source_commit",
            "source_hash_or_identifier",
            "evidence_type",
            "supports_sv",
            "supports_pc",
            "summary",
            "direct_or_indirect",
            "verified",
            "notes",
        ),
        rows,
    )
    return rows


def _float(value: str) -> float:
    return float(value.strip())


def _score(value: str) -> int:
    parsed = int(value)
    if parsed not in {0, 1, 2, 3, 4}:
        raise AssertionError(f"Invalid score: {value}")
    return parsed


def _assert_close(actual: float, expected: float, label: str) -> None:
    if abs(actual - expected) > 1e-9:
        raise AssertionError(f"{label}: expected {expected}, got {actual}")


def verify_results(root: Path = ROOT, require_clean: bool = False) -> dict[str, object]:
    """Verify every frozen RISK-0 result rule against committed-source evidence."""
    gates = hard_gates(root, require_clean=require_clean)
    inventory = read_csv(root / "artifacts" / "risk_0_evidence_inventory.csv")
    if [row["evidence_id"] for row in inventory] != [spec.evidence_id for spec in INVENTORY_SPECS]:
        raise AssertionError("Evidence inventory IDs/order do not match the frozen implementation")
    inventory_by_id = {row["evidence_id"]: row for row in inventory}
    for row in inventory:
        source = root / row["source_path"]
        if row["verified"] != "true" or not source.is_file():
            raise AssertionError(f"Unverified inventory evidence: {row['evidence_id']}")
        if sha256_path(source) != row["source_hash_or_identifier"]:
            raise AssertionError(f"Inventory source hash drift: {row['evidence_id']}")
        source_commit = _git("log", "-1", "--format=%H", "--", row["source_path"], root=root)
        if source_commit != row["source_commit"]:
            raise AssertionError(f"Inventory source commit drift: {row['evidence_id']}")

    primary = read_csv(root / "artifacts" / "risk_0_primary_scores.csv")
    if len(primary) != 69 or {row["criterion_id"] for row in primary} != set(CRITERIA):
        raise AssertionError("Primary scores must contain exactly all 69 frozen subcriteria")
    primary_by_id = {row["criterion_id"]: row for row in primary}
    valid_status = {"VERIFIED", "PARTIALLY_VERIFIED", "NOT_VERIFIED", "CONTRADICTED", "NOT_APPLICABLE"}
    valid_confidence = {"HIGH", "MEDIUM", "LOW"}
    valid_judgment = {"EVIDENCE_DRIVEN", "MIXED", "EXPERT_JUDGMENT"}
    for criterion_id, row in primary_by_id.items():
        dimension, internal_weight, name = CRITERIA[criterion_id]
        if row["dimension"] != dimension or row["criterion_name"] != name:
            raise AssertionError(f"Frozen criterion drift: {criterion_id}")
        _assert_close(_float(row["dimension_weight"]), DIMENSION_WEIGHTS[dimension], f"{criterion_id} dimension weight")
        _assert_close(_float(row["internal_weight"]), internal_weight, f"{criterion_id} internal weight")
        if row["evidence_status"] not in valid_status or row["evidence_confidence"] not in valid_confidence or row["judgment_type"] not in valid_judgment:
            raise AssertionError(f"Invalid evidence metadata: {criterion_id}")
        evidence_ids = [item for item in row["evidence_ids"].split(";") if item]
        if not set(evidence_ids) <= set(inventory_by_id):
            raise AssertionError(f"Unknown evidence ID in {criterion_id}")
        if dimension == "PC6":
            if row["evidence_status"] != "NOT_APPLICABLE" or row["primary_score_0_4"] or row["judgment_type"] != "EXPERT_JUDGMENT":
                raise AssertionError("PC6 must be retained as NOT_SCORED / NOT_APPLICABLE")
        else:
            score = _score(row["primary_score_0_4"])
            if score == 4 and not evidence_ids:
                raise AssertionError(f"Score 4 lacks persistent evidence: {criterion_id}")

    adversarial = read_csv(root / "artifacts" / "risk_0_adversarial_scores.csv")
    if len(adversarial) != 69 or {row["criterion_id"] for row in adversarial} != set(CRITERIA):
        raise AssertionError("Adversarial scores must contain exactly all 69 subcriteria")
    adversarial_by_id = {row["criterion_id"]: row for row in adversarial}
    final_rows = read_csv(root / "artifacts" / "risk_0_final_scores.csv")
    subcriteria = [row for row in final_rows if row["record_type"] == "SUBCRITERION"]
    dimensions = {row["dimension"]: row for row in final_rows if row["record_type"] == "DIMENSION"}
    if len(subcriteria) != 69 or set(dimensions) != set(DIMENSION_WEIGHTS):
        raise AssertionError("Final scores require 69 subcriteria and 12 dimension summaries")
    final_by_id = {row["criterion_id"]: row for row in subcriteria}
    computed_dimensions: dict[str, float | None] = {}
    for criterion_id, primary_row in primary_by_id.items():
        adversarial_row = adversarial_by_id[criterion_id]
        final_row = final_by_id[criterion_id]
        if final_row["dimension"] != CRITERIA[criterion_id][0]:
            raise AssertionError(f"Final dimension mismatch: {criterion_id}")
        if CRITERIA[criterion_id][0] == "PC6":
            if adversarial_row["adversarial_score_0_4"] or final_row["final_subscore_0_4"]:
                raise AssertionError("PC6 must remain unscored in every score artifact")
            continue
        primary_score = _score(primary_row["primary_score_0_4"])
        if _score(adversarial_row["primary_score_0_4"]) != primary_score:
            raise AssertionError(f"Adversarial primary mismatch: {criterion_id}")
        adversarial_score = _score(adversarial_row["adversarial_score_0_4"])
        if adversarial_score > primary_score:
            raise AssertionError(f"Silent adversarial upward correction: {criterion_id}")
        final_score = _score(final_row["final_subscore_0_4"])
        if final_score != min(primary_score, adversarial_score):
            raise AssertionError(f"Conservative reconciliation failed: {criterion_id}")

    for dimension in DIMENSION_WEIGHTS:
        summary_row = dimensions[dimension]
        if dimension == "PC6":
            if summary_row["final_dimension_score"] or summary_row["raw_dimension_score"]:
                raise AssertionError("PC6 dimension summary must be unscored")
            computed_dimensions[dimension] = None
            continue
        raw = DIMENSION_WEIGHTS[dimension] * sum(
            CRITERIA[row["criterion_id"]][1] * _score(row["final_subscore_0_4"]) / 4.0
            for row in subcriteria
            if row["dimension"] == dimension
        )
        _assert_close(_float(summary_row["raw_dimension_score"]), raw, f"{dimension} raw")
        if summary_row["cap_triggered"] == "true":
            cap = _float(summary_row["cap_value"])
            expected_final = min(raw, cap)
        elif summary_row["cap_triggered"] == "false":
            expected_final = raw
        else:
            raise AssertionError(f"Invalid cap flag: {dimension}")
        _assert_close(_float(summary_row["final_dimension_score"]), expected_final, f"{dimension} final")
        computed_dimensions[dimension] = expected_final

    critical = read_csv(root / "artifacts" / "risk_0_critical_risks.csv")
    if {row["risk_id"] for row in critical} != {f"CR{i}" for i in range(1, 8)} | {f"PCR{i}" for i in range(1, 6)}:
        raise AssertionError("Critical-risk register must contain CR1-CR7 and PCR1-PCR5")
    if any(row["status"] not in {"ABSENT", "POSSIBLE", "CONFIRMED"} for row in critical):
        raise AssertionError("Invalid critical-risk status")

    objections = read_csv(root / "artifacts" / "risk_0_reviewer_objections.csv")
    if not objections or not set(MANDATORY_OBJECTIONS) <= {row["objection"] for row in objections}:
        raise AssertionError("Reviewer matrix is missing mandatory objections")
    if any(row["status"] not in {"ADDRESSED_BY_EVIDENCE", "BOUNDED_BY_LIMITATION", "PARTIALLY_RESOLVED", "UNRESOLVED_MAJOR"} for row in objections):
        raise AssertionError("Invalid reviewer-objection status")

    risks = read_csv(root / "artifacts" / "risk_0_risk_register.csv")
    if any(row["severity"] not in {"MAJOR", "MODERATE", "MINOR"} for row in risks):
        raise AssertionError("Invalid non-critical risk severity")

    summary = json.loads((root / "artifacts" / "risk_0_run_summary.json").read_text(encoding="utf-8"))
    for name in COUNTER_NAMES:
        if summary.get(name) != 0:
            raise AssertionError(f"Scientific operation counter is nonzero: {name}")
    svs = sum(float(computed_dimensions[f"SV{i}"]) for i in range(1, 7))
    core_raw = sum(float(computed_dimensions[f"PC{i}"]) for i in range(1, 6))
    core_normalized = core_raw / 90.0 * 100.0
    _assert_close(float(summary["svs"]), svs, "SVS")
    _assert_close(float(summary["core_pcs_raw"]), core_raw, "Core PCS raw")
    _assert_close(float(summary["core_pcs_normalized"]), core_normalized, "Core PCS normalized")
    if summary["pc6_status"] != "NOT_SCORED" or summary["target_specific_pcs"] != "NOT_AVAILABLE":
        raise AssertionError("PC6 / target-specific PCS rule violated")
    confirmed = any(row["status"] == "CONFIRMED" for row in critical)
    possible = any(row["status"] == "POSSIBLE" for row in critical)
    unresolved_major = any(row["severity"] == "MAJOR" for row in risks) or any(row["status"] == "UNRESOLVED_MAJOR" for row in objections)
    if confirmed or svs < 70 or core_normalized < 60:
        expected_decision = "NO_GO"
    elif possible or unresolved_major or svs < 80 or core_normalized < 70:
        expected_decision = "GO_WITH_MITIGATION"
    else:
        expected_decision = "GO"
    if summary["final_publication_decision"] != expected_decision:
        raise AssertionError(f"Frozen decision rule requires {expected_decision}")
    report = (root / "docs" / "risk_0_publication_risk_audit_report.md").read_text(encoding="utf-8")
    for required in ("Scientific Validity Score", "Core Publication Competitiveness Score", expected_decision, "What Would Change the Decision"):
        if required not in report:
            raise AssertionError(f"Report missing required marker: {required}")
    for relative, expected_hash in summary["output_hashes"].items():
        if relative == "artifacts/risk_0_run_summary.json":
            raise AssertionError("Run summary must not self-hash")
        if sha256_path(root / relative) != expected_hash:
            raise AssertionError(f"Output hash mismatch: {relative}")
    return {
        "gates": gates,
        "inventory_count": len(inventory),
        "criterion_count": len(primary),
        "svs": svs,
        "core_pcs_raw": core_raw,
        "core_pcs_normalized": core_normalized,
        "decision": expected_decision,
        "reviewer_objection_count": len(objections),
        "risk_count": len(risks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("inventory", "verify"), required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    if args.phase == "inventory":
        rows = build_inventory(ROOT)
        print(json.dumps({"phase": "inventory", "rows": len(rows)}, sort_keys=True))
    else:
        result = verify_results(ROOT, require_clean=not args.allow_dirty)
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
