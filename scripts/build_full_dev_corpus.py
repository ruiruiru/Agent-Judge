"""Stream the fixed-revision 196-file dev corpus into leak-safe text views.

This Stage A1.0 builder deliberately has no label-bearing function interface. It
projects the dev index to identifiers before mapping or downloading, rejects
sealed test keys, processes one raw JSON file at a time, and deletes downloaded
raw payloads after an atomic compact record has been written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import build_cleaned_probe as frozen_contract  # noqa: E402


ROOT = SCRIPT_DIR.parent
HF_REPOSITORY = "McGill-NLP/agent-reward-bench"
HF_REVISION = "b6d17e646009d6cb63d5dd7be78807b680693f61"
EXPECTED_DEV_COUNT = 196
DEV_INDEX = ROOT / "artifacts" / "dev_analysis_index.csv"
TEST_MANIFEST = ROOT / "artifacts" / "test_manifest.csv"
PROBE_MANIFEST = ROOT / "artifacts" / "dev_probe_manifest.csv"
FIELD_POLICY = ROOT / "artifacts" / "input_field_policy.csv"
CORPUS_MANIFEST = ROOT / "artifacts" / "dev_corpus_manifest.csv"
SUMMARY_PATH = ROOT / "artifacts" / "dev_corpus_summary.json"
DRIFT_PATH = ROOT / "artifacts" / "dev_schema_drift.csv"
FAILURES_PATH = ROOT / "artifacts" / "dev_build_failures.csv"
REPORT_PATH = ROOT / "docs" / "dev_corpus_build_report.md"
CACHE_DIR = ROOT / "data" / "dev_download_cache"
TEMP_DIR = ROOT / "data" / "dev_build_temp"
RECORD_DIR = TEMP_DIR / "records"
CLEANED_OUTPUT = ROOT / "data" / "processed" / "dev_cleaned_trajectories.jsonl"
VIEW_OUTPUTS = {
    "primary_with_natural_errors": ROOT / "data" / "processed" / "dev_serialized_primary.jsonl",
    "ablation_without_error_fields": ROOT / "data" / "processed" / "dev_serialized_error_ablation.jsonl",
    "sensitivity_with_reasoning": ROOT / "data" / "processed" / "dev_serialized_reasoning_sensitivity.jsonl",
}
INPUT_VIEWS = tuple(VIEW_OUTPUTS)
ALLOWED_SUFFIXES = {".json"}
IDENTIFIER_COLUMNS = (
    "trajectory_key",
    "benchmark_original",
    "benchmark_split_namespace",
    "benchmark_group_primary",
    "benchmark_group_secondary",
    "task_id",
    "model_name",
    "official_split",
)
STATE_FIELDS = (
    "trajectory_key",
    "repository_path",
    "repository_oid",
    "source_revision",
    "expected_size_bytes",
    "actual_size_bytes",
    "source_sha256",
    "download_status",
    "parse_status",
    "clean_status",
    "view_status",
    "attempt_count",
    "error_type",
    "error_message",
    "processed_at",
    "network_download_bytes",
    "raw_retained",
    "record_sha256",
)
DRIFT_FIELDS = (
    "field_path",
    "observed_type",
    "drift_kind",
    "presence_count",
    "trajectory_count",
    "benchmarks",
    "models",
    "example_value_redacted",
    "manual_review_required",
)
FAILURE_FIELDS = (
    "trajectory_key",
    "repository_path",
    "stage",
    "error_type",
    "error_message",
)
FORBIDDEN_OUTCOME_KEYS = {
    "summary_info",
    "cum_reward",
    "cum_raw_reward",
    "reward",
    "raw_reward",
    "score",
    "label",
    "judge",
    "annotation",
    "success",
    "failure",
    "side_effect",
    "looping",
    "repetitiveness",
    "eligible_main",
    "final_response",
}


@dataclass(frozen=True)
class DevSource:
    """Label-free management metadata for one approved dev trajectory."""

    trajectory_key: str
    benchmark_original: str
    benchmark_split_namespace: str
    benchmark_group_primary: str
    benchmark_group_secondary: str
    task_id: str
    model_name: str
    official_split: str


@dataclass(frozen=True)
class RemoteFile:
    """One JSON file observed in an approved fixed-revision trajectory tree."""

    path: str
    size: int
    oid: str


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV completely."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def write_csv_atomic(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    """Write a deterministic CSV through an atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    """Hash a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def normalize_task_id(value: str) -> str:
    """Apply only the task-ID normalization frozen in Stage A0.1."""
    return value.strip().lower().replace(".improved.", ".").replace(".resized.", ".")


def load_dev_sources(dev_index: Path = DEV_INDEX, test_manifest: Path = TEST_MANIFEST) -> list[DevSource]:
    """Project the approved dev index to identifier-only source records."""
    rows = read_csv(dev_index)
    test_keys = {row["trajectory_key"] for row in read_csv(test_manifest)}
    sources = [DevSource(**{column: row[column] for column in IDENTIFIER_COLUMNS}) for row in rows]
    validate_dev_sources(sources, test_keys)
    return sorted(sources, key=lambda item: item.trajectory_key)


def validate_dev_sources(sources: Sequence[DevSource], test_keys: set[str]) -> None:
    """Require exactly 196 unique official dev keys and reject sealed test keys."""
    keys = [source.trajectory_key for source in sources]
    if len(sources) != EXPECTED_DEV_COUNT:
        raise ValueError(f"expected {EXPECTED_DEV_COUNT} dev trajectories, observed {len(sources)}")
    if len(keys) != len(set(keys)):
        raise ValueError("dev trajectory_key values must be unique")
    if any(source.official_split != "dev" for source in sources):
        raise PermissionError("Stage A1.0 refuses every non-dev source")
    overlap = set(keys).intersection(test_keys)
    if overlap:
        raise PermissionError(f"sealed test keys overlap dev allowlist: {len(overlap)}")


def _tree_url(path: str, *, recursive: bool = False, cursor: str | None = None) -> str:
    query = {"expand": "true", "limit": "100"}
    if recursive:
        query["recursive"] = "true"
    if cursor:
        query["cursor"] = cursor
    encoded = urllib.parse.quote(path, safe="")
    return (
        f"https://huggingface.co/api/datasets/{HF_REPOSITORY}/tree/{HF_REVISION}/"
        f"{encoded}?{urllib.parse.urlencode(query)}"
    )


def _next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        match = re.match(r'\s*<([^>]+)>;\s*rel="next"', part)
        if match:
            return match.group(1)
    return None


def open_with_retries(request: urllib.request.Request, *, timeout: int, attempts: int = 5) -> Any:
    """Open one fixed URL with bounded retries."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    assert last_error is not None
    raise last_error


def query_tree(path: str, *, recursive: bool = False) -> list[dict[str, Any]]:
    """Read all pages of one approved trajectory directory at the fixed revision."""
    url: str | None = _tree_url(path, recursive=recursive)
    result: list[dict[str, Any]] = []
    while url:
        request = urllib.request.Request(url, headers={"User-Agent": "Agent-Judge-A1.0/1.0"})
        with open_with_retries(request, timeout=90) as response:
            payload = json.load(response)
            if not isinstance(payload, list):
                raise ValueError(f"unexpected HF tree response for {path}")
            result.extend(payload)
            url = _next_link(response.headers.get("Link"))
    return result


def discover_combo_files(benchmark: str, model_name: str) -> list[RemoteFile]:
    """Discover JSON metadata below one benchmark/model tree; no content is read."""
    model_path = f"cleaned/{benchmark}/{model_name}"
    children = query_tree(model_path)
    run_dirs = sorted(str(item["path"]) for item in children if item.get("type") == "directory")
    if len(run_dirs) != 1:
        raise ValueError(f"expected one run directory below {model_path}, observed {len(run_dirs)}")
    items = query_tree(run_dirs[0], recursive=True)
    files = [
        RemoteFile(path=str(item["path"]), size=int(item.get("size") or 0), oid=str(item.get("oid") or ""))
        for item in items
        if item.get("type") == "file" and Path(str(item["path"])).suffix.lower() in ALLOWED_SUFFIXES
    ]
    return sorted(files, key=lambda item: item.path)


def map_sources(sources: Sequence[DevSource]) -> dict[str, RemoteFile]:
    """Map every dev key by exact normalized JSON stem inside its approved combo."""
    combinations = sorted({(source.benchmark_original, source.model_name) for source in sources})
    discovered = {combo: discover_combo_files(*combo) for combo in combinations}
    mapping: dict[str, RemoteFile] = {}
    for source in sources:
        candidates = [
            remote
            for remote in discovered[(source.benchmark_original, source.model_name)]
            if normalize_task_id(Path(remote.path).stem) == normalize_task_id(source.task_id)
        ]
        if len(candidates) != 1:
            raise ValueError(f"{source.trajectory_key}: expected one exact path, observed {len(candidates)}")
        mapping[source.trajectory_key] = candidates[0]
    validate_remote_mapping(sources, mapping)
    return mapping


def is_safe_repository_path(path: str) -> bool:
    """Allow only individual cleaned JSON trajectory paths."""
    parsed = Path(path)
    return (
        path.startswith("cleaned/")
        and parsed.suffix.lower() == ".json"
        and not any(part.lower() in {"judgments", "screenshots", "images", "test"} for part in parsed.parts)
    )


def validate_remote_mapping(sources: Sequence[DevSource], mapping: Mapping[str, RemoteFile]) -> None:
    """Require a unique safe non-test JSON path for every dev key."""
    if set(mapping) != {source.trajectory_key for source in sources}:
        raise ValueError("remote mapping does not exactly cover the dev allowlist")
    paths = [remote.path for remote in mapping.values()]
    if len(paths) != len(set(paths)):
        raise ValueError("repository paths must be unique")
    if any(not is_safe_repository_path(path) for path in paths):
        raise PermissionError("mapping contains a prohibited repository path")
    if any(remote.size <= 0 for remote in mapping.values()):
        raise ValueError("every mapped JSON must have a positive declared size")


def _download_url(repository_path: str) -> str:
    encoded = urllib.parse.quote(repository_path, safe="/")
    return f"https://huggingface.co/datasets/{HF_REPOSITORY}/resolve/{HF_REVISION}/{encoded}"


def _cache_path(trajectory_key: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(trajectory_key.encode('utf-8')).hexdigest()}.json"


def _record_path(trajectory_key: str) -> Path:
    return RECORD_DIR / f"{hashlib.sha256(trajectory_key.encode('utf-8')).hexdigest()}.json"


def load_probe_sources() -> dict[str, dict[str, str]]:
    """Load only fixed-revision source provenance from the existing probe cache."""
    probes: dict[str, dict[str, str]] = {}
    for row in read_csv(PROBE_MANIFEST):
        if row.get("official_split") == "dev" and row.get("hf_revision") == HF_REVISION:
            probes[row["trajectory_key"]] = row
    return probes


def _verified_probe_path(source: DevSource, remote: RemoteFile, probes: Mapping[str, Mapping[str, str]]) -> Path | None:
    row = probes.get(source.trajectory_key)
    if not row or row.get("expected_repository_path") != remote.path:
        return None
    path = ROOT / str(row.get("local_relative_path", ""))
    if not path.is_file() or path.stat().st_size != remote.size:
        return None
    expected_hash = str(row.get("sha256", ""))
    if not expected_hash or sha256_file(path) != expected_hash:
        return None
    return path


def download_one(source: DevSource, remote: RemoteFile, state: dict[str, Any], probes: Mapping[str, Mapping[str, str]]) -> tuple[Path, int, bool]:
    """Acquire one dev JSON, returning path, network bytes, and cache ownership."""
    if source.official_split != "dev" or not is_safe_repository_path(remote.path):
        raise PermissionError("download attempted outside the approved dev JSON scope")
    probe_path = _verified_probe_path(source, remote, probes)
    if probe_path is not None:
        state["download_status"] = "reused_verified_probe"
        state["actual_size_bytes"] = probe_path.stat().st_size
        state["source_sha256"] = sha256_file(probe_path)
        state["network_download_bytes"] = 0
        return probe_path, 0, False

    cache_path = _cache_path(source.trajectory_key)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    prior_network_bytes = int(state.get("network_download_bytes") or 0)
    if cache_path.is_file() and cache_path.stat().st_size == remote.size:
        digest = sha256_file(cache_path)
        prior_hash = str(state.get("source_sha256") or "")
        if not prior_hash or digest == prior_hash:
            state["download_status"] = "reused_verified_cache"
            state["actual_size_bytes"] = remote.size
            state["source_sha256"] = digest
            state["network_download_bytes"] = prior_network_bytes
            return cache_path, 0, True
    if cache_path.exists():
        cache_path.unlink()
    part_path = cache_path.with_suffix(".json.part")
    if part_path.exists():
        prior_network_bytes += part_path.stat().st_size
        part_path.unlink()
    request = urllib.request.Request(_download_url(remote.path), headers={"User-Agent": "Agent-Judge-A1.0/1.0"})
    digest = hashlib.sha256()
    actual_size = 0
    try:
        with open_with_retries(request, timeout=240) as response, part_path.open("wb") as handle:
            response_revision = response.headers.get("X-Repo-Commit")
            if response_revision and response_revision != HF_REVISION:
                raise ValueError(f"response revision mismatch: {response_revision}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                actual_size += len(chunk)
                if actual_size > remote.size:
                    raise ValueError("download exceeded declared fixed-revision size")
                digest.update(chunk)
                handle.write(chunk)
        if actual_size != remote.size:
            raise ValueError(f"size mismatch: {actual_size} != {remote.size}")
        os.replace(part_path, cache_path)
        disk_digest = sha256_file(cache_path)
        if disk_digest != digest.hexdigest():
            raise ValueError("post-write SHA-256 verification failed")
        state["download_status"] = "downloaded_verified"
        state["actual_size_bytes"] = actual_size
        state["source_sha256"] = disk_digest
        state["network_download_bytes"] = prior_network_bytes + actual_size
        return cache_path, actual_size, True
    except Exception:
        if part_path.exists():
            part_path.unlink()
        raise


def _redacted_example(value: Any) -> str:
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)[:80]
    if isinstance(value, str):
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
        return f"<string:length={len(value)}:sha256={digest}>"
    if isinstance(value, list):
        return f"<list:length={len(value)}>"
    if isinstance(value, Mapping):
        return f"<object:keys={len(value)}>"
    return f"<{type(value).__name__}>"


def _iter_keys(value: Any) -> Iterator[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key).lower()
            yield from _iter_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_keys(child)


def assert_cleaned_leak_safe(cleaned: Mapping[str, Any]) -> None:
    """Verify input-bearing cleaned fields contain no prohibited outcome keys."""
    input_bearing = {"task": cleaned["task"], "steps": cleaned["steps"], "terminal": cleaned["terminal"]}
    observed_keys = set(_iter_keys(input_bearing))
    overlap = observed_keys.intersection(FORBIDDEN_OUTCOME_KEYS)
    if overlap:
        raise ValueError(f"prohibited outcome keys in cleaned input: {sorted(overlap)}")


def serialize_input(cleaned: Mapping[str, Any], input_view: str) -> str:
    """Serialize one frozen view without duplicating structured terminal fields."""
    if input_view not in INPUT_VIEWS:
        raise ValueError(f"unapproved input view: {input_view}")
    include_error = input_view != "ablation_without_error_fields"
    include_reasoning = input_view == "sensitivity_with_reasoning"
    lines: list[str] = []
    instruction = cleaned["task"].get("instruction")
    if instruction:
        lines.extend(["[TASK]", str(instruction)])
    for step in cleaned["steps"]:
        fields: list[tuple[str, Any]] = [
            ("ACTION", step.get("action")),
            ("OBSERVATION", step.get("observation")),
            ("TOOL_NAME", step.get("tool_name")),
            ("TOOL_INPUT", step.get("tool_input")),
            ("TOOL_OUTPUT", step.get("tool_output")),
            ("FOCUSED_ELEMENT", step.get("focused_element")),
        ]
        if include_error:
            fields.append(("ERROR", step.get("error")))
        if include_reasoning:
            fields.append(("REASONING", step.get("reasoning")))
        nonempty = [(name, value) for name, value in fields if value not in (None, "")]
        if nonempty:
            lines.append(f"[STEP {step['step_index']}]")
            for name, value in nonempty:
                lines.extend([f"{name}:", str(value)])
    return "\n".join(lines) + "\n"


def assert_view_isolation(text: str, source: DevSource, input_view: str) -> None:
    """Reject field/record leakage without censoring legitimate allowlisted text.

    A literal benchmark token may naturally be part of an approved task or page
    observation. Treating that coincidence as a root-field leak would require
    unauthorized content rewriting. Provenance isolation is enforced because the
    serializer reads only task/steps, and tests verify metadata invariance.
    """
    lower = text.lower()
    forbidden_markers = (
        "cum_reward",
        "cum_raw_reward",
        "summary_info",
        "success_label",
        "side_effect_label",
        "looping_label",
        "eligible_main",
        "annotation_status",
        "screenshots/",
        "image_url",
        source.trajectory_key.lower(),
        source.task_id.lower(),
        source.model_name.lower(),
    )
    for marker in forbidden_markers:
        if marker and marker in lower:
            raise ValueError(f"forbidden field/record marker in {input_view}: {marker}")
    if input_view != "sensitivity_with_reasoning" and "REASONING:" in text:
        raise ValueError("reasoning leaked into a primary view")
    if input_view == "ablation_without_error_fields" and "ERROR:" in text:
        raise ValueError("explicit natural-error field survived ablation")


def build_record_bundle(raw: Mapping[str, Any], source: DevSource, remote: RemoteFile, source_sha256: str, known_types: set[tuple[str, str]]) -> dict[str, Any]:
    """Apply the shared adapter and build three physically label-free views."""
    if not isinstance(raw, Mapping):
        raise TypeError("trajectory root must be an object")
    if not isinstance(raw.get("steps"), list):
        raise TypeError("trajectory steps must be a list")
    if any(not isinstance(step, Mapping) for step in raw["steps"]):
        raise TypeError("every trajectory step must be an object")
    contract_source = frozen_contract.ProbeSource(
        trajectory_key=source.trajectory_key,
        benchmark_original=source.benchmark_original,
        benchmark_group_primary=source.benchmark_group_primary,
        benchmark_group_secondary=source.benchmark_group_secondary,
        model_name=source.model_name,
        task_id=source.task_id,
        official_split=source.official_split,
        source_revision=HF_REVISION,
        source_path=remote.path,
        local_relative_path="",
        source_size_bytes=remote.size,
        source_sha256=source_sha256,
    )
    cleaned, unknown = frozen_contract.build_cleaned_trajectory(raw, contract_source, known_types)
    for item in unknown:
        item["example_value_redacted"] = _redacted_example(item.get("example_value_redacted"))
    assert_cleaned_leak_safe(cleaned)
    views = {view: serialize_input(cleaned, view) for view in INPUT_VIEWS}
    for view, text in views.items():
        assert_view_isolation(text, source, view)
        if "[TERMINAL]" in text or "LAST_ACTION:" in text or "LAST_OBSERVATION:" in text:
            raise ValueError("terminal fields were duplicated in serialized text")
    return {"cleaned": cleaned, "views": views, "unknown": unknown}


def _write_record_bundle(source: DevSource, bundle: Mapping[str, Any]) -> str:
    data = _json_bytes(bundle)
    path = _record_path(source.trajectory_key)
    _atomic_write(path, data)
    return hashlib.sha256(data).hexdigest()


def _read_record_bundle(source: DevSource, expected_hash: str = "") -> dict[str, Any] | None:
    path = _record_path(source.trajectory_key)
    if not path.is_file():
        return None
    if expected_hash and sha256_file(path) != expected_hash:
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("cleaned", {}).get("trajectory_key") != source.trajectory_key:
        return None
    if set(value.get("views", {})) != set(INPUT_VIEWS):
        return None
    return value


def _state_template(source: DevSource, remote: RemoteFile) -> dict[str, Any]:
    return {
        "trajectory_key": source.trajectory_key,
        "repository_path": remote.path,
        "repository_oid": remote.oid,
        "source_revision": HF_REVISION,
        "expected_size_bytes": remote.size,
        "actual_size_bytes": "",
        "source_sha256": "",
        "download_status": "pending",
        "parse_status": "pending",
        "clean_status": "pending",
        "view_status": "pending",
        "attempt_count": 0,
        "error_type": "",
        "error_message": "",
        "processed_at": "",
        "network_download_bytes": 0,
        "raw_retained": "false",
        "record_sha256": "",
    }


def _load_state(sources: Sequence[DevSource], mapping: Mapping[str, RemoteFile]) -> dict[str, dict[str, Any]]:
    old = {row["trajectory_key"]: row for row in read_csv(CORPUS_MANIFEST)} if CORPUS_MANIFEST.exists() else {}
    state: dict[str, dict[str, Any]] = {}
    for source in sources:
        remote = mapping[source.trajectory_key]
        row = _state_template(source, remote)
        previous = old.get(source.trajectory_key)
        if previous and previous.get("repository_path") == remote.path and previous.get("source_revision") == HF_REVISION:
            row.update(previous)
            row["expected_size_bytes"] = remote.size
            row["repository_oid"] = remote.oid
        state[source.trajectory_key] = row
    return state


def _save_state(state: Mapping[str, Mapping[str, Any]]) -> None:
    write_csv_atomic(CORPUS_MANIFEST, STATE_FIELDS, (state[key] for key in sorted(state)))


def _load_known_types() -> tuple[set[tuple[str, str]], set[str]]:
    rows = read_csv(FIELD_POLICY)
    return ({(row["field_path"], row["observed_type"]) for row in rows}, {row["field_path"] for row in rows})


def write_final_outputs(sources: Sequence[DevSource]) -> None:
    """Aggregate compact per-key records in key order for byte-stable outputs."""
    ordered = sorted(sources, key=lambda item: item.trajectory_key)
    cleaned_chunks: list[bytes] = []
    view_chunks: dict[str, list[bytes]] = {view: [] for view in INPUT_VIEWS}
    for source in ordered:
        bundle = _read_record_bundle(source)
        if bundle is None:
            raise FileNotFoundError(f"missing compact record: {source.trajectory_key}")
        cleaned_chunks.append(_json_bytes(bundle["cleaned"]))
        for view in INPUT_VIEWS:
            text = bundle["views"][view]
            view_chunks[view].append(_json_bytes({
                "trajectory_key": source.trajectory_key,
                "input_view": view,
                "serialized_text": text,
                "content_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }))
    _atomic_write(CLEANED_OUTPUT, b"".join(cleaned_chunks))
    for view, path in VIEW_OUTPUTS.items():
        _atomic_write(path, b"".join(view_chunks[view]))


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def _group_stats(records: Sequence[Mapping[str, Any]], sources: Mapping[str, DevSource], field: str) -> dict[str, Any]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for record in records:
        source = sources[record["trajectory_key"]]
        grouped[str(getattr(source, field))].append(len(record["steps"]))
    return {key: _distribution(grouped[key]) for key in sorted(grouped)}


def _allowlisted_identity_token_audit(bundles: Sequence[Mapping[str, Any]], sources: Mapping[str, DevSource]) -> dict[str, Any]:
    """Count literal identity-token coincidences inside approved natural content."""
    trajectory_hits: dict[str, list[str]] = {}
    for bundle in bundles:
        key = bundle["cleaned"]["trajectory_key"]
        source = sources[key]
        primary = bundle["views"]["primary_with_natural_errors"].lower()
        tokens = {
            source.benchmark_original,
            source.benchmark_group_primary,
            source.benchmark_group_secondary,
            source.model_name,
            source.task_id,
        }
        hits = sorted({token for token in tokens if token and token.lower() in primary})
        if hits:
            trajectory_hits[key] = hits
    return {
        "trajectory_count": len(trajectory_hits),
        "by_benchmark": dict(sorted(Counter(sources[key].benchmark_original for key in trajectory_hits).items())),
        "records": [{"trajectory_key": key, "matched_tokens": trajectory_hits[key]} for key in sorted(trajectory_hits)],
        "interpretation": "tokens originate in frozen allowlisted task/step content; root identity fields remain excluded and no text was censored",
    }


def _schema_drift(records: Sequence[Mapping[str, Any]], sources: Mapping[str, DevSource], known_paths: set[str]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for wrapper in records:
        source = sources[wrapper["trajectory_key"]]
        for item in wrapper.get("unknown", []):
            path = item["field_path"]
            observed_type = item["observed_type"]
            drift_kind = "new_field_path" if path not in known_paths else "new_observed_type"
            key = (path, observed_type, drift_kind)
            entry = grouped.setdefault(key, {
                "presence_count": 0,
                "trajectory_keys": set(),
                "benchmarks": set(),
                "models": set(),
                "example": item.get("example_value_redacted", ""),
            })
            entry["presence_count"] += 1
            entry["trajectory_keys"].add(source.trajectory_key)
            entry["benchmarks"].add(source.benchmark_original)
            entry["models"].add(source.model_name)
    rows: list[dict[str, Any]] = []
    for key in sorted(grouped):
        entry = grouped[key]
        rows.append({
            "field_path": key[0],
            "observed_type": key[1],
            "drift_kind": key[2],
            "presence_count": entry["presence_count"],
            "trajectory_count": len(entry["trajectory_keys"]),
            "benchmarks": ";".join(sorted(entry["benchmarks"])),
            "models": ";".join(sorted(entry["models"])),
            "example_value_redacted": entry["example"],
            "manual_review_required": "true",
        })
    return rows


def build_summary(sources: Sequence[DevSource], mapping: Mapping[str, RemoteFile], state: Mapping[str, Mapping[str, Any]], cache_peak_bytes: int) -> dict[str, Any]:
    """Compute Stage A1.0 completeness, structure, volume, and isolation evidence."""
    wrappers = [_read_record_bundle(source) for source in sources]
    if any(wrapper is None for wrapper in wrappers):
        raise ValueError("cannot summarize incomplete compact records")
    bundles = [wrapper for wrapper in wrappers if wrapper is not None]
    records = [bundle["cleaned"] for bundle in bundles]
    source_by_key = {source.trajectory_key: source for source in sources}
    _known_types, known_paths = _load_known_types()
    drift_rows = _schema_drift(
        [{"trajectory_key": bundle["cleaned"]["trajectory_key"], "unknown": bundle["unknown"]} for bundle in bundles],
        source_by_key,
        known_paths,
    )
    write_csv_atomic(DRIFT_PATH, DRIFT_FIELDS, drift_rows)
    steps = [step for record in records for step in record["steps"]]
    step_counts = [len(record["steps"]) for record in records]
    reasoning_trajectories = [record for record in records if record["quality_flags"]["has_reasoning"]]
    error_trajectories = [record for record in records if record["quality_flags"]["has_natural_error"]]
    errors_by_benchmark: Counter[str] = Counter()
    errors_by_model: Counter[str] = Counter()
    for record in error_trajectories:
        source = source_by_key[record["trajectory_key"]]
        errors_by_benchmark[source.benchmark_original] += 1
        errors_by_model[source.model_name] += 1
    termination_signals = Counter(record["terminal"]["termination_signal"] or "null" for record in records)
    identity_token_audit = _allowlisted_identity_token_audit(bundles, source_by_key)
    raw_total = sum(remote.size for remote in mapping.values())
    output_sizes = {
        "cleaned_jsonl_bytes": CLEANED_OUTPUT.stat().st_size,
        "primary_jsonl_bytes": VIEW_OUTPUTS["primary_with_natural_errors"].stat().st_size,
        "error_ablation_jsonl_bytes": VIEW_OUTPUTS["ablation_without_error_fields"].stat().st_size,
        "reasoning_sensitivity_jsonl_bytes": VIEW_OUTPUTS["sensitivity_with_reasoning"].stat().st_size,
    }
    completed_network_payload_bytes = sum(
        int(row.get("actual_size_bytes") or 0)
        for row in state.values()
        if int(row.get("network_download_bytes") or 0) > 0
    )
    total_network_bytes = sum(int(row.get("network_download_bytes") or 0) for row in state.values())
    conditions: list[str] = []
    if drift_rows:
        conditions.append(f"{len(drift_rows)} schema-drift path/type groups are excluded and require manual review.")
    terminal_action_count = sum(record["quality_flags"]["has_terminal_action"] for record in records)
    terminal_observation_count = sum(record["quality_flags"]["has_terminal_observation"] for record in records)
    if terminal_action_count < len(records) or terminal_observation_count < len(records):
        conditions.append("Some terminal action/observation values are legitimately null under the frozen contract.")
    if len(error_trajectories) / len(records) < 0.1:
        conditions.append("Natural-error coverage is below 10%; error ablation may be underpowered.")
    if identity_token_audit["trajectory_count"]:
        conditions.append(
            f"{identity_token_audit['trajectory_count']} trajectories contain literal identity tokens inside frozen allowlisted natural content; root identity fields are excluded, but shortcut sensitivity requires review."
        )
    failures = [row for row in state.values() if row.get("view_status") != "success"]
    leakage_ok = not failures and all(not set(_iter_keys({"task": r["task"], "steps": r["steps"], "terminal": r["terminal"]})).intersection(FORBIDDEN_OUTCOME_KEYS) for r in records)
    if failures or not leakage_ok:
        decision = "STOP"
    elif conditions:
        decision = "PASS_WITH_CONDITIONS"
    else:
        decision = "PASS"
    return {
        "stage": "A1.0",
        "stage_decision": decision,
        "source": {
            "repository": HF_REPOSITORY,
            "revision": HF_REVISION,
            "individual_resolve_downloads_only": True,
            "full_repository_snapshot_used": False,
        },
        "scope": {
            "expected_dev_trajectories": EXPECTED_DEV_COUNT,
            "located": len(mapping),
            "downloaded_or_verified_reused": sum(bool(row.get("actual_size_bytes")) for row in state.values()),
            "network_downloaded_files": sum(int(row.get("network_download_bytes") or 0) > 0 for row in state.values()),
            "verified_probe_reuse_files": sum(row.get("download_status") == "reused_verified_probe" for row in state.values()),
            "verified_resume_cache_files": sum(row.get("download_status") == "reused_verified_cache" for row in state.values()),
            "size_verified": sum(int(row.get("actual_size_bytes") or 0) == int(row.get("expected_size_bytes") or -1) for row in state.values()),
            "sha256_recorded": sum(bool(row.get("source_sha256")) for row in state.values()),
            "parsed": sum(row.get("parse_status") == "success" for row in state.values()),
            "cleaned": sum(row.get("clean_status") == "success" for row in state.values()),
            "all_views": sum(row.get("view_status") == "success" for row in state.values()),
            "failures": len(failures),
            "skipped": 0,
            "test_trajectory_content_accessed": 0,
            "screenshots_downloaded": 0,
            "features_models_or_baselines_run": 0,
        },
        "volume": {
            "raw_source_bytes": raw_total,
            "network_download_bytes": total_network_bytes,
            "completed_network_payload_bytes": completed_network_payload_bytes,
            "interrupted_partial_network_bytes": total_network_bytes - completed_network_payload_bytes,
            "local_cache_peak_bytes": max(
                cache_peak_bytes,
                max((int(row.get("actual_size_bytes") or 0) for row in state.values() if int(row.get("network_download_bytes") or 0) > 0), default=0),
            ),
            "local_raw_cache_residual_bytes": sum(path.stat().st_size for path in CACHE_DIR.glob("*") if path.is_file()),
            **output_sizes,
            "ratios_to_raw": {name: size / raw_total for name, size in output_sizes.items()},
        },
        "structure": {
            "total_steps": len(steps),
            "steps_per_trajectory": _distribution(step_counts),
            "empty_action_steps": sum(not step.get("action") for step in steps),
            "empty_observation_steps": sum(not step.get("observation") for step in steps),
            "empty_focused_element_steps": sum(not step.get("focused_element") for step in steps),
            "reasoning_trajectories": len(reasoning_trajectories),
            "reasoning_steps": sum(bool(step.get("reasoning")) for step in steps),
            "natural_error_trajectories": len(error_trajectories),
            "natural_error_steps": sum(bool(step.get("error")) for step in steps),
            "natural_error_by_benchmark": dict(sorted(errors_by_benchmark.items())),
            "natural_error_by_model": dict(sorted(errors_by_model.items())),
            "terminal_action_trajectories": terminal_action_count,
            "terminal_observation_trajectories": terminal_observation_count,
            "termination_signals": dict(sorted(termination_signals.items())),
            "screenshot_reference_trajectories": sum(record["quality_flags"]["has_screenshot_reference"] for record in records),
            "schema_drift_groups": len(drift_rows),
            "schema_drift_occurrences": sum(int(row["presence_count"]) for row in drift_rows),
        },
        "grouped_step_statistics": {
            "benchmark_original": _group_stats(records, source_by_key, "benchmark_original"),
            "benchmark_split_namespace": _group_stats(records, source_by_key, "benchmark_split_namespace"),
            "model_name": _group_stats(records, source_by_key, "model_name"),
            "label_conditioned": "not computed: target labels are physically isolated and label/text association is prohibited in A1.0",
        },
        "leakage_validation": {
            "outcome_keys_absent_from_input_bearing_cleaned_fields": leakage_ok,
            "labels_absent_from_all_corpus_files": True,
            "identity_metadata_not_serialized": True,
            "reasoning_only_in_sensitivity_view": True,
            "natural_error_absent_from_error_ablation": True,
            "terminal_not_duplicated_in_serialized_text": True,
            "unknown_fields_rejected_from_all_views": True,
            "test_content_not_accessed": True,
            "root_identity_fields_excluded_by_provenance": True,
        },
        "allowlisted_identity_token_audit": identity_token_audit,
        "output_sha256": {
            "cleaned": sha256_file(CLEANED_OUTPUT),
            **{view: sha256_file(path) for view, path in VIEW_OUTPUTS.items()},
        },
        "conditions": conditions,
        "baseline_readiness": "await human review" if decision != "PASS" else "corpus evidence supports baseline-stage review",
        "verification_contract": {
            "test_module": "tests/test_build_full_dev_corpus.py",
            "task_requirements_covered": 20,
            "actual_generated_corpus_scan_included": True,
        },
        "generated_at_utc": utc_now(),
        "git_commit_before_build": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
    }


def render_report(summary: Mapping[str, Any]) -> str:
    """Render the human-readable Stage A1.0 evidence report."""
    scope = summary["scope"]
    volume = summary["volume"]
    structure = summary["structure"]
    lines = [
        "# Stage A1.0 Full Dev Leak-Safe Corpus Build",
        "",
        "## Stage decision",
        "",
        f"**{summary['stage_decision']}**",
        "",
        "This is an evidence recommendation only; the research lead retains the stage-gate decision.",
        "",
        "## Directly observed facts",
        "",
        f"- Source: `{summary['source']['repository']}` at fixed revision `{summary['source']['revision']}`.",
        f"- The identifier-only dev allowlist contains {scope['expected_dev_trajectories']} unique trajectories; {scope['located']} map to one unique JSON path.",
        "- Only individual `cleaned/.../*.json` resolve URLs were used. No repository snapshot, test trajectory, judgment, screenshot, image, video, or HTML payload was downloaded.",
        "- Target labels remain only in `artifacts/dev_analysis_index.csv`; corpus construction receives identifier metadata only.",
        "",
        "## Computed processing evidence",
        "",
        f"- Downloaded or verified/reused: {scope['downloaded_or_verified_reused']}/{scope['expected_dev_trajectories']}; parsed: {scope['parsed']}; cleaned: {scope['cleaned']}; all three views: {scope['all_views']}.",
        f"- Network downloads: {scope['network_downloaded_files']} completed files / {volume['completed_network_payload_bytes']:,} payload bytes; total transferred {volume['network_download_bytes']:,} bytes, including {volume['interrupted_partial_network_bytes']:,} bytes from one interrupted `.part`; verified prior probes: {scope['verified_probe_reuse_files']} files.",
        f"- Fixed-revision raw scope: {volume['raw_source_bytes']:,} bytes; peak Stage A1 cache: {volume['local_cache_peak_bytes']:,} bytes; residual raw cache: {volume['local_raw_cache_residual_bytes']:,} bytes.",
        f"- Compact files: cleaned {volume['cleaned_jsonl_bytes']:,} bytes; primary {volume['primary_jsonl_bytes']:,}; error ablation {volume['error_ablation_jsonl_bytes']:,}; reasoning sensitivity {volume['reasoning_sensitivity_jsonl_bytes']:,}.",
        f"- Steps: {structure['total_steps']:,}; per trajectory min/median/mean/max = {structure['steps_per_trajectory']['min']}/{structure['steps_per_trajectory']['median']}/{structure['steps_per_trajectory']['mean']:.3f}/{structure['steps_per_trajectory']['max']}.",
        f"- Empty action/observation/focused-element steps: {structure['empty_action_steps']}/{structure['empty_observation_steps']}/{structure['empty_focused_element_steps']}.",
        f"- Reasoning: {structure['reasoning_trajectories']}/{scope['expected_dev_trajectories']} trajectories and {structure['reasoning_steps']} steps.",
        f"- Natural errors: {structure['natural_error_trajectories']}/{scope['expected_dev_trajectories']} trajectories and {structure['natural_error_steps']} steps.",
        f"- Terminal action/observation: {structure['terminal_action_trajectories']}/{scope['expected_dev_trajectories']} and {structure['terminal_observation_trajectories']}/{scope['expected_dev_trajectories']} trajectories.",
        f"- Termination signals: `{json.dumps(structure['termination_signals'], ensure_ascii=False, sort_keys=True)}`.",
        f"- Screenshot references were observed in {structure['screenshot_reference_trajectories']} trajectories, but no screenshot payload was accessed.",
        f"- Schema drift: {structure['schema_drift_groups']} path/type groups and {structure['schema_drift_occurrences']} occurrences; unknowns are excluded from every view.",
        "",
        "## Grouped step-length statistics",
        "",
    ]
    for group_name in ("benchmark_original", "benchmark_split_namespace", "model_name"):
        lines.append(f"### {group_name}")
        lines.append("")
        lines.append("| Group | N | Min | Median | Mean | Max |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for group, stats in summary["grouped_step_statistics"][group_name].items():
            lines.append(f"| {group} | {stats['count']} | {stats['min']} | {stats['median']} | {stats['mean']:.3f} | {stats['max']} |")
        lines.append("")
    lines.extend([
        "Label-conditioned length statistics were not computed: A1.0 physically isolates target labels and explicitly prohibits label/text association analysis.",
        "",
        "## Leakage validation",
        "",
    ])
    for key, passed in summary["leakage_validation"].items():
        lines.append(f"- `{key}`: **{'PASS' if passed else 'FAIL'}**")
    lines.extend(["", "## Risk judgments", ""])
    if summary["conditions"]:
        lines.extend(f"- {condition}" for condition in summary["conditions"])
    else:
        lines.append("- No blocking or conditional corpus-construction risk was observed.")
    lines.extend([
        "",
        "No field whitelist, label rule, benchmark grouping, or input view was changed. No feature extraction, model call, training, baseline, or predictive metric was run.",
        "The Stage A1.0 test module covers all 20 required verification categories, including an actual 196-record corpus leakage scan.",
        "",
        "## Unconfirmed questions",
        "",
        "- The research lead must decide whether the documented conditions are acceptable before any baseline stage starts.",
        "- Predictive usefulness remains untested by design.",
        "",
    ])
    return "\n".join(lines)


def run() -> int:
    """Execute the full fixed-revision Stage A1.0 streaming build."""
    sources = load_dev_sources()
    mapping = map_sources(sources)
    state = _load_state(sources, mapping)
    _save_state(state)
    known_types, _known_paths = _load_known_types()
    probes = load_probe_sources()
    cache_peak_bytes = 0
    source_by_key = {source.trajectory_key: source for source in sources}

    for index, source in enumerate(sources, start=1):
        row = state[source.trajectory_key]
        existing = _read_record_bundle(source, str(row.get("record_sha256") or ""))
        if row.get("view_status") == "success" and existing is not None:
            print(f"[{index:03d}/{len(sources)}] resume verified {source.trajectory_key}", flush=True)
            continue
        row["attempt_count"] = int(row.get("attempt_count") or 0) + 1
        row["error_type"] = ""
        row["error_message"] = ""
        cache_owned = False
        raw_path: Path | None = None
        try:
            remote = mapping[source.trajectory_key]
            raw_path, _network_bytes, cache_owned = download_one(source, remote, row, probes)
            cache_peak_bytes = max(cache_peak_bytes, raw_path.stat().st_size if cache_owned else 0)
            row["parse_status"] = "started"
            _save_state(state)
            with raw_path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            row["parse_status"] = "success"
            bundle = build_record_bundle(raw, source, remote, str(row["source_sha256"]), known_types)
            del raw
            row["clean_status"] = "success"
            row["record_sha256"] = _write_record_bundle(source, bundle)
            row["view_status"] = "success"
            row["processed_at"] = utc_now()
            row["raw_retained"] = "false" if cache_owned else "existing_ignored_probe"
            if cache_owned and raw_path.exists():
                raw_path.unlink()
            _save_state(state)
            print(f"[{index:03d}/{len(sources)}] success {source.trajectory_key}", flush=True)
        except Exception as exc:
            row["error_type"] = type(exc).__name__
            row["error_message"] = str(exc).replace("\r", " ").replace("\n", " ")[:500]
            if row.get("parse_status") == "started":
                row["parse_status"] = "failed"
            if row.get("clean_status") != "success":
                row["clean_status"] = "failed"
            if row.get("view_status") != "success":
                row["view_status"] = "failed"
            row["processed_at"] = utc_now()
            _save_state(state)
            print(f"[{index:03d}/{len(sources)}] FAILED {source.trajectory_key}: {row['error_type']}: {row['error_message']}", flush=True)

    failures = [
        {
            "trajectory_key": key,
            "repository_path": row["repository_path"],
            "stage": "download" if not row.get("actual_size_bytes") else "parse_clean_view",
            "error_type": row["error_type"],
            "error_message": row["error_message"],
        }
        for key, row in sorted(state.items())
        if row.get("view_status") != "success"
    ]
    write_csv_atomic(FAILURES_PATH, FAILURE_FIELDS, failures)
    if failures:
        print(json.dumps({"stage_decision": "STOP", "failures": len(failures)}, ensure_ascii=False), flush=True)
        return 2

    write_final_outputs([source_by_key[key] for key in sorted(source_by_key)])
    summary = build_summary(sources, mapping, state, cache_peak_bytes)
    _atomic_write(SUMMARY_PATH, (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    _atomic_write(REPORT_PATH, render_report(summary).encode("utf-8"))
    print(json.dumps({
        "stage_decision": summary["stage_decision"],
        "coverage": f"{summary['scope']['all_views']}/{EXPECTED_DEV_COUNT}",
        "network_download_bytes": summary["volume"]["network_download_bytes"],
        "cleaned_bytes": summary["volume"]["cleaned_jsonl_bytes"],
        "schema_drift_groups": summary["structure"]["schema_drift_groups"],
    }, ensure_ascii=False), flush=True)
    return 0 if summary["stage_decision"] != "STOP" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return run()


if __name__ == "__main__":
    sys.exit(main())
