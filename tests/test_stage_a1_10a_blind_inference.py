"""Pre-raw-content tests for the frozen Stage A1.10a implementation."""

from __future__ import annotations

import ast
import csv
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

import numpy as np
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_stage_a1_10a_blind_inference.py"
SPEC = importlib.util.spec_from_file_location("stage_a1_10a", SCRIPT)
assert SPEC and SPEC.loader
stage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stage
SPEC.loader.exec_module(stage)


class DummyProbabilityModel:
    classes_ = np.asarray([0, 1])

    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        positive = np.linspace(0.1, 0.9, len(features))
        return np.column_stack([1.0 - positive, positive])


class A110aPreRawTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_01_taskbook_hash_is_exact(self) -> None:
        spec = self.config["taskbook"]
        self.assertEqual(stage.sha256_path(stage.resolve(spec["path"])), spec["sha256"])

    def test_02_only_a1_10a_is_authorized(self) -> None:
        self.assertEqual(self.config["authorization"], "AUTHORIZE A1.10a BLIND TEST INFERENCE")
        self.assertTrue(self.config["execution"]["stop_after_a1_10a"])

    def test_03_no_label_eligibility_or_metric_source_is_configured(self) -> None:
        execution = self.config["execution"]
        self.assertFalse(execution["label_source_configured"])
        self.assertFalse(execution["eligibility_source_configured"])
        self.assertFalse(execution["metric_computation_configured"])

    def test_04_all_prohibited_counters_are_zero(self) -> None:
        self.assertTrue(all(int(value) == 0 for value in self.config["prohibited_experiments"].values()))

    def test_05_final_forbidden_access_counters_are_zero(self) -> None:
        access = self.config["test_access_final"]
        self.assertEqual(access["labels"], 0)
        self.assertEqual(access["eligibility"], 0)
        self.assertEqual(access["metrics"], 0)

    def test_06_training_call_ast_count_is_zero(self) -> None:
        self.assertEqual(stage.training_call_count(SCRIPT), 0)

    def test_07_script_has_no_metric_library_import(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("sklearn.metrics" in name for name in imports))

    def test_08_frozen_feature_schema_is_exact(self) -> None:
        self.assertEqual(
            self.config["structural_features"],
            stage._baseline_module().FEATURE_NAMES,
        )
        self.assertEqual(len(self.config["structural_features"]), 13)

    def test_09_frozen_thresholds_and_roles_are_exact(self) -> None:
        self.assertEqual(self.config["models"]["success"]["threshold"], 0.55)
        self.assertEqual(self.config["models"]["looping"]["threshold"], 0.55)
        self.assertEqual(self.config["models"]["side_effect"]["threshold"], 0.40)
        self.assertEqual(self.config["models"]["side_effect"]["role"], "exploratory_only")
        self.assertFalse(self.config["models"]["side_effect"]["confirmatory_eligible"])

    def test_10_frozen_model_hashes_are_exact(self) -> None:
        for spec in self.config["models"].values():
            self.assertEqual(stage.sha256_path(stage.resolve(spec["path"])), spec["sha256"])

    def test_11_qwen_revision_hash_and_contract_are_exact(self) -> None:
        qwen = self.config["qwen"]
        self.assertEqual(qwen["immutable_revision"], "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3")
        self.assertEqual(qwen["weight_sha256"], "0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd")
        self.assertEqual(qwen["payload_tokens_per_chunk"], 8191)
        self.assertEqual(qwen["overlap"], 0)
        self.assertEqual(qwen["pooling"], "last_eos_hidden_state")
        self.assertEqual(qwen["output_dimension"], 1024)

    def test_12_identifier_validation_uses_only_sealed_fields(self) -> None:
        row = {
            "trajectory_key": "bench::task.1::model",
            "benchmark_original": "bench",
            "benchmark_split_namespace": "bench",
            "benchmark_group_primary": "bench",
            "benchmark_group_secondary": "bench",
            "task_id": "task.1",
            "model_name": "model",
            "official_split": "test",
            "annotation_count": "1",
        }
        stats = stage.validate_identifier_rows([row], 1)
        self.assertEqual(stats["rows"], 1)
        self.assertEqual(stats["duplicate_trajectory_keys"], 0)

    def test_13_identifier_validation_rejects_forbidden_column(self) -> None:
        row = {
            "trajectory_key": "bench::task.1::model",
            "benchmark_original": "bench",
            "benchmark_split_namespace": "bench",
            "benchmark_group_primary": "bench",
            "benchmark_group_secondary": "bench",
            "task_id": "task.1",
            "model_name": "model",
            "official_split": "test",
            "annotation_count": "1",
            "true_label": "0",
        }
        with self.assertRaises(stage.IntegrityError):
            stage.validate_identifier_rows([row], 1)

    def test_14_split_guard_alias_preserves_frozen_dev_primary_bytes(self) -> None:
        with (ROOT / "artifacts" / "dev_probe_manifest.csv").open(encoding="utf-8", newline="") as handle:
            probe = next(csv.DictReader(handle))
        source = stage.corpus.DevSource(
            trajectory_key=probe["trajectory_key"],
            benchmark_original=probe["benchmark_original"],
            benchmark_split_namespace=probe["benchmark_split_namespace"],
            benchmark_group_primary=probe["benchmark_group_primary"],
            benchmark_group_secondary=probe["benchmark_split_namespace"],
            task_id=probe["task_id"],
            model_name=probe["model_name"],
            official_split="test",
        )
        remote = stage.corpus.RemoteFile(
            path=probe["expected_repository_path"],
            size=int(probe["file_size_bytes"]),
            oid="test-only-parity",
        )
        raw = json.loads((ROOT / probe["local_relative_path"]).read_text(encoding="utf-8"))
        known_types, _ = stage.corpus._load_known_types()
        bundle = stage.build_primary_bundle(raw, source, remote, probe["sha256"], known_types)
        expected = None
        with (ROOT / "data" / "processed" / "dev_serialized_primary.jsonl").open(encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if record["trajectory_key"] == source.trajectory_key:
                    expected = record
                    break
        self.assertIsNotNone(expected)
        self.assertEqual(bundle["serialized_text"], expected["serialized_text"])
        self.assertEqual(bundle["content_sha256"], expected["content_sha256"])
        self.assertEqual(bundle["cleaned"]["metadata"]["official_split"], "test")

    def test_15_primary_bundle_has_no_sensitivity_or_terminal_serialization(self) -> None:
        raw = {
            "goal": "do a task",
            "steps": [{"action": "click('x')", "axtree_pruned": "page", "reasoning": "private"}],
        }
        source = stage.corpus.DevSource(
            trajectory_key="bench::task.1::model", benchmark_original="bench",
            benchmark_split_namespace="bench", benchmark_group_primary="bench",
            benchmark_group_secondary="bench", task_id="task.1", model_name="model",
            official_split="test",
        )
        remote = stage.corpus.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        # The frozen builder permits unknown fields but excludes them from input.
        bundle = stage.build_primary_bundle(raw, source, remote, "a" * 64, set())
        self.assertNotIn("REASONING:", bundle["serialized_text"])
        self.assertNotIn("[TERMINAL]", bundle["serialized_text"])

    def test_16_positive_probability_is_bounded_without_training(self) -> None:
        values = stage.positive_probability(DummyProbabilityModel(), np.zeros((4, 2)))
        self.assertTrue(np.isfinite(values).all())
        self.assertTrue(((values >= 0) & (values <= 1)).all())

    def test_17_row_key_is_deterministic_and_target_specific(self) -> None:
        first = stage.deterministic_row_key("k", "success", "FINAL_SUCCESS_B2")
        second = stage.deterministic_row_key("k", "success", "FINAL_SUCCESS_B2")
        other = stage.deterministic_row_key("k", "looping", "FINAL_LOOPING_B2")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)

    def test_18_prediction_schema_allows_predicted_label_but_no_truth(self) -> None:
        self.assertIn("predicted_label", stage.PREDICTION_FIELDS)
        self.assertNotIn("true_label", stage.PREDICTION_FIELDS)
        self.assertNotIn("eligibility", stage.PREDICTION_FIELDS)
        self.assertNotIn("metric", stage.PREDICTION_FIELDS)

    def test_19_output_binary_has_explicit_git_attribute(self) -> None:
        attributes = (ROOT / "artifacts" / ".gitattributes").read_text(encoding="utf-8")
        self.assertIn("a1_10a_*.npy -text", attributes)

    def test_20_raw_and_resumable_test_paths_are_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/test_download_cache/", ignored)
        self.assertIn("data/test_build_temp/", ignored)


if __name__ == "__main__":
    unittest.main()
