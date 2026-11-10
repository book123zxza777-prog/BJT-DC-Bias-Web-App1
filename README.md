# BJT DC Bias Web App — ENG29 2121 Lab 02

Flask web application สำหรับคำนวณ **DC Operating Point** ของ NPN BJT
Common-Emitter แบบ **Voltage-Divider Bias** ภายใต้ Forward-Active approximation
(β คงที่, VBE คงที่)

## ความสามารถ

- รับค่า `VCC`, `R1`, `R2`, `RC`, `RE`, `β`, `VBE` ผ่านหน้าเว็บ
- ตัวต้านทานแต่ละตัวเลือกหน่วยได้: Ω, kΩ, MΩ
- คำนวณ `VTH, RTH, IB, IC, IE, VE, VB, VC, VCE` ด้วย Python backend
- ตรวจสอบอินพุต (ค่าติดลบ/ศูนย์, ไม่ใช่ตัวเลข, `nan`/`inf`, หน่วยผิด) → HTTP 400 พร้อมข้อความไทย
- เตือนเมื่อวงจรอยู่นอก Active Region (Cutoff / Saturation)

ไม่รวมในสัปดาห์นี้: AC, transient, Bode plot, SPICE/ngspice, DC load line, circuit editor, FET

## โครงสร้าง

```
app.py                 # Flask routes: GET / และ POST /calculate
dc_bias.py             # สมการ DC, unit conversion, validation, region
templates/index.html   # ฟอร์ม + ตารางผลลัพธ์ (Jinja2)
static/style.css       # responsive layout
tests/test_dc_bias.py  # 12 เทสต์ (engineering)
tests/test_web.py      # 13 เทสต์ (HTTP ด้วย Flask test client)
docs/                  # design note, validation record, reflection
```

## การติดตั้งและรัน

ต้องมี Python 3.10 ขึ้นไป

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/>

> Flask development server ใช้เฉพาะบนเครื่องตัวเอง ไม่ควรเปิดให้เครือข่ายภายนอกเข้าถึง

## การทดสอบ

```powershell
python -m unittest discover -s tests -v
```

ผลที่คาดหวัง: `Ran 25 tests ... OK`

## ค่าอ้างอิงสำหรับตรวจด้วยมือ

VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

| ปริมาณ | ค่า |
|---|---|
| VTH | 2.164 V |
| RTH | 18.03 kΩ |
| IB | 12.30 µA |
| IC | 1.230 mA |
| IE | 1.242 mA |
| VE | 1.242 V |
| VB | 1.942 V |
| VC | 9.294 V |
| VCE | 8.052 V (Active) |

รายละเอียดการตรวจเทียบอยู่ใน [`docs/validation.md`](docs/validation.md)

## ข้อจำกัดของแบบจำลอง

- ใช้ Forward-Active approximation เท่านั้น ไม่ใช่การจำลอง SPICE
- ค่า `VCE_SAT_V = 0.3 V` เป็นค่าคงที่ของแบบจำลอง (ไม่ใช่ค่าจาก datasheet จริง)
- ผลที่อยู่ใน Cutoff/Saturation ยังแสดงตัวเลข แต่ติด warning ว่าเชื่อถือไม่ได้
- ไม่คิด Early effect, temperature, หรือความต้านทานภายในเบส
