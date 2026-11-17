# Lab 03 Multi-Mode BJT Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม Fixed Bias และ Emitter Bias ให้เว็บ Flask เดิม โดยคงผล Voltage Divider เดิมไว้ทุกหลัก

**Architecture:** คง `BiasInputs`/`calculate()` ของ Divider ไว้เป็นสัญญาเดิม เพิ่ม dataclass และฟังก์ชันแยกต่อโหมดใน `dc_bias.py`; `app.py` แปลงหน่วยที่จุดเดียวและ dispatch ตาม `mode`; เทมเพลตสลับช่อง/แผนภาพตามโหมดด้วย GET reload โดยไม่มี JavaScript

**Tech Stack:** Python 3.15.2, Flask 3.1.3, Jinja2, unittest (เฉพาะชุดเดิม), OpenCode Browser

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-multi-bias-design.md`

## Global Constraints

- รันเทสต์ด้วย `.venv\Scripts\python.exe` เท่านั้น (ระบบ `python` ไม่มี Flask)
- **ห้ามเพิ่ม unittest ใหม่** ตามใบงาน; เทสต์เดิม 25 ตัวต้องผ่านตลอด (`Ran 25 tests ... OK`)
- ห้ามแก้สมการ Divider เดิม; `calculate()` ต้องคงพฤติกรรมเดิม
- Warning threshold: `VCE_SAT_V = 0.2`
- หน่วย: Ω / kΩ / MΩ; แปลงเป็น SI ที่ `parse_inputs` จุดเดียว
- UI ภาษาไทย, ไม่มี JavaScript
- โหมดที่ไม่มีคีย์ `mode` = `divider`; `mode=""` หรือค่าไม่รู้จัก = HTTP 400
- ห้าม commit `.venv`, log, credentials
- ค่าอ้างอิงอิสระ A1–A5: A1 IC 1.229858 mA / VCE 8.052155 V; A2 1.130000 / 9.514000; A3 1.026340 / 8.705450; A4 0.940100 / 8.032779; A5 = 400

## Review Focus

1. **ฟอร์ม Lab 2 เดิมที่ไม่มี `mode`** — ต้องยังคำนวณ Divider ได้ (200 + ค่าเดิม) ไม่ใช่ 400
2. **`mode=""` หรือ `mode=banana`** — ต้องได้ 400 หน้า error ที่ไม่มีฟอร์ม/แผนภาพของโหมดใด และไม่ fallback เป็น Divider
3. **สลับโหมดแล้วสถานะค้าง** — หลังสลับไป Fixed ต้องไม่เห็นช่อง R1/R2, ไม่เห็นผลรอบก่อน, และผลใหม่ต้องติดป้าย Fixed
4. **อินพุตไม่จำกัดในโหมดใหม่** — `rb=nan`, `inf`, `1e999`, 0, ค่าลบ ต้องได้ 400 รายฟิลด์ ไม่มี 500 และไม่มี `nan` บนหน้าจอ
5. **การแปลงหน่วยต่อฟิลด์** — RB 1000 kΩ กับ 1 MΩ ต้องให้ผลเท่ากัน; เปลี่ยน RE 1→2 kΩ ในโหมด Emitter ต้องทำให้ IC ลดลง

---

### Task 1: Engineering core — Fixed/Emitter และ threshold 0.2

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py`, `tests/test_web.py` (ไม่แก้ไข; ใช้เป็น regression)

**Interfaces:**
- Produces:
  - `VCE_SAT_V: float = 0.2`
  - `FixedBiasInputs(vcc, rb, rc, beta, vbe)`, `EmitterBiasInputs(vcc, rb, rc, re, beta, vbe)` — frozen dataclass, SI
  - `BiasResult(... vth: float | None, rth: float | None ...)`
  - `calculate_divider(inputs: BiasInputs) -> BiasResult`
  - `calculate_fixed(inputs: FixedBiasInputs) -> BiasResult`
  - `calculate_emitter(inputs: EmitterBiasInputs) -> BiasResult`
  - `calculate` ยังเป็น alias ของ `calculate_divider`

- [ ] **Step 1: เพิ่ม dataclass และปรับ type ของ `BiasResult`**

เพิ่ม `FixedBiasInputs`, `EmitterBiasInputs`; เปลี่ยน `vth`/`rth` เป็น `float | None`; ตั้ง `VCE_SAT_V = 0.2`; แก้ข้อความ warning เป็น "VCE ต่ำกว่า 0.2 V"

- [ ] **Step 2: แยก `calculate_divider` และเพิ่ม `calculate_fixed`/`calculate_emitter`**

```python
def calculate_fixed(inputs):
    # IB = (VCC - VBE) / RB; VE = 0; VB = VBE
def calculate_emitter(inputs):
    # IB = (VCC - VBE) / (RB + (beta + 1) * RE)
# ร่วม: IC = beta*IB, IE = (beta+1)*IB, VC = VCC - IC*RC, VCE = VC - VE
# IB <= 0 -> REGION_CUTOFF (กระแสเป็น 0); VCE <= 0.2 -> REGION_SATURATION; อื่น -> ACTIVE
```

- [ ] **Step 3: รัน regression suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `Ran 25 tests ... OK`

- [ ] **Step 4: ตรวจค่าอ้างอิง A2–A4 ด้วยการคำนวณตรง (ไม่เพิ่มไฟล์ใน repo)**

รันสคริปต์ชั่วคราวใน `%TEMP%` ที่ import `calculate_fixed`/`calculate_emitter` แล้วพิมพ์ค่า
Expected (tolerance 1e-6):
A2 IC 1.130000 mA / VCE 9.514000 V; A3 1.026340 / 8.705450; A4 0.940100 / 8.032779

- [ ] **Step 5: Commit**

```bash
git add dc_bias.py
git commit -m "feat: add fixed and emitter bias calculations"
```

---

### Task 2: Mode-aware parsing, validation และ dispatch

**Files:**
- Modify: `app.py`
- Create: `templates/mode_error.html`

**Interfaces:**
- Consumes: `FixedBiasInputs`, `EmitterBiasInputs`, `calculate_fixed`, `calculate_emitter`, `calculate_divider` (Task 1)
- Produces:
  - `MODES: tuple[str, ...]`, `MODE_LABELS: dict[str, str]`
  - `MODE_RESISTORS: dict[str, tuple[str, ...]]` (divider: r1,r2,rc,re; fixed: rb,rc; emitter: rb,rc,re)
  - `DEFAULT_VALUES_BY_MODE`, `DEFAULT_UNITS_BY_MODE`
  - `mode_from(source) -> str` (raise `ValidationError({"mode": ...})` เมื่อค่าว่าง/ไม่รู้จัก)
  - `parse_inputs(form, mode="divider")`, `form_state(form, mode="divider")`, `format_result(result, mode="divider")`
  - `GET /?mode=` และ `POST /calculate` (hidden `mode`)
  - `templates/mode_error.html` — หน้า 400 สำหรับโหมดผิด (ไม่มีฟอร์ม/แผนภาพ)

- [ ] **Step 1: เพิ่มค่าคงที่โหมดและ default ต่อโหมด**

divider: R1 100k, R2 22k, RC 2.2k, RE 1k; fixed: RB 1000k, RC 2.2k; emitter: RB 1000k, RC 2.2k, RE 1k; common vcc 12, beta 100, vbe 0.70

- [ ] **Step 2: เพิ่ม `mode_from` และ `ValidationError` สำหรับโหมด**

ไม่มีคีย์ `mode` → `"divider"`; `""` หรือค่าอื่น → error `mode` ข้อความ "โหมดไม่ถูกต้อง"

- [ ] **Step 3: ทำ `parse_inputs`/`form_state`/`format_result` ให้รับ `mode`**

ตรวจเฉพาะตัวต้านทานของโหมด + `vcc`,`beta`,`vbe`; แปลงหน่วยที่จุดเดียว; `format_result` เพิ่ม `mode`, `mode_label`; `vth`/`rth` เป็น `None` สำหรับ fixed/emitter

- [ ] **Step 4: dispatch ใน route และจัดการโหมดผิด**

- `index()`: `mode = mode_from(request.args)`; ถ้า `ValidationError` → `render_template("mode_error.html", message=...)`, 400
- `calculate_route()`: `mode_from(request.form)`; ถ้า error → `mode_error.html`, 400
- dispatch: `if mode == "fixed": calculate_fixed(...) elif mode == "emitter": calculate_emitter(...) else: calculate_divider(...)`; error ทุกกรณี → `result=None`, 400

- [ ] **Step 5: สร้าง `templates/mode_error.html`**

ข้อความ "โหมดไม่ถูกต้อง" + ค่าที่ส่งมา + ลิงก์ "กลับไปเลือกโหมด" (`/`); ไม่มีฟอร์มคำนวณและไม่มี SVG

- [ ] **Step 6: รัน regression suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `Ran 25 tests ... OK` (เทสต์เดิม POST โดยไม่มี `mode` ต้องยังผ่าน)

- [ ] **Step 7: ตรวจ edge case ด้วย test client (สคริปต์ชั่วคราว)**

- POST ฟอร์ม Lab 2 ไม่มี `mode` → 200 และมี `1.230`
- POST `mode=banana` → 400 และข้อความโหมด
- POST `mode=""` → 400
- GET `/?mode=banana` → 400 และไม่มี `action="/calculate"`
- POST `mode=fixed, rb=nan` → 400 และมี "ขอบเขตจำกัด"
- POST `mode=fixed, rb=1000, unit_rb=kohm` กับ `rb=1, unit_rb=mohm` → ค่า IC/VCE เท่ากัน

- [ ] **Step 8: Commit**

```bash
git add app.py templates/mode_error.html
git commit -m "feat: dispatch bias calculations by selected mode"
```

---

### Task 3: Template/CSS — ตัวเลือกโหมด เฉพาะช่อง และแผนภาพตามโหมด

**Files:**
- Modify: `templates/index.html`, `static/style.css`

**Interfaces:**
- Consumes: `mode`, `mode_label`, รายการตัวต้านทานของโหมด จาก Task 2
- Produces: หน้าเว็บที่แสดงเฉพาะช่องของโหมด, hidden `mode` ในฟอร์ม POST, แผนภาพ 3 แบบ

- [ ] **Step 1: เพิ่มแถบเลือกโหมด (GET)**

`<form method="get">` + `<select name="mode">` + ปุ่ม "เปลี่ยนโหมด" พร้อม hidden ค่าที่ใช้ร่วม (`vcc`, `rc`, `beta`, `vbe` และหน่วยของ `rc`)

- [ ] **Step 2: แสดงเฉพาะช่องของโหมด**

ฟอร์ม POST มี `<input type="hidden" name="mode" value="{{ mode }}">`; วนแสดงช่องตาม `resistors` ที่ส่งมาจาก Flask; error ข้างช่องเหมือนเดิม

- [ ] **Step 3: แผนภาพ 3 แบบ**

เพิ่ม SVG Fixed (RB, RC) และ Emitter (RB, RC, RE) ตามสไตล์เดิม; แสดงเฉพาะที่ตรง `mode`

- [ ] **Step 4: ผลลัพธ์/error ระบุโหมด**

หัวข้อผลเป็น `{{ result['mode_label'] }}`; error summary มีบรรทัด "โหมด: …"; VTH/RTH แสดงเฉพาะเมื่อไม่ใช่ `None`

- [ ] **Step 5: รัน regression suite**

Run: `.venv\Scripts\python.exe -m unittest discover -s tests -v`
Expected: `Ran 25 tests ... OK`

- [ ] **Step 6: ตรวจ HTML ต่อโหมด (test client ชั่วคราว)**

- `GET /?mode=fixed` → มี `name="rb"`, ไม่มี `name="r1"`
- `GET /?mode=emitter` → มี `name="rb"` และ `name="re"`
- `GET /?mode=divider` → มี `name="r1"` และ `name="r2"`

- [ ] **Step 7: Commit**

```bash
git add templates/index.html static/style.css
git commit -m "feat: add mode selector and per-mode circuit diagrams"
```

---

### Task 4: Browser acceptance A1–A5 และหลักฐาน

**Files:**
- Modify: `docs/validation.md`
- Create: `docs/evidence/` (ภาพอย่างน้อยหนึ่งกรณี)

**Interfaces:**
- Consumes: เว็บที่รันบน `http://127.0.0.1:5000/` (Task 3)
- Produces: ตาราง A1–A5 พร้อมค่าคาดหมาย/เห็นจริง/วิธี/สถานะ/หลักฐาน

- [ ] **Step 1: เริ่ม Flask**

Run: `.venv\Scripts\python.exe -m flask --app app run --port 5000`

- [ ] **Step 2: เปิดเว็บด้วย OpenCode Browser และอ่าน snapshot**

ตรวจว่ามี mode selector, ช่องของ Divider, และปุ่มคำนวณ (ระบุชื่อเครื่องมือที่ใช้จริง)

- [ ] **Step 3: รัน A1–A5 ผ่านฟอร์มจริง**

A1 Divider 100k/22k/1k; A2 Fixed RB 1M; A3 Emitter RB 1M RE 1k; A4 Emitter RE 2k; A5 Fixed RB 0
บันทึกค่าที่เห็นจริงเทียบ tolerance (IC ±0.01 mA, VCE ±0.02 V)
ทุกกรณีที่สำเร็จ ตรวจว่าผลลัพธ์ระบุโหมดที่เลือก (Divider/Fixed/Emitter) ไม่ใช่ป้ายของรอบก่อน
A5 ต้องเห็นข้อความให้แก้ RB, ไม่มีผลลัพธ์ของรอบก่อนค้างอยู่, และหน้าเว็บไม่ล่ม
ก่อน A4 ให้ยืนยันว่าโหมดยังเป็น Emitter และค่า VCC/RB/RC/β/VBE เท่า A3 เปลี่ยนเฉพาะ RE

- [ ] **Step 4: เก็บหลักฐาน**

ถ่าย screenshot อย่างน้อยหนึ่งกรณีลง `docs/evidence/` และคัดข้อความผลจากหน้าเว็บ

- [ ] **Step 5: เขียน `docs/validation.md`**

เพิ่มตาราง A1–A5 + ค่าอ้างอิงอิสระ Fixed/Emitter พร้อมสมการ/หน่วย + ระบุวิธีว่า `OpenCode Browser`

- [ ] **Step 6: Commit**

```bash
git add docs/validation.md docs/evidence
git commit -m "docs: record Lab 03 browser acceptance results"
```

---

### Task 5: README, repo hygiene และเอกสารส่งงาน

**Files:**
- Modify: `README.md`, `.gitignore`, `docs/design-note.md`
- Create: `.opencode/skills/browser-acceptance-check/SKILL.md`
- Remove from tracking: `flask*.log`

**Interfaces:**
- Consumes: SHA ของ implementation commit (Task 4) และ URL `https://github.com/book123zxza777-prog/BJT-DC-Bias-Web-App1`
- Produces: เอกสารครบตามใบงาน

- [ ] **Step 1: เอา log ออกจาก tracking และ ignore**

```bash
git rm --cached flask.log flask.out.log flask.err.log
```

เพิ่ม `flask*.log` ใน `.gitignore`

- [ ] **Step 2: อัปเดต README**

เพิ่ม 3 โหมด + สมการย่อ, วิธีรัน/เปิดเว็บ, GitHub URL + SHA ของ implementation commit, ระบุส่วนที่ AI ช่วยและส่วนที่นักศึกษาตรวจ, เหตุผลที่ใช้ OpenCode Browser และ config `mcp.servers.playwright` ที่พร้อมใช้เมื่อติดตั้ง Node.js
เพิ่มย่อหน้าอธิบาย MCP: OpenCode เป็น MCP Client, Playwright MCP เป็น MCP Server ที่สั่งเบราว์เซอร์, และเบราว์เซอร์คุยกับ Flask ด้วย HTTP (คนละเส้นทางกัน)

- [ ] **Step 3: เพิ่ม skill แม่แบบ**

สร้าง `.opencode/skills/browser-acceptance-check/SKILL.md` ตามแม่แบบในใบงาน

- [ ] **Step 4: อัปเดต design note**

เพิ่มหัวข้อ 3 โหมดและเกณฑ์ VCE 0.2 V

- [ ] **Step 5: Commit และ push**

```bash
git add README.md .gitignore docs .opencode
git commit -m "docs: document three bias modes and Lab 03 submission"
git push origin main
```

- [ ] **Step 6: รายงาน SHA ล่าสุดของ `main` ให้ผู้ใช้**
