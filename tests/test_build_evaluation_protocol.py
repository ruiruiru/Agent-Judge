"""Tests for the Stage A1.1 frozen grouped evaluation protocol."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_evaluation_protocol", ROOT / "scripts" / "build_evaluation_protocol.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)

VERIFY_SPEC = importlib.util.spec_from_file_location(
    "verify_evaluation_protocol", ROOT / "scripts" / "verify_evaluation_protocol.py"
)
assert VERIFY_SPEC and VERIFY_SPEC.loader
verifier = importlib.util.module_from_spec(VERIFY_SPEC)
sys.modules[VERIFY_SPEC.name] = verifier
VERIFY_SPEC.loader.exec_module(verifier)


class EvaluationProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.samples, cls.sealing = builder.load_samples()
        cls.summary = json.loads(builder.SUMMARY_OUTPUT.read_text(encoding="utf-8"))

    def test_target_eligibility_unique_dev_and_test_sealing(self) -> None:
        index = {row["trajectory_key"]: row for row in builder.read_csv(builder.DEV_INDEX)}
        test_keys = {row["trajectory_key"] for row in builder.read_csv(builder.TEST_MANIFEST)}
        for target, samples in self.samples.items():
            self.assertEqual(len(samples), len({sample.trajectory_key for sample in samples}))
            self.assertTrue(all(sample.official_split == "dev" for sample in samples))
            self.assertFalse({sample.trajectory_key for sample in samples}.intersection(test_keys))
            for sample in samples:
                row = index[sample.trajectory_key]
                self.assertEqual(row[f"{target}_eligible_main"], "true")
                self.assertIn(row[f"{target}_label"], {"0", "1"})
                self.assertEqual(sample.label, int(row[f"{target}_label"]))
        self.assertEqual(self.sealing["test_target_columns_read"], 0)
        self.assertEqual(self.sealing["test_trajectory_content_accessed"], 0)

    def test_group_key_binds_all_models_to_one_outer_fold(self) -> None:
        for target, path in builder.FOLD_OUTPUTS.items():
            rows = builder.read_csv(path)
            validation_fold_by_group: dict[str, set[str]] = defaultdict(set)
            for row in rows:
                if row["outer_role"] == "outer_validation":
                    validation_fold_by_group[row["group_key"]].add(row["outer_fold"])
            self.assertTrue(all(len(folds) == 1 for folds in validation_fold_by_group.values()), target)

    def test_inner_train_and_validation_are_group_disjoint(self) -> None:
        for path in builder.FOLD_OUTPUTS.values():
            rows = builder.read_csv(path)
            for fold in sorted({row["outer_fold"] for row in rows}):
                fold_rows = [row for row in rows if row["outer_fold"] == fold]
                inner_train = {row["group_key"] for row in fold_rows if row["inner_split"] == "inner_train"}
                inner_validation = {row["group_key"] for row in fold_rows if row["inner_split"] == "inner_validation"}
                self.assertFalse(inner_train.intersection(inner_validation))

    def test_each_trajectory_is_outer_validation_exactly_once(self) -> None:
        for target, path in builder.FOLD_OUTPUTS.items():
            counts: dict[str, int] = defaultdict(int)
            for row in builder.read_csv(path):
                counts[row["trajectory_key"]] += row["outer_role"] == "outer_validation"
            self.assertEqual(set(counts), {sample.trajectory_key for sample in self.samples[target]})
            self.assertTrue(all(count == 1 for count in counts.values()))

    def test_every_outer_and_inner_partition_has_both_classes(self) -> None:
        for path in builder.FOLD_OUTPUTS.values():
            rows = builder.read_csv(path)
            for fold in sorted({row["outer_fold"] for row in rows}):
                fold_rows = [row for row in rows if row["outer_fold"] == fold]
                for field, role in (
                    ("outer_role", "outer_train"),
                    ("outer_role", "outer_validation"),
                    ("inner_split", "inner_train"),
                    ("inner_split", "inner_validation"),
                ):
                    labels = {row["label"] for row in fold_rows if row[field] == role}
                    self.assertEqual(labels, {"0", "1"}, (path, fold, role))

    def test_side_effect_uses_maximum_allowed_feasible_fold_count(self) -> None:
        self.assertEqual(self.summary["cv"]["side_effect"]["outer_folds"], 5)
        rows = builder.read_csv(builder.FOLD_OUTPUTS["side_effect"])
        self.assertEqual({row["outer_fold"] for row in rows}, {"1", "2", "3", "4", "5"})

    def test_frozen_manifests_are_hash_locked_and_builder_is_verification_only(self) -> None:
        paths = [*builder.FOLD_OUTPUTS.values(), builder.LOBO_PRIMARY, builder.LOBO_SECONDARY, builder.LOMO_OUTPUT, builder.SUMMARY_OUTPUT, builder.PROTOCOL_DOC, builder.AUDIT_DOC, builder.PROTOCOL_CONFIG, builder.BASELINE_CONFIG, builder.DRIFT_REVIEW, builder.LITERAL_AUDIT]
        before = {path: path.read_bytes() for path in paths}
        observed = verifier.verify_frozen_manifests()
        self.assertEqual(builder.run(), 0)
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        self.assertEqual(len(observed), 6)
        self.assertEqual(self.summary["protocol"]["split_seed"], 2026)

    def test_actual_splitter_identity_and_manifest_authority_are_explicit(self) -> None:
        config = verifier.load_protocol()
        outer = config["outer_cv"]
        self.assertEqual(outer["algorithm"], "custom_deterministic_grouped_stratification_v1")
        self.assertFalse(outer["scikit_learn_class_called"])
        self.assertFalse(outer["scikit_learn_equivalence_claimed"])
        self.assertFalse(outer["regeneration_allowed"])
        self.assertEqual(outer["sole_authority"], "recorded_manifest_bytes_and_sha256")
        self.assertNotIn("type", outer)

    def test_recorded_outer_fold_sha256_matches_bytes(self) -> None:
        config = verifier.load_protocol()
        recorded = config["outer_cv"]["authoritative_manifests"]
        self.assertEqual(set(recorded), {
            "artifacts/evaluation_folds_success.csv",
            "artifacts/evaluation_folds_side_effect.csv",
            "artifacts/evaluation_folds_looping.csv",
        })
        for relative_path, expected in recorded.items():
            self.assertEqual(verifier.sha256_file(ROOT / relative_path), expected)

    def test_lobo_heldout_groups_never_enter_train(self) -> None:
        for path, group_field in (
            (builder.LOBO_PRIMARY, "benchmark_group_primary"),
            (builder.LOBO_SECONDARY, "benchmark_group_secondary"),
        ):
            for row in builder.read_csv(path):
                if row["role"] == "train":
                    self.assertNotEqual(row[group_field], row["held_out_group"])
                else:
                    self.assertEqual(row[group_field], row["held_out_group"])

    def test_four_primary_and_five_sensitivity_lobo_are_separate(self) -> None:
        primary = builder.read_csv(builder.LOBO_PRIMARY)
        secondary = builder.read_csv(builder.LOBO_SECONDARY)
        self.assertEqual({row["held_out_group"] for row in primary}, set(builder.PRIMARY_GROUPS))
        self.assertEqual({row["held_out_group"] for row in secondary}, set(builder.SECONDARY_GROUPS))
        self.assertTrue(all(row["protocol"] == "primary_four_group" for row in primary))
        self.assertTrue(all(row["protocol"] == "sensitivity_five_group" for row in secondary))
        self.assertIn("workarena", {row["held_out_group"] for row in primary})
        self.assertNotIn("workarena_l1", {row["held_out_group"] for row in primary})
        self.assertTrue({"workarena_l1", "workarena_l2"}.issubset({row["held_out_group"] for row in secondary}))

    def test_identity_metadata_is_not_injected_into_primary_input(self) -> None:
        literal_rows = builder.read_csv(builder.LITERAL_AUDIT)
        self.assertTrue(literal_rows)
        self.assertTrue(all(row["source_is_natural_text"] == "true" for row in literal_rows))
        self.assertTrue(all(row["source_is_injected_metadata"] == "false" for row in literal_rows))
        self.assertFalse(self.summary["benchmark_literal_audit"]["serializer_or_metadata_injection_detected"])

    def test_terminal_terms_are_distinct_and_exact(self) -> None:
        terminal = self.summary["terminal_audit"]
        self.assertEqual(terminal["last_nonempty_action_count"], 196)
        self.assertEqual(terminal["last_nonempty_observation_count"], 196)
        self.assertEqual(terminal["explicit_termination_signal_count"], 71)
        self.assertFalse(terminal["last_nonempty_action_is_success_or_normal_termination"])

    def test_schema_drift_stays_outside_whitelist(self) -> None:
        review = builder.read_csv(builder.DRIFT_REVIEW)
        self.assertEqual(len(review), 4)
        self.assertEqual(sum(int(row["occurrence_count"]) for row in review), 12477)
        self.assertTrue(all(row["final_decision"] == "keep_excluded" for row in review))
        policy = {(row["field_path"], row["observed_type"]): row for row in builder.read_csv(builder.FIELD_POLICY)}
        self.assertTrue(all((row["field_path"], row["observed_type"]) not in policy for row in review))

    def test_primary_and_error_ablation_differ_only_as_frozen(self) -> None:
        view = self.summary["view_audit"]
        self.assertTrue(view["trajectory_keys_identical"])
        self.assertTrue(view["step_order_source_identical"])
        self.assertTrue(view["difference_matches_natural_error_coverage"])
        self.assertEqual(view["natural_error_trajectories"], 86)
        self.assertEqual(view["natural_error_steps"], 307)

    def test_baseline_registry_is_finite_and_contains_no_disallowed_model_family(self) -> None:
        registry = json.loads(builder.BASELINE_CONFIG.read_text(encoding="utf-8"))
        text = json.dumps(registry["baselines"]).lower()
        self.assertFalse(registry["execution_allowed_in_this_stage"])
        for forbidden in ("openai", "anthropic", "embedding+mlp", "transformer", "lora", "neural network"):
            self.assertNotIn(forbidden, text)
        self.assertEqual({item["id"] for item in registry["baselines"]}, {"B0", "B1", "B2", "B3"})

    def test_threshold_selection_never_accesses_outer_validation(self) -> None:
        config = json.loads(builder.PROTOCOL_CONFIG.read_text(encoding="utf-8"))
        self.assertEqual(config["threshold"]["selection_data"], "inner_validation_only")
        self.assertFalse(config["threshold"]["outer_validation_access_allowed"])
        self.assertFalse(config["inner_split"]["outer_validation_access_allowed"])
        self.assertEqual(config["threshold"]["candidates"], list(builder.THRESHOLD_CANDIDATES))

    def test_configuration_then_threshold_selection_and_outer_execution_are_frozen(self) -> None:
        config = verifier.load_protocol()
        selection = config["model_configuration_selection"]
        self.assertEqual(selection["selection_data"], "inner_validation_only")
        self.assertEqual(selection["primary_objective"], "pr_auc")
        self.assertEqual(config["threshold"]["selection_data"], "inner_validation_only")
        self.assertEqual(config["threshold"]["primary_objective"], "positive_f1")
        self.assertEqual(config["execution_sequence"], [
            "fit_each_registered_candidate_on_inner_train",
            "score_each_candidate_on_inner_validation_and_select_by_pr_auc",
            "select_positive_f1_threshold_for_selected_candidate_on_inner_validation",
            "refit_selected_candidate_on_complete_outer_train",
            "evaluate_complete_outer_validation_once_with_frozen_threshold",
        ])

    def test_pooled_oof_and_single_class_lobo_reporting_are_frozen(self) -> None:
        metrics = verifier.load_protocol()["metrics"]
        self.assertIn("pooled_out_of_fold", metrics["fold_aggregation"])
        pooled = metrics["pooled_out_of_fold"]
        self.assertTrue(pooled["predicted_label_uses_fold_specific_frozen_threshold"])
        self.assertTrue(pooled["report_separately_from_fold_mean_and_standard_deviation"])
        single_class = metrics["single_class_lobo_holdout"]
        self.assertEqual(single_class["all_other_predictive_metrics"], "NA")
        self.assertTrue(single_class["na_fill_value_prohibited"])
        self.assertEqual(set(single_class["known_affected_holdouts"]), {
            "primary:side_effect:assistantbench",
            "sensitivity:side_effect:assistantbench",
            "sensitivity:side_effect:workarena_l1",
        })

    def test_test_access_config_is_false(self) -> None:
        config = json.loads(builder.PROTOCOL_CONFIG.read_text(encoding="utf-8"))
        self.assertTrue(all(value is False for value in config["test_access"].values()))

    def test_formal_corpus_is_unchanged_by_protocol_build(self) -> None:
        self.assertTrue(self.summary["formal_inputs_unchanged"])
        self.assertEqual(self.summary["formal_input_sha256_before"], self.summary["formal_input_sha256_after"])


if __name__ == "__main__":
    unittest.main()
