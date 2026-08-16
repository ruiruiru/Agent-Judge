#!/usr/bin/env python3
"""Lock and audit the AgentRewardBench metadata contract for D9-R1 Stage A0.1.

This script downloads only the three small metadata files authorized by
STAGE_A0_1_DATA_CONTRACT.md. It does not download trajectories, judgments,
screenshots, or any model artifacts, and it performs no model evaluation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import stat
import sys
import tempfile
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


GITHUB_REPOSITORY = "https://github.com/McGill-NLP/agent-reward-bench"
GITHUB_COMMIT = "f838338886d723d40b586309465a38277803d9e6"
HUGGINGFACE_REPOSITORY = "McGill-NLP/agent-reward-bench"
HUGGINGFACE_REVISION = "b6d17e646009d6cb63d5dd7be78807b680693f61"
USER_AGENT = "Agent-Judge-D9-R1-Stage-A0.1"

ANNOTATIONS_RELATIVE_PATH = "agent_reward_bench/data/annotations.csv"
SPLITS_RELATIVE_PATH = "agent_reward_bench/data/splits.csv"

EXPECTED_ANNOTATION_COLUMNS = [
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
EXPECTED_SPLIT_COLUMNS = ["task_id", "benchmark", "split"]
ALLOWED_SPLITS = {"dev", "test"}

LABEL_CONTRACT: dict[str, dict[str, Any]] = {
    "Success": {
        "field": "trajectory_success",
        "mapping": {"Successful": 1, "Unsuccessful": 0, "Unsure": None},
    },
    "Side Effect": {
        "field": "trajectory_side_effect",
        "mapping": {"Yes": 1, "No": 0, "Unsure": None},
    },
    "Repetitiveness / Looping": {
        "field": "trajectory_looping",
        "mapping": {"Yes": 1, "No": 0},
    },
}
OPTIMALITY_FIELD = "trajectory_optimality"


class ContractError(RuntimeError):
    """Raised when an official metadata invariant cannot be confirmed."""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/agent_reward_bench/a0_1"),
    )
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    return parser.parse_args()


def fetch_bytes(url: str) -> bytes:
    """Fetch a small official metadata resource."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ContractError(f"Metadata query failed for {url}: {exc}") from exc


def fetch_json(url: str) -> dict[str, Any]:
    """Fetch and parse a JSON metadata endpoint."""
    try:
        value = json.loads(fetch_bytes(url).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"Invalid JSON metadata returned by {url}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"Expected a JSON object from {url}")
    return value


def sha256_bytes(data: bytes) -> str:
    """Return a lowercase SHA256 digest for bytes."""
    return hashlib.sha256(data).hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write bytes atomically, refusing to replace different existing raw data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        if existing != data:
            raise ContractError(f"Refusing to overwrite differing file: {path}")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(data)
    os.replace(temp_path, path)


def atomic_write_text(path: Path, text: str) -> None:
    """Write UTF-8 text atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(encoded)
    os.replace(temp_path, path)


def freeze_raw_file(path: Path) -> None:
    """Apply read-only file semantics to a downloaded raw metadata file."""
    path.chmod(stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)


def read_csv_bytes(data: bytes, source_name: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV bytes without silently skipping malformed records."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContractError(f"{source_name} is not valid UTF-8: {exc}") from exc
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        raise ContractError(f"{source_name} has no CSV header")
    rows: list[dict[str, str]] = []
    for line_number, row in enumerate(reader, start=2):
        if None in row:
            raise ContractError(f"{source_name}:{line_number} has extra CSV fields")
        if any(value is None for value in row.values()):
            raise ContractError(f"{source_name}:{line_number} has missing CSV fields")
        rows.append({key: value for key, value in row.items()})
    return list(reader.fieldnames), rows


def normalize_task_id(value: str) -> str:
    """Normalize observed annotation-only task-id decorations for split joining."""
    normalized = value.strip().lower()
    normalized = normalized.replace(".improved.", ".")
    normalized = normalized.replace(".resized.", ".")
    return normalized


def field_profile(rows: list[dict[str, str]], field: str) -> dict[str, Any]:
    """Compute compact metadata statistics for a CSV field."""
    values = [row[field] for row in rows]
    stripped = [value.strip() for value in values]
    return {
        "data_type": "string",
        "row_count": len(values),
        "missing_or_empty_count": sum(not value for value in stripped),
        "missing_or_empty_rate": (sum(not value for value in stripped) / len(values))
        if values
        else None,
        "unique_value_count": len(set(stripped)),
        "min_length": min((len(value) for value in stripped), default=0),
        "max_length": max((len(value) for value in stripped), default=0),
    }


def counter_dict(values: Iterable[str]) -> dict[str, int]:
    """Return a stable, sorted value-count mapping."""
    return dict(sorted(Counter(values).items(), key=lambda item: item[0]))


def mapped_label(value: str, mapping: dict[str, int | None]) -> int | None | str:
    """Apply an exact official label mapping, distinguishing unknown values."""
    if value in mapping:
        return mapping[value]
    return "UNKNOWN"


def label_summary(
    rows: list[dict[str, str]],
    target: str,
    field: str,
    mapping: dict[str, int | None],
) -> dict[str, Any]:
    """Summarize one target at annotation-row level."""
    raw_counts = counter_dict(row[field] or "<EMPTY>" for row in rows)
    mapped = [mapped_label(row[field], mapping) for row in rows]
    positive = sum(value == 1 for value in mapped)
    negative = sum(value == 0 for value in mapped)
    excluded = sum(value is None for value in mapped)
    unknown = sum(value == "UNKNOWN" for value in mapped)
    valid = positive + negative
    return {
        "target": target,
        "field": field,
        "raw_value_counts": raw_counts,
        "positive_count": positive,
        "negative_count": negative,
        "excluded_unsure_count": excluded,
        "unknown_count": unknown,
        "valid_binary_count": valid,
        "positive_rate_among_valid": positive / valid if valid else None,
    }


def distribution_rows(
    annotations: list[dict[str, str]],
    split_by_task: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    """Build machine-readable label distributions by split and benchmark."""
    output: list[dict[str, Any]] = []
    scopes: list[tuple[str, str, str, list[dict[str, str]]]] = [
        ("overall", "ALL", "ALL", annotations)
    ]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in annotations:
        split_row = split_by_task[normalize_task_id(row["task_id"])]
        grouped[(split_row["split"].strip(), row["benchmark"].strip())].append(row)
    for (split_name, benchmark), rows in sorted(grouped.items()):
        scopes.append(("split_x_annotation_benchmark", split_name, benchmark, rows))

    for scope, split_name, benchmark, rows in scopes:
        for target, contract in LABEL_CONTRACT.items():
            field = contract["field"]
            mapping = contract["mapping"]
            summary = label_summary(rows, target, field, mapping)
            output.append(
                {
                    "scope": scope,
                    "split": split_name,
                    "annotation_benchmark": benchmark,
                    "target": target,
                    "field": field,
                    "positive_count": summary["positive_count"],
                    "negative_count": summary["negative_count"],
                    "excluded_unsure_count": summary["excluded_unsure_count"],
                    "unknown_count": summary["unknown_count"],
                    "valid_binary_count": summary["valid_binary_count"],
                    "positive_rate_among_valid": summary["positive_rate_among_valid"],
                }
            )
    return output


def analyze_duplicates(annotations: list[dict[str, str]]) -> dict[str, Any]:
    """Audit repeated trajectory keys without collapsing annotation rows."""
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in annotations:
        key = (
            row["benchmark"].strip(),
            normalize_task_id(row["task_id"]),
            row["model_name"].strip(),
        )
        groups[key].append(row)

    duplicate_groups = {key: rows for key, rows in groups.items() if len(rows) > 1}
    unexpected: list[dict[str, Any]] = []
    disagreement_counts = {target: 0 for target in [*LABEL_CONTRACT, "Optimality"]}
    disagreement_fields = {
        **{target: contract["field"] for target, contract in LABEL_CONTRACT.items()},
        "Optimality": OPTIMALITY_FIELD,
    }
    for key, rows in duplicate_groups.items():
        annotators = {row["annotator_name"].strip() for row in rows}
        experiments = {row["exp_name"].strip() for row in rows}
        if len(annotators) != len(rows) or len(experiments) != 1:
            unexpected.append(
                {
                    "benchmark": key[0],
                    "task_id": key[1],
                    "model_name": key[2],
                    "row_count": len(rows),
                    "annotator_count": len(annotators),
                    "experiment_count": len(experiments),
                }
            )
        for target, field in disagreement_fields.items():
            if len({row[field].strip() for row in rows}) > 1:
                disagreement_counts[target] += 1

    return {
        "trajectory_key_definition": ["benchmark", "normalized_task_id", "model_name"],
        "unique_trajectory_count": len(groups),
        "duplicate_trajectory_group_count": len(duplicate_groups),
        "extra_annotation_row_count": sum(len(rows) - 1 for rows in duplicate_groups.values()),
        "all_duplicate_groups_have_distinct_annotators": all(
            len({row["annotator_name"].strip() for row in rows}) == len(rows)
            for rows in duplicate_groups.values()
        ),
        "all_duplicate_groups_share_one_exp_name": all(
            len({row["exp_name"].strip() for row in rows}) == 1
            for rows in duplicate_groups.values()
        ),
        "duplicate_group_label_disagreements": disagreement_counts,
        "unexpected_duplicate_groups": unexpected,
    }


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    """Render a compact Markdown table."""
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def build_data_contract(manifest: dict[str, Any], audit: dict[str, Any]) -> str:
    """Build the human-readable Stage A0.1 data contract."""
    label_rows = []
    for target, contract in LABEL_CONTRACT.items():
        mapping_text = ", ".join(
            f"`{raw}` → {'missing/excluded' if mapped is None else mapped}"
            for raw, mapped in contract["mapping"].items()
        )
        label_rows.append((target, f"`{contract['field']}`", mapping_text))

    overall = {item["target"]: item for item in audit["labels"]["targets"]}
    count_rows = [
        (
            target,
            summary["positive_count"],
            summary["negative_count"],
            summary["excluded_unsure_count"],
            summary["unknown_count"],
            f"{summary['positive_rate_among_valid']:.6f}",
        )
        for target, summary in overall.items()
    ]
    benchmark_rows = [
        (name, values["annotation_rows"], values["unique_trajectories"])
        for name, values in audit["annotations"]["benchmark_counts"].items()
    ]
    split_rows = [
        (name, values["rows"], values["unique_tasks"])
        for name, values in audit["splits"]["split_counts"].items()
    ]

    return f"""# AgentRewardBench Data Contract — Stage A0.1

## Scope and evidence status

This document locks metadata only. No full trajectories, judgments, screenshots, features, models, baselines, or test-set model results were downloaded or produced.

- Direct observations: official repository identifiers, revisions, CSV schemas, raw label values, Terms of Use location, and file hashes.
- Computed statistics: row counts, unique trajectory/task counts, distributions, duplicate-annotation checks, and split joins.
- Risk judgments: absence of a standard license identifier, duplicate-label disagreement, and benchmark namespace differences.
- Unconfirmed questions: how repeated human annotations should eventually be aggregated and which benchmark namespace should define LOBO. Neither is decided in Stage A0.1.

## Fixed sources

- GitHub repository: [{manifest['github_repository']}]({manifest['github_repository']})
- GitHub commit: `{manifest['github_commit']}`
- Hugging Face repository: `https://huggingface.co/datasets/{manifest['huggingface_repository']}`
- Hugging Face revision: `{manifest['huggingface_revision']}`
- Metadata retrieval time (UTC): `{manifest['retrieved_at_utc']}`

## License and Terms of Use

- License status: **{manifest['license_status']}**
- Terms of Use original location: [{manifest['terms_of_use_url']}]({manifest['terms_of_use_url']})
- The fixed Hugging Face card contains a `Terms of Use` section. Its card metadata does not declare a standard `license` identifier. This audit records that fact and does not infer a legal license.

## Official metadata files

{markdown_table(['File', 'Bytes', 'SHA256'], ((name, info['size_bytes'], f"`{info['sha256']}`") for name, info in manifest['files'].items()))}

## Official split contract

The official split file is `{SPLITS_RELATIVE_PATH}`. Only `dev` and `test` are accepted. Stage A0.1 computes aggregate metadata for both as explicitly required, but does not use test data for feature, model, threshold, or method selection.

Task IDs are normalized only by trimming/lowercasing and removing the observed annotation-only markers `.improved.` and `.resized.`. This maps all annotation rows to official split tasks; no unmatched task is assigned by guesswork.

{markdown_table(['Split', 'Rows', 'Unique tasks'], split_rows)}

## Target labels

{markdown_table(['Research target', 'Official field', 'Exact mapping'], label_rows)}

`trajectory_optimality` is distribution-audited only. It is not converted to a binary target.

{markdown_table(['Target', 'Positive', 'Negative', 'Unsure excluded', 'Unknown', 'Positive rate among valid'], count_rows)}

## Annotation and benchmark identity

- Annotation rows: **{audit['annotations']['row_count']}**
- Unique trajectories: **{audit['duplicates']['unique_trajectory_count']}**, using `(benchmark, normalized_task_id, model_name)`.
- Unique normalized tasks: **{audit['annotations']['unique_normalized_task_count']}**
- Annotation benchmarks: **{audit['annotations']['benchmark_count']}**
- Split-file benchmark namespaces: **{audit['splits']['benchmark_count']}**
- Models: **{audit['annotations']['model_count']}**

{markdown_table(['Annotation benchmark', 'Annotation rows', 'Unique trajectories'], benchmark_rows)}

The annotations use `workarena`, while the split file distinguishes `workarena_l1` and `workarena_l2`. Both observed fields are preserved. Stage A0.1 does not choose which namespace later LOBO evaluation must use.

## Repeated annotation policy

Repeated `(benchmark, normalized_task_id, model_name)` keys are retained as separate human annotation rows. They are not treated as independent trajectories for the unique-trajectory count, and they are not voted, averaged, deleted, or relabeled. A later aggregation rule requires explicit approval.

- Duplicate trajectory groups: **{audit['duplicates']['duplicate_trajectory_group_count']}**
- Extra annotation rows: **{audit['duplicates']['extra_annotation_row_count']}**
- All repeated groups have distinct annotators: **{audit['duplicates']['all_duplicate_groups_have_distinct_annotators']}**
- All repeated groups share one `exp_name`: **{audit['duplicates']['all_duplicate_groups_share_one_exp_name']}**
- Per-label disagreement groups: `{json.dumps(audit['duplicates']['duplicate_group_label_disagreements'], ensure_ascii=False)}`

## Test sealing principle

The official `test` assignments are immutable. This metadata audit reports only required aggregate counts and label distributions. Test records must not inform feature design, preprocessing, model selection, threshold selection, fusion weights, or protocol changes.

## Known limitations and stop conditions

- No standard license identifier is declared; the custom Terms of Use must be reviewed by the research lead.
- Duplicate human labels sometimes disagree; no aggregation policy is authorized yet.
- Annotation and split benchmark namespaces differ for WorkArena; a later evaluation contract must resolve the LOBO grouping field without consulting model results.
- This contract does not establish trajectory-field availability, parsing success, leakage safety, or Stage A/Stage B readiness because full trajectories were outside A0.1 scope.
"""


def main() -> int:
    """Execute the metadata-only contract audit."""
    args = parse_args()
    repo_root = args.repo_root.resolve()
    raw_dir = (repo_root / args.raw_dir).resolve() if not args.raw_dir.is_absolute() else args.raw_dir
    docs_dir = (repo_root / args.docs_dir).resolve() if not args.docs_dir.is_absolute() else args.docs_dir
    artifacts_dir = (
        (repo_root / args.artifacts_dir).resolve()
        if not args.artifacts_dir.is_absolute()
        else args.artifacts_dir
    )

    github_info = fetch_json(
        f"https://api.github.com/repos/McGill-NLP/agent-reward-bench/commits/{GITHUB_COMMIT}"
    )
    if github_info.get("sha") != GITHUB_COMMIT:
        raise ContractError("GitHub did not resolve the required fixed commit")

    hf_info = fetch_json(
        f"https://huggingface.co/api/datasets/{HUGGINGFACE_REPOSITORY}/revision/"
        f"{HUGGINGFACE_REVISION}"
    )
    hf_revision = str(hf_info.get("sha", ""))
    if hf_revision != HUGGINGFACE_REVISION:
        raise ContractError("Hugging Face did not resolve the required fixed revision")

    github_raw = (
        "https://raw.githubusercontent.com/McGill-NLP/agent-reward-bench/" + GITHUB_COMMIT
    )
    urls = {
        "annotations.csv": f"{github_raw}/{ANNOTATIONS_RELATIVE_PATH}",
        "splits.csv": f"{github_raw}/{SPLITS_RELATIVE_PATH}",
        "README.md": (
            f"https://huggingface.co/datasets/{HUGGINGFACE_REPOSITORY}/resolve/"
            f"{hf_revision}/README.md"
        ),
    }
    file_bytes = {name: fetch_bytes(url) for name, url in urls.items()}
    readme_text = file_bytes["README.md"].decode("utf-8-sig")
    if "## Terms of Use" not in readme_text:
        raise ContractError("The fixed Hugging Face README has no confirmable Terms of Use section")

    card_data = hf_info.get("cardData") or {}
    declared_license = card_data.get("license") if isinstance(card_data, dict) else None
    license_status = (
        f"Standard license identifier declared as {declared_license}; custom Terms of Use also apply"
        if declared_license
        else "No standard license identifier declared; custom Terms of Use apply"
    )

    annotations_columns, annotations = read_csv_bytes(
        file_bytes["annotations.csv"], "annotations.csv"
    )
    splits_columns, splits = read_csv_bytes(file_bytes["splits.csv"], "splits.csv")
    if annotations_columns != EXPECTED_ANNOTATION_COLUMNS:
        raise ContractError(f"Unexpected annotations.csv columns: {annotations_columns}")
    if splits_columns != EXPECTED_SPLIT_COLUMNS:
        raise ContractError(f"Unexpected splits.csv columns: {splits_columns}")

    split_by_task: dict[str, dict[str, str]] = {}
    duplicate_split_keys: list[str] = []
    invalid_splits: list[dict[str, str]] = []
    for row in splits:
        normalized = normalize_task_id(row["task_id"])
        if normalized in split_by_task:
            duplicate_split_keys.append(normalized)
        else:
            split_by_task[normalized] = row
        if row["split"].strip() not in ALLOWED_SPLITS:
            invalid_splits.append({"task_id": normalized, "split": row["split"]})
    if duplicate_split_keys:
        raise ContractError(f"Duplicate normalized task IDs in splits.csv: {duplicate_split_keys[:10]}")
    if invalid_splits:
        raise ContractError(f"Undefined official split values: {invalid_splits[:10]}")

    unmatched_rows = [
        {
            "benchmark": row["benchmark"].strip(),
            "task_id": row["task_id"].strip(),
            "model_name": row["model_name"].strip(),
        }
        for row in annotations
        if normalize_task_id(row["task_id"]) not in split_by_task
    ]
    if unmatched_rows:
        raise ContractError(
            f"{len(unmatched_rows)} annotation rows do not map to the official split; "
            f"examples: {unmatched_rows[:5]}"
        )

    duplicate_audit = analyze_duplicates(annotations)
    target_summaries = [
        label_summary(annotations, target, contract["field"], contract["mapping"])
        for target, contract in LABEL_CONTRACT.items()
    ]
    unknown_labels = {
        summary["field"]: summary["raw_value_counts"]
        for summary in target_summaries
        if summary["unknown_count"]
    }
    if unknown_labels:
        raise ContractError(f"Undefined target label values found: {unknown_labels}")

    trajectory_groups: dict[tuple[str, str, str], int] = Counter(
        (
            row["benchmark"].strip(),
            normalize_task_id(row["task_id"]),
            row["model_name"].strip(),
        )
        for row in annotations
    )
    benchmark_counts: dict[str, dict[str, int]] = {}
    for benchmark in sorted({row["benchmark"].strip() for row in annotations}):
        benchmark_counts[benchmark] = {
            "annotation_rows": sum(row["benchmark"].strip() == benchmark for row in annotations),
            "unique_trajectories": sum(key[0] == benchmark for key in trajectory_groups),
        }
    model_counts: dict[str, dict[str, int]] = {}
    for model in sorted({row["model_name"].strip() for row in annotations}):
        model_counts[model] = {
            "annotation_rows": sum(row["model_name"].strip() == model for row in annotations),
            "unique_trajectories": sum(key[2] == model for key in trajectory_groups),
        }

    split_counts: dict[str, dict[str, int]] = {}
    for split_name in sorted(ALLOWED_SPLITS):
        rows = [row for row in splits if row["split"].strip() == split_name]
        split_counts[split_name] = {
            "rows": len(rows),
            "unique_tasks": len({normalize_task_id(row["task_id"]) for row in rows}),
        }

    normalization_counts = {
        "annotation_task_ids_with_improved_marker": sum(
            ".improved." in row["task_id"].lower() for row in annotations
        ),
        "annotation_task_ids_with_resized_marker": sum(
            ".resized." in row["task_id"].lower() for row in annotations
        ),
        "unmatched_annotation_rows": len(unmatched_rows),
    }
    field_profiles = {
        field: field_profile(annotations, field) for field in annotations_columns
    }
    label_distributions = distribution_rows(annotations, split_by_task)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    files_manifest = {
        name: {
            "source_url": urls[name],
            "local_path": str((raw_dir / name).relative_to(repo_root)).replace("\\", "/"),
            "size_bytes": len(data),
            "sha256": sha256_bytes(data),
        }
        for name, data in file_bytes.items()
    }
    terms_url = (
        f"https://huggingface.co/datasets/{HUGGINGFACE_REPOSITORY}/blob/"
        f"{hf_revision}/README.md#terms-of-use"
    )
    manifest = {
        "schema_version": "1.0",
        "stage": "A0.1",
        "retrieved_at_utc": retrieved_at,
        "github_repository": GITHUB_REPOSITORY,
        "github_commit": GITHUB_COMMIT,
        "huggingface_repository": HUGGINGFACE_REPOSITORY,
        "huggingface_revision": hf_revision,
        "huggingface_revision_lock": (
            "main resolved once on 2026-08-02, then pinned for all subsequent runs"
        ),
        "license_status": license_status,
        "terms_of_use_url": terms_url,
        "annotations_file": files_manifest["annotations.csv"]["local_path"],
        "splits_file": files_manifest["splits.csv"]["local_path"],
        "readme_file": files_manifest["README.md"]["local_path"],
        "file_sha256": {name: info["sha256"] for name, info in files_manifest.items()},
        "files": files_manifest,
        "command": "python scripts/audit_agent_reward_bench_metadata.py",
    }
    audit = {
        "schema_version": "1.0",
        "stage": "A0.1",
        "source_revision": {
            "github_commit": GITHUB_COMMIT,
            "huggingface_revision": hf_revision,
        },
        "license": {
            "status": license_status,
            "declared_standard_license": declared_license,
            "terms_of_use_present": True,
            "terms_of_use_url": terms_url,
        },
        "annotations": {
            "columns": annotations_columns,
            "row_count": len(annotations),
            "unique_normalized_task_count": len(
                {normalize_task_id(row["task_id"]) for row in annotations}
            ),
            "benchmark_count": len(benchmark_counts),
            "benchmark_counts": benchmark_counts,
            "model_count": len(model_counts),
            "model_counts": model_counts,
            "field_profiles": field_profiles,
        },
        "splits": {
            "columns": splits_columns,
            "row_count": len(splits),
            "unique_task_count": len(split_by_task),
            "benchmark_count": len({row["benchmark"].strip() for row in splits}),
            "benchmark_counts": counter_dict(row["benchmark"].strip() for row in splits),
            "split_counts": split_counts,
            "allowed_values": sorted(ALLOWED_SPLITS),
            "duplicate_normalized_task_ids": duplicate_split_keys,
            "invalid_split_rows": invalid_splits,
        },
        "normalization": {
            "rules": [
                "strip leading/trailing whitespace",
                "lowercase",
                "replace '.improved.' with '.'",
                "replace '.resized.' with '.'",
            ],
            **normalization_counts,
        },
        "labels": {
            "unit": "annotation rows; repeated annotators are not collapsed",
            "targets": target_summaries,
            "optimality_distribution_only": {
                "field": OPTIMALITY_FIELD,
                "raw_value_counts": counter_dict(
                    row[OPTIMALITY_FIELD].strip() or "<EMPTY>" for row in annotations
                ),
            },
            "distribution_file": "artifacts/label_distribution.csv",
        },
        "duplicates": duplicate_audit,
        "mapping": {
            "annotation_rows_total": len(annotations),
            "annotation_rows_matched_to_split": len(annotations) - len(unmatched_rows),
            "annotation_rows_unmatched": len(unmatched_rows),
            "unmatched_rows": unmatched_rows,
        },
        "risks": [
            "No standard license identifier is declared in Hugging Face card metadata.",
            "Repeated human annotations are not yet governed by an approved aggregation rule.",
            "Annotation benchmark 'workarena' maps to split namespaces workarena_l1/workarena_l2.",
            "Full trajectory parsing and leakage safety are outside Stage A0.1 scope.",
        ],
        "status": "PASS_WITH_DOCUMENTED_LIMITATIONS",
    }

    for name, data in file_bytes.items():
        raw_path = raw_dir / name
        atomic_write_bytes(raw_path, data)
        freeze_raw_file(raw_path)

    atomic_write_text(
        artifacts_dir / "source_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(
        artifacts_dir / "metadata_audit.json",
        json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    distribution_path = artifacts_dir / "label_distribution.csv"
    distribution_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scope",
        "split",
        "annotation_benchmark",
        "target",
        "field",
        "positive_count",
        "negative_count",
        "excluded_unsure_count",
        "unknown_count",
        "valid_binary_count",
        "positive_rate_among_valid",
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", dir=distribution_path.parent, delete=False
    ) as handle:
        temp_distribution = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(label_distributions)
    os.replace(temp_distribution, distribution_path)

    atomic_write_text(docs_dir / "data_contract.md", build_data_contract(manifest, audit))

    print(
        json.dumps(
            {
                "status": audit["status"],
                "github_commit": GITHUB_COMMIT,
                "huggingface_revision": hf_revision,
                "annotation_rows": len(annotations),
                "unique_trajectories": duplicate_audit["unique_trajectory_count"],
                "unique_tasks": len(split_by_task),
                "unmatched_annotation_rows": len(unmatched_rows),
                "outputs": [
                    str((docs_dir / "data_contract.md").relative_to(repo_root)),
                    str((artifacts_dir / "source_manifest.json").relative_to(repo_root)),
                    str((artifacts_dir / "metadata_audit.json").relative_to(repo_root)),
                    str((artifacts_dir / "label_distribution.csv").relative_to(repo_root)),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
