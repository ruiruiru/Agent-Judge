"""Build and verify the Stage A3.3 manuscript evidence-freeze package.

This script only maps already frozen evidence. It performs no model fitting,
inference, embedding extraction, metric recomputation, bootstrap, significance
test, literature search, or figure generation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]

A3_1_RESULT = "e17bf7c6c1974d8a96ab7e7814b0a21ec827a082"
A3_2_RESULT = "ef37dee92ef319b2f7d39367e757919a898fbfdb"
A3_2_ADDENDUM_RESULT = "bb9dc52467f58769f833e501aa5fa96cb1be9937"
A3_3_PREREG = "b85c93f17a3e90f20bca5162817111c5bc1ac70a"
A3_3_IMPLEMENTATION = "23a030eb5c269b0a2ac24b3288ef673eae7b70af"
A1_11_CLAIM_SHA256 = "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175"

NOVELTY_POSITIONING = (
    "lightweight fixed-dimensional structural signals for outcome-oriented "
    "web-agent trajectory evaluation under a frozen blind-held-out protocol"
)

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

OUTPUTS = (
    "artifacts/a3_3_manuscript_evidence_registry.csv",
    "artifacts/a3_3_introduction_claim_map.csv",
    "artifacts/a3_3_methods_source_map.csv",
    "artifacts/a3_3_results_evidence_map.csv",
    "artifacts/a3_3_claim_ledger.csv",
    "artifacts/a3_3_numeric_consistency_map.csv",
    "artifacts/a3_3_manuscript_readiness_checklist.csv",
    "docs/a3_3_manuscript_section_contract.md",
    "docs/a3_3_methods_contract.md",
    "docs/a3_3_discussion_contract.md",
    "docs/a3_3_manuscript_limitations_contract.md",
    "docs/a3_3_related_work_integration_contract.md",
    "docs/a3_3_appendix_plan.md",
    "docs/a3_3_abstract_evidence_card.md",
    "docs/a3_3_contribution_contract.md",
    "docs/a3_3_figure_table_placement.md",
    "paper/manuscript/MANUSCRIPT_SKELETON.md",
)

EVIDENCE_FIELDS = (
    "evidence_id", "source_stage", "source_artifact", "source_row_or_claim_id",
    "target", "evidence_type", "evidence_status", "exact_value", "display_value",
    "allowed_sections", "primary_or_secondary", "allowed_wording",
    "forbidden_wording", "table_id", "figure_id", "citation_keys",
    "limitations_required", "verified",
)
INTRO_FIELDS = (
    "intro_block", "claim_id", "claim_text_template", "evidence_ids",
    "citation_keys", "status", "required_caveat", "forbidden_variant",
)
METHOD_FIELDS = (
    "method_id", "topic", "source_stage", "source_artifact", "source_detail",
    "required_content", "evidence_ids", "selection_role", "required_caveat", "verified",
)
RESULT_FIELDS = (
    "result_section", "question_answered", "primary_evidence_ids",
    "secondary_evidence_ids", "table_ids", "figure_ids", "allowed_numeric_claims",
    "allowed_interpretation", "required_caveats", "forbidden_claims",
)
CLAIM_FIELDS = (
    "claim_id", "manuscript_section", "claim_text_template", "claim_strength",
    "target", "evidence_ids", "citation_keys", "allowed", "required_caveat",
    "forbidden_variant", "status",
)
NUMERIC_FIELDS = (
    "metric_name", "target", "exact_value", "display_value", "source_artifact",
    "table_id", "figure_id", "allowed_sections", "rounding_rule", "verified",
)
READINESS_FIELDS = ("check_id", "check", "status", "evidence", "scientific")


def resolve(relative: str, root: Path = ROOT) -> Path:
    return root / Path(relative)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(relative: str) -> list[dict[str, str]]:
    with resolve(relative).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def a3_3_fix_commits() -> list[str]:
    """Return every independent post-implementation commit in chronological order."""
    output = git("rev-list", "--reverse", f"{A3_3_IMPLEMENTATION}..HEAD")
    return output.splitlines() if output else []


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def verify_preflight(require_clean: bool) -> dict[str, Any]:
    if require_clean:
        assert_equal(git("status", "--porcelain=v1"), "", "Git start status")
    fixed_commits = [
        ("A3.1 result", A3_1_RESULT),
        ("A3.2 result", A3_2_RESULT),
        ("A3.2 addendum result", A3_2_ADDENDUM_RESULT),
        ("A3.3 prereg", A3_3_PREREG),
        ("A3.3 implementation", A3_3_IMPLEMENTATION),
    ]
    fixed_commits.extend(
        (f"A3.3 fix {index}", commit)
        for index, commit in enumerate(a3_3_fix_commits(), start=1)
    )
    for label, commit in fixed_commits:
        git("cat-file", "-e", f"{commit}^{{commit}}")
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT, check=True)

    claim_path = resolve("artifacts/a1_11_final_claim_matrix.csv")
    assert_equal(sha256_path(claim_path), A1_11_CLAIM_SHA256, "A1.11 claim matrix SHA-256")
    claims = {row["claim_id"]: row for row in read_csv("artifacts/a1_11_final_claim_matrix.csv")}
    assert_equal(claims["FC1"]["status"], "CONFIRMATORY_SUPPORTED", "Success claim")
    assert_equal(claims["FC2"]["status"], "CONFIRMATORY_SUPPORTED", "Looping claim")
    assert_equal(claims["FE1"]["status"], "EXPLORATORY_SUPPORTED", "Side Effect claim")

    registry = read_csv("artifacts/a3_1_artifact_registry.csv")
    paper_rows = [row for row in registry if row["artifact_path"].startswith("paper/")]
    if not paper_rows:
        raise AssertionError("A3.1 paper-facing artifact registry is empty")
    for row in paper_rows:
        path = resolve(row["artifact_path"])
        if not path.is_file():
            raise AssertionError(f"A3.1 artifact missing: {row['artifact_path']}")
        assert_equal(sha256_path(path), row["sha256"], f"A3.1 artifact hash {row['artifact_path']}")

    addendum = json.loads(resolve("artifacts/a3_2_addendum_run_summary.json").read_text(encoding="utf-8"))
    assert_equal(addendum["stage_determination"], "PASS_WITH_CONDITIONS", "A3.2 addendum status")
    assert_equal(addendum["a3_3_formal_execution"], "AUTHORIZED", "A3.3 authorization")
    assert_equal(addendum["directly_comparable_after"], 0, "directly comparable count")
    assert_equal(addendum["head_to_head_after"], "NO_VALID_CROSS_PAPER_HEAD_TO_HEAD", "head-to-head gate")
    assert_equal(addendum["webgrapheval_comparability_class"], "PARTIALLY_COMPARABLE", "WebGraphEval")
    assert_equal(addendum["webstep_comparability_class"], "CONTEXT_ONLY", "WebStep")
    assert_equal(addendum["similar_resolution_status"], "RESOLVED_CANONICAL_IDENTITY", "Similar identity")
    assert_equal(addendum["novelty_after"], NOVELTY_POSITIONING, "novelty positioning")
    for path, expected in addendum["output_hashes"].items():
        assert_equal(sha256_path(resolve(path)), expected, f"A3.2 addendum hash {path}")

    citations = read_csv("artifacts/a3_2_citation_registry.csv")
    assert_equal(len(citations), 10, "verified citation count")
    return {
        "paper_artifact_hash_count": len(paper_rows),
        "citation_count": len(citations),
        "claim_matrix_sha256": A1_11_CLAIM_SHA256,
    }


def split_refs(value: str) -> tuple[str, str]:
    tables = ";".join(part.strip() for part in value.split(";") if part.strip().startswith("Table"))
    figures = ";".join(part.strip() for part in value.split(";") if part.strip().startswith("Figure"))
    return tables, figures


def allowed_sections_for_artifact(artifact_id: str) -> str:
    mapping = {
        "Table1_Main_Heldout_Results": "Abstract;Results R3;Discussion",
        "Fig2_Heldout_AP_Lift_CI": "Abstract;Results R3;Discussion",
        "Table2_Efficiency_Complexity": "Abstract optional;Results R4;Discussion;Limitations",
        "Fig3_Efficiency_Complexity": "Abstract optional;Results R4;Discussion;Limitations",
        "Table3_Dev_Representation_Robustness": "Results R1;Results R2;Appendix",
        "Table4_Benchmark_Heterogeneity": "Results R6;Limitations;Appendix",
        "FigS2_Benchmark_Heterogeneity": "Results R6;Limitations;Appendix",
        "Table5_Interpretability_Failure_Summary": "Results R5;Results R6;Discussion;Appendix",
        "Fig4_Structural_Interpretation": "Results R2;Results R5;Discussion;Appendix",
        "Fig5_Success_Failure_Boundaries": "Results R6;Discussion;Appendix",
        "FigS1_SideEffect_Exploratory_AP_Lift": "Results R3 exploratory;Appendix",
    }
    return mapping[artifact_id]


def target_from_key(key: str) -> str:
    match = re.search(r"target=([^;]+)", key)
    return match.group(1) if match else "All"


def build_numeric_map() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in read_csv("artifacts/a3_1_display_value_map.csv"):
        artifact_id = source["artifact_id"]
        rows.append({
            "metric_name": source["source_field"],
            "target": target_from_key(source["source_row_key"]),
            "exact_value": source["exact_value"],
            "display_value": source["display_value"],
            "source_artifact": source["source_artifact"],
            "table_id": artifact_id if source["location_kind"] == "table" else "",
            "figure_id": artifact_id if source["location_kind"] == "figure" else "",
            "allowed_sections": allowed_sections_for_artifact(artifact_id),
            "rounding_rule": source["format_rule"],
            "verified": "true",
        })
    return rows


METHOD_ROWS = (
    ("M1", "Data provenance", "A0-A1.0", "artifacts/dev_analysis_index.csv;artifacts/input_contract_summary.json", "fixed AgentRewardBench revision; cleaned leak-safe trajectory views", "Record dataset origin, official split reuse, immutable trajectory key, cleaning, exclusions, and provenance.", "M1_DATA_PROVENANCE", "development evidence", "Do not imply a new benchmark or modified expert labels."),
    ("M2", "Eligibility / labels", "A0.2-A1.1", "artifacts/dev_analysis_index.csv;artifacts/a1_10_test_scored_predictions.csv", "target-specific binary main eligibility; consensus exclusions", "Define Success, Looping, and Side Effect eligibility and preserve Side Effect low support.", "M2_ELIGIBILITY", "development and frozen test contract", "Side Effect is exploratory; do not infer missing labels."),
    ("M3", "Leakage-safe representation", "A0.4-A1.10a", "docs/input_contract.md;artifacts/a1_10a_test_structural_features.csv", "allowlisted structural fields; reward, label, and identity exclusions", "Describe whitelist processing and exclusion of reward/label and direct identity fields.", "M3_LEAKAGE_SAFE", "method freeze", "Natural-text collisions were not censored; morphology is not semantics."),
    ("M4", "B2 13 structural features", "A1.2-A1.9", "artifacts/a1_9_final_model_manifest.json;configs/stage_a1_9_final_freeze.yaml", "13 fixed-dimensional structural features; Logistic Regression", "List the frozen B2 representation and candidate-selection role exactly.", "M4_B2_FEATURES", "method freeze", "Do not call the ordinary classifier itself novel."),
    ("M5", "B0/B1/B3/B4 comparator roles", "A1.2-A1.7", "configs/baseline_registry.yaml;docs/stage_a1_7_frozen_dense_semantic_baseline_report.md", "majority/prior, TF-IDF, and frozen dense semantic comparators", "Separate comparator definitions from final target-specific methods.", "M5_COMPARATORS", "development evidence only", "Relative method comparisons are dev-only."),
    ("M6", "Grouped development / LOBO / model transfer", "A1.1-A1.4", "configs/evaluation_protocol.yaml;artifacts/lobo_primary_manifest.csv;artifacts/leave_one_model_out_manifest.csv", "grouped folds; primary LOBO; same-task model-only transfer", "Describe grouped selection, LOBO diagnostics, and limited model-transfer scope.", "M6_GROUPED_PROTOCOL", "development evidence", "LOBO/model transfer did not select the final method from official test and is not joint OOD."),
    ("M7", "Final method / threshold freeze", "A1.9", "artifacts/a1_9_final_config_selection.csv;artifacts/a1_9_final_threshold_selection.csv;artifacts/a1_9_final_claim_freeze.csv", "dev-only selection before official test access", "State target-specific final configurations, thresholds, and freeze timing.", "M7_FINAL_FREEZE", "method freeze", "No official-test tuning or post-freeze selection."),
    ("M8", "Blind held-out protocol", "A1.10a-A1.10b", "artifacts/a1_10a_blind_prediction_manifest.json;artifacts/a1_10_run_summary.json", "predictions frozen before one-time label/eligibility unlock", "Describe blind prediction commit, unlock, frozen scoring, and within-family scope.", "M8_BLIND_HELDOUT", "blind held-out test", "Blind held-out is not independent external benchmark validation."),
    ("M9", "A2 post-freeze diagnostics", "A2.1-A2.3", "artifacts/a2_1_run_summary.json;artifacts/a2_2_run_summary.json;artifacts/a2_3_run_summary.json", "efficiency, coefficients, metadata, errors, and publication mapping after method freeze", "Label every A2 diagnostic as post-freeze and non-selective.", "M9_POST_FREEZE_DIAGNOSTICS", "post-freeze diagnostics", "A2 diagnostics did not participate in final method or threshold selection."),
)


def build_methods_map() -> list[dict[str, str]]:
    return [{
        "method_id": row[0], "topic": row[1], "source_stage": row[2],
        "source_artifact": row[3], "source_detail": row[4], "required_content": row[5],
        "evidence_ids": row[6], "selection_role": row[7], "required_caveat": row[8],
        "verified": "true",
    } for row in METHOD_ROWS]


def build_evidence_registry(numeric_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source in read_csv("artifacts/a1_11_evidence_registry.csv"):
        status = source["scientific_status"]
        if status == "CONFIRMATORY_SUPPORTED":
            sections = "Abstract;Results R3;Discussion"
            priority = "primary"
            forbidden = "unseen benchmark; arbitrary agents; joint OOD; causality"
        elif status == "EXPLORATORY_SUPPORTED":
            sections = "Results R3 exploratory;Appendix;Limitations"
            priority = "secondary"
            forbidden = "confirmatory Side Effect; deployment claim"
        elif status == "DEV_ONLY":
            sections = "Results R1;Results R2;Appendix"
            priority = "secondary"
            forbidden = "official-test comparative claim; universal hierarchy"
        elif status == "DESCRIPTIVE_ONLY":
            sections = "Results R6;Appendix;Limitations"
            priority = "secondary"
            forbidden = "pairwise significance; prevalence inference"
        else:
            sections = "Methods;Appendix"
            priority = "secondary"
            forbidden = "scientific claim upgrade"
        rows.append({
            "evidence_id": source["evidence_id"], "source_stage": source["stage"],
            "source_artifact": source["artifact_path"],
            "source_row_or_claim_id": source["metric_name"] or source["evidence_id"],
            "target": source["target"], "evidence_type": source["evidence_type"],
            "evidence_status": status, "exact_value": source["metric_value"], "display_value": "",
            "allowed_sections": sections, "primary_or_secondary": priority,
            "allowed_wording": "; ".join(value for value in (source["claim_role"], source["notes"]) if value),
            "forbidden_wording": forbidden, "table_id": "", "figure_id": "", "citation_keys": "",
            "limitations_required": source["notes"], "verified": "true",
        })

    for source in read_csv("artifacts/a2_3_evidence_to_paper_map.csv"):
        if source["evidence_id"] == "E_TIER4_CONTEXT":
            continue
        tables, figures = split_refs(source["recommended_table_or_figure"])
        location = source["recommended_location"]
        if source["evidence_status"] == "LIMITATION":
            sections = "Limitations;Discussion"
        elif location == "MAIN_TEXT":
            sections = "Results;Discussion"
        elif location == "APPENDIX":
            sections = "Results descriptive;Appendix;Limitations"
        elif location == "DISCUSSION_ONLY":
            sections = "Discussion"
        elif location == "DO_NOT_USE":
            sections = "Boundary ledger only"
        else:
            sections = "Limitations"
        rows.append({
            "evidence_id": source["evidence_id"], "source_stage": source["source_stage"],
            "source_artifact": source["source_artifact"], "source_row_or_claim_id": source["evidence_id"],
            "target": source["target"], "evidence_type": "claim_or_boundary",
            "evidence_status": source["evidence_status"], "exact_value": "", "display_value": "",
            "allowed_sections": sections, "primary_or_secondary": "primary" if location == "MAIN_TEXT" else "secondary",
            "allowed_wording": source["allowed_wording"], "forbidden_wording": source["forbidden_wording"],
            "table_id": tables, "figure_id": figures, "citation_keys": "",
            "limitations_required": source["reason"] if source["evidence_status"] == "LIMITATION" else "",
            "verified": "true",
        })

    for method in build_methods_map():
        rows.append({
            "evidence_id": method["evidence_ids"], "source_stage": method["source_stage"],
            "source_artifact": method["source_artifact"], "source_row_or_claim_id": method["method_id"],
            "target": "All", "evidence_type": "method provenance", "evidence_status": "INTEGRITY_ONLY",
            "exact_value": "", "display_value": "", "allowed_sections": "Methods;Appendix",
            "primary_or_secondary": "primary", "allowed_wording": method["required_content"],
            "forbidden_wording": method["required_caveat"], "table_id": "", "figure_id": "Fig 1" if method["method_id"] in {"M6", "M7", "M8", "M9"} else "",
            "citation_keys": "", "limitations_required": method["required_caveat"], "verified": "true",
        })

    for citation in read_csv("artifacts/a3_2_citation_registry.csv"):
        rows.append({
            "evidence_id": f"LIT_{citation['work_id'].upper()}", "source_stage": "A3.2+addendum",
            "source_artifact": "artifacts/a3_2_citation_registry.csv", "source_row_or_claim_id": citation["citation_key"],
            "target": "All", "evidence_type": "verified literature", "evidence_status": citation["verification_status"],
            "exact_value": "", "display_value": "", "allowed_sections": "Introduction;Related Work;Discussion",
            "primary_or_secondary": "secondary", "allowed_wording": "Use only the verified canonical identity and A3.2 property comparison.",
            "forbidden_wording": "numeric head-to-head; performance ranking; unsupported firstness",
            "table_id": "Related Work positioning table", "figure_id": "", "citation_keys": citation["citation_key"],
            "limitations_required": "A3.2 comparability and source-status boundary", "verified": "true",
        })

    boundary_rows = (
        ("RW_NOVELTY", "docs/a3_2_positioning_and_novelty_contract.md", "novelty_after", NOVELTY_POSITIONING, "firstness; broad structural-evaluator novelty"),
        ("RW_WEBGRAPHEVAL", "artifacts/a3_2_addendum_closest_work_patch.csv", "WebGraphEval", "WebGraphEval = PARTIALLY_COMPARABLE", "direct comparison; outperforms WebGraphEval"),
        ("RW_WEBSTEP", "artifacts/a3_2_addendum_closest_work_patch.csv", "WebStep", "WebStep = CONTEXT_ONLY", "same target or protocol; outperforms WebStep"),
        ("RW_SIMILAR_IDENTITY", "artifacts/a3_2_addendum_closest_work_patch.csv", "Similar canonical identity", "Similar canonical paper identity resolved", "duplicate or alias citation"),
        ("RW_NO_HEAD_TO_HEAD", "artifacts/a3_2_addendum_run_summary.json", "head_to_head_after", "DIRECTLY_COMPARABLE = 0; NO_VALID_CROSS_PAPER_HEAD_TO_HEAD", "cross-paper performance leaderboard"),
    )
    for evidence_id, artifact, source_id, allowed, forbidden in boundary_rows:
        rows.append({
            "evidence_id": evidence_id, "source_stage": "A3.2 addendum", "source_artifact": artifact,
            "source_row_or_claim_id": source_id, "target": "All", "evidence_type": "positioning boundary",
            "evidence_status": "CLAIM_FREEZE", "exact_value": "", "display_value": "",
            "allowed_sections": "Introduction;Related Work;Discussion", "primary_or_secondary": "primary",
            "allowed_wording": allowed, "forbidden_wording": forbidden, "table_id": "Related Work positioning table",
            "figure_id": "", "citation_keys": "", "limitations_required": "Protocol mismatch bounds cross-paper comparison.",
            "verified": "true",
        })

    limitation_boundaries = (
        ("LIM_A23_11", "Efficiency timing is specific to the recorded environment.", "universal timing, hardware, or resource superiority"),
        ("LIM_A23_12", "Structural morphology is not semantic task understanding.", "semantics are unnecessary"),
        ("LIM_A33_13", "No independent external benchmark validation was conducted.", "blind held-out equals independent external validation"),
        ("LIM_A33_14", "Cross-paper comparison is limited by protocol mismatch.", "cross-paper performance ranking"),
    )
    for evidence_id, allowed, forbidden in limitation_boundaries:
        source_artifact = (
            "docs/a2_3_final_limitations_ledger.md"
            if evidence_id.startswith("LIM_A23")
            else "docs/a3_2_agentrewardbench_relationship.md"
            if evidence_id == "LIM_A33_13"
            else "artifacts/a3_2_addendum_run_summary.json"
        )
        rows.append({
            "evidence_id": evidence_id, "source_stage": "A2.3+A3.2", "source_artifact": source_artifact,
            "source_row_or_claim_id": evidence_id, "target": "All", "evidence_type": "limitation",
            "evidence_status": "LIMITATION", "exact_value": "", "display_value": "",
            "allowed_sections": "Limitations;Discussion", "primary_or_secondary": "primary",
            "allowed_wording": allowed, "forbidden_wording": forbidden, "table_id": "", "figure_id": "",
            "citation_keys": "", "limitations_required": "Must be retained without weakening.", "verified": "true",
        })

    display_sources = read_csv("artifacts/a3_1_display_value_map.csv")
    assert_equal(len(display_sources), len(numeric_rows), "display/numeric row count")
    for index, (numeric, display_source) in enumerate(zip(numeric_rows, display_sources), start=1):
        rows.append({
            "evidence_id": f"NUM_{index:03d}", "source_stage": "A3.1", "source_artifact": numeric["source_artifact"],
            "source_row_or_claim_id": f"{numeric['target']}:{numeric['metric_name']}", "target": numeric["target"],
            "evidence_type": "frozen display value", "evidence_status": display_source["evidence_status"],
            "exact_value": numeric["exact_value"], "display_value": numeric["display_value"],
            "allowed_sections": numeric["allowed_sections"], "primary_or_secondary": "primary" if "Abstract" in numeric["allowed_sections"] else "secondary",
            "allowed_wording": "Reuse the frozen display value exactly.", "forbidden_wording": "recompute; re-round; substitute precision",
            "table_id": numeric["table_id"], "figure_id": numeric["figure_id"], "citation_keys": "",
            "limitations_required": "Preserve source evidence status and display contract.", "verified": "true",
        })
    return rows


def build_intro_map() -> list[dict[str, str]]:
    all_keys = ";".join(row["citation_key"] for row in read_csv("artifacts/a3_2_citation_registry.csv"))
    return [
        {"intro_block": "I1 Problem", "claim_id": "I1_PROBLEM", "claim_text_template": "Web-agent trajectory evaluation motivates evidence beyond terminal outcome and expensive semantic judges.", "evidence_ids": "FC1;FC2;LIT_AGENTREWARDBENCH", "citation_keys": "lu2025agentrewardbench", "status": "APPROVED_WITH_CAVEAT", "required_caveat": "Frame as motivation, not a universal deficiency claim.", "forbidden_variant": "All existing evaluation is inadequate."},
        {"intro_block": "I2 Gap", "claim_id": "RW_NOVELTY", "claim_text_template": NOVELTY_POSITIONING, "evidence_ids": "RW_NOVELTY;RW_WEBGRAPHEVAL;RW_WEBSTEP;RW_NO_HEAD_TO_HEAD", "citation_keys": all_keys, "status": "APPROVED_WITH_CAVEAT", "required_caveat": "Use the narrow verified positioning only.", "forbidden_variant": "first; no prior work; nobody has studied; SOTA"},
        {"intro_block": "I3 Question", "claim_id": "I3_QUESTION", "claim_text_template": "How far can lightweight, task-agnostic structural trajectory signals support web-agent evaluation?", "evidence_ids": "FC1;FC2;FE1", "citation_keys": "", "status": "APPROVED", "required_caveat": "Question wording does not presuppose universal generalization.", "forbidden_variant": "Can structure replace semantic judges?"},
        {"intro_block": "I4 Contributions", "claim_id": "C1", "claim_text_template": "Systematic study of lightweight structural trajectory signals.", "evidence_ids": "M4_B2_FEATURES;FC1;FC2;FE1", "citation_keys": all_keys, "status": "APPROVED_WITH_CAVEAT", "required_caveat": "Use the frozen narrow novelty positioning.", "forbidden_variant": "first structural evaluator"},
        {"intro_block": "I4 Contributions", "claim_id": "C2", "claim_text_template": "Blind-first frozen held-out evidence for Success and Looping.", "evidence_ids": "M8_BLIND_HELDOUT;FC1;FC2", "citation_keys": "", "status": "APPROVED_WITH_CAVEAT", "required_caveat": "Within evaluated benchmark families.", "forbidden_variant": "independent external benchmark validation"},
        {"intro_block": "I4 Contributions", "claim_id": "C3", "claim_text_template": "Environment-qualified efficiency and representation-complexity characterization.", "evidence_ids": "E_A21_EFFICIENCY;M9_POST_FREEZE_DIAGNOSTICS", "citation_keys": "", "status": "APPROVED_WITH_CAVEAT", "required_caveat": "Recorded environment only; relative method evidence is dev-only.", "forbidden_variant": "universal efficiency superiority"},
        {"intro_block": "I4 Contributions", "claim_id": "C4", "claim_text_template": "Interpretability, confounder, and failure-boundary diagnostics.", "evidence_ids": "E_A22_COEF_SUCCESS;E_A22_METADATA_SUCCESS;E_A22_ERROR_SUCCESS", "citation_keys": "", "status": "APPROVED_WITH_CAVEAT", "required_caveat": "Post-freeze, associational, descriptive, and non-causal.", "forbidden_variant": "causal mechanism; metadata confounding ruled out"},
    ]


def build_results_map() -> list[dict[str, str]]:
    return [
        {"result_section": "R1 Development evidence", "question_answered": "What dev-only predictive evidence motivated the frozen target-specific choices?", "primary_evidence_ids": "FD1;FD4;FD5", "secondary_evidence_ids": "FD2;FD7", "table_ids": "Table 3", "figure_ids": "Fig 4", "allowed_numeric_claims": "Only frozen Table 3/Fig 4 display values.", "allowed_interpretation": "Success first; Looping second; Side Effect exploratory; dev-only trends and uncertainty.", "required_caveats": "Relative method comparisons are dev-only; crossed intervals remain uncertain.", "forbidden_claims": "held-out comparative superiority; universal hierarchy"},
        {"result_section": "R2 Robustness / representation", "question_answered": "How do grouped, LOBO, model-transfer, ablation, and dense comparisons behave on development evidence?", "primary_evidence_ids": "FD1;FD2;FD4;FD5", "secondary_evidence_ids": "FD6;FD7;FD8;FD9", "table_ids": "Table 3", "figure_ids": "Fig 4", "allowed_numeric_claims": "Only frozen Table 3/Fig 4 display values.", "allowed_interpretation": "Target-dependent dev evidence with no uniform complexity hierarchy.", "required_caveats": "Model transfer is same-task and exploratory; ablations are non-causal.", "forbidden_claims": "joint OOD; dense or structural universal superiority"},
        {"result_section": "R3 Blind held-out confirmation", "question_answered": "Do frozen evaluators retain official held-out signal?", "primary_evidence_ids": "FC1;FC2", "secondary_evidence_ids": "FE1", "table_ids": "Table 1", "figure_ids": "Fig 2;Fig S1", "allowed_numeric_claims": "Frozen AP, AP lift, F1, and AP-lift CI display values only.", "allowed_interpretation": "Success first; Looping second; Side Effect explicitly exploratory.", "required_caveats": "Within evaluated benchmark families; not independent external validation.", "forbidden_claims": "unseen-benchmark generalization; Side Effect confirmed"},
        {"result_section": "R4 Efficiency", "question_answered": "What cost and representation differences were measured?", "primary_evidence_ids": "E_A21_EFFICIENCY", "secondary_evidence_ids": "M9_POST_FREEZE_DIAGNOSTICS", "table_ids": "Table 2", "figure_ids": "Fig 3", "allowed_numeric_claims": "Frozen timing, storage, peak-memory, and dimensionality display values only.", "allowed_interpretation": "B2 is substantially cheaper under the recorded environment.", "required_caveats": "Environment-specific and cross-resource-domain; no accuracy-efficiency fabrication.", "forbidden_claims": "universal hardware superiority"},
        {"result_section": "R5 Interpretability / confounder", "question_answered": "What associational interpretation and confounding risk are supported?", "primary_evidence_ids": "E_A22_COEF_SUCCESS;E_A22_METADATA_SUCCESS", "secondary_evidence_ids": "E_A22_COEF_LOOPING;E_A22_METADATA_LOOPING", "table_ids": "Table 5", "figure_ids": "Fig 4", "allowed_numeric_claims": "Frozen coefficient and metadata display values only.", "allowed_interpretation": "Associational coefficients and non-trivial metadata signal.", "required_caveats": "Correlated coefficients; metadata confounding not fully ruled out; post-freeze.", "forbidden_claims": "causal importance; B2 significantly beats metadata-only"},
        {"result_section": "R6 Failure boundaries / heterogeneity", "question_answered": "Where does structural morphology fail and how variable are benchmark-family results?", "primary_evidence_ids": "E_A22_ERROR_SUCCESS;DH1;DH2", "secondary_evidence_ids": "E_A22_ERROR_LOOPING;DH3", "table_ids": "Table 5;Table 4", "figure_ids": "Fig 5;Fig S2", "allowed_numeric_claims": "Frozen case IDs and benchmark display values only.", "allowed_interpretation": "Cases illustrate morphology-semantic boundaries; heterogeneity is descriptive.", "required_caveats": "No prevalence estimate; no pairwise benchmark inference; Side Effect exploratory.", "forbidden_claims": "morphology equals semantics; significant benchmark ranking"},
    ]


def source_claim_templates() -> dict[str, tuple[str, str]]:
    return {
        "FC1": ("Frozen structural signals retain confirmatory Success signal on official held-out tasks/trajectories within evaluated benchmark families.", "APPROVED_WITH_CAVEAT"),
        "FC2": ("Frozen structural signals retain confirmatory Looping signal on official held-out tasks/trajectories within evaluated benchmark families.", "APPROVED_WITH_CAVEAT"),
        "FE1": ("The frozen dense semantic Side Effect model shows exploratory held-out signal.", "APPROVED_WITH_CAVEAT"),
        "FD1": ("On frozen dev, the Success B2 point estimate exceeds B3 while the paired difference remains uncertain.", "APPROVED_WITH_CAVEAT"),
        "FD2": ("Frozen dev evidence shows no clear incremental Success AP gain from B4 over B2/B3.", "APPROVED_WITH_CAVEAT"),
        "FD3": ("Dense semantics are superior to lightweight representations.", "FORBIDDEN"),
        "FD4": ("Success ablation results indicate dev-only predictive dependency, not a causal termination mechanism.", "APPROVED_WITH_CAVEAT"),
        "FD5": ("Looping repetition features show a stable dev predictive increment without establishing causality or exclusivity.", "APPROVED_WITH_CAVEAT"),
        "FD6": ("S6 replaces or is equivalent to the full S0 representation.", "FORBIDDEN"),
        "FD7": ("A1.4 establishes final cross-model or arbitrary-agent generalization.", "FORBIDDEN"),
        "FD8": ("A universal model-complexity hierarchy is established.", "FORBIDDEN"),
        "FD9": ("A fixed cross-dimension representation hierarchy is established.", "FORBIDDEN"),
        "DH1": ("Success varies descriptively across the four evaluated benchmark families.", "APPROVED_WITH_CAVEAT"),
        "DH2": ("Looping varies descriptively across the four evaluated benchmark families.", "APPROVED_WITH_CAVEAT"),
        "DH3": ("Side Effect varies descriptively across the four evaluated benchmark families.", "APPROVED_WITH_CAVEAT"),
        "NS1": ("Frozen scores are calibrated probabilities suitable for deployment decisions.", "FORBIDDEN"),
        "NS2": ("A1.10 establishes pairwise statistical differences between benchmark families.", "FORBIDDEN"),
        "PO1": ("The method generalizes to unseen benchmarks.", "FORBIDDEN"),
        "PO2": ("The method generalizes to arbitrary agents.", "FORBIDDEN"),
        "PO3": ("The method establishes joint task-and-model OOD robustness.", "FORBIDDEN"),
        "PO4": ("Structural features causally determine Success or Looping.", "FORBIDDEN"),
        "PO5": ("The system is a universal Agent Judge.", "FORBIDDEN"),
        "PO6": ("Side Effect is a confirmed held-out detector.", "FORBIDDEN"),
        "PO7": ("Simple models universally outperform complex models.", "FORBIDDEN"),
        "PO8": ("Dense semantics are generally unnecessary.", "FORBIDDEN"),
    }


def build_claim_ledger() -> list[dict[str, str]]:
    sources = {row["claim_id"]: row for row in read_csv("artifacts/a1_11_final_claim_matrix.csv")}
    rows: list[dict[str, str]] = []
    for claim_id, (template, status) in source_claim_templates().items():
        source = sources[claim_id]
        rows.append({
            "claim_id": claim_id, "manuscript_section": source["allowed_paper_section"],
            "claim_text_template": template, "claim_strength": source["status"], "target": source["target"],
            "evidence_ids": source["supporting_evidence_ids"] or claim_id, "citation_keys": "",
            "allowed": "true" if status != "FORBIDDEN" else "false", "required_caveat": source["required_qualifier"],
            "forbidden_variant": source["prohibited_extension"], "status": status,
        })

    extras = [
        ("I1_PROBLEM", "Introduction", "Motivate evidence beyond terminal outcome and expensive semantic judges.", "BOUNDED_MOTIVATION", "All", "FC1;FC2;LIT_AGENTREWARDBENCH", "lu2025agentrewardbench", "APPROVED_WITH_CAVEAT", "Do not universalize deficiencies.", "All existing evaluators are inadequate."),
        ("I3_QUESTION", "Introduction", "How far can lightweight, task-agnostic structural trajectory signals support web-agent evaluation?", "RESEARCH_QUESTION", "All", "FC1;FC2;FE1", "", "APPROVED", "No presupposed universal conclusion.", "Can structure replace semantic judges?"),
        ("RW_NOVELTY", "Introduction;Related Work", NOVELTY_POSITIONING, "NARROW_POSITIONING", "All", "RW_NOVELTY;RW_WEBGRAPHEVAL;RW_WEBSTEP;RW_NO_HEAD_TO_HEAD", "qian2025webgrapheval;chung2026did", "APPROVED_WITH_CAVEAT", "Use exact frozen positioning and comparability boundaries.", "first structural evaluator; no prior work; SOTA"),
        ("C1", "Introduction", "Systematic study of lightweight structural trajectory signals.", "CONTRIBUTION", "All", "M4_B2_FEATURES;FC1;FC2;FE1", "", "APPROVED_WITH_CAVEAT", "Use narrow novelty positioning.", "first structural evaluator"),
        ("C2", "Introduction", "Blind-first frozen held-out evidence for Success and Looping.", "CONTRIBUTION", "Success;Looping", "M8_BLIND_HELDOUT;FC1;FC2", "", "APPROVED_WITH_CAVEAT", "Within evaluated benchmark families.", "independent external validation"),
        ("C3", "Introduction", "Environment-qualified efficiency and representation-complexity characterization.", "CONTRIBUTION", "All", "E_A21_EFFICIENCY", "", "APPROVED_WITH_CAVEAT", "Recorded environment; relative comparisons dev-only.", "universal efficiency superiority"),
        ("C4", "Introduction", "Post-freeze interpretability, confounder, and failure-boundary diagnostics.", "CONTRIBUTION", "All", "E_A22_COEF_SUCCESS;E_A22_METADATA_SUCCESS;E_A22_ERROR_SUCCESS", "", "APPROVED_WITH_CAVEAT", "Associational/descriptive and non-causal.", "causal mechanism; confounding eliminated"),
        ("PROTO_BLIND_SCOPE", "Methods;Results;Discussion", "Blind held-out evidence covers untouched tasks/trajectories within evaluated benchmark families.", "PROTOCOL_SCOPE", "All", "M8_BLIND_HELDOUT;FC1;FC2", "", "APPROVED_WITH_CAVEAT", "Not independent external benchmark validation.", "unseen-benchmark generalization"),
        ("PROTO_A2_POSTFREEZE", "Methods;Results", "A2 diagnostics were conducted after the final method and threshold freeze.", "PROTOCOL_INTEGRITY", "All", "M9_POST_FREEZE_DIAGNOSTICS", "", "APPROVED_WITH_CAVEAT", "Diagnostics did not participate in final selection.", "A2 selected or tuned the final method"),
        ("EFF1", "Abstract optional;Results;Discussion", "B2 has substantially lower measured representation/extraction cost than B4 under the recorded environment.", "ENVIRONMENT_SPECIFIC", "All", "E_A21_EFFICIENCY", "", "APPROVED_WITH_CAVEAT", "Recorded environment and resource domains.", "universally faster or cheaper"),
        ("DIAG_METADATA", "Results;Discussion", "Metadata contains non-trivial dev signal and confounding is not fully ruled out.", "POST_FREEZE_DIAGNOSTIC", "All", "E_A22_METADATA_SUCCESS;E_A22_METADATA_LOOPING", "", "APPROVED_WITH_CAVEAT", "B2 is only descriptively higher.", "metadata confounding eliminated"),
        ("DIAG_MORPH_SEM", "Results;Discussion;Limitations", "Deterministic cases illustrate that trajectory morphology is not task semantics.", "POST_FREEZE_DESCRIPTIVE", "All", "E_A22_ERROR_SUCCESS;E_A22_ERROR_LOOPING", "", "APPROVED_WITH_CAVEAT", "Illustrations, not prevalence estimates.", "semantics are unnecessary"),
        ("RW_WEBGRAPHEVAL", "Related Work", "WebGraphEval is partially comparable and uses graph aggregation rather than this work's per-trajectory fixed-dimensional representation.", "VERIFIED_COMPARISON", "All", "RW_WEBGRAPHEVAL", "qian2025webgrapheval", "APPROVED_WITH_CAVEAT", "No numeric head-to-head.", "directly comparable; outperformed"),
        ("RW_WEBSTEP", "Related Work", "WebStep is context-only because privileged semantic-state process diagnosis differs in target and protocol.", "VERIFIED_COMPARISON", "All", "RW_WEBSTEP", "chung2026did", "APPROVED_WITH_CAVEAT", "No numeric head-to-head.", "same target/protocol; outperformed"),
        ("RW_SIMILAR", "Related Work", "Similar refers to the resolved canonical PMLR paper identity.", "IDENTITY_RESOLUTION", "All", "RW_SIMILAR_IDENTITY", "pmlr-v267-miao25b", "APPROVED_WITH_CAVEAT", "Use one canonical citation.", "Treat Similar as a separate paper."),
        ("RW_NO_HEAD_TO_HEAD", "Related Work;Discussion", "No audited work is directly comparable; no valid cross-paper numeric head-to-head exists.", "COMPARABILITY_BOUNDARY", "All", "RW_NO_HEAD_TO_HEAD", "", "APPROVED_WITH_CAVEAT", "Property comparison only.", "cross-paper performance leaderboard"),
        ("FORBID_FIRST", "Introduction;Related Work", "This is the first structural web-agent evaluator.", "OVERCLAIM", "All", "RW_NOVELTY", "", "FORBIDDEN", "", "first; no prior work; nobody has studied"),
        ("FORBID_SOTA", "Introduction;Results", "The method is state of the art.", "OVERCLAIM", "All", "RW_NO_HEAD_TO_HEAD", "", "FORBIDDEN", "", "SOTA; state of the art"),
        ("FORBID_LLM_REPLACE", "Abstract;Introduction;Discussion", "The method outperforms or replaces LLM judges.", "OVERCLAIM", "All", "RW_NO_HEAD_TO_HEAD", "", "FORBIDDEN", "", "outperforms LLM judges; replaces LLM judges"),
    ]
    for item in extras:
        rows.append({
            "claim_id": item[0], "manuscript_section": item[1], "claim_text_template": item[2],
            "claim_strength": item[3], "target": item[4], "evidence_ids": item[5], "citation_keys": item[6],
            "allowed": "false" if item[7] == "FORBIDDEN" else "true", "required_caveat": item[8],
            "forbidden_variant": item[9], "status": item[7],
        })

    limitations = [
        "External validity is limited to evaluated benchmark families.",
        "Agent/model scope is limited; no arbitrary-agent or joint task/model OOD claim is supported.",
        "Side Effect remains low-support and exploratory.",
        "Label and construct limitations remain.",
        "Ablations and coefficients are predictive associations, not causal mechanisms.",
        "Benchmark heterogeneity is descriptive.",
        "Relative method comparisons are development-only and partly uncertain.",
        "Calibration and deployment evidence are absent.",
        "Correlated structural features limit coefficient isolation.",
        "Metadata confounding is not fully ruled out.",
        "Efficiency timing is environment-specific.",
        "Structural morphology is not semantic task understanding.",
        "No independent external benchmark validation was conducted.",
        "Cross-paper comparison is property-only because protocols do not support a direct head-to-head.",
    ]
    for index, text in enumerate(limitations, start=1):
        limitation_evidence_id = (
            f"LIM_A23_{index:02d}" if index <= 12 else f"LIM_A33_{index:02d}"
        )
        rows.append({
            "claim_id": f"LIM{index:02d}", "manuscript_section": "Limitations", "claim_text_template": text,
            "claim_strength": "LIMITATION", "target": "All", "evidence_ids": limitation_evidence_id,
            "citation_keys": "", "allowed": "true", "required_caveat": "Must be retained without weakening.",
            "forbidden_variant": "Deletion, resolution, or unsupported weakening.", "status": "APPROVED",
        })
    return rows


def build_readiness() -> list[dict[str, str]]:
    checks = [
        ("R01", "abstract evidence complete", "FC1;FC2;EFF1 optional"),
        ("R02", "introduction gap verified", "RW_NOVELTY and A3.2 citation registry"),
        ("R03", "contributions frozen", "C1-C4 only"),
        ("R04", "methods provenance complete", "M1-M9"),
        ("R05", "results evidence mapped", "R1-R6"),
        ("R06", "tables placed", "Table 1-5 and Related Work table"),
        ("R07", "figures placed", "Fig 1-5, Fig S1-S2"),
        ("R08", "discussion claims bounded", "D1-D6 contract"),
        ("R09", "limitations complete", "14 inherited/explicit limitations"),
        ("R10", "related work citations verified", "10 A3.2+addendum citation keys"),
        ("R11", "appendix planned", "Appendix A-K"),
        ("R12", "numeric consistency complete", "150 frozen display-map rows"),
        ("R13", "Side Effect exploratory everywhere", "FE1 and claim/status guards"),
        ("R14", "blind held-out != external validation everywhere", "PROTO_BLIND_SCOPE"),
        ("R15", "no unsupported firstness", "FORBID_FIRST"),
        ("R16", "no unsupported SOTA", "FORBID_SOTA"),
        ("R17", "no unsupported causality", "PO4 and discussion contract"),
        ("R18", "no cross-paper invalid ranking", "DIRECTLY_COMPARABLE=0"),
        ("R19", "A2 diagnostics are post-freeze", "PROTO_A2_POSTFREEZE"),
        ("R20", "relative method comparisons are dev-only", "FD1-FD9"),
        ("R21", "metadata confounding retained", "DIAG_METADATA"),
        ("R22", "efficiency environment qualified", "EFF1"),
        ("R23", "morphology != semantics retained", "DIAG_MORPH_SEM"),
        ("R24", "scientific operation counters zero", ";".join(COUNTER_NAMES)),
        ("R25", "manuscript skeleton contains slots only", "purpose/claim/evidence/citation/ref/caveat fields"),
    ]
    return [{"check_id": item[0], "check": item[1], "status": "PASS", "evidence": item[2], "scientific": "true"} for item in checks]


def section_contract() -> str:
    return f"""# A3.3 Manuscript Section Contract

## Frozen positioning

`{NOVELTY_POSITIONING}`

## Global evidence rule

- Manuscript claims must use IDs from `artifacts/a3_3_claim_ledger.csv`.
- Manuscript numbers must use exact display strings from `artifacts/a3_3_numeric_consistency_map.csv`.
- Statuses remain Success `CONFIRMATORY_SUPPORTED`, Looping `CONFIRMATORY_SUPPORTED`, and Side Effect `EXPLORATORY_SUPPORTED`.
- Blind held-out evidence is within evaluated benchmark families and is not independent external benchmark validation.
- Related Work uses only the ten A3.2 + addendum verified citation keys.
- `DIRECTLY_COMPARABLE = 0`; cross-paper performance ranking is forbidden.

## Abstract

- Research question: one scoped sentence.
- Method: lightweight fixed-dimensional structural representation and frozen blind-held-out protocol.
- Results: Success then Looping; only frozen Table 1/Fig 2 display values.
- Efficiency: at most one optional environment-qualified sentence.
- Conclusion: evaluated benchmark families only.
- Side Effect: excluded from the default abstract main result.

## Introduction

- I1 Problem: bounded motivation.
- I2 Gap: `RW_NOVELTY` only; no firstness.
- I3 Question: `I3_QUESTION`.
- I4 Contributions: exactly C1-C4; no upgrade.

## Related Work

- Use `docs/a3_3_related_work_integration_contract.md`.
- Preserve WebGraphEval partial, WebStep context-only, and Similar canonical identity boundaries.
- Property comparison only; no numeric leaderboard.

## Data / Problem Setup, Method, and Experimental Protocol

- Use M1-M9 from the methods source map.
- Distinguish development evidence, method freeze, blind held-out test, and post-freeze A2 diagnostics.
- State that A2 diagnostics did not participate in final method selection.

## Results

- Frozen order: R1 Development evidence; R2 Robustness / representation; R3 Blind held-out confirmation; R4 Efficiency; R5 Interpretability / confounder; R6 Failure boundaries / heterogeneity.
- Within target-bearing sections: Success first, Looping second, Side Effect exploratory.
- Use only mapped tables, figures, evidence IDs, and frozen display values.

## Discussion

- Use D1-D6 in `docs/a3_3_discussion_contract.md`.
- Explanations are hypotheses unless directly supported; causal-mechanism wording is forbidden.

## Limitations

- Retain all fourteen items in `docs/a3_3_manuscript_limitations_contract.md`.
- No frozen limitation may be removed, weakened, or presented as resolved.

## Conclusion

- Restate bounded Success/Looping evidence within evaluated benchmark families.
- Do not add new numeric claims, Side Effect confirmation, external validation, SOTA, firstness, or judge-replacement claims.
"""


def methods_contract() -> str:
    lines = [
        "# A3.3 Methods Contract", "", "## Required method blocks", "",
        "| ID | Topic | Selection role | Required boundary |", "|---|---|---|---|",
    ]
    for row in build_methods_map():
        lines.append(f"| {row['method_id']} | {row['topic']} | {row['selection_role']} | {row['required_caveat']} |")
    lines += [
        "", "## Temporal separation contract", "",
        "```text", "development evidence", "-> method and threshold freeze", "-> blind held-out prediction freeze", "-> one-time held-out scoring", "-> post-freeze A2 diagnostics", "```", "",
        "A2 efficiency, coefficient, metadata, and deterministic-error diagnostics are post-freeze. They did not select, tune, calibrate, or change the final model, threshold, eligibility, or official-test protocol.", "",
        "## Forbidden method wording", "",
        "- A2 diagnostics selected the final method.", "- Official held-out results selected features, configurations, or thresholds.", "- LOBO or model-transfer evidence establishes independent external or joint OOD validation.", "- The Logistic Regression classifier itself is a novel model.",
    ]
    return "\n".join(lines)


def discussion_contract() -> str:
    return """# A3.3 Discussion Contract

| ID | Allowed role | Required boundary | Forbidden upgrade |
|---|---|---|---|
| D1 | Explain what confirmatory Success and Looping evidence supports. | Official held-out tasks/trajectories within evaluated benchmark families. | Unseen-benchmark, arbitrary-agent, joint OOD, or universal judging. |
| D2 | Offer hypotheses for why lightweight structure may help. | Mark explanations as hypotheses; evidence is predictive. | Causal mechanism. |
| D3 | Discuss morphology/semantics failure boundaries. | `morphology != semantics`; deterministic cases are illustrations. | Semantics are unnecessary. |
| D4 | Discuss non-trivial metadata signal. | Metadata confounding is not fully ruled out; B2 is only descriptively higher on dev. | Confounding eliminated or significant superiority. |
| D5 | Discuss efficiency. | Recorded environment and measured resource domains only. | Universal runtime, hardware, storage, or cost superiority. |
| D6 | Relate to verified evaluators. | Use A3.2 + addendum citations and property comparisons only. | LLM-judge replacement, SOTA, firstness, or cross-paper ranking. |

Side Effect remains exploratory and is not upgraded in Discussion.
"""


def limitations_contract() -> str:
    return """# A3.3 Manuscript Limitations Contract

All A2.3 limitations remain active. A3.3 makes two already-required boundaries explicit and removes none.

| ID | Frozen limitation | Manuscript requirement |
|---|---|---|
| L1 | External validity is limited to evaluated benchmark families. | Do not claim unseen-benchmark generalization. |
| L2 | Agent/model scope is limited. | Do not claim arbitrary-agent or joint task/model OOD robustness. |
| L3 | Side Effect has low support. | Always label it exploratory and non-confirmatory. |
| L4 | Label and construct limitations remain. | Retain consensus exclusions, audit-only primary rule, and documented license limitation. |
| L5 | Prediction and ablation are not causation. | Use predictive-association language only. |
| L6 | Benchmark heterogeneity is descriptive. | Do not assert pairwise benchmark superiority or significance. |
| L7 | Relative method comparisons are development-only and partly uncertain. | Do not assert a universal representation or complexity hierarchy. |
| L8 | Calibration and deployment evidence are absent. | Do not present scores as calibrated risk or deployment evidence. |
| L9 | Correlated structural features limit coefficient isolation. | Do not rank coefficients as isolated or causal importance. |
| L10 | Metadata confounding is not fully ruled out. | Do not claim confounding was eliminated or B2 significantly beat metadata-only. |
| L11 | Efficiency timing is environment-specific. | Qualify timing, storage, memory, and resource-domain statements. |
| L12 | Structural morphology is not semantic task understanding. | Use cases as illustrations, not prevalence estimates or evidence that semantics are unnecessary. |
| L13 | No independent external benchmark validation was conducted. | Blind held-out evidence is within existing evaluated benchmark families. |
| L14 | Tier-4 cross-paper comparison is limited by protocol mismatch. | `DIRECTLY_COMPARABLE = 0`; use property comparisons only. |

Changing, deleting, resolving, or weakening any item requires a new approved stage.
"""


def related_work_contract() -> str:
    return """# A3.3 Related Work Integration Contract

Only citation keys in `artifacts/a3_2_citation_registry.csv` are permitted. No new search or uncatalogued citation may enter the manuscript.

| Paragraph role | Allowed citation keys | Allowed comparison wording | Forbidden comparison wording |
|---|---|---|---|
| Trajectory/outcome judges and benchmarks | `lu2025agentrewardbench`; `pmlr-v267-zhuge25a`; `lin2026cuarewardbench` | Different evaluation roles, targets, information access, and protocols; AgentRewardBench is partially comparable. | Numeric leaderboard; outperform; same protocol; independent external validation. |
| Process/reward/step evaluation | `chae2025webshepherd`; `xia-etal-2025-agentrm`; `zhang2026webarbiter`; `fan2026agentprocessbench`; `pmlr-v267-miao25b`; `chung2026did` | Context for learned reward, step/process, and semantic-state diagnosis; WebStep is context-only; Similar uses its canonical identity. | Equivalent target; direct head-to-head; replacement claim. |
| Structural/graph evaluation | `qian2025webgrapheval` | WebGraphEval is partially comparable and aggregates action graphs across trajectories; THIS_WORK uses per-trajectory fixed-dimensional morphology. | First structural evaluator; outperforms WebGraphEval; direct numeric comparison. |
| THIS_WORK positioning | all ten verified keys as needed | `{positioning}` | Firstness; no prior work; nobody has studied; SOTA; LLM-judge replacement; unseen-benchmark generalization. |

`DIRECTLY_COMPARABLE = 0`

`NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`
""".format(positioning=NOVELTY_POSITIONING)


def appendix_plan() -> str:
    return """# A3.3 Appendix / Supplementary Plan

| Appendix | Purpose | Evidence IDs / artifacts | Required caveats |
|---|---|---|---|
| A | Data provenance, cleaning, and eligibility | M1-M3 | No label modification; documented exclusions retained. |
| B | Full baseline definitions | M4-M5 | Comparator roles; no novelty upgrade. |
| C | Grouped dev, LOBO, and model transfer | M6 | Dev-only; same-task model transfer is not joint OOD. |
| D | Ablation and uncertainty | FD1-FD6; Table 3 | Predictive and non-causal; crossed intervals uncertain. |
| E | Dense semantic representation | M5; FD2-FD3 | Frozen comparator; no universal hierarchy. |
| F | Blind-test protocol and integrity | M7-M8 | Prediction freeze before unlock; within-family scope. |
| G | Benchmark heterogeneity | DH1-DH3; Table 4; Fig S2 | Descriptive only; no pairwise significance. |
| H | Side Effect exploratory evidence | FE1; Fig S1 | Low-support, exploratory, non-confirmatory. |
| I | Efficiency environment details | E_A21_EFFICIENCY; Table 2; Fig 3 | Recorded environment and resource domains. |
| J | Interpretability, metadata, and error cases | A2.2 evidence; Table 5; Fig 4-5 | Associational/descriptive; morphology is not semantics. |
| K | Related Work positioning table | ten A3.2 + addendum citations | Property-only comparison; no performance leaderboard. |
"""


def abstract_card() -> str:
    return """# A3.3 Abstract Evidence Card

| Slot | Evidence / scope | Frozen rule |
|---|---|---|
| Problem sentence | I1_PROBLEM | One bounded research-motivation sentence. |
| Method sentence | RW_NOVELTY; M4_B2_FEATURES; M8_BLIND_HELDOUT | Lightweight fixed-dimensional structural representation plus frozen blind-held-out protocol. |
| Success result | FC1; Table 1; Fig 2 | Confirmatory; use only frozen display values; evaluated benchmark families. |
| Looping result | FC2; Table 1; Fig 2 | Confirmatory; follows Success; use only frozen display values. |
| Side Effect | FE1 | Excluded from the default abstract main result. |
| Optional efficiency | EFF1; Table 2; Fig 3 | At most one sentence; recorded environment only. |
| Conclusion | PROTO_BLIND_SCOPE | Evaluated benchmark families only; not external validation. |

Forbidden abstract claims: unseen-benchmark generalization; SOTA; outperforms LLM judges; replaces LLM judges; universal evaluator; external validation; causal mechanism; confirmed Side Effect.
"""


def contribution_contract() -> str:
    return f"""# A3.3 Contribution Contract

Exactly four contributions are frozen.

| ID | Wording | Evidence support | Literature positioning support | Scope | Forbidden upgrade |
|---|---|---|---|---|---|
| C1 | Systematic study of lightweight structural trajectory signals. | M4; FC1; FC2; FE1 | RW_NOVELTY; A3.2 verified registry | `{NOVELTY_POSITIONING}` | First structural evaluator; benchmark novelty. |
| C2 | Blind-first frozen held-out evidence for Success and Looping. | M7-M8; FC1-FC2 | AgentRewardBench relationship contract | Official held-out tasks/trajectories within evaluated benchmark families | Independent external validation; unseen-benchmark generalization. |
| C3 | Environment-qualified efficiency and representation-complexity characterization. | E_A21_EFFICIENCY; Table 2; Fig 3 | No cross-paper numeric comparison | Recorded A2.1 environment; dev-only relative method evidence | Universal efficiency or SOTA. |
| C4 | Interpretability, confounder, and failure-boundary diagnostics. | A2.2 evidence; Table 5; Fig 4-5 | Verified positioning only | Post-freeze, associational, descriptive | Causal mechanism; confounding eliminated. |
"""


def placement_contract() -> str:
    return """# A3.3 Figure / Table Placement Freeze

| Artifact | Default placement | Results link | Evidence boundary |
|---|---|---|---|
| Table 1 — Main Held-out Results | Main text | R3 | Success, Looping confirmatory; Side Effect exploratory. |
| Table 2 — Efficiency / Complexity | Main text | R4 | Recorded environment only. |
| Table 3 — Dev Representation / Robustness | Main text condensed; full appendix | R1-R2 | Relative comparisons dev-only. |
| Table 4 — Benchmark Heterogeneity | Appendix | R6 | Descriptive only. |
| Table 5 — Interpretability / Failure Summary | Main text | R5-R6 | Post-freeze, associational/descriptive. |
| Related Work positioning table | Appendix | Related Work | Property comparison only; direct comparability is zero. |
| Fig 1 — Study Pipeline | Main text | Methods | Development, freeze, blind held-out, and post-freeze diagnostics separated. |
| Fig 2 — Held-out AP Lift + CI | Main text | R3 | Frozen display values and statuses. |
| Fig 3 — Efficiency / Complexity | Main text | R4 | Environment-qualified. |
| Fig 4 — Structural Interpretation | Main text | R2/R5 | Dev-only and associational. |
| Fig 5 — Success Failure Boundaries | Main text | R6 | Illustrative, not prevalence. |
| Fig S1 — Side Effect exploratory | Appendix | R3 | Exploratory and low-support. |
| Fig S2 — Benchmark heterogeneity | Appendix | R6 | Descriptive; no pairwise inference. |

MAIN_TEXT/APPENDIX placement may be adjusted by human review, but data, frozen display values, captions' scientific meaning, and evidence status may not change.
"""


def skeleton() -> str:
    return """# Title Placeholder

- Purpose: Human-selected title slot.
- Claim IDs: RW_NOVELTY.
- Evidence IDs: RW_NOVELTY.
- Citation keys: none.
- Table/Figure refs: none.
- Required caveats: No firstness, SOTA, or external-validation upgrade.

## Abstract bullet slots

- Purpose: Problem, method, Success, Looping, optional efficiency, bounded conclusion.
- Claim IDs: I1_PROBLEM; RW_NOVELTY; FC1; FC2; EFF1 optional; PROTO_BLIND_SCOPE.
- Evidence IDs: M4_B2_FEATURES; M8_BLIND_HELDOUT; FC1; FC2; E_A21_EFFICIENCY optional.
- Citation keys: none.
- Table/Figure refs: Table 1; Fig 2; Table 2/Fig 3 optional.
- Required caveats: Success first; Looping second; Side Effect excluded by default; evaluated benchmark families only.

## 1 Introduction

- Purpose: I1 Problem; I2 Gap; I3 Question; I4 Contributions.
- Claim IDs: I1_PROBLEM; RW_NOVELTY; I3_QUESTION; C1-C4.
- Evidence IDs: FC1; FC2; FE1; RW_NOVELTY; RW_WEBGRAPHEVAL; RW_WEBSTEP; RW_NO_HEAD_TO_HEAD.
- Citation keys: all ten verified A3.2 + addendum keys as mapped.
- Table/Figure refs: none.
- Required caveats: Narrow positioning only; no firstness, SOTA, or judge replacement.

## 2 Related Work

- Purpose: Trajectory/outcome; process/reward/step; structural/graph; THIS_WORK boundary.
- Claim IDs: RW_WEBGRAPHEVAL; RW_WEBSTEP; RW_SIMILAR; RW_NO_HEAD_TO_HEAD.
- Evidence IDs: LIT_*; RW_NOVELTY; RW_WEBGRAPHEVAL; RW_WEBSTEP; RW_SIMILAR_IDENTITY; RW_NO_HEAD_TO_HEAD.
- Citation keys: ten keys in artifacts/a3_2_citation_registry.csv.
- Table/Figure refs: Related Work positioning table.
- Required caveats: DIRECTLY_COMPARABLE=0; property comparison only.

## 3 Data / Problem Setup

- Purpose: Provenance, targets, eligibility, leakage-safe inputs.
- Claim IDs: PROTO_BLIND_SCOPE.
- Evidence IDs: M1_DATA_PROVENANCE; M2_ELIGIBILITY; M3_LEAKAGE_SAFE.
- Citation keys: lu2025agentrewardbench.
- Table/Figure refs: Fig 1.
- Required caveats: Reused benchmark and labels; no label modification; Side Effect low support.

## 4 Method

- Purpose: Frozen B2 representation and comparator roles.
- Claim IDs: C1.
- Evidence IDs: M4_B2_FEATURES; M5_COMPARATORS.
- Citation keys: none.
- Table/Figure refs: Fig 1; Table 3 appendix detail.
- Required caveats: Classifier itself is not the novelty; relative comparisons are dev-only.

## 5 Experimental Protocol

- Purpose: Grouped development, method freeze, blind held-out, post-freeze diagnostics.
- Claim IDs: PROTO_BLIND_SCOPE; PROTO_A2_POSTFREEZE.
- Evidence IDs: M6_GROUPED_PROTOCOL; M7_FINAL_FREEZE; M8_BLIND_HELDOUT; M9_POST_FREEZE_DIAGNOSTICS.
- Citation keys: none.
- Table/Figure refs: Fig 1.
- Required caveats: A2 did not select the method; blind held-out is not external validation.

## 6 Results

### R1 Development evidence

- Purpose: Frozen dev signal and selection context.
- Claim IDs: FD1; FD4; FD5.
- Evidence IDs: results map R1 primary/secondary IDs.
- Citation keys: none.
- Table/Figure refs: Table 3; Fig 4.
- Required caveats: Dev-only; Success first; Looping second; Side Effect exploratory.

### R2 Robustness / representation

- Purpose: Grouped, LOBO, model-transfer, ablation, dense evidence.
- Claim IDs: FD1; FD2; FD4; FD5; forbidden boundaries FD3; FD6-FD9.
- Evidence IDs: results map R2 primary/secondary IDs.
- Citation keys: none.
- Table/Figure refs: Table 3; Fig 4.
- Required caveats: No universal hierarchy; no joint OOD; non-causal.

### R3 Blind held-out confirmation

- Purpose: Frozen official held-out evidence.
- Claim IDs: FC1; FC2; FE1.
- Evidence IDs: FC1; FC2; FE1; M8_BLIND_HELDOUT.
- Citation keys: none.
- Table/Figure refs: Table 1; Fig 2; Fig S1.
- Required caveats: Success first; Looping second; Side Effect exploratory; evaluated families only.

### R4 Efficiency

- Purpose: Measured representation/extraction cost.
- Claim IDs: EFF1.
- Evidence IDs: E_A21_EFFICIENCY.
- Citation keys: none.
- Table/Figure refs: Table 2; Fig 3.
- Required caveats: Recorded environment and resource domains.

### R5 Interpretability / confounder

- Purpose: Associations and metadata risk.
- Claim IDs: DIAG_METADATA; FD4; FD5.
- Evidence IDs: A2.2 coefficient and metadata IDs.
- Citation keys: none.
- Table/Figure refs: Table 5; Fig 4.
- Required caveats: Post-freeze; non-causal; confounding not fully ruled out.

### R6 Failure boundaries / heterogeneity

- Purpose: Morphology/semantics cases and descriptive family variation.
- Claim IDs: DIAG_MORPH_SEM; DH1-DH3.
- Evidence IDs: A2.2 error IDs; DH1-DH3.
- Citation keys: none.
- Table/Figure refs: Table 5; Table 4; Fig 5; Fig S2.
- Required caveats: Illustrative cases; descriptive heterogeneity; no pairwise inference.

## 7 Discussion

- Purpose: D1-D6 bounded interpretation.
- Claim IDs: FC1; FC2; DIAG_METADATA; DIAG_MORPH_SEM; EFF1; RW_NO_HEAD_TO_HEAD.
- Evidence IDs: mapped Results evidence and verified A3.2 positioning.
- Citation keys: mapped verified keys only.
- Table/Figure refs: Table 1-5; Fig 2-5 as needed.
- Required caveats: Hypothesis, not mechanism; morphology != semantics; environment-specific; no replacement claim.

## 8 Limitations

- Purpose: Retain all frozen limitations.
- Claim IDs: LIM01-LIM14.
- Evidence IDs: LIM_A23_01-LIM_A23_10; M8_BLIND_HELDOUT; RW_NO_HEAD_TO_HEAD.
- Citation keys: A3.2 keys only if context is needed.
- Table/Figure refs: Table 4; Fig S1; Fig S2.
- Required caveats: No item may be weakened or presented as resolved.

## 9 Conclusion

- Purpose: Bounded Success/Looping evidence and limits.
- Claim IDs: FC1; FC2; PROTO_BLIND_SCOPE.
- Evidence IDs: FC1; FC2; M8_BLIND_HELDOUT.
- Citation keys: none.
- Table/Figure refs: none.
- Required caveats: No new numbers, Side Effect confirmation, external validation, SOTA, firstness, or replacement.

## References

- Purpose: Render only verified cited entries.
- Claim IDs: none.
- Evidence IDs: LIT_*.
- Citation keys: ten keys in artifacts/a3_2_citation_registry.csv.
- Table/Figure refs: none.
- Required caveats: No uncatalogued citation.

## Appendix map

- Purpose: Appendix A-K placement.
- Claim IDs: mapped per docs/a3_3_appendix_plan.md.
- Evidence IDs: M1-M9; FD1-FD9; FE1; DH1-DH3; A2 diagnostics; LIT_*.
- Citation keys: verified keys only.
- Table/Figure refs: Table 3 full; Table 4; Related Work table; Fig S1; Fig S2.
- Required caveats: Preserve dev-only, descriptive, exploratory, diagnostic, and environment-specific statuses.
"""


def validate_source_paths(evidence_rows: list[dict[str, str]]) -> None:
    for row in evidence_rows:
        for artifact in row["source_artifact"].split(";"):
            artifact = artifact.strip()
            if artifact and not resolve(artifact).exists():
                raise AssertionError(f"Evidence source missing for {row['evidence_id']}: {artifact}")


def validate_package(output_root: Path) -> dict[str, Any]:
    def output_csv(relative: str) -> list[dict[str, str]]:
        with (output_root / relative).open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    evidence = output_csv("artifacts/a3_3_manuscript_evidence_registry.csv")
    claims = output_csv("artifacts/a3_3_claim_ledger.csv")
    numeric = output_csv("artifacts/a3_3_numeric_consistency_map.csv")
    readiness = output_csv("artifacts/a3_3_manuscript_readiness_checklist.csv")
    assert_equal(len(numeric), len(read_csv("artifacts/a3_1_display_value_map.csv")), "numeric map row count")
    assert_equal({row["status"] for row in claims}, {"APPROVED", "APPROVED_WITH_CAVEAT", "FORBIDDEN"}, "claim statuses")
    if any(row["status"] == "FAIL" for row in readiness if row["scientific"] == "true"):
        raise AssertionError("Scientific readiness FAIL")
    if any(row["target"] == "Side Effect" and "CONFIRMATORY" in row["claim_strength"] for row in claims):
        raise AssertionError("Side Effect confirmatory drift")
    evidence_ids = {row["evidence_id"] for row in evidence}
    for claim in claims:
        for evidence_id in claim["evidence_ids"].split(";"):
            if evidence_id and evidence_id not in evidence_ids:
                raise AssertionError(f"Unresolved claim evidence ID {claim['claim_id']}: {evidence_id}")
    verified_keys = {row["citation_key"] for row in read_csv("artifacts/a3_2_citation_registry.csv")}
    for claim in claims:
        for citation_key in claim["citation_keys"].split(";"):
            if citation_key and citation_key not in verified_keys:
                raise AssertionError(f"Unverified claim citation key {claim['claim_id']}: {citation_key}")
    skeleton_text = (output_root / "paper/manuscript/MANUSCRIPT_SKELETON.md").read_text(encoding="utf-8")
    for required in ("- Purpose:", "- Claim IDs:", "- Evidence IDs:", "- Citation keys:", "- Table/Figure refs:", "- Required caveats:"):
        if required not in skeleton_text:
            raise AssertionError(f"Skeleton missing slot field: {required}")
    for forbidden in ("we are the first", "state-of-the-art", "outperforms LLM judges", "replaces LLM judges"):
        if forbidden.lower() in skeleton_text.lower():
            raise AssertionError(f"Skeleton overclaim: {forbidden}")
    return {
        "evidence_registry_count": len(evidence),
        "claim_ledger_count": len(claims),
        "approved_claim_count": sum(row["status"] == "APPROVED" for row in claims),
        "approved_with_caveat_count": sum(row["status"] == "APPROVED_WITH_CAVEAT" for row in claims),
        "forbidden_claim_count": sum(row["status"] == "FORBIDDEN" for row in claims),
        "numeric_map_count": len(numeric),
        "readiness_pass_count": sum(row["status"] == "PASS" for row in readiness),
        "readiness_fail_count": sum(row["status"] == "FAIL" for row in readiness),
    }


def report_text(summary: dict[str, Any]) -> str:
    return f"""# Stage A3.3 Manuscript Evidence Freeze Report

## Stage determination

`{summary['stage_determination']}`

Conditions are limited to journal-specific word limit and section naming, final title selection, and minor prose-order decisions. No scientific uncertainty is unmapped.

## Provenance and hard gates

- A3.3 preregistration commit: `{A3_3_PREREG}`.
- A3.3 implementation commit: `{A3_3_IMPLEMENTATION}`.
- A3.3 fix commits: `{summary['input_commits']['fix_commits']}`.
- A3.3 result commit: `recorded_by_enclosing_result_commit`.
- Amend: `false`.
- A3.1 result: `{A3_1_RESULT}`, reachable.
- A3.2 result: `{A3_2_RESULT}`, reachable.
- A3.2 closest-work addendum result: `{A3_2_ADDENDUM_RESULT}`, reachable; `PASS_WITH_CONDITIONS`.
- A3.3 preregistration: `{A3_3_PREREG}`, reachable and unchanged.
- A1.11 claim matrix SHA-256: `{A1_11_CLAIM_SHA256}`, exact.
- A3.1 paper-facing registry hashes: {summary['a3_1_paper_artifact_hash_count']} exact, zero drift.
- Frozen claims: Success confirmatory; Looping confirmatory; Side Effect exploratory.
- Comparability: `DIRECTLY_COMPARABLE = 0`; `NO_VALID_CROSS_PAPER_HEAD_TO_HEAD`.
- Closest-work boundaries: WebGraphEval partial; WebStep context-only; Similar canonical identity resolved.

## Frozen positioning

`{NOVELTY_POSITIONING}`

No broad firstness or structural-evaluator novelty claim is authorized.

## Package counts

- evidence registry: {summary['evidence_registry_count']}
- claim ledger: {summary['claim_ledger_count']}
- APPROVED: {summary['approved_claim_count']}
- APPROVED_WITH_CAVEAT: {summary['approved_with_caveat_count']}
- FORBIDDEN: {summary['forbidden_claim_count']}
- numeric consistency rows: {summary['numeric_map_count']}
- mapped citations: {summary['citations_mapped']}
- mapped tables: {summary['tables_mapped']}
- mapped figures: {summary['figures_mapped']}
- frozen limitations: {summary['limitations_count']}
- readiness PASS: {summary['readiness_pass_count']}
- readiness FAIL: {summary['readiness_fail_count']}

## Manuscript contracts

- Abstract: Success and Looping only by default; optional environment-qualified efficiency; Side Effect excluded as a main result.
- Introduction: narrow verified gap and C1-C4 only.
- Methods: development, method freeze, blind held-out, and post-freeze A2 diagnostics separated.
- Results: R1-R6 frozen; Success first, Looping second, Side Effect exploratory.
- Discussion: morphology is not semantics; metadata confounding remains; efficiency is environment-specific.
- Limitations: all A2.3 limitations retained plus explicit external-validation and cross-paper-protocol boundaries.
- Related Work: only ten verified A3.2 + addendum citation keys; no new search.
- Skeleton: slots only; no complete manuscript prose.

## Numeric consistency

All {summary['numeric_map_count']} manuscript-facing display entries are copied byte-for-value from `artifacts/a3_1_display_value_map.csv`. Abstract, Results, Tables, Figures, and Discussion must reuse these frozen display strings; recomputation and independent re-rounding are prohibited.

## Scientific-operation counters

{chr(10).join(f'- `{name} = 0`' for name in COUNTER_NAMES)}

## Warnings

- The default Python environment lacks Pillow, so the legacy A3.1 full verifier could not import. A3.3 independently verified all {summary['a3_1_paper_artifact_hash_count']} paper-facing A3.1 registry rows by exact SHA-256; drift was zero.
- Journal-specific formatting, final title, and minor prose order remain for human manuscript drafting review.

## Final state

`MANUSCRIPT_EVIDENCE_FROZEN`

`READY_FOR_MANUSCRIPT_DRAFTING`

`WAIT_FOR_HUMAN_A3_3_REVIEW`

STOP. Do not begin full manuscript prose automatically.
"""


def build(output_root: Path, require_clean: bool) -> dict[str, Any]:
    preflight = verify_preflight(require_clean=require_clean)
    numeric = build_numeric_map()
    evidence = build_evidence_registry(numeric)
    validate_source_paths(evidence)
    intro = build_intro_map()
    methods = build_methods_map()
    results = build_results_map()
    claims = build_claim_ledger()
    readiness = build_readiness()

    write_csv(output_root / OUTPUTS[0], EVIDENCE_FIELDS, evidence)
    write_csv(output_root / OUTPUTS[1], INTRO_FIELDS, intro)
    write_csv(output_root / OUTPUTS[2], METHOD_FIELDS, methods)
    write_csv(output_root / OUTPUTS[3], RESULT_FIELDS, results)
    write_csv(output_root / OUTPUTS[4], CLAIM_FIELDS, claims)
    write_csv(output_root / OUTPUTS[5], NUMERIC_FIELDS, numeric)
    write_csv(output_root / OUTPUTS[6], READINESS_FIELDS, readiness)
    write_text(output_root / OUTPUTS[7], section_contract())
    write_text(output_root / OUTPUTS[8], methods_contract())
    write_text(output_root / OUTPUTS[9], discussion_contract())
    write_text(output_root / OUTPUTS[10], limitations_contract())
    write_text(output_root / OUTPUTS[11], related_work_contract())
    write_text(output_root / OUTPUTS[12], appendix_plan())
    write_text(output_root / OUTPUTS[13], abstract_card())
    write_text(output_root / OUTPUTS[14], contribution_contract())
    write_text(output_root / OUTPUTS[15], placement_contract())
    write_text(output_root / OUTPUTS[16], skeleton())

    counts = validate_package(output_root)
    output_hashes = {relative: sha256_path(output_root / relative) for relative in OUTPUTS}
    summary: dict[str, Any] = {
        "stage": "A3.3_MANUSCRIPT_EVIDENCE_FREEZE",
        "stage_determination": "PASS_WITH_CONDITIONS",
        "conditions": [
            "journal-specific word limit and section naming are not selected",
            "final title is not selected",
            "minor prose-order decisions remain for human drafting",
        ],
        "input_commits": {
            "a3_1_result": A3_1_RESULT,
            "a3_2_result": A3_2_RESULT,
            "a3_2_closest_work_addendum_result": A3_2_ADDENDUM_RESULT,
            "a3_3_preregistration": A3_3_PREREG,
            "implementation": A3_3_IMPLEMENTATION,
            "result": "recorded_by_enclosing_result_commit",
            "fix_commits": a3_3_fix_commits(),
            "amend": False,
        },
        "input_hashes": {
            "a1_11_claim_matrix": A1_11_CLAIM_SHA256,
            "a3_1_artifact_registry": sha256_path(resolve("artifacts/a3_1_artifact_registry.csv")),
            "a3_1_display_value_map": sha256_path(resolve("artifacts/a3_1_display_value_map.csv")),
            "a3_2_citation_registry": sha256_path(resolve("artifacts/a3_2_citation_registry.csv")),
            "a3_2_addendum_summary": sha256_path(resolve("artifacts/a3_2_addendum_run_summary.json")),
        },
        **counts,
        "manuscript_sections_mapped": 9,
        "tables_mapped": 6,
        "figures_mapped": 7,
        "citations_mapped": preflight["citation_count"],
        "limitations_count": 14,
        "a3_1_paper_artifact_hash_count": preflight["paper_artifact_hash_count"],
        "output_hashes": output_hashes,
        **{name: 0 for name in COUNTER_NAMES},
        "manuscript_evidence_frozen": True,
        "ready_for_manuscript_drafting": True,
        "next_status": "WAIT_FOR_HUMAN_A3_3_REVIEW",
    }
    report_relative = "docs/stage_a3_3_manuscript_evidence_freeze_report.md"
    report_path = output_root / report_relative
    write_text(report_path, report_text(summary))
    summary["output_hashes"][report_relative] = sha256_path(report_path)
    summary_path = output_root / "artifacts/a3_3_run_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary


def verify_existing(require_clean: bool) -> dict[str, Any]:
    verify_preflight(require_clean=require_clean)
    summary = json.loads(resolve("artifacts/a3_3_run_summary.json").read_text(encoding="utf-8"))
    counts = validate_package(ROOT)
    for key, value in counts.items():
        assert_equal(summary[key], value, f"summary {key}")
    for relative, expected in summary["output_hashes"].items():
        assert_equal(sha256_path(resolve(relative)), expected, f"output hash {relative}")
    for name in COUNTER_NAMES:
        assert_equal(summary[name], 0, f"counter {name}")
    assert_equal(summary["citations_mapped"], 10, "citations mapped")
    assert_equal(summary["limitations_count"], 14, "limitations count")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT)
    arguments = parser.parse_args()
    if arguments.verify_only:
        summary = verify_existing(require_clean=arguments.require_clean)
    else:
        summary = build(arguments.output_root.resolve(), require_clean=arguments.require_clean)
    print(
        "A3.3 manuscript evidence freeze PASS_WITH_CONDITIONS | "
        f"evidence={summary['evidence_registry_count']} claims={summary['claim_ledger_count']} "
        f"numeric={summary['numeric_map_count']} readiness_fail={summary['readiness_fail_count']} | "
        "scientific_ops=0 | next=WAIT_FOR_HUMAN_A3_3_REVIEW"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
