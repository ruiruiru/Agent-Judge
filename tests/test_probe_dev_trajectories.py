"""Tests for the bounded Stage A0.3 trajectory probe."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("probe", ROOT / "scripts" / "probe_dev_trajectories.py")
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class ProbeUnitTests(unittest.TestCase):
    def test_split_key_revision_budget_and_leakage_guards(self) -> None:
        rows = [
            {"trajectory_key": "dev-key", "official_split": "dev"},
        ]
        probe.validate_dev_rows(rows)
        with self.assertRaises(ValueError):
            probe.validate_dev_rows([{"trajectory_key": "test-key", "official_split": "test"}])
        with self.assertRaises(PermissionError):
            probe.assert_not_test_key("test-key", {"test-key"})
        self.assertIn(probe.HF_REVISION, probe._tree_url("cleaned/example"))
        self.assertIn(probe.HF_REVISION, probe._download_url("cleaned/example/a.json"))
        self.assertEqual(probe.MAX_DOWNLOAD_BYTES, 200 * 1024 * 1024)
        risk = probe.leakage_class("$.metadata.reward")
        self.assertIsNotNone(risk)
        self.assertEqual(risk[3], "exclude")

    def test_selection_inventory_and_failure_are_deterministic(self) -> None:
        base = {
            "benchmark_original": "bench",
            "benchmark_group_primary": "bench",
            "model_name": "model",
            "official_split": "dev",
            "path_resolved": True,
            "success_eligible_main": "true",
            "side_effect_eligible_main": "true",
            "looping_eligible_main": "true",
            "side_effect_label": "0",
            "looping_label": "0",
        }
        rows = [
            dict(base, trajectory_key="a", task_id="bench.1", expected_repository_path="cleaned/bench/model/run/bench.1.json", expected_size_bytes=10, success_label="0"),
            dict(base, trajectory_key="b", task_id="bench.2", expected_repository_path="cleaned/bench/model/run/bench.2.json", expected_size_bytes=20, success_label="1"),
        ]
        first = probe.select_probe_rows(rows)
        second = probe.select_probe_rows(list(reversed(rows)))
        self.assertEqual(first, second)
        self.assertEqual({row["trajectory_key"] for row in first}, {"a", "b"})
        fields_one = list(probe.iter_fields({"steps": [{"action": "click"}]}))
        fields_two = list(probe.iter_fields({"steps": [{"action": "click"}]}))
        self.assertEqual(fields_one, fields_two)

        missing = dict(rows[0], download_status="failed:HTTPError", download_error="404")
        inventory, leakage, completeness = probe.audit_downloads([missing])
        self.assertEqual(inventory, [])
        self.assertEqual(leakage, [])
        self.assertEqual(completeness[0]["parse_error"], "404")


class ProbeArtifactTests(unittest.TestCase):
    def test_committed_artifacts_obey_stage_boundaries(self) -> None:
        manifest = probe.read_csv(probe.PROBE_MANIFEST)
        self.assertGreater(len(manifest), 0)
        self.assertLessEqual(len(manifest), probe.MAX_PROBES)
        self.assertEqual(len(manifest), len({row["trajectory_key"] for row in manifest}))
        self.assertTrue(all(row["official_split"] == "dev" for row in manifest))
        self.assertTrue(all(row["hf_revision"] == probe.HF_REVISION for row in manifest))
        self.assertLessEqual(sum(int(row["file_size_bytes"]) for row in manifest), probe.MAX_DOWNLOAD_BYTES)
        self.assertTrue(all(Path(row["expected_repository_path"]).suffix == ".json" for row in manifest))
        self.assertTrue(all("screenshots/" not in row["expected_repository_path"] for row in manifest))
        test_keys = {row["trajectory_key"] for row in probe.read_csv(probe.TEST_MANIFEST)}
        self.assertFalse(test_keys.intersection(row["trajectory_key"] for row in manifest))

        ignored = subprocess.run(
            ["git", "check-ignore", "data/raw_probe/sentinel.json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(ignored.returncode, 0)
        self.assertEqual(
            subprocess.run(["git", "ls-files", "data/raw_probe"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
            "",
        )
        summary = json.loads(probe.SUMMARY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(summary["scope"]["test_trajectory_downloads"], 0)
        self.assertEqual(summary["scope"]["screenshots_downloaded"], 0)
        self.assertEqual(summary["scope"]["models_or_baselines_run"], 0)

        inventory, leakage, completeness = probe.audit_downloads([dict(row) for row in manifest])
        with tempfile.TemporaryDirectory() as directory:
            regenerated = Path(directory) / "inventory.csv"
            fields = [
                "field_path", "observed_type", "example_value_redacted", "presence_count",
                "benchmark", "model_name", "possible_semantic_role",
            ]
            probe.write_csv(regenerated, fields, inventory)
            self.assertEqual(regenerated.read_bytes(), probe.FIELD_INVENTORY.read_bytes())
        self.assertEqual(len(completeness), len(manifest))
        self.assertTrue(all(row["json_parseable"] for row in completeness))
        self.assertTrue(all(item["recommended_action"] != "retain" for item in leakage if item["risk_level"] in {"level_1", "level_2"}))


if __name__ == "__main__":
    unittest.main()
