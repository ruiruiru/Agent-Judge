"""Frozen-contract, synthetic, and formal-output tests for Stage A1.7."""

from __future__ import annotations

import ast
import csv
import json
import math
import unittest
from pathlib import Path

import numpy as np

from scripts import extract_stage_a1_7_embeddings as embedding
from scripts import run_stage_a1_7_dense_semantic as stage


class StageA17FrozenContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_01_repo_and_requested_revision_exact(self) -> None:
        self.assertEqual(self.config["model"]["repo_id"], "Qwen/Qwen3-Embedding-0.6B")
        self.assertEqual(self.config["model"]["requested_revision"], "97b0c61")

    def test_02_immutable_revision_full_and_exact(self) -> None:
        revision = self.config["model"]["immutable_revision"]
        self.assertEqual(revision, "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3")
        self.assertEqual(len(revision), 40)

    def test_03_weight_sha_exact(self) -> None:
        self.assertEqual(
            self.config["model"]["weight_sha256"],
            "0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd",
        )

    def test_04_model_license_recorded(self) -> None:
        self.assertEqual(self.config["model"]["license"], "apache-2.0")

    def test_05_primary_input_hash_matches_a13(self) -> None:
        spec = self.config["inputs"]["primary_text"]
        self.assertEqual(embedding.sha256_path(embedding.resolve(spec["path"])), spec["sha256"])
        self.assertEqual(spec["sha256"], "ec2757489c04b4388711826d29a028b24585156c9dab0496d4afe394aa02398a")

    def test_06_primary_interface_has_196_unique_keys(self) -> None:
        records = embedding.read_primary(self.config)
        self.assertEqual(len(records), 196)
        self.assertEqual(len({row["trajectory_key"] for row in records}), 196)

    def test_07_primary_interface_contains_no_labels_targets_or_benchmark_prefix(self) -> None:
        records = embedding.read_primary(self.config)
        self.assertEqual(list(records[0]), embedding.PRIMARY_FIELDS)
        self.assertFalse(any("label" in key or "target" in key for key in records[0]))
        self.assertTrue(all(row["serialized_text"].startswith("[TASK]\n") for row in records))

    def test_08_only_primary_view_is_used(self) -> None:
        records = embedding.read_primary(self.config)
        self.assertEqual({row["input_view"] for row in records}, {"primary_with_natural_errors"})

    def test_09_chunk_contract_exact(self) -> None:
        tokenization = self.config["tokenization"]
        self.assertFalse(tokenization["add_special_tokens"])
        self.assertEqual(tokenization["payload_tokens_per_chunk"], 8191)
        self.assertEqual(tokenization["overlap"], 0)
        self.assertEqual(tokenization["append_eos_count"], 1)
        self.assertFalse(tokenization["silent_truncation"])

    def test_10_chunking_preserves_order_without_overlap(self) -> None:
        payload = list(range(17000))
        chunks = embedding.payload_chunks(payload)
        self.assertEqual([len(chunk) for chunk in chunks], [8191, 8191, 618])
        self.assertEqual([token for chunk in chunks for token in chunk], payload)

    def test_11_empty_payload_stops(self) -> None:
        with self.assertRaises(embedding.IntegrityError):
            embedding.payload_chunks([])

    def test_12_probe_indices_fixed_sixteen(self) -> None:
        indices = self.config["tokenization"]["probe_row_indices"]
        self.assertEqual(len(indices), 16)
        self.assertEqual(indices, [0, 13, 26, 39, 52, 65, 78, 91, 104, 117, 130, 143, 156, 169, 182, 195])

    def test_13_embedding_algorithm_exact(self) -> None:
        spec = self.config["embedding"]
        self.assertEqual(spec["pooling"], "last_eos_hidden_state")
        self.assertEqual(spec["chunk_normalization"], "l2")
        self.assertEqual(spec["trajectory_aggregation"], "payload_token_count_weighted_mean")
        self.assertEqual(spec["trajectory_normalization"], "l2")
        self.assertEqual(spec["output_dimension"], 1024)
        self.assertEqual(spec["output_dtype"], "float32")

    def test_14_determinism_thresholds_exact(self) -> None:
        spec = self.config["embedding"]
        self.assertEqual(spec["determinism_cosine_minimum"], 0.999999)
        self.assertEqual(spec["determinism_max_absolute_difference"], 1e-5)
        self.assertFalse(spec["tf32"])
        self.assertTrue(spec["deterministic_algorithms"])
        self.assertEqual(spec["cublas_workspace_config"], ":4096:8")

    def test_15_no_quantization_finetune_or_prompt(self) -> None:
        model = self.config["model"]
        self.assertFalse(model["quantization"])
        self.assertFalse(model["fine_tune"])
        self.assertFalse(model["target_prompt"])
        self.assertFalse(model["benchmark_prompt"])

    def test_16_extractor_has_no_optimizer_backward_or_training_fit(self) -> None:
        source = (embedding.REPO_ROOT / "scripts" / "extract_stage_a1_7_embeddings.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        self.assertNotIn("backward", attributes)
        self.assertNotIn("optimizer", source.lower())
        self.assertNotIn("fit", attributes)

    def test_17_b4_exactly_six_configs_and_tie_order(self) -> None:
        candidates = stage.candidate_configs(self.config)
        self.assertEqual(len(candidates), 6)
        self.assertEqual([row["class_weight"] for row in candidates[:3]], [None, None, None])
        self.assertEqual([row["C"] for row in candidates[:3]], [0.1, 1.0, 10.0])

    def test_18_lr_semantics_and_no_scaler(self) -> None:
        spec = self.config["classifier"]
        self.assertEqual(spec["penalty"], "l2")
        self.assertEqual(spec["solver"], "liblinear")
        self.assertEqual(spec["max_iter"], 5000)
        self.assertEqual(spec["random_state"], 2026)
        self.assertFalse(spec["standard_scaler"])

    def test_19_threshold_grid_and_tie_break(self) -> None:
        self.assertEqual(self.config["selection"]["thresholds"], [round(i / 100, 2) for i in range(5, 100, 5)])
        self.assertEqual(self.config["selection"]["threshold_tie_break"], ["higher_recall", "closer_to_0.5", "smaller_threshold"])

    def test_20_synthetic_threshold_selection(self) -> None:
        selected, rows = stage.threshold_rows(self.config, [0, 0, 1, 1], [0.1, 0.4, 0.6, 0.9])
        self.assertEqual(sum(bool(row["selected"]) for row in rows), 1)
        self.assertEqual(selected, 0.5)

    def test_21_positive_probability_uses_classes(self) -> None:
        class Fake:
            classes_ = np.asarray([0, 1])

            @staticmethod
            def predict_proba(_: np.ndarray) -> np.ndarray:
                return np.asarray([[0.8, 0.2], [0.1, 0.9]])

        np.testing.assert_allclose(stage.positive_probability(Fake(), np.zeros((2, 1))), [0.2, 0.9])

    def test_22_single_class_metrics_are_missing(self) -> None:
        rows = [
            {"true_label": 0, "predicted_probability": 0.1, "predicted_label": 0},
            {"true_label": 0, "predicted_probability": 0.9, "predicted_label": 1},
        ]
        values = stage.metric_values(rows)
        self.assertEqual(values["metric_status"], "single_class_negative")
        self.assertIsNone(values["pr_auc_average_precision"])
        self.assertIsNone(values["positive_f1"])

    def test_23_frozen_outer_and_inner_hashes(self) -> None:
        for key in ["primary_lobo_manifest", "inner_folds"]:
            spec = self.config["inputs"][key]
            self.assertEqual(embedding.sha256_path(embedding.resolve(spec["path"])), spec["sha256"])

    def test_24_frozen_inner_roles_and_grouping(self) -> None:
        rows, counts = stage._validate_inner_folds(self.config)
        self.assertEqual(len(rows), 2332)
        self.assertEqual(counts["side_effect"]["webarena"], 4)
        self.assertTrue(all(counts[t][d] == 5 for t in stage.TARGETS for d in stage.DOMAINS if (t, d) != ("side_effect", "webarena")))

    def test_25_bootstrap_registry_reused_exactly(self) -> None:
        spec = self.config["inputs"]["bootstrap_registry"]
        self.assertEqual(embedding.sha256_path(embedding.resolve(spec["path"])), spec["sha256"])
        self.assertTrue(self.config["bootstrap"]["registry_reused"])
        self.assertFalse(self.config["bootstrap"]["invalid_redraw"])
        self.assertFalse(self.config["bootstrap"]["trajectory_bootstrap"])

    def test_26_expected_output_counts_exact(self) -> None:
        self.assertEqual(self.config["expected_counts"], {
            "embeddings": 196, "embedding_dimensions": 1024,
            "external_predictions": 583, "selected_inner_oof": 1749,
            "config_selection": 72, "threshold_selection": 228,
            "domain_metrics": 12, "macro_metrics": 3, "pooled_metrics": 3,
        })

    def test_27_formal_execution_is_offline_and_local_only(self) -> None:
        self.assertEqual(self.config["execution"]["formal_network"], 0)
        self.assertTrue(self.config["execution"]["local_files_only"])

    def test_28_test_access_and_all_prohibited_experiments_zero(self) -> None:
        execution = self.config["execution"]
        for key in [
            "test_access", "second_embedding_model", "fine_tune", "quantization",
            "fusion", "new_classifier", "outer_split_regeneration",
            "inner_split_regeneration", "new_bootstrap_registry",
            "trajectory_bootstrap", "secondary_lobo", "lomo", "joint_ood", "llm_judge",
        ]:
            self.assertFalse(execution[key], key)

    def test_29_baseline_lock_and_environment_unchanged(self) -> None:
        for key in ["baseline_lock", "baseline_environment"]:
            spec = self.config["inputs"][key]
            self.assertEqual(embedding.sha256_path(embedding.resolve(spec["path"])), spec["sha256"])

    def test_30_classifier_has_one_fit_site_and_no_fit_transform(self) -> None:
        source = (embedding.REPO_ROOT / "scripts" / "run_stage_a1_7_dense_semantic.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        ]
        self.assertEqual(sum(node.func.attr == "fit" for node in calls), 1)
        self.assertEqual(sum(node.func.attr == "fit_transform" for node in calls), 0)

    def test_30a_bootstrap_verification_key_separates_metrics(self) -> None:
        common = {
            "comparison_id": "Q2", "target": "success", "method_a": stage.BASELINE,
            "method_b": "B3", "scope": "macro", "held_out_group": "",
        }
        ap = {**common, "metric": "ap", "estimand": "macro_ap_delta_A_minus_B"}
        f1 = {**common, "metric": "f1", "estimand": "macro_f1_delta_A_minus_B"}
        self.assertNotEqual(stage.bootstrap_verification_key(ap), stage.bootstrap_verification_key(f1))


class StageA17PreregistrationArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        cls.integrity_path = embedding.resolve(cls.config["outputs"]["prerun_integrity"])
        if not cls.integrity_path.exists():
            raise unittest.SkipTest("A1.7a preregistration artifacts not generated yet")
        cls.integrity = json.loads(cls.integrity_path.read_text(encoding="utf-8"))

    def test_31_model_manifest_matches_snapshot(self) -> None:
        manifest = embedding.verify_model_manifest(self.config)
        self.assertEqual(manifest["hidden_size"], 1024)
        self.assertEqual(manifest["weight_sha256"], self.config["model"]["weight_sha256"])

    def test_32_semantic_environment_is_isolated_and_cuda_available(self) -> None:
        environment = json.loads(embedding.resolve(self.config["outputs"]["semantic_environment"]).read_text(encoding="utf-8"))
        self.assertTrue(environment["semantic_environment_only"])
        self.assertFalse(environment["baseline_environment_modified"])
        self.assertTrue(environment["hardware"]["cuda_available"])
        self.assertGreaterEqual(tuple(map(int, environment["dependencies"]["transformers"].split("."))), (4, 51, 0))

    def test_33_semantic_lock_exactly_records_torch_and_transformers(self) -> None:
        lock = embedding.resolve(self.config["environment"]["semantic_lock"]).read_text(encoding="utf-8")
        self.assertIn("torch==2.7.1+cu128", lock)
        self.assertIn("transformers==4.53.3", lock)

    def test_34_token_audit_has_196_unique_rows(self) -> None:
        rows = embedding.read_csv(embedding.resolve(self.config["outputs"]["tokenization_audit"]))
        self.assertEqual(len(rows), 196)
        self.assertEqual(len({row["trajectory_key"] for row in rows}), 196)

    def test_35_token_audit_has_no_silent_truncation(self) -> None:
        rows = embedding.read_csv(embedding.resolve(self.config["outputs"]["tokenization_audit"]))
        self.assertTrue(all(int(row["max_chunk_payload_tokens"]) <= 8191 for row in rows))
        self.assertTrue(all(int(row["payload_token_count"]) <= int(row["chunk_count"]) * 8191 for row in rows))
        self.assertTrue(all(int(row["payload_token_count"]) > (int(row["chunk_count"]) - 1) * 8191 for row in rows))

    def test_36_preregistered_probe_passes_tolerances(self) -> None:
        probe = self.integrity["determinism_probe"]
        self.assertTrue(probe["passed"])
        self.assertGreaterEqual(probe["minimum_cosine_similarity"], 0.999999)
        self.assertLessEqual(probe["maximum_absolute_difference"], 1e-5)
        self.assertEqual(probe["probe_count"], 16)

    def test_37_preregistration_has_no_formal_embeddings_or_label_fit(self) -> None:
        self.assertEqual(self.integrity["formal_embedding_count"], 0)
        self.assertEqual(self.integrity["real_label_fit_count"], 0)
        self.assertEqual(self.integrity["probe_label_access"], 0)

    def test_38_preregistration_test_and_forbidden_access_zero(self) -> None:
        self.assertEqual(set(self.integrity["test_access"].values()), {0})
        self.assertEqual(self.integrity["forbidden_experiments_executed"], [])

    def test_39_preregistered_file_hashes_recompute_with_documented_fix(self) -> None:
        manifest = stage.assert_preregistered_with_documented_fix(self.config)
        self.assertTrue(manifest["all_b4_outputs_invalidated"])
        self.assertFalse(manifest["embedding_invalidated"])

    def test_40_eos_id_is_unique_integer(self) -> None:
        self.assertIsInstance(self.integrity["eos_token_id"], int)
        self.assertGreater(self.integrity["eos_token_id"], 0)


class StageA17FormalOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        if not embedding.resolve(cls.config["outputs"]["run_summary"]).exists():
            raise unittest.SkipTest("A1.7b formal outputs not generated yet")
        cls.summary = json.loads(embedding.resolve(cls.config["outputs"]["run_summary"]).read_text(encoding="utf-8"))

    def test_41_embedding_integrity(self) -> None:
        checked = embedding.verify_embedding_outputs(self.config)
        self.assertEqual(checked["shape"], [196, 1024])
        self.assertEqual(checked["dtype"], "float32")
        self.assertTrue(checked["finite"])

    def test_42_all_formal_counts_and_metrics_recompute(self) -> None:
        checked = stage.verify_results(self.config)
        self.assertEqual(checked["external_predictions"], 583)
        self.assertEqual(checked["selected_inner_oof"], 1749)
        self.assertEqual(checked["config_selection"], 72)
        self.assertEqual(checked["threshold_selection"], 228)

    def test_43_side_effect_assistantbench_remains_single_class(self) -> None:
        rows = stage.read_csv(embedding.resolve(self.config["outputs"]["domain_metrics"]))
        row = next(item for item in rows if item["target"] == "side_effect" and item["held_out_group"] == "assistantbench")
        self.assertEqual(row["metric_status"], "single_class_negative")
        self.assertEqual(row["positive_count"], "0")
        self.assertEqual(row["negative_count"], "24")
        self.assertEqual(row["pr_auc_average_precision"], "")

    def test_44_q1_to_q5_complete_and_roles_frozen(self) -> None:
        rows = stage.read_csv(embedding.resolve(self.config["outputs"]["bootstrap_primary_summary"]))
        self.assertEqual({row["comparison_id"] for row in rows}, {"Q1", "Q2", "Q3", "Q4", "Q5"})
        self.assertTrue(all(row["role"] == "support_diagnostic_only" for row in rows if row["comparison_id"] == "Q4"))
        self.assertTrue(all(row["role"] == "secondary_complexity_control" for row in rows if row["comparison_id"] == "Q5"))

    def test_45_formal_boundaries_zero(self) -> None:
        self.assertEqual(self.summary["network_access"], 0)
        self.assertTrue(self.summary["local_files_only"])
        self.assertEqual(self.summary["fine_tune_count"], 0)
        self.assertEqual(self.summary["second_embedding_model_count"], 0)
        self.assertEqual(set(self.summary["test_access"].values()), {0})
        self.assertEqual(self.summary["forbidden_experiments_executed"], [])

    def test_46_registry_hash_reused_and_no_new_registry(self) -> None:
        self.assertEqual(self.summary["bootstrap"]["registry_sha256"], self.config["inputs"]["bootstrap_registry"]["sha256"])
        self.assertFalse(self.summary["bootstrap"]["new_registry_generated"])

    def test_47_frozen_input_hashes_unchanged(self) -> None:
        self.assertEqual(self.summary["hashes_before_run"], self.summary["hashes_after_run"])

    def test_48_report_and_machine_summary_exist(self) -> None:
        self.assertTrue(embedding.resolve(self.config["outputs"]["report"]).is_file())
        self.assertTrue(embedding.resolve(self.config["outputs"]["run_summary"]).is_file())


if __name__ == "__main__":
    unittest.main()
