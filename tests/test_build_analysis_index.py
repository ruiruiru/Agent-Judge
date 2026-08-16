"""Tests for the deterministic Stage A0.2 analysis index."""

from __future__ import annotations

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts/build_analysis_index.py"
SPEC = importlib.util.spec_from_file_location("build_analysis_index", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot import {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnalysisIndexTest(unittest.TestCase):
    """Verify Stage A0.2 invariants without network access."""

    def test_outputs_are_deterministic_and_test_manifest_is_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)
            first_summary = MODULE.build_analysis_index(REPO_ROOT, first)
            second_summary = MODULE.build_analysis_index(REPO_ROOT, second)

            for relative_path in MODULE.OUTPUT_PATHS:
                self.assertEqual(
                    (first / relative_path).read_bytes(),
                    (second / relative_path).read_bytes(),
                    relative_path,
                )

            self.assertEqual(first_summary, second_summary)
            self.assertEqual(first_summary["stage_decision"], "PASS")
            self.assertEqual(
                first_summary["trajectory_counts"]["annotation_rows_before_collapse"], 1408
            )
            self.assertEqual(first_summary["trajectory_counts"]["after_collapse"], 1302)
            self.assertEqual(first_summary["trajectory_counts"]["duplicate_groups"], 106)
            self.assertEqual(
                first_summary["annotation_status_counts"]["success"],
                {
                    "single_annotation": 1196,
                    "duplicate_agreement": 93,
                    "duplicate_disagreement": 12,
                    "contains_unsure": 1,
                },
            )
            self.assertEqual(
                first_summary["benchmark_groups"]["primary"],
                ["assistantbench", "visualwebarena", "webarena", "workarena"],
            )
            self.assertEqual(
                first_summary["benchmark_groups"]["secondary"],
                [
                    "assistantbench",
                    "visualwebarena",
                    "webarena",
                    "workarena_l1",
                    "workarena_l2",
                ],
            )
            expected_valid = {"success": 1289, "side_effect": 1297, "looping": 1291}
            for target, valid_count in expected_valid.items():
                counts = first_summary["overall_label_counts"][target]
                self.assertEqual(counts["valid_count"], valid_count)
                self.assertEqual(counts["valid_count"] + counts["unavailable_count"], 1302)

            with (first / "artifacts/dev_analysis_index.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                dev_rows = list(csv.DictReader(handle))
            with (first / "artifacts/test_manifest.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                test_reader = csv.DictReader(handle)
                test_fields = test_reader.fieldnames or []
                test_rows = list(test_reader)

            self.assertEqual(len(dev_rows), first_summary["trajectory_counts"]["dev"])
            self.assertEqual(len(test_rows), first_summary["trajectory_counts"]["test"])
            self.assertEqual(len(dev_rows) + len(test_rows), 1302)
            self.assertEqual(len({row["trajectory_key"] for row in dev_rows}), len(dev_rows))
            self.assertEqual(len({row["trajectory_key"] for row in test_rows}), len(test_rows))
            self.assertTrue(all(row["official_split"] == "test" for row in test_rows))
            self.assertFalse(any("label" in field for field in test_fields))
            self.assertFalse(any("status" in field for field in test_fields))
            self.assertFalse(any("values" in field for field in test_fields))
            self.assertFalse(any("eligible" in field for field in test_fields))
            self.assertFalse(any("primary_label" in field for field in test_fields))

            allowed_statuses = {"single_annotation", "duplicate_agreement"}
            for row in dev_rows:
                for target in ["success", "side_effect", "looping"]:
                    eligible = row[f"{target}_eligible_main"] == "true"
                    label = row[f"{target}_label"]
                    status = row[f"{target}_status"]
                    self.assertEqual(eligible, status in allowed_statuses)
                    if eligible:
                        self.assertIn(label, {"0", "1"})
                    else:
                        self.assertEqual(label, "")

    def test_summary_and_audit_cover_every_unique_trajectory(self) -> None:
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            summary = MODULE.build_analysis_index(REPO_ROOT, output)
            with (output / "artifacts/duplicate_annotation_audit.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                audit_rows = list(csv.DictReader(handle))
            persisted = json.loads(
                (output / "artifacts/analysis_index_summary.json").read_text(encoding="utf-8")
            )

            self.assertEqual(len(audit_rows), 1302)
            self.assertEqual(len({row["trajectory_key"] for row in audit_rows}), 1302)
            for row in audit_rows:
                for target in ["success", "side_effect", "looping"]:
                    eligible = row[f"{target}_eligible_main"] == "true"
                    label = row[f"{target}_label"]
                    status = row[f"{target}_status"]
                    if status in {"duplicate_disagreement", "contains_unsure"}:
                        self.assertFalse(eligible)
                        self.assertEqual(label, "")
                    if eligible:
                        self.assertIn(label, {"0", "1"})
                    else:
                        self.assertEqual(label, "")
            self.assertEqual(persisted, summary)
            self.assertEqual(summary["workarena"]["task_counts"]["workarena_l1"], 18)
            self.assertEqual(summary["workarena"]["task_counts"]["workarena_l2"], 100)
            self.assertEqual(summary["workarena"]["overlapping_task_ids"], [])
            self.assertTrue(summary["benchmark_groups"]["all_trajectories_mapped"])


if __name__ == "__main__":
    unittest.main()
