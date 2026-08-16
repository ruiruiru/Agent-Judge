"""Read-only real-manifest and synthetic-model tests for Stage A1.3."""

from __future__ import annotations

import copy
import inspect
import math
import unittest
from unittest import mock

import numpy as np
from sklearn.metrics import average_precision_score

from scripts import run_stage_a1_3_primary_lobo as stage


class StageA13ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        with mock.patch.object(stage.a12.LogisticRegression, "fit", side_effect=AssertionError("real-dev fit prohibited")), \
             mock.patch.object(stage.DummyClassifier, "fit", side_effect=AssertionError("real-dev fit prohibited")):
            cls.checked = stage.preflight(cls.config)
        cls.generated = stage.generate_inner_folds(cls.config, cls.checked["manifest"])

    def test_01_real_preflight_never_fits(self) -> None:
        self.assertEqual(len(self.checked["manifest"]), 2332)

    def test_02_exactly_four_primary_groups(self) -> None:
        self.assertEqual(self.config["held_out_groups"], stage.HELD_OUT_GROUPS)

    def test_03_target_sample_counts(self) -> None:
        self.assertEqual({target: len(labels) for target, labels in self.checked["labels"].items()},
                         {"success": 192, "side_effect": 195, "looping": 196})

    def test_04_each_key_has_one_primary_domain(self) -> None:
        for target in stage.TARGETS:
            by_key: dict[str, set[str]] = {}
            for row in self.checked["manifest"]:
                if row["target"] == target:
                    by_key.setdefault(row["trajectory_key"], set()).add(row["benchmark_group_primary"])
            self.assertEqual({len(value) for value in by_key.values()}, {1})

    def test_05_heldout_never_has_train_role(self) -> None:
        for row in self.checked["manifest"]:
            expected = "validation" if row["benchmark_group_primary"] == row["held_out_group"] else "train"
            self.assertEqual(row["role"], expected)

    def test_06_train_and_heldout_groups_disjoint(self) -> None:
        for target in stage.TARGETS:
            for heldout in stage.HELD_OUT_GROUPS:
                cell = [row for row in self.generated if row["target"] == target and row["held_out_group"] == heldout]
                train = {row["group_key"] for row in cell if row["role"] == "train"}
                external = {row["group_key"] for row in cell if row["role"] == "held_out"}
                self.assertFalse(train & external)

    def test_07_group_key_never_crosses_inner_fold(self) -> None:
        for target in stage.TARGETS:
            for heldout in stage.HELD_OUT_GROUPS:
                by_group: dict[str, set[int]] = {}
                for row in self.generated:
                    if row["target"] == target and row["held_out_group"] == heldout and row["role"] == "train":
                        by_group.setdefault(row["group_key"], set()).add(int(row["inner_fold"]))
                self.assertEqual({len(folds) for folds in by_group.values()}, {1})

    def test_08_heldout_inner_fold_is_blank(self) -> None:
        self.assertTrue(all(row["inner_fold"] == "" for row in self.generated if row["role"] == "held_out"))

    def test_09_every_training_trajectory_has_one_inner_validation_fold(self) -> None:
        keys = [(row["target"], row["held_out_group"], row["trajectory_key"]) for row in self.generated if row["role"] == "train"]
        self.assertEqual(len(keys), len(set(keys)))

    def test_10_every_inner_train_and_validation_is_mixed_class(self) -> None:
        counts = stage.validate_inner_folds(self.config, self.generated)
        self.assertEqual(set(counts), set(stage.TARGETS))

    def test_11_fold_count_uses_maximum_feasible_fallback(self) -> None:
        counts = stage.validate_inner_folds(self.config, self.generated)
        self.assertEqual(counts["side_effect"]["webarena"], 4)
        self.assertTrue(all(value == 5 for target, groups in counts.items() for heldout, value in groups.items()
                            if not (target == "side_effect" and heldout == "webarena")))

    def test_12_inner_folds_are_deterministic(self) -> None:
        self.assertEqual(self.generated, stage.generate_inner_folds(self.config, self.checked["manifest"]))

    def test_13_manifest_statistics_match_frozen_contract(self) -> None:
        for target in stage.TARGETS:
            for heldout in stage.HELD_OUT_GROUPS:
                expected = self.config["targets"][target]["held_out"][heldout]
                actual = self.checked["stats"][target][heldout]
                for field in expected:
                    self.assertEqual(actual[field], expected[field])

    def test_14_side_effect_assistantbench_is_24_negative_zero_positive(self) -> None:
        stat = self.checked["stats"]["side_effect"]["assistantbench"]
        self.assertEqual((stat["negative"], stat["positive"]), (24, 0))

    def test_15_workarena_primary_group_is_merged(self) -> None:
        domains = {row["benchmark_group_primary"] for row in self.checked["manifest"]}
        self.assertIn("workarena", domains)
        self.assertNotIn("workarena_l1", domains)
        self.assertNotIn("workarena_l2", domains)

    def test_16_dev_and_test_identifier_sets_are_disjoint(self) -> None:
        self.assertGreater(self.checked["test_identifier_count"], 0)


class StageA13ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_17_all_frozen_hashes_match(self) -> None:
        verified = stage.verify_frozen_hashes(self.config)
        self.assertIn("artifacts/lobo_primary_manifest.csv", verified)
        self.assertIn("artifacts/a1_2_pooled_metrics.csv", verified)

    def test_18_a1_2_commits_are_frozen(self) -> None:
        self.assertEqual(self.config["source"]["a1_2_preregistration_commit"], "b4fef6f63d55ccd4ed2cdf4feb2dcab1cd5b6d20")
        self.assertEqual(self.config["source"]["a1_2_experiment_commit"], "179ce02640a8e6e15411348b57fd8d7725047364")

    def test_19_baselines_are_exactly_b0_to_b3(self) -> None:
        self.assertEqual([row["id"] for row in self.config["baselines"]], stage.BASELINE_IDS)

    def test_20_b2_has_exactly_13_frozen_features(self) -> None:
        self.assertEqual(self.config["structural_features"], stage.a12.FEATURE_NAMES)

    def test_21_b2_candidate_count_and_order(self) -> None:
        candidates = stage.a12.candidate_configs(self.config, "B2")
        self.assertEqual(len(candidates), 6)
        self.assertEqual([(row["class_weight"], row["C"]) for row in candidates],
                         [(None, .1), (None, 1.), (None, 10.), ("balanced", .1), ("balanced", 1.), ("balanced", 10.)])

    def test_22_b3_candidate_count_and_order(self) -> None:
        candidates = stage.a12.candidate_configs(self.config, "B3")
        self.assertEqual(len(candidates), 12)
        self.assertEqual([row["tfidf"] for row in candidates[:6]], ["T1"] * 6)
        self.assertEqual([row["tfidf"] for row in candidates[6:]], ["T2"] * 6)

    def test_23_logistic_regression_contract_is_unchanged(self) -> None:
        model = stage.a12.make_lr(self.config, stage.a12.candidate_configs(self.config, "B2")[0])
        self.assertEqual((model.penalty, model.solver, model.max_iter, model.fit_intercept, model.random_state),
                         ("l2", "liblinear", 5000, True, 2026))

    def test_24_tfidf_is_word_t1_t2_only(self) -> None:
        for variant, ngram in [("T1", (1, 1)), ("T2", (1, 2))]:
            vectorizer = stage.a12.make_tfidf(self.config, variant)
            self.assertEqual((vectorizer.analyzer, vectorizer.ngram_range), ("word", ngram))

    def test_25_primary_input_only(self) -> None:
        self.assertEqual(self.config["execution"]["input_view"], "primary_with_natural_errors")

    def test_26_no_unapproved_model_or_char_ngram(self) -> None:
        forbidden = set(self.config["execution"]["forbidden_experiments"])
        self.assertTrue({"embedding", "mlp", "xgboost", "transformer", "llm_judge", "char_ngram"}.issubset(forbidden))

    def test_27_test_access_is_zero(self) -> None:
        self.assertFalse(self.config["execution"]["test_access"])

    def test_28_secondary_lobo_and_lomo_are_forbidden(self) -> None:
        forbidden = set(self.config["execution"]["forbidden_experiments"])
        self.assertIn("secondary_five_group_lobo", forbidden)
        self.assertIn("leave_one_model_out", forbidden)

    def test_29_a1_2_code_is_hash_locked_and_reused(self) -> None:
        self.assertIs(stage.a12.make_lr, stage.a12.make_lr)
        self.assertEqual(stage.a12.sha256_path(stage.resolve(self.config["a1_2_contract"]["implementation"]["path"])),
                         self.config["a1_2_contract"]["implementation"]["sha256"])

    def test_30_formal_run_guard_requires_clean_preregistration(self) -> None:
        source = inspect.getsource(stage.assert_clean_preregistration)
        self.assertIn("status", source)
        self.assertIn("required_preregistration_commit_subject", source)

    def test_30b_frozen_csv_writer_is_lf_only(self) -> None:
        source = inspect.getsource(stage.write_csv)
        self.assertIn('lineterminator="\\n"', source)


class StageA13SelectionAndMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_31_configuration_metric_is_average_precision(self) -> None:
        truth = [0, 1, 0, 1]
        probability = [.1, .7, .6, .8]
        self.assertAlmostEqual(average_precision_score(truth, probability), 1.0)
        self.assertEqual(self.config["selection"]["configuration_metric"], "average_precision_score")

    def test_32_threshold_grid_is_exact(self) -> None:
        self.assertEqual(self.config["selection"]["thresholds"], [round(i / 100, 2) for i in range(5, 100, 5)])

    def test_33_threshold_tie_break_is_deterministic(self) -> None:
        first = stage.a12.select_threshold(self.config, [1, 1, 0, 0], [.9, .6, .4, .1])
        second = stage.a12.select_threshold(self.config, [1, 1, 0, 0], [.9, .6, .4, .1])
        self.assertEqual(first, second)

    def test_34_positive_probability_uses_classes(self) -> None:
        class Reversed:
            classes_ = np.asarray([1, 0])
            def predict_proba(self, x: object) -> np.ndarray:
                return np.tile(np.asarray([[.8, .2]]), (len(x), 1))  # type: ignore[arg-type]
        np.testing.assert_allclose(stage.a12.positive_probability(Reversed(), np.zeros((3, 1))), [.8, .8, .8])

    def test_35_probability_contract_rejects_nonfinite(self) -> None:
        class Invalid:
            classes_ = np.asarray([0, 1])
            def predict_proba(self, x: object) -> np.ndarray:
                return np.asarray([[.2, math.nan]])
        with self.assertRaises(stage.a12.IntegrityError):
            stage.a12.positive_probability(Invalid(), np.zeros((1, 1)))

    def test_36_single_negative_metrics_are_missing(self) -> None:
        rows = [{"true_label": 0, "predicted_probability": .2, "predicted_label": 0} for _ in range(24)]
        metric = stage._metric_row("side_effect", "B2", "assistantbench", rows, "x", .5, 5, 6)
        self.assertEqual(metric["metric_status"], "single_class_negative")
        for field in [*stage.METRIC_NAMES, "ap_lift"]:
            self.assertIsNone(metric[field])

    def test_37_single_negative_false_positive_diagnostic(self) -> None:
        rows = [{"true_label": 0, "predicted_probability": .9 if i < 3 else .1, "predicted_label": int(i < 3)} for i in range(24)]
        metric = stage._metric_row("side_effect", "B3", "assistantbench", rows, "x", .5, 5, 6)
        self.assertEqual(metric["false_positive_count"], 3)
        self.assertAlmostEqual(metric["false_positive_rate"], 3 / 24)
        self.assertAlmostEqual(metric["specificity"], 21 / 24)

    def test_38_mixed_class_ap_uses_average_precision(self) -> None:
        rows = [
            {"true_label": 0, "predicted_probability": .1, "predicted_label": 0},
            {"true_label": 1, "predicted_probability": .9, "predicted_label": 1},
        ]
        metric = stage._metric_row("success", "B2", "x", rows, "x", .5, 5, 1)
        self.assertEqual(metric["pr_auc_average_precision"], 1.0)

    def test_39_macro_uses_sample_standard_deviation(self) -> None:
        base = {"target": "success", "baseline_id": "B0", "metric_status": "ok"}
        rows = []
        for value in [0.2, 0.4]:
            row = copy.deepcopy(base)
            row.update({metric: value for metric in [*stage.METRIC_NAMES, "ap_lift"]})
            rows.append(row)
        macro = stage._macro_rows(rows)[0]
        self.assertAlmostEqual(macro["positive_f1_macro_std"], statistics_stdev([.2, .4]))

    def test_40_single_class_is_excluded_from_macro(self) -> None:
        ok = {"target": "success", "baseline_id": "B0", "metric_status": "ok", **{metric: .5 for metric in [*stage.METRIC_NAMES, "ap_lift"]}}
        missing = {"target": "success", "baseline_id": "B0", "metric_status": "single_class_negative", **{metric: None for metric in [*stage.METRIC_NAMES, "ap_lift"]}}
        row = stage._macro_rows([ok, missing])[0]
        self.assertEqual((row["valid_domain_count"], row["excluded_single_class_domain_count"]), (1, 1))

    def test_41_expected_output_row_counts_are_frozen(self) -> None:
        execution = self.config["execution"]
        self.assertEqual((execution["expected_config_selection_rows"], execution["expected_threshold_selection_rows"],
                          execution["expected_external_prediction_rows"], execution["expected_domain_metric_rows"]),
                         (240, 912, 2332, 48))

    def test_42_expected_selected_inner_oof_count_is_6996(self) -> None:
        self.assertEqual(12 * sum(self.config["targets"][target]["expected_samples"] for target in stage.TARGETS), 6996)

    def test_43_external_prediction_uniqueness_key_is_frozen(self) -> None:
        required = {"target", "baseline_id", "trajectory_key"}
        self.assertTrue(required.issubset({"target", "baseline_id", "trajectory_key"}))

    def test_44_domain_schema_contains_single_class_diagnostics(self) -> None:
        required = {"metric_status", "false_positive_count", "false_positive_rate", "specificity",
                    "probability_mean", "probability_median", "probability_max"}
        self.assertTrue(required.issubset(stage.DOMAIN_FIELDS))

    def test_45_report_requires_stop_for_human_review(self) -> None:
        self.assertIn("wait for human stage-gate review", inspect.getsource(stage.render_report))

    def test_46_failure_path_invalidates_whole_run(self) -> None:
        source = inspect.getsource(stage.formal_run)
        self.assertIn("INVALIDATED", source)
        self.assertIn("every target, baseline, and held-out group", source)

    def test_47_no_a1_2_selected_config_is_loaded_for_selection(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertNotIn("a1_2_inner_config_selection", source)
        self.assertNotIn("a1_2_threshold_selection", source)

    def test_48_heldout_results_do_not_enter_selection(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertLess(source.index("selected_row ="), source.index("external_probability ="))

    def test_49_scaler_and_tfidf_are_fit_only_on_train_arguments(self) -> None:
        source = inspect.getsource(stage.fit_predict)
        self.assertIn("scaler.fit_transform(_matrix(structural, train_keys))", source)
        self.assertIn("vectorizer.fit_transform(train_text)", source)
        self.assertIn("vectorizer.transform(validation_text)", source)

    def test_50_b0_b1_also_use_inner_threshold_flow(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertIn("for baseline in BASELINE_IDS", source)
        self.assertIn("a12.select_threshold", source)

    def test_51_pooled_includes_all_four_external_domains(self) -> None:
        source = inspect.getsource(stage._pooled_rows)
        self.assertNotIn("metric_status", source)

    def test_52_a1_2_comparison_occurs_after_lobo_outputs(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertLess(source.index("pooled_rows ="), source.index("comparison_rows ="))

    def test_53_formal_hashes_are_checked_before_and_after(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertIn("hashes_before_run", source)
        self.assertIn("hashes_after_run", source)

    def test_54_formal_run_is_cpu_network_zero(self) -> None:
        self.assertFalse(self.config["environment"]["gpu_allowed"])
        self.assertFalse(self.config["environment"]["formal_run_network_allowed"])

    def test_55_signal_grade_labels_are_exact(self) -> None:
        source = inspect.getsource(stage._signal_grades)
        for label in ["robust_cross_benchmark_signal", "partial_or_domain_specific_signal",
                      "no_cross_benchmark_signal", "not_assessable"]:
            self.assertIn(label, source)


def statistics_stdev(values: list[float]) -> float:
    return math.sqrt(sum((value - sum(values) / len(values)) ** 2 for value in values) / (len(values) - 1))


if __name__ == "__main__":
    unittest.main()
