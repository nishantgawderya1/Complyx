"""Command line audit runner.

Runs the full pipeline on a PDF and prints the verdict:

    python -m scripts.audit_cli path/to/certificate.pdf

With no NVIDIA API key configured the pipeline falls back to the mock client,
so the wiring can be exercised before credentials exist. To see the engine
decide real verdicts offline:

    python -m scripts.audit_cli --demo

which builds synthetic certificates in memory and runs each through the same
code path the API will use.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

# Allow `python scripts/audit_cli.py` as well as `python -m scripts.audit_cli`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.doc_auditor import AuditError, audit_document  # noqa: E402
from engines.llm_client import MockLLMClient  # noqa: E402
from models.audit import AuditVerdict, ComplianceOutcome  # noqa: E402

SEPARATOR = "=" * 78
RULE = "-" * 78


def _field(
    value: Any,
    unit: str | None = None,
    page: int = 1,
    confidence: str = "high",
    source: str | None = None,
) -> dict[str, Any]:
    """Build one extracted-field payload for a demo fixture."""
    return {
        "value": value,
        "unit": unit,
        "page": page,
        "source_text": source or f"{value} {unit or ''}".strip(),
        "confidence": confidence,
    }


def _format_number(value: float | None) -> str:
    """Render a number without trailing noise, or a dash when absent."""
    if value is None:
        return "-"
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def render_verdict(verdict: AuditVerdict) -> str:
    """Render a verdict as a terminal report."""
    lines: list[str] = [SEPARATOR, " COMPLYX AUDIT RESULT", SEPARATOR]

    lines.append(f" Document        : {verdict.document_name}")
    lines.append(f" SHA-256         : {verdict.document_hash[:32]}...")
    lines.append(f" Grade detected  : {verdict.material_grade_detected or '-'}")
    lines.append(f" Standard applied: {verdict.standard_applied or '-'}")
    lines.append(f" Clause          : {verdict.clause_reference or '-'}")
    lines.append(f" Heat number     : {verdict.heat_number or '-'}")
    lines.append(f" Model           : {verdict.model_used or '-'}")
    lines.append("")
    lines.append(f" VERDICT: {verdict.overall_result.value}")
    lines.append("")

    if verdict.parameters:
        lines.append(
            f" {'PARAMETER':<24}{'VALUE':>10} {'UNIT':<6}"
            f"{'MIN':>9}{'MAX':>9}{'DELTA':>10}  RESULT"
        )
        lines.append(RULE)

        for p in verdict.parameters:
            shown = p.normalised_value if p.normalised_value is not None else p.extracted_value
            unit = p.unit or p.extracted_unit or ""
            lines.append(
                f" {p.field_name:<24}{_format_number(shown):>10} {unit:<6}"
                f"{_format_number(p.required_min):>9}"
                f"{_format_number(p.required_max):>9}"
                f"{_format_number(p.delta):>10}  {p.result.value}"
            )
        lines.append(RULE)

    if verdict.review_reasons:
        lines.append("")
        lines.append(" REVIEW REQUIRED:")
        for reason in verdict.review_reasons:
            lines.append(f"   - {reason}")

    if verdict.warnings:
        lines.append("")
        lines.append(" WARNINGS:")
        for warning in verdict.warnings:
            lines.append(f"   - {warning}")

    lines.append("")
    if not verdict.knowledge_base_verified:
        lines.append(
            " [!] Thresholds are UNVERIFIED - not checked against the governing "
            "code edition."
        )
    lines.append(" [!] Not final until a human confirms this result.")
    lines.append(SEPARATOR)

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Demo fixtures
# --------------------------------------------------------------------------

_CERT_TEXT = """MATERIAL TEST CERTIFICATE
Certificate No: MTC-2026-0412
Specification: ASTM A516/A516M-17   Grade: 70
Heat Number: HT-2891-B
Nominal Thickness: 12 mm
Yield Strength: 265 MPa   Tensile Strength: 480 MPa   Elongation: 24 %
C 0.21  Mn 1.05  P 0.012  S 0.008  Si 0.28
"""


def _base_extraction() -> dict[str, Any]:
    return {
        "document_type": "MTC",
        "specification": _field("ASTM A516/A516M"),
        "material_grade": _field("70"),
        "heat_number": _field("HT-2891-B"),
        "product_form": _field("plate"),
        "nominal_thickness": _field(12, "mm"),
        "yield_strength": _field(265, "MPa"),
        "tensile_strength": _field(480, "MPa"),
        "elongation": _field(24, "%"),
        "chemical_composition": {
            "C": _field(0.21, "%"),
            "Mn": _field(1.05, "%"),
            "P": _field(0.012, "%"),
            "S": _field(0.008, "%"),
            "Si": _field(0.28, "%"),
        },
        "uncertain_fields": [],
        "notes": None,
    }


def _demo_cases() -> list[tuple[str, dict[str, Any]]]:
    """Scenarios exercising each verdict path."""
    failing = _base_extraction()

    passing = _base_extraction()
    passing["tensile_strength"] = _field(520, "MPa")
    passing["yield_strength"] = _field(300, "MPa")

    imperial = _base_extraction()
    imperial["tensile_strength"] = _field(75, "ksi")
    imperial["yield_strength"] = _field(45, "ksi")
    imperial["nominal_thickness"] = _field(0.5, "in")

    unknown_grade = _base_extraction()
    unknown_grade["specification"] = _field("ASTM A999")
    unknown_grade["material_grade"] = _field("1")

    no_thickness = _base_extraction()
    no_thickness["tensile_strength"] = _field(520, "MPa")
    no_thickness["nominal_thickness"] = _field(None, None, confidence="not_found")

    low_confidence = _base_extraction()
    low_confidence["tensile_strength"] = _field(520, "MPa", confidence="low")
    low_confidence["uncertain_fields"] = ["tensile_strength"]

    ambiguous_unit = _base_extraction()
    ambiguous_unit["tensile_strength"] = _field(520, None)

    return [
        ("Tensile below minimum", failing),
        ("Fully conforming certificate", passing),
        ("Imperial units (ksi / inch)", imperial),
        ("Grade not in knowledge base", unknown_grade),
        ("Thickness missing, limits are thickness-dependent", no_thickness),
        ("Model flagged a reading as uncertain", low_confidence),
        ("Strength value with no unit", ambiguous_unit),
    ]


def _synthetic_pdf(text: str) -> bytes:
    """Build a small native-text PDF in memory."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def run_demo() -> int:
    """Run every demo scenario through the real pipeline with a mock model."""
    pdf_bytes = _synthetic_pdf(_CERT_TEXT)

    for title, payload in _demo_cases():
        print()
        print(f"### SCENARIO: {title}")
        client = MockLLMClient(response=payload)
        try:
            verdict = audit_document(pdf_bytes, "demo_certificate.pdf", llm_client=client)
        except AuditError as exc:
            print(f" AUDIT ERROR: {exc}")
            continue
        print(render_verdict(verdict))

    return 0


def run_file(path: Path) -> int:
    """Audit a real PDF from disk."""
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    try:
        verdict = audit_document(path.read_bytes(), path.name)
    except AuditError as exc:
        print(f"AUDIT ERROR: {exc}", file=sys.stderr)
        return 1

    print(render_verdict(verdict))
    return 0 if verdict.overall_result is not ComplianceOutcome.FAIL else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a Complyx compliance audit on a document."
    )
    parser.add_argument("pdf", nargs="?", type=Path, help="Path to a PDF to audit.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run built-in scenarios offline instead of reading a file.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)-8s %(name)s: %(message)s",
    )

    if args.demo:
        return run_demo()
    if args.pdf is None:
        parser.print_help()
        return 2
    return run_file(args.pdf)


if __name__ == "__main__":
    raise SystemExit(main())
