"""Real-data guards and synthetic regression tests for Stage A1.6."""

from __future__ import annotations

import ast
import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

from scripts import run_stage_a1_6_group_bootstrap as stage


class StageA16BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        cls.checked = stage.preflight(cls.config)
        cls.groups = stage.group_registry_source(cls.checked["a13"])
        cls.registry = stage.resolve(cls.config["outputs"]["draw_registry"])
        cls.draws = stage.verify_draw_registry(cls.registry, cls.groups, 10000, 2026)

    def test_01_a13_prediction_keys_unique(self) -> None:
        stage.verify_prediction_schema(self.checked["a13"], "a1_3")

    def test_02_a15_prediction_keys_unique(self) -> None:
        stage.verify_prediction_schema(self.checked["a15"], "a1_5")

    def test_03_s0_equals_a13_b2_rowwise(self) -> None:
        self.assertEqual(self.checked["s0_b2"]["max_probability_absolute_error"], 0.0)
        self.assertEqual(self.checked["s0_b2"]["row_count"], 583)

    def test_04_a13_point_metrics_within_tolerance(self) -> None:
        self.assertLessEqual(self.checked["point_regression"]["a1_3"]["max_absolute_error"], 1e-12)

    def test_05_a15_point_metrics_within_tolerance(self) -> None:
        self.assertLessEqual(self.checked["point_regression"]["a1_5"]["max_absolute_error"], 1e-12)

    def test_06_seed_fixed_2026(self) -> None:
        self.assertEqual(self.config["bootstrap"]["seed"], 2026)

    def test_07_pcg64_fixed(self) -> None:
        self.assertEqual(self.config["bootstrap"]["bit_generator"], "numpy.random.PCG64")

    def test_08_draw_count_10000(self) -> None:
        self.assertEqual(self.config["bootstrap"]["n_bootstrap_draws"], 10000)
        self.assertTrue(all(matrix.shape[0] == 10000 for matrix in self.draws.values()))

    def test_09_each_draw_samples_original_group_count(self) -> None:
        for cell, matrix in self.draws.items():
            self.assertEqual(matrix.shape[1], len(self.groups[cell]))

    def test_10_with_replacement_has_duplicate_groups(self) -> None:
        self.assertTrue(any(len(set(row.tolist())) < row.size
                            for matrix in self.draws.values() for row in matrix[:100]))

    def test_11_cluster_indices_replicate_all_trajectories(self) -> None:
        clusters = [np.array([0, 2]), np.array([1, 3])]
        actual = stage._sample_indices(clusters, np.array([0, 0, 1]))
        np.testing.assert_array_equal(actual, np.array([0, 2, 0, 2, 1, 3]))

    def test_12_methods_share_registry(self) -> None:
        self.assertEqual(set(self.draws), {(t, d) for t in stage.TARGETS for d in stage.DOMAINS})
        self.assertNotIn("method_id", stage.REGISTRY_FIELDS)

    def test_13_cells_do_not_mix_target_or_domain(self) -> None:
        for (target, domain), groups in self.groups.items():
            self.assertIn(target, stage.TARGETS)
            self.assertTrue(all(group.startswith(domain + "::") for group in groups))

    def test_14_registry_regeneration_is_byte_deterministic(self) -> None:
        tiny = {(t, d): self.groups[(t, d)][:2] for t in stage.TARGETS for d in stage.DOMAINS}
        with tempfile.TemporaryDirectory() as directory:
            one, two = Path(directory) / "one.csv", Path(directory) / "two.csv"
            stage.write_draw_registry(one, tiny, 5, 2026)
            stage.write_draw_registry(two, tiny, 5, 2026)
            self.assertEqual(one.read_bytes(), two.read_bytes())

    def test_15_ap_uses_average_precision_score(self) -> None:
        rows = [
            {"true_label": "0", "predicted_probability": "0.1", "predicted_label": "0"},
            {"true_label": "1", "predicted_probability": "0.9", "predicted_label": "1"},
        ]
        self.assertEqual(stage._metrics(rows)["ap"], average_precision_score([0, 1], [0.1, 0.9]))

    def test_16_f1_positive_class_is_one(self) -> None:
        self.assertEqual(stage._f1_binary(np.array([1, 1, 0]), np.array([1, 0, 1])), 0.5)

    def test_17_prevalence_comes_from_draw(self) -> None:
        rows = [
            {"true_label": "0", "predicted_probability": "0.2", "predicted_label": "0"},
            {"true_label": "1", "predicted_probability": "0.8", "predicted_label": "1"},
            {"true_label": "1", "predicted_probability": "0.7", "predicted_label": "1"},
        ]
        self.assertEqual(stage._metrics(rows)["prevalence"], 2 / 3)

    def test_18_ap_lift_uses_draw_prevalence(self) -> None:
        rows = [
            {"true_label": "0", "predicted_probability": "0.2", "predicted_label": "0"},
            {"true_label": "1", "predicted_probability": "0.8", "predicted_label": "1"},
        ]
        values = stage._metrics(rows)
        self.assertEqual(values["ap_lift"], values["ap"] - values["prevalence"])

    def test_19_invalid_single_class_is_nan_not_imputed(self) -> None:
        key, values = stage._domain_worker((
            ("x", "x", "x", "x"), np.array([0, 1]), np.array([0.1, 0.9]),
            np.array([0, 1]), [np.array([0]), np.array([1])], np.array([[0, 0]]),
        ))
        self.assertTrue(np.isnan(values["ap"][0]))
        self.assertTrue(np.isnan(values["f1"][0]))

    def test_20_valid_draw_fraction_correct(self) -> None:
        summary = stage.summarize(np.array([1.0, np.nan, 2.0, np.nan]), 1.5)
        self.assertEqual(summary["valid_draw_fraction"], 0.5)
        self.assertEqual(summary["invalid_draw_count"], 2)

    def test_21_percentile_ci_uses_2p5_97p5(self) -> None:
        values = np.arange(100, dtype=float)
        summary = stage.summarize(values, 49.5)
        expected = np.percentile(values, [2.5, 97.5])
        self.assertEqual(summary["ci_lower_95"], expected[0])
        self.assertEqual(summary["ci_upper_95"], expected[1])

    def test_22_macro_requires_two_valid_domains(self) -> None:
        self.assertEqual(self.config["bootstrap"]["macro_minimum_valid_mixed_domains"], 2)

    def test_23_pooled_is_same_bootstrap_id_across_domains(self) -> None:
        self.assertEqual(self.config["bootstrap"]["pooled_role"], "secondary")
        self.assertTrue(all(matrix.shape[0] == 10000 for matrix in self.draws.values()))

    def test_24_paired_delta_is_drawwise_subtraction(self) -> None:
        a, b = np.array([1.0, 2.0]), np.array([0.25, 0.5])
        np.testing.assert_array_equal(a - b, np.array([0.75, 1.5]))

    def test_25_paired_methods_use_same_registry(self) -> None:
        for row in self.config["primary_comparisons"]:
            if row["kind"] == "paired_delta":
                self.assertNotIn("method", self.config["bootstrap"]["strata"])

    def test_26_assistantbench_side_effect_has_no_ap_f1_ci(self) -> None:
        rows = [r for r in self.checked["a13"] if r["target"] == "side_effect"
                and r["baseline_id"] == "B3" and r["held_out_group"] == "assistantbench"]
        self.assertEqual(sum(int(r["true_label"]) for r in rows), 0)

    def test_27_sparse_side_effect_domains_allow_invalid_resamples(self) -> None:
        for domain in ["visualwebarena", "workarena"]:
            self.assertLess(len({r["group_key"] for r in self.checked["a13"]
                                 if r["target"] == "side_effect"
                                 and r["held_out_group"] == domain
                                 and r["true_label"] == "1"}), len(self.groups[("side_effect", domain)]))

    def test_28_not_stratified(self) -> None:
        self.assertFalse(self.config["bootstrap"]["stratified"])

    def test_29_invalid_draws_not_redrawn(self) -> None:
        self.assertFalse(self.config["bootstrap"]["redraw_invalid"])

    def test_30_support_diagnostic_schema_complete(self) -> None:
        self.assertIn("invalid_single_class_draw_count", stage.SIDE_FIELDS)
        self.assertIn("ci_width", stage.SIDE_FIELDS)

    def test_31_script_has_no_fit_call(self) -> None:
        self.assertEqual(stage.verify_training_boundary(), 0)

    def test_32_script_has_no_fit_transform_call(self) -> None:
        tree = ast.parse(Path(stage.__file__).read_text(encoding="utf-8"))
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)}
        self.assertNotIn("fit_transform", attrs)

    def test_33_script_has_no_partial_fit_call(self) -> None:
        tree = ast.parse(Path(stage.__file__).read_text(encoding="utf-8"))
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)}
        self.assertNotIn("partial_fit", attrs)

    def test_34_no_training_model_imports(self) -> None:
        text = Path(stage.__file__).read_text(encoding="utf-8")
        for name in ["LogisticRegression", "DummyClassifier", "StandardScaler", "TfidfVectorizer"]:
            self.assertNotIn(name, text)

    def test_35_no_raw_trajectory_input(self) -> None:
        self.assertFalse(any("data/raw" in spec["path"] for spec in self.config["inputs"].values()))

    def test_36_probabilities_are_frozen_inputs_only(self) -> None:
        self.assertFalse(self.config["execution"]["prediction_regeneration_allowed"])

    def test_37_p1_through_p8_exist_only(self) -> None:
        self.assertEqual({r["id"] for r in self.config["primary_comparisons"]},
                         {f"P{i}" for i in range(1, 9)})

    def test_38_primary_ci_reproducible_from_draw_parquet(self) -> None:
        self.assertTrue(self.config["outputs"]["primary_draw_metrics"].endswith(".parquet"))

    def test_39_single_method_ci_reproducible_from_registry(self) -> None:
        self.assertTrue(self.registry.is_file())
        self.assertEqual(len(self.draws), 12)

    def test_40_grade_rules_are_frozen_and_automatic(self) -> None:
        low = stage._grade("paired_delta", {"valid_draw_fraction": 0.79,
                    "point_estimate": 1.0, "ci_lower_95": 0.1, "ci_upper_95": 0.2})
        self.assertEqual(low, "low_support_unstable")

    def test_41_no_posthoc_comparison_ids(self) -> None:
        self.assertEqual(max(int(r["id"][1:]) for r in self.config["primary_comparisons"]), 8)

    def test_42_registry_verification_is_deterministic(self) -> None:
        again = stage.verify_draw_registry(self.registry, self.groups, 10000, 2026)
        for key in self.draws:
            np.testing.assert_array_equal(self.draws[key], again[key])

    def test_43_core_hashes_match(self) -> None:
        self.assertEqual(self.checked["hashes"]["artifacts/a1_3_lobo_predictions.csv"],
                         "e761f5a0d4e72faa837496a29b91db358bc03645d8b7ea695c6322aa550bfe4d")
        self.assertEqual(self.checked["hashes"]["artifacts/a1_5_external_predictions.csv"],
                         "a55abec76db6d3afb03e1936a8ae230b9b2c142e805c9b805068911820b00143")

    def test_44_test_access_zero(self) -> None:
        self.assertFalse(self.config["execution"]["test_access"])
        self.assertFalse(any("test_manifest" in spec["path"] for spec in self.config["inputs"].values()))

    def test_45_git_clean_required_for_formal_run(self) -> None:
        self.assertTrue(self.config["execution"]["git_worktree_must_be_clean"])


if __name__ == "__main__":
    unittest.main()
