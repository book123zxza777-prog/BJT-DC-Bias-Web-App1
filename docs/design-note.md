# Design Note — BJT DC Bias Web App + CE Amplifier Simulator (ENG29 2121 Lab 03/04)

## ขอบเขต

เว็บแอป Flask สำหรับ

- **Lab 03:** คำนวณ DC Operating Point ของ NPN BJT Common-Emitter 3 แบบ:
  Voltage-Divider Bias (คงจาก Lab 02), Fixed Bias และ Emitter Bias (แหล่งจ่ายเดียว)
  ภายใต้ Forward-Active approximation (β คงที่, VBE คงที่)
- **Lab 04:** จำลอง CE voltage-divider amplifier ด้วย ngspice จริง
  (`.op`, `.ac`, `.tran`) ในหน้า `/simulator` โดยไม่แตะ `dc_bias.py` หรือ route เดิม

## โครงไฟล์และหน้าที่

| ไฟล์ | หน้าที่ |
|---|---|
| `dc_bias.py` | สมการ DC ต่อโหมด (`calculate_divider`/`calculate_fixed`/`calculate_emitter`), unit conversion, validation, จำแนก region — ไม่รู้จัก HTTP/HTML |
| `app.py` | Lab 03 routes เดิม + Lab 03/04 parse/format; dispatch `/simulate`; ประกอบผล SPICE กับ analytical reference |
| `spice_engine.py` | สร้าง netlist, หา ngspice (`NGSPICE_BIN` → PATH → common paths), อ่าน version, รัน process ใน temp dir, parse `.op`/`.ac`/`.tran`, ตรวจ log และ warning |
| `charts.py` | สร้าง Bode magnitude/phase และ transient SVG จากข้อมูลที่ parse แล้ว (ฝั่งเซิร์ฟเวอร์) |
| `templates/index.html` | Lab 03: ตัวเลือกโหมด (GET), ฟอร์มตามโหมด, SVG 3 แบบ, ตารางผลลัพธ์ |
| `templates/simulator.html` | Lab 04: ภาพวงจร CE, analysis tabs, provenance, เปรียบเทียบ SPICE/Analytical, กราฟ, netlist/log |
| `templates/mode_error.html` | หน้า HTTP 400 สำหรับโหมดไม่ถูกต้อง (Lab 03) |
| `static/style.css` | layout เดิม + simulator/responsive styles |
| `static/simulator.js` | เฉพาะ UI: ซ่อน/โชว์ฟิลด์ตาม analysis และสถานะ running — ไม่มี physics หรือ plotting |
| `tests/test_dc_bias.py` | เทสต์สมการและ validation เดิม (12 เทสต์) |
| `tests/test_web.py` | เทสต์ HTTP เดิมด้วย Flask test client (13 เทสต์) |

## เส้นทางการไหลของข้อมูล

### Lab 03 (คงเดิม)

```
Browser form (POST /calculate, hidden mode)
   → app.mode_from()         ไม่มี mode = divider; ว่าง/ผิด = 400
   → app.parse_inputs()      แปลง string → float, คูณตัวคูณหน่วย, ตรวจตามโหมด
   → dc_bias.calculate_*()   validate + สมการ + จำแนก region
   → app.format_result()     จัดรูปแบบหน่วย/ทศนิยม + mode/mode_label
   → templates/index.html    แสดงผล (Jinja)

GET /?mode=fixed → app.form_state(request.args) → render เฉพาะช่อง/ภาพของโหมดนั้น
```

### Lab 04 (เพิ่มใหม่แยก route)

```
GET /simulator
   → find_ngspice() / ngspice_version() → ป้าย engine พร้อม/ไม่พร้อม

POST /simulate
   → parse_sim_inputs()
       · analysis-aware required fields (dc: bias / ac: + RL,CIN,COUT / tran: + amp,freq)
       · ช่องที่ไม่ได้ใช้ของ analysis นั้นได้ default (ไม่ validate ข้อความค้างในช่องที่ซ่อน)
       · แปลง kΩ→Ω, µF→F, mV→V; ตรวจ finite, >0, 10 Hz≤f≤20 kHz, amp≤500 mV
   → CeParameters.validate()  (SI ทั้งหมด)
   → spice_engine.run_simulation()
       · build_netlist() → circuit.cir ใน TemporaryDirectory ใหม่ทุกครั้ง
       · ngspice_con -b -o run.log circuit.cir (timeout 30 s)
       · _check_log() + exit code + parse op log / ac.txt / tran.txt → dataclass
   → app.format_sim_result()
       · เรียก dc_bias.calculate_divider(β=100, VBE=0.70) เพื่อทำ analytical reference
       · จัดรูปแบบตัวเลข/หน่วย/region + provenance (engine, model, run_at, elapsed)
   → charts.* สร้าง SVG จาก parsed arrays เท่านั้น
   → templates/simulator.html แสดงผล
```

`dc_bias.py` ไม่ถูกแก้และไม่ถูกเรียกเพื่อสร้างผล SPICE — เรียกแค่เพื่อทำคอลัมน์เปรียบเทียบ

## สมการและปริมาณที่ใช้

### Lab 03 (คงเดิม)

Divider:

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

ร่วมทุกโหมด:

```
IC  = β·IB          IE = (β + 1)·IB
VC  = VCC − IC·RC   VCE = VC − VE
```

### Lab 04 ( ngspice เป็นคนคำนวณ )

แอปไม่ได้เขียน SPICE solver เอง; ngspice แก้สมการของ model card `Q2N3904`
(Gummel–Poon/Ebers–Moll ที่มี parasitic Cje/Cjc, VAF, TF/TR ฯลฯ)
ส่วนปริมาณที่แอปคำนวณต่อจากผลที่ parse ได้คือ

```
VCE        = VC − VE                         (V)
Gain(dB)   = 20·log10(|Vout/Vin|)             (dB)
Phase      = atan2(Im(Vout/Vin), Re(Vout/Vin)) (deg, แล้ว unwrap ให้ต่อเนื่อง)
−3 dB point= |Gain| = Gain_midband / √2       (Hz)
Amplitude  = (max − min) / 2                  (V → แสดง mV)
Correlation= Σ(Vin−m̄in)(Vout−m̄out) / √(Σ(Vin−m̄in)²·Σ(Vout−m̄out)²)
```

การจำแนก region ของ SPICE ใช้ `IC ≤ 1 nA → Cutoff`, `VCE ≤ 0.2 V → Saturation`,
นั่นคือ threshold เดียวกับ Lab 03 แต่คำนวณจากค่าที่ ngspice รายงาน

## วงจรอ้างอิงและ netlist

| โนด/อุปกรณ์ | ค่า | หมายเหตุ |
|---|---|---|
| VCC | 12 V | แหล่งจ่ายเดียว |
| R1 / R2 | 100 kΩ / 22 kΩ | ตัวแบ่งเบส (vcc–b / b–0) |
| RC / RE | 2.2 kΩ / 1 kΩ | RE ไม่มี bypass capacitor |
| CIN / COUT | 10 µF / 10 µF | input/output coupling |
| RL | 10 kΩ | ต่อจาก COUT ลงกราวด์ |
| Q1 | 2N3904 (`Q2N3904`) | model card คงที่, BF=416.4 |
| VIN | DC 0, AC 1, SIN(0 amp freq) | AC ใช้ small-signal 1 V; transient ใช้ amp/freq จากฟอร์ม |

คำสั่งวิเคราะห์ที่สร้างจริง:

```
.op                                      → print v(b) v(e) v(c) @q1[ic] @q1[ib] @q1[ie]
.ac dec 20 1 1G + wrdata ac.txt v(out) v(in)     → 181 จุด
.tran <step> <stop> + wrdata tran.txt v(in) v(out) → ~50 samples/cycle, settle 0.2 s แล้ว 5 รอบ
```

`step = max(1/(50f), 2 µs)`, `stop = max(0.2 s, 5/f)` — ทำให้เปลี่ยน frequency แล้วหน้าต่างเวลา/จำนวนจุดเปลี่ยนจริง

## การตรวจอินพุตและสถานะ

| กรณี | HTTP | สิ่งที่เกิดขึ้น | สิ่งที่ถูกปิดไม่ให้แสดง |
|---|---|---|---|
| ค่าผิด/ขาด/อยู่นอกช่วง | 400 | `Invalid input`, error รายฟิลด์ | ไม่เรียก ngspice, ไม่มี result/graph/netlist |
| ไม่พบ ngspice | 503 | `Simulation failed` + วิธีติดตั้ง | ไม่มี result/graph/netlist |
| ngspice exit ≠ 0 หรือ log มี Error/Fatal | 502 | `Simulation failed` + ข้อความจาก log | ไม่มี result/graph/netlist |
| exception อื่น | 500 | ข้อความภายใน + log ของเซิร์ฟเวอร์ | ไม่มี result/graph/netlist |
| สำเร็จ | 200 | `Simulation succeeded` + engine/model/run-at/elapsed + ผล/กราฟ/netlist/log | — |

JavaScript ตั้งสถานะ `กำลังรัน ngspice…` และปิด button ระหว่าง POST แต่ไม่ได้เป็นแหล่งของผลลัพธ์
ถ้า POST ล้มเหลว Jinja จะ render เฉพาะ error card ทำให้ผลรอบเก่าไม่ค้างอยู่บนหน้าใหม่

## การแยก provenance

- ทุกตัวเลข/กราฟในส่วน `SPICE (ngspice)`, `.ac`, `.tran` มาจาก output ของ ngspice ที่ parse เป็นตัวเลขจริง
- ตาราง `Analytical (Lab 03)` มาจาก `dc_bias.py` ด้วย β=100, VBE=0.70 V และมี note กำกับว่าไม่ใช่ผล ngspice
- Analytical ไม่ถูกใช้สร้างกราฟ Bode/transient และไม่ถูกใช้แทนค่าเมื่อ ngspice fail
- netlist และ run log ต้นฉบับถูกแนบไว้ให้ตรวจว่า engine ใด/model ใดถูกใช้จริง

## เหตุผลที่ให้ผู้ใช้เลือกหน่วย Ω / kΩ / MΩ และ µF / mV / Hz

ค่าตัวอย่างใน Lab เป็น kΩ และ µF แต่ netlist ต้องการ Ω/F/V/Hz
การแปลงหน่วยถูกทำใน `app.parse_sim_inputs` ก่อนส่งเข้า `CeParameters`
ทำให้ตรวจสอบได้จากโค้ดและจาก netlist ที่แสดงบนหน้าเว็บ แทนการให้ผู้ใช้เติมศูนย์เอง

## สิ่งที่ยังไม่ทำ (ขอบเขต Lab 04)

- Circuit editor อิสระ/เพิ่มหรือลบอุปกรณ์
- AC sweep สำหรับ Fixed/Emitter bias (มีเฉพาะ voltage-divider reference)
- FET/MOSFET, custom SPICE solver, animated overlay, deployment สู่ production

## ขอบเขตเดิมของ Lab 03 (ยังคงอยู่)

AC/Transient/Bode, SPICE solver, DC load line, interactive schematic,
JavaScript สำหรับคำนวณ, unittest ชุดใหม่, ระบบล็อกอิน และฐานข้อมูล
เป็นสิ่งที่ **ไม่ได้ทำใน Lab 03** แต่ AC/Transient/SPICE ถูกเพิ่มใน Lab 04 ตามที่ใบงานกำหนด
