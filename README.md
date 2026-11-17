# BJT DC Bias Web App — ENG29 2121 Lab 03

Flask web application สำหรับคำนวณ **DC Operating Point** ของ NPN BJT Common-Emitter
สามแบบไบอัส: **Voltage Divider**, **Fixed** และ **Emitter Bias** (แหล่งจ่ายเดียว)
ภายใต้ Forward-Active approximation (β คงที่, VBE คงที่)

## ความสามารถ

- เลือกโหมดได้จากหน้าเว็บ (GET reload) และแสดงเฉพาะช่องที่โหมดนั้นใช้
  - Divider: `VCC, R1, R2, RC, RE, β, VBE`
  - Fixed: `VCC, RB, RC, β, VBE`
  - Emitter: `VCC, RB, RC, RE, β, VBE`
- ตัวต้านทานเลือกหน่วยได้ Ω / kΩ / MΩ (แปลงเป็น Ω ที่ `app.parse_inputs`)
- สมการอยู่ใน Python (`dc_bias.py`) ไม่มี JavaScript ในหน้าเว็บ
  - Divider: `VTH = VCC·R2/(R1+R2)`, `RTH = R1·R2/(R1+R2)`,
    `IB = (VTH−VBE)/(RTH+(β+1)RE)` (คงค่าจาก Lab 02 ทุกหลัก)
  - Fixed: `IB = (VCC−VBE)/RB`, `VE = 0`, `VB = VBE`
  - Emitter: `IB = (VCC−VBE)/(RB+(β+1)RE)`, `VE = IE·RE`, `VB = VE+VBE`
  - ร่วม: `IC = βIB`, `IE = (β+1)IB`, `VC = VCC−IC·RC`, `VCE = VC−VE`
- ตรวจอินพุตผิด (ขาด/ไม่ใช่ตัวเลข/`nan`/`inf`/≤0/หน่วยผิด) → HTTP 400 พร้อมข้อความไทยรายฟิลด์
- โหมดที่ไม่รู้จักหรือ `mode=""` → HTTP 400 หน้า error ที่ไม่มีฟอร์ม/แผนภาพ
  (ไม่มีคีย์ `mode` เลยยังถือเป็น Divider เพื่อเข้ากับฟอร์ม Lab 02)
- เตือนเมื่อ `IB ≤ 0` (Cutoff) หรือ `VCE ≤ 0.2 V` (Saturation)
- ผลและข้อความ error ระบุโหมดที่เลือก; ผลรอบก่อนไม่แสดงเป็นผลรอบใหม่

ไม่รวม: SPICE/ngspice, DC load line, AC/transient/Bode, bypass capacitor, JavaScript, unittest ชุดใหม่

## โครงสร้าง

```
app.py                       # Flask routes, mode dispatch, parse/format
dc_bias.py                   # สมการแยกตามโหมด, validation, region, unit conversion
templates/index.html         # ตัวเลือกโหมด, ช่องตามโหมด, SVG 3 แบบ, ตารางผล
templates/mode_error.html    # หน้า 400 สำหรับโหมดไม่ถูกต้อง
static/style.css             # layout + mode bar/badge
tests/test_dc_bias.py        # 12 เทสต์เดิม (ไม่แก้)
tests/test_web.py            # 13 เทสต์เดิม (ไม่แก้)
docs/design-note.md          # หลักการออกแบบ
docs/validation.md           # บันทึกตรวจ A1–A5 + หลักฐาน
docs/evidence/               # ภาพหน้าจอจาก browser acceptance
docs/superpowers/            # design + plan ที่ใช้สร้างงานนี้
.opencode/skills/browser-acceptance-check/SKILL.md  # แม่แบบตรวจผ่าน browser
```

## การติดตั้งและรัน

ต้องมี Python 3.10 ขึ้นไป (เครื่องที่ใช้พัฒนา: Python 3.15.2, Flask 3.1.3)

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

เปิดเบราว์เซอร์ที่ <http://127.0.0.1:5000/> เลือกโหมดแล้วกด "เปลี่ยนโหมด"
กรอกค่าแล้วกด "คำนวณ DC Bias"

> Flask development server ใช้เฉพาะบนเครื่องตัวเอง ไม่ควรเปิดให้เครือข่ายภายนอกเข้าถึง

## การทดสอบ

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลที่คาดหวัง: `Ran 25 tests ... OK` (ชุดเดิมจาก Lab 02 ไม่เพิ่มเทสต์ตามใบงาน)

## GitHub / Commit ส่งงาน

- Repository: <https://github.com/book123zxza777-prog/BJT-DC-Bias-Web-App1>
- CommitSHA ของงาน Lab 03 (ก่อน commit เอกสารรอบสุดท้าย): `8388b8a`
- Branch: `main`

## การตรวจผ่าน Browser (A1–A5)

ตารางฉบับเต็มอยู่ใน [`docs/validation.md`](docs/validation.md) สรุปค่า IC / VCE ที่เห็นจริง:

| เคส | โหมด | IC | VCE |
|---|---|---|---|
| A1 | Divider (100k/22k/1k) | 1.230 mA | 8.052 V |
| A2 | Fixed (RB 1 MΩ) | 1.130 mA | 9.514 V |
| A3 | Emitter (RB 1 MΩ, RE 1 kΩ) | 1.026 mA | 8.705 V |
| A4 | Emitter (RE 2 kΩ) | 0.940 mA | 8.033 V |
| A5 | Fixed (RB = 0) | HTTP 400 + แจ้งแก้ RB | — |

A4 เทียบ A3: IC ลดลง 0.086 mA เมื่อเพิ่ม RE เป็น 2 kΩ

## MCP และวิธีตรวจที่ใช้จริง

- **MCP (Model Context Protocol)** คือมาตรฐานที่ให้แอป AI รู้จักเครื่องมือ เรียกใช้ และรับผลกลับ
- ในใบงาน **OpenCode** เป็น MCP Client, **Playwright MCP** เป็น MCP Server ที่เปิดเครื่องมือควบคุมเบราว์เซอร์
- เบราว์เซอร์เป็นฝั่งที่คุยกับ Flask ด้วย HTTP (คนละเส้นทางกับ MCP)
- เครื่องที่ใช้ส่งงานยังไม่มี Node.js/npx → Playwright MCP `NOT RUN` (เหตุผล: ไม่มี prerequisite)
  จึงใช้ **OpenCode Browser** ในแอป OpenCode Desktop แทน ตามทางเลือกที่ใบงานอนุญาต
  (เกณฑ์การตรวจ A1–A5 เท่ากัน) — ระบุชื่อเครื่องมือที่ใช้จริงใน `docs/validation.md`
- เมื่อติดตั้ง Node.js LTS แล้ว สามารถเพิ่ม config V2 ได้ที่รากโปรเจกต์ (ยังไม่สร้าง `opencode.json`
  ในงานนี้เพราะรัน MCP ไม่ได้):

```json
{
  "mcp": {
    "servers": {
      "playwright": {
        "type": "local",
        "command": ["npx", "-y", "@playwright/mcp@latest", "--browser", "chrome", "--isolated"]
      }
    }
  }
}
```

## ส่วนที่ AI ช่วย / ส่วนที่ตรวจเอง

- **AI ช่วย:** เขียน `dc_bias.py`, `app.py`, template/CSS, หน้า error, เอกสาร design/plan/validation,
  รันชุดเทสต์เดิม, เปิดเว็บด้วย OpenCode Browser และอ่านผล A1–A5 ภายใต้คำสั่งที่ผู้ให้งานอนุมัติ
- **ผู้ให้งานตัดสิน/ตรวจ:** เลือกแนว A/A/A (GET reload, แยก dataclass ตามโหมด, คงชื่อคีย์ผลลัพธ์เดิม),
  อนุมัติ design และแผน, ทวนค่าอ้างอิงอิสระและตาราง A1–A5 และยืนยันให้ commit/push
- **ไม่ได้ให้ AI แต่งหลักฐาน:** ภาพหน้าจอใน `docs/evidence/` มาจาก browser tool จริง และ HTTP status
  400 ใน A5 อ่านจาก network log ของแท็บ

## ข้อจำกัดของแบบจำลอง

- ใช้ Forward-Active approximation เท่านั้น ไม่ใช่การจำลอง SPICE
- `VCE_SAT_V = 0.2 V` เป็นค่าคงที่ของแบบจำลอง Lab 03 (ไม่ใช่ค่าจาก datasheet จริง)
- ผลที่อยู่ใน Cutoff/Saturation ยังแสดงตัวเลข แต่ติด warning ว่าเชื่อถือไม่ได้
- ไม่คิด Early effect, temperature, หรือความต้านทานภายในเบส
