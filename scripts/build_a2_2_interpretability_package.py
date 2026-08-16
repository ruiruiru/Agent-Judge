#!/usr/bin/env python3
"""Build frozen A2.2 interpretability evidence and deterministic error cases.

The script only inspects frozen model attributes and frozen result artifacts. It
does not call estimator inference or training methods. Official-test trajectory
content is reduced to an exact allowlist for the twelve deterministically
selected errors before any human-readable inspection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import joblib


ROOT = Path(__file__).resolve().parents[1]
PREREG_COMMIT = "587ffec6a1c19ee8948e795044032365d84acc74"
TARGET_ORDER = ("success", "looping")
TARGET_METHODS = {
    "success": "FINAL_SUCCESS_B2",
    "looping": "FINAL_LOOPING_B2",
}
TARGET_THRESHOLDS = {"success": 0.55, "looping": 0.55}
EXPECTED_FEATURE_COUNT = 13

INPUTS = {
    "taskbook": (
        "docs/tasks/STAGE_A2_2_INTERPRETABILITY_CONFOUNDER_ERROR_ANALYSIS.md",
        "5019985dd1ec7cd4ca1a5feffb20ef5c7309c9298f9fc6f19cf966d6b34a7cac",
    ),
    "claim_matrix": (
        "artifacts/a1_11_final_claim_matrix.csv",
        "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175",
    ),
    "main_test_table": (
        "artifacts/a1_11_table_main_test_results.csv",
        "c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947",
    ),
    "success_model": (
        "artifacts/final_models/final_success_b2.joblib",
        "afbdb0a60205d7c6bd40232a8c8a1b1ad3b0910d6b65fecf894cca1a040123c1",
    ),
    "looping_model": (
        "artifacts/final_models/final_looping_b2.joblib",
        "862b7ff2b0cbcb5faf88908f5fe5824c7f4e52c2c21521e41bb5fb71b011660c",
    ),
    "feature_registry": (
        "artifacts/a1_5_feature_group_registry.csv",
        "23faa8f97c9cba9456081927d4fd633787179aa34e9eda51e9c31a960931f65d",
    ),
    "ablation_deltas": (
        "artifacts/a1_5_structural_ablation_deltas.csv",
        "4c5c6a6acd818800f5456c5a1cea816a72fa1938d86e641bb9a17d6c80317abf",
    ),
    "bootstrap_deltas": (
        "artifacts/a1_6_primary_paired_delta_summary.csv",
        "f240fa5d52f546add06e4bc360aac3820c38fa60ba2ef5e11d009ff0cea80e91",
    ),
    "scored_predictions": (
        "artifacts/a1_10_test_scored_predictions.csv",
        "22883f32ad22ecd2de6e7a3056a0f165d7aa4c03ab4ec847a535dbff7defb704",
    ),
    "test_cleaned": (
        "data/processed/a1_10a_test_cleaned_trajectories.jsonl",
        "4b9fdbaa18eb5c041bc68737a6b9ea2db202f6dbe17bb56cf339b43b4b2eb004",
    ),
}

OUTPUTS = {
    "coefficients": "artifacts/a2_2_structural_coefficients.csv",
    "feature_evidence": "artifacts/a2_2_feature_group_evidence.csv",
    "error_manifest": "artifacts/a2_2_error_case_manifest.csv",
}

COEFFICIENT_FIELDS = (
    "target",
    "feature",
    "feature_group",
    "standardized_coefficient",
    "absolute_coefficient",
    "absolute_rank",
    "sign",
    "interpretation_note",
    "evidence_status",
)

EVIDENCE_FIELDS = (
    "target",
    "feature_group",
    "frozen_variant_or_comparison",
    "effect_direction",
    "uncertainty_status",
    "source_stage",
    "source_artifact",
    "point_estimate",
    "allowed_interpretation",
    "forbidden_interpretation",
    "evidence_status",
)

MANIFEST_FIELDS = (
    "target",
    "error_type",
    "case_role",
    "trajectory_key",
    "benchmark",
    "model_name",
    "true_label",
    "predicted_label",
    "probability",
    "threshold",
    "distance_from_threshold",
    "selection_rank",
)

SAFE_CONTEXT_KEYS = {
    "trajectory_key",
    "task_instruction",
    "steps",
    "terminal",
    "structural_pattern",
}
SAFE_STEP_KEYS = {
    "step_index",
    "action",
    "observation",
    "focused_element",
    "last_action_error",
}
SAFE_TERMINAL_KEYS = {"last_step_index", "termination_signal"}
BANNED_FIELD_NAMES = {
    "reward",
    "cum_reward",
    "cum_raw_reward",
    "judge",
    "annotation",
    "summary_info",
    "success_label",
    "side_effect_label",
    "looping_label",
    "outcome",
    "outcome_summary",
}


class IntegrityError(RuntimeError):
    """Raised when a frozen artifact or analysis boundary is violated."""


def resolve(relative: str) -> Path:
    """Resolve a repository-relative path and reject path escapes."""

    candidate = Path(relative)
    if candidate.is_absolute():
        raise IntegrityError(f"absolute path is prohibited: {relative}")
    resolved = (ROOT / candidate).resolve()
    if ROOT not in resolved.parents and resolved != ROOT:
        raise IntegrityError(f"path escapes repository: {relative}")
    return resolved


def sha256_path(path: Path) -> str:
    """Return a file SHA-256 digest."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read UTF-8 CSV dictionaries."""

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


def atomic_json(path: Path, value: Any) -> None:
    """Write deterministic UTF-8 JSON atomically."""

    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def git_output(*args: str) -> str:
    """Run a read-only Git query."""

    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def verify_frozen_inputs() -> dict[str, str]:
    """Verify preregistration ancestry and every frozen package input."""

    head = git_output("rev-parse", "HEAD")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", PREREG_COMMIT, head],
        cwd=ROOT,
        check=False,
    )
    if ancestor.returncode != 0:
        raise IntegrityError("A2.2 preregistration commit is not an ancestor of HEAD")
    verified: dict[str, str] = {"formal_git_commit": head}
    for name, (relative, expected) in INPUTS.items():
        actual = sha256_path(resolve(relative))
        if actual != expected:
            raise IntegrityError(f"SHA-256 mismatch for {name}: {actual} != {expected}")
        verified[relative] = actual
    return verified


def frozen_features_and_groups() -> tuple[list[str], dict[str, str]]:
    """Read the ordered 13-feature schema from the frozen A1.5 registry."""

    rows = [
        row
        for row in read_csv(resolve(INPUTS["feature_registry"][0]))
        if row["variant_id"] == "S0_full13" and row["included"] == "True"
    ]
    rows.sort(key=lambda row: int(row["feature_order"]))
    features = [row["feature_name"] for row in rows]
    groups = {row["feature_name"]: row["feature_group"] for row in rows}
    if len(features) != EXPECTED_FEATURE_COUNT or len(set(features)) != EXPECTED_FEATURE_COUNT:
        raise IntegrityError(f"frozen B2 schema is not exactly {EXPECTED_FEATURE_COUNT}")
    expected_groups = {
        "G1_activity_volume",
        "G2_error",
        "G3_termination",
        "G4_repetition",
    }
    if set(groups.values()) != expected_groups:
        raise IntegrityError(f"unexpected frozen feature groups: {set(groups.values())}")
    return features, groups


def coefficient_rows() -> list[dict[str, Any]]:
    """Extract standardized LR coefficients without fitting or inference."""

    features, groups = frozen_features_and_groups()
    output: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        model = joblib.load(resolve(INPUTS[f"{target}_model"][0]))
        if not hasattr(model, "steps") or [name for name, _ in model.steps] != [
            "standard_scaler",
            "classifier",
        ]:
            raise IntegrityError(f"{target} final model is not the frozen scaler/LR pipeline")
        scaler = model.named_steps["standard_scaler"]
        classifier = model.named_steps["classifier"]
        if getattr(classifier, "__class__", object).__name__ != "LogisticRegression":
            raise IntegrityError(f"{target} final classifier type changed")
        coefficients = list(classifier.coef_[0])
        if any(
            len(list(values)) != EXPECTED_FEATURE_COUNT
            for values in (scaler.mean_, scaler.scale_, coefficients)
        ):
            raise IntegrityError(f"{target} model/scaler feature count changed")
        if list(classifier.classes_) != [0, 1]:
            raise IntegrityError(f"{target} class order changed")
        order = sorted(
            range(EXPECTED_FEATURE_COUNT),
            key=lambda index: (-abs(float(coefficients[index])), features[index]),
        )
        ranks = {index: rank for rank, index in enumerate(order, start=1)}
        for index, feature in enumerate(features):
            coefficient = float(coefficients[index])
            sign = "positive" if coefficient > 0 else "negative" if coefficient < 0 else "zero"
            output.append(
                {
                    "target": target,
                    "feature": feature,
                    "feature_group": groups[feature],
                    "standardized_coefficient": coefficient,
                    "absolute_coefficient": abs(coefficient),
                    "absolute_rank": ranks[index],
                    "sign": sign,
                    "interpretation_note": (
                        f"{sign.capitalize()} association within the frozen standardized LR; "
                        "coefficient is not a causal effect."
                    ),
                    "evidence_status": "POST_FREEZE_DIAGNOSTIC",
                }
            )
    output.sort(key=lambda row: (TARGET_ORDER.index(str(row["target"])), int(row["absolute_rank"])))
    return output


VARIANT_GROUPS = {
    "S1_no_termination": "G3_termination",
    "S2_no_repetition": "G4_repetition",
    "S3_no_activity_volume": "G1_activity_volume",
    "S4_no_error": "G2_error",
    "S6_termination_repetition_only": "G3_termination+G4_repetition",
}

BOOTSTRAP_COMPARISONS = {
    ("success", "S1_no_termination"): "P3",
    ("success", "S6_termination_repetition_only"): "P4",
    ("looping", "S2_no_repetition"): "P6",
    ("looping", "S6_termination_repetition_only"): "P7",
}


def _consistent_variant_rows(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    """Return one row after checking repeated A1.5 summary fields agree."""

    if not rows:
        raise IntegrityError("missing A1.5 comparison rows")
    fields = (
        "pooled_delta_AP",
        "retained_AP_lift_ratio",
        "frozen_dependency_classification",
    )
    for field in fields:
        if len({row.get(field, "") for row in rows}) != 1:
            raise IntegrityError(f"A1.5 repeated summary field differs: {field}")
    return rows[0]


def feature_group_evidence_rows() -> list[dict[str, Any]]:
    """Synthesize only already-frozen A1.5/A1.6 feature-group evidence."""

    ablation_rows = read_csv(resolve(INPUTS["ablation_deltas"][0]))
    bootstrap_rows = read_csv(resolve(INPUTS["bootstrap_deltas"][0]))
    bootstrap_index: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in bootstrap_rows:
        if row.get("scope") == "macro" and row.get("metric") == "ap":
            bootstrap_index[(row["target"], row["comparison_id"])] = row
    output: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        for variant, feature_group in VARIANT_GROUPS.items():
            matched = [
                row
                for row in ablation_rows
                if row["target"] == target and row["variant_id"] == variant
            ]
            source = _consistent_variant_rows(matched)
            point = float(source["pooled_delta_AP"])
            if variant == "S6_termination_repetition_only":
                effect = (
                    "restricted_variant_higher_pooled_ap"
                    if point > 0
                    else "restricted_variant_lower_pooled_ap"
                    if point < 0
                    else "restricted_variant_no_pooled_ap_change"
                )
            else:
                effect = (
                    "removal_raised_pooled_ap"
                    if point > 0
                    else "removal_lowered_pooled_ap"
                    if point < 0
                    else "removal_no_pooled_ap_change"
                )
            comparison_id = BOOTSTRAP_COMPARISONS.get((target, variant))
            uncertainty = "NOT_BOOTSTRAPPED_IN_A1_6"
            source_stage = "A1.5"
            source_artifact = INPUTS["ablation_deltas"][0]
            if comparison_id:
                bootstrap = bootstrap_index.get((target, comparison_id))
                if bootstrap is None:
                    raise IntegrityError(f"missing frozen bootstrap comparison {target}:{comparison_id}")
                uncertainty = bootstrap["bootstrap_grade"]
                source_stage = "A1.5+A1.6"
                source_artifact += ";" + INPUTS["bootstrap_deltas"][0]
            output.append(
                {
                    "target": target,
                    "feature_group": feature_group,
                    "frozen_variant_or_comparison": f"{variant} vs S0_full13",
                    "effect_direction": effect,
                    "uncertainty_status": uncertainty,
                    "source_stage": source_stage,
                    "source_artifact": source_artifact,
                    "point_estimate": point,
                    "allowed_interpretation": (
                        f"Frozen {variant} minus S0 pooled AP={point:.12g}; "
                        f"A1.5 classification={source['frozen_dependency_classification']}; "
                        f"A1.6 macro-AP uncertainty={uncertainty}. "
                        "The point estimate is the frozen A1.5 pooled-AP delta; "
                        "this is descriptive dev evidence."
                    ),
                    "forbidden_interpretation": (
                        "No causal effect, confirmatory upgrade, or unseen-benchmark generalization claim."
                    ),
                    "evidence_status": "DEV_ONLY",
                }
            )
    return output


def is_true(value: Any) -> bool:
    """Parse the repository's explicit CSV booleans."""

    return str(value).strip().lower() == "true"


def deterministic_error_selection(
    rows: Sequence[Mapping[str, str]], target: str, error_type: str
) -> list[dict[str, Any]]:
    """Select borderline, lower-median, and high-confidence frozen errors."""

    expected_truth, expected_prediction = (0, 1) if error_type == "FP" else (1, 0)
    candidates: list[dict[str, Any]] = []
    for raw in rows:
        if raw.get("target") != target or not is_true(raw.get("scoring_included")):
            continue
        if raw.get("method_id") != TARGET_METHODS[target]:
            continue
        truth = int(raw["true_label"])
        predicted = int(raw["predicted_label"])
        if (truth, predicted) != (expected_truth, expected_prediction):
            continue
        probability = float(raw["probability"])
        threshold = float(raw["frozen_threshold"])
        if not math.isclose(threshold, TARGET_THRESHOLDS[target], abs_tol=0.0, rel_tol=0.0):
            raise IntegrityError(f"frozen threshold changed for {target}")
        candidates.append(
            {
                "target": target,
                "error_type": error_type,
                "trajectory_key": raw["trajectory_key"],
                "benchmark": raw["benchmark_original"],
                "model_name": raw["model_name"],
                "true_label": truth,
                "predicted_label": predicted,
                "probability": probability,
                "threshold": threshold,
                "distance_from_threshold": abs(probability - threshold),
            }
        )
    if len(candidates) < 3:
        raise IntegrityError(f"fewer than three frozen {target} {error_type} errors")
    ordered = sorted(candidates, key=lambda row: (row["distance_from_threshold"], row["trajectory_key"]))
    median_index = (len(ordered) - 1) // 2
    maximum_distance = max(float(row["distance_from_threshold"]) for row in ordered)
    high = min(
        (row for row in ordered if float(row["distance_from_threshold"]) == maximum_distance),
        key=lambda row: row["trajectory_key"],
    )
    choices = (
        ("borderline", ordered[0]),
        ("median_error_confidence", ordered[median_index]),
        ("high_confidence_error", high),
    )
    if len({row["trajectory_key"] for _, row in choices}) != 3:
        raise IntegrityError(f"deterministic roles are not three distinct {target} {error_type} cases")
    rank = {id(row): index for index, row in enumerate(ordered, start=1)}
    selected: list[dict[str, Any]] = []
    for role, row in choices:
        selected.append({**row, "case_role": role, "selection_rank": rank[id(row)]})
    return selected


def error_manifest_rows() -> list[dict[str, Any]]:
    """Build the exact preregistered twelve-row error manifest."""

    scored = read_csv(resolve(INPUTS["scored_predictions"][0]))
    output: list[dict[str, Any]] = []
    for target in TARGET_ORDER:
        for error_type in ("FP", "FN"):
            output.extend(deterministic_error_selection(scored, target, error_type))
    if len(output) != 12 or len({row["trajectory_key"] + "|" + row["target"] for row in output}) != 12:
        raise IntegrityError("error manifest is not twelve unique target/case rows")
    return output


def _normalized_action(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def safe_context(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce one cleaned record to the exact leakage-safe A2.2 allowlist."""

    if set(record) & BANNED_FIELD_NAMES:
        raise IntegrityError("banned root field appeared in cleaned trajectory")
    task = record.get("task") if isinstance(record.get("task"), Mapping) else {}
    raw_steps = record.get("steps") if isinstance(record.get("steps"), list) else []
    steps: list[dict[str, Any]] = []
    actions: list[str] = []
    error_count = 0
    for index, raw in enumerate(raw_steps, start=1):
        if not isinstance(raw, Mapping):
            raise IntegrityError("non-object step in selected cleaned trajectory")
        action = raw.get("action")
        normalized = _normalized_action(action)
        if normalized:
            actions.append(normalized)
        if raw.get("error"):
            error_count += 1
        steps.append(
            {
                "step_index": int(raw.get("step_index") or index),
                "action": action,
                "observation": raw.get("observation"),
                "focused_element": raw.get("focused_element"),
                "last_action_error": raw.get("error"),
            }
        )
    consecutive_duplicates = sum(left == right for left, right in zip(actions, actions[1:]))
    terminal = record.get("terminal") if isinstance(record.get("terminal"), Mapping) else {}
    result = {
        "trajectory_key": record.get("trajectory_key"),
        "task_instruction": task.get("instruction"),
        "steps": steps,
        "terminal": {
            "last_step_index": terminal.get("last_step_index"),
            "termination_signal": terminal.get("termination_signal"),
        },
        "structural_pattern": {
            "step_count": len(steps),
            "nonempty_action_count": len(actions),
            "unique_action_ratio": (len(set(actions)) / len(actions)) if actions else 0.0,
            "consecutive_duplicate_action_count": consecutive_duplicates,
            "natural_error_step_count": error_count,
        },
    }
    validate_safe_context(result)
    return result


def validate_safe_context(value: Mapping[str, Any]) -> None:
    """Reject any field outside the selected-case content allowlist."""

    if set(value) != SAFE_CONTEXT_KEYS:
        raise IntegrityError(f"safe context root keys differ: {set(value)}")
    if not isinstance(value["steps"], list):
        raise IntegrityError("safe context steps is not a list")
    for step in value["steps"]:
        if not isinstance(step, Mapping) or set(step) != SAFE_STEP_KEYS:
            raise IntegrityError("safe context step keys differ")
    terminal = value["terminal"]
    if not isinstance(terminal, Mapping) or set(terminal) != SAFE_TERMINAL_KEYS:
        raise IntegrityError("safe context terminal keys differ")
    def visit(item: Any) -> None:
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if str(key).casefold() in BANNED_FIELD_NAMES:
                    raise IntegrityError(f"banned field in safe context: {key}")
                visit(nested)
        elif isinstance(item, list):
            for nested in item:
                visit(nested)
    visit(value)


def selected_contexts(manifest: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Stream the test-cleaned file and retain only the selected twelve records."""

    if len(manifest) != 12:
        raise IntegrityError("selected error case count is not twelve")
    selected_keys = {str(row["trajectory_key"]) for row in manifest}
    if not selected_keys:
        raise IntegrityError("selected context key set is empty")
    contexts: dict[str, dict[str, Any]] = {}
    with resolve(INPUTS["test_cleaned"][0]).open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = json.loads(line)
            key = str(raw.get("trajectory_key", ""))
            if key in selected_keys:
                if key in contexts:
                    raise IntegrityError(f"duplicate selected cleaned trajectory: {key}")
                contexts[key] = safe_context(raw)
    if set(contexts) != selected_keys:
        raise IntegrityError(f"missing selected cleaned contexts: {selected_keys - set(contexts)}")
    output: list[dict[str, Any]] = []
    for manifest_row in manifest:
        key = str(manifest_row["trajectory_key"])
        output.append(
            {
                "selection": {
                    field: manifest_row[field]
                    for field in ("target", "error_type", "case_role", "probability", "threshold")
                },
                "context": contexts[key],
            }
        )
    return output


def prepare(context_output: str) -> None:
    """Build the three machine artifacts and twelve-case safe context package."""

    for relative in OUTPUTS.values():
        if resolve(relative).exists():
            raise IntegrityError(f"refusing to overwrite existing output: {relative}")
    context_path = resolve(context_output)
    if context_path.exists():
        raise IntegrityError(f"refusing to overwrite selected context: {context_output}")
    context_path.parent.mkdir(parents=True, exist_ok=True)
    verified = verify_frozen_inputs()
    coefficients = coefficient_rows()
    evidence = feature_group_evidence_rows()
    manifest = error_manifest_rows()
    contexts = selected_contexts(manifest)
    atomic_csv(resolve(OUTPUTS["coefficients"]), COEFFICIENT_FIELDS, coefficients)
    atomic_csv(resolve(OUTPUTS["feature_evidence"]), EVIDENCE_FIELDS, evidence)
    atomic_csv(resolve(OUTPUTS["error_manifest"]), MANIFEST_FIELDS, manifest)
    atomic_json(
        context_path,
        {
            "stage": "A2.2",
            "identity": "POST_FREEZE_DESCRIPTIVE",
            "selected_case_count": len(contexts),
            "verified_inputs": verified,
            "cases": contexts,
        },
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "coefficient_rows": len(coefficients),
                "feature_evidence_rows": len(evidence),
                "error_manifest_rows": len(manifest),
                "selected_context_rows": len(contexts),
            },
            sort_keys=True,
        ),
        flush=True,
    )


def main() -> None:
    """CLI entry point."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--context-output",
        default="runs/a2_2_selected_error_context.json",
        help="Ignored intermediate containing only the twelve allowlisted contexts.",
    )
    args = parser.parse_args()
    prepare(args.context_output)


if __name__ == "__main__":
    main()
