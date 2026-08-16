"""Dependency-light guards for Stage A2.1 efficiency benchmarking."""

from __future__ import annotations

import ast
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_a2_1_efficiency_benchmark.py"
SPEC = importlib.util.spec_from_file_location("a2_1", SCRIPT_PATH)
assert SPEC and SPEC.loader
A2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A2)


class StageA21EfficiencyTests(unittest.TestCase):
    def test_frozen_contract_constants(self) -> None:
        self.assertEqual(A2.CLAIM_MATRIX_SHA256, "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175")
        self.assertEqual(A2.MAIN_TABLE_SHA256, "c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947")
        self.assertEqual(A2.B2_DIMENSION, 13)
        self.assertEqual(len(A2.FEATURE_NAMES), 13)
        self.assertEqual(A2.B4_DIMENSION, 1024)
        self.assertEqual(A2.QWEN_REVISION, "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3")
        self.assertEqual(A2.TRAJECTORY_COUNT, 196)

    def test_exact_repetition_contract(self) -> None:
        self.assertEqual(A2.WARMUP_REPETITIONS, 1)
        self.assertEqual(A2.B2_MEASURED_REPETITIONS, 5)
        self.assertEqual(A2.B4_MEASURED_REPETITIONS, 3)

    def test_no_training_or_metric_calls_in_ast(self) -> None:
        tree = ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute):
                calls.append(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.append(node.func.id)
        self.assertFalse({"fit", "partial_fit", "fit_predict", "fit_transform"} & set(calls))
        self.assertFalse({"average_precision_score", "f1_score", "roc_auc_score", "bootstrap"} & set(calls))

    def test_no_official_test_dependency(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8").lower()
        for token in ("artifacts/a1_10", "data/test", "test_manifest", "test_label", "test_eligibility"):
            self.assertNotIn(token, source)

    def test_output_schemas(self) -> None:
        self.assertIn("peak_gpu_reserved_mb", A2.RAW_FIELDS)
        self.assertIn("semantic_encoder_size_mb", A2.SUMMARY_FIELDS)
        self.assertEqual(A2.RELATIVE_FIELDS[:5], (
            "dimension_ratio_B4_over_B2", "representation_size_ratio_B4_over_B2",
            "extraction_time_ratio_B4_over_B2", "classifier_inference_ratio_B4_over_B2",
            "peak_memory_ratio_B4_over_B2",
        ))

    def test_safe_ratio(self) -> None:
        self.assertEqual(A2.safe_ratio(1024, 13), 1024 / 13)
        self.assertEqual(A2.safe_ratio(1, 0), "NA")
        self.assertEqual(A2.safe_ratio("NA", 3), "NA")

    def test_windows_peak_rss_measurement(self) -> None:
        self.assertGreater(A2.peak_rss_mb(), 0.0)

    def test_relative_ratio_arithmetic(self) -> None:
        summary = [
            {"method": "B2", "dimension": 13, "representation_size_bytes": 100,
             "median_extraction_ms_per_trajectory": 2.0,
             "median_inference_ms_per_trajectory": 0.5, "peak_cpu_rss_mb": 10.0},
            {"method": "B4", "dimension": 1024, "representation_size_bytes": 4000,
             "median_extraction_ms_per_trajectory": 50.0,
             "median_inference_ms_per_trajectory": 2.0, "peak_cpu_rss_mb": 30.0},
        ]
        row = A2.relative_cost(summary)[0]
        self.assertEqual(row["dimension_ratio_B4_over_B2"], 1024 / 13)
        self.assertEqual(row["representation_size_ratio_B4_over_B2"], 40.0)
        self.assertEqual(row["extraction_time_ratio_B4_over_B2"], 25.0)
        self.assertEqual(row["classifier_inference_ratio_B4_over_B2"], 4.0)
        self.assertEqual(row["peak_memory_ratio_B4_over_B2"], 3.0)

    def test_atomic_machine_json_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.json"
            A2.write_json(path, {"b": 2, "a": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"a": 1, "b": 2})
            self.assertTrue(path.read_bytes().endswith(b"\n"))

    def test_frozen_artifact_hash_guards(self) -> None:
        self.assertEqual(A2.verify_file(A2.CLAIM_MATRIX_PATH, A2.CLAIM_MATRIX_SHA256), A2.CLAIM_MATRIX_SHA256)
        self.assertEqual(A2.verify_file(A2.MAIN_TABLE_PATH, A2.MAIN_TABLE_SHA256), A2.MAIN_TABLE_SHA256)
        self.assertEqual(A2.verify_file(A2.STRUCTURAL_PATH, A2.STRUCTURAL_SHA256), A2.STRUCTURAL_SHA256)

    def test_model_manifest_revision_and_dimension(self) -> None:
        manifest = json.loads((REPO_ROOT / A2.MODEL_MANIFEST_PATH).read_text(encoding="utf-8"))
        self.assertEqual(manifest["immutable_revision"], A2.QWEN_REVISION)
        self.assertEqual(manifest["hidden_size"], A2.B4_DIMENSION)
        self.assertEqual(manifest["weight_sha256"], A2.QWEN_WEIGHT_SHA256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
