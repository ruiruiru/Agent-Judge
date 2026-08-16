#!/usr/bin/env python3
"""Preregister, run, and verify the Stage A1.8 evidence-only audit.

The module reads frozen A1.2-A1.7 dev artifacts and formal reports.  It does
not construct features, execute estimators, create predictions, resample data,
or inspect sealed test material.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_8_evidence_audit.yaml"
CLAIM_IDS = [f"C{i}" for i in range(1, 15)]
THREAT_IDS = [f"T{i}" for i in range(1, 11)]
STATUSES = [
    "SUPPORTED",
    "SUPPORTED_WITH_CONDITIONS",
    "DESCRIPTIVE_ONLY",
    "INSUFFICIENT_EVIDENCE",
    "PROHIBITED",
]
SUPPORT_ROLES = ["primary", "secondary", "exploratory", "diagnostic", "integrity_only"]
DECISIONS = [
    "READY_FOR_FINAL_METHOD_FREEZE",
    "ONE_BLOCKING_DEV_EXPERIMENT_REMAINS",
    "NOT_READY_RESEARCH_DIRECTION_WEAK",
]


class IntegrityError(RuntimeError):
    """Raised when a frozen source or adjudication invariant fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if path != REPO_ROOT and REPO_ROOT not in path.parents:
        raise IntegrityError(f"configured path escapes repository: {path_text}")
    return path


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
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
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = read_json(path)
    if config.get("stage") != "A1.8" or config.get("mode") != "evidence_audit_only":
        raise IntegrityError("configuration is not the frozen Stage A1.8 evidence audit")
    if [row["claim_id"] for row in config["claims"]] != CLAIM_IDS:
        raise IntegrityError("claim list is not exactly C1-C14 in order")
    if [row["threat_id"] for row in config["threats"]] != THREAT_IDS:
        raise IntegrityError("threat list is not exactly T1-T10 in order")
    if config["status_taxonomy"] != STATUSES:
        raise IntegrityError("status taxonomy changed")
    if config["support_roles"] != SUPPORT_ROLES:
        raise IntegrityError("support-role taxonomy changed")
    if config["remaining_evidence_decisions"] != DECISIONS:
        raise IntegrityError("remaining-evidence decision taxonomy changed")
    if any(value != 0 for value in config["boundaries"].values()):
        raise IntegrityError("A1.8 execution boundary contains a nonzero operation count")
    return config


def _all_source_paths(config: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for source in config["formal_sources"].values():
        paths.extend([resolve(source["summary"]), resolve(source["report"])])
        paths.extend(resolve(item) for item in source["artifacts"])
    paths.extend(resolve(item) for item in config["protocol_sources"])
    unique = {path.resolve(): path for path in paths}
    return [unique[key] for key in sorted(unique, key=lambda item: str(item))]


def _assert_no_test_source(config: dict[str, Any]) -> None:
    forbidden_exact = {
        "artifacts/test_manifest.csv",
        "data/processed/test_cleaned_trajectories.jsonl",
    }
    configured = {rel(path) for path in _all_source_paths(config)}
    overlap = configured & forbidden_exact
    if overlap:
        raise IntegrityError(f"test source configured for A1.8: {sorted(overlap)}")


def _decision(summary: dict[str, Any]) -> str:
    return str(summary.get("stage_determination") or summary.get("stage_decision") or "")


def _assert_zero_access(stage: str, summary: dict[str, Any]) -> None:
    allowed_identifier_checks = {"identifier_overlap_checks", "sealed_identifier_manifest_overlap_checks"}
    access = summary.get("test_access", {})
    nonzero = {
        key: value
        for key, value in access.items()
        if key not in allowed_identifier_checks and int(value) != 0
    }
    if nonzero:
        raise IntegrityError(f"{stage} has nonzero test access: {nonzero}")
    if summary.get("forbidden_experiments_executed", []):
        raise IntegrityError(f"{stage} recorded prohibited experiments")


def _assert_commit(commit: str) -> None:
    git_output(["cat-file", "-e", f"{commit}^{{commit}}"])


def _resolve_formal_commits(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    resolved: dict[str, dict[str, str]] = {}
    for stage, source in config["formal_sources"].items():
        commits = {
            key: value
            for key, value in source.items()
            if key.endswith("_commit")
        }
        for commit in commits.values():
            _assert_commit(commit)
        first_add = git_output(
            ["log", "--diff-filter=A", "--format=%H", "--", source["summary"]]
        ).splitlines()
        if not first_add or first_add[-1] != source["result_commit"]:
            raise IntegrityError(
                f"{stage} result commit mismatch: expected {source['result_commit']}, found {first_add}"
            )
        resolved[stage] = commits
    return resolved


def _find_row(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    matches = [row for row in rows if all(row.get(key) == value for key, value in criteria.items())]
    if len(matches) != 1:
        raise IntegrityError(f"expected one row for {criteria}, found {len(matches)}")
    return matches[0]


def _contains_table_row(report: str, prefix: str, values: Sequence[str]) -> None:
    candidates = [line for line in report.splitlines() if line.startswith(prefix)]
    if not any(all(value in line for value in values) for line in candidates):
        raise IntegrityError(f"formal report row conflict for prefix {prefix!r} and values {values!r}")


def _report_numeric_consistency(config: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, int] = {}

    a12 = read_csv(resolve("artifacts/a1_2_pooled_metrics.csv"))
    report = resolve(config["formal_sources"]["A1.2"]["report"]).read_text(encoding="utf-8")
    count = 0
    for target in config["targets"]:
        for method in ("B2", "B3"):
            row = _find_row(a12, target=target, baseline_id=method)
            _contains_table_row(
                report,
                f"| {target} | {method} |",
                [
                    f"{float(row['pooled_pr_auc_average_precision']):.6f}",
                    f"{float(row['pooled_positive_f1']):.6f}",
                    f"{float(row['ap_absolute_lift']):.6f}",
                ],
            )
            count += 3
    checks["A1.2"] = count

    a13 = read_csv(resolve("artifacts/a1_3_lobo_macro_metrics.csv"))
    report = resolve(config["formal_sources"]["A1.3"]["report"]).read_text(encoding="utf-8")
    count = 0
    for row in a13:
        _contains_table_row(
            report,
            f"| {row['target']} | {row['baseline_id']} |",
            [
                f"{float(row['pr_auc_average_precision_macro_mean']):.6f}",
                f"{float(row['positive_f1_macro_mean']):.6f}",
            ],
        )
        count += 2
    checks["A1.3"] = count

    a14 = read_csv(resolve("artifacts/a1_4_lomo_macro_metrics.csv"))
    report = resolve(config["formal_sources"]["A1.4"]["report"]).read_text(encoding="utf-8")
    count = 0
    for row in a14:
        _contains_table_row(
            report,
            f"| {row['target']} | {row['baseline_id']} |",
            [
                f"{float(row['pr_auc_average_precision_all_model_macro_mean']):.6f}",
                f"{float(row['positive_f1_all_model_macro_mean']):.6f}",
            ],
        )
        count += 2
    if "counterpart rate" not in report or "1.000000" not in report:
        raise IntegrityError("A1.4 report does not preserve the same-task counterpart limitation")
    checks["A1.4"] = count + 1

    a15_macro = read_csv(resolve("artifacts/a1_5_macro_metrics.csv"))
    a15_pooled = read_csv(resolve("artifacts/a1_5_pooled_metrics.csv"))
    report = resolve(config["formal_sources"]["A1.5"]["report"]).read_text(encoding="utf-8")
    count = 0
    for macro in a15_macro:
        pooled = _find_row(
            a15_pooled, target=macro["target"], variant_id=macro["variant_id"]
        )
        _contains_table_row(
            report,
            f"| {macro['target']} | {macro['variant_id']} |",
            [
                f"{float(macro['pr_auc_average_precision_macro_mean']):.6f}",
                f"{float(macro['positive_f1_macro_mean']):.6f}",
                f"{float(pooled['pr_auc_average_precision']):.6f}",
                f"{float(pooled['positive_f1']):.6f}",
            ],
        )
        count += 4
    checks["A1.5"] = count

    a16 = read_csv(resolve("artifacts/a1_6_primary_paired_delta_summary.csv"))
    report = resolve(config["formal_sources"]["A1.6"]["report"]).read_text(encoding="utf-8")
    count = 0
    for row in a16:
        _contains_table_row(
            report,
            f"| {row['comparison_id']} | {row['target']} |",
            [
                f"{float(row['point_estimate']):.6f}",
                f"{float(row['ci_lower_95']):.6f}",
                f"{float(row['ci_upper_95']):.6f}",
                row["bootstrap_grade"],
            ],
        )
        count += 4
    checks["A1.6"] = count

    a17_macro = read_csv(resolve("artifacts/a1_7_macro_metrics.csv"))
    report = resolve(config["formal_sources"]["A1.7"]["report"]).read_text(encoding="utf-8")
    count = 0
    for row in a17_macro:
        _contains_table_row(
            report,
            f"| {row['target']} |",
            [
                f"{float(row['pr_auc_average_precision_macro_mean']):.6f}",
                f"{float(row['positive_f1_macro_mean']):.6f}",
            ],
        )
        count += 2
    a17_boot = read_csv(resolve("artifacts/a1_7_bootstrap_primary_summary.csv"))
    for row in a17_boot:
        point = "NA" if row["point_estimate"] == "" else f"{float(row['point_estimate']):.6f}"
        lower = "NA" if row["ci_lower_95"] == "" else f"{float(row['ci_lower_95']):.6f}"
        upper = "NA" if row["ci_upper_95"] == "" else f"{float(row['ci_upper_95']):.6f}"
        _contains_table_row(
            report,
            f"| {row['comparison_id']} | {row['target']} |",
            [point, lower, upper, row["bootstrap_grade"]],
        )
        count += 4
    checks["A1.7"] = count
    return {"status": "PASS", "checked_core_values": checks, "total": sum(checks.values())}


def _a13_a15_consistency() -> dict[str, Any]:
    a13 = [
        row
        for row in read_csv(resolve("artifacts/a1_3_lobo_predictions.csv"))
        if row["baseline_id"] == "B2"
    ]
    a15 = [
        row
        for row in read_csv(resolve("artifacts/a1_5_external_predictions.csv"))
        if row["variant_id"] == "S0_full13"
    ]
    key = lambda row: (row["target"], row["held_out_group"], row["trajectory_key"])
    a13.sort(key=key)
    a15.sort(key=key)
    if len(a13) != 583 or len(a15) != 583 or [key(row) for row in a13] != [key(row) for row in a15]:
        raise IntegrityError("A1.3 B2 / A1.5 S0 prediction keys differ")
    fields = [
        "true_label",
        "predicted_probability",
        "selected_threshold",
        "predicted_label",
        "selected_config_id",
        "inner_n_splits",
    ]
    for left, right in zip(a13, a15):
        for field in fields:
            if left[field] != right[field]:
                raise IntegrityError(f"A1.3 B2 / A1.5 S0 differs at {key(left)} field {field}")
    return {"status": "PASS", "row_count": 583, "fields_exact": fields}


def _a16_regression_consistency() -> dict[str, Any]:
    summary = read_json(resolve("artifacts/a1_6_run_summary.json"))
    regression = summary["point_estimate_regression"]
    for stage in ("a1_3", "a1_5"):
        if regression[stage]["status"] != "PASS" or regression[stage]["max_absolute_error"] > 1e-12:
            raise IntegrityError(f"A1.6 point regression failed for {stage}")
    s0 = summary["s0_equals_a1_3_b2"]
    if s0["status"] != "PASS" or s0["max_probability_absolute_error"] != 0:
        raise IntegrityError("A1.6 S0/B2 regression guard failed")
    return {"status": "PASS", "point_estimate_regression": regression, "s0_equals_b2": s0}


def _a17_frozen_source_consistency() -> dict[str, Any]:
    comparison = read_csv(resolve("artifacts/a1_7_comparison_to_a1_3.csv"))
    macro = read_csv(resolve("artifacts/a1_3_lobo_macro_metrics.csv"))
    pooled = read_csv(resolve("artifacts/a1_3_lobo_pooled_metrics.csv"))
    checked = 0
    for row in comparison:
        for method in ("B2", "B3"):
            macro_row = _find_row(macro, target=row["target"], baseline_id=method)
            pooled_row = _find_row(pooled, target=row["target"], baseline_id=method)
            pairs = [
                (row[f"{method.lower()}_macro_ap"], macro_row["pr_auc_average_precision_macro_mean"]),
                (row[f"{method.lower()}_macro_f1"], macro_row["positive_f1_macro_mean"]),
                (row[f"{method.lower()}_pooled_ap"], pooled_row["pr_auc_average_precision"]),
                (row[f"{method.lower()}_pooled_f1"], pooled_row["positive_f1"]),
            ]
            for frozen, source in pairs:
                if not math.isclose(float(frozen), float(source), rel_tol=0.0, abs_tol=1e-12):
                    raise IntegrityError(
                        f"A1.7 frozen {method} source differs for {row['target']}: {frozen} vs {source}"
                    )
                checked += 1
    return {"status": "PASS", "checked_values": checked, "tolerance": 1e-12}


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    _assert_no_test_source(config)
    paths = _all_source_paths(config)
    missing = [rel(path) for path in paths if not path.is_file()]
    if missing:
        raise IntegrityError(f"missing formal sources: {missing}")
    decisions: dict[str, str] = {}
    boundary_audit: dict[str, Any] = {}
    for stage, source in config["formal_sources"].items():
        summary = read_json(resolve(source["summary"]))
        report = resolve(source["report"]).read_text(encoding="utf-8")
        decision = _decision(summary)
        if decision != "PASS_WITH_CONDITIONS" or decision not in report:
            raise IntegrityError(f"{stage} machine/report stage decision conflict")
        _assert_zero_access(stage, summary)
        decisions[stage] = decision
        boundary_audit[stage] = {
            "test_access_non_identifier": 0,
            "prohibited_experiments": 0,
        }
    a16 = read_json(resolve("artifacts/a1_6_run_summary.json"))
    for field in (
        "training_call_count",
        "real_model_training_count",
        "prediction_regeneration_count",
        "config_reselection_count",
        "threshold_reselection_count",
    ):
        if a16[field] != 0:
            raise IntegrityError(f"A1.6 boundary field is nonzero: {field}")
    a17 = read_json(resolve("artifacts/a1_7_run_summary.json"))
    for field in (
        "fine_tune_count",
        "fusion_count",
        "second_embedding_model_count",
        "new_classifier_family_count",
        "new_bootstrap_registry_count",
        "quantization_count",
    ):
        if a17[field] != 0:
            raise IntegrityError(f"A1.7 boundary field is nonzero: {field}")
    return {
        "status": "PASS",
        "source_paths": [rel(path) for path in paths],
        "formal_commits": _resolve_formal_commits(config),
        "stage_decisions": decisions,
        "report_numeric_consistency": _report_numeric_consistency(config),
        "a1_3_b2_equals_a1_5_s0": _a13_a15_consistency(),
        "a1_6_regression_guards": _a16_regression_consistency(),
        "a1_7_frozen_source_guards": _a17_frozen_source_consistency(),
        "boundary_audit": boundary_audit,
    }


def preregister(config: dict[str, Any]) -> dict[str, Any]:
    checked = preflight(config)
    frozen_paths = _all_source_paths(config) + [
        resolve(item) for item in config["preregistration_inputs"]
    ]
    missing = [rel(path) for path in frozen_paths if not path.is_file()]
    if missing:
        raise IntegrityError(f"missing preregistration inputs: {missing}")
    integrity = {
        "stage": "A1.8a",
        "status": "PASS",
        "generated_at_utc": utc_now(),
        "source_priority": config["source_priority"],
        "claim_ids": CLAIM_IDS,
        "claim_expected_status": {
            row["claim_id"]: row["expected_status"] for row in config["claims"]
        },
        "status_taxonomy": STATUSES,
        "threat_ids": THREAT_IDS,
        "method_proposal": config["formal_method_proposal"],
        "remaining_evidence_decisions": DECISIONS,
        "source_hashes": {rel(path): sha256_path(path) for path in frozen_paths},
        "formal_commits": checked["formal_commits"],
        "stage_decisions": checked["stage_decisions"],
        "consistency_guards": {
            "report_numeric_consistency": checked["report_numeric_consistency"],
            "a1_3_b2_equals_a1_5_s0": checked["a1_3_b2_equals_a1_5_s0"],
            "a1_6_regression_guards": checked["a1_6_regression_guards"],
            "a1_7_frozen_source_guards": checked["a1_7_frozen_source_guards"],
        },
        "execution_boundaries": config["boundaries"],
        "test_access_count": 0,
        "prohibited_experiment_count": 0,
    }
    write_json(resolve(config["outputs"]["prerun_integrity"]), integrity)
    return integrity


def _verify_preregistered_hashes(config: dict[str, Any]) -> dict[str, str]:
    integrity = read_json(resolve(config["outputs"]["prerun_integrity"]))
    if integrity.get("status") != "PASS" or integrity.get("claim_ids") != CLAIM_IDS:
        raise IntegrityError("invalid A1.8 preregistration integrity record")
    for path_text, expected in integrity["source_hashes"].items():
        actual = sha256_path(resolve(path_text))
        if actual != expected:
            raise IntegrityError(f"preregistered source hash changed: {path_text}")
    return integrity["source_hashes"]


EVIDENCE_FIELDS = [
    "evidence_id",
    "stage_id",
    "target",
    "protocol",
    "method_or_variant",
    "metric_or_estimand",
    "point_estimate",
    "ci_lower",
    "ci_upper",
    "valid_fraction",
    "sample_size",
    "positive_count",
    "support_role",
    "source_artifact",
    "source_row_key",
    "formal_commit",
    "notes",
]


def _evidence_row(**values: Any) -> dict[str, Any]:
    row = {field: "" for field in EVIDENCE_FIELDS}
    row.update(values)
    if row["support_role"] not in SUPPORT_ROLES:
        raise IntegrityError(f"invalid evidence support role: {row['support_role']}")
    return row


def build_evidence_registry(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counts = {
        row["target"]: (row["sample_count"], row["positive_count"])
        for row in read_csv(resolve("artifacts/a1_3_lobo_pooled_metrics.csv"))
        if row["baseline_id"] == "B2"
    }

    for row in read_csv(resolve("artifacts/a1_2_pooled_metrics.csv")):
        if row["baseline_id"] not in {"B2", "B3"}:
            continue
        role = "diagnostic" if row["target"] == "side_effect" else "secondary"
        rows.append(_evidence_row(
            evidence_id=f"E_A12_{row['target'].upper()}_{row['baseline_id']}_POOLED_AP",
            stage_id="A1.2",
            target=row["target"],
            protocol="task-grouped five-fold dev OOF",
            method_or_variant=row["baseline_id"],
            metric_or_estimand="pooled AP",
            point_estimate=row["pooled_pr_auc_average_precision"],
            sample_size=row["sample_count"],
            positive_count=row["positive_count"],
            support_role=role,
            source_artifact="artifacts/a1_2_pooled_metrics.csv",
            source_row_key=f"target={row['target']};baseline_id={row['baseline_id']}",
            formal_commit=config["formal_sources"]["A1.2"]["result_commit"],
            notes=f"pooled F1={row['pooled_positive_f1']}; AP lift={row['ap_absolute_lift']}; provisional dev signal only",
        ))

    for row in read_csv(resolve("artifacts/a1_3_lobo_macro_metrics.csv")):
        if row["baseline_id"] not in {"B2", "B3"}:
            continue
        if row["target"] == "side_effect":
            role = "diagnostic"
        elif row["baseline_id"] == "B2":
            role = "primary"
        else:
            role = "secondary"
        sample_size, positives = counts[row["target"]]
        rows.append(_evidence_row(
            evidence_id=f"E_A13_{row['target'].upper()}_{row['baseline_id']}_MACRO_AP",
            stage_id="A1.3",
            target=row["target"],
            protocol="primary four-group LOBO",
            method_or_variant=row["baseline_id"],
            metric_or_estimand="macro AP",
            point_estimate=row["pr_auc_average_precision_macro_mean"],
            sample_size=sample_size,
            positive_count=positives,
            support_role=role,
            source_artifact="artifacts/a1_3_lobo_macro_metrics.csv",
            source_row_key=f"target={row['target']};baseline_id={row['baseline_id']}",
            formal_commit=config["formal_sources"]["A1.3"]["result_commit"],
            notes=(f"macro F1={row['positive_f1_macro_mean']}; macro AP lift={row['ap_lift_macro_mean']}; "
                   f"valid domains={row['valid_domain_count']}; excluded single-class={row['excluded_single_class_domain_count']}"),
        ))

    a14 = read_csv(resolve("artifacts/a1_4_lomo_macro_metrics.csv"))
    for target, method in (("success", "B3"), ("side_effect", "B3"), ("looping", "B2")):
        row = _find_row(a14, target=target, baseline_id=method)
        sample_size, positives = counts[target]
        rows.append(_evidence_row(
            evidence_id=f"E_A14_{target.upper()}_{method}_MODEL_MACRO_AP",
            stage_id="A1.4",
            target=target,
            protocol="model-only LOMO with same-task counterparts",
            method_or_variant=method,
            metric_or_estimand="all-model macro AP",
            point_estimate=row["pr_auc_average_precision_all_model_macro_mean"],
            sample_size=sample_size,
            positive_count=positives,
            support_role="exploratory",
            source_artifact="artifacts/a1_4_lomo_macro_metrics.csv",
            source_row_key=f"target={target};baseline_id={method}",
            formal_commit=config["formal_sources"]["A1.4"]["result_commit"],
            notes=(f"all-model macro F1={row['positive_f1_all_model_macro_mean']}; "
                   "external task-group counterpart rate=1.0; not joint task-model OOD"),
        ))

    a15_macro = read_csv(resolve("artifacts/a1_5_macro_metrics.csv"))
    a15_delta = read_csv(resolve("artifacts/a1_5_structural_ablation_deltas.csv"))
    selected = {
        "success": ["S0_full13", "S1_no_termination", "S6_termination_repetition_only"],
        "side_effect": ["S0_full13"],
        "looping": ["S0_full13", "S2_no_repetition", "S6_termination_repetition_only"],
    }
    for target, variants in selected.items():
        for variant in variants:
            row = _find_row(a15_macro, target=target, variant_id=variant)
            delta = _find_row(
                a15_delta,
                target=target,
                variant_id=variant,
                held_out_group="assistantbench",
            )
            sample_size, positives = counts[target]
            role = "diagnostic" if target == "side_effect" else ("primary" if variant != "S6_termination_repetition_only" else "secondary")
            rows.append(_evidence_row(
                evidence_id=f"E_A15_{target.upper()}_{variant.upper()}_MACRO_AP",
                stage_id="A1.5",
                target=target,
                protocol="primary four-group LOBO structural ablation",
                method_or_variant=variant,
                metric_or_estimand="macro AP",
                point_estimate=row["pr_auc_average_precision_macro_mean"],
                sample_size=sample_size,
                positive_count=positives,
                support_role=role,
                source_artifact="artifacts/a1_5_macro_metrics.csv;artifacts/a1_5_structural_ablation_deltas.csv",
                source_row_key=f"target={target};variant_id={variant}",
                formal_commit=config["formal_sources"]["A1.5"]["result_commit"],
                notes=(f"macro delta AP={delta['macro_delta_AP']}; pooled delta AP={delta['pooled_delta_AP']}; "
                       f"retained AP-lift ratio={delta['retained_AP_lift_ratio'] or 'NA'}; descriptive non-causal ablation"),
            ))

    for row in read_csv(resolve("artifacts/a1_6_primary_paired_delta_summary.csv")):
        suffix = f"{row['comparison_id']}_{row['target']}_{row['scope']}_{row['metric']}".upper()
        role = "diagnostic" if row["target"] == "side_effect" else ("primary" if row["role"] == "primary" else "secondary")
        sample_size, positives = counts[row["target"]]
        rows.append(_evidence_row(
            evidence_id=f"E_A16_{suffix}",
            stage_id="A1.6",
            target=row["target"],
            protocol="fixed task-group cluster bootstrap over primary LOBO predictions",
            method_or_variant=f"{row['method_a']}{('-' + row['method_b']) if row['method_b'] else ''}",
            metric_or_estimand=row["estimand"],
            point_estimate=row["point_estimate"],
            ci_lower=row["ci_lower_95"],
            ci_upper=row["ci_upper_95"],
            valid_fraction=row["valid_draw_fraction"],
            sample_size=sample_size,
            positive_count=positives,
            support_role=role,
            source_artifact="artifacts/a1_6_primary_paired_delta_summary.csv",
            source_row_key=(f"comparison_id={row['comparison_id']};target={row['target']};"
                            f"scope={row['scope']};metric={row['metric']}"),
            formal_commit=config["formal_sources"]["A1.6"]["result_commit"],
            notes=f"grade={row['bootstrap_grade']}; fixed draws={row['fixed_draw_count']}; no new draw in A1.8",
        ))

    for row in read_csv(resolve("artifacts/a1_7_macro_metrics.csv")):
        role = "primary" if row["target"] == "success" else ("diagnostic" if row["target"] == "side_effect" else "secondary")
        sample_size, positives = counts[row["target"]]
        rows.append(_evidence_row(
            evidence_id=f"E_A17_{row['target'].upper()}_B4_MACRO_AP",
            stage_id="A1.7",
            target=row["target"],
            protocol="primary four-group LOBO frozen dense embedding",
            method_or_variant="B4_dense_embedding_lr",
            metric_or_estimand="macro AP",
            point_estimate=row["pr_auc_average_precision_macro_mean"],
            sample_size=sample_size,
            positive_count=positives,
            support_role=role,
            source_artifact="artifacts/a1_7_macro_metrics.csv",
            source_row_key=f"target={row['target']};baseline_id=B4_dense_embedding_lr",
            formal_commit=config["formal_sources"]["A1.7"]["result_commit"],
            notes=f"macro F1={row['positive_f1_macro_mean']}; macro AP lift={row['ap_lift_macro_mean']}",
        ))

    for row in read_csv(resolve("artifacts/a1_7_bootstrap_primary_summary.csv")):
        domain = f"_{row['held_out_group']}" if row["held_out_group"] else ""
        delta = "_delta" if "delta" in row["estimand"] else ""
        suffix = f"{row['comparison_id']}_{row['target']}_{row['scope']}{domain}_{row['metric']}{delta}".upper()
        if row["target"] == "side_effect":
            role = "diagnostic"
        elif row["role"] == "primary":
            role = "primary"
        else:
            role = "secondary"
        sample_size, positives = counts[row["target"]]
        rows.append(_evidence_row(
            evidence_id=f"E_A17_{suffix}",
            stage_id="A1.7",
            target=row["target"],
            protocol="fixed A1.6 task-group bootstrap registry over B4 and frozen comparators",
            method_or_variant=f"{row['method_a']}{('-' + row['method_b']) if row['method_b'] else ''}",
            metric_or_estimand=row["estimand"],
            point_estimate=row["point_estimate"],
            ci_lower=row["ci_lower_95"],
            ci_upper=row["ci_upper_95"],
            valid_fraction=row["valid_draw_fraction"],
            sample_size=sample_size,
            positive_count=positives,
            support_role=role,
            source_artifact="artifacts/a1_7_bootstrap_primary_summary.csv",
            source_row_key=(f"comparison_id={row['comparison_id']};target={row['target']};scope={row['scope']};"
                            f"held_out_group={row['held_out_group']};metric={row['metric']}"),
            formal_commit=config["formal_sources"]["A1.7"]["result_commit"],
            notes=f"grade={row['bootstrap_grade']}; reused frozen A1.6 draw registry byte-for-byte",
        ))

    ids = [row["evidence_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise IntegrityError("duplicate evidence IDs")
    return rows


CLAIM_FIELDS = [
    "claim_id", "target", "claim_short", "claim_precise", "claim_level",
    "best_supporting_evidence_ids", "counterevidence_or_limitation_ids",
    "allowed_wording_cn", "allowed_wording_en", "forbidden_wording_cn",
    "forbidden_wording_en", "paper_section", "status", "reason",
]


def build_claim_matrix(config: dict[str, Any], evidence: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence_ids = {row["evidence_id"] for row in evidence}
    rows = [
        {
            "claim_id": "C1", "target": "success", "claim_short": "Success跨Benchmark结构信号存在",
            "claim_precise": "Primary LOBO下，轻量结构特征为Success提供稳定的跨Benchmark预测信号。", "claim_level": "core",
            "best_supporting_evidence_ids": "E_A13_SUCCESS_B2_MACRO_AP;E_A16_P1_SUCCESS_MACRO_AP_LIFT", "counterevidence_or_limitation_ids": "T1;T5;T9;T10",
            "allowed_wording_cn": "轻量结构轨迹特征在Primary LOBO下为Success预测提供了稳定的跨Benchmark信号。",
            "allowed_wording_en": "Lightweight structural trajectory features provide stable cross-Benchmark signal for Success prediction under Primary LOBO.",
            "forbidden_wording_cn": "结构特征解决了所有Benchmark上的Success预测。", "forbidden_wording_en": "Structural features solve Success prediction across all Benchmarks.",
            "paper_section": "Evidence-Dimension Analysis", "status": "SUPPORTED",
            "reason": "A1.3 B2跨四域为正；A1.6 P1 macro AP lift 95% CI严格大于0。",
        },
        {
            "claim_id": "C2", "target": "success", "claim_short": "B2稳定优于B3",
            "claim_precise": "B2在Success Primary LOBO上的点估计高于B3，但配对不确定性不足以支持稳定优势。", "claim_level": "supporting",
            "best_supporting_evidence_ids": "E_A13_SUCCESS_B2_MACRO_AP;E_A13_SUCCESS_B3_MACRO_AP", "counterevidence_or_limitation_ids": "E_A16_P2_SUCCESS_MACRO_AP;E_A16_P2_SUCCESS_MACRO_F1",
            "allowed_wording_cn": "B2的点估计更高，但配对bootstrap区间跨0。", "allowed_wording_en": "B2 had a higher point estimate under Primary LOBO, but the paired bootstrap interval included zero.",
            "forbidden_wording_cn": "B2显著优于B3；B2稳定优于B3。", "forbidden_wording_en": "B2 is significantly or stably better than B3.",
            "paper_section": "Cross-Benchmark Results", "status": "INSUFFICIENT_EVIDENCE",
            "reason": "A1.6 P2的macro AP与F1配对区间均跨0。",
        },
        {
            "claim_id": "C3", "target": "success", "claim_short": "Success主要依赖termination",
            "claim_precise": "Termination携带预测信息，但删除termination未造成稳定退化。", "claim_level": "supporting",
            "best_supporting_evidence_ids": "E_A15_SUCCESS_S1_NO_TERMINATION_MACRO_AP", "counterevidence_or_limitation_ids": "E_A16_P3_SUCCESS_MACRO_AP;E_A16_P3_SUCCESS_POOLED_AP;E_A16_P3_SUCCESS_MACRO_F1;T7",
            "allowed_wording_cn": "Termination携带预测信息，但group-aware bootstrap未显示删除它会稳定降低性能。", "allowed_wording_en": "Termination carries predictive information, but removing it did not produce a stable degradation under group-aware bootstrap.",
            "forbidden_wording_cn": "Success主要由termination决定；termination导致Success。", "forbidden_wording_en": "Success is mainly determined or caused by termination.",
            "paper_section": "Structural Ablations", "status": "INSUFFICIENT_EVIDENCE",
            "reason": "A1.5点估计依赖与A1.6 P3跨0区间必须联合解释，且不得作因果表述。",
        },
        {
            "claim_id": "C4", "target": "success", "claim_short": "Success三特征表示与full13高度竞争",
            "claim_precise": "由termination与两项repetition特征组成的三特征表示在Success上与full13高度竞争，但差异不确定。", "claim_level": "supporting",
            "best_supporting_evidence_ids": "E_A15_SUCCESS_S6_TERMINATION_REPETITION_ONLY_MACRO_AP;E_A16_P4_SUCCESS_MACRO_AP", "counterevidence_or_limitation_ids": "E_A16_P4_SUCCESS_POOLED_AP;E_A16_P4_SUCCESS_MACRO_F1;T1;T5",
            "allowed_wording_cn": "三特征表示与完整结构集合高度竞争，但配对差异仍不确定。", "allowed_wording_en": "A three-feature representation was highly competitive with the full structural set; the paired difference remained uncertain.",
            "forbidden_wording_cn": "三特征与full13等价；已经证明两者一样好。", "forbidden_wording_en": "The three-feature representation is equivalent to or proven as good as full13.",
            "paper_section": "Structural Ablations", "status": "SUPPORTED_WITH_CONDITIONS",
            "reason": "A1.5 S6点估计接近/高于S0；A1.6 P4的AP/F1配对区间跨0，因此只能写competitive。",
        },
        {
            "claim_id": "C5", "target": "success", "claim_short": "Success dense semantics有稳定跨Benchmark信号",
            "claim_precise": "冻结dense embedding LR在Success Primary LOBO下具有稳定的正macro AP lift。", "claim_level": "core",
            "best_supporting_evidence_ids": "E_A17_SUCCESS_B4_MACRO_AP;E_A17_Q1_SUCCESS_MACRO_AP_LIFT", "counterevidence_or_limitation_ids": "T1;T5;T8;T9;T10",
            "allowed_wording_cn": "Dense embedding为Success提供了稳定的跨Benchmark信号。", "allowed_wording_en": "Frozen dense embeddings provide stable cross-Benchmark signal for Success.",
            "forbidden_wording_cn": "Dense embedding稳定优于所有轻量基线。", "forbidden_wording_en": "Dense embeddings stably outperform all lightweight baselines.",
            "paper_section": "Representation Complexity", "status": "SUPPORTED",
            "reason": "A1.7 Q1 macro AP lift 95% CI严格大于0。",
        },
        {
            "claim_id": "C6", "target": "success", "claim_short": "Dense semantics稳定优于B2/B3",
            "claim_precise": "Dense embedding有强信号，但没有相对B2/B3的稳定AP增量。", "claim_level": "supporting",
            "best_supporting_evidence_ids": "E_A17_SUCCESS_B4_MACRO_AP", "counterevidence_or_limitation_ids": "E_A17_Q2_SUCCESS_MACRO_AP_DELTA;E_A17_Q2_SUCCESS_MACRO_F1_DELTA;E_A17_Q3_SUCCESS_MACRO_AP_DELTA;E_A17_Q3_SUCCESS_MACRO_F1_DELTA",
            "allowed_wording_cn": "Dense embedding产生强跨Benchmark信号，但未显示相对冻结轻量基线的明确AP增量。", "allowed_wording_en": "Dense embeddings produced strong cross-Benchmark signal but no clear incremental AP gain over frozen lightweight baselines.",
            "forbidden_wording_cn": "Dense embedding稳定优于B2/B3。", "forbidden_wording_en": "Dense embeddings stably outperform B2 and B3.",
            "paper_section": "Representation Complexity", "status": "INSUFFICIENT_EVIDENCE",
            "reason": "Q2/Q3 AP区间跨0，且Q3 macro F1显示B4相对B2稳定下降。",
        },
        {
            "claim_id": "C7", "target": "looping", "claim_short": "Looping跨Benchmark结构信号存在",
            "claim_precise": "轻量结构特征为Looping提供稳定的跨Benchmark信号。", "claim_level": "core",
            "best_supporting_evidence_ids": "E_A13_LOOPING_B2_MACRO_AP;E_A16_P5_LOOPING_MACRO_AP_LIFT", "counterevidence_or_limitation_ids": "T1;T5;T7;T9;T10",
            "allowed_wording_cn": "轻量结构特征为Looping提供了稳定的跨Benchmark信号。", "allowed_wording_en": "Lightweight structural trajectory features provide stable cross-Benchmark signal for Looping.",
            "forbidden_wording_cn": "Looping结构模型对所有数据都已解决。", "forbidden_wording_en": "The structural model solves Looping on all data.",
            "paper_section": "Evidence-Dimension Analysis", "status": "SUPPORTED",
            "reason": "A1.3 B2在四域保持强信号；A1.6 P5 macro AP lift区间严格大于0。",
        },
        {
            "claim_id": "C8", "target": "looping", "claim_short": "Repetition特征有稳定增量",
            "claim_precise": "删除直接repetition特征使Looping macro AP稳定下降，但剩余结构模型仍然很强。", "claim_level": "core",
            "best_supporting_evidence_ids": "E_A15_LOOPING_S2_NO_REPETITION_MACRO_AP;E_A16_P6_LOOPING_MACRO_AP", "counterevidence_or_limitation_ids": "E_A15_LOOPING_S6_TERMINATION_REPETITION_ONLY_MACRO_AP;T7",
            "allowed_wording_cn": "直接repetition特征具有稳定增量；删除后剩余结构模型仍然很强。", "allowed_wording_en": "Direct repetition features add stable incremental value, while the remaining structural model stays strong after their removal.",
            "forbidden_wording_cn": "Looping完全由重复特征决定。", "forbidden_wording_en": "Looping is entirely determined by repetition features.",
            "paper_section": "Structural Ablations", "status": "SUPPORTED",
            "reason": "A1.6 P6 macro AP差值区间严格小于0，但S2本身仍保留高macro AP。",
        },
        {
            "claim_id": "C9", "target": "looping", "claim_short": "Dense semantics对Looping必要",
            "claim_precise": "现有证据未显示dense semantics相对B2增加Looping跨Benchmark价值。", "claim_level": "supporting",
            "best_supporting_evidence_ids": "E_A17_LOOPING_B4_MACRO_AP", "counterevidence_or_limitation_ids": "E_A17_Q5_LOOPING_MACRO_AP_DELTA;E_A13_LOOPING_B2_MACRO_AP",
            "allowed_wording_cn": "没有发现dense semantic表示相对轻量结构基线增加Looping跨Benchmark价值的明确证据。", "allowed_wording_en": "No clear evidence was found that dense semantic representations add cross-Benchmark value over the lightweight structural baseline for Looping.",
            "forbidden_wording_cn": "复杂语义表示对Looping是必要的。", "forbidden_wording_en": "Dense semantic representations are necessary for Looping.",
            "paper_section": "Representation Complexity", "status": "INSUFFICIENT_EVIDENCE",
            "reason": "A1.7 Q5 B4-B2 macro AP区间跨0，点估计为负。",
        },
        {
            "claim_id": "C10", "target": "side_effect", "claim_short": "Side Effect结构信号robust",
            "claim_precise": "现有Primary LOBO结构证据不支持Side Effect robust跨Benchmark预测。", "claim_level": "limitation",
            "best_supporting_evidence_ids": "E_A13_SIDE_EFFECT_B2_MACRO_AP;E_A15_SIDE_EFFECT_S0_FULL13_MACRO_AP", "counterevidence_or_limitation_ids": "T2;T3;T5",
            "allowed_wording_cn": "现有结构证据未建立Side Effect的robust跨Benchmark预测。", "allowed_wording_en": "Current structural evidence does not establish robust cross-Benchmark Side Effect prediction.",
            "forbidden_wording_cn": "Side Effect结构信号robust；Side Effect已由结构特征解决。", "forbidden_wording_en": "Side Effect has a robust structural signal or is solved by structural features.",
            "paper_section": "Limitations", "status": "PROHIBITED",
            "reason": "A1.3/A1.5 B2/S0 AP lift非正且支持稀疏，不能升级为robust claim。",
        },
        {
            "claim_id": "C11", "target": "side_effect", "claim_short": "Side Effect语义表示有潜力",
            "claim_precise": "TF-IDF与dense embedding呈现有希望的Side Effect点估计，但只有12个正例且区间很宽。", "claim_level": "auxiliary",
            "best_supporting_evidence_ids": "E_A12_SIDE_EFFECT_B3_POOLED_AP;E_A17_SIDE_EFFECT_B4_MACRO_AP;E_A17_Q4_SIDE_EFFECT_MACRO_AP", "counterevidence_or_limitation_ids": "E_A17_Q4_SIDE_EFFECT_MACRO_AP;T2;T3;T5",
            "allowed_wording_cn": "语义表示显示有希望的Side Effect点估计，但因dev仅12个正轨迹，统计支持很弱。", "allowed_wording_en": "Semantic representations showed promising point estimates for Side Effect, but statistical support is weak because only 12 positive dev trajectories are available.",
            "forbidden_wording_cn": "Side Effect已robust；Side Effect已经解决。", "forbidden_wording_en": "Side Effect has robust cross-Benchmark generalization or is solved.",
            "paper_section": "Exploratory Results and Limitations", "status": "DESCRIPTIVE_ONLY",
            "reason": "A1.2 B3和A1.7 B4仅为苗头；Q4是support-diagnostic-only，CI宽且存在单类域。",
        },
        {
            "claim_id": "C12", "target": "cross_model", "claim_short": "信号跨Agent/model转移",
            "claim_precise": "当训练侧包含相同任务的counterpart时，信号可转移到held-out Agent model。", "claim_level": "supporting",
            "best_supporting_evidence_ids": "E_A14_SUCCESS_B3_MODEL_MACRO_AP;E_A14_LOOPING_B2_MODEL_MACRO_AP;E_A14_SIDE_EFFECT_B3_MODEL_MACRO_AP", "counterevidence_or_limitation_ids": "T2;T4;T10",
            "allowed_wording_cn": "当底层任务在训练侧已有表示时，信号可以转移到held-out Agent model。", "allowed_wording_en": "Signals transferred to held-out Agent models when the underlying tasks were represented on the training side.",
            "forbidden_wording_cn": "A1.4证明同时泛化到新模型和新任务；joint task+model OOD。", "forbidden_wording_en": "A1.4 proves simultaneous new-model and new-task or joint task-model OOD generalization.",
            "paper_section": "Cross-Model Diagnostics", "status": "SUPPORTED_WITH_CONDITIONS",
            "reason": "A1.4 model-only LOMO显示信号，但external counterpart rate为100%，因此仅限same-task条件。",
        },
        {
            "claim_id": "C13", "target": "all", "claim_short": "模型越复杂越好",
            "claim_precise": "表示复杂度增加没有带来跨target统一、明确的跨Benchmark优势。", "claim_level": "limitation",
            "best_supporting_evidence_ids": "E_A17_Q2_SUCCESS_MACRO_AP_DELTA;E_A17_Q3_SUCCESS_MACRO_AP_DELTA;E_A17_Q5_LOOPING_MACRO_AP_DELTA", "counterevidence_or_limitation_ids": "T1;T5;T8",
            "allowed_wording_cn": "增加表示复杂度没有带来跨target清晰且一致的跨Benchmark优势。", "allowed_wording_en": "Increasing representation complexity did not yield a clear, uniform cross-Benchmark advantage across targets.",
            "forbidden_wording_cn": "模型越复杂越好。", "forbidden_wording_en": "More complex models are always better.",
            "paper_section": "Representation Complexity", "status": "PROHIBITED",
            "reason": "Success增量不确定且F1可稳定下降；Looping无明确增量；Side Effect仅descriptive。",
        },
        {
            "claim_id": "C14", "target": "all", "claim_short": "不同维度呈现不同经验表示需求",
            "claim_precise": "Success、Side Effect和Looping与结构/稀疏语义/dense语义表示呈现不同的经验关系。", "claim_level": "core",
            "best_supporting_evidence_ids": "E_A16_P1_SUCCESS_MACRO_AP_LIFT;E_A17_Q1_SUCCESS_MACRO_AP_LIFT;E_A16_P5_LOOPING_MACRO_AP_LIFT;E_A16_P6_LOOPING_MACRO_AP;E_A17_SIDE_EFFECT_B4_MACRO_AP", "counterevidence_or_limitation_ids": "C2;C6;C9;C11;T1;T2;T5;T9;T10",
            "allowed_wording_cn": "三个评价维度与结构和语义表示呈现不同的经验关系。", "allowed_wording_en": "The three evaluation dimensions exhibit different empirical relationships with structural and semantic representations.",
            "forbidden_wording_cn": "我们证明了不同维度存在固定的信息复杂度层级；这是因果机制。", "forbidden_wording_en": "We prove a fixed information-complexity hierarchy or a causal mechanism across dimensions.",
            "paper_section": "Contributions and Discussion", "status": "SUPPORTED_WITH_CONDITIONS",
            "reason": "Success、Looping具有不同的稳定结构/语义证据模式；Side Effect只能作为稀疏支持下的异质性限制，不能宣称固定层级。",
        },
    ]
    expected = {row["claim_id"]: row["expected_status"] for row in config["claims"]}
    if [row["claim_id"] for row in rows] != CLAIM_IDS:
        raise IntegrityError("generated claim matrix is not exactly C1-C14")
    for row in rows:
        if row["status"] != expected[row["claim_id"]]:
            raise IntegrityError(f"claim status conflicts with preregistration: {row['claim_id']}")
        if row["status"] not in STATUSES or row["claim_level"] not in config["claim_levels"]:
            raise IntegrityError(f"invalid claim taxonomy: {row['claim_id']}")
        referenced = [item for item in row["best_supporting_evidence_ids"].split(";") if item]
        if any(item not in evidence_ids for item in referenced):
            raise IntegrityError(f"claim references unknown supporting evidence: {row['claim_id']}")
    return rows


THREAT_FIELDS = [
    "threat_id", "category", "description", "affected_claims", "severity",
    "mitigated_by", "remaining_risk", "paper_wording", "blocking_for_test",
]


def build_threats() -> list[dict[str, str]]:
    return [
        {"threat_id": "T1", "category": "statistical conclusion validity", "description": "Dev set is about 196 trajectories across only 51 task groups.", "affected_claims": "C1-C14", "severity": "high", "mitigated_by": "task grouping; Primary LOBO; group-aware bootstrap; conservative claims", "remaining_risk": "Intervals and domain estimates may remain unstable.", "paper_wording": "Results are dev-scale evidence and require confirmatory evaluation after method freeze.", "blocking_for_test": "no"},
        {"threat_id": "T2", "category": "statistical conclusion validity", "description": "Side Effect has only 12 positive dev trajectories.", "affected_claims": "C10;C11;C12;C14", "severity": "critical", "mitigated_by": "diagnostic-only uncertainty; no imputation; exploratory-only paper role", "remaining_risk": "No strong Side Effect claim is supportable.", "paper_wording": "Side Effect findings are descriptive and exploratory because only 12 positives are available.", "blocking_for_test": "no; lower paper role"},
        {"threat_id": "T3", "category": "external validity", "description": "Side Effect AssistantBench is an all-negative held-out domain.", "affected_claims": "C10;C11;C14", "severity": "high", "mitigated_by": "dual-class metrics left missing; domain explicitly excluded from macro dual-class metrics", "remaining_risk": "Cross-domain Side Effect behavior cannot be assessed uniformly.", "paper_wording": "AssistantBench provides no positive Side Effect examples, so AP/F1 are not defined there.", "blocking_for_test": "no; exploratory-only"},
        {"threat_id": "T4", "category": "external validity", "description": "A1.4 model holdouts have 100% same-task counterparts on the training side.", "affected_claims": "C12", "severity": "critical", "mitigated_by": "model-only label; exact coverage and overlap audit", "remaining_risk": "Joint new-task and new-model generalization remains unknown.", "paper_wording": "LOMO measures model-only transfer with tasks represented during training, not joint task-model OOD.", "blocking_for_test": "no for proposed claims"},
        {"threat_id": "T5", "category": "statistical conclusion validity", "description": "Primary LOBO contains only four Benchmark groups.", "affected_claims": "C1-C11;C14", "severity": "high", "mitigated_by": "per-domain reporting; macro aggregation; clustered uncertainty", "remaining_risk": "Four-domain macro estimates have limited domain-level degrees of freedom.", "paper_wording": "Cross-Benchmark evidence covers four preregistered groups and should not be generalized beyond them.", "blocking_for_test": "no"},
        {"threat_id": "T6", "category": "measurement validity", "description": "High AP but low F1 in Success WorkArena resembles threshold-transfer or calibration symptoms.", "affected_claims": "C5;C6", "severity": "medium", "mitigated_by": "report AP and F1 separately; thresholds selected without held-out access", "remaining_risk": "Cause is untested because no calibration experiment was run.", "paper_wording": "The pattern is calibration-like only; it is not evidence of a diagnosed calibration failure.", "blocking_for_test": "no"},
        {"threat_id": "T7", "category": "construct validity", "description": "Direct repetition features are conceptually close to the Looping construct.", "affected_claims": "C3;C7;C8", "severity": "high", "mitigated_by": "no-repetition ablation remains strong; three-feature and residual models reported", "remaining_risk": "Some predictive signal may reflect a close structural proxy to the annotation definition.", "paper_wording": "Repetition features add value, but Looping is not fully explained by them.", "blocking_for_test": "no"},
        {"threat_id": "T8", "category": "representation validity", "description": "Long trajectories use non-overlap chunking and weighted pooling rather than one full-context embedding pass.", "affected_claims": "C5;C6;C9;C11;C13;C14", "severity": "medium", "mitigated_by": "frozen tokenizer audit; no truncation; deterministic normalized pooling", "remaining_risk": "Cross-chunk interactions may be lost.", "paper_wording": "B4 is a deterministic engineering approximation to long-context semantic representation.", "blocking_for_test": "no"},
        {"threat_id": "T9", "category": "researcher degrees of freedom", "description": "A1.2-A1.7 are dev-driven method-selection stages.", "affected_claims": "C1-C14", "severity": "critical", "mitigated_by": "stage preregistration; immutable artifacts; final candidate proposal before test", "remaining_risk": "Dev evidence is selection evidence, not final confirmatory evidence.", "paper_wording": "All candidates and claims must be frozen before any confirmatory test access.", "blocking_for_test": "yes until human-approved final freeze"},
        {"threat_id": "T10", "category": "external validity", "description": "All evidence uses one dataset and annotation source.", "affected_claims": "C1-C14", "severity": "high", "mitigated_by": "multiple Benchmark groups and held-out models within the dataset", "remaining_risk": "Transfer to other Judge datasets and annotation policies is unknown.", "paper_wording": "Claims are restricted to AgentRewardBench and its covered domains.", "blocking_for_test": "no"},
    ]


CONTRIBUTION_FIELDS = [
    "contribution_id", "contribution", "paper_status", "supporting_claims",
    "supporting_stages", "strongest_metric_evidence", "key_limitation",
    "reviewer_challenge", "response_supported_by_current_evidence",
]


def build_contributions() -> list[dict[str, str]]:
    return [
        {"contribution_id": "K1", "contribution": "Empirical cross-Benchmark signal characterization", "paper_status": "KEEP_WITH_CONDITIONS", "supporting_claims": "C1;C5;C7", "supporting_stages": "A1.3;A1.6;A1.7", "strongest_metric_evidence": "P1 Success B2 macro AP lift CI [0.108398,0.343576]; P5 Looping B2 [0.333629,0.505652]; Q1 Success B4 [0.164990,0.381854]", "key_limitation": "Only four Benchmark groups and one dataset.", "reviewer_challenge": "Is this truly cross-Benchmark with so few domains?", "response_supported_by_current_evidence": "Use exact four-group Primary LOBO wording and clustered intervals; do not generalize beyond covered groups."},
        {"contribution_id": "K2", "contribution": "Representation complexity comparison", "paper_status": "KEEP_WITH_CONDITIONS", "supporting_claims": "C4;C5;C6;C8;C9;C13", "supporting_stages": "A1.5;A1.6;A1.7", "strongest_metric_evidence": "Q2/Q3/Q5 show uncertain incremental AP; Q3 F1 is a stable B4 drop; P6 shows repetition increment.", "key_limitation": "One dense encoder and approximate chunk pooling.", "reviewer_challenge": "Why call this a complexity result when only one embedding was checked?", "response_supported_by_current_evidence": "Frame as a frozen complexity control, not an exhaustive semantic-model comparison."},
        {"contribution_id": "K3", "contribution": "Target-specific empirical evidence heterogeneity", "paper_status": "KEEP_WITH_CONDITIONS", "supporting_claims": "C1;C5;C7;C8;C14", "supporting_stages": "A1.2-A1.7", "strongest_metric_evidence": "Success supports B2 and B4 signal; Looping supports B2 plus repetition increment without B4 gain; Side Effect remains descriptive.", "key_limitation": "Side Effect sparsity prevents a symmetric three-target conclusion.", "reviewer_challenge": "Is heterogeneity just one weak target?", "response_supported_by_current_evidence": "State empirical relationships and asymmetry, not a fixed hierarchy or causal mechanism."},
        {"contribution_id": "K4", "contribution": "Rigorous grouped evaluation and uncertainty methodology", "paper_status": "KEEP", "supporting_claims": "C1;C7;C8;C12", "supporting_stages": "A1.3;A1.4;A1.6;A1.7", "strongest_metric_evidence": "Task-grouped Primary LOBO, model-only LOMO boundary audit, and fixed cluster bootstrap with no invalid redraw.", "key_limitation": "Methodology does not compensate for limited domain and positive support.", "reviewer_challenge": "Are the intervals valid with repeated trajectories per task?", "response_supported_by_current_evidence": "Bootstrap samples task groups within target and held-out domain and replicates all trajectories in each sampled cluster."},
    ]


PROPOSAL_FIELDS = [
    "target", "candidate_method", "role", "selection_rationale", "known_limitation",
    "eligible_for_confirmatory_test",
]


def build_method_proposal() -> list[dict[str, str]]:
    return [
        {"target": "success", "candidate_method": "B2 structural LR", "role": "primary candidate", "selection_rationale": "A1.6 P1 stable positive cross-Benchmark signal; A1.7 B4 has no stable AP gain over B2 and has a stable macro-F1 drop; B2 is simpler, cheaper, and interpretable.", "known_limitation": "B2 is not stably better than B3; termination mechanism is uncertain; four-domain dev evidence only.", "eligible_for_confirmatory_test": "true_after_human_freeze_approval"},
        {"target": "side_effect", "candidate_method": "B4 dense embedding LR", "role": "exploratory-only", "selection_rationale": "A1.7 B4 shows promising semantic point estimates, while B2 structural evidence is weak; candidate role is deliberately reduced.", "known_limitation": "Only 12 positives; AssistantBench is all-negative; B4-B3 difference is uncertain; no robust claim.", "eligible_for_confirmatory_test": "false_or_exploratory_only"},
        {"target": "looping", "candidate_method": "B2 structural LR", "role": "primary candidate", "selection_rationale": "A1.6 P5 is a strong stable cross-Benchmark signal; P6 shows repetition increment; A1.7 B4 has no clear gain. S6 remains compact auxiliary only.", "known_limitation": "Repetition features are construct-adjacent and do not fully explain performance; four-domain dev evidence only.", "eligible_for_confirmatory_test": "true_after_human_freeze_approval"},
    ]


PLAN_FIELDS = ["item_id", "item_type", "title", "content", "evidence_sources", "caveat"]


def build_table_figure_plan() -> list[dict[str, str]]:
    return [
        {"item_id": "Table1", "item_type": "table", "title": "Dataset and target support", "content": "target counts; positives; task groups; Benchmark coverage; Side Effect sparsity", "evidence_sources": "A1.3 held-out statistics; manifests", "caveat": "Expose the 12-positive and single-class-domain limitations prominently."},
        {"item_id": "Table2", "item_type": "table", "title": "Primary LOBO baselines", "content": "B0-B4 by Success, Side Effect, Looping with macro AP/F1, role, and caveat", "evidence_sources": "A1.3;A1.7", "caveat": "B4 is a later frozen complexity control; Side Effect is descriptive."},
        {"item_id": "Table3", "item_type": "table", "title": "Structural ablations", "content": "S0/S1/S2/S5/S6 for Success and Looping with AP deltas and bootstrap grades", "evidence_sources": "A1.5;A1.6", "caveat": "No causal or equivalence wording."},
        {"item_id": "Figure1", "item_type": "figure", "title": "Target by representation evidence map", "content": "structural; TF-IDF; dense semantic point estimates, intervals, and support roles", "evidence_sources": "A1.3;A1.6;A1.7", "caveat": "Do not visually imply robust Side Effect performance."},
        {"item_id": "Figure2", "item_type": "figure", "title": "Cross-Benchmark uncertainty", "content": "Success B2 AP lift; Looping B2 AP lift; Looping no-repetition delta; Success B4-B2/B3", "evidence_sources": "A1.6 P1/P5/P6; A1.7 Q2/Q3", "caveat": "Intervals are bootstrap stability summaries, not p-values."},
    ]


REVIEW_FIELDS = [
    "attack_id", "reviewer_challenge", "current_evidence_response",
    "remaining_weakness", "needs_new_experiment",
]


def build_reviewer_attacks() -> list[dict[str, str]]:
    return [
        {"attack_id": "R1", "reviewer_challenge": "196 trajectories are too few.", "current_evidence_response": "The protocol groups 51 tasks, uses four-domain LOBO, preserves per-domain results, and applies task-cluster bootstrap.", "remaining_weakness": "Small data and four domains limit precision and external validity.", "needs_new_experiment": "no; disclose limitation and use confirmatory test only after freeze"},
        {"attack_id": "R2", "reviewer_challenge": "Side Effect has only 12 positives, so its conclusion is unreliable.", "current_evidence_response": "Agreed for strong claims: all Side Effect evidence is diagnostic/descriptive and the final role is exploratory-only.", "remaining_weakness": "No current statistic can create missing positive support.", "needs_new_experiment": "no; lower paper role rather than extend dev indefinitely"},
        {"attack_id": "R3", "reviewer_challenge": "Looping features leak the label definition.", "current_evidence_response": "No-repetition ablation stays strong, while P6 shows a stable but limited repetition increment; full dependence is rejected.", "remaining_weakness": "Repetition remains construct-adjacent and cannot be treated as a causal mechanism.", "needs_new_experiment": "no for current bounded claim"},
        {"attack_id": "R4", "reviewer_challenge": "LOMO is not true OOD because the same tasks appear in training.", "current_evidence_response": "Correct; A1.4 is explicitly model-only with 100% task counterparts and supports only conditional cross-model transfer.", "remaining_weakness": "Joint task-model OOD remains unanswered.", "needs_new_experiment": "no for current model-only claim"},
        {"attack_id": "R5", "reviewer_challenge": "Why not use a larger LLM Judge?", "current_evidence_response": "The research question is lightweight, interpretable evidence under Benchmark shift; paid/large Judge methods are outside the preregistered scope.", "remaining_weakness": "The work does not claim superiority over large LLM Judges.", "needs_new_experiment": "no; out of scope"},
        {"attack_id": "R6", "reviewer_challenge": "Why did B4 not stably beat B2?", "current_evidence_response": "Q2/Q3 show uncertain AP increments and Q3 shows a stable Success macro-F1 drop, so complexity alone is not uniformly beneficial.", "remaining_weakness": "Only one dense encoder and one pooling design were frozen.", "needs_new_experiment": "no; this negative result is part of the contribution"},
        {"attack_id": "R7", "reviewer_challenge": "Are results only Benchmark/model identity shortcuts?", "current_evidence_response": "Identity fields are excluded from frozen inputs; Primary LOBO holds out full Benchmark groups; model-literal injection audit is zero.", "remaining_weakness": "Natural text can still contain domain-specific content and LOMO shares tasks.", "needs_new_experiment": "no for freeze decision; preserve as limitation"},
        {"attack_id": "R8", "reviewer_challenge": "Why compare pooled AP across held-out models?", "current_evidence_response": "Pooled metrics are secondary; primary cross-model interpretation uses per-model and macro results because probability scales may differ.", "remaining_weakness": "Cross-model probability calibration is not established.", "needs_new_experiment": "no; do not elevate pooled AP"},
        {"attack_id": "R9", "reviewer_challenge": "Why not tune on test?", "current_evidence_response": "Test tuning would invalidate confirmatory evidence; configs and thresholds are selected only inside development training folds and must be frozen before test.", "remaining_weakness": "Final confirmatory performance is not yet known.", "needs_new_experiment": "no; test remains sealed pending human freeze approval"},
        {"attack_id": "R10", "reviewer_challenge": "Chunk pooling may lose information in trajectories up to 160k tokens.", "current_evidence_response": "A1.7 uses no truncation, deterministic non-overlap chunks, last-EOS pooling, and payload-weighted normalization.", "remaining_weakness": "Cross-chunk interactions are approximated rather than jointly encoded.", "needs_new_experiment": "no for the frozen B4 complexity-control interpretation"},
    ]


def _validate_outputs(
    config: dict[str, Any],
    evidence: list[dict[str, Any]],
    claims: list[dict[str, str]],
    threats: list[dict[str, str]],
    contributions: list[dict[str, str]],
    proposal: list[dict[str, str]],
    decision: dict[str, Any],
) -> dict[str, Any]:
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    if [row["claim_id"] for row in claims] != CLAIM_IDS:
        raise IntegrityError("claim IDs changed")
    if [row["threat_id"] for row in threats] != THREAT_IDS:
        raise IntegrityError("threat IDs changed")
    for claim in claims:
        if claim["status"] == "SUPPORTED":
            ids = claim["best_supporting_evidence_ids"].split(";")
            if not any(evidence_by_id[item]["support_role"] == "primary" for item in ids):
                raise IntegrityError(f"SUPPORTED claim lacks primary evidence: {claim['claim_id']}")
        if claim["status"] == "SUPPORTED_WITH_CONDITIONS" and not claim["counterevidence_or_limitation_ids"]:
            raise IntegrityError(f"conditional claim lacks limitation: {claim['claim_id']}")
        if claim["status"] == "PROHIBITED" and not claim["forbidden_wording_en"]:
            raise IntegrityError(f"prohibited claim lacks forbidden wording: {claim['claim_id']}")
    core_contribution_claims = ";".join(row["supporting_claims"] for row in contributions)
    if "C11" in core_contribution_claims:
        raise IntegrityError("DESCRIPTIVE_ONLY C11 entered a core contribution")
    if len(proposal) != 3 or {row["target"] for row in proposal} != {"success", "side_effect", "looping"}:
        raise IntegrityError("method proposal does not have exactly one row per target")
    by_target = {row["target"]: row for row in proposal}
    if by_target["success"]["candidate_method"] != "B2 structural LR":
        raise IntegrityError("Success primary proposal changed")
    if by_target["looping"]["candidate_method"] != "B2 structural LR":
        raise IntegrityError("Looping primary proposal changed")
    if by_target["side_effect"]["role"] != "exploratory-only":
        raise IntegrityError("Side Effect role changed")
    if decision["decision"] not in DECISIONS:
        raise IntegrityError("invalid remaining-evidence decision")
    forbidden_blob = " ".join(
        claim["forbidden_wording_cn"] + " " + claim["forbidden_wording_en"] for claim in claims
    ).lower()
    required = [
        "b2显著优于b3", "dense embedding稳定优于b2/b3", "success主要由termination决定",
        "looping完全由重复特征决定", "side effect已robust", "joint task+model ood",
        "模型越复杂越好", "因果机制",
    ]
    missing = [phrase for phrase in required if phrase not in forbidden_blob]
    if missing:
        raise IntegrityError(f"required prohibited wording missing: {missing}")
    return {
        "status": "PASS",
        "evidence_rows": len(evidence),
        "claim_rows": len(claims),
        "threat_rows": len(threats),
        "contribution_rows": len(contributions),
        "proposal_rows": len(proposal),
    }


def _fmt_number(value: str) -> str:
    if value == "":
        return "NA"
    return f"{float(value):.6f}"


def _report_text(
    config: dict[str, Any],
    checked: dict[str, Any],
    claims: list[dict[str, str]],
    threats: list[dict[str, str]],
    contributions: list[dict[str, str]],
    proposal: list[dict[str, str]],
    reviews: list[dict[str, str]],
    decision: dict[str, Any],
) -> str:
    claim_lines = [
        f"| {row['claim_id']} | {row['target']} | {row['status']} | {row['allowed_wording_cn']} |"
        for row in claims
    ]
    threat_lines = [
        f"| {row['threat_id']} | {row['severity']} | {row['description']} | {row['remaining_risk']} |"
        for row in threats
    ]
    contribution_lines = [
        f"| {row['contribution_id']} | {row['paper_status']} | {row['contribution']} | {row['key_limitation']} |"
        for row in contributions
    ]
    proposal_lines = [
        f"| {row['target']} | {row['candidate_method']} | {row['role']} | {row['eligible_for_confirmatory_test']} |"
        for row in proposal
    ]
    review_lines = [
        f"| {row['attack_id']} | {row['reviewer_challenge']} | {row['current_evidence_response']} | {row['remaining_weakness']} |"
        for row in reviews
    ]
    forbidden = [f"- {row['forbidden_wording_cn']}" for row in claims if row["forbidden_wording_cn"]]
    commits = [
        f"- {stage}: prereg `{source['preregistration_commit']}`; formal result `{source['result_commit']}`"
        for stage, source in config["formal_sources"].items()
    ]
    return f"""# Stage A1.8 Evidence Audit and Paper Claim Matrix

## 阶段判定

`PASS_WITH_CONDITIONS`

技术审计通过；条件来自claim降级、Side Effect仅能exploratory、四域/小样本/单一数据源等未消失的限制，而不是实现失败。A1.8不构成test授权。

## A1.8 commits

- A1.8a preregistration commit: `{git_output(['rev-parse', 'HEAD'])}`
- A1.8b evidence result commit: recorded by the enclosing result commit and independently resolved after commit.

## A1.2-A1.7 evidence chain and provenance

{chr(10).join(commits)}

- Source priority: machine-readable artifact > formal stage report > human summary.
- Formal sources, paths, hashes, and commits: PASS.
- Machine summary/report core numeric consistency: PASS ({checked['report_numeric_consistency']['total']} checked values).
- A1.3 B2 / A1.5 S0: exact across 583 prediction rows.
- A1.6 point regression: PASS at tolerance `1e-12`.
- A1.7 frozen B2/B3 source values: PASS at tolerance `1e-12`.
- All formal-stage test-content/label/prediction/metric access: 0.
- All formal-stage prohibited-experiment records: 0.

## C1-C14 claim matrix

| Claim | Target | Status | Allowed wording |
|---|---|---|---|
{chr(10).join(claim_lines)}

## 明确禁止的表述

{chr(10).join(forbidden)}

这些禁止项覆盖：B2显著优于B3、Dense embedding稳定优于B2/B3、Success主要由termination决定、Looping完全由重复特征决定、Side Effect已robust/solved、A1.4证明joint task+model OOD、模型越复杂越好，以及任何因果机制表述。

## 三个target的最强结论

- Success：B2结构LR和B4 dense embedding各自都有稳定跨Benchmark信号；没有证据支持B4相对B2/B3的稳定AP增量，且B4相对B2 macro F1稳定下降。三特征S6与full13高度竞争，但不能写等价。
- Side Effect：结构证据不robust；B3/B4仅显示语义潜力。因仅12个正例且AssistantBench为全负，全部结论必须保持descriptive/exploratory。
- Looping：B2结构LR具有强且稳定的跨Benchmark信号；直接repetition特征有稳定增量，但删除后剩余结构模型仍强，不能写“完全由重复决定”；B4无明确增量。

## A1.4 cross-model解释边界

A1.4只支持model-only、same-task-counterpart条件下的跨Agent/model转移。external task-group counterpart rate为100%，因此不能解释joint task+model OOD。

## A1.5/A1.6对shortcut解释的修正

消融点估计不能升级成机制或因果结论。A1.6显示删除termination的差异不稳定；Looping删除repetition的macro AP稳定下降，但残余模型仍强。

## A1.7对复杂度升级的结论

Dense semantic表示可提供Success信号，但增加表示复杂度没有跨target产生清晰、统一的跨Benchmark优势。Side Effect只能作为低支持描述，Looping不需要dense语义来建立当前主线。

## Threats to validity

| ID | Severity | Threat | Remaining risk |
|---|---|---|---|
{chr(10).join(threat_lines)}

## Contribution matrix

| ID | Paper status | Contribution | Key limitation |
|---|---|---|---|
{chr(10).join(contribution_lines)}

没有为了凑贡献新增表述；K1-K4均保留，其中K1-K3带条件，K4保留。无DROP_FROM_PAPER项；C11不进入core contribution。

## Reviewer attacks

| ID | Attack | Current evidence response | Remaining weakness |
|---|---|---|---|
{chr(10).join(review_lines)}

## Final method freeze proposal

| Target | Candidate | Role | Confirmatory eligibility |
|---|---|---|---|
{chr(10).join(proposal_lines)}

## Remaining evidence decision

`{decision['decision']}`

Success和Looping的稳定跨Benchmark结构信号已由A1.6确认；B4已完成冻结语义复杂度检查；没有未解决的泄漏或协议错误；剩余问题主要是limitations而非主结果真伪。Side Effect通过降低论文角色处理，不以12 positives为理由无限追加dev实验。

## 是否建议进入final method freeze

建议进入**人工审批的final method freeze / test前预注册**。这不是自动进入test的授权。

## 执行边界与停止

- estimator fit count: 0
- model forward count: 0
- new prediction count: 0
- new threshold/config selection count: 0
- new bootstrap draw count: 0
- test access count: 0
- prohibited experiment count: 0

A1.8完成后立即停止，等待人工阶段门审查；不得自动开始final test或任何新模型实验。
"""


def _allowed_forbidden_text(claims: list[dict[str, str]]) -> str:
    sections = ["# Paper Claims Allowed and Forbidden", "", "本文件由A1.8冻结claim matrix生成；machine-readable CSV为权威来源。", ""]
    for row in claims:
        sections.extend([
            f"## {row['claim_id']} — {row['status']}", "",
            f"允许中文：{row['allowed_wording_cn']}", "",
            f"Allowed English: {row['allowed_wording_en']}", "",
            f"禁止中文：{row['forbidden_wording_cn']}", "",
            f"Forbidden English: {row['forbidden_wording_en']}", "",
            f"依据：{row['reason']}", "",
        ])
    return "\n".join(sections)


def _snapshot_text(evidence: list[dict[str, Any]], decision: dict[str, Any]) -> str:
    selected_ids = [
        "E_A16_P1_SUCCESS_MACRO_AP_LIFT",
        "E_A16_P5_LOOPING_MACRO_AP_LIFT",
        "E_A16_P6_LOOPING_MACRO_AP",
        "E_A17_Q1_SUCCESS_MACRO_AP_LIFT",
        "E_A17_Q3_SUCCESS_MACRO_F1_DELTA",
        "E_A17_Q4_SIDE_EFFECT_MACRO_AP",
        "E_A17_Q5_LOOPING_MACRO_AP_DELTA",
    ]
    by_id = {row["evidence_id"]: row for row in evidence}
    lines = []
    for evidence_id in selected_ids:
        row = by_id[evidence_id]
        lines.append(
            f"| {evidence_id} | {row['target']} | {row['metric_or_estimand']} | "
            f"{_fmt_number(str(row['point_estimate']))} | "
            f"[{_fmt_number(str(row['ci_lower']))}, {_fmt_number(str(row['ci_upper']))}] | "
            f"{row['support_role']} |"
        )
    return f"""# Paper Evidence Snapshot A1.8

## Frozen decision

`{decision['decision']}`

## Key machine-readable evidence

| Evidence | Target | Estimand | Point | 95% CI | Role |
|---|---|---|---:|---|---|
{chr(10).join(lines)}

## Interpretation boundary

- Stability labels are frozen bootstrap interpretations, not p-values or causal claims.
- Side Effect remains descriptive/exploratory because it has 12 positives and one all-negative domain.
- A1.4 is model-only transfer with same-task counterparts, not joint task-model OOD.
- Test access in A1.8: 0.
"""


def run_audit(config: dict[str, Any]) -> dict[str, Any]:
    if git_output(["status", "--porcelain"]):
        raise IntegrityError("A1.8b requires a clean Git worktree before formal execution")
    _verify_preregistered_hashes(config)
    checked = preflight(config)
    evidence = build_evidence_registry(config)
    claims = build_claim_matrix(config, evidence)
    threats = build_threats()
    contributions = build_contributions()
    proposal = build_method_proposal()
    plan = build_table_figure_plan()
    reviews = build_reviewer_attacks()
    decision = {
        "stage": "A1.8",
        "decision": "READY_FOR_FINAL_METHOD_FREEZE",
        "reason": "Stable Success and Looping structural cross-Benchmark signals are established, frozen uncertainty and dense-semantic complexity checks are complete, no unresolved protocol error exists, and remaining issues are limitations rather than blockers.",
        "exact_question": "",
        "why_blocking": "",
        "minimal_experiment": "",
        "why_existing_evidence_cannot_answer": "",
        "side_effect_policy": "lower_to_exploratory_only_not_unbounded_dev_extension",
        "requires_human_stage_gate_before_test": True,
        "test_access_count": 0,
    }
    validation = _validate_outputs(
        config, evidence, claims, threats, contributions, proposal, decision
    )

    outputs = config["outputs"]
    write_csv(resolve(outputs["evidence_registry"]), evidence, EVIDENCE_FIELDS)
    write_csv(resolve(outputs["claim_matrix"]), claims, CLAIM_FIELDS)
    write_csv(resolve(outputs["threats"]), threats, THREAT_FIELDS)
    write_csv(resolve(outputs["contributions"]), contributions, CONTRIBUTION_FIELDS)
    write_csv(resolve(outputs["method_proposal"]), proposal, PROPOSAL_FIELDS)
    write_csv(resolve(outputs["table_figure_plan"]), plan, PLAN_FIELDS)
    write_csv(resolve(outputs["reviewer_attacks"]), reviews, REVIEW_FIELDS)
    write_json(resolve(outputs["remaining_decision"]), decision)
    write_text(resolve(outputs["formal_report"]), _report_text(
        config, checked, claims, threats, contributions, proposal, reviews, decision
    ))
    write_text(resolve(outputs["allowed_forbidden"]), _allowed_forbidden_text(claims))
    write_text(resolve(outputs["evidence_snapshot"]), _snapshot_text(evidence, decision))

    hash_keys = [
        "evidence_registry", "claim_matrix", "threats", "contributions",
        "method_proposal", "table_figure_plan", "reviewer_attacks",
        "remaining_decision", "formal_report", "allowed_forbidden", "evidence_snapshot",
    ]
    output_hashes = {
        outputs[key]: sha256_path(resolve(outputs[key])) for key in hash_keys
    }
    summary = {
        "stage": "A1.8",
        "stage_determination": "PASS_WITH_CONDITIONS",
        "generated_at_utc": utc_now(),
        "a1_8a_preregistration_commit": git_output(["rev-parse", "HEAD"]),
        "a1_8b_result_commit": "recorded_by_enclosing_result_commit",
        "source_priority": config["source_priority"],
        "provenance_audit": checked,
        "claim_status": {row["claim_id"]: row["status"] for row in claims},
        "contribution_status": {row["contribution_id"]: row["paper_status"] for row in contributions},
        "final_method_freeze_proposal": proposal,
        "remaining_evidence_decision": decision["decision"],
        "recommend_enter_final_method_freeze": True,
        "execution_boundaries": config["boundaries"],
        "test_access_count": 0,
        "prohibited_experiment_count": 0,
        "validation": validation,
        "output_hashes": output_hashes,
        "stop_condition": "await_human_stage_gate_no_test_or_new_experiment",
    }
    write_json(resolve(outputs["run_summary"]), summary)
    return summary


def verify_formal_outputs(config: dict[str, Any], *, require_clean: bool = False) -> dict[str, Any]:
    _verify_preregistered_hashes(config)
    checked = preflight(config)
    outputs = config["outputs"]
    required_keys = [
        "evidence_registry", "claim_matrix", "threats", "contributions",
        "method_proposal", "table_figure_plan", "reviewer_attacks",
        "remaining_decision", "run_summary", "formal_report", "allowed_forbidden",
        "evidence_snapshot",
    ]
    missing = [outputs[key] for key in required_keys if not resolve(outputs[key]).is_file()]
    if missing:
        raise IntegrityError(f"missing formal A1.8 outputs: {missing}")
    evidence = read_csv(resolve(outputs["evidence_registry"]))
    claims = read_csv(resolve(outputs["claim_matrix"]))
    threats = read_csv(resolve(outputs["threats"]))
    contributions = read_csv(resolve(outputs["contributions"]))
    proposal = read_csv(resolve(outputs["method_proposal"]))
    decision = read_json(resolve(outputs["remaining_decision"]))
    validation = _validate_outputs(
        config, evidence, claims, threats, contributions, proposal, decision
    )
    summary = read_json(resolve(outputs["run_summary"]))
    for path_text, expected in summary["output_hashes"].items():
        if sha256_path(resolve(path_text)) != expected:
            raise IntegrityError(f"formal output hash mismatch: {path_text}")
    if summary["claim_status"] != {row["claim_id"]: row["status"] for row in claims}:
        raise IntegrityError("run summary claim status differs from claim matrix")
    if summary["remaining_evidence_decision"] != decision["decision"]:
        raise IntegrityError("run summary remaining-evidence decision differs")
    git_clean = git_output(["status", "--porcelain"]) == ""
    if require_clean and not git_clean:
        raise IntegrityError("final independent verification requires a clean Git worktree")
    result_log = git_output([
        "log", "--diff-filter=A", "--format=%H %s", "--", outputs["run_summary"]
    ])
    result_commit = result_log.splitlines()[-1].split(" ", 1)[0] if result_log else "uncommitted"
    return {
        "status": "PASS",
        "preflight": checked["status"],
        "validation": validation,
        "output_hash_count": len(summary["output_hashes"]),
        "git_clean": git_clean,
        "a1_8b_result_commit": result_commit,
        "test_access_count": 0,
        "prohibited_experiment_count": 0,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preregister", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.config.resolve())
        if args.preregister:
            result = preregister(config)
        elif args.run:
            result = run_audit(config)
        else:
            result = verify_formal_outputs(config, require_clean=args.require_clean)
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (IntegrityError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
