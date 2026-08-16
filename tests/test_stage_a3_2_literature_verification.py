"""Dependency-light guards for Stage A3.2 literature verification."""

from __future__ import annotations

import ast
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts" / "verify_a3_2_literature_verification.py"


def load_module():
    spec = importlib.util.spec_from_file_location("a3_2_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load A3.2 verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package = load_module()


class StageA32ImplementationTests(unittest.TestCase):
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

    def test_02_frozen_gate_contract(self) -> None:
        preflight = package.verify_preflight(require_clean=False)
        self.assertEqual(package.sha256_path(package.resolve(package.CLAIM_MATRIX_PATH)), package.CLAIM_MATRIX_SHA256)
        self.assertEqual(preflight["frozen_claims"]["Success"], "CONFIRMATORY_SUPPORTED")
        self.assertEqual(preflight["frozen_claims"]["Looping"], "CONFIRMATORY_SUPPORTED")
        self.assertEqual(preflight["frozen_claims"]["Side Effect"], "EXPLORATORY_SUPPORTED")

    def test_03_scope_and_cap_contract(self) -> None:
        self.assertEqual(package.MANDATORY_WORKS, {"agentrewardbench", "web_shepherd", "agentrm"})
        self.assertEqual(len(package.INCLUDED_ADDITIONAL_WORKS), 5)
        self.assertEqual(package.SEARCH_CUTOFF_DATE, "2026-08-14")
        self.assertTrue(all(value == 0 for value in package.COUNTERS.values()))

    def test_04_valid_taxonomies(self) -> None:
        self.assertEqual(
            package.VALID_COMPARABILITY,
            {"DIRECTLY_COMPARABLE", "PARTIALLY_COMPARABLE", "CONTEXT_ONLY", "NOT_COMPARABLE"},
        )
        self.assertIn("VERIFIED_WITH_LIMITATION", package.VALID_VERIFICATION)
        self.assertNotIn("search_snippet", package.PRIMARY_SOURCE_TYPES)

    def test_05_required_outputs_cover_taskbook(self) -> None:
        self.assertEqual(len(package.REQUIRED_OUTPUTS), 13)
        self.assertIn("docs/a3_2_agentrewardbench_relationship.md", package.REQUIRED_OUTPUTS)
        self.assertIn("paper/references/a3_2_verified_related_work.bib", package.REQUIRED_OUTPUTS)
        self.assertIn("paper/tables/Table_Related_Work_Positioning.tex", package.REQUIRED_OUTPUTS)


if __name__ == "__main__":
    unittest.main()
