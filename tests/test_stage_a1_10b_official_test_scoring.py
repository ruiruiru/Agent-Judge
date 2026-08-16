"""Synthetic pre-unlock tests for frozen Stage A1.10b scoring."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_stage_a1_10b_official_test_scoring.py"
SPEC = importlib.util.spec_from_file_location("stage_a1_10b", SCRIPT)
assert SPEC and SPEC.loader
stage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stage
SPEC.loader.exec_module(stage)


class A110bPreUnlockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config(ROOT / "configs" / "stage_a1_10b_official_test_scoring.yaml")

    def test_01_authorization_is_exact(self) -> None:
        self.assertEqual(self.config["authorization"], "AUTHORIZE A1.10b TEST LABEL UNLOCK")

    def test_02_a1_10a_commit_and_blind_hash_are_frozen(self) -> None:
        self.assertEqual(self.config["provenance"]["a1_10a_commit"], "cead3cbaa362da4a9918dab32e41b58fffb987d9")
        self.assertEqual(self.config["frozen_inputs"]["blind_predictions"]["sha256"], "a3a232484716ee455a604f03ffd40e6f734a1925ffdfb93e4a3d04118de27c3d")

    def test_03_taskbook_hash_is_exact(self) -> None:
        path = ROOT / self.config["provenance"]["taskbook"]["path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.config["provenance"]["taskbook"]["sha256"])

    def test_04_static_training_and_inference_boundary_is_zero(self) -> None:
        self.assertEqual(stage.static_boundary_counts(), {
            "estimator_training_calls": 0,
            "inference_calls": 0,
            "estimator_or_embedding_imports": 0,
        })

    def test_05_unlock_is_the_only_annotation_byte_open(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
        opens = [
            node for node in ast.walk(functions["unlock_test_labels"])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "read_bytes"
        ]
        self.assertEqual(len(opens), 1)
        preflight_source = ast.unparse(functions["run_preflight"])
        self.assertNotIn("unlock_test_labels", preflight_source)

    def test_06_bootstrap_contract_is_exact(self) -> None:
        bootstrap = self.config["bootstrap"]
        self.assertEqual(bootstrap["n_draws"], 10000)
        self.assertEqual(bootstrap["seed"], 2027)
        self.assertEqual(bootstrap["target_order"], list(stage.TARGETS))
        self.assertFalse(bootstrap["label_stratification"])
        self.assertFalse(bootstrap["trajectory_bootstrap"])
        self.assertFalse(bootstrap["invalid_redraw"])

    def test_07_thresholds_and_roles_are_exact(self) -> None:
        self.assertEqual(
            {target: self.config["targets"][target]["threshold"] for target in stage.TARGETS},
            {"success": 0.55, "looping": 0.55, "side_effect": 0.4},
        )
        self.assertEqual(self.config["targets"]["side_effect"]["role"], "exploratory_only")

    def test_08_grade_confirmed(self) -> None:
        self.assertEqual(stage.grade_target("success", 0.1, 0.01, 0.2)[0], "CONFIRMED_HELDOUT_SIGNAL")

    def test_09_grade_directional_when_ci_touches_zero(self) -> None:
        self.assertEqual(stage.grade_target("looping", 0.1, 0.0, 0.2)[0], "DIRECTIONAL_BUT_NOT_CONFIRMED")

    def test_10_grade_not_confirmed_at_zero_point(self) -> None:
        self.assertEqual(stage.grade_target("success", 0.0, -0.1, 0.1)[0], "NOT_CONFIRMED")

    def test_11_side_effect_never_upgrades(self) -> None:
        self.assertEqual(stage.grade_target("side_effect", 0.9, 0.8, 1.0)[0], "EXPLORATORY_TEST_RESULT")

    def test_12_metric_bundle_class_complete(self) -> None:
        rows = [
            {"true_label": 0, "probability": 0.1, "predicted_label": 0},
            {"true_label": 1, "probability": 0.9, "predicted_label": 1},
        ]
        result = stage.metric_bundle(rows)
        self.assertEqual(result["average_precision"], 1.0)
        self.assertEqual(result["positive_f1"], 1.0)
        self.assertAlmostEqual(result["ap_lift"], 0.5)

    def test_13_single_class_metrics_are_not_imputed(self) -> None:
        result = stage.metric_bundle([
            {"true_label": 0, "probability": 0.1, "predicted_label": 0},
            {"true_label": 0, "probability": 0.2, "predicted_label": 0},
        ])
        self.assertFalse(result["class_complete"])
        for name in ("average_precision", "ap_lift", "positive_f1", "roc_auc"):
            self.assertIsNone(result[name])

    def _join_fixture(self) -> tuple[dict, list[dict[str, str]], list[dict[str, str]], list[dict]]:
        config = copy.deepcopy(self.config)
        config["expected"]["blind_rows"] = 6
        identifiers = []
        entries = []
        blind = []
        for index, benchmark in enumerate(("assistantbench", "webarena")):
            key = f"{benchmark}::task{index}::model"
            identifiers.append({
                "trajectory_key": key, "benchmark_original": benchmark,
                "benchmark_group_primary": benchmark, "normalized_task_id": f"task{index}",
                "model_name": "model",
            })
            entry = {
                "trajectory_key": key, "benchmark_original": benchmark,
                "benchmark_group_primary": benchmark, "task_id": f"task{index}",
                "model_name": "model",
            }
            for target in stage.TARGETS:
                entry[f"{target}_eligible_main"] = True
                entry[f"{target}_label"] = index
                entry[f"{target}_status"] = "single_annotation"
                spec = config["targets"][target]
                probability = 0.9 if index else 0.1
                blind.append({
                    "trajectory_key": key, "benchmark_original": benchmark,
                    "benchmark_group_primary": benchmark, "normalized_task_id": f"task{index}",
                    "model_name": "model", "target": target, "method_id": spec["method_id"],
                    "role": spec["role"], "model_sha256": "frozen", "probability": str(probability),
                    "frozen_threshold": str(spec["threshold"]),
                    "predicted_label": str(int(probability >= spec["threshold"])),
                    "row_key": f"{key}::{target}", "inference_status": "success",
                })
            entries.append(entry)
        return config, blind, identifiers, entries

    def test_14_join_is_complete_and_target_specific(self) -> None:
        config, blind, identifiers, entries = self._join_fixture()
        joined, audit = stage.join_predictions(config, blind, identifiers, entries)
        self.assertEqual(len(joined), 6)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["silent_drops"], 0)

    def test_15_duplicate_prediction_stops(self) -> None:
        config, blind, identifiers, entries = self._join_fixture()
        with self.assertRaises(stage.IntegrityError):
            stage.join_predictions(config, blind + [blind[0]], identifiers, entries)

    def test_16_metadata_mismatch_stops(self) -> None:
        config, blind, identifiers, entries = self._join_fixture()
        blind[0]["benchmark_original"] = "changed"
        with self.assertRaises(stage.IntegrityError):
            stage.join_predictions(config, blind, identifiers, entries)

    def _scored_fixture(self) -> list[dict]:
        rows = []
        for target in stage.TARGETS:
            threshold = self.config["targets"][target]["threshold"]
            for benchmark in stage.BENCHMARKS:
                for group_index, label in enumerate((0, 1)):
                    for model_index in range(2):
                        probability = 0.1 if label == 0 else 0.9
                        rows.append({
                            "trajectory_key": f"{benchmark}::task{group_index}::m{model_index}",
                            "benchmark_original": benchmark,
                            "benchmark_group_primary": benchmark,
                            "normalized_task_id": f"task{group_index}",
                            "model_name": f"m{model_index}", "target": target,
                            "method_id": self.config["targets"][target]["method_id"],
                            "role": self.config["targets"][target]["role"],
                            "model_sha256": "frozen", "probability": probability,
                            "frozen_threshold": threshold,
                            "predicted_label": int(probability >= threshold),
                            "row_key": f"{target}:{benchmark}:{group_index}:{model_index}",
                            "inference_status": "success", "true_label": label,
                            "eligible_main": True, "label_status": "single_annotation",
                            "scoring_included": True,
                            "group_key": f"{benchmark}::task{group_index}",
                        })
        return rows

    def test_17_metric_tables_cover_all_targets_and_benchmarks(self) -> None:
        targets, benchmarks = stage.build_metric_tables(self.config, self._scored_fixture())
        self.assertEqual(len(targets), 3)
        self.assertEqual(len(benchmarks), 12)
        self.assertTrue(all(row["pooled_average_precision"] == 1.0 for row in targets))

    def test_18_bootstrap_is_deterministic_and_group_clustered(self) -> None:
        scored = self._scored_fixture()
        first_draws, first_summary = stage.build_bootstrap(self.config, scored, n_draws=40, seed=2027)
        second_draws, second_summary = stage.build_bootstrap(self.config, scored, n_draws=40, seed=2027)
        self.assertEqual(first_draws, second_draws)
        self.assertEqual(first_summary, second_summary)
        self.assertEqual(len(first_draws), 120)
        self.assertTrue(all(row["sampled_trajectory_n"] == 16 for row in first_draws))

    def test_19_bootstrap_retains_invalid_draws_without_redraw(self) -> None:
        draws, summaries = stage.build_bootstrap(self.config, self._scored_fixture(), n_draws=400, seed=2027)
        self.assertEqual(len(draws), 1200)
        self.assertTrue(any(row["status"] == "invalid_single_class_resample" for row in draws))
        self.assertTrue(all(row["fixed_draw_count"] == 400 for row in summaries))

    def test_20_csv_serialization_is_lf_and_deterministic(self) -> None:
        rows = [{"a": 1, "b": 0.125}]
        first = stage.csv_bytes(["a", "b"], rows)
        self.assertEqual(first, stage.csv_bytes(["a", "b"], rows))
        self.assertNotIn(b"\r\n", first)

    def test_21_all_prohibited_counters_are_zero(self) -> None:
        self.assertTrue(all(value == 0 for value in self.config["prohibited_after_unlock"].values()))

    def test_22_blind_output_is_never_an_a1_10b_output(self) -> None:
        outputs = set(self.config["outputs"].values())
        self.assertNotIn(self.config["frozen_inputs"]["blind_predictions"]["path"], outputs)

    def test_23_no_json_style_boolean_names_in_python(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertTrue(names.isdisjoint({"true", "false", "null"}))


if __name__ == "__main__":
    unittest.main()
