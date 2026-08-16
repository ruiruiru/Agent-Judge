"""Verify frozen Stage A1.1 evaluation manifests without modifying them."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_CONFIG = ROOT / "configs" / "evaluation_protocol.yaml"


def sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest of *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_protocol(path: Path = PROTOCOL_CONFIG) -> dict[str, Any]:
    """Load the JSON-compatible YAML 1.2 protocol configuration."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("evaluation protocol must be a mapping")
    return data


def locked_manifests(config: Mapping[str, Any]) -> dict[str, str]:
    """Collect every path/hash lock declared by the frozen protocol."""
    sections = (
        config["outer_cv"]["authoritative_manifests"],
        config["lobo"]["authoritative_manifests"],
        config["leave_one_model_out"]["authoritative_manifests"],
    )
    locks: dict[str, str] = {}
    for section in sections:
        for relative_path, expected_hash in section.items():
            if relative_path in locks:
                raise ValueError(f"duplicate manifest lock: {relative_path}")
            locks[relative_path] = str(expected_hash).lower()
    return locks


def verify_frozen_manifests(config_path: Path = PROTOCOL_CONFIG) -> dict[str, str]:
    """Verify every frozen manifest and return its observed SHA-256 digest."""
    config = load_protocol(config_path)
    if config["outer_cv"]["algorithm"] != "custom_deterministic_grouped_stratification_v1":
        raise ValueError("unexpected outer-CV algorithm declaration")
    if config["outer_cv"]["regeneration_allowed"] is not False:
        raise ValueError("frozen outer-CV manifests must prohibit regeneration")
    observed: dict[str, str] = {}
    for relative_path, expected_hash in locked_manifests(config).items():
        candidate = (ROOT / relative_path).resolve()
        try:
            candidate.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"manifest path escapes repository: {relative_path}") from exc
        if not candidate.is_file():
            raise FileNotFoundError(f"frozen manifest missing: {relative_path}")
        actual_hash = sha256_file(candidate)
        if actual_hash != expected_hash:
            raise ValueError(
                f"frozen manifest SHA-256 mismatch: {relative_path}; "
                f"expected={expected_hash}; actual={actual_hash}"
            )
        observed[relative_path] = actual_hash
    return observed


def main() -> int:
    """Run the read-only preflight check and print machine-readable evidence."""
    observed = verify_frozen_manifests()
    print(json.dumps({"status": "PASS", "verified_manifests": observed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
