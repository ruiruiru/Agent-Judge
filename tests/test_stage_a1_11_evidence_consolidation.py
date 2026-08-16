"""Dependency-free guards for Stage A1.11 evidence consolidation."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_stage_a1_11_evidence_consolidation.py"


def read_csv(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class StageA111Tests(unittest.TestCase):
    def test_static_forbidden_operation_guard(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_roots: set[str] = set()
        called_attributes: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
        self.assertTrue(imported_roots.isdisjoint({"sklearn", "numpy", "torch", "transformers", "joblib"}))
        self.assertTrue(called_attributes.isdisjoint({"fit", "predict", "predict_proba", "forward"}))
        self.assertNotIn("average_precision_score", source)
        self.assertNotIn("f1_score", source)
        self.assertNotIn("bootstrap_draw_metrics.csv\")", source)

    def test_scored_predictions_are_hash_only(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('sha256_path(resolve("artifacts/a1_10_test_scored_predictions.csv"))', source)
        self.assertNotIn('read_csv("artifacts/a1_10_test_scored_predictions.csv")', source)
        self.assertNotIn('read_csv("artifacts/a1_10a_blind_predictions.csv")', source)

    def test_output_rows_and_statuses(self) -> None:
        registry = read_csv("artifacts/a1_11_evidence_registry.csv")
        claims = read_csv("artifacts/a1_11_final_claim_matrix.csv")
        main = read_csv("artifacts/a1_11_table_main_test_results.csv")
        benchmark = read_csv("artifacts/a1_11_table_benchmark_results.csv")
        dev = read_csv("artifacts/a1_11_dev_evidence_summary.csv")
        self.assertEqual(len(registry), 90)
        self.assertEqual(len({row["evidence_id"] for row in registry}), 90)
        self.assertEqual(len(claims), 25)
        self.assertEqual(len(main), 3)
        self.assertEqual(len(benchmark), 12)
        self.assertEqual(len(dev), 21)
        counts: dict[str, int] = {}
        for row in claims:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        self.assertEqual(
            counts,
            {
                "CONFIRMATORY_SUPPORTED": 2,
                "EXPLORATORY_SUPPORTED": 1,
                "DEV_ONLY": 9,
                "DESCRIPTIVE_ONLY": 3,
                "NOT_SUPPORTED": 2,
                "PROHIBITED_OVERCLAIM": 8,
            },
        )

    def test_core_claims_and_exact_frozen_display_values(self) -> None:
        claims = {row["claim_id"]: row for row in read_csv("artifacts/a1_11_final_claim_matrix.csv")}
        self.assertEqual(claims["FC1"]["status"], "CONFIRMATORY_SUPPORTED")
        self.assertEqual(claims["FC2"]["status"], "CONFIRMATORY_SUPPORTED")
        self.assertEqual(claims["FE1"]["status"], "EXPLORATORY_SUPPORTED")
        main = {row["Target"]: row for row in read_csv("artifacts/a1_11_table_main_test_results.csv")}
        expected = {
            "Success": ("0.654836", "0.389567", "0.682099", "0.326806", "0.455411"),
            "Looping": ("0.921769", "0.394829", "0.876987", "0.360965", "0.428598"),
            "Side Effect": ("0.107279", "0.042851", "0.168582", "0.021245", "0.079200"),
        }
        for target, values in expected.items():
            row = main[target]
            actual = tuple(
                f"{float(row[key]):.6f}"
                for key in (
                    "AP",
                    "AP Lift",
                    "F1",
                    "AP-lift 95% CI Lower",
                    "AP-lift 95% CI Upper",
                )
            )
            self.assertEqual(actual, values)

    def test_machine_summary_contract(self) -> None:
        summary = json.loads((ROOT / "artifacts/a1_11_run_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["determination"], "PASS")
        self.assertEqual(summary["provenance_audit"]["coverage_count"], 17)
        self.assertEqual(summary["provenance_audit"]["coverage_expected"], 17)
        self.assertEqual(summary["evidence_registry_rows"], 90)
        for key in (
            "new_experiments_executed",
            "model_fits",
            "inference_runs",
            "embedding_runs",
            "test_metric_recomputations",
            "bootstrap_reruns",
            "threshold_changes",
            "eligibility_changes",
            "model_changes",
        ):
            self.assertEqual(summary[key], 0)
        self.assertEqual(summary["inconsistencies"], [])
        self.assertEqual(summary["next_stage_recommendation"], "READY_FOR_A2_DESIGN_REVIEW")
        self.assertEqual(summary["final_claim_matrix_hash"], sha256("artifacts/a1_11_final_claim_matrix.csv"))
        self.assertEqual(summary["main_table_hash"], sha256("artifacts/a1_11_table_main_test_results.csv"))


if __name__ == "__main__":
    unittest.main()
