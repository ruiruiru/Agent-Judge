"""Dependency-light guards for Stage A3.1 paper artifact rendering."""

from __future__ import annotations

import ast
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "a3_1_rendering.py"
BUILDER = ROOT / "scripts" / "build_a3_1_final_figures_tables.py"
sys.path.insert(0, str(ROOT / "scripts"))


def load_module():
    spec = importlib.util.spec_from_file_location("a3_1_builder", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load A3.1 builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = load_module()


class StageA31ImplementationTests(unittest.TestCase):
    def test_01_static_forbidden_operation_guard(self) -> None:
        imported_roots: set[str] = set()
        called_attributes: set[str] = set()
        combined = ""
        for path in (RENDERER, BUILDER):
            source = path.read_text(encoding="utf-8")
            combined += source
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported_roots.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_roots.add(node.module.split(".")[0])
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    called_attributes.add(node.func.attr)
        self.assertTrue(imported_roots.isdisjoint({"sklearn", "numpy", "torch", "transformers", "joblib", "scipy"}))
        self.assertTrue(called_attributes.isdisjoint({"fit", "partial_fit", "predict", "predict_proba", "forward", "backward"}))
        self.assertNotIn("average_precision_score", combined)
        self.assertNotIn("f1_score", combined)
        self.assertNotIn("bootstrap_draw", combined)

    def test_02_frozen_input_hash_contract(self) -> None:
        for frozen in package.INPUTS:
            self.assertEqual(package.sha256_path(package.resolve_root(frozen.path)), frozen.sha256)
        claims = package.read_csv("artifacts/a1_11_final_claim_matrix.csv")
        self.assertEqual(package.one(claims, claim_id="FC1")["status"], "CONFIRMATORY_SUPPORTED")
        self.assertEqual(package.one(claims, claim_id="FC2")["status"], "CONFIRMATORY_SUPPORTED")
        self.assertEqual(package.one(claims, claim_id="FE1")["status"], "EXPLORATORY_SUPPORTED")

    def test_03_display_rounding_contract(self) -> None:
        self.assertEqual(package.fixed3("0.65483617599915878"), "0.655")
        self.assertEqual(package.fixed3("-0.03169777524847239"), "-0.032")
        self.assertEqual(package.latency_display("0.01343163276775455")[0], "0.01343")
        self.assertEqual(package.latency_display("2370.268617346984")[0], "2.37e3")
        self.assertEqual(package.bytes_display("20512")[0], "20.0 KiB")

    def test_04_full_temp_build_and_verification(self) -> None:
        fake_preflight = {
            "head": "test-only-uncommitted-implementation",
            "implementation_commit": "test-only-uncommitted-implementation",
            "fix_commits": [],
            "verified_hashes": {item.path: item.sha256 for item in package.INPUTS},
            "frozen_claims": {
                "Success": "CONFIRMATORY_SUPPORTED",
                "Looping": "CONFIRMATORY_SUPPORTED",
                "Side Effect": "EXPLORATORY_SUPPORTED",
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            with mock.patch.object(package, "verify_preflight", return_value=fake_preflight):
                summary = package.build_package(output_root, require_clean=False)
            context = package.BuildContext(output_root)
            qa = package.validate_outputs(context, registry_path="artifacts/a3_1_artifact_registry.csv")
            self.assertEqual(summary["stage_determination"], "PASS_WITH_CONDITIONS")
            self.assertEqual(len(summary["figures_generated"]), 5)
            self.assertEqual(len(summary["appendix_figures_generated"]), 2)
            self.assertEqual(len(summary["tables_generated"]), 5)
            self.assertTrue(all(qa.values()))
            self.assertTrue(all(value == 0 for value in summary["scientific_operation_counters"].values()))
            self.assertEqual(summary["next_status"], "WAIT_FOR_HUMAN_A3_1_REVIEW")

    def test_05_caption_and_visual_boundaries(self) -> None:
        self.assertEqual(set(package.CAPTIONS), set(package.TABLE_SOURCES) | set(package.FIGURE_DIMENSIONS))
        combined = "\n".join(package.CAPTIONS.values())
        for term in ("confirmatory", "exploratory", "DEV_ONLY", "DESCRIPTIVE_ONLY", "Environment-specific", "not a prevalence estimate"):
            self.assertIn(term, combined)
        self.assertEqual(package.PNG_DPI, 300)
        self.assertFalse(any(width not in {3.4, 7.0} for width, _ in package.FIGURE_DIMENSIONS.values()))


if __name__ == "__main__":
    unittest.main()
