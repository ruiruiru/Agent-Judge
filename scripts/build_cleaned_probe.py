"""Build the Stage A0.4 leak-safe compact representations from 16 local dev probes."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROBE_MANIFEST = ROOT / "artifacts" / "dev_probe_manifest.csv"
DEV_INDEX = ROOT / "artifacts" / "dev_analysis_index.csv"
TEST_MANIFEST = ROOT / "artifacts" / "test_manifest.csv"
FIELD_INVENTORY = ROOT / "artifacts" / "trajectory_field_inventory.csv"
PROBE_SUMMARY = ROOT / "artifacts" / "trajectory_probe_summary.json"
FIELD_POLICY = ROOT / "artifacts" / "input_field_policy.csv"
CLEANED_JSONL = ROOT / "artifacts" / "probe_cleaned_trajectories.jsonl"
SERIALIZED_JSONL = ROOT / "artifacts" / "probe_serialized_inputs.jsonl"
SUMMARY_PATH = ROOT / "artifacts" / "input_contract_summary.json"
REPORT_PATH = ROOT / "docs" / "input_contract.md"
SOURCE_REVISION = "b6d17e646009d6cb63d5dd7be78807b680693f61"

INPUT_VIEWS = (
    "primary_with_natural_errors",
    "ablation_without_error_fields",
    "sensitivity_with_reasoning",
)
TERMINATION_ACTIONS = {"send_msg_to_user", "report_infeasible"}
PERMANENT_SEMANTIC_TERMS = {
    "reward", "raw_reward", "score", "success", "successful", "passed",
    "failure", "side_effect", "looping", "repetitiveness", "annotation",
    "human_judgment", "judge_result", "ground_truth", "label",
}
IDENTITY_ROOTS = {
    "$.agent", "$.benchmark", "$.experiment", "$.model", "$.model_args",
    "$.package_version", "$.seed", "$.valid", "$.flags",
}
PRIMARY_PATHS = {
    "$.goal", "$.steps", "$.steps[]", "$.steps[].action",
    "$.steps[].axtree_pruned", "$.steps[].focused_element",
    "$.steps[].last_action_error",
}
SENSITIVITY_PATHS = {"$.steps[].reasoning"}
METADATA_PATHS = {
    "$.steps[].num", "$.steps[].open_pages_urls", "$.steps[].stats",
    "$.steps[].url",
}


@dataclass(frozen=True)
class ProbeSource:
    """Label-free source metadata passed to the input builder."""

    trajectory_key: str
    benchmark_original: str
    benchmark_group_primary: str
    benchmark_group_secondary: str
    model_name: str
    task_id: str
    official_split: str
    source_revision: str
    source_path: str
    local_relative_path: str
    source_size_bytes: int
    source_sha256: str


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV fully."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    """Hash a file without modifying it."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_sources() -> list[ProbeSource]:
    """Load exactly the approved 16 dev probes while dropping manifest labels."""
    manifest = read_csv(PROBE_MANIFEST)
    dev_keys = {row["trajectory_key"] for row in read_csv(DEV_INDEX)}
    test_keys = {row["trajectory_key"] for row in read_csv(TEST_MANIFEST)}
    sources: list[ProbeSource] = []
    for row in manifest:
        source = ProbeSource(
            trajectory_key=row["trajectory_key"],
            benchmark_original=row["benchmark_original"],
            benchmark_group_primary=row["benchmark_group_primary"],
            benchmark_group_secondary=row["benchmark_split_namespace"],
            model_name=row["model_name"],
            task_id=row["task_id"],
            official_split=row["official_split"],
            source_revision=row["hf_revision"],
            source_path=row["expected_repository_path"],
            local_relative_path=row["local_relative_path"],
            source_size_bytes=int(row["file_size_bytes"]),
            source_sha256=row["sha256"],
        )
        if source.official_split != "dev" or source.trajectory_key not in dev_keys:
            raise PermissionError("A0.4 accepts only existing dev probe keys")
        if source.trajectory_key in test_keys:
            raise PermissionError("A0.4 refuses every sealed test trajectory")
        if source.source_revision != SOURCE_REVISION:
            raise ValueError("probe source revision changed")
        local_path = ROOT / source.local_relative_path
        if not local_path.is_file():
            raise FileNotFoundError(local_path)
        if local_path.stat().st_size != source.source_size_bytes:
            raise ValueError(f"source size mismatch: {source.trajectory_key}")
        if sha256_file(local_path) != source.source_sha256:
            raise ValueError(f"source hash mismatch: {source.trajectory_key}")
        sources.append(source)
    if len(sources) != 16 or len({source.trajectory_key for source in sources}) != 16:
        raise ValueError("A0.4 requires exactly 16 unique existing probes")
    return sorted(sources, key=lambda source: source.trajectory_key)


def canonical_field_key(key: Any) -> str:
    """Match the stable field-path normalization frozen in A0.3."""
    text = str(key)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,63}", text):
        return text
    return "{*}"


def iter_fields(value: Any, path: str = "$") -> Iterator[tuple[str, str, Any]]:
    """Enumerate recursively using A0.3 list and dynamic-map normalization."""
    observed_type = "null" if value is None else type(value).__name__
    yield path, observed_type, value
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            child = "{*}" if path.endswith((".bounding_boxes", ".extra_element_properties")) else canonical_field_key(key)
            yield from iter_fields(value[key], f"{path}.{child}")
    elif isinstance(value, list):
        for item in value:
            yield from iter_fields(item, f"{path}[]")


def _matches_prefix(path: str, prefixes: set[str]) -> bool:
    return any(path == prefix or path.startswith(prefix + ".") or path.startswith(prefix + "[]") for prefix in prefixes)


def classify_field(path: str) -> tuple[str, bool, bool, bool, str, str]:
    """Classify one observed raw path under the whitelist-first contract."""
    lower = path.lower()
    tokens = set(re.findall(r"[a-z0-9_]+", lower))
    if path.startswith("$.summary_info") or tokens.intersection(PERMANENT_SEMANTIC_TERMS):
        return "permanent_exclude", False, False, False, "Official outcome/summary semantics are outside every input view.", "May reveal labels, rewards, scores, or evaluator output."
    if any(term in lower for term in ("screenshot", "image_url", "base64")):
        return "permanent_exclude", False, False, False, "Image content, placeholders, and paths are prohibited in the text contract.", "Only a derived boolean reference flag is retained."
    if _matches_prefix(path, IDENTITY_ROOTS) or _matches_prefix(path, METADATA_PATHS):
        return "metadata_only", False, False, False, "Retained only for provenance, grouping, or audit.", "Identity/format shortcut risk; never serialize into main input."
    if path in SENSITIVITY_PATHS or path.startswith("$.steps[].reasoning."):
        return "sensitivity_only", False, False, True, "Reasoning is excluded from primary input and retained only in its named sensitivity view.", "Availability and style can reveal model identity."
    if path in PRIMARY_PATHS:
        is_error = path == "$.steps[].last_action_error"
        return (
            "primary_input", True, not is_error, True,
            "Explicitly allowlisted task/action/observation/focus/natural-error field.",
            "Natural error text requires the frozen ablation; no official outcome fields are admitted.",
        )
    return "manual_review", False, False, False, "Observed in A0.3 but not approved for any input view.", "Unknown or unnecessary semantics default to rejection."


def build_field_policy(inventory_rows: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    """Create one deterministic policy row per observed field path and type."""
    pairs = sorted({(row["field_path"], row["observed_type"]) for row in inventory_rows})
    output: list[dict[str, Any]] = []
    for path, observed_type in pairs:
        policy, primary, ablation, reasoning, justification, risk = classify_field(path)
        output.append({
            "field_path": path,
            "observed_type": observed_type,
            "policy_class": policy,
            "included_in_primary": str(primary).lower(),
            "included_in_error_ablation": str(ablation).lower(),
            "included_in_reasoning_sensitivity": str(reasoning).lower(),
            "justification": justification,
            "risk_notes": risk,
        })
    return output


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _termination_signal(last_action: str | None) -> str | None:
    if not last_action:
        return None
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\(", last_action)
    if match and match.group(1) in TERMINATION_ACTIONS:
        return match.group(1)
    return None


def _has_screenshot_reference(raw: Mapping[str, Any]) -> bool:
    for path, _observed_type, value in iter_fields(raw):
        if any(term in path.lower() for term in ("screenshot", "image_url")):
            if value not in (None, "", False, "REMOVED"):
                return True
    return False


def build_cleaned_trajectory(
    raw_trajectory: Mapping[str, Any],
    source: ProbeSource,
    known_field_types: set[tuple[str, str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Apply the frozen whitelist; this interface accepts no labels."""
    if source.official_split != "dev":
        raise PermissionError("cleaned builder refuses non-dev input")
    observed = list(iter_fields(raw_trajectory))
    unknown: list[dict[str, Any]] = []
    for path, observed_type, value in observed:
        if (path, observed_type) not in known_field_types:
            example = str(value).replace("\n", " ").replace("\r", " ")[:80]
            unknown.append({"field_path": path, "observed_type": observed_type, "example_value_redacted": example})

    raw_steps = raw_trajectory.get("steps")
    if not isinstance(raw_steps, list):
        raw_steps = []
    steps: list[dict[str, Any]] = []
    for index, raw_step in enumerate(raw_steps, start=1):
        if not isinstance(raw_step, Mapping):
            raw_step = {}
        steps.append({
            "step_index": index,
            "action": _text(raw_step.get("action")),
            "observation": _text(raw_step.get("axtree_pruned")),
            "tool_name": None,
            "tool_input": None,
            "tool_output": None,
            "focused_element": _text(raw_step.get("focused_element")),
            "error": _text(raw_step.get("last_action_error")),
            "reasoning": _text(raw_step.get("reasoning")),
        })

    action_steps = [step for step in steps if step["action"]]
    observation_steps = [step for step in steps if step["observation"]]
    last_action = action_steps[-1]["action"] if action_steps else None
    last_observation = observation_steps[-1]["observation"] if observation_steps else None
    terminal_indexes = [step["step_index"] for step in action_steps[-1:] + observation_steps[-1:]]
    terminal = {
        "last_nonempty_action": last_action,
        "last_nonempty_observation": last_observation,
        "last_step_index": max(terminal_indexes) if terminal_indexes else None,
        "termination_signal": _termination_signal(last_action),
    }
    quality_flags = {
        "has_task_instruction": bool(_text(raw_trajectory.get("goal"))),
        "has_steps": bool(steps),
        "has_action": bool(action_steps),
        "has_observation": bool(observation_steps),
        "has_reasoning": any(step["reasoning"] for step in steps),
        "has_natural_error": any(step["error"] for step in steps),
        "has_screenshot_reference": _has_screenshot_reference(raw_trajectory),
        "has_terminal_action": bool(last_action),
        "has_terminal_observation": bool(last_observation),
        "unknown_fields_present": bool(unknown),
    }
    cleaned = {
        "trajectory_key": source.trajectory_key,
        "metadata": {
            "benchmark_group_primary": source.benchmark_group_primary,
            "benchmark_group_secondary": source.benchmark_group_secondary,
            "model_name": source.model_name,
            "task_id": source.task_id,
            "official_split": source.official_split,
            "source_revision": source.source_revision,
            "source_path": source.source_path,
            "source_sha256": source.source_sha256,
        },
        "task": {"instruction": _text(raw_trajectory.get("goal")), "context": None},
        "steps": steps,
        "terminal": terminal,
        "quality_flags": quality_flags,
    }
    return cleaned, unknown


def serialize_input(cleaned_trajectory: Mapping[str, Any], input_view: str) -> str:
    """Serialize one of exactly three views using the same explicit whitelist."""
    if input_view not in INPUT_VIEWS:
        raise ValueError(f"unapproved input view: {input_view}")
    include_error = input_view != "ablation_without_error_fields"
    include_reasoning = input_view == "sensitivity_with_reasoning"
    lines: list[str] = []
    instruction = cleaned_trajectory["task"].get("instruction")
    if instruction:
        lines.extend(["[TASK]", instruction])
    for step in cleaned_trajectory["steps"]:
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
    terminal = cleaned_trajectory["terminal"]
    terminal_fields = [
        ("LAST_ACTION", terminal.get("last_nonempty_action")),
        ("LAST_OBSERVATION", terminal.get("last_nonempty_observation")),
        ("LAST_STEP_INDEX", terminal.get("last_step_index")),
        ("TERMINATION_SIGNAL", terminal.get("termination_signal")),
    ]
    nonempty_terminal = [(name, value) for name, value in terminal_fields if value not in (None, "")]
    if nonempty_terminal:
        lines.append("[TERMINAL]")
        for name, value in nonempty_terminal:
            lines.extend([f"{name}:", str(value)])
    return "\n".join(lines) + "\n"


def assert_view_isolation(
    text: str,
    source: ProbeSource,
    input_view: str,
    extra_identity_values: Iterable[str] = (),
) -> None:
    """Reject structural leakage, identity serialization, paths, and view mixing."""
    lower = text.lower()
    forbidden_markers = (
        "cum_reward", "cum_raw_reward", "summary_info", "success_label",
        "side_effect_label", "looping_label", "eligible_main", "annotation_status",
        "screenshots/", "image_url", source.source_path.lower(),
        source.task_id.lower(), source.trajectory_key.lower(),
    )
    for marker in forbidden_markers:
        if marker and marker in lower:
            raise ValueError(f"forbidden marker in {input_view}: {marker}")
    identities = {
        source.benchmark_original, source.benchmark_group_primary,
        source.benchmark_group_secondary, source.model_name,
    }
    identities.update(value for value in extra_identity_values if value)
    for identity in identities:
        if identity and identity.lower() in lower:
            raise ValueError(f"identity value leaked into {input_view}: {identity}")
    if input_view != "sensitivity_with_reasoning" and "REASONING:" in text:
        raise ValueError("reasoning leaked into a primary view")
    if input_view == "ablation_without_error_fields" and "ERROR:" in text:
        raise ValueError("explicit natural-error field survived ablation")


def _json_line(record: Mapping[str, Any]) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_bytes(path: Path, chunks: Iterable[bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        for chunk in chunks:
            handle.write(chunk)


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def _field_character_counts(cleaned: Mapping[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    instruction = cleaned["task"].get("instruction")
    if instruction:
        counts["task_instruction"] += len(instruction)
    for step in cleaned["steps"]:
        for output_name, field_name in (
            ("action", "action"), ("observation", "observation"),
            ("focused_element", "focused_element"), ("natural_error", "error"),
            ("reasoning", "reasoning"),
        ):
            value = step.get(field_name)
            if value:
                counts[output_name] += len(value)
    terminal = cleaned["terminal"]
    for name in ("last_nonempty_action", "last_nonempty_observation", "termination_signal"):
        value = terminal.get(name)
        if value:
            counts[f"terminal_{name}"] += len(str(value))
    return counts


def recursive_size_estimate(value: Any, seen: set[int] | None = None) -> int:
    """Estimate in-memory JSON object size deterministically via recursive getsizeof."""
    if seen is None:
        seen = set()
    object_id = id(value)
    if object_id in seen:
        return 0
    seen.add(object_id)
    size = sys.getsizeof(value)
    if isinstance(value, dict):
        size += sum(recursive_size_estimate(key, seen) + recursive_size_estimate(item, seen) for key, item in value.items())
    elif isinstance(value, (list, tuple, set)):
        size += sum(recursive_size_estimate(item, seen) for item in value)
    return size


def render_report(summary: Mapping[str, Any]) -> str:
    """Render the frozen contract and measured probe evidence."""
    volume = summary["volume"]
    stats = summary["probe_statistics"]
    projected = summary["projected_full_dev"]
    lines = [
        "# Stage A0.4 Leak-Safe Trajectory Input Contract",
        "",
        "## Stage decision",
        "",
        f"**{summary['stage_decision']}**",
        "",
        "This contract was derived only from the 16 existing dev probe JSON files. No network access, new trajectory download, feature extraction, model call, training, baseline, or predictive metric was used.",
        "",
        "## Frozen whitelist",
        "",
        "Primary input admits only:",
        "",
        "- `goal` → `task.instruction`;",
        "- `steps[].action` → `steps[].action`;",
        "- `steps[].axtree_pruned` → `steps[].observation`;",
        "- `steps[].focused_element` → `steps[].focused_element`;",
        "- `steps[].last_action_error` → `steps[].error` in the primary/error-preserving views.",
        "",
        "`steps[].reasoning` is sensitivity-only. Missing values remain null and are never imputed. Tool fields and task context remain null because no separate approved raw source field exists.",
        "",
        "## Permanent exclusions",
        "",
        "- The complete `summary_info` subtree, including `cum_reward` and `cum_raw_reward`;",
        "- every field with official reward/score/label/judge/annotation semantics;",
        "- screenshot paths, image placeholders, image payloads, and base64 content;",
        "- any future unknown field until explicitly reviewed and approved.",
        "",
        "Excluded fields cannot affect step retention, truncation, ordering, selection, missing-value handling, structure features, or text.",
        "",
        "## Identity, reasoning, and natural errors",
        "",
        "Benchmark, task, agent, model, experiment, split, repository path, and trajectory key are management metadata only. They do not appear inside any serialized view. Reasoning is excluded from both primary views and appears only when the raw step contains it in `sensitivity_with_reasoning`.",
        "",
        "Natural tool/environment errors from `last_action_error` remain in `primary_with_natural_errors` and `sensitivity_with_reasoning`; `ablation_without_error_fields` removes that explicit field without deleting a step or rewriting observation text.",
        "",
        "## Shared cleaned schema and terminal mapping",
        "",
        "```text",
        "trajectory_key",
        "metadata (management only)",
        "task {instruction, context}",
        "steps[] {step_index, action, observation, tool_name, tool_input, tool_output, focused_element, error, reasoning}",
        "terminal {last_nonempty_action, last_nonempty_observation, last_step_index, termination_signal}",
        "quality_flags",
        "```",
        "",
        "Terminal action and observation are exact copies of the last nonempty allowlisted raw fields. `termination_signal` records only the literal action name `send_msg_to_user` or `report_infeasible`; it is null otherwise. It never represents inferred success or failure, and no `final_response` field is invented.",
        "",
        "## Three frozen serialized views",
        "",
        "1. `primary_with_natural_errors`: task, actions, pruned observations, focused elements, natural error fields, and terminal evidence; no reasoning.",
        "2. `ablation_without_error_fields`: the same contract with explicit natural error fields removed; no reasoning.",
        "3. `sensitivity_with_reasoning`: the primary view plus raw reasoning where present.",
        "",
        "All omit empty fields and preserve original step order. Structured JSON and text share the same source whitelist.",
        "",
        "## Measured probe statistics",
        "",
        f"- Raw: {volume['raw_bytes']:,} bytes across {stats['trajectory_count']} files.",
        f"- Compact structured JSONL: {volume['cleaned_jsonl_bytes']:,} bytes ({volume['cleaned_to_raw_ratio']:.4%} of raw).",
        f"- Serialized JSONL container: {volume['serialized_jsonl_bytes']:,} bytes.",
        f"- View text bytes: primary {volume['view_text_bytes']['primary_with_natural_errors']:,}; error ablation {volume['view_text_bytes']['ablation_without_error_fields']:,}; reasoning sensitivity {volume['view_text_bytes']['sensitivity_with_reasoning']:,}.",
        f"- Steps: {stats['step_count']}; empty actions: {stats['empty_action_count']}; empty observations: {stats['empty_observation_count']}.",
        f"- Reasoning trajectory availability: {stats['reasoning_trajectory_rate']:.2%}; natural-error trajectory availability: {stats['natural_error_trajectory_rate']:.2%}; screenshot-reference rate: {stats['screenshot_reference_rate']:.2%}.",
        f"- Explicit terminal signal coverage: {stats['termination_signal_rate']:.2%}; no signal is inferred for the remainder.",
        f"- Average parsed-object memory estimate: {stats['average_parse_memory_estimate_bytes']:,.0f} bytes; maximum: {stats['max_parse_memory_estimate_bytes']:,} bytes.",
        f"- New fields relative to A0.3 inventory: {summary['unknown_fields']['count']}.",
        "",
        "## Full-dev streaming plan (not executed)",
        "",
        f"The fixed tree estimates 196 dev JSON files and {projected['raw_bytes']:,} raw bytes. Probe ratios project approximately {projected['cleaned_jsonl_bytes']:,} compact structured bytes. Projected view text bytes are recorded in the machine-readable summary.",
        "",
        "Use a dev-key allowlist and fixed revision, then process one file at a time: download to a `.part` cache, verify size/SHA256, parse, whitelist, write one compact record, and release or move the verified raw file to a recoverable cache. Resume from a manifest only after rechecking hashes. The full 3.65 GB need not be committed or permanently retained locally, but revision, path, size, and hash records must be permanent. Test keys are rejected before path resolution or file access.",
        "",
        "## Conditions and unresolved semantics",
        "",
    ]
    for condition in summary["conditions"]:
        lines.append(f"- {condition}")
    lines.extend(["", "No model-readiness or performance conclusion is made in this stage.", ""])
    return "\n".join(lines)


def run() -> int:
    """Generate every A0.4 artifact locally and deterministically."""
    sources = load_sources()
    inventory_rows = read_csv(FIELD_INVENTORY)
    known_field_types = {(row["field_path"], row["observed_type"]) for row in inventory_rows}
    field_policy = build_field_policy(inventory_rows)
    cleaned_records: list[dict[str, Any]] = []
    serialized_records: list[dict[str, Any]] = []
    trajectory_stats: list[dict[str, Any]] = []
    unknown_counter: Counter[tuple[str, str, str]] = Counter()
    character_totals: Counter[str] = Counter()
    view_bytes: Counter[str] = Counter()
    memory_estimates: list[int] = []

    for source in sources:
        with (ROOT / source.local_relative_path).open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        memory_estimate = recursive_size_estimate(raw)
        memory_estimates.append(memory_estimate)
        cleaned, unknown = build_cleaned_trajectory(raw, source, known_field_types)
        for item in unknown:
            unknown_counter[(item["field_path"], item["observed_type"], item["example_value_redacted"])] += 1
        views = {view: serialize_input(cleaned, view) for view in INPUT_VIEWS}
        raw_identities = [
            str(raw.get(name)) for name in ("agent", "benchmark", "experiment", "model")
            if raw.get(name) not in (None, "")
        ]
        for view, text in views.items():
            assert_view_isolation(text, source, view, raw_identities)
            view_bytes[view] += len(text.encode("utf-8"))
        cleaned_records.append(cleaned)
        serialized_records.append({"trajectory_key": source.trajectory_key, "views": views})
        character_totals.update(_field_character_counts(cleaned))
        cleaned_line_bytes = len(_json_line(cleaned))
        trajectory_stats.append({
            "trajectory_key": source.trajectory_key,
            "raw_bytes": source.source_size_bytes,
            "cleaned_jsonl_bytes": cleaned_line_bytes,
            "view_text_bytes": {view: len(text.encode("utf-8")) for view, text in views.items()},
            "parse_memory_estimate_bytes": memory_estimate,
            "step_count": len(cleaned["steps"]),
            "empty_action_count": sum(not step["action"] for step in cleaned["steps"]),
            "empty_observation_count": sum(not step["observation"] for step in cleaned["steps"]),
            "reasoning_available": cleaned["quality_flags"]["has_reasoning"],
            "natural_error_available": cleaned["quality_flags"]["has_natural_error"],
            "screenshot_reference": cleaned["quality_flags"]["has_screenshot_reference"],
            "unknown_field_count": len(unknown),
        })

    _write_bytes(CLEANED_JSONL, (_json_line(record) for record in cleaned_records))
    _write_bytes(SERIALIZED_JSONL, (_json_line(record) for record in serialized_records))
    _write_csv(FIELD_POLICY, [
        "field_path", "observed_type", "policy_class", "included_in_primary",
        "included_in_error_ablation", "included_in_reasoning_sensitivity",
        "justification", "risk_notes",
    ], field_policy)

    raw_bytes = sum(source.source_size_bytes for source in sources)
    cleaned_bytes = CLEANED_JSONL.stat().st_size
    serialized_bytes = SERIALIZED_JSONL.stat().st_size
    probe_summary = json.loads(PROBE_SUMMARY.read_text(encoding="utf-8"))
    projected_raw = int(probe_summary["projected_full_dev_text_scope"]["declared_bytes"])
    unknown_fields = [
        {"field_path": key[0], "observed_type": key[1], "example_value_redacted": key[2], "presence_count": count}
        for key, count in sorted(unknown_counter.items())
    ]
    termination_count = sum(bool(record["terminal"]["termination_signal"]) for record in cleaned_records)
    step_count = sum(len(record["steps"]) for record in cleaned_records)
    empty_actions = sum(not step["action"] for record in cleaned_records for step in record["steps"])
    empty_observations = sum(not step["observation"] for record in cleaned_records for step in record["steps"])
    reasoning_count = sum(record["quality_flags"]["has_reasoning"] for record in cleaned_records)
    error_count = sum(record["quality_flags"]["has_natural_error"] for record in cleaned_records)
    screenshot_count = sum(record["quality_flags"]["has_screenshot_reference"] for record in cleaned_records)
    conditions = [
        "Explicit terminal action semantics are present for only part of the probe; null remains the required representation elsewhere.",
        "Natural error fields occur in a minority of trajectories and remain subject to the frozen error-field ablation.",
    ]
    if unknown_fields:
        conditions.append("New raw fields require human classification before any full-dev construction.")
    summary = {
        "stage": "A0.4",
        "stage_decision": "PASS_WITH_CONDITIONS" if conditions else "PASS",
        "source_revision": SOURCE_REVISION,
        "scope": {
            "existing_dev_probe_files_only": True,
            "new_downloads": 0,
            "test_files_processed": 0,
            "screenshots_processed": 0,
            "features_or_models_run": 0,
        },
        "input_views": list(INPUT_VIEWS),
        "whitelist": {
            "task_instruction": "$.goal",
            "step_action": "$.steps[].action",
            "step_observation": "$.steps[].axtree_pruned",
            "step_focused_element": "$.steps[].focused_element",
            "step_natural_error": "$.steps[].last_action_error",
            "reasoning_sensitivity_only": "$.steps[].reasoning",
        },
        "permanent_exclusions": [
            "$.summary_info (entire subtree, including cum_reward and cum_raw_reward)",
            "all reward/score/label/judge/annotation outcome semantics",
            "all screenshot/image/base64 fields and path values",
            "every future unknown field until human approval",
        ],
        "identity_policy": "management metadata only; absent from all serialized view strings",
        "reasoning_policy": "missing remains null; text appears only in sensitivity_with_reasoning",
        "terminal_policy": {
            "last_nonempty_action": "exact last nonempty allowlisted raw action",
            "last_nonempty_observation": "exact last nonempty allowlisted raw axtree_pruned",
            "last_step_index": "maximum 1-based source position contributing terminal action/observation",
            "termination_signal": "literal send_msg_to_user/report_infeasible action name only; otherwise null",
            "final_response_created": False,
        },
        "volume": {
            "raw_bytes": raw_bytes,
            "cleaned_jsonl_bytes": cleaned_bytes,
            "serialized_jsonl_bytes": serialized_bytes,
            "view_text_bytes": dict(view_bytes),
            "cleaned_to_raw_ratio": cleaned_bytes / raw_bytes,
            "serialized_to_raw_ratio": serialized_bytes / raw_bytes,
        },
        "field_character_totals": dict(character_totals),
        "probe_statistics": {
            "trajectory_count": len(cleaned_records),
            "step_count": step_count,
            "empty_action_count": empty_actions,
            "empty_observation_count": empty_observations,
            "reasoning_trajectory_count": reasoning_count,
            "reasoning_trajectory_rate": reasoning_count / len(cleaned_records),
            "natural_error_trajectory_count": error_count,
            "natural_error_trajectory_rate": error_count / len(cleaned_records),
            "screenshot_reference_count": screenshot_count,
            "screenshot_reference_rate": screenshot_count / len(cleaned_records),
            "termination_signal_count": termination_count,
            "termination_signal_rate": termination_count / len(cleaned_records),
            "average_parse_memory_estimate_bytes": sum(memory_estimates) / len(memory_estimates),
            "max_parse_memory_estimate_bytes": max(memory_estimates),
            "memory_estimate_method": "recursive sys.getsizeof of parsed JSON objects; excludes parser buffers and interpreter overhead outside the object graph",
        },
        "per_trajectory": trajectory_stats,
        "unknown_fields": {"count": sum(unknown_counter.values()), "unique_count": len(unknown_fields), "items": unknown_fields},
        "projected_full_dev": {
            "trajectory_count": 196,
            "raw_bytes": projected_raw,
            "cleaned_jsonl_bytes": round(projected_raw * cleaned_bytes / raw_bytes),
            "serialized_jsonl_bytes": round(projected_raw * serialized_bytes / raw_bytes),
            "view_text_bytes": {view: round(projected_raw * count / raw_bytes) for view, count in view_bytes.items()},
            "streaming_feasible": True,
            "permanent_raw_retention_required": False,
            "estimate_basis": "A0.3 fixed-revision dev file metadata multiplied by A0.4 16-probe byte ratios",
        },
        "conditions": conditions,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    print(json.dumps({
        "decision": summary["stage_decision"],
        "trajectories": len(cleaned_records),
        "raw_bytes": raw_bytes,
        "cleaned_bytes": cleaned_bytes,
        "unknown_fields": summary["unknown_fields"]["count"],
    }, ensure_ascii=False))
    return 0 if summary["stage_decision"] != "STOP" else 2


if __name__ == "__main__":
    sys.exit(run())
