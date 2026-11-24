"""Small server-side SVG chart builders for real ngspice data.

The browser only receives already-parsed numeric arrays; no physics is
recomputed in JavaScript.  Charts are plain SVG so the app stays dependency
free and the same markup can be screenshotted by browser acceptance tools.
"""

from __future__ import annotations

import math
from html import escape

from spice_engine import AcResult, TransientResult

WIDTH = 760
HEIGHT = 330
LEFT = 76
RIGHT = 20
TOP = 48
BOTTOM = 50
PLOT_W = WIDTH - LEFT - RIGHT
PLOT_H = HEIGHT - TOP - BOTTOM

INK = "#17344b"
MUTED = "#546d83"
GRID = "#dbe6ef"
AXIS = "#8aa4b8"
TEAL = "#0f766e"
ORANGE = "#b45309"
BLUE = "#1d638b"


def _nice_step(span: float, target: int = 5) -> float:
    if span <= 0 or not math.isfinite(span):
        return 1.0
    raw = span / max(target, 1)
    magnitude = 10.0 ** math.floor(math.log10(raw))
    for multiplier in (1.0, 2.0, 2.5, 5.0, 10.0):
        step = multiplier * magnitude
        if step >= raw:
            return step
    return 10.0 * magnitude


def _ticks(low: float, high: float, target: int = 5) -> list[float]:
    if high <= low:
        high = low + 1.0
    step = _nice_step(high - low, target)
    start = math.floor(low / step) * step
    end = math.ceil(high / step) * step
    values: list[float] = []
    value = start
    while value <= end + step * 1e-9:
        values.append(round(value, 10))
        value += step
    return values


def _fmt(value: float, digits: int = 1) -> str:
    if value == 0:
        return "0"
    if abs(value) >= 1000:
        return f"{value:,.0f}"
    if digits == 0:
        return f"{value:.0f}"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def _freq_short(value: float) -> str:
    for scale, suffix in ((1e9, "G"), (1e6, "M"), (1e3, "k")):
        if value >= scale:
            return f"{value / scale:g}{suffix}"
    return f"{value:g}"


def _freq_long(value: float) -> str:
    if value is None:
        return "—"
    for scale, suffix in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if value >= scale:
            return f"{value / scale:.3g} {suffix}"
    return f"{value:.3g} Hz"


def _x_log(value: float, low: float, high: float) -> float:
    return LEFT + (math.log10(value) - math.log10(low)) / (
        math.log10(high) - math.log10(low)
    ) * PLOT_W


def _y(value: float, low: float, high: float) -> float:
    if high <= low:
        return TOP + PLOT_H / 2
    return TOP + (high - value) / (high - low) * PLOT_H


def _polyline(points: list[tuple[float, float]], color: str, width: float = 2.2) -> str:
    if not points:
        return ""
    path = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f'<polyline points="{path}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>'
    )


def _open_svg(title: str, desc: str) -> list[str]:
    return [
        f'<svg class="chart-svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        'xmlns="http://www.w3.org/2000/svg" role="img" '
        'preserveAspectRatio="xMidYMid meet">',
        f"<title>{escape(title)}</title>",
        f"<desc>{escape(desc)}</desc>",
        f'<rect x="0" y="0" width="{WIDTH}" height="{HEIGHT}" fill="#ffffff"/>',
    ]


def _axis_text(x: float, y: float, text: str, *, anchor: str = "middle",
               size: int = 11, color: str = MUTED, weight: str = "normal",
               rotate: float | None = None) -> str:
    transform = (
        f' transform="rotate({rotate} {x:.1f} {y:.1f})"'
        if rotate is not None
        else ""
    )
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{transform} '
        f'font-family="Tahoma, Arial, sans-serif" font-size="{size}" '
        f'fill="{color}" font-weight="{weight}">{escape(text)}</text>'
    )


def _grid_x(ticks: list[float], low: float, high: float) -> list[str]:
    parts = []
    for value in ticks:
        x = _x_log(value, low, high)
        parts.append(
            f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + PLOT_H}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
    return parts


def _grid_y(ticks: list[float], low: float, high: float) -> list[str]:
    parts = []
    for value in ticks:
        y = _y(value, low, high)
        parts.append(
            f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + PLOT_W}" y2="{y:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
    return parts


def _axes(x_label: str, y_label: str) -> list[str]:
    return [
        f'<line x1="{LEFT}" y1="{TOP + PLOT_H}" x2="{LEFT + PLOT_W}" '
        f'y2="{TOP + PLOT_H}" stroke="{AXIS}" stroke-width="1.2"/>',
        f'<line x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{TOP + PLOT_H}" '
        f'stroke="{AXIS}" stroke-width="1.2"/>',
        _axis_text(LEFT + PLOT_W / 2, HEIGHT - 12, x_label, size=12, color=INK),
        _axis_text(18, TOP + PLOT_H / 2, y_label, anchor="middle", size=12,
                   color=INK, rotate=-90),
    ]


def _title(text: str, subtitle: str | None = None) -> list[str]:
    parts = [_axis_text(LEFT, 24, text, anchor="start", size=15, color=INK,
                        weight="bold")]
    if subtitle:
        parts.append(_axis_text(LEFT, 41, subtitle, anchor="start", size=11))
    return parts


def _decade_ticks(low: float, high: float) -> list[float]:
    start = math.ceil(math.log10(low))
    end = math.floor(math.log10(high))
    values = [10.0 ** exponent for exponent in range(start, end + 1)]
    if len(values) > 12:
        values = values[::2]
    return values


def _legend(x: float, y: float, items: list[tuple[str, str]]) -> list[str]:
    parts = []
    cursor = x
    for label, color in items:
        parts.append(
            f'<line x1="{cursor:.1f}" y1="{y}" x2="{cursor + 20:.1f}" y2="{y}" '
            f'stroke="{color}" stroke-width="2.6"/>'
        )
        parts.append(_axis_text(cursor + 26, y + 4, label, anchor="start",
                                size=11, color=INK))
        cursor += 34 + 7.0 * len(label)
    return parts


def bode_magnitude_svg(ac: AcResult) -> str:
    """Bode magnitude chart from parsed ngspice AC points."""
    low, high = ac.sweep_min_hz, ac.sweep_max_hz
    values = [point.gain_db for point in ac.points]
    data_low, data_high = min(values), max(values)
    pad = max(3.0, (data_high - data_low) * 0.15)
    y_low = math.floor((data_low - pad) / 5.0) * 5.0
    y_high = math.ceil((data_high + pad) / 5.0) * 5.0
    if y_high - y_low < 10.0:
        y_low -= 5.0
        y_high += 5.0
    y_ticks = _ticks(y_low, y_high, 6)
    y_low, y_high = min(y_ticks), max(y_ticks)
    x_ticks = _decade_ticks(low, high)

    parts = _open_svg(
        "Bode magnitude จาก ngspice",
        "กราฟขนาดอัตราขยาย Vout/Vin เทียบความถี่ ข้อมูลจากการรัน ngspice .ac จริง",
    )
    parts += _title("Bode Magnitude · |Vout / Vin|",
                    "ข้อมูลจริงจาก ngspice .ac · แกนความถี่แบบลอการิทึม")
    parts += _grid_x(x_ticks, low, high)
    parts += _grid_y(y_ticks, y_low, y_high)
    parts += _axes("Frequency (Hz)", "Gain (dB)")

    for value in x_ticks:
        x = _x_log(value, low, high)
        parts.append(_axis_text(x, TOP + PLOT_H + 18, _freq_short(value)))
    for value in y_ticks:
        y = _y(value, y_low, y_high)
        parts.append(_axis_text(LEFT - 10, y + 4, _fmt(value, 1), anchor="end"))

    # -3 dB line relative to the measured midband gain.
    mid_db = ac.midband.gain_db
    minus3 = mid_db - 3.0103
    if y_low <= minus3 <= y_high:
        y = _y(minus3, y_low, y_high)
        parts.append(
            f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + PLOT_W}" y2="{y:.1f}" '
            f'stroke="{ORANGE}" stroke-width="1.2" stroke-dasharray="5 4"/>'
        )
        parts.append(_axis_text(LEFT + PLOT_W - 4, y - 5, "−3 dB", anchor="end",
                                size=10, color=ORANGE))

    if low <= 1e3 <= high:
        x = _x_log(1e3, low, high)
        parts.append(
            f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + PLOT_H}" '
            f'stroke="{BLUE}" stroke-width="1" stroke-dasharray="3 4"/>'
        )
        parts.append(_axis_text(x + 4, TOP + 12, "1 kHz", anchor="start",
                                size=10, color=BLUE))

    points = [
        (_x_log(point.frequency_hz, low, high), _y(point.gain_db, y_low, y_high))
        for point in ac.points
    ]
    parts.append(_polyline(points, BLUE))
    parts += _legend(LEFT + 4, TOP + PLOT_H - 10, [("ngspice .ac", BLUE)])
    parts.append("</svg>")
    return "\n".join(parts)


def bode_phase_svg(ac: AcResult) -> str:
    """Bode phase chart from parsed ngspice AC points."""
    low, high = ac.sweep_min_hz, ac.sweep_max_hz
    values = [point.phase_deg for point in ac.points]
    data_low, data_high = min(values), max(values)
    step = 45.0 if data_high - data_low <= 270.0 else 90.0
    y_low = math.floor(data_low / step) * step
    y_high = math.ceil(data_high / step) * step
    if y_high - y_low < step * 2:
        y_low -= step
        y_high += step
    y_ticks = []
    value = y_low
    while value <= y_high + step * 1e-9:
        y_ticks.append(value)
        value += step
    x_ticks = _decade_ticks(low, high)

    parts = _open_svg(
        "Bode phase จาก ngspice",
        "กราฟเฟสของ Vout เทียบ Vin จาก ngspice .ac จริง",
    )
    parts += _title("Bode Phase · เฟสของ Vout เทียบ Vin",
                    "ข้อมูลจริงจาก ngspice .ac · ค่าติดลบหมายถึง Vout ตามหลัง Vin")
    parts += _grid_x(x_ticks, low, high)
    parts += _grid_y(y_ticks, y_low, y_high)
    parts += _axes("Frequency (Hz)", "Phase (deg)")

    for value in x_ticks:
        x = _x_log(value, low, high)
        parts.append(_axis_text(x, TOP + PLOT_H + 18, _freq_short(value)))
    for value in y_ticks:
        y = _y(value, y_low, y_high)
        parts.append(_axis_text(LEFT - 10, y + 4, _fmt(value, 0), anchor="end"))

    if y_low <= -180.0 <= y_high:
        y = _y(-180.0, y_low, y_high)
        parts.append(
            f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + PLOT_W}" y2="{y:.1f}" '
            f'stroke="{ORANGE}" stroke-width="1.2" stroke-dasharray="5 4"/>'
        )
        parts.append(_axis_text(LEFT + PLOT_W - 4, y - 5, "−180° · กลับเฟส",
                                anchor="end", size=10, color=ORANGE))

    points = [
        (_x_log(point.frequency_hz, low, high), _y(point.phase_deg, y_low, y_high))
        for point in ac.points
    ]
    parts.append(_polyline(points, TEAL))
    parts += _legend(LEFT + 4, TOP + PLOT_H - 10, [("ngspice .ac phase", TEAL)])
    parts.append("</svg>")
    return "\n".join(parts)


def transient_svg(tran: TransientResult) -> str:
    """Vin/Vout waveform chart in milliseconds and millivolts."""
    times_ms = [value * 1e3 for value in tran.time_s]
    vin_mv = [value * 1e3 for value in tran.vin_v]
    vout_mv = [value * 1e3 for value in tran.vout_v]
    x_low, x_high = min(times_ms), max(times_ms)
    data_low = min(min(vin_mv), min(vout_mv))
    data_high = max(max(vin_mv), max(vout_mv))
    pad = max(0.5, (data_high - data_low) * 0.12)
    y_ticks = _ticks(data_low - pad, data_high + pad, 6)
    y_low, y_high = min(y_ticks), max(y_ticks)
    x_ticks = _ticks(x_low, x_high, 6)

    parts = _open_svg(
        "Transient waveform จาก ngspice",
        "กราฟ Vin และ Vout ตามเวลาจากการรัน ngspice .tran จริง",
    )
    parts += _title("Transient · Vin และ Vout ตามเวลา",
                    "ข้อมูลจริงจาก ngspice .tran · หน้าต่าง 5 รอบสุดท้าย")
    for value in x_ticks:
        x = LEFT + (value - x_low) / (x_high - x_low) * PLOT_W
        parts.append(
            f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" y2="{TOP + PLOT_H}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
    parts += _grid_y(y_ticks, y_low, y_high)
    parts += _axes("Time (ms)", "Voltage (mV)")

    for value in x_ticks:
        x = LEFT + (value - x_low) / (x_high - x_low) * PLOT_W
        parts.append(_axis_text(x, TOP + PLOT_H + 18, _fmt(value, 2)))
    for value in y_ticks:
        y = _y(value, y_low, y_high)
        parts.append(_axis_text(LEFT - 10, y + 4, _fmt(value, 1), anchor="end"))

    if y_low <= 0 <= y_high:
        y = _y(0, y_low, y_high)
        parts.append(
            f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + PLOT_W}" y2="{y:.1f}" '
            f'stroke="{AXIS}" stroke-width="1" stroke-dasharray="2 4"/>'
        )

    vin_points = [
        (LEFT + (t - x_low) / (x_high - x_low) * PLOT_W, _y(v, y_low, y_high))
        for t, v in zip(times_ms, vin_mv)
    ]
    vout_points = [
        (LEFT + (t - x_low) / (x_high - x_low) * PLOT_W, _y(v, y_low, y_high))
        for t, v in zip(times_ms, vout_mv)
    ]
    parts.append(_polyline(vin_points, TEAL, 2.0))
    parts.append(_polyline(vout_points, ORANGE, 2.2))
    parts += _legend(LEFT + 4, TOP + PLOT_H - 10,
                     [("Vin", TEAL), ("Vout", ORANGE)])
    parts.append("</svg>")
    return "\n".join(parts)


def cutoff_label(value: float | None) -> str:
    """Human-readable cutoff label used by the template context."""
    return _freq_long(value)
