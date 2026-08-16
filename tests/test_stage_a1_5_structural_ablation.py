"""Read-only real-data guards and synthetic tests for Stage A1.5."""

from __future__ import annotations

import inspect
import json
import math
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from scripts import run_stage_a1_5_structural_ablation as stage


class StageA15PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        with mock.patch.object(
            stage.StandardScaler, "fit", side_effect=AssertionError("real-dev scaler fit prohibited")
        ), mock.patch.object(
            stage.a12.LogisticRegression,
            "fit",
            side_effect=AssertionError("real-dev estimator fit prohibited"),
        ):
            cls.checked = stage.preflight(cls.config)

    def test_01_real_preflight_performs_zero_fits(self) -> None:
        self.assertEqual(len(self.checked["structural"]), 196)
        self.assertEqual(len(self.checked["folds"]), 2332)

    def test_02_fixed_source_revisions(self) -> None:
        self.assertEqual(
            self.checked["source_revisions"],
            {
                "github_commit": "f838338886d723d40b586309465a38277803d9e6",
                "huggingface_revision": "b6d17e646009d6cb63d5dd7be78807b680693f61",
            },
        )

    def test_03_a13_a14_commits_and_artifacts_are_locked(self) -> None:
        self.assertEqual(set(self.checked["verified_commits"]), set(self.config["approved_upstream"]))
        self.assertEqual(
            self.checked["verified_hashes"]["artifacts/dev_structural_features.csv"],
            "2dcd9f5a5a22c40d318f2a7fe1303cdcc0c27832d2ab443c0f3dbe2a1f631556",
        )
        self.assertIn("artifacts/a1_3_lobo_run_summary.json", self.checked["verified_hashes"])
        self.assertIn("artifacts/a1_4_lomo_run_summary.json", self.checked["verified_hashes"])

    def test_04_structural_schema_is_exactly_13_in_order(self) -> None:
        first = next(iter(self.checked["structural"].values()))
        self.assertEqual(list(first), ["trajectory_key", *stage.FEATURE_NAMES, "content_sha256"])
        self.assertEqual(len(stage.FEATURE_NAMES), 13)

    def test_05_four_groups_are_disjoint_and_exhaustive(self) -> None:
        groups = self.config["feature_groups"]
        flattened = [feature for group in stage.GROUP_IDS for feature in groups[group]]
        self.assertEqual(len(flattened), 13)
        self.assertEqual(len(set(flattened)), 13)
        self.assertEqual(set(flattened), set(stage.FEATURE_NAMES))

    def test_06_variant_registry_is_exactly_s0_through_s6(self) -> None:
        self.assertEqual([row["id"] for row in self.config["variants"]], stage.VARIANT_IDS)
        self.assertEqual(
            [len(stage._variant_features(self.config)[variant]) for variant in stage.VARIANT_IDS],
            [13, 12, 11, 5, 11, 10, 3],
        )

    def test_07_each_variant_has_only_preregistered_features(self) -> None:
        actual = stage._variant_features(self.config)
        self.assertEqual(actual, stage._expected_variant_features(self.config))
        self.assertNotIn("has_explicit_termination_signal", actual["S1_no_termination"])
        self.assertNotIn("unique_action_ratio", actual["S2_no_repetition"])
        self.assertEqual(
            actual["S6_termination_repetition_only"],
            [
                "has_explicit_termination_signal",
                "unique_action_ratio",
                "consecutive_duplicate_action_count",
            ],
        )

    def test_08_exactly_six_configs_in_frozen_tie_break_order(self) -> None:
        candidates = stage.candidate_configs(self.config)
        self.assertEqual(len(candidates), 6)
        self.assertEqual(
            [row["config_id"] for row in candidates],
            [
                "B2_C0p1_cw_none", "B2_C1p0_cw_none", "B2_C10p0_cw_none",
                "B2_C0p1_cw_balanced", "B2_C1p0_cw_balanced",
                "B2_C10p0_cw_balanced",
            ],
        )

    def test_09_lr_and_threshold_contract_is_exact(self) -> None:
        lr = self.config["logistic_regression"]
        self.assertEqual(
            {key: lr[key] for key in ["penalty", "solver", "max_iter", "fit_intercept", "random_state"]},
            {
                "penalty": "l2", "solver": "liblinear", "max_iter": 5000,
                "fit_intercept": True, "random_state": 2026,
            },
        )
        self.assertEqual(len(self.config["selection"]["thresholds"]), 19)

    def test_10_outer_and_inner_are_reused_not_regenerated(self) -> None:
        source = inspect.getsource(stage)
        self.assertNotIn("def generate_inner", source)
        self.assertFalse(self.config["execution"]["regenerate_outer_or_inner_splits"])
        self.assertEqual(
            self.checked["verified_hashes"]["artifacts/lobo_primary_manifest.csv"],
            "16735afc8defd5d91bf2d23ba7773a1f0515feafc238ad1cec2df0dc530b0191",
        )
        self.assertEqual(
            self.checked["verified_hashes"]["artifacts/a1_3_lobo_inner_folds.csv"],
            "22c02eabc7e3fca84b920069d430b484d9c6c52c475d711b9190d920a5347b35",
        )

    def test_11_heldout_benchmark_never_enters_inner_selection(self) -> None:
        for target in stage.TARGETS:
            for heldout in stage.HELD_OUT_GROUPS:
                cell = [
                    row for row in self.checked["folds"]
                    if row["target"] == target and row["held_out_group"] == heldout
                ]
                train_groups = {row["group_key"] for row in cell if row["role"] == "train"}
                held_groups = {row["group_key"] for row in cell if row["role"] == "held_out"}
                self.assertFalse(train_groups & held_groups)
                self.assertTrue(all(row["inner_fold"] == "" for row in cell if row["role"] == "held_out"))

    def test_12_heldout_statistics_match_a13(self) -> None:
        self.assertEqual(
            {
                target: sum(group["samples"] for group in groups.values())
                for target, groups in self.checked["held_out_statistics"].items()
            },
            {"success": 192, "side_effect": 195, "looping": 196},
        )
        self.assertEqual(
            self.checked["held_out_statistics"]["side_effect"]["assistantbench"]["positive"],
            0,
        )

    def test_13_test_and_forbidden_boundaries_are_zero_scope(self) -> None:
        self.assertFalse(self.config["execution"]["test_access"])
        self.assertEqual(
            set(self.config["inputs"]),
            {"structural_features", "label_index", "primary_lobo_manifest", "a1_3_inner_folds"},
        )
        self.assertEqual(self.config["execution"]["model_input_exactly"], "artifacts/dev_structural_features.csv")
        self.assertNotIn("test_manifest", json.dumps(self.config["inputs"]))

    def test_14_feature_registry_has_91_rows_when_preregistered(self) -> None:
        path = stage.resolve(self.config["outputs"]["feature_group_registry"])
        if not path.exists():
            self.skipTest("feature registry is created by --write-prerun")
        rows = stage.read_csv(path)
        self.assertEqual(len(rows), 91)
        self.assertEqual(list(rows[0]), stage.REGISTRY_FIELDS)

    def test_15_prerun_artifact_proves_zero_fit_when_present(self) -> None:
        path = stage.resolve(self.config["environment"]["prerun_integrity_artifact"])
        if not path.exists():
            self.skipTest("prerun integrity is created by --write-prerun")
        record = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(record["real_dev_scaler_fit_count"], 0)
        self.assertEqual(record["real_dev_estimator_fit_count"], 0)
        self.assertEqual(record["formal_prediction_count"], 0)


class StageA15SyntheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()

    def test_16_threshold_selection_uses_f1_then_frozen_ties(self) -> None:
        threshold, rows = stage.a12.select_threshold(
            self.config, [0, 0, 1, 1], [0.1, 0.4, 0.6, 0.9]
        )
        self.assertEqual(len(rows), 19)
        self.assertEqual(sum(bool(row["selected"]) for row in rows), 1)
        selected = max(
            rows,
            key=lambda row: (
                row["inner_f1"], row["inner_recall"],
                -abs(row["threshold"] - 0.5), -row["threshold"],
            ),
        )
        self.assertEqual(threshold, selected["threshold"])

    def test_17_synthetic_structural_lr_is_deterministic(self) -> None:
        structural: dict[str, dict[str, str]] = {}
        labels = {"a": 0, "b": 0, "c": 1, "d": 1, "e": 0, "f": 1}
        for index, key in enumerate(labels):
            row = {name: str((index + 1) * (feature_index + 1)) for feature_index, name in enumerate(stage.FEATURE_NAMES)}
            structural[key] = row
        candidate = stage.candidate_configs(self.config)[0]
        outputs = []
        for _ in range(2):
            warnings: list[dict[str, object]] = []
            audit = stage.FitAudit()
            outputs.append(
                stage.fit_predict(
                    self.config, candidate, ["a", "b", "c", "d"], ["e", "f"],
                    labels, structural, stage.FEATURE_NAMES,
                    {"phase": "synthetic"}, warnings, audit,
                )
            )
            self.assertEqual((audit.scaler_fit_count, audit.estimator_fit_count), (1, 1))
        np.testing.assert_array_equal(outputs[0], outputs[1])

    def test_18_macro_standard_deviation_is_ddof_one(self) -> None:
        rows = []
        for heldout, ap, f1 in zip(stage.HELD_OUT_GROUPS, [0.2, 0.4, 0.6, 0.8], [0.1, 0.3, 0.5, 0.7], strict=True):
            row = {
                "target": "success", "variant_id": "S0_full13",
                "held_out_group": heldout, "metric_status": "ok",
            }
            for metric in stage.METRIC_NAMES:
                row[metric] = ap if metric == "pr_auc_average_precision" else f1
            row["ap_lift"] = ap - 0.1
            rows.append(row)
        macro = stage.macro_rows(rows)[0]
        self.assertTrue(
            math.isclose(
                macro["pr_auc_average_precision_macro_std"],
                float(np.std([0.2, 0.4, 0.6, 0.8], ddof=1)),
            )
        )

    def test_19_retained_ap_lift_ratio_rules(self) -> None:
        self.assertEqual(stage.retained_ap_lift_ratio(0.2, 0.4), 0.5)
        self.assertEqual(stage.retained_ap_lift_ratio(-0.1, 0.4), 0.0)
        self.assertIsNone(stage.retained_ap_lift_ratio(0.1, 0.0))

    def test_20_dependency_grades_follow_frozen_rules(self) -> None:
        self.assertEqual(
            stage.dependency_classification(
                self.config, "success", "S1_no_termination", 0.4,
                [-0.10, -0.08, -0.01, 0.01],
            ),
            "strong_dependency",
        )
        self.assertEqual(
            stage.dependency_classification(
                self.config, "looping", "S2_no_repetition", 0.6,
                [-0.02, -0.03, -0.01, 0.01],
            ),
            "moderate_dependency",
        )
        self.assertEqual(
            stage.dependency_classification(
                self.config, "success", "S4_no_error", 0.9,
                [-0.01, 0.02, -0.01, 0.03],
            ),
            "limited_dependency",
        )

    def test_21_single_class_metrics_are_missing_not_imputed(self) -> None:
        predictions = [
            {
                "true_label": 0, "predicted_probability": probability,
                "predicted_label": int(probability >= 0.5),
            }
            for probability in [0.1, 0.6, 0.2]
        ]
        row = stage.metric_row(
            "side_effect", "S0_full13", "assistantbench", predictions,
            "B2_C0p1_cw_none", 0.5, 5, 1,
        )
        self.assertEqual(row["metric_status"], "single_class_negative")
        self.assertIsNone(row["pr_auc_average_precision"])
        self.assertIsNone(row["positive_f1"])
        self.assertEqual(row["false_positive_count"], 1)


class StageA15FormalResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        cls.summary_path = stage.resolve(cls.config["outputs"]["run_summary"])

    def _require_results(self) -> None:
        if not self.summary_path.exists():
            self.skipTest("formal A1.5 outputs do not exist during A1.5a")

    def test_22_independent_formal_recomputation(self) -> None:
        self._require_results()
        result = stage.verify_results(self.config)
        self.assertEqual(result["external_predictions"], 4081)
        self.assertEqual(result["inner_selected_oof"], 12243)

    def test_23_s0_exactly_reproduces_a13_b2(self) -> None:
        self._require_results()
        proof = stage.verify_results(self.config)["s0_positive_control"]
        self.assertTrue(proof["config_exact"])
        self.assertTrue(proof["threshold_exact"])
        self.assertTrue(proof["predicted_labels_exact"])
        self.assertLessEqual(proof["max_probability_absolute_error"], 1e-12)
        self.assertLessEqual(proof["max_metric_absolute_error"], 1e-12)

    def test_24_formal_counts_and_unique_predictions(self) -> None:
        self._require_results()
        summary = json.loads(self.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(
            summary["row_counts"],
            {
                "inner_config_selection": 504,
                "inner_selected_oof_predictions": 12243,
                "threshold_selection": 1596,
                "external_predictions": 4081,
                "domain_metrics": 84,
                "macro_metrics": 21,
                "pooled_metrics": 21,
                "structural_ablation_deltas": 84,
            },
        )

    def test_25_formal_test_access_and_forbidden_experiments_are_zero(self) -> None:
        self._require_results()
        summary = json.loads(self.summary_path.read_text(encoding="utf-8"))
        self.assertEqual(sum(summary["test_access"].values()), 0)
        self.assertEqual(summary["forbidden_experiments_executed"], [])


if __name__ == "__main__":
    unittest.main()
