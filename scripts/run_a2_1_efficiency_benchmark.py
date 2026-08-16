#!/usr/bin/env python3
"""Run and verify the preregistered Stage A2.1 efficiency benchmark.

The orchestrator launches separate baseline and semantic workers so each
method uses its frozen environment and process peak RSS remains interpretable.
No estimator training or A1 scientific metric computation is implemented.
"""

from __future__ import annotations

import argparse
import ast
import csv
import ctypes
import hashlib
import importlib.metadata
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import winreg
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = Path(__file__).resolve()
PREREG_COMMIT = "2ca01ec9bf8c2fdcb129f4a1737406510fe21645"
IMPLEMENTATION_COMMIT = "0708df64d11b6ed64d9fd6f4104f4c2de5dc8bba"
EXPECTED_IMPLEMENTATION_SUBJECT = "chore: implement A2.1 efficiency benchmark"
TASKBOOK_PATH = "docs/tasks/STAGE_A2_1_EFFICIENCY_COST_BENCHMARK.md"
TASKBOOK_SHA256 = "f9f1bee466b41e2ffbf5144267adc1b2fdd342b108b7929c9a015926649b3b45"
CLAIM_MATRIX_PATH = "artifacts/a1_11_final_claim_matrix.csv"
CLAIM_MATRIX_SHA256 = "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175"
MAIN_TABLE_PATH = "artifacts/a1_11_table_main_test_results.csv"
MAIN_TABLE_SHA256 = "c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947"
CLEANED_DEV_PATH = "data/processed/dev_cleaned_trajectories.jsonl"
CLEANED_DEV_SHA256 = "157a2f665ec33aced4e549e349012f97387961afca2da4f8629cc3472a29342e"
PRIMARY_DEV_PATH = "data/processed/dev_serialized_primary.jsonl"
PRIMARY_DEV_SHA256 = "ec2757489c04b4388711826d29a028b24585156c9dab0496d4afe394aa02398a"
STRUCTURAL_PATH = "artifacts/dev_structural_features.csv"
STRUCTURAL_SHA256 = "2dcd9f5a5a22c40d318f2a7fe1303cdcc0c27832d2ab443c0f3dbe2a1f631556"
FROZEN_EMBEDDING_PATH = "artifacts/a1_7_qwen3_embedding_0p6b.npy"
FROZEN_EMBEDDING_SHA256 = "26a52ea14c7538c87527bd129880ff795e10640355474688e6297a9407ad7037"
MODEL_MANIFEST_PATH = "artifacts/a1_7_embedding_model_manifest.json"
MODEL_MANIFEST_SHA256 = "801893709711d55b2310daad2ae7571122570bcbebb08553e3b92c10c870cf54"
QWEN_SNAPSHOT = ".semantic-cache/models/Qwen3-Embedding-0.6B-97b0c614"
QWEN_WEIGHT_PATH = f"{QWEN_SNAPSHOT}/model.safetensors"
QWEN_WEIGHT_SHA256 = "0437e45c94563b09e13cb7a64478fc406947a93cb34a7e05870fc8dcd48e23fd"
QWEN_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
B2_MODEL_PATH = "artifacts/final_models/final_success_b2.joblib"
B2_MODEL_SHA256 = "afbdb0a60205d7c6bd40232a8c8a1b1ad3b0910d6b65fecf894cca1a040123c1"
B2_SECONDARY_MODEL_PATH = "artifacts/final_models/final_looping_b2.joblib"
B2_SECONDARY_MODEL_SHA256 = "862b7ff2b0cbcb5faf88908f5fe5824c7f4e52c2c21521e41bb5fb71b011660c"
B4_MODEL_PATH = "artifacts/final_models/final_side_effect_b4.joblib"
B4_MODEL_SHA256 = "5eb29646c10a8193b8492ffe26a41a63414dc9da884890813273c43d17a7de59"
FINAL_MODEL_MANIFEST_PATH = "artifacts/a1_9_final_model_manifest.json"
B2_DIMENSION = 13
B4_DIMENSION = 1024
TRAJECTORY_COUNT = 196
B2_MEASURED_REPETITIONS = 5
B4_MEASURED_REPETITIONS = 3
WARMUP_REPETITIONS = 1
MIB = 1024 * 1024

FEATURE_NAMES = (
    "step_count", "nonempty_action_count", "nonempty_observation_count",
    "nonempty_focused_element_count", "natural_error_step_count",
    "natural_error_step_ratio", "has_explicit_termination_signal",
    "action_char_count_total", "observation_char_count_total",
    "action_char_count_mean_nonempty", "observation_char_count_mean_nonempty",
    "unique_action_ratio", "consecutive_duplicate_action_count",
)

RAW_FIELDS = (
    "method", "phase", "run_type", "run_index", "trajectory_count",
    "dimension", "device", "total_seconds", "ms_per_trajectory",
    "peak_cpu_rss_mb", "peak_gpu_allocated_mb", "peak_gpu_reserved_mb",
    "status", "notes",
)
SUMMARY_FIELDS = (
    "method", "representation", "dimension", "device", "measured_repetitions",
    "median_extraction_ms_per_trajectory", "median_inference_ms_per_trajectory",
    "cold_start_seconds", "model_load_seconds", "representation_size_bytes",
    "representation_size_mb", "representation_serialization", "classifier_artifact",
    "classifier_artifact_size_bytes", "classifier_artifact_size_mb",
    "semantic_encoder_size_bytes", "semantic_encoder_size_mb",
    "semantic_snapshot_size_bytes", "semantic_snapshot_size_mb", "peak_cpu_rss_mb",
    "peak_gpu_allocated_mb", "peak_gpu_reserved_mb", "peak_gpu_vram_mb",
    "evidence_status",
)
RELATIVE_FIELDS = (
    "dimension_ratio_B4_over_B2", "representation_size_ratio_B4_over_B2",
    "extraction_time_ratio_B4_over_B2", "classifier_inference_ratio_B4_over_B2",
    "peak_memory_ratio_B4_over_B2", "ratio_direction", "notes",
)
OUTPUT_PATHS = {
    "environment": REPO_ROOT / "artifacts" / "a2_1_environment.json",
    "raw": REPO_ROOT / "artifacts" / "a2_1_efficiency_raw.csv",
    "summary": REPO_ROOT / "artifacts" / "a2_1_efficiency_summary.csv",
    "relative": REPO_ROOT / "artifacts" / "a2_1_efficiency_relative_cost.csv",
    "run_summary": REPO_ROOT / "artifacts" / "a2_1_run_summary.json",
    "report": REPO_ROOT / "docs" / "stage_a2_1_efficiency_benchmark_report.md",
}


class IntegrityError(RuntimeError):
    """Raised when an A2.1 scientific, provenance, or measurement guard fails."""


def resolve(path_text: str) -> Path:
    """Resolve a repository-relative path and reject traversal."""
    path = (REPO_ROOT / path_text).resolve()
    if path != REPO_ROOT and REPO_ROOT not in path.parents:
        raise IntegrityError(f"path escapes repository: {path_text}")
    return path


def utc_now() -> str:
    """Return a second-resolution UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_path(path: Path) -> str:
    """Hash a file with bounded memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    """Write LF-only UTF-8 text atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_json(path: Path, value: Any) -> None:
    """Write deterministic machine-readable JSON."""
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: Sequence[str]) -> None:
    """Write a fixed-schema LF-only CSV atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV."""
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def git_output(arguments: Sequence[str]) -> str:
    """Run a read-only Git command."""
    result = subprocess.run(
        ["git", *arguments], cwd=REPO_ROOT, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def verify_file(path_text: str, expected_sha256: str) -> str:
    """Verify one frozen file and return its digest."""
    path = resolve(path_text)
    if not path.is_file():
        raise IntegrityError(f"missing frozen file: {path_text}")
    actual = sha256_path(path)
    if actual != expected_sha256:
        raise IntegrityError(f"SHA-256 mismatch for {path_text}: {actual} != {expected_sha256}")
    return actual


def peak_rss_mb() -> float:
    """Return process peak working-set RSS in MiB."""
    if os.name != "nt":
        import resource
        return float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) / 1024.0

    class ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ProcessMemoryCountersEx),
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    counters = ProcessMemoryCountersEx()
    counters.cb = ctypes.sizeof(counters)
    handle = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        raise IntegrityError(f"GetProcessMemoryInfo failed with Windows error {ctypes.get_last_error()}")
    return float(counters.PeakWorkingSetSize) / MIB


def npy_serialization(array: Any) -> tuple[int, str]:
    """Serialize an array as NumPy .npy in memory and return size and hash."""
    import numpy as np
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    payload = buffer.getvalue()
    return len(payload), hashlib.sha256(payload).hexdigest()


def raw_row(
    *, method: str, phase: str, run_type: str, run_index: int,
    trajectory_count: int, dimension: int, device: str, total_seconds: float,
    peak_cpu: float, peak_gpu_allocated: float | None = None,
    peak_gpu_reserved: float | None = None, notes: str = "",
) -> dict[str, Any]:
    """Build one raw timing record with stable units."""
    per_trajectory = total_seconds * 1000.0 / trajectory_count if trajectory_count else None
    return {
        "method": method, "phase": phase, "run_type": run_type, "run_index": run_index,
        "trajectory_count": trajectory_count, "dimension": dimension, "device": device,
        "total_seconds": total_seconds,
        "ms_per_trajectory": per_trajectory if per_trajectory is not None else "NA",
        "peak_cpu_rss_mb": peak_cpu,
        "peak_gpu_allocated_mb": peak_gpu_allocated if peak_gpu_allocated is not None else "NA",
        "peak_gpu_reserved_mb": peak_gpu_reserved if peak_gpu_reserved is not None else "NA",
        "status": "OK", "notes": notes,
    }


def progress(message: str) -> None:
    """Emit compact progress to terminal and the formal run log."""
    line = f"{utc_now()} {message}"
    print(line, flush=True)
    log_path = os.environ.get("A2_1_LOG_PATH")
    if log_path:
        with Path(log_path).open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")


def source_static_guards() -> dict[str, Any]:
    """Prove the A2.1 code has no training or A1 metric implementation path."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    training_calls: list[str] = []
    metric_calls: list[str] = []
    metric_names = {"average_precision_score", "f1_score", "roc_auc_score", "bootstrap"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "fit", "partial_fit", "fit_predict", "fit_transform"
        }:
            training_calls.append(node.func.attr)
        name = node.func.id if isinstance(node.func, ast.Name) else (
            node.func.attr if isinstance(node.func, ast.Attribute) else ""
        )
        if name in metric_names:
            metric_calls.append(name)
    if training_calls or metric_calls:
        raise IntegrityError(f"prohibited calls in A2.1 source: {training_calls + metric_calls}")
    forbidden = (
        "artifacts/" + "a1_10", "data/" + "test", "test_" + "manifest",
        "test_" + "label", "test_" + "eligibility",
    )
    hits = [token for token in forbidden if token in source.lower()]
    if hits:
        raise IntegrityError(f"official-test dependency exists in A2.1 source: {hits}")
    return {
        "training_calls": 0, "a1_metric_computation_calls": 0,
        "official_test_dependency_hits": 0, "source_sha256": sha256_path(SCRIPT_PATH),
    }


def verify_prerun(require_clean: bool = True) -> dict[str, Any]:
    """Verify every frozen gate before any benchmark worker starts."""
    status = git_output(["status", "--porcelain"])
    if require_clean and status:
        raise IntegrityError(f"Git worktree is not clean: {status}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREG_COMMIT, "HEAD"], cwd=REPO_ROOT).returncode:
        raise IntegrityError("A2.1 preregistration commit is not an ancestor of HEAD")
    if subprocess.run(
        ["git", "diff", "--quiet", PREREG_COMMIT, "HEAD", "--", TASKBOOK_PATH], cwd=REPO_ROOT
    ).returncode:
        raise IntegrityError("A2.1 taskbook differs from the preregistration commit")
    expected_files = {
        TASKBOOK_PATH: TASKBOOK_SHA256, CLAIM_MATRIX_PATH: CLAIM_MATRIX_SHA256,
        MAIN_TABLE_PATH: MAIN_TABLE_SHA256, CLEANED_DEV_PATH: CLEANED_DEV_SHA256,
        PRIMARY_DEV_PATH: PRIMARY_DEV_SHA256, STRUCTURAL_PATH: STRUCTURAL_SHA256,
        FROZEN_EMBEDDING_PATH: FROZEN_EMBEDDING_SHA256,
        MODEL_MANIFEST_PATH: MODEL_MANIFEST_SHA256, QWEN_WEIGHT_PATH: QWEN_WEIGHT_SHA256,
        B2_MODEL_PATH: B2_MODEL_SHA256, B2_SECONDARY_MODEL_PATH: B2_SECONDARY_MODEL_SHA256,
        B4_MODEL_PATH: B4_MODEL_SHA256,
    }
    verified_hashes = {path: verify_file(path, digest) for path, digest in expected_files.items()}
    structural = read_csv(resolve(STRUCTURAL_PATH))
    actual_features = tuple(name for name in structural[0] if name not in {"trajectory_key", "content_sha256"})
    if len(structural) != TRAJECTORY_COUNT or actual_features != FEATURE_NAMES:
        raise IntegrityError("B2 structural full13 contract changed")
    import numpy as np
    embedding = np.load(resolve(FROZEN_EMBEDDING_PATH), mmap_mode="r", allow_pickle=False)
    if embedding.shape != (TRAJECTORY_COUNT, B4_DIMENSION) or embedding.dtype != np.float32:
        raise IntegrityError("B4 frozen embedding shape/dtype contract changed")
    manifest = json.loads(resolve(MODEL_MANIFEST_PATH).read_text(encoding="utf-8"))
    if manifest["immutable_revision"] != QWEN_REVISION or manifest["hidden_size"] != B4_DIMENSION:
        raise IntegrityError("Qwen revision or B4 dimension changed")
    if manifest["weight_sha256"] != QWEN_WEIGHT_SHA256:
        raise IntegrityError("Qwen weight identity changed")
    final_manifest = json.loads(resolve(FINAL_MODEL_MANIFEST_PATH).read_text(encoding="utf-8"))
    by_method = {row["method_id"]: row for row in final_manifest["models"]}
    expected_models = {
        "FINAL_SUCCESS_B2": B2_MODEL_SHA256,
        "FINAL_LOOPING_B2": B2_SECONDARY_MODEL_SHA256,
        "FINAL_SIDE_EFFECT_B4": B4_MODEL_SHA256,
    }
    for method, digest in expected_models.items():
        if by_method[method]["artifact_sha256"] != digest:
            raise IntegrityError(f"frozen classifier changed: {method}")
    if by_method["FINAL_SIDE_EFFECT_B4"]["qwen"]["immutable_revision"] != QWEN_REVISION:
        raise IntegrityError("frozen classifier Qwen revision changed")
    return {
        "git_clean": status == "", "git_commit": git_output(["rev-parse", "HEAD"]),
        "preregistration_commit": PREREG_COMMIT, "taskbook_unchanged_from_prereg": True,
        "verified_hashes": verified_hashes, "trajectory_count": TRAJECTORY_COUNT,
        "b2_dimension": B2_DIMENSION, "b4_dimension": B4_DIMENSION,
        "qwen_revision": QWEN_REVISION, "static_guards": source_static_guards(),
    }


def _b2_matrix(cleaned: dict[str, dict[str, Any]], extractor: Any) -> tuple[list[str], Any]:
    """Extract the frozen full13 matrix in sorted trajectory-key order."""
    import numpy as np
    keys = sorted(cleaned)
    values = []
    for key in keys:
        features = extractor(cleaned[key])
        if tuple(features) != FEATURE_NAMES:
            raise IntegrityError("B2 extractor feature order changed")
        values.append([features[name] for name in FEATURE_NAMES])
    matrix = np.asarray(values, dtype=np.float64)
    if matrix.shape != (TRAJECTORY_COUNT, B2_DIMENSION) or not np.isfinite(matrix).all():
        raise IntegrityError("B2 extraction shape/finite guard failed")
    return keys, matrix


def run_b2_worker(output_path: Path) -> None:
    """Measure cold and warm B2 extraction in the frozen baseline environment."""
    import numpy as np
    import run_stage_a1_2_baselines as a12

    parent_start_ns = int(os.environ["A2_1_PARENT_START_NS"])
    cleaned = a12.read_jsonl(resolve(CLEANED_DEV_PATH))
    if len(cleaned) != TRAJECTORY_COUNT:
        raise IntegrityError("cleaned dev corpus is not exactly 196 trajectories")
    first_key = sorted(cleaned)[0]
    first = a12.extract_structural_features(cleaned[first_key])
    if tuple(first) != FEATURE_NAMES:
        raise IntegrityError("B2 cold output violates full13 contract")
    cold_seconds = (time.time_ns() - parent_start_ns) / 1_000_000_000.0
    rows = [raw_row(
        method="B2", phase="cold_start", run_type="measured", run_index=1,
        trajectory_count=1, dimension=B2_DIMENSION, device="cpu",
        total_seconds=cold_seconds, peak_cpu=peak_rss_mb(),
        notes="fresh process + frozen extractor import + cleaned-input load + first usable 13-d output",
    )]

    progress("B2 extraction warmup start")
    started = time.perf_counter()
    _, warm_matrix = _b2_matrix(cleaned, a12.extract_structural_features)
    elapsed = time.perf_counter() - started
    rows.append(raw_row(
        method="B2", phase="warm_extraction", run_type="warmup", run_index=0,
        trajectory_count=TRAJECTORY_COUNT, dimension=B2_DIMENSION, device="cpu",
        total_seconds=elapsed, peak_cpu=peak_rss_mb(), notes="excluded from summary median",
    ))
    del warm_matrix

    last_keys: list[str] = []
    last_matrix: Any = None
    for run_index in range(1, B2_MEASURED_REPETITIONS + 1):
        started = time.perf_counter()
        last_keys, last_matrix = _b2_matrix(cleaned, a12.extract_structural_features)
        elapsed = time.perf_counter() - started
        rows.append(raw_row(
            method="B2", phase="warm_extraction", run_type="measured", run_index=run_index,
            trajectory_count=TRAJECTORY_COUNT, dimension=B2_DIMENSION, device="cpu",
            total_seconds=elapsed, peak_cpu=peak_rss_mb(), notes="full frozen dev extraction",
        ))
        progress(f"B2 measured extraction {run_index}/{B2_MEASURED_REPETITIONS} complete")

    frozen_rows = read_csv(resolve(STRUCTURAL_PATH))
    frozen_by_key = {
        row["trajectory_key"]: np.asarray([float(row[name]) for name in FEATURE_NAMES], dtype=np.float64)
        for row in frozen_rows
    }
    frozen_matrix = np.stack([frozen_by_key[key] for key in last_keys])
    if not np.array_equal(last_matrix, frozen_matrix):
        raise IntegrityError("B2 measured extraction does not exactly reproduce frozen features")
    representation_bytes, representation_sha256 = npy_serialization(last_matrix)
    write_json(output_path, {
        "method": "B2", "raw_rows": rows,
        "representation_bytes": representation_bytes,
        "representation_sha256": representation_sha256,
        "representation_serialization": "NumPy .npy, float64, allow_pickle=false",
        "device": "cpu", "dimension": B2_DIMENSION,
        "trajectory_count": TRAJECTORY_COUNT, "exact_frozen_reproduction": True,
    })


def _embed_all(
    a17: Any, config: dict[str, Any], records: Sequence[dict[str, Any]],
    tokenizer: Any, model: Any, device: str, run_label: str,
) -> tuple[Any, float, float, float]:
    """Tokenize and embed all 196 records under the exact A1.7 contract."""
    import numpy as np
    import torch

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    _, payloads = a17.tokenize_records(config, records, tokenizer)
    matrix = np.empty((TRAJECTORY_COUNT, B4_DIMENSION), dtype=np.float32)
    for index, payload in enumerate(payloads, 1):
        matrix[index - 1] = a17.embed_payload(model, payload, tokenizer.eos_token_id, device)
        if index % 40 == 0 or index == TRAJECTORY_COUNT:
            progress(f"B4 {run_label}: {index}/{TRAJECTORY_COUNT}")
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    allocated = float(torch.cuda.max_memory_allocated()) / MIB
    reserved = float(torch.cuda.max_memory_reserved()) / MIB
    if matrix.shape != (TRAJECTORY_COUNT, B4_DIMENSION) or matrix.dtype != np.float32:
        raise IntegrityError("B4 measured matrix shape/dtype guard failed")
    if not np.isfinite(matrix).all():
        raise IntegrityError("B4 measured matrix contains non-finite values")
    return matrix, elapsed, allocated, reserved


def run_b4_worker(output_path: Path) -> None:
    """Measure cold/model-load and warm B4 extraction in the semantic environment."""
    import numpy as np
    import torch
    import extract_stage_a1_7_embeddings as a17

    parent_start_ns = int(os.environ["A2_1_PARENT_START_NS"])
    config = a17.load_config()
    records = a17.read_primary(config)
    if len(records) != TRAJECTORY_COUNT:
        raise IntegrityError("primary dev corpus is not exactly 196 trajectories")
    a17.configure_determinism(2026)
    tokenizer = a17.load_tokenizer(config)
    first_payload = tokenizer.encode(records[0]["serialized_text"], add_special_tokens=False)

    torch.cuda.reset_peak_memory_stats()
    load_started = time.perf_counter()
    model, device = a17.load_model(config)
    torch.cuda.synchronize()
    model_load_seconds = time.perf_counter() - load_started
    if not torch.cuda.is_available() or not str(device).startswith("cuda"):
        raise IntegrityError("B4 actual embedding device is not CUDA")
    model_load_allocated = float(torch.cuda.max_memory_allocated()) / MIB
    model_load_reserved = float(torch.cuda.max_memory_reserved()) / MIB
    model_load_rss = peak_rss_mb()
    first_vector = a17.embed_payload(model, first_payload, tokenizer.eos_token_id, device)
    torch.cuda.synchronize()
    if first_vector.shape != (B4_DIMENSION,):
        raise IntegrityError("B4 cold first output is not 1024-dimensional")
    cold_seconds = (time.time_ns() - parent_start_ns) / 1_000_000_000.0
    rows = [
        raw_row(
            method="B4", phase="model_load", run_type="measured", run_index=1,
            trajectory_count=0, dimension=B4_DIMENSION, device=str(device),
            total_seconds=model_load_seconds, peak_cpu=model_load_rss,
            peak_gpu_allocated=model_load_allocated, peak_gpu_reserved=model_load_reserved,
            notes="pinned local Qwen load only; tokenizer load excluded",
        ),
        raw_row(
            method="B4", phase="cold_start", run_type="measured", run_index=1,
            trajectory_count=1, dimension=B4_DIMENSION, device=str(device),
            total_seconds=cold_seconds, peak_cpu=peak_rss_mb(),
            peak_gpu_allocated=float(torch.cuda.max_memory_allocated()) / MIB,
            peak_gpu_reserved=float(torch.cuda.max_memory_reserved()) / MIB,
            notes="fresh process + tokenizer/model initialization + first usable 1024-d CUDA output",
        ),
    ]

    progress("B4 extraction warmup start")
    warm_matrix, warm_seconds, warm_allocated, warm_reserved = _embed_all(
        a17, config, records, tokenizer, model, device, "warmup"
    )
    rows.append(raw_row(
        method="B4", phase="warm_extraction", run_type="warmup", run_index=0,
        trajectory_count=TRAJECTORY_COUNT, dimension=B4_DIMENSION, device=str(device),
        total_seconds=warm_seconds, peak_cpu=peak_rss_mb(),
        peak_gpu_allocated=warm_allocated, peak_gpu_reserved=warm_reserved,
        notes="tokenization + full frozen encoder extraction; excluded from summary median",
    ))
    del warm_matrix

    frozen = np.load(resolve(FROZEN_EMBEDDING_PATH), allow_pickle=False)
    last_matrix: Any = None
    measured_hashes: list[str] = []
    for run_index in range(1, B4_MEASURED_REPETITIONS + 1):
        last_matrix, elapsed, allocated, reserved = _embed_all(
            a17, config, records, tokenizer, model, device, f"measured-{run_index}"
        )
        if not np.array_equal(last_matrix, frozen):
            raise IntegrityError(f"B4 measured run {run_index} does not exactly reproduce frozen embeddings")
        _, run_sha256 = npy_serialization(last_matrix)
        if run_sha256 != FROZEN_EMBEDDING_SHA256:
            raise IntegrityError(f"B4 measured run {run_index} serialized hash changed")
        measured_hashes.append(run_sha256)
        rows.append(raw_row(
            method="B4", phase="warm_extraction", run_type="measured", run_index=run_index,
            trajectory_count=TRAJECTORY_COUNT, dimension=B4_DIMENSION, device=str(device),
            total_seconds=elapsed, peak_cpu=peak_rss_mb(),
            peak_gpu_allocated=allocated, peak_gpu_reserved=reserved,
            notes="tokenization + full frozen encoder extraction",
        ))
        progress(f"B4 measured extraction {run_index}/{B4_MEASURED_REPETITIONS} complete")

    representation_bytes, representation_sha256 = npy_serialization(last_matrix)
    snapshot_bytes = sum(path.stat().st_size for path in resolve(QWEN_SNAPSHOT).rglob("*") if path.is_file())
    write_json(output_path, {
        "method": "B4", "raw_rows": rows,
        "representation_bytes": representation_bytes,
        "representation_sha256": representation_sha256,
        "representation_serialization": "NumPy .npy, float32, allow_pickle=false",
        "device": str(device), "gpu_name": torch.cuda.get_device_name(0),
        "dimension": B4_DIMENSION, "trajectory_count": TRAJECTORY_COUNT,
        "model_load_seconds": model_load_seconds,
        "encoder_weight_bytes": resolve(QWEN_WEIGHT_PATH).stat().st_size,
        "semantic_snapshot_bytes": snapshot_bytes, "qwen_revision": QWEN_REVISION,
        "measured_embedding_hashes": measured_hashes, "exact_frozen_reproduction": True,
        "semantic_runtime": {
            "python": platform.python_version(), "python_executable": sys.executable,
            "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
            "transformers": importlib.metadata.version("transformers"),
            "tokenizers": importlib.metadata.version("tokenizers"), "numpy": np.__version__,
            "gpu_name": torch.cuda.get_device_name(0),
            "gpu_capability": list(torch.cuda.get_device_capability(0)),
            "actual_device": str(device), "cuda_available": bool(torch.cuda.is_available()),
        },
    })


def _load_b2_matrix() -> Any:
    """Load the frozen full13 matrix without any label join."""
    import numpy as np
    rows = read_csv(resolve(STRUCTURAL_PATH))
    rows.sort(key=lambda row: row["trajectory_key"])
    matrix = np.asarray([[float(row[name]) for name in FEATURE_NAMES] for row in rows], dtype=np.float64)
    if matrix.shape != (TRAJECTORY_COUNT, B2_DIMENSION):
        raise IntegrityError("B2 inference matrix shape changed")
    return matrix


def run_inference_worker(method: str, output_path: Path) -> None:
    """Measure only reload plus predict_proba for one frozen classifier."""
    import joblib
    import numpy as np

    if method == "B2":
        model_path, matrix, dimension = resolve(B2_MODEL_PATH), _load_b2_matrix(), B2_DIMENSION
        repetitions, artifact, model_sha256 = B2_MEASURED_REPETITIONS, B2_MODEL_PATH, B2_MODEL_SHA256
        note = "FINAL_SUCCESS_B2; StandardScaler + frozen LogisticRegression"
    elif method == "B4":
        model_path = resolve(B4_MODEL_PATH)
        matrix = np.load(resolve(FROZEN_EMBEDDING_PATH), allow_pickle=False)
        dimension, repetitions = B4_DIMENSION, B4_MEASURED_REPETITIONS
        artifact, model_sha256 = B4_MODEL_PATH, B4_MODEL_SHA256
        note = "FINAL_SIDE_EFFECT_B4; frozen LogisticRegression; no scaler"
    else:
        raise IntegrityError(f"unknown inference method: {method}")
    if sha256_path(model_path) != model_sha256:
        raise IntegrityError(f"{method} classifier hash changed before reload")
    started = time.perf_counter()
    classifier = joblib.load(model_path)
    load_seconds = time.perf_counter() - started
    rows = [raw_row(
        method=method, phase="classifier_load", run_type="measured", run_index=1,
        trajectory_count=0, dimension=dimension, device="cpu",
        total_seconds=load_seconds, peak_cpu=peak_rss_mb(), notes=note,
    )]
    started = time.perf_counter()
    probability = classifier.predict_proba(matrix)
    elapsed = time.perf_counter() - started
    if probability.shape != (TRAJECTORY_COUNT, 2) or not np.isfinite(probability).all():
        raise IntegrityError(f"{method} warmup probability guard failed")
    rows.append(raw_row(
        method=method, phase="classifier_inference", run_type="warmup", run_index=0,
        trajectory_count=TRAJECTORY_COUNT, dimension=dimension, device="cpu",
        total_seconds=elapsed, peak_cpu=peak_rss_mb(), notes="excluded from summary median",
    ))
    prediction_hashes: list[str] = []
    for run_index in range(1, repetitions + 1):
        started = time.perf_counter()
        probability = classifier.predict_proba(matrix)
        elapsed = time.perf_counter() - started
        if probability.shape != (TRAJECTORY_COUNT, 2) or not np.isfinite(probability).all():
            raise IntegrityError(f"{method} measured probability guard failed")
        prediction_hashes.append(hashlib.sha256(probability.tobytes(order="C")).hexdigest())
        rows.append(raw_row(
            method=method, phase="classifier_inference", run_type="measured", run_index=run_index,
            trajectory_count=TRAJECTORY_COUNT, dimension=dimension, device="cpu",
            total_seconds=elapsed, peak_cpu=peak_rss_mb(), notes=note,
        ))
    if len(set(prediction_hashes)) != 1:
        raise IntegrityError(f"{method} probabilities changed across repetitions")
    write_json(output_path, {
        "method": method, "raw_rows": rows, "classifier_artifact": artifact,
        "classifier_size_bytes": model_path.stat().st_size,
        "classifier_sha256": model_sha256, "classifier_load_seconds": load_seconds,
        "prediction_sha256": prediction_hashes[0], "measured_repetitions": repetitions,
        "model_fits": 0,
    })


def _float(value: str | float | int) -> float:
    """Parse a required numeric artifact value."""
    if value == "NA" or value == "":
        raise IntegrityError("required numeric value is NA")
    return float(value)


def summarize(raw_rows: Sequence[dict[str, Any]], workers: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Reduce raw measured runs to the preregistered medians."""
    output: list[dict[str, Any]] = []
    for method, repetitions, representation in (
        ("B2", B2_MEASURED_REPETITIONS, "frozen structural full13"),
        ("B4", B4_MEASURED_REPETITIONS, "frozen Qwen3 dense semantic"),
    ):
        extraction = [
            _float(row["ms_per_trajectory"]) for row in raw_rows
            if row["method"] == method and row["phase"] == "warm_extraction"
            and row["run_type"] == "measured"
        ]
        inference = [
            _float(row["ms_per_trajectory"]) for row in raw_rows
            if row["method"] == method and row["phase"] == "classifier_inference"
            and row["run_type"] == "measured"
        ]
        if len(extraction) != repetitions or len(inference) != repetitions:
            raise IntegrityError(f"{method} repetition count does not match preregistration")
        cold = [
            _float(row["total_seconds"]) for row in raw_rows
            if row["method"] == method and row["phase"] == "cold_start"
            and row["run_type"] == "measured"
        ]
        if len(cold) != 1:
            raise IntegrityError(f"{method} cold-start record count changed")
        method_rows = [row for row in raw_rows if row["method"] == method]
        cpu_peak = max(_float(row["peak_cpu_rss_mb"]) for row in method_rows)
        allocated = [
            _float(row["peak_gpu_allocated_mb"]) for row in method_rows
            if row["peak_gpu_allocated_mb"] != "NA"
        ]
        reserved = [
            _float(row["peak_gpu_reserved_mb"]) for row in method_rows
            if row["peak_gpu_reserved_mb"] != "NA"
        ]
        extraction_worker = workers[f"{method}_extraction"]
        inference_worker = workers[f"{method}_inference"]
        encoder_bytes = int(extraction_worker.get("encoder_weight_bytes", 0))
        snapshot_bytes = int(extraction_worker.get("semantic_snapshot_bytes", 0))
        representation_bytes = int(extraction_worker["representation_bytes"])
        classifier_bytes = int(inference_worker["classifier_size_bytes"])
        output.append({
            "method": method, "representation": representation,
            "dimension": int(extraction_worker["dimension"]),
            "device": extraction_worker["device"], "measured_repetitions": repetitions,
            "median_extraction_ms_per_trajectory": statistics.median(extraction),
            "median_inference_ms_per_trajectory": statistics.median(inference),
            "cold_start_seconds": cold[0],
            "model_load_seconds": extraction_worker.get("model_load_seconds", "NA"),
            "representation_size_bytes": representation_bytes,
            "representation_size_mb": representation_bytes / MIB,
            "representation_serialization": extraction_worker["representation_serialization"],
            "classifier_artifact": inference_worker["classifier_artifact"],
            "classifier_artifact_size_bytes": classifier_bytes,
            "classifier_artifact_size_mb": classifier_bytes / MIB,
            "semantic_encoder_size_bytes": encoder_bytes if encoder_bytes else "NA",
            "semantic_encoder_size_mb": encoder_bytes / MIB if encoder_bytes else "NA",
            "semantic_snapshot_size_bytes": snapshot_bytes if snapshot_bytes else "NA",
            "semantic_snapshot_size_mb": snapshot_bytes / MIB if snapshot_bytes else "NA",
            "peak_cpu_rss_mb": cpu_peak,
            "peak_gpu_allocated_mb": max(allocated) if allocated else "NA",
            "peak_gpu_reserved_mb": max(reserved) if reserved else "NA",
            "peak_gpu_vram_mb": max(reserved) if reserved else "NA",
            "evidence_status": "EFFICIENCY_BENCHMARK",
        })
    return output


def safe_ratio(numerator: Any, denominator: Any) -> float | str:
    """Return a legal B4/B2 ratio or NA for a missing/zero denominator."""
    if numerator == "NA" or denominator == "NA":
        return "NA"
    bottom = float(denominator)
    return "NA" if bottom == 0.0 else float(numerator) / bottom


def relative_cost(summary_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute the five preregistered B4-over-B2 cost ratios."""
    by_method = {row["method"]: row for row in summary_rows}
    b2, b4 = by_method["B2"], by_method["B4"]
    return [{
        "dimension_ratio_B4_over_B2": safe_ratio(b4["dimension"], b2["dimension"]),
        "representation_size_ratio_B4_over_B2": safe_ratio(
            b4["representation_size_bytes"], b2["representation_size_bytes"]
        ),
        "extraction_time_ratio_B4_over_B2": safe_ratio(
            b4["median_extraction_ms_per_trajectory"], b2["median_extraction_ms_per_trajectory"]
        ),
        "classifier_inference_ratio_B4_over_B2": safe_ratio(
            b4["median_inference_ms_per_trajectory"], b2["median_inference_ms_per_trajectory"]
        ),
        "peak_memory_ratio_B4_over_B2": safe_ratio(b4["peak_cpu_rss_mb"], b2["peak_cpu_rss_mb"]),
        "ratio_direction": "B4 divided by B2; values above 1 mean B4 is more costly",
        "notes": "CPU peak ratio uses fresh-process PeakWorkingSetSize; B4 VRAM is separate",
    }]


def _cpu_name() -> str:
    """Read the Windows processor marketing name."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        ) as key:
            return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    except OSError:
        return platform.processor() or platform.machine()


def _total_ram_bytes() -> int:
    """Read installed physical RAM using GlobalMemoryStatusEx."""
    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise IntegrityError("GlobalMemoryStatusEx failed")
    return int(status.ullTotalPhys)


def _nvidia_driver() -> str:
    """Return the active NVIDIA driver version."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip().splitlines()[0]


def environment_snapshot(b4_worker: dict[str, Any]) -> dict[str, Any]:
    """Capture the machine and both frozen Python environments."""
    dependencies = {
        package: importlib.metadata.version(package)
        for package in ("numpy", "scikit-learn", "joblib")
    }
    thread_names = (
        "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "BLIS_NUM_THREADS",
        "CUBLAS_WORKSPACE_CONFIG",
    )
    ram_bytes = _total_ram_bytes()
    semantic = b4_worker["semantic_runtime"]
    return {
        "timestamp": utc_now(), "os": platform.platform(), "machine": platform.machine(),
        "python": {
            "baseline_version": platform.python_version(), "baseline_executable": sys.executable,
            "semantic_version": semantic["python"], "semantic_executable": semantic["python_executable"],
        },
        "cpu": _cpu_name(), "logical_cpu_count": os.cpu_count(),
        "ram_bytes": ram_bytes, "ram_gib": ram_bytes / (1024 ** 3),
        "gpu": semantic["gpu_name"], "gpu_capability": semantic["gpu_capability"],
        "gpu_driver": _nvidia_driver(), "cuda_runtime": semantic["cuda_runtime"],
        "torch": semantic["torch"], "transformers": semantic["transformers"],
        "tokenizers": semantic["tokenizers"],
        "numpy": {"baseline": dependencies["numpy"], "semantic": semantic["numpy"]},
        "scikit_learn": dependencies["scikit-learn"], "joblib": dependencies["joblib"],
        "thread_environment_variables": {name: os.environ.get(name) for name in thread_names},
        "semantic_offline_environment": {
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
            "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        },
        "batch_size": 1,
        "dtype": {
            "B2_representation": "float64", "B4_inference_weights": "bfloat16",
            "B4_representation": "float32",
        },
        "memory_measurement": {
            "cpu": "Windows GetProcessMemoryInfo PeakWorkingSetSize in MiB",
            "gpu": "torch.cuda reset_peak_memory_stats plus max allocated/reserved in MiB",
        },
        "timing_clock": "perf_counter phases; parent wall-clock handshake for process cold start",
    }


def _run_worker(
    interpreter: Path, arguments: Sequence[str], output_path: Path, log_path: Path,
) -> dict[str, Any]:
    """Launch one worker in its frozen environment and read its result."""
    environment = os.environ.copy()
    environment.update({
        "A2_1_PARENT_START_NS": str(time.time_ns()), "A2_1_LOG_PATH": str(log_path),
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8", "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    })
    command = [str(interpreter), str(SCRIPT_PATH), *arguments, "--worker-output", str(output_path)]
    progress(f"worker start: {' '.join(arguments)}")
    subprocess.run(command, cwd=REPO_ROOT, env=environment, check=True)
    if not output_path.is_file():
        raise IntegrityError(f"worker did not create result: {output_path}")
    value = json.loads(output_path.read_text(encoding="utf-8"))
    progress(f"worker complete: {' '.join(arguments)}")
    return value


def metadata_fingerprint(prerun: dict[str, Any], workers: dict[str, dict[str, Any]]) -> str:
    """Hash deterministic non-timing identities for verifier comparison."""
    payload = {
        "verified_hashes": prerun["verified_hashes"],
        "trajectory_count": prerun["trajectory_count"], "b2_dimension": prerun["b2_dimension"],
        "b4_dimension": prerun["b4_dimension"], "qwen_revision": prerun["qwen_revision"],
        "b2_representation_sha256": workers["B2_extraction"]["representation_sha256"],
        "b4_representation_sha256": workers["B4_extraction"]["representation_sha256"],
        "b2_classifier_sha256": workers["B2_inference"]["classifier_sha256"],
        "b4_classifier_sha256": workers["B4_inference"]["classifier_sha256"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_report(
    summary_rows: Sequence[dict[str, Any]], relative_rows: Sequence[dict[str, Any]],
    run_summary: dict[str, Any],
) -> str:
    """Render the A2.1 report without recomputing A1 metrics."""
    by_method = {row["method"]: row for row in summary_rows}
    b2, b4, ratios = by_method["B2"], by_method["B4"], relative_rows[0]
    context = read_csv(resolve(MAIN_TABLE_PATH))
    context_lines = "\n".join(
        f"| {row['Target']} | {row['Final Method']} | {row['AP']} | {row['Final Grade']} |"
        for row in context if row["Target"] in {"Success", "Looping", "Side Effect"}
    )
    return f"""# Stage A2.1 Efficiency & Cost Benchmark Report

## Stage determination

`{run_summary['stage_determination']}`

This report measures computational cost only under the recorded machine. It does not select a model or recompute scientific performance.

## Frozen gates

- Claim matrix SHA-256: `{CLAIM_MATRIX_SHA256}` (verified)
- Main table SHA-256: `{MAIN_TABLE_SHA256}` (verified)
- Corpus: {TRAJECTORY_COUNT} frozen dev trajectories
- B2: {B2_DIMENSION} dimensions, frozen structural extractor, CPU
- B4: {B4_DIMENSION} dimensions, revision `{QWEN_REVISION}`, device `{b4['device']}`
- Model fits / A1 metric recomputations / official-test access or tuning: 0

## Measurement definitions

- Cold start: fresh process, frozen input load, initialization, and first usable output.
- Warm extraction: full corpus after one excluded warmup. B4 includes tokenization and encoder forwards.
- Classifier inference: existing representation; reload is outside timed `predict_proba`.
- Storage: both matrices serialized as NumPy `.npy`; B2 float64, B4 float32.
- CPU peak: Windows peak working set. GPU peak: PyTorch reserved memory.

## Efficiency results

| Method | Dim | Device | Cold s | Extraction ms/traj | Inference ms/traj | Repr MiB | Classifier MiB | Encoder MiB | CPU RSS MiB | GPU VRAM MiB |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| B2 | {b2['dimension']} | {b2['device']} | {float(b2['cold_start_seconds']):.6f} | {float(b2['median_extraction_ms_per_trajectory']):.6f} | {float(b2['median_inference_ms_per_trajectory']):.6f} | {float(b2['representation_size_mb']):.6f} | {float(b2['classifier_artifact_size_mb']):.6f} | NA | {float(b2['peak_cpu_rss_mb']):.3f} | NA |
| B4 | {b4['dimension']} | {b4['device']} | {float(b4['cold_start_seconds']):.6f} | {float(b4['median_extraction_ms_per_trajectory']):.6f} | {float(b4['median_inference_ms_per_trajectory']):.6f} | {float(b4['representation_size_mb']):.6f} | {float(b4['classifier_artifact_size_mb']):.6f} | {float(b4['semantic_encoder_size_mb']):.3f} | {float(b4['peak_cpu_rss_mb']):.3f} | {float(b4['peak_gpu_vram_mb']):.3f} |

B4 model load: {float(b4['model_load_seconds']):.6f} s. Encoder is the pinned weight file; full snapshot is {float(b4['semantic_snapshot_size_mb']):.3f} MiB.

## Relative cost (B4 / B2)

- Dimension: {float(ratios['dimension_ratio_B4_over_B2']):.6f}x
- Representation storage: {float(ratios['representation_size_ratio_B4_over_B2']):.6f}x
- Warm extraction: {float(ratios['extraction_time_ratio_B4_over_B2']):.6f}x
- Classifier-only inference: {float(ratios['classifier_inference_ratio_B4_over_B2']):.6f}x
- Peak CPU RSS: {float(ratios['peak_memory_ratio_B4_over_B2']):.6f}x

Ratios apply only to this environment. They do not establish predictive superiority or universal hardware superiority.

## Frozen A1 context (exact artifact read; not recomputed)

| Target | Frozen method | Frozen AP string | Frozen grade |
|---|---|---:|---|
{context_lines}

Source: `{MAIN_TABLE_PATH}` at the verified hash above. No A1 metric function was called.

## Repetitions and scope

- B2: 1 warmup + {B2_MEASURED_REPETITIONS} measured extraction and inference runs.
- B4: 1 warmup + {B4_MEASURED_REPETITIONS} measured extraction and inference runs.
- Summary: median; no fastest-run selection.
- Formal commit: `{run_summary['formal_git_commit']}`
- Run directory: `{run_summary['run_directory']}`
- A1 metric recomputations = 0; model fits = 0; A1 model/threshold changes = 0.
- Official-test access/tuning = 0; A2.2/A2.3/external validation/A3 = 0.

## Limitations

- Timing is environment-specific and may reflect OS background activity.
- B2 inference uses frozen `FINAL_SUCCESS_B2`; B4 uses frozen `FINAL_SIDE_EFFECT_B4`.
- The additional frozen Looping B2 artifact is size-audited, not used to fabricate another timing result.
- CPU RSS and GPU reserved memory are different resource domains and are separate.

`WAIT_FOR_HUMAN_A2_1_REVIEW`
"""


def run_formal() -> None:
    """Run all A2.1 workers once and create the six required outputs."""
    prerun = verify_prerun(require_clean=True)
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", IMPLEMENTATION_COMMIT, "HEAD"], cwd=REPO_ROOT
    ).returncode:
        raise IntegrityError("formal run does not descend from the independent implementation commit")
    commit = prerun["git_commit"]
    run_id = f"a2_1_efficiency_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{commit[:8]}"
    run_directory = REPO_ROOT / "runs" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)
    log_path = run_directory / "stdout.log"
    atomic_write_text(run_directory / "command.txt", f"{sys.executable} {SCRIPT_PATH} --run\n")
    environment = os.environ.copy()
    environment["A2_1_LOG_PATH"] = str(log_path)
    os.environ["A2_1_LOG_PATH"] = str(log_path)
    progress(f"A2.1 formal run start: {run_id}")
    baseline_python = REPO_ROOT / ".venv-baselines" / "Scripts" / "python.exe"
    semantic_python = REPO_ROOT / ".venv-semantic" / "Scripts" / "python.exe"
    if not baseline_python.is_file() or not semantic_python.is_file():
        raise IntegrityError("frozen baseline or semantic environment is missing")
    workers = {
        "B2_extraction": _run_worker(
            baseline_python, ["--worker", "b2"], run_directory / "b2_extraction.json", log_path
        ),
        "B4_extraction": _run_worker(
            semantic_python, ["--worker", "b4"], run_directory / "b4_extraction.json", log_path
        ),
        "B2_inference": _run_worker(
            baseline_python, ["--worker", "inference", "--method", "B2"],
            run_directory / "b2_inference.json", log_path,
        ),
        "B4_inference": _run_worker(
            baseline_python, ["--worker", "inference", "--method", "B4"],
            run_directory / "b4_inference.json", log_path,
        ),
    }
    raw_rows: list[dict[str, Any]] = []
    for key in ("B2_extraction", "B2_inference", "B4_extraction", "B4_inference"):
        raw_rows.extend(workers[key]["raw_rows"])
    summary_rows = summarize(raw_rows, workers)
    relative_rows = relative_cost(summary_rows)
    machine_environment = environment_snapshot(workers["B4_extraction"])
    fingerprint = metadata_fingerprint(prerun, workers)
    machine_summary = {
        "stage": "A2.1", "stage_determination": "PASS",
        "started_from_clean_git": True, "formal_git_commit": commit,
        "preregistration_commit": PREREG_COMMIT, "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_commit_subject": EXPECTED_IMPLEMENTATION_SUBJECT,
        "run_id": run_id, "run_directory": run_directory.relative_to(REPO_ROOT).as_posix(),
        "completed_at_utc": utc_now(), "trajectory_count": TRAJECTORY_COUNT,
        "b2_dimension": B2_DIMENSION, "b4_dimension": B4_DIMENSION,
        "qwen_revision": QWEN_REVISION,
        "b4_actual_device": workers["B4_extraction"]["device"],
        "b4_gpu_name": workers["B4_extraction"]["gpu_name"],
        "verified_hashes": prerun["verified_hashes"], "metadata_fingerprint": fingerprint,
        "repetitions": {
            "B2": {"warmup": WARMUP_REPETITIONS, "measured": B2_MEASURED_REPETITIONS},
            "B4": {"warmup": WARMUP_REPETITIONS, "measured": B4_MEASURED_REPETITIONS},
            "summary": "median",
        },
        "counters": {
            "a1_metric_recomputations": 0, "model_fits": 0, "a1_model_changes": 0,
            "a1_threshold_changes": 0, "official_test_access": 0,
            "official_test_tuning": 0, "new_features": 0,
            "second_embedding_models": 0, "a2_2": 0, "a2_3": 0,
            "external_validation": 0, "a3": 0,
        },
        "warnings": [],
        "classifier_scope": {
            "B2_timed": B2_MODEL_PATH, "B2_additional_size_audited": B2_SECONDARY_MODEL_PATH,
            "B4_timed": B4_MODEL_PATH,
        },
        "output_paths": {
            key: path.relative_to(REPO_ROOT).as_posix() for key, path in OUTPUT_PATHS.items()
        },
    }
    write_json(OUTPUT_PATHS["environment"], machine_environment)
    write_csv(OUTPUT_PATHS["raw"], raw_rows, RAW_FIELDS)
    write_csv(OUTPUT_PATHS["summary"], summary_rows, SUMMARY_FIELDS)
    write_csv(OUTPUT_PATHS["relative"], relative_rows, RELATIVE_FIELDS)
    write_json(OUTPUT_PATHS["run_summary"], machine_summary)
    atomic_write_text(OUTPUT_PATHS["report"], build_report(summary_rows, relative_rows, machine_summary))
    verify_results(require_current_prerun=False)
    progress("A2.1 formal run and independent verifier complete")


def verify_results(require_current_prerun: bool = True) -> dict[str, Any]:
    """Verify schemas, medians, ratios, counters, and frozen identities."""
    current_prerun = verify_prerun(require_clean=False) if require_current_prerun else None
    for path in OUTPUT_PATHS.values():
        if not path.is_file():
            raise IntegrityError(f"missing A2.1 output: {path.relative_to(REPO_ROOT)}")
    raw = read_csv(OUTPUT_PATHS["raw"])
    summary = read_csv(OUTPUT_PATHS["summary"])
    relative = read_csv(OUTPUT_PATHS["relative"])
    machine = json.loads(OUTPUT_PATHS["run_summary"].read_text(encoding="utf-8"))
    environment = json.loads(OUTPUT_PATHS["environment"].read_text(encoding="utf-8"))
    if not raw or not summary or not relative:
        raise IntegrityError("empty A2.1 machine-readable output")
    if tuple(raw[0]) != RAW_FIELDS or tuple(summary[0]) != SUMMARY_FIELDS or tuple(relative[0]) != RELATIVE_FIELDS:
        raise IntegrityError("A2.1 output schema changed")
    if len(summary) != 2 or {row["method"] for row in summary} != {"B2", "B4"}:
        raise IntegrityError("summary must contain exactly B2 and B4")
    expected_measured = {"B2": B2_MEASURED_REPETITIONS, "B4": B4_MEASURED_REPETITIONS}
    for method, repetitions in expected_measured.items():
        extraction = [
            _float(row["ms_per_trajectory"]) for row in raw
            if row["method"] == method and row["phase"] == "warm_extraction"
            and row["run_type"] == "measured"
        ]
        inference = [
            _float(row["ms_per_trajectory"]) for row in raw
            if row["method"] == method and row["phase"] == "classifier_inference"
            and row["run_type"] == "measured"
        ]
        warm_extract = [
            row for row in raw if row["method"] == method and row["phase"] == "warm_extraction"
            and row["run_type"] == "warmup"
        ]
        warm_infer = [
            row for row in raw if row["method"] == method and row["phase"] == "classifier_inference"
            and row["run_type"] == "warmup"
        ]
        if len(extraction) != repetitions or len(inference) != repetitions:
            raise IntegrityError(f"{method} measured repetitions changed")
        if len(warm_extract) != 1 or len(warm_infer) != 1:
            raise IntegrityError(f"{method} warmup repetitions changed")
        row = next(item for item in summary if item["method"] == method)
        if abs(_float(row["median_extraction_ms_per_trajectory"]) - statistics.median(extraction)) > 1e-12:
            raise IntegrityError(f"{method} raw-to-median extraction mismatch")
        if abs(_float(row["median_inference_ms_per_trajectory"]) - statistics.median(inference)) > 1e-12:
            raise IntegrityError(f"{method} raw-to-median inference mismatch")
    by_method = {row["method"]: row for row in summary}
    expected_ratios = {
        "dimension_ratio_B4_over_B2": safe_ratio(by_method["B4"]["dimension"], by_method["B2"]["dimension"]),
        "representation_size_ratio_B4_over_B2": safe_ratio(
            by_method["B4"]["representation_size_bytes"], by_method["B2"]["representation_size_bytes"]
        ),
        "extraction_time_ratio_B4_over_B2": safe_ratio(
            by_method["B4"]["median_extraction_ms_per_trajectory"],
            by_method["B2"]["median_extraction_ms_per_trajectory"],
        ),
        "classifier_inference_ratio_B4_over_B2": safe_ratio(
            by_method["B4"]["median_inference_ms_per_trajectory"],
            by_method["B2"]["median_inference_ms_per_trajectory"],
        ),
        "peak_memory_ratio_B4_over_B2": safe_ratio(
            by_method["B4"]["peak_cpu_rss_mb"], by_method["B2"]["peak_cpu_rss_mb"]
        ),
    }
    for field, expected in expected_ratios.items():
        actual = relative[0][field]
        if expected == "NA":
            if actual != "NA":
                raise IntegrityError(f"relative ratio {field} should be NA")
        elif abs(float(actual) - float(expected)) > 1e-12:
            raise IntegrityError(f"relative ratio arithmetic mismatch: {field}")
    if int(by_method["B2"]["dimension"]) != B2_DIMENSION:
        raise IntegrityError("B2 summary dimension changed")
    if int(by_method["B4"]["dimension"]) != B4_DIMENSION or not by_method["B4"]["device"].startswith("cuda"):
        raise IntegrityError("B4 summary dimension/device changed")
    if machine["qwen_revision"] != QWEN_REVISION or machine["trajectory_count"] != TRAJECTORY_COUNT:
        raise IntegrityError("machine summary frozen identity changed")
    if any(value != 0 for value in machine["counters"].values()):
        raise IntegrityError("prohibited-operation counter is nonzero")
    if not environment["gpu"] or environment["batch_size"] != 1:
        raise IntegrityError("environment output is incomplete")
    if current_prerun and machine["verified_hashes"] != current_prerun["verified_hashes"]:
        raise IntegrityError("frozen hashes differ from formal run record")
    return {
        "verified": True, "raw_rows": len(raw), "summary_rows": len(summary),
        "relative_rows": len(relative), "repetition_counts": expected_measured,
        "raw_to_median": True, "ratio_arithmetic": True, "output_schema": True,
        "prohibited_counters_zero": True,
    }


def parse_args() -> argparse.Namespace:
    """Parse orchestrator and private worker modes."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--verify-prerun", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--verify-results", action="store_true")
    modes.add_argument("--worker", choices=("b2", "b4", "inference"))
    parser.add_argument("--method", choices=("B2", "B4"))
    parser.add_argument("--worker-output", type=Path)
    return parser.parse_args()


def main() -> int:
    """Dispatch verification, formal run, or an isolated worker."""
    args = parse_args()
    try:
        if args.verify_prerun:
            print(json.dumps(verify_prerun(require_clean=True), indent=2, sort_keys=True))
        elif args.run:
            run_formal()
        elif args.verify_results:
            print(json.dumps(verify_results(require_current_prerun=True), indent=2, sort_keys=True))
        else:
            if args.worker_output is None:
                raise IntegrityError("worker mode requires --worker-output")
            output_path = args.worker_output.resolve()
            if args.worker == "b2":
                run_b2_worker(output_path)
            elif args.worker == "b4":
                run_b4_worker(output_path)
            elif args.worker == "inference":
                if args.method is None:
                    raise IntegrityError("inference worker requires --method")
                run_inference_worker(args.method, output_path)
            else:
                raise IntegrityError("unknown worker mode")
        return 0
    except Exception as exc:
        print(f"A2.1 STOP: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
