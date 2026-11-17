# Design — Lab 03: Multi-Mode BJT DC Bias Web App

วันที่: 2026-11-17
ต่อยอดจาก: Lab 02 (Flask voltage-divider bias calculator)
ใบงาน: ENG29 2121 Lab 03 — BJT DC Bias Web App (อาจารย์ผู้สอน)

## 1. Intent และเหตุผล

ต่อยอดเว็บ Flask เดิมให้คำนวณ DC Operating Point ของ BJT NPN Common-Emitter ได้ **สามวงจรไบอัส** —
Voltage Divider (ของเดิม), Fixed Bias และ Emitter Bias (แหล่งจ่ายเดียว) — โดยนักศึกษาตรวจสมการที่ AI สร้าง
และตรวจผลจริงผ่านเบราว์เซอร์ด้วยตาราง A1–A5 ของตนเอง

เหตุผลเชิงการเรียน: แยก "สมการ" ออกจาก "การเลือกเส้นทาง/การแปลงหน่วย/การแสดงผล" ให้เห็นชัด
และฝึกใช้ MCP/เครื่องมือเบราว์เซอร์ตรวจงานจริงแทนการอ่านโค้ด

## 2. Goals

1. มีตัวเลือกโหมดบนหน้าเว็บ และแสดงเฉพาะช่องอินพุตที่โหมดนั้นใช้
2. `dc_bias.py` มีฟังก์ชันแยกต่อโหมด (Fixed, Emitter, Divider) ตามสมการในใบงาน
3. `app.py` เลือกฟังก์ชันตามโหมดด้วย `if/elif`; โหมดที่ไม่รู้จักต้อง 400 ไม่เดาเป็น Divider
4. ตรวจอินพุตเฉพาะช่องที่จำเป็นของโหมด; อินพุตผิด → HTTP 400 พร้อมข้อความไทยรายฟิลด์
5. ผลลัพธ์และ error ระบุโหมดที่เลือก; ผลรอบก่อนต้องไม่ถูกแสดงเป็นผลของรอบใหม่
6. **ผล Divider เดิมต้องคงเดิมทุกหลัก** (A1 = IC 1.229858 mA, VCE 8.052155 V)
7. เก็บเทสต์เดิม 25 ตัวให้ผ่านทั้งหมด (ไม่เพิ่ม unittest ใหม่ตามใบงาน)
8. เอกสาร: `docs/validation.md` ตาราง A1–A5 + ค่าอ้างอิงอิสระของโหมดใหม่, README วิธีรัน + GitHub URL/SHA

## 3. Non-goals

- SPICE/ngspice, DC load line, AC/transient/Bode, capacitor bypass
- JavaScript ฝั่ง client, Playwright script, unittest ชุดใหม่
- ระบบล็อกอิน ฐานข้อมูล deployment หรือ HTTPS
- แก้สมการ Divider เดิมหรือเปลี่ยนโครงไฟล์ Lab 02

## 4. Anti-goals (ถือเป็นความล้มเหลวแม้โปรแกรมทำงานได้)

- แสดงวงจรหรือผลของโหมดหนึ่งขณะผู้ใช้เลือกอีกโหมด
- โหมดที่ไม่รู้จักถูกตีความเป็น Divider เงียบ ๆ
- ผลของรอบก่อนค้างอยู่หลังส่งฟอร์มผิด
- ย้ายสมการไปไว้ใน HTML/JavaScript
- ค่า A1 เปลี่ยนจาก Lab 02
- commit `.venv`, log หรือ credentials

## 5. Constraints

- Python 3.15.2 + Flask 3.1.3 ใน `.venv` (ระบบ `python` ไม่มี Flask)
- เทสต์เดิม 25 ตัวห้ามแตก: `BiasInputs`/`calculate()` ต้องคงพฤติกรรม Divider
- ฟอร์ม/ผลเป็นภาษาไทย, หน่วย Ω/kΩ/MΩ และแปลงเป็น SI ที่จุดเดียว (`parse_inputs`)
- Low-voltage warning threshold ของ Lab 03: **VCE ≤ 0.2 V** (เดิม 0.3 V)
- เครื่องยังไม่มี Node.js/npx → Playwright MCP ยังรันไม่ได้; ใช้ OpenCode Browser
  เป็นวิธีตรวจ (ใบงานอนุญาต, คะแนนเท่ากัน) และบันทึกวิธีจริงในตาราง
- ไม่ใช้ JavaScript

## 6. Approaches (ที่คุยและเลือกแล้ว)

### 6.1 การเลือกโหมดบนหน้าเว็บ — เลือก A

- **A (เลือก): GET reload** — dropdown + ปุ่ม "เปลี่ยนโหมด" ส่ง `GET /?mode=...`; หน้าจะ render
  เฉพาะช่องของโหมดนั้น แล้วฟอร์มกรอกค่าเป็น `POST /calculate` พร้อม hidden `mode`
  ข้อดี: เห็นเฉพาะช่องที่ใช้, ไม่มี JS, URL แชร์/refresh ได้; ข้อเสีย: มีสองฟอร์มบนหน้า
- B: ฟอร์มเดียวแสดงทุกช่องแต่ disable ช่องที่ไม่ใช้ — ผู้ใช้ยังเห็นช่องเกิน และ disabled ไม่ถูกส่ง
- C: POST reload — ไม่มี state ใน URL แต่ back/refresh สับสน

### 6.2 โครงสร้างข้อมูล — เลือก A

- **A (เลือก): แยก dataclass ต่อโหมด** — `FixedBiasInputs`, `EmitterBiasInputs` ใหม่ +
  คง `BiasInputs` เดิมสำหรับ Divider; ผลลัพธ์ใช้ `BiasResult` ร่วมกัน
  ข้อดี: validation ต่อโหมดชัด, เทสต์เดิมไม่แตก; ข้อเสีย: โค้ดซ้ำเล็กน้อย
- B: dataclass เดียวมี optional ทุกฟิลด์ — เสี่ยงตกหล่นและกระทบเทสต์เดิม
- C: ฟังก์ชันเดียวรับ dict — ขัดเจตนาใบงานที่ให้แยกฟังก์ชัน และเสี่ยงทำเทสต์เดิมพัง

### 6.3 ชื่อคีย์ผลลัพธ์ — เลือก A

- **A (เลือก): คงชื่อเดิม** `vb`, `ve`, `vc`, `vce`, `ic_ma`, `ib_ua`, `ie_ma` + เพิ่ม `mode`/`mode_label`
  (ใบงานอนุญาตให้ใช้ชื่อคีย์เดิมของ Lab 2); VTH/RTH แสดงเฉพาะ Divider
- B: เปลี่ยนเป็น `vb_v`, `ve_v`, … ตามตัวอย่างใบงาน — ต้องแก้ template/เทสต์ เสี่ยง regression

## 7. Design

### 7.1 `dc_bias.py`

```python
VCE_SAT_V = 0.2

@dataclass(frozen=True)
class FixedBiasInputs:      vcc, rb, rc, beta, vbe        # SI: V, ohm
@dataclass(frozen=True)
class EmitterBiasInputs:    vcc, rb, rc, re, beta, vbe
# BiasInputs เดิม: vcc, r1, r2, rc, re, beta, vbe  (Divider)
```

- คง `BiasResult` โดยเปลี่ยน `vth`/`rth` เป็น `float | None` (โหมดที่ไม่ใช้ส่ง `None`)
- `calculate_divider(inputs)` = ตรรกะเดิมของ `calculate()`; คงชื่อ `calculate` เป็น alias
  เพื่อความเข้ากันได้กับเทสต์/โค้ดเดิม
- เพิ่ม `calculate_fixed(inputs)` และ `calculate_emitter(inputs)`:

```
Fixed:   IB = (VCC − VBE) / RB
Emitter: IB = (VCC − VBE) / (RB + (β+1)·RE)
ร่วม:    IC = βIB, IE = (β+1)IB
         Fixed: VE = 0, VB = VBE
         Emitter: VE = IE·RE, VB = VE + VBE
         VC = VCC − IC·RC, VCE = VC − VE
```

- Validation ใช้ helper ร่วม: finite ทุกค่า, VCC > 0, RC > 0, β > 0, 0 < VBE < VCC,
  และตัวต้านทานเฉพาะโหมด > 0 (`rb`; `rb`,`re`; `r1`,`r2`,`re`)
- Region/warning แบบเดียวกันทั้งสามโหมด:
  - `IB ≤ 0` → zero currents, `REGION_CUTOFF`, warning "IB ≈ 0 …"
  - `VCE ≤ 0.2` → `REGION_SATURATION`, warning "VCE ต่ำกว่า 0.2 V …"
  - อื่น ๆ → `REGION_ACTIVE`
- ตรวจ `math.isfinite` ของผลลัพธ์ทั้งหมดก่อนคืน (คงพฤติกรรมเดิม)

### 7.2 `app.py`

- `MODES = {"divider", "fixed", "emitter"}`; `MODE_LABELS` ภาษาไทย/อังกฤษ
  ("Voltage Divider Bias", "Fixed Bias", "Emitter Bias")
- `mode_from(form_or_args)`:
  - ไม่มีคีย์ `mode` เลย → `"divider"` (ความเข้ากันได้กับฟอร์ม Lab 2 และเทสต์เดิม)
  - มีคีย์แต่เป็นค่าว่าง (`mode=""`) หรือค่าไม่รู้จัก → error `mode` → HTTP 400
  - หน้า 400 ของโหมดผิดเป็น **หน้า error ขนาดเล็ก** (ข้อความไทย + ลิงก์ "กลับไปเลือกโหมด")
    ไม่มีฟอร์มคำนวณและไม่มีแผนภาพวงจร เพื่อไม่ให้เห็นวงจร/ฟอร์มของโหมดที่ไม่ได้เลือก
- `MODE_FIELDS`: divider→`r1,r2,rc,re`; fixed→`rb,rc`; emitter→`rb,rc,re`
  (ทุกโหมดมี `vcc,beta,vbe`); unit dropdown เฉพาะตัวต้านทานที่ใช้
- `parse_inputs(form, mode)` แปลงหน่วยเป็น Ω ที่จุดเดียว แล้วสร้าง dataclass ตามโหมด
- `form_state(form, mode)` echo ค่าที่กรอกของโหมดนั้น + default ต่อโหมด
  (divider: R1 100k, R2 22k, RC 2.2k, RE 1k; fixed: RB 1M, RC 2.2k; emitter: RB 1M, RC 2.2k, RE 1k)
- `format_result(result, mode)` คงคีย์เดิม + `mode`, `mode_label`; `vth`/`rth` เป็น `None`
  สำหรับโหมดที่ไม่ใช้
- Routes:
  - `GET /` อ่าน `?mode=`; ไม่มี → divider; ไม่รู้จัก → 400 page พร้อม error
  - `POST /calculate` อ่าน hidden `mode`; dispatch `if/elif`; error ใด ๆ → `result=None`, 400
- ฟอร์มสลับโหมด (GET) ส่งต่อค่าที่ใช้ร่วม (`vcc`, `rc`, `beta`, `vbe` และหน่วยของ `rc`)
  เป็น hidden inputs เพื่อไม่ให้ผู้ใช้พิมพ์ใหม่ทั้งหน้า

### 7.3 `templates/index.html`

- แถบเลือกโหมด: `<form method="get">` + `<select name="mode">` + ปุ่ม "เปลี่ยนโหมด"
  (ส่งค่าที่ใช้ร่วมเป็น hidden)
- ฟอร์มคำนวณ: `<form method="post" action="/calculate">` + hidden `mode`
  แสดงเฉพาะช่องของโหมด; ช่องที่มี error แสดง `.field-error` ข้างช่อง (คงของเดิม)
- แผนภาพวงจร: 3 SVG (Divider / Fixed / Emitter) เลือกแสดงตาม `mode`
- ผลลัพธ์: หัวข้อระบุ `mode_label`; ตาราง VB/VE/VC/VCE/IC/IB/IE
  (+ VTH/RTH เฉพาะ Divider); region badge + warning
- Error summary มีบรรทัดระบุโหมดที่กำลังแก้

### 7.4 `static/style.css`

- สไตล์แถบเลือกโหมด (`.mode-bar`) และป้ายโหมดในผล (`.mode-badge`)
- คงสไตล์เดิมทั้งหมด; วงจรใช้ `.circuit-diagram` ที่มีอยู่

### 7.5 เอกสารและ repo

- `docs/validation.md`: ตาราง A1–A5 (อินพุต, ค่าคาดหมาย, เห็นจริง, วิธี, สถานะ, หลักฐาน)
  + ค่าอ้างอิงอิสระของ Fixed/Emitter พร้อมสมการ/หน่วย
- `README.md`: 3 โหมด, วิธีรัน/เปิดเว็บ, GitHub URL + Commit SHA, ส่วนที่ AI ช่วย/นักศึกษาตรวจ
- `.opencode/skills/browser-acceptance-check/SKILL.md`: แม่แบบจากใบงาน
- `.gitignore`: เพิ่ม `flask*.log`; `git rm --cached flask*.log`
- `opencode.json`: **ยังไม่สร้าง** เพราะไม่มี Node.js; README ระบุ config V2 ที่พร้อมใช้
  (`mcp.servers.playwright`) และเหตุผลที่ใช้ OpenCode Browser แทน

### 7.6 การ commit/push และ SHA ใน README (builder call)

- Agent เป็นผู้ commit และ push (แนวเดียวกับที่ทำใน Lab 02 รอบล่าสุดที่ผู้ใช้อนุญาต)
- SHA ที่ใส่ใน README คือ **commit ของงาน implementation** (ไม่ใช่ commit ที่แก้ README เอง)
  แล้วจึง commit เอกสารรอบสุดท้าย — ผู้ใช้ได้รับ SHA ล่าสุดของ `main` ไปส่งงาน
- ลบ `flask*.log` ออกจาก tracking ก่อน commit แรกของงานนี้

## 8. Verification

1. `.venv\Scripts\python.exe -m unittest discover -s tests -v` → 25/25 ผ่าน (regression gate)
2. เปิดเว็บจริงและรัน A1–A5 ด้วย OpenCode Browser (navigate, snapshot, fill, submit)
   เก็บหลักฐานข้อความ/ภาพอย่างน้อยหนึ่งกรณี
3. ค่าอ้างอิง A1–A5 (คำนวณอิสระ):
   - A1 Divider: IC 1.229858 mA, VCE 8.052155 V
   - A2 Fixed RB=1M: IC 1.130000 mA, VCE 9.514000 V
   - A3 Emitter RB=1M RE=1k: IC 1.026340 mA, VCE 8.705450 V
   - A4 Emitter RE=2k: IC 0.940100 mA, VCE 8.032779 V (IC ลดลง 0.08624 mA)
   - A5 Fixed RB=0: HTTP 400 + ข้อความให้แก้ RB, ไม่ crash, ไม่มีผลเก่า
4. ตรวจว่าโหมดที่ไม่รู้จัก (`mode=banana`) ได้ 400

## 9. สิ่งที่เหลือให้ผู้สร้างตัดสิน

- ถ้อยคำไทยของป้ายโหมด/ข้อความ error และรูปแบบตัวเลข (คง 3 ตำแหน่งทศนิยม)
- รายละเอียดหน้าตา SVG ของ Fixed/Emitter ให้สอดคล้องของเดิม
- ลำดับการจัดวางแถบเลือกโหมด (บนสุดของการ์ดฟอร์ม)

## 10. ผลกระทบและความเสี่ยง

- **ต่ำ:** โค้ด Divider เดิมไม่ถูกแก้ตรรกะ; เทสต์เดิมเป็นตาข่ายกันพลาด
- **ปานกลาง:** การ render เฉพาะช่องอาจทำให้เทสต์ที่ตรวจ `name="r1"` ของหน้าแรกพัง —
  กันโดย default mode = divider
- **ต่ำ:** เปลี่ยน 0.3→0.2 V ไม่กระทบเทสต์เดิม (เคสทดสอบใช้ VCE ติดลบ)
- **ความเสี่ยงเชิงกระบวนการ:** ไม่มี unittest ใหม่ตามใบงาน → ต้องพึ่ง browser acceptance
  และการคำนวณอ้างอิงอิสระเป็นหลักฐาน
