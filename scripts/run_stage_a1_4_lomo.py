#!/usr/bin/env python3
"""Preregister, execute, and independently verify Stage A1.4 LOMO.

``--write-prerun`` may inspect the official dev manifest, labels, frozen
features, and primary text, but it never calls an estimator's ``fit`` method.
``--run`` is accepted only from the clean A1.4a commit.  ``--verify-results``
is read-only and performs no model fitting.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
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
import scipy
import sklearn
import yaml
from sklearn.metrics import average_precision_score

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import build_evaluation_protocol as splitter
from scripts import run_stage_a1_2_baselines as a12
from scripts import run_stage_a1_3_primary_lobo as a13


CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_4_lomo_execution.yaml"
TARGETS = ["success", "side_effect", "looping"]
BASELINE_IDS = ["B0", "B1", "B2", "B3"]
METRIC_NAMES = list(a12.METRIC_NAMES)
FEATURE_NAMES = list(a12.FEATURE_NAMES)


class IntegrityError(RuntimeError):
    """Raised when a frozen Stage A1.4 scientific invariant is violated."""


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
    return a13.read_jsonl(path)


def write_csv(path: Path, rows: Sequence[dict[str, Any]], fields: Sequence[str]) -> None:
    a13.write_csv(path, rows, fields)


def write_json(path: Path, value: Any) -> None:
    a12.write_json(path, value)


def git_output(arguments: Sequence[str], text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=text
    )
    return result.stdout


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config["stage"] != "A1.4" or list(config["targets"]) != TARGETS:
        raise IntegrityError("execution config is not the frozen Stage A1.4 target contract")
    if [row["id"] for row in config["baselines"]] != BASELINE_IDS:
        raise IntegrityError("baseline list is not exactly B0-B3")
    if config["structural_features"] != FEATURE_NAMES or len(FEATURE_NAMES) != 13:
        raise IntegrityError("B2 structural features differ from frozen A1.2/A1.3")
    if config["execution"]["input_view"] != "primary_with_natural_errors":
        raise IntegrityError("B3 input is not the frozen primary view")
    if config["execution"]["test_access"] is not False or config["execution"]["test_manifest_access"] is not False:
        raise IntegrityError("all test access must remain false")
    if config["external_group_overlap"] != {
        "allowed": True,
        "joint_task_model_holdout": False,
        "interpretation": "model_only_generalization_not_joint_task_model_ood",
    }:
        raise IntegrityError("LOMO was changed into a joint task/model holdout")
    if config["inner_folds"]["candidates"] != [5, 4, 3, 2]:
        raise IntegrityError("inner-fold fallback order changed")
    if set(config["tfidf"]) != {"T1", "T2", "common"}:
        raise IntegrityError("TF-IDF variants are not exactly T1/T2")
    if config["tfidf"]["T1"]["ngram_range"] != [1, 1] or config["tfidf"]["T2"]["ngram_range"] != [1, 2]:
        raise IntegrityError("TF-IDF n-grams changed")
    thresholds = [round(float(value), 2) for value in config["selection"]["thresholds"]]
    if thresholds != [round(value / 100, 2) for value in range(5, 100, 5)]:
        raise IntegrityError("threshold grid changed")
    required_forbidden = {
        "test_evaluation", "primary_lobo_rerun", "secondary_five_group_lobo",
        "task_model_joint_holdout", "reasoning_sensitivity", "error_ablation",
        "model_literal_redaction", "embedding", "mlp", "random_forest",
        "xgboost", "transformer", "llm_judge", "char_ngram", "B2_B3_fusion",
    }
    if not required_forbidden.issubset(set(config["execution"]["forbidden_experiments"])):
        raise IntegrityError("forbidden-experiment boundary is incomplete")
    expected = config["execution"]
    counts = (
        expected["expected_config_selection_rows"],
        expected["expected_threshold_selection_rows"],
        expected["expected_external_prediction_rows"],
        expected["expected_selected_inner_oof_rows"],
        expected["expected_model_metric_rows"],
    )
    if counts != (240, 912, 2332, 6996, 48):
        raise IntegrityError("formal row-count contract changed")
    return config


def _hash_specs(config: dict[str, Any]) -> list[dict[str, Any]]:
    specs = list(config["inputs"].values())
    specs.extend(config["frozen_protocol"].values())
    specs.extend(config["a1_2_contract"].values())
    specs.extend(config["a1_3_contract"].values())
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


def verify_source_commits(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    expected = {
        config["source"]["a1_2_preregistration_commit"]: "chore: preregister minimal grouped baselines",
        config["source"]["a1_2_experiment_commit"]: "experiment: run grouped minimal dev baselines",
        config["source"]["a1_3_preregistration_commit"]: "chore: preregister primary lobo baselines",
        config["source"]["a1_3_byte_fix_commit"]: "fix: normalize primary lobo preregistration bytes",
        config["source"]["a1_3_experiment_commit"]: "experiment: run primary lobo baselines",
    }
    result: dict[str, dict[str, str]] = {}
    for commit, subject in expected.items():
        if str(git_output(["cat-file", "-t", commit])).strip() != "commit":
            raise IntegrityError(f"required commit is unavailable: {commit}")
        actual_subject = str(git_output(["show", "-s", "--format=%s", commit])).strip()
        if actual_subject != subject:
            raise IntegrityError(f"commit subject mismatch: {commit}: {actual_subject}")
        result[commit] = {"subject": actual_subject}
    chain = [
        config["source"]["a1_3_preregistration_commit"],
        config["source"]["a1_3_byte_fix_commit"],
        config["source"]["a1_3_experiment_commit"],
    ]
    for parent, child in zip(chain, chain[1:]):
        actual_parent = str(git_output(["show", "-s", "--format=%P", child])).strip()
        if actual_parent != parent:
            raise IntegrityError(f"A1.3 commit chain mismatch: {child} parent is {actual_parent}")
    return result


def verify_environment(config: dict[str, Any]) -> dict[str, Any]:
    frozen = json.loads(resolve(config["environment"]["environment_artifact"]).read_text(encoding="utf-8"))
    current = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "dependencies": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit-learn": sklearn.__version__,
            "PyYAML": yaml.__version__,
        },
    }
    if current["python"] != frozen["python"]["version"] or current["platform"] != frozen["platform"]:
        raise IntegrityError(f"frozen runtime changed: {current}")
    for name, version in current["dependencies"].items():
        if version != frozen["dependencies"][name]:
            raise IntegrityError(f"frozen dependency changed: {name}={version}")
    return current


def _label_index(config: dict[str, Any]) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, int]]]:
    rows = read_csv(resolve(config["inputs"]["label_index"]["path"]))
    by_key = {row["trajectory_key"]: row for row in rows}
    if len(by_key) != len(rows) or any(row["official_split"] != "dev" for row in rows):
        raise IntegrityError("label index is not a unique official-dev-only index")
    columns = {
        "success": ("success_eligible_main", "success_label"),
        "side_effect": ("side_effect_eligible_main", "side_effect_label"),
        "looping": ("looping_eligible_main", "looping_label"),
    }
    labels: dict[str, dict[str, int]] = {}
    for target, (eligibility, label) in columns.items():
        labels[target] = {
            key: int(row[label]) for key, row in by_key.items()
            if a12.is_true(row[eligibility]) and row[label] in {"0", "1"}
        }
        expected = config["targets"][target]
        actual = (len(labels[target]), sum(labels[target].values()))
        if actual != (expected["expected_samples"], expected["expected_positive"]):
            raise IntegrityError(f"eligible target counts changed for {target}: {actual}")
    return by_key, labels


def _coverage_statuses(
    config: dict[str, Any], rows: Sequence[dict[str, str]], models: Sequence[str]
) -> dict[str, str]:
    primary = set(config["primary_benchmarks"])
    status: dict[str, str] = {}
    coverage_by_model: dict[str, set[str]] = {}
    for model in models:
        coverage = {
            row["benchmark_group_primary"] for row in rows
            if row["role"] == "validation" and row["held_out_model"] == model
        }
        coverage_by_model[model] = coverage
        status[model] = (
            "full_primary_benchmark_coverage" if coverage == primary
            else "partial_primary_benchmark_coverage"
        )
    selector = config["model_set"]["known_partial_selector"].removeprefix("casefold_contains_")
    matches = [model for model in models if selector in model.casefold()]
    if len(matches) != 1:
        raise IntegrityError("manifest does not identify exactly one Meta-Llama model")
    partial_model = matches[0]
    missing = primary - coverage_by_model[partial_model]
    if missing != {config["model_set"]["expected_missing_primary_benchmark"]}:
        raise IntegrityError(f"Meta-Llama coverage differs from A1.1: missing={sorted(missing)}")
    if any(status[model] != "full_primary_benchmark_coverage" for model in models if model != partial_model):
        raise IntegrityError("a non-Meta-Llama model unexpectedly has partial primary coverage")
    return status


def validate_lomo_manifest(
    config: dict[str, Any], labels: dict[str, dict[str, int]], index: dict[str, dict[str, str]]
) -> tuple[list[dict[str, str]], list[str], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_csv(resolve(config["inputs"]["lomo_manifest"]["path"]))
    models = sorted({row["held_out_model"] for row in rows}, key=str.casefold)
    if len(models) != config["model_set"]["expected_count"]:
        raise IntegrityError(f"manifest model set has {len(models)} entries, expected 4")
    expected_rows = sum(len(labels[target]) for target in TARGETS) * len(models)
    if len(rows) != expected_rows:
        raise IntegrityError(f"LOMO manifest has {len(rows)} rows, expected {expected_rows}")
    appearances: Counter[tuple[str, str]] = Counter()
    cells: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        target, heldout, key = row["target"], row["held_out_model"], row["trajectory_key"]
        if target not in TARGETS or heldout not in models or key not in labels[target] or key not in index:
            raise IntegrityError(f"invalid LOMO manifest row: {target}/{heldout}/{key}")
        expected_group = f"{index[key]['benchmark_original']}::{index[key]['task_id']}"
        if row["group_key"] != expected_group or row["model_name"] != index[key]["model_name"]:
            raise IntegrityError(f"LOMO identity/group join mismatch: {target}/{heldout}/{key}")
        if row["benchmark_group_primary"] != index[key]["benchmark_group_primary"]:
            raise IntegrityError(f"LOMO benchmark join mismatch: {target}/{heldout}/{key}")
        if int(row["label"]) != labels[target][key]:
            raise IntegrityError(f"LOMO label differs from main index: {target}/{key}")
        expected_role = "validation" if row["model_name"] == heldout else "train"
        if row["role"] != expected_role:
            raise IntegrityError(f"held-out model role failure: {target}/{heldout}/{key}")
        appearances[(target, key)] += 1
        cells[(target, heldout)].append(row)
    if set(appearances.values()) != {4}:
        raise IntegrityError("each eligible trajectory must appear once in each of four model runs")
    statuses = _coverage_statuses(config, rows, models)
    stats: dict[str, Any] = {target: {} for target in TARGETS}
    overlap_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        validation_union: set[str] = set()
        for heldout in models:
            cell = cells[(target, heldout)]
            if len(cell) != len(labels[target]) or len({row["trajectory_key"] for row in cell}) != len(cell):
                raise IntegrityError(f"LOMO cell does not cover target once: {target}/{heldout}")
            train = [row for row in cell if row["role"] == "train"]
            valid = [row for row in cell if row["role"] == "validation"]
            if {row["trajectory_key"] for row in train} & {row["trajectory_key"] for row in valid}:
                raise IntegrityError("a held-out trajectory entered external training")
            if any(row["model_name"] == heldout for row in train) or any(row["model_name"] != heldout for row in valid):
                raise IntegrityError("held-out model entered external training")
            train_labels = {int(row["label"]) for row in train}
            valid_labels = {int(row["label"]) for row in valid}
            if train_labels != {0, 1} or valid_labels != {0, 1}:
                raise IntegrityError(f"external train/validation lacks a class: {target}/{heldout}")
            validation_union.update(row["trajectory_key"] for row in valid)
            train_groups = {row["group_key"] for row in train}
            valid_groups = {row["group_key"] for row in valid}
            overlap = train_groups & valid_groups
            valid_with_counterpart = sum(row["group_key"] in train_groups for row in valid)
            stat = {
                "train_samples": len(train),
                "train_task_groups": len(train_groups),
                "train_negative": len(train) - sum(int(row["label"]) for row in train),
                "train_positive": sum(int(row["label"]) for row in train),
                "validation_samples": len(valid),
                "validation_task_groups": len(valid_groups),
                "validation_negative": len(valid) - sum(int(row["label"]) for row in valid),
                "validation_positive": sum(int(row["label"]) for row in valid),
                "overlap_group_count": len(overlap),
                "validation_only_group_count": len(valid_groups - train_groups),
                "validation_trajectories_with_train_counterpart": valid_with_counterpart,
                "validation_trajectory_counterpart_rate": valid_with_counterpart / len(valid),
                "coverage_status": statuses[heldout],
            }
            stats[target][heldout] = stat
            overlap_rows.append({"target": target, "held_out_model": heldout, **stat})
        if validation_union != set(labels[target]):
            raise IntegrityError(f"held-out validation union is incomplete for {target}")
    coverage_rows: list[dict[str, Any]] = []
    for target in TARGETS:
        for heldout in models:
            valid = [row for row in cells[(target, heldout)] if row["role"] == "validation"]
            for benchmark in config["primary_benchmarks"]:
                subset = [row for row in valid if row["benchmark_group_primary"] == benchmark]
                positives = sum(int(row["label"]) for row in subset)
                negatives = len(subset) - positives
                if not subset:
                    class_status = "no_coverage"
                elif positives and negatives:
                    class_status = "mixed_class"
                elif positives:
                    class_status = "single_class_positive"
                else:
                    class_status = "single_class_negative"
                coverage_rows.append({
                    "target": target, "held_out_model": heldout,
                    "benchmark_group_primary": benchmark, "trajectory_count": len(subset),
                    "task_group_count": len({row["group_key"] for row in subset}),
                    "negative_count": negatives, "positive_count": positives,
                    "coverage_present": bool(subset), "class_status": class_status,
                    "coverage_status": statuses[heldout],
                })
    if len(coverage_rows) != len(TARGETS) * len(models) * len(config["primary_benchmarks"]):
        raise IntegrityError("coverage matrix is incomplete")
    return rows, models, stats, overlap_rows, coverage_rows


def _literal_candidates(models: Sequence[str]) -> list[tuple[str, str, str]]:
    candidates: dict[str, set[str]] = defaultdict(set)
    exacts = {model.casefold(): model for model in models}
    for model in models:
        stripped = model.removeprefix("GenericAgent-")
        values = {stripped}
        if "_" in stripped:
            values.add(stripped.split("_", 1)[1])
        for value in values:
            if len(value) >= 8:
                candidates[value.casefold()].add(model)
    output = [(model, model, "exact_model_name") for model in models]
    for literal, owners in candidates.items():
        if len(owners) == 1 and literal not in exacts:
            output.append((next(iter(owners)), literal, "derived_unambiguous_alias"))
    return sorted(output, key=lambda item: (-len(item[1]), item[1].casefold()))


def _line_source_field(line: str, current: str) -> str:
    stripped = line.strip()
    if stripped == "[TASK]":
        return "task.instruction"
    if stripped.startswith("[STEP "):
        return "step"
    if stripped == "ACTION:":
        return "steps[].action"
    if stripped == "OBSERVATION:":
        return "steps[].observation"
    if stripped == "FOCUSED ELEMENT:":
        return "steps[].focused_element"
    if stripped == "ERROR:":
        return "steps[].error"
    if stripped == "[TERMINAL]":
        return "terminal"
    if stripped.startswith("LAST ACTION:"):
        return "terminal.last_nonempty_action"
    if stripped.startswith("LAST OBSERVATION:"):
        return "terminal.last_nonempty_observation"
    if stripped.startswith("TERMINATION SIGNAL:"):
        return "terminal.termination_signal"
    return current


LITERAL_FIELDS = [
    "trajectory_key", "model_name", "matched_model_name", "matched_literal",
    "match_type", "source_field", "occurrence_count", "review_status",
]


def audit_model_literals(
    primary: dict[str, dict[str, Any]], index: dict[str, dict[str, str]], models: Sequence[str]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates = _literal_candidates(models)
    audit: list[dict[str, Any]] = []
    affected: set[str] = set()
    metadata_injection = False
    for key in sorted(primary):
        record = primary[key]
        text = record.get("serialized_text")
        if record.get("input_view") != "primary_with_natural_errors" or not isinstance(text, str):
            raise IntegrityError(f"invalid primary serialized record: {key}")
        if key in text:
            metadata_injection = True
        found: Counter[tuple[str, str, str, str]] = Counter()
        current = "unclassified_serializer_text"
        for line in text.splitlines():
            current = _line_source_field(line, current)
            folded = line.casefold()
            for matched_model, literal, match_type in candidates:
                count = folded.count(literal.casefold())
                if count:
                    found[(matched_model, literal, match_type, current)] += count
        if found:
            affected.add(key)
            for (matched_model, literal, match_type, source_field), count in sorted(found.items()):
                if source_field in {"unclassified_serializer_text", "step", "terminal"}:
                    metadata_injection = True
                audit.append({
                    "trajectory_key": key, "model_name": index[key]["model_name"],
                    "matched_model_name": matched_model, "matched_literal": literal,
                    "match_type": match_type, "source_field": source_field,
                    "occurrence_count": count, "review_status": "natural_text_match_reported",
                })
        else:
            audit.append({
                "trajectory_key": key, "model_name": index[key]["model_name"],
                "matched_model_name": "", "matched_literal": "", "match_type": "none",
                "source_field": "none", "occurrence_count": 0,
                "review_status": "no_model_literal",
            })
    if metadata_injection:
        raise IntegrityError("model identity was injected by metadata or serializer")
    summary = {
        "trajectory_count": len(primary), "audit_row_count": len(audit),
        "affected_trajectory_count": len(affected),
        "literal_occurrence_count": sum(int(row["occurrence_count"]) for row in audit),
        "metadata_or_serializer_injection_detected": False,
        "redaction_performed": False,
        "candidate_rules": "exact manifest model plus unique aliases derived from manifest strings",
    }
    return audit, summary


def _sample(row: dict[str, Any]) -> splitter.Sample:
    original, normalized = str(row["group_key"]).split("::", 1)
    return splitter.Sample(
        trajectory_key=str(row["trajectory_key"]), group_key=str(row["group_key"]),
        target=str(row["target"]), label=int(row["label"]), benchmark_original=original,
        benchmark_group_primary=str(row["benchmark_group_primary"]),
        benchmark_group_secondary=str(row["benchmark_group_secondary"]),
        normalized_task_id=normalized, model_name=str(row["model_name"]), official_split="dev",
    )


INNER_FIELDS = [
    "protocol", "trajectory_key", "target", "label", "held_out_model", "role",
    "inner_fold", "inner_n_splits", "benchmark_group_primary",
    "benchmark_group_secondary", "group_key", "model_name",
]


def generate_inner_folds(
    config: dict[str, Any], manifest: Sequence[dict[str, str]], models: Sequence[str]
) -> list[dict[str, Any]]:
    """Generate deterministic grouped inner OOF assignments on three models only."""

    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for heldout in models:
            cell = [row for row in manifest if row["target"] == target and row["held_out_model"] == heldout]
            train = [row for row in cell if row["role"] == "train"]
            samples = [_sample(row) for row in train]
            namespace = config["inner_folds"]["namespace_template"].format(
                target=target, held_out_model=heldout
            )
            n_splits, assignment = splitter.choose_max_feasible(
                samples, config["inner_folds"]["candidates"], config["inner_folds"]["seed"], namespace
            )
            if not splitter.validate_assignment(samples, assignment, n_splits):
                raise IntegrityError(f"generated invalid inner assignment: {target}/{heldout}")
            for row in sorted(cell, key=lambda item: item["trajectory_key"]):
                role = "external_validation" if row["role"] == "validation" else "train"
                fold: int | str = "" if role == "external_validation" else assignment[row["group_key"]] + 1
                output.append({
                    "protocol": "leave_one_model_out", "trajectory_key": row["trajectory_key"],
                    "target": target, "label": int(row["label"]), "held_out_model": heldout,
                    "role": role, "inner_fold": fold, "inner_n_splits": n_splits,
                    "benchmark_group_primary": row["benchmark_group_primary"],
                    "benchmark_group_secondary": row["benchmark_group_secondary"],
                    "group_key": row["group_key"], "model_name": row["model_name"],
                })
    if len(output) != len(manifest):
        raise IntegrityError("inner-fold artifact does not mirror LOMO manifest")
    return output


def validate_inner_folds(
    config: dict[str, Any], rows: Sequence[dict[str, Any]], models: Sequence[str]
) -> dict[str, dict[str, int]]:
    if len(rows) != config["execution"]["expected_external_prediction_rows"]:
        raise IntegrityError(f"inner-fold artifact has {len(rows)} rows, expected 2332")
    result: dict[str, dict[str, int]] = {target: {} for target in TARGETS}
    for target in TARGETS:
        for heldout in models:
            cell = [row for row in rows if row["target"] == target and row["held_out_model"] == heldout]
            n_values = {int(row["inner_n_splits"]) for row in cell}
            if len(n_values) != 1:
                raise IntegrityError("cell has multiple inner-fold counts")
            n_splits = n_values.pop()
            train = [row for row in cell if row["role"] == "train"]
            external = [row for row in cell if row["role"] == "external_validation"]
            if any(str(row["inner_fold"]).strip() for row in external):
                raise IntegrityError("external validation row has an inner fold")
            if any(row["model_name"] == heldout for row in train) or any(row["model_name"] != heldout for row in external):
                raise IntegrityError("held-out model entered frozen inner training")
            by_group: dict[str, set[int]] = defaultdict(set)
            for row in train:
                by_group[str(row["group_key"])].add(int(row["inner_fold"]))
            if {len(value) for value in by_group.values()} != {1}:
                raise IntegrityError("group_key crosses inner folds")
            samples = [_sample(row) for row in train]
            assignment = {str(row["group_key"]): int(row["inner_fold"]) - 1 for row in train}
            if not splitter.validate_assignment(samples, assignment, n_splits):
                raise IntegrityError(f"frozen inner assignment invalid: {target}/{heldout}")
            namespace = config["inner_folds"]["namespace_template"].format(
                target=target, held_out_model=heldout
            )
            expected_n, expected_assignment = splitter.choose_max_feasible(
                samples, config["inner_folds"]["candidates"], config["inner_folds"]["seed"], namespace
            )
            if n_splits != expected_n or assignment != expected_assignment:
                raise IntegrityError("inner folds do not use the maximum feasible deterministic assignment")
            result[target][heldout] = n_splits
    return result


def preflight(config: dict[str, Any]) -> dict[str, Any]:
    """Run every real-dev guard without fitting any estimator or reading test."""

    verified = verify_frozen_hashes(config)
    commits = verify_source_commits(config)
    environment = verify_environment(config)
    index, labels = _label_index(config)
    primary = read_jsonl(resolve(config["inputs"]["primary"]["path"]))
    if len(primary) != 196 or set(primary) != set(index):
        raise IntegrityError("primary input is not exactly the 196-row dev index")
    manifest, models, stats, overlap, coverage = validate_lomo_manifest(config, labels, index)
    literal_rows, literal_summary = audit_model_literals(primary, index, models)
    return {
        "verified_hashes": verified, "verified_commits": commits, "environment": environment,
        "index": index, "labels": labels, "primary": primary, "manifest": manifest,
        "models": models, "stats": stats, "overlap": overlap, "coverage": coverage,
        "literal_rows": literal_rows, "literal_summary": literal_summary,
    }


def write_prerun(config: dict[str, Any]) -> None:
    checked = preflight(config)
    write_csv(resolve(config["outputs"]["coverage_matrix"]), checked["coverage"], list(checked["coverage"][0]))
    write_csv(resolve(config["outputs"]["model_literal_audit"]), checked["literal_rows"], LITERAL_FIELDS)
    folds = generate_inner_folds(config, checked["manifest"], checked["models"])
    write_csv(resolve(config["inner_folds"]["path"]), folds, INNER_FIELDS)
    counts = validate_inner_folds(config, folds, checked["models"])
    prereg_paths = {
        "script_sha256": Path(__file__).resolve(),
        "config_sha256": CONFIG_PATH,
        "inner_folds_sha256": resolve(config["inner_folds"]["path"]),
        "coverage_matrix_sha256": resolve(config["outputs"]["coverage_matrix"]),
        "model_literal_audit_sha256": resolve(config["outputs"]["model_literal_audit"]),
    }
    integrity = {
        "stage": "A1.4a", "status": "PASS", "generated_at_utc": utc_now(),
        "real_dev_estimator_fit_count": 0, "prediction_count": 0,
        "verified_hashes": checked["verified_hashes"], "verified_commits": checked["verified_commits"],
        "environment": checked["environment"], "model_names": checked["models"],
        "held_out_statistics": checked["stats"], "external_group_key_overlap": checked["overlap"],
        "inner_fold_counts": counts, "model_literal_audit": checked["literal_summary"],
        "coverage_matrix_rows": len(checked["coverage"]),
        "partial_coverage_models": [
            model for model in checked["models"]
            if checked["stats"][TARGETS[0]][model]["coverage_status"] == "partial_primary_benchmark_coverage"
        ],
        **{key: a12.sha256_path(path) for key, path in prereg_paths.items()},
        "test_access": {"manifest": 0, "trajectory_content": 0, "labels": 0, "predictions": 0, "metrics": 0},
        "forbidden_experiments_executed": [],
    }
    write_json(resolve(config["environment"]["prerun_integrity_artifact"]), integrity)
    print(json.dumps({
        "status": "PASS", "mode": "write-prerun", "model_names": checked["models"],
        "inner_fold_counts": counts, "real_dev_estimator_fit_count": 0, "predictions": 0,
    }))


def assert_clean_preregistration(config: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    status = str(git_output(["status", "--porcelain=v1"])).strip()
    if status:
        raise IntegrityError(f"formal run requires a clean worktree; found: {status}")
    subject = str(git_output(["show", "-s", "--format=%s", "HEAD"])).strip()
    if subject != config["execution"]["required_preregistration_commit_subject"]:
        raise IntegrityError(f"HEAD is not the A1.4a preregistration commit: {subject}")
    commit = str(git_output(["rev-parse", "HEAD"])).strip()
    integrity_path = resolve(config["environment"]["prerun_integrity_artifact"])
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    paths = {
        "script_sha256": Path(__file__).resolve(),
        "config_sha256": CONFIG_PATH,
        "inner_folds_sha256": resolve(config["inner_folds"]["path"]),
        "coverage_matrix_sha256": resolve(config["outputs"]["coverage_matrix"]),
        "model_literal_audit_sha256": resolve(config["outputs"]["model_literal_audit"]),
    }
    for key, path in paths.items():
        if integrity[key] != a12.sha256_path(path):
            raise IntegrityError(f"working {path.name} differs from the preregistered hash")
        relative = path.relative_to(REPO_ROOT).as_posix()
        if git_output(["show", f"HEAD:{relative}"], text=False) != path.read_bytes():
            raise IntegrityError(f"working {path.name} differs from committed A1.4a bytes")
    if integrity["real_dev_estimator_fit_count"] != 0 or integrity["prediction_count"] != 0:
        raise IntegrityError("A1.4a is not a zero-fit, zero-prediction preregistration")
    return commit, integrity


def _features_by_key(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = read_csv(resolve(config["inputs"]["structural_features"]["path"]))
    result = {row["trajectory_key"]: row for row in rows}
    if len(result) != len(rows) or list(rows[0]) != ["trajectory_key", *FEATURE_NAMES, "content_sha256"]:
        raise IntegrityError("frozen structural feature schema changed")
    return result


def _assert_fit_isolation(
    checked: dict[str, Any], heldout: str, train_keys: Sequence[str], validation_keys: Sequence[str],
    final_external: bool,
) -> None:
    index = checked["index"]
    if any(index[key]["model_name"] == heldout for key in train_keys):
        raise IntegrityError("held-out model entered estimator/preprocessor/class-weight fit")
    if final_external:
        if any(index[key]["model_name"] != heldout for key in validation_keys):
            raise IntegrityError("external validation includes a non-held-out model")
    elif any(index[key]["model_name"] == heldout for key in validation_keys):
        raise IntegrityError("held-out model entered inner configuration/threshold selection")


def fit_predict(
    config: dict[str, Any], checked: dict[str, Any], baseline: str, candidate: dict[str, Any],
    heldout: str, train_keys: Sequence[str], validation_keys: Sequence[str], labels: dict[str, int],
    structural: dict[str, dict[str, str]], context: dict[str, Any], warnings_out: list[dict[str, Any]],
    final_external: bool,
) -> np.ndarray:
    _assert_fit_isolation(checked, heldout, train_keys, validation_keys, final_external)
    return a13.fit_predict(
        config, baseline, candidate, train_keys, validation_keys, labels, structural,
        checked["primary"], context, warnings_out,
    )


def _model_metric_row(
    target: str, baseline: str, heldout: str, rows: Sequence[dict[str, Any]],
    selected_config: str, threshold: float, n_splits: int, task_groups: int,
    coverage_status: str,
) -> dict[str, Any]:
    truth = [int(row["true_label"]) for row in rows]
    probability = [float(row["predicted_probability"]) for row in rows]
    predicted = [int(row["predicted_label"]) for row in rows]
    positives = sum(truth)
    negatives = len(truth) - positives
    if not positives or not negatives:
        raise IntegrityError(f"LOMO external model cell is single-class: {target}/{heldout}")
    result: dict[str, Any] = {
        "target": target, "baseline_id": baseline, "held_out_model": heldout,
        "coverage_status": coverage_status, "trajectory_count": len(rows),
        "task_group_count": task_groups, "negative_count": negatives,
        "positive_count": positives, "prevalence": positives / len(rows),
        "predicted_positive_count": sum(predicted),
        "predicted_positive_rate": sum(predicted) / len(rows),
        "selected_config_id": selected_config, "selected_threshold": threshold,
        "inner_n_splits": n_splits, "metric_status": "ok",
    }
    result.update(a12.metrics(truth, probability, predicted))
    result["ap_lift"] = result["pr_auc_average_precision"] - result["prevalence"]
    result["ap_vs_best_dummy"] = None
    result["f1_vs_best_dummy"] = None
    return result


MODEL_METRIC_FIELDS = [
    "target", "baseline_id", "held_out_model", "coverage_status", "trajectory_count",
    "task_group_count", "negative_count", "positive_count", "prevalence",
    "predicted_positive_count", "predicted_positive_rate", "selected_config_id",
    "selected_threshold", "inner_n_splits", "metric_status", *METRIC_NAMES,
    "ap_lift", "ap_vs_best_dummy", "f1_vs_best_dummy",
]


def _augment_dummy_deltas(rows: list[dict[str, Any]], models: Sequence[str]) -> None:
    for target in TARGETS:
        for model in models:
            cell = [row for row in rows if row["target"] == target and row["held_out_model"] == model]
            dummy_ap = max(float(row["pr_auc_average_precision"]) for row in cell if row["baseline_id"] in {"B0", "B1"})
            dummy_f1 = max(float(row["positive_f1"]) for row in cell if row["baseline_id"] in {"B0", "B1"})
            for row in cell:
                if row["baseline_id"] in {"B2", "B3"}:
                    row["ap_vs_best_dummy"] = float(row["pr_auc_average_precision"]) - dummy_ap
                    row["f1_vs_best_dummy"] = float(row["positive_f1"]) - dummy_f1


def _diagnostic_rows(
    config: dict[str, Any], predictions: Sequence[dict[str, Any]], models: Sequence[str]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            for model in models:
                for benchmark in config["primary_benchmarks"]:
                    cell = [
                        row for row in predictions
                        if row["target"] == target and row["baseline_id"] == baseline
                        and row["held_out_model"] == model
                        and row["benchmark_group_primary"] == benchmark
                    ]
                    if not cell:
                        output.append({
                            "target": target, "baseline_id": baseline, "held_out_model": model,
                            "benchmark_group_primary": benchmark, "n": 0, "negative_count": 0,
                            "positive_count": 0, "prevalence": None, "metric_status": "no_coverage",
                            "pr_auc_average_precision": None, "positive_f1": None,
                            "predicted_positive_count": 0, "probability_mean": None,
                            "probability_median": None, "probability_max": None,
                        })
                        continue
                    truth = [int(row["true_label"]) for row in cell]
                    probability = [float(row["predicted_probability"]) for row in cell]
                    predicted = [int(row["predicted_label"]) for row in cell]
                    positives = sum(truth)
                    negatives = len(truth) - positives
                    mixed = positives > 0 and negatives > 0
                    output.append({
                        "target": target, "baseline_id": baseline, "held_out_model": model,
                        "benchmark_group_primary": benchmark, "n": len(cell),
                        "negative_count": negatives, "positive_count": positives,
                        "prevalence": positives / len(cell),
                        "metric_status": "ok" if mixed else ("single_class_positive" if positives else "single_class_negative"),
                        "pr_auc_average_precision": float(average_precision_score(truth, probability)) if mixed else None,
                        "positive_f1": a12.metrics(truth, probability, predicted)["positive_f1"] if mixed else None,
                        "predicted_positive_count": sum(predicted),
                        "probability_mean": float(np.mean(probability)),
                        "probability_median": float(np.median(probability)),
                        "probability_max": float(np.max(probability)),
                    })
    return output


DIAGNOSTIC_FIELDS = [
    "target", "baseline_id", "held_out_model", "benchmark_group_primary", "n",
    "negative_count", "positive_count", "prevalence", "metric_status",
    "pr_auc_average_precision", "positive_f1", "predicted_positive_count",
    "probability_mean", "probability_median", "probability_max",
]


def _macro_rows(model_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            all_models = [row for row in model_rows if row["target"] == target and row["baseline_id"] == baseline]
            full = [row for row in all_models if row["coverage_status"] == "full_primary_benchmark_coverage"]
            partial = [row for row in all_models if row["coverage_status"] == "partial_primary_benchmark_coverage"]
            if not all_models:
                continue
            if len(all_models) != 4 or len(full) < 2:
                raise IntegrityError("model macro lacks four total or two full-coverage models")
            row: dict[str, Any] = {
                "target": target, "baseline_id": baseline, "all_model_count": len(all_models),
                "full_coverage_model_count": len(full), "partial_coverage_model_count": len(partial),
            }
            for metric in [*METRIC_NAMES, "ap_lift"]:
                all_values = [float(item[metric]) for item in all_models]
                full_values = [float(item[metric]) for item in full]
                row[f"{metric}_all_model_macro_mean"] = statistics.mean(all_values)
                row[f"{metric}_all_model_macro_std"] = statistics.stdev(all_values)
                row[f"{metric}_full_coverage_macro_mean"] = statistics.mean(full_values)
                row[f"{metric}_full_coverage_macro_std"] = statistics.stdev(full_values)
            output.append(row)
    return output


def _pooled_rows(predictions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            cell = [row for row in predictions if row["target"] == target and row["baseline_id"] == baseline]
            truth = [int(row["true_label"]) for row in cell]
            probability = [float(row["predicted_probability"]) for row in cell]
            predicted = [int(row["predicted_label"]) for row in cell]
            prevalence = sum(truth) / len(truth)
            row = {
                "target": target, "baseline_id": baseline, "sample_count": len(cell),
                "positive_count": sum(truth), "negative_count": len(truth) - sum(truth),
                "prevalence": prevalence,
            }
            row.update(a12.metrics(truth, probability, predicted))
            row["ap_lift"] = row["pr_auc_average_precision"] - prevalence
            output.append(row)
    return output


def _comparison_rows(
    config: dict[str, Any], current_model: Sequence[dict[str, Any]],
    current_macro: Sequence[dict[str, Any]], current_pooled: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    a12_rows = read_csv(resolve(config["a1_2_contract"]["pooled_metrics"]["path"]))
    a13_rows = read_csv(resolve(config["a1_3_contract"]["pooled_metrics"]["path"]))
    output: list[dict[str, Any]] = []
    for target in TARGETS:
        for baseline in BASELINE_IDS:
            current = next(row for row in current_pooled if row["target"] == target and row["baseline_id"] == baseline)
            prior12 = next(row for row in a12_rows if row["target"] == target and row["baseline_id"] == baseline)
            prior13 = next(row for row in a13_rows if row["target"] == target and row["baseline_id"] == baseline)
            models = [row for row in current_model if row["target"] == target and row["baseline_id"] == baseline]
            full = [row for row in models if row["coverage_status"] == "full_primary_benchmark_coverage"]
            macro = next(row for row in current_macro if row["target"] == target and row["baseline_id"] == baseline)
            best_ap = max(models, key=lambda row: float(row["pr_auc_average_precision"]))
            worst_ap = min(models, key=lambda row: float(row["pr_auc_average_precision"]))
            best_f1 = max(models, key=lambda row: float(row["positive_f1"]))
            worst_f1 = min(models, key=lambda row: float(row["positive_f1"]))
            worst_full_ap = min(full, key=lambda row: float(row["pr_auc_average_precision"]))
            worst_full_f1 = min(full, key=lambda row: float(row["positive_f1"]))
            current_ap = float(current["pr_auc_average_precision"])
            current_f1 = float(current["positive_f1"])
            a12_ap, a12_f1 = float(prior12["pooled_pr_auc_average_precision"]), float(prior12["pooled_positive_f1"])
            a13_ap, a13_f1 = float(prior13["pr_auc_average_precision"]), float(prior13["positive_f1"])
            output.append({
                "target": target, "baseline_id": baseline,
                "a1_2_task_grouped_pooled_ap": a12_ap, "a1_2_task_grouped_pooled_f1": a12_f1,
                "a1_3_benchmark_held_out_pooled_ap": a13_ap, "a1_3_benchmark_held_out_pooled_f1": a13_f1,
                "a1_4_model_held_out_pooled_ap": current_ap, "a1_4_model_held_out_pooled_f1": current_f1,
                "ap_delta_a1_4_minus_a1_2": current_ap - a12_ap,
                "f1_delta_a1_4_minus_a1_2": current_f1 - a12_f1,
                "ap_delta_a1_4_minus_a1_3": current_ap - a13_ap,
                "f1_delta_a1_4_minus_a1_3": current_f1 - a13_f1,
                "best_model_ap": best_ap["held_out_model"], "best_model_ap_value": best_ap["pr_auc_average_precision"],
                "worst_model_ap": worst_ap["held_out_model"], "worst_model_ap_value": worst_ap["pr_auc_average_precision"],
                "best_model_f1": best_f1["held_out_model"], "best_model_f1_value": best_f1["positive_f1"],
                "worst_model_f1": worst_f1["held_out_model"], "worst_model_f1_value": worst_f1["positive_f1"],
                "model_ap_sample_std": macro["pr_auc_average_precision_all_model_macro_std"],
                "model_f1_sample_std": macro["positive_f1_all_model_macro_std"],
                "worst_full_coverage_model_ap": worst_full_ap["held_out_model"],
                "worst_full_coverage_model_ap_value": worst_full_ap["pr_auc_average_precision"],
                "worst_full_coverage_model_f1": worst_full_f1["held_out_model"],
                "worst_full_coverage_model_f1_value": worst_full_f1["positive_f1"],
            })
    return output


def _signal_grades(
    model_rows: Sequence[dict[str, Any]], pooled_rows: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for target in TARGETS:
        full_models = sorted({
            row["held_out_model"] for row in model_rows
            if row["target"] == target and row["coverage_status"] == "full_primary_benchmark_coverage"
        })
        if len(full_models) < 2:
            output[target] = {"grade": "not_assessable", "full_coverage_model_count": len(full_models)}
            continue
        pooled = {row["baseline_id"]: row for row in pooled_rows if row["target"] == target}
        pooled_dummy_f1 = max(float(pooled["B0"]["positive_f1"]), float(pooled["B1"]["positive_f1"]))
        details: dict[str, Any] = {}
        qualifying: list[str] = []
        any_signal = False
        for baseline in ["B2", "B3"]:
            learned = [row for row in model_rows if row["target"] == target and row["baseline_id"] == baseline]
            full = [row for row in learned if row["held_out_model"] in full_models]
            partial = [row for row in learned if row["held_out_model"] not in full_models]
            pooled_pass = (
                float(pooled[baseline]["pr_auc_average_precision"]) > float(pooled[baseline]["prevalence"])
                and float(pooled[baseline]["positive_f1"]) > pooled_dummy_f1
            )
            full_pass = all(float(row["ap_lift"]) > 0 and float(row["f1_vs_best_dummy"]) > 0 for row in full)
            partial_no_reverse = all(
                float(row["ap_lift"]) >= 0 or float(row["f1_vs_best_dummy"]) >= 0 for row in partial
            )
            robust = pooled_pass and full_pass and partial_no_reverse
            any_model_both = sum(float(row["ap_lift"]) > 0 and float(row["f1_vs_best_dummy"]) > 0 for row in learned)
            any_signal = any_signal or pooled_pass or any_model_both > 0
            details[baseline] = {
                "pooled_pass": pooled_pass, "all_full_coverage_models_pass": full_pass,
                "partial_coverage_no_reverse_collapse": partial_no_reverse,
                "models_with_ap_and_f1_improvement": any_model_both, "robust": robust,
            }
            if robust:
                qualifying.append(baseline)
        if qualifying:
            grade = "robust_cross_model_signal"
        elif any_signal:
            grade = "partial_or_model_specific_signal"
        else:
            grade = "no_cross_model_signal"
        output[target] = {
            "grade": grade, "full_coverage_model_count": len(full_models),
            "qualifying_baselines": qualifying, "details": details,
        }
    return output


def run_models(
    config: dict[str, Any], checked: dict[str, Any], run_id: str, prereg_commit: str,
    prereg_integrity: dict[str, Any], started_at_utc: str,
) -> dict[str, Any]:
    models = checked["models"]
    frozen_folds = read_csv(resolve(config["inner_folds"]["path"]))
    inner_counts = validate_inner_folds(config, frozen_folds, models)
    structural = _features_by_key(config)
    warnings_out: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    inner_selected_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    selected_configs: Counter[tuple[str, str, str]] = Counter()
    selected_thresholds: Counter[tuple[str, str, float]] = Counter()

    for target in TARGETS:
        labels = checked["labels"][target]
        for heldout in models:
            cell = [row for row in frozen_folds if row["target"] == target and row["held_out_model"] == heldout]
            train_rows = [row for row in cell if row["role"] == "train"]
            held_rows = [row for row in cell if row["role"] == "external_validation"]
            n_splits = inner_counts[target][heldout]
            train_keys_all = [row["trajectory_key"] for row in train_rows]
            held_keys = [row["trajectory_key"] for row in held_rows]
            coverage_status = checked["stats"][target][heldout]["coverage_status"]
            for baseline in BASELINE_IDS:
                candidate_probability: dict[str, dict[str, float]] = {}
                candidates = a12.candidate_configs(config, baseline)
                start = len(config_rows)
                for rank, candidate in enumerate(candidates, 1):
                    oof: dict[str, float] = {}
                    for fold in range(1, n_splits + 1):
                        validation_keys = [row["trajectory_key"] for row in train_rows if int(row["inner_fold"]) == fold]
                        fit_keys = [row["trajectory_key"] for row in train_rows if int(row["inner_fold"]) != fold]
                        probability = fit_predict(
                            config, checked, baseline, candidate, heldout, fit_keys, validation_keys,
                            labels, structural,
                            {"target": target, "baseline_id": baseline, "held_out_model": heldout,
                             "phase": "inner", "inner_fold": fold},
                            warnings_out, False,
                        )
                        for key, value in zip(validation_keys, probability, strict=True):
                            if key in oof:
                                raise IntegrityError("duplicate inner OOF prediction")
                            oof[key] = float(value)
                    if set(oof) != set(train_keys_all):
                        raise IntegrityError("inner OOF predictions are incomplete")
                    score = float(average_precision_score(
                        [labels[key] for key in train_keys_all], [oof[key] for key in train_keys_all]
                    ))
                    config_rows.append({
                        "target": target, "held_out_model": heldout, "baseline_id": baseline,
                        "config_id": candidate["config_id"], "inner_n_splits": n_splits,
                        "inner_oof_size": len(oof), "inner_oof_pr_auc": score,
                        "selected": False, "tie_break_rank": rank,
                    })
                    candidate_probability[candidate["config_id"]] = oof
                candidate_rows = config_rows[start:]
                best_score = max(float(row["inner_oof_pr_auc"]) for row in candidate_rows)
                selected_row = min(
                    (row for row in candidate_rows if math.isclose(float(row["inner_oof_pr_auc"]), best_score, rel_tol=0, abs_tol=1e-15)),
                    key=lambda row: int(row["tie_break_rank"]),
                )
                selected_row["selected"] = True
                selected_id = selected_row["config_id"]
                selected_candidate = next(row for row in candidates if row["config_id"] == selected_id)
                selected_configs[(target, baseline, selected_id)] += 1
                selected_oof = candidate_probability[selected_id]
                threshold, tested = a12.select_threshold(
                    config, [labels[key] for key in train_keys_all],
                    [selected_oof[key] for key in train_keys_all],
                )
                selected_thresholds[(target, baseline, threshold)] += 1
                fold_by_key = {row["trajectory_key"]: int(row["inner_fold"]) for row in train_rows}
                for key in train_keys_all:
                    inner_selected_rows.append({
                        "trajectory_key": key, "target": target, "baseline_id": baseline,
                        "held_out_model": heldout, "inner_fold": fold_by_key[key],
                        "true_label": labels[key], "predicted_probability": selected_oof[key],
                        "selected_config_id": selected_id, "inner_n_splits": n_splits,
                    })
                for threshold_row in tested:
                    threshold_rows.append({
                        "target": target, "held_out_model": heldout, "baseline_id": baseline,
                        "selected_config_id": selected_id, **threshold_row,
                    })
                external_probability = fit_predict(
                    config, checked, baseline, selected_candidate, heldout, train_keys_all,
                    held_keys, labels, structural,
                    {"target": target, "baseline_id": baseline, "held_out_model": heldout,
                     "phase": "final_refit", "inner_fold": ""},
                    warnings_out, True,
                )
                held_by_key = {row["trajectory_key"]: row for row in held_rows}
                external_rows: list[dict[str, Any]] = []
                for key, probability in zip(held_keys, external_probability, strict=True):
                    source = held_by_key[key]
                    out = {
                        "trajectory_key": key, "group_key": source["group_key"], "target": target,
                        "baseline_id": baseline, "held_out_model": heldout,
                        "benchmark_group_primary": source["benchmark_group_primary"],
                        "true_label": labels[key], "predicted_probability": float(probability),
                        "selected_threshold": threshold,
                        "predicted_label": int(float(probability) >= threshold),
                        "selected_config_id": selected_id, "inner_n_splits": n_splits,
                        "coverage_status": coverage_status,
                    }
                    predictions.append(out)
                    external_rows.append(out)
                model_rows.append(_model_metric_row(
                    target, baseline, heldout, external_rows, selected_id, threshold,
                    n_splits, len({row["group_key"] for row in held_rows}), coverage_status,
                ))

    _augment_dummy_deltas(model_rows, models)
    diagnostic_rows = _diagnostic_rows(config, predictions, models)
    macro_rows = _macro_rows(model_rows)
    pooled_rows = _pooled_rows(predictions)
    comparison_rows = _comparison_rows(config, model_rows, macro_rows, pooled_rows)
    signal_grades = _signal_grades(model_rows, pooled_rows)
    frequency_rows = [
        {"target": target, "baseline_id": baseline, "config_id": candidate["config_id"],
         "selected_held_out_model_count": selected_configs[(target, baseline, candidate["config_id"])]}
        for target in TARGETS for baseline in BASELINE_IDS
        for candidate in a12.candidate_configs(config, baseline)
    ]
    summary = {
        "stage": "A1.4", "stage_decision": "PASS_WITH_CONDITIONS", "run_id": run_id,
        "started_at_utc": started_at_utc, "completed_at_utc": utc_now(),
        "preregistration_commit": prereg_commit,
        "experiment_commit": "recorded_after_commit", "environment": a12.environment_record(),
        "model_names": models, "held_out_statistics": checked["stats"],
        "external_group_key_overlap": checked["overlap"], "inner_fold_counts": inner_counts,
        "coverage_matrix_rows": len(checked["coverage"]),
        "partial_coverage_models": [
            model for model in models
            if checked["stats"][TARGETS[0]][model]["coverage_status"] == "partial_primary_benchmark_coverage"
        ],
        "model_literal_audit": checked["literal_summary"],
        "row_counts": {
            "inner_config_selection": len(config_rows),
            "inner_selected_oof_predictions": len(inner_selected_rows),
            "threshold_selection": len(threshold_rows), "external_predictions": len(predictions),
            "model_metrics": len(model_rows), "model_benchmark_diagnostics": len(diagnostic_rows),
            "macro_metrics": len(macro_rows), "pooled_metrics": len(pooled_rows),
            "comparison": len(comparison_rows),
        },
        "warning_count": len(warnings_out),
        "convergence_warning_count": sum(bool(row["is_convergence_warning"]) for row in warnings_out),
        "warnings": warnings_out, "signal_grades": signal_grades,
        "test_access": {"manifest": 0, "trajectory_content": 0, "labels": 0, "predictions": 0, "metrics": 0},
        "network_access": 0, "gpu_used": False, "forbidden_experiments_executed": [],
        "hashes_before_run": checked["verified_hashes"],
        "hashes_after_run": verify_frozen_hashes(config),
        "preregistered_a1_4_hashes": {
            key: prereg_integrity[key] for key in [
                "script_sha256", "config_sha256", "inner_folds_sha256",
                "coverage_matrix_sha256", "model_literal_audit_sha256",
            ]
        },
        "conditions": [
            "One model has partial primary-Benchmark coverage (missing VisualWebArena).",
            "External train and validation intentionally share group_key values; this is model-only, not joint task/model OOD.",
            "Side Effect has only 12 positives overall.",
            "LOMO is an exploratory analysis and cannot establish simultaneous cross-task and cross-model generalization.",
        ] + (["Natural task/trajectory text contains model literals; no redaction was performed."]
             if checked["literal_summary"]["affected_trajectory_count"] else []),
        "selected_config_distribution": [
            {"target": key[0], "baseline_id": key[1], "config_id": key[2], "count": count}
            for key, count in sorted(selected_configs.items())
        ],
        "selected_threshold_distribution": [
            {"target": key[0], "baseline_id": key[1], "threshold": key[2], "count": count}
            for key, count in sorted(selected_thresholds.items())
        ],
    }
    paths = config["outputs"]
    write_csv(resolve(paths["inner_config_selection"]), config_rows,
              ["target", "held_out_model", "baseline_id", "config_id", "inner_n_splits", "inner_oof_size", "inner_oof_pr_auc", "selected", "tie_break_rank"])
    write_csv(resolve(paths["inner_selected_oof_predictions"]), inner_selected_rows,
              ["trajectory_key", "target", "baseline_id", "held_out_model", "inner_fold", "true_label", "predicted_probability", "selected_config_id", "inner_n_splits"])
    write_csv(resolve(paths["threshold_selection"]), threshold_rows,
              ["target", "held_out_model", "baseline_id", "selected_config_id", "threshold", "inner_f1", "inner_precision", "inner_recall", "selected"])
    write_csv(resolve(paths["predictions"]), predictions,
              ["trajectory_key", "group_key", "target", "baseline_id", "held_out_model", "benchmark_group_primary", "true_label", "predicted_probability", "selected_threshold", "predicted_label", "selected_config_id", "inner_n_splits", "coverage_status"])
    write_csv(resolve(paths["model_metrics"]), model_rows, MODEL_METRIC_FIELDS)
    write_csv(resolve(paths["model_benchmark_diagnostics"]), diagnostic_rows, DIAGNOSTIC_FIELDS)
    macro_fields = [
        "target", "baseline_id", "all_model_count", "full_coverage_model_count",
        "partial_coverage_model_count",
        *[field for metric in [*METRIC_NAMES, "ap_lift"] for field in (
            f"{metric}_all_model_macro_mean", f"{metric}_all_model_macro_std",
            f"{metric}_full_coverage_macro_mean", f"{metric}_full_coverage_macro_std",
        )],
    ]
    write_csv(resolve(paths["macro_metrics"]), macro_rows, macro_fields)
    write_csv(resolve(paths["pooled_metrics"]), pooled_rows,
              ["target", "baseline_id", "sample_count", "positive_count", "negative_count", "prevalence", *METRIC_NAMES, "ap_lift"])
    write_csv(resolve(paths["config_frequency"]), frequency_rows,
              ["target", "baseline_id", "config_id", "selected_held_out_model_count"])
    write_csv(resolve(paths["comparison"]), comparison_rows, list(comparison_rows[0]))
    write_json(resolve(paths["run_summary"]), summary)
    return {
        "summary": summary, "model": model_rows, "diagnostics": diagnostic_rows,
        "macro": macro_rows, "pooled": pooled_rows, "comparison": comparison_rows,
    }


def _fmt(value: Any) -> str:
    return "" if value is None or value == "" else f"{float(value):.6f}"


def render_report(config: dict[str, Any], result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# Stage A1.4 Leave-One-Model-Out report", "", "## Stage determination", "",
        "`PASS_WITH_CONDITIONS`", "",
        "All technical completeness and isolation checks passed. The determination remains conditional because one model has partial Benchmark coverage, external train/validation intentionally share tasks, Side Effect has only 12 positives, and LOMO is exploratory.", "",
        "## Scope and provenance", "",
        f"- A1.4a preregistration commit: `{summary['preregistration_commit']}`",
        "- A1.4b experiment commit: recorded by the enclosing result commit.",
        "- Official dev; B0-B3; primary_with_natural_errors only.",
        "- test access: 0 in every category; prohibited experiments executed: 0.",
        "- This is model-only holdout. It is not joint task/model OOD because external train and validation intentionally share group_key.", "",
        "## Exact held-out models", "",
    ]
    lines.extend(f"- `{model}`" for model in summary["model_names"])
    lines.extend(["", "## Coverage and external class/group statistics", "",
                  "| Target | Held-out model | coverage | train n/neg/pos | valid n/tasks/neg/pos | overlap groups | valid-only groups | counterpart rate | inner folds |",
                  "|---|---|---|---:|---:|---:|---:|---:|---:|"])
    for target in TARGETS:
        for model in summary["model_names"]:
            stat = summary["held_out_statistics"][target][model]
            lines.append(
                f"| {target} | `{model}` | {stat['coverage_status']} | "
                f"{stat['train_samples']}/{stat['train_negative']}/{stat['train_positive']} | "
                f"{stat['validation_samples']}/{stat['validation_task_groups']}/{stat['validation_negative']}/{stat['validation_positive']} | "
                f"{stat['overlap_group_count']} | {stat['validation_only_group_count']} | "
                f"{stat['validation_trajectory_counterpart_rate']:.6f} | {summary['inner_fold_counts'][target][model]} |"
            )
    lines.extend(["", "The exact Meta-Llama manifest model is the sole partial-coverage model and has no VisualWebArena trajectories. Full-coverage-model macro results therefore use the other three models.", "",
                  "## 48 held-out-model units", "",
                  "| Target | Baseline | Held-out model | coverage | n/neg/pos | prevalence | AP | AP lift | F1 | config | threshold |",
                  "|---|---|---|---|---:|---:|---:|---:|---:|---|---:|"])
    for row in result["model"]:
        lines.append(
            f"| {row['target']} | {row['baseline_id']} | `{row['held_out_model']}` | {row['coverage_status']} | "
            f"{row['trajectory_count']}/{row['negative_count']}/{row['positive_count']} | {_fmt(row['prevalence'])} | "
            f"{_fmt(row['pr_auc_average_precision'])} | {_fmt(row['ap_lift'])} | {_fmt(row['positive_f1'])} | "
            f"`{row['selected_config_id']}` | {_fmt(row['selected_threshold'])} |"
        )
    lines.extend(["", "## All-model and full-coverage-model macro", "",
                  "| Target | Baseline | models full/partial | all AP mean±std | full AP mean±std | all F1 mean±std | full F1 mean±std |",
                  "|---|---|---:|---:|---:|---:|---:|"])
    for row in result["macro"]:
        lines.append(
            f"| {row['target']} | {row['baseline_id']} | {row['full_coverage_model_count']}/{row['partial_coverage_model_count']} | "
            f"{_fmt(row['pr_auc_average_precision_all_model_macro_mean'])} ± {_fmt(row['pr_auc_average_precision_all_model_macro_std'])} | "
            f"{_fmt(row['pr_auc_average_precision_full_coverage_macro_mean'])} ± {_fmt(row['pr_auc_average_precision_full_coverage_macro_std'])} | "
            f"{_fmt(row['positive_f1_all_model_macro_mean'])} ± {_fmt(row['positive_f1_all_model_macro_std'])} | "
            f"{_fmt(row['positive_f1_full_coverage_macro_mean'])} ± {_fmt(row['positive_f1_full_coverage_macro_std'])} |"
        )
    comparison = {(row["target"], row["baseline_id"]): row for row in result["comparison"]}
    lines.extend(["", "## Pooled LOMO and A1.2/A1.3 deltas", "",
                  "| Target | Baseline | n | prevalence | LOMO AP | LOMO F1 | ΔAP vs A1.2 | ΔF1 vs A1.2 | ΔAP vs A1.3 | ΔF1 vs A1.3 |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for row in result["pooled"]:
        comp = comparison[(row["target"], row["baseline_id"])]
        lines.append(
            f"| {row['target']} | {row['baseline_id']} | {row['sample_count']} | {_fmt(row['prevalence'])} | "
            f"{_fmt(row['pr_auc_average_precision'])} | {_fmt(row['positive_f1'])} | "
            f"{float(comp['ap_delta_a1_4_minus_a1_2']):+.6f} | {float(comp['f1_delta_a1_4_minus_a1_2']):+.6f} | "
            f"{float(comp['ap_delta_a1_4_minus_a1_3']):+.6f} | {float(comp['f1_delta_a1_4_minus_a1_3']):+.6f} |"
        )
    status_counts = Counter(row["metric_status"] for row in result["diagnostics"])
    lines.extend(["", "## Model × Benchmark diagnostics", "",
                  f"The machine-readable diagnostic has {len(result['diagnostics'])} rows: `{json.dumps(dict(sorted(status_counts.items())))}`. Single-class and no-coverage cells leave AP/F1 blank; the 0-sample Meta-Llama/VisualWebArena cells are marked `no_coverage`.", "",
                  "## Configuration, threshold, literal, and warning audit", "",
                  f"- Selected configurations: `{json.dumps(summary['selected_config_distribution'], sort_keys=True)}`",
                  f"- Selected thresholds: `{json.dumps(summary['selected_threshold_distribution'], sort_keys=True)}`",
                  f"- Model literal audit: `{json.dumps(summary['model_literal_audit'], sort_keys=True)}`",
                  f"- Warnings: {summary['warning_count']} total; convergence warnings: {summary['convergence_warning_count']}.", "",
                  "## Completeness and integrity", "",
                  f"- External predictions: {summary['row_counts']['external_predictions']}/2332.",
                  f"- Selected inner OOF predictions: {summary['row_counts']['inner_selected_oof_predictions']}/6996.",
                  f"- Configuration rows: {summary['row_counts']['inner_config_selection']}/240; threshold rows: {summary['row_counts']['threshold_selection']}/912; model metrics: {summary['row_counts']['model_metrics']}/48.",
                  f"- Frozen hashes before/after identical: {summary['hashes_before_run'] == summary['hashes_after_run']}.",
                  "- test access: 0; prohibited experiments: none; network: 0; GPU: 0.", "",
                  "## Cross-model signal grades", ""])
    for target in TARGETS:
        lines.append(f"- {target}: `{summary['signal_grades'][target]['grade']}`")
    lines.extend(["", "## Interpretation and stop boundary", "",
                  "The external task overlap is expected by design: every held-out trajectory has a training-side trajectory for the same group_key from another model. Results support only exploratory cross-model generalization, not simultaneous cross-task and cross-model OOD generalization.", "",
                  "Stop after A1.4. Do not begin A1.5, ablations, fusion, complex models, or test evaluation without a new human stage-gate approval.", ""])
    return "\n".join(lines)


def _compare_numeric(expected: dict[str, Any], recorded: dict[str, str], fields: Iterable[str], label: str) -> None:
    for field in fields:
        value = expected[field]
        if value is None:
            if recorded[field] != "":
                raise IntegrityError(f"{label} missing metric was filled: {field}")
        elif not math.isclose(float(value), float(recorded[field]), rel_tol=1e-12, abs_tol=1e-12):
            raise IntegrityError(f"{label} metric cannot be reproduced: {field}")


def verify_results(config: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute selection, coverage, metrics, and frozen hashes."""

    checked = preflight(config)
    models = checked["models"]
    folds = read_csv(resolve(config["inner_folds"]["path"]))
    validate_inner_folds(config, folds, models)
    outputs = config["outputs"]
    configs = read_csv(resolve(outputs["inner_config_selection"]))
    inner = read_csv(resolve(outputs["inner_selected_oof_predictions"]))
    thresholds = read_csv(resolve(outputs["threshold_selection"]))
    predictions = read_csv(resolve(outputs["predictions"]))
    model_metrics = read_csv(resolve(outputs["model_metrics"]))
    diagnostics = read_csv(resolve(outputs["model_benchmark_diagnostics"]))
    macro = read_csv(resolve(outputs["macro_metrics"]))
    pooled = read_csv(resolve(outputs["pooled_metrics"]))
    comparison = read_csv(resolve(outputs["comparison"]))
    actual_counts = (
        len(configs), len(thresholds), len(predictions), len(inner), len(model_metrics),
        len(diagnostics), len(macro), len(pooled), len(comparison),
    )
    if actual_counts != (240, 912, 2332, 6996, 48, 192, 12, 12, 12):
        raise IntegrityError(f"formal output row counts differ from preregistration: {actual_counts}")
    if len({(row["target"], row["baseline_id"], row["trajectory_key"]) for row in predictions}) != 2332:
        raise IntegrityError("external predictions contain duplicates or omissions")
    if len({(row["target"], row["held_out_model"], row["baseline_id"], row["trajectory_key"]) for row in inner}) != 6996:
        raise IntegrityError("selected inner OOF predictions contain duplicates or omissions")
    role = {(row["target"], row["held_out_model"], row["trajectory_key"]): row["role"] for row in folds}
    if any(role[(row["target"], row["held_out_model"], row["trajectory_key"])] != "train" for row in inner):
        raise IntegrityError("held-out model appears in selected inner OOF")
    for target in TARGETS:
        for model in models:
            for baseline in BASELINE_IDS:
                selection = [row for row in configs if row["target"] == target and row["held_out_model"] == model and row["baseline_id"] == baseline]
                selected = [row for row in selection if row["selected"] == "True"]
                if len(selected) != 1:
                    raise IntegrityError("configuration selection is not unique")
                best = max(float(row["inner_oof_pr_auc"]) for row in selection)
                expected = min(
                    (row for row in selection if math.isclose(float(row["inner_oof_pr_auc"]), best, rel_tol=0, abs_tol=1e-15)),
                    key=lambda row: int(row["tie_break_rank"]),
                )
                if selected[0]["config_id"] != expected["config_id"]:
                    raise IntegrityError("configuration was not selected by pooled inner OOF AP/tie-break")
                inner_cell = [row for row in inner if row["target"] == target and row["held_out_model"] == model and row["baseline_id"] == baseline]
                if any(checked["index"][row["trajectory_key"]]["model_name"] == model for row in inner_cell):
                    raise IntegrityError("held-out model entered selected inner OOF")
                recomputed_threshold, _ = a12.select_threshold(
                    config, [int(row["true_label"]) for row in inner_cell],
                    [float(row["predicted_probability"]) for row in inner_cell],
                )
                selected_threshold = [
                    row for row in thresholds if row["target"] == target and row["held_out_model"] == model
                    and row["baseline_id"] == baseline and row["selected"] == "True"
                ]
                if len(selected_threshold) != 1 or not math.isclose(float(selected_threshold[0]["threshold"]), recomputed_threshold, abs_tol=1e-15):
                    raise IntegrityError("threshold was not selected from selected-config pooled inner OOF")
                external = [row for row in predictions if row["target"] == target and row["held_out_model"] == model and row["baseline_id"] == baseline]
                expected_keys = {
                    row["trajectory_key"] for row in folds
                    if row["target"] == target and row["held_out_model"] == model
                    and row["role"] == "external_validation"
                }
                if {row["trajectory_key"] for row in external} != expected_keys:
                    raise IntegrityError("external held-out-model prediction coverage mismatch")
                for row in external:
                    if checked["index"][row["trajectory_key"]]["model_name"] != model:
                        raise IntegrityError("external prediction is not from held-out model")
                    probability, threshold = float(row["predicted_probability"]), float(row["selected_threshold"])
                    if not math.isfinite(probability) or not 0 <= probability <= 1 or int(row["predicted_label"]) != int(probability >= threshold):
                        raise IntegrityError("invalid external probability/threshold label")
                    if int(row["true_label"]) != checked["labels"][target][row["trajectory_key"]]:
                        raise IntegrityError("external truth differs from frozen main label")
    recomputed_model: list[dict[str, Any]] = []
    for target in TARGETS:
        for model in models:
            for baseline in BASELINE_IDS:
                external = [row for row in predictions if row["target"] == target and row["held_out_model"] == model and row["baseline_id"] == baseline]
                source = next(row for row in model_metrics if row["target"] == target and row["held_out_model"] == model and row["baseline_id"] == baseline)
                recomputed_model.append(_model_metric_row(
                    target, baseline, model, external, source["selected_config_id"],
                    float(source["selected_threshold"]), int(source["inner_n_splits"]),
                    int(source["task_group_count"]), source["coverage_status"],
                ))
    _augment_dummy_deltas(recomputed_model, models)
    for expected, recorded in zip(recomputed_model, model_metrics, strict=True):
        _compare_numeric(expected, recorded, [*METRIC_NAMES, "ap_lift", "ap_vs_best_dummy", "f1_vs_best_dummy"], "model")
    recomputed_diagnostics = _diagnostic_rows(config, predictions, models)
    for expected, recorded in zip(recomputed_diagnostics, diagnostics, strict=True):
        if expected["metric_status"] != recorded["metric_status"]:
            raise IntegrityError("diagnostic status cannot be reproduced")
        _compare_numeric(expected, recorded,
                         ["prevalence", "pr_auc_average_precision", "positive_f1", "probability_mean", "probability_median", "probability_max"],
                         "diagnostic")
    recomputed_macro = _macro_rows(recomputed_model)
    macro_fields = [
        field for metric in [*METRIC_NAMES, "ap_lift"] for field in (
            f"{metric}_all_model_macro_mean", f"{metric}_all_model_macro_std",
            f"{metric}_full_coverage_macro_mean", f"{metric}_full_coverage_macro_std",
        )
    ]
    for expected, recorded in zip(recomputed_macro, macro, strict=True):
        _compare_numeric(expected, recorded, macro_fields, "macro")
    recomputed_pooled = _pooled_rows(predictions)
    for expected, recorded in zip(recomputed_pooled, pooled, strict=True):
        _compare_numeric(expected, recorded, [*METRIC_NAMES, "ap_lift"], "pooled")
    recomputed_comparison = _comparison_rows(config, recomputed_model, recomputed_macro, recomputed_pooled)
    comparison_numeric = [
        "a1_2_task_grouped_pooled_ap", "a1_2_task_grouped_pooled_f1",
        "a1_3_benchmark_held_out_pooled_ap", "a1_3_benchmark_held_out_pooled_f1",
        "a1_4_model_held_out_pooled_ap", "a1_4_model_held_out_pooled_f1",
        "ap_delta_a1_4_minus_a1_2", "f1_delta_a1_4_minus_a1_2",
        "ap_delta_a1_4_minus_a1_3", "f1_delta_a1_4_minus_a1_3",
        "best_model_ap_value", "worst_model_ap_value", "best_model_f1_value",
        "worst_model_f1_value", "model_ap_sample_std", "model_f1_sample_std",
        "worst_full_coverage_model_ap_value", "worst_full_coverage_model_f1_value",
    ]
    for expected, recorded in zip(recomputed_comparison, comparison, strict=True):
        _compare_numeric(expected, recorded, comparison_numeric, "comparison")
    summary = json.loads(resolve(outputs["run_summary"]).read_text(encoding="utf-8"))
    if summary["hashes_before_run"] != summary["hashes_after_run"] or verify_frozen_hashes(config) != summary["hashes_after_run"]:
        raise IntegrityError("frozen hashes changed before/after formal run")
    if any(summary["test_access"].values()) or summary["forbidden_experiments_executed"]:
        raise IntegrityError("test or a forbidden experiment was accessed")
    return {
        "status": "PASS", "external_predictions": len(predictions),
        "inner_selected_oof": len(inner), "config_rows": len(configs),
        "threshold_rows": len(thresholds), "model_metric_rows": len(model_metrics),
        "diagnostic_rows": len(diagnostics), "test_access": 0,
        "forbidden_experiments_executed": [], "estimator_fit_count": 0,
    }


def _register_run(config: dict[str, Any], summary: dict[str, Any]) -> None:
    path = REPO_ROOT / "research" / "02_EXPERIMENT_REGISTRY.csv"
    rows = read_csv(path)
    if any(row["run_id"] == summary["run_id"] for row in rows):
        raise IntegrityError("formal run_id already exists in experiment registry")
    rows.append({
        "run_id": summary["run_id"], "experiment_name": "Stage A1.4 leave-one-model-out baselines",
        "hypothesis_id": "H1", "git_commit": summary["preregistration_commit"],
        "data_version": config["source"]["data_version"], "split_version": config["source"]["split_version"],
        "config_path": "configs/stage_a1_4_lomo_execution.yaml", "seed": config["random_state"],
        "protocol": "leave-one-model-out official dev", "model": "B0-B3",
        "start_time": summary["started_at_utc"], "end_time": summary["completed_at_utc"],
        "hardware": "Windows 11 AMD64 CPU only", "status": "PASS_WITH_CONDITIONS",
        "primary_metric": "PR-AUC Average Precision and positive F1",
        "output_path": config["outputs"]["run_summary"],
        "notes": "LOMO complete 2332/2332 external and 6996/6996 selected inner OOF; model-only holdout with expected task overlap; one partial-coverage model; test access 0",
    })
    fields = [
        "run_id", "experiment_name", "hypothesis_id", "git_commit", "data_version",
        "split_version", "config_path", "seed", "protocol", "model", "start_time",
        "end_time", "hardware", "status", "primary_metric", "output_path", "notes",
    ]
    write_csv(path, rows, fields)


def formal_run(config: dict[str, Any]) -> None:
    prereg_commit, integrity = assert_clean_preregistration(config)
    checked = preflight(config)
    started_at_utc = utc_now()
    run_id = f"a1_4_lomo_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{prereg_commit[:8]}"
    run_dir = REPO_ROOT / "runs" / run_id
    if run_dir.exists():
        raise IntegrityError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    command = f"{sys.executable} scripts/run_stage_a1_4_lomo.py --config configs/stage_a1_4_lomo_execution.yaml --run"
    a12.atomic_write_text(run_dir / "command.txt", command + "\n")
    shutil.copy2(CONFIG_PATH, run_dir / "config.yaml")
    a12.atomic_write_text(run_dir / "git_commit.txt", prereg_commit + "\n")
    write_json(run_dir / "environment.json", a12.environment_record())
    write_json(run_dir / "hashes_before.json", checked["verified_hashes"])
    try:
        result = run_models(config, checked, run_id, prereg_commit, integrity, started_at_utc)
        a12.atomic_write_text(resolve(config["outputs"]["report"]), render_report(config, result))
        verification = verify_results(config)
        _register_run(config, result["summary"])
        write_json(run_dir / "verification.json", verification)
        for path_text in config["outputs"].values():
            source = resolve(path_text)
            if source.exists():
                shutil.copy2(source, run_dir / source.name)
        completion = {"status": "PASS_WITH_CONDITIONS", "run_id": run_id, **verification}
        write_json(run_dir / "completed.json", {**completion, "completed_at_utc": utc_now()})
        a12.atomic_write_text(run_dir / "stdout.log", json.dumps(completion, sort_keys=True) + "\n")
        a12.atomic_write_text(run_dir / "stderr.log", "")
        print(json.dumps(completion))
    except Exception as error:
        failure = {
            "status": "INVALIDATED", "failed_at_utc": utc_now(),
            "error_type": type(error).__name__, "error": str(error),
            "traceback": traceback.format_exc(),
            "required_action": "Preserve this run, make a separate fix commit, and rerun every target/model/baseline from the beginning.",
        }
        write_json(run_dir / "FAILED_RUN.json", failure)
        a12.atomic_write_text(run_dir / "stderr.log", failure["traceback"])
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
        print(f"A1.4 STOP: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
