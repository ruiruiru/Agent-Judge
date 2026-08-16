#!/usr/bin/env python3
"""Preregister, run, and independently verify Stage A1.5 ablations.

``--write-prerun`` is a read-only scientific audit of real dev inputs: it does
not fit a scaler or estimator. ``--run`` first executes and verifies only the
S0 positive control, then and only then executes S1--S6. ``--verify-results``
recomputes saved selections, metrics, deltas, and dependency grades without
fitting anything.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import yaml
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import run_stage_a1_2_baselines as a12


CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_5_structural_ablation.yaml"
TARGETS = ["success", "side_effect", "looping"]
HELD_OUT_GROUPS = ["assistantbench", "visualwebarena", "webarena", "workarena"]
FEATURE_NAMES = list(a12.FEATURE_NAMES)
METRIC_NAMES = list(a12.METRIC_NAMES)
GROUP_IDS = ["G1_activity_volume", "G2_error", "G3_termination", "G4_repetition"]
VARIANT_IDS = [
    "S0_full13",
    "S1_no_termination",
    "S2_no_repetition",
    "S3_no_activity_volume",
    "S4_no_error",
    "S5_no_termination_or_repetition",
    "S6_termination_repetition_only",
]


class IntegrityError(RuntimeError):
    """Raised when a frozen A1.5 scientific invariant is violated."""


@dataclass
class FitAudit:
    """Count real-data preprocessing and estimator fits during a formal run."""

    scaler_fit_count: int = 0
    estimator_fit_count: int = 0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if path != REPO_ROOT and REPO_ROOT not in path.parents:
        raise IntegrityError(f"configured path escapes repository: {path_text}")
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    """Write canonical UTF-8, LF-only CSV bytes atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    a12.write_json(path, value)


def git_output(arguments: Sequence[str], text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=text
    )
    return result.stdout


def _variant_features(config: dict[str, Any]) -> dict[str, list[str]]:
    groups = config["feature_groups"]
    result: dict[str, list[str]] = {}
    for variant in config["variants"]:
        included = set(
            feature
            for group_id in variant["include_groups"]
            for feature in groups[group_id]
        )
        result[variant["id"]] = [name for name in FEATURE_NAMES if name in included]
    return result


def _expected_variant_features(config: dict[str, Any]) -> dict[str, list[str]]:
    groups = config["feature_groups"]
    g1, g2, g3, g4 = (set(groups[group]) for group in GROUP_IDS)
    expected_sets = {
        "S0_full13": g1 | g2 | g3 | g4,
        "S1_no_termination": g1 | g2 | g4,
        "S2_no_repetition": g1 | g2 | g3,
        "S3_no_activity_volume": g2 | g3 | g4,
        "S4_no_error": g1 | g3 | g4,
        "S5_no_termination_or_repetition": g1 | g2,
        "S6_termination_repetition_only": g3 | g4,
    }
    return {
        variant: [name for name in FEATURE_NAMES if name in features]
        for variant, features in expected_sets.items()
    }


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the complete preregistered A1.5 protocol."""

    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config["stage"] != "A1.5":
        raise IntegrityError("execution config is not Stage A1.5")
    if list(config["targets"]) != TARGETS or config["held_out_groups"] != HELD_OUT_GROUPS:
        raise IntegrityError("targets or primary four held-out groups changed")
    if config["structural_features"] != FEATURE_NAMES or len(FEATURE_NAMES) != 13:
        raise IntegrityError("frozen structural feature names/order changed")
    if list(config["feature_groups"]) != GROUP_IDS:
        raise IntegrityError("feature groups are not exactly G1--G4 in frozen order")
    flattened = [feature for group in GROUP_IDS for feature in config["feature_groups"][group]]
    if len(flattened) != 13 or len(set(flattened)) != 13 or set(flattened) != set(FEATURE_NAMES):
        raise IntegrityError("feature groups are not disjoint and exhaustive")
    if [row["id"] for row in config["variants"]] != VARIANT_IDS:
        raise IntegrityError("variants are not exactly S0--S6 in frozen order")
    actual = _variant_features(config)
    if actual != _expected_variant_features(config):
        raise IntegrityError("variant feature subsets differ from the preregistration")
    if [len(actual[variant]) for variant in VARIANT_IDS] != [13, 12, 11, 5, 11, 10, 3]:
        raise IntegrityError("variant feature counts changed")
    lr = config["logistic_regression"]
    fixed = {
        "penalty": "l2", "solver": "liblinear", "max_iter": 5000,
        "fit_intercept": True, "random_state": 2026,
    }
    if any(lr[key] != value for key, value in fixed.items()):
        raise IntegrityError("B2 Logistic Regression semantics changed")
    if lr["C"] != [0.1, 1.0, 10.0] or lr["class_weight"] != [None, "balanced"]:
        raise IntegrityError("candidate configuration grid changed")
    thresholds = [round(float(value), 2) for value in config["selection"]["thresholds"]]
    if thresholds != [round(value / 100, 2) for value in range(5, 100, 5)]:
        raise IntegrityError("threshold grid is not exactly 0.05..0.95")
    execution = config["execution"]
    if execution["test_access"] is not False:
        raise IntegrityError("test access is not frozen to false")
    if execution["regenerate_outer_or_inner_splits"] is not False:
        raise IntegrityError("split regeneration is not frozen off")
    if execution["model_input_exactly"] != "artifacts/dev_structural_features.csv":
        raise IntegrityError("model input is not exactly the frozen feature CSV")
    required_forbidden = {
        "test", "B3_new_experiment", "tfidf", "B2_B3_fusion",
        "new_structural_features", "single_feature_13_exhaustive", "shap",
        "permutation_importance", "secondary_lobo", "lomo",
        "joint_task_model_ood", "reasoning_input", "error_ablation_input",
        "embedding", "mlp", "random_forest", "xgboost", "transformer", "llm_judge",
    }
    if set(execution["forbidden_experiments"]) != required_forbidden:
        raise IntegrityError("forbidden experiment boundary changed")
    return config


def candidate_configs(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the six B2 candidates in the frozen tie-break order."""

    rows: list[dict[str, Any]] = []
    for weight in [None, "balanced"]:
        for c_value in [0.1, 1.0, 10.0]:
            c_id = str(c_value).replace(".", "p")
            weight_id = "none" if weight is None else "balanced"
            rows.append(
                {
                    "config_id": f"B2_C{c_id}_cw_{weight_id}",
                    "C": c_value,
                    "class_weight": weight,
                }
            )
    if len(rows) != 6:
        raise IntegrityError("B2 candidate count is not six")
    return rows


def _hash_specs(config: dict[str, Any]) -> list[dict[str, str]]:
    specs: list[dict[str, str]] = []
    for section in ["inputs", "a1_3_formal", "a1_4_formal"]:
        specs.extend(config[section].values())
    specs.extend(
        [
            config["environment"]["lock_file"],
            config["environment"]["baseline_environment"],
            config["environment"]["source_manifest"],
        ]
    )
    return specs


def _assert_committed_bytes(path: Path, spec: dict[str, str] | None = None) -> None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    try:
        committed = git_output(["show", f"HEAD:{relative}"], text=False)
    except subprocess.CalledProcessError as error:
        raise IntegrityError(f"required frozen file is not committed at HEAD: {relative}") from error
    working = path.read_bytes()
    if committed == working:
        return
    if spec and spec.get("line_endings") == "crlf_worktree_lf_git_blob":
        if a12.sha256_path(path) != spec["sha256"]:
            raise IntegrityError(f"working-byte hash changed for {relative}")
        if hashlib.sha256(committed).hexdigest() != spec["git_blob_sha256"]:
            raise IntegrityError(f"Git-blob hash changed for {relative}")
        if working.count(b"\r\n") != working.count(b"\n") or b"\r" in working.replace(b"\r\n", b""):
            raise IntegrityError(f"working file is not uniformly CRLF: {relative}")
        if working.replace(b"\r\n", b"\n") != committed:
            raise IntegrityError(f"CRLF/LF normalization is not the only byte difference: {relative}")
        return
    raise IntegrityError(f"line-ending/byte guard failed for {relative}")


def verify_frozen_hashes(config: dict[str, Any]) -> dict[str, str]:
    """Verify SHA-256 and Git bytes for all upstream frozen artifacts."""

    verified: dict[str, str] = {}
    for spec in _hash_specs(config):
        path = resolve(spec["path"])
        if not path.is_file():
            raise IntegrityError(f"required frozen file missing: {spec['path']}")
        actual = a12.sha256_path(path)
        if actual != spec["sha256"]:
            raise IntegrityError(
                f"SHA-256 mismatch for {spec['path']}: {actual} != {spec['sha256']}"
            )
        _assert_committed_bytes(path, spec)
        verified[spec["path"]] = actual
    return verified


def verify_upstream_commits(config: dict[str, Any]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for name, spec in config["approved_upstream"].items():
        actual_commit = str(git_output(["rev-parse", spec["commit"]])).strip()
        actual_subject = str(git_output(["show", "-s", "--format=%s", spec["commit"]])).strip()
        if actual_commit != spec["commit"] or actual_subject != spec["subject"]:
            raise IntegrityError(f"upstream commit/subject mismatch: {name}")
        verified[name] = actual_commit
    return verified


def verify_source_revisions(config: dict[str, Any]) -> dict[str, str]:
    source = json.loads(
        resolve(config["environment"]["source_manifest"]["path"]).read_text(encoding="utf-8")
    )
    if source["github_commit"] != config["source"]["github_commit"]:
        raise IntegrityError("fixed GitHub commit changed")
    if source["huggingface_revision"] != config["source"]["huggingface_revision"]:
        raise IntegrityError("fixed Hugging Face revision changed")
    return {
        "github_commit": source["github_commit"],
        "huggingface_revision": source["huggingface_revision"],
    }


def _load_labels(config: dict[str, Any]) -> dict[str, dict[str, int]]:
    rows = read_csv(resolve(config["inputs"]["label_index"]["path"]))
    if len(rows) != 196 or len({row["trajectory_key"] for row in rows}) != 196:
        raise IntegrityError("dev label index must contain 196 unique trajectory keys")
    columns = {
        "success": ("success_eligible_main", "success_label"),
        "side_effect": ("side_effect_eligible_main", "side_effect_label"),
        "looping": ("looping_eligible_main", "looping_label"),
    }
    labels: dict[str, dict[str, int]] = {}
    for target, (eligible_column, label_column) in columns.items():
        labels[target] = {
            row["trajectory_key"]: int(row[label_column])
            for row in rows
            if a12.is_true(row[eligible_column])
        }
        expected = config["targets"][target]
        actual = (
            len(labels[target]),
            len(labels[target]) - sum(labels[target].values()),
            sum(labels[target].values()),
        )
        wanted = (
            expected["expected_samples"],
            expected["expected_negative"],
            expected["expected_positive"],
        )
        if actual != wanted:
            raise IntegrityError(f"label counts changed for {target}: {actual} != {wanted}")
    return labels


def _load_structural(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = read_csv(resolve(config["inputs"]["structural_features"]["path"]))
    expected_schema = ["trajectory_key", *FEATURE_NAMES, "content_sha256"]
    if not rows or list(rows[0]) != expected_schema:
        raise IntegrityError("structural feature schema/order changed")
    result = {row["trajectory_key"]: row for row in rows}
    if len(rows) != 196 or len(result) != 196:
        raise IntegrityError("structural feature CSV must contain 196 unique rows")
    for key, row in result.items():
        for name in FEATURE_NAMES:
            value = float(row[name])
            if not math.isfinite(value):
                raise IntegrityError(f"non-finite structural feature: {key}/{name}")
    return result


def validate_outer_and_inner_reuse(
    config: dict[str, Any], labels: dict[str, dict[str, int]]
) -> tuple[list[dict[str, str]], dict[str, dict[str, int]], dict[str, Any]]:
    """Validate the existing A1.3 splits without generating any assignment."""

    manifest = read_csv(resolve(config["inputs"]["primary_lobo_manifest"]["path"]))
    folds = read_csv(resolve(config["inputs"]["a1_3_inner_folds"]["path"]))
    if len(manifest) != 2332 or len(folds) != 2332:
        raise IntegrityError("primary manifest or frozen inner folds is not 2332 rows")
    manifest_keyed = {
        (row["target"], row["held_out_group"], row["trajectory_key"]): row
        for row in manifest
    }
    fold_keyed = {
        (row["target"], row["held_out_group"], row["trajectory_key"]): row
        for row in folds
    }
    if len(manifest_keyed) != 2332 or set(manifest_keyed) != set(fold_keyed):
        raise IntegrityError("outer and inner artifacts do not cover identical unique cells")
    appearances: Counter[tuple[str, str]] = Counter()
    stats: dict[str, Any] = {target: {} for target in TARGETS}
    inner_counts: dict[str, dict[str, int]] = {target: {} for target in TARGETS}
    for key, outer in manifest_keyed.items():
        inner = fold_keyed[key]
        target, heldout, trajectory_key = key
        if target not in TARGETS or heldout not in HELD_OUT_GROUPS:
            raise IntegrityError("non-primary target/group entered the A1.5 split")
        if outer["protocol"] != "primary_four_group" or inner["protocol"] != "primary_four_group":
            raise IntegrityError("non-primary protocol entered the A1.5 split")
        if trajectory_key not in labels[target] or int(outer["label"]) != labels[target][trajectory_key]:
            raise IntegrityError("outer label differs from the frozen dev label index")
        if int(inner["label"]) != labels[target][trajectory_key]:
            raise IntegrityError("inner label differs from the frozen dev label index")
        expected_inner_role = "held_out" if outer["role"] == "validation" else "train"
        if inner["role"] != expected_inner_role:
            raise IntegrityError("frozen outer/inner role mapping changed")
        if outer["group_key"] != inner["group_key"]:
            raise IntegrityError("group key changed between outer and inner artifacts")
        if expected_inner_role == "held_out" and inner["inner_fold"].strip():
            raise IntegrityError("held-out Benchmark has an inner-fold assignment")
        appearances[(target, trajectory_key)] += 1
    if set(appearances.values()) != {4}:
        raise IntegrityError("each eligible target trajectory must appear in four LOBO cells")
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            cell = [
                row for row in folds
                if row["target"] == target and row["held_out_group"] == heldout
            ]
            train = [row for row in cell if row["role"] == "train"]
            held = [row for row in cell if row["role"] == "held_out"]
            if {row["trajectory_key"] for row in train} & {row["trajectory_key"] for row in held}:
                raise IntegrityError("held-out trajectory entered inner training")
            if {row["group_key"] for row in train} & {row["group_key"] for row in held}:
                raise IntegrityError("held-out task group entered inner training")
            n_values = {int(row["inner_n_splits"]) for row in cell}
            if len(n_values) != 1:
                raise IntegrityError("multiple inner-fold counts in one frozen cell")
            n_splits = n_values.pop()
            if {int(row["inner_fold"]) for row in train} != set(range(1, n_splits + 1)):
                raise IntegrityError("frozen inner folds are incomplete")
            for fold in range(1, n_splits + 1):
                inner_train = [row for row in train if int(row["inner_fold"]) != fold]
                inner_valid = [row for row in train if int(row["inner_fold"]) == fold]
                if {row["group_key"] for row in inner_train} & {row["group_key"] for row in inner_valid}:
                    raise IntegrityError("task-group leakage inside frozen inner folds")
                if {int(row["label"]) for row in inner_train} != {0, 1}:
                    raise IntegrityError("inner training partition is not mixed class")
            positive = sum(int(row["label"]) for row in held)
            actual = {
                "samples": len(held),
                "task_groups": len({row["group_key"] for row in held}),
                "positive": positive,
                "negative": len(held) - positive,
            }
            if actual != config["targets"][target]["held_out"][heldout]:
                raise IntegrityError(f"held-out statistics changed for {target}/{heldout}")
            stats[target][heldout] = {**actual, "train_samples": len(train)}
            inner_counts[target][heldout] = n_splits
    if stats["side_effect"]["assistantbench"]["positive"] != 0:
        raise IntegrityError("Side Effect / AssistantBench is no longer single-class negative")
    return folds, inner_counts, stats


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Audit all real-dev guards without fitting a scaler or estimator."""

    verified_hashes = verify_frozen_hashes(config)
    verified_commits = verify_upstream_commits(config)
    source_revisions = verify_source_revisions(config)
    labels = _load_labels(config)
    structural = _load_structural(config)
    if set(structural) != set().union(*(set(rows) for rows in labels.values())):
        raise IntegrityError("structural keys differ from the union of eligible dev keys")
    folds, inner_counts, stats = validate_outer_and_inner_reuse(config, labels)
    return {
        "verified_hashes": verified_hashes,
        "verified_commits": verified_commits,
        "source_revisions": source_revisions,
        "labels": labels,
        "structural": structural,
        "folds": folds,
        "inner_counts": inner_counts,
        "held_out_statistics": stats,
    }


REGISTRY_FIELDS = [
    "variant_id", "feature_name", "feature_group", "included", "feature_order"
]


def feature_registry_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    features = _variant_features(config)
    group_by_feature = {
        feature: group for group, names in config["feature_groups"].items() for feature in names
    }
    return [
        {
            "variant_id": variant,
            "feature_name": feature,
            "feature_group": group_by_feature[feature],
            "included": feature in features[variant],
            "feature_order": order,
        }
        for variant in VARIANT_IDS
        for order, feature in enumerate(FEATURE_NAMES, 1)
    ]


def write_prerun(config: dict[str, Any]) -> None:
    """Freeze registries and real-dev integrity evidence with zero fits."""

    checked = preflight(config)
    registry_path = resolve(config["outputs"]["feature_group_registry"])
    write_csv(registry_path, feature_registry_rows(config), REGISTRY_FIELDS)
    formal_paths = [
        path for key, path in config["outputs"].items() if key != "feature_group_registry"
    ]
    existing = [path for path in formal_paths if resolve(path).exists()]
    if existing:
        raise IntegrityError(f"formal A1.5 outputs already exist before preregistration: {existing}")
    integrity = {
        "stage": "A1.5a",
        "status": "PASS",
        "generated_at_utc": utc_now(),
        "real_dev_scaler_fit_count": 0,
        "real_dev_estimator_fit_count": 0,
        "formal_prediction_count": 0,
        "verified_hashes": checked["verified_hashes"],
        "verified_upstream_commits": checked["verified_commits"],
        "source_revisions": checked["source_revisions"],
        "script_sha256": a12.sha256_path(Path(__file__).resolve()),
        "config_sha256": a12.sha256_path(CONFIG_PATH),
        "feature_registry_sha256": a12.sha256_path(registry_path),
        "feature_groups": config["feature_groups"],
        "variant_features": _variant_features(config),
        "candidate_config_count_per_variant": len(candidate_configs(config)),
        "threshold_count": len(config["selection"]["thresholds"]),
        "inner_fold_counts": checked["inner_counts"],
        "held_out_statistics": checked["held_out_statistics"],
        "outer_manifest_reused_not_regenerated": True,
        "inner_folds_reused_not_regenerated": True,
        "test_access": {
            "manifest": 0, "trajectory_content": 0, "labels": 0,
            "predictions": 0, "metrics": 0,
        },
        "forbidden_experiments_executed": [],
    }
    write_json(resolve(config["environment"]["prerun_integrity_artifact"]), integrity)
    print(json.dumps({"status": "PASS", "mode": "write-prerun", "real_dev_fit_count": 0}))


def _assert_clean_start(config: dict[str, Any]) -> str:
    status = str(git_output(["status", "--porcelain=v1"])).strip()
    if status:
        raise IntegrityError(f"formal run requires clean worktree; found: {status}")
    subject = str(git_output(["show", "-s", "--format=%s", "HEAD"])).strip()
    if subject != config["execution"]["required_preregistration_commit_subject"]:
        raise IntegrityError(f"HEAD is not the A1.5a preregistration commit: {subject}")
    return str(git_output(["rev-parse", "HEAD"])).strip()


def assert_preregistered_bytes(config: dict[str, Any]) -> dict[str, Any]:
    integrity_path = resolve(config["environment"]["prerun_integrity_artifact"])
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    paths = {
        "script_sha256": Path(__file__).resolve(),
        "config_sha256": CONFIG_PATH,
        "feature_registry_sha256": resolve(config["outputs"]["feature_group_registry"]),
    }
    for field, path in paths.items():
        if integrity[field] != a12.sha256_path(path):
            raise IntegrityError(f"working {path.name} differs from preregistered hash")
        _assert_committed_bytes(path)
    _assert_committed_bytes(integrity_path)
    if integrity["real_dev_estimator_fit_count"] != 0 or integrity["formal_prediction_count"] != 0:
        raise IntegrityError("A1.5a does not prove zero real-dev fits/predictions")
    return integrity


def _matrix(
    structural: dict[str, dict[str, str]], keys: Sequence[str], feature_names: Sequence[str]
) -> np.ndarray:
    return np.asarray(
        [[float(structural[key][name]) for name in feature_names] for key in keys],
        dtype=float,
    )


def fit_predict(
    config: dict[str, Any], candidate: dict[str, Any], train_keys: Sequence[str],
    validation_keys: Sequence[str], labels: dict[str, int],
    structural: dict[str, dict[str, str]], feature_names: Sequence[str],
    context: dict[str, Any], warnings_out: list[dict[str, Any]], fit_audit: FitAudit,
) -> np.ndarray:
    """Fit only StandardScaler + frozen LogisticRegression and return P(y=1)."""

    y_train = [labels[key] for key in train_keys]
    if set(y_train) != {0, 1}:
        raise IntegrityError(f"training partition is not mixed class: {context}")
    scaler = StandardScaler()
    fit_audit.scaler_fit_count += 1
    x_train = scaler.fit_transform(_matrix(structural, train_keys, feature_names))
    x_validation = scaler.transform(_matrix(structural, validation_keys, feature_names))
    model = a12.make_lr(config, candidate)
    fit_audit.estimator_fit_count += 1
    model = a12._fit_with_warning_capture(
        model, x_train, y_train, {**context, "config_id": candidate["config_id"]}, warnings_out
    )
    return a12.positive_probability(model, x_validation)


DOMAIN_FIELDS = [
    "target", "variant_id", "held_out_group", "held_out_size", "task_group_count",
    "positive_count", "negative_count", "prevalence", "predicted_positive_count",
    "predicted_positive_rate", "selected_config_id", "selected_threshold",
    "inner_n_splits", "metric_status", *METRIC_NAMES, "ap_lift",
    "false_positive_count", "false_positive_rate", "specificity",
    "probability_mean", "probability_median", "probability_max",
]


def metric_row(
    target: str, variant: str, heldout: str, rows: Sequence[dict[str, Any]],
    selected_config: str, threshold: float, n_splits: int, task_groups: int,
) -> dict[str, Any]:
    truth = [int(row["true_label"]) for row in rows]
    probabilities = [float(row["predicted_probability"]) for row in rows]
    predicted = [int(row["predicted_label"]) for row in rows]
    positive, negative = sum(truth), len(truth) - sum(truth)
    base: dict[str, Any] = {
        "target": target, "variant_id": variant, "held_out_group": heldout,
        "held_out_size": len(rows), "task_group_count": task_groups,
        "positive_count": positive, "negative_count": negative,
        "prevalence": positive / len(rows), "predicted_positive_count": sum(predicted),
        "predicted_positive_rate": sum(predicted) / len(rows),
        "selected_config_id": selected_config, "selected_threshold": threshold,
        "inner_n_splits": n_splits,
    }
    if positive == 0 or negative == 0:
        base["metric_status"] = "single_class_negative" if positive == 0 else "single_class_positive"
        for name in [*METRIC_NAMES, "ap_lift"]:
            base[name] = None
        false_positive = sum(predicted) if positive == 0 else None
        base.update(
            {
                "false_positive_count": false_positive,
                "false_positive_rate": false_positive / negative if positive == 0 else None,
                "specificity": 1.0 - false_positive / negative if positive == 0 else None,
                "probability_mean": float(np.mean(probabilities)),
                "probability_median": float(np.median(probabilities)),
                "probability_max": float(np.max(probabilities)),
            }
        )
        return base
    base["metric_status"] = "ok"
    base.update(a12.metrics(truth, probabilities, predicted))
    base["ap_lift"] = base["pr_auc_average_precision"] - base["prevalence"]
    false_positive = sum(
        1 for y_true, y_pred in zip(truth, predicted, strict=True)
        if y_true == 0 and y_pred == 1
    )
    base.update(
        {
            "false_positive_count": false_positive,
            "false_positive_rate": false_positive / negative,
            "specificity": 1.0 - false_positive / negative,
            "probability_mean": float(np.mean(probabilities)),
            "probability_median": float(np.median(probabilities)),
            "probability_max": float(np.max(probabilities)),
        }
    )
    return base


def macro_rows(domain_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for variant in VARIANT_IDS:
            cell = [
                row for row in domain_rows
                if row["target"] == target and row["variant_id"] == variant
            ]
            if not cell:
                continue
            valid = [row for row in cell if row["metric_status"] == "ok"]
            if len(cell) != 4 or not valid:
                raise IntegrityError(f"domain coverage incomplete for {target}/{variant}")
            row: dict[str, Any] = {
                "target": target, "variant_id": variant,
                "valid_domain_count": len(valid),
                "excluded_single_class_domain_count": len(cell) - len(valid),
            }
            for metric in [*METRIC_NAMES, "ap_lift"]:
                values = [float(item[metric]) for item in valid]
                row[f"{metric}_macro_mean"] = statistics.mean(values)
                row[f"{metric}_macro_std"] = (
                    statistics.stdev(values) if len(values) > 1 else None
                )
            output.append(row)
    return output


def pooled_rows(predictions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for variant in VARIANT_IDS:
            cell = [
                row for row in predictions
                if row["target"] == target and row["variant_id"] == variant
            ]
            if not cell:
                continue
            truth = [int(row["true_label"]) for row in cell]
            probabilities = [float(row["predicted_probability"]) for row in cell]
            predicted = [int(row["predicted_label"]) for row in cell]
            prevalence = sum(truth) / len(truth)
            row = {
                "target": target, "variant_id": variant, "sample_count": len(cell),
                "positive_count": sum(truth), "negative_count": len(truth) - sum(truth),
                "prevalence": prevalence,
            }
            row.update(a12.metrics(truth, probabilities, predicted))
            row["ap_lift"] = row["pr_auc_average_precision"] - prevalence
            output.append(row)
    return output


def retained_ap_lift_ratio(variant_lift: float, s0_lift: float) -> float | None:
    if s0_lift <= 0:
        return None
    if variant_lift <= 0:
        return 0.0
    return variant_lift / s0_lift


def dependency_classification(
    config: dict[str, Any], target: str, variant: str, ratio: float | None,
    domain_deltas: Sequence[float],
) -> str:
    rules = config["dependency_classification"]
    if variant == "S0_full13":
        return rules["reference_classification"]
    if variant == "S6_termination_repetition_only":
        return rules["sufficiency_classification"]
    if ratio is None:
        return rules["nonpositive_s0_lift_classification"]
    decline_count = sum(delta < 0 for delta in domain_deltas)
    large_decline_count = sum(delta <= -0.05 for delta in domain_deltas)
    required_declines = math.ceil(
        rules["strong"]["mixed_domain_ap_decline_fraction_gte"] * len(domain_deltas)
    )
    if (
        ratio < rules["strong"]["retained_ap_lift_ratio_lt"]
        and decline_count >= required_declines
        and large_decline_count
        >= rules["strong"]["domains_with_absolute_ap_decline_gte_0p05"]
    ):
        return "strong_dependency"
    if (
        rules["moderate"]["retained_ap_lift_ratio_gte"] <= ratio
        < rules["moderate"]["retained_ap_lift_ratio_lt"]
        and decline_count > len(domain_deltas) / 2
    ):
        return "moderate_dependency"
    return "limited_dependency"


DELTA_FIELDS = [
    "target", "held_out_group", "variant_id", "delta_AP", "delta_F1",
    "delta_AP_lift", "macro_delta_AP", "macro_delta_F1", "pooled_delta_AP",
    "pooled_delta_F1", "retained_AP_lift_ratio", "mixed_domain_ap_decline_count",
    "mixed_domain_count", "domains_with_ap_decline_gte_0p05",
    "frozen_dependency_classification",
]


def delta_rows(
    config: dict[str, Any], domain: Sequence[dict[str, Any]],
    macro: Sequence[dict[str, Any]], pooled: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    domain_index = {
        (row["target"], row["variant_id"], row["held_out_group"]): row for row in domain
    }
    macro_index = {(row["target"], row["variant_id"]): row for row in macro}
    pooled_index = {(row["target"], row["variant_id"]): row for row in pooled}
    for target in TARGETS:
        s0_macro = macro_index[(target, "S0_full13")]
        s0_pooled = pooled_index[(target, "S0_full13")]
        for variant in VARIANT_IDS:
            current_macro = macro_index[(target, variant)]
            current_pooled = pooled_index[(target, variant)]
            ratio = retained_ap_lift_ratio(
                float(current_pooled["ap_lift"]), float(s0_pooled["ap_lift"])
            )
            mixed_deltas: list[float] = []
            for heldout in HELD_OUT_GROUPS:
                current = domain_index[(target, variant, heldout)]
                reference = domain_index[(target, "S0_full13", heldout)]
                if current["metric_status"] == "ok" and reference["metric_status"] == "ok":
                    mixed_deltas.append(
                        float(current["pr_auc_average_precision"])
                        - float(reference["pr_auc_average_precision"])
                    )
            grade = dependency_classification(config, target, variant, ratio, mixed_deltas)
            decline_count = sum(delta < 0 for delta in mixed_deltas)
            large_declines = sum(delta <= -0.05 for delta in mixed_deltas)
            for heldout in HELD_OUT_GROUPS:
                current = domain_index[(target, variant, heldout)]
                reference = domain_index[(target, "S0_full13", heldout)]
                if current["metric_status"] == "ok" and reference["metric_status"] == "ok":
                    delta_ap = float(current["pr_auc_average_precision"]) - float(
                        reference["pr_auc_average_precision"]
                    )
                    delta_f1 = float(current["positive_f1"]) - float(reference["positive_f1"])
                    delta_lift = float(current["ap_lift"]) - float(reference["ap_lift"])
                else:
                    delta_ap = delta_f1 = delta_lift = None
                output.append(
                    {
                        "target": target, "held_out_group": heldout, "variant_id": variant,
                        "delta_AP": delta_ap, "delta_F1": delta_f1,
                        "delta_AP_lift": delta_lift,
                        "macro_delta_AP": float(current_macro["pr_auc_average_precision_macro_mean"])
                        - float(s0_macro["pr_auc_average_precision_macro_mean"]),
                        "macro_delta_F1": float(current_macro["positive_f1_macro_mean"])
                        - float(s0_macro["positive_f1_macro_mean"]),
                        "pooled_delta_AP": float(current_pooled["pr_auc_average_precision"])
                        - float(s0_pooled["pr_auc_average_precision"]),
                        "pooled_delta_F1": float(current_pooled["positive_f1"])
                        - float(s0_pooled["positive_f1"]),
                        "retained_AP_lift_ratio": ratio,
                        "mixed_domain_ap_decline_count": decline_count,
                        "mixed_domain_count": len(mixed_deltas),
                        "domains_with_ap_decline_gte_0p05": large_declines,
                        "frozen_dependency_classification": grade,
                    }
                )
    return output


def _run_variant(
    config: dict[str, Any], checked: dict[str, Any], variant: str,
    warnings_out: list[dict[str, Any]], fit_audit: FitAudit,
) -> dict[str, list[dict[str, Any]]]:
    features = _variant_features(config)[variant]
    folds = checked["folds"]
    candidates = candidate_configs(config)
    config_rows: list[dict[str, Any]] = []
    inner_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    domain: list[dict[str, Any]] = []
    for target in TARGETS:
        labels = checked["labels"][target]
        for heldout in HELD_OUT_GROUPS:
            cell = [
                row for row in folds
                if row["target"] == target and row["held_out_group"] == heldout
            ]
            train_rows = [row for row in cell if row["role"] == "train"]
            held_rows = [row for row in cell if row["role"] == "held_out"]
            train_keys = [row["trajectory_key"] for row in train_rows]
            held_keys = [row["trajectory_key"] for row in held_rows]
            n_splits = checked["inner_counts"][target][heldout]
            candidate_oof: dict[str, dict[str, float]] = {}
            for rank, candidate in enumerate(candidates, 1):
                oof: dict[str, float] = {}
                for fold in range(1, n_splits + 1):
                    validation_keys = [
                        row["trajectory_key"] for row in train_rows
                        if int(row["inner_fold"]) == fold
                    ]
                    fit_keys = [
                        row["trajectory_key"] for row in train_rows
                        if int(row["inner_fold"]) != fold
                    ]
                    probabilities = fit_predict(
                        config, candidate, fit_keys, validation_keys, labels,
                        checked["structural"], features,
                        {
                            "target": target, "variant_id": variant,
                            "held_out_group": heldout, "phase": "inner", "inner_fold": fold,
                        },
                        warnings_out, fit_audit,
                    )
                    for key, probability in zip(validation_keys, probabilities, strict=True):
                        if key in oof:
                            raise IntegrityError("duplicate selected inner OOF prediction")
                        oof[key] = float(probability)
                if set(oof) != set(train_keys):
                    raise IntegrityError("candidate pooled inner OOF is incomplete")
                score = float(
                    average_precision_score(
                        [labels[key] for key in train_keys], [oof[key] for key in train_keys]
                    )
                )
                config_rows.append(
                    {
                        "target": target, "held_out_group": heldout, "variant_id": variant,
                        "config_id": candidate["config_id"], "inner_n_splits": n_splits,
                        "inner_oof_size": len(oof), "inner_oof_pr_auc": score,
                        "selected": False, "tie_break_rank": rank,
                    }
                )
                candidate_oof[candidate["config_id"]] = oof
            selection = config_rows[-len(candidates):]
            best_score = max(float(row["inner_oof_pr_auc"]) for row in selection)
            selected_row = min(
                (
                    row for row in selection
                    if math.isclose(
                        float(row["inner_oof_pr_auc"]), best_score, rel_tol=0, abs_tol=1e-15
                    )
                ),
                key=lambda row: (int(row["tie_break_rank"]), row["config_id"]),
            )
            selected_row["selected"] = True
            selected_id = selected_row["config_id"]
            selected_candidate = next(
                candidate for candidate in candidates if candidate["config_id"] == selected_id
            )
            selected_oof = candidate_oof[selected_id]
            threshold, tested = a12.select_threshold(
                config,
                [labels[key] for key in train_keys],
                [selected_oof[key] for key in train_keys],
            )
            fold_by_key = {
                row["trajectory_key"]: int(row["inner_fold"]) for row in train_rows
            }
            for key in train_keys:
                inner_rows.append(
                    {
                        "trajectory_key": key, "target": target, "variant_id": variant,
                        "held_out_group": heldout, "inner_fold": fold_by_key[key],
                        "true_label": labels[key],
                        "predicted_probability": selected_oof[key],
                        "selected_config_id": selected_id, "inner_n_splits": n_splits,
                    }
                )
            for row in tested:
                threshold_rows.append(
                    {
                        "target": target, "held_out_group": heldout, "variant_id": variant,
                        "selected_config_id": selected_id, **row,
                    }
                )
            external_probability = fit_predict(
                config, selected_candidate, train_keys, held_keys, labels,
                checked["structural"], features,
                {
                    "target": target, "variant_id": variant,
                    "held_out_group": heldout, "phase": "final_refit", "inner_fold": "",
                },
                warnings_out, fit_audit,
            )
            held_by_key = {row["trajectory_key"]: row for row in held_rows}
            external_rows: list[dict[str, Any]] = []
            for key, probability in zip(held_keys, external_probability, strict=True):
                source = held_by_key[key]
                row = {
                    "trajectory_key": key, "group_key": source["group_key"],
                    "target": target, "variant_id": variant, "held_out_group": heldout,
                    "true_label": labels[key], "predicted_probability": float(probability),
                    "selected_threshold": threshold,
                    "predicted_label": int(float(probability) >= threshold),
                    "selected_config_id": selected_id, "inner_n_splits": n_splits,
                }
                predictions.append(row)
                external_rows.append(row)
            domain.append(
                metric_row(
                    target, variant, heldout, external_rows, selected_id, threshold,
                    n_splits, len({row["group_key"] for row in held_rows}),
                )
            )
    return {
        "config": config_rows, "inner": inner_rows, "threshold": threshold_rows,
        "predictions": predictions, "domain": domain,
    }


def verify_s0_positive_control(
    config: dict[str, Any], result: dict[str, Sequence[dict[str, Any]]]
) -> dict[str, Any]:
    """Require exact A1.3 B2 selection/labels and <=1e-12 numeric error."""

    a13 = config["a1_3_formal"]
    source_config = [
        row for row in read_csv(resolve(a13["inner_config_selection"]["path"]))
        if row["baseline_id"] == "B2"
    ]
    source_threshold = [
        row for row in read_csv(resolve(a13["threshold_selection"]["path"]))
        if row["baseline_id"] == "B2"
    ]
    source_predictions = [
        row for row in read_csv(resolve(a13["predictions"]["path"]))
        if row["baseline_id"] == "B2"
    ]
    source_domain = [
        row for row in read_csv(resolve(a13["domain_metrics"]["path"]))
        if row["baseline_id"] == "B2"
    ]
    source_macro = [
        row for row in read_csv(resolve(a13["macro_metrics"]["path"]))
        if row["baseline_id"] == "B2"
    ]
    source_pooled = [
        row for row in read_csv(resolve(a13["pooled_metrics"]["path"]))
        if row["baseline_id"] == "B2"
    ]
    config_index = {
        (row["target"], row["held_out_group"], row["config_id"]): row
        for row in result["config"]
    }
    def selected_value(value: Any) -> bool:
        return value is True or str(value) == "True"

    for source in source_config:
        current = config_index[(source["target"], source["held_out_group"], source["config_id"])]
        if (source["selected"] == "True") != selected_value(current["selected"]):
            raise IntegrityError("S0 selected configuration differs from A1.3 B2")
    threshold_index = {
        (row["target"], row["held_out_group"], float(row["threshold"])): row
        for row in result["threshold"]
    }
    for source in source_threshold:
        current = threshold_index[
            (source["target"], source["held_out_group"], float(source["threshold"]))
        ]
        if (source["selected"] == "True") != selected_value(current["selected"]):
            raise IntegrityError("S0 selected threshold differs from A1.3 B2")
    prediction_index = {
        (row["target"], row["held_out_group"], row["trajectory_key"]): row
        for row in result["predictions"]
    }
    if len(source_predictions) != 583 or len(prediction_index) != 583:
        raise IntegrityError("S0/A1.3 B2 prediction coverage is not 583")
    max_probability_error = 0.0
    for source in source_predictions:
        key = (source["target"], source["held_out_group"], source["trajectory_key"])
        current = prediction_index[key]
        if (
            current["selected_config_id"] != source["selected_config_id"]
            or float(current["selected_threshold"]) != float(source["selected_threshold"])
            or int(current["true_label"]) != int(source["true_label"])
            or int(current["predicted_label"]) != int(source["predicted_label"])
        ):
            raise IntegrityError(f"S0 discrete prediction/config mismatch: {key}")
        error = abs(
            float(current["predicted_probability"]) - float(source["predicted_probability"])
        )
        max_probability_error = max(max_probability_error, error)
    tolerance = float(config["execution"]["s0_probability_metric_absolute_tolerance"])
    if max_probability_error > tolerance:
        raise IntegrityError(f"S0 probability error exceeds tolerance: {max_probability_error}")
    current_macro = macro_rows(result["domain"])
    current_pooled = pooled_rows(result["predictions"])
    max_metric_error = 0.0
    metric_checks = [
        (
            result["domain"], source_domain,
            ("target", "held_out_group"),
            ["pr_auc_average_precision", "positive_f1"],
        ),
        (
            current_macro, source_macro, ("target",),
            [
                "pr_auc_average_precision_macro_mean", "pr_auc_average_precision_macro_std",
                "positive_f1_macro_mean", "positive_f1_macro_std",
            ],
        ),
        (
            current_pooled, source_pooled, ("target",),
            ["pr_auc_average_precision", "positive_f1"],
        ),
    ]
    for current_rows, source_rows, key_fields, fields in metric_checks:
        current_index = {tuple(row[field] for field in key_fields): row for row in current_rows}
        for source in source_rows:
            current = current_index[tuple(source[field] for field in key_fields)]
            for field in fields:
                if source[field] == "":
                    if current[field] is not None:
                        raise IntegrityError(f"S0 single-class metric is not missing: {field}")
                else:
                    error = abs(float(current[field]) - float(source[field]))
                    max_metric_error = max(max_metric_error, error)
    if max_metric_error > tolerance:
        raise IntegrityError(f"S0 metric error exceeds tolerance: {max_metric_error}")
    return {
        "status": "PASS",
        "reference": "A1.3 B2",
        "config_exact": True,
        "threshold_exact": True,
        "predicted_labels_exact": True,
        "true_labels_exact": True,
        "external_prediction_count": 583,
        "max_probability_absolute_error": max_probability_error,
        "max_metric_absolute_error": max_metric_error,
        "tolerance": tolerance,
    }


def _frequency_rows(config_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(
        (row["target"], row["variant_id"], row["config_id"])
        for row in config_rows if bool(row["selected"])
    )
    return [
        {
            "target": target, "variant_id": variant,
            "config_id": candidate["config_id"],
            "selected_held_out_group_count": counts[(target, variant, candidate["config_id"])],
        }
        for target in TARGETS
        for variant in VARIANT_IDS
        for candidate in candidate_configs(load_config())
    ]


def _float_text(value: Any, signed: bool = False) -> str:
    if value is None or value == "":
        return "NA"
    return f"{float(value):+0.6f}" if signed else f"{float(value):0.6f}"


def render_report(config: dict[str, Any], result: dict[str, Any]) -> str:
    summary = result["summary"]
    macro = result["macro"]
    pooled = result["pooled"]
    domain = result["domain"]
    deltas = result["deltas"]
    lines = [
        "# Stage A1.5 structural mechanism ablation report", "",
        "## Stage determination", "", "`PASS_WITH_CONDITIONS`", "",
        "All technical completeness checks passed. Interpretation remains conditional because Side Effect has only 12 positives and one single-class held-out domain, known scikit-learn FutureWarnings are retained, and dependency grades are descriptive rather than causal.", "",
        "## Scope and provenance", "",
        f"- A1.5a preregistration commit: `{summary['preregistration_commit']}`",
        "- A1.5b experiment commit: recorded by the enclosing result commit.",
        f"- GitHub commit: `{config['source']['github_commit']}`",
        f"- Hugging Face revision: `{config['source']['huggingface_revision']}`",
        "- Official dev structural features only; A1.3 primary four-group LOBO outer manifest and frozen inner folds reused byte-for-byte.",
        "- test access: 0 in every category; prohibited experiments executed: 0.", "",
        "## Frozen feature groups", "",
    ]
    for group, names in config["feature_groups"].items():
        lines.append(f"- `{group}`: {', '.join(f'`{name}`' for name in names)}")
    lines.extend(["", "## Frozen variants", ""])
    for variant in config["variants"]:
        names = _variant_features(config)[variant["id"]]
        lines.append(f"- `{variant['id']}` ({len(names)} features): {', '.join(names)}")
    proof = summary["s0_positive_control"]
    lines.extend(
        [
            "", "## S0 positive control", "",
            f"S0 exactly reproduced A1.3 B2: config `{proof['config_exact']}`, threshold `{proof['threshold_exact']}`, labels `{proof['predicted_labels_exact']}`; maximum probability error `{proof['max_probability_absolute_error']:.3e}` and maximum metric error `{proof['max_metric_absolute_error']:.3e}` (tolerance `{proof['tolerance']:.1e}`).",
            "", "## Macro and pooled results", "",
            "| Target | Variant | Macro AP | Macro F1 | Pooled AP | Pooled F1 | AP lift | Retained AP-lift ratio | Grade |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    macro_index = {(row["target"], row["variant_id"]): row for row in macro}
    pooled_index = {(row["target"], row["variant_id"]): row for row in pooled}
    delta_index = {
        (row["target"], row["variant_id"]): row
        for row in deltas if row["held_out_group"] == HELD_OUT_GROUPS[0]
    }
    for target in TARGETS:
        for variant in VARIANT_IDS:
            m = macro_index[(target, variant)]
            p = pooled_index[(target, variant)]
            d = delta_index[(target, variant)]
            lines.append(
                f"| {target} | {variant} | {_float_text(m['pr_auc_average_precision_macro_mean'])} | {_float_text(m['positive_f1_macro_mean'])} | {_float_text(p['pr_auc_average_precision'])} | {_float_text(p['positive_f1'])} | {_float_text(p['ap_lift'])} | {_float_text(d['retained_AP_lift_ratio'])} | `{d['frozen_dependency_classification']}` |"
            )
    lines.extend(
        [
            "", "## Domain results", "",
            "| Target | Variant | Held-out | status | prevalence | AP | F1 | config | threshold |",
            "|---|---|---|---|---:|---:|---:|---|---:|",
        ]
    )
    for row in domain:
        lines.append(
            f"| {row['target']} | {row['variant_id']} | {row['held_out_group']} | {row['metric_status']} | {_float_text(row['prevalence'])} | {_float_text(row['pr_auc_average_precision'])} | {_float_text(row['positive_f1'])} | `{row['selected_config_id']}` | {_float_text(row['selected_threshold'])} |"
        )
    lines.extend(
        [
            "", "## Deltas relative to S0", "",
            "| Target | Variant | Macro ΔAP | Macro ΔF1 | Pooled ΔAP | Pooled ΔF1 | Retained ratio | Grade |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for target in TARGETS:
        for variant in VARIANT_IDS:
            row = delta_index[(target, variant)]
            lines.append(
                f"| {target} | {variant} | {_float_text(row['macro_delta_AP'], True)} | {_float_text(row['macro_delta_F1'], True)} | {_float_text(row['pooled_delta_AP'], True)} | {_float_text(row['pooled_delta_F1'], True)} | {_float_text(row['retained_AP_lift_ratio'])} | `{row['frozen_dependency_classification']}` |"
            )
    lines.extend(["", "## Registered mechanism questions", ""])
    for target, variants in {
        "success": ["S1_no_termination", "S2_no_repetition", "S5_no_termination_or_repetition", "S6_termination_repetition_only"],
        "looping": ["S2_no_repetition", "S5_no_termination_or_repetition", "S6_termination_repetition_only"],
    }.items():
        lines.append(f"### {target.title()}")
        lines.append("")
        for variant in variants:
            row = delta_index[(target, variant)]
            lines.append(
                f"- `{variant}`: retained AP-lift ratio {_float_text(row['retained_AP_lift_ratio'])}; pooled ΔAP {_float_text(row['pooled_delta_AP'], True)}; pooled ΔF1 {_float_text(row['pooled_delta_F1'], True)}; `{row['frozen_dependency_classification']}`."
            )
        lines.append("")
    side = [
        row for row in domain
        if row["target"] == "side_effect" and row["held_out_group"] == "assistantbench"
    ]
    lines.extend(
        [
            "## Side Effect diagnostic", "",
            "Side Effect remains diagnostic only: 12 positives overall, and AssistantBench contains 24 negatives and 0 positives. Dual-class metrics are missing rather than imputed.", "",
            "| Variant | predicted positives | FPR | specificity | probability mean/max |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in side:
        lines.append(
            f"| {row['variant_id']} | {row['predicted_positive_count']} | {_float_text(row['false_positive_rate'])} | {_float_text(row['specificity'])} | {_float_text(row['probability_mean'])}/{_float_text(row['probability_max'])} |"
        )
    counts = summary["row_counts"]
    lines.extend(
        [
            "", "## Integrity, warnings, and boundaries", "",
            f"- External predictions: {counts['external_predictions']}/4081.",
            f"- Selected inner OOF predictions: {counts['inner_selected_oof_predictions']}/12243.",
            f"- Configuration rows: {counts['inner_config_selection']}/504; threshold rows: {counts['threshold_selection']}/1596.",
            f"- Domain metrics: {counts['domain_metrics']}/84; pooled metrics: {counts['pooled_metrics']}/21.",
            f"- Warnings: {summary['warning_count']} total; convergence warnings: {summary['convergence_warning_count']}.",
            f"- Frozen hashes before/after identical: `{summary['hashes_before_run'] == summary['hashes_after_run']}`.",
            "- test content/labels/predictions/metrics access: 0; test manifest access: 0.",
            "- B3/TF-IDF, fusion, new features, single-feature exhaustive search, SHAP, permutation importance, secondary LOBO, LOMO, joint OOD, reasoning/error input, complex models, LLM Judge, and test experiments executed: 0.",
            "- These are frozen-protocol predictive dependencies, not causal feature effects or significance tests.",
            "", "## Stage recommendation and stop", "",
            "`PASS_WITH_CONDITIONS`. The completed evidence is suitable for human review of whether a later uncertainty-analysis stage should be authorized. A1.5 stops here and does not automatically enter Bootstrap, significance testing, fusion, complex models, secondary LOBO, joint OOD, or test.", "",
        ]
    )
    return "\n".join(lines)


def _write_outputs(config: dict[str, Any], result: dict[str, Any]) -> None:
    paths = config["outputs"]
    write_csv(
        resolve(paths["inner_config_selection"]), result["config"],
        [
            "target", "held_out_group", "variant_id", "config_id", "inner_n_splits",
            "inner_oof_size", "inner_oof_pr_auc", "selected", "tie_break_rank",
        ],
    )
    write_csv(
        resolve(paths["inner_selected_oof_predictions"]), result["inner"],
        [
            "trajectory_key", "target", "variant_id", "held_out_group", "inner_fold",
            "true_label", "predicted_probability", "selected_config_id", "inner_n_splits",
        ],
    )
    write_csv(
        resolve(paths["threshold_selection"]), result["threshold"],
        [
            "target", "held_out_group", "variant_id", "selected_config_id",
            "threshold", "inner_f1", "inner_precision", "inner_recall", "selected",
        ],
    )
    write_csv(
        resolve(paths["external_predictions"]), result["predictions"],
        [
            "trajectory_key", "group_key", "target", "variant_id", "held_out_group",
            "true_label", "predicted_probability", "selected_threshold",
            "predicted_label", "selected_config_id", "inner_n_splits",
        ],
    )
    write_csv(resolve(paths["domain_metrics"]), result["domain"], DOMAIN_FIELDS)
    macro_fields = [
        "target", "variant_id", "valid_domain_count", "excluded_single_class_domain_count",
        *[
            field for metric in [*METRIC_NAMES, "ap_lift"]
            for field in (f"{metric}_macro_mean", f"{metric}_macro_std")
        ],
    ]
    write_csv(resolve(paths["macro_metrics"]), result["macro"], macro_fields)
    write_csv(
        resolve(paths["pooled_metrics"]), result["pooled"],
        [
            "target", "variant_id", "sample_count", "positive_count", "negative_count",
            "prevalence", *METRIC_NAMES, "ap_lift",
        ],
    )
    write_csv(resolve(paths["structural_ablation_deltas"]), result["deltas"], DELTA_FIELDS)
    write_csv(
        resolve(paths["config_frequency"]), result["frequency"],
        ["target", "variant_id", "config_id", "selected_held_out_group_count"],
    )
    write_json(resolve(paths["run_summary"]), result["summary"])
    a12.atomic_write_text(resolve(paths["report"]), render_report(config, result))


def _compare_numeric(
    expected: Any, recorded: str, field: str, tolerance: float = 1e-12
) -> None:
    if expected is None:
        if recorded != "":
            raise IntegrityError(f"expected missing value for {field}")
    elif not math.isclose(float(expected), float(recorded), rel_tol=tolerance, abs_tol=tolerance):
        raise IntegrityError(f"cannot independently reproduce {field}")


def verify_results(config: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute formal A1.5 outputs without any fit."""

    checked = preflight(config)
    paths = config["outputs"]
    configs = read_csv(resolve(paths["inner_config_selection"]))
    inner = read_csv(resolve(paths["inner_selected_oof_predictions"]))
    thresholds = read_csv(resolve(paths["threshold_selection"]))
    predictions = read_csv(resolve(paths["external_predictions"]))
    domain = read_csv(resolve(paths["domain_metrics"]))
    macro = read_csv(resolve(paths["macro_metrics"]))
    pooled = read_csv(resolve(paths["pooled_metrics"]))
    deltas = read_csv(resolve(paths["structural_ablation_deltas"]))
    expected_counts = (504, 12243, 1596, 4081, 84, 21, 21, 84)
    actual_counts = (
        len(configs), len(inner), len(thresholds), len(predictions), len(domain),
        len(macro), len(pooled), len(deltas),
    )
    if actual_counts != expected_counts:
        raise IntegrityError(f"formal output row counts differ: {actual_counts}")
    if len({(row["target"], row["variant_id"], row["trajectory_key"]) for row in predictions}) != 4081:
        raise IntegrityError("external target/variant/trajectory predictions are not unique")
    if len({(row["target"], row["variant_id"], row["held_out_group"], row["trajectory_key"]) for row in inner}) != 12243:
        raise IntegrityError("selected inner OOF predictions are not unique")
    role_by_key = {
        (row["target"], row["held_out_group"], row["trajectory_key"]): row["role"]
        for row in checked["folds"]
    }
    if any(
        role_by_key[(row["target"], row["held_out_group"], row["trajectory_key"])]
        != "train" for row in inner
    ):
        raise IntegrityError("held-out Benchmark entered selected inner OOF")
    for target in TARGETS:
        for variant in VARIANT_IDS:
            for heldout in HELD_OUT_GROUPS:
                selection = [
                    row for row in configs
                    if row["target"] == target and row["variant_id"] == variant
                    and row["held_out_group"] == heldout
                ]
                if len(selection) != 6:
                    raise IntegrityError("cell does not contain exactly six configurations")
                best_score = max(float(row["inner_oof_pr_auc"]) for row in selection)
                expected = min(
                    (
                        row for row in selection
                        if math.isclose(
                            float(row["inner_oof_pr_auc"]), best_score,
                            rel_tol=0, abs_tol=1e-15,
                        )
                    ),
                    key=lambda row: (int(row["tie_break_rank"]), row["config_id"]),
                )
                selected = [row for row in selection if row["selected"] == "True"]
                if len(selected) != 1 or selected[0]["config_id"] != expected["config_id"]:
                    raise IntegrityError("configuration selection is not pooled-inner-OOF AP/tie-break")
                inner_cell = [
                    row for row in inner
                    if row["target"] == target and row["variant_id"] == variant
                    and row["held_out_group"] == heldout
                ]
                threshold, _ = a12.select_threshold(
                    config,
                    [int(row["true_label"]) for row in inner_cell],
                    [float(row["predicted_probability"]) for row in inner_cell],
                )
                threshold_cell = [
                    row for row in thresholds
                    if row["target"] == target and row["variant_id"] == variant
                    and row["held_out_group"] == heldout
                ]
                selected_threshold = [row for row in threshold_cell if row["selected"] == "True"]
                if len(threshold_cell) != 19 or len(selected_threshold) != 1:
                    raise IntegrityError("threshold cell is not exactly 19 rows with one selection")
                if float(selected_threshold[0]["threshold"]) != threshold:
                    raise IntegrityError("threshold is not selected from selected pooled inner OOF")
                external = [
                    row for row in predictions
                    if row["target"] == target and row["variant_id"] == variant
                    and row["held_out_group"] == heldout
                ]
                expected_keys = {
                    row["trajectory_key"] for row in checked["folds"]
                    if row["target"] == target and row["held_out_group"] == heldout
                    and row["role"] == "held_out"
                }
                if {row["trajectory_key"] for row in external} != expected_keys:
                    raise IntegrityError("external held-out coverage differs from A1.3")
                for row in external:
                    probability = float(row["predicted_probability"])
                    if (
                        not math.isfinite(probability) or not 0 <= probability <= 1
                        or int(row["predicted_label"])
                        != int(probability >= float(row["selected_threshold"]))
                    ):
                        raise IntegrityError("invalid external probability or predicted label")
                    if int(row["true_label"]) != checked["labels"][target][row["trajectory_key"]]:
                        raise IntegrityError("external truth differs from frozen dev labels")
    recomputed_domain: list[dict[str, Any]] = []
    for target in TARGETS:
        for variant in VARIANT_IDS:
            for heldout in HELD_OUT_GROUPS:
                external = [
                    row for row in predictions
                    if row["target"] == target and row["variant_id"] == variant
                    and row["held_out_group"] == heldout
                ]
                source = next(
                    row for row in domain
                    if row["target"] == target and row["variant_id"] == variant
                    and row["held_out_group"] == heldout
                )
                recomputed_domain.append(
                    metric_row(
                        target, variant, heldout, external, source["selected_config_id"],
                        float(source["selected_threshold"]), int(source["inner_n_splits"]),
                        int(source["task_group_count"]),
                    )
                )
    recorded_domain = {
        (row["target"], row["variant_id"], row["held_out_group"]): row for row in domain
    }
    for expected in recomputed_domain:
        recorded = recorded_domain[
            (expected["target"], expected["variant_id"], expected["held_out_group"])
        ]
        for field in [*METRIC_NAMES, "ap_lift", "false_positive_rate", "specificity"]:
            _compare_numeric(expected[field], recorded[field], field)
    recomputed_macro = macro_rows(recomputed_domain)
    recomputed_pooled = pooled_rows(predictions)
    recomputed_deltas = delta_rows(config, recomputed_domain, recomputed_macro, recomputed_pooled)
    for expected, recorded in zip(recomputed_macro, macro, strict=True):
        for metric in [*METRIC_NAMES, "ap_lift"]:
            for suffix in ["macro_mean", "macro_std"]:
                field = f"{metric}_{suffix}"
                _compare_numeric(expected[field], recorded[field], field)
    for expected, recorded in zip(recomputed_pooled, pooled, strict=True):
        for field in [*METRIC_NAMES, "ap_lift"]:
            _compare_numeric(expected[field], recorded[field], field)
    for expected, recorded in zip(recomputed_deltas, deltas, strict=True):
        for field in DELTA_FIELDS[3:-1]:
            _compare_numeric(expected[field], recorded[field], field)
        if expected["frozen_dependency_classification"] != recorded["frozen_dependency_classification"]:
            raise IntegrityError("frozen dependency classification cannot be reproduced")
    s0_result = {
        "config": [row for row in configs if row["variant_id"] == "S0_full13"],
        "threshold": [row for row in thresholds if row["variant_id"] == "S0_full13"],
        "predictions": [row for row in predictions if row["variant_id"] == "S0_full13"],
        "domain": [row for row in recomputed_domain if row["variant_id"] == "S0_full13"],
    }
    s0_proof = verify_s0_positive_control(config, s0_result)
    summary = json.loads(resolve(paths["run_summary"]).read_text(encoding="utf-8"))
    if summary["hashes_before_run"] != summary["hashes_after_run"]:
        raise IntegrityError("frozen hashes changed during formal run")
    if verify_frozen_hashes(config) != summary["hashes_after_run"]:
        raise IntegrityError("current frozen hashes differ from formal-run hashes")
    if summary["test_access"] != {
        "manifest": 0, "trajectory_content": 0, "labels": 0,
        "predictions": 0, "metrics": 0,
    }:
        raise IntegrityError("test access audit is nonzero")
    if summary["forbidden_experiments_executed"]:
        raise IntegrityError("a forbidden experiment was recorded")
    return {
        "status": "PASS_WITH_CONDITIONS",
        "external_predictions": len(predictions),
        "inner_selected_oof": len(inner),
        "config_rows": len(configs), "threshold_rows": len(thresholds),
        "domain_rows": len(domain), "pooled_rows": len(pooled),
        "s0_positive_control": s0_proof,
        "test_access": 0, "forbidden_experiments_executed": 0,
        "independent_recomputation": True,
    }


def _append_experiment_registry(
    run_id: str, prereg_commit: str, started: str, completed: str
) -> None:
    path = REPO_ROOT / "research" / "02_EXPERIMENT_REGISTRY.csv"
    rows = read_csv(path)
    if any(row["run_id"] == run_id for row in rows):
        raise IntegrityError(f"experiment registry already contains {run_id}")
    fields = list(rows[0])
    rows.append(
        {
            "run_id": run_id,
            "experiment_name": "Stage A1.5 structural mechanism ablations",
            "hypothesis_id": "H1",
            "git_commit": prereg_commit,
            "data_version": "dev_cleaned_v1",
            "split_version": "custom_deterministic_grouped_stratification_v1",
            "config_path": "configs/stage_a1_5_structural_ablation.yaml",
            "seed": "2026",
            "protocol": "A1.3 primary four-group LOBO structural ablation",
            "model": "B2 StandardScaler plus LogisticRegression; S0-S6",
            "start_time": started,
            "end_time": completed,
            "hardware": "Windows 11 AMD64 CPU only",
            "status": "PASS_WITH_CONDITIONS",
            "primary_metric": "PR-AUC Average Precision and positive F1",
            "output_path": "artifacts/a1_5_run_summary.json",
            "notes": "S0 exact A1.3 B2 reproduction; 4081 external; 12243 selected inner OOF; test access 0; prohibited experiments 0",
        }
    )
    write_csv(path, rows, fields)


def formal_run(config: dict[str, Any]) -> None:
    prereg_commit = _assert_clean_start(config)
    started = utc_now()
    run_id = (
        f"a1_5_structural_ablation_"
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{prereg_commit[:8]}"
    )
    run_dir = REPO_ROOT / "runs" / run_id
    if run_dir.exists():
        raise IntegrityError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    command = (
        f"{sys.executable} scripts/run_stage_a1_5_structural_ablation.py "
        "--config configs/stage_a1_5_structural_ablation.yaml --run"
    )
    a12.atomic_write_text(run_dir / "command.txt", command + "\n")
    a12.atomic_write_text(run_dir / "git_commit.txt", prereg_commit + "\n")
    shutil.copy2(CONFIG_PATH, run_dir / "config.yaml")
    write_json(run_dir / "environment.json", a12.environment_record())
    fit_audit = FitAudit()
    formal_prediction_count = 0
    checked: dict[str, Any] | None = None
    try:
        assert_preregistered_bytes(config)
        checked = preflight(config)
        write_json(run_dir / "hashes_before.json", checked["verified_hashes"])
    except Exception as error:
        write_json(
            run_dir / "FAILED_PRERUN.json",
            {
                "status": "STOP_PREFIT_GUARD", "failed_at_utc": utc_now(),
                "error_type": type(error).__name__, "error": str(error),
                "traceback": traceback.format_exc(),
                "real_dev_scaler_fit_count": 0, "real_dev_estimator_fit_count": 0,
                "formal_prediction_count": 0,
                "required_action": "Fix in an independent commit and restart from S0.",
            },
        )
        raise
    try:
        warnings_out: list[dict[str, Any]] = []
        s0 = _run_variant(config, checked, "S0_full13", warnings_out, fit_audit)
        formal_prediction_count += len(s0["predictions"])
        s0_proof = verify_s0_positive_control(config, s0)
        write_json(run_dir / "s0_positive_control.json", s0_proof)
        combined = {key: list(value) for key, value in s0.items()}
        for variant in VARIANT_IDS[1:]:
            current = _run_variant(config, checked, variant, warnings_out, fit_audit)
            formal_prediction_count += len(current["predictions"])
            for key in combined:
                combined[key].extend(current[key])
        macro = macro_rows(combined["domain"])
        pooled = pooled_rows(combined["predictions"])
        deltas = delta_rows(config, combined["domain"], macro, pooled)
        frequency = _frequency_rows(combined["config"])
        expected = config["execution"]
        counts = {
            "inner_config_selection": len(combined["config"]),
            "inner_selected_oof_predictions": len(combined["inner"]),
            "threshold_selection": len(combined["threshold"]),
            "external_predictions": len(combined["predictions"]),
            "domain_metrics": len(combined["domain"]),
            "macro_metrics": len(macro), "pooled_metrics": len(pooled),
            "structural_ablation_deltas": len(deltas),
        }
        wanted = {
            "inner_config_selection": expected["expected_config_selection_rows"],
            "inner_selected_oof_predictions": expected["expected_inner_selected_oof_predictions"],
            "threshold_selection": expected["expected_threshold_selection_rows"],
            "external_predictions": expected["expected_external_predictions"],
            "domain_metrics": expected["expected_domain_metric_rows"],
            "macro_metrics": expected["expected_macro_metric_rows"],
            "pooled_metrics": expected["expected_pooled_metric_rows"],
            "structural_ablation_deltas": expected["expected_domain_metric_rows"],
        }
        if counts != wanted:
            raise IntegrityError(f"formal result counts differ: {counts} != {wanted}")
        completed = utc_now()
        summary = {
            "stage": "A1.5", "stage_decision": "PASS_WITH_CONDITIONS",
            "run_id": run_id, "started_at_utc": started, "completed_at_utc": completed,
            "preregistration_commit": prereg_commit,
            "experiment_commit": "recorded_after_commit",
            "environment": a12.environment_record(),
            "source_revisions": checked["source_revisions"],
            "verified_upstream_commits": checked["verified_commits"],
            "feature_groups": config["feature_groups"],
            "variant_features": _variant_features(config),
            "held_out_statistics": checked["held_out_statistics"],
            "inner_fold_counts": checked["inner_counts"],
            "s0_positive_control": s0_proof, "row_counts": counts,
            "warning_count": len(warnings_out),
            "convergence_warning_count": sum(
                bool(row["is_convergence_warning"]) for row in warnings_out
            ),
            "warnings": warnings_out,
            "real_dev_scaler_fit_count": fit_audit.scaler_fit_count,
            "real_dev_estimator_fit_count": fit_audit.estimator_fit_count,
            "test_access": {
                "manifest": 0, "trajectory_content": 0, "labels": 0,
                "predictions": 0, "metrics": 0,
            },
            "network_access": 0, "gpu_used": False,
            "forbidden_experiments_executed": [],
            "hashes_before_run": checked["verified_hashes"],
            "hashes_after_run": verify_frozen_hashes(config),
            "conditions": [
                "Side Effect has 12 positives and AssistantBench is single-class negative.",
                "Known penalty='l2' FutureWarnings are retained.",
                "Dependency classifications are descriptive and non-causal.",
            ],
        }
        result = {
            **combined, "macro": macro, "pooled": pooled, "deltas": deltas,
            "frequency": frequency, "summary": summary,
        }
        _write_outputs(config, result)
        verification = verify_results(config)
        write_json(run_dir / "verification.json", verification)
        _append_experiment_registry(run_id, prereg_commit, started, completed)
        for path_text in config["outputs"].values():
            source = resolve(path_text)
            if source.exists():
                shutil.copy2(source, run_dir / source.name)
        shutil.copy2(REPO_ROOT / "research" / "02_EXPERIMENT_REGISTRY.csv", run_dir / "02_EXPERIMENT_REGISTRY.csv")
        write_json(run_dir / "metrics.json", {"macro": macro, "pooled": pooled, "deltas": deltas})
        shutil.copy2(resolve(config["outputs"]["external_predictions"]), run_dir / "predictions.csv")
        a12.atomic_write_text(
            run_dir / "stdout.log",
            json.dumps({"status": "PASS_WITH_CONDITIONS", "run_id": run_id, **verification}) + "\n",
        )
        a12.atomic_write_text(run_dir / "stderr.log", "")
        a12.atomic_write_text(
            run_dir / "summary.md",
            f"# {run_id}\n\nPASS_WITH_CONDITIONS. S0 exact; all S1--S6 completed; test access 0.\n",
        )
        write_json(
            run_dir / "completed.json",
            {"status": "PASS_WITH_CONDITIONS", "completed_at_utc": completed},
        )
        print(json.dumps({"status": "PASS_WITH_CONDITIONS", "run_id": run_id, **verification}))
    except Exception as error:
        write_json(
            run_dir / "FAILED_RUN.json",
            {
                "status": "INVALIDATED", "failed_at_utc": utc_now(),
                "error_type": type(error).__name__, "error": str(error),
                "traceback": traceback.format_exc(),
                "real_dev_scaler_fit_count": fit_audit.scaler_fit_count,
                "real_dev_estimator_fit_count": fit_audit.estimator_fit_count,
                "formal_prediction_count": formal_prediction_count,
                "required_action": "Preserve this run, fix in an independent commit, and rerun from S0. Do not retain selective ablation results.",
            },
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write-prerun", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--verify-results", action="store_true")
    args = parser.parse_args()
    try:
        config = load_config(args.config.resolve())
        if args.write_prerun:
            write_prerun(config)
        elif args.run:
            formal_run(config)
        else:
            print(json.dumps(verify_results(config)))
        return 0
    except Exception as error:
        print(f"A1.5 STOP: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
