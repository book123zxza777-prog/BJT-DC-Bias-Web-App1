"""Flask routes for the BJT DC bias calculator.

All engineering logic lives in dc_bias.py; this module only resolves the
selected bias mode, parses the form, formats numbers for display and renders
templates.
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
    EmitterBiasInputs,
    FixedBiasInputs,
    ValidationError,
    calculate_divider,
    calculate_emitter,
    calculate_fixed,
    to_ohms,
)

app = Flask(__name__)

MODES = ("divider", "fixed", "emitter")

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

MODE_RESISTORS = {
    "divider": ("r1", "r2", "rc", "re"),
    "fixed": ("rb", "rc"),
    "emitter": ("rb", "rc", "re"),
}

DEFAULT_VALUES_BY_MODE = {
    "divider": {
        "vcc": "12",
        "r1": "100",
        "r2": "22",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.70",
    },
    "fixed": {"vcc": "12", "rb": "1000", "rc": "2.2", "beta": "100", "vbe": "0.70"},
    "emitter": {
        "vcc": "12",
        "rb": "1000",
        "rc": "2.2",
        "re": "1",
        "beta": "100",
        "vbe": "0.70",
    },
}

DEFAULT_UNITS_BY_MODE = {
    "divider": {"r1": "kohm", "r2": "kohm", "rc": "kohm", "re": "kohm"},
    "fixed": {"rb": "kohm", "rc": "kohm"},
    "emitter": {"rb": "kohm", "rc": "kohm", "re": "kohm"},
}

UNIT_LABELS = {"ohm": "Ω", "kohm": "kΩ", "mohm": "MΩ"}

NOT_A_NUMBER = "กรุณากรอกตัวเลข"
BAD_UNIT = "หน่วยไม่ถูกต้อง"
BAD_MODE = "โหมดไม่ถูกต้อง กรุณาเลือกโหมดจากรายการ"

REGION_LABELS = {
    REGION_ACTIVE: "Active",
    REGION_CUTOFF: "Cutoff",
    REGION_SATURATION: "Saturation",
}

FIELD_LABELS = {
    "mode": "โหมด",
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "rb": "RB",
    "beta": "β",
    "vbe": "VBE",
    "unit_r1": "หน่วย R1",
    "unit_r2": "หน่วย R2",
    "unit_rc": "หน่วย RC",
    "unit_re": "หน่วย RE",
    "unit_rb": "หน่วย RB",
    "__all__": "ผลการคำนวณ",
}


def mode_from(source: Mapping[str, str]) -> str:
    """Resolve the selected mode.

    A missing ``mode`` key means the legacy Lab 2 divider form, so it keeps
    working.  An empty or unknown value is an error instead of a guess.
    """
    if "mode" not in source:
        return "divider"

    mode = (source.get("mode") or "").strip()
    if mode not in MODE_RESISTORS:
        raise ValidationError({"mode": BAD_MODE})
    return mode


def value_fields(mode: str) -> tuple[str, ...]:
    """Numeric fields used by ``mode``."""
    return ("vcc", *MODE_RESISTORS[mode], "beta", "vbe")


def parse_inputs(
    form: Mapping[str, str], mode: str = "divider"
) -> tuple[object | None, dict[str, str]]:
    """Parse and convert the submitted form, returning inputs or field errors."""
    errors: dict[str, str] = {}
    numbers: dict[str, float] = {}

    for name in value_fields(mode):
        raw = (form.get(name) or "").strip()
        try:
            numbers[name] = float(raw)
        except ValueError:
            errors[name] = NOT_A_NUMBER

    units: dict[str, str] = {}
    for name in MODE_RESISTORS[mode]:
        unit = (form.get(f"unit_{name}") or "").strip()
        if unit not in UNIT_MULTIPLIERS:
            errors[f"unit_{name}"] = BAD_UNIT
        units[name] = unit

    if errors:
        return None, errors

    if mode == "fixed":
        return (
            FixedBiasInputs(
                vcc=numbers["vcc"],
                rb=to_ohms(numbers["rb"], units["rb"]),
                rc=to_ohms(numbers["rc"], units["rc"]),
                beta=numbers["beta"],
                vbe=numbers["vbe"],
            ),
            {},
        )

    if mode == "emitter":
        return (
            EmitterBiasInputs(
                vcc=numbers["vcc"],
                rb=to_ohms(numbers["rb"], units["rb"]),
                rc=to_ohms(numbers["rc"], units["rc"]),
                re=to_ohms(numbers["re"], units["re"]),
                beta=numbers["beta"],
                vbe=numbers["vbe"],
            ),
            {},
        )

    return (
        BiasInputs(
            vcc=numbers["vcc"],
            r1=to_ohms(numbers["r1"], units["r1"]),
            r2=to_ohms(numbers["r2"], units["r2"]),
            rc=to_ohms(numbers["rc"], units["rc"]),
            re=to_ohms(numbers["re"], units["re"]),
            beta=numbers["beta"],
            vbe=numbers["vbe"],
        ),
        {},
    )


def form_state(
    form: Mapping[str, str], mode: str = "divider"
) -> tuple[dict[str, str], dict[str, str]]:
    """Raw strings to echo back into the form (defaults fill anything missing)."""
    values = dict(DEFAULT_VALUES_BY_MODE[mode])
    for name in value_fields(mode):
        raw = form.get(name)
        if raw is not None:
            values[name] = raw

    units = dict(DEFAULT_UNITS_BY_MODE[mode])
    for name in MODE_RESISTORS[mode]:
        raw = form.get(f"unit_{name}")
        if raw is not None:
            units[name] = raw

    return values, units


def format_result(result: BiasResult, mode: str = "divider") -> dict[str, object]:
    """Turn SI values into display strings; the template never formats numbers."""
    return {
        "mode": mode,
        "mode_label": MODE_LABELS[mode],
        "vb": f"{result.vb:.3f}",
        "ve": f"{result.ve:.3f}",
        "vc": f"{result.vc:.3f}",
        "vce": f"{result.vce:.3f}",
        "vth": None if result.vth is None else f"{result.vth:.3f}",
        "ic_ma": f"{result.ic * 1e3:.3f}",
        "ie_ma": f"{result.ie * 1e3:.3f}",
        "ib_ua": f"{result.ib * 1e6:.2f}",
        "rth_kohm": None if result.rth is None else f"{result.rth / 1e3:.2f}",
        "region": result.region,
        "region_label": REGION_LABELS[result.region],
        "warnings": result.warnings,
    }


def render_index(mode: str, values, units, errors, result=None, status=200):
    return (
        render_template(
            "index.html",
            mode=mode,
            mode_label=MODE_LABELS[mode],
            mode_options=[(name, MODE_LABELS[name]) for name in MODES],
            resistors=MODE_RESISTORS[mode],
            values=values,
            units=units,
            unit_labels=UNIT_LABELS,
            field_labels=FIELD_LABELS,
            errors=errors,
            result=result,
        ),
        status,
    )


def render_mode_error(submitted_mode: str):
    return (
        render_template(
            "mode_error.html",
            submitted_mode=submitted_mode,
            message=BAD_MODE,
        ),
        400,
    )


@app.get("/")
def index():
    try:
        mode = mode_from(request.args)
    except ValidationError:
        return render_mode_error((request.args.get("mode") or "").strip())

    values, units = form_state(request.args, mode)
    return render_index(mode, values, units, {})


@app.post("/calculate")
def calculate_route():
    try:
        mode = mode_from(request.form)
    except ValidationError:
        return render_mode_error((request.form.get("mode") or "").strip())

    values, units = form_state(request.form, mode)
    inputs, errors = parse_inputs(request.form, mode)

    result = None
    if inputs is not None:
        try:
            if mode == "fixed":
                result = format_result(calculate_fixed(inputs), mode)
            elif mode == "emitter":
                result = format_result(calculate_emitter(inputs), mode)
            else:
                result = format_result(calculate_divider(inputs), mode)
        except ValidationError as exc:
            errors = dict(exc.errors)

    if errors:
        return render_index(mode, values, units, errors, status=400)

    return render_index(mode, values, units, {}, result=result)
