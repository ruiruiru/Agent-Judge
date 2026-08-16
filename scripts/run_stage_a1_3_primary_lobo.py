#!/usr/bin/env python3
"""Preregister, run, and independently verify Stage A1.3 primary LOBO.

``--write-prerun`` may inspect real dev labels and manifests but never calls an
estimator's ``fit`` method. ``--run`` is accepted only from the clean A1.3a
commit. ``--verify-results`` performs no fitting and recomputes the scientific
invariants from the saved predictions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
import subprocess
import sys
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import yaml
from sklearn.dummy import DummyClassifier
from sklearn.metrics import average_precision_score
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import build_evaluation_protocol as splitter
from scripts import run_stage_a1_2_baselines as a12


CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_3_lobo_execution.yaml"
TARGETS = ["success", "side_effect", "looping"]
BASELINE_IDS = ["B0", "B1", "B2", "B3"]
HELD_OUT_GROUPS = ["assistantbench", "visualwebarena", "webarena", "workarena"]
METRIC_NAMES = list(a12.METRIC_NAMES)
FEATURE_NAMES = list(a12.FEATURE_NAMES)


class IntegrityError(RuntimeError):
    """Raised when any frozen A1.3 scientific invariant is violated."""


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


def read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            key = row["trajectory_key"]
            if key in rows:
                raise IntegrityError(f"duplicate JSONL key at line {line_number}: {key}")
            rows[key] = row
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    """Write canonical LF-only CSV bytes so Git and the prereg hash agree."""

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


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config["stage"] != "A1.3":
        raise IntegrityError("execution config is not Stage A1.3")
    if list(config["targets"]) != TARGETS:
        raise IntegrityError("target order differs from the frozen contract")
    if list(config["held_out_groups"]) != HELD_OUT_GROUPS:
        raise IntegrityError("primary held-out groups are not exactly the frozen four")
    if [row["id"] for row in config["baselines"]] != BASELINE_IDS:
        raise IntegrityError("baseline list is not exactly B0-B3")
    if config["structural_features"] != FEATURE_NAMES or len(FEATURE_NAMES) != 13:
        raise IntegrityError("B2 structural features differ from frozen A1.2")
    if config["execution"]["input_view"] != "primary_with_natural_errors":
        raise IntegrityError("B3 input is not the primary view")
    if config["execution"]["test_access"] is not False:
        raise IntegrityError("test access is not frozen to false")
    if config["inner_folds"]["candidates"] != [5, 4, 3, 2]:
        raise IntegrityError("inner fold fallback order changed")
    if set(config["tfidf"]) != {"T1", "T2", "common"}:
        raise IntegrityError("TF-IDF variants are not exactly T1/T2")
    if config["tfidf"]["T1"]["ngram_range"] != [1, 1] or config["tfidf"]["T2"]["ngram_range"] != [1, 2]:
        raise IntegrityError("TF-IDF n-grams changed")
    thresholds = [round(float(value), 2) for value in config["selection"]["thresholds"]]
    if thresholds != [round(value / 100, 2) for value in range(5, 100, 5)]:
        raise IntegrityError("threshold grid changed")
    required_forbidden = {
        "test_evaluation", "secondary_five_group_lobo", "leave_one_model_out",
        "reasoning_sensitivity", "error_ablation", "embedding", "mlp",
        "xgboost", "transformer", "llm_judge", "char_ngram", "B2_B3_fusion",
    }
    if not required_forbidden.issubset(set(config["execution"]["forbidden_experiments"])):
        raise IntegrityError("forbidden experiment boundary is incomplete")
    return config


def _hash_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs = list(config["inputs"].values())
    specs.extend(config["locked_but_not_executed"].values())
    specs.extend(config["a1_2_contract"].values())
    specs.extend([
        {"path": config["environment"]["lock_file"], "sha256": config["environment"]["lock_file_sha256"]},
        {"path": config["environment"]["environment_artifact"], "sha256": config["environment"]["environment_artifact_sha256"]},
    ])
    return specs


def verify_frozen_hashes(config: dict[str, Any]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for spec in _hash_specs(config):
        path = resolve(spec["path"])
        if not path.is_file():
            raise IntegrityError(f"required frozen file missing: {spec['path']}")
        actual = a12.sha256_path(path)
        if actual != spec["sha256"]:
            raise IntegrityError(f"SHA-256 mismatch for {spec['path']}: {actual} != {spec['sha256']}")
        verified[spec["path"]] = actual
    return verified


def _label_index(config: dict[str, Any]) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, int]]]:
    rows = read_csv(resolve(config["inputs"]["label_index"]["path"]))
    by_key = {row["trajectory_key"]: row for row in rows}
    if len(by_key) != len(rows):
        raise IntegrityError("duplicate label-index trajectory key")
    columns = {
        "success": ("success_eligible_main", "success_label"),
        "side_effect": ("side_effect_eligible_main", "side_effect_label"),
        "looping": ("looping_eligible_main", "looping_label"),
    }
    labels: dict[str, dict[str, int]] = {}
    for target, (eligible_column, label_column) in columns.items():
        labels[target] = {
            key: int(row[label_column])
            for key, row in by_key.items()
            if a12.is_true(row[eligible_column])
        }
        expected = config["targets"][target]
        actual = (len(labels[target]), sum(labels[target].values()))
        if actual != (expected["expected_samples"], expected["expected_positive"]):
            raise IntegrityError(f"label-index counts changed for {target}: {actual}")
    return by_key, labels


def validate_primary_manifest(
    config: dict[str, Any], labels: dict[str, dict[str, int]], test_keys: set[str]
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    rows = read_csv(resolve(config["inputs"]["primary_lobo_manifest"]["path"]))
    expected_rows = sum(len(labels[target]) for target in TARGETS) * len(HELD_OUT_GROUPS)
    if len(rows) != expected_rows:
        raise IntegrityError(f"primary LOBO manifest row count is {len(rows)}, expected {expected_rows}")
    cell_rows: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    key_domain: dict[tuple[str, str], str] = {}
    appearances: Counter[tuple[str, str]] = Counter()
    for row in rows:
        target, heldout, key = row["target"], row["held_out_group"], row["trajectory_key"]
        if target not in TARGETS or heldout not in HELD_OUT_GROUPS:
            raise IntegrityError("manifest contains a non-primary target/group")
        if row["protocol"] != "primary_four_group" or key not in labels[target] or key in test_keys:
            raise IntegrityError(f"invalid or test trajectory in primary manifest: {target}/{key}")
        if int(row["label"]) != labels[target][key]:
            raise IntegrityError(f"manifest label differs from index: {target}/{key}")
        domain = row["benchmark_group_primary"]
        if domain not in HELD_OUT_GROUPS:
            raise IntegrityError(f"non-primary benchmark group: {domain}")
        expected_role = "validation" if domain == heldout else "train"
        if row["role"] != expected_role:
            raise IntegrityError(f"role/domain isolation failure: {target}/{heldout}/{key}")
        prior = key_domain.setdefault((target, key), domain)
        if prior != domain:
            raise IntegrityError(f"trajectory belongs to multiple primary domains: {target}/{key}")
        appearances[(target, key)] += 1
        cell_rows[(target, heldout)].append(row)
    if set(appearances.values()) != {4}:
        raise IntegrityError("each eligible trajectory must appear once for every held-out run")
    stats: dict[str, Any] = {}
    for target in TARGETS:
        stats[target] = {}
        for heldout in HELD_OUT_GROUPS:
            cell = cell_rows[(target, heldout)]
            if len(cell) != len(labels[target]) or len({row["trajectory_key"] for row in cell}) != len(cell):
                raise IntegrityError(f"cell does not cover target exactly once: {target}/{heldout}")
            valid = [row for row in cell if row["role"] == "validation"]
            train = [row for row in cell if row["role"] == "train"]
            if {row["group_key"] for row in valid} & {row["group_key"] for row in train}:
                raise IntegrityError(f"external train/held-out group leakage: {target}/{heldout}")
            positive = sum(int(row["label"]) for row in valid)
            actual = {
                "samples": len(valid), "task_groups": len({row["group_key"] for row in valid}),
                "positive": positive, "negative": len(valid) - positive,
            }
            if actual != config["targets"][target]["held_out"][heldout]:
                raise IntegrityError(f"held-out statistics changed for {target}/{heldout}: {actual}")
            stats[target][heldout] = {**actual, "train_samples": len(train)}
    if stats["side_effect"]["assistantbench"]["negative"] != 24 or stats["side_effect"]["assistantbench"]["positive"] != 0:
        raise IntegrityError("Side Effect / AssistantBench is not exactly 24 negative, 0 positive")
    return rows, stats


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Run all real-data integrity checks without fitting any estimator."""

    verified = verify_frozen_hashes(config)
    cleaned = read_jsonl(resolve(config["inputs"]["cleaned"]["path"]))
    primary = read_jsonl(resolve(config["inputs"]["primary"]["path"]))
    if len(cleaned) != 196 or set(cleaned) != set(primary):
        raise IntegrityError("cleaned and primary inputs are not the same 196 dev trajectories")
    for key, record in primary.items():
        if record.get("input_view") != "primary_with_natural_errors" or not isinstance(record.get("serialized_text"), str):
            raise IntegrityError(f"invalid primary serialization: {key}")
    _, labels = _label_index(config)
    test_rows = read_csv(resolve(config["inputs"]["sealed_test_manifest"]["path"]))
    test_keys = {row["trajectory_key"] for row in test_rows}
    if set(cleaned) & test_keys:
        raise IntegrityError("official dev overlaps the sealed test identifier manifest")
    manifest, stats = validate_primary_manifest(config, labels, test_keys)
    return {
        "verified_hashes": verified, "cleaned": cleaned, "primary": primary,
        "labels": labels, "manifest": manifest, "stats": stats,
        "test_identifier_count": len(test_keys),
    }


def _sample(row: dict[str, str]) -> splitter.Sample:
    original, normalized = row["group_key"].split("::", 1)
    return splitter.Sample(
        trajectory_key=row["trajectory_key"], group_key=row["group_key"],
        target=row["target"], label=int(row["label"]), benchmark_original=original,
        benchmark_group_primary=row["benchmark_group_primary"],
        benchmark_group_secondary=row["benchmark_group_secondary"],
        normalized_task_id=normalized, model_name=row["model_name"], official_split="dev",
    )


INNER_FIELDS = [
    "protocol", "trajectory_key", "target", "label", "held_out_group", "role",
    "inner_fold", "inner_n_splits", "benchmark_group_primary",
    "benchmark_group_secondary", "group_key", "model_name",
]


def generate_inner_folds(config: dict[str, Any], manifest: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    """Generate deterministic full inner OOF folds from training domains only."""

    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            cell = [row for row in manifest if row["target"] == target and row["held_out_group"] == heldout]
            train = [row for row in cell if row["role"] == "train"]
            samples = [_sample(row) for row in train]
            namespace = config["inner_folds"]["namespace_template"].format(target=target, held_out_group=heldout)
            n_splits, assignment = splitter.choose_max_feasible(
                samples, config["inner_folds"]["candidates"], config["inner_folds"]["seed"], namespace
            )
            if not splitter.validate_assignment(samples, assignment, n_splits):
                raise IntegrityError(f"generated invalid inner assignment: {target}/{heldout}")
            validation_count: Counter[str] = Counter()
            for row in sorted(cell, key=lambda item: item["trajectory_key"]):
                role = "held_out" if row["role"] == "validation" else "train"
                fold: int | str = "" if role == "held_out" else assignment[row["group_key"]] + 1
                if role == "train":
                    validation_count[row["trajectory_key"]] += 1
                output.append({
                    "protocol": "primary_four_group", "trajectory_key": row["trajectory_key"],
                    "target": target, "label": int(row["label"]), "held_out_group": heldout,
                    "role": role, "inner_fold": fold, "inner_n_splits": n_splits,
                    "benchmark_group_primary": row["benchmark_group_primary"],
                    "benchmark_group_secondary": row["benchmark_group_secondary"],
                    "group_key": row["group_key"], "model_name": row["model_name"],
                })
            if set(validation_count.values()) != {1}:
                raise IntegrityError("training trajectory lacks exactly one frozen inner fold")
    if len(output) != len(manifest):
        raise IntegrityError("inner fold artifact does not mirror primary manifest")
    return output


def validate_inner_folds(config: dict[str, Any], rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, int]]:
    if len(rows) != 2332:
        raise IntegrityError(f"inner fold artifact row count is {len(rows)}, expected 2332")
    result: dict[str, dict[str, int]] = {target: {} for target in TARGETS}
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            cell = [row for row in rows if row["target"] == target and row["held_out_group"] == heldout]
            n_values = {int(row["inner_n_splits"]) for row in cell}
            if len(n_values) != 1:
                raise IntegrityError("cell has multiple inner fold counts")
            n_splits = n_values.pop()
            result[target][heldout] = n_splits
            train = [row for row in cell if row["role"] == "train"]
            held = [row for row in cell if row["role"] == "held_out"]
            if any(str(row["inner_fold"]).strip() for row in held):
                raise IntegrityError("held-out row has an inner fold")
            if {row["group_key"] for row in train} & {row["group_key"] for row in held}:
                raise IntegrityError("held-out group entered inner training")
            if {int(row["inner_fold"]) for row in train} != set(range(1, n_splits + 1)):
                raise IntegrityError("inner fold indices are incomplete")
            samples = [_sample({key: str(value) for key, value in row.items()}) for row in train]
            assignment = {row["group_key"]: int(row["inner_fold"]) - 1 for row in train}
            if not splitter.validate_assignment(samples, assignment, n_splits):
                raise IntegrityError(f"frozen inner assignment invalid: {target}/{heldout}")
    return result


def write_prerun(config: dict[str, Any]) -> None:
    checked = preflight(config)
    folds = generate_inner_folds(config, checked["manifest"])
    fold_path = resolve(config["inner_folds"]["path"])
    write_csv(fold_path, folds, INNER_FIELDS)
    inner_counts = validate_inner_folds(config, folds)
    integrity_path = resolve(config["environment"]["prerun_integrity_artifact"])
    integrity = {
        "stage": "A1.3a", "status": "PASS", "generated_at_utc": utc_now(),
        "real_dev_estimator_fit_count": 0, "verified_hashes": checked["verified_hashes"],
        "script_sha256": a12.sha256_path(Path(__file__).resolve()),
        "config_sha256": a12.sha256_path(CONFIG_PATH),
        "inner_folds_sha256": a12.sha256_path(fold_path),
        "inner_fold_counts": inner_counts, "held_out_statistics": checked["stats"],
        "primary_input_view": "primary_with_natural_errors", "baseline_ids": BASELINE_IDS,
        "side_effect_assistantbench": {"negative": 24, "positive": 0},
        "test_access": {"identifier_overlap_checks": 1, "trajectory_content": 0, "labels": 0, "predictions": 0, "metrics": 0},
        "forbidden_experiments_executed": [],
    }
    write_json(integrity_path, integrity)
    print(json.dumps({"status": "PASS", "mode": "write-prerun", "inner_fold_counts": inner_counts}))


def git_output(arguments: Sequence[str], text: bool = True) -> str | bytes:
    result = subprocess.run(["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=text)
    return result.stdout


def assert_clean_preregistration(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = str(git_output(["status", "--porcelain=v1"])).strip()
    if status:
        raise IntegrityError(f"formal run requires clean worktree; found: {status}")
    subject = str(git_output(["show", "-s", "--format=%s", "HEAD"])).strip()
    if subject != config["execution"]["required_preregistration_commit_subject"]:
        raise IntegrityError(f"HEAD is not A1.3a preregistration: {subject}")
    commit = str(git_output(["rev-parse", "HEAD"])).strip()
    integrity_path = resolve(config["environment"]["prerun_integrity_artifact"])
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    paths = {
        "script_sha256": Path(__file__).resolve(), "config_sha256": CONFIG_PATH,
        "inner_folds_sha256": resolve(config["inner_folds"]["path"]),
    }
    for key, path in paths.items():
        if integrity[key] != a12.sha256_path(path):
            raise IntegrityError(f"working {path.name} differs from preregistered hash")
        relative = path.relative_to(REPO_ROOT).as_posix()
        if git_output(["show", f"HEAD:{relative}"], text=False) != path.read_bytes():
            raise IntegrityError(f"working {path.name} differs from committed A1.3a bytes")
    return commit, integrity


def _features_by_key(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = read_csv(resolve(config["inputs"]["structural_features"]["path"]))
    result = {row["trajectory_key"]: row for row in rows}
    if len(result) != len(rows) or list(rows[0]) != ["trajectory_key", *FEATURE_NAMES, "content_sha256"]:
        raise IntegrityError("frozen structural feature artifact schema changed")
    return result


def _matrix(features: dict[str, dict[str, str]], keys: Sequence[str]) -> np.ndarray:
    return np.asarray([[float(features[key][name]) for name in FEATURE_NAMES] for key in keys], dtype=float)


def fit_predict(
    config: dict[str, Any], baseline: str, candidate: dict[str, Any], train_keys: Sequence[str],
    validation_keys: Sequence[str], labels: dict[str, int], structural: dict[str, dict[str, str]],
    primary: dict[str, dict[str, Any]], context: dict[str, Any], warnings_out: list[dict[str, Any]],
) -> np.ndarray:
    """Fit preprocessing/model on train only and return P(y=1) on validation."""

    y_train = [labels[key] for key in train_keys]
    warning_context = {**context, "config_id": candidate["config_id"]}
    if set(y_train) != {0, 1}:
        raise IntegrityError(f"training partition is not mixed class: {warning_context}")
    if baseline in {"B0", "B1"}:
        model = DummyClassifier(strategy=candidate["strategy"])
        model = a12._fit_with_warning_capture(model, np.zeros((len(train_keys), 1)), y_train, warning_context, warnings_out)
        return a12.positive_probability(model, np.zeros((len(validation_keys), 1)))
    if baseline == "B2":
        scaler = StandardScaler()
        x_train = scaler.fit_transform(_matrix(structural, train_keys))
        x_validation = scaler.transform(_matrix(structural, validation_keys))
        model = a12.make_lr(config, candidate)
        model = a12._fit_with_warning_capture(model, x_train, y_train, warning_context, warnings_out)
        return a12.positive_probability(model, x_validation)
    if baseline == "B3":
        vectorizer = a12.make_tfidf(config, candidate["tfidf"])
        train_text = [primary[key]["serialized_text"] for key in train_keys]
        validation_text = [primary[key]["serialized_text"] for key in validation_keys]
        x_train = vectorizer.fit_transform(train_text)
        x_validation = vectorizer.transform(validation_text)
        model = a12.make_lr(config, candidate)
        model = a12._fit_with_warning_capture(model, x_train, y_train, warning_context, warnings_out)
        return a12.positive_probability(model, x_validation)
    raise IntegrityError(f"unknown baseline: {baseline}")


def _metric_row(
    target: str, baseline: str, heldout: str, rows: Sequence[dict[str, Any]],
    selected_config: str, threshold: float, n_splits: int, task_groups: int,
) -> dict[str, Any]:
    truth = [int(row["true_label"]) for row in rows]
    probabilities = [float(row["predicted_probability"]) for row in rows]
    predicted = [int(row["predicted_label"]) for row in rows]
    positive, negative = sum(truth), len(truth) - sum(truth)
    base: dict[str, Any] = {
        "target": target, "baseline_id": baseline, "held_out_group": heldout,
        "held_out_size": len(rows), "task_group_count": task_groups,
        "positive_count": positive, "negative_count": negative,
        "prevalence": positive / len(rows), "predicted_positive_count": sum(predicted),
        "predicted_positive_rate": sum(predicted) / len(rows), "selected_config_id": selected_config,
        "selected_threshold": threshold, "inner_n_splits": n_splits,
    }
    if positive == 0 or negative == 0:
        base["metric_status"] = "single_class_negative" if positive == 0 else "single_class_positive"
        for name in [*METRIC_NAMES, "ap_lift", "ap_vs_best_dummy", "f1_vs_best_dummy"]:
            base[name] = None
        if positive == 0:
            false_positive = sum(predicted)
            base.update({
                "false_positive_count": false_positive, "false_positive_rate": false_positive / negative,
                "specificity": 1.0 - false_positive / negative,
                "probability_mean": float(np.mean(probabilities)),
                "probability_median": float(np.median(probabilities)),
                "probability_max": float(np.max(probabilities)),
            })
        else:
            base.update({"false_positive_count": None, "false_positive_rate": None, "specificity": None,
                         "probability_mean": float(np.mean(probabilities)), "probability_median": float(np.median(probabilities)),
                         "probability_max": float(np.max(probabilities))})
        return base
    base["metric_status"] = "ok"
    base.update(a12.metrics(truth, probabilities, predicted))
    base["ap_lift"] = base["pr_auc_average_precision"] - base["prevalence"]
    base.update({"ap_vs_best_dummy": None, "f1_vs_best_dummy": None,
                 "false_positive_count": sum(1 for y, p in zip(truth, predicted, strict=True) if y == 0 and p == 1),
                 "false_positive_rate": sum(1 for y, p in zip(truth, predicted, strict=True) if y == 0 and p == 1) / negative,
                 "specificity": sum(1 for y, p in zip(truth, predicted, strict=True) if y == 0 and p == 0) / negative,
                 "probability_mean": float(np.mean(probabilities)), "probability_median": float(np.median(probabilities)),
                 "probability_max": float(np.max(probabilities))})
    return base


DOMAIN_FIELDS = [
    "target", "baseline_id", "held_out_group", "held_out_size", "task_group_count",
    "positive_count", "negative_count", "prevalence", "predicted_positive_count",
    "predicted_positive_rate", "selected_config_id", "selected_threshold", "inner_n_splits",
    "metric_status", *METRIC_NAMES, "ap_lift", "ap_vs_best_dummy", "f1_vs_best_dummy",
    "false_positive_count", "false_positive_rate", "specificity", "probability_mean",
    "probability_median", "probability_max",
]


def _augment_dummy_deltas(rows: list[dict[str, Any]]) -> None:
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            cell = [row for row in rows if row["target"] == target and row["held_out_group"] == heldout]
            if any(row["metric_status"] != "ok" for row in cell):
                continue
            dummy_ap = max(float(row["pr_auc_average_precision"]) for row in cell if row["baseline_id"] in {"B0", "B1"})
            dummy_f1 = max(float(row["positive_f1"]) for row in cell if row["baseline_id"] in {"B0", "B1"})
            for row in cell:
                if row["baseline_id"] in {"B2", "B3"}:
                    row["ap_vs_best_dummy"] = float(row["pr_auc_average_precision"]) - dummy_ap
                    row["f1_vs_best_dummy"] = float(row["positive_f1"]) - dummy_f1


def _macro_rows(domain_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            cell = [row for row in domain_rows if row["target"] == target and row["baseline_id"] == baseline]
            if not cell:
                continue
            valid = [row for row in cell if row["metric_status"] == "ok"]
            if not valid:
                raise IntegrityError(f"fewer than one mixed-class domain for {target}/{baseline}")
            row: dict[str, Any] = {
                "target": target, "baseline_id": baseline, "valid_domain_count": len(valid),
                "excluded_single_class_domain_count": len(cell) - len(valid),
            }
            for metric in [*METRIC_NAMES, "ap_lift"]:
                values = [float(item[metric]) for item in valid]
                row[f"{metric}_macro_mean"] = statistics.mean(values)
                row[f"{metric}_macro_std"] = statistics.stdev(values) if len(values) > 1 else None
            output.append(row)
    return output


def _pooled_rows(predictions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            cell = [row for row in predictions if row["target"] == target and row["baseline_id"] == baseline]
            truth = [int(row["true_label"]) for row in cell]
            probabilities = [float(row["predicted_probability"]) for row in cell]
            predicted = [int(row["predicted_label"]) for row in cell]
            prevalence = sum(truth) / len(truth)
            row = {"target": target, "baseline_id": baseline, "sample_count": len(cell),
                   "positive_count": sum(truth), "negative_count": len(truth) - sum(truth), "prevalence": prevalence}
            row.update(a12.metrics(truth, probabilities, predicted))
            row["ap_lift"] = row["pr_auc_average_precision"] - prevalence
            output.append(row)
    return output


def _signal_grades(domain_rows: Sequence[dict[str, Any]], pooled_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for target in TARGETS:
        mixed_domains = sorted({row["held_out_group"] for row in domain_rows if row["target"] == target and row["metric_status"] == "ok"})
        if len(mixed_domains) < 2:
            output[target] = {"grade": "not_assessable", "mixed_domain_count": len(mixed_domains)}
            continue
        pooled = {(row["baseline_id"]): row for row in pooled_rows if row["target"] == target}
        dummy_f1 = max(float(pooled[b]["positive_f1"]) for b in ["B0", "B1"])
        qualifying: list[str] = []
        details: dict[str, Any] = {}
        for baseline in ["B2", "B3"]:
            domains = [row for row in domain_rows if row["target"] == target and row["baseline_id"] == baseline and row["metric_status"] == "ok"]
            both = sum(float(row["ap_lift"]) > 0 and float(row["f1_vs_best_dummy"]) > 0 for row in domains)
            pooled_pass = float(pooled[baseline]["ap_lift"]) > 0 and float(pooled[baseline]["positive_f1"]) > dummy_f1
            robust = pooled_pass and both / len(domains) >= 0.75
            details[baseline] = {"pooled_pass": pooled_pass, "mixed_domains_with_both": both,
                                 "mixed_domain_count": len(domains), "robust": robust}
            if robust:
                qualifying.append(baseline)
        if qualifying:
            grade = "robust_cross_benchmark_signal"
        elif any(item["pooled_pass"] or item["mixed_domains_with_both"] > 0 for item in details.values()):
            grade = "partial_or_domain_specific_signal"
        else:
            grade = "no_cross_benchmark_signal"
        output[target] = {"grade": grade, "mixed_domain_count": len(mixed_domains), "qualifying_baselines": qualifying, "details": details}
    return output


def _comparison_rows(config: dict[str, Any], domain: Sequence[dict[str, Any]], macro: Sequence[dict[str, Any]], pooled: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    a12_rows = read_csv(resolve(config["a1_2_contract"]["pooled_metrics"]["path"]))
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            current = next(row for row in pooled if row["target"] == target and row["baseline_id"] == baseline)
            prior = next(row for row in a12_rows if row["target"] == target and row["baseline_id"] == baseline)
            domains = [row for row in domain if row["target"] == target and row["baseline_id"] == baseline and row["metric_status"] == "ok"]
            macro_row = next(row for row in macro if row["target"] == target and row["baseline_id"] == baseline)
            ap_best = max(domains, key=lambda row: float(row["pr_auc_average_precision"]))
            ap_worst = min(domains, key=lambda row: float(row["pr_auc_average_precision"]))
            f1_best = max(domains, key=lambda row: float(row["positive_f1"]))
            f1_worst = min(domains, key=lambda row: float(row["positive_f1"]))
            output.append({
                "target": target, "baseline_id": baseline,
                "lobo_pooled_ap": current["pr_auc_average_precision"], "a1_2_pooled_ap": prior["pooled_pr_auc_average_precision"],
                "ap_delta_lobo_minus_a1_2": float(current["pr_auc_average_precision"]) - float(prior["pooled_pr_auc_average_precision"]),
                "lobo_pooled_f1": current["positive_f1"], "a1_2_pooled_f1": prior["pooled_positive_f1"],
                "f1_delta_lobo_minus_a1_2": float(current["positive_f1"]) - float(prior["pooled_positive_f1"]),
                "best_domain_ap": ap_best["held_out_group"], "best_domain_ap_value": ap_best["pr_auc_average_precision"],
                "worst_domain_ap": ap_worst["held_out_group"], "worst_domain_ap_value": ap_worst["pr_auc_average_precision"],
                "best_domain_f1": f1_best["held_out_group"], "best_domain_f1_value": f1_best["positive_f1"],
                "worst_domain_f1": f1_worst["held_out_group"], "worst_domain_f1_value": f1_worst["positive_f1"],
                "domain_ap_std": macro_row["pr_auc_average_precision_macro_std"],
                "domain_f1_std": macro_row["positive_f1_macro_std"],
                "mixed_domains_beating_both_dummies": sum(
                    row["baseline_id"] in {"B2", "B3"} and float(row["ap_vs_best_dummy"]) > 0 and float(row["f1_vs_best_dummy"]) > 0
                    for row in domains
                ) if baseline in {"B2", "B3"} else None,
            })
    return output


def run_models(config: dict[str, Any], checked: dict[str, Any], run_id: str, prereg_commit: str) -> dict[str, Any]:
    frozen_folds = read_csv(resolve(config["inner_folds"]["path"]))
    inner_counts = validate_inner_folds(config, frozen_folds)
    structural = _features_by_key(config)
    primary = checked["primary"]
    warnings_out: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    inner_selected_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    domain_rows: list[dict[str, Any]] = []
    selected_configs: Counter[tuple[str, str, str]] = Counter()
    selected_thresholds: Counter[tuple[str, str, float]] = Counter()

    for target in TARGETS:
        labels = checked["labels"][target]
        for heldout in HELD_OUT_GROUPS:
            cell = [row for row in frozen_folds if row["target"] == target and row["held_out_group"] == heldout]
            train_rows = [row for row in cell if row["role"] == "train"]
            held_rows = [row for row in cell if row["role"] == "held_out"]
            n_splits = inner_counts[target][heldout]
            held_keys = [row["trajectory_key"] for row in held_rows]
            train_keys_all = [row["trajectory_key"] for row in train_rows]
            if set(held_keys) & set(train_keys_all):
                raise IntegrityError("held-out trajectory entered external training")
            for baseline in BASELINE_IDS:
                candidate_probabilities: dict[str, dict[str, float]] = {}
                candidates = a12.candidate_configs(config, baseline)
                for rank, candidate in enumerate(candidates, 1):
                    oof: dict[str, float] = {}
                    for fold in range(1, n_splits + 1):
                        validation_keys = [row["trajectory_key"] for row in train_rows if int(row["inner_fold"]) == fold]
                        fit_keys = [row["trajectory_key"] for row in train_rows if int(row["inner_fold"]) != fold]
                        probabilities = fit_predict(
                            config, baseline, candidate, fit_keys, validation_keys, labels, structural, primary,
                            {"target": target, "baseline_id": baseline, "held_out_group": heldout, "phase": "inner", "inner_fold": fold}, warnings_out,
                        )
                        for key, probability in zip(validation_keys, probabilities, strict=True):
                            if key in oof:
                                raise IntegrityError("duplicate inner OOF prediction")
                            oof[key] = float(probability)
                    if set(oof) != set(train_keys_all):
                        raise IntegrityError("inner OOF predictions are incomplete")
                    score = float(average_precision_score([labels[key] for key in train_keys_all], [oof[key] for key in train_keys_all]))
                    config_rows.append({"target": target, "held_out_group": heldout, "baseline_id": baseline,
                                        "config_id": candidate["config_id"], "inner_n_splits": n_splits,
                                        "inner_oof_size": len(oof), "inner_oof_pr_auc": score,
                                        "selected": False, "tie_break_rank": rank})
                    candidate_probabilities[candidate["config_id"]] = oof
                candidate_result_rows = config_rows[-len(candidates):]
                best_score = max(float(row["inner_oof_pr_auc"]) for row in candidate_result_rows)
                selected_row = min((row for row in candidate_result_rows if math.isclose(float(row["inner_oof_pr_auc"]), best_score, rel_tol=0, abs_tol=1e-15)), key=lambda row: int(row["tie_break_rank"]))
                selected_row["selected"] = True
                selected_id = selected_row["config_id"]
                selected_candidate = next(candidate for candidate in candidates if candidate["config_id"] == selected_id)
                selected_configs[(target, baseline, selected_id)] += 1
                selected_oof = candidate_probabilities[selected_id]
                inner_truth = [labels[key] for key in train_keys_all]
                inner_probability = [selected_oof[key] for key in train_keys_all]
                threshold, tested_thresholds = a12.select_threshold(config, inner_truth, inner_probability)
                selected_thresholds[(target, baseline, threshold)] += 1
                fold_by_key = {row["trajectory_key"]: int(row["inner_fold"]) for row in train_rows}
                for key in train_keys_all:
                    inner_selected_rows.append({"trajectory_key": key, "target": target, "baseline_id": baseline,
                                                "held_out_group": heldout, "inner_fold": fold_by_key[key],
                                                "true_label": labels[key], "predicted_probability": selected_oof[key],
                                                "selected_config_id": selected_id, "inner_n_splits": n_splits})
                for threshold_row in tested_thresholds:
                    threshold_rows.append({"target": target, "held_out_group": heldout, "baseline_id": baseline,
                                           "selected_config_id": selected_id, **threshold_row})
                external_probability = fit_predict(
                    config, baseline, selected_candidate, train_keys_all, held_keys, labels, structural, primary,
                    {"target": target, "baseline_id": baseline, "held_out_group": heldout, "phase": "final_refit", "inner_fold": ""}, warnings_out,
                )
                external_rows: list[dict[str, Any]] = []
                held_by_key = {row["trajectory_key"]: row for row in held_rows}
                for key, probability in zip(held_keys, external_probability, strict=True):
                    row = held_by_key[key]
                    prediction = int(float(probability) >= threshold)
                    out = {"trajectory_key": key, "group_key": row["group_key"], "target": target,
                           "baseline_id": baseline, "held_out_group": heldout, "true_label": labels[key],
                           "predicted_probability": float(probability), "selected_threshold": threshold,
                           "predicted_label": prediction, "selected_config_id": selected_id,
                           "inner_n_splits": n_splits}
                    predictions.append(out)
                    external_rows.append(out)
                task_groups = len({row["group_key"] for row in held_rows})
                domain_rows.append(_metric_row(target, baseline, heldout, external_rows, selected_id, threshold, n_splits, task_groups))

    _augment_dummy_deltas(domain_rows)
    macro_rows = _macro_rows(domain_rows)
    pooled_rows = _pooled_rows(predictions)
    comparison_rows = _comparison_rows(config, domain_rows, macro_rows, pooled_rows)
    signal_grades = _signal_grades(domain_rows, pooled_rows)
    frequency_rows = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            for candidate in a12.candidate_configs(config, baseline):
                frequency_rows.append({"target": target, "baseline_id": baseline, "config_id": candidate["config_id"],
                                       "selected_held_out_group_count": selected_configs[(target, baseline, candidate["config_id"])]})
    summary = {
        "stage": "A1.3", "stage_decision": "PASS_WITH_CONDITIONS", "run_id": run_id,
        "completed_at_utc": utc_now(), "preregistration_commit": prereg_commit,
        "experiment_commit": "recorded_after_commit", "environment": a12.environment_record(),
        "held_out_statistics": checked["stats"], "inner_fold_counts": inner_counts,
        "row_counts": {"inner_config_selection": len(config_rows), "inner_selected_oof_predictions": len(inner_selected_rows),
                       "threshold_selection": len(threshold_rows), "external_predictions": len(predictions),
                       "domain_metrics": len(domain_rows), "macro_metrics": len(macro_rows), "pooled_metrics": len(pooled_rows)},
        "warning_count": len(warnings_out),
        "convergence_warning_count": sum(bool(row["is_convergence_warning"]) for row in warnings_out),
        "warnings": warnings_out, "signal_grades": signal_grades,
        "test_access": {"identifier_overlap_checks": 1, "trajectory_content": 0, "labels": 0, "predictions": 0, "metrics": 0},
        "network_access": 0, "gpu_used": False, "forbidden_experiments_executed": [],
        "hashes_before_run": checked["verified_hashes"],
        "hashes_after_run": verify_frozen_hashes(config),
        "conditions": ["Side Effect / AssistantBench has 24 negatives and 0 positives; dual-class metrics are missing and excluded from macro."],
        "selected_config_distribution": [{"target": key[0], "baseline_id": key[1], "config_id": key[2], "count": count} for key, count in sorted(selected_configs.items())],
        "selected_threshold_distribution": [{"target": key[0], "baseline_id": key[1], "threshold": key[2], "count": count} for key, count in sorted(selected_thresholds.items())],
    }
    paths = config["outputs"]
    write_csv(resolve(paths["inner_config_selection"]), config_rows, ["target", "held_out_group", "baseline_id", "config_id", "inner_n_splits", "inner_oof_size", "inner_oof_pr_auc", "selected", "tie_break_rank"])
    write_csv(resolve(paths["inner_selected_oof_predictions"]), inner_selected_rows, ["trajectory_key", "target", "baseline_id", "held_out_group", "inner_fold", "true_label", "predicted_probability", "selected_config_id", "inner_n_splits"])
    write_csv(resolve(paths["threshold_selection"]), threshold_rows, ["target", "held_out_group", "baseline_id", "selected_config_id", "threshold", "inner_f1", "inner_precision", "inner_recall", "selected"])
    write_csv(resolve(paths["predictions"]), predictions, ["trajectory_key", "group_key", "target", "baseline_id", "held_out_group", "true_label", "predicted_probability", "selected_threshold", "predicted_label", "selected_config_id", "inner_n_splits"])
    write_csv(resolve(paths["domain_metrics"]), domain_rows, DOMAIN_FIELDS)
    macro_fields = ["target", "baseline_id", "valid_domain_count", "excluded_single_class_domain_count", *[field for metric in [*METRIC_NAMES, "ap_lift"] for field in (f"{metric}_macro_mean", f"{metric}_macro_std")]]
    write_csv(resolve(paths["macro_metrics"]), macro_rows, macro_fields)
    pooled_fields = ["target", "baseline_id", "sample_count", "positive_count", "negative_count", "prevalence", *METRIC_NAMES, "ap_lift"]
    write_csv(resolve(paths["pooled_metrics"]), pooled_rows, pooled_fields)
    write_csv(resolve(paths["config_frequency"]), frequency_rows, ["target", "baseline_id", "config_id", "selected_held_out_group_count"])
    write_csv(resolve(paths["comparison_to_a1_2"]), comparison_rows, list(comparison_rows[0]))
    write_json(resolve(paths["run_summary"]), summary)
    return {"summary": summary, "domain": domain_rows, "macro": macro_rows, "pooled": pooled_rows, "comparison": comparison_rows}


def render_report(config: dict[str, Any], result: dict[str, Any]) -> str:
    summary, domain, macro, pooled, comparison = (result[key] for key in ["summary", "domain", "macro", "pooled", "comparison"])
    lines = [
        "# Stage A1.3 primary four-group LOBO report", "", "## Stage decision", "",
        "`PASS_WITH_CONDITIONS` — all technical completeness checks passed; the preregistered single-class Side Effect / AssistantBench cell requires conditional interpretation.", "",
        "## Scope and provenance", "", f"- A1.3a preregistration commit: `{summary['preregistration_commit']}`",
        "- A1.3b experiment commit: recorded by the enclosing result commit", "- Official dev only; primary_with_natural_errors only; B0–B3 only.",
        "- test trajectory/label/prediction/metric access: 0; identifier-only overlap checks: 1.",
        "- Secondary LOBO, LOMO, reasoning/error sensitivity, fusion, complex models, and test evaluation were not run.", "",
        "## Environment", "", f"- Python {summary['environment']['python']['version']}; CPU-only; GPU 0; network access 0.",
        f"- Dependencies: `{json.dumps(summary['environment']['dependencies'], sort_keys=True)}`", "",
        "## Held-out statistics and inner folds", "",
        "| Target | Held-out | n | tasks | neg | pos | inner folds |", "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            stat = summary["held_out_statistics"][target][heldout]
            lines.append(f"| {target} | {heldout} | {stat['samples']} | {stat['task_groups']} | {stat['negative']} | {stat['positive']} | {summary['inner_fold_counts'][target][heldout]} |")
    lines.extend(["", "## Domain results", "", "AP is sklearn average_precision_score. Blank dual-class metrics are intentional for single-class domains.", "",
                  "| Target | Baseline | Held-out | status | prev | AP | AP lift | F1 | threshold | config |", "|---|---|---|---|---:|---:|---:|---:|---:|---|"])
    for row in domain:
        def f(value: Any) -> str:
            return "" if value is None else f"{float(value):.6f}"
        lines.append(f"| {row['target']} | {row['baseline_id']} | {row['held_out_group']} | {row['metric_status']} | {f(row['prevalence'])} | {f(row['pr_auc_average_precision'])} | {f(row['ap_lift'])} | {f(row['positive_f1'])} | {f(row['selected_threshold'])} | {row['selected_config_id']} |")
    lines.extend(["", "## Mixed-domain macro mean ± sample std", "", "| Target | Baseline | valid/excluded | AP | F1 |", "|---|---|---:|---:|---:|"])
    for row in macro:
        lines.append(f"| {row['target']} | {row['baseline_id']} | {row['valid_domain_count']}/{row['excluded_single_class_domain_count']} | {float(row['pr_auc_average_precision_macro_mean']):.6f} ± {float(row['pr_auc_average_precision_macro_std']):.6f} | {float(row['positive_f1_macro_mean']):.6f} ± {float(row['positive_f1_macro_std']):.6f} |")
    lines.extend(["", "## Pooled LOBO and A1.2 descriptive deltas", "", "| Target | Baseline | prevalence | LOBO AP | AP lift | LOBO F1 | ΔAP vs A1.2 | ΔF1 vs A1.2 |", "|---|---|---:|---:|---:|---:|---:|---:|"])
    comp = {(row["target"], row["baseline_id"]): row for row in comparison}
    for row in pooled:
        c = comp[(row["target"], row["baseline_id"])]
        lines.append(f"| {row['target']} | {row['baseline_id']} | {float(row['prevalence']):.6f} | {float(row['pr_auc_average_precision']):.6f} | {float(row['ap_lift']):.6f} | {float(row['positive_f1']):.6f} | {float(c['ap_delta_lobo_minus_a1_2']):+.6f} | {float(c['f1_delta_lobo_minus_a1_2']):+.6f} |")
    side = [row for row in domain if row["target"] == "side_effect" and row["held_out_group"] == "assistantbench"]
    lines.extend(["", "## Side Effect / AssistantBench diagnostic", "", "All four cells contain 24 negatives and 0 positives. AP, ROC-AUC, positive precision/recall/F1/F2, balanced accuracy, MCC, and AP lift are missing—not zero-filled.", "",
                  "| Baseline | predicted positives | false-positive rate | specificity | probability mean/median/max |", "|---|---:|---:|---:|---:|"])
    for row in side:
        lines.append(f"| {row['baseline_id']} | {row['predicted_positive_count']} | {float(row['false_positive_rate']):.6f} | {float(row['specificity']):.6f} | {float(row['probability_mean']):.6f}/{float(row['probability_median']):.6f}/{float(row['probability_max']):.6f} |")
    lines.extend(["", "## Integrity, warnings, and signals", "", f"- External prediction coverage: {summary['row_counts']['external_predictions']}/2332, unique and complete.",
                  f"- Inner configuration rows: {summary['row_counts']['inner_config_selection']}/240; threshold rows: {summary['row_counts']['threshold_selection']}/912.",
                  f"- Warnings: {summary['warning_count']} total; convergence warnings: {summary['convergence_warning_count']}.",
                  f"- Frozen hashes before/after match: {summary['hashes_before_run'] == summary['hashes_after_run']}.", ""])
    for target in TARGETS:
        lines.append(f"- {target}: `{summary['signal_grades'][target]['grade']}`")
    lines.extend(["", "## Stop condition", "", "The formal A1.3 results are complete. Stop here and wait for human stage-gate review; do not begin another experiment.", ""])
    return "\n".join(lines)


def verify_results(config: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute coverage, selection, thresholds, and metrics."""

    checked = preflight(config)
    folds = read_csv(resolve(config["inner_folds"]["path"]))
    validate_inner_folds(config, folds)
    output = config["outputs"]
    configs = read_csv(resolve(output["inner_config_selection"]))
    inner = read_csv(resolve(output["inner_selected_oof_predictions"]))
    thresholds = read_csv(resolve(output["threshold_selection"]))
    predictions = read_csv(resolve(output["predictions"]))
    domain = read_csv(resolve(output["domain_metrics"]))
    macro = read_csv(resolve(output["macro_metrics"]))
    pooled = read_csv(resolve(output["pooled_metrics"]))
    if (len(configs), len(thresholds), len(predictions), len(domain), len(pooled)) != (240, 912, 2332, 48, 12):
        raise IntegrityError("formal output row counts differ from preregistration")
    external_unique = {(row["target"], row["baseline_id"], row["trajectory_key"]) for row in predictions}
    if len(external_unique) != 2332:
        raise IntegrityError("external predictions contain duplicates")
    expected_inner = 12 * sum(config["targets"][target]["expected_samples"] for target in TARGETS)
    if len(inner) != expected_inner or len({(row["target"], row["held_out_group"], row["baseline_id"], row["trajectory_key"]) for row in inner}) != expected_inner:
        raise IntegrityError("selected inner OOF coverage is not exactly once")
    fold_role = {(row["target"], row["held_out_group"], row["trajectory_key"]): row["role"] for row in folds}
    if any(fold_role[(row["target"], row["held_out_group"], row["trajectory_key"])] != "train" for row in inner):
        raise IntegrityError("held-out row appears in inner OOF predictions")
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            for baseline in BASELINE_IDS:
                selection = [row for row in configs if row["target"] == target and row["held_out_group"] == heldout and row["baseline_id"] == baseline]
                selected = [row for row in selection if row["selected"] == "True"]
                if len(selected) != 1:
                    raise IntegrityError("configuration selection is not unique")
                best_score = max(float(row["inner_oof_pr_auc"]) for row in selection)
                expected = min((row for row in selection if math.isclose(float(row["inner_oof_pr_auc"]), best_score, abs_tol=1e-15, rel_tol=0)), key=lambda row: int(row["tie_break_rank"]))
                if selected[0]["config_id"] != expected["config_id"]:
                    raise IntegrityError("configuration is not selected by pooled inner OOF AP/tie-break")
                inner_cell = [row for row in inner if row["target"] == target and row["held_out_group"] == heldout and row["baseline_id"] == baseline]
                recomputed_threshold, _ = a12.select_threshold(config, [int(row["true_label"]) for row in inner_cell], [float(row["predicted_probability"]) for row in inner_cell])
                selected_threshold = [row for row in thresholds if row["target"] == target and row["held_out_group"] == heldout and row["baseline_id"] == baseline and row["selected"] == "True"]
                if len(selected_threshold) != 1 or not math.isclose(float(selected_threshold[0]["threshold"]), recomputed_threshold, abs_tol=1e-15):
                    raise IntegrityError("threshold does not match selected pooled inner OOF")
                external = [row for row in predictions if row["target"] == target and row["held_out_group"] == heldout and row["baseline_id"] == baseline]
                expected_keys = {row["trajectory_key"] for row in folds if row["target"] == target and row["held_out_group"] == heldout and row["role"] == "held_out"}
                if {row["trajectory_key"] for row in external} != expected_keys:
                    raise IntegrityError("external held-out prediction coverage mismatch")
                for row in external:
                    probability, threshold = float(row["predicted_probability"]), float(row["selected_threshold"])
                    if not math.isfinite(probability) or not 0 <= probability <= 1 or int(row["predicted_label"]) != int(probability >= threshold):
                        raise IntegrityError("invalid external probability/label")
                    if int(row["true_label"]) != checked["labels"][target][row["trajectory_key"]]:
                        raise IntegrityError("external truth differs from frozen label index")
    recomputed_domain: list[dict[str, Any]] = []
    for target in TARGETS:
        for heldout in HELD_OUT_GROUPS:
            for baseline in BASELINE_IDS:
                external = [row for row in predictions if row["target"] == target and row["held_out_group"] == heldout and row["baseline_id"] == baseline]
                source = next(row for row in domain if row["target"] == target and row["held_out_group"] == heldout and row["baseline_id"] == baseline)
                recomputed_domain.append(_metric_row(target, baseline, heldout, external, source["selected_config_id"], float(source["selected_threshold"]), int(source["inner_n_splits"]), int(source["task_group_count"])))
    _augment_dummy_deltas(recomputed_domain)
    for expected, recorded in zip(recomputed_domain, domain, strict=True):
        for field in [*METRIC_NAMES, "ap_lift", "ap_vs_best_dummy", "f1_vs_best_dummy"]:
            if expected[field] is None:
                if recorded[field] != "":
                    raise IntegrityError(f"single-class metric was not missing: {field}")
            elif not math.isclose(float(expected[field]), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError(f"domain metric cannot be reproduced: {field}")
    recomputed_macro = _macro_rows(recomputed_domain)
    recomputed_pooled = _pooled_rows(predictions)
    for expected, recorded in zip(recomputed_macro, macro, strict=True):
        for metric in [*METRIC_NAMES, "ap_lift"]:
            for suffix in ["macro_mean", "macro_std"]:
                field = f"{metric}_{suffix}"
                if not math.isclose(float(expected[field]), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
                    raise IntegrityError(f"macro metric cannot be reproduced: {field}")
    for expected, recorded in zip(recomputed_pooled, pooled, strict=True):
        for field in [*METRIC_NAMES, "ap_lift"]:
            if not math.isclose(float(expected[field]), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
                raise IntegrityError(f"pooled metric cannot be reproduced: {field}")
    summary = json.loads(resolve(output["run_summary"]).read_text(encoding="utf-8"))
    if summary["hashes_before_run"] != summary["hashes_after_run"] or verify_frozen_hashes(config) != summary["hashes_after_run"]:
        raise IntegrityError("frozen hashes changed before/after formal run")
    return {"status": "PASS", "external_predictions": len(predictions), "inner_selected_oof": len(inner),
            "config_rows": len(configs), "threshold_rows": len(thresholds), "domain_rows": len(domain),
            "test_content_access": 0, "forbidden_experiments_executed": []}


def formal_run(config: dict[str, Any]) -> None:
    prereg_commit, _ = assert_clean_preregistration(config)
    checked = preflight(config)
    run_id = f"a1_3_primary_lobo_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{prereg_commit[:8]}"
    run_dir = REPO_ROOT / "runs" / run_id
    if run_dir.exists():
        raise IntegrityError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    command = f"{sys.executable} scripts/run_stage_a1_3_primary_lobo.py --config configs/stage_a1_3_lobo_execution.yaml --run"
    (run_dir / "command.txt").write_text(command + "\n", encoding="utf-8")
    shutil.copy2(CONFIG_PATH, run_dir / "config.yaml")
    write_json(run_dir / "environment.json", a12.environment_record())
    write_json(run_dir / "hashes_before.json", checked["verified_hashes"])
    try:
        result = run_models(config, checked, run_id, prereg_commit)
        report = render_report(config, result)
        a12.atomic_write_text(resolve(config["outputs"]["report"]), report)
        verification = verify_results(config)
        write_json(run_dir / "verification.json", verification)
        for key, path_text in config["outputs"].items():
            source = resolve(path_text)
            if source.exists():
                shutil.copy2(source, run_dir / source.name)
        write_json(run_dir / "completed.json", {"status": "PASS_WITH_CONDITIONS", "completed_at_utc": utc_now()})
        print(json.dumps({"status": "PASS_WITH_CONDITIONS", "run_id": run_id, **verification}))
    except Exception as error:
        write_json(run_dir / "FAILED_RUN.json", {"status": "INVALIDATED", "failed_at_utc": utc_now(),
                   "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc(),
                   "required_action": "Preserve this run and rerun every target, baseline, and held-out group after a separate fix commit."})
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
        print(f"A1.3 STOP: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
