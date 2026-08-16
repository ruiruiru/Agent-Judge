"""Run Stage A1.7 B4 frozen dense-embedding LR under primary LOBO.

This script never loads the neural model.  It consumes the one-time frozen
196x1024 float32 matrix and runs the six preregistered liblinear LR configs in
the existing baseline environment, then reuses the exact A1.6 draw registry.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import warnings
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import sklearn
import yaml
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)

try:  # Support both ``python scripts/...`` and package-based unit-test imports.
    import extract_stage_a1_7_embeddings as extract
    import run_stage_a1_6_group_bootstrap as a16
except ModuleNotFoundError:  # pragma: no cover - exercised by package imports.
    from scripts import extract_stage_a1_7_embeddings as extract
    from scripts import run_stage_a1_6_group_bootstrap as a16


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_7_dense_semantic.yaml"
TARGETS = ["success", "side_effect", "looping"]
DOMAINS = ["assistantbench", "visualwebarena", "webarena", "workarena"]
BASELINE = "B4_dense_embedding_lr"
METHODS = ["B4_dense_embedding_lr", "B2", "B3"]
METRICS = ["ap", "f1", "ap_lift"]


class IntegrityError(RuntimeError):
    """Raised when a frozen A1.7 classifier/bootstrap invariant fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if path != REPO_ROOT and REPO_ROOT not in path.parents:
        raise IntegrityError(f"configured path escapes repository: {path_text}")
    return path


def sha256_path(path: Path) -> str:
    return extract.sha256_path(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


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


def write_json(path: Path, value: Any) -> None:
    extract.write_json(path, value)


def git_output(arguments: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    )
    return result.stdout


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = extract.load_config(path)
    classifier = config["classifier"]
    expected = {
        "baseline_id": BASELINE,
        "estimator": "LogisticRegression",
        "penalty": "l2",
        "solver": "liblinear",
        "max_iter": 5000,
        "fit_intercept": True,
        "random_state": 2026,
        "standard_scaler": False,
        "C": [0.1, 1.0, 10.0],
        "class_weight": [None, "balanced"],
        "config_tie_break": ["class_weight_none", "smaller_C", "config_id"],
    }
    if classifier != expected:
        raise IntegrityError("B4 classifier family/configuration changed")
    if config["selection"]["thresholds"] != [round(i / 100, 2) for i in range(5, 100, 5)]:
        raise IntegrityError("threshold grid changed")
    if config["held_out_groups"] != DOMAINS or list(config["targets"]) != TARGETS:
        raise IntegrityError("target/domain order changed")
    counts = config["expected_counts"]
    if counts != {
        "embeddings": 196, "embedding_dimensions": 1024,
        "external_predictions": 583, "selected_inner_oof": 1749,
        "config_selection": 72, "threshold_selection": 228,
        "domain_metrics": 12, "macro_metrics": 3, "pooled_metrics": 3,
    }:
        raise IntegrityError("expected formal output counts changed")
    boot = config["bootstrap"]
    if boot != {
        "unit": "task_group_cluster", "strata": ["target", "held_out_group"],
        "n_draws": 10000, "seed": 2026, "registry_reused": True,
        "percentile_interval": [2.5, 97.5], "invalid_redraw": False,
        "stratified": False, "trajectory_bootstrap": False,
        "macro_minimum_valid_mixed_domains": 2, "parallel_workers": 8,
    }:
        raise IntegrityError("A1.6 bootstrap reuse contract changed")
    return config


def assert_offline_environment() -> dict[str, Any]:
    required = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "A1_7_NETWORK": "0",
        "A1_7_LOCAL_FILES_ONLY": "true",
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    }
    actual = {key: os.environ.get(key) for key in required}
    if actual != required:
        raise IntegrityError(f"formal offline environment not frozen: {actual}")
    return actual


def assert_formal_classifier_state(config: dict[str, Any]) -> str:
    """Allow a preregistered implementation or a documented descendant fix."""

    embedding_summary = json.loads(
        resolve(config["outputs"]["embedding_extraction_summary"]).read_text(encoding="utf-8")
    )
    preregistration_commit = embedding_summary["preregistration_commit"]
    subject = git_output([
        "show", "-s", "--format=%s", preregistration_commit,
    ]).strip()
    if subject != config["execution"]["required_preregistration_commit_subject"]:
        raise IntegrityError(f"recorded A1.7a commit has unexpected subject: {subject}")
    try:
        git_output(["merge-base", "--is-ancestor", preregistration_commit, "HEAD"])
    except RuntimeError as error:
        raise IntegrityError("A1.7a preregistration is not an ancestor of HEAD") from error
    allowed = {
        config["outputs"]["embedding"],
        config["outputs"]["embedding_index"],
        config["outputs"]["embedding_extraction_summary"],
    }
    status_lines = [line for line in git_output(["status", "--porcelain=v1"]).splitlines() if line]
    observed: set[str] = set()
    for line in status_lines:
        path = line[3:].replace("\\", "/")
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        observed.add(path)
    if observed != allowed:
        raise IntegrityError(f"unexpected worktree state before B4 fit: {sorted(observed ^ allowed)}")
    return git_output(["rev-parse", "HEAD"]).strip()


def assert_preregistered_with_documented_fix(config: dict[str, Any]) -> dict[str, Any]:
    """Verify the A1.7a freeze, permitting only the recorded post-fit fix files."""

    integrity = json.loads(
        resolve(config["outputs"]["prerun_integrity"]).read_text(encoding="utf-8")
    )
    manifest = json.loads(
        resolve("artifacts/a1_7_implementation_fix_manifest.json").read_text(encoding="utf-8")
    )
    fixed = manifest["fixed_file_sha256"]
    if set(fixed) != {
        ".gitattributes",
        "scripts/run_stage_a1_7_dense_semantic.py",
        "tests/test_stage_a1_7_dense_semantic.py",
    }:
        raise IntegrityError("documented fixes change files outside verifier/tests/binary attributes")
    for relative, preregistered_hash in integrity["preregistered_files"].items():
        expected = fixed.get(relative, preregistered_hash)
        if sha256_path(resolve(relative)) != expected:
            raise IntegrityError(f"A1.7a/fix byte guard failed: {relative}")
    if manifest["embedding_invalidated"] or not manifest["all_b4_outputs_invalidated"]:
        raise IntegrityError("documented recovery disposition changed")
    return manifest


def bootstrap_verification_key(row: dict[str, Any]) -> tuple[str, ...]:
    """Identify one frozen bootstrap estimand without merging AP and F1 rows."""

    return (
        row["comparison_id"], row["target"], row["method_a"], row["method_b"],
        row["scope"], row["held_out_group"], row["metric"], row["estimand"],
    )


def _validate_inner_folds(config: dict[str, Any]) -> tuple[list[dict[str, str]], dict[str, dict[str, int]]]:
    rows = read_csv(resolve(config["inputs"]["inner_folds"]["path"]))
    if len(rows) != 2332:
        raise IntegrityError("frozen A1.3 inner fold artifact row count changed")
    counts: dict[str, dict[str, int]] = {target: {} for target in TARGETS}
    expected_total = {target: config["targets"][target]["expected_samples"] for target in TARGETS}
    for target in TARGETS:
        for domain in DOMAINS:
            cell = [row for row in rows if row["target"] == target and row["held_out_group"] == domain]
            if len(cell) != expected_total[target]:
                raise IntegrityError(f"inner cell size changed: {target}/{domain}")
            train = [row for row in cell if row["role"] == "train"]
            held = [row for row in cell if row["role"] == "held_out"]
            if len(train) + len(held) != len(cell) or any(row["inner_fold"] for row in held):
                raise IntegrityError("inner/held-out role boundary changed")
            n_splits = {int(row["inner_n_splits"]) for row in cell}
            if len(n_splits) != 1:
                raise IntegrityError("multiple inner split counts in one cell")
            n = n_splits.pop()
            if {int(row["inner_fold"]) for row in train} != set(range(1, n + 1)):
                raise IntegrityError("frozen inner folds are incomplete")
            group_fold: dict[str, set[int]] = defaultdict(set)
            for row in train:
                group_fold[row["group_key"]].add(int(row["inner_fold"]))
            if any(len(value) != 1 for value in group_fold.values()):
                raise IntegrityError("task group leaks across inner folds")
            counts[target][domain] = n
    return rows, counts


def load_embeddings(config: dict[str, Any]) -> tuple[np.ndarray, dict[str, int]]:
    verification = extract.verify_embedding_outputs(config)
    if verification["embedding_sha256"] != json.loads(
        resolve(config["outputs"]["embedding_extraction_summary"]).read_text(encoding="utf-8")
    )["embedding_sha256"]:
        raise IntegrityError("embedding extraction summary hash mismatch")
    matrix = np.load(resolve(config["outputs"]["embedding"]), allow_pickle=False)
    index = read_csv(resolve(config["outputs"]["embedding_index"]))
    key_to_row = {row["trajectory_key"]: int(row["row_index"]) for row in index}
    if len(key_to_row) != 196:
        raise IntegrityError("embedding index is not one-to-one")
    return matrix, key_to_row


def candidate_configs(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rank = 0
    for class_weight in [None, "balanced"]:
        for c_value in config["classifier"]["C"]:
            rank += 1
            c_text = str(c_value).replace(".", "p")
            cw_text = "none" if class_weight is None else "balanced"
            rows.append({
                "config_id": f"B4_C{c_text}_cw_{cw_text}",
                "C": float(c_value), "class_weight": class_weight,
                "tie_break_rank": rank,
            })
    if len(rows) != 6:
        raise IntegrityError("B4 does not expose exactly six configurations")
    return rows


def positive_probability(model: LogisticRegression, matrix: np.ndarray) -> np.ndarray:
    classes = list(model.classes_)
    if classes != [0, 1]:
        raise IntegrityError(f"unexpected fitted LR classes: {classes}")
    return model.predict_proba(matrix)[:, classes.index(1)]


def fit_predict(
    config: dict[str, Any], candidate: dict[str, Any], matrix: np.ndarray,
    key_to_row: dict[str, int], train_keys: Sequence[str], validation_keys: Sequence[str],
    labels: dict[str, int], context: dict[str, Any], warning_rows: list[dict[str, Any]],
) -> np.ndarray:
    y_train = np.asarray([labels[key] for key in train_keys], dtype=np.int8)
    if set(y_train.tolist()) != {0, 1}:
        raise IntegrityError(f"training partition is not mixed class: {context}")
    x_train = matrix[[key_to_row[key] for key in train_keys]]
    x_validation = matrix[[key_to_row[key] for key in validation_keys]]
    model = LogisticRegression(
        penalty=config["classifier"]["penalty"],
        solver=config["classifier"]["solver"],
        max_iter=config["classifier"]["max_iter"],
        fit_intercept=config["classifier"]["fit_intercept"],
        random_state=config["classifier"]["random_state"],
        C=candidate["C"], class_weight=candidate["class_weight"],
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(x_train, y_train)
    for item in caught:
        warning_rows.append({
            **context, "config_id": candidate["config_id"],
            "category": item.category.__name__, "message": str(item.message),
        })
    return positive_probability(model, x_validation)


def threshold_rows(
    config: dict[str, Any], truth: Sequence[int], probabilities: Sequence[float]
) -> tuple[float, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for threshold in config["selection"]["thresholds"]:
        predicted = [int(value >= threshold) for value in probabilities]
        rows.append({
            "threshold": threshold,
            "inner_f1": f1_score(truth, predicted, pos_label=1, zero_division=0),
            "inner_precision": precision_score(truth, predicted, pos_label=1, zero_division=0),
            "inner_recall": recall_score(truth, predicted, pos_label=1, zero_division=0),
        })
    best_f1 = max(float(row["inner_f1"]) for row in rows)
    tied = [row for row in rows if math.isclose(float(row["inner_f1"]), best_f1, abs_tol=1e-15, rel_tol=0)]
    selected = min(
        tied,
        key=lambda row: (
            -float(row["inner_recall"]),
            abs(float(row["threshold"]) - 0.5),
            float(row["threshold"]),
        ),
    )
    for row in rows:
        row["selected"] = row is selected
    return float(selected["threshold"]), rows


def metric_values(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    truth = np.asarray([int(row["true_label"]) for row in rows], dtype=np.int8)
    probabilities = np.asarray([float(row["predicted_probability"]) for row in rows], dtype=float)
    predicted = np.asarray([int(row["predicted_label"]) for row in rows], dtype=np.int8)
    prevalence = float(np.mean(truth))
    if np.unique(truth).size != 2:
        return {
            "metric_status": "single_class_negative" if int(np.sum(truth)) == 0 else "single_class_positive",
            "prevalence": prevalence,
            "pr_auc_average_precision": None, "positive_f1": None, "roc_auc": None,
            "precision": None, "recall": None, "f2": None,
            "balanced_accuracy": None, "mcc": None, "ap_lift": None,
        }
    ap = float(average_precision_score(truth, probabilities))
    return {
        "metric_status": "ok", "prevalence": prevalence,
        "pr_auc_average_precision": ap,
        "positive_f1": float(f1_score(truth, predicted, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(truth, probabilities)),
        "precision": float(precision_score(truth, predicted, pos_label=1, zero_division=0)),
        "recall": float(recall_score(truth, predicted, pos_label=1, zero_division=0)),
        "f2": float(fbeta_score(truth, predicted, beta=2, pos_label=1, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
        "mcc": float(matthews_corrcoef(truth, predicted)),
        "ap_lift": ap - prevalence,
    }


METRIC_NAMES = [
    "pr_auc_average_precision", "positive_f1", "roc_auc", "precision",
    "recall", "f2", "balanced_accuracy", "mcc",
]
DOMAIN_FIELDS = [
    "target", "baseline_id", "held_out_group", "held_out_size", "task_group_count",
    "positive_count", "negative_count", "prevalence", "predicted_positive_count",
    "predicted_positive_rate", "selected_config_id", "selected_threshold", "inner_n_splits",
    "metric_status", *METRIC_NAMES, "ap_lift", "false_positive_count",
    "false_positive_rate", "specificity", "probability_mean", "probability_median",
    "probability_max",
]


def domain_metric_row(
    target: str, domain: str, rows: Sequence[dict[str, Any]], selected_config: str,
    threshold: float, n_splits: int,
) -> dict[str, Any]:
    truth = [int(row["true_label"]) for row in rows]
    predicted = [int(row["predicted_label"]) for row in rows]
    probabilities = [float(row["predicted_probability"]) for row in rows]
    positive = sum(truth)
    negative = len(truth) - positive
    groups = {row["group_key"] for row in rows}
    values = metric_values(rows)
    false_positive = sum(y == 0 and p == 1 for y, p in zip(truth, predicted, strict=True))
    return {
        "target": target, "baseline_id": BASELINE, "held_out_group": domain,
        "held_out_size": len(rows), "task_group_count": len(groups),
        "positive_count": positive, "negative_count": negative,
        "prevalence": values["prevalence"],
        "predicted_positive_count": sum(predicted),
        "predicted_positive_rate": sum(predicted) / len(predicted),
        "selected_config_id": selected_config, "selected_threshold": threshold,
        "inner_n_splits": n_splits, **{name: values[name] for name in ["metric_status", *METRIC_NAMES, "ap_lift"]},
        "false_positive_count": false_positive,
        "false_positive_rate": false_positive / negative if negative else None,
        "specificity": sum(y == 0 and p == 0 for y, p in zip(truth, predicted, strict=True)) / negative if negative else None,
        "probability_mean": float(np.mean(probabilities)),
        "probability_median": float(np.median(probabilities)),
        "probability_max": float(np.max(probabilities)),
    }


def macro_rows(domain_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        cell = [row for row in domain_rows if row["target"] == target]
        valid = [row for row in cell if row["metric_status"] == "ok"]
        row: dict[str, Any] = {
            "target": target, "baseline_id": BASELINE,
            "valid_domain_count": len(valid),
            "excluded_single_class_domain_count": len(cell) - len(valid),
        }
        for metric in [*METRIC_NAMES, "ap_lift"]:
            values = [float(item[metric]) for item in valid]
            row[f"{metric}_macro_mean"] = statistics.mean(values)
            row[f"{metric}_macro_std"] = statistics.stdev(values) if len(values) > 1 else None
        output.append(row)
    return output


def pooled_rows(predictions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        cell = [row for row in predictions if row["target"] == target]
        truth = [int(row["true_label"]) for row in cell]
        values = metric_values(cell)
        output.append({
            "target": target, "baseline_id": BASELINE, "sample_count": len(cell),
            "positive_count": sum(truth), "negative_count": len(truth) - sum(truth),
            "prevalence": values["prevalence"],
            **{name: values[name] for name in [*METRIC_NAMES, "ap_lift"]},
        })
    return output


def comparison_rows(
    config: dict[str, Any], macro: Sequence[dict[str, Any]], pooled: Sequence[dict[str, Any]]
) -> list[dict[str, Any]]:
    frozen_macro = read_csv(resolve(config["inputs"]["a1_3_macro_metrics"]["path"]))
    frozen_pooled = read_csv(resolve(config["inputs"]["a1_3_pooled_metrics"]["path"]))
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        b4m = next(row for row in macro if row["target"] == target)
        b4p = next(row for row in pooled if row["target"] == target)
        row: dict[str, Any] = {
            "target": target,
            "b4_macro_ap": b4m["pr_auc_average_precision_macro_mean"],
            "b4_macro_f1": b4m["positive_f1_macro_mean"],
            "b4_macro_ap_lift": b4m["ap_lift_macro_mean"],
            "b4_pooled_ap": b4p["pr_auc_average_precision"],
            "b4_pooled_f1": b4p["positive_f1"],
            "b4_pooled_ap_lift": b4p["ap_lift"],
        }
        for method in ["B2", "B3"]:
            fm = next(r for r in frozen_macro if r["target"] == target and r["baseline_id"] == method)
            fp = next(r for r in frozen_pooled if r["target"] == target and r["baseline_id"] == method)
            prefix = method.lower()
            row.update({
                f"{prefix}_macro_ap": float(fm["pr_auc_average_precision_macro_mean"]),
                f"{prefix}_macro_f1": float(fm["positive_f1_macro_mean"]),
                f"b4_minus_{prefix}_macro_ap": float(b4m["pr_auc_average_precision_macro_mean"]) - float(fm["pr_auc_average_precision_macro_mean"]),
                f"b4_minus_{prefix}_macro_f1": float(b4m["positive_f1_macro_mean"]) - float(fm["positive_f1_macro_mean"]),
                f"{prefix}_pooled_ap": float(fp["pr_auc_average_precision"]),
                f"{prefix}_pooled_f1": float(fp["positive_f1"]),
                f"b4_minus_{prefix}_pooled_ap": float(b4p["pr_auc_average_precision"]) - float(fp["pr_auc_average_precision"]),
                f"b4_minus_{prefix}_pooled_f1": float(b4p["positive_f1"]) - float(fp["positive_f1"]),
            })
        output.append(row)
    return output


def run_b4(
    config: dict[str, Any], matrix: np.ndarray, key_to_row: dict[str, int],
    folds: Sequence[dict[str, str]], inner_counts: dict[str, dict[str, int]],
) -> dict[str, Any]:
    candidates = candidate_configs(config)
    config_rows: list[dict[str, Any]] = []
    selected_inner: list[dict[str, Any]] = []
    threshold_selection: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    domain_metrics: list[dict[str, Any]] = []
    warning_rows: list[dict[str, Any]] = []
    config_distribution: Counter[tuple[str, str]] = Counter()
    threshold_distribution: Counter[tuple[str, float]] = Counter()

    for target in TARGETS:
        for domain in DOMAINS:
            cell = [row for row in folds if row["target"] == target and row["held_out_group"] == domain]
            train_rows = [row for row in cell if row["role"] == "train"]
            held_rows = [row for row in cell if row["role"] == "held_out"]
            labels = {row["trajectory_key"]: int(row["label"]) for row in cell}
            n_splits = inner_counts[target][domain]
            candidate_oof: dict[str, dict[str, float]] = {}
            candidate_result_rows: list[dict[str, Any]] = []
            for candidate in candidates:
                oof: dict[str, float] = {}
                for inner_fold in range(1, n_splits + 1):
                    validation_keys = [row["trajectory_key"] for row in train_rows if int(row["inner_fold"]) == inner_fold]
                    fit_keys = [row["trajectory_key"] for row in train_rows if int(row["inner_fold"]) != inner_fold]
                    probabilities = fit_predict(
                        config, candidate, matrix, key_to_row, fit_keys, validation_keys,
                        labels, {"target": target, "held_out_group": domain, "phase": "inner", "inner_fold": inner_fold},
                        warning_rows,
                    )
                    for key, probability in zip(validation_keys, probabilities, strict=True):
                        if key in oof:
                            raise IntegrityError("duplicate pooled inner OOF prediction")
                        oof[key] = float(probability)
                train_keys = [row["trajectory_key"] for row in train_rows]
                if set(oof) != set(train_keys):
                    raise IntegrityError("candidate pooled inner OOF is incomplete")
                score = float(average_precision_score(
                    [labels[key] for key in train_keys], [oof[key] for key in train_keys]
                ))
                result = {
                    "target": target, "held_out_group": domain, "baseline_id": BASELINE,
                    "config_id": candidate["config_id"], "inner_n_splits": n_splits,
                    "inner_oof_size": len(oof), "inner_oof_pr_auc": score,
                    "selected": False, "tie_break_rank": candidate["tie_break_rank"],
                }
                candidate_result_rows.append(result)
                candidate_oof[candidate["config_id"]] = oof
            best_score = max(float(row["inner_oof_pr_auc"]) for row in candidate_result_rows)
            selected_config_row = min(
                (row for row in candidate_result_rows if math.isclose(float(row["inner_oof_pr_auc"]), best_score, abs_tol=1e-15, rel_tol=0)),
                key=lambda row: int(row["tie_break_rank"]),
            )
            selected_config_row["selected"] = True
            config_rows.extend(candidate_result_rows)
            selected_id = str(selected_config_row["config_id"])
            selected_candidate = next(item for item in candidates if item["config_id"] == selected_id)
            config_distribution[(target, selected_id)] += 1
            selected_oof = candidate_oof[selected_id]
            train_keys = [row["trajectory_key"] for row in train_rows]
            threshold, tested = threshold_rows(
                config, [labels[key] for key in train_keys], [selected_oof[key] for key in train_keys]
            )
            threshold_distribution[(target, threshold)] += 1
            fold_by_key = {row["trajectory_key"]: int(row["inner_fold"]) for row in train_rows}
            for key in train_keys:
                selected_inner.append({
                    "trajectory_key": key, "target": target, "baseline_id": BASELINE,
                    "held_out_group": domain, "inner_fold": fold_by_key[key],
                    "true_label": labels[key], "predicted_probability": selected_oof[key],
                    "selected_config_id": selected_id, "inner_n_splits": n_splits,
                })
            for row in tested:
                threshold_selection.append({
                    "target": target, "held_out_group": domain, "baseline_id": BASELINE,
                    "selected_config_id": selected_id, **row,
                })
            held_keys = [row["trajectory_key"] for row in held_rows]
            held_probabilities = fit_predict(
                config, selected_candidate, matrix, key_to_row, train_keys, held_keys,
                labels, {"target": target, "held_out_group": domain, "phase": "final_refit", "inner_fold": ""},
                warning_rows,
            )
            external_cell: list[dict[str, Any]] = []
            for source, probability in zip(held_rows, held_probabilities, strict=True):
                row = {
                    "trajectory_key": source["trajectory_key"], "group_key": source["group_key"],
                    "target": target, "baseline_id": BASELINE, "held_out_group": domain,
                    "true_label": int(source["label"]), "predicted_probability": float(probability),
                    "selected_threshold": threshold, "predicted_label": int(float(probability) >= threshold),
                    "selected_config_id": selected_id, "inner_n_splits": n_splits,
                }
                external.append(row)
                external_cell.append(row)
            domain_metrics.append(domain_metric_row(
                target, domain, external_cell, selected_id, threshold, n_splits
            ))
            print(json.dumps({"phase": "B4", "target": target, "held_out_group": domain, "completed_cells": len(domain_metrics), "total_cells": 12}), flush=True)

    macros = macro_rows(domain_metrics)
    pooled = pooled_rows(external)
    counts = {
        "inner_config_selection": len(config_rows),
        "inner_selected_oof_predictions": len(selected_inner),
        "threshold_selection": len(threshold_selection),
        "external_predictions": len(external),
        "domain_metrics": len(domain_metrics), "macro_metrics": len(macros),
        "pooled_metrics": len(pooled),
    }
    expected = config["expected_counts"]
    wanted = {
        "inner_config_selection": expected["config_selection"],
        "inner_selected_oof_predictions": expected["selected_inner_oof"],
        "threshold_selection": expected["threshold_selection"],
        "external_predictions": expected["external_predictions"],
        "domain_metrics": expected["domain_metrics"],
        "macro_metrics": expected["macro_metrics"],
        "pooled_metrics": expected["pooled_metrics"],
    }
    if counts != wanted:
        raise IntegrityError(f"B4 output counts mismatch: {counts} != {wanted}")
    return {
        "config_rows": config_rows, "selected_inner": selected_inner,
        "threshold_rows": threshold_selection, "external": external,
        "domain": domain_metrics, "macro": macros, "pooled": pooled,
        "warning_rows": warning_rows, "counts": counts,
        "config_distribution": [
            {"target": key[0], "config_id": key[1], "count": count}
            for key, count in sorted(config_distribution.items())
        ],
        "threshold_distribution": [
            {"target": key[0], "threshold": key[1], "count": count}
            for key, count in sorted(threshold_distribution.items())
        ],
    }


def _prediction_methods(
    config: dict[str, Any], b4: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    a13 = read_csv(resolve(config["inputs"]["a1_3_predictions"]["path"]))
    output = {BASELINE: b4}
    for method in ["B2", "B3"]:
        output[method] = [row for row in a13 if row["baseline_id"] == method]
    if any(len(rows) != 583 for rows in output.values()):
        raise IntegrityError("B4/B2/B3 prediction coverage is not 583 each")
    return output


def _aligned_cells(
    predictions: dict[str, list[dict[str, Any]]],
    groups_by_cell: dict[tuple[str, str], list[str]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    result: dict[tuple[str, str, str], dict[str, Any]] = {}
    for target in TARGETS:
        for domain in DOMAINS:
            reference: list[str] | None = None
            for method in METHODS:
                cell = sorted(
                    [row for row in predictions[method] if row["target"] == target and row["held_out_group"] == domain],
                    key=lambda row: row["trajectory_key"],
                )
                keys = [row["trajectory_key"] for row in cell]
                if reference is None:
                    reference = keys
                elif keys != reference:
                    raise IntegrityError("B4/B2/B3 do not share exact external keys")
                groups = groups_by_cell[(target, domain)]
                clusters = [
                    np.asarray([i for i, row in enumerate(cell) if row["group_key"] == group], dtype=np.int16)
                    for group in groups
                ]
                if any(cluster.size == 0 for cluster in clusters):
                    raise IntegrityError("bootstrap registry group missing from predictions")
                result[(target, method, domain)] = {
                    "truth": np.asarray([int(row["true_label"]) for row in cell], dtype=np.int8),
                    "probability": np.asarray([float(row["predicted_probability"]) for row in cell], dtype=float),
                    "predicted": np.asarray([int(row["predicted_label"]) for row in cell], dtype=np.int8),
                    "clusters": clusters,
                }
    return result


def _point_lookup(predictions: dict[str, list[dict[str, Any]]]) -> dict[tuple[str, str, str, str], float | None]:
    result: dict[tuple[str, str, str, str], float | None] = {}
    for target in TARGETS:
        for method in METHODS:
            domain_values: dict[str, dict[str, Any]] = {}
            pooled: list[dict[str, Any]] = []
            for domain in DOMAINS:
                cell = [row for row in predictions[method] if row["target"] == target and row["held_out_group"] == domain]
                values = metric_values(cell)
                domain_values[domain] = values
                pooled.extend(cell)
                for metric, field in [("ap", "pr_auc_average_precision"), ("f1", "positive_f1"), ("ap_lift", "ap_lift")]:
                    result[(target, method, "domain:" + domain, metric)] = values[field]
            for metric, field in [("ap", "pr_auc_average_precision"), ("f1", "positive_f1"), ("ap_lift", "ap_lift")]:
                valid = [float(domain_values[d][field]) for d in DOMAINS if domain_values[d][field] is not None]
                result[(target, method, "macro", metric)] = float(np.mean(valid))
                result[(target, method, "pooled", metric)] = metric_values(pooled)[field]
    return result


def _compute_bootstrap(
    config: dict[str, Any], b4: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, list[Any]], dict[str, Any]]:
    predictions = _prediction_methods(config, b4)
    a13_all = read_csv(resolve(config["inputs"]["a1_3_predictions"]["path"]))
    groups = a16.group_registry_source(a13_all)
    registry_path = resolve(config["inputs"]["bootstrap_registry"]["path"])
    if sha256_path(registry_path) != config["inputs"]["bootstrap_registry"]["sha256"]:
        raise IntegrityError("A1.6 bootstrap registry hash changed")
    draws = a16.verify_draw_registry(registry_path, groups, 10000, 2026)
    cells = _aligned_cells(predictions, groups)
    domain_values: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    jobs = []
    with ProcessPoolExecutor(max_workers=config["bootstrap"]["parallel_workers"]) as executor:
        for key, cell in cells.items():
            target, _, domain = key
            jobs.append(executor.submit(
                a16._domain_worker,
                (key, cell["truth"], cell["probability"], cell["predicted"], cell["clusters"], draws[(target, domain)]),
            ))
        for future in as_completed(jobs):
            key, values = future.result()
            domain_values[key] = values
    macro_values: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    for target in TARGETS:
        for method in METHODS:
            values: dict[str, np.ndarray] = {}
            for metric in METRICS:
                matrix = np.vstack([domain_values[(target, method, domain)][metric] for domain in DOMAINS])
                count = np.sum(np.isfinite(matrix), axis=0)
                result = np.full(10000, np.nan)
                good = count >= config["bootstrap"]["macro_minimum_valid_mixed_domains"]
                result[good] = np.nanmean(matrix[:, good], axis=0)
                values[metric] = result
            values["valid_domain_count"] = np.sum(np.isfinite(np.vstack([
                domain_values[(target, method, domain)]["ap"] for domain in DOMAINS
            ])), axis=0)
            macro_values[(target, method)] = values
    pooled_values: dict[tuple[str, str], dict[str, np.ndarray]] = {}
    jobs = []
    with ProcessPoolExecutor(max_workers=config["bootstrap"]["parallel_workers"]) as executor:
        for target in TARGETS:
            for method in METHODS:
                key = (target, method)
                jobs.append(executor.submit(
                    a16._pooled_worker,
                    (key, {domain: cells[(target, method, domain)] for domain in DOMAINS},
                     {domain: draws[(target, domain)] for domain in DOMAINS}),
                ))
        for future in as_completed(jobs):
            key, values = future.result()
            pooled_values[key] = values
    point = _point_lookup(predictions)

    specs: list[dict[str, Any]] = [
        {"id": "Q1", "target": "success", "kind": "positive_signal", "method_a": BASELINE, "method_b": "", "scope": "macro", "metric": "ap_lift", "role": "primary"},
        {"id": "Q2", "target": "success", "kind": "paired_delta", "method_a": BASELINE, "method_b": "B3", "scope": "macro", "metric": "ap", "role": "primary"},
        {"id": "Q2", "target": "success", "kind": "paired_delta", "method_a": BASELINE, "method_b": "B3", "scope": "macro", "metric": "f1", "role": "primary"},
        {"id": "Q3", "target": "success", "kind": "paired_delta", "method_a": BASELINE, "method_b": "B2", "scope": "macro", "metric": "ap", "role": "primary"},
        {"id": "Q3", "target": "success", "kind": "paired_delta", "method_a": BASELINE, "method_b": "B2", "scope": "macro", "metric": "f1", "role": "primary"},
        {"id": "Q4", "target": "side_effect", "kind": "support_diagnostic", "method_a": BASELINE, "method_b": "", "scope": "macro", "metric": "ap", "role": "support_diagnostic_only"},
        {"id": "Q4", "target": "side_effect", "kind": "support_diagnostic", "method_a": BASELINE, "method_b": "", "scope": "pooled", "metric": "ap", "role": "support_diagnostic_only"},
        {"id": "Q4", "target": "side_effect", "kind": "support_diagnostic", "method_a": BASELINE, "method_b": "B3", "scope": "macro", "metric": "ap", "role": "support_diagnostic_only"},
        {"id": "Q5", "target": "looping", "kind": "paired_delta", "method_a": BASELINE, "method_b": "B2", "scope": "macro", "metric": "ap", "role": "secondary_complexity_control"},
    ]
    for domain in DOMAINS:
        specs.append({
            "id": "Q4", "target": "side_effect", "kind": "support_diagnostic",
            "method_a": BASELINE, "method_b": "", "scope": "domain", "held_out_group": domain,
            "metric": "ap", "role": "support_diagnostic_only",
        })
    rows: list[dict[str, Any]] = []
    parquet: dict[str, list[Any]] = defaultdict(list)
    for spec in specs:
        target, method_a, method_b = spec["target"], spec["method_a"], spec["method_b"]
        scope, metric = spec["scope"], spec["metric"]
        domain = spec.get("held_out_group", "")
        if scope == "domain":
            values_a = domain_values[(target, method_a, domain)][metric]
            point_a = point[(target, method_a, "domain:" + domain, metric)]
            valid_domains = np.full(10000, 1)
        else:
            collection = macro_values if scope == "macro" else pooled_values
            values_a = collection[(target, method_a)][metric]
            point_a = point[(target, method_a, scope, metric)]
            valid_domains = collection[(target, method_a)].get("valid_domain_count", np.full(10000, 4))
        if method_b:
            if scope == "domain":
                values_b = domain_values[(target, method_b, domain)][metric]
                point_b = point[(target, method_b, "domain:" + domain, metric)]
            else:
                collection = macro_values if scope == "macro" else pooled_values
                values_b = collection[(target, method_b)][metric]
                point_b = point[(target, method_b, scope, metric)]
            statistic = values_a - values_b
            point_value = float(point_a) - float(point_b)
            estimand = f"{scope}_{metric}_delta_A_minus_B"
        else:
            values_b = np.full(10000, np.nan)
            statistic = values_a.copy()
            point_value = None if point_a is None else float(point_a)
            estimand = f"{scope}_{metric}"
        summary = a16.summarize(statistic, point_value)
        grade = "support_diagnostic_only" if spec["id"] == "Q4" else a16._grade(spec["kind"], summary)
        row = {
            "comparison_id": spec["id"], "target": target, "kind": spec["kind"],
            "method_a": method_a, "method_b": method_b, "scope": scope,
            "held_out_group": domain, "metric": metric, "estimand": estimand,
            "role": spec["role"], **summary, "bootstrap_grade": grade,
        }
        rows.append(row)
        for index in range(10000):
            parquet["comparison_id"].append(spec["id"])
            parquet["target"].append(target)
            parquet["kind"].append(spec["kind"])
            parquet["method_a"].append(method_a)
            parquet["method_b"].append(method_b)
            parquet["scope"].append(scope)
            parquet["held_out_group"].append(domain)
            parquet["metric"].append(metric)
            parquet["estimand"].append(estimand)
            parquet["role"].append(spec["role"])
            parquet["bootstrap_id"].append(index + 1)
            parquet["method_a_value"].append(None if not np.isfinite(values_a[index]) else float(values_a[index]))
            parquet["method_b_value"].append(None if not np.isfinite(values_b[index]) else float(values_b[index]))
            parquet["statistic_value"].append(None if not np.isfinite(statistic[index]) else float(statistic[index]))
            parquet["metric_status"].append("ok" if np.isfinite(statistic[index]) else "invalid_single_class_resample")
            parquet["valid_domain_count"].append(int(valid_domains[index]))
    return rows, parquet, {
        "registry_sha256": sha256_path(registry_path),
        "registry_rows": 1530000, "new_registry_generated": False,
        "draw_rows": len(parquet["comparison_id"]), "estimand_rows": len(rows),
    }


BOOTSTRAP_FIELDS = [
    "comparison_id", "target", "kind", "method_a", "method_b", "scope",
    "held_out_group", "metric", "estimand", "role", "point_estimate",
    "bootstrap_median", "ci_lower_95", "ci_upper_95", "ci_width",
    "fixed_draw_count", "valid_draw_count", "invalid_draw_count",
    "valid_draw_fraction", "bootstrap_grade",
]


def _write_parquet(path: Path, columns: dict[str, list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    pq.write_table(pa.table(columns), temporary, compression="zstd", use_dictionary=True)
    temporary.replace(path)


def success_conclusion(primary: Sequence[dict[str, Any]]) -> str:
    q1 = next(row for row in primary if row["comparison_id"] == "Q1")
    q2 = next(row for row in primary if row["comparison_id"] == "Q2" and row["metric"] == "ap")
    q3 = next(row for row in primary if row["comparison_id"] == "Q3" and row["metric"] == "ap")
    if q1["ci_lower_95"] is None or float(q1["ci_lower_95"]) <= 0:
        return "dense_semantic_cross_benchmark_signal_uncertain"
    if q2["ci_lower_95"] is not None and float(q2["ci_lower_95"]) > 0:
        if q3["ci_lower_95"] is not None and float(q3["ci_lower_95"]) > 0:
            return "dense_semantics_outperform_current_lightweight_baselines"
        return "dense_semantics_add_value_over_tfidf"
    return "dense_semantic_signal_without_clear_incremental_gain"


def side_effect_conclusion(primary: Sequence[dict[str, Any]]) -> str:
    delta = next(row for row in primary if row["comparison_id"] == "Q4" and row["method_b"] == "B3")
    if delta["point_estimate"] is not None and float(delta["point_estimate"]) > 0:
        return "promising_low_support_semantic_signal"
    return "no_clear_semantic_improvement"


def looping_conclusion(primary: Sequence[dict[str, Any]]) -> str:
    q5 = next(row for row in primary if row["comparison_id"] == "Q5")
    if q5["ci_lower_95"] is not None and float(q5["ci_lower_95"]) > 0:
        return "semantic_additional_signal_descriptive"
    return "semantic_complexity_not_needed"


def verify_results(config: dict[str, Any]) -> dict[str, Any]:
    outputs = config["outputs"]
    configs = read_csv(resolve(outputs["inner_config_selection"]))
    inner = read_csv(resolve(outputs["inner_selected_oof_predictions"]))
    thresholds = read_csv(resolve(outputs["threshold_selection"]))
    predictions = read_csv(resolve(outputs["external_predictions"]))
    domain = read_csv(resolve(outputs["domain_metrics"]))
    macro = read_csv(resolve(outputs["macro_metrics"]))
    pooled = read_csv(resolve(outputs["pooled_metrics"]))
    primary = read_csv(resolve(outputs["bootstrap_primary_summary"]))
    expected = config["expected_counts"]
    actual = {
        "external_predictions": len(predictions), "selected_inner_oof": len(inner),
        "config_selection": len(configs), "threshold_selection": len(thresholds),
        "domain_metrics": len(domain), "macro_metrics": len(macro), "pooled_metrics": len(pooled),
    }
    if actual != {key: expected[key] for key in actual}:
        raise IntegrityError(f"formal result counts cannot be verified: {actual}")
    if len({(row["target"], row["trajectory_key"]) for row in predictions}) != 583:
        raise IntegrityError("external target/trajectory predictions are duplicated")
    if len({(row["target"], row["held_out_group"], row["trajectory_key"]) for row in inner}) != 1749:
        raise IntegrityError("selected inner OOF predictions are duplicated")
    folds, _ = _validate_inner_folds(config)
    role = {(row["target"], row["held_out_group"], row["trajectory_key"]): row["role"] for row in folds}
    if any(role[(row["target"], row["held_out_group"], row["trajectory_key"])] != "train" for row in inner):
        raise IntegrityError("held-out trajectory entered selected inner OOF")
    for target in TARGETS:
        for heldout in DOMAINS:
            selection = [row for row in configs if row["target"] == target and row["held_out_group"] == heldout]
            if len(selection) != 6:
                raise IntegrityError("configuration cell does not contain six candidates")
            chosen = [row for row in selection if row["selected"] == "True"]
            best = max(float(row["inner_oof_pr_auc"]) for row in selection)
            expected_config = min(
                (row for row in selection if math.isclose(float(row["inner_oof_pr_auc"]), best, abs_tol=1e-15, rel_tol=0)),
                key=lambda row: int(row["tie_break_rank"]),
            )
            if len(chosen) != 1 or chosen[0]["config_id"] != expected_config["config_id"]:
                raise IntegrityError("configuration selection does not reproduce")
            inner_cell = [row for row in inner if row["target"] == target and row["held_out_group"] == heldout]
            selected_threshold, _ = threshold_rows(
                config,
                [int(row["true_label"]) for row in inner_cell],
                [float(row["predicted_probability"]) for row in inner_cell],
            )
            chosen_threshold = [row for row in thresholds if row["target"] == target and row["held_out_group"] == heldout and row["selected"] == "True"]
            if len(chosen_threshold) != 1 or not math.isclose(float(chosen_threshold[0]["threshold"]), selected_threshold, abs_tol=1e-15):
                raise IntegrityError("threshold selection does not reproduce")
    recomputed_domain: list[dict[str, Any]] = []
    for row in domain:
        cell = [item for item in predictions if item["target"] == row["target"] and item["held_out_group"] == row["held_out_group"]]
        recomputed_domain.append(domain_metric_row(
            row["target"], row["held_out_group"], cell, row["selected_config_id"],
            float(row["selected_threshold"]), int(row["inner_n_splits"]),
        ))
    for wanted, recorded in zip(recomputed_domain, domain, strict=True):
        for field in [*METRIC_NAMES, "ap_lift"]:
            if wanted[field] is None:
                if recorded[field] != "":
                    raise IntegrityError("single-class metric was imputed")
            elif not math.isclose(float(wanted[field]), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError(f"domain metric cannot be reproduced: {field}")
    recomputed_macro = macro_rows(recomputed_domain)
    recomputed_pooled = pooled_rows(predictions)
    for wanted, recorded in zip(recomputed_macro, macro, strict=True):
        for field in [f"{metric}_macro_{suffix}" for metric in [*METRIC_NAMES, "ap_lift"] for suffix in ["mean", "std"]]:
            if not math.isclose(float(wanted[field]), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError(f"macro metric cannot be reproduced: {field}")
    for wanted, recorded in zip(recomputed_pooled, pooled, strict=True):
        for field in [*METRIC_NAMES, "ap_lift"]:
            if not math.isclose(float(wanted[field]), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError(f"pooled metric cannot be reproduced: {field}")
    table = pq.read_table(resolve(outputs["bootstrap_draw_metrics"]))
    draw_rows = table.to_pylist()
    if len(draw_rows) != len(primary) * 10000:
        raise IntegrityError("bootstrap draw parquet row count mismatch")
    grouped: dict[tuple[str, ...], list[float]] = defaultdict(list)
    for row in draw_rows:
        if row["statistic_value"] is not None:
            grouped[bootstrap_verification_key(row)].append(float(row["statistic_value"]))
    for row in primary:
        key = bootstrap_verification_key(row)
        values = np.asarray(grouped[key], dtype=float)
        if len(values) != int(row["valid_draw_count"]):
            raise IntegrityError("bootstrap valid draw count cannot be reproduced")
        if len(values):
            lower, upper = np.percentile(values, [2.5, 97.5])
            if not math.isclose(float(lower), float(row["ci_lower_95"]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError("bootstrap lower CI cannot be reproduced")
            if not math.isclose(float(upper), float(row["ci_upper_95"]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError("bootstrap upper CI cannot be reproduced")
    return {"status": "PASS", **actual, "bootstrap_estimands": len(primary), "bootstrap_draw_rows": len(draw_rows), "test_access": 0, "forbidden_experiments": 0}


def render_report(config: dict[str, Any], summary: dict[str, Any]) -> str:
    domain = read_csv(resolve(config["outputs"]["domain_metrics"]))
    macro = read_csv(resolve(config["outputs"]["macro_metrics"]))
    pooled = read_csv(resolve(config["outputs"]["pooled_metrics"]))
    comparison = read_csv(resolve(config["outputs"]["comparison_to_a1_3"]))
    primary = read_csv(resolve(config["outputs"]["bootstrap_primary_summary"]))
    extraction_summary = json.loads(resolve(config["outputs"]["embedding_extraction_summary"]).read_text(encoding="utf-8"))

    def f(value: Any) -> str:
        return "NA" if value is None or value == "" else f"{float(value):.6f}"

    lines = [
        "# Stage A1.7 frozen dense semantic baseline report", "",
        "## Stage determination", "", f"`{summary['stage_determination']}`", "",
        "All technical completeness guards passed. Interpretation remains conditional because Side Effect has only 12 positives and one single-class held-out domain.", "",
        "## Provenance and model freeze", "",
        f"- A1.7a preregistration commit: `{summary['preregistration_commit']}`",
        "- A1.7b experiment commit: recorded by the enclosing result commit.",
        f"- Data GitHub revision: `{config['source']['github_commit']}`",
        f"- Data Hugging Face revision: `{config['source']['huggingface_revision']}`",
        f"- Model: `{config['model']['repo_id']}`; requested revision `{config['model']['requested_revision']}`; immutable revision `{config['model']['immutable_revision']}`.",
        f"- `model.safetensors` SHA-256: `{config['model']['weight_sha256']}`.",
        f"- Semantic environment: Python {summary['semantic_environment']['python']['version']}; torch {summary['semantic_environment']['dependencies']['torch']}; CUDA {summary['semantic_environment']['hardware']['cuda_runtime']}; GPU {summary['semantic_environment']['hardware']['gpu']}; transformers {summary['semantic_environment']['dependencies']['transformers']}.", "",
        "## Tokenization, chunking, pooling, and determinism", "",
        "Payload is `tokenizer.encode(text, add_special_tokens=False)`, split in-order into non-overlapping payload chunks of at most 8191 tokens, with exactly one tokenizer EOS appended. There is no truncation.",
        "Each chunk uses the last EOS hidden state, float32 L2 normalization, payload-token-count weighted mean, and final trajectory L2 normalization.",
        f"- Payload tokens min/median/mean/p95/max: {summary['tokenization']['payload_token_count']['min']}/{f(summary['tokenization']['payload_token_count']['median'])}/{f(summary['tokenization']['payload_token_count']['mean'])}/{f(summary['tokenization']['payload_token_count']['p95'])}/{summary['tokenization']['payload_token_count']['max']}.",
        f"- Chunk count min/median/mean/p95/max: {summary['tokenization']['chunk_count']['min']}/{f(summary['tokenization']['chunk_count']['median'])}/{f(summary['tokenization']['chunk_count']['mean'])}/{f(summary['tokenization']['chunk_count']['p95'])}/{summary['tokenization']['chunk_count']['max']}.",
        f"- Total payload tokens/chunks and multi-chunk trajectories: {summary['tokenization']['total_payload_tokens']}/{summary['tokenization']['total_chunks']}/{summary['tokenization']['multi_chunk_trajectories']}.",
        f"- Fixed 16-probe minimum cosine: `{extraction_summary['determinism_probe']['minimum_cosine_similarity']:.9f}`; maximum absolute difference: `{extraction_summary['determinism_probe']['maximum_absolute_difference']:.3e}`; PASS.", "",
        "## Frozen embeddings and B4", "",
        f"- Matrix: `196 × 1024`, float32, finite, L2-normalized; SHA-256 `{summary['embedding_sha256']}`.",
        "- Classifier: LogisticRegression, L2/liblinear, max_iter=5000, random_state=2026, no StandardScaler; C={0.1,1,10} × class_weight={None,balanced}.",
        f"- Selected config distribution: `{json.dumps(summary['selected_config_distribution'], ensure_ascii=False)}`.",
        f"- Selected threshold distribution: `{json.dumps(summary['selected_threshold_distribution'], ensure_ascii=False)}`.", "",
        "## Four-domain B4 results", "",
        "| Target | Held-out | Status | Pos/Neg | AP | AP lift | F1 | Config | Threshold |", "|---|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for row in domain:
        lines.append(f"| {row['target']} | {row['held_out_group']} | {row['metric_status']} | {row['positive_count']}/{row['negative_count']} | {f(row['pr_auc_average_precision'])} | {f(row['ap_lift'])} | {f(row['positive_f1'])} | `{row['selected_config_id']}` | {f(row['selected_threshold'])} |")
    lines.extend(["", "## Macro and pooled results", "", "| Target | Macro AP | Macro F1 | Pooled AP | Pooled F1 |", "|---|---:|---:|---:|---:|"])
    for target in TARGETS:
        m = next(row for row in macro if row["target"] == target)
        p = next(row for row in pooled if row["target"] == target)
        lines.append(f"| {target} | {f(m['pr_auc_average_precision_macro_mean'])} | {f(m['positive_f1_macro_mean'])} | {f(p['pr_auc_average_precision'])} | {f(p['positive_f1'])} |")
    lines.extend(["", "## Frozen A1.3 comparisons", "", "| Target | B4−B2 macro AP/F1 | B4−B3 macro AP/F1 | B4−B2 pooled AP/F1 | B4−B3 pooled AP/F1 |", "|---|---:|---:|---:|---:|"])
    for row in comparison:
        lines.append(f"| {row['target']} | {f(row['b4_minus_b2_macro_ap'])}/{f(row['b4_minus_b2_macro_f1'])} | {f(row['b4_minus_b3_macro_ap'])}/{f(row['b4_minus_b3_macro_f1'])} | {f(row['b4_minus_b2_pooled_ap'])}/{f(row['b4_minus_b2_pooled_f1'])} | {f(row['b4_minus_b3_pooled_ap'])}/{f(row['b4_minus_b3_pooled_f1'])} |")
    lines.extend(["", "## Q1–Q5 fixed group-aware bootstrap", "", "| ID | Target | Estimand | Role | Point | Median | 95% CI | Valid | Invalid | Grade |", "|---|---|---|---|---:|---:|---|---:|---:|---|"])
    for row in primary:
        label = f"{row['method_a']}{'−' + row['method_b'] if row['method_b'] else ''} {row['estimand']}"
        if row["held_out_group"]:
            label += f" ({row['held_out_group']})"
        lines.append(f"| {row['comparison_id']} | {row['target']} | {label} | {row['role']} | {f(row['point_estimate'])} | {f(row['bootstrap_median'])} | [{f(row['ci_lower_95'])}, {f(row['ci_upper_95'])}] | {f(row['valid_draw_fraction'])} | {row['invalid_draw_count']} | `{row['bootstrap_grade']}` |")
    lines.extend([
        "", "## Frozen conclusions", "",
        f"- Success: `{summary['conclusions']['success']}`.",
        f"- Side Effect: `{summary['conclusions']['side_effect']}`; role remains `support_diagnostic_only`, with 12 total positives and AssistantBench 0/24.",
        f"- Looping: `{summary['conclusions']['looping']}`; role remains `secondary_complexity_control`.", "",
        "## Integrity and boundaries", "",
        f"- External predictions: {summary['row_counts']['external_predictions']}/583; selected inner OOF: {summary['row_counts']['inner_selected_oof_predictions']}/1749; configs: {summary['row_counts']['inner_config_selection']}/72; thresholds: {summary['row_counts']['threshold_selection']}/228.",
        f"- A1.6 registry reused byte-for-byte: `{summary['bootstrap']['registry_sha256']}`; new registry generated: 0.",
        f"- Frozen hashes identical before/after: `{summary['hashes_before_run'] == summary['hashes_after_run']}`.",
        "- Fine-tune=0; quantization=0; fusion=0; second embedding model=0; new classifier family=0.",
        "- Formal network=0; local_files_only=true; test content/labels/predictions/metrics access=0; prohibited experiments=0.",
        f"- Tests: `{summary['tests']}`.", "",
        "## Stage recommendation and stop", "",
        f"`{summary['stage_determination']}`. The A1.7 evidence is complete and awaits human review. Do not enter fusion, a second embedding model, LLM Judge, secondary LOBO, joint OOD, or test.", "",
    ])
    return "\n".join(lines)


def baseline_environment() -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now(), "python": platform.python_version(),
        "executable": sys.executable, "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(), "numpy": np.__version__,
        "scikit_learn": sklearn.__version__, "pyarrow": pa.__version__,
        "gpu_used": False, "formal_run_network_allowed": False,
        "standard_scaler": False,
    }


def append_experiment_registry(config: dict[str, Any], summary: dict[str, Any]) -> None:
    path = REPO_ROOT / "research" / "02_EXPERIMENT_REGISTRY.csv"
    rows = read_csv(path)
    if any(row["run_id"] == summary["run_id"] for row in rows):
        raise IntegrityError("formal run_id already exists in experiment registry")
    fields = list(rows[0])
    rows.append({
        "run_id": summary["run_id"],
        "experiment_name": "Stage A1.7 frozen dense semantic baseline",
        "hypothesis_id": "H1", "git_commit": summary["preregistration_commit"],
        "data_version": config["source"]["data_version"],
        "split_version": config["source"]["split_version"],
        "config_path": "configs/stage_a1_7_dense_semantic.yaml", "seed": "2026",
        "protocol": "A1.3 primary four-group LOBO with frozen dense embedding",
        "model": "Qwen/Qwen3-Embedding-0.6B@97b0c614 + LogisticRegression",
        "start_time": summary["started_at_utc"], "end_time": summary["completed_at_utc"],
        "hardware": "Windows 11 AMD64; embedding RTX 5070; classifier CPU",
        "status": summary["stage_determination"],
        "primary_metric": "Average Precision and positive F1 with task-group bootstrap CI",
        "output_path": config["outputs"]["run_summary"],
        "notes": "196x1024 frozen embeddings; 583 external; 1749 inner OOF; network 0 formal; test 0",
    })
    write_csv(path, rows, fields)


def formal_run(config: dict[str, Any]) -> None:
    execution_code_commit = assert_formal_classifier_state(config)
    offline = assert_offline_environment()
    fix_manifest = assert_preregistered_with_documented_fix(config)
    input_hashes_before = extract.verify_input_hashes(config)
    embedding_verification = extract.verify_embedding_outputs(config)
    matrix, key_to_row = load_embeddings(config)
    folds, inner_counts = _validate_inner_folds(config)
    output_keys = [
        "inner_config_selection", "inner_selected_oof_predictions", "threshold_selection",
        "external_predictions", "domain_metrics", "macro_metrics", "pooled_metrics",
        "comparison_to_a1_3", "bootstrap_primary_summary", "bootstrap_draw_metrics",
        "run_summary", "report",
    ]
    existing = [config["outputs"][key] for key in output_keys if resolve(config["outputs"][key]).exists()]
    if existing:
        raise IntegrityError(f"formal B4 output exists; refusing overwrite: {existing}")
    started = utc_now()
    embedding_summary = json.loads(
        resolve(config["outputs"]["embedding_extraction_summary"]).read_text(encoding="utf-8")
    )
    preregistration_commit = embedding_summary["preregistration_commit"]
    run_id = f"a1_7_dense_semantic_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{execution_code_commit[:8]}"
    run_dir = resolve(f"runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "command.txt").write_text(
        f"{sys.executable} scripts/run_stage_a1_7_dense_semantic.py --config configs/stage_a1_7_dense_semantic.yaml --run\n",
        encoding="utf-8", newline="\n",
    )
    shutil.copy2(CONFIG_PATH, run_dir / "config.yaml")
    write_json(run_dir / "environment.json", baseline_environment())
    write_json(run_dir / "hashes_before.json", input_hashes_before)
    (run_dir / "stdout.log").write_text(
        f"{started} B4 guards PASS; starting six-config primary LOBO\n",
        encoding="utf-8", newline="\n",
    )
    start_clock = time.perf_counter()
    result = run_b4(config, matrix, key_to_row, folds, inner_counts)
    paths = config["outputs"]
    write_csv(resolve(paths["inner_config_selection"]), result["config_rows"], [
        "target", "held_out_group", "baseline_id", "config_id", "inner_n_splits",
        "inner_oof_size", "inner_oof_pr_auc", "selected", "tie_break_rank",
    ])
    write_csv(resolve(paths["inner_selected_oof_predictions"]), result["selected_inner"], [
        "trajectory_key", "target", "baseline_id", "held_out_group", "inner_fold",
        "true_label", "predicted_probability", "selected_config_id", "inner_n_splits",
    ])
    write_csv(resolve(paths["threshold_selection"]), result["threshold_rows"], [
        "target", "held_out_group", "baseline_id", "selected_config_id", "threshold",
        "inner_f1", "inner_precision", "inner_recall", "selected",
    ])
    prediction_fields = [
        "trajectory_key", "group_key", "target", "baseline_id", "held_out_group",
        "true_label", "predicted_probability", "selected_threshold", "predicted_label",
        "selected_config_id", "inner_n_splits",
    ]
    write_csv(resolve(paths["external_predictions"]), result["external"], prediction_fields)
    write_csv(resolve(paths["domain_metrics"]), result["domain"], DOMAIN_FIELDS)
    macro_fields = list(result["macro"][0])
    pooled_fields = list(result["pooled"][0])
    write_csv(resolve(paths["macro_metrics"]), result["macro"], macro_fields)
    write_csv(resolve(paths["pooled_metrics"]), result["pooled"], pooled_fields)
    comparisons = comparison_rows(config, result["macro"], result["pooled"])
    write_csv(resolve(paths["comparison_to_a1_3"]), comparisons, list(comparisons[0]))
    print(json.dumps({"phase": "bootstrap", "registry": config["inputs"]["bootstrap_registry"]["sha256"]}), flush=True)
    primary, draw_columns, bootstrap_info = _compute_bootstrap(config, result["external"])
    write_csv(resolve(paths["bootstrap_primary_summary"]), primary, BOOTSTRAP_FIELDS)
    _write_parquet(resolve(paths["bootstrap_draw_metrics"]), draw_columns)
    input_hashes_after = extract.verify_input_hashes(config)
    if input_hashes_before != input_hashes_after:
        raise IntegrityError("frozen upstream inputs changed during formal B4 run")
    warnings_by_category = Counter(row["category"] for row in result["warning_rows"])
    convergence = sum(row["category"] == ConvergenceWarning.__name__ for row in result["warning_rows"])
    if convergence:
        raise IntegrityError(f"B4 convergence warnings encountered: {convergence}")
    semantic_env = json.loads(resolve(config["outputs"]["semantic_environment"]).read_text(encoding="utf-8"))
    summary = {
        "stage": "A1.7", "stage_determination": "PASS_WITH_CONDITIONS",
        "started_at_utc": started, "completed_at_utc": utc_now(),
        "run_id": run_id, "run_directory": run_dir.relative_to(REPO_ROOT).as_posix(),
        "preregistration_commit": preregistration_commit,
        "execution_code_commit": execution_code_commit,
        "implementation_fix": fix_manifest,
        "experiment_commit": "recorded_after_commit",
        "source_revisions": config["source"],
        "model": config["model"], "semantic_environment": semantic_env,
        "classifier_environment": baseline_environment(), "offline_environment": offline,
        "embedding_sha256": embedding_verification["embedding_sha256"],
        "embedding_shape": [196, 1024], "embedding_dtype": "float32",
        "tokenization": json.loads(resolve(paths["embedding_extraction_summary"]).read_text(encoding="utf-8"))["tokenization"],
        "determinism_probe": json.loads(resolve(paths["embedding_extraction_summary"]).read_text(encoding="utf-8"))["determinism_probe"],
        "row_counts": result["counts"],
        "selected_config_distribution": result["config_distribution"],
        "selected_threshold_distribution": result["threshold_distribution"],
        "warning_count": len(result["warning_rows"]),
        "warning_categories": dict(warnings_by_category), "convergence_warning_count": convergence,
        "bootstrap": bootstrap_info, "primary_inference": primary,
        "conclusions": {
            "success": success_conclusion(primary),
            "side_effect": side_effect_conclusion(primary),
            "looping": looping_conclusion(primary),
        },
        "side_effect_support": {
            "total_positive": 12, "assistantbench_positive": 0,
            "assistantbench_negative": 24, "role": "support_diagnostic_only",
        },
        "elapsed_seconds_classifier_and_bootstrap": time.perf_counter() - start_clock,
        "hashes_before_run": input_hashes_before, "hashes_after_run": input_hashes_after,
        "network_access": 0, "local_files_only": True, "fine_tune_count": 0,
        "quantization_count": 0, "fusion_count": 0, "second_embedding_model_count": 0,
        "new_classifier_family_count": 0, "new_bootstrap_registry_count": 0,
        "test_access": {"content": 0, "labels": 0, "predictions": 0, "metrics": 0},
        "forbidden_experiments_executed": [], "tests": "pending final verification",
    }
    write_json(resolve(paths["run_summary"]), summary)
    report = render_report(config, summary)
    resolve(paths["report"]).write_text(report, encoding="utf-8", newline="\n")
    verification = verify_results(config)
    summary["tests"] = "independent result recomputation PASS; repository tests pending"
    output_keys_for_hash = [
        "embedding", "embedding_index", "embedding_extraction_summary",
        "inner_config_selection", "inner_selected_oof_predictions", "threshold_selection",
        "external_predictions", "domain_metrics", "macro_metrics", "pooled_metrics",
        "comparison_to_a1_3", "bootstrap_primary_summary", "bootstrap_draw_metrics",
    ]
    summary["output_hashes"] = {
        key: sha256_path(resolve(paths[key])) for key in output_keys_for_hash
    }
    write_json(resolve(paths["run_summary"]), summary)
    resolve(paths["report"]).write_text(render_report(config, summary), encoding="utf-8", newline="\n")
    summary["output_hashes"]["report"] = sha256_path(resolve(paths["report"]))
    write_json(resolve(paths["run_summary"]), summary)
    append_experiment_registry(config, summary)
    write_json(run_dir / "verification.json", verification)
    write_json(run_dir / "completed.json", {"status": summary["stage_determination"], "completed_at_utc": utc_now()})
    print(json.dumps({"status": summary["stage_determination"], "run_id": run_id, **verification}), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        config = load_config(Path(args.config).resolve())
        if args.run:
            formal_run(config)
        else:
            print(json.dumps(verify_results(config)))
        return 0
    except Exception as error:
        print(json.dumps({"status": "STOP", "error_type": type(error).__name__, "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
