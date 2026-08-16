"""Real-data read-only guards and synthetic model tests for Stage A1.4."""

from __future__ import annotations

import copy
import inspect
import math
import unittest
from unittest import mock

import numpy as np

from scripts import run_stage_a1_4_lomo as stage


class StageA14PrerunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        with mock.patch.object(stage.a12.LogisticRegression, "fit", side_effect=AssertionError("real-dev fit prohibited")), \
             mock.patch.object(stage.a13.DummyClassifier, "fit", side_effect=AssertionError("real-dev fit prohibited")):
            cls.checked = stage.preflight(cls.config)
        cls.generated = stage.generate_inner_folds(cls.config, cls.checked["manifest"], cls.checked["models"])

    def test_01_real_preflight_is_zero_fit(self) -> None:
        self.assertEqual(len(self.checked["manifest"]), 2332)

    def test_02_models_come_from_manifest_and_are_exactly_four(self) -> None:
        manifest_models = sorted({row["held_out_model"] for row in self.checked["manifest"]}, key=str.casefold)
        self.assertEqual(self.checked["models"], manifest_models)
        self.assertEqual(len(manifest_models), 4)

    def test_03_target_totals_are_frozen(self) -> None:
        self.assertEqual(
            {target: len(labels) for target, labels in self.checked["labels"].items()},
            {"success": 192, "side_effect": 195, "looping": 196},
        )

    def test_04_each_target_model_external_train_and_validation_are_mixed(self) -> None:
        for target in stage.TARGETS:
            for model in self.checked["models"]:
                stat = self.checked["stats"][target][model]
                self.assertGreater(stat["train_negative"], 0)
                self.assertGreater(stat["train_positive"], 0)
                self.assertGreater(stat["validation_negative"], 0)
                self.assertGreater(stat["validation_positive"], 0)

    def test_05_heldout_model_never_has_train_role(self) -> None:
        for row in self.checked["manifest"]:
            expected = "validation" if row["model_name"] == row["held_out_model"] else "train"
            self.assertEqual(row["role"], expected)

    def test_06_each_eligible_key_is_external_once(self) -> None:
        for target in stage.TARGETS:
            validation = [row["trajectory_key"] for row in self.checked["manifest"] if row["target"] == target and row["role"] == "validation"]
            self.assertEqual(len(validation), len(self.checked["labels"][target]))
            self.assertEqual(len(validation), len(set(validation)))

    def test_07_external_group_overlap_is_expected_and_complete(self) -> None:
        for row in self.checked["overlap"]:
            self.assertEqual(row["overlap_group_count"], row["validation_task_groups"])
            self.assertEqual(row["validation_only_group_count"], 0)
            self.assertEqual(row["validation_trajectory_counterpart_rate"], 1.0)

    def test_08_protocol_is_not_joint_task_model_holdout(self) -> None:
        self.assertTrue(self.config["external_group_overlap"]["allowed"])
        self.assertFalse(self.config["external_group_overlap"]["joint_task_model_holdout"])

    def test_09_coverage_matrix_has_all_48_cells(self) -> None:
        self.assertEqual(len(self.checked["coverage"]), 48)
        self.assertEqual(
            len({(row["target"], row["held_out_model"], row["benchmark_group_primary"]) for row in self.checked["coverage"]}),
            48,
        )

    def test_10_meta_llama_visualwebarena_is_the_only_missing_coverage(self) -> None:
        missing = [row for row in self.checked["coverage"] if not row["coverage_present"]]
        self.assertEqual(len(missing), 3)
        self.assertEqual({row["target"] for row in missing}, set(stage.TARGETS))
        self.assertEqual({row["benchmark_group_primary"] for row in missing}, {"visualwebarena"})
        self.assertEqual(len({row["held_out_model"] for row in missing}), 1)
        self.assertIn("meta-llama", missing[0]["held_out_model"].casefold())

    def test_11_coverage_artifact_recomputes_exactly(self) -> None:
        recorded = stage.read_csv(stage.resolve(self.config["outputs"]["coverage_matrix"]))
        normalized = [{key: str(value) for key, value in row.items()} for row in self.checked["coverage"]]
        self.assertEqual(recorded, normalized)

    def test_12_model_literal_audit_has_no_injection(self) -> None:
        summary = self.checked["literal_summary"]
        self.assertFalse(summary["metadata_or_serializer_injection_detected"])
        self.assertFalse(summary["redaction_performed"])
        self.assertEqual(summary["trajectory_count"], 196)

    def test_13_model_literal_artifact_recomputes_exactly(self) -> None:
        recorded = stage.read_csv(stage.resolve(self.config["outputs"]["model_literal_audit"]))
        normalized = [{key: str(value) for key, value in row.items()} for row in self.checked["literal_rows"]]
        self.assertEqual(recorded, normalized)

    def test_14_group_key_never_crosses_inner_fold(self) -> None:
        for target in stage.TARGETS:
            for model in self.checked["models"]:
                by_group: dict[str, set[int]] = {}
                for row in self.generated:
                    if row["target"] == target and row["held_out_model"] == model and row["role"] == "train":
                        by_group.setdefault(row["group_key"], set()).add(int(row["inner_fold"]))
                self.assertEqual({len(folds) for folds in by_group.values()}, {1})

    def test_15_external_rows_have_blank_inner_fold(self) -> None:
        self.assertTrue(all(row["inner_fold"] == "" for row in self.generated if row["role"] == "external_validation"))

    def test_16_each_training_trajectory_has_one_inner_validation_fold(self) -> None:
        keys = [(row["target"], row["held_out_model"], row["trajectory_key"]) for row in self.generated if row["role"] == "train"]
        self.assertEqual(len(keys), len(set(keys)))

    def test_17_every_inner_train_and_validation_is_mixed(self) -> None:
        counts = stage.validate_inner_folds(self.config, self.generated, self.checked["models"])
        self.assertEqual(set(counts), set(stage.TARGETS))

    def test_18_maximum_feasible_fold_count_is_used(self) -> None:
        counts = stage.validate_inner_folds(self.config, self.generated, self.checked["models"])
        self.assertEqual({value for target in counts.values() for value in target.values()}, {5})

    def test_19_inner_folds_are_deterministic(self) -> None:
        regenerated = stage.generate_inner_folds(self.config, self.checked["manifest"], self.checked["models"])
        self.assertEqual(self.generated, regenerated)

    def test_20_frozen_inner_artifact_recomputes_exactly(self) -> None:
        recorded = stage.read_csv(stage.resolve(self.config["inner_folds"]["path"]))
        normalized = [{key: str(value) for key, value in row.items()} for row in self.generated]
        self.assertEqual(recorded, normalized)


class StageA14ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_21_all_frozen_hashes_match(self) -> None:
        verified = stage.verify_frozen_hashes(self.config)
        self.assertIn("artifacts/leave_one_model_out_manifest.csv", verified)
        self.assertIn("artifacts/a1_3_lobo_run_summary.json", verified)

    def test_22_a1_2_and_a1_3_commits_are_verified(self) -> None:
        verified = stage.verify_source_commits(self.config)
        self.assertEqual(len(verified), 5)

    def test_23_environment_is_exactly_frozen(self) -> None:
        current = stage.verify_environment(self.config)
        self.assertEqual(current["python"], "3.14.6")
        self.assertEqual(current["dependencies"]["scikit-learn"], "1.9.0")

    def test_24_baselines_are_exactly_b0_to_b3(self) -> None:
        self.assertEqual([row["id"] for row in self.config["baselines"]], stage.BASELINE_IDS)

    def test_25_b2_has_exactly_13_frozen_features(self) -> None:
        self.assertEqual(self.config["structural_features"], stage.a12.FEATURE_NAMES)

    def test_26_b2_has_six_candidates_in_frozen_tie_order(self) -> None:
        candidates = stage.a12.candidate_configs(self.config, "B2")
        self.assertEqual(len(candidates), 6)
        self.assertEqual([(row["class_weight"], row["C"]) for row in candidates],
                         [(None, .1), (None, 1.), (None, 10.), ("balanced", .1), ("balanced", 1.), ("balanced", 10.)])

    def test_27_b3_has_twelve_candidates_with_t1_first(self) -> None:
        candidates = stage.a12.candidate_configs(self.config, "B3")
        self.assertEqual(len(candidates), 12)
        self.assertEqual([row["tfidf"] for row in candidates[:6]], ["T1"] * 6)
        self.assertEqual([row["tfidf"] for row in candidates[6:]], ["T2"] * 6)

    def test_28_logistic_regression_contract_is_unchanged(self) -> None:
        model = stage.a12.make_lr(self.config, stage.a12.candidate_configs(self.config, "B2")[0])
        self.assertEqual((model.penalty, model.solver, model.max_iter, model.fit_intercept, model.random_state),
                         ("l2", "liblinear", 5000, True, 2026))

    def test_29_tfidf_is_word_t1_t2_only(self) -> None:
        for variant, ngram in [("T1", (1, 1)), ("T2", (1, 2))]:
            vectorizer = stage.a12.make_tfidf(self.config, variant)
            self.assertEqual((vectorizer.analyzer, vectorizer.ngram_range), ("word", ngram))

    def test_30_threshold_grid_and_tie_break_are_frozen(self) -> None:
        self.assertEqual(self.config["selection"]["thresholds"], [round(i / 100, 2) for i in range(5, 100, 5)])
        self.assertEqual(self.config["selection"]["threshold_tie_break"], ["higher_recall", "closer_to_0.5", "smaller_threshold"])

    def test_31_test_manifest_is_not_an_input(self) -> None:
        input_paths = {spec["path"] for spec in stage._hash_specs(self.config)}
        self.assertNotIn("artifacts/test_manifest.csv", input_paths)

    def test_32_test_access_and_network_gpu_are_zero(self) -> None:
        self.assertFalse(self.config["execution"]["test_access"])
        self.assertFalse(self.config["execution"]["test_manifest_access"])
        self.assertFalse(self.config["environment"]["formal_run_network_allowed"])
        self.assertFalse(self.config["environment"]["gpu_allowed"])

    def test_33_forbidden_experiment_boundary_is_complete(self) -> None:
        forbidden = set(self.config["execution"]["forbidden_experiments"])
        self.assertTrue({"reasoning_sensitivity", "error_ablation", "B2_B3_fusion", "test_evaluation", "task_model_joint_holdout"}.issubset(forbidden))

    def test_34_formal_run_requires_clean_preregistration(self) -> None:
        source = inspect.getsource(stage.assert_clean_preregistration)
        self.assertIn("status", source)
        self.assertIn("required_preregistration_commit_subject", source)
        self.assertIn("committed A1.4a bytes", source)

    def test_35_prerun_integrity_proves_zero_fit_zero_predictions(self) -> None:
        integrity = stage.json.loads(stage.resolve(self.config["environment"]["prerun_integrity_artifact"]).read_text(encoding="utf-8"))
        self.assertEqual((integrity["real_dev_estimator_fit_count"], integrity["prediction_count"]), (0, 0))


class StageA14SyntheticBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_36_metadata_or_serializer_model_injection_stops(self) -> None:
        model = "GenericAgent-provider_Model-Example-123"
        primary = {"k": {"input_view": "primary_with_natural_errors", "serialized_text": f"[MODEL]\n{model}"}}
        index = {"k": {"model_name": model}}
        with self.assertRaises(stage.IntegrityError):
            stage.audit_model_literals(primary, index, [model])

    def test_37_natural_task_model_literal_is_reported_not_redacted(self) -> None:
        model = "GenericAgent-provider_Model-Example-123"
        primary = {"k": {"input_view": "primary_with_natural_errors", "serialized_text": f"[TASK]\ncompare {model}"}}
        index = {"k": {"model_name": model}}
        rows, summary = stage.audit_model_literals(primary, index, [model])
        self.assertTrue(any(row["match_type"] == "exact_model_name" for row in rows))
        self.assertFalse(summary["redaction_performed"])

    def test_38_heldout_model_in_fit_keys_stops_before_fit(self) -> None:
        checked = {"index": {"held": {"model_name": "M1"}, "other": {"model_name": "M2"}}}
        with self.assertRaises(stage.IntegrityError):
            stage._assert_fit_isolation(checked, "M1", ["held"], ["other"], False)

    def test_39_heldout_model_in_inner_validation_stops(self) -> None:
        checked = {"index": {"held": {"model_name": "M1"}, "other": {"model_name": "M2"}}}
        with self.assertRaises(stage.IntegrityError):
            stage._assert_fit_isolation(checked, "M1", ["other"], ["held"], False)

    def test_40_valid_final_external_isolation_passes(self) -> None:
        checked = {"index": {"held": {"model_name": "M1"}, "other": {"model_name": "M2"}}}
        stage._assert_fit_isolation(checked, "M1", ["other"], ["held"], True)

    def test_41_scaler_and_tfidf_fit_only_train_arguments(self) -> None:
        source = inspect.getsource(stage.a13.fit_predict)
        self.assertIn("scaler.fit_transform(_matrix(structural, train_keys))", source)
        self.assertIn("vectorizer.fit_transform(train_text)", source)
        self.assertIn("vectorizer.transform(validation_text)", source)

    def test_42_configuration_selection_precedes_external_prediction(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertLess(source.index("selected_row ="), source.index("external_probability ="))

    def test_43_prior_results_are_used_only_in_post_run_comparison(self) -> None:
        run_source = inspect.getsource(stage.run_models)
        self.assertNotIn("a1_2_inner_config_selection", run_source)
        self.assertNotIn("a1_3_lobo_inner_config_selection", run_source)
        self.assertLess(run_source.index("pooled_rows ="), run_source.index("comparison_rows ="))

    def test_44_no_coverage_diagnostic_leaves_metrics_missing(self) -> None:
        rows = stage._diagnostic_rows(self.config, [], ["M"])
        self.assertEqual(len(rows), 3 * 4 * 1 * 4)
        self.assertTrue(all(row["metric_status"] == "no_coverage" for row in rows))
        self.assertTrue(all(row["pr_auc_average_precision"] is None and row["positive_f1"] is None for row in rows))

    def test_45_single_class_diagnostic_leaves_ap_f1_missing(self) -> None:
        prediction = [{
            "target": "success", "baseline_id": "B0", "held_out_model": "M",
            "benchmark_group_primary": "assistantbench", "true_label": 0,
            "predicted_probability": .1, "predicted_label": 0,
        }]
        row = stage._diagnostic_rows(self.config, prediction, ["M"])[0]
        self.assertEqual(row["metric_status"], "single_class_negative")
        self.assertIsNone(row["pr_auc_average_precision"])
        self.assertIsNone(row["positive_f1"])

    def test_46_macro_uses_sample_standard_deviation(self) -> None:
        rows = []
        for index, value in enumerate([.2, .3, .4, .5]):
            row = {
                "target": "success", "baseline_id": "B0",
                "coverage_status": "full_primary_benchmark_coverage" if index < 3 else "partial_primary_benchmark_coverage",
            }
            row.update({metric: value for metric in [*stage.METRIC_NAMES, "ap_lift"]})
            rows.append(row)
        macro = stage._macro_rows(rows)[0]
        self.assertAlmostEqual(macro["positive_f1_all_model_macro_std"], sample_stdev([.2, .3, .4, .5]))
        self.assertAlmostEqual(macro["positive_f1_full_coverage_macro_std"], sample_stdev([.2, .3, .4]))

    def test_47_expected_output_counts_are_frozen(self) -> None:
        execution = self.config["execution"]
        self.assertEqual((execution["expected_external_prediction_rows"], execution["expected_selected_inner_oof_rows"],
                          execution["expected_config_selection_rows"], execution["expected_threshold_selection_rows"],
                          execution["expected_model_metric_rows"]), (2332, 6996, 240, 912, 48))

    def test_48_failure_path_invalidates_whole_run(self) -> None:
        source = inspect.getsource(stage.formal_run)
        self.assertIn("INVALIDATED", source)
        self.assertIn("every target/model/baseline", source)

    def test_49_formal_hashes_are_checked_before_and_after(self) -> None:
        source = inspect.getsource(stage.run_models)
        self.assertIn("hashes_before_run", source)
        self.assertIn("hashes_after_run", source)

    def test_50_signal_grade_labels_are_exact(self) -> None:
        source = inspect.getsource(stage._signal_grades)
        for label in ["robust_cross_model_signal", "partial_or_model_specific_signal", "no_cross_model_signal", "not_assessable"]:
            self.assertIn(label, source)

    def test_51_report_has_explicit_stop_boundary(self) -> None:
        self.assertIn("Do not begin A1.5", inspect.getsource(stage.render_report))

    def test_52_external_prediction_schema_contains_required_fields(self) -> None:
        source = inspect.getsource(stage.run_models)
        for field in ["trajectory_key", "group_key", "held_out_model", "benchmark_group_primary", "coverage_status"]:
            self.assertIn(f'"{field}"', source)


@unittest.skipUnless(stage.resolve("artifacts/a1_4_lomo_run_summary.json").exists(), "formal A1.4b outputs not generated yet")
class StageA14FormalOutputTests(unittest.TestCase):
    def test_53_independent_verification_is_zero_fit(self) -> None:
        config = stage.load_config()
        with mock.patch.object(stage.a12.LogisticRegression, "fit", side_effect=AssertionError("verification fit prohibited")), \
             mock.patch.object(stage.a13.DummyClassifier, "fit", side_effect=AssertionError("verification fit prohibited")):
            result = stage.verify_results(config)
        self.assertEqual(result["external_predictions"], 2332)
        self.assertEqual(result["inner_selected_oof"], 6996)
        self.assertEqual(result["test_access"], 0)

    def test_54_verification_is_deterministic(self) -> None:
        config = stage.load_config()
        self.assertEqual(stage.verify_results(config), stage.verify_results(config))


def json_text(value: object) -> str:
    return stage.json.dumps(value, sort_keys=True)


def sample_stdev(values: list[float]) -> float:
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))


if __name__ == "__main__":
    unittest.main()
