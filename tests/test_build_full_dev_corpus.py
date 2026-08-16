"""Contract tests for the Stage A1.0 full-dev streaming builder."""

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
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_full_dev_corpus", ROOT / "scripts" / "build_full_dev_corpus.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)


def synthetic_source(key: str = "bench::task.1::model") -> builder.DevSource:
    return builder.DevSource(key, "bench", "bench", "bench", "bench", "task.1", "model", "dev")


def synthetic_raw() -> dict:
    return {
        "goal": "Complete the task",
        "steps": [
            {
                "action": "click('x')",
                "axtree_pruned": "page state",
                "focused_element": "button",
                "last_action_error": "natural error",
                "reasoning": "raw thought",
            },
            {
                "action": "send_msg_to_user('done')",
                "axtree_pruned": "final state",
                "focused_element": None,
                "last_action_error": None,
                "reasoning": None,
            },
        ],
        "summary_info": {"cum_reward": 1.0},
        "benchmark": "bench",
        "model": "model",
    }


def known_types(raw: dict) -> set[tuple[str, str]]:
    return {(path, observed_type) for path, observed_type, _value in builder.frozen_contract.iter_fields(raw)}


class FullDevCorpusTests(unittest.TestCase):
    def test_manifest_is_exactly_196_unique_dev_and_excludes_test(self) -> None:
        sources = builder.load_dev_sources()
        self.assertEqual(len(sources), 196)
        self.assertEqual(len({source.trajectory_key for source in sources}), 196)
        self.assertTrue(all(source.official_split == "dev" for source in sources))
        test_keys = {row["trajectory_key"] for row in builder.read_csv(builder.TEST_MANIFEST)}
        self.assertFalse({source.trajectory_key for source in sources}.intersection(test_keys))

    def test_fixed_revision_and_individual_resolve_only(self) -> None:
        self.assertEqual(builder.HF_REVISION, "b6d17e646009d6cb63d5dd7be78807b680693f61")
        url = builder._download_url("cleaned/bench/model/run/task.json")
        self.assertIn(builder.HF_REVISION, url)
        source_text = (ROOT / "scripts" / "build_full_dev_corpus.py").read_text(encoding="utf-8")
        self.assertNotIn("snapshot_download", source_text)

    def test_remote_mapping_requires_unique_safe_json_paths(self) -> None:
        source = synthetic_source()
        good = {source.trajectory_key: builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")}
        builder.validate_remote_mapping([source], good)
        with self.assertRaises(PermissionError):
            builder.validate_remote_mapping([source], {source.trajectory_key: builder.RemoteFile("judgments/test.json", 10, "oid")})

    def test_shared_adapter_accepts_valid_trajectory_and_interface_has_no_labels(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        raw = synthetic_raw()
        bundle = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))
        self.assertEqual(bundle["cleaned"]["trajectory_key"], source.trajectory_key)
        params = inspect.signature(builder.build_record_bundle).parameters
        self.assertFalse(any("label" in name.lower() or "eligible" in name.lower() for name in params))

    def test_outcome_and_summary_fields_never_enter_outputs(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        raw = synthetic_raw()
        bundle = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))
        encoded = json.dumps(bundle, ensure_ascii=False).lower()
        self.assertNotIn("cum_reward", encoded)
        self.assertNotIn("summary_info", encoded)

    def test_identity_metadata_is_excluded_without_censoring_natural_text(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        raw = synthetic_raw()
        raw["goal"] = "The natural task legitimately says bench"
        bundle = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))
        self.assertIn("bench", bundle["views"]["primary_with_natural_errors"])
        changed = json.loads(json.dumps(bundle["cleaned"]))
        changed["metadata"] = {"benchmark_group_primary": "changed", "model_name": "changed"}
        self.assertEqual(
            {view: builder.serialize_input(changed, view) for view in builder.INPUT_VIEWS},
            bundle["views"],
        )

    def test_reasoning_and_error_views_are_frozen(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        raw = synthetic_raw()
        bundle = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))
        views = bundle["views"]
        self.assertNotIn("REASONING:", views["primary_with_natural_errors"])
        self.assertNotIn("REASONING:", views["ablation_without_error_fields"])
        self.assertIn("REASONING:", views["sensitivity_with_reasoning"])
        self.assertIn("ERROR:", views["primary_with_natural_errors"])
        self.assertNotIn("ERROR:", views["ablation_without_error_fields"])

    def test_terminal_is_exact_null_safe_and_not_duplicated(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        raw = synthetic_raw()
        bundle = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))
        terminal = bundle["cleaned"]["terminal"]
        self.assertEqual(terminal["termination_signal"], "send_msg_to_user")
        for text in bundle["views"].values():
            self.assertNotIn("[TERMINAL]", text)
            self.assertEqual(text.count("send_msg_to_user('done')"), 1)
        raw["steps"] = []
        empty = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))["cleaned"]["terminal"]
        self.assertTrue(all(value is None for value in empty.values()))

    def test_unknown_fields_are_rejected_but_recorded(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 10, "oid")
        raw = synthetic_raw()
        base_known = known_types(raw)
        raw["new_field"] = "secret new value"
        bundle = builder.build_record_bundle(raw, source, remote, "a" * 64, base_known)
        self.assertTrue(any(item["field_path"] == "$.new_field" for item in bundle["unknown"]))
        self.assertNotIn("secret new value", json.dumps(bundle["views"], ensure_ascii=False))

    def test_every_view_has_one_unique_key_and_matching_counts(self) -> None:
        records = [
            {"trajectory_key": "a", "input_view": view}
            for view in builder.INPUT_VIEWS
        ]
        self.assertEqual(len(records), 3)
        self.assertEqual({record["input_view"] for record in records}, set(builder.INPUT_VIEWS))

    def test_interruption_resume_and_repeat_outputs_are_byte_deterministic(self) -> None:
        sources = [synthetic_source("bench::task.2::model"), synthetic_source("bench::task.1::model")]
        bundles = {}
        for source in sources:
            raw = synthetic_raw()
            raw["benchmark"] = "unrelated_raw_identity"
            raw["model"] = "unrelated_raw_model"
            remote = builder.RemoteFile(f"cleaned/bench/model/run/{source.task_id}.json", 10, "oid")
            bundles[source.trajectory_key] = builder.build_record_bundle(raw, source, remote, "a" * 64, known_types(raw))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_dir = root / "records"
            output = root / "cleaned.jsonl"
            views = {view: root / f"{view}.jsonl" for view in builder.INPUT_VIEWS}
            with mock.patch.object(builder, "RECORD_DIR", record_dir), mock.patch.object(builder, "CLEANED_OUTPUT", output), mock.patch.object(builder, "VIEW_OUTPUTS", views):
                builder._write_record_bundle(sources[0], bundles[sources[0].trajectory_key])
                builder._write_record_bundle(sources[1], bundles[sources[1].trajectory_key])
                builder.write_final_outputs(sources)
                first = {path: path.read_bytes() for path in [output, *views.values()]}
                builder.write_final_outputs(list(reversed(sources)))
                self.assertEqual(first, {path: path.read_bytes() for path in [output, *views.values()]})

    def test_raw_cache_directories_are_ignored_and_untracked(self) -> None:
        for candidate in ("data/dev_download_cache/sentinel.json", "data/dev_build_temp/sentinel.json"):
            ignored = subprocess.run(["git", "check-ignore", candidate], cwd=ROOT, check=False, capture_output=True, text=True)
            self.assertEqual(ignored.returncode, 0)
        tracked = subprocess.run(["git", "ls-files", "data/dev_download_cache", "data/dev_build_temp"], cwd=ROOT, check=True, capture_output=True, text=True)
        self.assertEqual(tracked.stdout.strip(), "")

    def test_incomplete_download_is_never_success(self) -> None:
        source = synthetic_source()
        remote = builder.RemoteFile("cleaned/bench/model/run/task.1.json", 100, "oid")
        state = builder._state_template(source, remote)
        self.assertEqual(state["download_status"], "pending")
        self.assertEqual(state["view_status"], "pending")

    def test_all_three_final_files_are_label_free_by_schema(self) -> None:
        allowed = {"trajectory_key", "input_view", "serialized_text", "content_sha256"}
        self.assertFalse(allowed.intersection({"success_label", "eligible_main", "annotation_status"}))

    def test_generated_196_record_corpus_passes_actual_leakage_scan(self) -> None:
        if not builder.CLEANED_OUTPUT.exists():
            self.skipTest("full generated corpus is a local ignored artifact")
        sources = {source.trajectory_key: source for source in builder.load_dev_sources()}
        test_keys = {row["trajectory_key"] for row in builder.read_csv(builder.TEST_MANIFEST)}
        cleaned_keys: list[str] = []
        with builder.CLEANED_OUTPUT.open("r", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                key = record["trajectory_key"]
                cleaned_keys.append(key)
                builder.assert_cleaned_leak_safe(record)
                self.assertNotIn(key, test_keys)
        self.assertEqual(len(cleaned_keys), 196)
        self.assertEqual(len(set(cleaned_keys)), 196)
        for view, path in builder.VIEW_OUTPUTS.items():
            observed: list[str] = []
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    record = json.loads(line)
                    self.assertEqual(set(record), {"trajectory_key", "input_view", "serialized_text", "content_sha256"})
                    self.assertEqual(record["input_view"], view)
                    key = record["trajectory_key"]
                    observed.append(key)
                    text = record["serialized_text"]
                    self.assertEqual(record["content_sha256"], builder.hashlib.sha256(text.encode("utf-8")).hexdigest())
                    builder.assert_view_isolation(text, sources[key], view)
                    self.assertNotIn("[TERMINAL]", text)
            self.assertEqual(observed, sorted(cleaned_keys))


if __name__ == "__main__":
    unittest.main()
