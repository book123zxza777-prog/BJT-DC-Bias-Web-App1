# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** สร้าง Flask Web App หลายไฟล์ที่รับค่า VCC/R1/R2/RC/RE/β/VBE (ตัวต้านทานเลือกหน่วย Ω/kΩ/MΩ) แล้วคำนวณ DC Operating Point ด้วย Python พร้อม validation, region warning และ automated tests

**Architecture:** `dc_bias.py` เป็น engineering module บริสุทธิ์ (ไม่มี Flask) รับ `BiasInputs` หน่วย SI แล้วคืน `BiasResult`; `app.py` ทำหน้าที่ parse ฟอร์ม/แปลงหน่วย/จัดรูปแบบตัวเลข/เรนเดอร์ Jinja template เท่านั้น; template ไม่มีสมการและไม่คำนวณใด ๆ

**Tech Stack:** Python 3.15.2 (≥3.10), Flask ≥3.0, Jinja2, `unittest`, HTML + CSS (ไม่มี JavaScript)

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-web-app-design.md`

## Global Constraints

- Python ≥ 3.10 (เครื่องพัฒนา: 3.15.2)
- dependency เดียวใน `requirements.txt`: `Flask>=3.0`
- test runner: `unittest` — ห้ามใช้ pytest; คำสั่งตรวจ: `python -m unittest discover -s tests -v`
- UI เป็นภาษาไทย ใช้ศัพท์เทคนิคภาษาอังกฤษกำกับ; ไม่มี JavaScript
- `dc_bias.py` ต้องไม่ import flask/request/template ใด ๆ
- `VCE_SAT_V = 0.3` (V) เป็นค่าคงที่ของแบบจำลอง
- ตัวคูณหน่วย: `{"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}`
- ค่าที่แสดง: แรงดัน 3 ตำแหน่งทศนิยม + `V`; IC/IE เป็น mA (3 ตำแหน่ง); IB เป็น µA (2 ตำแหน่ง); RTH เป็น kΩ (2 ตำแหน่ง)
- นอก Active Region: แสดงตัวเลขที่คำนวณได้ + warning เสมอ (ห้ามซ่อนหรือ clamp)
- ห้าม commit `.venv/`, `__pycache__/`, `.env` (มีใน `.gitignore` แล้ว)
- Commit ผ่าน GitHub Desktop — agent เตรียมไฟล์ให้เท่านั้น ไม่ต้องรัน `git commit`

## Review Focus

1. **อินพุตที่ไม่เป็นจำนวนจำกัด (`nan`/`inf`)** — ผู้ใช้พิมพ์ `nan` หรือค่าที่ทำให้ผลลัพธ์ล้น ต้องได้ error อ่านรู้เรื่อง ไม่ใช่ 500 หรือตัวเลข `nan` บนหน้าจอ → เทสต์ใน Task 1 (`test_validate_rejects_non_finite`) และ Task 2 (`test_overflow_raises_validation_error`)
2. **ฟอร์มว่าง/ส่งมาไม่ครบทุกช่อง** — ต้องได้ HTTP 400 พร้อม error ครบทุกช่อง ไม่ crash → Task 4 (`test_empty_form_returns_400_with_errors`)
3. **หน่วยที่ส่งมาไม่ถูกต้องหรือหายไป** — ต้องไม่ถูกเดาเงียบ ๆ → Task 4 (`test_invalid_unit_returns_400`)
4. **ค่าที่ทำให้หารด้วยศูนย์/สูตรพัง** — R ทุกตัว > 0 ถูกบังคับแล้ว แต่ค่าสุดขั้วต้องไม่ทำให้เกิด exception ที่ไม่ถูกจัดการ → Task 2 (`test_overflow_raises_validation_error`)
5. **β ต่ำมาก (β=1)** — ต้องยังคำนวณและคง invariant ของ Active Region → Task 2 (`test_low_beta_stays_consistent`)

---

## File Structure

| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `dc_bias.py` | dataclasses, unit conversion, validation, สมการ DC, การจำแนก region |
| `app.py` | Flask app, parse ฟอร์ม, จัดรูปแบบตัวเลข, routes |
| `templates/index.html` | ฟอร์ม + ตารางผลลัพธ์ + error/warning (Jinja) |
| `static/style.css` | responsive layout |
| `tests/test_dc_bias.py` | เทสต์ engineering logic |
| `tests/test_web.py` | เทสต์ HTTP ด้วย Flask test client |
| `requirements.txt`, `README.md` | dependency และวิธีรัน |
| `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md` | เอกสารส่งงาน |

---

### Task 1: Engineering core — หน่วยและ validation

**Files:**
- Create: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Produces:
  - `VCE_SAT_V: float = 0.3`, `REGION_ACTIVE/CUTOFF/SATURATION: str`, `UNIT_MULTIPLIERS: dict[str, float]`
  - `BiasInputs(vcc, r1, r2, rc, re, beta, vbe)` — frozen dataclass, หน่วย SI
  - `ValidationError(errors: dict[str, str])` — subclass ของ `ValueError`, attribute `.errors`
  - `to_ohms(value: float, unit: str) -> float`
  - `validate_inputs(inputs: BiasInputs) -> None`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
# tests/test_dc_bias.py
import math
import unittest

from dc_bias import BiasInputs, ValidationError, to_ohms, validate_inputs


def make(**overrides):
    base = dict(vcc=12.0, r1=1e5, r2=2.2e4, rc=2.2e3, re=1e3, beta=100.0, vbe=0.7)
    base.update(overrides)
    return BiasInputs(**base)


class TestUnits(unittest.TestCase):
    def test_to_ohms_scales(self):
        self.assertEqual(to_ohms(100, "kohm"), 100000.0)
        self.assertEqual(to_ohms(2.2, "mohm"), 2.2e6)
        self.assertEqual(to_ohms(470, "ohm"), 470.0)

    def test_to_ohms_rejects_unknown_unit(self):
        with self.assertRaises(ValueError):
            to_ohms(1.0, "megohm")


class TestValidation(unittest.TestCase):
    def test_validate_accepts_reference_circuit(self):
        validate_inputs(make())

    def test_validate_rejects_nonpositive_values(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(r1=0.0))
        self.assertIn("r1", ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(beta=0.0))
        self.assertIn("beta", ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(vcc=0.0))
        self.assertIn("vcc", ctx.exception.errors)

    def test_validate_rejects_vbe_out_of_range(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(vbe=12.0))
        self.assertIn("vbe", ctx.exception.errors)

        with self.assertRaises(ValidationError) as ctx:
            validate_inputs(make(vbe=0.0))
        self.assertIn("vbe", ctx.exception.errors)

    def test_validate_rejects_non_finite(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValidationError) as ctx:
                validate_inputs(make(vcc=bad))
            self.assertIn("vcc", ctx.exception.errors)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `python -m unittest tests.test_dc_bias -v` (จากรากโปรเจกต์; ถ้า import ไม่เจอให้ใช้ `python -m unittest discover -s tests -v`)
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: สร้าง `dc_bias.py`**

ประกาศค่าคงที่ `VCE_SAT_V = 0.3`, `REGION_ACTIVE = "active"`, `REGION_CUTOFF = "cutoff"`,
`REGION_SATURATION = "saturation"`, `UNIT_MULTIPLIERS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}`
และ `BiasInputs` (frozen dataclass, ฟิลด์ `vcc, r1, r2, rc, re, beta, vbe: float`)

`to_ohms(value, unit)`: คูณด้วย `UNIT_MULTIPLIERS[unit]`; unit ที่ไม่รู้จัก → `raise ValueError(f"unknown unit: {unit!r}")`

`ValidationError.__init__(self, errors: dict[str, str])`: เก็บ `self.errors = dict(errors)` แล้วเรียก `super().__init__(...)` ด้วยข้อความสรุป

`validate_inputs`: ตรวจ `math.isfinite` ของทุกฟิลด์ก่อน แล้วตรวจ:
`vcc <= 0` → key `"vcc"`; `r1/r2/rc/re <= 0` → key ตามชื่อฟิลด์; `beta <= 0` → `"beta"`;
`vbe <= 0 or vbe >= vcc` → `"vbe"` — ใช้ข้อความไทยตาม spec §5.4 แล้ว `raise ValidationError(errors)` ถ้ามี error (สะสมทุก key ที่ผิด ไม่หยุดที่ตัวแรก)

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: PASS (6 tests)

- [ ] **Step 5: เตรียม commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: add bias inputs, unit conversion and validation"
```
(หรือ stage ไฟล์เหล่านี้แล้วให้ผู้ใช้ commit ผ่าน GitHub Desktop)

---

### Task 2: `calculate()` — สมการ DC และการจำแนก Region

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: `BiasInputs`, `ValidationError`, `validate_inputs`, `VCE_SAT_V`, `REGION_*` จาก Task 1
- Produces:
  - `BiasResult(vth, rth, ib, ic, ie, ve, vb, vc, vce, region, warnings)` — frozen dataclass;
    `vth/rth/ve/vb/vc/vce` หน่วย V และ Ω, `ib/ic/ie` หน่วย A, `region: str`, `warnings: tuple[str, ...]`
  - `calculate(inputs: BiasInputs) -> BiasResult`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
# ต่อท้าย tests/test_dc_bias.py
from dc_bias import (  # noqa: E402
    REGION_ACTIVE, REGION_CUTOFF, REGION_SATURATION, calculate,
)


class TestCalculateActive(unittest.TestCase):
    def test_reference_operating_point(self):
        r = calculate(make())
        self.assertEqual(r.region, REGION_ACTIVE)
        self.assertEqual(r.warnings, ())
        self.assertAlmostEqual(r.vth, 2.163934, places=5)
        self.assertAlmostEqual(r.rth, 18032.7869, places=3)
        self.assertAlmostEqual(r.ib * 1e6, 12.2986, places=3)   # µA
        self.assertAlmostEqual(r.ic * 1e3, 1.22986, places=5)   # mA
        self.assertAlmostEqual(r.ie * 1e3, 1.24216, places=5)   # mA
        self.assertAlmostEqual(r.ve, 1.24216, places=5)
        self.assertAlmostEqual(r.vb, 1.94216, places=5)
        self.assertAlmostEqual(r.vc, 9.29431, places=5)
        self.assertAlmostEqual(r.vce, 8.05215, places=5)

    def test_active_invariants(self):
        r = calculate(make())
        self.assertAlmostEqual(r.ie, (100 + 1) * r.ib, places=12)
        self.assertAlmostEqual(r.vb, r.ve + 0.7, places=12)
        self.assertAlmostEqual(r.vce, r.vc - r.ve, places=12)

    def test_low_beta_stays_consistent(self):
        r = calculate(make(beta=1.0))
        self.assertEqual(r.region, REGION_ACTIVE)
        self.assertAlmostEqual(r.ic, r.ib, places=12)
        self.assertAlmostEqual(r.ie, 2 * r.ib, places=12)


class TestCalculateRegions(unittest.TestCase):
    def test_cutoff(self):
        r = calculate(make(r1=1e5, r2=1e3))
        self.assertEqual(r.region, REGION_CUTOFF)
        self.assertTrue(r.warnings)
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, 12 * 1e3 / 101e3, places=9)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)

    def test_saturation(self):
        r = calculate(make(rc=2e4))
        self.assertEqual(r.region, REGION_SATURATION)
        self.assertTrue(r.warnings)
        self.assertLess(r.vce, 0.3)


class TestCalculateGuardrails(unittest.TestCase):
    def test_overflow_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            calculate(make(vcc=1e308, r1=1e308, r2=1e308))
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: FAIL — `ImportError: cannot import name 'calculate'` / `BiasResult`

- [ ] **Step 3: เพิ่ม `BiasResult` และ `calculate()` ใน `dc_bias.py`**

`BiasResult` เป็น frozen dataclass ตามรายการใน Interfaces

`calculate` ทำงานตามลำดับ:
1. `validate_inputs(inputs)`
2. `vth = vcc * r2 / (r1 + r2)`, `rth = r1 * r2 / (r1 + r2)`
3. ถ้า `vth <= vbe` → Cutoff: `ib = ic = ie = 0.0`, `ve = 0.0`, `vb = vth`, `vc = vcc`, `vce = vcc`,
   `region = REGION_CUTOFF`, `warnings = ("วงจรอยู่ในช่วง Cutoff — IB ≈ 0 และแบบจำลอง Forward-Active ใช้ไม่ได้",)`
4. ไม่งั้นคำนวณ `ib, ic, ie, ve, vb, vc, vce` ตามสมการใน spec §5.3;
   `region = REGION_SATURATION` + warning "VCE ต่ำกว่า 0.3 V — อยู่ใน Saturation …" เมื่อ `vce <= VCE_SAT_V`,
   อย่างอื่น `REGION_ACTIVE` และ `warnings = ()`
5. ถ้าค่าใดใน `(vth, rth, ib, ic, ie, ve, vb, vc, vce)` ไม่ finite →
   `raise ValidationError({"__all__": "ค่าที่กรอกทำให้ผลลัพธ์เกินขอบเขตตัวเลข"})`

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: PASS (11 tests)

- [ ] **Step 5: เตรียม commit**

```bash
git add dc_bias.py tests/test_dc_bias.py
git commit -m "feat: calculate DC operating point with region classification"
```

---

### Task 3: Flask skeleton — `GET /` แสดงฟอร์ม

**Files:**
- Create: `requirements.txt`, `app.py`, `templates/index.html`, `static/style.css`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `BiasInputs`, `UNIT_MULTIPLIERS` จาก Task 1
- Produces:
  - `app` (Flask instance) และ `create_app()` ถ้าจำเป็น — เทสต์ import `from app import app`
  - `DEFAULT_VALUES: dict[str, str] = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1", "beta": "100", "vbe": "0.70"}`
  - `DEFAULT_UNITS: dict[str, str] = {"r1": "kohm", "r2": "kohm", "rc": "kohm", "re": "kohm"}`
  - ชื่อฟิลด์ฟอร์ม: `vcc`, `r1`, `r2`, `rc`, `re`, `beta`, `vbe`, `unit_r1`, `unit_r2`, `unit_rc`, `unit_re`

- [ ] **Step 1: สร้าง venv และติดตั้ง Flask**

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows PowerShell
python -m pip install -r requirements.txt
```
(`requirements.txt` มีบรรทัดเดียว: `Flask>=3.0`)

- [ ] **Step 2: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
# tests/test_web.py
import unittest

from app import app


class TestIndexPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe",
                     "unit_r1", "unit_r2", "unit_rc", "unit_re"):
            self.assertIn(f'name="{name}"', html)
        self.assertIn('value="12"', html)      # ค่าเริ่มต้น VCC
        self.assertIn('value="100"', html)     # ค่าเริ่มต้น R1
        self.assertNotIn("ผลการคำนวณ", html)   # ยังไม่แสดงผลลัพธ์


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 4: สร้าง `app.py`, `templates/index.html`, `static/style.css`**

`app.py`: `app = Flask(__name__)` + route `GET /` ที่ `render_template("index.html", values=DEFAULT_VALUES, units=DEFAULT_UNITS, errors={}, result=None)`

`templates/index.html`: ฟอร์ม `method="post" action="/calculate"` มีช่อง `vcc, r1, r2, rc, re, beta, vbe`
(ใช้ `values[...]` เป็น `value`), `<select name="unit_rX">` ที่มี option `ohm` / `kohm` / `mohm`
โดยเลือกตัวที่ตรงกับ `units[...]` (แสดงข้อความ Ω / kΩ / MΩ), ปุ่ม submit "คำนวณ DC Bias",
บล็อกแสดง error (ถ้ามี) และบล็อก `{% if result %}` สำหรับตาราง "ผลการคำนวณ" (ยังไม่ต้องมีเนื้อหาใน task นี้)
ลิงก์ CSS ด้วย `url_for('static', filename='style.css')` — ห้ามมีสมการหรือการคำนวณในไฟล์นี้

`static/style.css`: สองคอลัมน์ (ฟอร์มซ้าย/ผลขวา) ยุบเป็นคอลัมน์เดียวที่ `max-width: 700px`

- [ ] **Step 5: รันเทสต์ให้ผ่าน**

Run: `python -m unittest tests.test_web -v`
Expected: PASS (1 test)

- [ ] **Step 6: เตรียม commit**

```bash
git add app.py templates/index.html static/style.css tests/test_web.py requirements.txt
git commit -m "feat: serve DC bias input form with Flask"
```

---

### Task 4: `POST /calculate` — parse, validation, ผลลัพธ์, warning

**Files:**
- Modify: `app.py`, `templates/index.html`
- Test: `tests/test_web.py`

**Interfaces:**
- Consumes: `app`, `DEFAULT_VALUES`, `DEFAULT_UNITS` (Task 3); `BiasInputs`, `ValidationError`, `UNIT_MULTIPLIERS`, `to_ohms`, `calculate` (Task 1–2)
- Produces (ใช้ในเทมเพลต):
  - `parse_inputs(form: Mapping[str, str]) -> tuple[BiasInputs | None, dict[str, str]]` — คืน `(inputs, errors)`; `errors` key ตามชื่อฟิลด์, ใช้ key `"unit_rX"` สำหรับหน่วยผิด
  - `form_state(form: Mapping[str, str]) -> tuple[dict[str, str], dict[str, str]]` — ค่า/หน่วยดิบสำหรับ echo กลับ (ถ้าฟอร์มไม่มีค่า ใช้ default)
  - `format_result(result: BiasResult) -> dict[str, object]` — คีย์: `vb, ve, vc, vce, vth` (เช่น `"1.942"`), `ic_ma` (`"1.230"`), `ie_ma`, `ib_ua` (`"12.30"`), `rth_kohm` (`"18.03"`), `region` (`"active"|"cutoff"|"saturation"`), `region_label` (ไทย), `warnings` (tuple)
- เทมเพลตใช้ตัวแปร `result` (ค่าที่ format แล้วหรือ `None`), `errors`, `values`, `units`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

```python
# ต่อท้าย tests/test_web.py
VALID = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70",
    "unit_r1": "kohm", "unit_r2": "kohm", "unit_rc": "kohm", "unit_re": "kohm",
}


class TestCalculateRoute(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_valid_post_shows_computed_results(self):
        res = self.client.post("/calculate", data=VALID)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for expected in ("1.942", "1.242", "9.294", "8.052", "1.230", "18.03"):
            self.assertIn(expected, html)
        self.assertIn("Active", html)

    def test_form_echoes_submitted_values(self):
        data = dict(VALID, r1="99", unit_r1="ohm")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn('value="99"', html)
        self.assertIn('value="ohm" selected', html)

    def test_invalid_resistor_returns_400(self):
        res = self.client.post("/calculate", data=dict(VALID, r1="0"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("มากกว่า 0", res.get_data(as_text=True))

    def test_non_numeric_returns_400(self):
        res = self.client.post("/calculate", data=dict(VALID, vcc="abc"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("ตัวเลข", res.get_data(as_text=True))

    def test_empty_form_returns_400_with_errors(self):
        res = self.client.post("/calculate", data={})
        self.assertEqual(res.status_code, 400)
        html = res.get_data(as_text=True)
        self.assertIn("ตัวเลข", html)

    def test_invalid_unit_returns_400(self):
        data = dict(VALID, unit_r1="megohm")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 400)
        self.assertIn("หน่วย", res.get_data(as_text=True))

    def test_cutoff_shows_warning(self):
        data = dict(VALID, r2="1")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Cutoff", res.get_data(as_text=True))

    def test_saturation_shows_warning(self):
        data = dict(VALID, rc="20")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Saturation", res.get_data(as_text=True))
```

- [ ] **Step 2: รันเทสต์ให้เห็นว่าล้มเหลว**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — `POST /calculate` คืน 404/405

- [ ] **Step 3: เพิ่ม `parse_inputs`, `form_state`, `format_result` และ route `POST /calculate` ใน `app.py`**

- `parse_inputs`: อ่านทุกฟิลด์ด้วย `.get(name, "")`; แปลง float ไม่ได้ → error `"กรุณากรอกตัวเลข"`; หน่วยที่ไม่อยู่ใน `UNIT_MULTIPLIERS` → error `"หน่วยไม่ถูกต้อง"` ที่ key `unit_rX`; สร้าง `BiasInputs` ด้วย `r1=to_ohms(v, unit)` ฯลฯ; คืน `(None, errors)` ถ้ามี error ใด ๆ
- route: `values, units = form_state(request.form)`; `inputs, errors = parse_inputs(request.form)`;
  ถ้า `inputs` ไม่ใช่ None ให้ `try: result = calculate(inputs)` แล้ว `except ValidationError as exc: errors.update(exc.errors)`;
  ถ้ามี error → `render_template(..., errors=errors, values=values, units=units, result=None)`, **400**;
  ถ้าสำเร็จ → `render_template(..., result=format_result(result), errors={}, values=values, units=units)`, **200**
- `format_result`: จัดรูปแบบตาม Global Constraints และแมป `region_label` เป็น `Active` / `Cutoff` / `Saturation`
- เทมเพลต: แสดง error ใต้ช่องที่ผิด (ключ `__all__` แสดงเป็นข้อความสรุปบนสุด), แสดงตารางผลลัพธ์
  (VB, VE, VC, VCE, IC, IB, IE, VTH, RTH) และกล่อง warning สีส้มเมื่อ `result.warnings` ไม่ว่าง

- [ ] **Step 4: รันเทสต์ให้ผ่าน**

Run: `python -m unittest discover -s tests -v`
Expected: PASS (19 tests total)

- [ ] **Step 5: ตรวจด้วยตาในเบราว์เซอร์**

```bash
python -m flask --app app run --debug
```
เปิด `http://127.0.0.1:5000/` → กดคำนวณด้วยค่าเริ่มต้น → เห็น VCE 8.052 V / IC 1.230 mA;
แก้ R1 เป็น `0` → เห็น error; ตั้ง R2 เป็น `1` (kΩ) → เห็น warning Cutoff

- [ ] **Step 6: เตรียม commit**

```bash
git add app.py templates/index.html static/style.css tests/test_web.py
git commit -m "feat: calculate DC bias from posted form with validation and warnings"
```

---

### Task 5: เอกสารส่งงานและ README

**Files:**
- Modify: `README.md`
- Create: `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md`

**Interfaces:**
- Consumes: ผลลัพธ์จริงจากแอป (รัน Task 4 แล้ว) และค่าคำนวณมือของ Task 2

- [ ] **Step 1: เขียน `docs/design-note.md`**

สรุป 1 หน้า: ขอบเขต, โครงไฟล์และหน้าที่, สมการที่ใช้, การจำแนก region (VCE_SAT = 0.3 V),
เหตุผลที่เลือกหน่วย Ω/kΩ/MΩ, สิ่งที่ไม่ทำในสัปดาห์นี้

- [ ] **Step 2: เขียน `docs/validation.md`**

ตารางคำนวณอิสระทีละขั้น (VTH, RTH, IB, IC, IE, VE, VB, VC, VCE) จาก
VCC=12 V, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70 V
เทียบค่ากับที่เว็บแสดง พร้อมคอลัมน์ผลต่าง (%) — ต้องใช้ค่าจากสมการ ไม่คัดลอกจากหน้าจอ
และเพิ่มเคส Cutoff (R2=1 kΩ) กับ Saturation (RC=20 kΩ) ว่าตรงกับ warning ที่เว็บแสดง

- [ ] **Step 3: สร้าง `docs/reflection.md` เป็น template**

หัวเรื่อง + คำถาม 5 ข้อ ให้ผู้เรียนเติมเอง (ห้ามเขียนคำตอบ):
เหตุใดเปิด `templates/index.html` ตรง ๆ จึงไม่เท่ากับการรัน Flask · ฟอร์มส่งข้อมูลไป Python อย่างไร ·
แก้สมการใน `dc_bias.py` แล้วต้องแก้ HTML หรือไม่ · ทำไมผลนอก Active Region จึงต้องมี warning ·
สิ่งที่คาดไม่ถึง/จะทำต่างออกไปถ้ามีเวลาอีก

- [ ] **Step 4: อัปเดต `README.md`**

ใส่คำสั่งจริงที่ทดสอบแล้ว (venv, pip install, flask run, unittest), ค่าอ้างอิงตัวอย่าง, โครงไฟล์,
หมายเหตุว่าแอปนี้ใช้ Forward-Active approximation และไม่ใช่ ngspice

- [ ] **Step 5: ตรวจทั้งชุดอีกครั้ง**

Run: `python -m unittest discover -s tests -v`
Expected: PASS ทุกเทสต์ (19 tests) และ `python -m flask --app app routes` แสดง `/` และ `/calculate`

- [ ] **Step 6: เตรียม commit**

```bash
git add README.md docs/design-note.md docs/validation.md docs/reflection.md
git commit -m "docs: add design note, validation record and reflection template"
```

---

## Self-Review

**1. Spec coverage**

| Spec section | Task |
|---|---|
| §2 Goal 1 (เปิดเว็บ/ฟอร์ม) | 3 |
| §2 Goal 2 (หน่วย Ω/kΩ/MΩ) | 1, 3, 4 |
| §2 Goal 3 (คำนวณ VB…VCE) | 2, 4 |
| §2 Goal 4 (validation) | 1, 4 |
| §2 Goal 5 (region warning) | 2, 4 |
| §2 Goal 6 (automated tests) | 1–4 |
| §2 Goal 7 (README, GitHub) | 5 (+ commit ผ่าน GitHub Desktop) |
| §5.2 API สาธารณะ | 1, 2 |
| §5.3 สมการ + cutoff/saturation | 2 |
| §5.4 validation rules | 1, 4 |
| §5.5 routes + echo ค่าที่กรอก | 3, 4 |
| §5.6 หน้าจอ | 3, 4 |
| §5.7 tests | 1–4 |
| §5.8 การแสดงผลตัวเลข | 4 |
| §5.1 docs | 5 |
| Review Focus 1–5 | 1, 2, 4 |

**2. Step scan:** ทุก step มีผลลัพธ์ตรวจได้ (รันคำสั่ง/เห็นค่าที่คาด) ไม่มี step ที่ตัดสินใจไม่ลง (“จัดการ edge case” ถูกแทนด้วยเงื่อนไขและเทสต์ที่ระบุชัด)

**3. Type consistency:** `BiasInputs`/`BiasResult`/`ValidationError`/`calculate`/`to_ohms`/`parse_inputs`/`form_state`/`format_result` ใช้ชื่อเดียวกันตลอด; ชื่อฟิลด์ฟอร์ม `unit_rX` ตรงกันทั้ง app.py และ template

**4. Review Focus:** แต่ละข้อมีเทสต์ใน task ที่เป็นเจ้าของโค้ด ตามที่ระบุในหัวข้อ Review Focus

**5. Proportion:** แผนยาวกว่า spec เล็กน้อยเพราะมีเทสต์เป็นโค้ด (เจตนาให้ตรวจได้ตรง) แต่ไม่มี implementation body ของ `calculate`/`parse_inputs` (มีแต่ signature + กฎที่ตัดสินแล้ว)
