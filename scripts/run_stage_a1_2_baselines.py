#!/usr/bin/env python3
"""Run the preregistered Stage A1.2 grouped minimal dev baselines.

The module has three deliberately separate modes:

* ``--write-prerun`` performs read-only integrity checks and writes the
  environment/preregistration evidence.  It never fits an estimator.
* ``--run`` requires a clean preregistration commit and performs the one
  authorized real-dev run.
* ``--verify-results`` recomputes integrity and result invariants without
  fitting any estimator.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import logging
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import yaml
from sklearn.dummy import DummyClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
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
from sklearn.preprocessing import StandardScaler


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_2_execution.yaml"
FEATURE_NAMES = [
    "step_count",
    "nonempty_action_count",
    "nonempty_observation_count",
    "nonempty_focused_element_count",
    "natural_error_step_count",
    "natural_error_step_ratio",
    "has_explicit_termination_signal",
    "action_char_count_total",
    "observation_char_count_total",
    "action_char_count_mean_nonempty",
    "observation_char_count_mean_nonempty",
    "unique_action_ratio",
    "consecutive_duplicate_action_count",
]
METRIC_NAMES = [
    "pr_auc_average_precision",
    "positive_f1",
    "roc_auc",
    "precision",
    "recall",
    "f2",
    "balanced_accuracy",
    "mcc",
]
BASELINE_IDS = ["B0", "B1", "B2", "B3"]
TARGETS = ["success", "side_effect", "looping"]
FORMAL_OUTPUT_KEYS = [
    "structural_features",
    "inner_config_selection",
    "threshold_selection",
    "oof_predictions",
    "fold_metrics",
    "pooled_metrics",
    "config_frequency",
    "run_summary",
    "report",
]


class IntegrityError(RuntimeError):
    """Raised when a frozen scientific invariant is violated."""


def utc_now() -> str:
    """Return a second-resolution UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_path(path: Path) -> str:
    """Compute the SHA-256 digest of a file without changing it."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_content_sha256(record: dict[str, Any]) -> str:
    """Hash a JSON record using a deterministic label-independent encoding."""

    payload = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Atomically write UTF-8 text within the repository."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    """Write a deterministic, human-readable JSON artifact."""

    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    """Write a CSV artifact atomically with a fixed column order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and validate the frozen execution configuration."""

    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config["stage"] != "A1.2":
        raise IntegrityError("execution config stage is not A1.2")
    if [item["id"] for item in config["baselines"]] != BASELINE_IDS:
        raise IntegrityError("baseline list is not exactly B0-B3 in frozen order")
    if list(config["targets"]) != TARGETS:
        raise IntegrityError("target list/order differs from the frozen contract")
    if config["structural_features"] != FEATURE_NAMES:
        raise IntegrityError("the structural feature list/order is not the frozen 13")
    if config["execution"]["test_access"] is not False:
        raise IntegrityError("test access must be false")
    if config["execution"]["input_view"] != "primary_with_natural_errors":
        raise IntegrityError("the formal input view is not primary_with_natural_errors")
    thresholds = [round(float(value), 2) for value in config["selection"]["thresholds"]]
    if thresholds != [round(value / 100, 2) for value in range(5, 100, 5)]:
        raise IntegrityError("threshold candidates differ from 0.05..0.95")
    if set(config["tfidf"]) != {"T1", "T2", "common"}:
        raise IntegrityError("TF-IDF variants are not exactly T1 and T2")
    if config["tfidf"]["T1"]["ngram_range"] != [1, 1]:
        raise IntegrityError("T1 is not word unigram")
    if config["tfidf"]["T2"]["ngram_range"] != [1, 2]:
        raise IntegrityError("T2 is not word unigram+bigram")
    forbidden = set(config["execution"]["forbidden_experiments"])
    required_forbidden = {
        "test_evaluation",
        "lobo",
        "leave_one_model_out",
        "reasoning_sensitivity",
        "error_ablation",
        "embedding",
        "mlp",
        "xgboost",
        "transformer",
        "llm_judge",
        "char_ngram",
    }
    if not required_forbidden.issubset(forbidden):
        raise IntegrityError("one or more prohibited experiment paths are not frozen")
    return config


def resolve(path_text: str) -> Path:
    """Resolve a repository-relative configured path."""

    path = (REPO_ROOT / path_text).resolve()
    if REPO_ROOT not in path.parents and path != REPO_ROOT:
        raise IntegrityError(f"configured path escapes repository: {path_text}")
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV file into dictionaries."""

    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    """Read unique trajectory-keyed JSONL records."""

    records: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            key = record.get("trajectory_key")
            if not isinstance(key, str) or not key:
                raise IntegrityError(f"missing trajectory_key at {path}:{line_number}")
            if key in records:
                raise IntegrityError(f"duplicate trajectory_key in {path}: {key}")
            records[key] = record
    return records


def is_true(value: str) -> bool:
    """Parse the fixed CSV boolean spelling."""

    return value.strip().lower() == "true"


def verify_frozen_hashes(config: dict[str, Any]) -> dict[str, str]:
    """Verify all inputs, labels, test identifiers, and ordinary manifests."""

    specifications: list[dict[str, Any]] = list(config["inputs"].values())
    specifications.extend(config["manifests"].values())
    verified: dict[str, str] = {}
    for specification in specifications:
        path = resolve(specification["path"])
        if not path.is_file():
            raise IntegrityError(f"required frozen file is missing: {path}")
        actual = sha256_path(path)
        expected = specification["sha256"]
        if actual != expected:
            raise IntegrityError(
                f"SHA-256 mismatch for {specification['path']}: {actual} != {expected}"
            )
        verified[specification["path"]] = actual
    return verified


def load_label_index(config: dict[str, Any]) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, int]]]:
    """Load eligible dev labels independently for each target."""

    rows = read_csv(resolve(config["inputs"]["label_index"]["path"]))
    by_key: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row["trajectory_key"]
        if key in by_key:
            raise IntegrityError(f"duplicate label-index trajectory_key: {key}")
        by_key[key] = row
    labels: dict[str, dict[str, int]] = {}
    for target, target_config in config["targets"].items():
        eligible: dict[str, int] = {}
        for key, row in by_key.items():
            if is_true(row[target_config["eligibility_column"]]):
                raw_label = row[target_config["label_column"]]
                if raw_label not in {"0", "1"}:
                    raise IntegrityError(f"eligible non-binary {target} label for {key}")
                if row.get("official_split") != "dev":
                    raise IntegrityError(f"eligible {target} sample is not dev: {key}")
                eligible[key] = int(raw_label)
        positives = sum(eligible.values())
        negatives = len(eligible) - positives
        expected = target_config
        if (len(eligible), positives, negatives) != (
            expected["expected_samples"],
            expected["expected_positive"],
            expected["expected_negative"],
        ):
            raise IntegrityError(
                f"{target} counts differ: {(len(eligible), positives, negatives)}"
            )
        labels[target] = eligible
    return by_key, labels


def validate_manifests(
    config: dict[str, Any], labels: dict[str, dict[str, int]], test_keys: set[str]
) -> dict[str, dict[int, list[dict[str, str]]]]:
    """Validate immutable outer/inner membership and group isolation."""

    manifests: dict[str, dict[int, list[dict[str, str]]]] = {}
    for target in TARGETS:
        rows = read_csv(resolve(config["manifests"][target]["path"]))
        eligible_keys = set(labels[target])
        if len(rows) != len(eligible_keys) * 5:
            raise IntegrityError(f"{target} manifest does not contain five rows per sample")
        by_fold: dict[int, list[dict[str, str]]] = defaultdict(list)
        outer_validation_counts: Counter[str] = Counter()
        appearances: Counter[str] = Counter()
        for row in rows:
            key = row["trajectory_key"]
            fold = int(row["outer_fold"])
            if row["target"] != target or row["official_split"] != "dev":
                raise IntegrityError(f"invalid target/split in {target} manifest")
            if key not in eligible_keys or key in test_keys:
                raise IntegrityError(f"invalid/test key in {target} manifest: {key}")
            if int(row["label"]) != labels[target][key]:
                raise IntegrityError(f"manifest/index label mismatch for {target}:{key}")
            appearances[key] += 1
            if row["outer_role"] == "outer_validation":
                outer_validation_counts[key] += 1
                if row["inner_split"] != "not_applicable":
                    raise IntegrityError("outer validation entered an inner split")
            elif row["outer_role"] == "outer_train":
                if row["inner_split"] not in {"inner_train", "inner_validation"}:
                    raise IntegrityError("outer training row lacks a frozen inner role")
            else:
                raise IntegrityError("unknown outer role")
            by_fold[fold].append(row)
        if set(by_fold) != {1, 2, 3, 4, 5}:
            raise IntegrityError(f"{target} outer folds are not exactly 1..5")
        if set(appearances.values()) != {5} or set(outer_validation_counts.values()) != {1}:
            raise IntegrityError(f"{target} OOF membership is not exactly once")
        for fold, fold_rows in by_fold.items():
            if {row["trajectory_key"] for row in fold_rows} != eligible_keys:
                raise IntegrityError(f"{target} fold {fold} does not cover all eligible keys")
            outer_train_groups = {
                row["group_key"] for row in fold_rows if row["outer_role"] == "outer_train"
            }
            outer_validation_groups = {
                row["group_key"]
                for row in fold_rows
                if row["outer_role"] == "outer_validation"
            }
            if outer_train_groups & outer_validation_groups:
                raise IntegrityError(f"outer group leakage in {target} fold {fold}")
            inner_train_groups = {
                row["group_key"] for row in fold_rows if row["inner_split"] == "inner_train"
            }
            inner_validation_groups = {
                row["group_key"]
                for row in fold_rows
                if row["inner_split"] == "inner_validation"
            }
            if inner_train_groups & inner_validation_groups:
                raise IntegrityError(f"inner group leakage in {target} fold {fold}")
        manifests[target] = dict(by_fold)
    return manifests


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Perform every real-data integrity check without fitting a model."""

    verified_hashes = verify_frozen_hashes(config)
    cleaned = read_jsonl(resolve(config["inputs"]["cleaned"]["path"]))
    primary = read_jsonl(resolve(config["inputs"]["primary"]["path"]))
    if len(cleaned) != 196 or set(cleaned) != set(primary):
        raise IntegrityError("cleaned/primary inputs do not contain the same 196 dev keys")
    for key, record in primary.items():
        if set(record) != {"trajectory_key", "input_view", "serialized_text", "content_sha256"}:
            raise IntegrityError(f"unexpected primary input schema for {key}")
        if record["input_view"] != "primary_with_natural_errors":
            raise IntegrityError(f"non-primary input view for {key}")
        if not isinstance(record["serialized_text"], str):
            raise IntegrityError(f"non-text primary serialization for {key}")
    _, labels = load_label_index(config)
    test_rows = read_csv(resolve(config["inputs"]["sealed_test_manifest"]["path"]))
    test_keys = {row["trajectory_key"] for row in test_rows}
    if set(cleaned) & test_keys:
        raise IntegrityError("dev corpus overlaps the sealed identifier-only test manifest")
    manifests = validate_manifests(config, labels, test_keys)
    return {
        "verified_hashes": verified_hashes,
        "cleaned": cleaned,
        "primary": primary,
        "labels": labels,
        "manifests": manifests,
        "test_identifier_count": len(test_keys),
    }


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_action(value: str) -> str:
    return " ".join(value.strip().split())


def extract_structural_features(record: dict[str, Any]) -> dict[str, float | int]:
    """Extract only the 13 preregistered label/identity-independent features."""

    steps = record.get("steps")
    if not isinstance(steps, list):
        raise IntegrityError("cleaned trajectory steps must be a list")
    actions = [step.get("action") for step in steps]
    observations = [step.get("observation") for step in steps]
    focused = [step.get("focused_element") for step in steps]
    errors = [step.get("error") for step in steps]
    nonempty_actions = [value for value in actions if _nonempty_text(value)]
    nonempty_observations = [value for value in observations if _nonempty_text(value)]
    normalized_actions = [_normalize_action(value) for value in nonempty_actions]
    step_count = len(steps)
    natural_error_count = sum(_nonempty_text(value) for value in errors)
    action_total = sum(len(value) for value in nonempty_actions)
    observation_total = sum(len(value) for value in nonempty_observations)
    termination_signal = (record.get("terminal") or {}).get("termination_signal")
    if termination_signal not in {None, "send_msg_to_user", "report_infeasible"}:
        raise IntegrityError("unapproved explicit termination signal")
    return {
        "step_count": step_count,
        "nonempty_action_count": len(nonempty_actions),
        "nonempty_observation_count": len(nonempty_observations),
        "nonempty_focused_element_count": sum(_nonempty_text(value) for value in focused),
        "natural_error_step_count": natural_error_count,
        "natural_error_step_ratio": natural_error_count / step_count if step_count else 0.0,
        "has_explicit_termination_signal": int(termination_signal is not None),
        "action_char_count_total": action_total,
        "observation_char_count_total": observation_total,
        "action_char_count_mean_nonempty": (
            action_total / len(nonempty_actions) if nonempty_actions else 0.0
        ),
        "observation_char_count_mean_nonempty": (
            observation_total / len(nonempty_observations) if nonempty_observations else 0.0
        ),
        "unique_action_ratio": (
            len(set(normalized_actions)) / len(normalized_actions)
            if normalized_actions
            else 0.0
        ),
        "consecutive_duplicate_action_count": sum(
            left == right
            for left, right in zip(normalized_actions, normalized_actions[1:], strict=False)
        ),
    }


def structural_rows(cleaned: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the label-free structural artifact before any target join."""

    rows: list[dict[str, Any]] = []
    for key in sorted(cleaned):
        record = cleaned[key]
        row: dict[str, Any] = {"trajectory_key": key}
        row.update(extract_structural_features(record))
        row["content_sha256"] = canonical_content_sha256(record)
        rows.append(row)
    return rows


def _c_id(value: float) -> str:
    return str(value).replace(".", "p")


def candidate_configs(config: dict[str, Any], baseline_id: str) -> list[dict[str, Any]]:
    """Return candidates in the exact preregistered tie-break order."""

    if baseline_id == "B0":
        return [{"config_id": "B0_most_frequent", "strategy": "most_frequent"}]
    if baseline_id == "B1":
        return [{"config_id": "B1_prior", "strategy": "prior"}]
    c_values = [0.1, 1.0, 10.0]
    weights: list[str | None] = [None, "balanced"]
    candidates: list[dict[str, Any]] = []
    if baseline_id == "B2":
        for weight in weights:
            for c_value in c_values:
                weight_id = "none" if weight is None else "balanced"
                candidates.append(
                    {
                        "config_id": f"B2_C{_c_id(c_value)}_cw_{weight_id}",
                        "C": c_value,
                        "class_weight": weight,
                    }
                )
        return candidates
    if baseline_id == "B3":
        for variant in ["T1", "T2"]:
            for weight in weights:
                for c_value in c_values:
                    weight_id = "none" if weight is None else "balanced"
                    candidates.append(
                        {
                            "config_id": f"B3_{variant}_C{_c_id(c_value)}_cw_{weight_id}",
                            "tfidf": variant,
                            "C": c_value,
                            "class_weight": weight,
                        }
                    )
        return candidates
    raise IntegrityError(f"unknown baseline: {baseline_id}")


def make_tfidf(config: dict[str, Any], variant: str) -> TfidfVectorizer:
    """Construct exactly T1 or T2 from the frozen configuration."""

    common = config["tfidf"]["common"]
    return TfidfVectorizer(
        ngram_range=tuple(config["tfidf"][variant]["ngram_range"]),
        lowercase=common["lowercase"],
        strip_accents=common["strip_accents"],
        min_df=common["min_df"],
        max_df=common["max_df"],
        max_features=common["max_features"],
        sublinear_tf=common["sublinear_tf"],
        norm=common["norm"],
        use_idf=common["use_idf"],
        smooth_idf=common["smooth_idf"],
        token_pattern=common["token_pattern"],
        analyzer="word",
    )


def make_lr(config: dict[str, Any], candidate: dict[str, Any]) -> LogisticRegression:
    """Construct the frozen binary Logistic Regression estimator."""

    fixed = config["logistic_regression"]
    return LogisticRegression(
        C=candidate["C"],
        class_weight=candidate["class_weight"],
        penalty=fixed["penalty"],
        solver=fixed["solver"],
        max_iter=fixed["max_iter"],
        fit_intercept=fixed["fit_intercept"],
        random_state=fixed["random_state"],
    )


def positive_probability(model: Any, features: Any) -> np.ndarray:
    """Locate P(y=1) through ``classes_`` and validate the probabilities."""

    classes = np.asarray(model.classes_)
    indices = np.flatnonzero(classes == 1)
    if len(indices) != 1:
        raise IntegrityError(f"model classes do not contain exactly one positive class: {classes}")
    probabilities = np.asarray(model.predict_proba(features)[:, int(indices[0])], dtype=float)
    if not np.all(np.isfinite(probabilities)):
        raise IntegrityError("non-finite predicted probability")
    if np.any(probabilities < 0.0) or np.any(probabilities > 1.0):
        raise IntegrityError("predicted probability outside [0,1]")
    return probabilities


def metrics(y_true: Sequence[int], probabilities: Sequence[float], predicted: Sequence[int]) -> dict[str, float]:
    """Compute the frozen primary and auxiliary binary metrics."""

    truth = np.asarray(y_true, dtype=int)
    probability = np.asarray(probabilities, dtype=float)
    prediction = np.asarray(predicted, dtype=int)
    return {
        "pr_auc_average_precision": float(average_precision_score(truth, probability)),
        "positive_f1": float(f1_score(truth, prediction, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(truth, probability)),
        "precision": float(precision_score(truth, prediction, pos_label=1, zero_division=0)),
        "recall": float(recall_score(truth, prediction, pos_label=1, zero_division=0)),
        "f2": float(fbeta_score(truth, prediction, beta=2, pos_label=1, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, prediction)),
        "mcc": float(matthews_corrcoef(truth, prediction)),
    }


def select_threshold(
    config: dict[str, Any], y_true: Sequence[int], probabilities: Sequence[float]
) -> tuple[float, list[dict[str, Any]]]:
    """Select positive F1 threshold on inner validation with frozen tie-breaks."""

    rows: list[dict[str, Any]] = []
    truth = np.asarray(y_true, dtype=int)
    probability = np.asarray(probabilities, dtype=float)
    for threshold in config["selection"]["thresholds"]:
        prediction = (probability >= float(threshold)).astype(int)
        rows.append(
            {
                "threshold": float(threshold),
                "inner_f1": float(f1_score(truth, prediction, pos_label=1, zero_division=0)),
                "inner_precision": float(
                    precision_score(truth, prediction, pos_label=1, zero_division=0)
                ),
                "inner_recall": float(
                    recall_score(truth, prediction, pos_label=1, zero_division=0)
                ),
            }
        )
    selected = max(
        rows,
        key=lambda row: (
            row["inner_f1"],
            row["inner_recall"],
            -abs(row["threshold"] - 0.5),
            -row["threshold"],
        ),
    )
    for row in rows:
        row["selected"] = row is selected
    return selected["threshold"], rows


def _fit_with_warning_capture(
    estimator: Any,
    features: Any,
    labels: Sequence[int],
    warning_context: dict[str, Any],
    warning_records: list[dict[str, Any]],
) -> Any:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        estimator.fit(features, labels)
    for warning in caught:
        record = dict(warning_context)
        record.update(
            {
                "category": warning.category.__name__,
                "message": str(warning.message),
                "is_convergence_warning": issubclass(warning.category, ConvergenceWarning),
            }
        )
        warning_records.append(record)
    return estimator


def _matrix(feature_by_key: dict[str, dict[str, Any]], keys: Sequence[str]) -> np.ndarray:
    return np.asarray(
        [[float(feature_by_key[key][name]) for name in FEATURE_NAMES] for key in keys],
        dtype=float,
    )


def run_fold(
    config: dict[str, Any],
    target: str,
    baseline_id: str,
    outer_fold: int,
    fold_rows: Sequence[dict[str, str]],
    labels: dict[str, int],
    feature_by_key: dict[str, dict[str, Any]],
    primary: dict[str, dict[str, Any]],
    warning_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Execute one target/baseline/fold with inner-only selection and one outer score."""

    inner_train_keys = [r["trajectory_key"] for r in fold_rows if r["inner_split"] == "inner_train"]
    inner_validation_keys = [
        r["trajectory_key"] for r in fold_rows if r["inner_split"] == "inner_validation"
    ]
    outer_train_keys = [r["trajectory_key"] for r in fold_rows if r["outer_role"] == "outer_train"]
    outer_validation_rows = [r for r in fold_rows if r["outer_role"] == "outer_validation"]
    outer_validation_keys = [r["trajectory_key"] for r in outer_validation_rows]
    y_inner_train = [labels[key] for key in inner_train_keys]
    y_inner_validation = [labels[key] for key in inner_validation_keys]
    candidates = candidate_configs(config, baseline_id)
    candidate_probabilities: dict[str, np.ndarray] = {}
    candidate_rows: list[dict[str, Any]] = []

    if baseline_id in {"B0", "B1"}:
        candidate = candidates[0]
        model = DummyClassifier(strategy=candidate["strategy"])
        model = _fit_with_warning_capture(
            model,
            np.zeros((len(inner_train_keys), 1)),
            y_inner_train,
            {"target": target, "baseline_id": baseline_id, "outer_fold": outer_fold,
             "config_id": candidate["config_id"], "phase": "inner_candidate"},
            warning_records,
        )
        candidate_probabilities[candidate["config_id"]] = positive_probability(
            model, np.zeros((len(inner_validation_keys), 1))
        )
    elif baseline_id == "B2":
        inner_scaler = StandardScaler().fit(_matrix(feature_by_key, inner_train_keys))
        x_inner_train = inner_scaler.transform(_matrix(feature_by_key, inner_train_keys))
        x_inner_validation = inner_scaler.transform(_matrix(feature_by_key, inner_validation_keys))
        for candidate in candidates:
            model = make_lr(config, candidate)
            model = _fit_with_warning_capture(
                model,
                x_inner_train,
                y_inner_train,
                {"target": target, "baseline_id": baseline_id, "outer_fold": outer_fold,
                 "config_id": candidate["config_id"], "phase": "inner_candidate"},
                warning_records,
            )
            candidate_probabilities[candidate["config_id"]] = positive_probability(
                model, x_inner_validation
            )
    elif baseline_id == "B3":
        train_text = [primary[key]["serialized_text"] for key in inner_train_keys]
        validation_text = [primary[key]["serialized_text"] for key in inner_validation_keys]
        for variant in ["T1", "T2"]:
            vectorizer = make_tfidf(config, variant)
            x_inner_train = vectorizer.fit_transform(train_text)
            x_inner_validation = vectorizer.transform(validation_text)
            for candidate in [item for item in candidates if item["tfidf"] == variant]:
                model = make_lr(config, candidate)
                model = _fit_with_warning_capture(
                    model,
                    x_inner_train,
                    y_inner_train,
                    {"target": target, "baseline_id": baseline_id, "outer_fold": outer_fold,
                     "config_id": candidate["config_id"], "phase": "inner_candidate"},
                    warning_records,
                )
                candidate_probabilities[candidate["config_id"]] = positive_probability(
                    model, x_inner_validation
                )
    else:
        raise IntegrityError(f"unknown baseline {baseline_id}")

    best_ap = max(
        float(average_precision_score(y_inner_validation, probabilities))
        for probabilities in candidate_probabilities.values()
    )
    selected_candidate = next(
        candidate
        for candidate in candidates
        if float(
            average_precision_score(
                y_inner_validation, candidate_probabilities[candidate["config_id"]]
            )
        )
        == best_ap
    )
    for rank, candidate in enumerate(candidates, start=1):
        candidate_id = candidate["config_id"]
        candidate_rows.append(
            {
                "target": target,
                "baseline_id": baseline_id,
                "outer_fold": outer_fold,
                "config_id": candidate_id,
                "inner_train_size": len(inner_train_keys),
                "inner_validation_size": len(inner_validation_keys),
                "inner_pr_auc": float(
                    average_precision_score(
                        y_inner_validation, candidate_probabilities[candidate_id]
                    )
                ),
                "selected": candidate_id == selected_candidate["config_id"],
                "tie_break_rank": rank,
            }
        )
    selected_inner_probability = candidate_probabilities[selected_candidate["config_id"]]
    threshold, threshold_rows = select_threshold(
        config, y_inner_validation, selected_inner_probability
    )
    for row in threshold_rows:
        row.update(
            {
                "target": target,
                "baseline_id": baseline_id,
                "outer_fold": outer_fold,
                "config_id": selected_candidate["config_id"],
            }
        )

    y_outer_train = [labels[key] for key in outer_train_keys]
    if baseline_id in {"B0", "B1"}:
        outer_model = DummyClassifier(strategy=selected_candidate["strategy"])
        outer_model = _fit_with_warning_capture(
            outer_model,
            np.zeros((len(outer_train_keys), 1)),
            y_outer_train,
            {"target": target, "baseline_id": baseline_id, "outer_fold": outer_fold,
             "config_id": selected_candidate["config_id"], "phase": "outer_refit"},
            warning_records,
        )
        outer_probability = positive_probability(
            outer_model, np.zeros((len(outer_validation_keys), 1))
        )
    elif baseline_id == "B2":
        outer_scaler = StandardScaler().fit(_matrix(feature_by_key, outer_train_keys))
        x_outer_train = outer_scaler.transform(_matrix(feature_by_key, outer_train_keys))
        x_outer_validation = outer_scaler.transform(
            _matrix(feature_by_key, outer_validation_keys)
        )
        outer_model = _fit_with_warning_capture(
            make_lr(config, selected_candidate),
            x_outer_train,
            y_outer_train,
            {"target": target, "baseline_id": baseline_id, "outer_fold": outer_fold,
             "config_id": selected_candidate["config_id"], "phase": "outer_refit"},
            warning_records,
        )
        outer_probability = positive_probability(outer_model, x_outer_validation)
    else:
        vectorizer = make_tfidf(config, selected_candidate["tfidf"])
        x_outer_train = vectorizer.fit_transform(
            [primary[key]["serialized_text"] for key in outer_train_keys]
        )
        x_outer_validation = vectorizer.transform(
            [primary[key]["serialized_text"] for key in outer_validation_keys]
        )
        outer_model = _fit_with_warning_capture(
            make_lr(config, selected_candidate),
            x_outer_train,
            y_outer_train,
            {"target": target, "baseline_id": baseline_id, "outer_fold": outer_fold,
             "config_id": selected_candidate["config_id"], "phase": "outer_refit"},
            warning_records,
        )
        outer_probability = positive_probability(outer_model, x_outer_validation)

    y_outer = [labels[key] for key in outer_validation_keys]
    predicted = (outer_probability >= threshold).astype(int)
    metric_values = metrics(y_outer, outer_probability, predicted)
    fold_metric: dict[str, Any] = {
        "target": target,
        "baseline_id": baseline_id,
        "outer_fold": outer_fold,
        "sample_count": len(y_outer),
        "positive_count": sum(y_outer),
        "negative_count": len(y_outer) - sum(y_outer),
        "prevalence": sum(y_outer) / len(y_outer),
        "predicted_positive_count": int(predicted.sum()),
        "selected_config_id": selected_candidate["config_id"],
        "selected_threshold": threshold,
    }
    fold_metric.update(metric_values)
    prediction_rows: list[dict[str, Any]] = []
    for manifest_row, truth, probability, prediction in zip(
        outer_validation_rows, y_outer, outer_probability, predicted, strict=True
    ):
        prediction_rows.append(
            {
                "trajectory_key": manifest_row["trajectory_key"],
                "group_key": manifest_row["group_key"],
                "target": target,
                "baseline_id": baseline_id,
                "outer_fold": outer_fold,
                "true_label": truth,
                "predicted_probability": float(probability),
                "selected_threshold": threshold,
                "predicted_label": int(prediction),
                "selected_config_id": selected_candidate["config_id"],
            }
        )
    return prediction_rows, fold_metric, candidate_rows, threshold_rows


def aggregate_results(
    config: dict[str, Any],
    predictions: list[dict[str, Any]],
    fold_metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute fold mean±sample-std and pooled OOF metrics."""

    pooled_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        expected = config["targets"][target]["expected_samples"]
        for baseline_id in BASELINE_IDS:
            selected = [
                row
                for row in predictions
                if row["target"] == target and row["baseline_id"] == baseline_id
            ]
            if len(selected) != expected:
                raise IntegrityError(f"OOF count mismatch for {target}/{baseline_id}")
            keys = [row["trajectory_key"] for row in selected]
            if len(keys) != len(set(keys)):
                raise IntegrityError(f"duplicate OOF key for {target}/{baseline_id}")
            pooled_metric = metrics(
                [row["true_label"] for row in selected],
                [row["predicted_probability"] for row in selected],
                [row["predicted_label"] for row in selected],
            )
            target_folds = sorted(
                [
                    row
                    for row in fold_metrics
                    if row["target"] == target and row["baseline_id"] == baseline_id
                ],
                key=lambda row: row["outer_fold"],
            )
            if len(target_folds) != 5:
                raise IntegrityError(f"missing fold metrics for {target}/{baseline_id}")
            positive_count = sum(row["true_label"] for row in selected)
            output: dict[str, Any] = {
                "target": target,
                "baseline_id": baseline_id,
                "sample_count": len(selected),
                "positive_count": positive_count,
                "negative_count": len(selected) - positive_count,
                "prevalence": positive_count / len(selected),
                "predicted_positive_count": sum(row["predicted_label"] for row in selected),
            }
            for name in METRIC_NAMES:
                values = [float(row[name]) for row in target_folds]
                output[f"pooled_{name}"] = pooled_metric[name]
                output[f"fold_mean_{name}"] = statistics.mean(values)
                output[f"fold_std_{name}"] = statistics.stdev(values)
            output["ap_absolute_lift"] = (
                output["pooled_pr_auc_average_precision"] - output["prevalence"]
            )
            pooled_rows.append(output)
    return pooled_rows


def config_frequencies(
    config: dict[str, Any], selections: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Count selected configurations while retaining zero-frequency candidates."""

    rows: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline_id in BASELINE_IDS:
            selected_counts = Counter(
                row["config_id"]
                for row in selections
                if row["target"] == target
                and row["baseline_id"] == baseline_id
                and row["selected"]
            )
            for rank, candidate in enumerate(candidate_configs(config, baseline_id), start=1):
                rows.append(
                    {
                        "target": target,
                        "baseline_id": baseline_id,
                        "config_id": candidate["config_id"],
                        "tie_break_rank": rank,
                        "selected_count": selected_counts[candidate["config_id"]],
                    }
                )
    return rows


def signal_grades(
    pooled: list[dict[str, Any]], fold_rows: list[dict[str, Any]], anomalies: list[str]
) -> dict[str, str]:
    """Apply the preregistered descriptive signal grading rule."""

    grades: dict[str, str] = {}
    pooled_map = {(r["target"], r["baseline_id"]): r for r in pooled}
    fold_map = {(r["target"], r["baseline_id"], int(r["outer_fold"])): r for r in fold_rows}
    for target in TARGETS:
        dummy_f1 = max(
            pooled_map[(target, "B0")]["pooled_positive_f1"],
            pooled_map[(target, "B1")]["pooled_positive_f1"],
        )
        learned_status: list[tuple[bool, bool]] = []
        clear = False
        for baseline_id in ["B2", "B3"]:
            row = pooled_map[(target, baseline_id)]
            ap_better = row["pooled_pr_auc_average_precision"] > row["prevalence"]
            f1_better = row["pooled_positive_f1"] > dummy_f1
            improved_folds = 0
            for fold in range(1, 6):
                learned = fold_map[(target, baseline_id, fold)]
                fold_dummy_f1 = max(
                    fold_map[(target, "B0", fold)]["positive_f1"],
                    fold_map[(target, "B1", fold)]["positive_f1"],
                )
                if (
                    learned["pr_auc_average_precision"] > learned["prevalence"]
                    and learned["positive_f1"] > fold_dummy_f1
                ):
                    improved_folds += 1
            learned_status.append((ap_better, f1_better))
            if ap_better and f1_better and improved_folds >= 2 and not anomalies:
                clear = True
        if clear:
            grades[target] = "clear_provisional_signal"
        elif all(not ap and not f1 for ap, f1 in learned_status):
            grades[target] = "no_obvious_signal"
        else:
            grades[target] = "weak_or_mixed_signal"
    return grades


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def build_report(
    config: dict[str, Any],
    environment: dict[str, Any],
    verified_hashes: dict[str, str],
    fold_rows: list[dict[str, Any]],
    pooled_rows: list[dict[str, Any]],
    config_rows: list[dict[str, Any]],
    threshold_rows: list[dict[str, Any]],
    warning_records: list[dict[str, Any]],
    signal: dict[str, str],
    stage_decision: str,
    conditions: list[str],
    run_metadata: dict[str, Any],
) -> str:
    """Render the complete formal Stage A1.2 report."""

    lines = [
        "# Stage A1.2 Minimal Task-Grouped Dev Baselines",
        "",
        "## Stage determination",
        "",
        f"**{stage_decision}**",
        "",
        "This is a dev-only evidence recommendation. Human stage-gate review is required.",
        "",
    ]
    if conditions:
        lines.extend(["Conditions:", ""] + [f"- {item}" for item in conditions] + [""])
    lines.extend(
        [
            "## Environment and frozen scope",
            "",
            f"- Run ID: `{run_metadata['run_id']}`",
            f"- Preregistration commit: `{run_metadata['git_commit']}`",
            f"- Python: `{environment['python']['version']}`",
            f"- OS: `{environment['platform']}`",
            f"- CPU logical count: `{environment['hardware']['logical_cpu_count']}`; GPU used: `false`",
            "- Dependencies: " + ", ".join(
                f"`{name}=={version}`" for name, version in environment["dependencies"].items()
            ),
            "- Formal-run network access: `0`",
            "- Input view: `primary_with_natural_errors` only",
            "- Baselines: B0 most-frequent Dummy; B1 prior Dummy; B2 frozen 13 structural features + scaled LR; B3 frozen TF-IDF + LR.",
            "",
            "## Frozen hashes",
            "",
            "| File | SHA-256 |",
            "|---|---|",
        ]
    )
    for path, digest in verified_hashes.items():
        lines.append(f"| `{path}` | `{digest}` |")
    lines.extend(
        [
            "",
            "The post-run hashes matched the same values. The identifier-only sealed test manifest was read only for a dev/test key-overlap assertion; test trajectory content, labels, predictions, and metrics accessed: **0**.",
            "",
            "## Per-fold results",
            "",
            "PR-AUC is `sklearn.metrics.average_precision_score`. All F metrics use positive class 1.",
            "",
            "| Target | Baseline | Fold | N | Pos | Prev | Pred+ | Config | Thr | AP | F1 | ROC-AUC | Precision | Recall | F2 | BalAcc | MCC |",
            "|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(fold_rows, key=lambda r: (TARGETS.index(r["target"]), BASELINE_IDS.index(r["baseline_id"]), r["outer_fold"])):
        lines.append(
            "| {target} | {baseline_id} | {outer_fold} | {sample_count} | {positive_count} | {prevalence} | {predicted_positive_count} | `{selected_config_id}` | {selected_threshold} | {pr_auc_average_precision} | {positive_f1} | {roc_auc} | {precision} | {recall} | {f2} | {balanced_accuracy} | {mcc} |".format(
                **{key: _fmt(value) for key, value in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "## Fold mean ± sample standard deviation and pooled OOF",
            "",
            "| Target | Baseline | OOF N | Prev | AP mean±std | F1 mean±std | Pooled AP | Pooled F1 | Pooled ROC-AUC | Pooled Precision | Pooled Recall | Pooled F2 | Pooled BalAcc | Pooled MCC | AP lift |",
            "|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in pooled_rows:
        lines.append(
            f"| {row['target']} | {row['baseline_id']} | {row['sample_count']} | {_fmt(row['prevalence'])} | "
            f"{_fmt(row['fold_mean_pr_auc_average_precision'])} ± {_fmt(row['fold_std_pr_auc_average_precision'])} | "
            f"{_fmt(row['fold_mean_positive_f1'])} ± {_fmt(row['fold_std_positive_f1'])} | "
            f"{_fmt(row['pooled_pr_auc_average_precision'])} | {_fmt(row['pooled_positive_f1'])} | "
            f"{_fmt(row['pooled_roc_auc'])} | {_fmt(row['pooled_precision'])} | {_fmt(row['pooled_recall'])} | "
            f"{_fmt(row['pooled_f2'])} | {_fmt(row['pooled_balanced_accuracy'])} | {_fmt(row['pooled_mcc'])} | {_fmt(row['ap_absolute_lift'])} |"
        )
    lines.extend(["", "## Configuration and threshold selection", ""])
    selected_config = [row for row in config_rows if int(row["selected_count"]) > 0]
    lines.extend(["| Target | Baseline | Config | Selected folds |", "|---|---|---|---:|"])
    for row in selected_config:
        lines.append(
            f"| {row['target']} | {row['baseline_id']} | `{row['config_id']}` | {row['selected_count']} |"
        )
    lines.extend(["", "Selected threshold frequencies:", ""])
    threshold_counts = Counter(
        (row["target"], row["baseline_id"], float(row["threshold"]))
        for row in threshold_rows
        if row["selected"]
    )
    lines.extend(["| Target | Baseline | Threshold | Selected folds |", "|---|---|---:|---:|"])
    for (target, baseline, threshold), count in sorted(threshold_counts.items()):
        lines.append(f"| {target} | {baseline} | {_fmt(threshold)} | {count} |")
    convergence = [row for row in warning_records if row["is_convergence_warning"]]
    lines.extend(
        [
            "",
            "## Integrity, warnings, and boundaries",
            "",
            f"- Logistic Regression convergence warnings: `{len(convergence)}`.",
            "- OOF completeness: each eligible trajectory appears exactly once per target × baseline; expected counts 192/195/196 were met.",
            "- Outer validation probability evaluation count: `60` (3 targets × 4 baselines × 5 folds), exactly one per combination.",
            "- Configuration selection used inner-validation AP only; threshold selection used inner-validation positive F1 only.",
            "- TF-IDF and StandardScaler were fitted only on the corresponding inner-train or complete outer-train partition.",
            "- No test evaluation, LOBO, Leave-One-Model-Out, reasoning sensitivity, natural-error ablation, benchmark redaction, Embedding, MLP, XGBoost, Transformer, LoRA, screenshot model, or LLM Judge was run.",
            "- No confidence interval or significance test was run in this stage.",
            "",
            "## Descriptive evidence summary",
            "",
        ]
    )
    pooled_map = {(row["target"], row["baseline_id"]): row for row in pooled_rows}
    for target in TARGETS:
        b2 = pooled_map[(target, "B2")]
        b3 = pooled_map[(target, "B3")]
        lines.append(
            f"- **{target} — `{signal[target]}`.** B2 AP lift `{_fmt(b2['ap_absolute_lift'])}`; "
            f"B3 AP lift `{_fmt(b3['ap_absolute_lift'])}`; B3−B2 pooled AP "
            f"`{_fmt(b3['pooled_pr_auc_average_precision'] - b2['pooled_pr_auc_average_precision'])}`; "
            f"B3−B2 pooled positive F1 `{_fmt(b3['pooled_positive_f1'] - b2['pooled_positive_f1'])}`."
        )
    lines.extend(
        [
            "",
            "These observations apply only to the frozen task-grouped official-dev OOF protocol. They do not establish test performance, cross-benchmark generalization, statistical significance, the core hypothesis, or publication-level claims.",
            "",
            "Stop after this report and wait for human stage-gate review.",
            "",
        ]
    )
    return "\n".join(lines)


def environment_record() -> dict[str, Any]:
    """Record exact interpreter, OS, hardware, and installed baseline dependencies."""

    package_names = [
        "joblib",
        "narwhals",
        "numpy",
        "PyYAML",
        "scikit-learn",
        "scipy",
        "threadpoolctl",
    ]
    return {
        "generated_at_utc": utc_now(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": platform.platform(),
        "hardware": {
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "gpu_used": False,
        },
        "dependencies": {
            name: importlib.metadata.version(name) for name in package_names
        },
        "formal_run_network_allowed": False,
    }


def write_prerun(config: dict[str, Any]) -> None:
    """Write A1.2a environment and integrity artifacts without estimator fitting."""

    checked = preflight(config)
    environment_path = resolve(config["environment"]["environment_artifact"])
    integrity_path = resolve(config["environment"]["prerun_integrity_artifact"])
    environment = environment_record()
    write_json(environment_path, environment)
    integrity = {
        "stage": "A1.2a",
        "status": "PASS",
        "generated_at_utc": utc_now(),
        "real_dev_estimator_fit_count": 0,
        "verified_hashes": checked["verified_hashes"],
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "config_sha256": sha256_path(CONFIG_PATH),
        "requirements_lock_sha256": sha256_path(
            resolve(config["environment"]["lock_file"])
        ),
        "environment_artifact_sha256": sha256_path(environment_path),
        "eligible_counts": {
            target: {
                "samples": len(checked["labels"][target]),
                "positive": sum(checked["labels"][target].values()),
                "negative": len(checked["labels"][target])
                - sum(checked["labels"][target].values()),
            }
            for target in TARGETS
        },
        "oof_membership_verified_exactly_once": True,
        "outer_and_inner_group_leakage": 0,
        "primary_input_view": "primary_with_natural_errors",
        "baseline_ids": BASELINE_IDS,
        "test_access": {
            "sealed_identifier_manifest_overlap_checks": 1,
            "trajectory_content": 0,
            "labels": 0,
            "predictions": 0,
            "metrics": 0,
        },
        "forbidden_experiments_executed": [],
    }
    write_json(integrity_path, integrity)
    print(json.dumps({"status": "PASS", "mode": "write-prerun"}))


def git_output(arguments: Sequence[str], text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=text
    )
    return result.stdout


def assert_clean_preregistration(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Require a clean worktree and byte-identical A1.2a HEAD implementation."""

    status = str(git_output(["status", "--porcelain=v1"])).strip()
    if status:
        raise IntegrityError(f"formal run requires a clean worktree; found: {status}")
    subject = str(git_output(["show", "-s", "--format=%s", "HEAD"])).strip()
    expected_subject = config["execution"]["required_preregistration_commit_subject"]
    if subject != expected_subject:
        raise IntegrityError(f"HEAD is not the A1.2a preregistration commit: {subject}")
    commit = str(git_output(["rev-parse", "HEAD"])).strip()
    integrity_path = resolve(config["environment"]["prerun_integrity_artifact"])
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    if integrity["script_sha256"] != sha256_path(Path(__file__).resolve()):
        raise IntegrityError("working script differs from preregistered script hash")
    if integrity["config_sha256"] != sha256_path(CONFIG_PATH):
        raise IntegrityError("working config differs from preregistered config hash")
    committed_script = git_output(["show", "HEAD:scripts/run_stage_a1_2_baselines.py"], text=False)
    if committed_script != Path(__file__).read_bytes():
        raise IntegrityError("working run script differs from committed A1.2a bytes")
    committed_config = git_output(["show", "HEAD:configs/stage_a1_2_execution.yaml"], text=False)
    if committed_config != CONFIG_PATH.read_bytes():
        raise IntegrityError("working run config differs from committed A1.2a bytes")
    return commit, integrity


def verify_results(config: dict[str, Any]) -> dict[str, Any]:
    """Recompute frozen hashes, OOF coverage, probabilities, and metrics from artifacts."""

    checked = preflight(config)
    output = config["outputs"]
    predictions = read_csv(resolve(output["oof_predictions"]))
    fold_rows = read_csv(resolve(output["fold_metrics"]))
    pooled_rows = read_csv(resolve(output["pooled_metrics"]))
    expected_total = sum(config["targets"][target]["expected_samples"] for target in TARGETS) * 4
    if len(predictions) != expected_total:
        raise IntegrityError("formal OOF prediction row count is incorrect")
    unique = {
        (row["target"], row["baseline_id"], row["trajectory_key"])
        for row in predictions
    }
    if len(unique) != expected_total:
        raise IntegrityError("formal OOF predictions contain a duplicate key")
    if len(fold_rows) != 60 or len(pooled_rows) != 12:
        raise IntegrityError("fold or pooled metric row count is incorrect")
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            selected = [
                row for row in predictions if row["target"] == target and row["baseline_id"] == baseline
            ]
            if len(selected) != config["targets"][target]["expected_samples"]:
                raise IntegrityError(f"OOF coverage mismatch for {target}/{baseline}")
            for row in selected:
                probability = float(row["predicted_probability"])
                threshold = float(row["selected_threshold"])
                if not math.isfinite(probability) or not 0 <= probability <= 1:
                    raise IntegrityError("invalid probability in prediction artifact")
                if int(row["predicted_label"]) != int(probability >= threshold):
                    raise IntegrityError("predicted label is inconsistent with frozen threshold")
                if int(row["true_label"]) != checked["labels"][target][row["trajectory_key"]]:
                    raise IntegrityError("prediction truth differs from frozen label index")
            recomputed = metrics(
                [int(row["true_label"]) for row in selected],
                [float(row["predicted_probability"]) for row in selected],
                [int(row["predicted_label"]) for row in selected],
            )
            pooled = next(
                row for row in pooled_rows if row["target"] == target and row["baseline_id"] == baseline
            )
            for metric_name, value in recomputed.items():
                if not math.isclose(
                    value, float(pooled[f"pooled_{metric_name}"]), rel_tol=0, abs_tol=1e-12
                ):
                    raise IntegrityError(f"pooled metric mismatch: {target}/{baseline}/{metric_name}")
    return {
        "status": "PASS",
        "verified_hashes": checked["verified_hashes"],
        "oof_rows": len(predictions),
        "unique_target_baseline_trajectory_keys": len(unique),
        "fold_metric_rows": len(fold_rows),
        "pooled_metric_rows": len(pooled_rows),
        "test_trajectory_content_accessed": 0,
        "test_labels_accessed": 0,
    }


def formal_run(config: dict[str, Any], run_id: str, command: str) -> None:
    """Execute the single authorized real-dev run from a clean A1.2a commit."""

    commit, prereg_integrity = assert_clean_preregistration(config)
    for key in FORMAL_OUTPUT_KEYS:
        path = resolve(config["outputs"][key])
        if path.exists():
            raise IntegrityError(f"formal output already exists and will not be overwritten: {path}")
    run_dir = resolve(f"runs/{run_id}")
    if run_dir.exists():
        raise IntegrityError(f"run directory already exists and will not be overwritten: {run_dir}")
    run_dir.mkdir(parents=True)
    log_path = run_dir / "stdout.log"
    logger = logging.getLogger("stage_a1_2")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    start_time = utc_now()
    logger.info("formal Stage A1.2 run starting from preregistration commit %s", commit)
    checked = preflight(config)
    logger.info("preflight hashes, dev eligibility, grouped folds, and sealed-key overlap: PASS")

    feature_rows = structural_rows(checked["cleaned"])
    feature_path = resolve(config["outputs"]["structural_features"])
    write_csv(
        feature_path,
        feature_rows,
        ["trajectory_key", *FEATURE_NAMES, "content_sha256"],
    )
    feature_by_key = {row["trajectory_key"]: row for row in feature_rows}
    predictions: list[dict[str, Any]] = []
    fold_metric_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    warning_records: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline_id in BASELINE_IDS:
            for fold in range(1, 6):
                logger.info("running target=%s baseline=%s outer_fold=%d", target, baseline_id, fold)
                fold_predictions, fold_metric, candidates, thresholds = run_fold(
                    config,
                    target,
                    baseline_id,
                    fold,
                    checked["manifests"][target][fold],
                    checked["labels"][target],
                    feature_by_key,
                    checked["primary"],
                    warning_records,
                )
                predictions.extend(fold_predictions)
                fold_metric_rows.append(fold_metric)
                selection_rows.extend(candidates)
                threshold_rows.extend(thresholds)
                logger.info(
                    "completed target=%s baseline=%s fold=%d config=%s threshold=%.2f AP=%.6f F1=%.6f",
                    target,
                    baseline_id,
                    fold,
                    fold_metric["selected_config_id"],
                    fold_metric["selected_threshold"],
                    fold_metric["pr_auc_average_precision"],
                    fold_metric["positive_f1"],
                )

    predictions.sort(
        key=lambda row: (
            TARGETS.index(row["target"]),
            BASELINE_IDS.index(row["baseline_id"]),
            row["outer_fold"],
            row["trajectory_key"],
        )
    )
    pooled_rows = aggregate_results(config, predictions, fold_metric_rows)
    frequency_rows = config_frequencies(config, selection_rows)
    post_hashes = verify_frozen_hashes(config)
    if post_hashes != checked["verified_hashes"]:
        raise IntegrityError("frozen input hash set changed during the formal run")
    anomalies: list[str] = []
    convergence = [row for row in warning_records if row["is_convergence_warning"]]
    conditions: list[str] = []
    if convergence:
        conditions.append(f"{len(convergence)} Logistic Regression convergence warnings were recorded.")
    learned_zero_positive = [
        row
        for row in fold_metric_rows
        if row["baseline_id"] in {"B2", "B3"} and row["predicted_positive_count"] == 0
    ]
    if learned_zero_positive:
        conditions.append(
            f"{len(learned_zero_positive)} learned-baseline outer folds predicted no positives."
        )
    low_positive_targets = [
        target
        for target in TARGETS
        if config["targets"][target]["expected_positive"]
        < config["stage_conditions"]["target_positive_count_below"]
    ]
    if low_positive_targets:
        conditions.append(
            "Low positive-class support remains a stability limitation for: "
            + ", ".join(low_positive_targets)
            + "."
        )
    stage_decision = "PASS_WITH_CONDITIONS" if conditions else "PASS"
    grades = signal_grades(pooled_rows, fold_metric_rows, anomalies)

    write_csv(
        resolve(config["outputs"]["inner_config_selection"]),
        selection_rows,
        ["target", "baseline_id", "outer_fold", "config_id", "inner_train_size",
         "inner_validation_size", "inner_pr_auc", "selected", "tie_break_rank"],
    )
    write_csv(
        resolve(config["outputs"]["threshold_selection"]),
        threshold_rows,
        ["target", "baseline_id", "outer_fold", "config_id", "threshold", "inner_f1",
         "inner_precision", "inner_recall", "selected"],
    )
    write_csv(
        resolve(config["outputs"]["oof_predictions"]),
        predictions,
        ["trajectory_key", "group_key", "target", "baseline_id", "outer_fold", "true_label",
         "predicted_probability", "selected_threshold", "predicted_label", "selected_config_id"],
    )
    fold_fields = [
        "target", "baseline_id", "outer_fold", "sample_count", "positive_count", "negative_count",
        "prevalence", "predicted_positive_count", "selected_config_id", "selected_threshold",
        *METRIC_NAMES,
    ]
    write_csv(resolve(config["outputs"]["fold_metrics"]), fold_metric_rows, fold_fields)
    pooled_fields = [
        "target", "baseline_id", "sample_count", "positive_count", "negative_count", "prevalence",
        "predicted_positive_count",
    ]
    for metric_name in METRIC_NAMES:
        pooled_fields.extend(
            [f"pooled_{metric_name}", f"fold_mean_{metric_name}", f"fold_std_{metric_name}"]
        )
    pooled_fields.append("ap_absolute_lift")
    write_csv(resolve(config["outputs"]["pooled_metrics"]), pooled_rows, pooled_fields)
    write_csv(
        resolve(config["outputs"]["config_frequency"]),
        frequency_rows,
        ["target", "baseline_id", "config_id", "tie_break_rank", "selected_count"],
    )
    environment = json.loads(
        resolve(config["environment"]["environment_artifact"]).read_text(encoding="utf-8")
    )
    end_time = utc_now()
    run_metadata = {
        "run_id": run_id,
        "git_commit": commit,
        "start_time": start_time,
        "end_time": end_time,
    }
    report = build_report(
        config,
        environment,
        post_hashes,
        fold_metric_rows,
        pooled_rows,
        frequency_rows,
        threshold_rows,
        warning_records,
        grades,
        stage_decision,
        conditions,
        run_metadata,
    )
    report_path = resolve(config["outputs"]["report"])
    atomic_write_text(report_path, report)
    output_hashes = {
        config["outputs"][key]: sha256_path(resolve(config["outputs"][key]))
        for key in FORMAL_OUTPUT_KEYS
        if key != "run_summary"
    }
    summary = {
        "stage": "A1.2",
        "stage_determination": stage_decision,
        "conditions": conditions,
        "run_id": run_id,
        "status": "completed",
        "hypothesis_id": "H1",
        "git_preregistration_commit": commit,
        "data_version": config["source"]["data_version"],
        "split_version": config["source"]["split_version"],
        "config_path": str(CONFIG_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "command": command,
        "random_seed": config["random_state"],
        "start_time": start_time,
        "end_time": end_time,
        "environment": environment,
        "verified_input_hashes_before": checked["verified_hashes"],
        "verified_input_hashes_after": post_hashes,
        "prerun_integrity_sha256": sha256_path(
            resolve(config["environment"]["prerun_integrity_artifact"])
        ),
        "expected_oof_counts": {target: config["targets"][target]["expected_samples"] for target in TARGETS},
        "actual_prediction_rows": len(predictions),
        "oof_complete_exactly_once": True,
        "outer_validation_probability_evaluations": 60,
        "configuration_selection_data": "inner_validation_only",
        "configuration_selection_metric": "average_precision_score",
        "threshold_selection_data": "inner_validation_only",
        "threshold_selection_metric": "positive_f1",
        "convergence_warnings": convergence,
        "all_warnings": warning_records,
        "signal_grades": grades,
        "test_access": {
            "sealed_identifier_manifest_overlap_checks": 1,
            "trajectory_content": 0,
            "labels": 0,
            "predictions": 0,
            "metrics": 0,
        },
        "forbidden_experiments_executed": [],
        "output_hashes": output_hashes,
        "formal_run_code_changed_after_start": False,
        "preregistration_integrity": prereg_integrity,
    }
    summary_path = resolve(config["outputs"]["run_summary"])
    write_json(summary_path, summary)

    shutil.copy2(CONFIG_PATH, run_dir / "config.yaml")
    atomic_write_text(run_dir / "command.txt", command + "\n")
    atomic_write_text(run_dir / "environment.txt", json.dumps(environment, indent=2) + "\n")
    shutil.copy2(summary_path, run_dir / "metrics.json")
    shutil.copy2(resolve(config["outputs"]["oof_predictions"]), run_dir / "predictions.csv")
    shutil.copy2(report_path, run_dir / "summary.md")
    logger.info("formal Stage A1.2 run completed with determination %s", stage_decision)
    for handler in logger.handlers:
        handler.flush()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--write-prerun", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--verify-results", action="store_true")
    parser.add_argument("--run-id")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point with non-zero failure status."""

    args = parse_args(argv)
    try:
        config = load_config(args.config.resolve())
        if args.preflight:
            checked = preflight(config)
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "mode": "preflight",
                        "verified_hashes": checked["verified_hashes"],
                        "real_dev_estimator_fit_count": 0,
                    }
                )
            )
        elif args.write_prerun:
            write_prerun(config)
        elif args.verify_results:
            print(json.dumps(verify_results(config), indent=2))
        else:
            if not args.run_id:
                raise IntegrityError("--run requires --run-id")
            command = " ".join([str(Path(sys.executable)), str(Path(__file__).resolve()), *sys.argv[1:]])
            formal_run(config, args.run_id, command)
        return 0
    except (IntegrityError, KeyError, ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"FATAL: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
