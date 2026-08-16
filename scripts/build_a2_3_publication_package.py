#!/usr/bin/env python3
"""Build the deterministic Stage A2.3 publication evidence package.

This builder performs artifact reads, exact field joins, claim mapping, hashing,
and report generation only. It deliberately imports no scientific-computing or
model library and contains no training, inference, embedding, resampling,
threshold-selection, eligibility-selection, or metric-recomputation path.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PREREG_COMMIT = "409807cf1dce736bc9e6a97ff6698de18b024b6f"
A2_1_RESULT_COMMIT = "b4e4a6ab95d8191f1bef91dab9844bef48f00a8d"
A2_2_RESULT_COMMIT = "a57befbb027d2544d32e3e0cde906c2edf13d385"
IMPLEMENTATION_COMMIT = "583ef6eec683151f08b458b1976da62b36accc9f"
RESULT_COMMIT_SENTINEL = "recorded_by_enclosing_result_commit"

INPUTS: dict[str, tuple[str, str]] = {
    "taskbook": (
        "docs/tasks/STAGE_A2_3_BASELINE_PAPER_PACKAGE.md",
        "a84d68ae81ff578d156bddb40058feb477cae6dcd7165effa8733a5df5984a46",
    ),
    "claim_matrix": (
        "artifacts/a1_11_final_claim_matrix.csv",
        "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175",
    ),
    "main_test_table": (
        "artifacts/a1_11_table_main_test_results.csv",
        "c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947",
    ),
    "benchmark_table": (
        "artifacts/a1_11_table_benchmark_results.csv",
        "3df5b511d0cf29472ccfba5c63ea28caf4b58407285109231f176871668d77a2",
    ),
    "dev_evidence": (
        "artifacts/a1_11_dev_evidence_summary.csv",
        "0b6860d68c51cf343044739743c5d92f5f28d34c2213ed9635e2acf2fe184d0e",
    ),
    "baseline_registry": (
        "configs/baseline_registry.yaml",
        "956ba0395f8ade9fc91ee4d10e0590d82eca0a889db97950f0faa00ec38dab17",
    ),
    "a1_2_config": (
        "configs/stage_a1_2_execution.yaml",
        "ab09e851b43c6a3f98cc18be571f0786dff7e21f5a74e3c5b37f41023af9ee28",
    ),
    "feature_registry": (
        "artifacts/a1_5_feature_group_registry.csv",
        "23faa8f97c9cba9456081927d4fd633787179aa34e9eda51e9c31a960931f65d",
    ),
    "a1_7_config": (
        "configs/stage_a1_7_dense_semantic.yaml",
        "6e87198b93c19792b21944a189898b77f0d403dfb9bbddb4b64a432baaa04828",
    ),
    "research_charter": (
        "research/00_RESEARCH_CHARTER.md",
        "dc76edb162ab6b64d73e6af0ea8bd7a3aeb975acf0fe16c5a6d66007e48f65a1",
    ),
    "a1_11_limitations": (
        "docs/a1_11_limitations_ledger.md",
        "d16384d16a0f25456524efaa4e1624f7338dc472d235ff2e0d083ac8e0e58057",
    ),
    "efficiency_summary": (
        "artifacts/a2_1_efficiency_summary.csv",
        "7d37fddef61b526f4b054483ba900ba72a69b0c4c98cd2b31b7ce725043df0c3",
    ),
    "efficiency_relative": (
        "artifacts/a2_1_efficiency_relative_cost.csv",
        "fb8619c1914b4a23308800bd3aaf2dd256701820443f3b0a171f7508c4fa3d1f",
    ),
    "efficiency_environment": (
        "artifacts/a2_1_environment.json",
        "7ffa7812b67a6ab4faaf1d08caadb105d1f8391ffe7af2688c4ffbf1c9fdf1ec",
    ),
    "coefficients": (
        "artifacts/a2_2_structural_coefficients.csv",
        "cd762d7975566f2d107cddff82e8e2d2a58738ee8dbf74f13ee8cffad1ec29d2",
    ),
    "feature_evidence": (
        "artifacts/a2_2_feature_group_evidence.csv",
        "8160dc969d6043b8da8ee294b8cabb8811c5d4171af24cad6ec0f35efd881af8",
    ),
    "metadata_summary": (
        "artifacts/a2_2_metadata_baseline_summary.csv",
        "f5bf2aa3c71e81f2025de01c38d93be0af1a0038e772a5d282649bccd33df967",
    ),
    "error_manifest": (
        "artifacts/a2_2_error_case_manifest.csv",
        "0372151a32b24fb9f5b53acc802dc23d480ff2bc813c2d394b7faeca33e70cf0",
    ),
    "error_notes": (
        "artifacts/a2_2_error_case_notes.csv",
        "ec060f556d6402dfa7a333c4c7498a20d1b2e5d067002a9bfdcb2225e3b1b6ee",
    ),
    "a2_2_summary": (
        "artifacts/a2_2_run_summary.json",
        "9d277fd391bce335ccca3bfa26c467ba7ed755b9e46019637d9568f1862486b5",
    ),
}

OUTPUTS = {
    "baseline_matrix": "artifacts/a2_3_baseline_completeness_matrix.csv",
    "evidence_map": "artifacts/a2_3_evidence_to_paper_map.csv",
    "table_1": "artifacts/a2_3_table_1_main_heldout_results.csv",
    "table_2": "artifacts/a2_3_table_2_efficiency_tradeoff.csv",
    "table_3": "artifacts/a2_3_table_3_dev_representation_summary.csv",
    "table_4": "artifacts/a2_3_table_4_benchmark_heterogeneity.csv",
    "table_5": "artifacts/a2_3_table_5_interpretability_error_summary.csv",
    "figure_spec": "docs/a2_3_publication_figure_spec.md",
    "story": "docs/a2_3_publication_results_story.md",
    "limitations": "docs/a2_3_final_limitations_ledger.md",
    "external_decision": "docs/a2_3_external_validation_decision.md",
    "package_index": "artifacts/a2_3_publication_package_index.csv",
    "summary": "artifacts/a2_3_run_summary.json",
    "report": "docs/stage_a2_3_baseline_paper_package_report.md",
}

COUNTERS = {
    "new_model_fits": 0,
    "new_inference_runs": 0,
    "new_embedding_runs": 0,
    "A1_metric_recomputations": 0,
    "bootstrap_reruns": 0,
    "threshold_changes": 0,
    "eligibility_changes": 0,
    "final_model_changes": 0,
    "official_test_tuning": 0,
}

BASELINE_FIELDS = (
    "method_id",
    "method_name",
    "tier",
    "representation_type",
    "feature_or_embedding_dim",
    "classifier_or_evaluator",
    "semantic_encoder",
    "dev_evaluated",
    "grouped_cv",
    "lobo_evaluated",
    "leave_one_model_out",
    "ablation_role",
    "uncertainty_available",
    "official_test_role",
    "final_method_role",
    "target_scope",
    "evidence_status",
    "source_stage",
    "source_artifact",
    "paper_role",
    "needs_literature_verification",
    "notes",
)

EVIDENCE_MAP_FIELDS = (
    "evidence_id",
    "claim_or_result",
    "target",
    "source_stage",
    "source_artifact",
    "evidence_status",
    "recommended_location",
    "recommended_table_or_figure",
    "allowed_wording",
    "forbidden_wording",
    "reason",
)

TABLE_1_FIELDS = (
    "target",
    "final_method",
    "eligible_n",
    "positive_n",
    "negative_n",
    "prevalence",
    "AP",
    "AP_lift",
    "F1",
    "AP_lift_CI_low",
    "AP_lift_CI_high",
    "claim_status",
    "scope",
)

TABLE_2_FIELDS = (
    "method",
    "representation",
    "dimension",
    "device",
    "cold_start_seconds",
    "extraction_ms_per_trajectory",
    "inference_ms_per_trajectory",
    "representation_size_bytes",
    "classifier_size_bytes",
    "encoder_size_bytes",
    "peak_cpu_rss_mb",
    "peak_gpu_vram_mb",
    "relative_cost",
    "environment_specific",
    "evidence_status",
    "source_artifacts",
)

TABLE_3_FIELDS = (
    "stage",
    "target",
    "method_or_comparison",
    "representation",
    "evidence_area",
    "metric",
    "point_estimate",
    "CI_low_95",
    "CI_high_95",
    "stage_determination",
    "evidence_status",
    "claim_boundary",
    "source_artifact",
    "source_commit",
)

TABLE_4_FIELDS = (
    "target",
    "benchmark",
    "AP",
    "F1",
    "role",
    "evidence_status",
    "source_artifact",
)

TABLE_5_FIELDS = (
    "target",
    "top_structural_signals",
    "feature_group_evidence",
    "metadata_AP",
    "metadata_AP_lift",
    "frozen_B2_dev_AP",
    "main_failure_modes",
    "main_interpretation",
    "evidence_status",
    "source_artifacts",
)

INDEX_FIELDS = (
    "artifact",
    "source_stage",
    "role",
    "evidence_status",
    "paper_location",
    "sha256",
    "verified",
)

RQ_TEXTS = (
    "RQ1: Do lightweight structural trajectory signals contain predictive information for agent evaluation?",
    "RQ2: How robust are these signals across grouped tasks, benchmarks, and model shifts within the development evidence?",
    "RQ3: Which structural feature groups contribute most consistently?",
    "RQ4: Does dense semantic representation provide stable gains over lightweight structural representation in the studied dev regime?",
    "RQ5: Do frozen structural evaluators retain signal on the official blind held-out test?",
    "RQ6: What are the efficiency advantages, confounding risks, and characteristic failure modes of structural evaluation?",
)

PROHIBITED_CLAIMS = (
    "unseen-benchmark generalization",
    "joint task/model OOD generalization",
    "universal Agent Judge",
    "universal LLM Judge replacement",
    "causal mechanism",
    "dense semantics are generally unnecessary",
    "structural models are universally more efficient",
    "metadata confounding completely ruled out",
    "B2 significantly beats metadata-only",
    "benchmark pairwise superiority",
    "Side Effect confirmed",
)

TITLE_CANDIDATES = (
    "Lightweight Structural Signals for Web-Agent Trajectory Evaluation: Blind Held-Out Evidence and Failure Boundaries",
    "How Far Can Structure Go? Efficient Web-Agent Trajectory Evaluation under Frozen Held-Out Testing",
    "Evidence, Efficiency, and Limits of Structural Web-Agent Trajectory Evaluation",
    "Dimension-Aware Lightweight Evaluation of Web-Agent Trajectories under Benchmark Shift",
)


class IntegrityError(RuntimeError):
    """Raised when a frozen input or output contract is violated."""


def resolve_root(relative: str) -> Path:
    """Resolve a repository-relative input path without permitting escape."""

    candidate = Path(relative)
    if candidate.is_absolute():
        raise IntegrityError(f"absolute path prohibited: {relative}")
    resolved = (ROOT / candidate).resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise IntegrityError(f"path escapes repository: {relative}")
    return resolved


def resolve_output(output_root: Path, relative: str) -> Path:
    """Resolve an output path under the selected output root."""

    candidate = Path(relative)
    if candidate.is_absolute():
        raise IntegrityError(f"absolute output path prohibited: {relative}")
    root = output_root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise IntegrityError(f"output path escapes root: {relative}")
    return resolved


def sha256_path(path: Path) -> str:
    """Return the SHA-256 digest for one file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(relative: str) -> list[dict[str, str]]:
    """Read one frozen UTF-8 CSV artifact."""

    with resolve_root(relative).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_output_csv(output_root: Path, relative: str) -> list[dict[str, str]]:
    """Read one generated UTF-8 CSV artifact."""

    with resolve_output(output_root, relative).open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def read_json(relative: str) -> Any:
    """Read one frozen JSON artifact."""

    return json.loads(resolve_root(relative).read_text(encoding="utf-8"))


def atomic_csv(
    output_root: Path,
    relative: str,
    fields: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    """Write an LF-only deterministic CSV atomically."""

    path = resolve_output(output_root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def atomic_text(output_root: Path, relative: str, value: str) -> None:
    """Write deterministic UTF-8/LF text atomically."""

    path = resolve_output(output_root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def atomic_json(output_root: Path, relative: str, value: Any) -> None:
    """Write deterministic sorted JSON atomically."""

    atomic_text(
        output_root,
        relative,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
    )


def git_output(*arguments: str) -> str:
    """Run a read-only Git query."""

    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    """Raise an integrity error on exact inequality."""

    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, found {actual!r}")


def one(rows: Sequence[Mapping[str, str]], **criteria: str) -> Mapping[str, str]:
    """Return exactly one row matching all criteria."""

    matches = [
        row
        for row in rows
        if all(str(row.get(key, "")) == value for key, value in criteria.items())
    ]
    if len(matches) != 1:
        raise IntegrityError(f"expected one row for {criteria}, found {len(matches)}")
    return matches[0]


def verify_preflight(require_clean: bool) -> dict[str, Any]:
    """Verify the mandatory A2.3 frozen-input and claim gates."""

    if require_clean:
        assert_equal(git_output("status", "--porcelain"), "", "Git start status")

    hashes: dict[str, str] = {}
    for name, (path_text, expected_hash) in INPUTS.items():
        actual_hash = sha256_path(resolve_root(path_text))
        assert_equal(actual_hash, expected_hash, f"{name} SHA-256")
        hashes[path_text] = actual_hash

    head = git_output("rev-parse", "HEAD")
    for commit in (PREREG_COMMIT, A2_1_RESULT_COMMIT, A2_2_RESULT_COMMIT):
        git_output("cat-file", "-e", f"{commit}^{{commit}}")
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, head], cwd=ROOT
        )
        if completed.returncode != 0:
            raise IntegrityError(f"required commit is not an ancestor of HEAD: {commit}")

    claims = read_csv(INPUTS["claim_matrix"][0])
    frozen = {
        "FC1": ("Success", "CONFIRMATORY_SUPPORTED"),
        "FC2": ("Looping", "CONFIRMATORY_SUPPORTED"),
        "FE1": ("Side Effect", "EXPLORATORY_SUPPORTED"),
    }
    for claim_id, (target, status) in frozen.items():
        row = one(claims, claim_id=claim_id)
        assert_equal(row["target"], target, f"{claim_id} target")
        assert_equal(row["status"], status, f"{claim_id} status")

    return {
        "head": head,
        "hashes": hashes,
        "commits": {
            "a2_3_prereg": PREREG_COMMIT,
            "a2_1_result": A2_1_RESULT_COMMIT,
            "a2_2_result": A2_2_RESULT_COMMIT,
        },
        "frozen_claims": {
            claim_id: status for claim_id, (_, status) in frozen.items()
        },
    }


def baseline_rows() -> list[dict[str, str]]:
    """Construct the frozen baseline hierarchy without performance inference."""

    registry = read_json(INPUTS["baseline_registry"][0])
    registered = {row["id"]: row for row in registry["baselines"]}
    assert_equal(set(registered), {"B0", "B1", "B2", "B3"}, "baseline registry IDs")

    feature_rows = read_csv(INPUTS["feature_registry"][0])
    variants: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in feature_rows:
        variants[row["variant_id"]].append(row)
    expected_variants = {
        "S0_full13",
        "S1_no_termination",
        "S2_no_repetition",
        "S3_no_activity_volume",
        "S4_no_error",
        "S5_no_termination_or_repetition",
        "S6_termination_repetition_only",
    }
    assert_equal(set(variants), expected_variants, "structural variant IDs")

    rows: list[dict[str, str]] = []

    def add(**values: str) -> None:
        row = {field: "" for field in BASELINE_FIELDS}
        row.update(values)
        rows.append(row)

    add(
        method_id="B0",
        method_name=registered["B0"]["name"],
        tier="Tier 0 — trivial / minimal control",
        representation_type="constant most-frequent label control",
        feature_or_embedding_dim="0",
        classifier_or_evaluator=registered["B0"]["estimator"],
        semantic_encoder="none",
        dev_evaluated="true",
        grouped_cv="true",
        lobo_evaluated="true",
        leave_one_model_out="true",
        ablation_role="minimal control",
        uncertainty_available="false",
        official_test_role="none",
        final_method_role="control only",
        target_scope="Success;Side Effect;Looping",
        evidence_status="DEV_ONLY",
        source_stage="A1.1–A1.4",
        source_artifact="configs/baseline_registry.yaml;artifacts/a1_2_pooled_metrics.csv;artifacts/a1_3_lobo_pooled_metrics.csv;artifacts/a1_4_lomo_pooled_metrics.csv",
        paper_role="baseline context",
        needs_literature_verification="false",
        notes="Training-fold most-frequent DummyClassifier control.",
    )
    add(
        method_id="B1",
        method_name=registered["B1"]["name"],
        tier="Tier 0 — trivial / minimal control",
        representation_type="training prevalence probability control",
        feature_or_embedding_dim="0",
        classifier_or_evaluator=registered["B1"]["estimator"],
        semantic_encoder="none",
        dev_evaluated="true",
        grouped_cv="true",
        lobo_evaluated="true",
        leave_one_model_out="true",
        ablation_role="minimal probabilistic control",
        uncertainty_available="false",
        official_test_role="none",
        final_method_role="control only",
        target_scope="Success;Side Effect;Looping",
        evidence_status="DEV_ONLY",
        source_stage="A1.1–A1.4",
        source_artifact="configs/baseline_registry.yaml;artifacts/a1_2_pooled_metrics.csv;artifacts/a1_3_lobo_pooled_metrics.csv;artifacts/a1_4_lomo_pooled_metrics.csv",
        paper_role="baseline context",
        needs_literature_verification="false",
        notes="Training-prior DummyClassifier control.",
    )
    add(
        method_id="B2",
        method_name="leak_safe_structural_logistic_regression",
        tier="Tier 1 — lightweight structural",
        representation_type="task-agnostic structural trajectory features",
        feature_or_embedding_dim="13",
        classifier_or_evaluator="standardized LogisticRegression",
        semantic_encoder="none",
        dev_evaluated="true",
        grouped_cv="true",
        lobo_evaluated="true",
        leave_one_model_out="true",
        ablation_role="full structural baseline",
        uncertainty_available="true",
        official_test_role="Success and Looping confirmatory",
        final_method_role="FINAL_SUCCESS_B2;FINAL_LOOPING_B2",
        target_scope="Success;Side Effect;Looping",
        evidence_status="CONFIRMATORY_SUPPORTED_FOR_SUCCESS_AND_LOOPING",
        source_stage="A1.1–A1.11",
        source_artifact="configs/stage_a1_2_execution.yaml;artifacts/a1_11_table_main_test_results.csv",
        paper_role="primary lightweight method",
        needs_literature_verification="false",
        notes="Thirteen frozen structural features; target-specific frozen LR models.",
    )
    add(
        method_id="B3",
        method_name=registered["B3"]["name"],
        tier="Tier 2 — alternative lightweight / text",
        representation_type="TF-IDF word unigram or unigram-bigram text",
        feature_or_embedding_dim="up to 20000",
        classifier_or_evaluator="TfidfVectorizer + LogisticRegression",
        semantic_encoder="none",
        dev_evaluated="true",
        grouped_cv="true",
        lobo_evaluated="true",
        leave_one_model_out="true",
        ablation_role="alternative sparse text representation",
        uncertainty_available="true",
        official_test_role="none",
        final_method_role="not selected",
        target_scope="Success;Side Effect;Looping",
        evidence_status="DEV_ONLY",
        source_stage="A1.1–A1.6",
        source_artifact="configs/baseline_registry.yaml;artifacts/a1_6_primary_paired_delta_summary.csv",
        paper_role="sparse text comparator",
        needs_literature_verification="false",
        notes="Vocabulary and classifier selection remained inside training/validation data.",
    )
    add(
        method_id="B4",
        method_name="B4_dense_embedding_lr",
        tier="Tier 3 — dense semantic",
        representation_type="frozen dense trajectory embedding",
        feature_or_embedding_dim="1024",
        classifier_or_evaluator="LogisticRegression",
        semantic_encoder="Qwen/Qwen3-Embedding-0.6B@97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
        dev_evaluated="true",
        grouped_cv="true",
        lobo_evaluated="true",
        leave_one_model_out="false",
        ablation_role="dense semantic complexity control",
        uncertainty_available="true",
        official_test_role="Side Effect exploratory",
        final_method_role="FINAL_SIDE_EFFECT_B4",
        target_scope="Success;Side Effect;Looping",
        evidence_status="DEV_ONLY;EXPLORATORY_SUPPORTED_FOR_SIDE_EFFECT",
        source_stage="A1.7–A1.11",
        source_artifact="configs/stage_a1_7_dense_semantic.yaml;artifacts/a1_7_bootstrap_primary_summary.csv;artifacts/a1_11_table_main_test_results.csv",
        paper_role="dense semantic comparator",
        needs_literature_verification="false",
        notes="Frozen encoder, no fine-tuning, one shared benchmark-blind embedding matrix.",
    )

    ablation_roles = {
        "S0_full13": "reference",
        "S1_no_termination": "remove G3 termination",
        "S2_no_repetition": "remove G4 repetition",
        "S3_no_activity_volume": "remove G1 activity/volume",
        "S4_no_error": "remove G2 error",
        "S5_no_termination_or_repetition": "remove G3 and G4",
        "S6_termination_repetition_only": "sufficiency-only restricted representation",
    }
    uncertainty = {
        "S0_full13": "partial_registered_comparisons",
        "S2_no_repetition": "partial_registered_comparisons",
        "S6_termination_repetition_only": "partial_registered_comparisons",
    }
    for variant_id in sorted(variants, key=lambda value: int(value[1])):
        included = [row for row in variants[variant_id] if row["included"] == "True"]
        groups = sorted({row["feature_group"] for row in included})
        add(
            method_id=variant_id.split("_", 1)[0],
            method_name=variant_id,
            tier="Tier 1 — lightweight structural",
            representation_type="structural feature-group ablation",
            feature_or_embedding_dim=str(len(included)),
            classifier_or_evaluator="standardized LogisticRegression",
            semantic_encoder="none",
            dev_evaluated="true",
            grouped_cv="true",
            lobo_evaluated="true",
            leave_one_model_out="false",
            ablation_role=ablation_roles[variant_id],
            uncertainty_available=uncertainty.get(variant_id, "false"),
            official_test_role="none",
            final_method_role="not selected",
            target_scope="Success;Side Effect;Looping",
            evidence_status="DEV_ONLY",
            source_stage="A1.5–A1.6",
            source_artifact="artifacts/a1_5_feature_group_registry.csv;artifacts/a1_5_structural_ablation_deltas.csv;artifacts/a1_6_primary_paired_delta_summary.csv",
            paper_role="structural interpretation / ablation",
            needs_literature_verification="false",
            notes=f"Included frozen groups: {';'.join(groups)}.",
        )

    for method_id, name, citation in (
        ("T4_WEB_SHEPHERD", "Web-Shepherd", "https://arxiv.org/abs/2505.15277"),
        ("T4_AGENT_REWARDBENCH", "Agent-RewardBench", "https://aclanthology.org/2025.acl-long.857/"),
        ("T4_AGENTRM", "AgentRM", "https://aclanthology.org/2025.acl-long.945/"),
    ):
        add(
            method_id=method_id,
            method_name=name,
            tier="Tier 4 — published external evaluator context",
            representation_type="not locally verified",
            feature_or_embedding_dim="NA",
            classifier_or_evaluator="not locally verified",
            semantic_encoder="not locally verified",
            dev_evaluated="false",
            grouped_cv="false",
            lobo_evaluated="false",
            leave_one_model_out="false",
            ablation_role="literature context only",
            uncertainty_available="not locally verified",
            official_test_role="none; not head-to-head",
            final_method_role="none",
            target_scope="not locally verified",
            evidence_status="NEEDS_LITERATURE_VERIFICATION",
            source_stage="Research charter reference entry",
            source_artifact="research/00_RESEARCH_CHARTER.md",
            paper_role="discussion-only literature context",
            needs_literature_verification="true",
            notes=f"Citation entry only ({citation}); no method definition or performance number is asserted.",
        )
    return rows


def table_1_rows() -> list[dict[str, str]]:
    """Exact-map the frozen A1.11 held-out result rows."""

    source = read_csv(INPUTS["main_test_table"][0])
    claims = read_csv(INPUTS["claim_matrix"][0])
    claim_ids = {"Success": "FC1", "Looping": "FC2", "Side Effect": "FE1"}
    output: list[dict[str, str]] = []
    for row in source:
        claim = one(claims, claim_id=claim_ids[row["Target"]])
        output.append(
            {
                "target": row["Target"],
                "final_method": row["Final Method"],
                "eligible_n": row["Eligible"],
                "positive_n": row["Positive"],
                "negative_n": row["Negative"],
                "prevalence": row["Prevalence"],
                "AP": row["AP"],
                "AP_lift": row["AP Lift"],
                "F1": row["F1"],
                "AP_lift_CI_low": row["AP-lift 95% CI Lower"],
                "AP_lift_CI_high": row["AP-lift 95% CI Upper"],
                "claim_status": claim["status"],
                "scope": claim["scope"],
            }
        )
    return output


def table_2_rows() -> list[dict[str, str]]:
    """Exact-map A2.1 efficiency strings without joining scientific accuracy."""

    source = read_csv(INPUTS["efficiency_summary"][0])
    relative = one(read_csv(INPUTS["efficiency_relative"][0]))
    ratio_text = ";".join(
        f"{key}={relative[key]}"
        for key in (
            "dimension_ratio_B4_over_B2",
            "representation_size_ratio_B4_over_B2",
            "extraction_time_ratio_B4_over_B2",
            "classifier_inference_ratio_B4_over_B2",
            "peak_memory_ratio_B4_over_B2",
        )
    )
    output: list[dict[str, str]] = []
    for row in source:
        output.append(
            {
                "method": row["method"],
                "representation": row["representation"],
                "dimension": row["dimension"],
                "device": row["device"],
                "cold_start_seconds": row["cold_start_seconds"],
                "extraction_ms_per_trajectory": row[
                    "median_extraction_ms_per_trajectory"
                ],
                "inference_ms_per_trajectory": row[
                    "median_inference_ms_per_trajectory"
                ],
                "representation_size_bytes": row["representation_size_bytes"],
                "classifier_size_bytes": row["classifier_artifact_size_bytes"],
                "encoder_size_bytes": row["semantic_encoder_size_bytes"],
                "peak_cpu_rss_mb": row["peak_cpu_rss_mb"],
                "peak_gpu_vram_mb": row["peak_gpu_vram_mb"],
                "relative_cost": "B2 reference" if row["method"] == "B2" else ratio_text,
                "environment_specific": "true",
                "evidence_status": row["evidence_status"],
                "source_artifacts": "artifacts/a2_1_efficiency_summary.csv;artifacts/a2_1_efficiency_relative_cost.csv",
            }
        )
    return output


def representation_for_evidence(evidence_id: str) -> str:
    """Map a frozen evidence identifier to a display-only representation label."""

    for token, label in (
        ("B4", "dense semantic embedding"),
        ("B3", "TF-IDF sparse text"),
        ("B2", "full structural"),
        ("S2", "structural without repetition group"),
        ("S6", "termination + repetition structural subset"),
        ("P1", "full structural positive-signal uncertainty"),
        ("P2", "B2 versus B3 uncertainty"),
        ("P5", "full structural positive-signal uncertainty"),
        ("P6", "repetition-group ablation uncertainty"),
        ("Q1", "dense semantic positive-signal uncertainty"),
        ("Q4", "dense semantic support diagnostic"),
        ("Q5", "dense semantic versus structural uncertainty"),
    ):
        if token in evidence_id:
            return label
    return "frozen dev evidence"


def table_3_rows() -> list[dict[str, str]]:
    """Normalize only frozen A1.2–A1.7 dev evidence rows."""

    allowed_stages = {"A1.2", "A1.3", "A1.4", "A1.5", "A1.6", "A1.7"}
    output: list[dict[str, str]] = []
    for row in read_csv(INPUTS["dev_evidence"][0]):
        if row["Stage"] not in allowed_stages:
            continue
        output.append(
            {
                "stage": row["Stage"],
                "target": row["Target"],
                "method_or_comparison": row["Method or Comparison"],
                "representation": representation_for_evidence(
                    row["Method or Comparison"]
                ),
                "evidence_area": row["Evidence Area"],
                "metric": row["Metric"],
                "point_estimate": row["Point Estimate"],
                "CI_low_95": row["95% CI Lower"],
                "CI_high_95": row["95% CI Upper"],
                "stage_determination": row["Stage Determination"],
                "evidence_status": row["Support Level"].upper(),
                "claim_boundary": row["Claim Boundary"],
                "source_artifact": row["Source Artifact"],
                "source_commit": row["Source Commit"],
            }
        )
    return output


def table_4_rows() -> list[dict[str, str]]:
    """Exact-map the frozen A1.11 benchmark rows as descriptive only."""

    return [
        {
            "target": row["Target"],
            "benchmark": row["Benchmark"],
            "AP": row["AP"],
            "F1": row["F1"],
            "role": row["Role"],
            "evidence_status": row["Interpretation"],
            "source_artifact": "artifacts/a1_11_table_benchmark_results.csv",
        }
        for row in read_csv(INPUTS["benchmark_table"][0])
    ]


def table_5_rows() -> list[dict[str, str]]:
    """Consolidate frozen A2.2 diagnostic artifacts without causal promotion."""

    coefficients = read_csv(INPUTS["coefficients"][0])
    groups = read_csv(INPUTS["feature_evidence"][0])
    metadata = read_csv(INPUTS["metadata_summary"][0])
    notes = read_csv(INPUTS["error_notes"][0])
    output: list[dict[str, str]] = []
    for target in ("success", "looping"):
        target_coefficients = sorted(
            [row for row in coefficients if row["target"] == target],
            key=lambda row: int(row["absolute_rank"]),
        )[:5]
        top_signals = ";".join(
            f"{row['feature']}:{row['standardized_coefficient']}"
            for row in target_coefficients
        )
        target_groups = [row for row in groups if row["target"] == target]
        group_text = ";".join(
            f"{row['feature_group']}|{row['frozen_variant_or_comparison']}|delta={row['point_estimate']}|{row['uncertainty_status']}"
            for row in target_groups
        )
        target_notes = [row for row in notes if row["target"] == target]
        mode_counts = Counter(row["primary_code"] for row in target_notes)
        mode_text = ";".join(
            f"{code}:{count}" for code, count in sorted(mode_counts.items())
        )
        metadata_row = one(metadata, target=target)
        interpretation = (
            "Associations and deterministic cases delimit where task-agnostic structure tracks execution morphology but misses semantic completion; coefficients are not causal importance."
            if target == "success"
            else "Associations and deterministic cases distinguish literal action repetition from progress and semantic cycling; coefficients are not causal importance."
        )
        output.append(
            {
                "target": target,
                "top_structural_signals": top_signals,
                "feature_group_evidence": group_text,
                "metadata_AP": metadata_row["pooled_ap"],
                "metadata_AP_lift": metadata_row["ap_lift"],
                "frozen_B2_dev_AP": metadata_row["b2_frozen_dev_ap"],
                "main_failure_modes": mode_text,
                "main_interpretation": interpretation,
                "evidence_status": "DEV_ONLY;POST_FREEZE_DIAGNOSTIC;POST_FREEZE_DESCRIPTIVE",
                "source_artifacts": "artifacts/a2_2_structural_coefficients.csv;artifacts/a2_2_feature_group_evidence.csv;artifacts/a2_2_metadata_baseline_summary.csv;artifacts/a2_2_error_case_manifest.csv;artifacts/a2_2_error_case_notes.csv",
            }
        )
    return output


def evidence_map_rows() -> list[dict[str, str]]:
    """Map frozen claims and A2 diagnostics to bounded paper locations."""

    claims = read_csv(INPUTS["claim_matrix"][0])
    locations = {
        "FC1": "MAIN_TEXT",
        "FC2": "MAIN_TEXT",
        "FE1": "MAIN_TEXT",
        "FD1": "DISCUSSION_ONLY",
        "FD2": "DISCUSSION_ONLY",
        "FD3": "DO_NOT_USE",
        "FD4": "DISCUSSION_ONLY",
        "FD5": "DISCUSSION_ONLY",
        "FD6": "DO_NOT_USE",
        "FD7": "DO_NOT_USE",
        "FD8": "DO_NOT_USE",
        "FD9": "DO_NOT_USE",
        "DH1": "APPENDIX",
        "DH2": "APPENDIX",
        "DH3": "APPENDIX",
        "NS1": "DO_NOT_USE",
        "NS2": "DO_NOT_USE",
        "PO1": "DO_NOT_USE",
        "PO2": "DO_NOT_USE",
        "PO3": "DO_NOT_USE",
        "PO4": "DO_NOT_USE",
        "PO5": "DO_NOT_USE",
        "PO6": "DO_NOT_USE",
        "PO7": "DO_NOT_USE",
        "PO8": "DO_NOT_USE",
    }
    rows: list[dict[str, str]] = []
    for claim in claims:
        claim_id = claim["claim_id"]
        location = locations[claim_id]
        table_or_figure = (
            "Table 1;Figure 2"
            if claim_id in {"FC1", "FC2", "FE1"}
            else "Table 4;Figure 5"
            if claim_id.startswith("DH")
            else "Table 3;Figure 4"
            if claim_id.startswith("FD")
            else "none"
        )
        rows.append(
            {
                "evidence_id": claim_id,
                "claim_or_result": claim["claim_text"],
                "target": claim["target"],
                "source_stage": "A1.11",
                "source_artifact": "artifacts/a1_11_final_claim_matrix.csv",
                "evidence_status": claim["status"],
                "recommended_location": location,
                "recommended_table_or_figure": table_or_figure,
                "allowed_wording": claim["required_qualifier"],
                "forbidden_wording": claim["prohibited_extension"],
                "reason": (
                    "Frozen supported claim with its required qualifier."
                    if location != "DO_NOT_USE"
                    else "Frozen unsupported, dev-only overextension, or prohibited claim; retain only as a boundary."
                ),
            }
        )

    additions = [
        (
            "E_A21_EFFICIENCY",
            "B2 has substantially lower representation and extraction cost than B4 under the recorded A2.1 environment.",
            "All",
            "A2.1",
            "artifacts/a2_1_efficiency_summary.csv;artifacts/a2_1_efficiency_relative_cost.csv",
            "EFFICIENCY_BENCHMARK",
            "MAIN_TEXT",
            "Table 2;Figure 3",
            "under the recorded environment; cost comparison only",
            "universal hardware superiority or cross-target accuracy-efficiency ranking",
            "Directly answers the measured efficiency component without recomputing performance.",
        ),
        (
            "E_A22_COEF_SUCCESS",
            "Frozen standardized Success coefficients provide associational structural interpretation.",
            "Success",
            "A2.2",
            "artifacts/a2_2_structural_coefficients.csv",
            "POST_FREEZE_DIAGNOSTIC",
            "MAIN_TEXT",
            "Table 5;Figure 4",
            "association within the frozen standardized LR",
            "causal importance or mechanism",
            "Success is the primary paper-facing diagnostic target.",
        ),
        (
            "E_A22_COEF_LOOPING",
            "Frozen standardized Looping coefficients provide associational structural interpretation.",
            "Looping",
            "A2.2",
            "artifacts/a2_2_structural_coefficients.csv",
            "POST_FREEZE_DIAGNOSTIC",
            "APPENDIX",
            "Table 5;Figure 4 appendix panel",
            "association within the frozen standardized LR",
            "causal importance or mechanism",
            "Looping is strong supporting evidence but coefficient interpretation remains secondary.",
        ),
        (
            "E_A22_METADATA_SUCCESS",
            "Benchmark/model metadata contains non-trivial Success signal; frozen B2 dev AP is descriptively higher.",
            "Success",
            "A2.2",
            "artifacts/a2_2_metadata_baseline_summary.csv",
            "POST_FREEZE_DIAGNOSTIC",
            "MAIN_TEXT",
            "Table 5",
            "metadata contains non-trivial signal; B2 is descriptively higher on frozen dev",
            "metadata confounding ruled out or B2 significantly beats metadata-only",
            "Directly documents a confounding risk without a new significance claim.",
        ),
        (
            "E_A22_METADATA_LOOPING",
            "Benchmark/model metadata contains non-trivial Looping signal; frozen B2 dev AP is descriptively higher.",
            "Looping",
            "A2.2",
            "artifacts/a2_2_metadata_baseline_summary.csv",
            "POST_FREEZE_DIAGNOSTIC",
            "APPENDIX",
            "Table 5",
            "metadata contains non-trivial signal; B2 is descriptively higher on frozen dev",
            "metadata confounding ruled out or B2 significantly beats metadata-only",
            "Supporting confounder evidence retains its diagnostic status.",
        ),
        (
            "E_A22_ERROR_SUCCESS",
            "Deterministic Success errors illustrate morphology-versus-semantic completion boundaries.",
            "Success",
            "A2.2",
            "artifacts/a2_2_error_case_notes.csv",
            "POST_FREEZE_DESCRIPTIVE",
            "MAIN_TEXT",
            "Table 5;Figure 5",
            "illustrates selected failure modes",
            "prevalence estimate or exhaustive taxonomy",
            "Primary qualitative evidence for the representation boundary.",
        ),
        (
            "E_A22_ERROR_LOOPING",
            "Deterministic Looping errors illustrate literal repetition, progress, and semantic-cycle boundaries.",
            "Looping",
            "A2.2",
            "artifacts/a2_2_error_case_notes.csv",
            "POST_FREEZE_DESCRIPTIVE",
            "APPENDIX",
            "Table 5;Figure 5 appendix alternative",
            "illustrates selected failure modes",
            "prevalence estimate or exhaustive taxonomy",
            "Supporting diagnostic evidence; one case remains UNCLEAR.",
        ),
        (
            "E_TIER4_CONTEXT",
            "Published evaluator entries are retained as literature context without locally verified numbers.",
            "All",
            "Research charter reference entry",
            "research/00_RESEARCH_CHARTER.md",
            "NEEDS_LITERATURE_VERIFICATION",
            "DISCUSSION_ONLY",
            "Related Work only",
            "literature context pending human verification",
            "head-to-head superiority or invented numbers",
            "Local records contain citation entry points but not verified comparable performance values.",
        ),
    ]
    for values in additions:
        rows.append(dict(zip(EVIDENCE_MAP_FIELDS, values, strict=True)))

    limitation_texts = (
        "External validity is limited to evaluated benchmark families.",
        "Side Effect remains low-support and exploratory.",
        "Benchmark-level variation is descriptive heterogeneity only.",
        "Relative method comparisons are development-only.",
        "Ablations and coefficients do not identify causal mechanisms.",
        "Correlated structural features limit coefficient isolation.",
        "Metadata confounding is not fully ruled out.",
        "Efficiency timing is specific to the recorded environment.",
        "Structural morphology is not semantic task understanding.",
        "Calibration and deployment evidence are absent.",
    )
    for index, text in enumerate(limitation_texts, start=1):
        rows.append(
            {
                "evidence_id": f"LIM_A23_{index:02d}",
                "claim_or_result": text,
                "target": "All",
                "source_stage": "A1.11+A2.1+A2.2+A2.3",
                "source_artifact": "docs/a1_11_limitations_ledger.md;docs/a2_3_final_limitations_ledger.md",
                "evidence_status": "LIMITATION",
                "recommended_location": "LIMITATION_ONLY",
                "recommended_table_or_figure": "Limitations",
                "allowed_wording": text,
                "forbidden_wording": "removal or weakening of the frozen limitation",
                "reason": "Required limitation retained in the final ledger.",
            }
        )
    return rows


def figure_spec_text() -> str:
    """Return the frozen publication figure specification."""

    return """# A2.3 Publication Figure Specification

No final publication figure is generated in Stage A2.3. Every mark below must be produced later only from the listed frozen fields.

## Figure 1 — Study and blind-first evaluation pipeline

- Source artifacts: `artifacts/a1_11_evidence_registry.csv`, `artifacts/a1_9_run_summary.json`, `artifacts/a1_10a_run_summary.json`, `artifacts/a1_10_run_summary.json`.
- Exact fields: stage/commit/artifact provenance; frozen method and threshold records; blind-prediction hash; label-unlock sequence.
- Evidence status: `INTEGRITY_ONLY` and protocol provenance.
- Axes / labels: left-to-right stages — grouped dev evidence → method freeze → blind inference → one-time label unlock → frozen scoring → A2 diagnostics.
- Allowed caption: models, roles, thresholds, and blind prediction bytes were frozen before official-test labels/metrics were available.
- Prohibited interpretation: unseen-benchmark, arbitrary-agent, or joint task/model OOD generalization.

## Figure 2 — Official held-out AP lift and frozen 95% CI

- Source artifact: `artifacts/a2_3_table_1_main_heldout_results.csv` (exactly mapped from A1.11).
- Exact fields: `target`, `AP_lift`, `AP_lift_CI_low`, `AP_lift_CI_high`, `claim_status`, `scope`.
- Evidence status: Success and Looping `CONFIRMATORY_SUPPORTED`; Side Effect `EXPLORATORY_SUPPORTED`.
- Axes / labels: x-axis target; y-axis pooled AP lift; zero reference line; Side Effect visibly labeled exploratory.
- Allowed caption: frozen structural evaluators retain confirmatory held-out predictive signal for Success and Looping on official held-out tasks/trajectories within evaluated benchmark families; Side Effect is exploratory.
- Prohibited interpretation: Side Effect confirmation, calibration, unseen-benchmark generalization, or benchmark pairwise superiority.

## Figure 3 — Efficiency and representation complexity

- Source artifact: `artifacts/a2_3_table_2_efficiency_tradeoff.csv` (exactly mapped from A2.1).
- Exact fields: `method`, `dimension`, `device`, `extraction_ms_per_trajectory`, `inference_ms_per_trajectory`, `representation_size_bytes`, `classifier_size_bytes`, `encoder_size_bytes`, `peak_cpu_rss_mb`, `peak_gpu_vram_mb`, `environment_specific`.
- Evidence status: `EFFICIENCY_BENCHMARK`; environment-specific.
- Axes / labels: separate panels for extraction latency (log scale), representation bytes (log scale), and representation dimension; annotate CPU/GPU devices rather than merging resource domains.
- Allowed caption: B2 required substantially lower representation and extraction cost than B4 under the recorded environment.
- Prohibited interpretation: universal efficiency, cross-hardware superiority, or a cross-target accuracy–efficiency frontier.

## Figure 4 — Structural interpretation and dev uncertainty

- Source artifacts: `artifacts/a2_3_table_3_dev_representation_summary.csv`, `artifacts/a2_2_feature_group_evidence.csv`, `artifacts/a2_2_structural_coefficients.csv`.
- Exact fields: Table 3 `target`, `method_or_comparison`, `point_estimate`, `CI_low_95`, `CI_high_95`, `evidence_status`; A2.2 `feature_group`, `point_estimate`, `uncertainty_status`; coefficient `feature`, `standardized_coefficient`, `absolute_rank`.
- Evidence status: `DEV_ONLY` and `POST_FREEZE_DIAGNOSTIC`.
- Axes / labels: coefficient panel uses signed standardized coefficient; feature-group panel uses frozen delta and interval/status where available; explicitly mark missing A1.6 uncertainty.
- Allowed caption: frozen associations and ablations identify predictive structural patterns under the dev protocol; several comparisons remain uncertain.
- Prohibited interpretation: causal feature importance, equivalence, dense semantic necessity/unnecessity, or confirmatory upgrade.

## Figure 5 — Success error taxonomy

- Source artifacts: `artifacts/a2_2_error_case_manifest.csv`, `artifacts/a2_2_error_case_notes.csv`, and summary `artifacts/a2_3_table_5_interpretability_error_summary.csv`.
- Exact fields: `error_type`, `case_role`, `primary_code`, `secondary_code`, `representation_boundary`, `semantic_understanding_needed`, `evidence_status`.
- Evidence status: `POST_FREEZE_DESCRIPTIVE`.
- Axes / labels: compact taxonomy/tree or case matrix; distinguish FP/FN and borderline/median/high-confidence selection roles; do not plot category frequency as prevalence.
- Allowed caption: deterministic cases illustrate where execution morphology diverges from semantic task completion.
- Prohibited interpretation: population prevalence, exhaustive taxonomy, causal mechanism, or post-hoc model modification.

## Appendix alternative

The frozen benchmark heterogeneity table may replace Figure 5 or appear in the appendix. If plotted, use `target`, `benchmark`, `AP`, and `evidence_status` from `artifacts/a2_3_table_4_benchmark_heterogeneity.csv`; every caption and panel must say `DESCRIPTIVE_ONLY`, with no pairwise significance marks.
"""


def story_text() -> str:
    """Return the frozen publication results story."""

    titles = "\n".join(f"{index}. {title}" for index, title in enumerate(TITLE_CANDIDATES, 1))
    rqs = "\n\n".join(f"### {rq.split(':', 1)[0]}\n\n{rq.split(': ', 1)[1]}" for rq in RQ_TEXTS)
    prohibited = "\n".join(f"- {claim}" for claim in PROHIBITED_CLAIMS)
    return f"""# A2.3 Publication Results Story

This document freezes the results narrative; it is not a manuscript.

## Title candidates

{titles}

## One-sentence problem

Web-agent trajectory evaluation needs evidence beyond terminal outcomes, but it is unclear how far inexpensive task-agnostic structural signals remain predictive under grouped development and blind held-out evaluation.

## One-sentence main finding

Frozen lightweight structural evaluators retained confirmatory held-out predictive signal for Success and Looping on official held-out tasks/trajectories within the evaluated benchmark families, with substantially lower measured representation/extraction cost than the frozen dense semantic comparator under the recorded environment, while metadata diagnostics and deterministic errors expose unresolved confounding and semantic failure boundaries.

## Contributions

1. A staged, blind-first evaluation of task-agnostic structural trajectory evidence with grouped development protocols and frozen official held-out scoring.
2. Target-specific evidence showing confirmatory Success and Looping signal, while preserving Side Effect as exploratory and low-support.
3. An environment-qualified efficiency comparison between frozen 13-dimensional structural and 1,024-dimensional dense semantic representations, without cross-target performance–efficiency fabrication.
4. Post-freeze associational, metadata-confounder, and deterministic error diagnostics that delimit what morphology-only evaluation can and cannot support.

## Frozen research questions

{rqs}

## Results section order

1. **R1 — Held-out predictive evidence.** Lead with Success, then Looping, then explicitly exploratory Side Effect using Table 1 and Figure 2.
2. **R2 — Development robustness and representation evidence.** Summarize grouped, LOBO, same-task model-only transfer, ablation, and dense semantic comparisons as dev-only evidence using Table 3 and Figure 4.
3. **R3 — Efficiency.** Present the exact A2.1 cost table and environment boundaries using Table 2 and Figure 3.
4. **R4 — Interpretability, confounders, and failure boundaries.** Present associational coefficients, feature-group evidence, metadata diagnostics, and deterministic cases using Table 5 and Figure 5; place descriptive benchmark heterogeneity in Table 4/appendix.

## Main tables

- Table 1: official held-out results — main text.
- Table 2: efficiency and representation cost — main text.
- Table 3: A1.2–A1.7 dev representation/robustness evidence — condensed main text, full appendix.
- Table 4: benchmark heterogeneity — appendix, `DESCRIPTIVE_ONLY`.
- Table 5: interpretability/confounder/error summary — main text, with detailed coefficients and cases in appendix.

## Main figures

- Figure 1: study and blind-first evaluation pipeline.
- Figure 2: held-out AP lift with frozen 95% CI.
- Figure 3: efficiency and representation complexity under the recorded environment.
- Figure 4: structural interpretation and dev uncertainty.
- Figure 5: Success error taxonomy; benchmark heterogeneity is the appendix alternative.

## Allowed claims

- Success and Looping show **confirmatory held-out predictive signal** on official held-out tasks/trajectories **within evaluated benchmark families**.
- Side Effect is exploratory, low-support, and non-confirmatory.
- B2 has substantially lower representation/extraction cost than B4 under the recorded environment.
- Metadata contains non-trivial signal; frozen B2 dev AP is descriptively higher, but confounding cannot be fully excluded.
- Deterministic cases illustrate failure modes where structural morphology diverges from semantic task completion or progress.
- Development ablations and coefficients support predictive-association wording only.

## Prohibited claims

{prohibited}

## Limitations

The paper must retain all items in `docs/a2_3_final_limitations_ledger.md`, including evaluated-family external validity, Side Effect support, benchmark heterogeneity, dev-only comparisons, non-causal ablations, coefficient correlation, unresolved metadata confounding, environment-specific timing, morphology-versus-semantics, and missing calibration/deployment evidence.

## Appendix plan

- Full baseline completeness hierarchy, including Tier 4 entries marked for literature verification.
- Full A1.2–A1.7 dev evidence and uncertainty table.
- Per-benchmark descriptive table/plot with no pairwise significance language.
- Full standardized coefficient and feature-group evidence tables.
- All 12 deterministic error cases, retaining `UNCLEAR` and evidence sufficiency notes.
- Provenance and package-index hashes; frozen claim/evidence map.

## Remaining work

- Human literature verification for Tier 4 definitions and any comparable numbers before manuscript use.
- Human A2.3 review and placement decisions.
- Full manuscript writing only under a separate authorization.
- External validation only after a separately approved adapter/data/label audit; current decision is `DEFER_TO_REVISION`.
- A3 artifact freeze only after a new human stage-gate decision.
"""


def limitations_text() -> str:
    """Return the inherited and extended final limitations ledger."""

    return """# A2.3 Final Limitations Ledger

All A1.11 limitations remain active. A2.3 adds specificity but does not delete, weaken, or resolve them.

| ID | Frozen limitation | Evidence consequence | Manuscript requirement | Inheritance / source |
|---|---|---|---|---|
| L1 | External validity is limited to evaluated benchmark families. | Official held-out rows are new tasks/trajectories from existing benchmark families, not a truly independent unseen benchmark. | Do not claim unseen-benchmark generalization. | A1.11 L1 |
| L2 | Agent/model scope is limited. | A1.4 is same-task model-only transfer; official test is not joint task/model OOD. | Do not claim arbitrary-agent or joint task/model OOD robustness. | A1.11 L2 |
| L3 | Side Effect has low support. | Only 12 eligible positive dev trajectories supported the exploratory freeze. | Always label Side Effect exploratory, low-support, and non-confirmatory. | A1.11 L3 |
| L4 | Label and construct limitations remain. | Consensus exclusions, the audit-only official-primary rule, and the missing standard license identifier constrain interpretation. | State documented data-contract limitations without inventing construct facts. | A1.11 L4 |
| L5 | Prediction and ablation are not causation. | Structural associations and removal deltas do not identify mechanisms. | Use predictive-association language only. | A1.11 L5 |
| L6 | Benchmark heterogeneity is descriptive. | AP/F1 vary across evaluated families without preregistered pairwise tests. | Treat heterogeneity as an external-validity limitation; do not assert benchmark pairwise superiority. | A1.11 L6 |
| L7 | Relative method comparisons are development-only and partly uncertain. | Several B2/B3/B4 and S6/S0 intervals cross zero; one Success B4–B2 F1 contrast is a stable drop. | Do not assert a universal representation or complexity hierarchy. | A1.11 L7 |
| L8 | Calibration and deployment evidence are absent. | Calibration, selective prediction, online behavior, and deployment utility were not evaluated. | Do not present scores as calibrated risk or deployment-safety evidence. | A1.11 L8 |
| L9 | Coefficient interpretation is limited by correlated structural features. | Standardized LR coefficients can redistribute association among correlated counts and lengths. | Do not rank coefficients as isolated or causal importance. | A2.2 coefficients |
| L10 | Metadata confounding is not fully ruled out. | Benchmark/model metadata contains non-trivial dev signal; frozen B2 is only descriptively higher. | Do not say confounding is eliminated or that B2 significantly beats metadata-only. | A2.2 metadata audit |
| L11 | Efficiency timing is environment-specific. | B2 and B4 used different devices/resource domains under one recorded machine; background and hardware conditions may matter. | Qualify all timing/storage/memory claims with the recorded environment and do not universalize them. | A2.1 efficiency benchmark |
| L12 | Structural morphology is not semantic task understanding. | Short successful traces, long semantic failures, productive repetition, and semantic cycles expose representation boundaries. | Present deterministic errors as illustrations, not prevalence estimates or proof that semantics are unnecessary. | A2.2 deterministic error analysis |

Changing or removing any item requires a newly approved stage.
"""


def external_decision_text() -> str:
    """Return the decision-only external-validation assessment."""

    return """# A2.3 External Validation Decision

## Decision

`DEFER_TO_REVISION`

## Rationale

An independent public dataset could materially address the strongest remaining external-validity criticism, but the current local record does not yet verify compatible Success labels, trajectory availability, immutable revision/license terms, or direct reuse of the frozen 13-feature extractor. Establishing those facts requires a new data-contract and adapter stage. The current A1/A2 evidence already supports a bounded submission story, so performing that work now would create material schedule and scope risk.

## Decision factors

| Factor | Current assessment |
|---|---|
| Label compatibility | Not yet verified; a new explicit mapping audit is required. |
| Trajectory availability | Candidate literature entry points exist, but usable trajectory fields are not locally verified. |
| Extractor reuse | Plausible but unverified; no claim of zero-adapter reuse. |
| Adapter cost | Potentially material because field semantics and termination/error structure must be audited. |
| Scientific value | High for independent-dataset external validity if a compatible source is found. |
| Submission delay | Likely non-trivial relative to the already complete bounded evidence story. |
| Scope gain | Would test transfer to another dataset/annotation policy; it would not automatically establish universal generalization. |

## Publication value

The primary value is a direct response to reviewer concern that all current evidence comes from one dataset and its evaluated benchmark families. A clean compatible validation could strengthen external validity in a revision.

## Implementation cost

A new stage would need source/revision/license freezing, label-contract audit, trajectory-schema audit, leakage review, extractor compatibility tests, a frozen adapter if necessary, and a preregistered evaluation protocol. None is authorized or executed in A2.3.

## Scientific risks

- Incompatible label semantics could make the result uninterpretable.
- Missing or transformed trajectories could prevent faithful 13-feature extraction.
- Adapter choices could inadvertently change the frozen method.
- A rushed validation could encourage test-driven mapping or unsupported cross-paper comparisons.

## Reviewer criticism addressed

If executed cleanly, it would address the criticism that current held-out evidence is confined to AgentRewardBench and its covered benchmark families.

## What it would NOT prove

It would not by itself prove arbitrary unseen-benchmark generalization, arbitrary-agent generalization, joint task/model OOD robustness, universal Agent Judge validity, universal replacement of LLM judges, calibration, deployment safety, or causal mechanisms.

## Revisit trigger

Revisit after submission or reviewer request if a public source has: a fixed revision/license, accessible trajectories, a highly compatible Success label, direct or lightweight-adapter compatibility with the frozen extractor, and a separately approved preregistration that forbids method changes and tuning.

No external dataset was downloaded, adapted, or evaluated in A2.3.
"""


def parse_inherited_limitations() -> list[str]:
    """Extract the eight frozen A1.11 limitation IDs for inheritance checks."""

    text = resolve_root(INPUTS["a1_11_limitations"][0]).read_text(encoding="utf-8")
    return [line.split("|", 2)[1].strip() for line in text.splitlines() if line.startswith("| L")]


def package_index_rows(output_root: Path) -> list[dict[str, str]]:
    """Build a verified hash index for source and generated paper artifacts."""

    entries = [
        ("artifacts/a1_11_final_claim_matrix.csv", "A1.11", "frozen claim contract", "MIXED_FROZEN_STATUS", "claims / limitations"),
        ("artifacts/a1_11_table_main_test_results.csv", "A1.11", "official held-out source", "CONFIRMATORY_AND_EXPLORATORY", "Table 1 / Figure 2"),
        ("artifacts/a1_11_table_benchmark_results.csv", "A1.11", "benchmark heterogeneity source", "DESCRIPTIVE_ONLY", "Table 4 / appendix"),
        ("artifacts/a1_11_dev_evidence_summary.csv", "A1.11", "dev evidence source", "DEV_ONLY", "Table 3 / Figure 4"),
        ("artifacts/a2_1_efficiency_summary.csv", "A2.1", "efficiency source", "EFFICIENCY_BENCHMARK", "Table 2 / Figure 3"),
        ("artifacts/a2_1_efficiency_relative_cost.csv", "A2.1", "relative-cost source", "EFFICIENCY_BENCHMARK", "Table 2 / Figure 3"),
        ("artifacts/a2_2_structural_coefficients.csv", "A2.2", "coefficient source", "POST_FREEZE_DIAGNOSTIC", "Table 5 / Figure 4"),
        ("artifacts/a2_2_feature_group_evidence.csv", "A2.2", "feature-group source", "DEV_ONLY", "Table 5 / Figure 4"),
        ("artifacts/a2_2_metadata_baseline_summary.csv", "A2.2", "metadata source", "POST_FREEZE_DIAGNOSTIC", "Table 5"),
        ("artifacts/a2_2_error_case_notes.csv", "A2.2", "error-analysis source", "POST_FREEZE_DESCRIPTIVE", "Table 5 / Figure 5"),
        ("artifacts/a2_3_implementation_failures.json", "A2.3", "implementation-failure provenance", "INTEGRITY_ONLY", "provenance"),
        (OUTPUTS["baseline_matrix"], "A2.3", "baseline hierarchy", "MIXED_FROZEN_STATUS", "appendix / methods context"),
        (OUTPUTS["evidence_map"], "A2.3", "evidence placement contract", "MIXED_FROZEN_STATUS", "writing control"),
        (OUTPUTS["table_1"], "A2.3", "paper-ready held-out table", "CONFIRMATORY_AND_EXPLORATORY", "main text"),
        (OUTPUTS["table_2"], "A2.3", "paper-ready efficiency table", "EFFICIENCY_BENCHMARK", "main text"),
        (OUTPUTS["table_3"], "A2.3", "paper-ready dev evidence table", "DEV_ONLY", "main text / appendix"),
        (OUTPUTS["table_4"], "A2.3", "paper-ready heterogeneity table", "DESCRIPTIVE_ONLY", "appendix"),
        (OUTPUTS["table_5"], "A2.3", "paper-ready diagnostic table", "POST_FREEZE_DIAGNOSTIC_AND_DESCRIPTIVE", "main text / appendix"),
        (OUTPUTS["story"], "A2.3", "publication story freeze", "CLAIM_BOUNDED", "writing plan"),
        (OUTPUTS["figure_spec"], "A2.3", "figure specification", "CLAIM_BOUNDED", "figure plan"),
        (OUTPUTS["limitations"], "A2.3", "final limitations ledger", "LIMITATION", "limitations"),
        (OUTPUTS["external_decision"], "A2.3", "external-validation decision", "DECISION_ONLY", "remaining work"),
    ]
    output_paths = set(OUTPUTS.values())
    rows: list[dict[str, str]] = []
    for artifact, stage, role, status, location in entries:
        path = (
            resolve_output(output_root, artifact)
            if artifact in output_paths
            else resolve_root(artifact)
        )
        rows.append(
            {
                "artifact": artifact,
                "source_stage": stage,
                "role": role,
                "evidence_status": status,
                "paper_location": location,
                "sha256": sha256_path(path),
                "verified": "true",
            }
        )
    return rows


def report_text(summary: Mapping[str, Any]) -> str:
    """Render the concise Stage A2.3 decision report."""

    evidence_counts = summary["evidence_location_counts"]
    table_hashes = summary["table_hashes"]
    counter_lines = "\n".join(f"{key} = {value}" for key, value in COUNTERS.items())
    title_lines = "\n".join(f"- {title}" for title in TITLE_CANDIDATES)
    rq_lines = "\n".join(f"- {rq}" for rq in RQ_TEXTS)
    return f"""# Stage A2.3 Baseline Completeness and Paper Package Report

## Stage determination

`PASS_WITH_CONDITIONS`

Conditions: all three Tier 4 literature-context entries require human verification before manuscript use, and external validation is `DEFER_TO_REVISION`. No scientific inconsistency is present.

## Provenance gates

- A2.3 prereg commit: `{PREREG_COMMIT}`
- A2.1 result commit: `{A2_1_RESULT_COMMIT}` (verified reachable)
- A2.2 result commit: `{A2_2_RESULT_COMMIT}` (verified reachable)
- Implementation commit: `{summary['input_commits']['implementation']}`
- Result commit: `{RESULT_COMMIT_SENTINEL}`
- Fix commits: `{';'.join(summary['input_commits']['fix_commits']) or 'none'}`
- Amend: none
- A1.11 claim matrix SHA-256: `{INPUTS['claim_matrix'][1]}` (verified)
- A1.11 main test table SHA-256: `{INPUTS['main_test_table'][1]}` (verified)
- Frozen claims: FC1/FC2 `CONFIRMATORY_SUPPORTED`; FE1 `EXPLORATORY_SUPPORTED`.

## Baseline completeness

- Total rows: {summary['baseline_count']} ({summary['local_baseline_count']} frozen local methods/variants + {summary['tier4_count']} literature-context entries).
- Tier 0: B0, B1.
- Tier 1: B2 and S0–S6.
- Tier 2: B3.
- Tier 3: B4.
- Tier 4: Web-Shepherd, Agent-RewardBench, AgentRM — all `NEEDS_LITERATURE_VERIFICATION`; no performance number or head-to-head claim was added.

## Paper tables

- Table 1 SHA-256: `{table_hashes['table_1']}`; exact A1.11 held-out mapping.
- Table 2 SHA-256: `{table_hashes['table_2']}`; exact A2.1 efficiency mapping with no cross-target performance join.
- Table 3 SHA-256: `{table_hashes['table_3']}`; {summary['table_rows']['table_3']} A1.2–A1.7 frozen dev-evidence rows.
- Table 4 SHA-256: `{table_hashes['table_4']}`; all rows `DESCRIPTIVE_ONLY`.
- Table 5 SHA-256: `{table_hashes['table_5']}`; A2.2 associations, metadata, and deterministic failures only.

## Evidence placement counts

- MAIN_TEXT: {evidence_counts.get('MAIN_TEXT', 0)}
- APPENDIX: {evidence_counts.get('APPENDIX', 0)}
- DISCUSSION_ONLY: {evidence_counts.get('DISCUSSION_ONLY', 0)}
- LIMITATION_ONLY: {evidence_counts.get('LIMITATION_ONLY', 0)}
- DO_NOT_USE: {evidence_counts.get('DO_NOT_USE', 0)}

Frozen claim-status counts: `{json.dumps(summary['claim_status_counts'], sort_keys=True)}`.

## Frozen title candidates

{title_lines}

## Problem and main finding

- Problem: Web-agent trajectory evaluation needs evidence beyond terminal outcomes, but it is unclear how far inexpensive task-agnostic structural signals remain predictive under grouped development and blind held-out evaluation.
- Finding: Frozen lightweight structural evaluators retained confirmatory held-out predictive signal for Success and Looping on official held-out tasks/trajectories within the evaluated benchmark families, with substantially lower measured representation/extraction cost than B4 under the recorded environment, while diagnostics expose unresolved confounding and semantic failure boundaries.

## Contributions

1. Blind-first grouped and held-out evaluation of lightweight structural evidence.
2. Confirmatory Success/Looping evidence with exploratory-only Side Effect retained.
3. Environment-qualified representation/extraction efficiency evidence.
4. Associational, confounder, and deterministic error boundaries without causal promotion.

## RQ1–RQ6

{rq_lines}

## Main figure plan

1. Study and blind-first evaluation pipeline.
2. Official held-out AP lift with frozen 95% CI.
3. Efficiency and representation complexity.
4. Structural interpretation and dev uncertainty.
5. Success error taxonomy; benchmark heterogeneity is the appendix alternative.

## External validation

- Decision: `DEFER_TO_REVISION`.
- Rationale: potential external-validity value is high, but compatible labels, accessible trajectories, immutable source terms, and extractor/adapter reuse require a new audited stage and would materially delay the current bounded submission package.
- No external dataset was accessed or executed.

## Limitations

- Final ledger count: {summary['limitations_count']}.
- All eight A1.11 limitations are retained; A2.3 adds coefficient-correlation, metadata-confounding, environment-specific timing, and morphology-versus-semantics boundaries.

## Scientific operation counters

```text
{counter_lines}
```

## Verification

- Frozen SHA/commit/claim gates passed.
- Table 1 exact mapping passed.
- Table 2 A2.1 exact mapping passed.
- Table 4 exact benchmark mapping passed.
- A2.2 metadata strings and deterministic error counts passed.
- Package-index hashes passed.
- Output summary consistency passed.
- Side Effect remains exploratory; benchmark heterogeneity remains descriptive.
- Static forbidden-operation AST guards are provided in `tests/test_stage_a2_3_publication_package.py`.

## Warnings

- Tier 4 definitions and any comparable numbers require human literature verification.
- External validation is deferred, not executed.
- One A2.2 high-confidence Looping FN remains `UNCLEAR`.
- Several dev representation/ablation intervals remain uncertain or unavailable.
- The first A2.3 build omitted the required machine-summary `claim_status_counts` field; all outputs from that invocation were invalidated and rebuilt after an independent fix commit.

`WAIT_FOR_HUMAN_A2_3_REVIEW`
"""


def build_package(output_root: Path, require_clean: bool = True) -> dict[str, Any]:
    """Build all A2.3 outputs under ``output_root`` and return the summary."""

    preflight = verify_preflight(require_clean=require_clean)
    inherited = parse_inherited_limitations()
    assert_equal(inherited, [f"L{index}" for index in range(1, 9)], "A1.11 limitation IDs")

    baselines = baseline_rows()
    evidence = evidence_map_rows()
    tables = {
        "table_1": table_1_rows(),
        "table_2": table_2_rows(),
        "table_3": table_3_rows(),
        "table_4": table_4_rows(),
        "table_5": table_5_rows(),
    }

    atomic_csv(output_root, OUTPUTS["baseline_matrix"], BASELINE_FIELDS, baselines)
    atomic_csv(output_root, OUTPUTS["evidence_map"], EVIDENCE_MAP_FIELDS, evidence)
    atomic_csv(output_root, OUTPUTS["table_1"], TABLE_1_FIELDS, tables["table_1"])
    atomic_csv(output_root, OUTPUTS["table_2"], TABLE_2_FIELDS, tables["table_2"])
    atomic_csv(output_root, OUTPUTS["table_3"], TABLE_3_FIELDS, tables["table_3"])
    atomic_csv(output_root, OUTPUTS["table_4"], TABLE_4_FIELDS, tables["table_4"])
    atomic_csv(output_root, OUTPUTS["table_5"], TABLE_5_FIELDS, tables["table_5"])
    atomic_text(output_root, OUTPUTS["figure_spec"], figure_spec_text())
    atomic_text(output_root, OUTPUTS["story"], story_text())
    atomic_text(output_root, OUTPUTS["limitations"], limitations_text())
    atomic_text(output_root, OUTPUTS["external_decision"], external_decision_text())

    index_rows = package_index_rows(output_root)
    atomic_csv(output_root, OUTPUTS["package_index"], INDEX_FIELDS, index_rows)

    location_counts = Counter(row["recommended_location"] for row in evidence)
    claim_status_counts = Counter(
        row["status"] for row in read_csv(INPUTS["claim_matrix"][0])
    )
    table_hashes = {
        key: sha256_path(resolve_output(output_root, OUTPUTS[key]))
        for key in ("table_1", "table_2", "table_3", "table_4", "table_5")
    }
    generated_before_summary = (
        "baseline_matrix",
        "evidence_map",
        "table_1",
        "table_2",
        "table_3",
        "table_4",
        "table_5",
        "figure_spec",
        "story",
        "limitations",
        "external_decision",
        "package_index",
    )
    output_hashes = {
        OUTPUTS[key]: sha256_path(resolve_output(output_root, OUTPUTS[key]))
        for key in generated_before_summary
    }
    summary: dict[str, Any] = {
        "stage": "A2.3",
        "stage_determination": "PASS_WITH_CONDITIONS",
        "conditions": [
            "Tier 4 literature context needs human verification before manuscript use.",
            "External validation decision is DEFER_TO_REVISION; no experiment was executed.",
        ],
        "input_commits": {
            **preflight["commits"],
            "implementation": IMPLEMENTATION_COMMIT,
            "result": RESULT_COMMIT_SENTINEL,
            "fix_commits": (
                [] if preflight["head"] == IMPLEMENTATION_COMMIT else [preflight["head"]]
            ),
            "amend": False,
        },
        "input_hashes": preflight["hashes"],
        "output_hashes": output_hashes,
        "table_hashes": table_hashes,
        "baseline_count": len(baselines),
        "local_baseline_count": sum(
            row["needs_literature_verification"] == "false" for row in baselines
        ),
        "tier4_count": sum(
            row["needs_literature_verification"] == "true" for row in baselines
        ),
        "tier4_literature_verification": "NEEDS_LITERATURE_VERIFICATION",
        "table_count": 5,
        "table_rows": {key: len(value) for key, value in tables.items()},
        "evidence_location_counts": dict(sorted(location_counts.items())),
        "claim_status_counts": dict(sorted(claim_status_counts.items())),
        "frozen_claims": preflight["frozen_claims"],
        "external_validation_decision": "DEFER_TO_REVISION",
        "limitations_count": 12,
        "title_candidates": list(TITLE_CANDIDATES),
        "research_questions": list(RQ_TEXTS),
        "scientific_operation_counters": dict(COUNTERS),
        "warnings": [
            "Tier 4 literature definitions/numbers are not locally verified.",
            "External validation was deferred and not executed.",
            "A2.2 retains one UNCLEAR high-confidence Looping false negative.",
            "The first A2.3 build was invalidated because claim_status_counts was absent from its machine summary.",
        ],
        "inconsistencies": [],
        "next_status": "WAIT_FOR_HUMAN_A2_3_REVIEW",
    }
    atomic_json(output_root, OUTPUTS["summary"], summary)
    atomic_text(output_root, OUTPUTS["report"], report_text(summary))
    validate_outputs(output_root)
    return summary


def validate_outputs(output_root: Path) -> None:
    """Verify exact joins, statuses, counts, hashes, and narrative boundaries."""

    baselines = read_output_csv(output_root, OUTPUTS["baseline_matrix"])
    assert_equal(len(baselines), 15, "baseline row count")
    assert_equal(len({row["method_id"] for row in baselines}), 15, "baseline ID uniqueness")
    required_local = {"B0", "B1", "B2", "B3", "B4", "S0", "S1", "S2", "S3", "S4", "S5", "S6"}
    if not required_local.issubset({row["method_id"] for row in baselines}):
        raise IntegrityError("baseline matrix is missing required B0–B4 or S0–S6 rows")
    tier4 = [row for row in baselines if row["tier"].startswith("Tier 4")]
    assert_equal(len(tier4), 3, "Tier 4 row count")
    assert_equal(
        {row["needs_literature_verification"] for row in tier4},
        {"true"},
        "Tier 4 verification flags",
    )

    source_main = read_csv(INPUTS["main_test_table"][0])
    table_1 = read_output_csv(output_root, OUTPUTS["table_1"])
    assert_equal(len(table_1), 3, "Table 1 row count")
    table_1_map = {
        "target": "Target",
        "final_method": "Final Method",
        "eligible_n": "Eligible",
        "positive_n": "Positive",
        "negative_n": "Negative",
        "prevalence": "Prevalence",
        "AP": "AP",
        "AP_lift": "AP Lift",
        "F1": "F1",
        "AP_lift_CI_low": "AP-lift 95% CI Lower",
        "AP_lift_CI_high": "AP-lift 95% CI Upper",
    }
    for output_row in table_1:
        source_row = one(source_main, Target=output_row["target"])
        for output_field, source_field in table_1_map.items():
            assert_equal(
                output_row[output_field],
                source_row[source_field],
                f"Table 1 exact map {output_row['target']} {output_field}",
            )
    side_effect = one(table_1, target="Side Effect")
    assert_equal(side_effect["claim_status"], "EXPLORATORY_SUPPORTED", "Side Effect status")

    source_efficiency = read_csv(INPUTS["efficiency_summary"][0])
    table_2 = read_output_csv(output_root, OUTPUTS["table_2"])
    assert_equal(len(table_2), 2, "Table 2 row count")
    table_2_map = {
        "representation": "representation",
        "dimension": "dimension",
        "device": "device",
        "cold_start_seconds": "cold_start_seconds",
        "extraction_ms_per_trajectory": "median_extraction_ms_per_trajectory",
        "inference_ms_per_trajectory": "median_inference_ms_per_trajectory",
        "representation_size_bytes": "representation_size_bytes",
        "classifier_size_bytes": "classifier_artifact_size_bytes",
        "encoder_size_bytes": "semantic_encoder_size_bytes",
        "peak_cpu_rss_mb": "peak_cpu_rss_mb",
        "peak_gpu_vram_mb": "peak_gpu_vram_mb",
        "evidence_status": "evidence_status",
    }
    for output_row in table_2:
        source_row = one(source_efficiency, method=output_row["method"])
        for output_field, source_field in table_2_map.items():
            assert_equal(
                output_row[output_field],
                source_row[source_field],
                f"Table 2 exact map {output_row['method']} {output_field}",
            )
        assert_equal(output_row["environment_specific"], "true", "Table 2 environment flag")

    table_3 = read_output_csv(output_root, OUTPUTS["table_3"])
    assert_equal(len(table_3), 18, "Table 3 row count")
    allowed_stages = {"A1.2", "A1.3", "A1.4", "A1.5", "A1.6", "A1.7"}
    assert_equal({row["stage"] for row in table_3}, allowed_stages, "Table 3 stages")

    source_benchmark = read_csv(INPUTS["benchmark_table"][0])
    table_4 = read_output_csv(output_root, OUTPUTS["table_4"])
    assert_equal(len(table_4), 12, "Table 4 row count")
    for output_row in table_4:
        source_row = one(
            source_benchmark,
            Target=output_row["target"],
            Benchmark=output_row["benchmark"],
        )
        for output_field, source_field in (
            ("AP", "AP"),
            ("F1", "F1"),
            ("role", "Role"),
            ("evidence_status", "Interpretation"),
        ):
            assert_equal(output_row[output_field], source_row[source_field], "Table 4 exact map")
        assert_equal(output_row["evidence_status"], "DESCRIPTIVE_ONLY", "Table 4 status")

    table_5 = read_output_csv(output_root, OUTPUTS["table_5"])
    assert_equal(len(table_5), 2, "Table 5 row count")
    metadata = read_csv(INPUTS["metadata_summary"][0])
    notes = read_csv(INPUTS["error_notes"][0])
    for output_row in table_5:
        source_row = one(metadata, target=output_row["target"])
        assert_equal(output_row["metadata_AP"], source_row["pooled_ap"], "Table 5 metadata AP")
        assert_equal(output_row["metadata_AP_lift"], source_row["ap_lift"], "Table 5 metadata lift")
        assert_equal(output_row["frozen_B2_dev_AP"], source_row["b2_frozen_dev_ap"], "Table 5 B2 AP")
        assert_equal(
            len([row for row in notes if row["target"] == output_row["target"]]),
            6,
            "Table 5 deterministic error count",
        )
        if "not causal importance" not in output_row["main_interpretation"]:
            raise IntegrityError("Table 5 must explicitly reject causal coefficient importance")

    evidence = read_output_csv(output_root, OUTPUTS["evidence_map"])
    assert_equal(len({row["evidence_id"] for row in evidence}), len(evidence), "evidence ID uniqueness")
    claims = read_csv(INPUTS["claim_matrix"][0])
    for claim in claims:
        mapped = one(evidence, evidence_id=claim["claim_id"])
        assert_equal(mapped["evidence_status"], claim["status"], "claim status preservation")
    assert_equal(
        {row["recommended_location"] for row in evidence},
        {"MAIN_TEXT", "APPENDIX", "DISCUSSION_ONLY", "LIMITATION_ONLY", "DO_NOT_USE"},
        "evidence placement vocabulary",
    )

    index = read_output_csv(output_root, OUTPUTS["package_index"])
    output_paths = set(OUTPUTS.values())
    for row in index:
        path = (
            resolve_output(output_root, row["artifact"])
            if row["artifact"] in output_paths
            else resolve_root(row["artifact"])
        )
        assert_equal(sha256_path(path), row["sha256"], f"package hash {row['artifact']}")
        assert_equal(row["verified"], "true", f"package verified {row['artifact']}")

    summary_path = resolve_output(output_root, OUTPUTS["summary"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert_equal(summary["stage_determination"], "PASS_WITH_CONDITIONS", "summary determination")
    assert_equal(summary["baseline_count"], len(baselines), "summary baseline count")
    assert_equal(summary["table_count"], 5, "summary table count")
    assert_equal(summary["limitations_count"], 12, "summary limitation count")
    assert_equal(
        summary["claim_status_counts"],
        {
            "CONFIRMATORY_SUPPORTED": 2,
            "DESCRIPTIVE_ONLY": 3,
            "DEV_ONLY": 9,
            "EXPLORATORY_SUPPORTED": 1,
            "NOT_SUPPORTED": 2,
            "PROHIBITED_OVERCLAIM": 8,
        },
        "summary claim-status counts",
    )
    assert_equal(summary["scientific_operation_counters"], COUNTERS, "scientific counters")
    assert_equal(summary["inconsistencies"], [], "summary inconsistencies")
    for relative, expected_hash in summary["output_hashes"].items():
        assert_equal(
            sha256_path(resolve_output(output_root, relative)),
            expected_hash,
            f"summary output hash {relative}",
        )

    combined_text = "\n".join(
        resolve_output(output_root, OUTPUTS[key]).read_text(encoding="utf-8")
        for key in ("story", "figure_spec", "limitations", "external_decision", "report")
    )
    for claim in PROHIBITED_CLAIMS:
        if claim not in combined_text:
            raise IntegrityError(f"missing prohibited-claim boundary: {claim}")
    if "Side Effect is exploratory" not in combined_text:
        raise IntegrityError("Side Effect exploratory boundary is missing")
    assert_equal(
        "`DEFER_TO_REVISION`" in resolve_output(
            output_root, OUTPUTS["external_decision"]
        ).read_text(encoding="utf-8"),
        True,
        "external validation decision",
    )


def main() -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify existing repository outputs without writing them",
    )
    arguments = parser.parse_args()
    if arguments.verify_only:
        verify_preflight(require_clean=False)
        validate_outputs(ROOT)
        print("A2.3 verification PASS: exact joins, statuses, hashes, and zero counters")
        return 0

    summary = build_package(ROOT, require_clean=True)
    counts = summary["evidence_location_counts"]
    print(
        "A2.3 PASS_WITH_CONDITIONS | "
        f"baselines={summary['baseline_count']} tables={summary['table_count']} "
        f"evidence={sum(counts.values())} limitations={summary['limitations_count']} "
        "external=DEFER_TO_REVISION scientific_ops=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
