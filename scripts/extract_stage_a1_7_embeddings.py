"""Freeze and extract the Stage A1.7 target-blind trajectory embeddings.

The preregistration mode is label-blind.  It creates the model/environment
manifest, tokenizer-only audit, and the fixed 16-trajectory determinism audit.
The formal extraction mode additionally requires an offline clean-worktree
start at the independent A1.7a commit.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "configs" / "stage_a1_7_dense_semantic.yaml"
PRIMARY_FIELDS = ["content_sha256", "input_view", "serialized_text", "trajectory_key"]
TOKEN_FIELDS = [
    "row_index", "trajectory_key", "payload_token_count", "chunk_count",
    "min_chunk_payload_tokens", "max_chunk_payload_tokens", "probe_member",
]
INDEX_FIELDS = [
    "row_index", "trajectory_key", "payload_token_count", "chunk_count",
    "embedding_norm",
]


class IntegrityError(RuntimeError):
    """Raised when a frozen A1.7 scientific or execution invariant fails."""


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp without fractional seconds."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def resolve(path_text: str) -> Path:
    """Resolve a repository-relative path and reject path traversal."""

    path = (REPO_ROOT / path_text).resolve()
    if path != REPO_ROOT and REPO_ROOT not in path.parents:
        raise IntegrityError(f"configured path escapes repository: {path_text}")
    return path


def sha256_path(path: Path) -> str:
    """Compute a file SHA-256 using bounded memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Atomically write stable UTF-8 JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8", newline="\n",
    )
    temporary.replace(path)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
    """Atomically write stable LF-terminated UTF-8 CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(fields), extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into ordered dictionaries."""

    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def git_output(arguments: Sequence[str]) -> str:
    """Run a read-only Git command at the repository root."""

    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True,
        capture_output=True, text=True,
    )
    return result.stdout


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    """Load and strictly validate frozen extraction semantics."""

    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if config["stage"] != "A1.7":
        raise IntegrityError("configuration is not Stage A1.7")
    model = config["model"]
    expected_model = {
        "repo_id": "Qwen/Qwen3-Embedding-0.6B",
        "requested_revision": "97b0c61",
        "immutable_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
        "weight_file": "model.safetensors",
        "weight_sha256": "0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd",
    }
    for key, value in expected_model.items():
        if model[key] != value:
            raise IntegrityError(f"frozen model field changed: {key}")
    if model["trust_remote_code"] or model["quantization"] or model["fine_tune"]:
        raise IntegrityError("model execution boundary changed")
    tok = config["tokenization"]
    if tok != {
        "add_special_tokens": False,
        "max_model_tokens": 8192,
        "payload_tokens_per_chunk": 8191,
        "overlap": 0,
        "append_eos_count": 1,
        "silent_truncation": False,
        "probe_row_indices": [0, 13, 26, 39, 52, 65, 78, 91, 104, 117, 130, 143, 156, 169, 182, 195],
    }:
        raise IntegrityError("tokenization/chunking contract changed")
    emb = config["embedding"]
    required_embedding = {
        "pooling": "last_eos_hidden_state",
        "chunk_normalization": "l2",
        "trajectory_aggregation": "payload_token_count_weighted_mean",
        "trajectory_normalization": "l2",
        "output_dimension": 1024,
        "output_dtype": "float32",
        "inference_weight_dtype": "bfloat16",
        "model_eval": True,
        "inference_mode": True,
        "tf32": False,
        "deterministic_algorithms": True,
        "cublas_workspace_config": ":4096:8",
        "expected_rows": 196,
        "norm_absolute_tolerance": 1e-5,
        "determinism_cosine_minimum": 0.999999,
        "determinism_max_absolute_difference": 1e-5,
    }
    if emb != required_embedding:
        raise IntegrityError("embedding algorithm changed")
    if config["execution"]["formal_network"] != 0 or not config["execution"]["local_files_only"]:
        raise IntegrityError("formal offline boundary changed")
    return config


def verify_input_hashes(config: dict[str, Any]) -> dict[str, str]:
    """Verify every frozen upstream input without reading test data."""

    verified: dict[str, str] = {}
    for spec in config["inputs"].values():
        path = resolve(spec["path"])
        if not path.is_file():
            raise IntegrityError(f"missing frozen input: {spec['path']}")
        actual = sha256_path(path)
        if actual != spec["sha256"]:
            raise IntegrityError(
                f"SHA-256 mismatch for {spec['path']}: {actual} != {spec['sha256']}"
            )
        verified[spec["path"]] = actual
    return verified


def read_primary(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Read the sole label/target/benchmark-blind primary text interface."""

    path = resolve(config["inputs"]["primary_text"]["path"])
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            record = json.loads(line)
            if list(record) != PRIMARY_FIELDS:
                raise IntegrityError(f"primary input schema/order changed at line {line_number}")
            if record["input_view"] != "primary_with_natural_errors":
                raise IntegrityError("non-primary view entered embedding input")
            if not isinstance(record["serialized_text"], str) or not record["serialized_text"]:
                raise IntegrityError("empty or non-string serialized trajectory")
            if hashlib.sha256(record["serialized_text"].encode("utf-8")).hexdigest() != record["content_sha256"]:
                raise IntegrityError("serialized trajectory content hash mismatch")
            records.append(record)
    expected = config["inputs"]["primary_text"]["expected_rows"]
    if len(records) != expected or len({row["trajectory_key"] for row in records}) != expected:
        raise IntegrityError("primary trajectory coverage is not exactly 196 unique keys")
    return records


def _model_files(config: dict[str, Any]) -> list[dict[str, Any]]:
    model_dir = resolve(config["model"]["local_snapshot"])
    if not model_dir.is_dir():
        raise IntegrityError(f"missing local model snapshot: {model_dir}")
    rows: list[dict[str, Any]] = []
    for path in sorted(model_dir.rglob("*")):
        if not path.is_file() or ".cache" in path.relative_to(model_dir).parts:
            continue
        rows.append({
            "path": path.relative_to(model_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        })
    return rows


def build_model_manifest(config: dict[str, Any]) -> dict[str, Any]:
    """Hash the complete pinned local snapshot and enforce its weight/config."""

    files = _model_files(config)
    by_name = {row["path"]: row for row in files}
    required = {
        ".gitattributes", "README.md", "config.json", "generation_config.json",
        "model.safetensors", "tokenizer.json", "tokenizer_config.json",
        "merges.txt", "vocab.json", "modules.json",
        "config_sentence_transformers.json", "1_Pooling/config.json",
    }
    if set(by_name) != required:
        raise IntegrityError(f"snapshot file set changed: {sorted(set(by_name) ^ required)}")
    expected_weight = config["model"]["weight_sha256"]
    if by_name["model.safetensors"]["sha256"] != expected_weight:
        raise IntegrityError("model.safetensors SHA-256 mismatch")
    model_dir = resolve(config["model"]["local_snapshot"])
    model_config = json.loads((model_dir / "config.json").read_text(encoding="utf-8"))
    if model_config.get("model_type") != "qwen3" or model_config.get("hidden_size") != 1024:
        raise IntegrityError("model type or embedding dimension differs from preregistration")
    return {
        "stage": "A1.7a",
        "repo_id": config["model"]["repo_id"],
        "requested_revision": config["model"]["requested_revision"],
        "immutable_revision": config["model"]["immutable_revision"],
        "license": config["model"]["license"],
        "library_name": "sentence-transformers",
        "pipeline_tag": "feature-extraction",
        "local_snapshot": config["model"]["local_snapshot"],
        "weight_file": config["model"]["weight_file"],
        "weight_sha256": expected_weight,
        "weight_bytes": by_name["model.safetensors"]["bytes"],
        "hidden_size": model_config["hidden_size"],
        "max_position_embeddings": model_config["max_position_embeddings"],
        "torch_dtype_declared": model_config["torch_dtype"],
        "files": files,
    }


def verify_model_manifest(config: dict[str, Any]) -> dict[str, Any]:
    """Recompute and exactly compare the tracked snapshot manifest."""

    path = resolve(config["outputs"]["model_manifest"])
    recorded = json.loads(path.read_text(encoding="utf-8"))
    current = build_model_manifest(config)
    if recorded != current:
        raise IntegrityError("local model snapshot differs from frozen manifest")
    return recorded


def package_lock_lines() -> list[str]:
    """Return a machine-independent exact package/version lock."""

    rows = {
        f"{distribution.metadata['Name']}=={distribution.version}"
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    return sorted(rows, key=str.lower)


def semantic_environment() -> dict[str, Any]:
    """Capture the isolated semantic runtime and hardware."""

    import huggingface_hub
    import safetensors
    import tokenizers
    import torch
    import transformers

    cuda_available = bool(torch.cuda.is_available())
    return {
        "generated_at_utc": utc_now(),
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "platform": platform.platform(),
        "hardware": {
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "cuda_available": cuda_available,
            "gpu": torch.cuda.get_device_name(0) if cuda_available else None,
            "gpu_capability": list(torch.cuda.get_device_capability(0)) if cuda_available else None,
            "cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version() if cuda_available else None,
        },
        "dependencies": {
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "tokenizers": tokenizers.__version__,
            "safetensors": safetensors.__version__,
            "numpy": np.__version__,
            "huggingface_hub": huggingface_hub.__version__,
        },
        "semantic_environment_only": True,
        "baseline_environment_modified": False,
        "formal_run_network_allowed": False,
        "quantization": False,
        "fine_tune": False,
    }


def load_tokenizer(config: dict[str, Any]) -> Any:
    """Load only the pinned local tokenizer with no remote code or network."""

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        resolve(config["model"]["local_snapshot"]),
        local_files_only=True,
        trust_remote_code=False,
    )
    if not isinstance(tokenizer.eos_token_id, int) or tokenizer.eos_token_id < 0:
        raise IntegrityError("tokenizer does not expose one usable eos_token_id")
    encoded = tokenizer.encode("A1.7 eos audit", add_special_tokens=False)
    if not encoded or tokenizer.eos_token_id in encoded:
        raise IntegrityError("EOS audit cannot distinguish payload from appended EOS")
    return tokenizer


def payload_chunks(payload: Sequence[int], payload_limit: int = 8191) -> list[list[int]]:
    """Split payload tokens in order with no overlap or truncation."""

    if payload_limit != 8191:
        raise IntegrityError("payload chunk limit changed")
    if not payload:
        raise IntegrityError("zero-token trajectory is not permitted")
    chunks = [list(payload[start : start + payload_limit]) for start in range(0, len(payload), payload_limit)]
    if any(not chunk or len(chunk) > payload_limit for chunk in chunks):
        raise IntegrityError("invalid payload chunk length")
    flattened = [token for chunk in chunks for token in chunk]
    if flattened != list(payload):
        raise IntegrityError("chunking changed order, overlapped, or truncated payload")
    return chunks


def tokenize_records(
    config: dict[str, Any], records: Sequence[dict[str, Any]], tokenizer: Any
) -> tuple[list[dict[str, Any]], list[list[int]]]:
    """Tokenize every primary trajectory without labels or special tokens."""

    probe = set(config["tokenization"]["probe_row_indices"])
    rows: list[dict[str, Any]] = []
    payloads: list[list[int]] = []
    for index, record in enumerate(records):
        payload = tokenizer.encode(record["serialized_text"], add_special_tokens=False)
        chunks = payload_chunks(payload)
        payloads.append(payload)
        sizes = [len(chunk) for chunk in chunks]
        rows.append({
            "row_index": index,
            "trajectory_key": record["trajectory_key"],
            "payload_token_count": len(payload),
            "chunk_count": len(chunks),
            "min_chunk_payload_tokens": min(sizes),
            "max_chunk_payload_tokens": max(sizes),
            "probe_member": index in probe,
        })
    if len(rows) != 196 or sum(bool(row["probe_member"]) for row in rows) != 16:
        raise IntegrityError("token audit row/probe count mismatch")
    return rows, payloads


def audit_statistics(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Summarize frozen token and chunk distributions."""

    def stats(values: Sequence[int]) -> dict[str, float | int]:
        array = np.asarray(values, dtype=np.float64)
        return {
            "min": int(np.min(array)),
            "median": float(np.median(array)),
            "mean": float(np.mean(array)),
            "p95": float(np.percentile(array, 95)),
            "max": int(np.max(array)),
        }

    return {
        "trajectory_count": len(rows),
        "payload_token_count": stats([int(row["payload_token_count"]) for row in rows]),
        "chunk_count": stats([int(row["chunk_count"]) for row in rows]),
        "total_payload_tokens": sum(int(row["payload_token_count"]) for row in rows),
        "total_chunks": sum(int(row["chunk_count"]) for row in rows),
        "multi_chunk_trajectories": sum(int(row["chunk_count"]) > 1 for row in rows),
        "maximum_chunk_payload_tokens": max(int(row["max_chunk_payload_tokens"]) for row in rows),
    }


def configure_determinism(seed: int = 2026) -> dict[str, Any]:
    """Configure deterministic, non-TF32 inference."""

    import torch

    if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
        raise IntegrityError("CUBLAS_WORKSPACE_CONFIG must be :4096:8 before process start")
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    return {
        "seed": seed,
        "tf32_matmul": bool(torch.backends.cuda.matmul.allow_tf32),
        "tf32_cudnn": bool(torch.backends.cudnn.allow_tf32),
        "deterministic_algorithms": bool(torch.are_deterministic_algorithms_enabled()),
        "cublas_workspace_config": os.environ["CUBLAS_WORKSPACE_CONFIG"],
    }


def load_model(config: dict[str, Any]) -> tuple[Any, str]:
    """Load the unquantized pinned AutoModel in native bfloat16 for inference."""

    import torch
    from transformers import AutoModel

    if not torch.cuda.is_available():
        raise IntegrityError("A1.7 semantic environment has no available CUDA device")
    model = AutoModel.from_pretrained(
        resolve(config["model"]["local_snapshot"]),
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    model.eval()
    model.to("cuda:0")
    if model.config.hidden_size != config["embedding"]["output_dimension"]:
        raise IntegrityError("loaded model hidden size is not 1024")
    if model.training:
        raise IntegrityError("model.eval() did not disable training mode")
    return model, "cuda:0"


def embed_payload(model: Any, payload: Sequence[int], eos_token_id: int, device: str) -> np.ndarray:
    """Apply last-EOS pooling, per-chunk L2, weighted mean, and final L2."""

    import torch

    chunk_vectors: list[torch.Tensor] = []
    weights: list[int] = []
    with torch.inference_mode():
        for payload_chunk in payload_chunks(payload):
            input_ids_list = [*payload_chunk, eos_token_id]
            if len(input_ids_list) > 8192 or input_ids_list[-1] != eos_token_id:
                raise IntegrityError("chunk EOS append or maximum length violated")
            input_ids = torch.tensor([input_ids_list], dtype=torch.long, device=device)
            attention_mask = torch.ones_like(input_ids, dtype=torch.long, device=device)
            output = model(input_ids=input_ids, attention_mask=attention_mask, use_cache=False)
            hidden = output.last_hidden_state[0, -1].to(dtype=torch.float32)
            norm = torch.linalg.vector_norm(hidden)
            if not torch.isfinite(norm) or float(norm) <= 0:
                raise IntegrityError("non-finite or zero chunk embedding norm")
            chunk_vectors.append(hidden / norm)
            weights.append(len(payload_chunk))
    stacked = torch.stack(chunk_vectors)
    weight_tensor = torch.tensor(weights, dtype=torch.float32, device=device).unsqueeze(1)
    trajectory = torch.sum(stacked * weight_tensor, dim=0) / torch.sum(weight_tensor)
    norm = torch.linalg.vector_norm(trajectory)
    if not torch.isfinite(norm) or float(norm) <= 0:
        raise IntegrityError("non-finite or zero trajectory embedding norm")
    result = (trajectory / norm).detach().cpu().numpy().astype(np.float32, copy=False)
    if result.shape != (1024,) or result.dtype != np.float32 or not np.isfinite(result).all():
        raise IntegrityError("trajectory embedding shape/dtype/finite guard failed")
    return result


def determinism_probe(
    config: dict[str, Any], model: Any, tokenizer: Any,
    records: Sequence[dict[str, Any]], payloads: Sequence[Sequence[int]], device: str,
) -> dict[str, Any]:
    """Run the fixed 16 trajectories twice consecutively and enforce tolerances."""

    indices = config["tokenization"]["probe_row_indices"]
    first = np.stack([
        embed_payload(model, payloads[index], tokenizer.eos_token_id, device)
        for index in indices
    ])
    second = np.stack([
        embed_payload(model, payloads[index], tokenizer.eos_token_id, device)
        for index in indices
    ])
    cosine = np.sum(first * second, axis=1) / (
        np.linalg.norm(first, axis=1) * np.linalg.norm(second, axis=1)
    )
    maximum = np.max(np.abs(first - second), axis=1)
    minimum_cosine = float(np.min(cosine))
    maximum_difference = float(np.max(maximum))
    passed = (
        minimum_cosine >= config["embedding"]["determinism_cosine_minimum"]
        and maximum_difference <= config["embedding"]["determinism_max_absolute_difference"]
    )
    result = {
        "probe_count": 16,
        "probe_row_indices": indices,
        "probe_trajectory_keys": [records[index]["trajectory_key"] for index in indices],
        "minimum_cosine_similarity": minimum_cosine,
        "maximum_absolute_difference": maximum_difference,
        "cosine_threshold": config["embedding"]["determinism_cosine_minimum"],
        "absolute_difference_threshold": config["embedding"]["determinism_max_absolute_difference"],
        "two_consecutive_runs": True,
        "passed": passed,
    }
    if not passed:
        raise IntegrityError(f"determinism probe failed: {result}")
    return result


def _assert_tracked(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    try:
        git_output(["ls-files", "--error-unmatch", relative])
    except subprocess.CalledProcessError as error:
        raise IntegrityError(f"preregistered file is not tracked: {relative}") from error


def preregistered_file_paths(config: dict[str, Any]) -> list[Path]:
    """Return files whose exact A1.7a bytes authorize formal extraction."""

    return [
        REPO_ROOT / ".gitattributes",
        CONFIG_PATH,
        REPO_ROOT / "scripts" / "extract_stage_a1_7_embeddings.py",
        REPO_ROOT / "scripts" / "run_stage_a1_7_dense_semantic.py",
        REPO_ROOT / "tests" / "test_stage_a1_7_dense_semantic.py",
        resolve(config["environment"]["semantic_lock"]),
        resolve(config["outputs"]["model_manifest"]),
        resolve(config["outputs"]["semantic_environment"]),
        resolve(config["outputs"]["tokenization_audit"]),
    ]


def assert_preregistered(config: dict[str, Any]) -> dict[str, Any]:
    """Verify every A1.7a byte is committed and unchanged."""

    integrity_path = resolve(config["outputs"]["prerun_integrity"])
    integrity = json.loads(integrity_path.read_text(encoding="utf-8"))
    for path in preregistered_file_paths(config):
        relative = path.relative_to(REPO_ROOT).as_posix()
        if integrity["preregistered_files"].get(relative) != sha256_path(path):
            raise IntegrityError(f"preregistered hash changed: {relative}")
        _assert_tracked(path)
    _assert_tracked(integrity_path)
    if integrity["formal_embedding_count"] != 0 or integrity["real_label_fit_count"] != 0:
        raise IntegrityError("A1.7a contains prohibited formal work")
    return integrity


def assert_clean_formal_start(config: dict[str, Any]) -> str:
    """Require a clean independent A1.7a commit before any formal forward."""

    status = git_output(["status", "--porcelain=v1"]).strip()
    if status:
        raise IntegrityError(f"formal A1.7b requires clean worktree: {status}")
    subject = git_output(["show", "-s", "--format=%s", "HEAD"]).strip()
    expected = config["execution"]["required_preregistration_commit_subject"]
    if subject != expected:
        raise IntegrityError(f"HEAD is not the A1.7a preregistration commit: {subject}")
    return git_output(["rev-parse", "HEAD"]).strip()


def assert_offline_environment() -> dict[str, Any]:
    """Require explicit offline variables for formal model loading/inference."""

    required = {
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "A1_7_NETWORK": "0",
        "A1_7_LOCAL_FILES_ONLY": "true",
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    }
    actual = {key: os.environ.get(key) for key in required}
    if actual != required:
        raise IntegrityError(f"formal offline environment not frozen: {actual}")
    return actual


def prepare_preregistration(config: dict[str, Any]) -> None:
    """Create all A1.7a artifacts before any full embedding or real-label fit."""

    verify_input_hashes(config)
    formal = [
        "embedding", "embedding_index", "embedding_extraction_summary",
        "inner_config_selection", "inner_selected_oof_predictions",
        "threshold_selection", "external_predictions", "domain_metrics",
        "macro_metrics", "pooled_metrics", "comparison_to_a1_3",
        "bootstrap_primary_summary", "bootstrap_draw_metrics", "run_summary", "report",
    ]
    existing = [config["outputs"][key] for key in formal if resolve(config["outputs"][key]).exists()]
    if existing:
        raise IntegrityError(f"formal A1.7 outputs already exist before preregistration: {existing}")

    manifest = build_model_manifest(config)
    write_json(resolve(config["outputs"]["model_manifest"]), manifest)
    lock_path = resolve(config["environment"]["semantic_lock"])
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("\n".join(package_lock_lines()) + "\n", encoding="utf-8", newline="\n")
    environment = semantic_environment()
    write_json(resolve(config["outputs"]["semantic_environment"]), environment)

    records = read_primary(config)
    tokenizer = load_tokenizer(config)
    token_rows, payloads = tokenize_records(config, records, tokenizer)
    write_csv(resolve(config["outputs"]["tokenization_audit"]), token_rows, TOKEN_FIELDS)
    token_stats = audit_statistics(token_rows)
    deterministic_setup = configure_determinism(config["random_state"])
    model, device = load_model(config)
    probe = determinism_probe(config, model, tokenizer, records, payloads, device)
    del model
    import torch
    torch.cuda.empty_cache()

    paths = preregistered_file_paths(config)
    integrity = {
        "stage": "A1.7a",
        "created_at_utc": utc_now(),
        "source_revisions": config["source"],
        "model": {
            "repo_id": manifest["repo_id"],
            "requested_revision": manifest["requested_revision"],
            "immutable_revision": manifest["immutable_revision"],
            "weight_sha256": manifest["weight_sha256"],
            "license": manifest["license"],
        },
        "verified_input_hashes": verify_input_hashes(config),
        "baseline_lock_unchanged": True,
        "baseline_environment_unchanged": True,
        "semantic_lock_sha256": sha256_path(lock_path),
        "tokenization": token_stats,
        "eos_token_id": int(tokenizer.eos_token_id),
        "deterministic_setup": deterministic_setup,
        "determinism_probe": probe,
        "probe_label_access": 0,
        "formal_embedding_count": 0,
        "real_label_fit_count": 0,
        "network_scope": "pinned_model_and_semantic_environment_only",
        "test_access": {"content": 0, "labels": 0, "predictions": 0, "metrics": 0},
        "forbidden_experiments_executed": [],
        "preregistered_files": {
            path.relative_to(REPO_ROOT).as_posix(): sha256_path(path) for path in paths
        },
    }
    write_json(resolve(config["outputs"]["prerun_integrity"]), integrity)
    print(json.dumps({
        "status": "PASS", "mode": "prepare-preregistration",
        "immutable_revision": manifest["immutable_revision"],
        "weight_sha256": manifest["weight_sha256"],
        "tokenization": token_stats, "determinism_probe": probe,
    }))


def verify_embedding_outputs(config: dict[str, Any]) -> dict[str, Any]:
    """Independently verify frozen embedding shape/index/norm/hash integrity."""

    embedding_path = resolve(config["outputs"]["embedding"])
    index_path = resolve(config["outputs"]["embedding_index"])
    summary_path = resolve(config["outputs"]["embedding_extraction_summary"])
    array = np.load(embedding_path, allow_pickle=False)
    index = read_csv(index_path)
    if array.shape != (196, 1024) or array.dtype != np.float32:
        raise IntegrityError("frozen embedding shape/dtype mismatch")
    if not np.isfinite(array).all():
        raise IntegrityError("frozen embedding contains NaN/Inf")
    norms = np.linalg.norm(array, axis=1)
    if not np.allclose(norms, 1.0, rtol=0.0, atol=1e-5):
        raise IntegrityError("frozen trajectory embeddings are not L2 normalized")
    if len(index) != 196 or len({row["trajectory_key"] for row in index}) != 196:
        raise IntegrityError("embedding index is not 196 unique trajectories")
    if [int(row["row_index"]) for row in index] != list(range(196)):
        raise IntegrityError("embedding row indices are not exact and ordered")
    records = read_primary(config)
    if [row["trajectory_key"] for row in index] != [row["trajectory_key"] for row in records]:
        raise IntegrityError("embedding index differs from primary input order")
    for i, row in enumerate(index):
        if not math.isclose(float(row["embedding_norm"]), float(norms[i]), abs_tol=1e-6):
            raise IntegrityError("recorded embedding norm cannot be reproduced")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    hash_value = sha256_path(embedding_path)
    if summary["embedding_sha256"] != hash_value:
        raise IntegrityError("embedding hash differs from extraction summary")
    return {
        "status": "PASS", "shape": [196, 1024], "dtype": "float32",
        "finite": True, "unique_keys": 196, "embedding_sha256": hash_value,
        "norm_min": float(np.min(norms)), "norm_max": float(np.max(norms)),
    }


def formal_extract(config: dict[str, Any]) -> None:
    """Run the one-time full 196-trajectory offline embedding extraction."""

    preregistration_commit = assert_clean_formal_start(config)
    offline = assert_offline_environment()
    integrity = assert_preregistered(config)
    input_hashes_before = verify_input_hashes(config)
    verify_model_manifest(config)
    output_keys = ["embedding", "embedding_index", "embedding_extraction_summary"]
    existing = [config["outputs"][key] for key in output_keys if resolve(config["outputs"][key]).exists()]
    if existing:
        raise IntegrityError(f"formal embedding output exists; refusing overwrite: {existing}")

    started = utc_now()
    run_id = f"a1_7_embedding_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{preregistration_commit[:8]}"
    run_dir = resolve(f"runs/{run_id}")
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "command.txt").write_text(
        f"{sys.executable} scripts/extract_stage_a1_7_embeddings.py --config configs/stage_a1_7_dense_semantic.yaml --extract\n",
        encoding="utf-8", newline="\n",
    )
    write_json(run_dir / "environment.json", semantic_environment())
    write_json(run_dir / "hashes_before.json", input_hashes_before)
    (run_dir / "stdout.log").write_text(
        f"{started} offline guards PASS; starting determinism probe\n",
        encoding="utf-8", newline="\n",
    )

    records = read_primary(config)
    tokenizer = load_tokenizer(config)
    token_rows, payloads = tokenize_records(config, records, tokenizer)
    tracked_token_rows = read_csv(resolve(config["outputs"]["tokenization_audit"]))
    normalized = [{key: str(value) for key, value in row.items()} for row in token_rows]
    for row in normalized:
        row["probe_member"] = "True" if row["probe_member"] == "True" else "False"
    if normalized != tracked_token_rows:
        raise IntegrityError("formal tokenization differs from preregistered audit")
    deterministic_setup = configure_determinism(config["random_state"])
    model, device = load_model(config)
    probe = determinism_probe(config, model, tokenizer, records, payloads, device)
    with (run_dir / "stdout.log").open("a", encoding="utf-8", newline="\n") as log:
        log.write(f"{utc_now()} determinism probe PASS; starting 196 embeddings\n")

    vectors: list[np.ndarray] = []
    index_rows: list[dict[str, Any]] = []
    start_clock = time.perf_counter()
    for index, (record, payload, token_row) in enumerate(zip(records, payloads, token_rows, strict=True)):
        vector = embed_payload(model, payload, tokenizer.eos_token_id, device)
        vectors.append(vector)
        index_rows.append({
            "row_index": index,
            "trajectory_key": record["trajectory_key"],
            "payload_token_count": token_row["payload_token_count"],
            "chunk_count": token_row["chunk_count"],
            "embedding_norm": float(np.linalg.norm(vector)),
        })
        if (index + 1) % 10 == 0 or index + 1 == 196:
            message = json.dumps({"phase": "embedding", "completed": index + 1, "total": 196})
            print(message, flush=True)
            with (run_dir / "stdout.log").open("a", encoding="utf-8", newline="\n") as log:
                log.write(message + "\n")
    matrix = np.stack(vectors).astype(np.float32, copy=False)
    if matrix.shape != (196, 1024) or not np.isfinite(matrix).all():
        raise IntegrityError("formal embedding matrix failed shape/finite guard")
    if not np.allclose(np.linalg.norm(matrix, axis=1), 1.0, rtol=0.0, atol=1e-5):
        raise IntegrityError("formal trajectory norm guard failed")

    embedding_path = resolve(config["outputs"]["embedding"])
    embedding_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = embedding_path.with_name(embedding_path.name + ".tmp")
    with temporary.open("wb") as handle:
        np.save(handle, matrix, allow_pickle=False)
    temporary.replace(embedding_path)
    write_csv(resolve(config["outputs"]["embedding_index"]), index_rows, INDEX_FIELDS)
    elapsed = time.perf_counter() - start_clock
    input_hashes_after = verify_input_hashes(config)
    if input_hashes_before != input_hashes_after:
        raise IntegrityError("frozen inputs changed during embedding extraction")
    summary = {
        "stage": "A1.7b_embedding_extraction",
        "started_at_utc": started,
        "completed_at_utc": utc_now(),
        "run_id": run_id,
        "run_directory": run_dir.relative_to(REPO_ROOT).as_posix(),
        "preregistration_commit": preregistration_commit,
        "model": integrity["model"],
        "semantic_environment": semantic_environment(),
        "offline_environment": offline,
        "network_access": 0,
        "local_files_only": True,
        "deterministic_setup": deterministic_setup,
        "determinism_probe": probe,
        "tokenization": audit_statistics(token_rows),
        "embedding_shape": [196, 1024],
        "embedding_dtype": "float32",
        "embedding_finite": True,
        "embedding_norm_min": float(np.min(np.linalg.norm(matrix, axis=1))),
        "embedding_norm_max": float(np.max(np.linalg.norm(matrix, axis=1))),
        "embedding_sha256": sha256_path(embedding_path),
        "embedding_index_sha256": sha256_path(resolve(config["outputs"]["embedding_index"])),
        "elapsed_seconds_full_embedding_only": elapsed,
        "hashes_before_run": input_hashes_before,
        "hashes_after_run": input_hashes_after,
        "label_access": 0,
        "target_specific_embedding_count": 0,
        "benchmark_specific_embedding_count": 0,
        "fine_tune_count": 0,
        "quantization_count": 0,
        "second_embedding_model_count": 0,
        "test_access": {"content": 0, "labels": 0, "predictions": 0, "metrics": 0},
    }
    write_json(resolve(config["outputs"]["embedding_extraction_summary"]), summary)
    verification = verify_embedding_outputs(config)
    write_json(run_dir / "verification.json", verification)
    write_json(run_dir / "completed.json", {"status": "PASS", "completed_at_utc": utc_now()})
    print(json.dumps({"status": "PASS", "run_id": run_id, **verification}), flush=True)


def main() -> int:
    """CLI entry point."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-preregistration", action="store_true")
    modes.add_argument("--extract", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        config = load_config(Path(args.config).resolve())
        if args.prepare_preregistration:
            prepare_preregistration(config)
        elif args.extract:
            formal_extract(config)
        else:
            print(json.dumps(verify_embedding_outputs(config)))
        return 0
    except Exception as error:
        print(json.dumps({"status": "STOP", "error_type": type(error).__name__, "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
