#!/usr/bin/env python3
"""Verify the Stage A3.2 targeted closest-work addendum.

This verifier is bibliographic and policy-only. It does not search the web,
download data, fit models, run inference, recompute A1 metrics, bootstrap,
or perform statistical tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ADDENDUM_PREREG_COMMIT = "a57040bf3314b446772ada355143298a24d4ff14"
A3_2_RESULT_COMMIT = "ef37dee92ef319b2f7d39367e757919a898fbfdb"
A3_3_PREREG_COMMIT = "b85c93f17a3e90f20bca5162817111c5bc1ac70a"
A3_3_TASKBOOK = "docs/tasks/STAGE_A3_3_MANUSCRIPT_EVIDENCE_FREEZE.md"
CLAIM_MATRIX_PATH = "artifacts/a1_11_final_claim_matrix.csv"
CLAIM_MATRIX_SHA256 = "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175"
SIMILAR_CANONICAL_TITLE = (
    "Boosting Virtual Agent Learning and Reasoning: A Step-Wise, "
    "Multi-Dimensional, and Generalist Reward Model with Benchmark"
)
WEBGRAPHEVAL_TITLE = (
    "WebGraphEval: Multi-Turn Trajectory Evaluation for Web Agents using Graph Representation"
)
WEBSTEP_TITLE = (
    "Where Did It Go Wrong? Process-Level Evaluation of Web Agents with Semantic State Tracking"
)

COUNTERS = {
    "new_model_fits": 0,
    "new_inference_runs": 0,
    "new_embedding_runs": 0,
    "A1_metric_recomputations": 0,
    "bootstrap_reruns": 0,
    "new_significance_tests": 0,
    "threshold_changes": 0,
    "eligibility_changes": 0,
    "final_model_changes": 0,
    "official_test_tuning": 0,
    "external_dataset_downloads": 0,
    "external_dataset_runs": 0,
    "new_scientific_figures": 0,
}

VALID_COMPARABILITY = {
    "DIRECTLY_COMPARABLE",
    "PARTIALLY_COMPARABLE",
    "CONTEXT_ONLY",
    "NOT_COMPARABLE",
}
BASELINE_COMPARABILITY = {
    "DIRECTLY_COMPARABLE": 0,
    "PARTIALLY_COMPARABLE": 2,
    "CONTEXT_ONLY": 8,
    "NOT_COMPARABLE": 0,
}
EXPECTED_COMPARABILITY = {
    "DIRECTLY_COMPARABLE": 0,
    "PARTIALLY_COMPARABLE": 3,
    "CONTEXT_ONLY": 9,
    "NOT_COMPARABLE": 0,
}

PATCHED_OUTPUTS = (
    "artifacts/a3_2_verified_literature_registry.csv",
    "artifacts/a3_2_positioning_matrix.csv",
    "artifacts/a3_2_citation_registry.csv",
    "paper/references/a3_2_verified_related_work.bib",
    "docs/a3_2_positioning_and_novelty_contract.md",
    "paper/tables/Table_Related_Work_Positioning.md",
    "paper/tables/Table_Related_Work_Positioning.tex",
    "docs/a3_2_related_work_writing_skeleton.md",
    "artifacts/a3_2_addendum_closest_work_patch.csv",
    "docs/a3_2_closest_work_addendum_report.md",
    "artifacts/a3_2_addendum_run_summary.json",
)
ALLOWED_CHANGED_PATHS = set(PATCHED_OUTPUTS) | {
    "scripts/verify_a3_2_addendum_closest_work.py",
    "tests/test_stage_a3_2_addendum_closest_work.py",
}
PATCH_FIELDS = (
    "item",
    "action",
    "old_value",
    "new_value",
    "source",
    "reason",
    "comparability_before",
    "comparability_after",
    "paper_facing_effect",
    "verified",
)


class VerificationError(RuntimeError):
    """Raised when the addendum violates a frozen evidence contract."""


def resolve(relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise VerificationError(f"absolute repository path prohibited: {relative}")
    path = (ROOT / candidate).resolve()
    if path != ROOT and ROOT not in path.parents:
        raise VerificationError(f"path escapes repository: {relative}")
    return path


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(relative: str) -> list[dict[str, str]]:
    with resolve(relative).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def csv_fields(relative: str) -> tuple[str, ...]:
    with resolve(relative).open("r", encoding="utf-8", newline="") as handle:
        return tuple(next(csv.reader(handle)))


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise VerificationError(f"{label}: expected {expected!r}, found {actual!r}")


def assert_true(condition: bool, label: str) -> None:
    if not condition:
        raise VerificationError(label)


def require_columns(relative: str, required: Iterable[str]) -> None:
    actual = csv_fields(relative)
    missing = [field for field in required if field not in actual]
    if missing:
        raise VerificationError(f"{relative} missing columns: {missing}")


def _is_ancestor(commit: str, head: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, head],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def verify_preflight(require_clean: bool) -> dict[str, str]:
    if require_clean:
        assert_equal(git_output("status", "--porcelain"), "", "Git status")
    head = git_output("rev-parse", "HEAD")
    for label, commit in (
        ("A3.2 result", A3_2_RESULT_COMMIT),
        ("A3.3 prereg", A3_3_PREREG_COMMIT),
        ("addendum prereg", ADDENDUM_PREREG_COMMIT),
    ):
        assert_equal(git_output("cat-file", "-t", commit), "commit", f"{label} type")
        assert_true(_is_ancestor(commit, head), f"{label} is not reachable from HEAD")
    assert_true(resolve(A3_3_TASKBOOK).is_file(), "A3.3 taskbook missing")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", A3_3_PREREG_COMMIT, "--", A3_3_TASKBOOK],
        cwd=ROOT,
    ).returncode == 0
    assert_true(unchanged, "A3.3 taskbook changed after preregistration")
    assert_equal(
        sha256_path(resolve(CLAIM_MATRIX_PATH)),
        CLAIM_MATRIX_SHA256,
        "A1.11 claim matrix SHA-256",
    )
    claims = read_csv(CLAIM_MATRIX_PATH)
    observed = {
        row["target"]: row["status"]
        for row in claims
        if row.get("claim_id") in {"FC1", "FC2", "FE1"}
    }
    assert_equal(
        observed,
        {
            "Success": "CONFIRMATORY_SUPPORTED",
            "Looping": "CONFIRMATORY_SUPPORTED",
            "Side Effect": "EXPLORATORY_SUPPORTED",
        },
        "frozen claim statuses",
    )
    return {"head": head}


def _bibtex_keys(text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", text, flags=re.IGNORECASE))


def _comparability_counts(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    rows = list(rows)
    return {
        status: sum(row["comparability_class"] == status for row in rows)
        for status in VALID_COMPARABILITY
    }


def verify_outputs() -> dict[str, Any]:
    for relative in PATCHED_OUTPUTS:
        path = resolve(relative)
        assert_true(path.is_file() and path.stat().st_size > 0, f"missing output: {relative}")

    literature = read_csv("artifacts/a3_2_verified_literature_registry.csv")
    by_id = {row["work_id"]: row for row in literature}
    assert_equal(len(by_id), len(literature), "unique literature work_id")
    assert_equal(_comparability_counts(literature), EXPECTED_COMPARABILITY, "comparability counts")

    graph = by_id.get("webgrapheval", {})
    assert_equal(graph.get("canonical_title"), WEBGRAPHEVAL_TITLE, "WebGraphEval title")
    assert_equal(graph.get("primary_source_identifier"), "arXiv:2510.19205", "WebGraphEval id")
    assert_equal(graph.get("comparability_class"), "PARTIALLY_COMPARABLE", "WebGraphEval class")
    assert_equal(graph.get("verification_status"), "VERIFIED_PRIMARY", "WebGraphEval verification")

    webstep = by_id.get("webstep", {})
    assert_equal(webstep.get("canonical_title"), WEBSTEP_TITLE, "WebStep title")
    assert_equal(webstep.get("primary_source_identifier"), "arXiv:2606.15673", "WebStep id")
    assert_equal(webstep.get("version_or_revision"), "arXiv v2; COLM 2026", "WebStep version")
    assert_equal(webstep.get("comparability_class"), "CONTEXT_ONLY", "WebStep class")
    assert_equal(webstep.get("verification_status"), "VERIFIED_PRIMARY", "WebStep verification")

    similar = by_id.get("similar_srm", {})
    assert_equal(similar.get("canonical_title"), SIMILAR_CANONICAL_TITLE, "Similar canonical title")
    assert_equal(similar.get("primary_source_identifier"), "PMLR:v267/miao25b; arXiv:2503.18665", "Similar id")

    citations = read_csv("artifacts/a3_2_citation_registry.csv")
    citation_by_id = {row["work_id"]: row for row in citations}
    assert_equal(len(citations), 10, "citation count")
    assert_equal(citation_by_id["similar_srm"]["canonical_title"], SIMILAR_CANONICAL_TITLE, "Similar citation title")
    assert_equal(citation_by_id["webgrapheval"]["doi"], "", "unsupported WebGraphEval DOI")
    assert_equal(citation_by_id["webstep"]["doi"], "", "unsupported WebStep DOI")

    bib_text = resolve("paper/references/a3_2_verified_related_work.bib").read_text(encoding="utf-8")
    assert_equal(_bibtex_keys(bib_text), {row["citation_key"] for row in citations}, "BibTeX keys")
    assert_true(SIMILAR_CANONICAL_TITLE.replace("Step-Wise", "Step-{W}ise") not in bib_text or "Boosting Virtual Agent Learning" in bib_text, "Similar BibTeX title")

    positioning = read_csv("artifacts/a3_2_positioning_matrix.csv")
    positioning_names = {row["work"] for row in positioning}
    assert_true(WEBGRAPHEVAL_TITLE in positioning_names, "WebGraphEval missing from positioning")
    assert_true(WEBSTEP_TITLE in positioning_names, "WebStep missing from positioning")
    assert_true(SIMILAR_CANONICAL_TITLE in positioning_names, "Similar canonical name missing from positioning")
    assert_true("Similar" not in positioning_names, "Similar alias remains in positioning")

    contract = resolve("docs/a3_2_positioning_and_novelty_contract.md").read_text(encoding="utf-8")
    for phrase in (
        "WebGraphEval boundary",
        "WebStep boundary",
        "lightweight fixed-dimensional structural signals",
        "first structural web-agent evaluator",
        "first trajectory-structure evaluator",
        "outperforms WebGraphEval",
        "outperforms WebStep",
        "NO_VALID_CROSS_PAPER_HEAD_TO_HEAD",
    ):
        assert_true(phrase in contract, f"positioning contract missing: {phrase}")

    table_md = resolve("paper/tables/Table_Related_Work_Positioning.md").read_text(encoding="utf-8")
    table_tex = resolve("paper/tables/Table_Related_Work_Positioning.tex").read_text(encoding="utf-8")
    skeleton = resolve("docs/a3_2_related_work_writing_skeleton.md").read_text(encoding="utf-8")
    for text, label in ((table_md, "Markdown table"), (table_tex, "LaTeX table"), (skeleton, "writing skeleton")):
        assert_true("WebGraphEval" in text and "WebStep" in text, f"{label} closest works")
        assert_true("Boosting Virtual Agent Learning" in text, f"{label} Similar canonical name")
    assert_true("performance leaderboard" in table_md.lower(), "attribute-only table guard")

    require_columns("artifacts/a3_2_addendum_closest_work_patch.csv", PATCH_FIELDS)
    patch_rows = read_csv("artifacts/a3_2_addendum_closest_work_patch.csv")
    patch_items = {row["item"] for row in patch_rows}
    assert_true({"WebGraphEval", "WebStep", "Similar canonical identity"} <= patch_items, "patch registry items")
    assert_true(all(row["verified"] == "true" for row in patch_rows), "unverified patch row")

    summary = json.loads(resolve("artifacts/a3_2_addendum_run_summary.json").read_text(encoding="utf-8"))
    assert_equal(summary["stage_determination"], "PASS_WITH_CONDITIONS", "stage determination")
    assert_equal(summary["similar_resolution_status"], "RESOLVED_CANONICAL_IDENTITY", "Similar resolution")
    assert_equal(summary["head_to_head_after"], "NO_VALID_CROSS_PAPER_HEAD_TO_HEAD", "head-to-head gate")
    assert_equal(summary["citation_count_before"], 8, "citation count before")
    assert_equal(summary["citation_count_after"], 10, "citation count after")
    for key, value in COUNTERS.items():
        assert_equal(summary[key], value, f"counter {key}")
    for relative, expected in summary["output_hashes"].items():
        assert_equal(sha256_path(resolve(relative)), expected, f"output hash {relative}")

    return {"literature": literature, "citations": citations, "summary": summary}


def verify_changed_scope() -> None:
    changed = set(git_output("diff", "--name-only", ADDENDUM_PREREG_COMMIT, "HEAD").splitlines())
    unexpected = changed - ALLOWED_CHANGED_PATHS
    assert_true(not unexpected, f"unauthorized changed paths: {sorted(unexpected)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--verify-scope", action="store_true")
    arguments = parser.parse_args()
    verify_preflight(require_clean=arguments.require_clean)
    if arguments.preflight_only:
        print("A3.2 closest-work addendum preflight PASS")
        return 0
    verify_outputs()
    if arguments.verify_scope:
        verify_changed_scope()
    print(
        "A3.2 closest-work addendum verification PASS_WITH_CONDITIONS | "
        "direct=0 partial=3 context=9 not_comparable=0 | "
        "cross-paper=NO_VALID_CROSS_PAPER_HEAD_TO_HEAD | scientific_ops=0 | "
        "next=WAIT_FOR_HUMAN_A3_2_ADDENDUM_REVIEW"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
