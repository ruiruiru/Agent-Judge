"""Dependency-light guards for the Stage A3.2 closest-work addendum."""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_a3_2_addendum_closest_work.py"


def load_module():
    spec = importlib.util.spec_from_file_location("a3_2_addendum_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load A3.2 addendum verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = load_module()


class StageA32AddendumImplementationTests(unittest.TestCase):
    def test_01_static_forbidden_operation_guard(self) -> None:
        source = VERIFIER.read_text(encoding="utf-8")
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
        self.assertTrue(imported_roots.isdisjoint({"sklearn", "numpy", "torch", "transformers", "scipy"}))
        self.assertTrue(called_attributes.isdisjoint({"fit", "partial_fit", "predict", "predict_proba", "forward", "backward"}))
        self.assertNotIn("average_precision_score", source)
        self.assertNotIn("bootstrap_draw", source)

    def test_02_frozen_preflight(self) -> None:
        package.verify_preflight(require_clean=False)

    def test_03_scientific_counters_are_zero(self) -> None:
        self.assertEqual(len(package.COUNTERS), 13)
        self.assertTrue(all(value == 0 for value in package.COUNTERS.values()))

    def test_04_comparability_contract(self) -> None:
        self.assertEqual(package.BASELINE_COMPARABILITY["DIRECTLY_COMPARABLE"], 0)
        self.assertEqual(package.EXPECTED_COMPARABILITY["DIRECTLY_COMPARABLE"], 0)
        self.assertEqual(package.EXPECTED_COMPARABILITY["PARTIALLY_COMPARABLE"], 3)
        self.assertEqual(package.EXPECTED_COMPARABILITY["CONTEXT_ONLY"], 9)

    def test_05_search_scope_is_exact(self) -> None:
        source = VERIFIER.read_text(encoding="utf-8")
        self.assertIn("webgrapheval", source)
        self.assertIn("webstep", source)
        self.assertIn("similar_srm", source)


if __name__ == "__main__":
    unittest.main()
