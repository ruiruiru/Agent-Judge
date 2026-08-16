#!/usr/bin/env python3
"""Consolidate frozen A0-A1.10 evidence for Stage A1.11.

This program is deliberately evidence-only. It reads frozen reports, summaries,
and result tables; verifies hashes and cross-artifact equality; and writes
paper-facing registries, tables, and ledgers. It never reads test labels or
prediction rows for metric calculation and contains no training, inference,
embedding, resampling, threshold-selection, or metric-library code.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
A1_11A_COMMIT = "c0d82fb1b89eddc8a8f0765183e51808b9268616"
A1_10B_RESULT_COMMIT = "53d81eb17e1be52e55489f5fbdf1f72018c5a349"
TASKBOOK_SHA256 = "ee7899a0d2070e9507262ade5a9ebfad1d2982a824d530f857bdf9430adcab5e"
BLIND_SHA256 = "a3a232484716ee455a604f03ffd40e6f734a1925ffdfb93e4a3d04118de27c3d"
SCORED_SHA256 = "22883f32ad22ecd2de6e7a3056a0f165d7aa4c03ab4ec847a535dbff7defb704"
A1_8_CLAIM_SHA256 = "264678a325f1680c8cfdad3631e6f5209a29a91e6ab8dd5b9683adb857810590"
GITHUB_REVISION = "f838338886d723d40b586309465a38277803d9e6"
HF_REVISION = "b6d17e646009d6cb63d5dd7be78807b680693f61"
RESULT_COMMIT_SENTINEL = "recorded_by_enclosing_result_commit"

REGISTRY_FIELDS = [
    "evidence_id",
    "stage",
    "evidence_type",
    "target",
    "artifact_path",
    "artifact_sha256",
    "commit",
    "metric_name",
    "metric_value",
    "uncertainty",
    "sample_n",
    "task_group_n",
    "benchmark_scope",
    "model_scope",
    "claim_role",
    "scientific_status",
    "notes",
]

CLAIM_FIELDS = [
    "claim_id",
    "claim_text",
    "status",
    "target",
    "scope",
    "supporting_evidence_ids",
    "contradicting_or_limiting_evidence",
    "allowed_paper_section",
    "required_qualifier",
    "prohibited_extension",
]

MAIN_TABLE_FIELDS = [
    "Target",
    "Role",
    "Eligible",
    "Positive",
    "Negative",
    "Prevalence",
    "Final Method",
    "Threshold",
    "AP",
    "AP Lift",
    "F1",
    "AP-lift 95% CI Lower",
    "AP-lift 95% CI Upper",
    "Final Grade",
]

BENCHMARK_TABLE_FIELDS = ["Target", "Benchmark", "AP", "F1", "Role", "Interpretation"]

DEV_TABLE_FIELDS = [
    "Evidence Area",
    "Stage",
    "Target",
    "Method or Comparison",
    "Metric",
    "Point Estimate",
    "95% CI Lower",
    "95% CI Upper",
    "Stage Determination",
    "Support Level",
    "Claim Boundary",
    "Source Artifact",
    "Source Commit",
]


class IntegrityError(RuntimeError):
    """Raised when a frozen input or cross-artifact invariant fails."""


def resolve(relative: str) -> Path:
    """Resolve a repository-relative path without permitting path escape."""
    path = (ROOT / relative).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise IntegrityError(f"path escapes repository: {relative}")
    return path


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_hash_contract(path_text: str) -> str:
    """Hash one or more semicolon-delimited frozen artifact paths."""
    paths = [item for item in path_text.split(";") if item]
    if not paths:
        raise IntegrityError("empty artifact path contract")
    hashes = [(item, sha256_path(resolve(item))) for item in paths]
    if len(hashes) == 1:
        return hashes[0][1]
    return ";".join(f"{item}={digest}" for item, digest in hashes)


def read_json(relative: str) -> Any:
    return json.loads(resolve(relative).read_text(encoding="utf-8"))


def read_csv(relative: str) -> list[dict[str, str]]:
    with resolve(relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(relative: str, value: Any) -> None:
    path = resolve(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def write_text(relative: str, value: str) -> None:
    path = resolve(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_csv(relative: str, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
    path = resolve(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def git_output(arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, found {actual!r}")


def assert_close(actual: Any, expected: Any, label: str, tolerance: float = 1e-15) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=tolerance):
        raise IntegrityError(f"{label}: expected {expected!r}, found {actual!r}")


def one(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    matches = [row for row in rows if all(row.get(key) == value for key, value in criteria.items())]
    if len(matches) != 1:
        raise IntegrityError(f"expected one row for {criteria}, found {len(matches)}")
    return matches[0]


STAGES: list[dict[str, str]] = [
    {
        "stage": "A0.1",
        "determination": "PASS_WITH_DOCUMENTED_LIMITATIONS",
        "taskbook": "docs/tasks/STAGE_A0_1_DATA_CONTRACT.md",
        "report": "docs/data_contract.md",
        "artifact": "artifacts/metadata_audit.json",
        "preregistration_commit": "49f7d7c7d6c83f23ff8d6a5a68c671a0d3687177",
        "result_commit": "49f7d7c7d6c83f23ff8d6a5a68c671a0d3687177",
        "fix_commits": "",
        "sample_n": "1408 annotation rows; 1302 unique trajectories; 351 tasks",
        "conclusion": "Fixed-source data and label contract established.",
        "warnings": "No standard license identifier; duplicate annotations and WorkArena namespaces documented.",
    },
    {
        "stage": "A0.2",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A0_2_ANALYSIS_INDEX.md",
        "report": "docs/analysis_unit_policy.md",
        "artifact": "artifacts/analysis_index_summary.json",
        "preregistration_commit": "70f11b75a3ec21efd40df632c39e96af80f5f724",
        "result_commit": "70f11b75a3ec21efd40df632c39e96af80f5f724",
        "fix_commits": "60296babe21a7c91c5ca52a3da2780f3ee859b9f",
        "sample_n": "1302 unique trajectories; 300 sealed test tasks",
        "conclusion": "Trajectory key, consensus policy, and benchmark group fields frozen.",
        "warnings": "Official primary label retained audit-only; WorkArena L1/L2 sensitivity required.",
    },
    {
        "stage": "A0.2-Fix",
        "determination": "PASS",
        "taskbook": "docs/tasks/STAGE_A0_2_FIX_LABEL_ELIGIBILITY.md",
        "report": "docs/analysis_unit_policy.md",
        "artifact": "artifacts/analysis_index_summary.json",
        "preregistration_commit": "60296babe21a7c91c5ca52a3da2780f3ee859b9f",
        "result_commit": "60296babe21a7c91c5ca52a3da2780f3ee859b9f",
        "fix_commits": "",
        "sample_n": "Success 1289; Side Effect 1297; Looping 1291 eligible trajectories",
        "conclusion": "Consensus-only main eligibility enforced.",
        "warnings": "Disagreement and Unsure labels remain unavailable for main analysis.",
    },
    {
        "stage": "A0.3",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A0_3_MINIMAL_TRAJECTORY_PROBE.md",
        "report": "docs/trajectory_schema_probe.md",
        "artifact": "artifacts/trajectory_probe_summary.json",
        "preregistration_commit": "c8fa3cde43e92de8069ab8dd6a6f41f975297651",
        "result_commit": "c8fa3cde43e92de8069ab8dd6a6f41f975297651",
        "fix_commits": "",
        "sample_n": "16 dev trajectories",
        "conclusion": "Shared text/structured adapter feasible after leakage exclusions.",
        "warnings": "Probe-only scope; screenshots referenced but not required for minimal text path.",
    },
    {
        "stage": "A0.4",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A0_4_INPUT_CONTRACT.md",
        "report": "docs/input_contract.md",
        "artifact": "artifacts/input_contract_summary.json",
        "preregistration_commit": "e302dfc2b159f295e6e3a17243fbb6c490bd5d15",
        "result_commit": "e302dfc2b159f295e6e3a17243fbb6c490bd5d15",
        "fix_commits": "",
        "sample_n": "16 probe trajectories; 196 projected dev trajectories",
        "conclusion": "Leak-safe input whitelist and serialization views frozen.",
        "warnings": "Reasoning view sensitivity-only; identity and direct leakage fields excluded.",
    },
    {
        "stage": "A1.0",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_0_BUILD_DEV_CORPUS.md",
        "report": "docs/dev_corpus_build_report.md",
        "artifact": "artifacts/dev_corpus_summary.json",
        "preregistration_commit": "695750f6011e307324a4b483117bcd5010653260",
        "result_commit": "695750f6011e307324a4b483117bcd5010653260",
        "fix_commits": "",
        "sample_n": "196 dev trajectories; 3812 steps",
        "conclusion": "Full dev corpus built under the frozen leak-safe contract.",
        "warnings": "Baseline readiness remained subject to human review.",
    },
    {
        "stage": "A1.1",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_1_FREEZE_EVALUATION_PROTOCOL.md",
        "report": "docs/pre_baseline_audit_report.md",
        "artifact": "artifacts/pre_baseline_summary.json",
        "preregistration_commit": "1044cb783dc0d7883b9065393b3e7147dafad34b",
        "result_commit": "1044cb783dc0d7883b9065393b3e7147dafad34b",
        "fix_commits": "49bba3279f356c779a0bfe93e8d31c5319009102",
        "sample_n": "196 dev trajectories; five frozen grouped folds per target",
        "conclusion": "Grouped CV, LOBO, inner selection, and NA policies frozen.",
        "warnings": "Side Effect single-class holdouts must remain NA where applicable.",
    },
    {
        "stage": "A1.2",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_2_RUN_MINIMAL_BASELINES.md",
        "report": "docs/stage_a1_2_minimal_baseline_report.md",
        "artifact": "artifacts/a1_2_run_summary.json",
        "preregistration_commit": "b4fef6f63d55ccd4ed2cdf4feb2dcab1cd5b6d20",
        "result_commit": "179ce02640a8e6e15411348b57fd8d7725047364",
        "fix_commits": "",
        "sample_n": "Success 192; Side Effect 195; Looping 196 dev trajectories",
        "conclusion": "Minimal grouped baselines established dev signal patterns.",
        "warnings": "All findings are development-stage only.",
    },
    {
        "stage": "A1.3",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_3_RUN_PRIMARY_LOBO_BASELINES.md",
        "report": "docs/stage_a1_3_primary_lobo_report.md",
        "artifact": "artifacts/a1_3_lobo_run_summary.json",
        "preregistration_commit": "6b98e03537360d8e60e5ccf3ca4c5ea7b51a652d",
        "result_commit": "346bb4b3d4a90fc51c1e099618c3b7592fa76b99",
        "fix_commits": "6027d5e5af29a1b0143bb04024084a6c4209529e",
        "sample_n": "583 selected external predictions across three targets",
        "conclusion": "Primary four-family LOBO established structural Success/Looping signal.",
        "warnings": "Side Effect support sparse; single-class domains retained as NA.",
    },
    {
        "stage": "A1.4",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_4_RUN_LEAVE_ONE_MODEL_OUT_BASELINES.md",
        "report": "docs/stage_a1_4_leave_one_model_out_report.md",
        "artifact": "artifacts/a1_4_lomo_run_summary.json",
        "preregistration_commit": "84bf9da03c12c4bbe28f57e42b31de71e8cb1041",
        "result_commit": "91e6b195dc63bae8c82728a126945abd0d5d2b68",
        "fix_commits": "21012dd38d86b631408bd64a65af3dde8cb9b86c",
        "sample_n": "2332 external predictions; four held-out Agent models",
        "conclusion": "Exploratory model-only transfer observed when tasks are represented in training.",
        "warnings": "Not joint task/model OOD; one Agent model has partial benchmark coverage.",
    },
    {
        "stage": "A1.5",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_5_RUN_STRUCTURAL_MECHANISM_ABLATIONS.md",
        "report": "docs/stage_a1_5_structural_mechanism_ablation_report.md",
        "artifact": "artifacts/a1_5_run_summary.json",
        "preregistration_commit": "fa9ef0771ea44a720ed8b900199a75ef3c863379",
        "result_commit": "e4fd9aba83cc6ed3b01b1f624c666b6cc7fce3ca",
        "fix_commits": "",
        "sample_n": "4081 external predictions across S0-S6",
        "conclusion": "Frozen structural dependency patterns recorded descriptively.",
        "warnings": "Ablations are predictive dependencies, not causal mechanisms.",
    },
    {
        "stage": "A1.6",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_6_RUN_GROUP_AWARE_BOOTSTRAP.md",
        "report": "docs/stage_a1_6_group_aware_bootstrap_report.md",
        "artifact": "artifacts/a1_6_run_summary.json",
        "preregistration_commit": "d7b851c48581a6c7c6220ab0dfc851b92a32162e",
        "result_commit": "040d081d3359f75f1303f4c24d7f8be79b5da75d",
        "fix_commits": "",
        "sample_n": "170000 primary draw-metric rows from frozen predictions",
        "conclusion": "Success/Looping positive LOBO signals stable; several paired differences uncertain.",
        "warnings": "Side Effect remains support-diagnostic with invalid sparse-domain draws.",
    },
    {
        "stage": "A1.7",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_7_RUN_FROZEN_DENSE_SEMANTIC_BASELINE.md",
        "report": "docs/stage_a1_7_frozen_dense_semantic_baseline_report.md",
        "artifact": "artifacts/a1_7_run_summary.json",
        "preregistration_commit": "e776c16710fd18c1462808a044f911e40061c5c3",
        "result_commit": "e24066fa27c027c60e2ac35b8305ea3d4a585493",
        "fix_commits": "676ab5efe4f05a2cd5552421510058e5d7553859;362a45917e403be7aacb54359aac2537473508fb",
        "sample_n": "196 shared embeddings; 583 external predictions",
        "conclusion": "Dense semantic Success signal exists without clear incremental AP gain over B2/B3.",
        "warnings": "Side Effect has 12 positives; all relative representation claims remain dev-only.",
    },
    {
        "stage": "A1.8",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_8_EVIDENCE_AUDIT_AND_PAPER_CLAIM_MATRIX.md",
        "report": "docs/stage_a1_8_evidence_audit_report.md",
        "artifact": "artifacts/a1_8_run_summary.json",
        "preregistration_commit": "d2f0b84c6247c95cc599b28784c5a2db10ad947f",
        "result_commit": "ddc3f9b6ef89ada12b7393fc31c5b57dbb7118f0",
        "fix_commits": "a7406bcc2e4fe885c02a0024243abfa6fee8fb61",
        "sample_n": "55 evidence rows; 14 claim rows; 277 report/artifact values checked",
        "conclusion": "Dev evidence and claim boundaries frozen before final-method selection.",
        "warnings": "Side Effect descriptive/exploratory; A1.4 model-only transfer only.",
    },
    {
        "stage": "A1.9",
        "determination": "PASS_WITH_CONDITIONS",
        "taskbook": "docs/tasks/STAGE_A1_9_FINAL_METHOD_FREEZE_AND_TEST_PREREGISTRATION.md",
        "report": "docs/stage_a1_9_final_method_freeze_report.md",
        "artifact": "artifacts/a1_9_run_summary.json",
        "preregistration_commit": "4944df46be45d8ad52d57a051e04b59c4a1a82ee",
        "result_commit": "8f96a6f032ee9b4dd0272164d60230303612043b",
        "fix_commits": "",
        "sample_n": "583 selected OOF rows; three frozen final models",
        "conclusion": "Success B2, Looping B2, and exploratory Side Effect B4 frozen before test.",
        "warnings": "Dev-only comparisons cannot be upgraded by official test outcomes.",
    },
    {
        "stage": "A1.10a",
        "determination": "PASS",
        "taskbook": "docs/tasks/STAGE_A1_10_BLIND_FIRST_OFFICIAL_TEST_EVALUATION.md",
        "report": "docs/stage_a1_10a_blind_test_inference_report.md",
        "artifact": "artifacts/a1_10a_run_summary.json",
        "preregistration_commit": "d32f9e215f27425ce907493344e4c65c835e91f6",
        "result_commit": "cead3cbaa362da4a9918dab32e41b58fffb987d9",
        "fix_commits": "100966969bf36c968051dea7fbbb675c1814b7cd",
        "sample_n": "1106 test trajectories; 3318 blind trajectory-target predictions",
        "conclusion": "Blind predictions committed before any label, eligibility, or metric access.",
        "warnings": "Startup dependency failure was fixed before model load and all embedding work restarted.",
    },
    {
        "stage": "A1.10b",
        "determination": "PASS",
        "taskbook": "docs/tasks/STAGE_A1_10_BLIND_FIRST_OFFICIAL_TEST_EVALUATION.md",
        "report": "docs/stage_a1_10_official_test_evaluation_report.md",
        "artifact": "artifacts/a1_10_run_summary.json",
        "preregistration_commit": "042866147e7b4a0c930eeb120d6e642cb34773a7",
        "result_commit": A1_10B_RESULT_COMMIT,
        "fix_commits": "3f0bc4da460652a74ae4767ff6d482fd4116ec9f;85cb71a49c9c25c9284562afad751f975d787608",
        "sample_n": "3318 joined rows; 30000 frozen bootstrap draw rows",
        "conclusion": "Success and Looping confirmed within evaluated families; Side Effect exploratory.",
        "warnings": "Per-benchmark results descriptive only; no unseen-benchmark or joint OOD claim.",
    },
]


def verify_commits_and_stage_inputs() -> dict[str, Any]:
    git_output(["merge-base", "--is-ancestor", A1_11A_COMMIT, "HEAD"])
    assert_equal(
        git_output(["rev-parse", f"{A1_11A_COMMIT}^"]),
        A1_10B_RESULT_COMMIT,
        "A1.11a parent",
    )
    assert_equal(
        sha256_path(resolve("docs/tasks/STAGE_A1_11_FINAL_EVIDENCE_CONSOLIDATION.md")),
        TASKBOOK_SHA256,
        "A1.11 taskbook SHA-256",
    )

    commits: set[str] = {A1_11A_COMMIT, A1_10B_RESULT_COMMIT}
    for stage in STAGES:
        commits.add(stage["preregistration_commit"])
        commits.add(stage["result_commit"])
        commits.update(item for item in stage["fix_commits"].split(";") if item)
        for key in ("taskbook", "report", "artifact"):
            path = resolve(stage[key])
            if not path.is_file():
                raise IntegrityError(f"missing {stage['stage']} {key}: {stage[key]}")
    for commit in sorted(commits):
        git_output(["cat-file", "-e", f"{commit}^{{commit}}"])
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, A1_11A_COMMIT], cwd=ROOT
        )
        if result.returncode != 0:
            raise IntegrityError(f"commit is not in A1.11 ancestry: {commit}")

    metadata = read_json("artifacts/metadata_audit.json")
    source_manifest = read_json("artifacts/source_manifest.json")
    for label, value in (
        ("metadata GitHub revision", metadata["source_revision"]["github_commit"]),
        ("metadata HF revision", metadata["source_revision"]["huggingface_revision"]),
        ("source-manifest GitHub revision", source_manifest["github_commit"]),
        ("source-manifest HF revision", source_manifest["huggingface_revision"]),
    ):
        assert_equal(value, GITHUB_REVISION if "GitHub" in label else HF_REVISION, label)

    expected_decisions = {stage["stage"]: stage["determination"] for stage in STAGES}
    early_summaries = {
        "A0.1": read_json("artifacts/metadata_audit.json").get("status"),
        "A0.2-Fix": read_json("artifacts/analysis_index_summary.json").get("stage_decision"),
        "A0.3": read_json("artifacts/trajectory_probe_summary.json").get("stage_decision"),
        "A0.4": read_json("artifacts/input_contract_summary.json").get("stage_decision"),
        "A1.0": read_json("artifacts/dev_corpus_summary.json").get("stage_decision"),
        "A1.1": read_json("artifacts/pre_baseline_summary.json").get("stage_decision"),
    }
    for stage, decision in early_summaries.items():
        assert_equal(decision, expected_decisions[stage], f"{stage} determination")

    a18_integrity = read_json("artifacts/a1_8_prerun_integrity.json")
    assert_equal(a18_integrity["status"], "PASS", "A1.8 prerun integrity")
    assert_equal(
        a18_integrity["consistency_guards"]["report_numeric_consistency"]["total"],
        277,
        "A1.2-A1.7 report consistency count",
    )
    checked_source_hashes = 0
    for path_text, expected_hash in a18_integrity["source_hashes"].items():
        if not (
            path_text.startswith("artifacts/a1_")
            or path_text.startswith("docs/stage_a1_")
            or path_text in {"artifacts/lobo_primary_manifest.csv", "artifacts/leave_one_model_out_manifest.csv"}
        ):
            continue
        if "a1_8" in path_text:
            continue
        assert_equal(sha256_path(resolve(path_text)), expected_hash, f"frozen source hash {path_text}")
        checked_source_hashes += 1

    assert_equal(
        sha256_path(resolve("artifacts/a1_8_claim_matrix.csv")),
        A1_8_CLAIM_SHA256,
        "A1.8 claim matrix hash",
    )
    a19_integrity = read_json("artifacts/a1_9_prerun_integrity.json")
    for path_text, expected_hash in a19_integrity["source_hashes"].items():
        if path_text.startswith("artifacts/") and resolve(path_text).is_file():
            assert_equal(sha256_path(resolve(path_text)), expected_hash, f"A1.9 frozen input {path_text}")

    a10a_integrity = read_json("artifacts/a1_10a_prerun_integrity.json")
    for path_text, expected_hash in a10a_integrity["verified_hashes"].items():
        assert_equal(sha256_path(resolve(path_text)), expected_hash, f"A1.10a frozen input {path_text}")

    assert_equal(
        sha256_path(resolve("artifacts/a1_10a_blind_predictions.csv")),
        BLIND_SHA256,
        "blind prediction SHA-256",
    )
    assert_equal(
        sha256_path(resolve("artifacts/a1_10_test_scored_predictions.csv")),
        SCORED_SHA256,
        "scored prediction SHA-256",
    )
    return {
        "verified_commit_count": len(commits),
        "verified_a1_2_to_a1_7_source_hashes": checked_source_hashes,
        "stage_units": [stage["stage"] for stage in STAGES],
    }


def verify_a1_9_a1_10() -> dict[str, Any]:
    a19 = read_json("artifacts/a1_9_run_summary.json")
    a10 = read_json("artifacts/a1_10_run_summary.json")
    target_rows = read_csv("artifacts/a1_10_target_metrics.csv")
    benchmark_rows = read_csv("artifacts/a1_10_benchmark_metrics.csv")
    bootstrap_rows = read_csv("artifacts/a1_10_bootstrap_summary.csv")
    grade_rows = read_csv("artifacts/a1_10_confirmatory_grade.csv")
    claim_rows = read_csv("artifacts/a1_10_final_claim_status.csv")
    report = resolve("docs/stage_a1_10_official_test_evaluation_report.md").read_text(
        encoding="utf-8"
    )

    assert_equal(a19["stage_determination"], "PASS_WITH_CONDITIONS", "A1.9 determination")
    assert_equal(a10["stage_determination"], "PASS", "A1.10 determination")
    assert_equal(a10["blind_predictions_changed"], False, "blind predictions changed")
    assert_equal(a10["dev_only_claims_upgraded"], 0, "dev-only claim upgrades")
    assert_equal(a10["next_stage_entered"], False, "automatic next-stage entry")
    assert_equal(a10["join_integrity"]["status"], "PASS", "A1.10 join integrity")
    assert_equal(a10["join_integrity"]["joined_rows"], 3318, "A1.10 joined rows")

    expected_output_hashes = {
        "target_metrics": "artifacts/a1_10_target_metrics.csv",
        "benchmark_metrics": "artifacts/a1_10_benchmark_metrics.csv",
        "bootstrap_summary": "artifacts/a1_10_bootstrap_summary.csv",
        "confirmatory_grade": "artifacts/a1_10_confirmatory_grade.csv",
        "final_claim_status": "artifacts/a1_10_final_claim_status.csv",
        "scored_predictions": "artifacts/a1_10_test_scored_predictions.csv",
    }
    for key, path_text in expected_output_hashes.items():
        assert_equal(sha256_path(resolve(path_text)), a10["output_hashes"][key], f"A1.10 {key} hash")

    models = {row["target"]: row for row in a19["models"]}
    if set(models) != {"success", "looping", "side_effect"}:
        raise IntegrityError("A1.9 final model set changed")
    target_map = {row["target"]: row for row in target_rows}
    if set(target_map) != set(models):
        raise IntegrityError("A1.10 target set differs from A1.9")

    expected_claims = {
        "success": ("FC1", "CONFIRMED_HELDOUT_SIGNAL", "confirmatory_primary"),
        "looping": ("FC2", "CONFIRMED_HELDOUT_SIGNAL", "confirmatory_primary"),
        "side_effect": ("FE1", "EXPLORATORY_TEST_RESULT", "exploratory_only"),
    }
    report_checks = 0
    for target, row in target_map.items():
        frozen = models[target]
        summary_metric = a10["target_metrics"][target]
        bootstrap = one(bootstrap_rows, target=target)
        grade = one(grade_rows, target=target)
        claim = one(claim_rows, target=target)
        claim_id, expected_grade, expected_role = expected_claims[target]

        assert_equal(row["method_id"], frozen["method_id"], f"{target} method")
        assert_close(row["threshold"], frozen["selected_threshold"], f"{target} threshold")
        assert_equal(row["role"], frozen["role"], f"{target} role")
        assert_equal(row["role"], expected_role, f"{target} frozen role")
        assert_equal(claim["claim_id"], claim_id, f"{target} claim id")
        assert_equal(grade["final_grade"], expected_grade, f"{target} grade")
        assert_equal(claim["status"], expected_grade, f"{target} claim status")
        assert_equal(a10["grades"][target], expected_grade, f"{target} summary grade")
        assert_equal(
            a10["preunlock"]["model_hashes"][target],
            frozen["artifact_sha256"],
            f"{target} model hash",
        )

        scalar_pairs = (
            ("eligible_n", "eligible_n"),
            ("positive_n", "positive_n"),
            ("negative_n", "negative_n"),
            ("prevalence", "prevalence"),
            ("pooled_average_precision", "pooled_average_precision"),
            ("pooled_ap_lift", "pooled_ap_lift"),
            ("positive_f1", "positive_f1"),
        )
        for csv_key, json_key in scalar_pairs:
            if csv_key.endswith("_n"):
                assert_equal(int(row[csv_key]), int(summary_metric[json_key]), f"{target} {csv_key}")
            else:
                assert_close(row[csv_key], summary_metric[json_key], f"{target} {csv_key}")
        assert_close(bootstrap["point_estimate"], row["pooled_ap_lift"], f"{target} bootstrap point")
        assert_close(grade["pooled_ap_lift"], row["pooled_ap_lift"], f"{target} grade point")
        assert_close(grade["ci_lower"], bootstrap["ci_lower"], f"{target} CI lower")
        assert_close(grade["ci_upper"], bootstrap["ci_upper"], f"{target} CI upper")

        rounded_values = [
            f"{float(row['prevalence']):.6f}",
            f"{float(row['pooled_average_precision']):.6f}",
            f"{float(row['pooled_ap_lift']):.6f}",
            f"{float(row['positive_f1']):.6f}",
            f"{float(bootstrap['ci_lower']):.6f}",
            f"{float(bootstrap['ci_upper']):.6f}",
            expected_grade,
        ]
        report_line = next(
            (line for line in report.splitlines() if line.startswith(f"| {target} | {expected_role} |")),
            "",
        )
        if not report_line or not all(value in report_line for value in rounded_values):
            raise IntegrityError(f"A1.10 report row conflicts for {target}")
        report_checks += len(rounded_values)

    if len(benchmark_rows) != 12:
        raise IntegrityError(f"expected 12 A1.10 benchmark rows, found {len(benchmark_rows)}")
    expected_benchmarks = {"assistantbench", "visualwebarena", "webarena", "workarena"}
    for target in target_map:
        found = {row["benchmark_group_primary"] for row in benchmark_rows if row["target"] == target}
        assert_equal(found, expected_benchmarks, f"{target} benchmark coverage")

    prohibited = a10["post_unlock_prohibited_operations"]
    nonzero = {key: value for key, value in prohibited.items() if value != 0}
    if nonzero:
        raise IntegrityError(f"A1.10 prohibited-operation counters nonzero: {nonzero}")
    assert_equal(a10["blind_prediction_sha256_before_unlock"], BLIND_SHA256, "blind SHA before unlock")
    assert_equal(a10["blind_prediction_sha256_after_scoring"], BLIND_SHA256, "blind SHA after scoring")
    return {
        "a1_10_report_value_checks": report_checks,
        "target_rows": target_rows,
        "benchmark_rows": benchmark_rows,
        "bootstrap_rows": bootstrap_rows,
        "grade_rows": grade_rows,
        "a1_9_models": a19["models"],
        "a1_10_summary": a10,
    }


def provenance_registry_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for stage in STAGES:
        artifact = stage["artifact"]
        notes = (
            f"determination={stage['determination']}; taskbook={stage['taskbook']}; "
            f"report={stage['report']}; preregistration_commit={stage['preregistration_commit']}; "
            f"result_commit={stage['result_commit']}; fix_commits={stage['fix_commits'] or 'none'}; "
            f"conclusion={stage['conclusion']}; warnings={stage['warnings']}"
        )
        evidence_type = "DATA_CONTRACT" if stage["stage"].startswith("A0") else "INTEGRITY"
        if stage["stage"] == "A1.9":
            evidence_type = "METHOD_FREEZE"
        elif stage["stage"] in {"A1.10a", "A1.10b"}:
            evidence_type = "BLIND_TEST" if stage["stage"] == "A1.10b" else "INTEGRITY"
        rows.append(
            {
                "evidence_id": "E_PROV_" + stage["stage"].replace(".", "").replace("-", "_"),
                "stage": stage["stage"],
                "evidence_type": evidence_type,
                "target": "all",
                "artifact_path": artifact,
                "artifact_sha256": artifact_hash_contract(artifact),
                "commit": stage["result_commit"],
                "metric_name": "stage_determination",
                "metric_value": stage["determination"],
                "uncertainty": "",
                "sample_n": stage["sample_n"],
                "task_group_n": "",
                "benchmark_scope": "frozen stage scope",
                "model_scope": "frozen stage scope",
                "claim_role": "provenance",
                "scientific_status": "INTEGRITY_ONLY",
                "notes": notes,
            }
        )
    return rows


def dev_registry_rows() -> list[dict[str, str]]:
    type_map = {
        "A1.2": "DEV_BASELINE",
        "A1.3": "LOBO",
        "A1.4": "MODEL_TRANSFER",
        "A1.5": "ABLATION",
        "A1.6": "UNCERTAINTY",
        "A1.7": "DENSE_SEMANTICS",
    }
    scope_map = {
        "A1.2": "grouped five-fold official dev",
        "A1.3": "primary four-family LOBO on official dev",
        "A1.4": "held-out Agent model with underlying tasks represented in training",
        "A1.5": "primary four-family LOBO structural ablations on official dev",
        "A1.6": "task-group bootstrap of frozen A1.3/A1.5 dev predictions",
        "A1.7": "primary four-family LOBO dense semantic baseline on official dev",
    }
    rows: list[dict[str, str]] = []
    for source in read_csv("artifacts/a1_8_evidence_registry.csv"):
        uncertainty = ""
        if source["ci_lower"] or source["ci_upper"]:
            uncertainty = (
                f"95% CI [{source['ci_lower']}, {source['ci_upper']}]; "
                f"valid_fraction={source['valid_fraction'] or 'NA'}"
            )
        artifact = source["source_artifact"]
        role = source["support_role"]
        rows.append(
            {
                "evidence_id": source["evidence_id"],
                "stage": source["stage_id"],
                "evidence_type": type_map[source["stage_id"]],
                "target": source["target"],
                "artifact_path": artifact,
                "artifact_sha256": artifact_hash_contract(artifact),
                "commit": source["formal_commit"],
                "metric_name": source["metric_or_estimand"],
                "metric_value": source["point_estimate"],
                "uncertainty": uncertainty,
                "sample_n": source["sample_size"],
                "task_group_n": "",
                "benchmark_scope": scope_map[source["stage_id"]],
                "model_scope": "frozen dev Agent models",
                "claim_role": "exploratory_dev" if role in {"diagnostic", "exploratory"} else "dev_only",
                "scientific_status": "DEV_ONLY",
                "notes": f"source_row_key={source['source_row_key']}; support_role={role}; {source['notes']}",
            }
        )
    return rows


def final_method_registry_rows(models: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for model in models:
        rows.append(
            {
                "evidence_id": "E_A19_" + model["target"].upper() + "_METHOD_FREEZE",
                "stage": "A1.9",
                "evidence_type": "METHOD_FREEZE",
                "target": model["target"],
                "artifact_path": model["artifact_path"],
                "artifact_sha256": model["artifact_sha256"],
                "commit": "8f96a6f032ee9b4dd0272164d60230303612043b",
                "metric_name": "selected_method_threshold",
                "metric_value": f"{model['method_id']}@{model['selected_threshold']}",
                "uncertainty": "",
                "sample_n": str(model["dev_eligibility_count"]),
                "task_group_n": "",
                "benchmark_scope": "official dev selection only",
                "model_scope": "frozen final estimator",
                "claim_role": model["role"],
                "scientific_status": "DEV_ONLY",
                "notes": (
                    f"config={model['selected_config']['config_id']}; positive_n={model['dev_positive_count']}; "
                    f"oof_AP={model['final_oof_average_precision']}; oof_F1={model['final_oof_positive_f1']}"
                ),
            }
        )
    return rows


def test_registry_rows(
    target_rows: list[dict[str, str]],
    benchmark_rows: list[dict[str, str]],
    bootstrap_rows: list[dict[str, str]],
    grade_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    target_status = {
        "success": "CONFIRMATORY_SUPPORTED",
        "looping": "CONFIRMATORY_SUPPORTED",
        "side_effect": "EXPLORATORY_SUPPORTED",
    }
    for row in target_rows:
        target = row["target"]
        bootstrap = one(bootstrap_rows, target=target)
        grade = one(grade_rows, target=target)
        result.append(
            {
                "evidence_id": "E_A110_" + target.upper() + "_HELDOUT",
                "stage": "A1.10b",
                "evidence_type": "BLIND_TEST",
                "target": target,
                "artifact_path": "artifacts/a1_10_target_metrics.csv",
                "artifact_sha256": sha256_path(resolve("artifacts/a1_10_target_metrics.csv")),
                "commit": A1_10B_RESULT_COMMIT,
                "metric_name": "pooled_AP|AP_lift|positive_F1",
                "metric_value": (
                    f"{row['pooled_average_precision']}|{row['pooled_ap_lift']}|{row['positive_f1']}"
                ),
                "uncertainty": f"AP-lift 95% CI [{bootstrap['ci_lower']}, {bootstrap['ci_upper']}]",
                "sample_n": row["eligible_n"],
                "task_group_n": row["task_group_n"],
                "benchmark_scope": "official held-out tasks/trajectories within evaluated benchmark families",
                "model_scope": "frozen A1.9 final method only",
                "claim_role": row["role"],
                "scientific_status": target_status[target],
                "notes": (
                    f"positive_n={row['positive_n']}; negative_n={row['negative_n']}; "
                    f"prevalence={row['prevalence']}; final_grade={grade['final_grade']}"
                ),
            }
        )
    for row in benchmark_rows:
        target = row["target"]
        benchmark = row["benchmark_group_primary"]
        result.append(
            {
                "evidence_id": f"E_A110_{target.upper()}_{benchmark.upper()}_DESCRIPTIVE",
                "stage": "A1.10b",
                "evidence_type": "BLIND_TEST",
                "target": target,
                "artifact_path": "artifacts/a1_10_benchmark_metrics.csv",
                "artifact_sha256": sha256_path(resolve("artifacts/a1_10_benchmark_metrics.csv")),
                "commit": A1_10B_RESULT_COMMIT,
                "metric_name": "benchmark_AP|positive_F1",
                "metric_value": f"{row['average_precision']}|{row['positive_f1']}",
                "uncertainty": "no frozen pairwise inferential comparison",
                "sample_n": row["eligible_n"],
                "task_group_n": row["task_group_n"],
                "benchmark_scope": benchmark,
                "model_scope": "frozen A1.9 final method only",
                "claim_role": "descriptive_only",
                "scientific_status": "DESCRIPTIVE_ONLY",
                "notes": "Performance varies descriptively; significance language is prohibited.",
            }
        )
    return result


def claim_rows() -> list[dict[str, str]]:
    scope = "official held-out tasks/trajectories within evaluated benchmark families"
    claims = [
        {
            "claim_id": "FC1",
            "claim_text": "Frozen structural trajectory features retain predictive signal for Success on untouched official held-out tasks/trajectories within the evaluated benchmark families.",
            "status": "CONFIRMATORY_SUPPORTED",
            "target": "Success",
            "scope": scope,
            "supporting_evidence_ids": "E_A110_SUCCESS_HELDOUT",
            "contradicting_or_limiting_evidence": "No unseen-benchmark, arbitrary-Agent, joint OOD, or causal evidence.",
            "allowed_paper_section": "Abstract; Results; Discussion",
            "required_qualifier": "frozen structural features; official held-out; evaluated benchmark families",
            "prohibited_extension": "unseen benchmark; arbitrary agents; joint task/model OOD; universal judging; causality",
        },
        {
            "claim_id": "FC2",
            "claim_text": "Frozen structural trajectory features retain strong predictive signal for Looping on untouched official held-out tasks/trajectories within the evaluated benchmark families.",
            "status": "CONFIRMATORY_SUPPORTED",
            "target": "Looping",
            "scope": scope,
            "supporting_evidence_ids": "E_A110_LOOPING_HELDOUT",
            "contradicting_or_limiting_evidence": "No unseen-benchmark, arbitrary-Agent, joint OOD, or causal evidence.",
            "allowed_paper_section": "Abstract; Results; Discussion",
            "required_qualifier": "frozen structural features; official held-out; evaluated benchmark families",
            "prohibited_extension": "unseen benchmark; arbitrary agents; joint task/model OOD; universal judging; causality",
        },
        {
            "claim_id": "FE1",
            "claim_text": "The frozen dense semantic Side Effect model showed positive exploratory held-out signal.",
            "status": "EXPLORATORY_SUPPORTED",
            "target": "Side Effect",
            "scope": scope,
            "supporting_evidence_ids": "E_A110_SIDE_EFFECT_HELDOUT",
            "contradicting_or_limiting_evidence": "Low dev support, 12 dev positives, and exploratory-only preregistered role.",
            "allowed_paper_section": "Exploratory Results; Limitations",
            "required_qualifier": "exploratory_only; low-support; not confirmatory",
            "prohibited_extension": "confirmed detector; confirmatory Side Effect claim; general deployment claim",
        },
        {
            "claim_id": "FD1",
            "claim_text": "B2 is better than B3 for Success.",
            "status": "DEV_ONLY",
            "target": "Success",
            "scope": "frozen official dev protocols",
            "supporting_evidence_ids": "E_A13_SUCCESS_B2_MACRO_AP;E_A13_SUCCESS_B3_MACRO_AP;E_A16_P2_SUCCESS_MACRO_AP",
            "contradicting_or_limiting_evidence": "A1.6 paired interval crosses zero.",
            "allowed_paper_section": "Development Results",
            "required_qualifier": "point-estimate trend; paired difference uncertain; dev-only",
            "prohibited_extension": "stable or significant superiority; held-out comparative claim",
        },
        {
            "claim_id": "FD2",
            "claim_text": "B4 is better than B2/B3 for Success.",
            "status": "DEV_ONLY",
            "target": "Success",
            "scope": "frozen official dev LOBO",
            "supporting_evidence_ids": "E_A17_Q2_SUCCESS_MACRO_AP_DELTA;E_A17_Q3_SUCCESS_MACRO_AP_DELTA",
            "contradicting_or_limiting_evidence": "AP intervals cross zero; B4-B2 macro F1 is a stable drop.",
            "allowed_paper_section": "Development Results",
            "required_qualifier": "no clear incremental AP gain; dev-only",
            "prohibited_extension": "stable dense superiority; official-test comparative claim",
        },
        {
            "claim_id": "FD3",
            "claim_text": "Dense semantics are superior to lightweight representations.",
            "status": "DEV_ONLY",
            "target": "All",
            "scope": "A1.7 frozen dev comparisons",
            "supporting_evidence_ids": "E_A17_Q1_SUCCESS_MACRO_AP_LIFT;E_A17_Q4_SIDE_EFFECT_MACRO_AP;E_A17_Q5_LOOPING_MACRO_AP_DELTA",
            "contradicting_or_limiting_evidence": "Relative gains are target-dependent and mostly uncertain.",
            "allowed_paper_section": "Representation Analysis",
            "required_qualifier": "empirical dev pattern; target-dependent",
            "prohibited_extension": "general superiority or necessity",
        },
        {
            "claim_id": "FD4",
            "claim_text": "Termination features are the Success mechanism.",
            "status": "DEV_ONLY",
            "target": "Success",
            "scope": "A1.5-A1.6 frozen dev ablations",
            "supporting_evidence_ids": "E_A15_SUCCESS_S1_NO_TERMINATION_MACRO_AP;E_A16_P3_SUCCESS_MACRO_AP",
            "contradicting_or_limiting_evidence": "Removal effect is uncertain and ablation is non-causal.",
            "allowed_paper_section": "Development Ablations",
            "required_qualifier": "predictive dependency only; dev-only",
            "prohibited_extension": "causal or dominant mechanism",
        },
        {
            "claim_id": "FD5",
            "claim_text": "Repetition features are the Looping mechanism.",
            "status": "DEV_ONLY",
            "target": "Looping",
            "scope": "A1.5-A1.6 frozen dev ablations",
            "supporting_evidence_ids": "E_A15_LOOPING_S2_NO_REPETITION_MACRO_AP;E_A16_P6_LOOPING_MACRO_AP",
            "contradicting_or_limiting_evidence": "Stable predictive increment does not establish causality or exclusivity.",
            "allowed_paper_section": "Development Ablations",
            "required_qualifier": "stable predictive increment; non-causal; dev-only",
            "prohibited_extension": "complete or causal mechanism",
        },
        {
            "claim_id": "FD6",
            "claim_text": "S6 can replace the full S0 structural representation.",
            "status": "DEV_ONLY",
            "target": "Success; Looping",
            "scope": "A1.5-A1.6 frozen dev ablations",
            "supporting_evidence_ids": "E_A16_P4_SUCCESS_MACRO_AP;E_A16_P7_LOOPING_MACRO_AP",
            "contradicting_or_limiting_evidence": "Paired intervals are uncertain; equivalence was not tested.",
            "allowed_paper_section": "Development Ablations",
            "required_qualifier": "competitive point estimates; no equivalence claim",
            "prohibited_extension": "proven replacement or equivalence",
        },
        {
            "claim_id": "FD7",
            "claim_text": "A1.4 establishes final cross-model generalization.",
            "status": "DEV_ONLY",
            "target": "All",
            "scope": "held-out Agent model with same tasks represented in training",
            "supporting_evidence_ids": "E_A14_SUCCESS_B3_MODEL_MACRO_AP;E_A14_LOOPING_B2_MODEL_MACRO_AP;E_A14_SIDE_EFFECT_B3_MODEL_MACRO_AP",
            "contradicting_or_limiting_evidence": "External group-key counterpart rate is 100%; one model has partial coverage.",
            "allowed_paper_section": "Development Diagnostics",
            "required_qualifier": "model-only transfer; exploratory; same-task condition",
            "prohibited_extension": "joint task/model OOD or arbitrary-Agent generalization",
        },
        {
            "claim_id": "FD8",
            "claim_text": "A universal model-complexity hierarchy is established.",
            "status": "DEV_ONLY",
            "target": "All",
            "scope": "A1.2-A1.7 frozen dev evidence",
            "supporting_evidence_ids": "E_A17_Q2_SUCCESS_MACRO_AP_DELTA;E_A17_Q3_SUCCESS_MACRO_AP_DELTA;E_A17_Q5_LOOPING_MACRO_AP_DELTA",
            "contradicting_or_limiting_evidence": "No uniform improvement with representation complexity.",
            "allowed_paper_section": "Discussion",
            "required_qualifier": "no clear uniform hierarchy; dev-only",
            "prohibited_extension": "simple or complex models universally superior",
        },
        {
            "claim_id": "FD9",
            "claim_text": "A fixed cross-dimension representation hierarchy is established.",
            "status": "DEV_ONLY",
            "target": "All",
            "scope": "A1.2-A1.7 frozen dev evidence",
            "supporting_evidence_ids": "E_A16_P1_SUCCESS_MACRO_AP_LIFT;E_A16_P5_LOOPING_MACRO_AP_LIFT;E_A17_Q4_SIDE_EFFECT_MACRO_AP",
            "contradicting_or_limiting_evidence": "Side Effect support is sparse and comparative increments are uncertain.",
            "allowed_paper_section": "Discussion",
            "required_qualifier": "different empirical relationships; no fixed hierarchy",
            "prohibited_extension": "universal information hierarchy or causal theory",
        },
    ]

    for index, target in enumerate(("Success", "Looping", "Side Effect"), start=1):
        slug = target.lower().replace(" ", "_").upper()
        claims.append(
            {
                "claim_id": f"DH{index}",
                "claim_text": f"{target} performance varies across the four evaluated benchmark families.",
                "status": "DESCRIPTIVE_ONLY",
                "target": target,
                "scope": "A1.10 per-benchmark frozen results",
                "supporting_evidence_ids": ";".join(
                    f"E_A110_{slug}_{benchmark}_DESCRIPTIVE"
                    for benchmark in ("ASSISTANTBENCH", "VISUALWEBARENA", "WEBARENA", "WORKARENA")
                ),
                "contradicting_or_limiting_evidence": "No preregistered pairwise inferential comparison.",
                "allowed_paper_section": "Results; Limitations",
                "required_qualifier": "descriptive heterogeneity only",
                "prohibited_extension": "Benchmark A significantly outperforms Benchmark B",
            }
        )

    claims.extend(
        [
            {
                "claim_id": "NS1",
                "claim_text": "The frozen scores are calibrated probabilities suitable for operational decisions.",
                "status": "NOT_SUPPORTED",
                "target": "All",
                "scope": "current evidence package",
                "supporting_evidence_ids": "",
                "contradicting_or_limiting_evidence": "No calibration experiment or decision-utility study was authorized.",
                "allowed_paper_section": "Limitations",
                "required_qualifier": "predictive ranking/classification evidence only",
                "prohibited_extension": "calibrated risk or deployment safety",
            },
            {
                "claim_id": "NS2",
                "claim_text": "A1.10 establishes pairwise statistical differences between benchmark families.",
                "status": "NOT_SUPPORTED",
                "target": "All",
                "scope": "A1.10 per-benchmark table",
                "supporting_evidence_ids": "E_A110_SUCCESS_ASSISTANTBENCH_DESCRIPTIVE;E_A110_SUCCESS_WORKARENA_DESCRIPTIVE",
                "contradicting_or_limiting_evidence": "No frozen pairwise inferential test exists.",
                "allowed_paper_section": "Limitations",
                "required_qualifier": "descriptive variation only",
                "prohibited_extension": "significantly better or worse benchmark claims",
            },
        ]
    )

    prohibited = [
        ("PO1", "Our method generalizes to unseen benchmarks.", "No truly independent unseen benchmark was evaluated.", "E_A110_SUCCESS_HELDOUT;E_A110_LOOPING_HELDOUT"),
        ("PO2", "Our method generalizes to arbitrary agents.", "Agent coverage is finite and A1.4 is model-only same-task transfer.", "E_A14_SUCCESS_B3_MODEL_MACRO_AP;E_A14_LOOPING_B2_MODEL_MACRO_AP"),
        ("PO3", "Our method establishes joint task-and-model OOD robustness.", "No joint unseen-task plus unseen-model protocol was run.", "E_A14_SUCCESS_B3_MODEL_MACRO_AP;E_A110_SUCCESS_HELDOUT"),
        ("PO4", "Structural features causally determine Success or Looping.", "Predictive features and ablations do not identify causal mechanisms.", "E_A16_P3_SUCCESS_MACRO_AP;E_A16_P6_LOOPING_MACRO_AP"),
        ("PO5", "The system is a universal Agent Judge.", "Evidence is limited to three targets and evaluated benchmark families.", "E_A110_SUCCESS_HELDOUT;E_A110_LOOPING_HELDOUT;E_A110_SIDE_EFFECT_HELDOUT"),
        ("PO6", "Side Effect is a confirmed held-out detector.", "Side Effect was preregistered and evaluated as exploratory-only with low dev support.", "E_A110_SIDE_EFFECT_HELDOUT;E_A17_Q4_SIDE_EFFECT_MACRO_AP"),
        ("PO7", "Simple models universally outperform complex models.", "Only a bounded model/representation set was compared and several differences are uncertain.", "E_A17_Q2_SUCCESS_MACRO_AP_DELTA;E_A17_Q3_SUCCESS_MACRO_AP_DELTA;E_A17_Q5_LOOPING_MACRO_AP_DELTA"),
        ("PO8", "Dense semantics are generally unnecessary.", "Dense semantics showed target-dependent signal and was not exhaustively tested.", "E_A17_Q1_SUCCESS_MACRO_AP_LIFT;E_A17_Q4_SIDE_EFFECT_MACRO_AP;E_A17_Q5_LOOPING_MACRO_AP_DELTA"),
    ]
    for claim_id, text, reason, evidence_ids in prohibited:
        claims.append(
            {
                "claim_id": claim_id,
                "claim_text": text,
                "status": "PROHIBITED_OVERCLAIM",
                "target": "All",
                "scope": "outside supported evidence boundary",
                "supporting_evidence_ids": evidence_ids,
                "contradicting_or_limiting_evidence": reason,
                "allowed_paper_section": "Limitations or reviewer-response rejection only",
                "required_qualifier": "must not be asserted as a supported finding",
                "prohibited_extension": text,
            }
        )
    return claims


def main_table_rows(
    target_rows: list[dict[str, str]],
    bootstrap_rows: list[dict[str, str]],
    grade_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    display = {"success": "Success", "looping": "Looping", "side_effect": "Side Effect"}
    rows: list[dict[str, str]] = []
    for target in ("success", "looping", "side_effect"):
        source = one(target_rows, target=target)
        boot = one(bootstrap_rows, target=target)
        grade = one(grade_rows, target=target)
        rows.append(
            {
                "Target": display[target],
                "Role": source["role"],
                "Eligible": source["eligible_n"],
                "Positive": source["positive_n"],
                "Negative": source["negative_n"],
                "Prevalence": source["prevalence"],
                "Final Method": source["method_id"],
                "Threshold": source["threshold"],
                "AP": source["pooled_average_precision"],
                "AP Lift": source["pooled_ap_lift"],
                "F1": source["positive_f1"],
                "AP-lift 95% CI Lower": boot["ci_lower"],
                "AP-lift 95% CI Upper": boot["ci_upper"],
                "Final Grade": grade["final_grade"],
            }
        )
    return rows


def benchmark_table_rows(source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    display = {"success": "Success", "looping": "Looping", "side_effect": "Side Effect"}
    return [
        {
            "Target": display[row["target"]],
            "Benchmark": row["benchmark_group_primary"],
            "AP": row["average_precision"],
            "F1": row["positive_f1"],
            "Role": row["role"],
            "Interpretation": "DESCRIPTIVE_ONLY",
        }
        for row in source_rows
    ]


def dev_summary_rows(registry: list[dict[str, str]]) -> list[dict[str, str]]:
    selected = [
        ("Minimal grouped baselines", "E_A12_SUCCESS_B2_POOLED_AP", "provisional dev signal"),
        ("Minimal grouped baselines", "E_A12_SIDE_EFFECT_B3_POOLED_AP", "low-support dev signal"),
        ("Minimal grouped baselines", "E_A12_LOOPING_B2_POOLED_AP", "provisional dev signal"),
        ("External / LOBO", "E_A13_SUCCESS_B2_MACRO_AP", "dev-only cross-family evidence"),
        ("External / LOBO", "E_A13_SIDE_EFFECT_B3_MACRO_AP", "diagnostic; sparse support"),
        ("External / LOBO", "E_A13_LOOPING_B2_MACRO_AP", "dev-only cross-family evidence"),
        ("Model-only transfer", "E_A14_SUCCESS_B3_MODEL_MACRO_AP", "same-task model-only transfer"),
        ("Model-only transfer", "E_A14_SIDE_EFFECT_B3_MODEL_MACRO_AP", "exploratory and low-support"),
        ("Model-only transfer", "E_A14_LOOPING_B2_MODEL_MACRO_AP", "same-task model-only transfer"),
        ("Structural ablation", "E_A15_SUCCESS_S6_TERMINATION_REPETITION_ONLY_MACRO_AP", "competitive point estimate; not equivalence"),
        ("Structural ablation", "E_A15_LOOPING_S2_NO_REPETITION_MACRO_AP", "predictive dependency; non-causal"),
        ("Uncertainty", "E_A16_P1_SUCCESS_MACRO_AP_LIFT", "stable positive dev LOBO signal"),
        ("Uncertainty", "E_A16_P2_SUCCESS_MACRO_AP", "B2-B3 difference uncertain"),
        ("Uncertainty", "E_A16_P5_LOOPING_MACRO_AP_LIFT", "stable positive dev LOBO signal"),
        ("Uncertainty", "E_A16_P6_LOOPING_MACRO_AP", "stable repetition-feature increment; non-causal"),
        ("Dense semantics", "E_A17_Q1_SUCCESS_MACRO_AP_LIFT", "stable positive signal; no stable relative gain"),
        ("Dense semantics", "E_A17_Q4_SIDE_EFFECT_MACRO_AP", "support diagnostic only"),
        ("Dense semantics", "E_A17_Q5_LOOPING_MACRO_AP_DELTA", "relative difference uncertain"),
        ("Final method freeze", "E_A19_SUCCESS_METHOD_FREEZE", "confirmatory method frozen before test"),
        ("Final method freeze", "E_A19_LOOPING_METHOD_FREEZE", "confirmatory method frozen before test"),
        ("Final method freeze", "E_A19_SIDE_EFFECT_METHOD_FREEZE", "exploratory-only method freeze"),
    ]
    by_id = {row["evidence_id"]: row for row in registry}
    result: list[dict[str, str]] = []
    for area, evidence_id, boundary in selected:
        row = by_id[evidence_id]
        lower = upper = ""
        if row["uncertainty"].startswith("95% CI ["):
            interval = row["uncertainty"].split("[", 1)[1].split("]", 1)[0]
            lower, upper = [part.strip() for part in interval.split(",", 1)]
        determination = next(stage["determination"] for stage in STAGES if stage["stage"] == row["stage"])
        result.append(
            {
                "Evidence Area": area,
                "Stage": row["stage"],
                "Target": row["target"],
                "Method or Comparison": evidence_id,
                "Metric": row["metric_name"],
                "Point Estimate": row["metric_value"],
                "95% CI Lower": lower,
                "95% CI Upper": upper,
                "Stage Determination": determination,
                "Support Level": row["claim_role"],
                "Claim Boundary": boundary,
                "Source Artifact": row["artifact_path"],
                "Source Commit": row["commit"],
            }
        )
    return result


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def claim_ledger(claims: list[dict[str, str]], claim_hash: str) -> str:
    lines = [
        "# A1.11 Final Claim Ledger",
        "",
        f"Final claim matrix SHA-256: `{claim_hash}`",
        "",
        "This hash is the claim contract for manuscript drafting. Without a newly approved Stage, the manuscript must not add a confirmatory claim, enlarge claim scope, remove a frozen limitation, or promote exploratory evidence to confirmatory status.",
        "",
        "| Claim | Status | Target | Allowed claim / boundary | Required qualifier | Prohibited extension |",
        "|---|---|---|---|---|---|",
    ]
    for row in claims:
        lines.append(
            "| " + " | ".join(
                md_escape(row[key])
                for key in (
                    "claim_id",
                    "status",
                    "target",
                    "claim_text",
                    "required_qualifier",
                    "prohibited_extension",
                )
            ) + " |"
        )
    lines.extend(
        [
            "",
            "## Core frozen metrics",
            "",
            "- FC1 Success: AP 0.654836; AP lift 0.389567; F1 0.682099; AP-lift 95% CI [0.326806, 0.455411].",
            "- FC2 Looping: AP 0.921769; AP lift 0.394829; F1 0.876987; AP-lift 95% CI [0.360965, 0.428598].",
            "- FE1 Side Effect: AP 0.107279; AP lift 0.042851; F1 0.168582; AP-lift 95% CI [0.021245, 0.079200]; exploratory_only, low-support, not confirmatory.",
        ]
    )
    return "\n".join(lines)


def figure_spec() -> str:
    return """# A1.11 Paper Figure Specification

## Figure 1 — Blind-first evaluation protocol

- Question: how did development-only selection lead to an untouched official held-out evaluation?
- Source: `artifacts/a1_9_run_summary.json`, `artifacts/a1_10a_run_summary.json`, `artifacts/a1_10_run_summary.json`.
- Layout: left-to-right protocol timeline: dev-only grouped selection → A1.9 method/threshold/hash freeze → A1.10a identifier/content-only inference → blind prediction commit/hash → one-time label unlock → A1.10b frozen scoring.
- Caption emphasis: labels, eligibility, and metrics were unavailable when blind predictions were generated; blind prediction bytes were unchanged after unlock.
- Forbidden interpretation: the protocol does not establish unseen-benchmark or joint task/model OOD generalization.

## Figure 2 — Final held-out AP lift with frozen 95% CI

- Question: which targets retain positive signal above their held-out prevalence?
- Source: `artifacts/a1_10_bootstrap_summary.csv` and `artifacts/a1_10_confirmatory_grade.csv`.
- Marks: one point and frozen percentile interval per target; no new bootstrap.
- X-axis: target. Y-axis: pooled AP lift. Reference line: zero.
- Status encoding: Success and Looping are confirmatory; Side Effect is visually and textually marked exploratory-only.
- Caption emphasis: official held-out tasks/trajectories within evaluated benchmark families.

## Figure 3 — Per-benchmark descriptive AP

- Question: how does observed signal strength vary across evaluated benchmark families?
- Source: `artifacts/a1_10_benchmark_metrics.csv` or the frozen copy `artifacts/a1_11_table_benchmark_results.csv`.
- X-axis: benchmark family. Y-axis: AP. Facet or color: target.
- Caption requirement: descriptive heterogeneity only; not a preregistered pairwise significance comparison.
- Forbidden annotation: significance stars, pairwise p-values, or claims that one benchmark significantly outperforms another.

## Figure 4 — Development representation and ablation evidence

- Question: what development-stage evidence motivated the frozen target-specific methods?
- Source: `artifacts/a1_6_primary_paired_delta_summary.csv`, `artifacts/a1_7_bootstrap_primary_summary.csv`, and `artifacts/a1_11_dev_evidence_summary.csv`.
- Suggested panels: Success B2/B3/B4 paired estimates; Looping repetition ablation; Side Effect support diagnostic.
- Status label: `DEV_ONLY` on the figure and in the caption.
- Caption emphasis: several comparative intervals cross zero; ablations are predictive, not causal; Side Effect dev support is sparse.
"""


def results_outline() -> str:
    return """# A1.11 Paper Results Outline

| Section | Frozen source | Table / figure | Allowed claim | Forbidden interpretation |
|---|---|---|---|---|
| R1. Development-stage signal discovery | `artifacts/a1_2_pooled_metrics.csv` | Dev evidence summary | Report target-specific dev signal patterns. | Confirmatory or held-out claims. |
| R2. Grouped-fold and held-out-family robustness | `artifacts/a1_3_lobo_macro_metrics.csv` | Dev evidence summary | Success and Looping show dev LOBO signal. | Generalization to unseen benchmark datasets. |
| R3. Structural ablations and uncertainty | `artifacts/a1_6_primary_paired_delta_summary.csv` | Figure 4 | Repetition features add predictive value for Looping under the frozen dev protocol. | Causal mechanism or untested equivalence. |
| R4. Dense semantic comparison | `artifacts/a1_7_bootstrap_primary_summary.csv` | Figure 4 | Dense Success signal exists; relative gains are mostly uncertain. | Universal dense superiority or necessity. |
| R5. Final freeze and blind protocol | `artifacts/a1_9_run_summary.json`; `artifacts/a1_10a_run_summary.json` | Figure 1 | Models, thresholds, roles, and blind predictions were frozen before labels. | Test-driven selection or tuning. |
| R6. Official held-out Success | `artifacts/a1_11_table_main_test_results.csv` | Main table; Figure 2 | FC1 within evaluated benchmark families. | Unseen-benchmark, arbitrary-Agent, joint OOD, or causal claims. |
| R7. Official held-out Looping | `artifacts/a1_11_table_main_test_results.csv` | Main table; Figure 2 | FC2 within evaluated benchmark families. | Universal Looping judge or causal explanation. |
| R8. Exploratory Side Effect | `artifacts/a1_11_table_main_test_results.csv` | Main table; Figure 2 | FE1 as exploratory, low-support, non-confirmatory evidence. | Confirmed Side Effect detector. |
| R9. Benchmark heterogeneity | `artifacts/a1_11_table_benchmark_results.csv` | Figure 3 | Performance varies descriptively across families. | Pairwise statistical superiority. |
| R10. Claim boundaries and limitations | `artifacts/a1_11_final_claim_matrix.csv`; `docs/a1_11_limitations_ledger.md` | Claim ledger | State frozen scope and negative evidence. | Removing limitations or promoting claims without a new Stage. |
"""


def limitations_ledger() -> str:
    return """# A1.11 Limitations Ledger

| ID | Frozen limitation | Evidence consequence | Manuscript requirement |
|---|---|---|---|
| L1 | Benchmark-family scope | The official holdout contains tasks/trajectories from evaluated benchmark families, not a truly independent unseen benchmark. | Do not claim unseen-benchmark generalization. |
| L2 | Agent/model scope | A1.4 holds out Agent model names while the same underlying tasks remain represented on the training side; the official test is not joint task/model OOD. | Do not claim arbitrary-Agent or joint OOD robustness. |
| L3 | Side Effect support | Side Effect had 12 eligible positive dev trajectories and was frozen as exploratory-only before test. | Always say exploratory_only, low-support, and not confirmatory. |
| L4 | Label and construct limitations | The data contract records consensus exclusions, an audit-only official primary rule, and no standard license identifier. | Describe only documented annotation/data-contract limitations; do not invent construct facts. |
| L5 | Prediction is not causation | Structural prediction and ablation effects do not identify causal mechanisms. | Use predictive-association language for termination and repetition features. |
| L6 | Benchmark heterogeneity | Success and the other targets show materially different descriptive AP/F1 across families. | Treat this as an external-validity limitation and future-work motivation, not pairwise significance. |
| L7 | Comparative representation uncertainty | Several B2/B3/B4 and S6/S0 paired intervals cross zero; one Success B4-B2 F1 contrast is a stable drop. | Do not assert a universal representation or complexity hierarchy. |
| L8 | Operational validity | Calibration, selective prediction, deployment utility, and online behavior were not evaluated. | Do not present scores as calibrated risk or deployment safety evidence. |

These limitations are part of the final claim contract. Removing or weakening one requires a newly approved Stage.
"""


def a2_gap_analysis() -> str:
    return """# A1.11 A2 Gap Analysis

## Bottom line

The current evidence is sufficient to begin the manuscript body now: FC1 and FC2 have frozen blind held-out support, FE1 has an explicitly exploratory role, and the provenance and claim boundaries are auditable. The largest remaining evidence gap is external validity: there is no truly independent benchmark/dataset that can support an unseen-benchmark claim. A secondary gap is mechanism validity; current feature and ablation evidence is predictive rather than causal.

## MUST

- Begin the manuscript body using the A1.11 claim matrix as the binding claim contract.
- Preserve FC1/FC2 scope, FE1 exploratory status, all limitations, and the descriptive-only benchmark interpretation.
- Require a new approved Stage before any new experiment or claim expansion.

## SHOULD

- Design, but do not yet execute, a genuinely independent external benchmark/dataset validation if unseen-benchmark generalization is important to the paper's intended contribution.
- Design a lightweight mechanism-validation stage for the Success termination and Looping repetition signals, with explicit non-causal alternatives and preregistered tests.

## OPTIONAL

- Add a separately approved joint task/model OOD study if arbitrary-Agent robustness is central to the target venue.
- Add frozen-artifact error taxonomy or efficiency presentation that does not alter claims or rerun test inference.

## DO_NOT_PRIORITIZE

- Additional complex classifiers, fusion, larger or second embedding models, calibration, or an LLM Judge merely to chase score gains.
- New benchmarks or datasets without a preregistered external-validity question and stage gate.

## Recommendation

Start paper writing now. For A2 design review, prioritize independent external validation first and targeted mechanism validation second; do not prioritize additional model complexity.
"""


def report_text(
    registry_rows: list[dict[str, str]],
    claims: list[dict[str, str]],
    claim_hash: str,
    main_hash: str,
    provenance: dict[str, Any],
    consistency: dict[str, Any],
    fix_commits: list[str],
) -> str:
    counts = Counter(row["status"] for row in claims)
    return f"""# Stage A1.11 Final Evidence Consolidation Report

## 1. Stage determination

`PASS`

Final state after the independent result commit and clean-tree verification: `READY_FOR_A2_DESIGN_REVIEW`.

## 2. Git and input provenance

- Branch: `master`
- Clean start HEAD / A1.11a: `{A1_11A_COMMIT}`
- A1.11a parent / A1.10b result: `{A1_10B_RESULT_COMMIT}`
- A1.10a result: `cead3cbaa362da4a9918dab32e41b58fffb987d9`
- A1.10a fix: `100966969bf36c968051dea7fbbb675c1814b7cd`
- A1.10b preregistration: `042866147e7b4a0c930eeb120d6e642cb34773a7`
- A1.10b pre-unlock fix: `3f0bc4da460652a74ae4767ff6d482fd4116ec9f`
- A1.10b pre-unlock integrity: `85cb71a49c9c25c9284562afad751f975d787608`
- A1.9a / A1.9b: `4944df46be45d8ad52d57a051e04b59c4a1a82ee` / `8f96a6f032ee9b4dd0272164d60230303612043b`
- GitHub / Hugging Face revisions: `{GITHUB_REVISION}` / `{HF_REVISION}`
- Blind / scored prediction SHA-256: `{BLIND_SHA256}` / `{SCORED_SHA256}`
- A1.8 claim matrix SHA-256: `{A1_8_CLAIM_SHA256}`
- A1.11 fix commits: `{';'.join(fix_commits)}`
- A1.11b result commit: `{RESULT_COMMIT_SENTINEL}`; no amend.

## 3. A0-A1.10 provenance coverage

Coverage is {len(STAGES)}/{len(STAGES)} stage units: {', '.join(stage['stage'] for stage in STAGES)}. Every unit records a determination, taskbook, formal report, machine artifact, result commit, fix commits where applicable, sample scope, scientific conclusion, warning boundary, and current artifact SHA-256. {provenance['verified_commit_count']} unique commits and {provenance['verified_a1_2_to_a1_7_source_hashes']} frozen A1.2-A1.7 sources were directly verified. The existing A1.8 audit's 277 report/artifact checks remain intact.

## 4. A1.9-A1.10 consistency and blind provenance

- Three final methods, roles, thresholds, and model hashes match exactly across A1.9 and A1.10 pre-unlock artifacts.
- A1.10 target metrics, bootstrap summaries, grades, final claim status, JSON summary, and {consistency['a1_10_report_value_checks']} rounded report values agree.
- Blind prediction bytes are identical before and after label unlock.
- Join integrity is complete at 3,318 rows with zero duplicates, unmatched rows, silent drops, or metadata mismatches.
- No test metric was recomputed in A1.11; the script only compared frozen fields and hashes.

## 5. Evidence registry and final claim matrix

- Evidence registry rows: {len(registry_rows)}
- Final claim matrix rows: {len(claims)}
- Claim status counts: {json.dumps(dict(sorted(counts.items())), ensure_ascii=False)}
- Final claim matrix SHA-256: `{claim_hash}`

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

- Dev-only claims: {counts['DEV_ONLY']}; none upgraded from development evidence.
- Prohibited overclaims: {counts['PROHIBITED_OVERCLAIM']}.
- Not-supported claims: {counts['NOT_SUPPORTED']}.
- Descriptive-only benchmark heterogeneity claims: {counts['DESCRIPTIVE_ONLY']}.

## 8. Benchmark heterogeneity

Observed AP/F1 varies across assistantbench, visualwebarena, webarena, and workarena for all three targets. These rows are frozen as `DESCRIPTIVE_ONLY`; no preregistered pairwise inferential comparison supports wording that one benchmark significantly outperforms another.

## 9. Paper package

- Main held-out table SHA-256: `{main_hash}`
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
"""


def run() -> dict[str, Any]:
    provenance = verify_commits_and_stage_inputs()
    consistency = verify_a1_9_a1_10()
    a1_11_fix_commits = git_output(
        ["log", "--format=%H", "--grep=^fix: .*A1.11"]
    ).splitlines()

    registry = provenance_registry_rows()
    registry.extend(dev_registry_rows())
    registry.extend(final_method_registry_rows(consistency["a1_9_models"]))
    registry.extend(
        test_registry_rows(
            consistency["target_rows"],
            consistency["benchmark_rows"],
            consistency["bootstrap_rows"],
            consistency["grade_rows"],
        )
    )
    ids = [row["evidence_id"] for row in registry]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        raise IntegrityError(f"duplicate evidence IDs: {duplicates}")

    claims = claim_rows()
    claim_ids = [row["claim_id"] for row in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise IntegrityError("duplicate final claim IDs")
    registry_ids = set(ids)
    for row in claims:
        for evidence_id in row["supporting_evidence_ids"].split(";"):
            if not evidence_id:
                continue
            if evidence_id not in registry_ids:
                raise IntegrityError(f"claim {row['claim_id']} cites unknown evidence {evidence_id}")

    main_rows = main_table_rows(
        consistency["target_rows"], consistency["bootstrap_rows"], consistency["grade_rows"]
    )
    benchmark_rows = benchmark_table_rows(consistency["benchmark_rows"])
    dev_rows = dev_summary_rows(registry)

    write_csv("artifacts/a1_11_evidence_registry.csv", registry, REGISTRY_FIELDS)
    write_json(
        "artifacts/a1_11_evidence_registry.json",
        {"schema_version": "1.0", "row_count": len(registry), "rows": registry},
    )
    write_csv("artifacts/a1_11_final_claim_matrix.csv", claims, CLAIM_FIELDS)
    write_csv("artifacts/a1_11_table_main_test_results.csv", main_rows, MAIN_TABLE_FIELDS)
    write_csv(
        "artifacts/a1_11_table_benchmark_results.csv", benchmark_rows, BENCHMARK_TABLE_FIELDS
    )
    write_csv("artifacts/a1_11_dev_evidence_summary.csv", dev_rows, DEV_TABLE_FIELDS)

    claim_hash = sha256_path(resolve("artifacts/a1_11_final_claim_matrix.csv"))
    main_hash = sha256_path(resolve("artifacts/a1_11_table_main_test_results.csv"))
    write_text("docs/a1_11_final_claim_ledger.md", claim_ledger(claims, claim_hash))
    write_text("docs/a1_11_paper_figure_spec.md", figure_spec())
    write_text("docs/a1_11_paper_results_outline.md", results_outline())
    write_text("docs/a1_11_limitations_ledger.md", limitations_ledger())
    write_text("docs/a1_11_a2_gap_analysis.md", a2_gap_analysis())

    counts = Counter(row["status"] for row in claims)
    warnings = [
        "The first A1.11 implementation invocation stopped before output generation because a multi-artifact evidence source was parsed as one path; the failure is preserved and corrected in an independent fix commit.",
        "Side Effect remains exploratory-only and low-support despite positive held-out AP lift.",
        "Per-benchmark results are descriptive only; no pairwise significance comparison exists.",
        "A1.4 is model-only same-task transfer, not joint task/model OOD.",
        "Structural ablations are predictive, not causal.",
        "The dataset declares custom Terms of Use but no standard license identifier.",
        "Calibration, deployment utility, and online behavior were not evaluated.",
    ]
    summary = {
        "stage": "A1.11",
        "determination": "PASS",
        "head_before": A1_11A_COMMIT,
        "result_commit": RESULT_COMMIT_SENTINEL,
        "a1_11_fix_commits": a1_11_fix_commits,
        "implementation_failures": {
            "count": len(read_json("artifacts/a1_11_implementation_failures.json")["failures"]),
            "path": "artifacts/a1_11_implementation_failures.json",
            "sha256": sha256_path(resolve("artifacts/a1_11_implementation_failures.json")),
        },
        "input_reports": [stage["report"] for stage in STAGES],
        "input_machine_artifacts": sorted({stage["artifact"] for stage in STAGES}),
        "verified_commits": {
            stage["stage"]: {
                "preregistration": stage["preregistration_commit"],
                "result": stage["result_commit"],
                "fixes": [item for item in stage["fix_commits"].split(";") if item],
            }
            for stage in STAGES
        },
        "verified_hashes": {
            "github_revision": GITHUB_REVISION,
            "huggingface_revision": HF_REVISION,
            "a1_8_claim_matrix": A1_8_CLAIM_SHA256,
            "a1_10_blind_predictions": BLIND_SHA256,
            "a1_10_scored_predictions": SCORED_SHA256,
        },
        "provenance_audit": {
            "coverage_count": len(STAGES),
            "coverage_expected": len(STAGES),
            "stage_units": provenance["stage_units"],
            "verified_commit_count": provenance["verified_commit_count"],
            "verified_a1_2_to_a1_7_source_hashes": provenance[
                "verified_a1_2_to_a1_7_source_hashes"
            ],
            "a1_2_to_a1_7_report_artifact_values_previously_verified": 277,
            "a1_10_report_value_checks": consistency["a1_10_report_value_checks"],
            "status": "PASS",
        },
        "evidence_registry_rows": len(registry),
        "claim_count_by_status": dict(sorted(counts.items())),
        "core_confirmatory_claims": ["FC1", "FC2"],
        "exploratory_claims": ["FE1"],
        "dev_only_claims": [row["claim_id"] for row in claims if row["status"] == "DEV_ONLY"],
        "prohibited_overclaims": [
            row["claim_id"] for row in claims if row["status"] == "PROHIBITED_OVERCLAIM"
        ],
        "main_table_hash": main_hash,
        "final_claim_matrix_hash": claim_hash,
        "output_hashes": {
            path_text: sha256_path(resolve(path_text))
            for path_text in (
                "artifacts/a1_11_evidence_registry.csv",
                "artifacts/a1_11_evidence_registry.json",
                "artifacts/a1_11_final_claim_matrix.csv",
                "artifacts/a1_11_table_main_test_results.csv",
                "artifacts/a1_11_table_benchmark_results.csv",
                "artifacts/a1_11_dev_evidence_summary.csv",
                "docs/a1_11_final_claim_ledger.md",
                "docs/a1_11_paper_figure_spec.md",
                "docs/a1_11_paper_results_outline.md",
                "docs/a1_11_limitations_ledger.md",
                "docs/a1_11_a2_gap_analysis.md",
            )
        },
        "warnings": warnings,
        "inconsistencies": [],
        "new_experiments_executed": 0,
        "model_fits": 0,
        "inference_runs": 0,
        "embedding_runs": 0,
        "test_metric_recomputations": 0,
        "bootstrap_reruns": 0,
        "threshold_changes": 0,
        "eligibility_changes": 0,
        "model_changes": 0,
        "git_start_clean": True,
        "git_clean": True,
        "limitations_count": 8,
        "a2_gap_recommendation": "Start manuscript writing now; prioritize independent external validation, then lightweight mechanism validation; do not prioritize additional model complexity.",
        "next_stage_recommendation": "READY_FOR_A2_DESIGN_REVIEW",
    }
    write_json("artifacts/a1_11_run_summary.json", summary)
    write_text(
        "docs/stage_a1_11_final_evidence_consolidation_report.md",
        report_text(
            registry,
            claims,
            claim_hash,
            main_hash,
            provenance,
            consistency,
            a1_11_fix_commits,
        ),
    )

    compact = {
        "determination": "PASS",
        "provenance": f"{len(STAGES)}/{len(STAGES)}",
        "evidence_registry_rows": len(registry),
        "claim_rows": len(claims),
        "claim_status_counts": dict(sorted(counts.items())),
        "final_claim_matrix_sha256": claim_hash,
        "main_test_table_sha256": main_hash,
        "inconsistencies": 0,
        "new_experiments": 0,
        "model_fits": 0,
        "inference_runs": 0,
        "embedding_runs": 0,
        "test_metric_recomputations": 0,
        "fix_commits": a1_11_fix_commits,
        "next": "READY_FOR_A2_DESIGN_REVIEW",
    }
    print(json.dumps(compact, sort_keys=True))
    return summary


if __name__ == "__main__":
    run()
