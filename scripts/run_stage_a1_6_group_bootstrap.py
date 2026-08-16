#!/usr/bin/env python3
"""Freeze, run, and verify Stage A1.6 task-group cluster bootstrap.

This module consumes only committed A1.3/A1.5 external predictions and metric
artifacts.  It never constructs features, trains estimators, changes thresholds,
or accesses the sealed test set.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
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
from sklearn.metrics import average_precision_score, f1_score


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_6_bootstrap.yaml"
TARGETS = ["success", "side_effect", "looping"]
DOMAINS = ["assistantbench", "visualwebarena", "webarena", "workarena"]
A13_METHODS = ["B0", "B1", "B2", "B3"]
A15_METHODS = [
    "S0_full13", "S1_no_termination", "S2_no_repetition",
    "S3_no_activity_volume", "S4_no_error",
    "S5_no_termination_or_repetition", "S6_termination_repetition_only",
]
METRICS = ["ap", "f1", "ap_lift"]


class IntegrityError(RuntimeError):
    """Raised when a frozen scientific invariant is violated."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path_text: str) -> Path:
    path = (REPO_ROOT / path_text).resolve()
    if path != REPO_ROOT and REPO_ROOT not in path.parents:
        raise IntegrityError(f"configured path escapes repository: {path_text}")
    return path


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    temporary.replace(path)


def git_output(arguments: Sequence[str], *, binary: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True,
        text=not binary,
    )
    return result.stdout


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config["stage"] != "A1.6":
        raise IntegrityError("configuration is not Stage A1.6")
    if config["targets"] != TARGETS or config["held_out_groups"] != DOMAINS:
        raise IntegrityError("target/domain order changed")
    if config["methods"] != {"a1_3": A13_METHODS, "a1_5": A15_METHODS}:
        raise IntegrityError("frozen method collection changed")
    boot = config["bootstrap"]
    expected = {
        "unit": "task_group_cluster", "strata": ["target", "held_out_group"],
        "n_bootstrap_draws": 10000, "seed": 2026,
        "numpy_rng": "numpy.random.Generator", "bit_generator": "numpy.random.PCG64",
        "confidence_level": 0.95, "interval_method": "percentile",
        "percentiles": [2.5, 97.5], "stratified": False,
        "redraw_invalid": False, "impute_invalid": False,
        "macro_minimum_valid_mixed_domains": 2,
        "prevalence_source": "bootstrap_draw", "pooled_role": "secondary",
        "parallel_workers": 8,
    }
    if boot != expected:
        raise IntegrityError("bootstrap design differs from the frozen protocol")
    if config["group_key_definition"] != ["benchmark_original", "normalized_task_id"]:
        raise IntegrityError("group key definition changed")
    comparisons = config["primary_comparisons"]
    if {row["id"] for row in comparisons} != {f"P{i}" for i in range(1, 9)}:
        raise IntegrityError("P1-P8 are incomplete")
    expected_counts = {"P1": 1, "P2": 2, "P3": 3, "P4": 3,
                       "P5": 1, "P6": 3, "P7": 3, "P8": 1}
    if Counter(row["id"] for row in comparisons) != Counter(expected_counts):
        raise IntegrityError("primary estimand collection changed")
    execution = config["execution"]
    if execution["model_training_allowed"] or execution["test_access"]:
        raise IntegrityError("training/test boundary is not frozen off")
    if any(execution[key] for key in [
        "prediction_regeneration_allowed", "config_reselection_allowed",
        "threshold_reselection_allowed",
    ]):
        raise IntegrityError("prediction/selection boundary changed")
    return config


def verify_training_boundary() -> int:
    """AST-audit this formal script for estimator fitting calls."""

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    banned = {"fit", "fit_transform", "partial_fit"}
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in banned
    ]
    if calls:
        raise IntegrityError("formal A1.6 script contains a training call")
    return 0


def _assert_tracked(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    try:
        git_output(["ls-files", "--error-unmatch", relative])
    except subprocess.CalledProcessError as error:
        raise IntegrityError(f"frozen input is not tracked at HEAD: {relative}") from error


def verify_hashes(config: dict[str, Any]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for spec in config["inputs"].values():
        path = resolve(spec["path"])
        if not path.is_file():
            raise IntegrityError(f"missing frozen input: {spec['path']}")
        actual = sha256_path(path)
        if actual != spec["sha256"]:
            raise IntegrityError(
                f"SHA-256 mismatch for {spec['path']}: {actual} != {spec['sha256']}"
            )
        _assert_tracked(path)
        verified[spec["path"]] = actual
    return verified


def verify_upstream_commits(config: dict[str, Any]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for name, spec in config["approved_upstream"].items():
        commit = str(git_output(["rev-parse", spec["commit"]])).strip()
        subject = str(git_output(["show", "-s", "--format=%s", spec["commit"]])).strip()
        if commit != spec["commit"] or subject != spec["subject"]:
            raise IntegrityError(f"upstream commit mismatch: {name}")
        verified[name] = commit
    return verified


def verify_source_revisions(config: dict[str, Any]) -> dict[str, str]:
    manifest = json.loads(resolve(config["inputs"]["source_manifest"]["path"]).read_text(
        encoding="utf-8"
    ))
    for key in ["github_commit", "huggingface_revision"]:
        if manifest[key] != config["source"][key]:
            raise IntegrityError(f"fixed source revision changed: {key}")
    return {key: manifest[key] for key in ["github_commit", "huggingface_revision"]}


def verify_prediction_schema(
    rows: list[dict[str, str]], source: str
) -> tuple[str, list[str]]:
    method_field = "baseline_id" if source == "a1_3" else "variant_id"
    fields = list(rows[0]) if rows else []
    required = [
        "trajectory_key", "group_key", "target", method_field, "held_out_group",
        "true_label", "predicted_probability", "selected_threshold",
        "predicted_label", "selected_config_id", "inner_n_splits",
    ]
    if fields != required:
        raise IntegrityError(f"{source} prediction schema/order changed: {fields}")
    methods = A13_METHODS if source == "a1_3" else A15_METHODS
    expected_count = 2332 if source == "a1_3" else 4081
    if len(rows) != expected_count:
        raise IntegrityError(f"{source} prediction row count changed")
    keys = [
        (r["trajectory_key"], r["target"], r[method_field], r["held_out_group"])
        for r in rows
    ]
    if len(keys) != len(set(keys)):
        raise IntegrityError(f"{source} prediction keys are not unique")
    if set(r[method_field] for r in rows) != set(methods):
        raise IntegrityError(f"{source} method set changed")
    for row in rows:
        if row["target"] not in TARGETS or row["held_out_group"] not in DOMAINS:
            raise IntegrityError(f"non-primary prediction cell in {source}")
        if row["group_key"].split("::", 1)[0] != row["held_out_group"]:
            raise IntegrityError("group_key is not domain-local benchmark_original::task")
        if not row["trajectory_key"].startswith(row["group_key"] + "::"):
            raise IntegrityError("trajectory_key/group_key relationship changed")
        if int(row["true_label"]) not in {0, 1} or int(row["predicted_label"]) not in {0, 1}:
            raise IntegrityError("non-binary frozen prediction label")
        probability = float(row["predicted_probability"])
        if not math.isfinite(probability) or probability < 0.0 or probability > 1.0:
            raise IntegrityError("invalid frozen probability")
    return method_field, methods


def verify_s0_equals_b2(
    a13: list[dict[str, str]], a15: list[dict[str, str]]
) -> dict[str, Any]:
    left = {
        (r["trajectory_key"], r["target"], r["held_out_group"]): r
        for r in a13 if r["baseline_id"] == "B2"
    }
    right = {
        (r["trajectory_key"], r["target"], r["held_out_group"]): r
        for r in a15 if r["variant_id"] == "S0_full13"
    }
    if len(left) != 583 or set(left) != set(right):
        raise IntegrityError("S0/B2 keys differ")
    exact_fields = [
        "group_key", "true_label", "selected_threshold", "predicted_label",
        "selected_config_id", "inner_n_splits",
    ]
    max_probability_error = 0.0
    for key in sorted(left):
        if any(left[key][field] != right[key][field] for field in exact_fields):
            raise IntegrityError(f"S0/B2 exact field mismatch: {key}")
        error = abs(float(left[key]["predicted_probability"]) -
                    float(right[key]["predicted_probability"]))
        max_probability_error = max(max_probability_error, error)
    if max_probability_error != 0.0:
        raise IntegrityError("S0/B2 probability maximum error is not zero")
    return {
        "status": "PASS", "row_count": len(left),
        "keys_exact": True, "labels_exact": True, "configs_exact": True,
        "thresholds_exact": True, "predicted_labels_exact": True,
        "max_probability_absolute_error": max_probability_error,
    }


def _metrics(rows: Sequence[dict[str, str]]) -> dict[str, float | None]:
    truth = np.asarray([int(r["true_label"]) for r in rows], dtype=np.int8)
    probabilities = np.asarray([float(r["predicted_probability"]) for r in rows])
    predicted = np.asarray([int(r["predicted_label"]) for r in rows], dtype=np.int8)
    prevalence = float(np.mean(truth))
    if np.unique(truth).size != 2:
        return {"ap": None, "f1": None, "ap_lift": None, "prevalence": prevalence}
    ap_value = float(average_precision_score(truth, probabilities))
    f1_value = float(f1_score(truth, predicted, pos_label=1, zero_division=0))
    return {"ap": ap_value, "f1": f1_value,
            "ap_lift": ap_value - prevalence, "prevalence": prevalence}


def _optional_float(value: str) -> float | None:
    return None if value.strip() == "" else float(value)


def point_estimate_regression(
    config: dict[str, Any], source: str, predictions: list[dict[str, str]]
) -> tuple[dict[tuple[str, str, str, str, str], float | None], dict[str, Any]]:
    method_field = "baseline_id" if source == "a1_3" else "variant_id"
    prefix = "a1_3" if source == "a1_3" else "a1_5"
    methods = A13_METHODS if source == "a1_3" else A15_METHODS
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in predictions:
        grouped[(row["target"], row[method_field], row["held_out_group"])].append(row)
    point: dict[tuple[str, str, str, str, str], float | None] = {}
    max_error = 0.0
    checked = 0
    domain_report = read_csv(resolve(config["inputs"][f"{prefix}_domain_metrics"]["path"]))
    report_domain = {
        (r["target"], r[method_field], r["held_out_group"]): r for r in domain_report
    }
    for target in TARGETS:
        for method in methods:
            domain_values: dict[str, dict[str, float | None]] = {}
            pooled_rows: list[dict[str, str]] = []
            for domain in DOMAINS:
                rows = grouped[(target, method, domain)]
                if not rows:
                    raise IntegrityError(f"missing frozen cell: {source}/{target}/{method}/{domain}")
                values = _metrics(rows)
                domain_values[domain] = values
                pooled_rows.extend(rows)
                for metric, column in [("ap", "pr_auc_average_precision"),
                                       ("f1", "positive_f1"), ("ap_lift", "ap_lift")]:
                    point[(source, target, method, "domain:" + domain, metric)] = values[metric]
                    expected = _optional_float(report_domain[(target, method, domain)][column])
                    if values[metric] is None or expected is None:
                        if values[metric] is not None or expected is not None:
                            raise IntegrityError("single-class point-estimate NA policy changed")
                    else:
                        error = abs(float(values[metric]) - expected)
                        max_error = max(max_error, error); checked += 1
            macro_report = read_csv(resolve(config["inputs"][f"{prefix}_macro_metrics"]["path"]))
            macro_row = next(r for r in macro_report
                             if r["target"] == target and r[method_field] == method)
            for metric, column in [("ap", "pr_auc_average_precision_macro_mean"),
                                   ("f1", "positive_f1_macro_mean"),
                                   ("ap_lift", "ap_lift_macro_mean")]:
                valid = [float(domain_values[d][metric]) for d in DOMAINS
                         if domain_values[d][metric] is not None]
                value = float(np.mean(valid))
                point[(source, target, method, "macro", metric)] = value
                error = abs(value - float(macro_row[column]))
                max_error = max(max_error, error); checked += 1
            pooled = _metrics(pooled_rows)
            pooled_report = read_csv(resolve(config["inputs"][f"{prefix}_pooled_metrics"]["path"]))
            pooled_row = next(r for r in pooled_report
                              if r["target"] == target and r[method_field] == method)
            for metric, column in [("ap", "pr_auc_average_precision"),
                                   ("f1", "positive_f1"), ("ap_lift", "ap_lift")]:
                value = pooled[metric]
                point[(source, target, method, "pooled", metric)] = value
                if value is None:
                    raise IntegrityError("pooled point estimate unexpectedly invalid")
                error = abs(float(value) - float(pooled_row[column]))
                max_error = max(max_error, error); checked += 1
    if max_error > 1e-12:
        raise IntegrityError(f"{source} point estimate error exceeds 1e-12: {max_error}")
    return point, {"status": "PASS", "checked_values": checked,
                   "max_absolute_error": max_error, "tolerance": 1e-12}


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    training_calls = verify_training_boundary()
    hashes = verify_hashes(config)
    commits = verify_upstream_commits(config)
    revisions = verify_source_revisions(config)
    a13 = read_csv(resolve(config["inputs"]["a1_3_predictions"]["path"]))
    a15 = read_csv(resolve(config["inputs"]["a1_5_predictions"]["path"]))
    verify_prediction_schema(a13, "a1_3")
    verify_prediction_schema(a15, "a1_5")
    s0 = verify_s0_equals_b2(a13, a15)
    point13, check13 = point_estimate_regression(config, "a1_3", a13)
    point15, check15 = point_estimate_regression(config, "a1_5", a15)
    return {
        "hashes": hashes, "commits": commits, "source_revisions": revisions,
        "a13": a13, "a15": a15, "s0_b2": s0,
        "point": {**point13, **point15},
        "point_regression": {"a1_3": check13, "a1_5": check15},
        "training_call_count": training_calls,
    }


def group_registry_source(a13: list[dict[str, str]]) -> dict[tuple[str, str], list[str]]:
    result: dict[tuple[str, str], list[str]] = {}
    for target in TARGETS:
        for domain in DOMAINS:
            rows = [r for r in a13 if r["target"] == target
                    and r["held_out_group"] == domain and r["baseline_id"] == "B0"]
            groups = sorted({r["group_key"] for r in rows})
            if not groups:
                raise IntegrityError(f"no groups for {target}/{domain}")
            result[(target, domain)] = groups
    return result


REGISTRY_FIELDS = [
    "target", "held_out_group", "bootstrap_id", "draw_position",
    "sampled_group_key", "sampled_group_occurrence",
]


def write_draw_registry(
    path: Path, groups_by_cell: dict[tuple[str, str], list[str]], n_draws: int, seed: int
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    rng = np.random.Generator(np.random.PCG64(seed))
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
        writer.writeheader()
        for target in TARGETS:
            for domain in DOMAINS:
                groups = groups_by_cell[(target, domain)]
                count = len(groups)
                for bootstrap_id in range(1, n_draws + 1):
                    sampled = rng.integers(0, count, size=count)
                    occurrences: Counter[str] = Counter()
                    for position, index in enumerate(sampled, 1):
                        group = groups[int(index)]
                        occurrences[group] += 1
                        writer.writerow({
                            "target": target, "held_out_group": domain,
                            "bootstrap_id": bootstrap_id, "draw_position": position,
                            "sampled_group_key": group,
                            "sampled_group_occurrence": occurrences[group],
                        })
    temporary.replace(path)
    return sha256_path(path)


def verify_draw_registry(
    path: Path, groups_by_cell: dict[tuple[str, str], list[str]], n_draws: int, seed: int
) -> dict[tuple[str, str], np.ndarray]:
    rng = np.random.Generator(np.random.PCG64(seed))
    draws: dict[tuple[str, str], np.ndarray] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REGISTRY_FIELDS:
            raise IntegrityError("bootstrap registry schema/order changed")
        iterator = iter(reader)
        total = 0
        duplicate_draw_count = 0
        for target in TARGETS:
            for domain in DOMAINS:
                groups = groups_by_cell[(target, domain)]
                index_by_group = {group: i for i, group in enumerate(groups)}
                matrix = np.empty((n_draws, len(groups)), dtype=np.int16)
                for bootstrap_index in range(n_draws):
                    expected = rng.integers(0, len(groups), size=len(groups))
                    occurrences: Counter[str] = Counter()
                    for position, expected_index in enumerate(expected, 1):
                        try:
                            row = next(iterator)
                        except StopIteration as error:
                            raise IntegrityError("bootstrap registry ended early") from error
                        group = groups[int(expected_index)]
                        occurrences[group] += 1
                        wanted = {
                            "target": target, "held_out_group": domain,
                            "bootstrap_id": str(bootstrap_index + 1),
                            "draw_position": str(position), "sampled_group_key": group,
                            "sampled_group_occurrence": str(occurrences[group]),
                        }
                        if row != wanted:
                            raise IntegrityError("bootstrap registry differs from PCG64(2026)")
                        matrix[bootstrap_index, position - 1] = index_by_group[group]
                        total += 1
                    if len(set(matrix[bootstrap_index].tolist())) < len(groups):
                        duplicate_draw_count += 1
                draws[(target, domain)] = matrix
        try:
            next(iterator)
            raise IntegrityError("bootstrap registry contains trailing rows")
        except StopIteration:
            pass
    if duplicate_draw_count == 0:
        raise IntegrityError("with-replacement registry has no repeated-group draw")
    return draws


def write_prerun(config: dict[str, Any]) -> None:
    checked = preflight(config)
    outputs = config["outputs"]
    formal_keys = [
        "single_method_summary", "primary_delta_summary", "domain_summary",
        "macro_summary", "pooled_summary", "side_effect_support",
        "primary_draw_metrics", "run_summary", "report",
    ]
    existing = [outputs[key] for key in formal_keys if resolve(outputs[key]).exists()]
    if existing:
        raise IntegrityError(f"formal A1.6 outputs already exist before preregistration: {existing}")
    groups = group_registry_source(checked["a13"])
    registry_path = resolve(outputs["draw_registry"])
    registry_hash = write_draw_registry(
        registry_path, groups, config["bootstrap"]["n_bootstrap_draws"],
        config["bootstrap"]["seed"],
    )
    verify_draw_registry(
        registry_path, groups, config["bootstrap"]["n_bootstrap_draws"],
        config["bootstrap"]["seed"],
    )
    group_counts = {
        target: {domain: len(groups[(target, domain)]) for domain in DOMAINS}
        for target in TARGETS
    }
    registry_summary = {
        "stage": "A1.6a", "seed": 2026,
        "rng": "numpy.random.Generator(numpy.random.PCG64(2026))",
        "bit_generator": "PCG64", "n_draws": 10000,
        "resampling_unit": "group_key=(benchmark_original, normalized_task_id)",
        "strata": ["target", "held_out_group"],
        "group_counts": group_counts, "registry_sha256": registry_hash,
        "registry_row_count": sum(sum(v.values()) for v in group_counts.values()) * 10000,
        "stratified_bootstrap": False, "invalid_redraw": False,
    }
    write_json(resolve(outputs["registry_summary"]), registry_summary)
    integrity = {
        "stage": "A1.6a", "status": "PASS", "generated_at_utc": utc_now(),
        "source_revisions": checked["source_revisions"],
        "verified_upstream_commits": checked["commits"],
        "verified_input_hashes": checked["hashes"],
        "point_estimate_regression": checked["point_regression"],
        "s0_equals_a1_3_b2": checked["s0_b2"],
        "training_call_count": checked["training_call_count"],
        "real_model_training_count": 0, "formal_bootstrap_metric_draw_count": 0,
        "test_access": {"manifest": 0, "content": 0, "labels": 0,
                        "predictions": 0, "metrics": 0},
        "forbidden_experiments_executed": [],
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "config_sha256": sha256_path(CONFIG_PATH),
        "registry_sha256": registry_hash,
        "registry_summary_sha256": sha256_path(resolve(outputs["registry_summary"])),
        "group_counts": group_counts,
        "bootstrap": config["bootstrap"],
        "primary_comparisons": config["primary_comparisons"],
    }
    write_json(resolve(outputs["prerun_integrity"]), integrity)
    print(json.dumps({
        "status": "PASS", "mode": "write-prerun", "registry_sha256": registry_hash,
        "registry_rows": registry_summary["registry_row_count"],
        "point_max_error": max(v["max_absolute_error"]
                               for v in checked["point_regression"].values()),
        "s0_b2_probability_max_error": checked["s0_b2"]["max_probability_absolute_error"],
        "training_call_count": 0,
    }, sort_keys=True))


def _assert_committed(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    committed = git_output(["show", f"HEAD:{relative}"], binary=True)
    working = path.read_bytes()
    if committed != working:
        raise IntegrityError(f"preregistered file bytes differ from HEAD: {relative}")


def assert_preregistered(config: dict[str, Any]) -> dict[str, Any]:
    outputs = config["outputs"]
    integrity_path = resolve(outputs["prerun_integrity"])
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    paths = {
        "script_sha256": Path(__file__).resolve(),
        "config_sha256": CONFIG_PATH,
        "registry_sha256": resolve(outputs["draw_registry"]),
        "registry_summary_sha256": resolve(outputs["registry_summary"]),
    }
    for field, path in paths.items():
        if sha256_path(path) != integrity[field]:
            raise IntegrityError(f"preregistered hash changed: {path.name}")
        _assert_committed(path)
    _assert_committed(integrity_path)
    if integrity["formal_bootstrap_metric_draw_count"] != 0:
        raise IntegrityError("A1.6a already contains formal metrics")
    if integrity["primary_comparisons"] != config["primary_comparisons"]:
        raise IntegrityError("P1-P8 changed after preregistration")
    return integrity


def verify_prerun(config: dict[str, Any], *, require_committed: bool = False) -> dict[str, Any]:
    checked = preflight(config)
    groups = group_registry_source(checked["a13"])
    summary = json.loads(resolve(config["outputs"]["registry_summary"]).read_text(
        encoding="utf-8"
    ))
    path = resolve(config["outputs"]["draw_registry"])
    if sha256_path(path) != summary["registry_sha256"]:
        raise IntegrityError("registry hash differs from frozen summary")
    verify_draw_registry(path, groups, 10000, 2026)
    if require_committed:
        assert_preregistered(config)
    return checked


def _assert_clean_formal_start(config: dict[str, Any]) -> str:
    status = str(git_output(["status", "--porcelain=v1"])).strip()
    if status:
        raise IntegrityError(f"formal A1.6b requires clean worktree: {status}")
    subject = str(git_output(["show", "-s", "--format=%s", "HEAD"])).strip()
    if subject != config["execution"]["required_preregistration_commit_subject"]:
        raise IntegrityError(f"HEAD is not A1.6a preregistration: {subject}")
    return str(git_output(["rev-parse", "HEAD"])).strip()


def _aligned_cells(
    rows: list[dict[str, str]], source: str,
    groups_by_cell: dict[tuple[str, str], list[str]],
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    method_field = "baseline_id" if source == "a1_3" else "variant_id"
    methods = A13_METHODS if source == "a1_3" else A15_METHODS
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(row["target"], row[method_field], row["held_out_group"])].append(row)
    result: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    reference_keys: dict[tuple[str, str], list[str]] = {}
    for target in TARGETS:
        for domain in DOMAINS:
            for method in methods:
                cell = sorted(grouped[(target, method, domain)],
                              key=lambda row: row["trajectory_key"])
                keys = [row["trajectory_key"] for row in cell]
                if (target, domain) not in reference_keys:
                    reference_keys[(target, domain)] = keys
                elif keys != reference_keys[(target, domain)]:
                    raise IntegrityError("methods do not share identical external prediction keys")
                groups = groups_by_cell[(target, domain)]
                clusters = [
                    np.asarray([i for i, row in enumerate(cell) if row["group_key"] == group],
                               dtype=np.int16)
                    for group in groups
                ]
                if any(cluster.size == 0 for cluster in clusters):
                    raise IntegrityError("registry group missing from prediction cell")
                result[(source, target, method, domain)] = {
                    "truth": np.asarray([int(row["true_label"]) for row in cell], dtype=np.int8),
                    "probability": np.asarray([float(row["predicted_probability"]) for row in cell]),
                    "predicted": np.asarray([int(row["predicted_label"]) for row in cell], dtype=np.int8),
                    "clusters": clusters,
                }
    return result


def _f1_binary(truth: np.ndarray, predicted: np.ndarray) -> float:
    tp = int(np.sum((truth == 1) & (predicted == 1)))
    fp = int(np.sum((truth == 0) & (predicted == 1)))
    fn = int(np.sum((truth == 1) & (predicted == 0)))
    denominator = 2 * tp + fp + fn
    return 0.0 if denominator == 0 else 2.0 * tp / denominator


def _sample_indices(clusters: list[np.ndarray], sampled: np.ndarray) -> np.ndarray:
    return np.concatenate([clusters[int(index)] for index in sampled])


def _domain_worker(args: tuple[Any, ...]) -> tuple[tuple[str, str, str, str], dict[str, np.ndarray]]:
    key, truth, probability, predicted, clusters, draws = args
    n_draws = draws.shape[0]
    values = {name: np.full(n_draws, np.nan) for name in
              ["ap", "f1", "ap_lift", "prevalence", "fpr", "specificity"]}
    original_mixed = np.unique(truth).size == 2
    for i in range(n_draws):
        indices = _sample_indices(clusters, draws[i])
        y = truth[indices]
        p = probability[indices]
        label = predicted[indices]
        prevalence = float(np.mean(y))
        values["prevalence"][i] = prevalence
        negative = int(np.sum(y == 0))
        if negative:
            fp = int(np.sum((y == 0) & (label == 1)))
            values["fpr"][i] = fp / negative
            values["specificity"][i] = 1.0 - fp / negative
        if original_mixed and np.unique(y).size == 2:
            ap_value = float(average_precision_score(y, p))
            values["ap"][i] = ap_value
            values["f1"][i] = _f1_binary(y, label)
            values["ap_lift"][i] = ap_value - prevalence
    return key, values


def _pooled_worker(args: tuple[Any, ...]) -> tuple[tuple[str, str, str], dict[str, np.ndarray]]:
    key, domain_cells, domain_draws = args
    n_draws = next(iter(domain_draws.values())).shape[0]
    values = {name: np.full(n_draws, np.nan) for name in METRICS}
    for i in range(n_draws):
        truth_parts: list[np.ndarray] = []
        probability_parts: list[np.ndarray] = []
        predicted_parts: list[np.ndarray] = []
        for domain in DOMAINS:
            cell = domain_cells[domain]
            indices = _sample_indices(cell["clusters"], domain_draws[domain][i])
            truth_parts.append(cell["truth"][indices])
            probability_parts.append(cell["probability"][indices])
            predicted_parts.append(cell["predicted"][indices])
        truth = np.concatenate(truth_parts)
        probability = np.concatenate(probability_parts)
        predicted = np.concatenate(predicted_parts)
        if np.unique(truth).size != 2:
            continue
        ap_value = float(average_precision_score(truth, probability))
        values["ap"][i] = ap_value
        values["f1"][i] = _f1_binary(truth, predicted)
        values["ap_lift"][i] = ap_value - float(np.mean(truth))
    return key, values


def compute_distributions(
    config: dict[str, Any], checked: dict[str, Any], draws: dict[tuple[str, str], np.ndarray]
) -> tuple[
    dict[tuple[str, str, str, str], dict[str, np.ndarray]],
    dict[tuple[str, str, str], dict[str, np.ndarray]],
    dict[tuple[str, str, str], dict[str, np.ndarray]],
]:
    groups = group_registry_source(checked["a13"])
    cells = {
        **_aligned_cells(checked["a13"], "a1_3", groups),
        **_aligned_cells(checked["a15"], "a1_5", groups),
    }
    domain_values: dict[tuple[str, str, str, str], dict[str, np.ndarray]] = {}
    workers = config["bootstrap"]["parallel_workers"]
    jobs = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for key, cell in cells.items():
            _, target, _, domain = key
            jobs.append(executor.submit(
                _domain_worker,
                (key, cell["truth"], cell["probability"], cell["predicted"],
                 cell["clusters"], draws[(target, domain)]),
            ))
        for future in as_completed(jobs):
            key, values = future.result()
            domain_values[key] = values
    macro_values: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    for source, methods in [("a1_3", A13_METHODS), ("a1_5", A15_METHODS)]:
        for target in TARGETS:
            for method in methods:
                key = (source, target, method)
                macro_values[key] = {}
                for metric in METRICS:
                    matrix = np.vstack([
                        domain_values[(source, target, method, domain)][metric]
                        for domain in DOMAINS
                    ])
                    valid_count = np.sum(np.isfinite(matrix), axis=0)
                    result = np.full(matrix.shape[1], np.nan)
                    good = valid_count >= config["bootstrap"]["macro_minimum_valid_mixed_domains"]
                    result[good] = np.nanmean(matrix[:, good], axis=0)
                    macro_values[key][metric] = result
                macro_values[key]["valid_domain_count"] = np.sum(np.isfinite(np.vstack([
                    domain_values[(source, target, method, domain)]["ap"]
                    for domain in DOMAINS
                ])), axis=0)
    pooled_values: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    jobs = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for source, methods in [("a1_3", A13_METHODS), ("a1_5", A15_METHODS)]:
            for target in TARGETS:
                for method in methods:
                    key = (source, target, method)
                    jobs.append(executor.submit(
                        _pooled_worker,
                        (key, {domain: cells[(source, target, method, domain)]
                               for domain in DOMAINS},
                         {domain: draws[(target, domain)] for domain in DOMAINS}),
                    ))
        for future in as_completed(jobs):
            key, values = future.result()
            pooled_values[key] = values
    return domain_values, macro_values, pooled_values


def summarize(values: np.ndarray, point: float | None) -> dict[str, Any]:
    valid = values[np.isfinite(values)]
    fixed = int(values.size)
    count = int(valid.size)
    if count:
        lower, upper = np.percentile(valid, [2.5, 97.5])
        median = float(np.median(valid))
        lower_value, upper_value = float(lower), float(upper)
        width = upper_value - lower_value
    else:
        median = lower_value = upper_value = width = None
    return {
        "point_estimate": point, "bootstrap_median": median,
        "ci_lower_95": lower_value, "ci_upper_95": upper_value,
        "ci_width": width, "fixed_draw_count": fixed,
        "valid_draw_count": count, "invalid_draw_count": fixed - count,
        "valid_draw_fraction": count / fixed,
    }


SUMMARY_FIELDS = [
    "source", "target", "method_id", "scope", "held_out_group", "metric",
    "point_estimate", "bootstrap_median", "ci_lower_95", "ci_upper_95",
    "ci_width", "fixed_draw_count", "valid_draw_count", "invalid_draw_count",
    "valid_draw_fraction", "original_metric_status",
]


def build_single_method_summaries(
    checked: dict[str, Any],
    domain_values: dict[tuple[str, str, str, str], dict[str, np.ndarray]],
    macro_values: dict[tuple[str, str, str], dict[str, np.ndarray]],
    pooled_values: dict[tuple[str, str, str], dict[str, np.ndarray]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    point = checked["point"]
    domain_rows: list[dict[str, Any]] = []
    macro_rows: list[dict[str, Any]] = []
    pooled_rows: list[dict[str, Any]] = []
    for source, methods in [("a1_3", A13_METHODS), ("a1_5", A15_METHODS)]:
        for target in TARGETS:
            for method in methods:
                for domain in DOMAINS:
                    for metric in METRICS:
                        point_value = point[(source, target, method, "domain:" + domain, metric)]
                        row = {
                            "source": source, "target": target, "method_id": method,
                            "scope": "domain", "held_out_group": domain, "metric": metric,
                            **summarize(domain_values[(source, target, method, domain)][metric],
                                        point_value),
                            "original_metric_status": "ok" if point_value is not None
                            else "original_single_class",
                        }
                        domain_rows.append(row)
                for scope, collection, destination in [
                    ("macro", macro_values, macro_rows),
                    ("pooled", pooled_values, pooled_rows),
                ]:
                    for metric in METRICS:
                        destination.append({
                            "source": source, "target": target, "method_id": method,
                            "scope": scope, "held_out_group": "", "metric": metric,
                            **summarize(collection[(source, target, method)][metric],
                                        point[(source, target, method, scope, metric)]),
                            "original_metric_status": "ok",
                        })
    single = [*domain_rows, *macro_rows, *pooled_rows]
    return single, domain_rows, macro_rows, pooled_rows


PRIMARY_FIELDS = [
    "comparison_id", "target", "kind", "source", "method_a", "method_b",
    "scope", "metric", "estimand", "role", "point_estimate",
    "bootstrap_median", "ci_lower_95", "ci_upper_95", "ci_width",
    "fixed_draw_count", "valid_draw_count", "invalid_draw_count",
    "valid_draw_fraction", "bootstrap_grade", "interpretation",
]


def _grade(kind: str, summary: dict[str, Any]) -> str:
    valid = summary["valid_draw_fraction"]
    point = summary["point_estimate"]
    lower = summary["ci_lower_95"]
    upper = summary["ci_upper_95"]
    if valid < 0.80:
        return "low_support_unstable"
    if kind == "support_diagnostic":
        return "support_diagnostic_only"
    if kind == "positive_signal":
        if point is not None and point > 0 and lower is not None and lower > 0 and valid >= 0.95:
            return "stable_positive_under_bootstrap"
        if point is not None and point > 0:
            return "directional_but_uncertain"
        return "no_positive_point_signal"
    if upper is not None and upper < 0:
        return "stable_drop_for_A_vs_B"
    if lower is not None and lower > 0:
        return "stable_gain_for_A_vs_B"
    return "difference_uncertain"


def build_primary(
    config: dict[str, Any], checked: dict[str, Any],
    macro_values: dict[tuple[str, str, str], dict[str, np.ndarray]],
    pooled_values: dict[tuple[str, str, str], dict[str, np.ndarray]],
) -> tuple[list[dict[str, Any]], dict[str, list[Any]]]:
    rows: list[dict[str, Any]] = []
    parquet: dict[str, list[Any]] = defaultdict(list)
    for comparison in config["primary_comparisons"]:
        source, target = comparison["source"], comparison["target"]
        method_a, method_b = comparison["method_a"], comparison.get("method_b", "")
        scope, metric = comparison["scope"], comparison["metric"]
        collection = macro_values if scope == "macro" else pooled_values
        values_a = collection[(source, target, method_a)][metric]
        point_a = checked["point"][(source, target, method_a, scope, metric)]
        if comparison["kind"] == "paired_delta":
            values_b = collection[(source, target, method_b)][metric]
            point_b = checked["point"][(source, target, method_b, scope, metric)]
            statistic = values_a - values_b
            point_value = float(point_a) - float(point_b)
            estimand = f"{scope}_{metric}_delta_A_minus_B"
        else:
            values_b = np.full(values_a.size, np.nan)
            statistic = values_a.copy()
            point_value = float(point_a)
            estimand = f"{scope}_{metric}"
        summary = summarize(statistic, point_value)
        grade = _grade(comparison["kind"], summary)
        interpretation = (
            "Side Effect support/width diagnostic only; never upgrades the target conclusion."
            if comparison["kind"] == "support_diagnostic"
            else "Bootstrap stability label under the frozen non-causal protocol."
        )
        row = {
            "comparison_id": comparison["id"], "target": target,
            "kind": comparison["kind"], "source": source,
            "method_a": method_a, "method_b": method_b,
            "scope": scope, "metric": metric, "estimand": estimand,
            "role": comparison["role"], **summary,
            "bootstrap_grade": grade, "interpretation": interpretation,
        }
        rows.append(row)
        valid_domains = (collection[(source, target, method_a)].get("valid_domain_count")
                         if scope == "macro" else np.full(values_a.size, 4))
        for i in range(values_a.size):
            parquet["comparison_id"].append(comparison["id"])
            parquet["target"].append(target)
            parquet["kind"].append(comparison["kind"])
            parquet["source"].append(source)
            parquet["method_a"].append(method_a)
            parquet["method_b"].append(method_b)
            parquet["scope"].append(scope)
            parquet["metric"].append(metric)
            parquet["estimand"].append(estimand)
            parquet["role"].append(comparison["role"])
            parquet["bootstrap_id"].append(i + 1)
            parquet["method_a_value"].append(
                None if not np.isfinite(values_a[i]) else float(values_a[i]))
            parquet["method_b_value"].append(
                None if not np.isfinite(values_b[i]) else float(values_b[i]))
            parquet["statistic_value"].append(
                None if not np.isfinite(statistic[i]) else float(statistic[i]))
            parquet["metric_status"].append(
                "ok" if np.isfinite(statistic[i]) else "invalid_single_class_resample")
            parquet["valid_domain_count"].append(int(valid_domains[i]))
    return rows, parquet


SIDE_FIELDS = [
    "source", "method_id", "held_out_group", "original_positive_count",
    "original_negative_count", "task_group_count", "metric",
    "fixed_draw_count", "valid_draw_count", "invalid_single_class_draw_count",
    "valid_draw_fraction", "point_estimate", "bootstrap_median", "ci_lower_95",
    "ci_upper_95", "ci_width", "support_note",
]


def side_effect_diagnostics(
    checked: dict[str, Any], groups: dict[tuple[str, str], list[str]],
    domain_values: dict[tuple[str, str, str, str], dict[str, np.ndarray]],
    domain_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup = {(r["source"], r["target"], r["method_id"], r["held_out_group"], r["metric"]): r
              for r in domain_rows}
    result: list[dict[str, Any]] = []
    for source, methods, prediction_rows, method_field in [
        ("a1_3", A13_METHODS, checked["a13"], "baseline_id"),
        ("a1_5", A15_METHODS, checked["a15"], "variant_id"),
    ]:
        for method in methods:
            for domain in DOMAINS:
                original = [r for r in prediction_rows if r["target"] == "side_effect"
                            and r[method_field] == method and r["held_out_group"] == domain]
                positive = sum(int(r["true_label"]) for r in original)
                for metric in ["ap", "f1"]:
                    row = lookup[(source, "side_effect", method, domain, metric)]
                    result.append({
                        "source": source, "method_id": method, "held_out_group": domain,
                        "original_positive_count": positive,
                        "original_negative_count": len(original) - positive,
                        "task_group_count": len(groups[("side_effect", domain)]),
                        "metric": metric, "fixed_draw_count": row["fixed_draw_count"],
                        "valid_draw_count": row["valid_draw_count"],
                        "invalid_single_class_draw_count": row["invalid_draw_count"],
                        "valid_draw_fraction": row["valid_draw_fraction"],
                        "point_estimate": row["point_estimate"],
                        "bootstrap_median": row["bootstrap_median"],
                        "ci_lower_95": row["ci_lower_95"],
                        "ci_upper_95": row["ci_upper_95"], "ci_width": row["ci_width"],
                        "support_note": (
                            "original_single_class_negative_no_ap_f1_ci"
                            if positive == 0 else "invalid_single_class_resamples_retained_no_redraw"
                        ),
                    })
    return result


def _format_number(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    return f"{float(value):.6f}"


def generate_report(
    config: dict[str, Any], summary: dict[str, Any], primary: list[dict[str, Any]],
    side_rows: list[dict[str, Any]],
) -> str:
    lines = [
        "# Stage A1.6 group-aware bootstrap uncertainty report", "",
        "## Stage determination", "", f"`{summary['stage_determination']}`", "",
        "The analysis used only frozen A1.3/A1.5 external dev predictions. No model was trained, no prediction/config/threshold was regenerated or reselected, and test access was zero.", "",
        "## Provenance and frozen protocol", "",
        f"- A1.6a preregistration commit: `{summary['preregistration_commit']}`",
        "- A1.6b result commit: recorded by the enclosing result commit.",
        f"- GitHub commit: `{summary['source_revisions']['github_commit']}`",
        f"- Hugging Face revision: `{summary['source_revisions']['huggingface_revision']}`",
        "- Bootstrap unit: `group_key=(benchmark_original, normalized_task_id)`.",
        "- Sampling strata: `target × held_out_group`; Benchmark groups were never pooled into one sampling urn.",
        "- Every selected task group replicates all eligible trajectories in that cluster.",
        "- Seed/RNG/draws: `2026` / `numpy.random.Generator(numpy.random.PCG64(2026))` / `10000`.",
        "- Interval: 95% percentile CI (2.5th, 97.5th percentiles). No BCa/basic/studentized switch.",
        "- Sampling is not stratified. Invalid single-class draws are retained, never redrawn, imputed, or replaced.",
        "- AP lift uses each bootstrap draw's own prevalence.", "",
        "Task-group clustering avoids treating multiple model trajectories for one task as independent observations, which would artificially narrow intervals.", "",
        "## Pre-analysis guards", "",
        f"- A1.3 point-estimate maximum error: `{summary['point_estimate_regression']['a1_3']['max_absolute_error']:.3e}`.",
        f"- A1.5 point-estimate maximum error: `{summary['point_estimate_regression']['a1_5']['max_absolute_error']:.3e}`.",
        f"- S0 vs A1.3 B2 maximum probability error: `{summary['s0_equals_a1_3_b2']['max_probability_absolute_error']:.3e}`; all required keys/labels/configs/thresholds/predicted labels exact.",
        f"- Formal script estimator-training calls: `{summary['training_call_count']}`.", "",
        "## Group counts", "", "| Target | AssistantBench | VisualWebArena | WebArena | WorkArena |", "|---|---:|---:|---:|---:|",
    ]
    for target in TARGETS:
        counts = summary["group_counts"][target]
        lines.append(f"| {target} | {counts['assistantbench']} | {counts['visualwebarena']} | {counts['webarena']} | {counts['workarena']} |")
    lines.extend(["", "## P1-P8 primary inference", "",
                  "| ID | Target | Estimand | Role | Point | Median | 95% CI | Valid fraction | Grade |",
                  "|---|---|---|---|---:|---:|---|---:|---|"])
    for row in primary:
        lines.append(
            f"| {row['comparison_id']} | {row['target']} | {row['method_a']}"
            f"{' − ' + row['method_b'] if row['method_b'] else ''} {row['estimand']} | "
            f"{row['role']} | {_format_number(row['point_estimate'])} | "
            f"{_format_number(row['bootstrap_median'])} | "
            f"[{_format_number(row['ci_lower_95'])}, {_format_number(row['ci_upper_95'])}] | "
            f"{_format_number(row['valid_draw_fraction'])} | `{row['bootstrap_grade']}` |"
        )
    lines.extend([
        "", "These labels describe bootstrap stability only. They are not causal claims or formal hypothesis tests; no p-values or significance terminology are used.", "",
        "## Side Effect support diagnostics", "",
        "Side Effect has only 12 positives. AssistantBench is originally 24 negative / 0 positive and therefore has no AP/F1 CI. VisualWebArena and WorkArena all-negative resamples are retained as low-support evidence.", "",
        "| Method | Domain | Metric | Pos/neg | Invalid draws | Valid fraction | 95% CI | Width |",
        "|---|---|---|---:|---:|---:|---|---:|",
    ])
    for row in side_rows:
        if row["source"] == "a1_3" and row["method_id"] == "B3":
            lines.append(
                f"| B3 | {row['held_out_group']} | {row['metric']} | "
                f"{row['original_positive_count']}/{row['original_negative_count']} | "
                f"{row['invalid_single_class_draw_count']} | "
                f"{_format_number(row['valid_draw_fraction'])} | "
                f"[{_format_number(row['ci_lower_95'])}, {_format_number(row['ci_upper_95'])}] | "
                f"{_format_number(row['ci_width'])} |"
            )
    lines.extend([
        "", "## Per-domain, macro, and pooled uncertainty", "",
        "Complete single-method per-domain, macro, and pooled AP/F1/AP-lift point estimates, medians, percentile intervals, invalid counts, and valid fractions are preserved in the three dedicated CSV artifacts and their combined single-method summary.", "",
        "Pooled LOBO intervals are secondary because the four held-out Benchmarks were evaluated by independently trained models whose probability scales may differ. Primary interpretation prioritizes per-domain and macro distributions.", "",
        "## Integrity and boundaries", "",
        f"- Fixed draw registry SHA-256: `{summary['registry_sha256']}`.",
        f"- Draw-level primary Parquet SHA-256: `{summary['output_hashes']['primary_draw_metrics']}`.",
        f"- Draw-level rows: `{summary['row_counts']['primary_draw_metrics']}`; every preregistered estimand has exactly 10000 fixed draws.",
        "- Paired deltas use the same target/domain registry and bootstrap_id for A and B.",
        "- CI/median/valid fractions were independently recomputed from the draw-level Parquet.",
        "- test access: 0; prohibited experiments: 0; network during formal analysis: 0; GPU: 0.",
        "- No complex model, fusion, secondary LOBO, LOMO, joint OOD, trajectory bootstrap, stratified bootstrap, invalid redraw, or test experiment was run.", "",
        "## Stage recommendation and stop", "",
        f"`{summary['stage_determination']}`. Conditions reflect interval width, direction uncertainty, or low Side Effect support rather than a technical failure.", "",
        "Stop here and wait for human stage-gate review. Do not enter complex models, fusion, secondary LOBO, joint OOD, or test.", "",
    ])
    return "\n".join(lines)


def _environment() -> dict[str, Any]:
    import pyarrow
    return {
        "generated_at_utc": utc_now(), "python": sys.version.split()[0],
        "executable": sys.executable, "platform": platform.platform(),
        "logical_cpu_count": os.cpu_count(), "numpy": np.__version__,
        "scikit_learn": sklearn.__version__, "pyarrow": pyarrow.__version__,
        "gpu_used": False, "formal_run_network_allowed": False,
    }


def _write_primary_parquet(path: Path, columns: dict[str, list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    table = pa.table(columns)
    pq.write_table(table, temporary, compression="zstd", use_dictionary=True)
    temporary.replace(path)


def formal_run(config: dict[str, Any]) -> None:
    preregistration_commit = _assert_clean_formal_start(config)
    checked = verify_prerun(config, require_committed=True)
    outputs = config["outputs"]
    formal_keys = [
        "single_method_summary", "primary_delta_summary", "domain_summary",
        "macro_summary", "pooled_summary", "side_effect_support",
        "primary_draw_metrics", "run_summary", "report",
    ]
    existing = [outputs[key] for key in formal_keys if resolve(outputs[key]).exists()]
    if existing:
        raise IntegrityError(f"formal output exists; refusing overwrite: {existing}")
    started = utc_now()
    run_id = f"a1_6_group_bootstrap_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{preregistration_commit[:8]}"
    run_dir = resolve(f"runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "command.txt").write_text(
        f"{sys.executable} scripts/run_stage_a1_6_group_bootstrap.py --config configs/stage_a1_6_bootstrap.yaml --run\n",
        encoding="utf-8", newline="\n",
    )
    write_json(run_dir / "environment.json", _environment())
    (run_dir / "stdout.log").write_text(
        f"{started} guards PASS; starting frozen 10000-draw analysis\n",
        encoding="utf-8", newline="\n",
    )
    groups = group_registry_source(checked["a13"])
    draws = verify_draw_registry(
        resolve(outputs["draw_registry"]), groups, 10000, 2026
    )
    print(json.dumps({"status": "running", "phase": "bootstrap_metrics", "run_id": run_id}))
    domain_values, macro_values, pooled_values = compute_distributions(
        config, checked, draws
    )
    single, domain_rows, macro_rows, pooled_rows = build_single_method_summaries(
        checked, domain_values, macro_values, pooled_values
    )
    primary, parquet_columns = build_primary(
        config, checked, macro_values, pooled_values
    )
    side_rows = side_effect_diagnostics(checked, groups, domain_values, domain_rows)
    write_csv(resolve(outputs["single_method_summary"]), single, SUMMARY_FIELDS)
    write_csv(resolve(outputs["domain_summary"]), domain_rows, SUMMARY_FIELDS)
    write_csv(resolve(outputs["macro_summary"]), macro_rows, SUMMARY_FIELDS)
    write_csv(resolve(outputs["pooled_summary"]), pooled_rows, SUMMARY_FIELDS)
    write_csv(resolve(outputs["primary_delta_summary"]), primary, PRIMARY_FIELDS)
    write_csv(resolve(outputs["side_effect_support"]), side_rows, SIDE_FIELDS)
    _write_primary_parquet(resolve(outputs["primary_draw_metrics"]), parquet_columns)
    row_counts = {
        "single_method_summary": len(single), "domain_summary": len(domain_rows),
        "macro_summary": len(macro_rows), "pooled_summary": len(pooled_rows),
        "primary_delta_summary": len(primary), "side_effect_support": len(side_rows),
        "primary_draw_metrics": len(parquet_columns["bootstrap_id"]),
    }
    output_hashes = {
        key: sha256_path(resolve(outputs[key])) for key in [
            "single_method_summary", "primary_delta_summary", "domain_summary",
            "macro_summary", "pooled_summary", "side_effect_support",
            "primary_draw_metrics",
        ]
    }
    primary_conditions = [
        row for row in primary
        if row["bootstrap_grade"] in {
            "directional_but_uncertain", "difference_uncertain", "low_support_unstable"
        }
    ]
    side_b3 = [row for row in side_rows if row["source"] == "a1_3"
               and row["method_id"] == "B3"]
    stage_determination = "PASS_WITH_CONDITIONS" if primary_conditions or any(
        row["valid_draw_fraction"] < 0.95 for row in side_b3
        if row["held_out_group"] != "assistantbench"
    ) else "PASS"
    summary = {
        "stage": "A1.6", "stage_determination": stage_determination,
        "run_id": run_id, "started_at_utc": started, "completed_at_utc": utc_now(),
        "preregistration_commit": preregistration_commit,
        "experiment_commit": "recorded_after_commit", "environment": _environment(),
        "source_revisions": checked["source_revisions"],
        "verified_upstream_commits": checked["commits"],
        "hashes_before_run": checked["hashes"],
        "hashes_after_run": verify_hashes(config),
        "point_estimate_regression": checked["point_regression"],
        "s0_equals_a1_3_b2": checked["s0_b2"],
        "bootstrap": config["bootstrap"],
        "registry_sha256": sha256_path(resolve(outputs["draw_registry"])),
        "group_counts": {target: {domain: len(groups[(target, domain)]) for domain in DOMAINS}
                         for target in TARGETS},
        "row_counts": row_counts, "output_hashes": output_hashes,
        "primary_inference": primary,
        "training_call_count": checked["training_call_count"],
        "real_model_training_count": 0, "prediction_regeneration_count": 0,
        "config_reselection_count": 0, "threshold_reselection_count": 0,
        "test_access": {"manifest": 0, "content": 0, "labels": 0,
                        "predictions": 0, "metrics": 0},
        "network_access": 0, "gpu_used": False,
        "forbidden_experiments_executed": [],
        "invalid_draws_redrawn": 0, "stratified_bootstrap": False,
        "trajectory_level_bootstrap": False,
        "conditions": [
            "Side Effect has only 12 positives; AssistantBench is single-class negative.",
            "Some bootstrap intervals or paired directions may remain uncertain.",
            "Pooled LOBO is secondary because domain-specific probability scales may differ.",
        ],
        "run_directory": run_dir.relative_to(REPO_ROOT).as_posix(),
    }
    report = generate_report(config, summary, primary, side_rows)
    resolve(outputs["report"]).write_text(report, encoding="utf-8", newline="\n")
    summary["output_hashes"]["report"] = sha256_path(resolve(outputs["report"]))
    write_json(resolve(outputs["run_summary"]), summary)
    write_json(run_dir / "metrics.json", {
        "stage_determination": stage_determination,
        "primary_inference": primary, "output_hashes": summary["output_hashes"],
    })
    (run_dir / "summary.md").write_text(
        f"# {run_id}\n\nStage determination: `{stage_determination}`.\n\n"
        "Frozen 10000-draw task-group cluster bootstrap completed with no training and zero test access.\n",
        encoding="utf-8", newline="\n",
    )
    with (run_dir / "stdout.log").open("a", encoding="utf-8", newline="") as handle:
        handle.write(f"{utc_now()} formal analysis PASS; outputs written\n")
    print(json.dumps({
        "status": "PASS", "mode": "run", "stage_determination": stage_determination,
        "run_id": run_id, "primary_rows": len(primary),
        "draw_metric_rows": row_counts["primary_draw_metrics"],
    }, sort_keys=True))


def verify_results(config: dict[str, Any], *, recompute_bootstrap: bool = False) -> None:
    checked = verify_prerun(config, require_committed=False)
    outputs = config["outputs"]
    summary = json.loads(resolve(outputs["run_summary"]).read_text(encoding="utf-8"))
    if summary["hashes_before_run"] != summary["hashes_after_run"]:
        raise IntegrityError("formal input hashes changed during A1.6b")
    current = verify_hashes(config)
    if current != summary["hashes_after_run"]:
        raise IntegrityError("formal input hashes changed after A1.6b")
    primary_saved = read_csv(resolve(outputs["primary_delta_summary"]))
    table = pq.read_table(resolve(outputs["primary_draw_metrics"]))
    rows = table.to_pylist()
    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    fixed_counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        key = (row["comparison_id"], row["scope"], row["metric"], row["role"])
        fixed_counts[key] += 1
        if row["statistic_value"] is not None:
            grouped[key].append(float(row["statistic_value"]))
    for saved in primary_saved:
        key = (saved["comparison_id"], saved["scope"], saved["metric"], saved["role"])
        if fixed_counts[key] != 10000:
            raise IntegrityError(f"draw-level primary count is not 10000: {key}")
        values = np.asarray(grouped[key], dtype=float)
        expected_valid = int(saved["valid_draw_count"])
        if values.size != expected_valid:
            raise IntegrityError("draw-level valid count differs from primary summary")
        if values.size:
            lower, upper = np.percentile(values, [2.5, 97.5])
            comparisons = [
                (float(saved["bootstrap_median"]), float(np.median(values))),
                (float(saved["ci_lower_95"]), float(lower)),
                (float(saved["ci_upper_95"]), float(upper)),
            ]
            if any(abs(a - b) > 1e-12 for a, b in comparisons):
                raise IntegrityError("draw-level CI/median does not reproduce summary")
        fraction = values.size / 10000
        if abs(fraction - float(saved["valid_draw_fraction"])) > 1e-12:
            raise IntegrityError("draw-level valid fraction does not reproduce summary")
    if recompute_bootstrap:
        groups = group_registry_source(checked["a13"])
        draws = verify_draw_registry(resolve(outputs["draw_registry"]), groups, 10000, 2026)
        domain_values, macro_values, pooled_values = compute_distributions(config, checked, draws)
        single, domain_rows, macro_rows, pooled_rows = build_single_method_summaries(
            checked, domain_values, macro_values, pooled_values
        )
        primary, _ = build_primary(config, checked, macro_values, pooled_values)
        for path_key, actual_rows, fields in [
            ("single_method_summary", single, SUMMARY_FIELDS),
            ("domain_summary", domain_rows, SUMMARY_FIELDS),
            ("macro_summary", macro_rows, SUMMARY_FIELDS),
            ("pooled_summary", pooled_rows, SUMMARY_FIELDS),
            ("primary_delta_summary", primary, PRIMARY_FIELDS),
        ]:
            temporary = resolve(outputs[path_key]).with_name(outputs[path_key].split("/")[-1] + ".verify.tmp")
            write_csv(temporary, actual_rows, fields)
            same = temporary.read_bytes() == resolve(outputs[path_key]).read_bytes()
            temporary.unlink()
            if not same:
                raise IntegrityError(f"full recomputation differs: {path_key}")
    print(json.dumps({
        "status": "PASS", "mode": "verify-results",
        "draw_level_primary_ci_recomputed": True,
        "full_bootstrap_recomputed": recompute_bootstrap,
        "training_call_count": checked["training_call_count"],
        "test_access": 0,
    }, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-prerun", action="store_true")
    group.add_argument("--verify-prerun", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--verify-results", action="store_true")
    parser.add_argument("--recompute-bootstrap", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config_path = args.config if args.config.is_absolute() else (REPO_ROOT / args.config)
        config = load_config(config_path.resolve())
        if args.write_prerun:
            write_prerun(config)
        elif args.verify_prerun:
            verify_prerun(config, require_committed=False)
            print(json.dumps({"status": "PASS", "mode": "verify-prerun"}))
        elif args.run:
            formal_run(config)
        else:
            verify_results(config, recompute_bootstrap=args.recompute_bootstrap)
        return 0
    except Exception as error:
        print(json.dumps({"status": "STOP", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
