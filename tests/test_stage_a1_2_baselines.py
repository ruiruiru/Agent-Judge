"""Synthetic-model and read-only-integrity tests for Stage A1.2."""

from __future__ import annotations

import copy
import inspect
import math
import unittest
from unittest import mock

import numpy as np

from scripts import run_stage_a1_2_baselines as stage


class ReversedClassModel:
    classes_ = np.asarray([1, 0])

    def predict_proba(self, features: object) -> np.ndarray:
        size = len(features)  # type: ignore[arg-type]
        return np.tile(np.asarray([[0.8, 0.2]]), (size, 1))


class StageA12IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_real_preflight_is_read_only_and_never_fits(self) -> None:
        with mock.patch.object(
            stage.LogisticRegression, "fit", side_effect=AssertionError("real-dev fit prohibited")
        ), mock.patch.object(
            stage.DummyClassifier, "fit", side_effect=AssertionError("real-dev fit prohibited")
        ):
            checked = stage.preflight(self.config)
        self.assertEqual(len(checked["cleaned"]), 196)
        self.assertEqual(set(checked["cleaned"]), set(checked["primary"]))
        self.assertEqual(
            {target: len(labels) for target, labels in checked["labels"].items()},
            {"success": 192, "side_effect": 195, "looping": 196},
        )
        for target in stage.TARGETS:
            self.assertEqual(set(checked["manifests"][target]), {1, 2, 3, 4, 5})

    def test_hashes_are_the_frozen_values(self) -> None:
        self.assertEqual(
            stage.verify_frozen_hashes(self.config),
            {
                item["path"]: item["sha256"]
                for item in [
                    *self.config["inputs"].values(),
                    *self.config["manifests"].values(),
                ]
            },
        )

    def test_boundary_is_exactly_b0_to_b3_primary_dev_only(self) -> None:
        self.assertEqual(
            [item["id"] for item in self.config["baselines"]], stage.BASELINE_IDS
        )
        self.assertEqual(
            self.config["execution"]["input_view"], "primary_with_natural_errors"
        )
        self.assertFalse(self.config["execution"]["test_access"])
        forbidden = set(self.config["execution"]["forbidden_experiments"])
        for name in [
            "test_evaluation",
            "lobo",
            "leave_one_model_out",
            "reasoning_sensitivity",
            "error_ablation",
            "embedding",
            "mlp",
            "xgboost",
            "transformer",
            "llm_judge",
            "char_ngram",
        ]:
            self.assertIn(name, forbidden)


class StageA12StructuralFeatureTests(unittest.TestCase):
    def sample_record(self) -> dict[str, object]:
        return {
            "trajectory_key": "synthetic::task::model",
            "metadata": {"benchmark": "must_not_be_used", "label": 1},
            "quality_flags": {},
            "task": {"instruction": "synthetic"},
            "steps": [
                {
                    "action": "  Click   Button ",
                    "observation": "abc",
                    "focused_element": "button",
                    "error": None,
                    "reasoning": "private reasoning one",
                },
                {
                    "action": "Click Button",
                    "observation": "abcdef",
                    "focused_element": "",
                    "error": "natural error",
                    "reasoning": "private reasoning two",
                },
                {
                    "action": "",
                    "observation": "abcdefghi",
                    "focused_element": None,
                    "error": None,
                    "reasoning": "private reasoning three",
                },
            ],
            "terminal": {
                "last_nonempty_action": "send_msg_to_user('text')",
                "termination_signal": "send_msg_to_user",
            },
        }

    def test_feature_signature_has_no_label_argument_and_order_is_frozen(self) -> None:
        self.assertNotIn("label", inspect.signature(stage.extract_structural_features).parameters)
        self.assertEqual(stage.FEATURE_NAMES, stage.load_config()["structural_features"])
        self.assertEqual(len(stage.FEATURE_NAMES), 13)

    def test_exact_structural_feature_values(self) -> None:
        features = stage.extract_structural_features(self.sample_record())
        self.assertEqual(list(features), stage.FEATURE_NAMES)
        self.assertEqual(features["step_count"], 3)
        self.assertEqual(features["nonempty_action_count"], 2)
        self.assertEqual(features["nonempty_observation_count"], 3)
        self.assertEqual(features["nonempty_focused_element_count"], 1)
        self.assertEqual(features["natural_error_step_count"], 1)
        self.assertAlmostEqual(features["natural_error_step_ratio"], 1 / 3)
        self.assertEqual(features["has_explicit_termination_signal"], 1)
        self.assertEqual(features["action_char_count_total"], 29)
        self.assertEqual(features["observation_char_count_total"], 18)
        self.assertEqual(features["action_char_count_mean_nonempty"], 14.5)
        self.assertEqual(features["observation_char_count_mean_nonempty"], 6)
        self.assertEqual(features["unique_action_ratio"], 0.5)
        self.assertEqual(features["consecutive_duplicate_action_count"], 1)

    def test_missing_denominators_are_zero(self) -> None:
        record = self.sample_record()
        record["steps"] = []
        features = stage.extract_structural_features(record)
        for name in [
            "natural_error_step_ratio",
            "action_char_count_mean_nonempty",
            "observation_char_count_mean_nonempty",
            "unique_action_ratio",
        ]:
            self.assertEqual(features[name], 0)

    def test_terminal_is_not_inferred_from_last_action(self) -> None:
        record = self.sample_record()
        record["terminal"] = {
            "last_nonempty_action": "send_msg_to_user('text')",
            "termination_signal": None,
        }
        self.assertEqual(
            stage.extract_structural_features(record)["has_explicit_termination_signal"], 0
        )

    def test_reasoning_and_metadata_cannot_change_features(self) -> None:
        left = self.sample_record()
        right = copy.deepcopy(left)
        right["metadata"] = {"benchmark": "different", "label": 0, "fold": 5}
        for item in right["steps"]:  # type: ignore[index]
            item["reasoning"] = "completely different"
        self.assertEqual(
            stage.extract_structural_features(left),
            stage.extract_structural_features(right),
        )

    def test_structural_artifact_schema_excludes_labels_identity_and_folds(self) -> None:
        rows = stage.structural_rows({"synthetic::task::model": self.sample_record()})
        self.assertEqual(
            list(rows[0]), ["trajectory_key", *stage.FEATURE_NAMES, "content_sha256"]
        )
        forbidden = {"label", "eligible_main", "benchmark", "model_name", "fold", "task_id"}
        self.assertFalse(forbidden & set(rows[0]))


class StageA12ModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_tfidf_is_word_only_and_validation_token_never_enters_vocabulary(self) -> None:
        train = ["common alpha", "common alpha", "common beta", "common beta"]
        validation = ["validationonlytoken common", "validationonlytoken common"]
        for variant, ngram in [("T1", (1, 1)), ("T2", (1, 2))]:
            vectorizer = stage.make_tfidf(self.config, variant)
            vectorizer.fit(train)
            vectorizer.transform(validation)
            self.assertNotIn("validationonlytoken", vectorizer.vocabulary_)
            self.assertEqual(vectorizer.analyzer, "word")
            self.assertEqual(vectorizer.ngram_range, ngram)
        self.assertEqual(set(self.config["tfidf"]), {"T1", "T2", "common"})

    def test_logistic_regression_is_frozen(self) -> None:
        candidate = stage.candidate_configs(self.config, "B2")[0]
        model = stage.make_lr(self.config, candidate)
        self.assertEqual(model.penalty, "l2")
        self.assertEqual(model.solver, "liblinear")
        self.assertEqual(model.max_iter, 5000)
        self.assertTrue(model.fit_intercept)
        self.assertEqual(model.random_state, 2026)

    def test_candidate_counts_and_tie_break_order_are_exact(self) -> None:
        b2 = stage.candidate_configs(self.config, "B2")
        b3 = stage.candidate_configs(self.config, "B3")
        self.assertEqual(len(b2), 6)
        self.assertEqual(len(b3), 12)
        self.assertEqual(
            [(item["class_weight"], item["C"]) for item in b2],
            [(None, 0.1), (None, 1.0), (None, 10.0), ("balanced", 0.1),
             ("balanced", 1.0), ("balanced", 10.0)],
        )
        self.assertEqual([item["tfidf"] for item in b3[:6]], ["T1"] * 6)
        self.assertEqual([item["tfidf"] for item in b3[6:]], ["T2"] * 6)

    def test_threshold_candidates_and_tie_break_are_deterministic(self) -> None:
        expected = [round(value / 100, 2) for value in range(5, 100, 5)]
        self.assertEqual(self.config["selection"]["thresholds"], expected)
        truth = [1, 1, 0, 0]
        probability = [0.9, 0.6, 0.4, 0.1]
        first, rows_one = stage.select_threshold(self.config, truth, probability)
        second, rows_two = stage.select_threshold(self.config, truth, probability)
        self.assertEqual(first, second)
        self.assertEqual(rows_one, rows_two)
        self.assertEqual(sum(row["selected"] for row in rows_one), 1)

    def test_positive_probability_uses_classes_not_fixed_column(self) -> None:
        probabilities = stage.positive_probability(ReversedClassModel(), np.zeros((3, 1)))
        np.testing.assert_allclose(probabilities, [0.8, 0.8, 0.8])
        self.assertTrue(np.all(np.isfinite(probabilities)))
        self.assertTrue(np.all((0 <= probabilities) & (probabilities <= 1)))

    def test_metrics_use_average_precision_and_positive_class(self) -> None:
        result = stage.metrics([0, 0, 1, 1], [0.1, 0.4, 0.6, 0.9], [0, 0, 1, 1])
        self.assertEqual(result["pr_auc_average_precision"], 1.0)
        self.assertEqual(result["positive_f1"], 1.0)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)

    def test_synthetic_structural_fold_is_reproducible(self) -> None:
        keys = [f"synthetic::{index}" for index in range(20)]
        labels = {key: index % 2 for index, key in enumerate(keys)}
        feature_by_key = {
            key: {name: float(index + offset) for offset, name in enumerate(stage.FEATURE_NAMES)}
            for index, key in enumerate(keys)
        }
        primary = {
            key: {"serialized_text": f"common token class{labels[key]} sample{index}"}
            for index, key in enumerate(keys)
        }
        rows = []
        for index, key in enumerate(keys):
            if index < 12:
                outer_role, inner = "outer_train", "inner_train"
            elif index < 16:
                outer_role, inner = "outer_train", "inner_validation"
            else:
                outer_role, inner = "outer_validation", "not_applicable"
            rows.append(
                {
                    "trajectory_key": key,
                    "group_key": f"group::{index // 2}",
                    "outer_role": outer_role,
                    "inner_split": inner,
                }
            )
        output_one = stage.run_fold(
            self.config, "success", "B2", 1, rows, labels, feature_by_key, primary, []
        )
        output_two = stage.run_fold(
            self.config, "success", "B2", 1, rows, labels, feature_by_key, primary, []
        )
        self.assertEqual(output_one, output_two)


class StageA12AggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = copy.deepcopy(stage.load_config())
        for target in stage.TARGETS:
            cls.config["targets"][target]["expected_samples"] = 10

    def synthetic_rows(self) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        predictions: list[dict[str, object]] = []
        folds: list[dict[str, object]] = []
        for target in stage.TARGETS:
            for baseline in stage.BASELINE_IDS:
                for fold in range(1, 6):
                    y = [0, 1]
                    p = [0.1, 0.9]
                    pred = [0, 1]
                    for position in range(2):
                        predictions.append(
                            {
                                "trajectory_key": f"{target}::{fold}::{position}",
                                "target": target,
                                "baseline_id": baseline,
                                "outer_fold": fold,
                                "true_label": y[position],
                                "predicted_probability": p[position],
                                "predicted_label": pred[position],
                            }
                        )
                    row: dict[str, object] = {
                        "target": target,
                        "baseline_id": baseline,
                        "outer_fold": fold,
                    }
                    row.update(stage.metrics(y, p, pred))
                    folds.append(row)
        return predictions, folds

    def test_fold_mean_sample_std_and_pooled_are_recomputable(self) -> None:
        predictions, folds = self.synthetic_rows()
        pooled = stage.aggregate_results(self.config, predictions, folds)
        self.assertEqual(len(pooled), 12)
        for row in pooled:
            self.assertEqual(row["pooled_pr_auc_average_precision"], 1.0)
            self.assertEqual(row["fold_mean_positive_f1"], 1.0)
            self.assertEqual(row["fold_std_positive_f1"], 0.0)

    def test_duplicate_oof_trajectory_is_rejected(self) -> None:
        predictions, folds = self.synthetic_rows()
        duplicate = copy.deepcopy(predictions[0])
        predictions[-1] = duplicate
        with self.assertRaises(stage.IntegrityError):
            stage.aggregate_results(self.config, predictions, folds)


if __name__ == "__main__":
    unittest.main()
