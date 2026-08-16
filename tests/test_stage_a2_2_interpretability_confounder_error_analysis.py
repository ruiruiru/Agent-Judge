"""Unit guards for the preregistered A2.2 diagnostic implementation."""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


metadata = load_module("a2_2_metadata", "scripts/run_a2_2_metadata_confounder_audit.py")
package = load_module("a2_2_package", "scripts/build_a2_2_interpretability_package.py")


class A22ImplementationTests(unittest.TestCase):
    def test_01_metadata_features_are_exactly_frozen_identity_fields(self) -> None:
        self.assertEqual(
            metadata.METADATA_FEATURES,
            ("benchmark_group_primary", "model_name"),
        )

    def test_02_metadata_model_contract_is_fixed(self) -> None:
        model = metadata.metadata_model()
        self.assertEqual([name for name, _ in model.steps], ["one_hot", "classifier"])
        encoder = model.named_steps["one_hot"]
        classifier = model.named_steps["classifier"]
        self.assertEqual(encoder.handle_unknown, "ignore")
        self.assertEqual(classifier.C, 1.0)
        self.assertEqual(classifier.class_weight, "balanced")
        self.assertEqual(classifier.penalty, "l2")
        self.assertEqual(classifier.solver, "liblinear")
        self.assertEqual(classifier.max_iter, 5000)
        self.assertTrue(classifier.fit_intercept)
        self.assertEqual(classifier.random_state, 2026)
        self.assertEqual(metadata.THRESHOLD, 0.5)

    def test_03_metadata_script_has_only_authorized_estimator_calls(self) -> None:
        source = (ROOT / "scripts/run_a2_2_metadata_confounder_audit.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        calls = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        self.assertEqual(calls.count("fit"), 1)
        self.assertEqual(calls.count("predict_proba"), 1)
        self.assertFalse({"partial_fit", "fit_transform", "predict"} & set(calls))
        self.assertNotIn("a1_10", source.casefold())

    def test_04_package_script_has_no_fit_or_inference_call(self) -> None:
        source = (ROOT / "scripts/build_a2_2_interpretability_package.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(
            {"fit", "partial_fit", "fit_transform", "predict", "predict_proba"} & calls
        )

    def test_05_frozen_fold_parser_requires_grouped_oof_once(self) -> None:
        rows = []
        keys = [f"key-{index}" for index in range(10)]
        for index, key in enumerate(keys):
            validation_fold = (index % 5) + 1
            for fold in range(1, 6):
                role = "outer_validation" if fold == validation_fold else "outer_train"
                rows.append(
                    {
                        "trajectory_key": key,
                        "group_key": f"group-{index}",
                        "target": "success",
                        "label": str(index % 2),
                        "outer_fold": str(fold),
                        "outer_role": role,
                        "official_split": "dev",
                    }
                )
        labels, folds = metadata.frozen_outer_folds(rows, "success")
        self.assertEqual(len(labels), 10)
        self.assertEqual(set(folds), {1, 2, 3, 4, 5})
        validation = [key for _, values in folds.items() for key in values[1]]
        self.assertEqual(sorted(validation), sorted(keys))

    def test_06_deterministic_error_selection_uses_lower_median(self) -> None:
        distances = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
        rows = []
        for index, distance in enumerate(distances):
            rows.append(
                {
                    "target": "success",
                    "scoring_included": "true",
                    "method_id": "FINAL_SUCCESS_B2",
                    "true_label": "0",
                    "predicted_label": "1",
                    "probability": str(0.55 + distance),
                    "frozen_threshold": "0.55",
                    "trajectory_key": f"key-{index}",
                    "benchmark_original": "benchmark",
                    "model_name": "model",
                }
            )
        selected = package.deterministic_error_selection(rows, "success", "FP")
        by_role = {row["case_role"]: row for row in selected}
        self.assertEqual(by_role["borderline"]["trajectory_key"], "key-0")
        self.assertEqual(by_role["median_error_confidence"]["trajectory_key"], "key-2")
        self.assertEqual(by_role["high_confidence_error"]["trajectory_key"], "key-5")

    def test_07_deterministic_ties_use_lexical_ascending(self) -> None:
        rows = []
        for key, probability in (
            ("b-min", 0.56),
            ("a-min", 0.56),
            ("middle", 0.60),
            ("b-max", 0.90),
            ("a-max", 0.90),
        ):
            rows.append(
                {
                    "target": "success",
                    "scoring_included": "true",
                    "method_id": "FINAL_SUCCESS_B2",
                    "true_label": "0",
                    "predicted_label": "1",
                    "probability": str(probability),
                    "frozen_threshold": "0.55",
                    "trajectory_key": key,
                    "benchmark_original": "benchmark",
                    "model_name": "model",
                }
            )
        selected = package.deterministic_error_selection(rows, "success", "FP")
        by_role = {row["case_role"]: row for row in selected}
        self.assertEqual(by_role["borderline"]["trajectory_key"], "a-min")
        self.assertEqual(by_role["high_confidence_error"]["trajectory_key"], "a-max")

    def test_08_safe_context_contains_only_allowed_fields(self) -> None:
        raw = {
            "trajectory_key": "key",
            "metadata": {"model_name": "ignored"},
            "task": {"instruction": "do the task", "context": None},
            "steps": [
                {
                    "step_index": 1,
                    "action": "click x",
                    "observation": "page",
                    "focused_element": "x",
                    "error": "temporary error",
                    "reasoning": "must not pass through",
                }
            ],
            "terminal": {
                "last_step_index": 1,
                "termination_signal": None,
                "last_nonempty_observation": "ignored duplicate",
            },
            "quality_flags": {"ignored": True},
        }
        safe = package.safe_context(raw)
        self.assertEqual(set(safe), package.SAFE_CONTEXT_KEYS)
        self.assertEqual(set(safe["steps"][0]), package.SAFE_STEP_KEYS)
        self.assertNotIn("reasoning", json_keys(safe))
        self.assertNotIn("metadata", json_keys(safe))

    def test_09_safe_context_rejects_banned_root_field(self) -> None:
        with self.assertRaises(package.IntegrityError):
            package.safe_context(
                {
                    "trajectory_key": "key",
                    "reward": 1,
                    "task": {"instruction": "task"},
                    "steps": [],
                    "terminal": {},
                }
            )

    def test_10_frozen_schema_has_13_features_and_four_groups(self) -> None:
        features, groups = package.frozen_features_and_groups()
        self.assertEqual(len(features), 13)
        self.assertEqual(
            set(groups.values()),
            {
                "G1_activity_volume",
                "G2_error",
                "G3_termination",
                "G4_repetition",
            },
        )

    def test_11_required_output_schemas_are_frozen(self) -> None:
        self.assertIn("standardized_coefficient", package.COEFFICIENT_FIELDS)
        self.assertIn("uncertainty_status", package.EVIDENCE_FIELDS)
        self.assertIn("selection_rank", package.MANIFEST_FIELDS)
        self.assertEqual(metadata.PREDICTION_FIELDS[0:3], ("target", "fold", "trajectory_key"))
        self.assertIn("b2_frozen_dev_ap", metadata.SUMMARY_FIELDS)


def json_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(key)
            keys.update(json_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(json_keys(nested))
    return keys


if __name__ == "__main__":
    unittest.main()
