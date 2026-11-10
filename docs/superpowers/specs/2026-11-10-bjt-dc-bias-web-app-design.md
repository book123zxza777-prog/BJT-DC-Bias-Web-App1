# BJT DC Bias Web App — Design Document

- **วันที่:** 10 พฤศจิกายน 2569
- **รายวิชา:** ENG29 2121 Computer Programming for Electrical Engineers (2/2569)
- **Lab:** 02 — First DC Bias Web App
- **สถานะ:** รอการอนุมัติจากนักศึกษา (Design Gate)

---

## 1. Intent และเหตุผล

สร้าง **Flask Web Application** สำหรับคำนวณ DC Operating Point ของวงจร NPN BJT
Common-Emitter แบบ **Voltage-Divider Bias** ภายในคาบ Lab เดียว

เป้าหมายเชิงการเรียนรู้คือให้นักศึกษาเห็นเส้นแบ่งระหว่าง **Frontend (Template/CSS)**,
**Backend (Flask routes)**, **Engineering logic (Python module แยก)** และ **Automated tests**
พร้อมตรวจผลคำนวณกับสมการที่คำนวณเองได้ ไม่ใช่เชื่อตัวเลขจาก AI หรือค่าที่ฝังใน HTML

---

## 2. Goals / Non-goals / Anti-goals

### Goals
1. เปิดเว็บผ่าน `http://127.0.0.1:5000/` ได้จริง และเห็นฟอร์มกรอกค่า
2. รับ `VCC, R1, R2, RC, RE, β, VBE` โดย **ตัวต้านทานทั้งสี่เลือกหน่วยได้ (Ω / kΩ / MΩ)**
3. Python คำนวณ `VTH, RTH, IB, IC, IE, VE, VB, VC, VCE` แล้วส่งกลับไปแสดงใน HTML
4. Validation: ค่าหายไป / ไม่ใช่ตัวเลข / R ≤ 0 / β ≤ 0 / VCC ≤ 0 / VBE ไม่สมเหตุสมผล → Error ที่อ่านรู้เรื่อง ไม่ทำให้เว็บล้ม
5. Region warning: Cutoff และ Saturation ต้องมีคำเตือนว่า Forward-Active approximation ใช้ไม่ได้
6. Automated tests: engineering math ≥ 3 + Flask HTTP test client ≥ 1 ผ่านคำสั่ง `python -m unittest discover -s tests -v`
7. README อธิบายติดตั้ง/รัน/ทดสอบ และ commit ขึ้น GitHub ผ่าน GitHub Desktop

### Non-goals (ไม่ทำในสัปดาห์นี้)
- Bias แบบอื่น (Fixed, Emitter bias), FET
- AC small-signal, Gain, Bode plot, Transient, Signal generator
- SPICE/ngspice solver, DC load line
- Interactive schematic, overlay animation
- Authentication, database, deployment, JavaScript framework

### Anti-goals (ทำแล้วถือว่าล้มเหลว)
- ผลลัพธ์ถูกฮาร์ดโค้ดใน HTML/template แทนที่จะมาจาก Python
- สมการฟิสิกส์ไปอยู่ใน `index.html` หรือใน `app.py`
- แสดงตัวเลขโดยไม่มี warning เมื่ออยู่นอก Forward-Active
- หน้าเว็บล้ม (500) เมื่อผู้ใช้กรอกค่าผิด
- Commit `.venv/`, `.env`, credentials

---

## 3. Constraints

| ข้อจำกัด | ค่า |
|---|---|
| Runtime | Python 3.15.2 (เครื่องนี้), ใช้ได้กับ Python ≥ 3.10 |
| Framework | Flask ≥ 3.0 (dependency เดียวใน `requirements.txt`) |
| Test runner | `unittest` (ตามคำสั่งในเอกสาร Lab) — ไม่ใช้ pytest |
| โครงไฟล์ | ตาม Lab §04: `app.py`, `dc_bias.py`, `templates/`, `static/`, `tests/`, `docs/` |
| เวลา | อยู่ในกรอบ Execute 75 นาทีของ Lab |
| UI | Server-rendered HTML + CSS ล้วน ไม่ใช้ JavaScript framework |
| ภาษา UI | ป้าย/ข้อความภาษาไทย ใช้ศัพท์เทคนิคภาษาอังกฤษกำกับ (เช่น "แรงดัน VCE") |
| Git | commit ผ่าน GitHub Desktop, branch `main` |

---

## 4. Approaches ที่พิจารณา

### 4.1 การจัดการหน่วยตัวต้านทาน (ผู้ใช้เลือกแล้ว)
- **A. รับเป็น Ω ล้วน** — ง่ายสุด แต่ผู้ใช้ต้องพิมพ์ `100000` เอง เสี่ยงพิมพ์ผิด และขัดกับค่าตัวอย่างใน Lab ที่เป็น kΩ
- **B. Dropdown หน่วยต่อช่อง (Ω / kΩ / MΩ)** ✅ **เลือก**
  พิมพ์ `100` + เลือก `kΩ` → backend แปลงเป็น Ω ก่อนคำนวณ
  ต้นทุน: เพิ่ม 4 `<select>`, 1 ฟังก์ชันแปลงหน่วย, 1 เทสต์ — คุ้มเพราะทำให้ requirement "แปลง kΩ เป็น Ω ให้สอดคล้อง" มีที่ยืนชัดเจน
- **C. ฟิกซ์ว่ากรอกเป็น kΩ ทั้งสี่ตัว** — ตรงกับข้อมูล Lab ที่สุด แต่กรอก `470 Ω` ไม่ได้ ขาด generality

**ผลลัพธ์:** ใช้ B

### 4.2 โครง Route
- **A. `GET /` + `POST /calculate`** ✅ **เลือก** — ตรงกับเกณฑ์ตรวจรับ A1/A2 ที่ระบุว่า "POST /calculate หรือ POST /" ตรงตัว, ผลลัพธ์เป็น server-rendered HTML ทำให้ตรวจได้ว่า backend คำนวณจริง
- B. Route เดียว + Post/Redirect/Get — กันการกด refresh ซ้ำได้ แต่ต้องใช้ session/flash เพิ่ม Complexity โดยไม่จำเป็นกับ scope นี้
- C. JSON API + `fetch()` — เสี่ยงตีความว่า "ค่ามาจาก JavaScript" และเพิ่ม JS ที่ไม่อยู่ใน scope

**ผลลัพธ์:** ใช้ A

### 4.3 ตำแหน่งของการคำนวณและการจำแนก Region
- **A. `dc_bias.py` คำนวณ + จำแนก region + คืน warning เอง** ✅ **เลือก** — engineering logic ทดสอบได้โดยไม่ต้องมี HTTP, `app.py` เหลือหน้าที่แค่ parse/แปลงหน่วย/เรนเดอร์
- B. `app.py` จำแนก region เอง — ทำให้ตรรกะฟิสิกส์รั่วไปฝั่งเว็บ ขัดกับ anti-goal

**ผลลัพธ์:** ใช้ A

### 4.4 ตำแหน่งของ Validation
- **A. `dc_bias.py` ตรวจข้อจำกัดทางวิศวกรรม (R>0, β>0, VCC>0, VBE<VCC) แล้ว raise `ValidationError` พร้อม key ของ field** ✅ **เลือก**
- B. ตรวจใน `app.py` ทั้งหมด — เขียนเทสต์ง่ายกว่าเล็กน้อย แต่ฟิสิกส์ไปปนกับ HTTP

**ผลลัพธ์:** ใช้ A (การแปลง string → float และการอ่านหน่วยเป็นหน้าที่ของ `app.py`)

---

## 5. การออกแบบ (ส่วนที่ตัดสินแล้ว)

### 5.1 โครงสร้างไฟล์

```
app.py                          # Flask app, routes, parse form, render
dc_bias.py                      # engineering logic ล้วน (ไม่ import flask)
templates/index.html            # form + results (Jinja2)
static/style.css                # responsive layout
tests/test_dc_bias.py           # engineering calculations
tests/test_web.py               # Flask test client
requirements.txt                # Flask>=3.0
README.md                       # วิธีติดตั้ง/รัน/ทดสอบ
docs/superpowers/specs/…        # เอกสารนี้ (design ฉบับสมบูรณ์)
docs/design-note.md             # สรุป design ฉบับนักศึกษา — Agent ร่าง
docs/validation.md              # ตารางคำนวณอิสระ + เทียบกับผลเว็บ — Agent ร่าง
docs/reflection.md              # template คำถามนำ — นักศึกษาเติมเอง (Agent ไม่เขียนเนื้อหา)
```

**ขอบเขตของ docs:** `design-note.md` และ `validation.md` เป็นส่วนหนึ่งของงานที่ Agent สร้าง (ต้องมีตารางคำนวณอิสระจริง ไม่ใช่คัดลอกผลจากเว็บ) ส่วน `reflection.md` สร้างเป็นโครงคำถามเท่านั้น เนื้อหาสะท้อนคิดเป็นของผู้เรียน

### 5.2 `dc_bias.py` — สาธารณะ API

```python
VCE_SAT_V = 0.3                      # เกณฑ์ Saturation (V) — ค่าคงที่ของแบบจำลอง

REGION_ACTIVE = "active"
REGION_CUTOFF = "cutoff"
REGION_SATURATION = "saturation"

UNIT_MULTIPLIERS = {"ohm": 1.0, "kohm": 1e3, "mohm": 1e6}

@dataclass(frozen=True)
class BiasInputs:      # หน่วย SI แล้ว (V, Ω)
    vcc: float; r1: float; r2: float; rc: float; re: float
    beta: float; vbe: float

@dataclass(frozen=True)
class BiasResult:
    vth: float; rth: float
    ib: float; ic: float; ie: float          # A
    ve: float; vb: float; vc: float; vce: float  # V
    region: str
    warnings: tuple[str, ...]

class ValidationError(ValueError):
    def __init__(self, errors: dict[str, str])   # {"r1": "...", "beta": "..."}

def to_ohms(value: float, unit: str) -> float   # unit ∈ {"ohm","kohm","mohm"}
def validate_inputs(inputs: BiasInputs) -> None # raise ValidationError
def calculate(inputs: BiasInputs) -> BiasResult # เรียก validate_inputs ก่อนเสมอ
```

### 5.3 สมการ

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
ถ้า VTH ≤ VBE  → Cutoff: IB = IC = IE = 0, VE = 0, VB = VTH, VC = VCC, VCE = VCC
ถ้า VTH > VBE:
    IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
    IC  = β·IB
    IE  = (β + 1)·IB
    VE  = IE·RE
    VB  = VE + VBE
    VC  = VCC − IC·RC
    VCE = VC − VE
    ถ้า VCE ≤ 0.3 V → region = saturation (+ warning)
    อย่างอื่น       → region = active
```

**การตัดสินใจ:** เมื่ออยู่นอก Forward-Active **ยังแสดงตัวเลขที่คำนวณได้** แต่ติด warning ชัดเจนว่าแบบจำลองใช้ไม่ได้และค่าที่แสดงเชื่อถือไม่ได้ (ไม่ปัดเป็น 0 และไม่ซ่อนผล เพราะนักศึกษาต้องเห็นว่าทำไมจึงผิด)

**หมายเหตุ Cutoff:** ในสภาวะ Cutoff กระแสทุกตัวเป็น 0 และไม่มีแรงดันตกคร่อม RE
ดังนั้น `VB = VTH` (แรงดันจากตัวแบ่งแรงดันขณะไม่มีโหลด) ซึ่ง **ไม่เท่ากับ** `VE + VBE`
ความสัมพันธ์ `VB = VE + VBE`, `IE = (β+1)·IB`, `VCE = VC − VE` **ใช้เฉพาะกับ Active Region**


### 5.4 Validation rules

| เงื่อนไข | ข้อความ (ไทย) | ระดับ |
|---|---|---|
| field ว่าง / แปลง float ไม่ได้ | "กรุณากรอกตัวเลข" | error |
| ค่าเป็น `NaN` หรือ `inf` (`math.isfinite` เป็น False) | "กรุณากรอกตัวเลขที่มีขอบเขตจำกัด" | error |
| `VCC ≤ 0` | "VCC ต้องมากกว่า 0 V" | error |
| `R1, R2, RC, RE ≤ 0` | "ค่าความต้านทานต้องมากกว่า 0 Ω" | error |
| `β ≤ 0` | "β ต้องมากกว่า 0" | error |
| `VBE ≤ 0` หรือ `VBE ≥ VCC` | "VBE ต้องอยู่ระหว่าง 0 ถึง VCC" | error |
| `VTH ≤ VBE` | "วงจรอยู่ในช่วง Cutoff — IB ≈ 0" | warning |
| `VCE ≤ 0.3 V` | "VCE ต่ำกว่า 0.3 V — อยู่ใน Saturation" | warning |

Error → HTTP **400** + แสดงค่าที่ผู้ใช้กรอกไว้กลับในฟอร์ม (ไม่ต้องพิมพ์ใหม่)
Warning → HTTP **200** + ผลลัพธ์ + ป้ายสถานะ

### 5.5 Routes

| Route | Method | พฤติกรรม |
|---|---|---|
| `/` | GET | แสดงฟอร์มพร้อมค่าเริ่มต้น = ค่าตัวอย่างใน Lab (12 V, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ, β=100, VBE=0.70) ยังไม่แสดงผล |
| `/calculate` | POST | parse → แปลงหน่วย → `calculate()` → render ผลลัพธ์; error → 400 |

**ทั้งสองกรณี (สำเร็จและ error) ฟอร์มจะแสดงค่าที่ผู้ใช้ส่งมาและหน่วยที่เลือกไว้กลับไป** ไม่รีเซ็ตเป็นค่าเริ่มต้น เพื่อให้แก้ค่าเดิมต่อได้ทันที


### 5.6 หน้าจอ (text sketch)

```
┌──────────────────────────────────────────────────────────┐
│  BJT DC Bias Calculator — Voltage Divider                │
├───────────────────────────┬──────────────────────────────┤
│ VCC [ 12    ] V           │  ผลการคำนวณ                  │
│ R1  [ 100   ] [kΩ ▾]      │  สถานะ: ACTIVE (เขียว)        │
│ R2  [ 22    ] [kΩ ▾]      │  VB   1.942 V                │
│ RC  [ 2.2   ] [kΩ ▾]      │  VE   1.242 V                │
│ RE  [ 1     ] [kΩ ▾]      │  VC   9.294 V                │
│ β   [ 100   ]             │  VCE  8.052 V                │
│ VBE [ 0.70  ] V           │  IC   1.230 mA               │
│                           │  IB  12.30 µA · IE 1.242 mA   │
│ [ คำนวณ DC Bias ]         │  VTH 2.164 V · RTH 18.03 kΩ   │
└───────────────────────────┴──────────────────────────────┘
```

- Error: แสดงใต้ช่องที่ผิด + สรุปด้านบน
- Warning: กล่องสีส้มเหนือตารางผลลัพธ์
- Responsive: ≤ 700 px ยุบเป็นคอลัมน์เดียว
- หน้าตาละเอียด (สี/ฟอนต์) เป็นดุลพินิจของผู้สร้าง

### 5.7 Tests (ขั้นต่ำ)

`tests/test_dc_bias.py`
1. ค่าอ้างอิง Lab: VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, β=100, VBE=0.7
   → VTH ≈ 2.1639 V, RTH ≈ 18032.79 Ω, IB ≈ 12.299 µA, IC ≈ 1.2299 mA, IE ≈ 1.2422 mA,
     VE ≈ 1.2422 V, VB ≈ 1.9422 V, VC ≈ 9.2943 V, VCE ≈ 8.0522 V, region = active
2. `to_ohms(100, "kohm") == 100000` และผลคำนวณจาก "100 kΩ" เท่ากับจาก "100000 Ω" (tolerance 1e-9)
3. Cutoff: R2 เล็กมาก (เช่น R1=100k, R2=1k) → region = cutoff, IC = 0, มี warning
4. Saturation: RC ใหญ่ (เช่น 20 kΩ) → region = saturation, มี warning
5. Validation: R1 = 0, β = 0, และ VBE ≥ VCC → `ValidationError` พร้อม key ถูกต้อง
6. ความสอดคล้อง **ใน Active Region เท่านั้น**: `IE == (β+1)·IB`, `VB == VE + VBE`, `VCE == VC − VE`
7. Cutoff invariants แยกต่างหาก: `IB == IC == IE == 0`, `VE == 0`, `VB == VTH`, `VC == VCC`, `VCE == VCC`

`tests/test_web.py`
1. `GET /` → 200 และมีช่อง `name="vcc"`, `name="r1"`… ครบ
2. `POST /calculate` ค่าปกติ → 200 และ HTML มีค่า VB/VCE ที่คำนวณได้ (ไม่ใช่ค่าคงที่)
3. `POST /calculate` `r1=0` → 400 + ข้อความ error
4. `POST /calculate` `vcc=abc` → 400 ไม่ crash
5. `POST /calculate` เคส cutoff → 200 + ข้อความเตือน

### 5.8 การแสดงผลตัวเลข
- แรงดัน: ทศนิยม 3 ตำแหน่ง + `V`
- กระแส: `IC`, `IE` เป็น mA (3 ตำแหน่ง), `IB` เป็น µA (2 ตำแหน่ง)
- ความต้านทาน: `RTH` แสดงเป็น kΩ (2 ตำแหน่ง)

รูปแบบทั้งหมดอยู่ใน helper เดียวใน `app.py` เพื่อไม่ให้ template คำนวณ

---

## 6. สิ่งที่เหลือให้ผู้สร้างตัดสินใจ

- รายละเอียดหน้าตา: สี ฟอนต์ ระยะห่าง เงา การ์ด (ทำตาม `static/style.css` ได้อิสระ)
- ถ้อยคำภาษาไทยของ label/ข้อความ error ให้อ่านเป็นธรรมชาติ (ความหมายตาม §5.4 ต้องคงเดิม)
- จะแยก `base.html` หรือใช้ไฟล์เดียว (แนะนำไฟล์เดียวเพราะมีหน้าเดียว)
- จำนวนตำแหน่งทศนิยมละเอียดเพิ่มเติม ตราบใดที่ยังตรวจค่าอ้างอิงได้
- ข้อความ commit และชื่อ repository บน GitHub
