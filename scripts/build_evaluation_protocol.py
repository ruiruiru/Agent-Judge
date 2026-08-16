"""Freeze Stage A1.1 grouped evaluation manifests without running any model."""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import build_full_dev_corpus as input_builder  # noqa: E402


SPLIT_SEED = 2026
TARGETS = ("success", "side_effect", "looping")
OUTER_CANDIDATES = (5, 4, 3)
INNER_CANDIDATES = (5, 4, 3, 2)
PRIMARY_GROUPS = ("assistantbench", "visualwebarena", "webarena", "workarena")
SECONDARY_GROUPS = ("assistantbench", "visualwebarena", "webarena", "workarena_l1", "workarena_l2")
THRESHOLD_CANDIDATES = tuple(round(value / 100, 2) for value in range(5, 100, 5))
FROZEN_FOLD_SHA256 = {
    "success": "820599f85fd901c1b73db61cbc77c54eb8223df3f3abc14062d5a9f20bb02e65",
    "side_effect": "11be1d8b803d4afffe25716519d117ce1e1909231954bcfd587347317e9b089c",
    "looping": "b950bf23e465d2f108f28281395ac8816c9916b20eaebe2d529e9d5fde74c749",
}

DEV_INDEX = ROOT / "artifacts" / "dev_analysis_index.csv"
TEST_MANIFEST = ROOT / "artifacts" / "test_manifest.csv"
DEV_SUMMARY = ROOT / "artifacts" / "dev_corpus_summary.json"
DRIFT_INPUT = ROOT / "artifacts" / "dev_schema_drift.csv"
FIELD_POLICY = ROOT / "artifacts" / "input_field_policy.csv"
CLEANED = ROOT / "data" / "processed" / "dev_cleaned_trajectories.jsonl"
PRIMARY_INPUT = ROOT / "data" / "processed" / "dev_serialized_primary.jsonl"
ERROR_ABLATION = ROOT / "data" / "processed" / "dev_serialized_error_ablation.jsonl"
REASONING_INPUT = ROOT / "data" / "processed" / "dev_serialized_reasoning_sensitivity.jsonl"

FOLD_OUTPUTS = {
    target: ROOT / "artifacts" / f"evaluation_folds_{target}.csv" for target in TARGETS
}
LOBO_PRIMARY = ROOT / "artifacts" / "lobo_primary_manifest.csv"
LOBO_SECONDARY = ROOT / "artifacts" / "lobo_secondary_manifest.csv"
LOMO_OUTPUT = ROOT / "artifacts" / "leave_one_model_out_manifest.csv"
SUMMARY_OUTPUT = ROOT / "artifacts" / "pre_baseline_summary.json"
DRIFT_REVIEW = ROOT / "artifacts" / "schema_drift_review.csv"
LITERAL_AUDIT = ROOT / "artifacts" / "benchmark_literal_audit.csv"
PROTOCOL_CONFIG = ROOT / "configs" / "evaluation_protocol.yaml"
BASELINE_CONFIG = ROOT / "configs" / "baseline_registry.yaml"
PROTOCOL_DOC = ROOT / "docs" / "evaluation_protocol.md"
AUDIT_DOC = ROOT / "docs" / "pre_baseline_audit_report.md"

CV_FIELDS = (
    "trajectory_key", "group_key", "target", "label", "outer_fold", "outer_role",
    "inner_split", "inner_n_splits", "benchmark_original", "benchmark_group_primary",
    "benchmark_group_secondary", "normalized_task_id", "model_name", "official_split",
)
LOBO_FIELDS = (
    "protocol", "trajectory_key", "target", "label", "held_out_group", "role",
    "inner_split", "inner_n_splits", "benchmark_group_primary", "benchmark_group_secondary",
    "group_key", "model_name",
)
LOMO_FIELDS = (
    "trajectory_key", "target", "label", "held_out_model", "role", "group_key",
    "benchmark_group_primary", "benchmark_group_secondary", "model_name",
)
DRIFT_REVIEW_FIELDS = (
    "field_path", "observed_type", "occurrence_count", "trajectory_count",
    "benchmark_distribution", "model_distribution", "short_redacted_example",
    "current_policy", "semantic_assessment", "final_decision",
)
LITERAL_FIELDS = (
    "trajectory_key", "field_path", "step_index", "occurrence_count", "redacted_context",
    "source_is_natural_text", "source_is_injected_metadata",
)


@dataclass(frozen=True)
class Sample:
    """One target-specific eligible dev trajectory."""

    trajectory_key: str
    group_key: str
    target: str
    label: int
    benchmark_original: str
    benchmark_group_primary: str
    benchmark_group_secondary: str
    normalized_task_id: str
    model_name: str
    official_split: str


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV completely."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    """Write a deterministic UTF-8 CSV atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    """Write deterministic text atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    """Hash a file without changing it."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a compact local JSONL artifact."""
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_task_id(value: str) -> str:
    """Apply only the normalization frozen in Stage A0.1."""
    return value.strip().lower().replace(".improved.", ".").replace(".resized.", ".")


def group_key(benchmark_original: str, task_id: str) -> str:
    """Serialize the frozen two-component task grouping key."""
    return f"{benchmark_original}::{normalize_task_id(task_id)}"


def _jsonl_key_set(path: Path) -> set[str]:
    keys: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                keys.append(str(json.loads(line)["trajectory_key"]))
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate trajectory_key in {path}")
    return set(keys)


def load_samples() -> tuple[dict[str, list[Sample]], dict[str, Any]]:
    """Join labels by trajectory_key only and enforce target-specific eligibility."""
    rows = read_csv(DEV_INDEX)
    test_rows = read_csv(TEST_MANIFEST)
    forbidden_test_columns = {
        f"{target}_{suffix}" for target in TARGETS for suffix in ("label", "status", "eligible_main")
    }
    if forbidden_test_columns.intersection(test_rows[0] if test_rows else {}):
        raise PermissionError("sealed test manifest unexpectedly exposes target information")
    test_keys = {row["trajectory_key"] for row in test_rows}
    corpus_sets = {
        "cleaned": _jsonl_key_set(CLEANED),
        "primary": _jsonl_key_set(PRIMARY_INPUT),
        "error_ablation": _jsonl_key_set(ERROR_ABLATION),
        "reasoning": _jsonl_key_set(REASONING_INPUT),
    }
    expected = set(corpus_sets["cleaned"])
    if len(expected) != 196 or any(keys != expected for keys in corpus_sets.values()):
        raise ValueError("the four frozen dev corpus files must share exactly 196 keys")
    index_keys = [row["trajectory_key"] for row in rows]
    if len(index_keys) != len(set(index_keys)) or set(index_keys) != expected:
        raise ValueError("dev index and frozen corpus do not join one-to-one")
    if expected.intersection(test_keys):
        raise PermissionError("sealed test key entered the dev corpus")

    samples: dict[str, list[Sample]] = {}
    excluded: dict[str, list[dict[str, str]]] = {}
    for target in TARGETS:
        target_samples: list[Sample] = []
        excluded_rows: list[dict[str, str]] = []
        for row in rows:
            eligible = row[f"{target}_eligible_main"].lower() == "true"
            label_text = row[f"{target}_label"]
            if not eligible or label_text not in {"0", "1"}:
                excluded_rows.append({
                    "trajectory_key": row["trajectory_key"],
                    "status": row[f"{target}_status"],
                    "eligible_main": row[f"{target}_eligible_main"],
                    "label": label_text,
                })
                continue
            normalized = normalize_task_id(row["task_id"])
            target_samples.append(Sample(
                trajectory_key=row["trajectory_key"],
                group_key=group_key(row["benchmark_original"], normalized),
                target=target,
                label=int(label_text),
                benchmark_original=row["benchmark_original"],
                benchmark_group_primary=row["benchmark_group_primary"],
                benchmark_group_secondary=row["benchmark_group_secondary"],
                normalized_task_id=normalized,
                model_name=row["model_name"],
                official_split=row["official_split"],
            ))
        if any(sample.official_split != "dev" for sample in target_samples):
            raise PermissionError("non-dev sample entered an evaluation target")
        if len({sample.trajectory_key for sample in target_samples}) != len(target_samples):
            raise ValueError(f"duplicate target trajectory: {target}")
        samples[target] = sorted(target_samples, key=lambda sample: sample.trajectory_key)
        excluded[target] = excluded_rows
    return samples, {
        "corpus_key_count": len(expected),
        "test_identifier_count_read_for_sealing_only": len(test_keys),
        "test_target_columns_read": 0,
        "test_trajectory_content_accessed": 0,
        "excluded": excluded,
    }


def _stable_rank(seed: int, namespace: str, salt: int, value: str) -> int:
    payload = f"{seed}|{namespace}|{salt}|{value}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _group_counts(samples: Sequence[Sample]) -> dict[str, tuple[int, int, int]]:
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for sample in samples:
        counts[sample.group_key][sample.label] += 1
        counts[sample.group_key][2] += 1
    return {key: tuple(value) for key, value in counts.items()}


def _assignment_objective(
    fold_counts: Sequence[Sequence[int]], fold_sizes: Sequence[int], fold_groups: Sequence[int], totals: Sequence[int], total_size: int, total_groups: int,
) -> float:
    n_splits = len(fold_counts)
    score = 0.0
    for label in (0, 1):
        expected = totals[label] / n_splits
        denominator = max(totals[label], 1)
        score += sum((fold_counts[fold][label] - expected) ** 2 for fold in range(n_splits)) / denominator
    expected_size = total_size / n_splits
    score += 0.15 * sum((size - expected_size) ** 2 for size in fold_sizes) / max(total_size, 1)
    expected_groups = total_groups / n_splits
    score += 0.05 * sum((count - expected_groups) ** 2 for count in fold_groups) / max(total_groups, 1)
    return score


def validate_assignment(samples: Sequence[Sample], assignment: Mapping[str, int], n_splits: int) -> bool:
    """Check group exclusivity and binary class coverage in every train/validation fold."""
    if set(assignment) != {sample.group_key for sample in samples}:
        return False
    for fold in range(n_splits):
        validation = [sample for sample in samples if assignment[sample.group_key] == fold]
        train = [sample for sample in samples if assignment[sample.group_key] != fold]
        if {sample.label for sample in validation} != {0, 1}:
            return False
        if {sample.label for sample in train} != {0, 1}:
            return False
    return True


def assign_grouped_stratified(samples: Sequence[Sample], n_splits: int, seed: int, namespace: str) -> dict[str, int] | None:
    """Create a deterministic grouped stratification using fixed multi-start greedy search."""
    counts = _group_counts(samples)
    if len(counts) < n_splits:
        return None
    totals = [sum(sample.label == label for sample in samples) for label in (0, 1)]
    if min(totals) < n_splits:
        return None
    best: tuple[float, tuple[tuple[str, int], ...], dict[str, int]] | None = None
    for salt in range(512):
        def order_key(key: str) -> tuple[float, int, int]:
            negative, positive, size = counts[key]
            rarity = max(negative / max(totals[0], 1), positive / max(totals[1], 1))
            return (-rarity, -size, _stable_rank(seed, namespace, salt, key))

        ordered = sorted(counts, key=order_key)
        fold_counts = [[0, 0] for _ in range(n_splits)]
        fold_sizes = [0 for _ in range(n_splits)]
        fold_groups = [0 for _ in range(n_splits)]
        assignment: dict[str, int] = {}
        for index, key in enumerate(ordered):
            negative, positive, size = counts[key]
            candidates = [fold for fold in range(n_splits) if fold_groups[fold] == 0] if index < n_splits else list(range(n_splits))
            choices: list[tuple[float, int, int]] = []
            for fold in candidates:
                trial_counts = [list(values) for values in fold_counts]
                trial_sizes = list(fold_sizes)
                trial_groups = list(fold_groups)
                trial_counts[fold][0] += negative
                trial_counts[fold][1] += positive
                trial_sizes[fold] += size
                trial_groups[fold] += 1
                objective = _assignment_objective(
                    trial_counts, trial_sizes, trial_groups, totals, len(samples), len(counts)
                )
                choices.append((objective, _stable_rank(seed, namespace + "|fold", salt, f"{key}|{fold}"), fold))
            chosen = min(choices)[2]
            assignment[key] = chosen
            fold_counts[chosen][0] += negative
            fold_counts[chosen][1] += positive
            fold_sizes[chosen] += size
            fold_groups[chosen] += 1
        if not validate_assignment(samples, assignment, n_splits):
            continue
        objective = _assignment_objective(fold_counts, fold_sizes, fold_groups, totals, len(samples), len(counts))
        signature = tuple(sorted(assignment.items()))
        candidate = (objective, signature, assignment)
        if best is None or candidate[:2] < best[:2]:
            best = candidate
    return None if best is None else best[2]


def choose_max_feasible(samples: Sequence[Sample], candidates: Sequence[int], seed: int, namespace: str) -> tuple[int, dict[str, int]]:
    """Choose the largest candidate split count with complete binary class coverage."""
    for n_splits in candidates:
        assignment = assign_grouped_stratified(samples, n_splits, seed, namespace)
        if assignment is not None:
            return n_splits, assignment
    raise ValueError(f"no class-complete grouped split is feasible for {namespace}")


def _role_counts(rows: Sequence[Mapping[str, Any]], role_field: str, role: str) -> dict[str, Any]:
    selected = [row for row in rows if row[role_field] == role]
    return {
        "trajectories": len(selected),
        "task_groups": len({row["group_key"] for row in selected}),
        "negative": sum(int(row["label"]) == 0 for row in selected),
        "positive": sum(int(row["label"]) == 1 for row in selected),
    }


def build_cv_manifests(samples_by_target: Mapping[str, Sequence[Sample]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Build one target-specific outer/inner grouped manifest per target."""
    outputs: dict[str, list[dict[str, Any]]] = {}
    summary: dict[str, Any] = {}
    for target_index, target in enumerate(TARGETS):
        samples = list(samples_by_target[target])
        outer_n, outer_assignment = choose_max_feasible(
            samples, OUTER_CANDIDATES, SPLIT_SEED, f"outer|{target}"
        )
        rows: list[dict[str, Any]] = []
        inner_details: dict[int, dict[str, Any]] = {}
        for outer_fold_zero in range(outer_n):
            outer_train = [sample for sample in samples if outer_assignment[sample.group_key] != outer_fold_zero]
            inner_seed = SPLIT_SEED + (target_index + 1) * 100 + outer_fold_zero + 1
            inner_n, inner_assignment = choose_max_feasible(
                outer_train, INNER_CANDIDATES, inner_seed, f"inner|{target}|outer{outer_fold_zero + 1}"
            )
            inner_details[outer_fold_zero + 1] = {
                "n_splits": inner_n,
                "selected_validation_fold": 1,
                "seed": inner_seed,
            }
            for sample in samples:
                is_outer_validation = outer_assignment[sample.group_key] == outer_fold_zero
                if is_outer_validation:
                    outer_role = "outer_validation"
                    inner_split = "not_applicable"
                else:
                    outer_role = "outer_train"
                    inner_split = "inner_validation" if inner_assignment[sample.group_key] == 0 else "inner_train"
                rows.append({
                    "trajectory_key": sample.trajectory_key,
                    "group_key": sample.group_key,
                    "target": target,
                    "label": sample.label,
                    "outer_fold": outer_fold_zero + 1,
                    "outer_role": outer_role,
                    "inner_split": inner_split,
                    "inner_n_splits": inner_n,
                    "benchmark_original": sample.benchmark_original,
                    "benchmark_group_primary": sample.benchmark_group_primary,
                    "benchmark_group_secondary": sample.benchmark_group_secondary,
                    "normalized_task_id": sample.normalized_task_id,
                    "model_name": sample.model_name,
                    "official_split": sample.official_split,
                })
        rows.sort(key=lambda row: (int(row["outer_fold"]), row["trajectory_key"]))
        outputs[target] = rows
        fold_stats = []
        for fold in range(1, outer_n + 1):
            fold_rows = [row for row in rows if int(row["outer_fold"]) == fold]
            fold_stats.append({
                "outer_fold": fold,
                "outer_train": _role_counts(fold_rows, "outer_role", "outer_train"),
                "outer_validation": _role_counts(fold_rows, "outer_role", "outer_validation"),
                "inner_train": _role_counts(fold_rows, "inner_split", "inner_train"),
                "inner_validation": _role_counts(fold_rows, "inner_split", "inner_validation"),
                "inner_n_splits": inner_details[fold]["n_splits"],
                "inner_seed": inner_details[fold]["seed"],
            })
        summary[target] = {
            "eligible_trajectories": len(samples),
            "negative": sum(sample.label == 0 for sample in samples),
            "positive": sum(sample.label == 1 for sample in samples),
            "task_groups": len({sample.group_key for sample in samples}),
            "positive_task_groups": len({sample.group_key for sample in samples if sample.label == 1}),
            "outer_folds": outer_n,
            "folds": fold_stats,
        }
    return outputs, summary


def _optional_inner(samples: Sequence[Sample], seed: int, namespace: str) -> tuple[int | None, dict[str, int] | None]:
    try:
        return choose_max_feasible(samples, INNER_CANDIDATES, seed, namespace)
    except ValueError:
        return None, None


def build_lobo_manifest(
    samples_by_target: Mapping[str, Sequence[Sample]], protocol: str, groups: Sequence[str], group_field: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build primary or sensitivity LOBO manifests with group-aware inner roles."""
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for target_index, target in enumerate(TARGETS):
        summary[target] = {}
        samples = list(samples_by_target[target])
        for group_index, held_out in enumerate(groups):
            train = [sample for sample in samples if getattr(sample, group_field) != held_out]
            validation = [sample for sample in samples if getattr(sample, group_field) == held_out]
            inner_seed = SPLIT_SEED + 1000 + target_index * 100 + group_index
            inner_n, inner_assignment = _optional_inner(
                train, inner_seed, f"{protocol}|{target}|{held_out}"
            )
            for sample in samples:
                is_validation = getattr(sample, group_field) == held_out
                role = "validation" if is_validation else "train"
                if is_validation:
                    inner_split = "not_applicable"
                elif inner_assignment is None:
                    inner_split = "unavailable"
                else:
                    inner_split = "inner_validation" if inner_assignment[sample.group_key] == 0 else "inner_train"
                rows.append({
                    "protocol": protocol,
                    "trajectory_key": sample.trajectory_key,
                    "target": target,
                    "label": sample.label,
                    "held_out_group": held_out,
                    "role": role,
                    "inner_split": inner_split,
                    "inner_n_splits": "" if inner_n is None else inner_n,
                    "benchmark_group_primary": sample.benchmark_group_primary,
                    "benchmark_group_secondary": sample.benchmark_group_secondary,
                    "group_key": sample.group_key,
                    "model_name": sample.model_name,
                })
            validation_counts = {
                "trajectories": len(validation),
                "task_groups": len({sample.group_key for sample in validation}),
                "negative": sum(sample.label == 0 for sample in validation),
                "positive": sum(sample.label == 1 for sample in validation),
            }
            train_counts = {
                "trajectories": len(train),
                "task_groups": len({sample.group_key for sample in train}),
                "negative": sum(sample.label == 0 for sample in train),
                "positive": sum(sample.label == 1 for sample in train),
            }
            summary[target][held_out] = {
                "train": train_counts,
                "validation": validation_counts,
                "validation_has_both_classes": validation_counts["negative"] > 0 and validation_counts["positive"] > 0,
                "inner_split_feasible": inner_assignment is not None,
                "inner_n_splits": inner_n,
            }
    rows.sort(key=lambda row: (row["target"], row["held_out_group"], row["trajectory_key"]))
    return rows, summary


def build_lomo_manifest(samples_by_target: Mapping[str, Sequence[Sample]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build the candidate Leave-One-Model-Out management manifest."""
    models = sorted({sample.model_name for samples in samples_by_target.values() for sample in samples})
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {"models": models, "targets": {}}
    all_primary_groups = set(PRIMARY_GROUPS)
    all_models_cover_all_primary = True
    for target in TARGETS:
        samples = list(samples_by_target[target])
        summary["targets"][target] = {}
        for held_out in models:
            validation = [sample for sample in samples if sample.model_name == held_out]
            train = [sample for sample in samples if sample.model_name != held_out]
            for sample in samples:
                rows.append({
                    "trajectory_key": sample.trajectory_key,
                    "target": target,
                    "label": sample.label,
                    "held_out_model": held_out,
                    "role": "validation" if sample.model_name == held_out else "train",
                    "group_key": sample.group_key,
                    "benchmark_group_primary": sample.benchmark_group_primary,
                    "benchmark_group_secondary": sample.benchmark_group_secondary,
                    "model_name": sample.model_name,
                })
            validation_groups = {sample.benchmark_group_primary for sample in validation}
            train_groups = {sample.benchmark_group_primary for sample in train}
            validation_both = {sample.label for sample in validation} == {0, 1}
            covers_all = validation_groups == all_primary_groups
            all_models_cover_all_primary = all_models_cover_all_primary and covers_all
            summary["targets"][target][held_out] = {
                "validation": {
                    "trajectories": len(validation),
                    "task_groups": len({sample.group_key for sample in validation}),
                    "negative": sum(sample.label == 0 for sample in validation),
                    "positive": sum(sample.label == 1 for sample in validation),
                    "benchmark_groups": sorted(validation_groups),
                },
                "train_benchmark_groups": sorted(train_groups),
                "train_covers_all_primary_benchmarks": train_groups == all_primary_groups,
                "validation_covers_all_primary_benchmarks": covers_all,
                "validation_has_both_classes": validation_both,
            }
    rows.sort(key=lambda row: (row["target"], row["held_out_model"], row["trajectory_key"]))
    summary["all_models_cover_all_primary_benchmarks"] = all_models_cover_all_primary
    summary["recommended_status"] = "candidate" if all_models_cover_all_primary else "exploratory_only"
    return rows, summary


def audit_group_key(samples: Sequence[Sample]) -> dict[str, Any]:
    """Audit task groups, partial model coverage, and cross-benchmark ID collisions."""
    by_group: dict[str, list[Sample]] = defaultdict(list)
    by_task_id: dict[str, set[str]] = defaultdict(set)
    for sample in samples:
        by_group[sample.group_key].append(sample)
        by_task_id[sample.normalized_task_id].add(sample.benchmark_original)
    sizes = [len(values) for values in by_group.values()]
    collisions = {task: sorted(benchmarks) for task, benchmarks in by_task_id.items() if len(benchmarks) > 1}
    return {
        "group_key_components": ["benchmark_original", "normalized_task_id"],
        "task_groups": len(by_group),
        "group_size_distribution": dict(sorted(Counter(sizes).items())),
        "min_group_size": min(sizes),
        "median_group_size": statistics.median(sizes),
        "max_group_size": max(sizes),
        "groups_with_four_models": sum(len({sample.model_name for sample in values}) == 4 for values in by_group.values()),
        "groups_with_partial_model_coverage": sum(len({sample.model_name for sample in values}) < 4 for values in by_group.values()),
        "cross_benchmark_normalized_task_id_collisions": collisions,
        "benchmark_component_prevents_namespace_collision": True,
    }


def audit_terminal_and_views() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    """Audit exact terminal concepts and frozen input-view relationships."""
    cleaned = load_jsonl(CLEANED)
    primary = {row["trajectory_key"]: row for row in load_jsonl(PRIMARY_INPUT)}
    ablation = {row["trajectory_key"]: row for row in load_jsonl(ERROR_ABLATION)}
    reasoning = {row["trajectory_key"]: row for row in load_jsonl(REASONING_INPUT)}
    key_sets = [set(primary), set(ablation), set(reasoning), {row["trajectory_key"] for row in cleaned}]
    if any(keys != key_sets[0] for keys in key_sets[1:]):
        raise ValueError("input views do not share identical trajectory keys")
    last_action_count = 0
    last_observation_count = 0
    explicit_count = 0
    signal_counts: Counter[str] = Counter()
    natural_error_trajectories = 0
    natural_error_steps = 0
    reasoning_trajectories = 0
    reasoning_steps = 0
    difference_trajectories = 0
    cleaned_by_key: dict[str, dict[str, Any]] = {}
    for record in cleaned:
        key = record["trajectory_key"]
        cleaned_by_key[key] = record
        actions = [step["action"] for step in record["steps"] if step.get("action")]
        observations = [step["observation"] for step in record["steps"] if step.get("observation")]
        terminal = record["terminal"]
        if terminal["last_nonempty_action"] != (actions[-1] if actions else None):
            raise ValueError(f"last_nonempty_action mismatch: {key}")
        if terminal["last_nonempty_observation"] != (observations[-1] if observations else None):
            raise ValueError(f"last_nonempty_observation mismatch: {key}")
        signal = terminal["termination_signal"]
        if signal not in {None, "send_msg_to_user", "report_infeasible"}:
            raise ValueError(f"unapproved explicit termination signal: {signal}")
        last_action_count += terminal["last_nonempty_action"] is not None
        last_observation_count += terminal["last_nonempty_observation"] is not None
        explicit_count += signal is not None
        signal_counts[signal or "null"] += 1
        has_errors = any(step.get("error") for step in record["steps"])
        natural_error_trajectories += has_errors
        natural_error_steps += sum(bool(step.get("error")) for step in record["steps"])
        has_reasoning = any(step.get("reasoning") for step in record["steps"])
        reasoning_trajectories += has_reasoning
        reasoning_steps += sum(bool(step.get("reasoning")) for step in record["steps"])
        expected_primary = input_builder.serialize_input(record, "primary_with_natural_errors")
        expected_ablation = input_builder.serialize_input(record, "ablation_without_error_fields")
        expected_reasoning = input_builder.serialize_input(record, "sensitivity_with_reasoning")
        if primary[key]["serialized_text"] != expected_primary:
            raise ValueError(f"primary serialization mismatch: {key}")
        if ablation[key]["serialized_text"] != expected_ablation:
            raise ValueError(f"error ablation mismatch: {key}")
        if reasoning[key]["serialized_text"] != expected_reasoning:
            raise ValueError(f"reasoning serialization mismatch: {key}")
        difference_trajectories += expected_primary != expected_ablation
    terminal_audit = {
        "trajectory_count": len(cleaned),
        "last_nonempty_action_count": last_action_count,
        "last_nonempty_action_rate": last_action_count / len(cleaned),
        "last_nonempty_observation_count": last_observation_count,
        "last_nonempty_observation_rate": last_observation_count / len(cleaned),
        "explicit_termination_signal_count": explicit_count,
        "explicit_termination_signal_rate": explicit_count / len(cleaned),
        "explicit_termination_signal_values": dict(sorted(signal_counts.items())),
        "legacy_field_alias": "cleaned terminal.termination_signal means explicit_termination_signal",
        "last_nonempty_action_is_success_or_normal_termination": False,
    }
    view_audit = {
        "trajectory_keys_identical": True,
        "step_order_source_identical": True,
        "natural_error_trajectories": natural_error_trajectories,
        "natural_error_steps": natural_error_steps,
        "primary_error_ablation_differing_trajectories": difference_trajectories,
        "difference_matches_natural_error_coverage": difference_trajectories == natural_error_trajectories,
        "last_action_error_is_natural_environment_or_tool_feedback": True,
        "natural_error_used_for_sample_or_label_selection": False,
        "reasoning_trajectories": reasoning_trajectories,
        "reasoning_steps": reasoning_steps,
        "reasoning_primary_baseline_allowed": False,
    }
    return terminal_audit, view_audit, cleaned_by_key


def audit_schema_drift() -> list[dict[str, Any]]:
    """Perform a path/type-level manual review without expanding the whitelist."""
    drift_rows = read_csv(DRIFT_INPUT)
    policy_rows = read_csv(FIELD_POLICY)
    exact_policy = {(row["field_path"], row["observed_type"]): row["policy_class"] for row in policy_rows}
    path_policy: dict[str, set[str]] = defaultdict(set)
    for row in policy_rows:
        path_policy[row["field_path"]].add(row["policy_class"])
    assessments = {
        "$.steps[].axtree_obj.nodes[].name.sources[].invalid": (
            "Low-level accessibility-tree source validity flag under excluded axtree_obj; axtree_pruned remains the approved observation and exclusion does not block parsing."
        ),
        "$.steps[].axtree_obj.nodes[].name.sources[].nativeSourceValue.relatedNodes[].idref": (
            "Low-level accessibility cross-node reference under excluded axtree_obj; redundant with unapproved raw tree internals and not required by the shared cleaned schema."
        ),
        "$.steps[].axtree_obj.nodes[].value.value": (
            "Integer type variant of an already excluded raw accessibility-node value; the approved axtree_pruned text remains available and adapter behavior is unaffected."
        ),
        "$.steps[].stats.n_retry": (
            "Integer type variant of a metadata-only retry counter; it may encode runtime/model behavior and is not approved as first-round structural evidence."
        ),
    }
    output: list[dict[str, Any]] = []
    for row in drift_rows:
        path = row["field_path"]
        observed_type = row["observed_type"]
        if (path, observed_type) in exact_policy:
            current = exact_policy[(path, observed_type)]
        elif path in path_policy:
            current = "unapproved_type_variant_of:" + ";".join(sorted(path_policy[path]))
        else:
            current = "default_reject_unregistered_path"
        output.append({
            "field_path": path,
            "observed_type": observed_type,
            "occurrence_count": row["presence_count"],
            "trajectory_count": row["trajectory_count"],
            "benchmark_distribution": row["benchmarks"],
            "model_distribution": row["models"],
            "short_redacted_example": row["example_value_redacted"],
            "current_policy": current,
            "semantic_assessment": assessments[path],
            "final_decision": "keep_excluded",
        })
    if len(output) != 4 or sum(int(row["occurrence_count"]) for row in output) != 12477:
        raise ValueError("Stage A1.0 drift evidence changed unexpectedly")
    return output


def _redacted_literal_context(value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    return f"<redacted>workarena<redacted>;length={len(value)};sha256={digest}"


def audit_benchmark_literals(cleaned_by_key: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Trace every WorkArena literal in allowlisted natural text fields."""
    rows: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()
    for key in sorted(cleaned_by_key):
        record = cleaned_by_key[key]
        candidates: list[tuple[str, int | None, Any]] = [("$.goal", None, record["task"].get("instruction"))]
        for step in record["steps"]:
            index = int(step["step_index"])
            candidates.extend([
                ("$.steps[].action", index, step.get("action")),
                ("$.steps[].axtree_pruned", index, step.get("observation")),
                ("$.steps[].focused_element", index, step.get("focused_element")),
                ("$.steps[].last_action_error", index, step.get("error")),
            ])
        for path, index, value in candidates:
            if not isinstance(value, str) or "workarena" not in value.lower():
                continue
            occurrences = value.lower().count("workarena")
            field_counts[path] += occurrences
            rows.append({
                "trajectory_key": key,
                "field_path": path,
                "step_index": "" if index is None else index,
                "occurrence_count": occurrences,
                "redacted_context": _redacted_literal_context(value),
                "source_is_natural_text": "true",
                "source_is_injected_metadata": "false",
            })
    primary = {row["trajectory_key"]: row["serialized_text"] for row in load_jsonl(PRIMARY_INPUT)}
    affected = sorted({row["trajectory_key"] for row in rows})
    for key in affected:
        if "workarena" not in primary[key].lower():
            raise ValueError(f"natural literal absent from primary serialization: {key}")
        changed = copy.deepcopy(cleaned_by_key[key])
        changed["metadata"] = {
            "benchmark_group_primary": "injected-sentinel",
            "benchmark_group_secondary": "injected-sentinel",
            "model_name": "injected-sentinel",
            "task_id": "injected-sentinel",
            "official_split": "injected-sentinel",
            "source_revision": "injected-sentinel",
            "source_path": "injected-sentinel",
            "source_sha256": "injected-sentinel",
        }
        if input_builder.serialize_input(changed, "primary_with_natural_errors") != primary[key]:
            raise ValueError("metadata mutation changed a primary serialized input")
    return rows, {
        "affected_trajectories": len(affected),
        "trajectory_keys": affected,
        "audit_rows": len(rows),
        "literal_occurrences": sum(int(row["occurrence_count"]) for row in rows),
        "field_occurrences": dict(sorted(field_counts.items())),
        "all_sources_are_allowlisted_natural_text": all(row["source_is_natural_text"] == "true" for row in rows),
        "serializer_or_metadata_injection_detected": False,
        "decision": "retain_natural_text",
        "future_sensitivity_candidate": "benchmark_literal_redacted (not generated in A1.1)",
    }


def protocol_config(folds_by_target: Mapping[str, int]) -> dict[str, Any]:
    """Return the frozen evaluation protocol as JSON-compatible YAML 1.2."""
    return {
        "schema_version": "1.0",
        "stage": "A1.1",
        "split_seed": SPLIT_SEED,
        "targets": list(TARGETS),
        "eligibility": {
            "required": ["<target>_eligible_main == true", "<target>_label in {0, 1}"],
            "join_key": "trajectory_key",
        },
        "group_key": ["benchmark_original", "normalized_task_id"],
        "outer_cv": {
            "algorithm": "custom_deterministic_grouped_stratification_v1",
            "authoritative_outputs": [path.relative_to(ROOT).as_posix() for path in FOLD_OUTPUTS.values()],
            "authoritative_manifests": {
                FOLD_OUTPUTS[target].relative_to(ROOT).as_posix(): FROZEN_FOLD_SHA256[target]
                for target in TARGETS
            },
            "candidate_folds_descending": list(OUTER_CANDIDATES),
            "folds_by_target": dict(folds_by_target),
            "random_state": SPLIT_SEED,
            "scikit_learn_class_called": False,
            "scikit_learn_equivalence_claimed": False,
            "regeneration_allowed": False,
            "sole_authority": "recorded_manifest_bytes_and_sha256",
        },
        "inner_split": {
            "type": "fixed_once_group_aware_split_within_each_outer_train",
            "group_aware": True,
            "candidate_folds_descending": list(INNER_CANDIDATES),
            "selected_validation_fold": 1,
            "outer_validation_access_allowed": False,
            "applies_identically_to_all_registered_models": True,
        },
        "model_configuration_selection": {
            "selection_data": "inner_validation_only",
            "primary_objective": "pr_auc",
            "direction": "maximize",
            "tie_break": "predeclared_registry_order",
        },
        "threshold": {
            "selection_data": "inner_validation_only",
            "primary_objective": "positive_f1",
            "candidates": list(THRESHOLD_CANDIDATES),
            "side_effect_f2_is_reporting_only": True,
            "tie_break": ["higher_recall", "closer_to_0.5", "smaller_threshold"],
            "outer_validation_access_allowed": False,
        },
        "metrics": {
            "primary": ["pr_auc", "positive_f1"],
            "secondary": ["roc_auc", "precision", "recall", "f2", "balanced_accuracy", "mcc"],
            "accuracy_is_primary": False,
            "fold_aggregation": ["raw_fold_values", "mean", "standard_deviation", "pooled_out_of_fold"],
            "pooled_out_of_fold": {
                "definition": "concatenate_exactly_one_outer_validation_prediction_per_eligible_trajectory",
                "predicted_label_uses_fold_specific_frozen_threshold": True,
                "report_separately_from_fold_mean_and_standard_deviation": True,
            },
            "single_class_lobo_holdout": {
                "allowed_reports": [
                    "predicted_positive_rate",
                    "false_positive_rate_if_negatives_exist",
                    "specificity_if_negatives_exist",
                    "mean_predicted_probability",
                ],
                "all_other_predictive_metrics": "NA",
                "na_fill_value_prohibited": True,
                "known_affected_holdouts": [
                    "primary:side_effect:assistantbench",
                    "sensitivity:side_effect:assistantbench",
                    "sensitivity:side_effect:workarena_l1",
                ],
            },
            "uncomputable_metric_policy": "record_not_computable_never_impute",
        },
        "lobo": {
            "authoritative_manifests": {
                LOBO_PRIMARY.relative_to(ROOT).as_posix(): "16735afc8defd5d91bf2d23ba7773a1f0515feafc238ad1cec2df0dc530b0191",
                LOBO_SECONDARY.relative_to(ROOT).as_posix(): "5872f114890e7a6c3096be0a7be6ba971528e72b1f2e6e67a3452c4575c9abfe",
            },
            "primary_group_field": "benchmark_group_primary",
            "primary_groups": list(PRIMARY_GROUPS),
            "sensitivity_group_field": "benchmark_group_secondary",
            "sensitivity_groups": list(SECONDARY_GROUPS),
        },
        "leave_one_model_out": {
            "authoritative_manifests": {
                LOMO_OUTPUT.relative_to(ROOT).as_posix(): "5f1f64803014b6891089c18a67b41778ab0ced4f4110bcca014008675b07ac7d",
            },
        },
        "execution_sequence": [
            "fit_each_registered_candidate_on_inner_train",
            "score_each_candidate_on_inner_validation_and_select_by_pr_auc",
            "select_positive_f1_threshold_for_selected_candidate_on_inner_validation",
            "refit_selected_candidate_on_complete_outer_train",
            "evaluate_complete_outer_validation_once_with_frozen_threshold",
        ],
        "primary_input_view": "primary_with_natural_errors",
        "first_round_disallowed_views": ["ablation_without_error_fields", "sensitivity_with_reasoning"],
        "probability_calibration": "not_registered_first_round",
        "resampling": "prohibited",
        "test_access": {"allowed": False, "trajectory_content": False, "labels": False, "metrics": False},
    }


def baseline_registry() -> dict[str, Any]:
    """Return the finite first-round registry; nothing in it is executed here."""
    return {
        "schema_version": "1.0",
        "stage": "A1.1",
        "execution_allowed_in_this_stage": False,
        "primary_input_view": "primary_with_natural_errors",
        "baselines": [
            {"id": "B0", "name": "majority", "estimator": "DummyClassifier", "parameters": {"strategy": ["most_frequent"]}},
            {"id": "B1", "name": "training_prior", "estimator": "DummyClassifier", "parameters": {"strategy": ["prior"]}},
            {
                "id": "B2",
                "name": "leak_safe_structural_logistic_regression",
                "estimator": "LogisticRegression",
                "input": "dev_cleaned_trajectories",
                "candidate_features": [
                    "step_count", "nonempty_action_count", "nonempty_observation_count",
                    "nonempty_focused_element_count", "natural_error_step_count",
                    "explicit_termination_signal_present", "action_text_total_length",
                    "observation_text_total_length", "mean_action_length",
                    "mean_observation_length", "repeated_action_ratio",
                ],
                "parameters": {"C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"], "solver": ["liblinear"], "max_iter": [1000]},
            },
            {
                "id": "B3",
                "name": "tfidf_logistic_regression",
                "estimator": "TfidfVectorizer+LogisticRegression",
                "input": "primary_with_natural_errors",
                "tfidf_variants": [
                    {"id": "word_unigram", "ngram_range": [1, 1], "min_df": 2, "max_features": 20000},
                    {"id": "word_unigram_bigram", "ngram_range": [1, 2], "min_df": 2, "max_features": 20000},
                ],
                "parameters": {"C": [0.1, 1.0, 10.0], "class_weight": [None, "balanced"], "solver": ["liblinear"], "max_iter": [1000]},
            },
        ],
        "forbidden": [
            "llm_judge", "embedding_mlp", "transformer_finetuning", "lora", "xgboost_large_search",
            "graph_neural_network", "multimodal_screenshot_model", "per_sample_manual_judgment", "test_evaluation",
            "smote", "oversampling", "undersampling",
        ],
        "execution_protocol": {
            "configuration_selection_data": "inner_validation_only",
            "configuration_selection_metric": "pr_auc",
            "configuration_tie_break": "predeclared_registry_order",
            "threshold_selection_data": "inner_validation_only",
            "threshold_selection_metric": "positive_f1",
            "outer_validation_use": "single_evaluation_after_complete_outer_train_refit",
        },
        "feature_and_hyperparameter_selection_data": "inner_validation_only",
        "outer_validation_selection_allowed": False,
    }


def _fold_table(summary: Mapping[str, Any]) -> list[str]:
    lines = [
        "| Target | Fold | Train N/G/0/1 | Validation N/G/0/1 | Inner train N/G/0/1 | Inner validation N/G/0/1 |",
        "|---|---:|---|---|---|---|",
    ]
    for target in TARGETS:
        for fold in summary[target]["folds"]:
            def fmt(role: str) -> str:
                value = fold[role]
                return f"{value['trajectories']}/{value['task_groups']}/{value['negative']}/{value['positive']}"
            lines.append(
                f"| {target} | {fold['outer_fold']} | {fmt('outer_train')} | {fmt('outer_validation')} | {fmt('inner_train')} | {fmt('inner_validation')} |"
            )
    return lines


def _lobo_table(summary: Mapping[str, Any]) -> list[str]:
    lines = [
        "| Target | Held out | Train N/G/0/1 | Validation N/G/0/1 | Both classes | Inner feasible |",
        "|---|---|---|---|---|---|",
    ]
    for target in TARGETS:
        for group, item in summary[target].items():
            train = item["train"]
            validation = item["validation"]
            lines.append(
                f"| {target} | {group} | {train['trajectories']}/{train['task_groups']}/{train['negative']}/{train['positive']} | "
                f"{validation['trajectories']}/{validation['task_groups']}/{validation['negative']}/{validation['positive']} | "
                f"{item['validation_has_both_classes']} | {item['inner_split_feasible']} |"
            )
    return lines


def render_protocol(summary: Mapping[str, Any]) -> str:
    """Render the frozen protocol document."""
    lines = [
        "# Stage A1.1 Frozen Grouped Evaluation Protocol",
        "",
        "## Scope",
        "",
        "This document freezes dev-only data eligibility and evaluation management. No feature extraction, estimator, prediction, threshold optimization, or model metric was run in A1.1.",
        "",
        "## Target eligibility and outer folds",
        "",
        "| Target | Eligible | Negative | Positive | Task groups | Positive task groups | Outer folds |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for target in TARGETS:
        value = summary["cv"][target]
        lines.append(
            f"| {target} | {value['eligible_trajectories']} | {value['negative']} | {value['positive']} | {value['task_groups']} | {value['positive_task_groups']} | {value['outer_folds']} |"
        )
    lines.extend([
        "",
        "Eligibility requires both `<target>_eligible_main == true` and a binary main label. Labels join the frozen input only through `trajectory_key`.",
        "",
        "The frozen group key is `(benchmark_original, normalized_task_id)`. The actual splitter was `custom_deterministic_grouped_stratification_v1`; scikit-learn `StratifiedGroupKFold` was not called and equivalence is not claimed. The recorded manifest bytes and SHA-256 values are the sole authority and regeneration is prohibited.",
        "",
        "## Outer and fixed inner split statistics",
        "",
        "Cells use `trajectories/task_groups/negative/positive`.",
        "",
        *_fold_table(summary["cv"]),
        "",
        "Each outer training pool has one frozen group-aware inner validation partition. Candidate configurations are selected there by PR-AUC; the selected configuration then receives a positive-F1 threshold on the same inner validation. The selected configuration is refit on complete outer_train before one outer_validation evaluation. Outer validation is forbidden for selection.",
        "",
        "## Thresholds and metrics",
        "",
        "- Threshold candidates: `0.05, 0.10, ..., 0.95`.",
        "- Primary threshold objective: positive-class F1 on inner validation only.",
        "- Tie-break: higher recall, then closest to 0.5, then smaller threshold.",
        "- Primary metrics: PR-AUC and positive-class F1.",
        "- Secondary metrics: ROC-AUC, precision, recall, F2, balanced accuracy, and MCC.",
        "- Side Effect F2 is auxiliary reporting, not a post-hoc threshold objective.",
        "- Uncomputable metrics are marked not computable and never imputed.",
        "- Pooled OOF metrics concatenate exactly one outer-validation prediction per eligible trajectory and are reported separately from per-fold values and mean ± standard deviation.",
        "- In a single-class LOBO holdout, all ordinary predictive metrics are NA. Only predicted-positive rate, mean predicted probability, and—when negatives exist—false-positive rate and specificity may be reported.",
        "",
        "## Four-group primary LOBO",
        "",
        *_lobo_table(summary["lobo_primary"]),
        "",
        "## Five-group sensitivity LOBO",
        "",
        *_lobo_table(summary["lobo_secondary"]),
        "",
        "Primary LOBO merges WorkArena L1/L2 under `workarena`; sensitivity LOBO keeps `workarena_l1` and `workarena_l2` separate.",
        "",
        "## First-round baseline boundary",
        "",
        "Registered only, not executed: B0 most-frequent Dummy; B1 prior Dummy; B2 leak-safe structural statistics + Logistic Regression; B3 primary-view TF-IDF + Logistic Regression. The finite spaces are frozen in `configs/baseline_registry.yaml`.",
        "",
        "Only `primary_with_natural_errors` is permitted in the first round. Reasoning and error ablation remain later pre-registered sensitivity analyses.",
        "",
        "## Test sealing",
        "",
        "Test trajectory content, labels, predictions, and metrics remain inaccessible. The identifier-only sealed manifest is read solely to assert zero key overlap.",
        "",
    ])
    return "\n".join(lines)


def render_audit(summary: Mapping[str, Any], drift_rows: Sequence[Mapping[str, Any]]) -> str:
    """Render the human-readable pre-baseline audit."""
    terminal = summary["terminal_audit"]
    literal = summary["benchmark_literal_audit"]
    view = summary["view_audit"]
    lines = [
        "# Stage A1.1 Pre-Baseline Audit",
        "",
        "## Stage decision",
        "",
        f"**{summary['stage_decision']}**",
        "",
        "This is an evidence recommendation. Human approval is required before any baseline execution.",
        "",
        "## Group-key audit",
        "",
        f"- Base dev task groups: {summary['group_key_audit']['task_groups']}; group-size distribution: `{json.dumps(summary['group_key_audit']['group_size_distribution'], sort_keys=True)}`.",
        f"- Groups with all four models: {summary['group_key_audit']['groups_with_four_models']}; partial model coverage: {summary['group_key_audit']['groups_with_partial_model_coverage']}.",
        f"- Cross-benchmark normalized-task-ID collisions: {len(summary['group_key_audit']['cross_benchmark_normalized_task_id_collisions'])}; the benchmark component remains mandatory.",
        "",
        "## Terminal terminology correction",
        "",
        f"- `last_nonempty_action`: {terminal['last_nonempty_action_count']}/196. It is only the last nonempty action and does not imply success or normal termination.",
        f"- `last_nonempty_observation`: {terminal['last_nonempty_observation_count']}/196.",
        f"- `explicit_termination_signal`: {terminal['explicit_termination_signal_count']}/196, limited to `send_msg_to_user` and `report_infeasible`.",
        "- The historical cleaned field `termination_signal` is a non-destructive alias for `explicit_termination_signal`.",
        "",
        "## Four-group schema-drift review",
        "",
        "| Field | Type | Occurrences | Trajectories | Current policy | Decision |",
        "|---|---|---:|---:|---|---|",
    ]
    for row in drift_rows:
        lines.append(
            f"| `{row['field_path']}` | {row['observed_type']} | {row['occurrence_count']} | {row['trajectory_count']} | {row['current_policy']} | {row['final_decision']} |"
        )
    lines.extend([
        "",
        "All four remain excluded. They are raw accessibility-tree internals or metadata type variants; `axtree_pruned` and the shared cleaned schema remain intact. The field whitelist was not expanded.",
        "",
        "## WorkArena literal provenance",
        "",
        f"- Affected trajectories: {literal['affected_trajectories']}; audited field rows: {literal['audit_rows']}; literal occurrences: {literal['literal_occurrences']}.",
        f"- Field distribution: `{json.dumps(literal['field_occurrences'], sort_keys=True)}`.",
        "- Every occurrence originates from frozen allowlisted task/environment text. Metadata mutation leaves serialization byte-identical, so no serializer injection was found.",
        "- Natural text is retained unchanged. A uniform `benchmark_literal_redacted` view is only a future sensitivity candidate and was not generated.",
        "",
        "## Natural errors and reasoning",
        "",
        f"- Natural errors: {view['natural_error_trajectories']}/196 trajectories and {view['natural_error_steps']} steps. Primary/error-ablation differences occur in exactly {view['primary_error_ablation_differing_trajectories']} trajectories.",
        f"- Reasoning: {view['reasoning_trajectories']}/196 trajectories and {view['reasoning_steps']} steps; it remains sensitivity-only.",
        "",
        "## Leave-One-Model-Out feasibility",
        "",
        f"- Status: **{summary['leave_one_model_out']['recommended_status']}**.",
        "- The meta-llama source lacks VisualWebArena coverage, so not every held-out model validation domain covers all four primary Benchmarks. Training domains still retain all primary Benchmarks; detailed per-target class counts are machine-readable.",
        "",
        "## Conditions and stop boundary",
        "",
    ])
    lines.extend(f"- {condition}" for condition in summary["conditions"])
    lines.extend([
        "",
        "No Dummy, TF-IDF, Logistic Regression, other estimator, prediction probability, or predictive metric was run. Test remains sealed.",
        "",
    ])
    return "\n".join(lines)


def run() -> int:
    """Verify the frozen manifests; generation was retired after Stage A1.1."""
    from verify_evaluation_protocol import verify_frozen_manifests

    observed = verify_frozen_manifests()
    print(json.dumps({
        "status": "PASS",
        "mode": "verification_only",
        "regeneration_allowed": False,
        "verified_manifests": observed,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(run())
