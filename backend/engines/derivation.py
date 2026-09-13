"""Qualified range derivation.

Given the actual values welded, compute what the welder is qualified for under
ASME Section IX. This is the deliverable: the Qualified Range column of the
WPQR is not copied from anywhere, it is derived, and that derivation is where
errors hide because a wrong range looks exactly like a right one on paper.

Two properties make this defensible, and both are structural rather than
aspirational:

**No model is involved.** This is plain Python over reviewer-signed tables. The
vision model reads what is printed on the source documents; it never decides
what those values qualify. That separation is the reason a wrong extraction
produces a visibly wrong actual value rather than a silently wrong range.

**A missing rule is an answer.** Every lookup that cannot find its row produces
a variable with `status != DERIVED` and no `qualified` value at all. There is no
representation of "probably this". `DerivationResult.issuable` stays false while
any variable is underived *or* rests on an unsigned rule row, so an incomplete
derivation cannot be issued by forgetting to check.

The variable list comes from Table QW-353, not from what happens to be
implemented: if the code says a welder requalifies on seven variables, seven
rows appear, and the ones with no encoded rule say so.
"""

from __future__ import annotations

import logging

from knowledge_base.section_ix_loader import (
    RuleNotEncodedError,
    RuleNotFoundError,
    code_edition,
    essential_variables,
    f_number_for_electrode,
    kb_version,
    qualified_backing,
    qualified_f_numbers,
    qualified_p_number,
    qualified_positions,
    qualified_progression,
    qualified_thickness,
    required_tests,
)
from models.derivation import (
    CouponInput,
    DerivationResult,
    DerivationStatus,
    DerivedVariable,
    Provenance,
)

logger = logging.getLogger(__name__)


def _missing(name: str, brief: str, what: str) -> DerivedVariable:
    """A variable whose input was never supplied."""
    return DerivedVariable(
        name=name,
        brief=brief,
        actual=None,
        qualified=None,
        status=DerivationStatus.INPUT_MISSING,
        reason=(
            f"{what} was not read from the source documents, so this range "
            "cannot be derived. It must be supplied before the record is issued."
        ),
    )


def _not_found(name: str, brief: str, actual: str, exc: Exception) -> DerivedVariable:
    """A variable whose rule row does not exist."""
    encoded_gap = isinstance(exc, RuleNotEncodedError)
    return DerivedVariable(
        name=name,
        brief=brief,
        actual=actual,
        qualified=None,
        status=DerivationStatus.RULE_NOT_FOUND
        if encoded_gap
        else DerivationStatus.INPUT_UNRECOGNISED,
        reason=str(exc),
    )


def _derived(
    name: str,
    brief: str,
    actual: str,
    qualified: str,
    reason: str,
    provenance: Provenance,
) -> DerivedVariable:
    return DerivedVariable(
        name=name,
        brief=brief,
        actual=actual,
        qualified=qualified,
        status=DerivationStatus.DERIVED,
        reason=reason,
        provenance=provenance,
    )


def _derive_position(coupon: CouponInput) -> DerivedVariable:
    name, brief = "position", "Position (QW-405.1)"
    if not coupon.test_position:
        return _missing(name, brief, "The test position")
    actual = f"{coupon.test_position} on {coupon.coupon_form.value.replace('_', ' ')}"
    try:
        qualified, prov = qualified_positions(coupon.coupon_form, coupon.test_position)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, actual, exc)
    return _derived(
        name,
        brief,
        actual,
        qualified,
        f"Table QW-461.9 row for {coupon.test_position} on "
        f"{coupon.coupon_form.value.replace('_', ' ')}.",
        prov,
    )


def _derive_thickness(coupon: CouponInput) -> DerivedVariable:
    name, brief = "thickness", "Weld deposit thickness (QW-404.30)"
    if coupon.thickness_mm is None:
        return _missing(name, brief, "The coupon thickness")
    actual = f"{coupon.thickness_mm:g} mm"
    try:
        qualified, prov = qualified_thickness(coupon.thickness_mm, coupon.layers)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, actual, exc)

    if coupon.layers is not None and coupon.layers >= 3:
        reason = (
            f"QW-452.1(b): a coupon of 13 mm or more welded in three or more "
            f"layers qualifies the maximum to be welded. This coupon is "
            f"{coupon.thickness_mm:g} mm in {coupon.layers} layers."
        )
    else:
        reason = (
            f"QW-452.1(b): without the three-layer condition the range is twice "
            f"the coupon thickness."
        )
    return _derived(name, brief, actual, qualified, reason, prov)


def _derive_filler(coupon: CouponInput) -> DerivedVariable:
    name, brief = "f_number", "Filler metal F-number (QW-404.15)"
    if not coupon.electrode_classification:
        return _missing(name, brief, "The electrode classification")
    if coupon.backing is None:
        return _missing(
            name,
            brief,
            "Whether the coupon was welded with backing (QW-433 is indexed by it)",
        )

    try:
        f_number, f_prov = f_number_for_electrode(coupon.electrode_classification)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, coupon.electrode_classification, exc)

    actual = f"F-No. {f_number} ({coupon.electrode_classification})"
    try:
        qualified, prov = qualified_f_numbers(f_number, coupon.backing)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, actual, exc)

    # The answer rests on both rows, so it is only as signed as the weaker one.
    merged = prov.model_copy(
        update={"verified": prov.verified and f_prov.verified}
    )
    return _derived(
        name,
        brief,
        actual,
        qualified,
        f"{coupon.electrode_classification} is F-No. {f_number}. Table QW-433 "
        f"gives the substitutions permitted when qualified "
        f"{coupon.backing.value} backing.",
        merged,
    )


def _derive_backing(coupon: CouponInput) -> DerivedVariable:
    name, brief = "backing", "Backing (QW-402.4)"
    if coupon.backing is None:
        return _missing(name, brief, "Whether the coupon was welded with backing")
    actual = f"Welded {coupon.backing.value} backing"
    try:
        qualified, prov = qualified_backing(coupon.backing)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, actual, exc)
    return _derived(
        name,
        brief,
        actual,
        qualified,
        "QW-402.4: deletion of backing is the essential change, so a coupon "
        "welded without backing qualifies both with and without.",
        prov,
    )


def _derive_progression(coupon: CouponInput) -> DerivedVariable:
    name, brief = "progression", "Vertical progression (QW-405.3)"
    if coupon.progression is None:
        return _missing(name, brief, "The vertical progression")
    actual = coupon.progression.value.capitalize()
    try:
        qualified, prov = qualified_progression(coupon.progression)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, actual, exc)
    return _derived(
        name,
        brief,
        actual,
        qualified,
        "QW-405.3: a change in vertical progression requires requalification.",
        prov,
    )


def _derive_p_number(coupon: CouponInput) -> DerivedVariable:
    name, brief = "p_number", "Base metal P-number (QW-403.18)"
    if not coupon.base_metal_p_number:
        return _missing(name, brief, "The base metal P-number")
    try:
        qualified, prov = qualified_p_number(coupon.base_metal_p_number)
    except RuleNotFoundError as exc:
        return _not_found(name, brief, coupon.base_metal_p_number, exc)
    return _derived(  # pragma: no cover - unreachable until QW-423 is encoded
        name, brief, coupon.base_metal_p_number, qualified, "QW-403.18.", prov
    )


def _derive_pipe_diameter(coupon: CouponInput) -> DerivedVariable:
    """QW-403.16 — pipe diameter.

    A plate coupon has no diameter to qualify, and the diameter limits for pipe
    coupons live in QW-452.3/.4/.6, which are not encoded. Both cases are stated
    rather than silently omitted, because QW-353 lists this as essential and a
    variable missing from the record is indistinguishable from one that passed.
    """
    name, brief = "pipe_diameter", "Pipe diameter (QW-403.16)"
    if coupon.coupon_form.value.startswith("plate"):
        prov = Provenance(
            clause_ref="QW-403.16",
            source_page=126,
            code_edition=code_edition(),
            kb_version=kb_version(),
            verified=False,
        )
        return _derived(
            name,
            brief,
            "Plate coupon",
            "Diameter limits per Table QW-461.9 as stated under position",
            "A plate coupon carries no diameter of its own; the diameters it "
            "qualifies are the ones given in the position row.",
            prov,
        )
    return _not_found(
        name,
        brief,
        f"{coupon.pipe_diameter_mm:g} mm O.D." if coupon.pipe_diameter_mm else "pipe",
        RuleNotEncodedError(
            "Pipe diameter limits (QW-452.3, QW-452.4, QW-452.6) are not "
            "encoded. A pipe coupon's diameter range cannot be derived yet."
        ),
    )


#: Derivation is driven by the essential-variable list, not the other way round.
_DERIVERS = {
    "QW-402.4": _derive_backing,
    "QW-403.16": _derive_pipe_diameter,
    "QW-403.18": _derive_p_number,
    "QW-404.15": _derive_filler,
    "QW-404.30": _derive_thickness,
    "QW-405.1": _derive_position,
    "QW-405.3": _derive_progression,
}


def derive(coupon: CouponInput) -> DerivationResult:
    """Derive the full qualified range for one coupon.

    The variable list is read from Table QW-353 rather than hardcoded here, so
    a variable the code requires and this engine cannot yet compute appears in
    the result as an explicit gap instead of being silently absent.

    Never raises on a rule miss. A missing rule is a result -- that *is* the
    answer, and the caller routes it to REVIEW.
    """
    result = DerivationResult(
        code_edition=code_edition(),
        kb_version=kb_version(),
    )

    try:
        variables = essential_variables(coupon.process)
    except RuleNotEncodedError as exc:
        result.variables.append(
            DerivedVariable(
                name="process",
                brief="Welding process",
                actual=coupon.process,
                qualified=None,
                status=DerivationStatus.RULE_NOT_FOUND,
                reason=str(exc),
            )
        )
        return result

    for variable in variables:
        deriver = _DERIVERS.get(variable["clause_ref"])
        if deriver is None:  # pragma: no cover - guards a rule table edit
            result.variables.append(
                DerivedVariable(
                    name=variable["brief"].lower().replace(" ", "_"),
                    brief=f"{variable['brief']} ({variable['clause_ref']})",
                    status=DerivationStatus.RULE_NOT_FOUND,
                    reason=(
                        f"Table QW-353 lists {variable['clause_ref']} as essential "
                        "but no deriver is implemented for it."
                    ),
                )
            )
            continue
        result.variables.append(deriver(coupon))

    # Which tests the coupon should have had. Compared against the lab report by
    # the Class 2 compliance check; recorded here so the comparison has a
    # reviewed expectation to work from.
    if coupon.thickness_mm is not None:
        try:
            result.test_requirement = required_tests(coupon.thickness_mm)
        except RuleNotFoundError as exc:
            logger.warning("No test requirement band for coupon: %s", exc)

    return result
