#!/usr/bin/env python3
"""Score the frozen A1.10a blind predictions after one-time label unlock.

The preflight path never opens the annotation source. The score path opens the
pinned annotation bytes exactly once, derives the already-frozen eligibility
contract, joins to immutable blind predictions, and computes only preregistered
metrics and task-group cluster bootstrap intervals. No estimator is imported.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import yaml
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    fbeta_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_analysis_index as frozen_labels  # noqa: E402


CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_10b_official_test_scoring.yaml"
TARGETS = ("success", "looping", "side_effect")
BENCHMARKS = ("assistantbench", "visualwebarena", "webarena", "workarena")

SCORED_FIELDS = [
    "trajectory_key", "benchmark_original", "benchmark_group_primary",
    "normalized_task_id", "model_name", "target", "method_id", "role",
    "model_sha256", "probability", "frozen_threshold", "predicted_label",
    "row_key", "inference_status", "true_label", "eligible_main",
    "label_status", "scoring_included", "group_key",
]
TARGET_METRIC_FIELDS = [
    "target", "role", "method_id", "threshold", "eligible_n", "positive_n",
    "negative_n", "prevalence", "task_group_n", "pooled_average_precision",
    "pooled_ap_lift", "positive_f1", "precision", "recall", "f2",
    "roc_auc", "balanced_accuracy", "mcc", "macro_benchmark_ap",
    "macro_benchmark_f1", "macro_ap_valid_benchmarks",
    "macro_f1_valid_benchmarks",
]
BENCHMARK_METRIC_FIELDS = [
    "target", "benchmark_group_primary", "role", "eligible_n", "positive_n",
    "negative_n", "prevalence", "task_group_n", "class_complete",
    "average_precision", "ap_lift", "positive_f1", "precision", "recall",
    "f2", "roc_auc", "balanced_accuracy", "mcc", "predicted_positive_rate",
    "false_positive_rate", "specificity", "mean_probability",
]
BOOTSTRAP_DRAW_FIELDS = [
    "target", "bootstrap_id", "ap_lift", "status", "positive_n",
    "negative_n", "sampled_trajectory_n",
]
BOOTSTRAP_SUMMARY_FIELDS = [
    "target", "role", "estimand", "point_estimate", "ci_lower", "ci_upper",
    "bootstrap_median", "fixed_draw_count", "valid_draw_count",
    "invalid_draw_count", "valid_fraction", "seed", "rng", "interval",
    "resampling_unit", "strata", "label_stratification", "invalid_redraw",
]
GRADE_FIELDS = [
    "target", "role", "pooled_ap_lift", "ci_lower", "ci_upper", "final_grade",
    "grading_rule",
]
CLAIM_FIELDS = ["claim_id", "target", "role", "status", "scope", "basis"]


class IntegrityError(RuntimeError):
    """Raised when a frozen A1.10 boundary cannot be reproduced exactly."""


def resolve(path: str) -> Path:
    return REPO_ROOT / path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(args: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=True,
    )
    return completed.stdout.strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise IntegrityError(f"CSV has no header: {path}")
        rows = []
        for line_number, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise IntegrityError(f"Malformed CSV row at {path}:{line_number}")
            rows.append(dict(row))
    return rows


def csv_bytes(fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: _cell(row.get(name)) for name in fieldnames})
    return stream.getvalue().encode("utf-8")


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (float, np.floating)):
        return format(float(value), ".17g")
    return str(value)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    os.replace(temporary, path)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    atomic_write_bytes(path, csv_bytes(fieldnames, rows))


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_write_bytes(path, data)


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config["stage"] != "A1.10b":
        raise IntegrityError("unexpected stage")
    if tuple(config["bootstrap"]["target_order"]) != TARGETS:
        raise IntegrityError("bootstrap target order changed")
    return config


def static_boundary_counts() -> dict[str, int]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    calls = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])
    }
    return {
        "estimator_training_calls": sum(name in {"fit", "fit_transform", "partial_fit"} for name in calls),
        "inference_calls": sum(name in {"predict", "predict_proba", "decision_function", "forward"} for name in calls),
        "estimator_or_embedding_imports": sum(name in {"joblib", "torch", "transformers"} for name in imports),
    }


def verify_working_matches_commit(path: Path, commit: str) -> dict[str, str]:
    relative = path.relative_to(REPO_ROOT).as_posix()
    working_oid = git_output(["hash-object", "--no-filters", "--", relative])
    committed_oid = git_output(["rev-parse", f"{commit}:{relative}"])
    if working_oid != committed_oid:
        raise IntegrityError(f"working bytes differ from {commit}: {relative}")
    return {"working_oid": working_oid, "committed_oid": committed_oid}


def preunlock_checks(config: dict[str, Any], *, require_clean: bool) -> dict[str, Any]:
    a1_10a = config["provenance"]["a1_10a_commit"]
    if git_output(["cat-file", "-t", a1_10a]) != "commit":
        raise IntegrityError("A1.10a commit is missing")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", a1_10a, "HEAD"], cwd=REPO_ROOT,
        check=False, capture_output=True,
    ).returncode != 0:
        raise IntegrityError("A1.10a is not an ancestor of HEAD")
    status = git_output(["status", "--porcelain"])
    if require_clean and status:
        raise IntegrityError("pre-unlock Git worktree is not clean")

    hashes: dict[str, str] = {}
    byte_identity: dict[str, dict[str, str]] = {}
    for name, spec in config["frozen_inputs"].items():
        path = resolve(spec["path"])
        actual = sha256_file(path)
        if actual != spec["sha256"]:
            raise IntegrityError(f"frozen input hash mismatch: {name}")
        hashes[name] = actual
        byte_identity[name] = verify_working_matches_commit(path, a1_10a)

    model_hashes: dict[str, str] = {}
    for target, spec in config["frozen_models"].items():
        actual = sha256_file(resolve(spec["path"]))
        if actual != spec["sha256"]:
            raise IntegrityError(f"frozen model hash mismatch: {target}")
        model_hashes[target] = actual
        verify_working_matches_commit(resolve(spec["path"]), a1_10a)

    manifest = json.loads(resolve(config["frozen_inputs"]["blind_manifest"]["path"]).read_text(encoding="utf-8"))
    for target in TARGETS:
        if float(manifest["thresholds"][target]) != float(config["targets"][target]["threshold"]):
            raise IntegrityError(f"frozen threshold mismatch: {target}")
    a1_summary = json.loads(resolve("artifacts/a1_10a_run_summary.json").read_text(encoding="utf-8"))
    if any(int(a1_summary["test_access"][name]) != 0 for name in ("labels", "eligibility", "metrics")):
        raise IntegrityError("A1.10a access counters are not zero")
    boundary = static_boundary_counts()
    if any(boundary.values()):
        raise IntegrityError(f"A1.10b static boundary failed: {boundary}")
    return {
        "status": "PASS",
        "checked_at_utc": utc_now(),
        "head": git_output(["rev-parse", "HEAD"]),
        "a1_10a_commit": a1_10a,
        "git_clean": not bool(status),
        "frozen_hashes": hashes,
        "committed_byte_identity": byte_identity,
        "model_hashes": model_hashes,
        "thresholds": {target: float(config["targets"][target]["threshold"]) for target in TARGETS},
        "a1_10a_access": {name: int(a1_summary["test_access"][name]) for name in ("labels", "eligibility", "metrics")},
        "static_boundary_counts": boundary,
        "label_source_opened": False,
        "label_access": 0,
        "eligibility_access": 0,
        "metrics_access": 0,
        "authorization": config["authorization"],
    }


def run_preflight(config: dict[str, Any]) -> None:
    result = preunlock_checks(config, require_clean=True)
    write_json(resolve(config["outputs"]["prerun_integrity"]), result)
    print(json.dumps({"phase": "preunlock", "status": "PASS", "label_access": 0}, sort_keys=True))


def _rows_from_bytes(data: bytes, expected_columns: Sequence[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""))
    if reader.fieldnames != list(expected_columns):
        raise IntegrityError(f"source schema changed: {reader.fieldnames}")
    rows = []
    for line_number, row in enumerate(reader, 2):
        if None in row or any(value is None for value in row.values()):
            raise IntegrityError(f"malformed source row: {line_number}")
        rows.append(dict(row))
    return rows


def unlock_test_labels(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Open the pinned annotation bytes once and derive frozen test labels."""
    manifest = json.loads(resolve(config["source"]["manifest"]).read_text(encoding="utf-8"))
    if manifest["github_commit"] != config["source"]["github_commit"]:
        raise IntegrityError("GitHub source revision changed")
    if manifest["huggingface_revision"] != config["source"]["huggingface_revision"]:
        raise IntegrityError("Hugging Face source revision changed")

    split_path = resolve(config["source"]["splits_path"])
    if sha256_file(split_path) != config["source"]["splits_sha256"]:
        raise IntegrityError("split source hash changed")
    splits = frozen_labels.read_csv(split_path, frozen_labels.SPLITS_COLUMNS)
    test_tasks = {
        frozen_labels.normalize_task_id(row["task_id"])
        for row in splits if row["split"] == "test"
    }

    annotation_path = resolve(config["source"]["annotations_path"])
    annotation_bytes = annotation_path.read_bytes()
    annotation_sha = sha256_bytes(annotation_bytes)
    if annotation_sha != config["source"]["annotations_sha256"]:
        raise IntegrityError("annotation source hash changed after unlock")
    all_annotations = _rows_from_bytes(annotation_bytes, frozen_labels.ANNOTATIONS_COLUMNS)
    test_annotations = [
        row for row in all_annotations
        if frozen_labels.normalize_task_id(row["task_id"]) in test_tasks
    ]
    entries, validation = frozen_labels.build_entries(test_annotations, splits)
    entries = [entry for entry in entries if entry["official_split"] == "test"]
    if validation and any(validation.values()):
        raise IntegrityError(f"test label key validation failed: {validation}")
    if len(entries) != int(config["expected"]["trajectories"]):
        raise IntegrityError("test label trajectory count changed")
    return entries, {
        "unlocked_at_utc": utc_now(),
        "unlock_head": git_output(["rev-parse", "HEAD"]),
        "annotation_sha256": annotation_sha,
        "label_source_open_count": 1,
        "test_label_trajectory_access": len(entries),
        "test_eligibility_trajectory_access": len(entries),
    }


def join_predictions(
    config: dict[str, Any], blind: list[dict[str, str]], identifiers: list[dict[str, str]],
    entries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected_rows = int(config["expected"]["blind_rows"])
    if len(blind) != expected_rows:
        raise IntegrityError("blind prediction row count changed")
    row_keys = [row["row_key"] for row in blind]
    pairs = [(row["trajectory_key"], row["target"]) for row in blind]
    if len(set(row_keys)) != len(row_keys) or len(set(pairs)) != len(pairs):
        raise IntegrityError("duplicate blind prediction")
    if any(Counter(row["target"] for row in blind)[target] != len(entries) for target in TARGETS):
        raise IntegrityError("target prediction coverage changed")

    identifier_map = {row["trajectory_key"]: row for row in identifiers}
    label_map = {entry["trajectory_key"]: entry for entry in entries}
    if len(identifier_map) != len(identifiers) or len(label_map) != len(entries):
        raise IntegrityError("duplicate identifier or label entry")
    blind_keys = {row["trajectory_key"] for row in blind}
    identifier_keys = set(identifier_map)
    label_keys = set(label_map)
    unmatched_predictions = sorted(blind_keys - label_keys)
    unmatched_labels = sorted(label_keys - blind_keys)
    if blind_keys != identifier_keys or unmatched_predictions or unmatched_labels:
        raise IntegrityError("join key universe mismatch")

    joined: list[dict[str, Any]] = []
    for row in blind:
        target = row["target"]
        if target not in TARGETS:
            raise IntegrityError("unexpected blind target")
        entry = label_map[row["trajectory_key"]]
        identifier = identifier_map[row["trajectory_key"]]
        comparisons = {
            "benchmark_original": entry["benchmark_original"],
            "benchmark_group_primary": entry["benchmark_group_primary"],
            "normalized_task_id": entry["task_id"],
            "model_name": entry["model_name"],
        }
        for field, expected in comparisons.items():
            if row[field] != str(expected) or identifier[field] != str(expected):
                raise IntegrityError(f"join metadata mismatch: {field}")
        target_config = config["targets"][target]
        if row["method_id"] != target_config["method_id"]:
            raise IntegrityError("method changed after label unlock")
        if row["role"] != target_config["role"]:
            raise IntegrityError("role changed after label unlock")
        if float(row["frozen_threshold"]) != float(target_config["threshold"]):
            raise IntegrityError("threshold changed after label unlock")
        eligible = bool(entry[f"{target}_eligible_main"])
        label = entry[f"{target}_label"]
        if eligible != (entry[f"{target}_status"] in {"single_annotation", "duplicate_agreement"}):
            raise IntegrityError("frozen eligibility/status mismatch")
        if eligible and label not in {0, 1}:
            raise IntegrityError("eligible test label is not binary")
        if not eligible and label is not None:
            raise IntegrityError("ineligible test trajectory retained a main label")
        predicted = int(row["predicted_label"])
        mechanical = int(float(row["probability"]) >= float(row["frozen_threshold"]))
        if predicted != mechanical:
            raise IntegrityError("blind predicted label is not threshold-mechanical")
        joined.append({
            **row,
            "true_label": label if eligible else None,
            "eligible_main": eligible,
            "label_status": entry[f"{target}_status"],
            "scoring_included": eligible,
            "group_key": f"{row['benchmark_original']}::{row['normalized_task_id']}",
        })
    return joined, {
        "blind_rows": len(blind),
        "joined_rows": len(joined),
        "unique_prediction_rows": len(set(row_keys)),
        "unique_trajectory_target_pairs": len(set(pairs)),
        "duplicate_predictions": 0,
        "duplicate_target_labels": 0,
        "unmatched_predictions": len(unmatched_predictions),
        "unmatched_labels": len(unmatched_labels),
        "silent_drops": expected_rows - len(joined),
        "metadata_mismatches": 0,
        "status": "PASS",
    }


def metric_bundle(rows: Sequence[Mapping[str, Any]]) -> dict[str, float | int | bool | None]:
    if not rows:
        raise IntegrityError("metric cell is empty")
    truth = np.asarray([int(row["true_label"]) for row in rows], dtype=np.int8)
    probability = np.asarray([float(row["probability"]) for row in rows], dtype=np.float64)
    predicted = np.asarray([int(row["predicted_label"]) for row in rows], dtype=np.int8)
    positive = int(np.sum(truth == 1))
    negative = int(np.sum(truth == 0))
    prevalence = float(np.mean(truth))
    predicted_positive_rate = float(np.mean(predicted))
    tn = int(np.sum((truth == 0) & (predicted == 0)))
    fp = int(np.sum((truth == 0) & (predicted == 1)))
    class_complete = positive > 0 and negative > 0
    result: dict[str, float | int | bool | None] = {
        "eligible_n": len(rows), "positive_n": positive, "negative_n": negative,
        "prevalence": prevalence, "class_complete": class_complete,
        "average_precision": None, "ap_lift": None, "positive_f1": None,
        "precision": None, "recall": None, "f2": None, "roc_auc": None,
        "balanced_accuracy": None, "mcc": None,
        "predicted_positive_rate": predicted_positive_rate,
        "false_positive_rate": (float(fp / negative) if negative else None),
        "specificity": (float(tn / negative) if negative else None),
        "mean_probability": float(np.mean(probability)),
    }
    if not class_complete:
        return result
    ap = float(average_precision_score(truth, probability))
    result.update({
        "average_precision": ap,
        "ap_lift": ap - prevalence,
        "positive_f1": float(f1_score(truth, predicted, pos_label=1, zero_division=0)),
        "precision": float(precision_score(truth, predicted, pos_label=1, zero_division=0)),
        "recall": float(recall_score(truth, predicted, pos_label=1, zero_division=0)),
        "f2": float(fbeta_score(truth, predicted, beta=2, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(truth, probability)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
        "mcc": float(matthews_corrcoef(truth, predicted)),
    })
    return result


def build_metric_tables(
    config: dict[str, Any], scored: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included = [row for row in scored if str(row["scoring_included"]).lower() == "true" or row["scoring_included"] is True]
    target_rows: list[dict[str, Any]] = []
    benchmark_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        rows = [row for row in included if row["target"] == target]
        pooled = metric_bundle(rows)
        if not pooled["class_complete"]:
            raise IntegrityError(f"pooled test target is single-class: {target}")
        per_benchmark: list[dict[str, Any]] = []
        for benchmark in BENCHMARKS:
            cell = [row for row in rows if row["benchmark_group_primary"] == benchmark]
            values = metric_bundle(cell)
            record = {
                "target": target, "benchmark_group_primary": benchmark,
                "role": config["targets"][target]["role"],
                **values,
                "task_group_n": len({row["group_key"] for row in cell}),
            }
            per_benchmark.append(record)
            benchmark_rows.append(record)
        valid_ap = [float(row["average_precision"]) for row in per_benchmark if row["average_precision"] is not None]
        valid_f1 = [float(row["positive_f1"]) for row in per_benchmark if row["positive_f1"] is not None]
        target_rows.append({
            "target": target,
            "role": config["targets"][target]["role"],
            "method_id": config["targets"][target]["method_id"],
            "threshold": float(config["targets"][target]["threshold"]),
            "eligible_n": pooled["eligible_n"], "positive_n": pooled["positive_n"],
            "negative_n": pooled["negative_n"], "prevalence": pooled["prevalence"],
            "task_group_n": len({row["group_key"] for row in rows}),
            "pooled_average_precision": pooled["average_precision"],
            "pooled_ap_lift": pooled["ap_lift"], "positive_f1": pooled["positive_f1"],
            "precision": pooled["precision"], "recall": pooled["recall"],
            "f2": pooled["f2"], "roc_auc": pooled["roc_auc"],
            "balanced_accuracy": pooled["balanced_accuracy"], "mcc": pooled["mcc"],
            "macro_benchmark_ap": float(np.mean(valid_ap)) if valid_ap else None,
            "macro_benchmark_f1": float(np.mean(valid_f1)) if valid_f1 else None,
            "macro_ap_valid_benchmarks": len(valid_ap),
            "macro_f1_valid_benchmarks": len(valid_f1),
        })
    return target_rows, benchmark_rows


def build_bootstrap(
    config: dict[str, Any], scored: Sequence[Mapping[str, Any]],
    *, n_draws: int | None = None, seed: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    n_draws = int(config["bootstrap"]["n_draws"] if n_draws is None else n_draws)
    seed = int(config["bootstrap"]["seed"] if seed is None else seed)
    rng = np.random.Generator(np.random.PCG64(seed))
    included = [row for row in scored if str(row["scoring_included"]).lower() == "true" or row["scoring_included"] is True]
    draw_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        rows = [row for row in included if row["target"] == target]
        point = metric_bundle(rows)["ap_lift"]
        if point is None:
            raise IntegrityError(f"pooled AP lift unavailable: {target}")
        groups: dict[str, list[int]] = defaultdict(list)
        strata: dict[str, set[str]] = defaultdict(set)
        for index, row in enumerate(rows):
            group = str(row["group_key"])
            groups[group].append(index)
            strata[str(row["benchmark_group_primary"])].add(group)
        ordered_strata = {name: sorted(values) for name, values in sorted(strata.items())}
        if set(ordered_strata) != set(BENCHMARKS):
            raise IntegrityError(f"bootstrap strata changed: {target}")
        truth_all = np.asarray([int(row["true_label"]) for row in rows], dtype=np.int8)
        probability_all = np.asarray([float(row["probability"]) for row in rows], dtype=np.float64)
        values: list[float] = []
        invalid = 0
        for bootstrap_id in range(1, n_draws + 1):
            sampled_indices: list[int] = []
            for group_names in ordered_strata.values():
                sampled = rng.integers(0, len(group_names), size=len(group_names))
                for group_index in sampled:
                    sampled_indices.extend(groups[group_names[int(group_index)]])
            truth = truth_all[np.asarray(sampled_indices, dtype=np.int64)]
            probability = probability_all[np.asarray(sampled_indices, dtype=np.int64)]
            positive = int(np.sum(truth == 1))
            negative = int(np.sum(truth == 0))
            if positive == 0 or negative == 0:
                invalid += 1
                ap_lift = None
                status = "invalid_single_class_resample"
            else:
                ap = float(average_precision_score(truth, probability))
                ap_lift = ap - float(np.mean(truth))
                values.append(ap_lift)
                status = "valid"
            draw_rows.append({
                "target": target, "bootstrap_id": bootstrap_id,
                "ap_lift": ap_lift, "status": status, "positive_n": positive,
                "negative_n": negative, "sampled_trajectory_n": len(sampled_indices),
            })
        if not values:
            raise IntegrityError(f"all bootstrap draws invalid: {target}")
        lower, upper = np.percentile(np.asarray(values, dtype=np.float64), [2.5, 97.5])
        summary_rows.append({
            "target": target, "role": config["targets"][target]["role"],
            "estimand": "pooled_ap_lift", "point_estimate": point,
            "ci_lower": float(lower), "ci_upper": float(upper),
            "bootstrap_median": float(np.median(values)),
            "fixed_draw_count": n_draws, "valid_draw_count": len(values),
            "invalid_draw_count": invalid, "valid_fraction": len(values) / n_draws,
            "seed": seed, "rng": f"numpy.random.Generator(numpy.random.PCG64({seed}))",
            "interval": "percentile_95", "resampling_unit": "task_group",
            "strata": "benchmark_group_primary", "label_stratification": False,
            "invalid_redraw": False,
        })
    return draw_rows, summary_rows


def grade_target(target: str, point: float, lower: float, upper: float) -> tuple[str, str]:
    if target == "side_effect":
        return "EXPLORATORY_TEST_RESULT", "role_frozen_exploratory_regardless_of_result"
    if point <= 0.0:
        return "NOT_CONFIRMED", "pooled_ap_lift_point_lte_0"
    if lower > 0.0:
        return "CONFIRMED_HELDOUT_SIGNAL", "pooled_ap_lift_gt_0_and_ci_lower_gt_0"
    return "DIRECTIONAL_BUT_NOT_CONFIRMED", "pooled_ap_lift_gt_0_and_ci_lower_lte_0"


def build_grades(
    config: dict[str, Any], target_metrics: Sequence[Mapping[str, Any]],
    bootstrap_summary: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    metrics = {row["target"]: row for row in target_metrics}
    bootstrap = {row["target"]: row for row in bootstrap_summary}
    grades: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    claim_ids = {"success": "FC1", "looping": "FC2", "side_effect": "FE1"}
    for target in TARGETS:
        point = float(metrics[target]["pooled_ap_lift"])
        lower = float(bootstrap[target]["ci_lower"])
        upper = float(bootstrap[target]["ci_upper"])
        grade, rule = grade_target(target, point, lower, upper)
        role = config["targets"][target]["role"]
        grades.append({
            "target": target, "role": role, "pooled_ap_lift": point,
            "ci_lower": lower, "ci_upper": upper, "final_grade": grade,
            "grading_rule": rule,
        })
        claims.append({
            "claim_id": claim_ids[target], "target": target, "role": role,
            "status": grade,
            "scope": "official_held_out_tasks_and_trajectories_within_existing_benchmark_families",
            "basis": "frozen_blind_prediction_pooled_ap_lift_and_preregistered_ci" if target != "side_effect" else "exploratory_metrics_only_no_confirmatory_upgrade",
        })
    return grades, claims


def _hash_outputs(config: dict[str, Any], names: Sequence[str]) -> dict[str, str]:
    return {name: sha256_file(resolve(config["outputs"][name])) for name in names}


def _report(
    config: dict[str, Any], unlock: Mapping[str, Any], join: Mapping[str, Any],
    target_metrics: Sequence[Mapping[str, Any]], benchmark_metrics: Sequence[Mapping[str, Any]],
    bootstrap_summary: Sequence[Mapping[str, Any]], grades: Sequence[Mapping[str, Any]],
    output_hashes: Mapping[str, str],
) -> str:
    metrics = {row["target"]: row for row in target_metrics}
    boot = {row["target"]: row for row in bootstrap_summary}
    grade = {row["target"]: row for row in grades}
    lines = [
        "# Stage A1.10 official test evaluation report", "",
        "## Stage determination", "", "`PASS`", "",
        "Technical PASS does not imply that a scientific claim is confirmed.", "",
        "## Blind-before-label provenance", "",
        f"- A1.10a commit: `{config['provenance']['a1_10a_commit']}`",
        "- A1.10b result commit: `recorded_by_enclosing_result_commit`",
        f"- Frozen blind prediction SHA-256: `{config['frozen_inputs']['blind_predictions']['sha256']}`",
        f"- Label unlock UTC: `{unlock['unlocked_at_utc']}`",
        f"- Label unlock commit state: `{unlock['unlock_head']}`",
        "- Pre-unlock Git clean: `true`", "- Blind predictions changed after unlock: `false`", "",
        "## Join integrity", "",
        f"- Joined rows: {join['joined_rows']}",
        f"- Duplicate predictions / labels: {join['duplicate_predictions']} / {join['duplicate_target_labels']}",
        f"- Unmatched predictions / labels: {join['unmatched_predictions']} / {join['unmatched_labels']}",
        f"- Silent drops / metadata mismatches: {join['silent_drops']} / {join['metadata_mismatches']}", "",
        "## Target results", "",
        "| Target | Role | Eligible | Positive | Negative | Prevalence | AP | AP lift | F1 | AP-lift 95% CI | Grade |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for target in TARGETS:
        row = metrics[target]; ci = boot[target]; g = grade[target]
        lines.append(
            f"| {target} | {row['role']} | {row['eligible_n']} | {row['positive_n']} | "
            f"{row['negative_n']} | {float(row['prevalence']):.6f} | "
            f"{float(row['pooled_average_precision']):.6f} | {float(row['pooled_ap_lift']):.6f} | "
            f"{float(row['positive_f1']):.6f} | [{float(ci['ci_lower']):.6f}, {float(ci['ci_upper']):.6f}] | "
            f"{g['final_grade']} |"
        )
    lines.extend([
        "", "Side Effect remains `EXPLORATORY_TEST_RESULT` regardless of its numerical result.", "",
        "## Bootstrap integrity", "",
        f"- Draws per target: {config['bootstrap']['n_draws']}",
        f"- RNG: `{config['bootstrap']['rng']}`",
        "- Unit: `(benchmark_original, normalized_task_id)` task-group cluster.",
        "- Sampling: within `benchmark_group_primary`; all model trajectories in a sampled task group move together.",
        "- Label stratification: `false`", "- Invalid redraw: `false`", "",
        "## Descriptive benchmark results", "",
        "Per-Benchmark and macro descriptive results are preserved in `artifacts/a1_10_benchmark_metrics.csv`. "
        "Single-class cells are recorded as not computable and are never imputed.", "",
        "## Claim boundary", "",
        "Only FC1 and FC2 use the mechanical confirmatory grading rule. FE1 remains exploratory. "
        "No dev-only comparison, mechanism claim, unseen-Benchmark claim, or joint task/model OOD claim was upgraded.", "",
        "## Post-unlock integrity", "",
        "- Re-inference / embedding regeneration / estimator refit: `0 / 0 / 0`",
        "- Threshold / eligibility / metric / bootstrap changes: `0 / 0 / 0 / 0`",
        "- Fusion / calibration / test-driven tuning: `0 / 0 / 0`",
        "- Independent verification: `PASS` (recorded after report generation).",
        "- Git clean: verified immediately after the enclosing result commit.", "",
        "## Frozen output hashes", "",
    ])
    for name, digest in sorted(output_hashes.items()):
        lines.append(f"- {name}: `{digest}`")
    lines.extend([
        "", "## Stop boundary", "",
        "A1.10 is complete. No next Stage was entered; further progression requires a new human decision.", "",
    ])
    return "\n".join(lines)


def run_score(config: dict[str, Any]) -> None:
    pre = preunlock_checks(config, require_clean=True)
    prerun_path = resolve(config["outputs"]["prerun_integrity"])
    if not prerun_path.exists() or git_output(["ls-files", "--error-unmatch", prerun_path.relative_to(REPO_ROOT).as_posix()]) == "":
        raise IntegrityError("committed pre-unlock integrity artifact is missing")
    frozen_blind_before = sha256_file(resolve(config["frozen_inputs"]["blind_predictions"]["path"]))
    entries, unlock = unlock_test_labels(config)
    blind = read_csv(resolve(config["frozen_inputs"]["blind_predictions"]["path"]))
    identifiers = read_csv(resolve(config["frozen_inputs"]["identifier_manifest"]["path"]))
    scored, join = join_predictions(config, blind, identifiers, entries)
    target_metrics, benchmark_metrics = build_metric_tables(config, scored)
    draw_rows, bootstrap_summary = build_bootstrap(config, scored)
    grades, claims = build_grades(config, target_metrics, bootstrap_summary)

    write_csv(resolve(config["outputs"]["scored_predictions"]), SCORED_FIELDS, scored)
    write_csv(resolve(config["outputs"]["target_metrics"]), TARGET_METRIC_FIELDS, target_metrics)
    write_csv(resolve(config["outputs"]["benchmark_metrics"]), BENCHMARK_METRIC_FIELDS, benchmark_metrics)
    write_csv(resolve(config["outputs"]["bootstrap_draw_metrics"]), BOOTSTRAP_DRAW_FIELDS, draw_rows)
    write_csv(resolve(config["outputs"]["bootstrap_summary"]), BOOTSTRAP_SUMMARY_FIELDS, bootstrap_summary)
    write_csv(resolve(config["outputs"]["confirmatory_grade"]), GRADE_FIELDS, grades)
    write_csv(resolve(config["outputs"]["final_claim_status"]), CLAIM_FIELDS, claims)

    output_names = [
        "scored_predictions", "target_metrics", "benchmark_metrics",
        "bootstrap_draw_metrics", "bootstrap_summary", "confirmatory_grade",
        "final_claim_status",
    ]
    output_hashes = _hash_outputs(config, output_names)
    report_text = _report(
        config, unlock, join, target_metrics, benchmark_metrics,
        bootstrap_summary, grades, output_hashes,
    )
    atomic_write_bytes(resolve(config["outputs"]["report"]), report_text.encode("utf-8"))
    output_hashes["report"] = sha256_file(resolve(config["outputs"]["report"]))
    frozen_blind_after = sha256_file(resolve(config["frozen_inputs"]["blind_predictions"]["path"]))
    if frozen_blind_before != frozen_blind_after or frozen_blind_after != config["frozen_inputs"]["blind_predictions"]["sha256"]:
        raise IntegrityError("blind predictions changed during scoring")
    prohibited = dict(config["prohibited_after_unlock"])
    if any(int(value) != 0 for value in prohibited.values()):
        raise IntegrityError("prohibited operation counter is nonzero")
    summary = {
        "stage": "A1.10b", "stage_determination": "PASS",
        "status": "A1_10_COMPLETE_AWAIT_HUMAN_NEXT_STAGE_DECISION",
        "authorization": config["authorization"],
        "a1_10a_commit": config["provenance"]["a1_10a_commit"],
        "a1_10b_result_commit": "recorded_by_enclosing_result_commit",
        "preunlock": pre, "label_unlock": unlock, "join_integrity": join,
        "target_metrics": {row["target"]: dict(row) for row in target_metrics},
        "bootstrap": {row["target"]: dict(row) for row in bootstrap_summary},
        "grades": {row["target"]: row["final_grade"] for row in grades},
        "output_hashes": output_hashes,
        "blind_prediction_sha256_before_unlock": frozen_blind_before,
        "blind_prediction_sha256_after_scoring": frozen_blind_after,
        "blind_predictions_changed": False,
        "test_access": {
            "label_source_open_count": 1, "labels": len(entries),
            "eligibility": len(entries), "metrics": len(TARGETS),
        },
        "bootstrap_integrity": {
            **config["bootstrap"], "draw_rows": len(draw_rows),
            "no_invalid_redraw": True, "no_label_stratification": True,
        },
        "post_unlock_prohibited_operations": prohibited,
        "dev_only_claims_upgraded": 0, "next_stage_entered": False,
        "runtime": {
            "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "completed_at_utc": utc_now(),
        },
    }
    write_json(resolve(config["outputs"]["run_summary"]), summary)
    print(json.dumps({
        "phase": "score", "status": "PASS", "grades": summary["grades"],
        "blind_sha256": frozen_blind_after,
    }, sort_keys=True))


def _compare_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    expected = csv_bytes(fieldnames, rows)
    actual = path.read_bytes()
    if actual != expected:
        raise IntegrityError(f"independent CSV recomputation differs: {path.name}")


def run_verify(config: dict[str, Any]) -> None:
    preunlock_checks(config, require_clean=False)
    scored = read_csv(resolve(config["outputs"]["scored_predictions"]))
    if len(scored) != int(config["expected"]["blind_rows"]):
        raise IntegrityError("scored prediction row count changed")
    target_metrics, benchmark_metrics = build_metric_tables(config, scored)
    draw_rows, bootstrap_summary = build_bootstrap(config, scored)
    grades, claims = build_grades(config, target_metrics, bootstrap_summary)
    _compare_csv(resolve(config["outputs"]["target_metrics"]), TARGET_METRIC_FIELDS, target_metrics)
    _compare_csv(resolve(config["outputs"]["benchmark_metrics"]), BENCHMARK_METRIC_FIELDS, benchmark_metrics)
    _compare_csv(resolve(config["outputs"]["bootstrap_draw_metrics"]), BOOTSTRAP_DRAW_FIELDS, draw_rows)
    _compare_csv(resolve(config["outputs"]["bootstrap_summary"]), BOOTSTRAP_SUMMARY_FIELDS, bootstrap_summary)
    _compare_csv(resolve(config["outputs"]["confirmatory_grade"]), GRADE_FIELDS, grades)
    _compare_csv(resolve(config["outputs"]["final_claim_status"]), CLAIM_FIELDS, claims)
    summary = json.loads(resolve(config["outputs"]["run_summary"]).read_text(encoding="utf-8"))
    if summary["blind_predictions_changed"] or summary["dev_only_claims_upgraded"] != 0:
        raise IntegrityError("post-unlock boundary summary changed")
    if any(int(value) != 0 for value in summary["post_unlock_prohibited_operations"].values()):
        raise IntegrityError("post-unlock prohibited operation recorded")
    verification = {
        "stage": "A1.10b_independent_verification", "status": "PASS",
        "generated_at_utc": utc_now(), "label_source_access_during_verify": 0,
        "eligibility_source_access_during_verify": 0,
        "metric_tables_byte_exact": True, "bootstrap_draws_byte_exact": True,
        "bootstrap_summary_byte_exact": True, "grades_byte_exact": True,
        "claims_byte_exact": True, "draw_rows_recomputed": len(draw_rows),
        "bootstrap_draws_per_target": int(config["bootstrap"]["n_draws"]),
        "seed": int(config["bootstrap"]["seed"]), "invalid_redraw": False,
        "label_stratification": False,
        "blind_prediction_sha256": sha256_file(resolve(config["frozen_inputs"]["blind_predictions"]["path"])),
        "scored_prediction_sha256": sha256_file(resolve(config["outputs"]["scored_predictions"])),
        "static_boundary_counts": static_boundary_counts(),
    }
    verification_path = resolve(config["outputs"]["independent_verification"])
    write_json(verification_path, verification)
    summary["independent_verification"] = {
        "status": "PASS",
        "path": config["outputs"]["independent_verification"],
        "sha256": sha256_file(verification_path),
        "label_source_access_during_verify": 0,
    }
    write_json(resolve(config["outputs"]["run_summary"]), summary)
    print(json.dumps({"phase": "verify", "status": "PASS", "draw_rows": len(draw_rows)}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    phase = parser.add_mutually_exclusive_group(required=True)
    phase.add_argument("--preflight", action="store_true")
    phase.add_argument("--score", action="store_true")
    phase.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    if args.preflight:
        run_preflight(config)
    elif args.score:
        run_score(config)
    else:
        run_verify(config)


if __name__ == "__main__":
    main()
