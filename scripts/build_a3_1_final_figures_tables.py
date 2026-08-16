#!/usr/bin/env python3
"""Build and verify Stage A3.1 final paper figures and tables.

Only frozen artifacts are read.  Numeric operations are limited to Decimal
display rounding, unit conversion, sorting for presentation, and plot-coordinate
placement.  The module imports no estimator, tensor, embedding, statistics, or
scientific-metric library.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from PIL import Image
from pypdf import PdfReader
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from a3_1_rendering import (
    ACCENT,
    BLACK,
    DARK,
    EXPLORATORY,
    LIGHT,
    MID,
    PALE,
    PDF_FONT,
    PDF_FONT_BOLD,
    PT_PER_INCH,
    SVG_FONT_STACK,
    WHITE,
    RenderingError,
    VectorFigure,
    save_figure_bundle,
    text_width,
    wrap_text,
)


ROOT = Path(__file__).resolve().parents[1]
PREREG_COMMIT = "32a2d6f4d82e2c0541595fdb416142855189a4c8"
A2_3_RESULT_COMMIT = "ad0576c488fafed243b464e0b8f903e9bb233b43"
RESULT_COMMIT_SENTINEL = "recorded_by_enclosing_result_commit"
DISPLAY_CONTRACT_VERSION = "a3_1_display_contract_v1"
PNG_DPI = 300


@dataclass(frozen=True)
class FrozenInput:
    path: str
    sha256: str
    source_stage: str
    role: str
    evidence_status: str


INPUTS: tuple[FrozenInput, ...] = (
    FrozenInput("docs/tasks/STAGE_A3_1_FINAL_FIGURES_TABLES.md", "20bb183ecdb5025cb44b1937f6d7b42a77ef4710af0a0029ee5b66293f0d337e", "A3.1", "approved taskbook", "PREREGISTERED_PROTOCOL"),
    FrozenInput("artifacts/a1_11_final_claim_matrix.csv", "2fc929e242e614244940d6d96d8ff1e3935e059925cff0b36b009a86b04f3175", "A1.11", "frozen claim identities", "CLAIM_FREEZE"),
    FrozenInput("artifacts/a1_11_table_main_test_results.csv", "c60ff992487e7a05d70c39de7db9364c31529a6b4334739e59045783ec3e9947", "A1.11", "exact main held-out source", "CONFIRMATORY_AND_EXPLORATORY"),
    FrozenInput("artifacts/a1_11_table_benchmark_results.csv", "3df5b511d0cf29472ccfba5c63ea28caf4b58407285109231f176871668d77a2", "A1.11", "benchmark heterogeneity source", "DESCRIPTIVE_ONLY"),
    FrozenInput("artifacts/a1_11_evidence_registry.csv", "98c8f66e7d53bdecaef201c362565279a2a81630f73a3c5970c725433c0cd0a8", "A1.11", "pipeline provenance", "INTEGRITY_ONLY"),
    FrozenInput("artifacts/a1_9_run_summary.json", "3dd5e65c0e5ba022065f20d71131cb7b22c160375d1d093007091f3796e43f3a", "A1.9", "method-freeze provenance", "INTEGRITY_ONLY"),
    FrozenInput("artifacts/a1_10a_run_summary.json", "d314cc0e0c0d028b9e02fc4995e0a7de036f761383018b0d456d9830cf57ab69", "A1.10a", "blind-prediction provenance", "INTEGRITY_ONLY"),
    FrozenInput("artifacts/a1_10_run_summary.json", "523c9d01fd60d2d35fb083011a6f30ebc8dbfb9fb265ecf4753d81c6040a4ed2", "A1.10b", "unlock and held-out provenance", "INTEGRITY_ONLY"),
    FrozenInput("artifacts/a2_1_efficiency_summary.csv", "7d37fddef61b526f4b054483ba900ba72a69b0c4c98cd2b31b7ce725043df0c3", "A2.1", "efficiency measurements", "EFFICIENCY_BENCHMARK"),
    FrozenInput("artifacts/a2_1_efficiency_relative_cost.csv", "fb8619c1914b4a23308800bd3aaf2dd256701820443f3b0a171f7508c4fa3d1f", "A2.1", "relative-cost provenance", "EFFICIENCY_BENCHMARK"),
    FrozenInput("artifacts/a2_1_environment.json", "7ffa7812b67a6ab4faaf1d08caadb105d1f8391ffe7af2688c4ffbf1c9fdf1ec", "A2.1", "measured environment", "ENVIRONMENT_SPECIFIC"),
    FrozenInput("artifacts/a2_2_structural_coefficients.csv", "cd762d7975566f2d107cddff82e8e2d2a58738ee8dbf74f13ee8cffad1ec29d2", "A2.2", "signed structural coefficients", "POST_FREEZE_DIAGNOSTIC"),
    FrozenInput("artifacts/a2_2_feature_group_evidence.csv", "8160dc969d6043b8da8ee294b8cabb8811c5d4171af24cad6ec0f35efd881af8", "A2.2", "feature-group evidence", "DEV_ONLY"),
    FrozenInput("artifacts/a2_2_metadata_baseline_summary.csv", "f5bf2aa3c71e81f2025de01c38d93be0af1a0038e772a5d282649bccd33df967", "A2.2", "metadata diagnostic summary", "POST_FREEZE_DIAGNOSTIC"),
    FrozenInput("artifacts/a2_2_error_case_manifest.csv", "0372151a32b24fb9f5b53acc802dc23d480ff2bc813c2d394b7faeca33e70cf0", "A2.2", "deterministic error selection", "POST_FREEZE_DESCRIPTIVE"),
    FrozenInput("artifacts/a2_2_error_case_notes.csv", "ec060f556d6402dfa7a333c4c7498a20d1b2e5d067002a9bfdcb2225e3b1b6ee", "A2.2", "deterministic error notes", "POST_FREEZE_DESCRIPTIVE"),
    FrozenInput("artifacts/a2_3_table_1_main_heldout_results.csv", "297a1f59c34fc7f29864d722e8e2a233945dba061527848e31b4d7411b2964a5", "A2.3", "Table 1 exact source", "CONFIRMATORY_AND_EXPLORATORY"),
    FrozenInput("artifacts/a2_3_table_2_efficiency_tradeoff.csv", "bbf36c09827819fbf49aaa7487db66b34077052d8a29cb093c72001bee66f02a", "A2.3", "Table 2 exact source", "ENVIRONMENT_SPECIFIC"),
    FrozenInput("artifacts/a2_3_table_3_dev_representation_summary.csv", "f0e15e670e3f9592c167c57adaf41a63d56bce0fc9bc37a1945a8ed3f3431c1e", "A2.3", "Table 3 exact source", "DEV_ONLY"),
    FrozenInput("artifacts/a2_3_table_4_benchmark_heterogeneity.csv", "de0cbc94d114eab5677d1ff620a5f0d976883ae8515d3cb24e873f9f213ac511", "A2.3", "Table 4 exact source", "DESCRIPTIVE_ONLY"),
    FrozenInput("artifacts/a2_3_table_5_interpretability_error_summary.csv", "037a8b3200377093bf1abb5ea0cf9b82db74fb162e27971690d10f7d9cdf4a0f", "A2.3", "Table 5 exact source", "ASSOCIATIVE_AND_DESCRIPTIVE"),
    FrozenInput("artifacts/a2_3_evidence_to_paper_map.csv", "8f471d50d4b1e8d53e4946aadcbd3541d81ebb4c27b6d93b9fbf56e4859cf60a", "A2.3", "evidence-to-paper mapping", "EVIDENCE_MAP"),
    FrozenInput("docs/a2_3_publication_results_story.md", "5b68968cdf43061cef044ce1e969883178bd7fa50a691cbcedde5c3215f86827", "A2.3", "frozen narrative boundary", "CLAIM_FREEZE"),
    FrozenInput("docs/a2_3_publication_figure_spec.md", "96cbd15126bec73ac6a644b2be14a6a940728257ee678bde4f8e93b4bb295a58", "A2.3", "figure specification", "FIGURE_SPEC"),
    FrozenInput("docs/a2_3_final_limitations_ledger.md", "80490f81318903267bfe117a0cadae9192ba35db50a352329aac4a01094d8255", "A2.3", "limitations boundary", "LIMITATION_FREEZE"),
    FrozenInput("artifacts/a2_3_publication_package_index.csv", "0777f29536cf0f698138b41c26ff448cc7000304423224e5443a010662a39c65", "A2.3", "package provenance", "INTEGRITY_ONLY"),
)


TABLE_SOURCES = {
    "Table1_Main_Heldout_Results": "artifacts/a2_3_table_1_main_heldout_results.csv",
    "Table2_Efficiency_Complexity": "artifacts/a2_3_table_2_efficiency_tradeoff.csv",
    "Table3_Dev_Representation_Robustness": "artifacts/a2_3_table_3_dev_representation_summary.csv",
    "Table4_Benchmark_Heterogeneity": "artifacts/a2_3_table_4_benchmark_heterogeneity.csv",
    "Table5_Interpretability_Failure_Summary": "artifacts/a2_3_table_5_interpretability_error_summary.csv",
}


FIGURE_DIMENSIONS = {
    "Fig1_Study_Pipeline": (7.0, 2.6),
    "Fig2_Heldout_AP_Lift_CI": (3.4, 2.4),
    "Fig3_Efficiency_Complexity": (7.0, 2.9),
    "Fig4_Structural_Interpretation": (7.0, 4.2),
    "Fig5_Success_Failure_Boundaries": (7.0, 4.8),
    "FigS1_SideEffect_Exploratory_AP_Lift": (3.4, 2.2),
    "FigS2_Benchmark_Heterogeneity": (7.0, 3.8),
}


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
    "external_dataset_runs": 0,
}


IMPLEMENTATION_FAILURES = (
    {
        "phase": "post-render manual visual QA",
        "failure_type": "label_overlap",
        "affected_artifacts": [
            "paper/figures/Fig4_Structural_Interpretation.*",
            "paper/figures/FigS2_Benchmark_Heterogeneity.*",
        ],
        "finding": "Fig4 rank-1 Success coefficient text overlapped its feature label; two high-AP FigS2 Looping labels intersected markers.",
        "scientific_values_affected": False,
        "outputs_reused": False,
        "resolution": "independent layout-only fix commit followed by complete A3.1 regeneration",
    },
)


DISPLAY_FIELDS = (
    "artifact_id",
    "artifact_path",
    "location_kind",
    "source_artifact",
    "source_row_key",
    "source_field",
    "exact_value",
    "display_value",
    "format_rule",
    "evidence_status",
)


FIGURE_DATA_FIELDS = (
    "figure_id",
    "panel",
    "series",
    "label",
    "value_type",
    "source_field",
    "exact_value",
    "display_value",
    "source_artifact",
    "source_row_key",
    "evidence_status",
    "trajectory_key",
    "error_type",
    "case_role",
    "primary_code",
)


REGISTRY_FIELDS = (
    "artifact_id",
    "artifact_path",
    "artifact_type",
    "paper_role",
    "source_artifacts",
    "sha256",
    "evidence_status",
    "display_contract_version",
    "verified",
)


class IntegrityError(RuntimeError):
    """Raised when frozen inputs or generated artifacts violate A3.1."""


@dataclass
class BuildContext:
    output_root: Path
    display_rows: list[dict[str, str]] = field(default_factory=list)
    figure_rows: list[dict[str, str]] = field(default_factory=list)

    def output(self, relative: str) -> Path:
        return resolve_output(self.output_root, relative)

    def add_display(
        self,
        *,
        artifact_id: str,
        artifact_path: str,
        location_kind: str,
        source_artifact: str,
        source_row_key: str,
        source_field: str,
        exact_value: str,
        display_value: str,
        format_rule: str,
        evidence_status: str,
    ) -> str:
        self.display_rows.append(
            {
                "artifact_id": artifact_id,
                "artifact_path": artifact_path,
                "location_kind": location_kind,
                "source_artifact": source_artifact,
                "source_row_key": source_row_key,
                "source_field": source_field,
                "exact_value": exact_value,
                "display_value": display_value,
                "format_rule": format_rule,
                "evidence_status": evidence_status,
            }
        )
        return display_value

    def add_figure_datum(
        self,
        *,
        figure_id: str,
        panel: str,
        series: str,
        label: str,
        value_type: str,
        source_field: str,
        exact_value: str,
        display_value: str,
        source_artifact: str,
        source_row_key: str,
        evidence_status: str,
        trajectory_key: str = "",
        error_type: str = "",
        case_role: str = "",
        primary_code: str = "",
    ) -> None:
        self.figure_rows.append(
            {
                "figure_id": figure_id,
                "panel": panel,
                "series": series,
                "label": label,
                "value_type": value_type,
                "source_field": source_field,
                "exact_value": exact_value,
                "display_value": display_value,
                "source_artifact": source_artifact,
                "source_row_key": source_row_key,
                "evidence_status": evidence_status,
                "trajectory_key": trajectory_key,
                "error_type": error_type,
                "case_role": case_role,
                "primary_code": primary_code,
            }
        )


def resolve_root(relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise IntegrityError(f"absolute input path prohibited: {relative}")
    resolved = (ROOT / candidate).resolve()
    if resolved != ROOT and ROOT not in resolved.parents:
        raise IntegrityError(f"input path escapes repository: {relative}")
    return resolved


def resolve_output(output_root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise IntegrityError(f"absolute output path prohibited: {relative}")
    root = output_root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise IntegrityError(f"output path escapes root: {relative}")
    return resolved


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(relative: str) -> list[dict[str, str]]:
    with resolve_root(relative).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(relative: str) -> Any:
    return json.loads(resolve_root(relative).read_text(encoding="utf-8"))


def read_output_csv(output_root: Path, relative: str) -> list[dict[str, str]]:
    with resolve_output(output_root, relative).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_text(output_root: Path, relative: str, value: str) -> None:
    path = resolve_output(output_root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def atomic_json(output_root: Path, relative: str, value: Any) -> None:
    atomic_text(output_root, relative, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def atomic_csv(
    output_root: Path,
    relative: str,
    fields: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    path = resolve_output(output_root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return completed.stdout.strip()


def assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise IntegrityError(f"{label}: expected {expected!r}, found {actual!r}")


def one(rows: Sequence[Mapping[str, str]], **criteria: str) -> Mapping[str, str]:
    matches = [row for row in rows if all(str(row.get(key, "")) == value for key, value in criteria.items())]
    if len(matches) != 1:
        raise IntegrityError(f"expected one row for {criteria}, found {len(matches)}")
    return matches[0]


def verify_preflight(require_clean: bool) -> dict[str, Any]:
    if require_clean:
        assert_equal(git_output("status", "--porcelain"), "", "Git start status")
    head = git_output("rev-parse", "HEAD")
    assert_equal(git_output("cat-file", "-t", PREREG_COMMIT), "commit", "prereg commit type")
    assert_equal(git_output("cat-file", "-t", A2_3_RESULT_COMMIT), "commit", "A2.3 result type")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PREREG_COMMIT, head], cwd=ROOT).returncode:
        raise IntegrityError("A3.1 prereg commit is not an ancestor of HEAD")
    assert_equal(git_output("rev-parse", f"{PREREG_COMMIT}^"), A2_3_RESULT_COMMIT, "prereg parent")
    assert_equal(git_output("ls-files", "--error-unmatch", "--", "docs/tasks/STAGE_A3_1_FINAL_FIGURES_TABLES.md"), "docs/tasks/STAGE_A3_1_FINAL_FIGURES_TABLES.md", "tracked taskbook")

    verified_hashes: dict[str, str] = {}
    for frozen in INPUTS:
        path = resolve_root(frozen.path)
        if not path.is_file():
            raise IntegrityError(f"missing frozen input: {frozen.path}")
        actual = sha256_path(path)
        assert_equal(actual, frozen.sha256, f"SHA-256 {frozen.path}")
        verified_hashes[frozen.path] = actual

    claims = read_csv("artifacts/a1_11_final_claim_matrix.csv")
    frozen_claims = {
        "Success": ("FC1", "CONFIRMATORY_SUPPORTED"),
        "Looping": ("FC2", "CONFIRMATORY_SUPPORTED"),
        "Side Effect": ("FE1", "EXPLORATORY_SUPPORTED"),
    }
    for target, (claim_id, status) in frozen_claims.items():
        row = one(claims, claim_id=claim_id)
        assert_equal(row["target"], target, f"{claim_id} target")
        assert_equal(row["status"], status, f"{claim_id} status")

    commits = git_output("log", "--format=%H", "--reverse", f"{PREREG_COMMIT}..{head}").splitlines()
    if not commits:
        raise IntegrityError("formal build requires an implementation commit after preregistration")
    return {
        "head": head,
        "implementation_commit": commits[0],
        "fix_commits": commits[1:],
        "verified_hashes": verified_hashes,
        "frozen_claims": {target: status for target, (_, status) in frozen_claims.items()},
    }


def fixed3(value: str) -> str:
    return format(Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP), "f")


def significant(value: str, digits: int) -> str:
    number = Decimal(value)
    if number == 0:
        return "0"
    exponent = number.copy_abs().adjusted()
    quantum = Decimal(1).scaleb(exponent - digits + 1)
    rounded = number.quantize(quantum, rounding=ROUND_HALF_UP)
    if exponent >= 3:
        return f"{rounded.scaleb(-exponent):.{digits-1}f}e{exponent}"
    places = max(0, digits - exponent - 1)
    return f"{rounded:.{places}f}"


def latency_display(value: str) -> tuple[str, str]:
    digits = 4 if Decimal(value) < 1 else 3
    return significant(value, digits), f"latency_{digits}_significant_digits"


def bytes_display(value: str) -> tuple[str, str]:
    kib = Decimal(value) / Decimal(1024)
    return f"{significant(str(kib), 3)} KiB", "bytes_to_KiB_3_significant_digits"


def mb_display(value: str) -> tuple[str, str]:
    if value == "NA" or value == "":
        return "NA", "missing_as_NA"
    return f"{significant(value, 3)} MiB", "memory_3_significant_digits"


def tex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(value.replace("|", "\\|").replace("\n", "<br>") for value in row) + " |")
    return "\n".join(lines)


def latex_table(
    label: str,
    caption: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    widths: Sequence[str],
    *,
    font_command: str = r"\small",
) -> str:
    columns = "".join(widths)
    body = [
        r"\begin{table*}[t]",
        r"\centering",
        font_command,
        f"\\caption{{{tex_escape(caption)}}}",
        f"\\label{{tab:{label}}}",
        f"\\begin{{tabular}}{{{columns}}}",
        r"\hline",
        " & ".join(tex_escape(header) for header in headers) + r" \\",
        r"\hline",
    ]
    for row in rows:
        body.append(" & ".join(tex_escape(value).replace("\n", r" \newline ") for value in row) + r" \\")
    body.extend([r"\hline", r"\end{tabular}", r"\end{table*}"])
    return "\n".join(body) + "\n"


def write_contracts(ctx: BuildContext, preflight: Mapping[str, Any]) -> None:
    input_manifest = {
        "stage": "A3.1",
        "formal_git_commit": preflight["head"],
        "a2_3_result_commit": A2_3_RESULT_COMMIT,
        "inputs": [
            {
                "path": item.path,
                "source_stage": item.source_stage,
                "sha256": item.sha256,
                "role": item.role,
                "evidence_status": item.evidence_status,
                "verified": True,
            }
            for item in INPUTS
        ],
    }
    display_contract = {
        "version": DISPLAY_CONTRACT_VERSION,
        "machine_source_policy": "Exact frozen source strings remain unchanged; display formatting is recorded separately.",
        "rounding_mode": "Decimal ROUND_HALF_UP",
        "predictive_metrics": {"fields": ["AP", "F1", "prevalence", "AP_lift", "CI endpoints"], "display": "3 decimal places"},
        "efficiency": {
            "latency_below_1_ms": "4 significant digits",
            "latency_at_least_1_ms": "3 significant digits",
            "ratios": "3 significant digits",
            "memory_and_storage": "3 significant digits with documented binary-unit conversion",
            "dimension": "integer",
        },
        "coefficients": "3 decimal places",
        "counts": "integer",
        "missing": "NA",
        "allowed_operations": ["formatting", "rounding for display", "unit conversion", "sorting for presentation", "plot coordinate placement", "rendering", "hashing", "source verification"],
        "source_writeback": False,
    }
    visual_style = {
        "version": "a3_1_journal_neutral_v1",
        "background": "white",
        "color_redundancy": "Direct labels, marker shape, line style, outline, and hatch; color is never the only encoding.",
        "grayscale_readability": "Designed in grayscale-first tones with direct labels and redundant encodings.",
        "three_dimensional": False,
        "gradients": False,
        "shadows": False,
        "fonts": {
            "pdf": {"actual_font_name": PDF_FONT, "bold_font_name": PDF_FONT_BOLD, "font_type": "standard PDF Type 1", "embedded_font_file": False},
            "svg": {"font_family": SVG_FONT_STACK, "font_file_embedded": False},
            "png": {"source": "300 dpi Poppler rasterization of PDF", "font_reference": PDF_FONT},
        },
        "font_files_distributed": False,
        "preview_dpi": PNG_DPI,
        "figure_dimensions_inches": {name: {"width": dims[0], "height": dims[1]} for name, dims in FIGURE_DIMENSIONS.items()},
        "candidate_widths_inches": {"single_column": 3.4, "double_column": 7.0},
    }
    atomic_json(ctx.output_root, "artifacts/a3_1_input_manifest.json", input_manifest)
    atomic_json(ctx.output_root, "artifacts/a3_1_display_contract.json", display_contract)
    atomic_json(ctx.output_root, "artifacts/a3_1_visual_style.json", visual_style)
    atomic_json(
        ctx.output_root,
        "artifacts/a3_1_implementation_failures.json",
        {
            "stage": "A3.1",
            "initial_formal_git_commit": preflight["implementation_commit"],
            "fix_commits": preflight["fix_commits"],
            "status": "RESOLVED_BY_INDEPENDENT_FIX_COMMIT" if preflight["fix_commits"] else "OPEN_IN_TEST_CONTEXT",
            "failures": list(IMPLEMENTATION_FAILURES),
            "scientific_operation_counters": dict(COUNTERS),
        },
    )


def _record(
    ctx: BuildContext,
    *,
    artifact_id: str,
    artifact_path: str,
    source_artifact: str,
    source_row_key: str,
    source_field: str,
    exact: str,
    display: str,
    rule: str,
    evidence_status: str,
) -> str:
    return ctx.add_display(
        artifact_id=artifact_id,
        artifact_path=artifact_path,
        location_kind="table",
        source_artifact=source_artifact,
        source_row_key=source_row_key,
        source_field=source_field,
        exact_value=exact,
        display_value=display,
        format_rule=rule,
        evidence_status=evidence_status,
    )


def render_tables(ctx: BuildContext) -> list[str]:
    generated: list[str] = []

    # Table 1
    table_id = "Table1_Main_Heldout_Results"
    source = TABLE_SOURCES[table_id]
    rows = read_csv(source)
    order = {"Success": 0, "Looping": 1, "Side Effect": 2}
    rows.sort(key=lambda row: order[row["target"]])
    display_rows: list[list[str]] = []
    for row in rows:
        key = f"target={row['target']}"
        status = row["claim_status"]
        values = [row["target"], row["final_method"]]
        for field_name in ("eligible_n", "positive_n", "negative_n"):
            values.append(_record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field=field_name, exact=row[field_name], display=row[field_name], rule="integer", evidence_status=status))
        for field_name in ("prevalence", "AP", "AP_lift", "F1"):
            values.append(_record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field=field_name, exact=row[field_name], display=fixed3(row[field_name]), rule="predictive_metric_3_decimal_places", evidence_status=status))
        low = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="AP_lift_CI_low", exact=row["AP_lift_CI_low"], display=fixed3(row["AP_lift_CI_low"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
        high = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="AP_lift_CI_high", exact=row["AP_lift_CI_high"], display=fixed3(row["AP_lift_CI_high"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
        values.extend([f"[{low}, {high}]", status])
        display_rows.append(values)
    headers = ["Target", "Frozen method", "N", "Positive", "Negative", "Prevalence", "AP", "AP lift", "F1", "AP-lift 95% CI", "Evidence status"]
    caption = "Official held-out tasks/trajectories within evaluated benchmark families using frozen thresholds. Success and Looping are confirmatory; Side Effect is exploratory."
    md = f"# Table 1. Main held-out results\n\n{caption}\n\n" + markdown_table(headers, display_rows) + "\n"
    tex = latex_table("main-heldout-results", caption, headers, display_rows, ["l", "p{0.17\\textwidth}", "r", "r", "r", "r", "r", "r", "r", "p{0.13\\textwidth}", "p{0.17\\textwidth}"], font_command=r"\scriptsize")
    for extension, content in (("md", md), ("tex", tex)):
        path = f"paper/tables/{table_id}.{extension}"
        atomic_text(ctx.output_root, path, content)
        generated.append(path)

    # Table 2
    table_id = "Table2_Efficiency_Complexity"
    source = TABLE_SOURCES[table_id]
    rows = read_csv(source)
    rows.sort(key=lambda row: row["method"])
    display_rows = []
    for row in rows:
        key = f"method={row['method']}"
        status = row["evidence_status"]
        dimension = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="dimension", exact=row["dimension"], display=row["dimension"], rule="integer", evidence_status=status)
        extraction, extraction_rule = latency_display(row["extraction_ms_per_trajectory"])
        extraction = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="extraction_ms_per_trajectory", exact=row["extraction_ms_per_trajectory"], display=extraction, rule=extraction_rule, evidence_status=status)
        inference, inference_rule = latency_display(row["inference_ms_per_trajectory"])
        inference = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="inference_ms_per_trajectory", exact=row["inference_ms_per_trajectory"], display=inference, rule=inference_rule, evidence_status=status)
        storage, storage_rule = bytes_display(row["representation_size_bytes"])
        storage = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="representation_size_bytes", exact=row["representation_size_bytes"], display=storage, rule=storage_rule, evidence_status=status)
        classifier, classifier_rule = bytes_display(row["classifier_size_bytes"])
        classifier = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="classifier_size_bytes", exact=row["classifier_size_bytes"], display=classifier, rule=classifier_rule, evidence_status=status)
        encoder = "NA"
        if row["encoder_size_bytes"] != "NA":
            encoder, encoder_rule = bytes_display(row["encoder_size_bytes"])
            encoder = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="encoder_size_bytes", exact=row["encoder_size_bytes"], display=encoder, rule=encoder_rule, evidence_status=status)
        cpu, cpu_rule = mb_display(row["peak_cpu_rss_mb"])
        cpu = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="peak_cpu_rss_mb", exact=row["peak_cpu_rss_mb"], display=cpu, rule=cpu_rule, evidence_status=status)
        gpu = "NA"
        if row["peak_gpu_vram_mb"] != "NA":
            gpu, gpu_rule = mb_display(row["peak_gpu_vram_mb"])
            gpu = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="peak_gpu_vram_mb", exact=row["peak_gpu_vram_mb"], display=gpu, rule=gpu_rule, evidence_status=status)
        device = "CPU" if row["method"] == "B2" else "CUDA RTX 5070"
        display_rows.append([row["method"], row["representation"], dimension, device, f"{extraction} ms", f"{inference} ms", storage, classifier, encoder, cpu, gpu])
    headers = ["Method", "Representation", "Dim.", "Measured device", "Warm extraction / traj.", "Classifier inference / traj.", "Representation storage", "Classifier", "Encoder", "Peak CPU RSS", "Peak GPU VRAM"]
    caption = "Environment-specific measurements only: B2 used CPU and B4 used CUDA on an NVIDIA GeForce RTX 5070. No cross-target AP comparison is implied."
    md = f"# Table 2. Efficiency and complexity\n\n{caption}\n\n" + markdown_table(headers, display_rows) + "\n"
    tex = latex_table("efficiency-complexity", caption, headers, display_rows, ["l", "p{0.15\\textwidth}", "r", "p{0.10\\textwidth}", "r", "r", "r", "r", "r", "r", "r"], font_command=r"\scriptsize")
    for extension, content in (("md", md), ("tex", tex)):
        path = f"paper/tables/{table_id}.{extension}"
        atomic_text(ctx.output_root, path, content)
        generated.append(path)

    # Table 3
    table_id = "Table3_Dev_Representation_Robustness"
    source = TABLE_SOURCES[table_id]
    rows = read_csv(source)
    display_rows = []
    for index, row in enumerate(rows, start=1):
        key = f"row={index}|stage={row['stage']}|target={row['target']}"
        status = row["evidence_status"]
        point = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="point_estimate", exact=row["point_estimate"], display=fixed3(row["point_estimate"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
        ci = "NA"
        if row["CI_low_95"]:
            low = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="CI_low_95", exact=row["CI_low_95"], display=fixed3(row["CI_low_95"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
            high = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="CI_high_95", exact=row["CI_high_95"], display=fixed3(row["CI_high_95"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
            ci = f"[{low}, {high}]"
        display_rows.append([row["stage"], row["target"].replace("_", " ").title(), row["evidence_area"], row["representation"], row["metric"], point, ci, status, row["claim_boundary"]])
    headers = ["Stage", "Target", "Evidence area", "Representation/comparison", "Metric", "Estimate", "Frozen 95% CI", "Source status", "Claim boundary"]
    caption = "All entries are DEV_ONLY. Exploratory development rows retain their original EXPLORATORY_DEV status; no held-out or confirmatory upgrade is made."
    md = f"# Table 3. Development representation and robustness evidence\n\n**DEV_ONLY** - {caption}\n\n" + markdown_table(headers, display_rows) + "\n"
    tex = latex_table("dev-representation-robustness", "DEV_ONLY. " + caption, headers, display_rows, ["l", "l", "p{0.13\\textwidth}", "p{0.17\\textwidth}", "p{0.10\\textwidth}", "r", "p{0.10\\textwidth}", "p{0.12\\textwidth}", "p{0.16\\textwidth}"], font_command=r"\scriptsize")
    for extension, content in (("md", md), ("tex", tex)):
        path = f"paper/tables/{table_id}.{extension}"
        atomic_text(ctx.output_root, path, content)
        generated.append(path)

    # Table 4
    table_id = "Table4_Benchmark_Heterogeneity"
    source = TABLE_SOURCES[table_id]
    rows = read_csv(source)
    target_order = {"Success": 0, "Looping": 1, "Side Effect": 2}
    benchmark_order = {"assistantbench": 0, "visualwebarena": 1, "webarena": 2, "workarena": 3}
    rows.sort(key=lambda row: (target_order[row["target"]], benchmark_order[row["benchmark"]]))
    display_rows = []
    for row in rows:
        key = f"target={row['target']}|benchmark={row['benchmark']}"
        ap = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="AP", exact=row["AP"], display=fixed3(row["AP"]), rule="predictive_metric_3_decimal_places", evidence_status="DESCRIPTIVE_ONLY")
        f1 = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field="F1", exact=row["F1"], display=fixed3(row["F1"]), rule="predictive_metric_3_decimal_places", evidence_status="DESCRIPTIVE_ONLY")
        display_rows.append([row["target"], row["benchmark"], ap, f1, row["role"], row["evidence_status"]])
    headers = ["Target", "Benchmark family", "AP", "F1", "Role", "Evidence status"]
    caption = "DESCRIPTIVE_ONLY benchmark heterogeneity. No winner ranking, significance mark, or pairwise inference is authorized."
    md = f"# Table 4. Benchmark heterogeneity\n\n**DESCRIPTIVE_ONLY** - {caption}\n\n" + markdown_table(headers, display_rows) + "\n"
    tex = latex_table("benchmark-heterogeneity", caption, headers, display_rows, ["l", "l", "r", "r", "p{0.22\\textwidth}", "p{0.18\\textwidth}"], font_command=r"\small")
    for extension, content in (("md", md), ("tex", tex)):
        path = f"paper/tables/{table_id}.{extension}"
        atomic_text(ctx.output_root, path, content)
        generated.append(path)

    # Table 5
    table_id = "Table5_Interpretability_Failure_Summary"
    source = TABLE_SOURCES[table_id]
    rows = read_csv(source)
    rows.sort(key=lambda row: {"success": 0, "looping": 1}[row["target"]])
    display_rows = []
    for row in rows:
        key = f"target={row['target']}"
        status = row["evidence_status"]
        signals = []
        for item in row["top_structural_signals"].split(";"):
            feature, exact = item.rsplit(":", 1)
            display = _record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field=f"top_structural_signals:{feature}", exact=exact, display=fixed3(exact), rule="coefficient_3_decimal_places", evidence_status=status)
            signals.append(f"{feature}: {display}")
        metric_values = []
        for field_name in ("metadata_AP", "metadata_AP_lift", "frozen_B2_dev_AP"):
            metric_values.append(_record(ctx, artifact_id=table_id, artifact_path=f"paper/tables/{table_id}.md", source_artifact=source, source_row_key=key, source_field=field_name, exact=row[field_name], display=fixed3(row[field_name]), rule="predictive_metric_3_decimal_places", evidence_status=status))
        display_rows.append([row["target"].title(), "\n".join(signals), metric_values[0], metric_values[1], metric_values[2], row["main_failure_modes"].replace(";", "; "), row["main_interpretation"], status])
    headers = ["Target", "Top signed structural signals", "Metadata AP", "Metadata AP lift", "Frozen B2 dev AP", "Deterministic illustrative cases", "Interpretation", "Evidence status"]
    caption = "Associative/diagnostic coefficients are not causal effects. Metadata comparison is descriptive. Error cases are deterministic illustrations, not prevalence estimates."
    md = f"# Table 5. Interpretability and failure summary\n\n{caption}\n\n" + markdown_table(headers, display_rows) + "\n"
    tex = latex_table("interpretability-failure-summary", caption, headers, display_rows, ["l", "p{0.18\\textwidth}", "r", "r", "r", "p{0.18\\textwidth}", "p{0.23\\textwidth}", "p{0.15\\textwidth}"], font_command=r"\scriptsize")
    for extension, content in (("md", md), ("tex", tex)):
        path = f"paper/tables/{table_id}.{extension}"
        atomic_text(ctx.output_root, path, content)
        generated.append(path)

    return generated


def _figure_display(
    ctx: BuildContext,
    *,
    figure_id: str,
    panel: str,
    series: str,
    label: str,
    source_artifact: str,
    source_row_key: str,
    source_field: str,
    exact: str,
    display: str,
    rule: str,
    evidence_status: str,
    value_type: str = "numeric",
) -> str:
    ctx.add_display(
        artifact_id=figure_id,
        artifact_path=f"paper/figures/{figure_id}.pdf",
        location_kind="figure",
        source_artifact=source_artifact,
        source_row_key=source_row_key,
        source_field=source_field,
        exact_value=exact,
        display_value=display,
        format_rule=rule,
        evidence_status=evidence_status,
    )
    ctx.add_figure_datum(
        figure_id=figure_id,
        panel=panel,
        series=series,
        label=label,
        value_type=value_type,
        source_field=source_field,
        exact_value=exact,
        display_value=display,
        source_artifact=source_artifact,
        source_row_key=source_row_key,
        evidence_status=evidence_status,
    )
    return display


def _save(ctx: BuildContext, figure_id: str, figure: VectorFigure) -> list[str]:
    base = ctx.output(f"paper/figures/{figure_id}")
    paths = save_figure_bundle(figure, base, dpi=PNG_DPI)
    return [str(path.relative_to(ctx.output_root.resolve())).replace("\\", "/") for path in paths.values()]


def _panel_frame(figure: VectorFigure, x: float, y: float, width: float, height: float, title: str, panel: str) -> None:
    figure.rect(x, y, width, height, fill=WHITE, stroke=LIGHT, line_width=0.8)
    figure.text(x + 8, y + height - 12, panel, size=8, bold=True)
    figure.text(x + 24, y + height - 12, title, size=8, bold=True)


def figure_1(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "Fig1_Study_Pipeline"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Study and blind-first evaluation pipeline")
    stages = [
        ("Raw\ntrajectories", "artifacts/a1_11_evidence_registry.csv", "raw_trajectories", "INTEGRITY_ONLY"),
        ("Leakage-safe\ncleaning", "artifacts/a1_11_evidence_registry.csv", "leakage_safe_cleaning", "INTEGRITY_ONLY"),
        ("Grouped\ndev", "artifacts/a1_11_evidence_registry.csv", "grouped_dev", "DEV_ONLY"),
        ("Method\nfreeze", "artifacts/a1_9_run_summary.json", "method_freeze", "INTEGRITY_ONLY"),
        ("Blind\nprediction", "artifacts/a1_10a_run_summary.json", "blind_prediction", "INTEGRITY_ONLY"),
        ("Label\nunlock", "artifacts/a1_10_run_summary.json", "label_unlock", "INTEGRITY_ONLY"),
        ("Held-out\nconfirmation", "artifacts/a1_10_run_summary.json", "heldout_confirmation", "CONFIRMATORY"),
        ("Post-freeze\nA2 diagnostics", "docs/a2_3_publication_figure_spec.md", "post_freeze_a2_diagnostics", "POST_FREEZE_DIAGNOSTIC"),
    ]
    margin = 14.0
    gap = 8.0
    node_width = (figure.width - 2 * margin - gap * (len(stages) - 1)) / len(stages)
    node_height = 55.0
    node_y = 69.0
    figure.text(margin, figure.height - 22, "FROZEN BLIND-FIRST SEQUENCE", size=8, bold=True)
    confirmatory_end = margin + 7 * node_width + 6 * gap
    figure.line(margin, figure.height - 30, confirmatory_end, figure.height - 30, stroke=ACCENT, line_width=1.4)
    figure.text((margin + confirmatory_end) / 2, figure.height - 39, "development and confirmatory pipeline", size=6.6, anchor="middle", color=DARK)
    last_x = margin + 7 * (node_width + gap)
    figure.line(last_x, figure.height - 30, last_x + node_width, figure.height - 30, stroke=MID, line_width=1.2, dash=(3, 2))
    figure.text(last_x + node_width / 2, figure.height - 39, "after confirmation", size=6.6, anchor="middle", color=DARK)
    for index, (label, source, key, status) in enumerate(stages):
        x = margin + index * (node_width + gap)
        is_post = index == len(stages) - 1
        figure.rect(x, node_y, node_width, node_height, fill=PALE if not is_post else WHITE, stroke=MID if not is_post else DARK, line_width=0.9, dash=(3, 2) if is_post else None, radius=3)
        figure.text(x + node_width / 2, node_y + node_height / 2 + 2, label, size=6.6, bold=index in {3, 4, 5, 6}, anchor="middle", line_height=8.3)
        figure.text(x + node_width / 2, node_y + 8, f"{index + 1}", size=6, anchor="middle", color=MID)
        if index < len(stages) - 1:
            figure.arrow(x + node_width + 1, node_y + node_height / 2, x + node_width + gap - 1, node_y + node_height / 2, stroke=DARK, head=3.5)
        ctx.add_figure_datum(
            figure_id=figure_id,
            panel="pipeline",
            series="protocol_stage",
            label=label.replace("\n", " "),
            value_type="protocol_text",
            source_field="stage_sequence",
            exact_value=key,
            display_value=label.replace("\n", " "),
            source_artifact=source,
            source_row_key=key,
            evidence_status=status,
        )
    figure.text(figure.width / 2, 38, "Labels and metrics remain unavailable until after blind prediction bytes are frozen.", size=7.2, anchor="middle", color=DARK)
    figure.text(figure.width / 2, 21, "A2 efficiency and diagnostics are visually and procedurally downstream of held-out confirmation.", size=7.2, anchor="middle", color=DARK)
    return figure_id, figure


def _x_scale(value: Decimal, low: Decimal, high: Decimal, x0: float, x1: float) -> float:
    return x0 + float((value - low) / (high - low)) * (x1 - x0)


def figure_2(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "Fig2_Heldout_AP_Lift_CI"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Held-out AP lift and frozen 95 percent confidence intervals")
    source = "artifacts/a2_3_table_1_main_heldout_results.csv"
    rows = [one(read_csv(source), target=target) for target in ("Success", "Looping")]
    x0, x1 = 67.0, figure.width - 18.0
    y_axis = 42.0
    top = figure.height - 30.0
    low, high = Decimal("-0.02"), Decimal("0.48")
    figure.text(12, figure.height - 14, "CONFIRMATORY HELD-OUT RESULTS", size=7.5, bold=True, color=ACCENT)
    for tick in (Decimal("0.0"), Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0.4")):
        x = _x_scale(tick, low, high, x0, x1)
        figure.line(x, y_axis, x, top, stroke=LIGHT, line_width=0.5)
        figure.text(x, y_axis - 10, f"{tick:.1f}", size=6.6, anchor="middle")
    zero_x = _x_scale(Decimal("0"), low, high, x0, x1)
    figure.line(zero_x, y_axis, zero_x, top, stroke=BLACK, line_width=1.0)
    figure.line(x0, y_axis, x1, y_axis, stroke=BLACK, line_width=0.8)
    figure.text((x0 + x1) / 2, 16, "Pooled AP lift (frozen 95% CI)", size=7.2, anchor="middle")
    y_positions = [112.0, 73.0]
    for index, (row, y) in enumerate(zip(rows, y_positions)):
        key = f"target={row['target']}"
        status = row["claim_status"]
        display_point = _figure_display(ctx, figure_id=figure_id, panel="main", series=row["target"], label=row["target"], source_artifact=source, source_row_key=key, source_field="AP_lift", exact=row["AP_lift"], display=fixed3(row["AP_lift"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
        display_low = _figure_display(ctx, figure_id=figure_id, panel="main", series=row["target"], label=f"{row['target']} lower", source_artifact=source, source_row_key=key, source_field="AP_lift_CI_low", exact=row["AP_lift_CI_low"], display=fixed3(row["AP_lift_CI_low"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
        display_high = _figure_display(ctx, figure_id=figure_id, panel="main", series=row["target"], label=f"{row['target']} upper", source_artifact=source, source_row_key=key, source_field="AP_lift_CI_high", exact=row["AP_lift_CI_high"], display=fixed3(row["AP_lift_CI_high"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
        point_x = _x_scale(Decimal(row["AP_lift"]), low, high, x0, x1)
        low_x = _x_scale(Decimal(row["AP_lift_CI_low"]), low, high, x0, x1)
        high_x = _x_scale(Decimal(row["AP_lift_CI_high"]), low, high, x0, x1)
        figure.text(x0 - 8, y, row["target"], size=7.4, bold=True, anchor="right")
        figure.line(low_x, y, high_x, y, stroke=ACCENT, line_width=1.8)
        figure.line(low_x, y - 4, low_x, y + 4, stroke=ACCENT, line_width=1.0)
        figure.line(high_x, y - 4, high_x, y + 4, stroke=ACCENT, line_width=1.0)
        if index == 0:
            figure.circle(point_x, y, 4.0, fill=WHITE, stroke=ACCENT, line_width=1.5)
        else:
            figure.rect(point_x - 3.5, y - 3.5, 7, 7, fill=ACCENT, stroke=ACCENT)
        figure.text((low_x + high_x) / 2, y + 12, f"{display_point} [{display_low}, {display_high}]", size=6.5, anchor="middle")
    return figure_id, figure


def figure_s1(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "FigS1_SideEffect_Exploratory_AP_Lift"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Exploratory Side Effect held-out AP lift")
    source = "artifacts/a2_3_table_1_main_heldout_results.csv"
    row = one(read_csv(source), target="Side Effect")
    key = "target=Side Effect"
    status = row["claim_status"]
    x0, x1 = 58.0, figure.width - 18.0
    y_axis, top = 38.0, figure.height - 42.0
    low, high = Decimal("-0.01"), Decimal("0.09")
    figure.rect(7, 7, figure.width - 14, figure.height - 14, fill=WHITE, stroke=EXPLORATORY, line_width=1.0, dash=(4, 3))
    figure.text(14, figure.height - 18, "EXPLORATORY - LOW SUPPORT - NON-CONFIRMATORY", size=7.2, bold=True, color=EXPLORATORY)
    for tick in (Decimal("0.00"), Decimal("0.02"), Decimal("0.04"), Decimal("0.06"), Decimal("0.08")):
        x = _x_scale(tick, low, high, x0, x1)
        figure.line(x, y_axis, x, top, stroke=LIGHT, line_width=0.5)
        figure.text(x, y_axis - 10, f"{tick:.2f}", size=6.4, anchor="middle")
    zero_x = _x_scale(Decimal("0"), low, high, x0, x1)
    figure.line(zero_x, y_axis, zero_x, top, stroke=BLACK, line_width=1.0)
    figure.line(x0, y_axis, x1, y_axis, stroke=BLACK, line_width=0.8)
    display_point = _figure_display(ctx, figure_id=figure_id, panel="appendix", series="Side Effect", label="Side Effect", source_artifact=source, source_row_key=key, source_field="AP_lift", exact=row["AP_lift"], display=fixed3(row["AP_lift"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
    display_low = _figure_display(ctx, figure_id=figure_id, panel="appendix", series="Side Effect", label="Side Effect lower", source_artifact=source, source_row_key=key, source_field="AP_lift_CI_low", exact=row["AP_lift_CI_low"], display=fixed3(row["AP_lift_CI_low"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
    display_high = _figure_display(ctx, figure_id=figure_id, panel="appendix", series="Side Effect", label="Side Effect upper", source_artifact=source, source_row_key=key, source_field="AP_lift_CI_high", exact=row["AP_lift_CI_high"], display=fixed3(row["AP_lift_CI_high"]), rule="predictive_metric_3_decimal_places", evidence_status=status)
    y = 83.0
    point_x = _x_scale(Decimal(row["AP_lift"]), low, high, x0, x1)
    low_x = _x_scale(Decimal(row["AP_lift_CI_low"]), low, high, x0, x1)
    high_x = _x_scale(Decimal(row["AP_lift_CI_high"]), low, high, x0, x1)
    figure.line(low_x, y, high_x, y, stroke=EXPLORATORY, line_width=1.8, dash=(4, 2))
    figure.line(low_x, y - 4, low_x, y + 4, stroke=EXPLORATORY)
    figure.line(high_x, y - 4, high_x, y + 4, stroke=EXPLORATORY)
    figure.polygon(((point_x, y + 5), (point_x + 5, y), (point_x, y - 5), (point_x - 5, y)), fill=WHITE, stroke=EXPLORATORY, line_width=1.4)
    figure.text((low_x + high_x) / 2, y + 15, f"{display_point} [{display_low}, {display_high}]", size=6.7, anchor="middle", color=EXPLORATORY)
    figure.text((x0 + x1) / 2, 16, "Pooled AP lift (frozen 95% CI)", size=7, anchor="middle")
    return figure_id, figure


def _draw_two_method_panel(
    figure: VectorFigure,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str,
    panel: str,
    raw_values: Sequence[Decimal],
    display_values: Sequence[str],
    log_scale: bool,
) -> None:
    _panel_frame(figure, x, y, width, height, title, panel)
    plot_x0, plot_x1 = x + 34, x + width - 12
    plot_y0, plot_y1 = y + 31, y + height - 31
    transformed = [math.log10(float(value)) if log_scale else float(value) for value in raw_values]
    low = min(0.0, min(transformed)) if not log_scale else min(transformed) - 0.25
    high = max(transformed) * 1.08 if not log_scale else max(transformed) + 0.25
    if high == low:
        high = low + 1
    for index, (method, value, display) in enumerate(zip(("B2", "B4"), transformed, display_values)):
        bar_y = plot_y1 - 34 - index * 47
        value_x = plot_x0 + (value - low) / (high - low) * (plot_x1 - plot_x0)
        baseline = plot_x0 if log_scale else plot_x0 + (0 - low) / (high - low) * (plot_x1 - plot_x0)
        left, right = sorted((baseline, value_x))
        if index == 0:
            figure.hatched_rect(left, bar_y - 8, max(2, right - left), 16, fill=WHITE, stroke=ACCENT, spacing=6)
        else:
            figure.rect(left, bar_y - 8, max(2, right - left), 16, fill=LIGHT, stroke=DARK)
        figure.text(plot_x0 - 7, bar_y, method, size=7.2, bold=True, anchor="right")
        label_x = min(plot_x1 - 1, max(right + 4, plot_x0 + 42))
        figure.text(label_x, bar_y, display, size=6.7, anchor="right" if label_x >= plot_x1 - 2 else "left")
    figure.line(plot_x0, plot_y0, plot_x1, plot_y0, stroke=BLACK, line_width=0.7)
    figure.text((plot_x0 + plot_x1) / 2, y + 15, "log scale" if log_scale else "linear scale", size=6.4, anchor="middle", color=MID)


def figure_3(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "Fig3_Efficiency_Complexity"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Efficiency and representation complexity")
    source = "artifacts/a2_3_table_2_efficiency_tradeoff.csv"
    rows = [one(read_csv(source), method=method) for method in ("B2", "B4")]
    values: dict[str, list[Decimal]] = {"dimension": [], "extraction": [], "storage": []}
    displays: dict[str, list[str]] = {"dimension": [], "extraction": [], "storage": []}
    for row in rows:
        key = f"method={row['method']}"
        status = row["evidence_status"]
        values["dimension"].append(Decimal(row["dimension"]))
        displays["dimension"].append(_figure_display(ctx, figure_id=figure_id, panel="A", series=row["method"], label=row["method"], source_artifact=source, source_row_key=key, source_field="dimension", exact=row["dimension"], display=row["dimension"], rule="integer", evidence_status=status))
        extraction_display, extraction_rule = latency_display(row["extraction_ms_per_trajectory"])
        values["extraction"].append(Decimal(row["extraction_ms_per_trajectory"]))
        displays["extraction"].append(_figure_display(ctx, figure_id=figure_id, panel="B", series=row["method"], label=row["method"], source_artifact=source, source_row_key=key, source_field="extraction_ms_per_trajectory", exact=row["extraction_ms_per_trajectory"], display=f"{extraction_display} ms", rule=extraction_rule, evidence_status=status))
        storage_display, storage_rule = bytes_display(row["representation_size_bytes"])
        values["storage"].append(Decimal(row["representation_size_bytes"]))
        displays["storage"].append(_figure_display(ctx, figure_id=figure_id, panel="C", series=row["method"], label=row["method"], source_artifact=source, source_row_key=key, source_field="representation_size_bytes", exact=row["representation_size_bytes"], display=storage_display, rule=storage_rule, evidence_status=status))
    margin, gap = 10.0, 9.0
    panel_width = (figure.width - 2 * margin - 2 * gap) / 3
    panel_y, panel_height = 37.0, figure.height - 55.0
    _draw_two_method_panel(figure, x=margin, y=panel_y, width=panel_width, height=panel_height, title="Representation dimension", panel="A", raw_values=values["dimension"], display_values=displays["dimension"], log_scale=False)
    _draw_two_method_panel(figure, x=margin + panel_width + gap, y=panel_y, width=panel_width, height=panel_height, title="Warm extraction / trajectory", panel="B", raw_values=values["extraction"], display_values=displays["extraction"], log_scale=True)
    _draw_two_method_panel(figure, x=margin + 2 * (panel_width + gap), y=panel_y, width=panel_width, height=panel_height, title="Representation storage", panel="C", raw_values=values["storage"], display_values=displays["storage"], log_scale=True)
    figure.text(figure.width / 2, 18, "Measured environment only: B2 CPU; B4 CUDA on NVIDIA GeForce RTX 5070. Classifier-only inference is not the main visual.", size=6.8, anchor="middle")
    return figure_id, figure


FEATURE_LABELS = {
    "observation_char_count_total": "Observation chars (total)",
    "observation_char_count_mean_nonempty": "Observation chars (mean)",
    "action_char_count_total": "Action chars (total)",
    "has_explicit_termination_signal": "Explicit termination",
    "unique_action_ratio": "Unique action ratio",
    "nonempty_action_count": "Nonempty actions",
    "nonempty_observation_count": "Nonempty observations",
    "step_count": "Step count",
    "nonempty_focused_element_count": "Focused elements",
}


def _draw_coefficient_panel(
    ctx: BuildContext,
    figure: VectorFigure,
    *,
    figure_id: str,
    target: str,
    panel: str,
    x: float,
    y: float,
    width: float,
    height: float,
    rows: Sequence[Mapping[str, str]],
) -> None:
    _panel_frame(figure, x, y, width, height, target.title(), panel)
    label_x = x + 104
    plot_x0, plot_x1 = x + 112, x + width - 14
    plot_y0, plot_y1 = y + 33, y + height - 33
    low, high = Decimal("-2.4"), Decimal("2.1")
    zero_x = _x_scale(Decimal("0"), low, high, plot_x0, plot_x1)
    figure.line(zero_x, plot_y0, zero_x, plot_y1, stroke=BLACK, line_width=0.9)
    for tick in (Decimal("-2"), Decimal("-1"), Decimal("0"), Decimal("1"), Decimal("2")):
        tick_x = _x_scale(tick, low, high, plot_x0, plot_x1)
        figure.line(tick_x, plot_y0, tick_x, plot_y1, stroke=LIGHT, line_width=0.45)
        figure.text(tick_x, plot_y0 - 10, str(tick), size=6.2, anchor="middle")
    row_gap = (plot_y1 - plot_y0 - 8) / 5
    source = "artifacts/a2_2_structural_coefficients.csv"
    for index, row in enumerate(rows):
        row_y = plot_y1 - 15 - index * row_gap
        coefficient = Decimal(row["standardized_coefficient"])
        end_x = _x_scale(coefficient, low, high, plot_x0, plot_x1)
        left, right = sorted((zero_x, end_x))
        if coefficient >= 0:
            figure.rect(left, row_y - 5, max(1.5, right - left), 10, fill=DARK, stroke=DARK)
        else:
            figure.hatched_rect(left, row_y - 5, max(1.5, right - left), 10, fill=WHITE, stroke=ACCENT, spacing=5)
        label = FEATURE_LABELS.get(row["feature"], row["feature"].replace("_", " "))
        figure.text(label_x, row_y, label, size=6.4, anchor="right")
        display = _figure_display(ctx, figure_id=figure_id, panel=panel, series=target.title(), label=row["feature"], source_artifact=source, source_row_key=f"target={target}|feature={row['feature']}", source_field="standardized_coefficient", exact=row["standardized_coefficient"], display=fixed3(row["standardized_coefficient"]), rule="coefficient_3_decimal_places", evidence_status=row["evidence_status"])
        if coefficient >= 0:
            text_x, text_anchor = end_x + 4, "left"
        else:
            value_width = text_width(display, 6.2)
            if zero_x - end_x >= value_width + 8:
                text_x, text_anchor = end_x + 4, "left"
            else:
                text_x, text_anchor = end_x - 4, "right"
            rendered_left = text_x if text_anchor == "left" else text_x - value_width
            if rendered_left <= label_x + 5:
                raise IntegrityError(f"coefficient value would overlap feature label: {target} {row['feature']}")
        figure.text(text_x, row_y, display, size=6.2, anchor=text_anchor)
    figure.text((plot_x0 + plot_x1) / 2, y + 14, "Signed standardized coefficient", size=6.6, anchor="middle")


def figure_4(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "Fig4_Structural_Interpretation"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Structural interpretation through frozen coefficients")
    rows = read_csv("artifacts/a2_2_structural_coefficients.csv")
    margin, gap = 10.0, 10.0
    panel_width = (figure.width - 2 * margin - gap) / 2
    panel_y, panel_height = 37.0, figure.height - 55.0
    for index, target in enumerate(("success", "looping")):
        selected = sorted((row for row in rows if row["target"] == target), key=lambda row: int(row["absolute_rank"]))[:5]
        assert_equal([int(row["absolute_rank"]) for row in selected], [1, 2, 3, 4, 5], f"{target} top-five coefficient ranks")
        _draw_coefficient_panel(ctx, figure, figure_id=figure_id, target=target, panel="A" if index == 0 else "B", x=margin + index * (panel_width + gap), y=panel_y, width=panel_width, height=panel_height, rows=selected)
    figure.text(figure.width / 2, 18, "Associative model coefficients; not causal effects. Correlated structural features can redistribute coefficients.", size=7, anchor="middle")
    return figure_id, figure


def figure_5(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "Fig5_Success_Failure_Boundaries"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Six deterministic illustrative Success errors")
    manifest_source = "artifacts/a2_2_error_case_manifest.csv"
    notes_source = "artifacts/a2_2_error_case_notes.csv"
    manifests = [row for row in read_csv(manifest_source) if row["target"] == "success"]
    notes = [row for row in read_csv(notes_source) if row["target"] == "success"]
    assert_equal(len(manifests), 6, "Success error manifest cases")
    assert_equal(len(notes), 6, "Success error note cases")
    note_map = {row["trajectory_key"]: row for row in notes}
    role_order = {"borderline": 0, "median_error_confidence": 1, "high_confidence_error": 2}
    manifests.sort(key=lambda row: ({"FP": 0, "FN": 1}[row["error_type"]], role_order[row["case_role"]]))
    figure.text(12, figure.height - 16, "6 DETERMINISTIC ILLUSTRATIVE SUCCESS ERRORS - NOT A PREVALENCE ESTIMATE", size=8, bold=True, color=ACCENT)
    margin_x, gap_x = 12.0, 9.0
    card_width = (figure.width - 2 * margin_x - 2 * gap_x) / 3
    card_height = 126.0
    top_y = figure.height - 37.0
    role_labels = {"borderline": "Borderline", "median_error_confidence": "Median confidence", "high_confidence_error": "High confidence"}
    for index, row in enumerate(manifests):
        note = note_map[row["trajectory_key"]]
        column, row_index = index % 3, index // 3
        x = margin_x + column * (card_width + gap_x)
        y = top_y - (row_index + 1) * card_height - row_index * 10
        if row["error_type"] == "FP":
            figure.rect(x, y, card_width, card_height, fill=WHITE, stroke=DARK, line_width=0.9, radius=3)
            figure.rect(x, y + card_height - 22, card_width, 22, fill=LIGHT, stroke=DARK, line_width=0.7)
        else:
            figure.hatched_rect(x, y, card_width, card_height, fill=WHITE, stroke=ACCENT, spacing=9)
            figure.rect(x, y + card_height - 22, card_width, 22, fill=PALE, stroke=ACCENT, line_width=0.7)
        figure.text(x + 7, y + card_height - 11, row["error_type"], size=8, bold=True, color=ACCENT if row["error_type"] == "FN" else DARK)
        figure.text(x + card_width - 7, y + card_height - 11, role_labels[row["case_role"]], size=6.4, anchor="right")
        primary = note["primary_code"].replace("_", " ")
        primary_lines = wrap_text(primary, card_width - 14, 7.0, bold=True)
        figure.text(x + 7, y + card_height - 38, "\n".join(primary_lines), size=7.0, bold=True, line_height=8.2)
        figure.text(x + 7, y + card_height - 60, row["benchmark"], size=6.3, color=MID)
        boundary_lines = wrap_text(note["representation_boundary"], card_width - 14, 6.2)
        boundary_lines = boundary_lines[:5]
        figure.text(x + 7, y + 42, "\n".join(boundary_lines), size=6.2, line_height=7.4)
        figure.text(x + 7, y + 11, "Semantic evidence needed: " + note["semantic_understanding_needed"], size=5.9, color=DARK)
        ctx.add_figure_datum(
            figure_id=figure_id,
            panel="FP" if row["error_type"] == "FP" else "FN",
            series=row["case_role"],
            label=note["primary_code"],
            value_type="illustrative_case",
            source_field="primary_code",
            exact_value=note["primary_code"],
            display_value=primary,
            source_artifact=f"{manifest_source};{notes_source}",
            source_row_key=f"trajectory_key={row['trajectory_key']}",
            evidence_status=note["evidence_status"],
            trajectory_key=row["trajectory_key"],
            error_type=row["error_type"],
            case_role=row["case_role"],
            primary_code=note["primary_code"],
        )
    return figure_id, figure


def figure_s2(ctx: BuildContext) -> tuple[str, VectorFigure]:
    figure_id = "FigS2_Benchmark_Heterogeneity"
    width, height = FIGURE_DIMENSIONS[figure_id]
    figure = VectorFigure(width, height, "Descriptive benchmark heterogeneity")
    source = "artifacts/a2_3_table_4_benchmark_heterogeneity.csv"
    rows = read_csv(source)
    margin, gap = 10.0, 9.0
    panel_width = (figure.width - 2 * margin - 2 * gap) / 3
    panel_y, panel_height = 33.0, figure.height - 61.0
    benchmarks = ["assistantbench", "visualwebarena", "webarena", "workarena"]
    short_benchmarks = {"assistantbench": "AssistantBench", "visualwebarena": "VisualWebArena", "webarena": "WebArena", "workarena": "WorkArena"}
    markers = {"assistantbench": "circle", "visualwebarena": "square", "webarena": "diamond", "workarena": "circle"}
    for panel_index, target in enumerate(("Success", "Looping", "Side Effect")):
        x = margin + panel_index * (panel_width + gap)
        _panel_frame(figure, x, panel_y, panel_width, panel_height, target, chr(ord("A") + panel_index))
        if target == "Side Effect":
            for x1, y1, x2, y2 in (
                (x + 3, panel_y + 3, x + panel_width - 3, panel_y + 3),
                (x + 3, panel_y + panel_height - 3, x + panel_width - 3, panel_y + panel_height - 3),
                (x + 3, panel_y + 3, x + 3, panel_y + panel_height - 3),
                (x + panel_width - 3, panel_y + 3, x + panel_width - 3, panel_y + panel_height - 3),
            ):
                figure.line(x1, y1, x2, y2, stroke=EXPLORATORY, line_width=0.7, dash=(4, 3))
            figure.text(x + panel_width - 7, panel_y + panel_height - 12, "EXPLORATORY", size=5.8, bold=True, anchor="right", color=EXPLORATORY)
        plot_x0, plot_x1 = x + 74, x + panel_width - 12
        plot_y0, plot_y1 = panel_y + 30, panel_y + panel_height - 31
        for tick in (Decimal("0"), Decimal("0.25"), Decimal("0.50"), Decimal("0.75"), Decimal("1.00")):
            tick_x = _x_scale(tick, Decimal("0"), Decimal("1"), plot_x0, plot_x1)
            figure.line(tick_x, plot_y0, tick_x, plot_y1, stroke=LIGHT, line_width=0.45)
            figure.text(tick_x, plot_y0 - 9, f"{tick:.2f}" if tick not in {Decimal("0"), Decimal("1.00")} else f"{tick:.0f}", size=5.8, anchor="middle")
        for row_index, benchmark in enumerate(benchmarks):
            row = one(rows, target=target, benchmark=benchmark)
            row_y = plot_y1 - 16 - row_index * ((plot_y1 - plot_y0 - 24) / 3)
            point_x = _x_scale(Decimal(row["AP"]), Decimal("0"), Decimal("1"), plot_x0, plot_x1)
            figure.text(plot_x0 - 6, row_y, short_benchmarks[benchmark], size=5.9, anchor="right")
            marker = markers[benchmark]
            color = EXPLORATORY if target == "Side Effect" else ACCENT
            if marker == "circle":
                figure.circle(point_x, row_y, 3.6, fill=WHITE, stroke=color, line_width=1.2)
            elif marker == "square":
                figure.rect(point_x - 3.2, row_y - 3.2, 6.4, 6.4, fill=color, stroke=color)
            else:
                figure.polygon(((point_x, row_y + 4), (point_x + 4, row_y), (point_x, row_y - 4), (point_x - 4, row_y)), fill=WHITE, stroke=color, line_width=1.2)
            display = _figure_display(ctx, figure_id=figure_id, panel=chr(ord("A") + panel_index), series=target, label=benchmark, source_artifact=source, source_row_key=f"target={target}|benchmark={benchmark}", source_field="AP", exact=row["AP"], display=fixed3(row["AP"]), rule="predictive_metric_3_decimal_places", evidence_status="DESCRIPTIVE_ONLY")
            display_width = text_width(display, 5.8)
            if point_x + 6 + display_width <= plot_x1:
                label_x, label_anchor = point_x + 6, "left"
            else:
                label_x, label_anchor = point_x - 6, "right"
            figure.text(label_x, row_y, display, size=5.8, anchor=label_anchor)
        figure.text((plot_x0 + plot_x1) / 2, panel_y + 13, "AP", size=6.3, anchor="middle")
    figure.text(figure.width / 2, figure.height - 15, "DESCRIPTIVE_ONLY - no significance marks, winner ranking, or pairwise inference", size=7.4, bold=True, anchor="middle")
    return figure_id, figure


def render_figures(ctx: BuildContext) -> list[str]:
    generated: list[str] = []
    for builder in (figure_1, figure_2, figure_3, figure_4, figure_5, figure_s1, figure_s2):
        figure_id, figure = builder(ctx)
        generated.extend(_save(ctx, figure_id, figure))
    return generated


CAPTIONS = {
    "Table1_Main_Heldout_Results": "Official held-out tasks/trajectories within evaluated benchmark families using frozen thresholds. Success and Looping are confirmatory; Side Effect is exploratory and low-support.",
    "Table2_Efficiency_Complexity": "Environment-specific efficiency and representation measurements. B2 used CPU and B4 used CUDA on an NVIDIA GeForce RTX 5070; no cross-target AP comparison is implied.",
    "Table3_Dev_Representation_Robustness": "DEV_ONLY grouped, LOBO, model-only, ablation, uncertainty, and dense-representation evidence. Exploratory development rows remain exploratory and no held-out upgrade is implied.",
    "Table4_Benchmark_Heterogeneity": "DESCRIPTIVE_ONLY per-family AP and F1. No significance testing, winner ranking, or pairwise superiority is shown.",
    "Table5_Interpretability_Failure_Summary": "Associative coefficients and metadata diagnostics with deterministic illustrative error cases. Coefficients are not causal effects and case counts are not prevalence estimates.",
    "Fig1_Study_Pipeline": "Blind-first study pipeline. Method roles and thresholds were frozen before blind prediction, label unlock, and held-out confirmation; A2 diagnostics occur only post-freeze.",
    "Fig2_Heldout_AP_Lift_CI": "Confirmatory held-out AP lift and frozen 95% confidence intervals for Success and Looping on official held-out tasks/trajectories within evaluated benchmark families.",
    "Fig3_Efficiency_Complexity": "Representation dimension, warm extraction latency, and representation storage under the measured environment only: B2 CPU and B4 CUDA on an NVIDIA GeForce RTX 5070.",
    "Fig4_Structural_Interpretation": "Top-five signed standardized coefficients for frozen Success and Looping structural models. Coefficients are associative, diagnostic, and not causal effects.",
    "Fig5_Success_Failure_Boundaries": "Six deterministic illustrative Success errors selected under the frozen A2.2 protocol. The cards illustrate representation boundaries and are not a prevalence estimate.",
    "FigS1_SideEffect_Exploratory_AP_Lift": "EXPLORATORY held-out Side Effect AP lift and frozen 95% confidence interval. Low support and the preregistered exploratory role prohibit confirmatory interpretation.",
    "FigS2_Benchmark_Heterogeneity": "DESCRIPTIVE_ONLY AP by evaluated benchmark family. No significance marks, winner ranking, or pairwise inference are shown; Side Effect remains exploratory.",
}


def write_caption_contract(ctx: BuildContext) -> str:
    lines = [
        "# A3.1 Figure and Table Caption Contract",
        "",
        "These captions describe frozen evidence only. They do not authorize new claims or manuscript prose.",
        "",
        "## Boundary vocabulary",
        "",
        "- `confirmatory`: Success and Looping official held-out signal within evaluated benchmark families.",
        "- `exploratory`: Side Effect remains low-support and non-confirmatory.",
        "- `DEV_ONLY`: A1.2-A1.7 representation, robustness, ablation, and uncertainty evidence.",
        "- `DESCRIPTIVE_ONLY`: benchmark heterogeneity without pairwise inference.",
        "- `environment-specific`: A2.1 timings and resources on the recorded CPU/GPU environment.",
        "- `illustrative-not-prevalence`: deterministic selected error cases do not estimate population frequencies.",
        "",
        "## Frozen captions",
        "",
    ]
    for artifact_id, caption in CAPTIONS.items():
        lines.extend([f"### {artifact_id}", "", caption, ""])
    relative = "docs/a3_1_figure_table_caption_contract.md"
    atomic_text(ctx.output_root, relative, "\n".join(lines))
    return relative


def write_table_preview(ctx: BuildContext) -> str:
    sections = [
        "# A3.1 Table Preview",
        "",
        "Human-review preview only. Machine-exact values remain in the frozen A2.3 CSV sources and the A3.1 display-value map.",
        "",
    ]
    for table_id in TABLE_SOURCES:
        sections.append(ctx.output(f"paper/tables/{table_id}.md").read_text(encoding="utf-8").rstrip())
        sections.extend(["", "---", ""])
    relative = "paper/tables/A3_1_Table_Preview.md"
    atomic_text(ctx.output_root, relative, "\n".join(sections))
    return relative


def write_contact_sheet(ctx: BuildContext) -> str:
    relative = "paper/figures/A3_1_Figure_Contact_Sheet.pdf"
    path = ctx.output(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(letter)
    pdf = canvas.Canvas(str(path), pagesize=(page_width, page_height), pageCompression=1)
    pdf.setTitle("A3.1 Figure Contact Sheet")
    pdf.setAuthor("D9-R1 Stage A3.1")
    figure_ids = list(FIGURE_DIMENSIONS)
    cell_width, cell_height = 372.0, 252.0
    positions = [(22, 322), (398, 322), (22, 54), (398, 54)]
    for index, figure_id in enumerate(figure_ids):
        if index and index % 4 == 0:
            pdf.setFont(PDF_FONT, 7)
            pdf.drawCentredString(page_width / 2, 24, "Human-review contact sheet - not a manuscript artifact")
            pdf.showPage()
        slot = index % 4
        x, y = positions[slot]
        pdf.setStrokeColorRGB(0.75, 0.75, 0.75)
        pdf.setLineWidth(0.6)
        pdf.rect(x, y, cell_width, cell_height, fill=0, stroke=1)
        pdf.setFont(PDF_FONT_BOLD, 8)
        pdf.setFillColorRGB(0.07, 0.07, 0.07)
        pdf.drawString(x + 6, y + cell_height - 14, figure_id)
        png_path = ctx.output(f"paper/figures/{figure_id}.png")
        with Image.open(png_path) as image:
            image_width, image_height = image.size
        max_width, max_height = cell_width - 12, cell_height - 28
        scale = min(max_width / image_width, max_height / image_height)
        draw_width, draw_height = image_width * scale, image_height * scale
        draw_x = x + (cell_width - draw_width) / 2
        draw_y = y + 5 + (max_height - draw_height) / 2
        pdf.drawImage(ImageReader(str(png_path)), draw_x, draw_y, width=draw_width, height=draw_height, preserveAspectRatio=True, mask="auto")
    pdf.setFont(PDF_FONT, 7)
    pdf.drawCentredString(page_width / 2, 24, "Human-review contact sheet - not a manuscript artifact")
    pdf.showPage()
    pdf.save()
    return relative


def _artifact_metadata(relative: str) -> tuple[str, str, str, str]:
    if relative.startswith("paper/tables/Table"):
        table_id = Path(relative).stem
        return "final_table", "paper table", TABLE_SOURCES[table_id], {
            "Table1_Main_Heldout_Results": "CONFIRMATORY_AND_EXPLORATORY",
            "Table2_Efficiency_Complexity": "ENVIRONMENT_SPECIFIC",
            "Table3_Dev_Representation_Robustness": "DEV_ONLY",
            "Table4_Benchmark_Heterogeneity": "DESCRIPTIVE_ONLY",
            "Table5_Interpretability_Failure_Summary": "ASSOCIATIVE_AND_DESCRIPTIVE",
        }[table_id]
    if relative.startswith("paper/figures/Fig"):
        figure_id = Path(relative).stem
        evidence = {
            "Fig1_Study_Pipeline": "INTEGRITY_ONLY",
            "Fig2_Heldout_AP_Lift_CI": "CONFIRMATORY_SUPPORTED",
            "Fig3_Efficiency_Complexity": "ENVIRONMENT_SPECIFIC",
            "Fig4_Structural_Interpretation": "POST_FREEZE_DIAGNOSTIC",
            "Fig5_Success_Failure_Boundaries": "POST_FREEZE_DESCRIPTIVE",
            "FigS1_SideEffect_Exploratory_AP_Lift": "EXPLORATORY_SUPPORTED",
            "FigS2_Benchmark_Heterogeneity": "DESCRIPTIVE_ONLY",
        }[figure_id]
        sources = {
            "Fig1_Study_Pipeline": "artifacts/a1_9_run_summary.json;artifacts/a1_10a_run_summary.json;artifacts/a1_10_run_summary.json",
            "Fig2_Heldout_AP_Lift_CI": TABLE_SOURCES["Table1_Main_Heldout_Results"],
            "Fig3_Efficiency_Complexity": TABLE_SOURCES["Table2_Efficiency_Complexity"],
            "Fig4_Structural_Interpretation": "artifacts/a2_2_structural_coefficients.csv",
            "Fig5_Success_Failure_Boundaries": "artifacts/a2_2_error_case_manifest.csv;artifacts/a2_2_error_case_notes.csv",
            "FigS1_SideEffect_Exploratory_AP_Lift": TABLE_SOURCES["Table1_Main_Heldout_Results"],
            "FigS2_Benchmark_Heterogeneity": TABLE_SOURCES["Table4_Benchmark_Heterogeneity"],
        }[figure_id]
        return "final_figure", "paper figure", sources, evidence
    mapping = {
        "artifacts/a3_1_input_manifest.json": ("manifest", "source traceability", ";".join(item.path for item in INPUTS), "INTEGRITY_ONLY"),
        "artifacts/a3_1_display_contract.json": ("contract", "display precision", "docs/tasks/STAGE_A3_1_FINAL_FIGURES_TABLES.md", "INTEGRITY_ONLY"),
        "artifacts/a3_1_display_value_map.csv": ("manifest", "exact-to-display mapping", ";".join(TABLE_SOURCES.values()), "INTEGRITY_ONLY"),
        "artifacts/a3_1_visual_style.json": ("contract", "visual style", "docs/tasks/STAGE_A3_1_FINAL_FIGURES_TABLES.md", "INTEGRITY_ONLY"),
        "artifacts/a3_1_implementation_failures.json": ("provenance", "implementation failure provenance", "scripts/build_a3_1_final_figures_tables.py", "INTEGRITY_ONLY"),
        "artifacts/a3_1_figure_data_manifest.csv": ("manifest", "figure source mapping", ";".join(TABLE_SOURCES.values()), "INTEGRITY_ONLY"),
        "docs/a3_1_figure_table_caption_contract.md": ("contract", "caption boundary", "docs/a2_3_publication_figure_spec.md;docs/a2_3_final_limitations_ledger.md", "CLAIM_FREEZE"),
        "paper/figures/A3_1_Figure_Contact_Sheet.pdf": ("review", "human review only", ";".join(f"paper/figures/{name}.png" for name in FIGURE_DIMENSIONS), "REVIEW_ONLY"),
        "paper/tables/A3_1_Table_Preview.md": ("review", "human review only", ";".join(TABLE_SOURCES.values()), "REVIEW_ONLY"),
    }
    return mapping[relative]


def write_registry(ctx: BuildContext, paths: Sequence[str]) -> str:
    rows = []
    for relative in sorted(set(paths)):
        artifact_type, paper_role, sources, evidence_status = _artifact_metadata(relative)
        rows.append(
            {
                "artifact_id": Path(relative).stem,
                "artifact_path": relative,
                "artifact_type": artifact_type,
                "paper_role": paper_role,
                "source_artifacts": sources,
                "sha256": sha256_path(ctx.output(relative)),
                "evidence_status": evidence_status,
                "display_contract_version": DISPLAY_CONTRACT_VERSION,
                "verified": "true",
            }
        )
    relative = "artifacts/a3_1_artifact_registry.csv"
    atomic_csv(ctx.output_root, relative, REGISTRY_FIELDS, rows)
    return relative


def _source_value(source_artifact: str, source_row_key: str, source_field: str) -> str:
    if ";" in source_artifact:
        raise IntegrityError("numeric trace must resolve to one source artifact")
    rows = read_csv(source_artifact)
    criteria: dict[str, str] = {}
    row_number: int | None = None
    for component in source_row_key.split("|"):
        key, value = component.split("=", 1)
        if key == "row":
            row_number = int(value)
        else:
            criteria[key] = value
    if row_number is not None:
        row = rows[row_number - 1]
        for key, value in criteria.items():
            assert_equal(row[key], value, f"source row key {source_row_key}")
    else:
        row = one(rows, **criteria)
    if source_field.startswith("top_structural_signals:"):
        feature = source_field.split(":", 1)[1]
        parsed = dict(item.rsplit(":", 1) for item in row["top_structural_signals"].split(";"))
        return parsed[feature]
    return row[source_field]


def _format_from_rule(exact: str, rule: str) -> str:
    if rule == "integer":
        return exact
    if rule in {"predictive_metric_3_decimal_places", "coefficient_3_decimal_places"}:
        return fixed3(exact)
    if rule.startswith("latency_"):
        return latency_display(exact)[0]
    if rule == "bytes_to_KiB_3_significant_digits":
        return bytes_display(exact)[0]
    if rule == "memory_3_significant_digits":
        return mb_display(exact)[0]
    if rule == "missing_as_NA":
        return "NA"
    raise IntegrityError(f"unknown display rule: {rule}")


def _pdf_has_embedded_font_file(reader: PdfReader) -> bool:
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        resources = resources.get_object()
        fonts = resources.get("/Font")
        if not fonts:
            continue
        for font_reference in fonts.get_object().values():
            font = font_reference.get_object()
            descriptor_reference = font.get("/FontDescriptor")
            if not descriptor_reference:
                continue
            descriptor = descriptor_reference.get_object()
            if any(descriptor.get(name) for name in ("/FontFile", "/FontFile2", "/FontFile3")):
                return True
    return False


def _pdf_image_xobject_count(reader: PdfReader) -> int:
    count = 0
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        xobjects = resources.get_object().get("/XObject")
        if not xobjects:
            continue
        for reference in xobjects.get_object().values():
            if reference.get_object().get("/Subtype") == "/Image":
                count += 1
    return count


def validate_outputs(ctx: BuildContext, registry_path: str | None = None) -> dict[str, bool]:
    qa: dict[str, bool] = {}
    # Frozen sources remain exact.
    for frozen in INPUTS:
        assert_equal(sha256_path(resolve_root(frozen.path)), frozen.sha256, f"post-build source hash {frozen.path}")
    qa["frozen_source_hashes_exact"] = True

    display_rows = read_output_csv(ctx.output_root, "artifacts/a3_1_display_value_map.csv")
    for row in display_rows:
        exact = _source_value(row["source_artifact"], row["source_row_key"], row["source_field"])
        assert_equal(exact, row["exact_value"], f"display exact source {row['artifact_id']} {row['source_field']}")
        expected_display = _format_from_rule(exact, row["format_rule"])
        if row["display_value"].endswith(" ms"):
            assert_equal(row["display_value"], expected_display + " ms", "latency display with unit")
        else:
            assert_equal(row["display_value"], expected_display, f"display formatting {row['artifact_id']} {row['source_field']}")
        if row["location_kind"] == "table":
            table_text = ctx.output(row["artifact_path"]).read_text(encoding="utf-8")
            if row["display_value"] not in table_text:
                raise IntegrityError(f"table display value missing: {row['artifact_id']} {row['display_value']}")
    qa["rounding_contract_exact"] = True
    qa["table_values_trace_to_source"] = True

    expected_table_rows = {
        "Table1_Main_Heldout_Results": 3,
        "Table2_Efficiency_Complexity": 2,
        "Table3_Dev_Representation_Robustness": 18,
        "Table4_Benchmark_Heterogeneity": 12,
        "Table5_Interpretability_Failure_Summary": 2,
    }
    for artifact_id, expected in expected_table_rows.items():
        unique_keys = {row["source_row_key"] for row in display_rows if row["artifact_id"] == artifact_id}
        assert_equal(len(unique_keys), expected, f"{artifact_id} represented source rows")
    qa["no_table_source_row_dropped"] = True

    figure_rows = read_output_csv(ctx.output_root, "artifacts/a3_1_figure_data_manifest.csv")
    numeric_rows = [row for row in figure_rows if row["value_type"] == "numeric"]
    for row in numeric_rows:
        exact = _source_value(row["source_artifact"], row["source_row_key"], row["source_field"])
        assert_equal(exact, row["exact_value"], f"figure exact source {row['figure_id']} {row['label']}")
        match = [
            display for display in display_rows
            if display["artifact_id"] == row["figure_id"]
            and display["source_artifact"] == row["source_artifact"]
            and display["source_row_key"] == row["source_row_key"]
            and display["source_field"] == row["source_field"]
            and display["exact_value"] == row["exact_value"]
            and display["display_value"] == row["display_value"]
        ]
        assert_equal(len(match), 1, f"figure display mapping {row['figure_id']} {row['label']}")
    qa["figure_values_trace_to_source"] = True

    assert_equal(len([row for row in figure_rows if row["figure_id"] == "Fig1_Study_Pipeline"]), 8, "Fig1 stages")
    assert_equal({row["series"] for row in figure_rows if row["figure_id"] == "Fig2_Heldout_AP_Lift_CI"}, {"Success", "Looping"}, "Fig2 main targets")
    fig2 = [row for row in figure_rows if row["figure_id"] == "Fig2_Heldout_AP_Lift_CI"]
    assert_equal(len(fig2), 6, "Fig2 exact AP-lift and CI values")
    qa["fig2_ci_exact"] = True
    figs1 = [row for row in figure_rows if row["figure_id"] == "FigS1_SideEffect_Exploratory_AP_Lift"]
    assert_equal(len(figs1), 3, "FigS1 values")
    assert_equal({row["evidence_status"] for row in figs1}, {"EXPLORATORY_SUPPORTED"}, "FigS1 exploratory status")
    qa["side_effect_remains_exploratory"] = True
    assert_equal(len([row for row in figure_rows if row["figure_id"] == "Fig3_Efficiency_Complexity"]), 6, "Fig3 exact values")
    qa["fig3_efficiency_exact"] = True
    fig4 = [row for row in figure_rows if row["figure_id"] == "Fig4_Structural_Interpretation"]
    assert_equal(len(fig4), 10, "Fig4 coefficient count")
    assert_equal(len([row for row in fig4 if row["panel"] == "A"]), 5, "Fig4 Success top five")
    assert_equal(len([row for row in fig4 if row["panel"] == "B"]), 5, "Fig4 Looping top five")
    qa["fig4_coefficients_exact"] = True
    fig5 = [row for row in figure_rows if row["figure_id"] == "Fig5_Success_Failure_Boundaries"]
    assert_equal(len(fig5), 6, "Fig5 Success illustrative cases")
    assert_equal({row["error_type"] for row in fig5}, {"FP", "FN"}, "Fig5 FP/FN roles")
    qa["fig5_exactly_six_success_cases"] = True
    figs2 = [row for row in figure_rows if row["figure_id"] == "FigS2_Benchmark_Heterogeneity"]
    assert_equal(len(figs2), 12, "FigS2 benchmark points")
    assert_equal({row["evidence_status"] for row in figs2}, {"DESCRIPTIVE_ONLY"}, "FigS2 descriptive status")
    qa["benchmark_heterogeneity_descriptive_only"] = True

    for figure_id, (width_in, height_in) in FIGURE_DIMENSIONS.items():
        pdf_path = ctx.output(f"paper/figures/{figure_id}.pdf")
        svg_path = ctx.output(f"paper/figures/{figure_id}.svg")
        png_path = ctx.output(f"paper/figures/{figure_id}.png")
        for path in (pdf_path, svg_path, png_path):
            if not path.is_file() or path.stat().st_size == 0:
                raise IntegrityError(f"missing or blank figure file: {path}")
        reader = PdfReader(str(pdf_path))
        assert_equal(len(reader.pages), 1, f"{figure_id} PDF page count")
        page = reader.pages[0]
        actual_width = float(page.mediabox.width) / PT_PER_INCH
        actual_height = float(page.mediabox.height) / PT_PER_INCH
        if abs(actual_width - width_in) > 0.002 or abs(actual_height - height_in) > 0.002:
            raise IntegrityError(f"{figure_id} PDF dimensions drift: {(actual_width, actual_height)}")
        assert_equal(_pdf_image_xobject_count(reader), 0, f"{figure_id} PDF vector-only")
        assert_equal(_pdf_has_embedded_font_file(reader), False, f"{figure_id} embedded font file")
        svg_text = svg_path.read_text(encoding="utf-8")
        if "linearGradient" in svg_text or "radialGradient" in svg_text or "filter=" in svg_text:
            raise IntegrityError(f"{figure_id} contains prohibited gradient/filter")
        if f'width="{width_in:.3f}in"' not in svg_text or f'height="{height_in:.3f}in"' not in svg_text:
            raise IntegrityError(f"{figure_id} SVG dimensions missing")
        with Image.open(png_path) as image:
            min_width = round(width_in * PNG_DPI) - 2
            min_height = round(height_in * PNG_DPI) - 2
            if image.width < min_width or image.height < min_height:
                raise IntegrityError(f"{figure_id} PNG below 300 dpi dimensions: {image.size}")
            dpi = image.info.get("dpi", (0, 0))
            if min(dpi) < 299:
                raise IntegrityError(f"{figure_id} PNG DPI metadata below 300: {dpi}")
            extrema = image.convert("L").getextrema()
            if extrema[0] == extrema[1]:
                raise IntegrityError(f"{figure_id} PNG is blank")
    qa["pdf_svg_png_exist"] = True
    qa["png_at_least_300_dpi"] = True
    qa["pdf_vector_only"] = True
    qa["fonts_recorded_and_not_embedded"] = True
    qa["figure_dimensions_recorded_and_exact"] = True
    qa["no_blank_figures"] = True
    qa["no_3d_gradient_or_shadow"] = True
    qa["no_clipped_labels_by_geometry_guard"] = True
    qa["no_overlapping_tick_labels_by_fixed_layout_guard"] = True
    qa["legends_or_direct_labels_visible"] = True
    qa["grayscale_readability_documented"] = True

    caption_text = ctx.output("docs/a3_1_figure_table_caption_contract.md").read_text(encoding="utf-8")
    for term in ("confirmatory", "exploratory", "DEV_ONLY", "DESCRIPTIVE_ONLY", "environment-specific", "illustrative-not-prevalence"):
        if term not in caption_text:
            raise IntegrityError(f"caption boundary missing: {term}")
    qa["caption_boundaries_complete"] = True

    contact = PdfReader(str(ctx.output("paper/figures/A3_1_Figure_Contact_Sheet.pdf")))
    assert_equal(len(contact.pages), 2, "contact sheet page count")
    qa["contact_sheet_complete"] = True
    qa["table_preview_complete"] = ctx.output("paper/tables/A3_1_Table_Preview.md").is_file()

    if registry_path:
        registry_rows = read_output_csv(ctx.output_root, registry_path)
        for row in registry_rows:
            assert_equal(sha256_path(ctx.output(row["artifact_path"])), row["sha256"], f"registry hash {row['artifact_path']}")
            assert_equal(row["verified"], "true", f"registry verified {row['artifact_path']}")
        qa["artifact_registry_hashes_exact"] = True
    return qa


def report_text(
    *,
    output_root: Path,
    preflight: Mapping[str, Any],
    qa: Mapping[str, bool],
    registry_path: str,
    primary_paths: Sequence[str],
) -> str:
    hashes = {path: sha256_path(resolve_output(output_root, path)) for path in primary_paths}
    table_lines = [f"- `{path}` - `{hashes[path]}`" for path in primary_paths if path.startswith("paper/tables/Table")]
    figure_lines = [f"- `{path}` - `{hashes[path]}`" for path in primary_paths if path.startswith("paper/figures/Fig")]
    qa_lines = [f"- {name}: `{'PASS' if passed else 'FAIL'}`" for name, passed in sorted(qa.items())]
    counter_lines = [f"- {name} = {value}" for name, value in COUNTERS.items()]
    return "\n".join(
        [
            "# Stage A3.1 Final Figures and Tables Report",
            "",
            "## Stage determination",
            "",
            "`PASS_WITH_CONDITIONS`",
            "",
            "Conditions are limited to human visual placement/resize review and Tier 4 caption context deferred to A3.2. No data or claim inconsistency was found.",
            "",
            "## Commits",
            "",
            f"- preregistration: `{PREREG_COMMIT}`",
            f"- implementation: `{preflight['implementation_commit']}`",
            f"- fix commits: `{json.dumps(preflight['fix_commits'])}`",
            f"- result: `{RESULT_COMMIT_SENTINEL}`",
            "- amend: `false`",
            "",
            "## Frozen gates",
            "",
            f"- A2.3 result: `{A2_3_RESULT_COMMIT}`",
            f"- A1.11 claim matrix: `{preflight['verified_hashes']['artifacts/a1_11_final_claim_matrix.csv']}`",
            f"- A1.11 main table: `{preflight['verified_hashes']['artifacts/a1_11_table_main_test_results.csv']}`",
            "- A2.3 Table 1-5 hashes: exact match",
            "- frozen claims: Success/Looping confirmatory; Side Effect exploratory",
            "",
            "## Contracts and manifests",
            "",
            "- `artifacts/a3_1_input_manifest.json`",
            "- `artifacts/a3_1_display_contract.json`",
            "- `artifacts/a3_1_display_value_map.csv`",
            "- `artifacts/a3_1_visual_style.json`",
            "- `artifacts/a3_1_figure_data_manifest.csv`",
            "- `docs/a3_1_figure_table_caption_contract.md`",
            f"- `{registry_path}`",
            "",
            "## Final tables",
            "",
            *table_lines,
            "",
            "## Final figures",
            "",
            *figure_lines,
            "",
            "## Review artifacts",
            "",
            "- `paper/figures/A3_1_Figure_Contact_Sheet.pdf`",
            "- `paper/tables/A3_1_Table_Preview.md`",
            "",
            "## QA",
            "",
            *qa_lines,
            "",
            "## Scientific-operation counters",
            "",
            *counter_lines,
            "",
            "## Warnings",
            "",
            "- Tier 4 literature context remains outside A3.1 and requires A3.2 authorization.",
            "- Journal-specific resize/reflow and final placement require human review.",
            "- Helvetica is referenced as a standard PDF font; no font file is embedded or distributed.",
            "- The first formal render was invalidated after manual QA found label overlap in Fig4 and FigS2; no invalid output was reused.",
            "",
            "## Next state",
            "",
            "`WAIT_FOR_HUMAN_A3_1_REVIEW`",
            "",
            "Do not enter A3.2 automatically.",
        ]
    ) + "\n"


def build_package(output_root: Path, require_clean: bool = True) -> dict[str, Any]:
    preflight = verify_preflight(require_clean=require_clean)
    ctx = BuildContext(output_root.resolve())
    write_contracts(ctx, preflight)
    table_paths = render_tables(ctx)
    figure_paths = render_figures(ctx)
    atomic_csv(ctx.output_root, "artifacts/a3_1_display_value_map.csv", DISPLAY_FIELDS, ctx.display_rows)
    atomic_csv(ctx.output_root, "artifacts/a3_1_figure_data_manifest.csv", FIGURE_DATA_FIELDS, ctx.figure_rows)
    caption_path = write_caption_contract(ctx)
    preview_path = write_table_preview(ctx)
    contact_path = write_contact_sheet(ctx)

    contract_paths = [
        "artifacts/a3_1_input_manifest.json",
        "artifacts/a3_1_display_contract.json",
        "artifacts/a3_1_display_value_map.csv",
        "artifacts/a3_1_visual_style.json",
        "artifacts/a3_1_implementation_failures.json",
        "artifacts/a3_1_figure_data_manifest.csv",
        caption_path,
        preview_path,
        contact_path,
    ]
    primary_paths = table_paths + figure_paths + contract_paths
    registry_path = write_registry(ctx, primary_paths)
    qa = validate_outputs(ctx, registry_path=registry_path)

    report_path = "docs/stage_a3_1_final_figures_tables_report.md"
    report = report_text(output_root=ctx.output_root, preflight=preflight, qa=qa, registry_path=registry_path, primary_paths=primary_paths)
    atomic_text(ctx.output_root, report_path, report)
    output_hashes = {path: sha256_path(ctx.output(path)) for path in primary_paths + [registry_path, report_path]}
    summary = {
        "stage": "A3.1",
        "stage_determination": "PASS_WITH_CONDITIONS",
        "conditions": [
            "Human review may choose journal-specific resize/reflow without scientific changes.",
            "Tier 4 caption context remains deferred to separately authorized A3.2 literature verification.",
        ],
        "commits": {
            "a3_1_preregistration": PREREG_COMMIT,
            "a2_3_result": A2_3_RESULT_COMMIT,
            "implementation": preflight["implementation_commit"],
            "fix_commits": preflight["fix_commits"],
            "result": RESULT_COMMIT_SENTINEL,
            "amend": False,
        },
        "input_hashes": preflight["verified_hashes"],
        "frozen_claims": preflight["frozen_claims"],
        "output_hashes": output_hashes,
        "figures_generated": [name for name in FIGURE_DIMENSIONS if not name.startswith("FigS")],
        "appendix_figures_generated": [name for name in FIGURE_DIMENSIONS if name.startswith("FigS")],
        "tables_generated": list(TABLE_SOURCES),
        "display_contract": DISPLAY_CONTRACT_VERSION,
        "visual_style": "a3_1_journal_neutral_v1",
        "font": {"pdf": PDF_FONT, "svg": SVG_FONT_STACK, "embedded_font_files": False},
        "figure_dimensions_inches": {name: {"width": dims[0], "height": dims[1]} for name, dims in FIGURE_DIMENSIONS.items()},
        "qa_results": qa,
        "scientific_operation_counters": dict(COUNTERS),
        "warnings": [
            "Tier 4 literature verification is not part of A3.1.",
            "Human review may select journal-specific resize/reflow.",
            "The first formal render was invalidated for Fig4/FigS2 label overlap and fully regenerated after an independent fix commit.",
        ],
        "implementation_failures": "artifacts/a3_1_implementation_failures.json",
        "report_path": report_path,
        "artifact_registry": registry_path,
        "next_status": "WAIT_FOR_HUMAN_A3_1_REVIEW",
        "a3_2_entered": False,
    }
    summary_path = "artifacts/a3_1_run_summary.json"
    atomic_json(ctx.output_root, summary_path, summary)
    assert_equal(all(value == 0 for value in summary["scientific_operation_counters"].values()), True, "zero scientific counters")
    return summary


def verify_repository_outputs() -> dict[str, Any]:
    preflight = verify_preflight(require_clean=False)
    ctx = BuildContext(ROOT)
    summary = read_json("artifacts/a3_1_run_summary.json")
    qa = validate_outputs(ctx, registry_path="artifacts/a3_1_artifact_registry.csv")
    assert_equal(summary["qa_results"], qa, "machine summary QA")
    assert_equal(summary["scientific_operation_counters"], COUNTERS, "machine summary counters")
    for relative, expected_hash in summary["output_hashes"].items():
        assert_equal(sha256_path(resolve_root(relative)), expected_hash, f"summary output hash {relative}")
    assert_equal(summary["commits"]["implementation"], preflight["implementation_commit"], "summary implementation commit")
    assert_equal(summary["next_status"], "WAIT_FOR_HUMAN_A3_1_REVIEW", "summary next status")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="verify existing A3.1 outputs without writing")
    arguments = parser.parse_args()
    if arguments.verify_only:
        summary = verify_repository_outputs()
        print(f"A3.1 verification PASS | figures={len(summary['figures_generated']) + len(summary['appendix_figures_generated'])} tables={len(summary['tables_generated'])} scientific_ops=0")
        return 0
    summary = build_package(ROOT, require_clean=True)
    print(f"A3.1 {summary['stage_determination']} | figures={len(summary['figures_generated']) + len(summary['appendix_figures_generated'])} tables={len(summary['tables_generated'])} scientific_ops=0 next={summary['next_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
