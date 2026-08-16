"""Guards for Stage A1.9 final method freeze and test preregistration."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from functools import wraps

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_stage_a1_9_final_freeze.py"
SPEC = importlib.util.spec_from_file_location("a1_9", SCRIPT)
assert SPEC and SPEC.loader
A19 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(A19)
CONFIG = A19.load_config(ROOT / "configs" / "stage_a1_9_final_freeze.yaml")
RESULT_EXISTS = (ROOT / CONFIG["outputs"]["run_summary"]).exists()


def result_only(function):
    """Skip result-only checks before A1.9b without requiring pytest."""

    @wraps(function)
    def wrapper(*args, **kwargs):
        if not RESULT_EXISTS:
            return "SKIP"
        return function(*args, **kwargs)

    return wrapper


def test_a1_8_ready_and_claim_hash() -> None:
    ready = A19.verify_a1_8_ready(CONFIG)
    assert ready["decision"] == "READY_FOR_FINAL_METHOD_FREEZE"
    assert ready["stage_determination"] == "PASS_WITH_CONDITIONS"
    assert ready["claim_matrix_sha256"] == CONFIG["inputs"]["a1_8_claim_matrix"]["sha256"]


def test_all_frozen_source_hashes_match() -> None:
    observed = A19.verify_source_hashes(CONFIG)
    assert len(observed) == len(CONFIG["inputs"])


def test_method_registry_is_exactly_three() -> None:
    A19.verify_method_registry(CONFIG)
    assert len(CONFIG["methods"]) == 3


def test_each_final_method() -> None:
    cases = [
        ("success", "FINAL_SUCCESS_B2", "B2_structural_logistic_regression", "confirmatory_primary", True),
        ("looping", "FINAL_LOOPING_B2", "B2_structural_logistic_regression", "confirmatory_primary", True),
        ("side_effect", "FINAL_SIDE_EFFECT_B4", "B4_qwen3_frozen_dense_embedding_logistic_regression", "exploratory_only", False),
    ]
    for target, method_id, family, role, eligible in cases:
        method = CONFIG["methods"][target]
        assert (method["method_id"], method["family"], method["role"], method["confirmatory_eligible"]) == (method_id, family, role, eligible)


def test_prohibited_method_flags_are_false() -> None:
    for flag in ["s6_final_method", "b3_final_method", "fusion", "second_embedding_model", "llm_judge", "new_model_family", "secondary_lobo", "joint_ood"]:
        assert CONFIG["execution"][flag] is False


def test_qwen_dev_forward_and_regeneration_forbidden() -> None:
    assert CONFIG["qwen"]["dev_forward_allowed"] is False
    assert CONFIG["qwen"]["dev_embedding_regeneration_allowed"] is False


def test_classifier_and_selection_protocol() -> None:
    A19.verify_protocol(CONFIG)
    assert CONFIG["classifier"]["max_iter"] == 5000
    assert CONFIG["classifier"]["solver"] == "liblinear"
    assert CONFIG["selection"]["folds"] == 5


def test_six_configs_in_frozen_tie_break_order() -> None:
    for target in ["success", "looping", "side_effect"]:
        rows = A19.candidate_configs(CONFIG, target)
        assert len(rows) == 6
        assert [row["class_weight"] for row in rows] == [None, None, None, "balanced", "balanced", "balanced"]
        assert [row["C"] for row in rows] == [0.1, 1.0, 10.0, 0.1, 1.0, 10.0]


def test_threshold_grid_is_exactly_nineteen() -> None:
    assert CONFIG["selection"]["thresholds"] == [round(index * 0.05, 2) for index in range(1, 20)]


def test_threshold_tie_break_prefers_recall_then_distance_then_smaller() -> None:
    class MinimalConfig(dict):
        pass

    cfg = MinimalConfig(selection={"thresholds": [0.4, 0.6]})
    threshold, rows = A19.select_threshold(cfg, [0, 1], [0.7, 0.8])
    assert threshold == 0.4
    assert len(rows) == 2 and sum(bool(row["selected"]) for row in rows) == 1


def test_full13_feature_contract() -> None:
    assert len(CONFIG["structural_features"]) == 13
    assert CONFIG["structural_features"][-2:] == ["unique_action_ratio", "consecutive_duplicate_action_count"]


def test_eligibility_counts_and_labels() -> None:
    _, index = A19.eligible_index(CONFIG)
    expected = {"success": (192, 58), "side_effect": (195, 12), "looping": (196, 92)}
    for target, (count, positives) in expected.items():
        rows = [row for row in index.values() if row[f"{target}_eligible_main"].lower() == "true" and row[f"{target}_label"] in {"0", "1"}]
        assert len(rows) == count
        assert sum(int(row[f"{target}_label"]) for row in rows) == positives


def test_frozen_folds_cover_each_eligible_dev_once_without_group_split() -> None:
    _, index = A19.eligible_index(CONFIG)
    for target in ["success", "side_effect", "looping"]:
        assignments = A19.fold_assignments(CONFIG, target, index)
        assert len(assignments) == CONFIG["methods"][target]["expected_samples"]
        assert {item["fold"] for item in assignments.values()} == {1, 2, 3, 4, 5}
        seen: dict[str, int] = {}
        for item in assignments.values():
            assert seen.setdefault(item["group_key"], item["fold"]) == item["fold"]


def test_frozen_structural_features_are_finite() -> None:
    features = A19.load_structural(CONFIG)
    assert len(features) == 196
    assert all(value.shape == (13,) and np.isfinite(value).all() for value in features.values())


def test_frozen_embedding_is_196_by_1024_and_normalized() -> None:
    matrix, key_to_row = A19.load_embeddings(CONFIG)
    assert matrix.shape == (196, 1024)
    assert matrix.dtype == np.float32
    assert len(key_to_row) == 196
    assert np.allclose(np.linalg.norm(matrix, axis=1), 1.0, atol=1e-5, rtol=0.0)


def test_b2_uses_scaler_pipeline_and_b4_does_not() -> None:
    b2 = A19.make_model(CONFIG, "success", A19.candidate_configs(CONFIG, "success")[0])
    b4 = A19.make_model(CONFIG, "side_effect", A19.candidate_configs(CONFIG, "side_effect")[0])
    assert list(b2.named_steps) == ["standard_scaler", "classifier"]
    assert b4.__class__.__name__ == "LogisticRegression"


def test_positive_probability_uses_classes_location() -> None:
    class FakeModel:
        classes_ = np.asarray([1, 0])

        @staticmethod
        def predict_proba(matrix: np.ndarray) -> np.ndarray:
            return np.tile(np.asarray([[0.8, 0.2]]), (len(matrix), 1))

    assert A19.positive_probability(FakeModel(), np.zeros((2, 1))).tolist() == [0.8, 0.8]


def test_expected_counts_are_frozen() -> None:
    assert CONFIG["expected_counts"] == {
        "all_config_oof": 3498,
        "selected_config_oof": 583,
        "config_summary": 18,
        "threshold_summary": 57,
        "estimator_fits": 93,
        "final_model_artifacts": 3,
    }


def test_claim_freeze_roles_and_no_upgrade() -> None:
    rows = A19.read_csv(ROOT / CONFIG["outputs"]["claim_freeze"])
    assert len(rows) == 8
    assert {(row["claim_id"], row["role"]) for row in rows[:3]} == {
        ("FC1", "confirmatory_primary"), ("FC2", "confirmatory_primary"), ("FE1", "exploratory_only")
    }
    assert all(row["automatic_upgrade_allowed"] == "false" for row in rows)


def test_test_preregistration_is_blind_first_and_zero_access() -> None:
    payload = json.loads((ROOT / CONFIG["outputs"]["test_preregistration"]).read_text(encoding="utf-8"))
    assert payload["status"] == "FROZEN_NOT_EXECUTED"
    assert payload["a1_9_test_access"] == A19.TEST_ACCESS_ZERO
    assert payload["a1_10a_blind_inference"]["label_access_before_blind_prediction_commit"] == 0
    assert payload["a1_10b_one_time_label_unlock"]["preconditions"][-1] == "git_clean"


def test_test_prior_counts_are_not_treated_as_current_access() -> None:
    payload = json.loads((ROOT / CONFIG["outputs"]["test_preregistration"]).read_text(encoding="utf-8"))
    prior = payload["a1_10a_blind_inference"]["prior_provenance_only"]
    assert prior == {
        "trajectory_count": 1106,
        "prediction_row_count": 3318,
        "must_be_confirmed_from_identifier_only_manifest_in_A1_10a": True,
        "mismatch_action": "STOP",
    }


def test_final_metrics_and_bootstrap_are_frozen() -> None:
    payload = json.loads((ROOT / CONFIG["outputs"]["test_preregistration"]).read_text(encoding="utf-8"))
    assert payload["primary_metrics"]["point"] == ["pooled_average_precision", "pooled_ap_lift", "positive_f1_at_frozen_dev_threshold"]
    bootstrap = payload["bootstrap"]
    assert (bootstrap["n_draws"], bootstrap["seed"], bootstrap["strata"]) == (10000, 2027, "benchmark_group_primary")
    assert bootstrap["label_stratification"] is False and bootstrap["invalid_redraw"] is False


def test_confirmatory_grading_and_side_effect_role_are_frozen() -> None:
    payload = json.loads((ROOT / CONFIG["outputs"]["test_preregistration"]).read_text(encoding="utf-8"))
    assert set(payload["grading"]) >= {"CONFIRMED_HELDOUT_SIGNAL", "DIRECTIONAL_BUT_NOT_CONFIRMED", "NOT_CONFIRMED"}
    assert payload["grading"]["side_effect"] == "EXPLORATORY_TEST_RESULT"
    assert payload["side_effect_confirmatory_upgrade_allowed"] is False


def test_post_unlock_prohibitions_cover_all_method_changes() -> None:
    payload = json.loads((ROOT / CONFIG["outputs"]["test_preregistration"]).read_text(encoding="utf-8"))
    forbidden = set(payload["post_label_unlock_permanent_prohibitions"])
    assert {"threshold_change", "C_change", "class_weight_change", "structural_feature_change", "qwen_revision_change", "chunking_or_pooling_change", "calibration", "fusion", "second_embedding", "llm_judge", "eligibility_change", "primary_metric_change", "success_criterion_change"} <= forbidden


def test_prefit_guard_has_zero_fit_test_and_prohibited_counts() -> None:
    result = A19.prefit_guard(CONFIG)
    assert result["status"] == "PASS"
    assert result["real_dev_fit_count"] == 0
    assert result["test_access"] == A19.TEST_ACCESS_ZERO
    assert result["prohibited_experiments"] == A19.PROHIBITED_ZERO


@result_only
def test_formal_results_independently_verify() -> None:
    result = A19.verify_results(CONFIG)
    assert result["status"] == "PASS"


@result_only
def test_formal_counts_are_exact() -> None:
    result = A19.verify_results(CONFIG)
    assert result["counts"] == CONFIG["expected_counts"]


@result_only
def test_final_model_hash_reload_and_prediction_reproduction() -> None:
    result = A19.verify_results(CONFIG)
    for target in ["success", "looping", "side_effect"]:
        assert result["reload_verification"][target]["status"] == "PASS"
        assert result["reload_verification"][target]["max_absolute_error"] == 0.0


@result_only
def test_formal_run_kept_all_boundary_counters_zero() -> None:
    result = A19.verify_results(CONFIG)
    assert result["test_access"] == A19.TEST_ACCESS_ZERO
    assert result["prohibited_experiments"] == A19.PROHIBITED_ZERO


@result_only
def test_run_summary_stops_before_a1_10() -> None:
    summary = json.loads((ROOT / CONFIG["outputs"]["run_summary"]).read_text(encoding="utf-8"))
    assert summary["a1_10_status"] == "NOT_AUTHORIZED_NOT_EXECUTED"
    assert summary["stop_condition"] == "await_explicit_human_authorization_before_any_test_access"
    assert summary["recommend_human_authorization_a1_10"] is True


def main() -> int:
    """Run this dependency-free targeted test module."""

    tests = [(name, value) for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    passed = 0
    skipped = 0
    for name, function in tests:
        result = function()
        if result == "SKIP":
            skipped += 1
            print(f"SKIP {name}")
        else:
            passed += 1
            print(f"PASS {name}")
    print(json.dumps({"status": "PASS", "passed": passed, "skipped": skipped, "total": len(tests)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
