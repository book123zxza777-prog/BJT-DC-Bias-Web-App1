"""ngspice adapter for the Lab 04 Common-Emitter amplifier simulator.

The module owns the external-process boundary: it builds a netlist from
validated SI values, runs ngspice in an isolated temporary directory, parses
the real solver output and returns typed results.  It never invents waveform
or operating-point data.

The reference circuit is the single-supply CE voltage-divider amplifier from
the Lab 04 handout: VCC, R1/R2 divider, RC, RE, coupling capacitors CIN/COUT,
load RL and an NPN 2N3904 model.  Lab 03 analytical values are intentionally
kept in ``dc_bias.py`` and are compared by the Flask layer, not here.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Literal

Analysis = Literal["dc", "ac", "tran"]

MODEL_NAME = "Q2N3904"
MODEL_LABEL = "2N3904"
MODEL_CARD = (
    ".model Q2N3904 NPN(IS=6.734f XTI=3 EG=1.11 VAF=74.03 BF=416.4 "
    "NE=1.259 ISE=6.734f IKF=66.78m XTB=1.5 BR=.7371 NC=2 ISC=0 "
    "IKR=0 RC=1 CJC=3.638p MJC=.3085 VJC=.75 FC=.5 CJE=4.493p "
    "MJE=.2593 VJE=.75 TR=239.5n TF=301.2p ITF=.4 VTF=4 XTF=2 RB=10)"
)

AC_SWEEP = "dec 20 1 1G"
AC_MIN_HZ = 1.0
AC_MAX_HZ = 1e9
TRANSIENT_SETTLE_S = 0.2
RUN_TIMEOUT_S = 30

_BENIGN_LOG_FRAGMENTS = (
    "code model",
    "xtradev",
    "couldn't be loaded",
    "can't find init file",
    "no compatibility mode selected",
)


class SpiceError(RuntimeError):
    """Base class for simulator failures with a user-facing message."""


class NgspiceNotFound(SpiceError):
    """Raised when no usable ngspice executable is available."""


class SimulationError(SpiceError):
    """Raised when ngspice fails or returns unusable output."""


@dataclass(frozen=True)
class CeParameters:
    """CE amplifier values already converted to SI units (V, A, ohm, F, Hz)."""

    vcc: float = 12.0
    r1: float = 100e3
    r2: float = 22e3
    rc: float = 2.2e3
    re: float = 1e3
    rl: float = 10e3
    cin: float = 10e-6
    cout: float = 10e-6
    source_amplitude: float = 10e-3
    frequency: float = 1e3

    def validate(self) -> None:
        values = {
            "vcc": self.vcc,
            "r1": self.r1,
            "r2": self.r2,
            "rc": self.rc,
            "re": self.re,
            "rl": self.rl,
            "cin": self.cin,
            "cout": self.cout,
            "source_amplitude": self.source_amplitude,
            "frequency": self.frequency,
        }
        for name, value in values.items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if not 10.0 <= self.frequency <= 20_000.0:
            raise ValueError("frequency must be between 10 Hz and 20 kHz")


@dataclass(frozen=True)
class DcOperatingPoint:
    vb: float
    ve: float
    vc: float
    vce: float
    ic: float
    ib: float
    ie: float


@dataclass(frozen=True)
class AcPoint:
    frequency_hz: float
    magnitude: float
    gain_db: float
    phase_deg: float


@dataclass(frozen=True)
class AcResult:
    points: tuple[AcPoint, ...]
    midband: AcPoint
    gain_1k: AcPoint
    low_cutoff_hz: float | None
    high_cutoff_hz: float | None
    sweep_min_hz: float
    sweep_max_hz: float


@dataclass(frozen=True)
class TransientResult:
    time_s: tuple[float, ...]
    vin_v: tuple[float, ...]
    vout_v: tuple[float, ...]
    vin_amplitude_v: float
    vout_amplitude_v: float
    gain: float
    inverted: bool
    correlation: float
    window_start_s: float
    window_end_s: float


@dataclass(frozen=True)
class SimulationResult:
    analysis: Analysis
    dc: DcOperatingPoint
    ac: AcResult | None
    tran: TransientResult | None
    netlist: str
    log: str
    engine: str
    model: str
    warnings: tuple[str, ...]


def find_ngspice() -> str | None:
    """Return a usable ngspice executable, or None.

    ``NGSPICE_BIN`` wins so a student can point the app at a custom install.
    """
    override = os.environ.get("NGSPICE_BIN", "").strip()
    if override and Path(override).is_file():
        return override

    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            return found

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe",
        Path("C:/Spice64/bin/ngspice_con.exe"),
        Path("C:/Program Files/ngspice/Spice64/bin/ngspice_con.exe"),
        Path("C:/Program Files (x86)/ngspice/Spice64/bin/ngspice_con.exe"),
        Path.home() / "ngspice" / "Spice64" / "bin" / "ngspice_con.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


@lru_cache(maxsize=4)
def ngspice_version(executable: str) -> str:
    """Return a short version label such as ``ngspice-47``."""
    for flag in ("-v", "--version"):
        try:
            proc = subprocess.run(
                [executable, flag],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (proc.stdout or "") + (proc.stderr or "")
        match = re.search(r"ngspice-(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            return f"ngspice-{match.group(1)}"
    return "ngspice (version unknown)"


def _fmt(value: float) -> str:
    return f"{value:.12g}"


def transient_step(frequency_hz: float) -> float:
    """A time step with about 50 samples per cycle, capped for file size."""
    return max(1.0 / (frequency_hz * 50.0), 2e-6)


def transient_stop(frequency_hz: float) -> float:
    """Run long enough for the coupling capacitors to settle, then 5 cycles."""
    return max(TRANSIENT_SETTLE_S, 5.0 / frequency_hz)


def build_netlist(params: CeParameters, analysis: Analysis) -> str:
    """Build a deterministic ngspice netlist from validated numeric values."""
    params.validate()
    if analysis not in ("dc", "ac", "tran"):
        raise ValueError(f"unknown analysis: {analysis!r}")

    lines = [
        "* ENG29 2121 Lab 04 - CE voltage-divider amplifier",
        f"* analysis: {analysis}",
        "* Q1 model: 2N3904 (Fairchild/ON Semiconductor SPICE parameters)",
        f"VCC vcc 0 DC {_fmt(params.vcc)}",
        (
            "VIN in 0 DC 0 AC 1 "
            f"SIN(0 {_fmt(params.source_amplitude)} {_fmt(params.frequency)})"
        ),
        f"R1 vcc b {_fmt(params.r1)}",
        f"R2 b 0 {_fmt(params.r2)}",
        f"RC vcc c {_fmt(params.rc)}",
        f"RE e 0 {_fmt(params.re)}",
        f"CIN in b {_fmt(params.cin)}",
        f"COUT c out {_fmt(params.cout)}",
        f"RL out 0 {_fmt(params.rl)}",
        f"Q1 c b e {MODEL_NAME}",
        MODEL_CARD,
        ".control",
        "set wr_singlescale",
        "set wr_vecnames",
        "op",
        "print v(b) v(e) v(c) @q1[ic] @q1[ib] @q1[ie]",
    ]

    if analysis == "ac":
        lines += [f"ac {AC_SWEEP}", "wrdata ac.txt v(out) v(in)"]
    elif analysis == "tran":
        step = transient_step(params.frequency)
        stop = transient_stop(params.frequency)
        lines += [f"tran {_fmt(step)} {_fmt(stop)}", "wrdata tran.txt v(in) v(out)"]

    lines += ["quit", ".endc", ".end", ""]
    return "\n".join(lines)


def _check_log(log: str) -> None:
    fatal: list[str] = []
    for raw_line in log.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(fragment in lower for fragment in _BENIGN_LOG_FRAGMENTS):
            continue
        if line.startswith("Error") or line.startswith("Fatal"):
            fatal.append(line)
        elif "no such vector" in lower or "simulation interrupted" in lower:
            fatal.append(line)
    if fatal:
        raise SimulationError(
            "ngspice รายงานข้อผิดพลาด: " + " | ".join(fatal[:4])
        )


def parse_op_log(log: str) -> DcOperatingPoint:
    """Parse the ``print`` lines produced by the .op analysis."""
    patterns = {
        "vb": r"v\(b\)\s*=\s*([-+0-9.eE]+)",
        "ve": r"v\(e\)\s*=\s*([-+0-9.eE]+)",
        "vc": r"v\(c\)\s*=\s*([-+0-9.eE]+)",
        "ic": r"@q1\[ic\]\s*=\s*([-+0-9.eE]+)",
        "ib": r"@q1\[ib\]\s*=\s*([-+0-9.eE]+)",
        "ie": r"@q1\[ie\]\s*=\s*([-+0-9.eE]+)",
    }
    found: dict[str, float] = {}
    for name, pattern in patterns.items():
        match = re.search(pattern, log)
        if not match:
            raise SimulationError(f"อ่านค่า {name} จาก ngspice output ไม่ได้")
        found[name] = float(match.group(1))

    vb, ve, vc = found["vb"], found["ve"], found["vc"]
    return DcOperatingPoint(
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vc - ve,
        ic=abs(found["ic"]),
        ib=abs(found["ib"]),
        ie=abs(found["ie"]),
    )


def parse_ac_file(path: Path) -> AcResult:
    """Parse ``wrdata`` AC output: frequency, Re/Im V(out), Re/Im V(in)."""
    if not path.is_file() or path.stat().st_size == 0:
        raise SimulationError("ngspice ไม่ได้สร้างไฟล์ผล AC")

    points: list[AcPoint] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw_line.split()
        if len(parts) < 5:
            continue
        try:
            frequency, out_re, out_im, in_re, in_im = map(float, parts[:5])
        except ValueError:
            continue
        denominator = complex(in_re, in_im)
        if abs(denominator) < 1e-30:
            continue
        gain = complex(out_re, out_im) / denominator
        magnitude = abs(gain)
        if not math.isfinite(magnitude) or magnitude <= 0:
            continue
        points.append(
            AcPoint(
                frequency_hz=frequency,
                magnitude=magnitude,
                gain_db=20.0 * math.log10(magnitude),
                phase_deg=math.degrees(math.atan2(gain.imag, gain.real)),
            )
        )

    if len(points) < 3:
        raise SimulationError("ข้อมูล AC จาก ngspice มีไม่พอสำหรับสร้างกราฟ")

    # Unwrap phase so the Bode plot is continuous instead of jumping at ±180°.
    unwrapped: list[AcPoint] = []
    previous = points[0].phase_deg
    for point in points:
        phase = point.phase_deg
        while phase - previous > 180.0:
            phase -= 360.0
        while previous - phase > 180.0:
            phase += 360.0
        unwrapped.append(replace(point, phase_deg=phase))
        previous = phase

    midband = max(unwrapped, key=lambda point: point.magnitude)
    gain_1k = min(unwrapped, key=lambda point: abs(point.frequency_hz - 1e3))
    threshold = midband.magnitude / math.sqrt(2.0)

    low_cutoff: float | None = None
    high_cutoff: float | None = None
    for first, second in zip(unwrapped, unwrapped[1:]):
        if first.magnitude < threshold <= second.magnitude and low_cutoff is None:
            low_cutoff = second.frequency_hz
        if first.magnitude >= threshold > second.magnitude and high_cutoff is None:
            high_cutoff = second.frequency_hz

    return AcResult(
        points=tuple(unwrapped),
        midband=midband,
        gain_1k=gain_1k,
        low_cutoff_hz=low_cutoff,
        high_cutoff_hz=high_cutoff,
        sweep_min_hz=unwrapped[0].frequency_hz,
        sweep_max_hz=unwrapped[-1].frequency_hz,
    )


def parse_tran_file(path: Path, frequency_hz: float) -> TransientResult:
    """Parse ``wrdata`` transient output and measure the last five cycles."""
    if not path.is_file() or path.stat().st_size == 0:
        raise SimulationError("ngspice ไม่ได้สร้างไฟล์ผล Transient")

    rows: list[tuple[float, float, float]] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw_line.split()
        if len(parts) < 3:
            continue
        try:
            time_s, vin, vout = map(float, parts[:3])
        except ValueError:
            continue
        if math.isfinite(time_s) and math.isfinite(vin) and math.isfinite(vout):
            rows.append((time_s, vin, vout))

    if len(rows) < 20:
        raise SimulationError("ข้อมูล Transient จาก ngspice มีไม่พอสำหรับสร้างกราฟ")

    end = rows[-1][0]
    start = max(rows[0][0], end - 5.0 / frequency_hz)
    segment = [row for row in rows if row[0] >= start]
    if len(segment) < 10:
        segment = rows[-10:]

    times = tuple(row[0] for row in segment)
    vin = tuple(row[1] for row in segment)
    vout = tuple(row[2] for row in segment)
    vin_amplitude = (max(vin) - min(vin)) / 2.0
    vout_amplitude = (max(vout) - min(vout)) / 2.0
    if vin_amplitude <= 1e-9:
        raise SimulationError("สัญญาณ Vin จาก ngspice มีแอมพลิจูดเป็นศูนย์")

    vin_mean = sum(vin) / len(vin)
    vout_mean = sum(vout) / len(vout)
    numerator = sum((a - vin_mean) * (b - vout_mean) for a, b in zip(vin, vout))
    denominator = math.sqrt(
        sum((a - vin_mean) ** 2 for a in vin)
        * sum((b - vout_mean) ** 2 for b in vout)
    )
    correlation = numerator / denominator if denominator else 0.0

    return TransientResult(
        time_s=times,
        vin_v=vin,
        vout_v=vout,
        vin_amplitude_v=vin_amplitude,
        vout_amplitude_v=vout_amplitude,
        gain=vout_amplitude / vin_amplitude,
        inverted=correlation < -0.5,
        correlation=correlation,
        window_start_s=times[0],
        window_end_s=times[-1],
    )


def _warnings(result_dc: DcOperatingPoint, ac: AcResult | None, tran: TransientResult | None) -> tuple[str, ...]:
    warnings: list[str] = []
    if result_dc.vce <= 0.2:
        warnings.append(
            "SPICE operating point อยู่ใกล้/อยู่ใน Saturation (VCE ≤ 0.2 V) — ตรวจวงจรก่อนใช้ผล AC"
        )
    if ac is not None:
        if ac.low_cutoff_hz is None:
            warnings.append(
                f"ไม่พบจุดตัด -3 dB ด้านความถี่ต่ำในช่วง {ac.sweep_min_hz:g} Hz – {ac.sweep_max_hz:g} Hz"
            )
        if ac.high_cutoff_hz is None:
            warnings.append(
                f"ไม่พบจุดตัด -3 dB ด้านความถี่สูงในช่วง {ac.sweep_min_hz:g} Hz – {ac.sweep_max_hz:g} Hz"
            )
    if tran is not None and not tran.inverted:
        warnings.append(
            "Transient ไม่แสดงการกลับเฟสที่คาดสำหรับ CE — ตรวจจุดวัด Vin/Vout"
        )
    return tuple(warnings)


def run_simulation(
    params: CeParameters,
    analysis: Analysis,
    *,
    timeout_s: int = RUN_TIMEOUT_S,
) -> SimulationResult:
    """Run one real ngspice analysis in a fresh temporary directory."""
    params.validate()
    if analysis not in ("dc", "ac", "tran"):
        raise ValueError(f"unknown analysis: {analysis!r}")

    executable = find_ngspice()
    if not executable:
        raise NgspiceNotFound(
            "ไม่พบ ngspice บนเครื่องนี้ — ติดตั้ง ngspice แล้วเพิ่ม bin ใน PATH "
            "หรือกำหนด environment variable NGSPICE_BIN"
        )

    netlist = build_netlist(params, analysis)
    engine = ngspice_version(executable)

    with tempfile.TemporaryDirectory(prefix="bjt_lab04_") as tmp:
        workdir = Path(tmp)
        (workdir / "circuit.cir").write_text(netlist, encoding="ascii")
        try:
            proc = subprocess.run(
                [executable, "-b", "-o", "run.log", "circuit.cir"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SimulationError(
                f"ngspice ใช้เวลาเกิน {timeout_s} วินาที — ลดจำนวนจุดหรือตรวจ Netlist"
            ) from exc
        except OSError as exc:
            raise SimulationError(f"เรียก ngspice ไม่สำเร็จ: {exc}") from exc

        log_path = workdir / "run.log"
        log = (
            log_path.read_text(encoding="utf-8", errors="replace")
            if log_path.is_file()
            else ""
        )
        if proc.returncode != 0:
            tail = " | ".join(log.strip().splitlines()[-4:])
            raise SimulationError(
                f"ngspice จบด้วย exit code {proc.returncode}: {tail or 'ไม่มี log'}"
            )

        _check_log(log)
        dc = parse_op_log(log)
        ac = parse_ac_file(workdir / "ac.txt") if analysis == "ac" else None
        tran = (
            parse_tran_file(workdir / "tran.txt", params.frequency)
            if analysis == "tran"
            else None
        )

        return SimulationResult(
            analysis=analysis,
            dc=dc,
            ac=ac,
            tran=tran,
            netlist=netlist,
            log=log,
            engine=engine,
            model=f"{MODEL_LABEL} ({MODEL_NAME})",
            warnings=_warnings(dc, ac, tran),
        )
