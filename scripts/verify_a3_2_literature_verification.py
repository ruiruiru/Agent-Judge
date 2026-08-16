#!/usr/bin/env python3
"""Verify and summarize the Stage A3.2 literature evidence package.

This verifier performs bibliographic, provenance, schema, and policy checks only.
It does not download data, fit a model, run inference, recompute an A1 metric,
or perform any statistical operation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
PREREG_COMMIT = "f2cced39b237f7cb5759214e8401cf3bee2ab696"
A3_1_RESULT_COMMIT = "e17bf7c6c1974d8a96ab7e7814b0a21ec827a082"
A2_3_RESULT_COMMIT = "ad0576c488fafed243b464e0b8f903e9bb233b43"
CLAIM_MATRIX_PATH = "artifacts/a1_11_final_claim_matrix.csv"
CLAIM_MATRIX_SHA256 = "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175"
SEARCH_CUTOFF_DATE = "2026-08-14"
RESULT_COMMIT_SENTINEL = "recorded_by_enclosing_result_commit"

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
}

MANDATORY_WORKS = {"agentrewardbench", "web_shepherd", "agentrm"}
INCLUDED_ADDITIONAL_WORKS = {
    "agent_as_a_judge",
    "similar_srm",
    "cuarewardbench",
    "webarbiter",
    "agentprocessbench",
}
VALID_VERIFICATION = {
    "VERIFIED_PRIMARY",
    "VERIFIED_WITH_LIMITATION",
    "IDENTITY_ONLY",
    "EXCLUDED_NOT_CLOSE",
    "UNRESOLVED",
}
VALID_COMPARABILITY = {
    "DIRECTLY_COMPARABLE",
    "PARTIALLY_COMPARABLE",
    "CONTEXT_ONLY",
    "NOT_COMPARABLE",
}
PRIMARY_SOURCE_TYPES = {
    "peer_reviewed_proceedings",
    "official_paper_pdf",
    "official_arxiv",
    "official_openreview",
}

REQUIRED_OUTPUTS = (
    "artifacts/a3_2_verified_literature_registry.csv",
    "artifacts/a3_2_verified_result_claims.csv",
    "artifacts/a3_2_positioning_matrix.csv",
    "artifacts/a3_2_citation_registry.csv",
    "artifacts/a3_2_literature_search_log.csv",
    "docs/a3_2_agentrewardbench_relationship.md",
    "docs/a3_2_related_work_taxonomy.md",
    "docs/a3_2_positioning_and_novelty_contract.md",
    "docs/a3_2_related_work_writing_skeleton.md",
    "paper/references/a3_2_verified_related_work.bib",
    "paper/tables/Table_Related_Work_Positioning.md",
    "paper/tables/Table_Related_Work_Positioning.tex",
    "docs/stage_a3_2_literature_baseline_verification_report.md",
)

LITERATURE_FIELDS = (
    "work_id", "canonical_title", "authors", "year", "venue_or_status",
    "primary_source_type", "primary_source_identifier", "primary_source_url",
    "version_or_revision", "verified_date", "research_object",
    "evaluation_granularity", "input_representation", "output_signal",
    "training_required", "uses_llm_or_vlm", "uses_reward_model",
    "uses_rule_based_eval", "web_agent_specific", "trajectory_level",
    "step_level", "benchmarks", "policy_models", "reported_metrics",
    "reported_main_result", "result_source_location", "code_available",
    "data_available", "comparability_class", "paper_role",
    "verification_status", "notes",
)
RESULT_FIELDS = (
    "work_id", "result_id", "claim_type", "verbatim_location",
    "paraphrased_result", "metric", "value", "dataset", "split",
    "evaluation_unit", "scope", "comparability_class", "allowed_use",
    "forbidden_use", "primary_source_identifier",
)
CITATION_FIELDS = (
    "citation_key", "work_id", "canonical_title", "authors", "year",
    "venue", "doi", "arxiv_id", "primary_url", "bibtex_source",
    "verification_status", "paper_sections",
)
SEARCH_FIELDS = (
    "query", "date", "source", "candidate", "included_or_excluded", "reason",
)


class VerificationError(RuntimeError):
    """Raised when an A3.2 evidence or provenance contract is violated."""


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
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True,
        text=True, encoding="utf-8",
    )
    return completed.stdout.strip()


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise VerificationError(f"{label}: expected {expected!r}, found {actual!r}")


def assert_true(condition: bool, label: str) -> None:
    if not condition:
        raise VerificationError(label)


def require_columns(relative: str, required: Sequence[str]) -> None:
    actual = csv_fields(relative)
    missing = [field for field in required if field not in actual]
    if missing:
        raise VerificationError(f"{relative} missing columns: {missing}")


def verify_preflight(require_clean: bool) -> dict[str, Any]:
    if require_clean:
        assert_equal(git_output("status", "--porcelain"), "", "Git status")
    head = git_output("rev-parse", "HEAD")
    for label, commit in (
        ("A3.2 prereg", PREREG_COMMIT),
        ("A3.1 result", A3_1_RESULT_COMMIT),
        ("A2.3 result", A2_3_RESULT_COMMIT),
    ):
        assert_equal(git_output("cat-file", "-t", commit), "commit", f"{label} type")
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, head], cwd=ROOT
        ).returncode == 0
        assert_true(ancestor, f"{label} is not reachable from HEAD")
    assert_equal(sha256_path(resolve(CLAIM_MATRIX_PATH)), CLAIM_MATRIX_SHA256, "claim matrix SHA-256")
    claims = read_csv(CLAIM_MATRIX_PATH)
    expected = {
        "Success": "CONFIRMATORY_SUPPORTED",
        "Looping": "CONFIRMATORY_SUPPORTED",
        "Side Effect": "EXPLORATORY_SUPPORTED",
    }
    frozen_ids = {"FC1": "Success", "FC2": "Looping", "FE1": "Side Effect"}
    observed: dict[str, str] = {}
    for row in claims:
        claim_id = row.get("claim_id", "")
        if claim_id in frozen_ids:
            target = frozen_ids[claim_id]
            assert_equal(row.get("target", ""), target, f"{claim_id} target")
            observed[target] = row.get("status", "")
    assert_equal(observed, expected, "frozen claims")
    commits = git_output("log", "--format=%H", "--reverse", f"{PREREG_COMMIT}..{head}").splitlines()
    return {
        "head": head,
        "implementation_commit": commits[0] if commits else "",
        "fix_commits": commits[1:] if len(commits) > 1 else [],
        "input_hashes": {
            CLAIM_MATRIX_PATH: CLAIM_MATRIX_SHA256,
            "docs/tasks/STAGE_A3_2_LITERATURE_BASELINE_VERIFICATION.md": sha256_path(
                resolve("docs/tasks/STAGE_A3_2_LITERATURE_BASELINE_VERIFICATION.md")
            ),
        },
        "frozen_claims": expected,
    }


def _bibtex_keys(text: str) -> set[str]:
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)", text, flags=re.IGNORECASE))


def _has_number(value: str) -> bool:
    return bool(re.search(r"\d", value))


def verify_outputs() -> dict[str, Any]:
    for relative in REQUIRED_OUTPUTS:
        path = resolve(relative)
        assert_true(path.is_file() and path.stat().st_size > 0, f"missing or blank output: {relative}")

    require_columns("artifacts/a3_2_verified_literature_registry.csv", LITERATURE_FIELDS)
    require_columns("artifacts/a3_2_verified_result_claims.csv", RESULT_FIELDS)
    require_columns("artifacts/a3_2_citation_registry.csv", CITATION_FIELDS)
    require_columns("artifacts/a3_2_literature_search_log.csv", SEARCH_FIELDS)

    literature = read_csv("artifacts/a3_2_verified_literature_registry.csv")
    results = read_csv("artifacts/a3_2_verified_result_claims.csv")
    citations = read_csv("artifacts/a3_2_citation_registry.csv")
    search = read_csv("artifacts/a3_2_literature_search_log.csv")
    positioning = read_csv("artifacts/a3_2_positioning_matrix.csv")

    by_id = {row["work_id"]: row for row in literature}
    assert_equal(len(by_id), len(literature), "unique literature work_id")
    assert_true(MANDATORY_WORKS <= by_id.keys(), "mandatory work missing")
    for work_id in MANDATORY_WORKS:
        row = by_id[work_id]
        assert_true(row["primary_source_type"] in PRIMARY_SOURCE_TYPES, f"{work_id} lacks primary source")
        assert_true(row["primary_source_url"].startswith("https://"), f"{work_id} source URL")
        assert_true(row["verification_status"].startswith("VERIFIED_"), f"{work_id} unresolved")
    for row in literature:
        assert_true(row["verification_status"] in VALID_VERIFICATION, f"invalid verification status: {row['work_id']}")
        assert_true(row["comparability_class"] in VALID_COMPARABILITY, f"invalid comparability: {row['work_id']}")
        assert_true(row["canonical_title"] != "" and row["authors"] != "", f"identity incomplete: {row['work_id']}")
        assert_true("snippet" not in row["primary_source_type"].lower(), f"snippet used as evidence: {row['work_id']}")
        assert_true("scholar" not in row["primary_source_url"].lower(), f"scholar used as evidence: {row['work_id']}")

    for work_id in INCLUDED_ADDITIONAL_WORKS:
        assert_equal(by_id[work_id]["paper_role"], "included_closest_work", f"included paper role {work_id}")
    assert_true(len(INCLUDED_ADDITIONAL_WORKS) <= 5, "additional included cap exceeded")

    for row in results:
        assert_true(row["work_id"] in by_id, f"result work unknown: {row['work_id']}")
        assert_true(row["verbatim_location"] != "", f"result location missing: {row['result_id']}")
        assert_true(row["primary_source_identifier"] != "", f"result source missing: {row['result_id']}")
        if _has_number(row["value"]) or _has_number(row["paraphrased_result"]):
            assert_true(
                any(token in row["verbatim_location"].lower() for token in ("table", "section", "abstract", "page", "figure")),
                f"numeric result lacks source location: {row['result_id']}",
            )
        if row["comparability_class"] == "CONTEXT_ONLY":
            assert_true("head-to-head" in row["forbidden_use"].lower(), f"context result ranking guard: {row['result_id']}")

    relationship = resolve("docs/a3_2_agentrewardbench_relationship.md").read_text(encoding="utf-8")
    assert_true("blind held-out within evaluated benchmark families" in relationship, "blind-heldout boundary missing")
    assert_true("independent external benchmark validation" in relationship, "external-validation boundary missing")
    assert_true("does not create a new benchmark" in relationship, "new-benchmark denial missing")

    novelty = resolve("docs/a3_2_positioning_and_novelty_contract.md").read_text(encoding="utf-8")
    for phrase in (
        "first automatic evaluator for agents",
        "first web-agent trajectory evaluator",
        "first reward model for web agents",
        "state of the art",
        "outperforms LLM judges",
        "replaces LLM judges",
        "generalizes to unseen benchmarks",
        "first process-aware evaluator",
    ):
        assert_true(phrase in novelty, f"prohibited novelty phrase not frozen: {phrase}")

    assert_true(any(row.get("work", "") == "THIS_WORK" for row in positioning), "THIS_WORK missing from positioning matrix")
    direct_count = sum(row["comparability_class"] == "DIRECTLY_COMPARABLE" for row in literature)
    assert_equal(direct_count, 0, "direct-comparability gate")

    bib_text = resolve("paper/references/a3_2_verified_related_work.bib").read_text(encoding="utf-8")
    bib_keys = _bibtex_keys(bib_text)
    citation_keys = {row["citation_key"] for row in citations}
    assert_equal(bib_keys, citation_keys, "citation registry/BibTeX keys")
    assert_equal(len(citation_keys), 8, "citation count")
    for row in citations:
        assert_true(row["primary_url"].startswith("https://"), f"citation primary URL: {row['citation_key']}")
        if row["doi"]:
            assert_true(row["doi"].startswith("10."), f"DOI form: {row['citation_key']}")

    table_md = resolve("paper/tables/Table_Related_Work_Positioning.md").read_text(encoding="utf-8")
    assert_true("NO_VALID_CROSS_PAPER_HEAD_TO_HEAD" in table_md, "numeric gate absent from table")
    assert_true("Performance" not in table_md and "Accuracy" not in table_md, "paper table became numeric ranking")

    assert_true(len(search) >= 10, "search log too short")
    assert_true(sum(row["included_or_excluded"] == "INCLUDED" for row in search) >= 5, "included search records")
    assert_true(len({row["candidate"] for row in search if row["candidate"]}) >= 7, "recent candidate review count")
    assert_true(all(row["date"] <= SEARCH_CUTOFF_DATE for row in search), "search after cutoff")

    return {
        "literature": literature,
        "results": results,
        "citations": citations,
        "search": search,
        "positioning": positioning,
    }


def build_summary(preflight: Mapping[str, Any], verified: Mapping[str, Any]) -> dict[str, Any]:
    literature = verified["literature"]
    searches = verified["search"]
    counts = {status: sum(row["verification_status"] == status for row in literature) for status in VALID_VERIFICATION}
    comparability = {kind: sum(row["comparability_class"] == kind for row in literature) for kind in VALID_COMPARABILITY}
    output_hashes = {relative: sha256_path(resolve(relative)) for relative in REQUIRED_OUTPUTS}
    reviewed = {
        row["candidate"] for row in searches
        if row["candidate"] and row["candidate"] not in {"AgentRewardBench", "Web-Shepherd", "AgentRM"}
    }
    return {
        "stage": "A3.2",
        "stage_determination": "PASS_WITH_CONDITIONS",
        "conditions": [
            "No DIRECTLY_COMPARABLE cross-paper baseline was identified under the preregistered gate.",
            "CUARewardBench arXiv v1 and the later ICML 2026 OpenReview record contain versioned result values; only the later official record is cited for those values.",
            "Several 2026 works remain preprints or lack a verified DOI/pages field; absent metadata is left blank.",
        ],
        "commits": {
            "a3_2_preregistration": PREREG_COMMIT,
            "a3_1_result": A3_1_RESULT_COMMIT,
            "a2_3_result": A2_3_RESULT_COMMIT,
            "implementation": preflight["implementation_commit"],
            "fix_commits": preflight["fix_commits"],
            "result": RESULT_COMMIT_SENTINEL,
            "amend": False,
        },
        "search_cutoff_date": SEARCH_CUTOFF_DATE,
        "mandatory_works_verified": sorted(MANDATORY_WORKS),
        "additional_candidates_reviewed": sorted(reviewed),
        "additional_works_included": sorted(INCLUDED_ADDITIONAL_WORKS),
        "verified_primary_count": counts["VERIFIED_PRIMARY"],
        "verified_with_limitation_count": counts["VERIFIED_WITH_LIMITATION"],
        "identity_only_count": counts["IDENTITY_ONLY"],
        "unresolved_count": counts["UNRESOLVED"],
        "directly_comparable_count": comparability["DIRECTLY_COMPARABLE"],
        "partially_comparable_count": comparability["PARTIALLY_COMPARABLE"],
        "context_only_count": comparability["CONTEXT_ONLY"],
        "not_comparable_count": comparability["NOT_COMPARABLE"],
        "cross_paper_head_to_head_status": "NO_VALID_CROSS_PAPER_HEAD_TO_HEAD",
        "citation_count": len(verified["citations"]),
        "bibtex_count": len(verified["citations"]),
        "input_hashes": preflight["input_hashes"],
        "output_hashes": output_hashes,
        "scientific_operation_counters": dict(COUNTERS),
        **COUNTERS,
        "stopping_rule_satisfied": True,
        "next_status": "WAIT_FOR_HUMAN_A3_2_REVIEW",
        "a3_3_entered": False,
    }


def write_summary(summary: Mapping[str, Any]) -> None:
    path = resolve("artifacts/a3_2_run_summary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def verify_summary(summary: Mapping[str, Any], preflight: Mapping[str, Any]) -> None:
    assert_equal(summary["stage_determination"], "PASS_WITH_CONDITIONS", "stage determination")
    assert_equal(summary["cross_paper_head_to_head_status"], "NO_VALID_CROSS_PAPER_HEAD_TO_HEAD", "numeric gate")
    assert_equal(summary["scientific_operation_counters"], COUNTERS, "scientific counters")
    assert_equal(summary["next_status"], "WAIT_FOR_HUMAN_A3_2_REVIEW", "next status")
    assert_equal(summary["commits"]["implementation"], preflight["implementation_commit"], "implementation commit")
    for relative, expected in summary["output_hashes"].items():
        assert_equal(sha256_path(resolve(relative)), expected, f"output hash {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--write-summary", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    arguments = parser.parse_args()
    preflight = verify_preflight(require_clean=arguments.require_clean)
    if arguments.preflight_only:
        print("A3.2 preflight PASS")
        return 0
    verified = verify_outputs()
    if arguments.write_summary:
        write_summary(build_summary(preflight, verified))
    summary = json.loads(resolve("artifacts/a3_2_run_summary.json").read_text(encoding="utf-8"))
    verify_summary(summary, preflight)
    print(
        "A3.2 verification PASS_WITH_CONDITIONS | mandatory=3 additional=5 "
        "direct=0 cross-paper=NO_VALID_CROSS_PAPER_HEAD_TO_HEAD scientific_ops=0 "
        "next=WAIT_FOR_HUMAN_A3_2_REVIEW"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
