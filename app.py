"""Flask routes for the BJT DC bias calculator.

All engineering logic lives in dc_bias.py; this module only parses the form,
formats numbers for display and renders templates.
"""

from __future__ import annotations

from collections.abc import Mapping

from flask import Flask, render_template, request

from dc_bias import (
    REGION_ACTIVE,
    REGION_CUTOFF,
    REGION_SATURATION,
    UNIT_MULTIPLIERS,
    BiasInputs,
    BiasResult,
    ValidationError,
    calculate,
    to_ohms,
)

app = Flask(__name__)

DEFAULT_VALUES = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}

DEFAULT_UNITS = {"r1": "kohm", "r2": "kohm", "rc": "kohm", "re": "kohm"}

UNIT_LABELS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}

RESISTOR_FIELDS = ("r1", "r2", "rc", "re")
VALUE_FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

NOT_A_NUMBER = "กรุณากรอกตัวเลข"
BAD_UNIT = "หน่วยไม่ถูกต้อง"

REGION_LABELS = {
    REGION_ACTIVE: "Active",
    REGION_CUTOFF: "Cutoff",
    REGION_SATURATION: "Saturation",
}

FIELD_LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "β",
    "vbe": "VBE",
    "unit_r1": "หน่วย R1",
    "unit_r2": "หน่วย R2",
    "unit_rc": "หน่วย RC",
    "unit_re": "หน่วย RE",
    "__all__": "ผลการคำนวณ",
}


def parse_inputs(form: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]:
    """Parse and convert the submitted form, returning inputs or field errors."""
    errors: dict[str, str] = {}
    numbers: dict[str, float] = {}

    for name in VALUE_FIELDS:
        raw = (form.get(name) or "").strip()
        try:
            numbers[name] = float(raw)
        except ValueError:
            errors[name] = NOT_A_NUMBER

    units: dict[str, str] = {}
    for name in RESISTOR_FIELDS:
        unit = (form.get(f"unit_{name}") or "").strip()
        if unit not in UNIT_MULTIPLIERS:
            errors[f"unit_{name}"] = BAD_UNIT
        units[name] = unit

    if errors:
        return None, errors

    inputs = BiasInputs(
        vcc=numbers["vcc"],
        r1=to_ohms(numbers["r1"], units["r1"]),
        r2=to_ohms(numbers["r2"], units["r2"]),
        rc=to_ohms(numbers["rc"], units["rc"]),
        re=to_ohms(numbers["re"], units["re"]),
        beta=numbers["beta"],
        vbe=numbers["vbe"],
    )
    return inputs, {}


def form_state(form: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Raw strings to echo back into the form (defaults fill anything missing)."""
    values = dict(DEFAULT_VALUES)
    for name in VALUE_FIELDS:
        raw = form.get(name)
        if raw is not None:
            values[name] = raw

    units = dict(DEFAULT_UNITS)
    for name in RESISTOR_FIELDS:
        raw = form.get(f"unit_{name}")
        if raw is not None:
            units[name] = raw

    return values, units


def format_result(result: BiasResult) -> dict[str, object]:
    """Turn SI values into display strings; the template never formats numbers."""
    return {
        "vb": f"{result.vb:.3f}",
        "ve": f"{result.ve:.3f}",
        "vc": f"{result.vc:.3f}",
        "vce": f"{result.vce:.3f}",
        "vth": f"{result.vth:.3f}",
        "ic_ma": f"{result.ic * 1e3:.3f}",
        "ie_ma": f"{result.ie * 1e3:.3f}",
        "ib_ua": f"{result.ib * 1e6:.2f}",
        "rth_kohm": f"{result.rth / 1e3:.2f}",
        "region": result.region,
        "region_label": REGION_LABELS[result.region],
        "warnings": result.warnings,
    }


@app.get("/")
def index():
    return render_template(
        "index.html",
        values=DEFAULT_VALUES,
        units=DEFAULT_UNITS,
        unit_labels=UNIT_LABELS,
        field_labels=FIELD_LABELS,
        errors={},
        result=None,
    )


@app.post("/calculate")
def calculate_route():
    values, units = form_state(request.form)
    inputs, errors = parse_inputs(request.form)

    result = None
    if inputs is not None:
        try:
            result = format_result(calculate(inputs))
        except ValidationError as exc:
            errors = dict(exc.errors)

    if errors:
        return (
            render_template(
                "index.html",
                values=values,
                units=units,
                unit_labels=UNIT_LABELS,
                field_labels=FIELD_LABELS,
                errors=errors,
                result=None,
            ),
            400,
        )

    return render_template(
        "index.html",
        values=values,
        units=units,
        unit_labels=UNIT_LABELS,
        field_labels=FIELD_LABELS,
        errors={},
        result=result,
    )
