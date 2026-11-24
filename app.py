"""Flask routes for the BJT DC bias calculator.

All engineering logic lives in dc_bias.py; this module only resolves the
selected bias mode, parses the form, formats numbers for display and renders
templates.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from time import perf_counter

from flask import Flask, render_template, request

from charts import bode_magnitude_svg, bode_phase_svg, transient_svg
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
from spice_engine import (
    CeParameters,
    NgspiceNotFound,
    SimulationError,
    find_ngspice,
    ngspice_version,
    run_simulation,
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

SIM_ANALYSES = ("dc", "ac", "tran")

SIM_ANALYSIS_LABELS = {
    "dc": "DC Operating Point (.op)",
    "ac": "AC Frequency Response (.ac)",
    "tran": "Transient Waveform (.tran)",
}

SIM_ANALYSIS_SHORT = {"dc": "DC", "ac": "AC", "tran": "Transient"}

SIM_DEFAULTS = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rl": "10",
    "cin": "10",
    "cout": "10",
    "amplitude": "10",
    "frequency": "1000",
}

SIM_DEFAULT_NUMBERS = {
    "vcc": 12.0,
    "r1": 100.0,
    "r2": 22.0,
    "rc": 2.2,
    "re": 1.0,
    "rl": 10.0,
    "cin": 10.0,
    "cout": 10.0,
    "amplitude": 10.0,
    "frequency": 1000.0,
}

SIM_ALWAYS_FIELDS = ("vcc", "r1", "r2", "rc", "re")
SIM_AC_FIELDS = ("rl", "cin", "cout")
SIM_TRAN_FIELDS = ("amplitude", "frequency")

SIM_FIELD_LABELS = {
    "analysis": "โหมดวิเคราะห์",
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "rl": "RL",
    "cin": "CIN",
    "cout": "COUT",
    "amplitude": "Amplitude",
    "frequency": "Frequency",
    "__all__": "การจำลอง",
}

SIM_FIELD_GROUPS = (
    (
        "bias",
        "DC Bias",
        "ใช้ร่วมกันทุกโหมดวิเคราะห์",
        (
            ("vcc", "VCC", "V", "แรงดันแหล่งจ่าย"),
            ("r1", "R1", "kΩ", "VCC → Base"),
            ("r2", "R2", "kΩ", "Base → Ground"),
            ("rc", "RC", "kΩ", "VCC → Collector"),
            ("re", "RE", "kΩ", "Emitter → Ground (ไม่มี CE)"),
        ),
    ),
    (
        "load",
        "Load & Coupling",
        "ใช้ใน AC และ Transient (DC ไม่ใช้)",
        (
            ("rl", "RL", "kΩ", "โหลดที่ต่อจาก COUT"),
            ("cin", "CIN", "µF", "Input coupling"),
            ("cout", "COUT", "µF", "Output coupling"),
        ),
    ),
    (
        "source",
        "Source",
        "ใช้ใน Transient เท่านั้น",
        (
            ("amplitude", "Amplitude", "mV peak", "SIN amplitude"),
            ("frequency", "Frequency", "Hz", "SIN frequency (10 Hz – 20 kHz)"),
        ),
    ),
)


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


def _sim_number(
    form: Mapping[str, str], name: str, errors: dict[str, str], *, required: bool
) -> float | None:
    """Read one display-unit number; optional fields fall back to defaults."""
    raw = (form.get(name) or "").strip()
    if not raw:
        if required:
            errors[name] = "กรุณากรอกตัวเลข"
            return None
        return SIM_DEFAULT_NUMBERS[name]
    try:
        value = float(raw)
    except ValueError:
        errors[name] = "กรุณากรอกตัวเลข"
        return None
    if not math.isfinite(value):
        errors[name] = "ค่าต้องเป็นจำนวนจำกัด"
        return None
    return value


def parse_sim_inputs(
    form: Mapping[str, str],
) -> tuple[CeParameters | None, str, dict[str, str]]:
    """Validate the CE form and convert display units to SI for the netlist."""
    errors: dict[str, str] = {}
    raw_analysis = (form.get("analysis") or "dc").strip()
    if raw_analysis not in SIM_ANALYSES:
        errors["analysis"] = "โหมดวิเคราะห์ไม่ถูกต้อง"
        analysis = "dc"
    else:
        analysis = raw_analysis

    required = set(SIM_ALWAYS_FIELDS)
    if analysis in ("ac", "tran"):
        required.update(SIM_AC_FIELDS)
    if analysis == "tran":
        required.update(SIM_TRAN_FIELDS)

    # Hidden/unused fields must not be validated: use their defaults instead.
    # This keeps analysis-aware validation honest when switching DC -> AC -> Tran.
    display: dict[str, float | None] = {}
    for name in (*SIM_ALWAYS_FIELDS, *SIM_AC_FIELDS, *SIM_TRAN_FIELDS):
        if name in required:
            display[name] = _sim_number(form, name, errors, required=True)
        else:
            display[name] = SIM_DEFAULT_NUMBERS[name]

    multipliers = {
        "vcc": 1.0,
        "r1": 1e3,
        "r2": 1e3,
        "rc": 1e3,
        "re": 1e3,
        "rl": 1e3,
        "cin": 1e-6,
        "cout": 1e-6,
        "amplitude": 1e-3,
        "frequency": 1.0,
    }
    numbers: dict[str, float] = {}
    for name, value in display.items():
        if value is None:
            continue
        numbers[name] = value * multipliers[name]

    for name, value in numbers.items():
        if name in errors:
            continue
        if not math.isfinite(value) or value <= 0:
            errors[name] = "ค่าต้องมากกว่า 0"

    if analysis == "tran":
        frequency = numbers.get("frequency")
        if "frequency" not in errors and frequency is not None:
            if not 10.0 <= frequency <= 20_000.0:
                errors["frequency"] = "ความถี่ต้องอยู่ระหว่าง 10 Hz ถึง 20 kHz"
        amplitude = numbers.get("amplitude")
        if "amplitude" not in errors and amplitude is not None and amplitude > 0.5:
            errors["amplitude"] = "แอมพลิจูดต้องไม่เกิน 500 mV peak"

    if errors:
        return None, analysis, errors

    params = CeParameters(
        vcc=numbers["vcc"],
        r1=numbers["r1"],
        r2=numbers["r2"],
        rc=numbers["rc"],
        re=numbers["re"],
        rl=numbers["rl"],
        cin=numbers["cin"],
        cout=numbers["cout"],
        source_amplitude=numbers["amplitude"],
        frequency=numbers["frequency"],
    )
    try:
        params.validate()
    except ValueError as exc:
        errors["__all__"] = f"ค่าอุปกรณ์ไม่ถูกต้อง: {exc}"
        return None, analysis, errors
    return params, analysis, errors


def sim_form_state(form: Mapping[str, str]) -> tuple[dict[str, str], str]:
    """Echo submitted strings into the simulator form."""
    values = dict(SIM_DEFAULTS)
    for name in SIM_DEFAULTS:
        raw = form.get(name)
        if raw is not None:
            values[name] = raw
    raw_analysis = (form.get("analysis") or "dc").strip()
    analysis = raw_analysis if raw_analysis in SIM_ANALYSES else "dc"
    return values, analysis


def _format_freq(value: float | None) -> str:
    if value is None:
        return "—"
    for scale, suffix in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if value >= scale:
            return f"{value / scale:.3g} {suffix}"
    return f"{value:.3g} Hz"


def _signed(value: float, unit: str, digits: int = 3) -> str:
    return f"{value:+.{digits}f}".replace("-", "−") + f" {unit}"


def _percent(delta: float, reference: float) -> str:
    if abs(reference) < 1e-15:
        return "—"
    return f"{delta / reference * 100:+.1f}%".replace("-", "−")


def _spice_region(dc) -> str:
    if dc.ic <= 1e-9:
        return REGION_CUTOFF
    if dc.vce <= 0.2:
        return REGION_SATURATION
    return REGION_ACTIVE


def _comparison_rows(spice, analytical) -> list[dict[str, str]]:
    if analytical is None:
        return []
    specs = (
        ("VB", spice.vb, analytical.vb, "V", 3),
        ("VE", spice.ve, analytical.ve, "V", 3),
        ("VC", spice.vc, analytical.vc, "V", 3),
        ("VCE", spice.vce, analytical.vce, "V", 3),
        ("IC", spice.ic * 1e3, analytical.ic * 1e3, "mA", 3),
        ("IB", spice.ib * 1e6, analytical.ib * 1e6, "µA", 2),
        ("IE", spice.ie * 1e3, analytical.ie * 1e3, "mA", 3),
    )
    rows: list[dict[str, str]] = []
    for label, spice_value, reference, unit, digits in specs:
        delta = spice_value - reference
        rows.append(
            {
                "label": label,
                "spice": f"{spice_value:.{digits}f} {unit}",
                "analytical": f"{reference:.{digits}f} {unit}",
                "delta": _signed(delta, unit, digits),
                "delta_pct": _percent(delta, reference),
            }
        )
    return rows


def format_sim_result(result, params: CeParameters, analysis: str, elapsed_ms: float):
    """Format real ngspice results plus the independent Lab 03 reference."""
    dc = result.dc
    analytical = None
    try:
        analytical = calculate_divider(
            BiasInputs(
                vcc=params.vcc,
                r1=params.r1,
                r2=params.r2,
                rc=params.rc,
                re=params.re,
                beta=100.0,
                vbe=0.70,
            )
        )
    except ValidationError:
        analytical = None

    region = _spice_region(dc)
    dc_view = {
        "vb": f"{dc.vb:.3f}",
        "ve": f"{dc.ve:.3f}",
        "vc": f"{dc.vc:.3f}",
        "vce": f"{dc.vce:.3f}",
        "ic_ma": f"{dc.ic * 1e3:.3f}",
        "ib_ua": f"{dc.ib * 1e6:.2f}",
        "ie_ma": f"{dc.ie * 1e3:.3f}",
        "region": region,
        "region_label": REGION_LABELS[region],
    }

    ac_view = None
    if result.ac is not None:
        ac = result.ac
        ac_view = {
            "midband_gain": f"{ac.midband.magnitude:.3f}",
            "midband_db": f"{ac.midband.gain_db:.2f}",
            "midband_freq": _format_freq(ac.midband.frequency_hz),
            "gain_1k": f"{ac.gain_1k.magnitude:.3f}",
            "gain_1k_db": f"{ac.gain_1k.gain_db:.2f}",
            "phase_1k": f"{ac.gain_1k.phase_deg:.1f}".replace("-", "−") + "°",
            "inverting": abs(ac.gain_1k.phase_deg) > 90.0,
            "low_cutoff": (
                _format_freq(ac.low_cutoff_hz)
                if ac.low_cutoff_hz is not None
                else "ไม่พบในช่วง sweep"
            ),
            "high_cutoff": (
                _format_freq(ac.high_cutoff_hz)
                if ac.high_cutoff_hz is not None
                else "ไม่พบในช่วง sweep"
            ),
            "sweep": f"{_format_freq(ac.sweep_min_hz)} – {_format_freq(ac.sweep_max_hz)}",
            "points": len(ac.points),
            "magnitude_chart": bode_magnitude_svg(ac),
            "phase_chart": bode_phase_svg(ac),
        }

    tran_view = None
    if result.tran is not None:
        tran = result.tran
        tran_view = {
            "vin_amp_mv": f"{tran.vin_amplitude_v * 1e3:.2f}",
            "vout_amp_mv": f"{tran.vout_amplitude_v * 1e3:.2f}",
            "gain": f"{tran.gain:.3f}",
            "correlation": f"{tran.correlation:.4f}".replace("-", "−"),
            "inverted": tran.inverted,
            "phase_text": "กลับเฟส 180°" if tran.inverted else "ไม่กลับเฟส",
            "window": (
                f"{tran.window_start_s * 1e3:.2f} – "
                f"{tran.window_end_s * 1e3:.2f} ms"
            ),
            "points": len(tran.time_s),
            "chart": transient_svg(tran),
        }

    return {
        "analysis": analysis,
        "analysis_label": SIM_ANALYSIS_LABELS[analysis],
        "analysis_short": SIM_ANALYSIS_SHORT[analysis],
        "engine": result.engine,
        "model": result.model,
        "run_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "elapsed_ms": f"{elapsed_ms:.0f}",
        "netlist": result.netlist,
        "log": result.log,
        "warnings": result.warnings,
        "dc": dc_view,
        "comparison": _comparison_rows(dc, analytical),
        "analytical_available": analytical is not None,
        "analytical_note": (
            "Analytical reference จาก dc_bias.py (β=100, VBE=0.70 V, "
            "Forward-Active approximation) — ไม่ใช่ผล ngspice"
        ),
        "ac": ac_view,
        "tran": tran_view,
    }


def render_simulator(
    *,
    values=None,
    analysis="dc",
    errors=None,
    result=None,
    error_message=None,
    error_kind=None,
    engine_available=None,
    engine_name=None,
    status=200,
):
    if engine_available is None:
        executable = find_ngspice()
        engine_available = executable is not None
        engine_name = ngspice_version(executable) if executable else None

    return (
        render_template(
            "simulator.html",
            values=values or dict(SIM_DEFAULTS),
            analysis=analysis,
            analysis_options=[
                (name, SIM_ANALYSIS_LABELS[name], SIM_ANALYSIS_SHORT[name])
                for name in SIM_ANALYSES
            ],
            analysis_label=SIM_ANALYSIS_LABELS.get(analysis, SIM_ANALYSIS_LABELS["dc"]),
            analysis_short=SIM_ANALYSIS_SHORT.get(analysis, "DC"),
            field_groups=SIM_FIELD_GROUPS,
            field_labels=SIM_FIELD_LABELS,
            errors=errors or {},
            result=result,
            error_message=error_message,
            error_kind=error_kind,
            engine_available=engine_available,
            engine_name=engine_name,
        ),
        status,
    )


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


@app.get("/simulator")
def simulator_page():
    executable = find_ngspice()
    return render_simulator(
        values=dict(SIM_DEFAULTS),
        analysis="dc",
        engine_available=executable is not None,
        engine_name=ngspice_version(executable) if executable else None,
    )


@app.post("/simulate")
def simulate_route():
    values, analysis = sim_form_state(request.form)
    params, analysis, errors = parse_sim_inputs(request.form)

    executable = find_ngspice()
    engine_available = executable is not None
    engine_name = ngspice_version(executable) if executable else None

    if errors:
        return render_simulator(
            values=values,
            analysis=analysis,
            errors=errors,
            engine_available=engine_available,
            engine_name=engine_name,
            status=400,
        )

    started = perf_counter()
    try:
        result = run_simulation(params, analysis)
    except NgspiceNotFound as exc:
        return render_simulator(
            values=values,
            analysis=analysis,
            error_message=str(exc),
            error_kind="engine",
            engine_available=False,
            engine_name=None,
            status=503,
        )
    except SimulationError as exc:
        return render_simulator(
            values=values,
            analysis=analysis,
            error_message=str(exc),
            error_kind="simulation",
            engine_available=engine_available,
            engine_name=engine_name,
            status=502,
        )
    except Exception as exc:  # pragma: no cover - last-resort safety net
        app.logger.exception("Unexpected simulator failure")
        return render_simulator(
            values=values,
            analysis=analysis,
            error_message=f"เกิดข้อผิดพลาดภายในระหว่างเรียก ngspice: {exc}",
            error_kind="internal",
            engine_available=engine_available,
            engine_name=engine_name,
            status=500,
        )

    elapsed_ms = (perf_counter() - started) * 1000.0
    return render_simulator(
        values=values,
        analysis=analysis,
        result=format_sim_result(result, params, analysis, elapsed_ms),
        engine_available=engine_available,
        engine_name=engine_name,
    )
