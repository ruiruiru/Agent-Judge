"""Tests for the Stage A0.4 leak-safe compact input contract."""

from __future__ import annotations

import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_cleaned_probe", ROOT / "scripts" / "build_cleaned_probe.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def recursive_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from recursive_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from recursive_keys(item)


class CleanedProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sources = builder.load_sources()
        cls.cleaned = load_jsonl(builder.CLEANED_JSONL)
        cls.serialized = load_jsonl(builder.SERIALIZED_JSONL)

    def test_exact_existing_dev_scope_and_physical_label_isolation(self) -> None:
        self.assertEqual(len(self.sources), 16)
        self.assertEqual(len(self.cleaned), 16)
        self.assertEqual(len({row["trajectory_key"] for row in self.cleaned}), 16)
        self.assertTrue(all(source.official_split == "dev" for source in self.sources))
        params = inspect.signature(builder.build_cleaned_trajectory).parameters
        self.assertFalse(any("label" in name.lower() for name in params))
        forbidden_keys = {
            "cum_reward", "cum_raw_reward", "reward", "label", "judge",
            "annotation", "success_label", "side_effect_label", "looping_label",
            "eligible_main", "final_response",
        }
        for row in self.cleaned + self.serialized:
            keys = {key.lower() for key in recursive_keys(row)}
            self.assertFalse(keys.intersection(forbidden_keys))

    def test_three_views_exclude_identity_paths_images_and_reasoning(self) -> None:
        by_key = {source.trajectory_key: source for source in self.sources}
        for record in self.serialized:
            self.assertEqual(set(record["views"]), set(builder.INPUT_VIEWS))
            source = by_key[record["trajectory_key"]]
            with (ROOT / source.local_relative_path).open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            raw_identities = [
                str(raw.get(name)) for name in ("agent", "benchmark", "experiment", "model")
                if raw.get(name) not in (None, "")
            ]
            for view, text in record["views"].items():
                builder.assert_view_isolation(text, source, view, raw_identities)
                self.assertNotIn("screenshots/", text.lower())
                self.assertNotIn("cum_reward", text.lower())
                self.assertNotIn("cum_raw_reward", text.lower())
            self.assertNotIn("REASONING:", record["views"]["primary_with_natural_errors"])
            self.assertNotIn("REASONING:", record["views"]["ablation_without_error_fields"])
            self.assertNotIn("ERROR:", record["views"]["ablation_without_error_fields"])

    def test_reasoning_errors_terminal_and_workarena_null_focus_are_exact(self) -> None:
        cleaned_by_key = {row["trajectory_key"]: row for row in self.cleaned}
        serialized_by_key = {row["trajectory_key"]: row for row in self.serialized}
        saw_error = False
        saw_workarena_null_focus = False
        for source in self.sources:
            with (ROOT / source.local_relative_path).open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            cleaned = cleaned_by_key[source.trajectory_key]
            raw_steps = raw.get("steps") or []
            raw_actions = [step.get("action").strip() for step in raw_steps if isinstance(step.get("action"), str) and step.get("action").strip()]
            raw_observations = [step.get("axtree_pruned").strip() for step in raw_steps if isinstance(step.get("axtree_pruned"), str) and step.get("axtree_pruned").strip()]
            self.assertEqual(cleaned["terminal"]["last_nonempty_action"], raw_actions[-1] if raw_actions else None)
            self.assertEqual(cleaned["terminal"]["last_nonempty_observation"], raw_observations[-1] if raw_observations else None)
            expected_signal = builder._termination_signal(raw_actions[-1] if raw_actions else None)
            self.assertEqual(cleaned["terminal"]["termination_signal"], expected_signal)
            for raw_step, step in zip(raw_steps, cleaned["steps"]):
                expected_reasoning = raw_step.get("reasoning")
                expected_reasoning = expected_reasoning.strip() if isinstance(expected_reasoning, str) and expected_reasoning.strip() else None
                self.assertEqual(step["reasoning"], expected_reasoning)
                if step["error"]:
                    saw_error = True
                    primary = serialized_by_key[source.trajectory_key]["views"]["primary_with_natural_errors"]
                    ablation = serialized_by_key[source.trajectory_key]["views"]["ablation_without_error_fields"]
                    self.assertIn(step["error"], primary)
                    self.assertNotIn(step["error"], ablation)
                if source.benchmark_group_primary == "workarena" and raw_step.get("focused_element") is None:
                    saw_workarena_null_focus = True
                    self.assertIsNone(step["focused_element"])
        self.assertTrue(saw_error)
        self.assertTrue(saw_workarena_null_focus)

    def test_unknown_fields_are_rejected_and_test_sources_are_blocked(self) -> None:
        source = self.sources[0]
        known = {(row["field_path"], row["observed_type"]) for row in builder.read_csv(builder.FIELD_INVENTORY)}
        with (ROOT / source.local_relative_path).open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        raw["new_unapproved_field"] = "must not enter input"
        cleaned, unknown = builder.build_cleaned_trajectory(raw, source, known)
        self.assertTrue(cleaned["quality_flags"]["unknown_fields_present"])
        self.assertTrue(any(item["field_path"] == "$.new_unapproved_field" for item in unknown))
        for view in builder.INPUT_VIEWS:
            self.assertNotIn("must not enter input", builder.serialize_input(cleaned, view))
        test_source = replace(source, trajectory_key="sealed-test", official_split="test")
        with self.assertRaises(PermissionError):
            builder.build_cleaned_trajectory(raw, test_source, known)

    def test_outputs_are_byte_deterministic_and_raw_is_ignored_unchanged(self) -> None:
        paths = [builder.FIELD_POLICY, builder.CLEANED_JSONL, builder.SERIALIZED_JSONL, builder.SUMMARY_PATH, builder.REPORT_PATH]
        before = {path: path.read_bytes() for path in paths}
        hashes_before = {source.local_relative_path: builder.sha256_file(ROOT / source.local_relative_path) for source in self.sources}
        self.assertEqual(builder.run(), 0)
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        self.assertEqual(hashes_before, {source.local_relative_path: builder.sha256_file(ROOT / source.local_relative_path) for source in self.sources})
        ignored = subprocess.run(["git", "check-ignore", "data/raw_probe/sentinel.json"], cwd=ROOT, check=False, capture_output=True, text=True)
        self.assertEqual(ignored.returncode, 0)
        tracked = subprocess.run(["git", "ls-files", "data/raw_probe"], cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(tracked.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
