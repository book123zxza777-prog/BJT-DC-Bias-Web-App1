"""Engineering calculations for the BJT voltage-divider DC bias lab.

This module knows nothing about HTTP, HTML or Flask: it takes SI values and
returns the DC operating point.  Model: forward-active approximation with
constant beta and constant VBE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

VCE_SAT_V = 0.3

REGION_ACTIVE = "active"
REGION_CUTOFF = "cutoff"
REGION_SATURATION = "saturation"

UNIT_MULTIPLIERS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

_NON_FINITE_MESSAGE = "กรุณากรอกตัวเลขที่มีขอบเขตจำกัด"


@dataclass(frozen=True)
class BiasInputs:
    """Circuit values already converted to SI units (V and ohm)."""

    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


class ValidationError(ValueError):
    """Raised when circuit values are physically meaningless."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = dict(errors)
        super().__init__("; ".join(f"{key}: {msg}" for key, msg in self.errors.items()))


def to_ohms(value: float, unit: str) -> float:
    """Convert a resistance value expressed in ``unit`` to ohms."""
    try:
        multiplier = UNIT_MULTIPLIERS[unit]
    except KeyError:
        raise ValueError(f"unknown unit: {unit!r}") from None
    return value * multiplier


def validate_inputs(inputs: BiasInputs) -> None:
    """Check that every input is finite and physically sensible."""
    errors: dict[str, str] = {}

    fields = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
    for name in fields:
        if not math.isfinite(getattr(inputs, name)):
            errors[name] = _NON_FINITE_MESSAGE

    if "vcc" not in errors and inputs.vcc <= 0:
        errors["vcc"] = "VCC ต้องมากกว่า 0 V"

    for name in ("r1", "r2", "rc", "re"):
        if name not in errors and getattr(inputs, name) <= 0:
            errors[name] = "ค่าความต้านทานต้องมากกว่า 0 Ω"

    if "beta" not in errors and inputs.beta <= 0:
        errors["beta"] = "β ต้องมากกว่า 0"

    if "vbe" not in errors and not (0 < inputs.vbe < inputs.vcc):
        errors["vbe"] = "VBE ต้องอยู่ระหว่าง 0 ถึง VCC"

    if errors:
        raise ValidationError(errors)
