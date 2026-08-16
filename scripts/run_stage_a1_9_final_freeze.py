#!/usr/bin/env python3
"""Preregister, execute, and independently verify Stage A1.9.

``--write-prerun`` performs dev-only read-only guards and writes the A1.9a
integrity record without fitting an estimator. ``--run`` requires the clean
A1.9a commit and performs exactly 93 authorized Logistic Regression fits.
``--verify-results`` reloads artifacts and independently recomputes selection
invariants without fitting. No mode reads any test manifest or test data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import joblib
import numpy as np
import yaml
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_9_final_freeze.yaml"
TARGET_ORDER = ["success", "looping", "side_effect"]
PREREG_FILES = [
    ".gitattributes",
    "docs/tasks/STAGE_A1_9_FINAL_METHOD_FREEZE_AND_TEST_PREREGISTRATION.md",
    "configs/stage_a1_9_final_freeze.yaml",
    "artifacts/a1_9_prerun_integrity.json",
    "artifacts/a1_9_test_preregistration.json",
    "artifacts/a1_9_final_claim_freeze.csv",
    "scripts/run_stage_a1_9_final_freeze.py",
    "tests/test_stage_a1_9_final_freeze.py",
    "research/01_DECISION_LOG.md",
]
TEST_ACCESS_ZERO = {
    "manifest": 0,
    "content": 0,
    "labels": 0,
    "eligibility": 0,
    "features": 0,
    "embeddings": 0,
    "predictions": 0,
    "metrics": 0,
}
PROHIBITED_ZERO = {
    "new_model_family": 0,
    "s6_final_method": 0,
    "b3_final_method": 0,
    "fusion": 0,
    "second_embedding_model": 0,
    "llm_judge": 0,
    "qwen_forward": 0,
    "embedding_regeneration": 0,
    "secondary_lobo": 0,
    "joint_ood": 0,
}


class IntegrityError(RuntimeError):
    """Raised when a frozen scientific invariant is violated."""


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp at second resolution."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path: str | Path) -> Path:
    """Resolve a repository-relative path without allowing escape."""

    candidate = (REPO_ROOT / Path(path)).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise IntegrityError(f"path escapes repository: {path}") from exc
    return candidate


def sha256_path(path: Path) -> str:
    """Compute SHA-256 over exact working-tree bytes."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def probability_sha256(values: Sequence[float]) -> str:
    """Hash probabilities as canonical little-endian float64 bytes."""

    array = np.asarray(values, dtype="<f8")
    return hashlib.sha256(array.tobytes(order="C")).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8/LF text atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def atomic_write_json(path: Path, payload: Any) -> None:
    """Write deterministic JSON with LF line endings."""

    atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def atomic_write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    """Write deterministic RFC-style CSV with explicit LF bytes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV as string-keyed rows."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_config(path: Path) -> dict[str, Any]:
    """Load the frozen YAML configuration."""

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IntegrityError("configuration must be an object")
    return payload


def git(*args: str) -> str:
    """Run a read-only Git query."""

    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def git_status() -> list[str]:
    """Return porcelain status lines."""

    output = git("status", "--porcelain")
    return output.splitlines() if output else []


def verify_worktree_matches_head(paths: Iterable[str]) -> None:
    """Require selected working files to be byte-identical to committed blobs."""

    for relative in paths:
        path = resolve(relative)
        if not path.exists():
            raise IntegrityError(f"missing committed preregistration file: {relative}")
        worktree_blob = git("hash-object", "--no-filters", relative)
        committed_blob = git("rev-parse", f"HEAD:{relative}")
        if worktree_blob != committed_blob:
            raise IntegrityError(f"working bytes differ from HEAD blob: {relative}")


def verify_source_hashes(config: dict[str, Any]) -> dict[str, str]:
    """Verify every declared dev/protocol source without touching test files."""

    observed: dict[str, str] = {}
    for name, spec in config["inputs"].items():
        path = resolve(spec["path"])
        if not path.is_file():
            raise IntegrityError(f"missing frozen input {name}: {spec['path']}")
        digest = sha256_path(path)
        if digest != spec["sha256"]:
            raise IntegrityError(f"hash mismatch for {name}: {digest} != {spec['sha256']}")
        observed[spec["path"]] = digest
    return observed


def verify_method_registry(config: dict[str, Any]) -> None:
    """Enforce the only three authorized final methods and prohibitions."""

    methods = config["methods"]
    if set(methods) != {"success", "looping", "side_effect"} or len(methods) != 3:
        raise IntegrityError("final method registry must contain exactly three targets")
    expected = {
        "success": ("FINAL_SUCCESS_B2", "B2_structural_logistic_regression", "confirmatory_primary", True, True),
        "looping": ("FINAL_LOOPING_B2", "B2_structural_logistic_regression", "confirmatory_primary", True, True),
        "side_effect": ("FINAL_SIDE_EFFECT_B4", "B4_qwen3_frozen_dense_embedding_logistic_regression", "exploratory_only", False, False),
    }
    for target, wanted in expected.items():
        item = methods[target]
        actual = (
            item["method_id"], item["family"], item["role"],
            bool(item["confirmatory_eligible"]), bool(item["standard_scaler"]),
        )
        if actual != wanted:
            raise IntegrityError(f"final method conflict for {target}: {actual}")
    execution = config["execution"]
    for flag in [
        "fusion", "second_embedding_model", "b3_final_method", "s6_final_method",
        "llm_judge", "new_model_family", "secondary_lobo", "joint_ood",
    ]:
        if execution[flag] is not False:
            raise IntegrityError(f"prohibited method flag enabled: {flag}")
    if config["qwen"]["dev_forward_allowed"] or config["qwen"]["dev_embedding_regeneration_allowed"]:
        raise IntegrityError("Qwen forward or dev embedding regeneration is enabled")


def verify_protocol(config: dict[str, Any]) -> None:
    """Verify selection, threshold, classifier, and count contracts."""

    classifier = config["classifier"]
    if classifier != {
        "estimator": "LogisticRegression", "penalty": "l2", "solver": "liblinear",
        "max_iter": 5000, "fit_intercept": True, "random_state": 2026,
        "C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"],
        "config_tie_break": ["class_weight_none", "smaller_C", "config_id"],
    }:
        raise IntegrityError("classifier grid differs from frozen contract")
    selection = config["selection"]
    if selection["folds"] != 5 or selection["configuration_metric"] != "average_precision_score":
        raise IntegrityError("selection fold or metric conflict")
    thresholds = [round(index * 0.05, 2) for index in range(1, 20)]
    if [float(value) for value in selection["thresholds"]] != thresholds:
        raise IntegrityError("threshold grid conflict")
    if selection["threshold_tie_break"] != ["higher_recall", "closer_to_0.5", "smaller_threshold"]:
        raise IntegrityError("threshold tie-break conflict")
    if len(config["structural_features"]) != 13 or len(set(config["structural_features"])) != 13:
        raise IntegrityError("structural feature contract is not full13")
    if config["expected_counts"] != {
        "all_config_oof": 3498, "selected_config_oof": 583,
        "config_summary": 18, "threshold_summary": 57,
        "estimator_fits": 93, "final_model_artifacts": 3,
    }:
        raise IntegrityError("expected output count contract changed")


def verify_a1_8_ready(config: dict[str, Any]) -> dict[str, Any]:
    """Verify A1.8 machine evidence authorizes only final-method freeze."""

    decision = json.loads(resolve(config["inputs"]["a1_8_remaining_decision"]["path"]).read_text(encoding="utf-8"))
    summary = json.loads(resolve(config["inputs"]["a1_8_run_summary"]["path"]).read_text(encoding="utf-8"))
    if decision["decision"] != "READY_FOR_FINAL_METHOD_FREEZE":
        raise IntegrityError("A1.8 remaining-evidence decision is not ready")
    if not decision["requires_human_stage_gate_before_test"]:
        raise IntegrityError("A1.8 human test gate is not preserved")
    if summary["remaining_evidence_decision"] != "READY_FOR_FINAL_METHOD_FREEZE":
        raise IntegrityError("A1.8 summary disagrees with remaining decision")
    if summary["stage_determination"] != "PASS_WITH_CONDITIONS":
        raise IntegrityError("A1.8 stage determination changed")
    proposal = summary["final_method_freeze_proposal"]
    if len(proposal) != 3:
        raise IntegrityError("A1.8 final method proposal is not three rows")
    return {
        "decision": decision["decision"],
        "stage_determination": summary["stage_determination"],
        "claim_matrix_sha256": sha256_path(resolve(config["inputs"]["a1_8_claim_matrix"]["path"])),
        "requires_human_stage_gate_before_test": True,
    }


def eligible_index(config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, dict[str, str]]]:
    """Load and validate the frozen dev label interface."""

    rows = read_csv(resolve(config["inputs"]["dev_index"]["path"]))
    if len(rows) != 196 or len({row["trajectory_key"] for row in rows}) != 196:
        raise IntegrityError("dev index is not 196 unique trajectories")
    by_key = {row["trajectory_key"]: row for row in rows}
    for target, method in config["methods"].items():
        selected = [
            row for row in rows
            if row[f"{target}_eligible_main"].lower() == "true" and row[f"{target}_label"] in {"0", "1"}
        ]
        positives = sum(int(row[f"{target}_label"]) for row in selected)
        if len(selected) != method["expected_samples"] or positives != method["expected_positive"]:
            raise IntegrityError(f"eligibility count mismatch for {target}")
    return rows, by_key


def fold_assignments(config: dict[str, Any], target: str, index: dict[str, dict[str, str]]) -> dict[str, dict[str, Any]]:
    """Extract the sole outer-validation assignment from the frozen A1.1 manifest."""

    spec = config["inputs"][f"{target}_folds"]
    rows = read_csv(resolve(spec["path"]))
    expected_n = int(config["methods"][target]["expected_samples"])
    if len(rows) != expected_n * 5:
        raise IntegrityError(f"fold manifest row count mismatch for {target}")
    eligible = {
        key for key, row in index.items()
        if row[f"{target}_eligible_main"].lower() == "true" and row[f"{target}_label"] in {"0", "1"}
    }
    validation = [row for row in rows if row["outer_role"] == "outer_validation"]
    if len(validation) != expected_n or {row["trajectory_key"] for row in validation} != eligible:
        raise IntegrityError(f"outer-validation coverage mismatch for {target}")
    output: dict[str, dict[str, Any]] = {}
    group_fold: dict[str, int] = {}
    for row in validation:
        key = row["trajectory_key"]
        fold = int(row["outer_fold"])
        if fold not in range(1, 6) or key in output:
            raise IntegrityError(f"invalid or duplicate fold assignment for {target}")
        if int(row["label"]) != int(index[key][f"{target}_label"]):
            raise IntegrityError(f"fold label mismatch for {target}: {key}")
        group = row["group_key"]
        if group in group_fold and group_fold[group] != fold:
            raise IntegrityError(f"task group crosses folds for {target}: {group}")
        group_fold[group] = fold
        output[key] = {"fold": fold, "group_key": group}
    if set(item["fold"] for item in output.values()) != set(range(1, 6)):
        raise IntegrityError(f"not all five folds are used for {target}")
    return output


def load_structural(config: dict[str, Any]) -> dict[str, np.ndarray]:
    """Load the frozen full13 structural feature matrix by trajectory key."""

    rows = read_csv(resolve(config["inputs"]["structural_features"]["path"]))
    features = config["structural_features"]
    if len(rows) != 196 or any(field not in rows[0] for field in features):
        raise IntegrityError("structural feature table violates full13 contract")
    output = {row["trajectory_key"]: np.asarray([float(row[field]) for field in features], dtype=float) for row in rows}
    if len(output) != 196 or not np.all(np.isfinite(np.vstack(list(output.values())))):
        raise IntegrityError("structural features are duplicate or non-finite")
    return output


def load_embeddings(config: dict[str, Any]) -> tuple[np.ndarray, dict[str, int]]:
    """Load the already-frozen A1.7 dev embeddings without model forward."""

    matrix = np.load(resolve(config["inputs"]["dev_embedding"]["path"]), allow_pickle=False)
    expected_shape = tuple(config["inputs"]["dev_embedding"]["expected_shape"])
    if matrix.shape != expected_shape or matrix.dtype != np.float32 or not np.all(np.isfinite(matrix)):
        raise IntegrityError("frozen embedding shape/dtype/finite guard failed")
    norms = np.linalg.norm(matrix, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=1e-5):
        raise IntegrityError("frozen embedding normalization guard failed")
    rows = read_csv(resolve(config["inputs"]["embedding_index"]["path"]))
    if [int(row["row_index"]) for row in rows] != list(range(196)):
        raise IntegrityError("embedding row index is not contiguous")
    key_to_row = {row["trajectory_key"]: int(row["row_index"]) for row in rows}
    if len(key_to_row) != 196:
        raise IntegrityError("embedding index contains duplicate trajectory keys")
    return matrix, key_to_row


def prefit_guard(config: dict[str, Any]) -> dict[str, Any]:
    """Run every guard required before the first real-dev fit."""

    hashes = verify_source_hashes(config)
    verify_method_registry(config)
    verify_protocol(config)
    ready = verify_a1_8_ready(config)
    rows, index = eligible_index(config)
    folds = {target: fold_assignments(config, target, index) for target in TARGET_ORDER}
    structural = load_structural(config)
    embedding, embedding_index = load_embeddings(config)
    if set(structural) != set(index) or set(embedding_index) != set(index):
        raise IntegrityError("dev feature/embedding/index trajectory keys differ")
    test_prereg = json.loads(resolve(config["outputs"]["test_preregistration"]).read_text(encoding="utf-8"))
    if test_prereg["a1_9_test_access"] != TEST_ACCESS_ZERO or test_prereg["status"] != "FROZEN_NOT_EXECUTED":
        raise IntegrityError("test preregistration boundary is not frozen at zero")
    claims = read_csv(resolve(config["outputs"]["claim_freeze"]))
    if len(claims) != 8 or sum(row["role"] == "confirmatory_primary" for row in claims) != 2:
        raise IntegrityError("final claim freeze is incomplete")
    return {
        "source_hashes": hashes,
        "a1_8_ready": ready,
        "dev_index_rows": len(rows),
        "eligible_counts": {target: len(folds[target]) for target in TARGET_ORDER},
        "embedding_shape": list(embedding.shape),
        "test_access": dict(TEST_ACCESS_ZERO),
        "prohibited_experiments": dict(PROHIBITED_ZERO),
        "real_dev_fit_count": 0,
        "status": "PASS",
    }


def environment_record() -> dict[str, Any]:
    """Capture the final classifier environment."""

    packages = ["joblib", "numpy", "PyYAML", "scikit-learn", "scipy", "threadpoolctl"]
    return {
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
        "gpu_used": False,
        "dependencies": {name: importlib.metadata.version(name) for name in packages},
    }


def write_prerun(config: dict[str, Any]) -> dict[str, Any]:
    """Write the no-fit A1.9a integrity record."""

    result = prefit_guard(config)
    preregistration_sources = [path for path in PREREG_FILES if path != "artifacts/a1_9_prerun_integrity.json"]
    result.update({
        "stage": "A1.9a",
        "generated_at_utc": utc_now(),
        "environment": environment_record(),
        "preregistration_files": preregistration_sources,
        "preregistration_hashes": {path: sha256_path(resolve(path)) for path in preregistration_sources},
        "note": "No test manifest or test data was accessed; no real-dev estimator was fit.",
    })
    atomic_write_json(resolve(config["outputs"]["prerun_integrity"]), result)
    return result


def candidate_configs(config: dict[str, Any], target: str) -> list[dict[str, Any]]:
    """Return the six configurations in the frozen tie-break order."""

    prefix = "B4" if target == "side_effect" else "B2"
    rows: list[dict[str, Any]] = []
    for class_weight in [None, "balanced"]:
        for c_value in [0.1, 1.0, 10.0]:
            c_text = {0.1: "0p1", 1.0: "1p0", 10.0: "10p0"}[c_value]
            weight_text = "none" if class_weight is None else "balanced"
            rows.append({
                "config_id": f"{prefix}_C{c_text}_cw_{weight_text}",
                "C": c_value,
                "class_weight": class_weight,
                "tie_break_rank": len(rows) + 1,
            })
    return rows


def make_model(config: dict[str, Any], target: str, candidate: dict[str, Any]) -> Any:
    """Construct exactly the frozen B2 pipeline or B4 classifier."""

    fixed = config["classifier"]
    classifier = LogisticRegression(
        C=float(candidate["C"]), class_weight=candidate["class_weight"],
        penalty=fixed["penalty"], solver=fixed["solver"], max_iter=int(fixed["max_iter"]),
        fit_intercept=bool(fixed["fit_intercept"]), random_state=int(fixed["random_state"]),
    )
    if target == "side_effect":
        return classifier
    return Pipeline([("standard_scaler", StandardScaler()), ("classifier", classifier)])


def positive_probability(model: Any, matrix: np.ndarray) -> np.ndarray:
    """Locate P(y=1) via classes_ and validate bounds."""

    classes = np.asarray(model.classes_)
    indices = np.flatnonzero(classes == 1)
    if len(indices) != 1:
        raise IntegrityError(f"positive class missing or duplicated: {classes}")
    probabilities = np.asarray(model.predict_proba(matrix)[:, int(indices[0])], dtype=float)
    if not np.all(np.isfinite(probabilities)) or np.any(probabilities < 0) or np.any(probabilities > 1):
        raise IntegrityError("invalid predicted probabilities")
    return probabilities


def select_threshold(config: dict[str, Any], truth: Sequence[int], probabilities: Sequence[float]) -> tuple[float, list[dict[str, Any]]]:
    """Select positive F1 using the frozen recall/distance/smaller tie-break."""

    y_true = np.asarray(truth, dtype=int)
    prob = np.asarray(probabilities, dtype=float)
    rows: list[dict[str, Any]] = []
    for threshold in config["selection"]["thresholds"]:
        predicted = (prob >= float(threshold)).astype(int)
        rows.append({
            "threshold": float(threshold),
            "positive_f1": float(f1_score(y_true, predicted, pos_label=1, zero_division=0)),
            "precision": float(precision_score(y_true, predicted, pos_label=1, zero_division=0)),
            "recall": float(recall_score(y_true, predicted, pos_label=1, zero_division=0)),
            "selected": False,
        })
    best = max(float(row["positive_f1"]) for row in rows)
    tied = [row for row in rows if math.isclose(float(row["positive_f1"]), best, rel_tol=0.0, abs_tol=1e-15)]
    selected = min(tied, key=lambda row: (-float(row["recall"]), abs(float(row["threshold"]) - 0.5), float(row["threshold"])))
    selected["selected"] = True
    return float(selected["threshold"]), rows


def _fit(model: Any, matrix: np.ndarray, labels: Sequence[int], context: dict[str, Any], warning_rows: list[dict[str, Any]], fit_counter: list[int]) -> Any:
    """Perform and count one authorized real-dev LR fit."""

    if len(set(int(value) for value in labels)) != 2:
        raise IntegrityError(f"training split is not mixed class: {context}")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(matrix, labels)
    fit_counter[0] += 1
    for item in caught:
        warning_rows.append({
            **context,
            "category": item.category.__name__,
            "message": str(item.message),
            "is_convergence_warning": issubclass(item.category, ConvergenceWarning),
        })
    return model


def _target_matrix(target: str, keys: Sequence[str], structural: dict[str, np.ndarray], embeddings: np.ndarray, embedding_index: dict[str, int]) -> np.ndarray:
    if target == "side_effect":
        return embeddings[[embedding_index[key] for key in keys]]
    return np.vstack([structural[key] for key in keys])


def execute_target(
    config: dict[str, Any], target: str, index_rows: list[dict[str, str]],
    fold_map: dict[str, dict[str, Any]], structural: dict[str, np.ndarray],
    embeddings: np.ndarray, embedding_index: dict[str, int],
    warning_rows: list[dict[str, Any]], fit_counter: list[int], training_commit: str,
) -> dict[str, Any]:
    """Run all six five-fold OOF configurations and one all-dev refit."""

    method = config["methods"][target]
    keys = [row["trajectory_key"] for row in index_rows if row["trajectory_key"] in fold_map]
    labels = {row["trajectory_key"]: int(row[f"{target}_label"]) for row in index_rows if row["trajectory_key"] in fold_map}
    candidates = candidate_configs(config, target)
    all_rows: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    oof_by_config: dict[str, dict[str, float]] = {}
    for candidate in candidates:
        oof: dict[str, float] = {}
        for fold in range(1, 6):
            train_keys = [key for key in keys if fold_map[key]["fold"] != fold]
            validation_keys = [key for key in keys if fold_map[key]["fold"] == fold]
            model = make_model(config, target, candidate)
            model = _fit(
                model,
                _target_matrix(target, train_keys, structural, embeddings, embedding_index),
                [labels[key] for key in train_keys],
                {"target": target, "phase": "five_fold_oof", "fold": fold, "config_id": candidate["config_id"]},
                warning_rows, fit_counter,
            )
            probabilities = positive_probability(
                model, _target_matrix(target, validation_keys, structural, embeddings, embedding_index)
            )
            for key, probability in zip(validation_keys, probabilities, strict=True):
                if key in oof:
                    raise IntegrityError(f"duplicate OOF prediction for {target}/{candidate['config_id']}/{key}")
                oof[key] = float(probability)
                all_rows.append({
                    "target": target, "method_id": method["method_id"],
                    "config_id": candidate["config_id"], "outer_fold": fold,
                    "trajectory_key": key, "group_key": fold_map[key]["group_key"],
                    "true_label": labels[key], "predicted_probability": float(probability),
                })
        if set(oof) != set(keys):
            raise IntegrityError(f"incomplete OOF for {target}/{candidate['config_id']}")
        score = float(average_precision_score([labels[key] for key in keys], [oof[key] for key in keys]))
        config_rows.append({
            "target": target, "method_id": method["method_id"], "config_id": candidate["config_id"],
            "C": candidate["C"], "class_weight": "none" if candidate["class_weight"] is None else "balanced",
            "pooled_oof_rows": len(oof), "pooled_oof_average_precision": score,
            "tie_break_rank": candidate["tie_break_rank"], "selected": False,
        })
        oof_by_config[candidate["config_id"]] = oof
    best_ap = max(float(row["pooled_oof_average_precision"]) for row in config_rows)
    selected_config_row = min(
        [row for row in config_rows if math.isclose(float(row["pooled_oof_average_precision"]), best_ap, rel_tol=0.0, abs_tol=1e-15)],
        key=lambda row: int(row["tie_break_rank"]),
    )
    selected_config_row["selected"] = True
    selected_id = str(selected_config_row["config_id"])
    selected_candidate = next(item for item in candidates if item["config_id"] == selected_id)
    selected_oof = oof_by_config[selected_id]
    threshold, threshold_rows = select_threshold(
        config, [labels[key] for key in keys], [selected_oof[key] for key in keys]
    )
    threshold_output = [{
        "target": target, "method_id": method["method_id"], "selected_config_id": selected_id,
        **row,
    } for row in threshold_rows]
    selected_rows = [{
        "target": target, "method_id": method["method_id"], "trajectory_key": key,
        "group_key": fold_map[key]["group_key"], "outer_fold": fold_map[key]["fold"],
        "true_label": labels[key], "predicted_probability": selected_oof[key],
        "selected_config_id": selected_id, "selected_threshold": threshold,
        "predicted_label": int(selected_oof[key] >= threshold),
    } for key in keys]
    final_model = make_model(config, target, selected_candidate)
    final_model = _fit(
        final_model, _target_matrix(target, keys, structural, embeddings, embedding_index),
        [labels[key] for key in keys],
        {"target": target, "phase": "all_eligible_dev_refit", "fold": "", "config_id": selected_id},
        warning_rows, fit_counter,
    )
    final_probabilities = positive_probability(
        final_model, _target_matrix(target, keys, structural, embeddings, embedding_index)
    )
    model_path = resolve(config["outputs"][f"{target}_model"])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = model_path.with_name(model_path.name + ".tmp")
    joblib.dump(final_model, temporary, compress=3)
    os.replace(temporary, model_path)
    reloaded = joblib.load(model_path)
    reloaded_probabilities = positive_probability(
        reloaded, _target_matrix(target, keys, structural, embeddings, embedding_index)
    )
    reload_error = float(np.max(np.abs(final_probabilities - reloaded_probabilities)))
    if reload_error != 0.0:
        raise IntegrityError(f"reload predictions changed for {target}: {reload_error}")
    oof_truth = [int(row["true_label"]) for row in selected_rows]
    oof_probability = [float(row["predicted_probability"]) for row in selected_rows]
    oof_predicted = [int(row["predicted_label"]) for row in selected_rows]
    input_hash = (
        config["inputs"]["dev_embedding"]["sha256"] if target == "side_effect"
        else config["inputs"]["structural_features"]["sha256"]
    )
    record = {
        "method_id": method["method_id"], "target": target, "role": method["role"],
        "confirmatory_eligible": bool(method["confirmatory_eligible"]),
        "input_contract": "A1.7 frozen 1024-d dense embedding; no StandardScaler" if target == "side_effect" else "A1.2 frozen full13 structural features; StandardScaler pipeline",
        "input_sha256": input_hash,
        "dev_eligibility_count": len(keys), "dev_positive_count": sum(labels.values()),
        "selection_fold_path": config["inputs"][f"{target}_folds"]["path"],
        "selection_fold_sha256": config["inputs"][f"{target}_folds"]["sha256"],
        "selected_config": {"config_id": selected_id, "C": selected_candidate["C"], "class_weight": selected_candidate["class_weight"]},
        "selected_threshold": threshold,
        "final_oof_average_precision": float(average_precision_score(oof_truth, oof_probability)),
        "final_oof_positive_f1": float(f1_score(oof_truth, oof_predicted, pos_label=1, zero_division=0)),
        "training_commit": training_commit,
        "artifact_path": config["outputs"][f"{target}_model"],
        "artifact_sha256": sha256_path(model_path),
        "full_dev_prediction_sha256": probability_sha256(final_probabilities),
        "reload_prediction_sha256": probability_sha256(reloaded_probabilities),
        "reload_max_absolute_error": reload_error,
    }
    if target == "side_effect":
        record["qwen"] = {
            "repo_id": config["qwen"]["repo_id"],
            "immutable_revision": config["qwen"]["immutable_revision"],
            "weight_sha256": config["qwen"]["weight_sha256"],
            "embedding_extraction_contract": config["qwen"]["test_extraction_contract"],
        }
    return {
        "all_rows": all_rows, "selected_rows": selected_rows,
        "config_rows": config_rows, "threshold_rows": threshold_output,
        "model_record": record,
    }


def verify_results(config: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute output and reload invariants without fitting."""

    verify_source_hashes(config)
    verify_method_registry(config)
    verify_protocol(config)
    index_rows, index = eligible_index(config)
    fold_maps = {target: fold_assignments(config, target, index) for target in TARGET_ORDER}
    structural = load_structural(config)
    embeddings, embedding_index = load_embeddings(config)
    all_rows = read_csv(resolve(config["outputs"]["all_config_oof"]))
    selected = read_csv(resolve(config["outputs"]["selected_oof"]))
    configs = read_csv(resolve(config["outputs"]["config_selection"]))
    thresholds = read_csv(resolve(config["outputs"]["threshold_selection"]))
    manifest = json.loads(resolve(config["outputs"]["model_manifest"]).read_text(encoding="utf-8"))
    expected = config["expected_counts"]
    actual = {
        "all_config_oof": len(all_rows), "selected_config_oof": len(selected),
        "config_summary": len(configs), "threshold_summary": len(thresholds),
        "estimator_fits": int(manifest["estimator_fit_count"]),
        "final_model_artifacts": len(manifest["models"]),
    }
    if actual != expected:
        raise IntegrityError(f"formal count mismatch: {actual} != {expected}")
    if len({(row["target"], row["config_id"], row["trajectory_key"]) for row in all_rows}) != 3498:
        raise IntegrityError("all-config OOF rows are not unique")
    if len({(row["target"], row["trajectory_key"]) for row in selected}) != 583:
        raise IntegrityError("selected-config OOF rows are not unique")
    metric_recompute: dict[str, dict[str, float]] = {}
    reload_verification: dict[str, Any] = {}
    records = {row["target"]: row for row in manifest["models"]}
    for target in TARGET_ORDER:
        target_configs = [row for row in configs if row["target"] == target]
        if len(target_configs) != 6:
            raise IntegrityError(f"config row count is not six for {target}")
        best_ap = max(float(row["pooled_oof_average_precision"]) for row in target_configs)
        recomputed_choice = min(
            [row for row in target_configs if math.isclose(float(row["pooled_oof_average_precision"]), best_ap, rel_tol=0.0, abs_tol=1e-15)],
            key=lambda row: int(row["tie_break_rank"]),
        )
        chosen = [row for row in target_configs if row["selected"] == "True"]
        if len(chosen) != 1 or chosen[0]["config_id"] != recomputed_choice["config_id"]:
            raise IntegrityError(f"config selection does not recompute for {target}")
        target_selected = [row for row in selected if row["target"] == target]
        target_thresholds = [row for row in thresholds if row["target"] == target]
        if len(target_thresholds) != 19 or any(row["selected_config_id"] != chosen[0]["config_id"] for row in target_thresholds):
            raise IntegrityError(f"threshold rows invalid for {target}")
        threshold, _ = select_threshold(
            config, [int(row["true_label"]) for row in target_selected],
            [float(row["predicted_probability"]) for row in target_selected],
        )
        chosen_threshold = [row for row in target_thresholds if row["selected"] == "True"]
        if len(chosen_threshold) != 1 or not math.isclose(float(chosen_threshold[0]["threshold"]), threshold, abs_tol=1e-15):
            raise IntegrityError(f"threshold selection does not recompute for {target}")
        predicted = [int(float(row["predicted_probability"]) >= threshold) for row in target_selected]
        ap = float(average_precision_score(
            [int(row["true_label"]) for row in target_selected],
            [float(row["predicted_probability"]) for row in target_selected],
        ))
        f1 = float(f1_score([int(row["true_label"]) for row in target_selected], predicted, pos_label=1, zero_division=0))
        record = records[target]
        if not math.isclose(ap, float(record["final_oof_average_precision"]), rel_tol=1e-12, abs_tol=1e-12):
            raise IntegrityError(f"OOF AP mismatch for {target}")
        if not math.isclose(f1, float(record["final_oof_positive_f1"]), rel_tol=1e-12, abs_tol=1e-12):
            raise IntegrityError(f"OOF F1 mismatch for {target}")
        if sha256_path(resolve(record["artifact_path"])) != record["artifact_sha256"]:
            raise IntegrityError(f"model hash mismatch for {target}")
        keys = [row["trajectory_key"] for row in index_rows if row["trajectory_key"] in fold_maps[target]]
        model = joblib.load(resolve(record["artifact_path"]))
        if target == "side_effect" and isinstance(model, Pipeline):
            raise IntegrityError("Side Effect B4 unexpectedly uses a pipeline/scaler")
        if target != "side_effect":
            if not isinstance(model, Pipeline) or list(model.named_steps) != ["standard_scaler", "classifier"]:
                raise IntegrityError(f"B2 final artifact is not the frozen pipeline for {target}")
        probabilities = positive_probability(
            model, _target_matrix(target, keys, structural, embeddings, embedding_index)
        )
        digest = probability_sha256(probabilities)
        if digest != record["full_dev_prediction_sha256"] or digest != record["reload_prediction_sha256"]:
            raise IntegrityError(f"reload full-dev predictions do not reproduce for {target}")
        metric_recompute[target] = {"average_precision": ap, "positive_f1": f1, "threshold": threshold}
        reload_verification[target] = {"prediction_sha256": digest, "max_absolute_error": 0.0, "status": "PASS"}
    if manifest["test_access"] != TEST_ACCESS_ZERO or manifest["prohibited_experiments"] != PROHIBITED_ZERO:
        raise IntegrityError("formal boundary counters are nonzero")
    return {
        "status": "PASS", "counts": actual,
        "metric_recomputation": metric_recompute,
        "reload_verification": reload_verification,
        "test_access": dict(TEST_ACCESS_ZERO),
        "prohibited_experiments": dict(PROHIBITED_ZERO),
    }


def build_report(summary: dict[str, Any], manifest: dict[str, Any]) -> str:
    """Build the formal A1.9 freeze report."""

    model_rows = []
    for record in manifest["models"]:
        weight = record["selected_config"]["class_weight"]
        model_rows.append(
            f"| {record['target']} | `{record['method_id']}` | `{record['role']}` | "
            f"C={record['selected_config']['C']}, class_weight={weight} | {record['selected_threshold']:.2f} | "
            f"{record['final_oof_average_precision']:.6f} | {record['final_oof_positive_f1']:.6f} | "
            f"`{record['artifact_sha256']}` |"
        )
    return "\n".join([
        "# Stage A1.9 final method freeze and test preregistration report", "",
        "## Stage determination", "", f"`{summary['stage_determination']}`", "",
        "All final-dev selection, model-freeze, reload, count, hash, and zero-test-access guards passed. "
        "The condition is scientific: Side Effect remains exploratory-only. This report does not authorize or execute A1.10.", "",
        "## Commits and A1.8 readiness", "",
        f"- A1.9a preregistration commit: `{summary['a1_9a_preregistration_commit']}`",
        "- A1.9b experiment commit: recorded by the enclosing result commit.",
        "- A1.8: `PASS_WITH_CONDITIONS` and `READY_FOR_FINAL_METHOD_FREEZE`, hash-verified before fitting.", "",
        "## Frozen methods and dev selection", "",
        "| Target | Method | Role | Final config | Threshold | OOF AP | OOF F1 | Model SHA-256 |",
        "|---|---|---|---|---:|---:|---:|---|", *model_rows, "",
        "Success and Looping use the full frozen 13-feature StandardScaler + LogisticRegression pipeline. "
        "S6 is auxiliary only. Side Effect uses the already-frozen A1.7 1024-d embedding and LogisticRegression without StandardScaler; no Qwen forward occurred.", "",
        "## Completeness and reload", "",
        f"- all-config OOF: {summary['counts']['all_config_oof']}/3498",
        f"- selected-config OOF: {summary['counts']['selected_config_oof']}/583",
        f"- config rows: {summary['counts']['config_summary']}/18",
        f"- threshold rows: {summary['counts']['threshold_summary']}/57",
        f"- Logistic Regression fits: {summary['counts']['estimator_fits']}/93",
        f"- final model artifacts: {summary['counts']['final_model_artifacts']}/3",
        "- All three joblib artifacts reload and reproduce full-dev prediction hashes exactly.", "",
        "## Final claim freeze", "",
        "FC1 Success and FC2 Looping are confirmatory-primary held-out official-task signal claims. "
        "FE1 Side Effect is permanently exploratory-only and cannot be upgraded from a high test score. "
        "B2/B3 or B4 relative superiority, termination/repetition mechanisms, A1.4 model-only transfer, and representation hierarchy remain dev-only.", "",
        "## Frozen A1.10 blind-first opening", "",
        "A1.10a requires new human approval. It may read identifiers and raw test content, but not labels or eligibility; it must produce all three methods' blind probabilities/labels, freeze SHA-256, commit the blind artifact, and return to a clean Git state. "
        "The counts 1106 trajectories and 3318 target rows are prior provenance only until identifier-only confirmation. "
        "Only then may A1.10b unlock labels/eligibility once and perform join-plus-scoring.", "",
        "## Final test metrics, bootstrap, and grade", "",
        "Success/Looping primary point metrics are pooled AP, pooled AP lift, and positive F1 at the frozen dev threshold. "
        "Primary uncertainty is pooled AP-lift 95% task-group cluster bootstrap CI: 10000 PCG64 draws, seed 2027, clusters sampled with replacement within benchmark_group_primary, no label stratification, no trajectory bootstrap, and no invalid redraw. "
        "A positive lift with CI lower > 0 is CONFIRMED_HELDOUT_SIGNAL; positive lift with CI crossing 0 is DIRECTIONAL_BUT_NOT_CONFIRMED; point <= 0 is NOT_CONFIRMED. Side Effect is always EXPLORATORY_TEST_RESULT.", "",
        "After label unlock, threshold/config/feature/model/embedding/pooling/calibration/fusion and eligibility changes are permanently prohibited for the confirmatory result.", "",
        "## Integrity, boundaries, and stop", "",
        f"- Test access: `{json.dumps(summary['test_access'], sort_keys=True)}`",
        f"- Prohibited experiments: `{json.dumps(summary['prohibited_experiments'], sort_keys=True)}`",
        f"- Warnings: {summary['warning_count']} total; convergence warnings: {summary['convergence_warning_count']}.",
        f"- Independent recomputation: `{summary['independent_verification']['status']}`.", "",
        "Recommendation: the technical A1.9 freeze is complete, so human review may authorize A1.10. Do not open test automatically. Stop here.", "",
    ])


def execute(config: dict[str, Any]) -> dict[str, Any]:
    """Perform the one authorized clean-worktree A1.9b formal run."""

    if git_status():
        raise IntegrityError(f"A1.9b requires a clean Git worktree: {git_status()}")
    if git("log", "-1", "--format=%s") != config["execution"]["required_preregistration_commit_subject"]:
        raise IntegrityError("HEAD is not the required A1.9a preregistration commit")
    verify_worktree_matches_head(PREREG_FILES)
    prefit = prefit_guard(config)
    if prefit["real_dev_fit_count"] != 0 or prefit["test_access"] != TEST_ACCESS_ZERO:
        raise IntegrityError("pre-fit boundary guard failed")
    training_commit = git("rev-parse", "HEAD")
    started = utc_now()
    run_id = f"a1_9_final_freeze_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{training_commit[:8]}"
    run_dir = resolve(Path("runs") / run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(CONFIG_PATH, run_dir / "config.yaml")
    atomic_write_text(run_dir / "command.txt", f"{sys.executable} scripts/run_stage_a1_9_final_freeze.py --config configs/stage_a1_9_final_freeze.yaml --run\n")
    atomic_write_text(run_dir / "git_commit.txt", training_commit + "\n")
    atomic_write_json(run_dir / "environment.json", environment_record())
    log_lines = [f"{started} prefit_guard PASS test_access=0"]
    index_rows, index = eligible_index(config)
    fold_maps = {target: fold_assignments(config, target, index) for target in TARGET_ORDER}
    structural = load_structural(config)
    embeddings, embedding_index = load_embeddings(config)
    warning_rows: list[dict[str, Any]] = []
    fit_counter = [0]
    results: dict[str, dict[str, Any]] = {}
    for target in TARGET_ORDER:
        results[target] = execute_target(
            config, target, index_rows, fold_maps[target], structural, embeddings,
            embedding_index, warning_rows, fit_counter, training_commit,
        )
        log_lines.append(f"{utc_now()} target={target} fits={fit_counter[0]} PASS")
    all_rows = [row for target in TARGET_ORDER for row in results[target]["all_rows"]]
    selected_rows = [row for target in TARGET_ORDER for row in results[target]["selected_rows"]]
    config_rows = [row for target in TARGET_ORDER for row in results[target]["config_rows"]]
    threshold_rows = [row for target in TARGET_ORDER for row in results[target]["threshold_rows"]]
    if (len(all_rows), len(selected_rows), len(config_rows), len(threshold_rows), fit_counter[0]) != (3498, 583, 18, 57, 93):
        raise IntegrityError("formal execution count guard failed")
    if any(row["is_convergence_warning"] for row in warning_rows):
        raise IntegrityError("Logistic Regression convergence warning occurred")
    atomic_write_csv(resolve(config["outputs"]["all_config_oof"]), all_rows, [
        "target", "method_id", "config_id", "outer_fold", "trajectory_key", "group_key", "true_label", "predicted_probability",
    ])
    atomic_write_csv(resolve(config["outputs"]["selected_oof"]), selected_rows, [
        "target", "method_id", "trajectory_key", "group_key", "outer_fold", "true_label", "predicted_probability", "selected_config_id", "selected_threshold", "predicted_label",
    ])
    atomic_write_csv(resolve(config["outputs"]["config_selection"]), config_rows, [
        "target", "method_id", "config_id", "C", "class_weight", "pooled_oof_rows", "pooled_oof_average_precision", "tie_break_rank", "selected",
    ])
    atomic_write_csv(resolve(config["outputs"]["threshold_selection"]), threshold_rows, [
        "target", "method_id", "selected_config_id", "threshold", "positive_f1", "precision", "recall", "selected",
    ])
    post_hashes = verify_source_hashes(config)
    if post_hashes != prefit["source_hashes"]:
        raise IntegrityError("frozen dev/protocol source hashes changed after fits")
    manifest = {
        "stage": "A1.9b", "status": "FROZEN", "generated_at_utc": utc_now(),
        "training_commit": training_commit, "training_environment": environment_record(),
        "models": [results[target]["model_record"] for target in TARGET_ORDER],
        "estimator_fit_count": fit_counter[0],
        "test_access": dict(TEST_ACCESS_ZERO), "prohibited_experiments": dict(PROHIBITED_ZERO),
        "source_hashes_before_and_after_identical": True,
        "claim_freeze_sha256": sha256_path(resolve(config["outputs"]["claim_freeze"])),
        "test_preregistration_sha256": sha256_path(resolve(config["outputs"]["test_preregistration"])),
    }
    atomic_write_json(resolve(config["outputs"]["model_manifest"]), manifest)
    verification = verify_results(config)
    completed = utc_now()
    counts = verification["counts"]
    output_hashes = {
        config["outputs"][name]: sha256_path(resolve(config["outputs"][name]))
        for name in ["all_config_oof", "selected_oof", "config_selection", "threshold_selection", "success_model", "looping_model", "side_effect_model", "model_manifest", "claim_freeze", "test_preregistration", "prerun_integrity"]
    }
    summary = {
        "stage": "A1.9", "stage_determination": "PASS_WITH_CONDITIONS",
        "a1_9a_preregistration_commit": training_commit,
        "a1_9b_result_commit": "recorded_by_enclosing_result_commit",
        "run_id": run_id, "run_directory": str(run_dir.relative_to(REPO_ROOT)).replace("\\", "/"),
        "started_at_utc": started, "completed_at_utc": completed,
        "a1_8_ready_verification": prefit["a1_8_ready"],
        "counts": counts, "models": manifest["models"],
        "warning_count": len(warning_rows),
        "convergence_warning_count": sum(bool(row["is_convergence_warning"]) for row in warning_rows),
        "reload_verification": verification["reload_verification"],
        "independent_verification": verification,
        "source_hashes_before_and_after_identical": True,
        "output_hashes": output_hashes,
        "test_access": dict(TEST_ACCESS_ZERO), "prohibited_experiments": dict(PROHIBITED_ZERO),
        "claim_freeze_status": "FROZEN",
        "a1_10_status": "NOT_AUTHORIZED_NOT_EXECUTED",
        "recommend_human_authorization_a1_10": True,
        "stop_condition": "await_explicit_human_authorization_before_any_test_access",
    }
    atomic_write_json(resolve(config["outputs"]["run_summary"]), summary)
    atomic_write_text(resolve(config["outputs"]["report"]), build_report(summary, manifest))
    atomic_write_json(run_dir / "metrics.json", verification["metric_recomputation"])
    atomic_write_text(run_dir / "stdout.log", "\n".join(log_lines + [f"{completed} independent_verification PASS", f"{completed} STOP before A1.10"]) + "\n")
    atomic_write_json(run_dir / "summary.json", summary)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-prerun", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-results", action="store_true")
    mode.add_argument("--prefit-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config.resolve())
    try:
        if args.write_prerun:
            result = write_prerun(config)
        elif args.run:
            result = execute(config)
        elif args.verify_results:
            result = verify_results(config)
        else:
            result = prefit_guard(config)
    except (IntegrityError, KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "STOP", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps({
        "status": result.get("status", result.get("stage_determination", "PASS")),
        "mode": "write-prerun" if args.write_prerun else "run" if args.run else "verify-results" if args.verify_results else "prefit-check",
        "real_dev_fit_count": 0 if not args.run else result["counts"]["estimator_fits"],
        "test_access": result.get("test_access", TEST_ACCESS_ZERO),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
