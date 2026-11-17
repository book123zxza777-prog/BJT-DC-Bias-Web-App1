# Design Note — BJT DC Bias Web App (ENG29 2121 Lab 03)

## ขอบเขต

เว็บแอป Flask สำหรับคำนวณ DC Operating Point ของ NPN BJT Common-Emitter
สามแบบ: Voltage-Divider Bias (คงจาก Lab 02), Fixed Bias และ Emitter Bias
(แหล่งจ่ายเดียว) ภายใต้ Forward-Active approximation (β คงที่, VBE คงที่)

## โครงไฟล์และหน้าที่

| ไฟล์ | หน้าที่ |
|---|---|
| `dc_bias.py` | สมการ DC ต่อโหมด (`calculate_divider`/`calculate_fixed`/`calculate_emitter`), unit conversion, validation, จำแนก region — ไม่รู้จัก HTTP/HTML |
| `app.py` | Flask routes, เลือกโหมด, อ่านฟอร์ม, แปลงหน่วย, จัดรูปแบบตัวเลข, เรนเดอร์ template |
| `templates/index.html` | ตัวเลือกโหมด (GET), ฟอร์มตามโหมด, SVG 3 แบบ, ตารางผลลัพธ์ (ไม่มีสมการ ไม่คำนวณ) |
| `templates/mode_error.html` | หน้า HTTP 400 สำหรับโหมดไม่ถูกต้อง (ไม่มีฟอร์ม/แผนภาพ) |
| `static/style.css` | layout สองคอลัมน์ ยุบเป็นคอลัมน์เดียวที่หน้าจอกว้าง ≤ 700 px + mode bar/badge |
| `tests/test_dc_bias.py` | เทสต์สมการและ validation (12 เทสต์) |
| `tests/test_web.py` | เทสต์ HTTP ด้วย Flask test client (13 เทสต์) |

## เส้นทางการไหลของข้อมูล

```
Browser form (POST /calculate, hidden mode)
   → app.mode_from()         ไม่มี mode = divider; ว่าง/ผิด = 400
   → app.parse_inputs()      แปลง string → float, คูณตัวคูณหน่วย, ตรวจตามโหมด
   → dc_bias.calculate_*()   validate + สมการ + จำแนก region
   → app.format_result()     จัดรูปแบบหน่วย/ทศนิยม + mode/mode_label
   → templates/index.html    แสดงผล (Jinja)

GET /?mode=fixed → app.form_state(request.args) → render เฉพาะช่อง/ภาพของโหมดนั้น
```

## สมการที่ใช้

Divider (คงจาก Lab 02):

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
```

Fixed:

```
IB = (VCC − VBE) / RB
VE = 0        VB = VBE
```

Emitter (แหล่งจ่ายเดียว):

```
IB = (VCC − VBE) / (RB + (β + 1)·RE)
VE = IE·RE    VB = VE + VBE
```

ร่วม (ทุกโหมด):

```
IC  = β·IB          IE = (β + 1)·IB
VC  = VCC − IC·RC   VCE = VC − VE
```

## การจำแนก Operating Region

| เงื่อนไข | Region | การแสดงผล |
|---|---|---|
| Divider: `VTH ≤ VBE` | Cutoff | IB = IC = IE = 0, VE = 0, VB = VTH, VC = VCE = VCC + warning |
| `IB ≤ 0` (Fixed/Emitter) | Cutoff | กระแสเป็น 0 + warning |
| `VCE ≤ 0.2 V` | Saturation | แสดงค่าที่คำนวณได้ทั้งหมด + warning |
| อื่น ๆ | Active | แสดงค่าปกติ ไม่มี warning |

`VCE_SAT_V = 0.2` เป็นค่าคงที่ใน `dc_bias.py` ตามใบงาน Lab 03 (Lab 02 ใช้ 0.3)

## เหตุผลที่ให้ผู้ใช้เลือกหน่วย Ω / kΩ / MΩ

ค่าตัวอย่างใน Lab เป็น kΩ ทั้งหมด (100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ) แต่สมการต้องใช้ Ω
การให้เลือกหน่วยทำให้กรอกได้ตรงกับ datasheet และบังคับให้เกิดขั้นตอนแปลงหน่วยที่ตรวจสอบได้
(`to_ohms` มีเทสต์แยก) แทนการให้ผู้ใช้เติมศูนย์เองซึ่งเสี่ยงผิดพลาด

## สิ่งที่ไม่ทำในสัปดาห์นี้

AC/Transient/Bode, SPICE solver, DC load line, interactive schematic, FET,
JavaScript, unittest ชุดใหม่, ระบบล็อกอิน และฐานข้อมูล
