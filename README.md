# BJT DC Bias Web App + CE Amplifier Simulator — ENG29 2121 Lab 03/04

Flask web application สำหรับ

- **Lab 03:** คำนวณ **DC Operating Point** ของ NPN BJT Common-Emitter 3 แบบไบอัส
  (Voltage Divider / Fixed / Emitter) ด้วยสมการวิเคราะห์ใน `dc_bias.py`
- **Lab 04:** จำลอง **Common-Emitter amplifier** ด้วย **ngspice จริง** (`.op`, `.ac`, `.tran`)
  ในหน้า `/simulator` — ไม่มี mock, ไม่คำนวณ physics ซ้ำใน browser

Lab 03 ถูกทิ้งไว้เหมือนเดิมทั้ง route `/`, `/calculate`, สมการและชุดเทสต์เดิม

## ความสามารถ

### Lab 03 — หน้า `/`

- เลือกโหมดได้จากหน้าเว็บ (GET reload) และแสดงเฉพาะช่องที่โหมดนั้นใช้
  - Divider: `VCC, R1, R2, RC, RE, β, VBE`
  - Fixed: `VCC, RB, RC, β, VBE`
  - Emitter: `VCC, RB, RC, RE, β, VBE`
- ตัวต้านทานเลือกหน่วยได้ Ω / kΩ / MΩ (แปลงเป็น Ω ที่ `app.parse_inputs`)
- สมการอยู่ใน Python (`dc_bias.py`) ไม่มี JavaScript คำนวณในหน้าเว็บ
  - Divider: `VTH = VCC·R2/(R1+R2)`, `RTH = R1·R2/(R1+R2)`,
    `IB = (VTH−VBE)/(RTH+(β+1)RE)`
  - Fixed: `IB = (VCC−VBE)/RB`, `VE = 0`, `VB = VBE`
  - Emitter: `IB = (VCC−VBE)/(RB+(β+1)RE)`, `VE = IE·RE`, `VB = VE+VBE`
  - ร่วม: `IC = βIB`, `IE = (β+1)IB`, `VC = VCC−IC·RC`, `VCE = VC−VE`
- ตรวจอินพุตผิด (ขาด/ไม่ใช่ตัวเลข/`nan`/`inf`/≤0/หน่วยผิด) → HTTP 400 พร้อมข้อความไทยรายฟิลด์
- โหมดที่ไม่รู้จักหรือ `mode=""` → HTTP 400 หน้า error ที่ไม่มีฟอร์ม/แผนภาพ
  (ไม่มีคีย์ `mode` เลยยังถือเป็น Divider เพื่อเข้ากับฟอร์ม Lab 02)
- เตือนเมื่อ `IB ≤ 0` (Cutoff) หรือ `VCE ≤ 0.2 V` (Saturation)
- ผลและข้อความ error ระบุโหมดที่เลือก; ผลรอบก่อนไม่แสดงเป็นผลรอบใหม่

### Lab 04 — หน้า `/simulator`

- เลือกวิเคราะห์ได้ 3 แบบ: **DC Operating Point (`.op`)**, **AC Frequency Response (`.ac`)**,
  **Transient Waveform (`.tran`)**; แต่ละรันเรียก ngspice process จริงใน temp directory
- วงจรอ้างอิงคงที่: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ,
  RL 10 kΩ, CIN = COUT = 10 µF, แหล่งสัญญาณ 10 mV peak / 1 kHz, NPN 2N3904
  (RE ไม่มี bypass capacitor)
- BJT model ถูก lock ที่ `Q2N3904` (`MODEL_LABEL = "2N3904"`, `BF = 416.4`) เพื่อให้ผลเปรียบเทียบได้
- ตรวจอินพุตตามโหมดวิเคราะห์ก่อนสร้าง netlist: ค่าทุกตัวต้อง > 0, finite,
  frequency 10 Hz–20 kHz, amplitude ≤ 500 mV peak; ช่องที่ซ่อนอยู่จะใช้ค่า default แทน
- แสดง **Run Status** (success / invalid / engine missing / simulation failed),
  engine version, ชื่อ model, เวลาที่รัน และ elapsed time ทุกครั้ง
- แยกผล **SPICE (ngspice)** กับ **Analytical (Lab 03, β=100 / VBE=0.70 V)** ในตารางเปรียบเทียบ
  และระบุว่าค่าทางวิเคราะห์ใช้เพื่ออ้างอิงเท่านั้น
- กราฟ SVG (Bode magnitude/phase, transient Vin/Vout) ถูกสร้างฝั่งเซิร์ฟเวอร์จากข้อมูลที่ parse ได้จริง
- แสดง netlist และ run log ต้นฉบับให้ตรวจได้ใน `<details>`

ไม่รวม: circuit editor อิสระ, AC ทุก bias mode, FET, custom SPICE solver,
animated overlay, deployment สู่ production

## โครงสร้าง

```
app.py                       # Flask routes เดิม + /simulator, /simulate, validation และ formatting
dc_bias.py                   # สมการ Lab 03 เดิม (ไม่แก้)
spice_engine.py              # netlist builder, ngspice discovery/version, subprocess, parser
charts.py                    # Bode magnitude/phase + transient SVG (สร้างฝั่งเซิร์ฟเวอร์)
templates/index.html         # หน้า Lab 03 + ลิงก์ไป simulator
templates/simulator.html     # หน้า Lab 04, provenance, ตารางเปรียบเทียบ, กราฟ, netlist/log
templates/mode_error.html    # หน้า 400 ของ Lab 03
static/style.css             # layout เดิม + simulator/responsive styles
static/simulator.js          # เฉพาะ UI: ซ่อน/โชว์ฟิลด์ตามโหมด + running state (ไม่มี physics)
tests/test_dc_bias.py        # 12 เทสต์เดิม (ไม่แก้)
tests/test_web.py            # 13 เทสต์เดิม (ไม่แก้)
docs/design-note.md          # หลักการออกแบบ Lab 03 + Lab 04
docs/validation.md           # A1–A5 และ B1–B8 + หลักฐาน
docs/evidence/               # ภาพหน้าจอจาก browser acceptance
docs/superpowers/            # design + plan ที่ใช้สร้างงานนี้
.opencode/skills/browser-acceptance-check/SKILL.md  # แม่แบบตรวจผ่าน browser
```

## การติดตั้งและรัน

ต้องมี Python 3.10 ขึ้นไป (เครื่องที่ใช้พัฒนา: **Python 3.13.17**, Flask 3.1.3)

### 1) ติดตั้ง ngspice

Windows (เครื่องที่ใช้พัฒนาใช้ **ngspice 47**):

1. โหลด `ngspice-47_64.7z` จาก <https://ngspice.sourceforge.io/download.html>
2. แตกเป็นเช่น `%LOCALAPPDATA%\ngspice\Spice64`
3. เพิ่ม `%LOCALAPPDATA%\ngspice\Spice64\bin` ใน `PATH`
   **หรือ** ตั้ง `NGSPICE_BIN` ให้ชี้ตรงถึง `ngspice_con.exe`
4. ตรวจสอบ: `ngspice_con -v` ต้องขึ้น `ngspice-47`

Linux/macOS: ติดตั้ง `ngspice` ด้วย package manager แล้วตรวจว่า `ngspice` หรือ
`ngspice_con` อยู่ใน `PATH` (แอปลอง `NGSPICE_BIN` ก่อน เสร็จแล้วค่อย `shutil.which`)

ถ้าไม่พบ engine หน้า `/simulator` จะขึ้นป้าย **ไม่พบ ngspice** และการกด Run จะได้ HTTP 503
โดยไม่มีการสร้างผลปลอม

### 2) ติดตั้ง Flask และรันเซิร์ฟเวอร์

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

เปิด:

- Lab 03: <http://127.0.0.1:5000/>
- Lab 04: <http://127.0.0.1:5000/simulator>

> Flask development server ใช้เฉพาะบนเครื่องตัวเอง ไม่ควรเปิดให้เครือข่ายภายนอกเข้าถึง

## การทดสอบ

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

ผลที่คาดหวัง: `Ran 25 tests ... OK` (ชุดเดิมจาก Lab 02/03 ไม่เพิ่มเทสต์ตามใบงาน)

การตรวจหน้าเว็บจริง B1–B8 และ HTTP 400/503/502 อยู่ใน [`docs/validation.md`](docs/validation.md)

## ผลจริงจากเครื่องพัฒนา (ngspice-47, 2N3904)

| รัน | ค่าที่อ่านได้ |
|---|---|
| `.op` (RE = 1 kΩ) | VB 2.004 V · VE 1.333 V · VC 9.087 V · VCE 7.754 V · IC 1.324 mA · IB 8.89 µA · IE 1.333 mA |
| `.op` (RE = 2 kΩ) | VB 2.073 V · VE 1.419 V · VC 10.450 V · VCE 9.032 V · IC 0.705 mA · IB 5.06 µA · IE 0.710 mA |
| `.ac` (RE = 1 kΩ) | gain @1 kHz 1.756 V/V (4.89 dB), phase −179.9°, midband 1.756 @8.91 kHz, cutoff ≈2 Hz / 141 MHz, 181 จุด |
| `.ac` (RE = 2 kΩ) | gain @1 kHz 0.879 V/V (−1.12 dB), midband 1.073, low cutoff ≈3.16 Hz; แจ้งเตือนว่าหา high cutoff ไม่พบในช่วง sweep |
| `.tran` (10 mV/1 kHz) | Vin 10.00 mV peak, Vout 17.55 mV peak, gain 1.756, correlation −1.0000, inverted |
| `.tran` (20 mV/2 kHz) | Vin 19.99 mV peak, Vout 35.10 mV peak, gain 1.756, correlation −1.0000, inverted |

## GitHub / Commit ส่งงาน

- Repository: <https://github.com/book123zxza777-prog/BJT-DC-Bias-Web-App1>
- Lab 03 clean-tree commit: `4e4b285`
- Lab 04 commit SHA: บันทึกในรายงานส่งงาน/ประวัติ git หลัง commit สุดท้าย
  (`git rev-parse --short HEAD`)
- Branch: `main`

## การตรวจผ่าน Browser (A1–A5, B1–B8)

ตารางฉบับเต็มอยู่ใน [`docs/validation.md`](docs/validation.md) สรุปสั้น ๆ:

| เคส | สิ่งที่ตรวจ | หลักฐาน |
|---|---|---|
| A1–A5 | Lab 03 Fixed/Emitter/Divider ไม่เปลี่ยนผลเดิม + RB=0 ได้ 400 | `evidence/a*`, `evidence/b1-*` |
| B1 | Regression Lab 03 ทั้ง 3 โหมด | `evidence/b1-*.jpg` |
| B2 | DC `.op` จาก ngspice + engine/model/status | `evidence/b2-dc.jpg` |
| B3 | เปลี่ยน RE = 2 kΩ แล้ว operating point และ gain เปลี่ยน | `evidence/b3-re2.jpg`, `evidence/b3-re2-ac.jpg` |
| B4 | Bode magnitude/phase มีแกน/หน่วย/ค่าจริง | `evidence/b4-ac.jpg` |
| B5 | Transient 10 mV/1 kHz เห็น Vin/Vout กลับเฟส | `evidence/b5-tran.jpg` |
| B6 | เปลี่ยน amplitude/frequency แล้ว waveform เปลี่ยน | `evidence/b6-source.jpg` |
| B7 | RE=0 → 400 ไม่มี success/กราฟ/ netlist | `evidence/b7-invalid.jpg` |
| B8 | Desktop + phone 390×844 ไม่มี horizontal overflow | `evidence/b8-desktop.jpg`, `evidence/b8-phone.png` |

## MCP และวิธีตรวจที่ใช้จริง

- **MCP (Model Context Protocol)** คือมาตรฐานที่ให้แอป AI รู้จักเครื่องมือ เรียกใช้ และรับผลกลับ
- ในใบงาน **OpenCode** เป็น MCP Client, **Playwright MCP** เป็น MCP Server ที่เปิดเครื่องมือควบคุมเบราว์เซอร์
- เบราว์เซอร์คุยกับ Flask ด้วย HTTP (คนละเส้นทางกับ MCP)
- เครื่องนี้ติดตั้ง Node.js 26.13.1 แล้ว แต่ยังไม่ได้ configure Playwright MCP จึงใช้
  **OpenCode Browser** สำหรับ B1–B7 และ desktop B8, และใช้ headless Chrome + `puppeteer-core`
  แค่เพื่อตั้ง viewport 390×844 ใน B8 (เกณฑ์การตรวจเท่ากัน)
- หากต้องการเพิ่ม Playwright MCP ภายหลัง สามารถสร้าง `opencode.json` ที่รากโปรเจกต์ได้:

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

## ส่วนที่ AI ช่วย / ส่วนที่ต้องตรวจเอง

- **AI ช่วย:** เขียน/แก้ `app.py`, `spice_engine.py`, `charts.py`, template/CSS/JS, เอกสาร,
  รัน unittest 25 เทสต์, เรียก ngspice จริง, เก็บ screenshot ผ่าน browser tool
  และทดสอบเส้นทาง 400/503/502 ด้วย Flask test client
- **ผู้ให้งานต้องตรวจเอง:** สมการ Lab 03, หน่วย (kΩ/µF/mV/Hz → SI), ค่า DC/AC/Transient
  เทียบกับการคำนวณอิสระใน `docs/validation.md`, netlist/log ที่แนบมา และภาพ B1–B8
  **สถานะ: ผู้ให้งานตรวจ equations/units/results และภาพ B1–B8 แล้ว อนุมัติเมื่อ 24/11/2026 ก่อน commit สุดท้าย**
- **ไม่ได้ให้ AI แต่งหลักฐาน:** ภาพหน้าจอมาจาก browser tool จริง, ตัวเลขมาจาก ngspice-47 จริง
  และ HTTP status อ่านจาก test client/network log

## ข้อจำกัดของแบบจำลอง

### Lab 03

- ใช้ Forward-Active approximation เท่านั้น, β และ VBE คงที่
- `VCE_SAT_V = 0.2 V` เป็นค่าคงที่ของแบบจำลอง Lab 03 (ไม่ใช่ค่าจาก datasheet จริง)
- ผลใน Cutoff/Saturation ยังแสดงตัวเลขแต่ติด warning ว่าเชื่อถือไม่ได้
- ไม่คิด Early effect, temperature หรือความต้านทานภายในเบส

### Lab 04

- ผลขึ้นกับ SPICE model card `Q2N3904` ที่ lock ไว้ (BF=416.4) ไม่ได้เทียบกับล็อตจริง
- ไม่มีอุณหภูมิ sweep, ไม่มี bypass capacitor, ไม่มี circuit editor อิสระ
- AC ใช้แหล่ง small-signal 1 V และ sweep 1 Hz–1 GHz; amplitude/frequency มีผลกับ Transient เท่านั้น
- Transient รอให้ coupling capacitors settle 0.2 s แล้ววัด 5 รอบสุดท้าย
- จำกัด frequency 10 Hz–20 kHz, amplitude ≤ 500 mV peak และ ngspice timeout 30 s
- Analytical comparison ใช้ β=100/VBE=0.70 V ตั้งใจให้ต่างจาก SPICE model (โดยเฉพาะ IB) เพื่อเห็นผลของสมมติฐาน
