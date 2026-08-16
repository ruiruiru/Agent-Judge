#!/usr/bin/env python3
"""Build the Stage A0.2 metadata-only analysis index for AgentRewardBench."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence


ANNOTATIONS_COLUMNS = [
    "annotator_name",
    "benchmark",
    "task_id",
    "model_name",
    "exp_name",
    "trajectory_success",
    "trajectory_side_effect",
    "trajectory_optimality",
    "trajectory_looping",
]
SPLITS_COLUMNS = ["task_id", "benchmark", "split"]
ALLOWED_SPLITS = {"dev", "test"}

LABELS: dict[str, dict[str, Any]] = {
    "success": {
        "field": "trajectory_success",
        "mapping": {"Successful": 1, "Unsuccessful": 0, "Unsure": None},
    },
    "side_effect": {
        "field": "trajectory_side_effect",
        "mapping": {"Yes": 1, "No": 0, "Unsure": None},
    },
    "looping": {
        "field": "trajectory_looping",
        "mapping": {"Yes": 1, "No": 0},
    },
}

OFFICIAL_PRIMARY_RULE_URL = (
    "https://github.com/McGill-NLP/agent-reward-bench/blob/"
    "f838338886d723d40b586309465a38277803d9e6/agent_reward_bench/judge/utils.py"
)
OFFICIAL_SCORING_RULE_URL = (
    "https://github.com/McGill-NLP/agent-reward-bench/blob/"
    "f838338886d723d40b586309465a38277803d9e6/scripts/score_judgments.py"
)
OFFICIAL_WORKARENA_RULE_URL = (
    "https://github.com/McGill-NLP/agent-reward-bench/blob/"
    "f838338886d723d40b586309465a38277803d9e6/"
    "agent_reward_bench/processing/filter_workarena.py"
)

OUTPUT_PATHS = [
    Path("docs/analysis_unit_policy.md"),
    Path("artifacts/duplicate_annotation_audit.csv"),
    Path("artifacts/dev_analysis_index.csv"),
    Path("artifacts/test_manifest.csv"),
    Path("artifacts/analysis_index_summary.json"),
]


class AnalysisIndexError(RuntimeError):
    """Raised when the Stage A0.2 contract cannot be confirmed."""


def normalize_task_id(value: str) -> str:
    """Apply the fixed official task-id normalization from Stage A0.1."""
    return value.strip().lower().replace(".improved", "").replace(".resized", "")


def sha256_file(path: Path) -> str:
    """Return the SHA256 digest of a local file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path, expected_columns: Sequence[str]) -> list[dict[str, str]]:
    """Read a CSV and fail on any schema or row-width ambiguity."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(expected_columns):
            raise AnalysisIndexError(
                f"Unexpected columns in {path}: {reader.fieldnames}; expected {list(expected_columns)}"
            )
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise AnalysisIndexError(f"Malformed CSV row at {path}:{line_number}")
            rows.append(dict(row))
    return rows


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 text atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
    os.replace(temporary, path)


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    """Write a deterministic UTF-8 CSV atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def trajectory_key(benchmark: str, task_id: str, model_name: str) -> str:
    """Serialize the frozen three-field trajectory key."""
    values = [benchmark.strip(), normalize_task_id(task_id), model_name.strip()]
    if any("::" in value for value in values):
        raise AnalysisIndexError("A trajectory-key component contains the reserved delimiter '::'")
    return "::".join(values)


def classify_values(values: list[str]) -> str:
    """Classify the annotation multiplicity/status for one target."""
    if "Unsure" in values:
        return "contains_unsure"
    if len(values) == 1:
        return "single_annotation"
    if len(set(values)) == 1:
        return "duplicate_agreement"
    return "duplicate_disagreement"


def resolve_primary_audit_label(
    values: list[str], mapping: dict[str, int | None]
) -> int | None:
    """Return the fixed official primary value for audit only."""
    primary = values[0]
    if primary not in mapping:
        raise AnalysisIndexError(f"Undefined label value: {primary!r}")
    return mapping[primary]


def resolve_main_label(
    values: list[str], status: str, mapping: dict[str, int | None]
) -> tuple[int | None, bool]:
    """Resolve the conservative main-experiment label and eligibility."""
    if status not in {"single_annotation", "duplicate_agreement"}:
        return None, False
    resolved = mapping[values[0]]
    if resolved not in {0, 1}:
        raise AnalysisIndexError(
            f"Eligible status {status!r} did not resolve to a binary label"
        )
    return resolved, True


def primary_group(split_namespace: str) -> str:
    """Map five official split namespaces to four environment-level groups."""
    if split_namespace in {"workarena_l1", "workarena_l2"}:
        return "workarena"
    return split_namespace


def label_counts(entries: Iterable[dict[str, Any]], target: str) -> dict[str, Any]:
    """Count resolved labels and unavailable statuses for one target."""
    rows = list(entries)
    for row in rows:
        label = row[f"{target}_label"]
        eligible = row[f"{target}_eligible_main"]
        status = row[f"{target}_status"]
        expected_eligible = status in {"single_annotation", "duplicate_agreement"}
        if eligible != expected_eligible:
            raise AnalysisIndexError(
                f"{target} eligibility/status mismatch for {row['trajectory_key']}: "
                f"status={status}, eligible={eligible}"
            )
        if eligible and label not in {0, 1}:
            raise AnalysisIndexError(
                f"Eligible {target} trajectory has non-binary label: {row['trajectory_key']}"
            )
        if not eligible and label is not None:
            raise AnalysisIndexError(
                f"Ineligible {target} trajectory retains a main label: {row['trajectory_key']}"
            )
    values = [
        row[f"{target}_label"]
        for row in rows
        if row[f"{target}_eligible_main"]
    ]
    positive = sum(value == 1 for value in values)
    negative = sum(value == 0 for value in values)
    return {
        "trajectory_count": len(rows),
        "valid_count": len(values),
        "positive_count": positive,
        "negative_count": negative,
        "unavailable_count": len(rows) - len(values),
        "positive_rate": positive / len(values) if values else None,
    }


def grouped_label_statistics(
    entries: list[dict[str, Any]], group_field: str
) -> dict[str, dict[str, dict[str, Any]]]:
    """Compute per-target counts for each value of a grouping field."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        groups[str(entry[group_field])].append(entry)
    return {
        group: {target: label_counts(rows, target) for target in LABELS}
        for group, rows in sorted(groups.items())
    }


def build_entries(
    annotations: list[dict[str, str]], splits: list[dict[str, str]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse annotation rows into one metadata record per trajectory."""
    split_by_task: dict[str, dict[str, str]] = {}
    for row in splits:
        normalized = normalize_task_id(row["task_id"])
        if normalized in split_by_task:
            raise AnalysisIndexError(f"Duplicate normalized split task_id: {normalized}")
        if row["split"] not in ALLOWED_SPLITS:
            raise AnalysisIndexError(f"Undefined official split: {row['split']!r}")
        split_by_task[normalized] = row

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    key_parts: dict[str, tuple[str, str, str]] = {}
    for row in annotations:
        key = trajectory_key(row["benchmark"], row["task_id"], row["model_name"])
        groups[key].append(row)
        key_parts[key] = (
            row["benchmark"].strip(),
            normalize_task_id(row["task_id"]),
            row["model_name"].strip(),
        )

    entries: list[dict[str, Any]] = []
    validation = {
        "keys_with_multiple_exp_name": 0,
        "keys_with_multiple_raw_task_id": 0,
        "keys_with_repeated_annotator": 0,
        "keys_with_more_than_two_annotations": 0,
        "unmatched_split_keys": 0,
    }
    for key in sorted(groups):
        rows = groups[key]
        benchmark, normalized_task, model_name = key_parts[key]
        exp_names = {row["exp_name"] for row in rows}
        raw_task_ids = {row["task_id"] for row in rows}
        annotators = [row["annotator_name"] for row in rows]
        if len(exp_names) != 1:
            validation["keys_with_multiple_exp_name"] += 1
        if len(raw_task_ids) != 1:
            validation["keys_with_multiple_raw_task_id"] += 1
        if len(set(annotators)) != len(annotators):
            validation["keys_with_repeated_annotator"] += 1
        if len(rows) > 2:
            validation["keys_with_more_than_two_annotations"] += 1
        split_row = split_by_task.get(normalized_task)
        if split_row is None:
            validation["unmatched_split_keys"] += 1
            continue

        split_namespace = split_row["benchmark"]
        expected_original = (
            "workarena" if split_namespace in {"workarena_l1", "workarena_l2"} else split_namespace
        )
        if benchmark != expected_original:
            raise AnalysisIndexError(
                f"Benchmark mismatch for {key}: annotation={benchmark}, split={split_namespace}"
            )

        entry: dict[str, Any] = {
            "trajectory_key": key,
            "benchmark_original": benchmark,
            "benchmark_split_namespace": split_namespace,
            "benchmark_group_primary": primary_group(split_namespace),
            "benchmark_group_secondary": split_namespace,
            "task_id": normalized_task,
            "model_name": model_name,
            "exp_name": next(iter(exp_names)) if len(exp_names) == 1 else "",
            "official_split": split_row["split"],
            "annotation_count": len(rows),
            "annotator_count": len(set(annotators)),
            "primary_annotator": annotators[0],
            "secondary_annotators": json.dumps(annotators[1:], ensure_ascii=False),
        }
        for target, contract in LABELS.items():
            values = [row[contract["field"]] for row in rows]
            allowed = set(contract["mapping"])
            unknown = [value for value in values if value not in allowed]
            if unknown:
                raise AnalysisIndexError(
                    f"Undefined {contract['field']} values for {key}: {unknown}"
                )
            status = classify_values(values)
            entry[f"{target}_values"] = json.dumps(values, ensure_ascii=False)
            entry[f"{target}_status"] = status
            entry[f"{target}_primary_label_audit_only"] = resolve_primary_audit_label(
                values, contract["mapping"]
            )
            main_label, eligible_main = resolve_main_label(
                values, status, contract["mapping"]
            )
            entry[f"{target}_label"] = main_label
            entry[f"{target}_eligible_main"] = eligible_main
        entries.append(entry)

    if any(validation.values()):
        raise AnalysisIndexError(f"Trajectory-key validation failed: {validation}")
    if len(entries) != len(groups):
        raise AnalysisIndexError("Not every trajectory key produced an analysis entry")
    if len({entry["trajectory_key"] for entry in entries}) != len(entries):
        raise AnalysisIndexError("Duplicate trajectory_key values remain after collapsing")
    return entries, validation


def status_counts(entries: list[dict[str, Any]], target: str) -> dict[str, int]:
    """Count annotation statuses for a target."""
    expected = [
        "single_annotation",
        "duplicate_agreement",
        "duplicate_disagreement",
        "contains_unsure",
    ]
    counts = Counter(entry[f"{target}_status"] for entry in entries)
    return {name: counts.get(name, 0) for name in expected}


def workarena_audit(entries: list[dict[str, Any]], splits: list[dict[str, str]]) -> dict[str, Any]:
    """Audit WorkArena L1/L2 mapping and label distributions."""
    task_sets = {
        namespace: {
            normalize_task_id(row["task_id"])
            for row in splits
            if row["benchmark"] == namespace
        }
        for namespace in ["workarena_l1", "workarena_l2"]
    }
    groups = {
        namespace: [
            entry for entry in entries if entry["benchmark_group_secondary"] == namespace
        ]
        for namespace in task_sets
    }
    return {
        "official_semantics": {
            "finding": (
                "The fixed official code identifies L2 via the WorkArena 'level' field and "
                "scores L1/L2 as WorkArena/WorkArena++; both use the WorkArena ServiceNow environment."
            ),
            "workarena_rule_url": OFFICIAL_WORKARENA_RULE_URL,
            "scoring_rule_url": OFFICIAL_SCORING_RULE_URL,
        },
        "task_counts": {name: len(tasks) for name, tasks in task_sets.items()},
        "overlapping_task_ids": sorted(task_sets["workarena_l1"] & task_sets["workarena_l2"]),
        "unique_trajectory_counts": {name: len(rows) for name, rows in groups.items()},
        "models": {
            name: sorted({entry["model_name"] for entry in rows}) for name, rows in groups.items()
        },
        "label_counts_before_merge": {
            name: {target: label_counts(rows, target) for target in LABELS}
            for name, rows in groups.items()
        },
        "label_counts_after_benchmark_group_merge": {
            target: label_counts(groups["workarena_l1"] + groups["workarena_l2"], target)
            for target in LABELS
        },
    }


def markdown_table(headers: Sequence[str], rows: Iterable[Iterable[Any]]) -> str:
    """Render a Markdown table."""
    output = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    output.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return "\n".join(output)


def build_policy(summary: dict[str, Any]) -> str:
    """Render the human-readable analysis-unit policy."""
    status_rows = []
    for target in LABELS:
        counts = summary["annotation_status_counts"][target]
        status_rows.append(
            (
                target,
                counts["single_annotation"],
                counts["duplicate_agreement"],
                counts["duplicate_disagreement"],
                counts["contains_unsure"],
                summary["overall_label_counts"][target]["valid_count"],
                f"{summary['overall_label_counts'][target]['positive_rate']:.6f}",
            )
        )
    workarena_rows = []
    for namespace in ["workarena_l1", "workarena_l2"]:
        workarena_rows.append(
            (
                namespace,
                summary["workarena"]["task_counts"][namespace],
                summary["workarena"]["unique_trajectory_counts"][namespace],
                len(summary["workarena"]["models"][namespace]),
            )
        )

    return f"""# Stage A0.2 Analysis Unit and Benchmark Group Policy

## Stage decision

**PASS**

Stage A0.2 freezes metadata analysis units and grouping only. It does not authorize full trajectory download, feature engineering, baselines, training, or model evaluation.

Known limitations retained for later research-lead review:

1. The official primary annotation is operationally defined by fixed CSV encounter order, not by an adjudication record or a documented annotator-quality hierarchy.
2. WorkArena L1/L2 are retained separately for sensitivity analysis because the official scorer names them WorkArena and WorkArena++, even though both are levels in the same WorkArena/ServiceNow environment.
3. Aggregate test-label exposure occurred for audit only; no test labels may enter regular development files or method decisions.

## Frozen trajectory unit

`trajectory_key = (benchmark_original, normalized_task_id, model_name)`

The serialized index key is `benchmark_original::normalized_task_id::model_name`. Across 1,408 annotation rows this yields **{summary['trajectory_counts']['after_collapse']}** unique trajectories. Every repeated key has exactly two distinct annotators, one `exp_name`, and one raw task ID. No key contains evidence of multiple independent runs, and the official CSV exposes no separate trajectory ID, run ID, or path field.

`exp_name` is retained as metadata but is not added to the key because it is constant within every key and identifies benchmark/model experiment groups rather than distinguishing trajectories.

## Official annotation rule and frozen resolution

The fixed official utility labels the first occurrence of `(benchmark, model_name, task_id)` as primary and later occurrences as secondary. The fixed scorer evaluates human labels from primary records. Evidence:

- [Official annotator utility]({OFFICIAL_PRIMARY_RULE_URL})
- [Official scoring script]({OFFICIAL_SCORING_RULE_URL})

Frozen A0.2-Fix behavior:

- One row becomes `single_annotation`.
- Repeated equal values become `duplicate_agreement` and are folded to one trajectory.
- Repeated unequal values become `duplicate_disagreement`; the main-experiment label is empty and `eligible_main` is false.
- Any annotation set containing `Unsure` becomes `contains_unsure` and that target is unavailable.
- Resolution is target-specific. No trajectory is removed from other targets because one target is unavailable or disputed.
- No voting, random selection, relabeling, or duplicate weighting is permitted.
- The fixed official primary value is retained only as `<target>_primary_label_audit_only` in the audit file. It never appears in the dev training interface.

{markdown_table(['Target', 'Single', 'Duplicate agreement', 'Duplicate disagreement', 'Contains Unsure', 'Valid trajectories', 'Positive rate'], status_rows)}

`duplicate_annotation_audit.csv` is audit-only. It must never be used directly as training data.

Every future training-set constructor must require both `<target>_eligible_main == true` and `<target>_label in {{0, 1}}`. Checking only that a label is non-empty is prohibited.

## Downstream misuse audit

The Stage A0.2-Fix repository scan found no training implementation using `dropna`, `notna`, `fillna(0/1)`, `first()`, or `iloc[0]` to select target labels. References to `primary_label` are confined to the explicitly audit-only field and tests that prevent it from entering `test_manifest.csv`. No training code exists at this stage.

## Benchmark namespaces

Every trajectory retains:

- `benchmark_original`: the annotation value.
- `benchmark_split_namespace`: the official `splits.csv` value.
- `benchmark_group_primary`: four environment-level groups, merging `workarena_l1` and `workarena_l2` into `workarena`.
- `benchmark_group_secondary`: five official split namespaces, retaining WorkArena L1/L2 separately.

The fixed official WorkArena processing code selects L2 with a `level == l2` field, while the scorer names the two groups WorkArena and WorkArena++. Both are backed by the WorkArena ServiceNow environment. The four-group merge is therefore frozen for the primary cross-environment analysis, while the official five-way split remains mandatory as a sensitivity grouping.

{markdown_table(['Namespace', 'Tasks', 'Unique trajectories', 'Models'], workarena_rows)}

WorkArena L1/L2 overlapping normalized task IDs: **{len(summary['workarena']['overlapping_task_ids'])}**.

## Analysis index files

- `dev_analysis_index.csv`: one labeled row per unique dev trajectory after fixed resolution.
- `test_manifest.csv`: identifiers and grouping metadata only; it contains no target labels, raw values, or target statuses.
- `duplicate_annotation_audit.csv`: one audit row per unique trajectory, including raw annotation sets and statuses.

## Test sealing

Test labels received aggregate, audit-only exposure during Stage A0.1. No model, feature, threshold, hyperparameter, or research decision was tuned using test performance.

After Stage A0.2, routine development may use only the labeled dev analysis index. The test manifest contains identifiers and grouping fields only. Complete test labels may be read only by a future final, locked evaluation flow explicitly approved by the research lead.

## Reproducibility and limitations

- Inputs are the A0.1 files pinned by `artifacts/source_manifest.json`; hashes are verified before indexing.
- Output generation is deterministic and requires no network access.
- The primary-label rule is official but position-based and not adjudicated; it is retained for audit only and is not a main-experiment eligibility rule.
- This stage does not establish full-trajectory availability, parsing success, feature validity, leakage safety, or readiness for model experiments.
"""


def build_analysis_index(repo_root: Path, output_root: Path) -> dict[str, Any]:
    """Build every Stage A0.2 artifact from the fixed local A0.1 metadata."""
    repo_root = repo_root.resolve()
    output_root = output_root.resolve()
    manifest_path = repo_root / "artifacts/source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("github_commit") != "f838338886d723d40b586309465a38277803d9e6":
        raise AnalysisIndexError("Unexpected GitHub commit in source manifest")
    if manifest.get("huggingface_revision") != "b6d17e646009d6cb63d5dd7be78807b680693f61":
        raise AnalysisIndexError("Unexpected Hugging Face revision in source manifest")

    annotations_path = repo_root / manifest["annotations_file"]
    splits_path = repo_root / manifest["splits_file"]
    for name, path in [("annotations.csv", annotations_path), ("splits.csv", splits_path)]:
        expected_hash = manifest["file_sha256"][name]
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise AnalysisIndexError(
                f"SHA256 mismatch for {path}: expected {expected_hash}, got {actual_hash}"
            )

    annotations = read_csv(annotations_path, ANNOTATIONS_COLUMNS)
    splits = read_csv(splits_path, SPLITS_COLUMNS)
    entries, key_validation = build_entries(annotations, splits)

    duplicate_rows: list[dict[str, Any]] = []
    for entry in entries:
        row = {
            "trajectory_key": entry["trajectory_key"],
            "benchmark": entry["benchmark_original"],
            "benchmark_split_namespace": entry["benchmark_split_namespace"],
            "task_id": entry["task_id"],
            "model_name": entry["model_name"],
            "exp_name": entry["exp_name"],
            "official_split": entry["official_split"],
            "annotation_count": entry["annotation_count"],
            "annotator_count": entry["annotator_count"],
            "primary_annotator": entry["primary_annotator"],
            "secondary_annotators": entry["secondary_annotators"],
        }
        for target in LABELS:
            row[f"{target}_values"] = entry[f"{target}_values"]
            row[f"{target}_status"] = entry[f"{target}_status"]
            row[f"{target}_eligible_main"] = str(
                entry[f"{target}_eligible_main"]
            ).lower()
            row[f"{target}_label"] = (
                "" if entry[f"{target}_label"] is None else entry[f"{target}_label"]
            )
            row[f"{target}_primary_label_audit_only"] = (
                ""
                if entry[f"{target}_primary_label_audit_only"] is None
                else entry[f"{target}_primary_label_audit_only"]
            )
        duplicate_rows.append(row)

    index_fields = [
        "trajectory_key",
        "benchmark_original",
        "benchmark_split_namespace",
        "benchmark_group_primary",
        "benchmark_group_secondary",
        "task_id",
        "model_name",
        "official_split",
        "annotation_count",
        "success_label",
        "success_status",
        "success_eligible_main",
        "side_effect_label",
        "side_effect_status",
        "side_effect_eligible_main",
        "looping_label",
        "looping_status",
        "looping_eligible_main",
    ]
    dev_rows = []
    for entry in entries:
        if entry["official_split"] != "dev":
            continue
        dev_rows.append(
            {
                field: (
                    ""
                    if entry[field] is None
                    else str(entry[field]).lower()
                    if field.endswith("_eligible_main")
                    else entry[field]
                )
                for field in index_fields
            }
        )

    test_fields = [
        "trajectory_key",
        "benchmark_original",
        "benchmark_split_namespace",
        "benchmark_group_primary",
        "benchmark_group_secondary",
        "task_id",
        "model_name",
        "official_split",
        "annotation_count",
    ]
    test_rows = [
        {field: entry[field] for field in test_fields}
        for entry in entries
        if entry["official_split"] == "test"
    ]

    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "stage": "A0.2",
        "stage_decision": "PASS",
        "source_revision": {
            "github_commit": manifest["github_commit"],
            "huggingface_revision": manifest["huggingface_revision"],
        },
        "trajectory_key": {
            "fields": ["benchmark_original", "normalized_task_id", "model_name"],
            "serialization": "benchmark_original::normalized_task_id::model_name",
            "official_primary_key_order": ["benchmark", "model_name", "task_id"],
            "key_validation": key_validation,
        },
        "resolution_policy": {
            "strategy": "consensus_only_main_eligibility",
            "contains_unsure": "target unavailable",
            "duplicate_agreement": "fold to one trajectory",
            "duplicate_disagreement": "main label unavailable; official primary retained for audit only",
            "main_eligibility_rule": (
                "eligible_main is true only for single_annotation or duplicate_agreement "
                "with a binary label"
            ),
            "official_primary_rule_url": OFFICIAL_PRIMARY_RULE_URL,
            "official_scoring_rule_url": OFFICIAL_SCORING_RULE_URL,
        },
        "trajectory_counts": {
            "annotation_rows_before_collapse": len(annotations),
            "after_collapse": len(entries),
            "dev": len(dev_rows),
            "test": len(test_rows),
            "duplicate_groups": sum(entry["annotation_count"] > 1 for entry in entries),
            "extra_annotation_rows": len(annotations) - len(entries),
        },
        "annotation_status_counts": {
            target: status_counts(entries, target) for target in LABELS
        },
        "overall_label_counts": {
            target: label_counts(entries, target) for target in LABELS
        },
        "statistics": {
            "by_official_split": grouped_label_statistics(entries, "official_split"),
            "by_benchmark_group_primary": grouped_label_statistics(
                entries, "benchmark_group_primary"
            ),
            "by_benchmark_group_secondary": grouped_label_statistics(
                entries, "benchmark_group_secondary"
            ),
            "by_model": grouped_label_statistics(entries, "model_name"),
        },
        "benchmark_groups": {
            "primary": sorted({entry["benchmark_group_primary"] for entry in entries}),
            "secondary": sorted({entry["benchmark_group_secondary"] for entry in entries}),
            "all_trajectories_mapped": True,
        },
        "workarena": workarena_audit(entries, splits),
        "test_sealing": {
            "aggregate_audit_exposure_statement": (
                "Test labels received aggregate, audit-only exposure during Stage A0.1. "
                "No model, feature, threshold, hyperparameter, or research decision was "
                "tuned using test performance."
            ),
            "test_manifest_contains_target_labels": False,
            "test_metrics_computed": False,
        },
        "known_limitations": [
            "Official primary labels are fixed by CSV encounter order and are audit-only.",
            "WorkArena L1/L2 remain separate in the required secondary sensitivity grouping.",
            "No full-trajectory or model readiness conclusion is made in Stage A0.2.",
        ],
    }

    duplicate_fields = [
        "trajectory_key",
        "benchmark",
        "benchmark_split_namespace",
        "task_id",
        "model_name",
        "exp_name",
        "official_split",
        "annotation_count",
        "annotator_count",
        "primary_annotator",
        "secondary_annotators",
        "success_values",
        "success_primary_label_audit_only",
        "success_label",
        "success_status",
        "success_eligible_main",
        "side_effect_values",
        "side_effect_primary_label_audit_only",
        "side_effect_label",
        "side_effect_status",
        "side_effect_eligible_main",
        "looping_values",
        "looping_primary_label_audit_only",
        "looping_label",
        "looping_status",
        "looping_eligible_main",
    ]
    write_csv(
        output_root / "artifacts/duplicate_annotation_audit.csv",
        duplicate_fields,
        duplicate_rows,
    )
    write_csv(output_root / "artifacts/dev_analysis_index.csv", index_fields, dev_rows)
    write_csv(output_root / "artifacts/test_manifest.csv", test_fields, test_rows)
    atomic_write_text(
        output_root / "artifacts/analysis_index_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(output_root / "docs/analysis_unit_policy.md", build_policy(summary))
    return summary


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    default_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=default_root,
        help="Output root; tests may use a temporary directory.",
    )
    return parser.parse_args()


def main() -> int:
    """Build Stage A0.2 outputs and print a compact summary."""
    args = parse_args()
    summary = build_analysis_index(args.repo_root, args.output_root)
    print(
        json.dumps(
            {
                "stage_decision": summary["stage_decision"],
                "trajectory_counts": summary["trajectory_counts"],
                "benchmark_groups": summary["benchmark_groups"],
                "outputs": [str(path).replace("\\", "/") for path in OUTPUT_PATHS],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AnalysisIndexError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2) from exc
