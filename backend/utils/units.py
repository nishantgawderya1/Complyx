"""Unit normalisation.

Material test certificates state the same property in whatever unit the issuing
mill prefers: MPa, N/mm², ksi, psi, kgf/mm². The knowledge base stores one
canonical unit per dimension, so every extracted value is converted before it
is compared.

Conversion is a lookup table and a multiplication. It is deliberately kept out
of the LLM -- the extraction prompt reports units exactly as printed and this
module does the arithmetic, because a fixed conversion factor is not something
a language model should be asked to recall.

Canonical units: stress -> MPa, ratio -> %, length -> mm.
"""

from __future__ import annotations

# Stress-like units, expressed as multipliers to MPa.
_STRESS_TO_MPA: dict[str, float] = {
    "mpa": 1.0,
    "n/mm2": 1.0,  # numerically identical to MPa
    "nmm2": 1.0,
    "n/mm^2": 1.0,
    "gpa": 1000.0,
    "kpa": 0.001,
    "pa": 1e-6,
    "ksi": 6.894757293168361,
    "psi": 0.006894757293168361,
    "kgf/mm2": 9.80665,
    "kg/mm2": 9.80665,
    "kgf/cm2": 0.0980665,
    "kg/cm2": 0.0980665,
}

# Ratio units, expressed as multipliers to percent.
_RATIO_TO_PERCENT: dict[str, float] = {
    "%": 1.0,
    "pct": 1.0,
    "percent": 1.0,
    "ppm": 1e-4,
}

# Length units, expressed as multipliers to millimetres.
_LENGTH_TO_MM: dict[str, float] = {
    "mm": 1.0,
    "cm": 10.0,
    "m": 1000.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
    '"': 25.4,
    "ft": 304.8,
}


class UnknownUnitError(ValueError):
    """Raised when a unit string is not recognised.

    Never swallowed into a default. An unrecognised unit means the value cannot
    be compared safely, and the caller must route the field to REVIEW.
    """


def normalise_unit(unit: str | None) -> str:
    """Reduce a printed unit string to a lookup key.

    Handles the superscript and spacing variants that appear on real
    certificates: "N/mm²", "N / mm2", "MPA", "Ksi".
    """
    if unit is None:
        return ""

    cleaned = unit.strip().lower()
    cleaned = cleaned.replace("²", "2").replace("³", "3")
    cleaned = cleaned.replace(" ", "").replace("·", "").replace("*", "")
    return cleaned


def is_stress_unit(unit: str | None) -> bool:
    """True when the unit denotes a stress, e.g. a strength value."""
    return normalise_unit(unit) in _STRESS_TO_MPA


def is_ratio_unit(unit: str | None) -> bool:
    """True when the unit denotes a ratio, e.g. elongation or a chemistry percentage."""
    return normalise_unit(unit) in _RATIO_TO_PERCENT


def is_length_unit(unit: str | None) -> bool:
    """True when the unit denotes a length, e.g. a thickness."""
    return normalise_unit(unit) in _LENGTH_TO_MM


def to_mpa(value: float, unit: str | None) -> float:
    """Convert a stress value to MPa.

    Raises:
        UnknownUnitError: The unit is not a recognised stress unit.
    """
    key = normalise_unit(unit)
    if key not in _STRESS_TO_MPA:
        raise UnknownUnitError(f"Unrecognised stress unit: {unit!r}")
    return value * _STRESS_TO_MPA[key]


def to_percent(value: float, unit: str | None) -> float:
    """Convert a ratio value to percent.

    An absent unit is treated as percent: chemistry tables on real certificates
    routinely print bare numbers under a "%" column header.
    """
    key = normalise_unit(unit)
    if not key:
        return value
    if key not in _RATIO_TO_PERCENT:
        raise UnknownUnitError(f"Unrecognised ratio unit: {unit!r}")
    return value * _RATIO_TO_PERCENT[key]


def to_mm(value: float, unit: str | None) -> float:
    """Convert a length value to millimetres.

    Raises:
        UnknownUnitError: The unit is not a recognised length unit.
    """
    key = normalise_unit(unit)
    if key not in _LENGTH_TO_MM:
        raise UnknownUnitError(f"Unrecognised length unit: {unit!r}")
    return value * _LENGTH_TO_MM[key]
