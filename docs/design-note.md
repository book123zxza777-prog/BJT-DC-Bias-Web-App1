# Design Note — BJT DC Bias Web App (ENG29 2121 Lab 02)

## ขอบเขต

เว็บแอป Flask สำหรับคำนวณ DC Operating Point ของ NPN BJT Common-Emitter
แบบ Voltage-Divider Bias ภายใต้ Forward-Active approximation (β คงที่, VBE คงที่)

## โครงไฟล์และหน้าที่

| ไฟล์ | หน้าที่ |
|---|---|
| `dc_bias.py` | สมการ DC, unit conversion, validation, จำแนก region — ไม่รู้จัก HTTP/HTML |
| `app.py` | Flask routes, อ่านฟอร์ม, แปลงหน่วย, จัดรูปแบบตัวเลข, เรนเดอร์ template |
| `templates/index.html` | ฟอร์มรับค่า + ตารางผลลัพธ์ (ไม่มีสมการ ไม่คำนวณ) |
| `static/style.css` | layout สองคอลัมน์ ยุบเป็นคอลัมน์เดียวที่หน้าจอกว้าง ≤ 700 px |
| `tests/test_dc_bias.py` | เทสต์สมการและ validation (12 เทสต์) |
| `tests/test_web.py` | เทสต์ HTTP ด้วย Flask test client (9 เทสต์) |

## เส้นทางการไหลของข้อมูล

```
Browser form (POST /calculate)
   → app.parse_inputs()      แปลง string → float, คูณตัวคูณหน่วย
   → dc_bias.calculate()     validate + สมการ + จำแนก region
   → app.format_result()     จัดรูปแบบหน่วย/ทศนิยม
   → templates/index.html    แสดงผล (Jinja)
```

## สมการที่ใช้

```
VTH = VCC · R2 / (R1 + R2)
RTH = R1 · R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1)·RE)
IC  = β·IB          IE = (β + 1)·IB
VE  = IE·RE         VB = VE + VBE
VC  = VCC − IC·RC   VCE = VC − VE
```

## การจำแนก Operating Region

| เงื่อนไข | Region | การแสดงผล |
|---|---|---|
| `VTH ≤ VBE` | Cutoff | IB = IC = IE = 0, VE = 0, VB = VTH, VC = VCE = VCC + warning |
| `VCE ≤ 0.3 V` | Saturation | แสดงค่าที่คำนวณได้ทั้งหมด + warning |
| อื่น ๆ | Active | แสดงค่าปกติ ไม่มี warning |

`VCE_SAT_V = 0.3` เป็นค่าคงที่ใน `dc_bias.py` (ปรับได้เมื่อเปลี่ยนแบบจำลอง)

## เหตุผลที่ให้ผู้ใช้เลือกหน่วย Ω / kΩ / MΩ

ค่าตัวอย่างใน Lab เป็น kΩ ทั้งหมด (100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ) แต่สมการต้องใช้ Ω
การให้เลือกหน่วยทำให้กรอกได้ตรงกับdatasheet และบังคับให้เกิดขั้นตอนแปลงหน่วยที่ตรวจสอบได้
(`to_ohms` มีเทสต์แยก) แทนการให้ผู้ใช้เติมศูนย์เองซึ่งเสี่ยงผิดพลาด

## สิ่งที่ไม่ทำในสัปดาห์นี้

Bias แบบอื่น, AC/Transient/Bode, SPICE solver, DC load line, interactive schematic, FET,
ระบบล็อกอิน และฐานข้อมูล
