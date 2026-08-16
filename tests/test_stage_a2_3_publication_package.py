"""Dependency-free guards for Stage A2.3 deterministic consolidation."""

from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_a2_3_publication_package.py"


def load_module():
    spec = importlib.util.spec_from_file_location("a2_3_package", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load A2.3 builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = load_module()


class StageA23ImplementationTests(unittest.TestCase):
    def test_01_static_forbidden_operation_guard(self) -> None:
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
        self.assertTrue(
            imported_roots.isdisjoint(
                {"sklearn", "numpy", "torch", "transformers", "joblib", "scipy"}
            )
        )
        self.assertTrue(
            called_attributes.isdisjoint(
                {
                    "fit",
                    "partial_fit",
                    "fit_transform",
                    "predict",
                    "predict_proba",
                    "forward",
                    "backward",
                    "transform",
                }
            )
        )
        self.assertNotIn("average_precision_score", source)
        self.assertNotIn("f1_score", source)
        self.assertNotIn("bootstrap_draw", source)

    def test_02_frozen_preflight_contract(self) -> None:
        result = package.verify_preflight(require_clean=False)
        self.assertEqual(result["commits"]["a2_3_prereg"], package.PREREG_COMMIT)
        self.assertEqual(result["commits"]["a2_1_result"], package.A2_1_RESULT_COMMIT)
        self.assertEqual(result["commits"]["a2_2_result"], package.A2_2_RESULT_COMMIT)
        self.assertEqual(
            result["frozen_claims"],
            {
                "FC1": "CONFIRMATORY_SUPPORTED",
                "FC2": "CONFIRMATORY_SUPPORTED",
                "FE1": "EXPLORATORY_SUPPORTED",
            },
        )

    def test_03_required_output_schemas(self) -> None:
        self.assertIn("needs_literature_verification", package.BASELINE_FIELDS)
        self.assertIn("recommended_location", package.EVIDENCE_MAP_FIELDS)
        self.assertIn("claim_status", package.TABLE_1_FIELDS)
        self.assertIn("environment_specific", package.TABLE_2_FIELDS)
        self.assertIn("evidence_status", package.TABLE_4_FIELDS)
        self.assertIn("main_failure_modes", package.TABLE_5_FIELDS)

    def test_04_full_temp_build_and_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            summary = package.build_package(output_root, require_clean=False)
            package.validate_outputs(output_root)
            self.assertEqual(summary["stage_determination"], "PASS_WITH_CONDITIONS")
            self.assertEqual(summary["baseline_count"], 15)
            self.assertEqual(summary["local_baseline_count"], 12)
            self.assertEqual(summary["tier4_count"], 3)
            self.assertEqual(summary["table_rows"]["table_3"], 18)
            self.assertEqual(summary["external_validation_decision"], "DEFER_TO_REVISION")
            self.assertEqual(
                summary["claim_status_counts"],
                {
                    "CONFIRMATORY_SUPPORTED": 2,
                    "DESCRIPTIVE_ONLY": 3,
                    "DEV_ONLY": 9,
                    "EXPLORATORY_SUPPORTED": 1,
                    "NOT_SUPPORTED": 2,
                    "PROHIBITED_OVERCLAIM": 8,
                },
            )
            self.assertTrue(
                all(value == 0 for value in summary["scientific_operation_counters"].values())
            )

    def test_05_rq_and_prohibited_claim_freeze(self) -> None:
        self.assertEqual(len(package.RQ_TEXTS), 6)
        story = package.story_text()
        for rq in package.RQ_TEXTS:
            self.assertIn(rq.split(": ", 1)[1], story)
        for claim in package.PROHIBITED_CLAIMS:
            self.assertIn(claim, story)
        self.assertNotIn("RQ7", story)


if __name__ == "__main__":
    unittest.main()
