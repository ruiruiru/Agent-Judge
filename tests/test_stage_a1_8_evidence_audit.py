"""Integrity, adjudication, and zero-execution tests for Stage A1.8."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import run_stage_a1_8_evidence_audit as stage


class StageA18EvidenceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = stage.load_config()
        cls.checked = stage.preflight(cls.config)
        cls.evidence = stage.build_evidence_registry(cls.config)
        cls.claims = stage.build_claim_matrix(cls.config, cls.evidence)
        cls.threats = stage.build_threats()
        cls.contributions = stage.build_contributions()
        cls.proposal = stage.build_method_proposal()
        cls.decision = {
            "decision": "READY_FOR_FINAL_METHOD_FREEZE",
        }

    def test_01_formal_summaries_and_reports_exist(self) -> None:
        for source in self.config["formal_sources"].values():
            self.assertTrue(stage.resolve(source["summary"]).is_file())
            self.assertTrue(stage.resolve(source["report"]).is_file())

    def test_02_exact_commits_resolve(self) -> None:
        self.assertEqual(set(self.checked["formal_commits"]), {f"A1.{i}" for i in range(2, 8)})

    def test_03_machine_report_core_metrics_consistent(self) -> None:
        audit = self.checked["report_numeric_consistency"]
        self.assertEqual(audit["status"], "PASS")
        self.assertGreater(audit["total"], 100)

    def test_04_a13_b2_equals_a15_s0(self) -> None:
        audit = self.checked["a1_3_b2_equals_a1_5_s0"]
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["row_count"], 583)

    def test_05_a16_point_regression_guard(self) -> None:
        audit = self.checked["a1_6_regression_guards"]
        self.assertEqual(audit["status"], "PASS")
        self.assertLessEqual(
            audit["point_estimate_regression"]["a1_3"]["max_absolute_error"], 1e-12
        )
        self.assertLessEqual(
            audit["point_estimate_regression"]["a1_5"]["max_absolute_error"], 1e-12
        )

    def test_06_a17_frozen_b2_b3_sources_match_a13(self) -> None:
        audit = self.checked["a1_7_frozen_source_guards"]
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["checked_values"], 24)

    def test_07_claim_list_exactly_c1_to_c14(self) -> None:
        self.assertEqual([row["claim_id"] for row in self.claims], stage.CLAIM_IDS)

    def test_08_status_taxonomy_frozen(self) -> None:
        self.assertEqual(self.config["status_taxonomy"], stage.STATUSES)
        self.assertTrue({row["status"] for row in self.claims} <= set(stage.STATUSES))

    def test_09_expected_claim_statuses(self) -> None:
        expected = {
            "C1": "SUPPORTED", "C2": "INSUFFICIENT_EVIDENCE",
            "C3": "INSUFFICIENT_EVIDENCE", "C4": "SUPPORTED_WITH_CONDITIONS",
            "C5": "SUPPORTED", "C6": "INSUFFICIENT_EVIDENCE",
            "C7": "SUPPORTED", "C8": "SUPPORTED",
            "C9": "INSUFFICIENT_EVIDENCE", "C10": "PROHIBITED",
            "C11": "DESCRIPTIVE_ONLY", "C12": "SUPPORTED_WITH_CONDITIONS",
            "C13": "PROHIBITED", "C14": "SUPPORTED_WITH_CONDITIONS",
        }
        self.assertEqual({row["claim_id"]: row["status"] for row in self.claims}, expected)

    def test_10_supported_claims_have_primary_evidence(self) -> None:
        by_id = {row["evidence_id"]: row for row in self.evidence}
        for claim in self.claims:
            if claim["status"] == "SUPPORTED":
                ids = claim["best_supporting_evidence_ids"].split(";")
                self.assertTrue(any(by_id[item]["support_role"] == "primary" for item in ids))

    def test_11_conditional_claims_have_limitations(self) -> None:
        for claim in self.claims:
            if claim["status"] == "SUPPORTED_WITH_CONDITIONS":
                self.assertTrue(claim["counterevidence_or_limitation_ids"])

    def test_12_descriptive_only_not_core_contribution(self) -> None:
        supporting = ";".join(row["supporting_claims"] for row in self.contributions)
        self.assertNotIn("C11", supporting)

    def test_13_prohibited_claims_have_forbidden_wording(self) -> None:
        for claim in self.claims:
            if claim["status"] == "PROHIBITED":
                self.assertTrue(claim["forbidden_wording_cn"])
                self.assertTrue(claim["forbidden_wording_en"])

    def test_14_required_overclaims_are_forbidden(self) -> None:
        blob = " ".join(
            row["forbidden_wording_cn"] + " " + row["forbidden_wording_en"]
            for row in self.claims
        ).lower()
        for phrase in (
            "b2显著优于b3", "dense embedding稳定优于b2/b3",
            "success主要由termination决定", "looping完全由重复特征决定",
            "side effect已robust", "joint task+model ood", "模型越复杂越好", "因果机制",
        ):
            self.assertIn(phrase, blob)

    def test_15_threat_list_contains_t1_to_t10(self) -> None:
        self.assertEqual([row["threat_id"] for row in self.threats], stage.THREAT_IDS)

    def test_16_method_proposal_exact_targets(self) -> None:
        self.assertEqual({row["target"] for row in self.proposal}, {"success", "side_effect", "looping"})
        self.assertEqual(len(self.proposal), 3)

    def test_17_success_and_looping_primary_proposal_b2(self) -> None:
        by_target = {row["target"]: row for row in self.proposal}
        self.assertEqual(by_target["success"]["candidate_method"], "B2 structural LR")
        self.assertEqual(by_target["looping"]["candidate_method"], "B2 structural LR")

    def test_18_side_effect_role_exploratory_only(self) -> None:
        by_target = {row["target"]: row for row in self.proposal}
        self.assertEqual(by_target["side_effect"]["role"], "exploratory-only")

    def test_19_remaining_decision_taxonomy_and_choice(self) -> None:
        self.assertEqual(self.config["remaining_evidence_decisions"], stage.DECISIONS)
        self.assertEqual(
            self.config["default_remaining_evidence_decision"],
            "READY_FOR_FINAL_METHOD_FREEZE",
        )

    def test_20_no_test_source_is_configured(self) -> None:
        configured = {stage.rel(path) for path in stage._all_source_paths(self.config)}
        self.assertNotIn("artifacts/test_manifest.csv", configured)

    def test_21_execution_boundaries_are_all_zero(self) -> None:
        self.assertTrue(all(value == 0 for value in self.config["boundaries"].values()))

    def test_22_script_contains_no_estimator_or_forward_call(self) -> None:
        source = Path(stage.__file__).read_text(encoding="utf-8")
        self.assertNotIn(".fit(", source)
        self.assertNotIn(".forward(", source)
        self.assertNotIn("from sklearn", source)
        self.assertNotIn("import transformers", source)

    def test_23_evidence_roles_are_frozen(self) -> None:
        self.assertTrue({row["support_role"] for row in self.evidence} <= set(stage.SUPPORT_ROLES))

    def test_24_in_memory_output_validation(self) -> None:
        result = stage._validate_outputs(
            self.config,
            self.evidence,
            self.claims,
            self.threats,
            self.contributions,
            self.proposal,
            self.decision,
        )
        self.assertEqual(result["status"], "PASS")

    def test_25_prerun_integrity_when_present(self) -> None:
        path = stage.resolve(self.config["outputs"]["prerun_integrity"])
        if not path.exists():
            self.skipTest("A1.8a prerun integrity not generated yet")
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["claim_ids"], stage.CLAIM_IDS)
        self.assertEqual(payload["test_access_count"], 0)

    def test_26_formal_outputs_when_present(self) -> None:
        path = stage.resolve(self.config["outputs"]["run_summary"])
        if not path.exists():
            self.skipTest("A1.8b formal outputs not generated yet")
        result = stage.verify_formal_outputs(self.config)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["test_access_count"], 0)
        self.assertEqual(result["prohibited_experiment_count"], 0)


if __name__ == "__main__":
    unittest.main()
