#!/usr/bin/env python3
"""Run the preregistered A2.2 metadata-only dev diagnostic.

This module is intentionally isolated from official-test artifacts. It fits the
fixed metadata-only estimator on the five frozen A1.1 outer folds for Success
and Looping and emits one OOF prediction per eligible dev trajectory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parents[1]
PREREG_COMMIT = "587ffec6a1c19ee8948e795044032365d84acc74"
TARGET_ORDER = ("success", "looping")
METADATA_FEATURES = ("benchmark_group_primary", "model_name")
THRESHOLD = 0.5

INPUTS = {
    "taskbook": (
        "docs/tasks/STAGE_A2_2_INTERPRETABILITY_CONFOUNDER_ERROR_ANALYSIS.md",
        "5019985dd1ec7cd4ca1a5feffb20ef5c7309c9298f9fc6f19cf966d6b34a7cac",
    ),
    "dev_index": (
        "artifacts/dev_analysis_index.csv",
        "2b29b46522b5cce32f084e6dc620ff3203f1fd474721fb001123348be0ab56d0",
    ),
    "success_folds": (
        "artifacts/evaluation_folds_success.csv",
        "820599f85fd901c1b73db61cbc77c54eb8223df3f3abc14062d5a9f20bb02e65",
    ),
    "looping_folds": (
        "artifacts/evaluation_folds_looping.csv",
        "b950bf23e465d2f108f28281395ac8816c9916b20eaebe2d529e9d5fde74c749",
    ),
    "final_model_manifest": (
        "artifacts/a1_9_final_model_manifest.json",
        "44d7fce8e2b3cef51fd8c1d2e46bae7838dcd92e8c664a31c48962ff2070881f",
    ),
}

OUTPUTS = {
    "config": "artifacts/a2_2_metadata_config.json",
    "predictions": "artifacts/a2_2_metadata_baseline_predictions.csv",
    "summary": "artifacts/a2_2_metadata_baseline_summary.csv",
}

PREDICTION_FIELDS = (
    "target",
    "fold",
    "trajectory_key",
    "true_label",
    "predicted_probability",
    "predicted_label",
    "benchmark_group_primary",
    "model_name",
)

SUMMARY_FIELDS = (
    "target",
    "eligible_n",
    "positive_n",
    "negative_n",
    "prevalence",
    "pooled_ap",
    "ap_lift",
    "f1_at_0_5",
    "b2_frozen_dev_ap",
    "b2_frozen_dev_f1",
    "evidence_status",
)


class IntegrityError(RuntimeError):
    """Raised when a frozen input or protocol guard fails."""


def resolve(relative: str) -> Path:
    """Resolve a repository-relative path without accepting absolute inputs."""

    candidate = Path(relative)
    if candidate.is_absolute():
        raise IntegrityError(f"absolute path is prohibited: {relative}")
    resolved = (ROOT / candidate).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise IntegrityError(f"path escapes repository: {relative}")
    return resolved


def sha256_path(path: Path) -> str:
    """Return the SHA-256 digest of a file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV as dictionaries."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_csv(path: Path, fields: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    """Write an LF-only CSV atomically."""

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    """Write deterministic UTF-8 JSON atomically."""

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def git_output(*args: str) -> str:
    """Run a read-only Git query and return stripped stdout."""

    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def verify_preflight(require_clean: bool = True) -> dict[str, str]:
    """Verify Git provenance and every frozen metadata input before fitting."""

    if require_clean and git_output("status", "--porcelain"):
        raise IntegrityError("formal metadata diagnostic must start from clean Git")
    head = git_output("rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PREREG_COMMIT, head],
        cwd=ROOT,
        check=False,
    )
    if ancestor.returncode != 0:
        raise IntegrityError("A2.2 preregistration commit is not an ancestor of HEAD")
    verified: dict[str, str] = {}
    for name, (relative, expected) in INPUTS.items():
        actual = sha256_path(resolve(relative))
        if actual != expected:
            raise IntegrityError(f"SHA-256 mismatch for {name}: {actual} != {expected}")
        verified[relative] = actual
    return {"formal_git_commit": head, **verified}


def metadata_model() -> Pipeline:
    """Construct the fixed preregistered metadata-only estimator."""

    return Pipeline(
        [
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
            (
                "classifier",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    penalty="l2",
                    solver="liblinear",
                    max_iter=5000,
                    fit_intercept=True,
                    random_state=2026,
                ),
            ),
        ]
    )


def index_by_key(rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    """Validate and index the frozen dev analysis rows."""

    indexed: dict[str, dict[str, str]] = {}
    for raw in rows:
        row = dict(raw)
        key = row.get("trajectory_key", "")
        if not key or key in indexed:
            raise IntegrityError(f"missing or duplicate dev trajectory key: {key}")
        if row.get("official_split") != "dev":
            raise IntegrityError(f"non-dev row entered metadata source: {key}")
        if any(not row.get(feature) for feature in METADATA_FEATURES):
            raise IntegrityError(f"missing allowed metadata feature for {key}")
        indexed[key] = row
    if len(indexed) != 196:
        raise IntegrityError(f"dev index row count differs: {len(indexed)}")
    return indexed


def frozen_outer_folds(
    rows: Sequence[Mapping[str, str]], target: str
) -> tuple[dict[str, int], dict[int, tuple[list[str], list[str]]]]:
    """Validate frozen A1.1 fold rows and return labels/train-validation keys."""

    appearances: Counter[str] = Counter()
    validation_appearances: Counter[str] = Counter()
    labels: dict[str, int] = {}
    by_fold: dict[int, dict[str, list[str]]] = defaultdict(
        lambda: {"outer_train": [], "outer_validation": []}
    )
    train_groups: dict[int, set[str]] = defaultdict(set)
    validation_groups: dict[int, set[str]] = defaultdict(set)
    for row in rows:
        key = row.get("trajectory_key", "")
        if row.get("target") != target or row.get("official_split") != "dev":
            raise IntegrityError(f"invalid target/split in {target} folds")
        try:
            fold = int(row["outer_fold"])
            label = int(row["label"])
        except (KeyError, ValueError) as exc:
            raise IntegrityError(f"invalid fold/label in {target} folds") from exc
        if fold not in {1, 2, 3, 4, 5} or label not in {0, 1}:
            raise IntegrityError(f"out-of-contract fold/label in {target}")
        if key in labels and labels[key] != label:
            raise IntegrityError(f"label changed across {target} folds for {key}")
        labels[key] = label
        appearances[key] += 1
        role = row.get("outer_role", "")
        if role not in {"outer_train", "outer_validation"}:
            raise IntegrityError(f"invalid outer role in {target}")
        by_fold[fold][role].append(key)
        group = row.get("group_key", "")
        if role == "outer_validation":
            validation_appearances[key] += 1
            validation_groups[fold].add(group)
        else:
            train_groups[fold].add(group)
    if set(by_fold) != {1, 2, 3, 4, 5}:
        raise IntegrityError(f"{target} folds are not exactly 1..5")
    if (
        set(appearances) != set(labels)
        or set(validation_appearances) != set(labels)
        or set(appearances.values()) != {5}
        or set(validation_appearances.values()) != {1}
    ):
        raise IntegrityError(f"{target} frozen OOF membership is not exactly once")
    result: dict[int, tuple[list[str], list[str]]] = {}
    for fold in range(1, 6):
        train = sorted(by_fold[fold]["outer_train"])
        validation = sorted(by_fold[fold]["outer_validation"])
        if set(train) & set(validation):
            raise IntegrityError(f"sample leakage in {target} fold {fold}")
        if train_groups[fold] & validation_groups[fold]:
            raise IntegrityError(f"group leakage in {target} fold {fold}")
        if set(train) | set(validation) != set(labels):
            raise IntegrityError(f"incomplete {target} fold {fold}")
        if len({labels[key] for key in train}) != 2:
            raise IntegrityError(f"single-class training data in {target} fold {fold}")
        result[fold] = (train, validation)
    return labels, result


def feature_rows(keys: Sequence[str], index: Mapping[str, Mapping[str, str]]) -> list[list[str]]:
    """Materialize only the two preregistered metadata features."""

    return [[index[key][feature] for feature in METADATA_FEATURES] for key in keys]


def frozen_b2_reference() -> dict[str, dict[str, float]]:
    """Read, without recomputation, the frozen B2 dev AP and positive F1."""

    manifest = json.loads(resolve(INPUTS["final_model_manifest"][0]).read_text(encoding="utf-8"))
    references: dict[str, dict[str, float]] = {}
    for item in manifest.get("models", []):
        target = item.get("target")
        if target in TARGET_ORDER:
            expected_method = f"FINAL_{target.upper()}_B2"
            if item.get("method_id") != expected_method:
                raise IntegrityError(f"unexpected frozen B2 method for {target}")
            references[target] = {
                "ap": float(item["final_oof_average_precision"]),
                "f1": float(item["final_oof_positive_f1"]),
            }
    if set(references) != set(TARGET_ORDER):
        raise IntegrityError("frozen B2 dev references are incomplete")
    return references


def run_diagnostic() -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, list[str]]:
    """Fit the fixed diagnostic over frozen folds and return OOF artifacts."""

    index = index_by_key(read_csv(resolve(INPUTS["dev_index"][0])))
    references = frozen_b2_reference()
    predictions: list[dict[str, Any]] = []
    warning_messages: list[str] = []
    fit_count = 0
    for target in TARGET_ORDER:
        labels, folds = frozen_outer_folds(
            read_csv(resolve(INPUTS[f"{target}_folds"][0])), target
        )
        if not set(labels).issubset(index):
            raise IntegrityError(f"{target} fold key absent from dev index")
        for fold in range(1, 6):
            train_keys, validation_keys = folds[fold]
            model = metadata_model()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                model.fit(feature_rows(train_keys, index), [labels[key] for key in train_keys])
                probabilities = model.predict_proba(feature_rows(validation_keys, index))[:, 1]
            fit_count += 1
            warning_messages.extend(str(item.message) for item in caught)
            for key, probability in zip(validation_keys, probabilities, strict=True):
                predictions.append(
                    {
                        "target": target,
                        "fold": fold,
                        "trajectory_key": key,
                        "true_label": labels[key],
                        "predicted_probability": float(probability),
                        "predicted_label": int(float(probability) >= THRESHOLD),
                        "benchmark_group_primary": index[key]["benchmark_group_primary"],
                        "model_name": index[key]["model_name"],
                    }
                )
    if fit_count != 10:
        raise IntegrityError(f"metadata diagnostic fit count differs: {fit_count}")
    predictions.sort(key=lambda row: (TARGET_ORDER.index(str(row["target"])), str(row["trajectory_key"])))
    pair_counts = Counter((str(row["target"]), str(row["trajectory_key"])) for row in predictions)
    if set(pair_counts.values()) != {1}:
        raise IntegrityError("metadata OOF prediction is not exactly once per target/key")

    summaries: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        rows = [row for row in predictions if row["target"] == target]
        truth = [int(row["true_label"]) for row in rows]
        probability = [float(row["predicted_probability"]) for row in rows]
        predicted = [int(row["predicted_label"]) for row in rows]
        positives = sum(truth)
        prevalence = positives / len(rows)
        pooled_ap = float(average_precision_score(truth, probability))
        summaries.append(
            {
                "target": target,
                "eligible_n": len(rows),
                "positive_n": positives,
                "negative_n": len(rows) - positives,
                "prevalence": prevalence,
                "pooled_ap": pooled_ap,
                "ap_lift": pooled_ap - prevalence,
                "f1_at_0_5": float(f1_score(truth, predicted, pos_label=1, zero_division=0)),
                "b2_frozen_dev_ap": references[target]["ap"],
                "b2_frozen_dev_f1": references[target]["f1"],
                "evidence_status": "POST_FREEZE_DIAGNOSTIC",
            }
        )
    return predictions, summaries, fit_count, warning_messages


def main() -> None:
    """CLI entry point for the one-time local metadata diagnostic."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-dirty-for-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for relative in OUTPUTS.values():
        if resolve(relative).exists():
            raise IntegrityError(f"refusing to overwrite existing output: {relative}")
    verified = verify_preflight(require_clean=not args.allow_dirty_for_test)
    predictions, summaries, fit_count, warning_messages = run_diagnostic()
    config = {
        "stage": "A2.2",
        "identity": "POST_FREEZE_DIAGNOSTIC",
        "targets": list(TARGET_ORDER),
        "features": list(METADATA_FEATURES),
        "encoder": {"name": "OneHotEncoder", "handle_unknown": "ignore"},
        "classifier": {
            "name": "LogisticRegression",
            "C": 1.0,
            "class_weight": "balanced",
            "penalty": "l2",
            "solver": "liblinear",
            "max_iter": 5000,
            "fit_intercept": True,
            "random_state": 2026,
        },
        "threshold": THRESHOLD,
        "split_source": "A1.1 frozen grouped folds",
        "official_test_use": 0,
        "configuration_search": 0,
        "threshold_tuning": 0,
        "metadata_diagnostic_fits": fit_count,
        "verified_inputs": verified,
        "warning_count": len(warning_messages),
        "warnings": sorted(set(warning_messages)),
    }
    atomic_csv(resolve(OUTPUTS["predictions"]), PREDICTION_FIELDS, predictions)
    atomic_csv(resolve(OUTPUTS["summary"]), SUMMARY_FIELDS, summaries)
    atomic_json(resolve(OUTPUTS["config"]), config)
    print(
        json.dumps(
            {
                "status": "PASS",
                "metadata_diagnostic_fits": fit_count,
                "prediction_rows": len(predictions),
                "warning_count": len(warning_messages),
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
