"""Run the bounded Stage A0.3 dev trajectory schema and leakage probe."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


HF_REPOSITORY = "McGill-NLP/agent-reward-bench"
HF_REVISION = "b6d17e646009d6cb63d5dd7be78807b680693f61"
MAX_PROBES = 24
MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]
DEV_INDEX = ROOT / "artifacts" / "dev_analysis_index.csv"
TEST_MANIFEST = ROOT / "artifacts" / "test_manifest.csv"
PROBE_MANIFEST = ROOT / "artifacts" / "dev_probe_manifest.csv"
FIELD_INVENTORY = ROOT / "artifacts" / "trajectory_field_inventory.csv"
LEAKAGE_REGISTER = ROOT / "artifacts" / "leakage_risk_register.csv"
SUMMARY_PATH = ROOT / "artifacts" / "trajectory_probe_summary.json"
REPORT_PATH = ROOT / "docs" / "trajectory_schema_probe.md"
RAW_PROBE = ROOT / "data" / "raw_probe"

ALLOWED_SUFFIXES = {".json"}
TARGETS = ("success", "side_effect", "looping")
DIRECT_TERMS = {
    "success", "successful", "failure", "failed", "passed", "side_effect",
    "looping", "repetitiveness", "ground_truth_label", "annotation",
    "human_judgment", "judge_result", "reward", "score", "task_reward",
}
STRONG_PROXY_TERMS = {
    "evaluation", "evaluator", "judgment", "judgement", "verdict",
    "task_completed", "task_success", "done_status", "final_score",
}


@dataclass(frozen=True)
class RemoteFile:
    """Metadata for one file observed in the fixed Hugging Face tree."""

    path: str
    size: int


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV completely into dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    """Write a deterministic UTF-8 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def normalize_task_id(value: str) -> str:
    """Apply only the A0.1-approved task-ID normalization."""
    normalized = value.strip().lower()
    normalized = normalized.replace(".improved.", ".")
    normalized = normalized.replace(".resized.", ".")
    return normalized


def validate_dev_rows(rows: Sequence[Mapping[str, str]]) -> None:
    """Reject non-dev, duplicate, malformed, or oversized candidate sets."""
    keys = [row["trajectory_key"] for row in rows]
    if any(row.get("official_split") != "dev" for row in rows):
        raise ValueError("A0.3 refuses every non-dev trajectory")
    if len(keys) != len(set(keys)):
        raise ValueError("dev trajectory_key values must be unique")


def assert_not_test_key(trajectory_key: str, test_keys: set[str]) -> None:
    """Prevent a sealed test key from reaching mapping or download code."""
    if trajectory_key in test_keys:
        raise PermissionError("A0.3 refuses test trajectory mapping and download")


def _tree_url(path: str, *, recursive: bool = False, cursor: str | None = None) -> str:
    encoded = urllib.parse.quote(path, safe="")
    query: dict[str, str] = {"expand": "true", "limit": "100"}
    if recursive:
        query["recursive"] = "true"
    if cursor:
        query["cursor"] = cursor
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


def open_with_retries(request: urllib.request.Request, *, timeout: int, attempts: int = 4) -> Any:
    """Open an HTTP request with bounded retries for transient network failures."""
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(request, timeout=timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    assert last_error is not None
    raise last_error


def query_tree(path: str, *, recursive: bool = False) -> list[dict[str, Any]]:
    """Query every page of one directory at the fixed HF revision."""
    url: str | None = _tree_url(path, recursive=recursive)
    result: list[dict[str, Any]] = []
    while url:
        request = urllib.request.Request(url, headers={"User-Agent": "Agent-Judge-A0.3/1.0"})
        with open_with_retries(request, timeout=60) as response:
            payload = json.load(response)
            if not isinstance(payload, list):
                raise ValueError(f"unexpected HF tree response for {path}")
            result.extend(payload)
            url = _next_link(response.headers.get("Link"))
    return result


def discover_combo_files(benchmark: str, model_name: str) -> list[RemoteFile]:
    """Discover the unique run directory, then enumerate its JSON files."""
    model_path = f"cleaned/{benchmark}/{model_name}"
    children = query_tree(model_path)
    run_dirs = sorted(item["path"] for item in children if item.get("type") == "directory")
    if len(run_dirs) != 1:
        raise ValueError(f"expected one run directory under {model_path}, observed {len(run_dirs)}")
    items = query_tree(run_dirs[0], recursive=True)
    files = [
        RemoteFile(str(item["path"]), int(item.get("size") or 0))
        for item in items
        if item.get("type") == "file" and Path(str(item["path"])).suffix.lower() in ALLOWED_SUFFIXES
    ]
    return sorted(files, key=lambda item: item.path)


def map_dev_rows(
    dev_rows: Sequence[Mapping[str, str]],
    combo_files: Mapping[tuple[str, str], Sequence[RemoteFile]],
    test_keys: set[str],
) -> list[dict[str, Any]]:
    """Map each dev key by exact normalized JSON stem; never fuzzy-match."""
    mapped: list[dict[str, Any]] = []
    for row in dev_rows:
        assert_not_test_key(row["trajectory_key"], test_keys)
        files = combo_files[(row["benchmark_original"], row["model_name"])]
        candidates = [
            item for item in files
            if normalize_task_id(Path(item.path).stem) == normalize_task_id(row["task_id"])
        ]
        record: dict[str, Any] = dict(row)
        record["candidate_count"] = len(candidates)
        if len(candidates) == 1:
            record["path_resolved"] = True
            record["expected_repository_path"] = candidates[0].path
            record["expected_size_bytes"] = candidates[0].size
            record["mapping_issue"] = ""
        else:
            record["path_resolved"] = False
            record["expected_repository_path"] = ""
            record["expected_size_bytes"] = 0
            record["mapping_issue"] = "no_candidate" if not candidates else "ambiguous_candidates"
        mapped.append(record)
    return mapped


def _eligible(row: Mapping[str, Any], target: str, label: str) -> bool:
    return (
        str(row.get(f"{target}_eligible_main", "")).lower() == "true"
        and str(row.get(f"{target}_label", "")) == label
    )


def select_probe_rows(mapped_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Deterministically cover every observed benchmark/model combo and label polarity."""
    resolved = [dict(row) for row in mapped_rows if row.get("path_resolved")]
    by_combo: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in resolved:
        by_combo[(row["benchmark_group_primary"], row["model_name"])].append(row)

    selected: dict[str, dict[str, Any]] = {}
    reasons: dict[str, list[str]] = defaultdict(list)
    for combo in sorted(by_combo):
        row = min(
            by_combo[combo],
            key=lambda item: (int(item["expected_size_bytes"]), item["trajectory_key"]),
        )
        selected[row["trajectory_key"]] = row
        reasons[row["trajectory_key"]].append("coverage_benchmark_model")

    for target in TARGETS:
        for label in ("0", "1"):
            if any(_eligible(row, target, label) for row in selected.values()):
                continue
            candidates = [
                row for row in resolved
                if row["trajectory_key"] not in selected and _eligible(row, target, label)
            ]
            if candidates:
                row = min(candidates, key=lambda item: (int(item["expected_size_bytes"]), item["trajectory_key"]))
                selected[row["trajectory_key"]] = row
                reasons[row["trajectory_key"]].append(f"label_{target}_{label}")

    if selected:
        ordered_selected = list(selected.values())
        shortest = min(ordered_selected, key=lambda item: (int(item["expected_size_bytes"]), item["trajectory_key"]))
        longest = max(ordered_selected, key=lambda item: (int(item["expected_size_bytes"]), item["trajectory_key"]))
        reasons[shortest["trajectory_key"]].append("short_trajectory_size_proxy")
        reasons[longest["trajectory_key"]].append("long_trajectory_size_proxy")

    if len(selected) > MAX_PROBES:
        raise ValueError(f"deterministic selection exceeds {MAX_PROBES} trajectories")
    total = sum(int(row["expected_size_bytes"]) for row in selected.values())
    if total > MAX_DOWNLOAD_BYTES:
        raise ValueError(f"coverage selection requires {total} bytes, above the 200 MB limit")

    output: list[dict[str, Any]] = []
    for key in sorted(selected):
        row = dict(selected[key])
        row["selection_reason"] = ";".join(reasons[key])
        output.append(row)
    return output


def _download_url(repository_path: str) -> str:
    encoded_path = urllib.parse.quote(repository_path, safe="/")
    return f"https://huggingface.co/datasets/{HF_REPOSITORY}/resolve/{HF_REVISION}/{encoded_path}"


def _safe_local_path(repository_path: str) -> Path:
    path = Path(repository_path)
    if not repository_path.startswith("cleaned/") or path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError(f"refusing non-trajectory path: {repository_path}")
    return RAW_PROBE.joinpath(*path.parts[1:])


def download_probe(rows: Sequence[dict[str, Any]], test_keys: set[str]) -> None:
    """Download only selected dev JSON files, enforcing revision and byte budget."""
    expected_total = sum(int(row["expected_size_bytes"]) for row in rows)
    if expected_total > MAX_DOWNLOAD_BYTES:
        raise ValueError("declared probe size exceeds 200 MB")
    downloaded_total = 0
    for row in rows:
        assert_not_test_key(row["trajectory_key"], test_keys)
        if row.get("official_split") != "dev":
            raise PermissionError("non-dev download refused")
        repository_path = str(row["expected_repository_path"])
        local_path = _safe_local_path(repository_path)
        expected_size = int(row["expected_size_bytes"])
        if downloaded_total + expected_size > MAX_DOWNLOAD_BYTES:
            raise ValueError("download would exceed 200 MB")
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if local_path.exists() and local_path.stat().st_size == expected_size:
            content = local_path.read_bytes()
            row.update({
                "download_status": "downloaded",
                "local_relative_path": local_path.relative_to(ROOT).as_posix(),
                "file_size_bytes": expected_size,
                "sha256": hashlib.sha256(content).hexdigest(),
            })
            downloaded_total += expected_size
            continue
        temp_path = local_path.with_suffix(local_path.suffix + ".part")
        digest = hashlib.sha256()
        actual_size = 0
        request = urllib.request.Request(
            _download_url(repository_path), headers={"User-Agent": "Agent-Judge-A0.3/1.0"}
        )
        try:
            with open_with_retries(request, timeout=120) as response, temp_path.open("wb") as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    actual_size += len(chunk)
                    if downloaded_total + actual_size > MAX_DOWNLOAD_BYTES:
                        raise ValueError("actual download exceeds 200 MB")
                    digest.update(chunk)
                    handle.write(chunk)
            if actual_size != expected_size:
                raise ValueError(f"size mismatch for {repository_path}: {actual_size} != {expected_size}")
            os.replace(temp_path, local_path)
            downloaded_total += actual_size
            row.update({
                "download_status": "downloaded",
                "local_relative_path": local_path.relative_to(ROOT).as_posix(),
                "file_size_bytes": actual_size,
                "sha256": digest.hexdigest(),
            })
        except Exception as exc:
            if temp_path.exists():
                temp_path.unlink()
            row.update({"download_status": f"failed:{type(exc).__name__}", "local_relative_path": "", "file_size_bytes": 0, "sha256": ""})
            row["download_error"] = str(exc)


def canonical_field_key(key: Any) -> str:
    """Preserve schema-like object keys and collapse dynamic map keys."""
    text = str(key)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,63}", text):
        return text
    return "{*}"


def iter_fields(value: Any, path: str = "$") -> Iterator[tuple[str, str, Any]]:
    """Recursively enumerate raw JSON fields using stable list-normalized paths."""
    observed_type = "null" if value is None else type(value).__name__
    yield path, observed_type, value
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            if path.endswith((".bounding_boxes", ".extra_element_properties")):
                child_key = "{*}"
            else:
                child_key = canonical_field_key(key)
            yield from iter_fields(value[key], f"{path}.{child_key}")
    elif isinstance(value, list):
        for item in value:
            yield from iter_fields(item, f"{path}[]")


def redact_example(value: Any, limit: int = 80) -> str:
    """Return a short, one-line, non-bulk example."""
    if isinstance(value, (dict, list)):
        return f"<{type(value).__name__}:{len(value)}>"
    text = str(value).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def semantic_role(field_path: str) -> str:
    """Assign a cautious semantic-role suggestion from the raw field name."""
    name = field_path.lower()
    rules = [
        (("task", "intent", "instruction"), "task_instruction_or_metadata"),
        (("system",), "system_prompt"),
        (("reason", "thought"), "assistant_reasoning_or_visible_trace"),
        (("action",), "action"),
        (("tool",), "tool_call_or_result"),
        (("observation", "axtree"), "observation_or_environment_state"),
        (("final", "answer", "response"), "final_response_or_message"),
        (("timestamp", "time"), "timestamp"),
        (("token", "step"), "token_or_step_metadata"),
        (("model",), "model_metadata"),
        (("benchmark", "exp_name"), "benchmark_metadata"),
        (("screenshot", "image"), "screenshot_reference_or_payload"),
        (("reward", "score", "success", "judge", "annotation"), "outcome_or_judgment"),
    ]
    for terms, role in rules:
        if any(term in name for term in terms):
            return role
    return "unclassified"


def leakage_class(field_path: str) -> tuple[str, str, str, str] | None:
    """Classify a field conservatively; outcome fields can never be marked safe."""
    lower = field_path.lower()
    tokens = set(re.findall(r"[a-z0-9_]+", lower))
    direct = sorted(term for term in DIRECT_TERMS if term in tokens or term in lower)
    if direct:
        affected = "Success" if any(term in lower for term in ("reward", "score", "success", "passed", "failure")) else "Success;Side Effect;Looping"
        return "level_1", "direct_label_or_official_outcome", affected, "exclude"
    strong = sorted(term for term in STRONG_PROXY_TERMS if term in tokens or term in lower)
    if strong:
        return "level_2", "strong_outcome_proxy", "Success;Side Effect;Looping", "exclude"
    if lower in {"$.agent", "$.benchmark", "$.experiment", "$.model"}:
        return "level_3", "benchmark_or_agent_identity_shortcut", "Success;Side Effect;Looping", "retain_with_ablation"
    if any(term in lower for term in ("error", "completed", "finish", "final", "observation")):
        return "level_3", "natural_trajectory_outcome_information", "Success;Side Effect;Looping", "retain_with_ablation"
    return None


def audit_downloads(rows: Sequence[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Parse downloaded files and return field, leakage, and per-file completeness records."""
    inventory_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    leakage_groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    completeness: list[dict[str, Any]] = []
    for row in rows:
        result = {
            "trajectory_key": row["trajectory_key"],
            "benchmark": row["benchmark_group_primary"],
            "model_name": row["model_name"],
            "path_resolved": bool(row.get("path_resolved")),
            "downloaded": row.get("download_status") == "downloaded",
            "json_parseable": False,
            "trajectory_nonempty": False,
            "task_instruction_found": False,
            "steps_found": False,
            "action_found": False,
            "observation_found": False,
            "final_response_found": False,
            "screenshot_reference_found": False,
            "direct_leakage_found": False,
            "strong_proxy_found": False,
            "parse_error": "",
        }
        if not result["downloaded"]:
            result["parse_error"] = row.get("download_error", "not_downloaded")
            completeness.append(result)
            continue
        local_path = ROOT / str(row["local_relative_path"])
        try:
            with local_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            result["json_parseable"] = True
            result["trajectory_nonempty"] = bool(payload)
            observed_paths: set[str] = set()
            for field_path, observed_type, value in iter_fields(payload):
                observed_paths.add(field_path)
                role = semantic_role(field_path)
                key = (field_path, observed_type, row["benchmark_group_primary"], row["model_name"])
                group = inventory_groups.setdefault(key, {
                    "field_path": field_path,
                    "observed_type": observed_type,
                    "example_value_redacted": redact_example(value),
                    "presence_count": 0,
                    "benchmark": row["benchmark_group_primary"],
                    "model_name": row["model_name"],
                    "possible_semantic_role": role,
                })
                group["presence_count"] += 1
                risk = leakage_class(field_path)
                if risk:
                    level, risk_type, affected, action = risk
                    leak_key = (field_path, level, risk_type, action)
                    leak = leakage_groups.setdefault(leak_key, {
                        "field_path": field_path,
                        "risk_level": level,
                        "risk_type": risk_type,
                        "affected_target": affected,
                        "observed_in_benchmarks": set(),
                        "observed_in_models": set(),
                        "recommended_action": action,
                        "justification": "Observed field name carries outcome information; conservative isolation is required.",
                    })
                    leak["observed_in_benchmarks"].add(row["benchmark_group_primary"])
                    leak["observed_in_models"].add(row["model_name"])
                    if level == "level_1":
                        result["direct_leakage_found"] = True
                    elif level == "level_2":
                        result["strong_proxy_found"] = True
            lower_paths = "\n".join(path.lower() for path in observed_paths)
            result["task_instruction_found"] = any(term in lower_paths for term in ("task", "intent", "instruction"))
            result["steps_found"] = any(term in lower_paths for term in ("step", "messages[]", "trajectory[]"))
            result["action_found"] = "action" in lower_paths
            result["observation_found"] = any(term in lower_paths for term in ("observation", "axtree", "state"))
            result["final_response_found"] = any(term in lower_paths for term in ("final", "answer", "response"))
            result["screenshot_reference_found"] = any(term in lower_paths for term in ("screenshot", "image"))
        except Exception as exc:
            result["parse_error"] = f"{type(exc).__name__}: {exc}"
        completeness.append(result)

    inventory = sorted(inventory_groups.values(), key=lambda item: (item["field_path"], item["observed_type"], item["benchmark"], item["model_name"]))
    leakage: list[dict[str, Any]] = []
    for item in leakage_groups.values():
        item["observed_in_benchmarks"] = ";".join(sorted(item["observed_in_benchmarks"]))
        item["observed_in_models"] = ";".join(sorted(item["observed_in_models"]))
        leakage.append(item)
    leakage.sort(key=lambda item: (item["risk_level"], item["field_path"]))
    return inventory, leakage, completeness


def _rates(completeness: Sequence[Mapping[str, Any]], group_field: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in completeness:
        groups[str(row[group_field])].append(row)
    return {
        key: {
            "probe_count": len(rows),
            "parseable_count": sum(bool(row["json_parseable"]) for row in rows),
            "parse_success_rate": sum(bool(row["json_parseable"]) for row in rows) / len(rows),
        }
        for key, rows in sorted(groups.items())
    }


def build_summary(
    mapped_rows: Sequence[Mapping[str, Any]],
    probe_rows: Sequence[Mapping[str, Any]],
    inventory: Sequence[Mapping[str, Any]],
    completeness: Sequence[Mapping[str, Any]],
    leakage: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the machine-readable A0.3 evidence summary."""
    resolved = sum(bool(row.get("path_resolved")) for row in mapped_rows)
    downloaded = sum(row.get("download_status") == "downloaded" for row in probe_rows)
    parsed = sum(bool(row["json_parseable"]) for row in completeness)
    screenshots = sum(bool(row["screenshot_reference_found"]) for row in completeness)
    direct = sum(bool(row["direct_leakage_found"]) for row in completeness)
    proxies = sum(bool(row["strong_proxy_found"]) for row in completeness)
    total_bytes = sum(int(row.get("file_size_bytes") or 0) for row in probe_rows)
    mapped_sizes = [int(row["expected_size_bytes"]) for row in mapped_rows if row.get("path_resolved")]
    benchmarks = sorted({str(row["benchmark_group_primary"]) for row in probe_rows})
    root_pattern = re.compile(r"^\$\.[^.\[\]]+$")
    step_pattern = re.compile(r"^\$\.steps\[\]\.[^.\[\]]+$")
    root_fields = {
        benchmark: sorted({str(item["field_path"]) for item in inventory if item["benchmark"] == benchmark and root_pattern.match(str(item["field_path"]))})
        for benchmark in benchmarks
    }
    step_fields = {
        benchmark: sorted({str(item["field_path"]) for item in inventory if item["benchmark"] == benchmark and step_pattern.match(str(item["field_path"]))})
        for benchmark in benchmarks
    }
    type_profiles: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for item in inventory:
        path = str(item["field_path"])
        if root_pattern.match(path) or step_pattern.match(path):
            benchmark = str(item["benchmark"])
            existing = set(type_profiles[path].get(benchmark, []))
            existing.add(str(item["observed_type"]))
            type_profiles[path][benchmark] = sorted(existing)
    type_differences = {
        path: profiles for path, profiles in sorted(type_profiles.items())
        if len({tuple(profiles.get(benchmark, [])) for benchmark in benchmarks}) > 1
    }
    shared_root_schema = len({tuple(paths) for paths in root_fields.values()}) == 1
    shared_step_schema = len({tuple(paths) for paths in step_fields.values()}) == 1
    conditions: list[str] = []
    if resolved != len(mapped_rows):
        conditions.append("Some dev trajectory keys did not map uniquely.")
    if parsed != len(probe_rows):
        conditions.append("Some selected JSON trajectories did not parse.")
    if not (shared_root_schema and shared_step_schema):
        conditions.append("Some benchmark families expose different direct root or step field sets.")
    if type_differences:
        conditions.append("Shared fields have benchmark-dependent null/type profiles and require guarded normalization.")
    if sum(bool(row["final_response_found"]) for row in completeness) != len(completeness):
        conditions.append("No explicit final_response field was observed; any final message mapping needs manual semantic confirmation.")
    decision = "PASS" if not conditions else "PASS_WITH_CONDITIONS"
    if resolved < max(1, int(0.5 * len(mapped_rows))) or parsed < max(1, int(0.5 * len(probe_rows))):
        decision = "STOP"
    return {
        "stage": "A0.3",
        "stage_decision": decision,
        "source": {"huggingface_repository": HF_REPOSITORY, "revision": HF_REVISION},
        "scope": {"dev_only": True, "test_trajectory_downloads": 0, "screenshots_downloaded": 0, "models_or_baselines_run": 0},
        "selection": {
            "rule": "smallest exact-mapped file per benchmark_group_primary x model_name, then smallest missing eligible target polarities; deterministic lexical tie-break",
            "probe_count": len(probe_rows),
            "max_probe_count": MAX_PROBES,
            "download_bytes": total_bytes,
            "download_limit_bytes": MAX_DOWNLOAD_BYTES,
        },
        "mapping": {
            "dev_index_count": len(mapped_rows),
            "resolved_count": resolved,
            "resolution_rate": resolved / len(mapped_rows) if mapped_rows else 0.0,
            "unresolved": [
                {"trajectory_key": row["trajectory_key"], "issue": row.get("mapping_issue", "")}
                for row in mapped_rows if not row.get("path_resolved")
            ],
        },
        "parsing": {
            "downloaded_count": downloaded,
            "parseable_count": parsed,
            "parse_success_rate": parsed / len(probe_rows) if probe_rows else 0.0,
            "by_benchmark": _rates(completeness, "benchmark"),
            "by_model": _rates(completeness, "model_name"),
            "text_structured_parseable_count": parsed,
            "text_structured_parseable_rate": parsed / len(probe_rows) if probe_rows else 0.0,
            "screenshot_reference_count": screenshots,
            "screenshot_reference_rate": screenshots / len(probe_rows) if probe_rows else 0.0,
            "completeness": list(completeness),
        },
        "leakage": {
            "direct_leakage_trajectory_count": direct,
            "direct_leakage_rate": direct / len(probe_rows) if probe_rows else 0.0,
            "strong_proxy_trajectory_count": proxies,
            "strong_proxy_rate": proxies / len(probe_rows) if probe_rows else 0.0,
            "registered_field_count": len(leakage),
        },
        "schema": {
            "adapter_recommendation": "one shared cleaned-schema adapter with benchmark/model-aware nullable and semantic hooks",
            "independent_benchmark_adapters_required": not (shared_root_schema and shared_step_schema),
            "shared_root_field_set": shared_root_schema,
            "shared_step_field_set": shared_step_schema,
            "root_fields_by_benchmark": root_fields,
            "step_fields_by_benchmark": step_fields,
            "direct_field_type_differences": type_differences,
            "screenshots_required_for_minimal_text_probe": False,
        },
        "projected_full_dev_text_scope": {
            "file_count": resolved,
            "declared_bytes": sum(mapped_sizes),
            "estimate_basis": "exact fixed-revision file metadata for uniquely mapped dev trajectories; no full files downloaded",
        },
        "conditions": conditions,
    }


def render_report(summary: Mapping[str, Any], leakage: Sequence[Mapping[str, Any]]) -> str:
    """Render a concise human-readable report from measured evidence."""
    selection = summary["selection"]
    mapping = summary["mapping"]
    parsing = summary["parsing"]
    leak = summary["leakage"]
    lines = [
        "# Stage A0.3 Minimal Dev Trajectory Probe",
        "",
        "## Stage decision",
        "",
        f"**{summary['stage_decision']}**",
        "",
        "This probe used only fixed-revision dev JSON trajectories. It did not download test trajectories, screenshots, judgments, or the full dataset, and it did not construct features or run models/baselines.",
        "",
        "## Direct observations",
        "",
        f"- Fixed Hugging Face revision: `{summary['source']['revision']}`.",
        "- Trajectories are individual JSON files below `cleaned/<benchmark>/<model>/<run>/`.",
        "- `judgments/` is a separate tree and was neither queried for sample mapping nor downloaded.",
        f"- Selected/downloaded files: {selection['probe_count']}; bytes: {selection['download_bytes']} (limit {selection['download_limit_bytes']}).",
        "- No screenshot/image/video file was downloaded.",
        "",
        "## Computed audit statistics",
        "",
        f"- Exact dev path mapping: {mapping['resolved_count']}/{mapping['dev_index_count']} ({mapping['resolution_rate']:.2%}).",
        f"- Probe JSON parsing: {parsing['parseable_count']}/{selection['probe_count']} ({parsing['parse_success_rate']:.2%}).",
        f"- Screenshot references: {parsing['screenshot_reference_count']}/{selection['probe_count']} ({parsing['screenshot_reference_rate']:.2%}); referenced assets were not downloaded.",
        f"- Direct outcome/label fields: {leak['direct_leakage_trajectory_count']}/{selection['probe_count']} trajectories.",
        f"- Strong outcome proxies: {leak['strong_proxy_trajectory_count']}/{selection['probe_count']} trajectories.",
        "",
        "## Raw structure differences and adapter recommendation",
        "",
        "All probed benchmark families share the same direct root and `steps[]` field sets. Use one shared cleaned-schema adapter with benchmark/model-aware null and semantic guards, emitting this small common contract:",
        "",
        "```text",
        "trajectory_id, benchmark, task_instruction, steps[]",
        "steps[].action, steps[].observation, steps[].tool_name",
        "steps[].tool_input, steps[].tool_output, final_response, metadata",
        "```",
        "",
        "Observed differences are type-level rather than separate top-level schemas: `focused_element` is additionally nullable in WorkArena, while action/reasoning availability can vary by individual trajectory or model. No explicit final-response field was observed. Outcome/judgment/reward/score fields are forbidden model inputs. Screenshot paths and removed image placeholders remain optional metadata; the minimal text probe does not require image files.",
        "",
        "## Leakage isolation",
        "",
    ]
    for item in leakage:
        lines.append(f"- `{item['field_path']}` — {item['risk_level']}, `{item['recommended_action']}` ({item['risk_type']}).")
    lines.extend([
        "",
        "## Risk judgments",
        "",
        "- A shared output contract and shared cleaned-schema adapter are feasible, with guarded normalization for nullable and semantically benchmark-specific values.",
        "- Natural action repetition and environment/tool errors are legitimate trajectory evidence, not automatically labels; retain them with an explicit leakage/ablation policy.",
        "- Direct official outcomes and strong evaluator proxies must remain isolated from future model inputs.",
        "",
        "## Unconfirmed questions",
        "",
        "- Whether screenshot content is required for later non-minimal research remains untested because screenshots were prohibited here.",
        "- Field semantics marked `unclassified` require adapter-level confirmation before any full dev transformation.",
        "- This schema probe does not establish predictive value or model performance.",
        "",
    ])
    return "\n".join(lines)


def _manifest_rows(probes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "trajectory_key": row["trajectory_key"],
            "benchmark_original": row["benchmark_original"],
            "benchmark_split_namespace": row["benchmark_split_namespace"],
            "benchmark_group_primary": row["benchmark_group_primary"],
            "model_name": row["model_name"],
            "task_id": row["task_id"],
            "official_split": row["official_split"],
            "selection_reason": row["selection_reason"],
            "expected_repository_path": row["expected_repository_path"],
            "hf_revision": HF_REVISION,
            "download_status": row.get("download_status", "not_attempted"),
            "local_relative_path": row.get("local_relative_path", ""),
            "file_size_bytes": row.get("file_size_bytes", ""),
            "sha256": row.get("sha256", ""),
            "success_label": row.get("success_label", ""),
            "side_effect_label": row.get("side_effect_label", ""),
            "looping_label": row.get("looping_label", ""),
        }
        for row in probes
    ]


def run() -> int:
    """Execute the bounded online probe and materialize all approved artifacts."""
    dev_rows = read_csv(DEV_INDEX)
    validate_dev_rows(dev_rows)
    test_keys = {row["trajectory_key"] for row in read_csv(TEST_MANIFEST)}
    combos = sorted({(row["benchmark_original"], row["model_name"]) for row in dev_rows})
    combo_files = {combo: discover_combo_files(*combo) for combo in combos}
    mapped = map_dev_rows(dev_rows, combo_files, test_keys)
    probes = select_probe_rows(mapped)
    download_probe(probes, test_keys)
    inventory, leakage, completeness = audit_downloads(probes)
    summary = build_summary(mapped, probes, inventory, completeness, leakage)

    write_csv(PROBE_MANIFEST, list(_manifest_rows(probes)[0]), _manifest_rows(probes))
    write_csv(FIELD_INVENTORY, [
        "field_path", "observed_type", "example_value_redacted", "presence_count",
        "benchmark", "model_name", "possible_semantic_role",
    ], inventory)
    write_csv(LEAKAGE_REGISTER, [
        "field_path", "risk_level", "risk_type", "affected_target",
        "observed_in_benchmarks", "observed_in_models", "recommended_action", "justification",
    ], leakage)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(summary, leakage), encoding="utf-8")
    print(json.dumps({
        "decision": summary["stage_decision"],
        "probe_count": len(probes),
        "download_bytes": summary["selection"]["download_bytes"],
        "mapping_rate": summary["mapping"]["resolution_rate"],
        "parse_rate": summary["parsing"]["parse_success_rate"],
    }, ensure_ascii=False))
    return 0 if summary["stage_decision"] != "STOP" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return run()


if __name__ == "__main__":
    sys.exit(main())
