"""Run Stage A1.10a blind-first official-test inference without labels or fitting.

The four phases are deliberately separated by runtime environment:

* ``--preflight`` and ``--build-inputs`` use the frozen baseline environment;
* ``--extract-embeddings`` uses the frozen semantic CUDA environment;
* ``--predict`` and ``--verify`` use the frozen baseline environment.

No function in this module accepts a label or eligibility source. The official
test annotation file is never configured or opened.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_cleaned_probe as frozen_contract  # noqa: E402
import build_full_dev_corpus as corpus  # noqa: E402
import extract_stage_a1_7_embeddings as semantic  # noqa: E402


def _baseline_module() -> Any:
    """Load the structural-feature module only in the baseline environment."""
    import run_stage_a1_2_baselines as baseline  # noqa: PLC0415

    return baseline


CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_10a_blind_inference.yaml"
IDENTIFIER_FIELDS = [
    "trajectory_key",
    "benchmark_original",
    "benchmark_split_namespace",
    "benchmark_group_primary",
    "benchmark_group_secondary",
    "normalized_task_id",
    "model_name",
    "official_split",
    "annotation_count",
    "repository_path",
    "repository_oid",
    "expected_size_bytes",
    "source_revision",
]
PRIMARY_FIELDS = ["content_sha256", "input_view", "serialized_text", "trajectory_key"]
EMBEDDING_INDEX_FIELDS = [
    "row_index", "trajectory_key", "payload_token_count", "chunk_count",
    "embedding_norm", "content_sha256",
]
TOKEN_FIELDS = [
    "row_index", "trajectory_key", "payload_token_count", "chunk_count",
    "min_chunk_payload_tokens", "max_chunk_payload_tokens",
]
PREDICTION_FIELDS = [
    "trajectory_key", "benchmark_original", "benchmark_group_primary",
    "normalized_task_id", "model_name", "target", "method_id", "role",
    "model_sha256", "probability", "frozen_threshold", "predicted_label",
    "row_key", "inference_status",
]
FORBIDDEN_PREDICTION_TERMS = {
    "true_label", "label", "eligibility", "eligible", "annotation", "reward",
    "judge", "metric", "score", "outcome",
}
STATE_FIELDS = [
    "trajectory_key", "repository_path", "repository_oid", "source_revision",
    "expected_size_bytes", "actual_size_bytes", "source_sha256",
    "download_status", "parse_status", "clean_status", "primary_status",
    "attempt_count", "error_type", "error_message", "processed_at",
    "network_download_bytes", "raw_retained", "record_sha256",
]


class IntegrityError(RuntimeError):
    """Raised whenever a frozen A1.10a guard fails."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else REPO_ROOT / path


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def write_json(path: Path, value: Any) -> None:
    atomic_bytes(
        path,
        (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("stage") != "A1.10a":
        raise IntegrityError("A1.10a config stage changed")
    if config["execution"].get("label_source_configured"):
        raise IntegrityError("label source must not be configured")
    if config["execution"].get("eligibility_source_configured"):
        raise IntegrityError("eligibility source must not be configured")
    if config["execution"].get("metric_computation_configured"):
        raise IntegrityError("metric computation must not be configured")
    if config["execution"].get("estimator_fit_allowed"):
        raise IntegrityError("estimator fitting must remain disabled")
    if any(int(value) != 0 for value in config["prohibited_experiments"].values()):
        raise IntegrityError("all prohibited experiment counters must be zero")
    return config


def git(*arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=REPO_ROOT, text=True, encoding="utf-8"
    ).strip()


def ensure_ancestor(commit: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPO_ROOT, check=False, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise IntegrityError(f"required commit is not an ancestor: {commit}")


def verify_sha(path_text: str, expected: str) -> str:
    path = resolve(path_text)
    actual = sha256_path(path)
    if actual != expected:
        raise IntegrityError(f"SHA-256 mismatch for {path_text}: {actual} != {expected}")
    return actual


def environment_record() -> dict[str, Any]:
    return {
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpu_count": os.cpu_count(),
    }


def run_context_path(config: Mapping[str, Any]) -> Path:
    return resolve(config["outputs"]["local_state"]).parent / "run_context.json"


def load_run_context(config: Mapping[str, Any]) -> dict[str, Any]:
    path = run_context_path(config)
    if not path.is_file():
        raise IntegrityError("A1.10a preflight run context is missing")
    return json.loads(path.read_text(encoding="utf-8"))


def log_event(config: Mapping[str, Any], message: str) -> None:
    context = load_run_context(config)
    path = resolve(context["run_directory"]) / "stdout.log"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"{utc_now()} {message}\n")


def validate_identifier_rows(rows: Sequence[Mapping[str, str]], expected: int) -> dict[str, Any]:
    if len(rows) != expected:
        raise IntegrityError(f"expected {expected} identifier rows, observed {len(rows)}")
    required = {
        "trajectory_key", "benchmark_original", "benchmark_split_namespace",
        "benchmark_group_primary", "benchmark_group_secondary", "task_id",
        "model_name", "official_split", "annotation_count",
    }
    if not rows or set(rows[0]) != required:
        raise IntegrityError("sealed identifier manifest schema changed")
    forbidden = {
        column for column in rows[0]
        if column != "annotation_count"
        and any(term in column.lower() for term in FORBIDDEN_PREDICTION_TERMS)
    }
    if forbidden:
        raise IntegrityError(f"forbidden identifier columns: {sorted(forbidden)}")
    keys = [row["trajectory_key"] for row in rows]
    if len(keys) != len(set(keys)):
        raise IntegrityError("duplicate test trajectory identifiers")
    if {row["official_split"] for row in rows} != {"test"}:
        raise IntegrityError("identifier universe contains a non-test row")
    mismatches = [
        row["trajectory_key"]
        for row in rows
        if row["trajectory_key"] != "::".join(
            (row["benchmark_original"], row["task_id"], row["model_name"])
        )
    ]
    if mismatches:
        raise IntegrityError(f"trajectory-key reconstruction mismatches: {len(mismatches)}")
    return {
        "rows": len(rows),
        "unique_trajectory_keys": len(set(keys)),
        "duplicate_trajectory_keys": 0,
        "benchmark_original": dict(sorted(Counter(row["benchmark_original"] for row in rows).items())),
        "benchmark_group_primary": dict(sorted(Counter(row["benchmark_group_primary"] for row in rows).items())),
        "benchmark_group_secondary": dict(sorted(Counter(row["benchmark_group_secondary"] for row in rows).items())),
        "task_groups": len({(row["benchmark_original"], row["task_id"]) for row in rows}),
        "normalized_task_ids": len({row["task_id"] for row in rows}),
        "model_name": dict(sorted(Counter(row["model_name"] for row in rows).items())),
    }


def test_sources(rows: Sequence[Mapping[str, str]]) -> list[corpus.DevSource]:
    return sorted(
        [
            corpus.DevSource(
                trajectory_key=row["trajectory_key"],
                benchmark_original=row["benchmark_original"],
                benchmark_split_namespace=row["benchmark_split_namespace"],
                benchmark_group_primary=row["benchmark_group_primary"],
                benchmark_group_secondary=row["benchmark_group_secondary"],
                task_id=row.get("task_id", row.get("normalized_task_id", "")),
                model_name=row["model_name"],
                official_split=row["official_split"],
            )
            for row in rows
        ],
        key=lambda source: source.trajectory_key,
    )


def verify_model_artifacts(config: Mapping[str, Any]) -> dict[str, Any]:
    import joblib

    result: dict[str, Any] = {}
    for target, spec in config["models"].items():
        verify_sha(spec["path"], spec["sha256"])
        model = joblib.load(resolve(spec["path"]))
        classifier = model.steps[-1][1] if hasattr(model, "steps") else model
        shape = list(classifier.coef_.shape)
        if shape != [1, int(spec["input_dimension"])]:
            raise IntegrityError(f"{target} model coefficient shape changed: {shape}")
        if list(classifier.classes_) != [0, 1]:
            raise IntegrityError(f"{target} model classes changed")
        steps = [name for name, _ in model.steps] if hasattr(model, "steps") else []
        if bool(spec["standard_scaler"]) != (steps == ["standard_scaler", "classifier"]):
            raise IntegrityError(f"{target} scaler contract changed")
        result[target] = {"sha256": spec["sha256"], "coef_shape": shape, "steps": steps}
    return result


def preflight(config: dict[str, Any]) -> None:
    """Verify all pre-test guards, map identifiers, and freeze the opening record."""

    status = git("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise IntegrityError(f"pre-test Git worktree is not clean: {status}")
    head = git("rev-parse", "HEAD")
    ensure_ancestor(config["provenance"]["a1_9a_commit"])
    ensure_ancestor(config["provenance"]["a1_9b_commit"])
    ensure_ancestor(config["taskbook"]["docs_commit"])
    hashes: dict[str, str] = {}
    hashes[config["taskbook"]["path"]] = verify_sha(
        config["taskbook"]["path"], config["taskbook"]["sha256"]
    )
    for key in (
        "a1_8_claim_matrix", "a1_9_prerun_integrity", "a1_9_model_manifest",
        "a1_9_claim_freeze", "a1_9_test_preregistration",
    ):
        spec = config["provenance"][key]
        hashes[spec["path"]] = verify_sha(spec["path"], spec["sha256"])
    source_manifest = json.loads(resolve("artifacts/source_manifest.json").read_text(encoding="utf-8"))
    if source_manifest["github_commit"] != config["source"]["github_commit"]:
        raise IntegrityError("GitHub data commit changed")
    if source_manifest["huggingface_revision"] != config["source"]["huggingface_revision"]:
        raise IntegrityError("Hugging Face data revision changed")
    models = verify_model_artifacts(config)
    a1_7_config = semantic.load_config(resolve(config["qwen"]["frozen_a1_7_config"]))
    model_manifest = semantic.verify_model_manifest(a1_7_config)
    if model_manifest["immutable_revision"] != config["qwen"]["immutable_revision"]:
        raise IntegrityError("Qwen immutable revision changed")
    if model_manifest["weight_sha256"] != config["qwen"]["weight_sha256"]:
        raise IntegrityError("Qwen weight hash changed")

    source_path = resolve(config["source"]["identifier_manifest"])
    rows = read_csv(source_path)
    identifier_stats = validate_identifier_rows(rows, int(config["expected"]["trajectories"]))
    sources = test_sources(rows)
    mapping = corpus.map_sources(sources)
    if set(mapping) != {source.trajectory_key for source in sources}:
        raise IntegrityError("raw mapping does not exactly cover the identifier universe")
    if len({remote.path for remote in mapping.values()}) != len(sources):
        raise IntegrityError("raw mapping paths are not unique")
    if any(not corpus.is_safe_repository_path(remote.path) for remote in mapping.values()):
        raise IntegrityError("raw mapping contains an unsafe path")
    output_rows = []
    for source in sources:
        remote = mapping[source.trajectory_key]
        output_rows.append({
            "trajectory_key": source.trajectory_key,
            "benchmark_original": source.benchmark_original,
            "benchmark_split_namespace": source.benchmark_split_namespace,
            "benchmark_group_primary": source.benchmark_group_primary,
            "benchmark_group_secondary": source.benchmark_group_secondary,
            "normalized_task_id": source.task_id,
            "model_name": source.model_name,
            "official_split": source.official_split,
            "annotation_count": next(row["annotation_count"] for row in rows if row["trajectory_key"] == source.trajectory_key),
            "repository_path": remote.path,
            "repository_oid": remote.oid,
            "expected_size_bytes": remote.size,
            "source_revision": config["source"]["huggingface_revision"],
        })
    identifier_output = resolve(config["outputs"]["identifier_manifest"])
    write_csv(identifier_output, output_rows, IDENTIFIER_FIELDS)

    run_id = f"a1_10a_blind_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{head[:8]}"
    run_directory = resolve(f"runs/{run_id}")
    run_directory.mkdir(parents=True, exist_ok=False)
    context = {
        "run_id": run_id,
        "run_directory": run_directory.relative_to(REPO_ROOT).as_posix(),
        "formal_start_commit": head,
        "started_at_utc": utc_now(),
    }
    write_json(run_context_path(config), context)
    (run_directory / "command.txt").write_text(
        "\n".join([
            f"{sys.executable} scripts/run_stage_a1_10a_blind_inference.py --preflight",
            ".venv-baselines\\Scripts\\python.exe scripts/run_stage_a1_10a_blind_inference.py --build-inputs",
            ".venv-semantic\\Scripts\\python.exe scripts/run_stage_a1_10a_blind_inference.py --extract-embeddings",
            ".venv-baselines\\Scripts\\python.exe scripts/run_stage_a1_10a_blind_inference.py --predict",
            ".venv-baselines\\Scripts\\python.exe scripts/run_stage_a1_10a_blind_inference.py --verify",
        ]) + "\n",
        encoding="utf-8", newline="\n",
    )
    (run_directory / "stdout.log").write_text(
        f"{utc_now()} pre-test guards PASS; identifier-only opening complete\n",
        encoding="utf-8", newline="\n",
    )
    write_json(run_directory / "preflight_environment.json", environment_record())
    integrity = {
        "stage": "A1.10a_pretest",
        "status": "PASS",
        "authorization": config["authorization"],
        "generated_at_utc": utc_now(),
        "git": {"head": head, "status_porcelain": "", "clean": True},
        "commits": {
            "a1_9a": config["provenance"]["a1_9a_commit"],
            "a1_9b": config["provenance"]["a1_9b_commit"],
            "taskbook_docs": config["taskbook"]["docs_commit"],
        },
        "verified_hashes": hashes,
        "source_revisions": {
            "github_commit": config["source"]["github_commit"],
            "huggingface_revision": config["source"]["huggingface_revision"],
        },
        "models": models,
        "qwen": {
            "repo_id": config["qwen"]["repo_id"],
            "immutable_revision": model_manifest["immutable_revision"],
            "weight_sha256": model_manifest["weight_sha256"],
            "snapshot_file_count": len(model_manifest["files"]),
        },
        "identifier_source_sha256": sha256_path(source_path),
        "identifier_output_sha256": sha256_path(identifier_output),
        "identifier_stats": identifier_stats,
        "raw_mapping": {
            "mapped": len(mapping),
            "unique_paths": len({remote.path for remote in mapping.values()}),
            "missing": 0,
            "declared_bytes": sum(remote.size for remote in mapping.values()),
        },
        "test_access": {
            "manifest": len(rows), "content": 0, "labels": 0, "eligibility": 0,
            "features": 0, "embeddings": 0, "predictions": 0, "metrics": 0,
        },
        "prohibited_experiments": config["prohibited_experiments"],
        "run": context,
    }
    write_json(resolve(config["outputs"]["prerun_integrity"]), integrity)
    print(json.dumps({
        "status": "PASS", "phase": "preflight", "trajectories": len(rows),
        "mapping": len(mapping), "declared_bytes": integrity["raw_mapping"]["declared_bytes"],
        "run_id": run_id,
    }, sort_keys=True), flush=True)


def state_template(row: Mapping[str, str]) -> dict[str, Any]:
    return {
        "trajectory_key": row["trajectory_key"],
        "repository_path": row["repository_path"],
        "repository_oid": row["repository_oid"],
        "source_revision": row["source_revision"],
        "expected_size_bytes": row["expected_size_bytes"],
        "actual_size_bytes": "",
        "source_sha256": "",
        "download_status": "pending",
        "parse_status": "pending",
        "clean_status": "pending",
        "primary_status": "pending",
        "attempt_count": 0,
        "error_type": "",
        "error_message": "",
        "processed_at": "",
        "network_download_bytes": 0,
        "raw_retained": "false",
        "record_sha256": "",
    }


def record_path(config: Mapping[str, Any], trajectory_key: str) -> Path:
    name = hashlib.sha256(trajectory_key.encode("utf-8")).hexdigest() + ".json"
    return resolve(config["outputs"]["local_records"]) / name


def cache_path(config: Mapping[str, Any], trajectory_key: str) -> Path:
    name = hashlib.sha256(trajectory_key.encode("utf-8")).hexdigest() + ".json"
    return resolve(config["outputs"]["raw_cache"]) / name


def load_state(config: Mapping[str, Any], rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, Any]]:
    path = resolve(config["outputs"]["local_state"])
    old = {row["trajectory_key"]: row for row in read_csv(path)} if path.is_file() else {}
    state: dict[str, dict[str, Any]] = {}
    for identifier in rows:
        current = state_template(identifier)
        previous = old.get(identifier["trajectory_key"])
        if previous and previous["repository_path"] == identifier["repository_path"]:
            current.update(previous)
        state[identifier["trajectory_key"]] = current
    return state


def save_state(config: Mapping[str, Any], state: Mapping[str, Mapping[str, Any]]) -> None:
    write_csv(
        resolve(config["outputs"]["local_state"]),
        (state[key] for key in sorted(state)),
        STATE_FIELDS,
    )


def verified_record(config: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any] | None:
    path = record_path(config, str(row["trajectory_key"]))
    expected = str(row.get("record_sha256") or "")
    if not path.is_file() or not expected or sha256_path(path) != expected:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("cleaned", {}).get("trajectory_key") != row["trajectory_key"]:
        return None
    if value.get("input_view") != "primary_with_natural_errors":
        return None
    return value


def download_test_json(
    config: Mapping[str, Any], source: corpus.DevSource, remote: corpus.RemoteFile,
    row: dict[str, Any],
) -> Path:
    if source.official_split != "test":
        raise PermissionError("A1.10a downloader accepts only official test sources")
    if not corpus.is_safe_repository_path(remote.path):
        raise PermissionError("A1.10a raw path is outside fixed cleaned JSON scope")
    path = cache_path(config, source.trajectory_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size == remote.size:
        row["actual_size_bytes"] = remote.size
        row["source_sha256"] = sha256_path(path)
        row["download_status"] = "reused_verified_cache"
        return path
    if path.exists():
        path.unlink()
    temporary = path.with_name(path.name + ".part")
    if temporary.exists():
        temporary.unlink()
    request = urllib.request.Request(
        corpus._download_url(remote.path), headers={"User-Agent": "Agent-Judge-A1.10a/1.0"}
    )
    digest = hashlib.sha256()
    size = 0
    with corpus.open_with_retries(request, timeout=240) as response, temporary.open("wb") as handle:
        response_revision = response.headers.get("X-Repo-Commit")
        if response_revision and response_revision != config["source"]["huggingface_revision"]:
            raise IntegrityError(f"response revision mismatch: {response_revision}")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > remote.size:
                raise IntegrityError("download exceeded fixed-revision declared size")
            digest.update(chunk)
            handle.write(chunk)
    if size != remote.size:
        if temporary.exists():
            temporary.unlink()
        raise IntegrityError(f"download size mismatch: {size} != {remote.size}")
    os.replace(temporary, path)
    if sha256_path(path) != digest.hexdigest():
        raise IntegrityError("downloaded raw SHA-256 mismatch after write")
    row["actual_size_bytes"] = size
    row["source_sha256"] = digest.hexdigest()
    row["download_status"] = "downloaded_verified"
    row["network_download_bytes"] = int(row.get("network_download_bytes") or 0) + size
    return path


def build_primary_bundle(
    raw: Mapping[str, Any], source: corpus.DevSource, remote: corpus.RemoteFile,
    source_sha256: str, known_types: set[tuple[str, str]],
) -> dict[str, Any]:
    """Reuse the frozen adapter with split-only guard aliasing and no sensitivity view."""

    if source.official_split != "test":
        raise PermissionError("A1.10a primary builder accepts only official test sources")
    if not isinstance(raw, Mapping) or not isinstance(raw.get("steps"), list):
        raise IntegrityError("raw test trajectory root/steps schema is invalid")
    if any(not isinstance(step, Mapping) for step in raw["steps"]):
        raise IntegrityError("every raw test trajectory step must be an object")
    contract_source = frozen_contract.ProbeSource(
        trajectory_key=source.trajectory_key,
        benchmark_original=source.benchmark_original,
        benchmark_group_primary=source.benchmark_group_primary,
        benchmark_group_secondary=source.benchmark_group_secondary,
        model_name=source.model_name,
        task_id=source.task_id,
        official_split="dev",
        source_revision=source_sha256 and corpus.HF_REVISION,
        source_path=remote.path,
        local_relative_path="",
        source_size_bytes=remote.size,
        source_sha256=source_sha256,
    )
    cleaned, unknown = frozen_contract.build_cleaned_trajectory(raw, contract_source, known_types)
    cleaned["metadata"]["official_split"] = "test"
    corpus.assert_cleaned_leak_safe(cleaned)
    primary = corpus.serialize_input(cleaned, "primary_with_natural_errors")
    corpus.assert_view_isolation(primary, source, "primary_with_natural_errors")
    if "REASONING:" in primary or "[TERMINAL]" in primary:
        raise IntegrityError("primary serialization changed from the frozen A1.0/A1.7 contract")
    redacted_unknown = []
    for item in unknown:
        redacted_unknown.append({
            "field_path": item["field_path"],
            "observed_type": item["observed_type"],
            "example_value_redacted": corpus._redacted_example(item.get("example_value_redacted")),
        })
    return {
        "cleaned": cleaned,
        "input_view": "primary_with_natural_errors",
        "serialized_text": primary,
        "content_sha256": hashlib.sha256(primary.encode("utf-8")).hexdigest(),
        "unknown": redacted_unknown,
    }


def write_record(config: Mapping[str, Any], source: corpus.DevSource, bundle: Mapping[str, Any]) -> str:
    data = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    atomic_bytes(record_path(config, source.trajectory_key), data)
    return hashlib.sha256(data).hexdigest()


def aggregate_inputs(
    config: Mapping[str, Any], identifiers: Sequence[Mapping[str, str]],
    state: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    cleaned_chunks: list[bytes] = []
    primary_chunks: list[bytes] = []
    feature_rows: list[dict[str, Any]] = []
    drift: dict[tuple[str, str], dict[str, Any]] = {}
    for identifier in identifiers:
        row = state[identifier["trajectory_key"]]
        bundle = verified_record(config, row)
        if bundle is None:
            raise IntegrityError(f"missing verified compact record: {identifier['trajectory_key']}")
        cleaned = bundle["cleaned"]
        cleaned_chunks.append(
            (json.dumps(cleaned, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        )
        primary_record = {
            "content_sha256": bundle["content_sha256"],
            "input_view": "primary_with_natural_errors",
            "serialized_text": bundle["serialized_text"],
            "trajectory_key": identifier["trajectory_key"],
        }
        primary_chunks.append(
            (json.dumps(primary_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        )
        features = _baseline_module().extract_structural_features(cleaned)
        feature_row = {"trajectory_key": identifier["trajectory_key"], **features, "content_sha256": bundle["content_sha256"]}
        feature_rows.append(feature_row)
        for item in bundle.get("unknown", []):
            key = (item["field_path"], item["observed_type"])
            entry = drift.setdefault(key, {
                "field_path": key[0], "observed_type": key[1], "presence_count": 0,
                "trajectory_keys": set(), "benchmarks": set(), "models": set(),
                "example_value_redacted": item["example_value_redacted"],
            })
            entry["presence_count"] += 1
            entry["trajectory_keys"].add(identifier["trajectory_key"])
            entry["benchmarks"].add(identifier["benchmark_original"])
            entry["models"].add(identifier["model_name"])
    atomic_bytes(resolve(config["outputs"]["cleaned_jsonl"]), b"".join(cleaned_chunks))
    atomic_bytes(resolve(config["outputs"]["primary_jsonl"]), b"".join(primary_chunks))
    feature_fields = ["trajectory_key", *config["structural_features"], "content_sha256"]
    if list(feature_rows[0])[1:-1] != list(config["structural_features"]):
        raise IntegrityError("frozen 13-feature order changed")
    write_csv(resolve(config["outputs"]["structural_features"]), feature_rows, feature_fields)
    drift_rows = [
        {
            "field_path": value["field_path"],
            "observed_type": value["observed_type"],
            "presence_count": value["presence_count"],
            "trajectory_count": len(value["trajectory_keys"]),
            "benchmarks": "|".join(sorted(value["benchmarks"])),
            "models": "|".join(sorted(value["models"])),
            "example_value_redacted": value["example_value_redacted"],
            "input_inclusion": "excluded_unknown_field",
        }
        for _key, value in sorted(drift.items())
    ]
    write_csv(
        resolve("artifacts/a1_10a_test_schema_drift.csv"), drift_rows,
        ["field_path", "observed_type", "presence_count", "trajectory_count", "benchmarks", "models", "example_value_redacted", "input_inclusion"],
    )
    return {
        "cleaned_rows": len(cleaned_chunks),
        "primary_rows": len(primary_chunks),
        "feature_rows": len(feature_rows),
        "feature_count": len(config["structural_features"]),
        "schema_drift_groups": len(drift_rows),
        "cleaned_sha256": sha256_path(resolve(config["outputs"]["cleaned_jsonl"])),
        "primary_sha256": sha256_path(resolve(config["outputs"]["primary_jsonl"])),
        "structural_feature_sha256": sha256_path(resolve(config["outputs"]["structural_features"])),
        "schema_drift_sha256": sha256_path(resolve("artifacts/a1_10a_test_schema_drift.csv")),
    }


def build_inputs(config: dict[str, Any]) -> None:
    """Stream fixed-revision test raw JSON into frozen primary inputs/features."""

    preflight_record = json.loads(resolve(config["outputs"]["prerun_integrity"]).read_text(encoding="utf-8"))
    if preflight_record.get("status") != "PASS" or preflight_record["test_access"]["labels"] != 0:
        raise IntegrityError("valid label-free preflight record is required")
    identifiers = read_csv(resolve(config["outputs"]["identifier_manifest"]))
    if len(identifiers) != int(config["expected"]["trajectories"]):
        raise IntegrityError("frozen identifier output count changed")
    sources = test_sources(identifiers)
    source_by_key = {source.trajectory_key: source for source in sources}
    remote_by_key = {
        row["trajectory_key"]: corpus.RemoteFile(
            path=row["repository_path"], size=int(row["expected_size_bytes"]), oid=row["repository_oid"]
        )
        for row in identifiers
    }
    state = load_state(config, identifiers)
    save_state(config, state)
    known_types, _known_paths = corpus._load_known_types()
    failures: list[dict[str, str]] = []
    for index, identifier in enumerate(identifiers, start=1):
        key = identifier["trajectory_key"]
        source = source_by_key[key]
        remote = remote_by_key[key]
        row = state[key]
        if row.get("primary_status") == "success" and verified_record(config, row) is not None:
            if index % 25 == 0 or index == len(identifiers):
                print(json.dumps({"phase": "build_inputs", "resumed": index, "total": len(identifiers)}), flush=True)
            continue
        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1
        row["error_type"] = ""
        row["error_message"] = ""
        raw_path: Path | None = None
        try:
            raw_path = download_test_json(config, source, remote, row)
            row["parse_status"] = "started"
            save_state(config, state)
            with raw_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            row["parse_status"] = "success"
            bundle = build_primary_bundle(raw, source, remote, str(row["source_sha256"]), known_types)
            del raw
            row["clean_status"] = "success"
            row["record_sha256"] = write_record(config, source, bundle)
            row["primary_status"] = "success"
            row["processed_at"] = utc_now()
            row["raw_retained"] = "false"
            if raw_path.exists():
                raw_path.unlink()
            save_state(config, state)
            if index % 10 == 0 or index == len(identifiers):
                message = json.dumps({"phase": "build_inputs", "completed": index, "total": len(identifiers)})
                print(message, flush=True)
                log_event(config, message)
        except Exception as exc:
            row["error_type"] = type(exc).__name__
            row["error_message"] = str(exc).replace("\r", " ").replace("\n", " ")[:500]
            if row["parse_status"] == "started":
                row["parse_status"] = "failed"
            if row["clean_status"] != "success":
                row["clean_status"] = "failed"
            if row["primary_status"] != "success":
                row["primary_status"] = "failed"
            row["processed_at"] = utc_now()
            save_state(config, state)
            failures.append({
                "trajectory_key": key, "repository_path": remote.path,
                "error_type": row["error_type"], "error_message": row["error_message"],
            })
            print(json.dumps({"phase": "build_inputs", "failed": key, "error": row["error_message"]}), flush=True)
    failures.extend([
        {
            "trajectory_key": key, "repository_path": row["repository_path"],
            "error_type": str(row["error_type"]), "error_message": str(row["error_message"]),
        }
        for key, row in sorted(state.items())
        if row.get("primary_status") != "success" and not any(item["trajectory_key"] == key for item in failures)
    ])
    write_csv(
        resolve("artifacts/a1_10a_input_failures.csv"), failures,
        ["trajectory_key", "repository_path", "error_type", "error_message"],
    )
    if failures:
        log_event(config, f"build inputs STOP; failures={len(failures)}")
        raise IntegrityError(f"test raw build has {len(failures)} failures")
    summary = aggregate_inputs(config, identifiers, state)
    network_bytes = sum(int(row.get("network_download_bytes") or 0) for row in state.values())
    summary["network_download_bytes"] = network_bytes
    summary["raw_retained_count"] = sum(cache_path(config, key).exists() for key in state)
    if summary["raw_retained_count"] != 0:
        raise IntegrityError("downloaded raw test payload remains in local cache")
    write_json(resolve("artifacts/a1_10a_input_build_summary.json"), summary)
    log_event(config, f"build inputs PASS {json.dumps(summary, sort_keys=True)}")
    print(json.dumps({"status": "PASS", "phase": "build_inputs", **summary}, sort_keys=True), flush=True)


def read_primary_records(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with resolve(config["outputs"]["primary_jsonl"]).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            if list(row) != PRIMARY_FIELDS:
                raise IntegrityError(f"primary test schema/order changed at line {line_number}")
            if row["input_view"] != "primary_with_natural_errors":
                raise IntegrityError("non-primary test view reached B4")
            if hashlib.sha256(row["serialized_text"].encode("utf-8")).hexdigest() != row["content_sha256"]:
                raise IntegrityError("primary serialized content hash mismatch")
            rows.append(row)
    expected = int(config["expected"]["trajectories"])
    if len(rows) != expected or len({row["trajectory_key"] for row in rows}) != expected:
        raise IntegrityError("primary test coverage is incomplete")
    return rows


def vector_cache_path(config: Mapping[str, Any], trajectory_key: str) -> Path:
    name = hashlib.sha256(trajectory_key.encode("utf-8")).hexdigest() + ".npy"
    return resolve(config["outputs"]["local_embeddings"]) / name


def write_numpy(path: Path, array: Any) -> None:
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, array, allow_pickle=False)
    os.replace(temporary, path)


def extract_embeddings(config: dict[str, Any]) -> None:
    """Run one frozen A1.7-contract Qwen forward per test trajectory."""

    import numpy as np
    import torch

    required_env = {
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "A1_7_LOCAL_FILES_ONLY": "true",
        "A1_7_NETWORK": "0",
    }
    mismatches = {key: os.environ.get(key) for key, value in required_env.items() if os.environ.get(key) != value}
    if mismatches:
        raise IntegrityError(f"offline deterministic semantic environment mismatch: {mismatches}")
    records = read_primary_records(config)
    identifiers = read_csv(resolve(config["outputs"]["identifier_manifest"]))
    if [row["trajectory_key"] for row in identifiers] != [row["trajectory_key"] for row in records]:
        raise IntegrityError("identifier and primary input order differ")
    a1_7_config = semantic.load_config(resolve(config["qwen"]["frozen_a1_7_config"]))
    semantic.verify_model_manifest(a1_7_config)
    deterministic_setup = semantic.configure_determinism(int(config["random_state"]))
    tokenizer = semantic.load_tokenizer(a1_7_config)
    model, device = semantic.load_model(a1_7_config)
    vectors = []
    index_rows = []
    token_rows = []
    fresh = 0
    resumed = 0
    started = time.perf_counter()
    for index, record in enumerate(records):
        payload = tokenizer.encode(record["serialized_text"], add_special_tokens=False)
        chunks = semantic.payload_chunks(payload, int(config["qwen"]["payload_tokens_per_chunk"]))
        sizes = [len(chunk) for chunk in chunks]
        cached = vector_cache_path(config, record["trajectory_key"])
        if cached.is_file():
            vector = np.load(cached, allow_pickle=False)
            resumed += 1
        else:
            vector = semantic.embed_payload(model, payload, tokenizer.eos_token_id, device)
            write_numpy(cached, vector)
            fresh += 1
        if vector.shape != (1024,) or vector.dtype != np.float32 or not np.isfinite(vector).all():
            raise IntegrityError("cached/generated test embedding failed shape/dtype/finite guard")
        norm = float(np.linalg.norm(vector))
        if not math.isclose(norm, 1.0, abs_tol=1e-5, rel_tol=0.0):
            raise IntegrityError("test embedding norm differs from frozen contract")
        vectors.append(vector)
        token_rows.append({
            "row_index": index, "trajectory_key": record["trajectory_key"],
            "payload_token_count": len(payload), "chunk_count": len(chunks),
            "min_chunk_payload_tokens": min(sizes), "max_chunk_payload_tokens": max(sizes),
        })
        index_rows.append({
            "row_index": index, "trajectory_key": record["trajectory_key"],
            "payload_token_count": len(payload), "chunk_count": len(chunks),
            "embedding_norm": norm, "content_sha256": record["content_sha256"],
        })
        if (index + 1) % 10 == 0 or index + 1 == len(records):
            message = json.dumps({"phase": "embedding", "completed": index + 1, "total": len(records), "fresh": fresh, "resumed": resumed})
            print(message, flush=True)
            log_event(config, message)
    matrix = np.stack(vectors).astype(np.float32, copy=False)
    expected_shape = (int(config["expected"]["trajectories"]), int(config["expected"]["embedding_dimension"]))
    if matrix.shape != expected_shape or not np.isfinite(matrix).all():
        raise IntegrityError(f"test embedding matrix shape/finite failure: {matrix.shape}")
    if not np.allclose(np.linalg.norm(matrix, axis=1), 1.0, atol=1e-5, rtol=0.0):
        raise IntegrityError("test embedding matrix norm guard failed")
    write_numpy(resolve(config["outputs"]["embedding"]), matrix)
    write_csv(resolve(config["outputs"]["embedding_index"]), index_rows, EMBEDDING_INDEX_FIELDS)
    write_csv(resolve(config["outputs"]["tokenization_audit"]), token_rows, TOKEN_FIELDS)
    summary = {
        "stage": "A1.10a_embedding_extraction",
        "status": "PASS",
        "completed_at_utc": utc_now(),
        "elapsed_seconds": time.perf_counter() - started,
        "shape": list(matrix.shape), "dtype": str(matrix.dtype),
        "finite": True,
        "norm_min": float(np.min(np.linalg.norm(matrix, axis=1))),
        "norm_max": float(np.max(np.linalg.norm(matrix, axis=1))),
        "embedding_sha256": sha256_path(resolve(config["outputs"]["embedding"])),
        "embedding_index_sha256": sha256_path(resolve(config["outputs"]["embedding_index"])),
        "tokenization_audit_sha256": sha256_path(resolve(config["outputs"]["tokenization_audit"])),
        "payload_tokens": sum(row["payload_token_count"] for row in token_rows),
        "chunks": sum(row["chunk_count"] for row in token_rows),
        "maximum_chunk_payload_tokens": max(row["max_chunk_payload_tokens"] for row in token_rows),
        "fresh_forwards": fresh, "resumed_vectors": resumed,
        "total_unique_test_forwards": len(records),
        "deterministic_setup": deterministic_setup,
        "model": {
            "repo_id": config["qwen"]["repo_id"],
            "immutable_revision": config["qwen"]["immutable_revision"],
            "weight_sha256": config["qwen"]["weight_sha256"],
        },
        "network_access": 0, "local_files_only": True,
        "labels_access": 0, "eligibility_access": 0, "metrics_access": 0,
        "dev_embedding_regeneration": 0,
    }
    write_json(resolve("artifacts/a1_10a_embedding_extraction_summary.json"), summary)
    del model
    torch.cuda.empty_cache()
    log_event(config, f"embedding PASS {json.dumps(summary, sort_keys=True)}")
    print(json.dumps({"status": "PASS", "phase": "embedding", **summary}, sort_keys=True), flush=True)


def positive_probability(model: Any, features: Any) -> Any:
    import numpy as np

    classes = list(model.classes_) if hasattr(model, "classes_") else list(model.steps[-1][1].classes_)
    if classes != [0, 1]:
        raise IntegrityError(f"model classes changed: {classes}")
    probabilities = np.asarray(model.predict_proba(features), dtype=np.float64)
    if probabilities.shape != (len(features), 2):
        raise IntegrityError("predict_proba returned an unexpected shape")
    result = probabilities[:, 1]
    if not np.isfinite(result).all() or np.any(result < 0) or np.any(result > 1):
        raise IntegrityError("blind probabilities are missing, non-finite, or out of range")
    return result


def load_feature_matrix(config: Mapping[str, Any]) -> tuple[list[str], Any]:
    import numpy as np

    rows = read_csv(resolve(config["outputs"]["structural_features"]))
    expected_fields = ["trajectory_key", *config["structural_features"], "content_sha256"]
    if not rows or list(rows[0]) != expected_fields:
        raise IntegrityError("structural feature schema/order changed")
    matrix = np.asarray(
        [[float(row[name]) for name in config["structural_features"]] for row in rows],
        dtype=np.float64,
    )
    if matrix.shape != (int(config["expected"]["trajectories"]), 13) or not np.isfinite(matrix).all():
        raise IntegrityError("structural feature matrix failed shape/finite guard")
    return [row["trajectory_key"] for row in rows], matrix


def deterministic_row_key(trajectory_key: str, target: str, method_id: str) -> str:
    return hashlib.sha256(f"{trajectory_key}\x1f{target}\x1f{method_id}".encode("utf-8")).hexdigest()


def prediction_rows(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    import joblib
    import numpy as np

    identifiers = read_csv(resolve(config["outputs"]["identifier_manifest"]))
    metadata = {row["trajectory_key"]: row for row in identifiers}
    feature_keys, feature_matrix = load_feature_matrix(config)
    embedding_index = read_csv(resolve(config["outputs"]["embedding_index"]))
    embedding_keys = [row["trajectory_key"] for row in embedding_index]
    embedding = np.load(resolve(config["outputs"]["embedding"]), allow_pickle=False)
    expected_keys = [row["trajectory_key"] for row in identifiers]
    if feature_keys != expected_keys or embedding_keys != expected_keys:
        raise IntegrityError("identifier/features/embedding key order differs")
    if embedding.shape != (len(expected_keys), 1024) or embedding.dtype != np.float32:
        raise IntegrityError("embedding shape/dtype changed before inference")
    by_target: dict[str, Any] = {}
    for target, spec in config["models"].items():
        verify_sha(spec["path"], spec["sha256"])
        model = joblib.load(resolve(spec["path"]))
        values = feature_matrix if spec["input"] == "structural_features" else embedding
        by_target[target] = positive_probability(model, values)
    rows: list[dict[str, Any]] = []
    for index, trajectory_key in enumerate(expected_keys):
        item = metadata[trajectory_key]
        for target in ("success", "looping", "side_effect"):
            spec = config["models"][target]
            probability = float(by_target[target][index])
            threshold = float(spec["threshold"])
            rows.append({
                "trajectory_key": trajectory_key,
                "benchmark_original": item["benchmark_original"],
                "benchmark_group_primary": item["benchmark_group_primary"],
                "normalized_task_id": item["normalized_task_id"],
                "model_name": item["model_name"],
                "target": target,
                "method_id": spec["method_id"],
                "role": spec["role"],
                "model_sha256": spec["sha256"],
                "probability": probability,
                "frozen_threshold": threshold,
                "predicted_label": int(probability >= threshold),
                "row_key": deterministic_row_key(trajectory_key, target, spec["method_id"]),
                "inference_status": "success",
            })
    return rows


def validate_predictions(config: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    import numpy as np

    expected = int(config["expected"]["prediction_rows"])
    if len(rows) != expected:
        raise IntegrityError(f"expected {expected} blind prediction rows, observed {len(rows)}")
    if not rows or list(rows[0]) != PREDICTION_FIELDS:
        raise IntegrityError("blind prediction schema/order changed")
    bad_columns = [
        column for column in rows[0]
        if column != "predicted_label"
        and any(term == column.lower() or term in column.lower() for term in FORBIDDEN_PREDICTION_TERMS)
    ]
    if bad_columns:
        raise IntegrityError(f"blind artifact contains forbidden columns: {bad_columns}")
    row_keys = [str(row["row_key"]) for row in rows]
    if len(row_keys) != len(set(row_keys)):
        raise IntegrityError("duplicate blind row_key")
    pairs = [(str(row["trajectory_key"]), str(row["target"])) for row in rows]
    if len(pairs) != len(set(pairs)):
        raise IntegrityError("duplicate trajectory-by-target prediction")
    probabilities = np.asarray([float(row["probability"]) for row in rows], dtype=np.float64)
    if not np.isfinite(probabilities).all() or np.any(probabilities < 0) or np.any(probabilities > 1):
        raise IntegrityError("blind probabilities failed finite/range guard")
    target_counts = Counter(str(row["target"]) for row in rows)
    expected_per_target = int(config["expected"]["trajectories"])
    if target_counts != Counter({"success": expected_per_target, "looping": expected_per_target, "side_effect": expected_per_target}):
        raise IntegrityError(f"target row counts changed: {target_counts}")
    for row in rows:
        spec = config["models"][str(row["target"])]
        threshold = float(row["frozen_threshold"])
        probability = float(row["probability"])
        if threshold != float(spec["threshold"]):
            raise IntegrityError("frozen threshold changed")
        if int(row["predicted_label"]) != int(probability >= threshold):
            raise IntegrityError("predicted label differs from mechanical frozen threshold")
        if row["method_id"] != spec["method_id"] or row["model_sha256"] != spec["sha256"]:
            raise IntegrityError("method/model provenance changed")
    return {
        "rows": len(rows), "unique_row_keys": len(set(row_keys)),
        "unique_trajectory_target_pairs": len(set(pairs)),
        "target_counts": dict(sorted(target_counts.items())),
        "probability_finite": True, "probability_range": [float(probabilities.min()), float(probabilities.max())],
        "duplicate_row_keys": 0, "duplicate_trajectory_target_pairs": 0,
    }


def report_text(summary: Mapping[str, Any]) -> str:
    counts = summary["coverage"]
    hashes = summary["output_hashes"]
    return "\n".join([
        "# Stage A1.10a blind official-test inference report",
        "",
        "## Stage determination",
        "",
        f"`{summary['stage_determination']}`",
        "",
        "This is blind inference only. No test labels, eligibility, or metrics were accessed.",
        "",
        "## Provenance",
        "",
        f"- Formal start commit: `{summary['formal_start_commit']}`",
        f"- A1.9a: `{summary['provenance']['a1_9a']}`",
        f"- A1.9b: `{summary['provenance']['a1_9b']}`",
        f"- A1.10a result commit: `recorded_by_enclosing_result_commit`",
        f"- A1.8 claim matrix SHA-256: `{summary['provenance']['a1_8_claim_matrix_sha256']}`",
        f"- GitHub data commit: `{summary['source']['github_commit']}`",
        f"- Hugging Face revision: `{summary['source']['huggingface_revision']}`",
        f"- Qwen revision: `{summary['qwen']['immutable_revision']}`",
        f"- Qwen weight SHA-256: `{summary['qwen']['weight_sha256']}`",
        "",
        "## Coverage and frozen representations",
        "",
        f"- Test trajectories: {counts['trajectories']}",
        f"- Task groups: {counts['task_groups']}",
        f"- Benchmarks: {json.dumps(counts['benchmark_group_primary'], sort_keys=True)}",
        f"- Models: {json.dumps(counts['model_name'], sort_keys=True)}",
        f"- Duplicate identifiers: {counts['duplicate_identifiers']}",
        f"- Missing raw mappings: {counts['missing_raw_mappings']}",
        f"- B2 feature rows/schema: {counts['structural_feature_rows']} / 13",
        f"- B4 embedding rows/dim: {counts['embedding_rows']} / 1024",
        f"- Blind prediction rows: {counts['prediction_rows']}",
        "",
        "## Frozen methods",
        "",
        f"- Success: threshold 0.55; model `{summary['models']['success']}`",
        f"- Looping: threshold 0.55; model `{summary['models']['looping']}`",
        f"- Side Effect: threshold 0.40; exploratory-only; model `{summary['models']['side_effect']}`",
        "- Estimator fits: 0",
        "",
        "## Frozen artifact hashes",
        "",
        f"- Identifier manifest: `{hashes['identifier_manifest']}`",
        f"- Structural features: `{hashes['structural_features']}`",
        f"- Test embedding: `{hashes['embedding']}`",
        f"- Blind predictions: `{hashes['blind_predictions']}`",
        f"- Blind prediction manifest: `{hashes['blind_prediction_manifest']}`",
        "",
        "## Access and prohibited-operation guards",
        "",
        f"- Test access: `{json.dumps(summary['test_access'], sort_keys=True)}`",
        f"- Prohibited experiments: `{json.dumps(summary['prohibited_experiments'], sort_keys=True)}`",
        f"- Warnings: {summary['warnings']['count']}",
        f"- Independent verification: `{summary['independent_verification']['status']}`",
        "",
        "## Stop boundary",
        "",
        "`READY_FOR_TEST_LABEL_UNLOCK_REVIEW`",
        "",
        "A1.10b was not authorized or executed. Stop and await human review.",
        "",
    ])


def predict(config: dict[str, Any]) -> None:
    rows = prediction_rows(config)
    validation = validate_predictions(config, rows)
    prediction_path = resolve(config["outputs"]["blind_predictions"])
    write_csv(prediction_path, rows, PREDICTION_FIELDS)
    identifiers = read_csv(resolve(config["outputs"]["identifier_manifest"]))
    feature_rows = read_csv(resolve(config["outputs"]["structural_features"]))
    embedding_index = read_csv(resolve(config["outputs"]["embedding_index"]))
    model_hashes = {target: spec["sha256"] for target, spec in config["models"].items()}
    manifest = {
        "stage": "A1.10a", "status": "FROZEN_BLIND_NOT_SCORED",
        "generated_at_utc": utc_now(),
        "blind_prediction_path": config["outputs"]["blind_predictions"],
        "blind_prediction_sha256": sha256_path(prediction_path),
        "identifier_manifest_sha256": sha256_path(resolve(config["outputs"]["identifier_manifest"])),
        "structural_features_sha256": sha256_path(resolve(config["outputs"]["structural_features"])),
        "embedding_sha256": sha256_path(resolve(config["outputs"]["embedding"])),
        "embedding_index_sha256": sha256_path(resolve(config["outputs"]["embedding_index"])),
        "models": model_hashes,
        "thresholds": {target: float(spec["threshold"]) for target, spec in config["models"].items()},
        "counts": validation,
        "schema": PREDICTION_FIELDS,
        "forbidden_columns_present": [],
        "test_access": config["test_access_final"],
        "prohibited_experiments": config["prohibited_experiments"],
        "labels_present": False, "eligibility_present": False, "metrics_present": False,
    }
    manifest_path = resolve(config["outputs"]["blind_prediction_manifest"])
    write_json(manifest_path, manifest)
    preflight_record = json.loads(resolve(config["outputs"]["prerun_integrity"]).read_text(encoding="utf-8"))
    input_summary = json.loads(resolve("artifacts/a1_10a_input_build_summary.json").read_text(encoding="utf-8"))
    embedding_summary = json.loads(resolve("artifacts/a1_10a_embedding_extraction_summary.json").read_text(encoding="utf-8"))
    context = load_run_context(config)
    summary = {
        "stage": "A1.10a",
        "stage_determination": "PASS",
        "status": "READY_FOR_TEST_LABEL_UNLOCK_REVIEW",
        "started_at_utc": context["started_at_utc"],
        "completed_at_utc": utc_now(),
        "run_id": context["run_id"],
        "run_directory": context["run_directory"],
        "formal_start_commit": context["formal_start_commit"],
        "result_commit": "recorded_by_enclosing_result_commit",
        "fix_commits": [], "amended_a1_9": False,
        "provenance": {
            "a1_9a": config["provenance"]["a1_9a_commit"],
            "a1_9b": config["provenance"]["a1_9b_commit"],
            "a1_8_claim_matrix_sha256": config["provenance"]["a1_8_claim_matrix"]["sha256"],
            "taskbook_sha256": config["taskbook"]["sha256"],
        },
        "source": {
            "github_commit": config["source"]["github_commit"],
            "huggingface_revision": config["source"]["huggingface_revision"],
        },
        "qwen": {
            "repo_id": config["qwen"]["repo_id"],
            "immutable_revision": config["qwen"]["immutable_revision"],
            "weight_sha256": config["qwen"]["weight_sha256"],
        },
        "models": model_hashes,
        "thresholds": {target: float(spec["threshold"]) for target, spec in config["models"].items()},
        "coverage": {
            "trajectories": len(identifiers),
            "task_groups": preflight_record["identifier_stats"]["task_groups"],
            "benchmark_group_primary": preflight_record["identifier_stats"]["benchmark_group_primary"],
            "model_name": preflight_record["identifier_stats"]["model_name"],
            "duplicate_identifiers": 0, "missing_raw_mappings": 0,
            "structural_feature_rows": len(feature_rows),
            "structural_feature_count": len(config["structural_features"]),
            "embedding_rows": len(embedding_index),
            "embedding_dimension": int(config["expected"]["embedding_dimension"]),
            "prediction_rows": len(rows),
        },
        "input_build": input_summary,
        "embedding_extraction": embedding_summary,
        "prediction_integrity": validation,
        "estimator_fits": 0,
        "test_access": config["test_access_final"],
        "prohibited_experiments": config["prohibited_experiments"],
        "warnings": {"count": int(input_summary["schema_drift_groups"]), "kind": "excluded_schema_drift_groups"},
        "output_hashes": {
            "identifier_manifest": sha256_path(resolve(config["outputs"]["identifier_manifest"])),
            "structural_features": sha256_path(resolve(config["outputs"]["structural_features"])),
            "embedding": sha256_path(resolve(config["outputs"]["embedding"])),
            "embedding_index": sha256_path(resolve(config["outputs"]["embedding_index"])),
            "tokenization_audit": sha256_path(resolve(config["outputs"]["tokenization_audit"])),
            "blind_predictions": sha256_path(prediction_path),
            "blind_prediction_manifest": sha256_path(manifest_path),
        },
        "independent_verification": {"status": "PENDING"},
        "a1_10b": "NOT_AUTHORIZED_NOT_EXECUTED",
        "stop_condition": "await_explicit_AUTHORIZE_A1_10b_TEST_LABEL_UNLOCK",
    }
    write_json(resolve(config["outputs"]["run_summary"]), summary)
    atomic_bytes(resolve(config["outputs"]["report"]), report_text(summary).encode("utf-8"))
    log_event(config, f"blind prediction PASS sha256={summary['output_hashes']['blind_predictions']}")
    print(json.dumps({"status": "PASS", "phase": "predict", "rows": len(rows), "blind_sha256": summary["output_hashes"]["blind_predictions"]}, sort_keys=True), flush=True)


def training_call_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"fit", "partial_fit", "fit_transform"}:
                count += 1
    return count


def verify(config: dict[str, Any]) -> None:
    import numpy as np

    summary_path = resolve(config["outputs"]["run_summary"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    recorded_rows = read_csv(resolve(config["outputs"]["blind_predictions"]))
    validate_predictions(config, recorded_rows)
    recomputed = prediction_rows(config)
    if len(recorded_rows) != len(recomputed):
        raise IntegrityError("independent prediction row count differs")
    max_error = 0.0
    for recorded, current in zip(recorded_rows, recomputed, strict=True):
        for field in PREDICTION_FIELDS:
            if field == "probability":
                max_error = max(max_error, abs(float(recorded[field]) - float(current[field])))
            elif field == "frozen_threshold":
                if float(recorded[field]) != float(current[field]):
                    raise IntegrityError("independent threshold differs")
            elif field == "predicted_label":
                if int(recorded[field]) != int(current[field]):
                    raise IntegrityError("independent predicted label differs")
            elif str(recorded[field]) != str(current[field]):
                raise IntegrityError(f"independent prediction field differs: {field}")
    if max_error != 0.0:
        raise IntegrityError(f"independent probability recomputation max error: {max_error}")
    features = read_csv(resolve(config["outputs"]["structural_features"]))
    cleaned: dict[str, dict[str, Any]] = {}
    with resolve(config["outputs"]["cleaned_jsonl"]).open("r", encoding="utf-8") as handle:
        for line in handle:
            value = json.loads(line)
            cleaned[value["trajectory_key"]] = value
    if len(cleaned) != int(config["expected"]["trajectories"]):
        raise IntegrityError("independent cleaned input coverage changed")
    for row in features:
        expected = _baseline_module().extract_structural_features(
            cleaned[row["trajectory_key"]]
        )
        for name in config["structural_features"]:
            if float(row[name]) != float(expected[name]):
                raise IntegrityError(f"independent structural feature differs: {name}")
    embedding = np.load(resolve(config["outputs"]["embedding"]), allow_pickle=False)
    index_rows = read_csv(resolve(config["outputs"]["embedding_index"]))
    norms = np.linalg.norm(embedding, axis=1)
    if embedding.shape != (1106, 1024) or not np.isfinite(embedding).all():
        raise IntegrityError("independent embedding shape/finite guard failed")
    for index, row in enumerate(index_rows):
        if not math.isclose(float(row["embedding_norm"]), float(norms[index]), abs_tol=1e-6, rel_tol=0.0):
            raise IntegrityError("independent embedding norm differs")
    script_path = Path(__file__).resolve()
    calls = training_call_count(script_path)
    if calls != 0:
        raise IntegrityError(f"training-call AST count is not zero: {calls}")
    manifest_path = resolve(config["outputs"]["blind_prediction_manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["blind_prediction_sha256"] != sha256_path(resolve(config["outputs"]["blind_predictions"])):
        raise IntegrityError("blind prediction manifest hash differs")
    if any(int(value) != 0 for value in config["prohibited_experiments"].values()):
        raise IntegrityError("prohibited experiment counter changed")
    if config["test_access_final"]["labels"] or config["test_access_final"]["eligibility"] or config["test_access_final"]["metrics"]:
        raise IntegrityError("forbidden test access counter is nonzero")
    verification = {
        "stage": "A1.10a_independent_verification", "status": "PASS",
        "generated_at_utc": utc_now(), "prediction_rows": len(recorded_rows),
        "probability_max_absolute_error": max_error,
        "structural_rows_recomputed": len(features),
        "embedding_shape": list(embedding.shape),
        "embedding_finite": True,
        "embedding_norm_min": float(norms.min()), "embedding_norm_max": float(norms.max()),
        "estimator_fit_ast_count": calls,
        "labels_access": 0, "eligibility_access": 0, "metrics_access": 0,
        "prohibited_experiments": config["prohibited_experiments"],
        "output_hashes": summary["output_hashes"],
    }
    verification_path = resolve("artifacts/a1_10a_independent_verification.json")
    write_json(verification_path, verification)
    summary["independent_verification"] = {
        "status": "PASS", "path": "artifacts/a1_10a_independent_verification.json",
        "sha256": sha256_path(verification_path),
        "probability_max_absolute_error": 0.0,
        "estimator_fit_ast_count": 0,
    }
    summary["completed_at_utc"] = utc_now()
    write_json(summary_path, summary)
    atomic_bytes(resolve(config["outputs"]["report"]), report_text(summary).encode("utf-8"))
    log_event(config, "independent verification PASS; stop before A1.10b")
    print(json.dumps({"status": "PASS", "phase": "verify", "ready": "READY_FOR_TEST_LABEL_UNLOCK_REVIEW"}, sort_keys=True), flush=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    phase = parser.add_mutually_exclusive_group(required=True)
    phase.add_argument("--preflight", action="store_true")
    phase.add_argument("--build-inputs", action="store_true")
    phase.add_argument("--extract-embeddings", action="store_true")
    phase.add_argument("--predict", action="store_true")
    phase.add_argument("--verify", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    if args.preflight:
        preflight(config)
    elif args.build_inputs:
        build_inputs(config)
    elif args.extract_embeddings:
        extract_embeddings(config)
    elif args.predict:
        predict(config)
    elif args.verify:
        verify(config)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "STOP", "error_type": type(exc).__name__, "error": str(exc)}, ensure_ascii=False), file=sys.stderr, flush=True)
        raise
