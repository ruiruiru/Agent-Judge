"""Dependency-light tests for the frozen RISK-0 audit implementation."""

from __future__ import annotations

import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_risk_0_publication_audit.py"
SPEC = importlib.util.spec_from_file_location("risk_0", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class Risk0ImplementationTests(unittest.TestCase):
    def test_frozen_rubric_has_69_subcriteria(self) -> None:
        self.assertEqual(len(MODULE.CRITERIA), 69)
        self.assertEqual(sum(key.startswith("SV") for key in MODULE.CRITERIA), 36)
        self.assertEqual(sum(key.startswith("PC") for key in MODULE.CRITERIA), 33)
        self.assertEqual(sum(key.startswith("PC6.") for key in MODULE.CRITERIA), 6)

    def test_weights_are_exact(self) -> None:
        self.assertEqual(sum(MODULE.DIMENSION_WEIGHTS[f"SV{i}"] for i in range(1, 7)), 100.0)
        self.assertEqual(sum(MODULE.DIMENSION_WEIGHTS[f"PC{i}"] for i in range(1, 6)), 90.0)
        for dimension in MODULE.DIMENSION_WEIGHTS:
            total = sum(weight for current, weight, _ in MODULE.CRITERIA.values() if current == dimension)
            self.assertAlmostEqual(total, 1.0)

    def test_hard_gates_pass_from_preregistration_head(self) -> None:
        gates = MODULE.hard_gates(ROOT, require_clean=False)
        self.assertEqual(gates["preregistration"], MODULE.PREREG_COMMIT)
        self.assertEqual(gates["a3_3_result"], MODULE.A3_3_RESULT)
        self.assertEqual(gates["a3_2_addendum_result"], MODULE.A3_2_ADDENDUM_RESULT)
        self.assertEqual(gates["a1_11_claim_matrix_sha256"], MODULE.A1_11_CLAIM_MATRIX_SHA256)

    def test_inventory_phase_creates_only_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            rows = MODULE.build_inventory(ROOT, output_root, require_clean=False)
            inventory = output_root / "artifacts" / "risk_0_evidence_inventory.csv"
            self.assertTrue(inventory.is_file())
            with inventory.open("r", encoding="utf-8", newline="") as handle:
                parsed = list(csv.DictReader(handle))
            self.assertEqual(len(parsed), len(MODULE.INVENTORY_SPECS))
            self.assertEqual(parsed, rows)
            self.assertFalse((output_root / "artifacts" / "risk_0_primary_scores.csv").exists())
            self.assertFalse((output_root / "artifacts" / "risk_0_adversarial_scores.csv").exists())
            self.assertFalse((output_root / "artifacts" / "risk_0_final_scores.csv").exists())

    def test_mandatory_objection_set_is_exact(self) -> None:
        self.assertEqual(len(MODULE.MANDATORY_OBJECTIONS), 15)
        self.assertIn("novelty too weak", MODULE.MANDATORY_OBJECTIONS)
        self.assertIn("no independent external benchmark", MODULE.MANDATORY_OBJECTIONS)
        self.assertIn("practical relevance", MODULE.MANDATORY_OBJECTIONS)


if __name__ == "__main__":
    unittest.main()
