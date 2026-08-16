"""Dependency-light tests for the A3.3 manuscript evidence-freeze builder."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_a3_3_manuscript_evidence_freeze.py"
SPEC = importlib.util.spec_from_file_location("build_a3_3", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class StageA33Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.output_root = Path(cls.temp_dir.name)
        cls.summary = MODULE.build(cls.output_root, require_clean=False)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    def test_preflight_and_frozen_boundaries(self) -> None:
        self.assertEqual(MODULE.NOVELTY_POSITIONING, "lightweight fixed-dimensional structural signals for outcome-oriented web-agent trajectory evaluation under a frozen blind-held-out protocol")
        self.assertEqual(self.summary["citations_mapped"], 10)
        self.assertEqual(self.summary["limitations_count"], 14)
        self.assertEqual(self.summary["a3_1_paper_artifact_hash_count"], 33)
        self.assertEqual(self.summary["input_commits"]["implementation"], MODULE.A3_3_IMPLEMENTATION)
        self.assertEqual(self.summary["input_commits"]["fix_commits"], MODULE.a3_3_fix_commits())
        self.assertGreaterEqual(len(self.summary["input_commits"]["fix_commits"]), 2)
        self.assertFalse(self.summary["input_commits"]["amend"])

    def test_numeric_map_exactly_mirrors_display_map(self) -> None:
        source = read_csv(ROOT / "artifacts" / "a3_1_display_value_map.csv")
        numeric = read_csv(self.output_root / "artifacts" / "a3_3_numeric_consistency_map.csv")
        self.assertEqual(len(source), len(numeric))
        self.assertEqual(
            [(row["exact_value"], row["display_value"], row["format_rule"]) for row in source],
            [(row["exact_value"], row["display_value"], row["rounding_rule"]) for row in numeric],
        )
        self.assertTrue(all(row["verified"] == "true" for row in numeric))

    def test_claim_ledger_statuses_and_side_effect(self) -> None:
        rows = read_csv(self.output_root / "artifacts" / "a3_3_claim_ledger.csv")
        evidence = read_csv(self.output_root / "artifacts" / "a3_3_manuscript_evidence_registry.csv")
        evidence_ids = {row["evidence_id"] for row in evidence}
        self.assertEqual({row["status"] for row in rows}, {"APPROVED", "APPROVED_WITH_CAVEAT", "FORBIDDEN"})
        side_effect = [row for row in rows if row["target"] == "Side Effect"]
        self.assertTrue(side_effect)
        self.assertTrue(all("CONFIRMATORY" not in row["claim_strength"] for row in side_effect))
        self.assertEqual(sum(row["claim_id"].startswith("C") and len(row["claim_id"]) == 2 for row in rows), 4)
        for row in rows:
            self.assertTrue({item for item in row["evidence_ids"].split(";") if item} <= evidence_ids)

    def test_results_order_and_boundaries(self) -> None:
        rows = read_csv(self.output_root / "artifacts" / "a3_3_results_evidence_map.csv")
        self.assertEqual([row["result_section"].split()[0] for row in rows], ["R1", "R2", "R3", "R4", "R5", "R6"])
        text = "\n".join(" ".join(row.values()) for row in rows)
        self.assertIn("Side Effect exploratory", text)
        self.assertIn("not independent external validation", text)
        self.assertIn("dev-only", text)

    def test_related_work_uses_only_verified_keys(self) -> None:
        verified = {row["citation_key"] for row in read_csv(ROOT / "artifacts" / "a3_2_citation_registry.csv")}
        evidence = read_csv(self.output_root / "artifacts" / "a3_3_manuscript_evidence_registry.csv")
        used = {key for row in evidence for key in row["citation_keys"].split(";") if key}
        self.assertTrue(used <= verified)
        contract = (self.output_root / "docs" / "a3_3_related_work_integration_contract.md").read_text(encoding="utf-8")
        self.assertIn("DIRECTLY_COMPARABLE = 0", contract)
        self.assertIn("NO_VALID_CROSS_PAPER_HEAD_TO_HEAD", contract)
        self.assertIn("WebGraphEval", contract)
        self.assertIn("WebStep", contract)

    def test_methods_separate_post_freeze_diagnostics(self) -> None:
        methods = read_csv(self.output_root / "artifacts" / "a3_3_methods_source_map.csv")
        self.assertEqual([row["method_id"] for row in methods], [f"M{i}" for i in range(1, 10)])
        m9 = methods[-1]
        self.assertEqual(m9["selection_role"], "post-freeze diagnostics")
        self.assertIn("did not participate", m9["required_caveat"])

    def test_readiness_and_counters(self) -> None:
        rows = read_csv(self.output_root / "artifacts" / "a3_3_manuscript_readiness_checklist.csv")
        self.assertTrue(rows)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))
        for name in MODULE.COUNTER_NAMES:
            self.assertEqual(self.summary[name], 0)
        report_relative = "docs/stage_a3_3_manuscript_evidence_freeze_report.md"
        self.assertIn(report_relative, self.summary["output_hashes"])
        self.assertEqual(
            self.summary["output_hashes"][report_relative],
            MODULE.sha256_path(self.output_root / report_relative),
        )

    def test_skeleton_is_slots_only(self) -> None:
        text = (self.output_root / "paper" / "manuscript" / "MANUSCRIPT_SKELETON.md").read_text(encoding="utf-8")
        for field in ("Purpose", "Claim IDs", "Evidence IDs", "Citation keys", "Table/Figure refs", "Required caveats"):
            self.assertIn(f"- {field}:", text)
        self.assertNotIn("we are the first", text.lower())
        self.assertNotIn("state-of-the-art", text.lower())


if __name__ == "__main__":
    unittest.main()
