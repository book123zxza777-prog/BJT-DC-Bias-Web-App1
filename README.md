# BJT DC Bias Web App — ENG29 2121 Lab 02

Flask web application for the DC operating point of an NPN BJT
Common-Emitter amplifier with voltage-divider bias.

> สถานะ: โครงโปรเจกต์เริ่มต้น (scaffold) — โค้ดแอปพลิเคชันจะถูกเพิ่มตาม Implementation Plan ของ Lab 02

## ขอบเขต (Week 2)

- รับค่า `VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE` ผ่านหน้าเว็บ
- Python backend คำนวณ `VB, VE, VC, VCE, IC` (และ IB, IE) ภายใต้ Forward-Active approximation
- Validation + warning เมื่ออยู่นอก Active Region
- Automated tests: engineering math + Flask HTTP

ไม่รวมในสัปดาห์นี้: AC, transient, Bode plot, circuit editor, FET

## วิธีรัน (จะสมบูรณ์เมื่อโค้ดเสร็จ)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app app run --debug
# เปิด http://127.0.0.1:5000/
python -m unittest discover -s tests -v
```

## โครงสร้างเป้าหมาย

```
app.py                 # Flask routes
dc_bias.py             # engineering calculations (ไม่รู้จัก HTML/HTTP)
templates/index.html   # form + results
static/style.css
tests/test_dc_bias.py
tests/test_web.py
requirements.txt
README.md
docs/
```
