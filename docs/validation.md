# Validation Record — BJT DC Bias Web App

บันทึกการตรวจผลลัพธ์ของเว็บกับการคำนวณอิสระ (คำนวณด้วยสมการโดยตรง ไม่ได้คัดลอกจากหน้าจอ)

## 1. เคสอ้างอิง (Reference case)

**ข้อมูลเข้า:** VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V

**ขั้นตอนคำนวณอิสระ**

1. `VTH = 12 × 22k / (100k + 22k) = 2.163934 V`
2. `RTH = 100k × 22k / (100k + 22k) = 18.032787 kΩ`
3. `IB = (2.163934 − 0.70) / (18.032787k + 101 × 1k) = 12.298581 µA`
4. `IC = 100 × IB = 1.229858 mA`
5. `IE = 101 × IB = 1.242157 mA`
6. `VE = IE × 1k = 1.242157 V`
7. `VB = VE + 0.70 = 1.942157 V`
8. `VC = 12 − IC × 2.2k = 9.294312 V`
9. `VCE = VC − VE = 8.052155 V`

**ผลเทียบค่าที่เว็บแสดง**

| ปริมาณ | คำนวณอิสระ | เว็บแสดง | ผลต่าง (%) |
|---|---|---|---|
| VTH | 2.163934 V | 2.164 V | +0.003 |
| RTH | 18.032787 kΩ | 18.03 kΩ | −0.015 |
| IB | 12.298581 µA | 12.30 µA | +0.012 |
| IC | 1.229858 mA | 1.230 mA | +0.012 |
| IE | 1.242157 mA | 1.242 mA | −0.013 |
| VE | 1.242157 V | 1.242 V | −0.013 |
| VB | 1.942157 V | 1.942 V | −0.008 |
| VC | 9.294312 V | 9.294 V | −0.003 |
| VCE | 8.052155 V | 8.052 V | −0.002 |

ผลต่างทั้งหมด < 0.02 % และมาจากการปัดเศษทศนิยมที่ใช้แสดงผลเท่านั้น
Region ที่เว็บรายงาน: **Active** (VCE = 8.05 V > 0.2 V) — threshold ของ Lab 03 คือ VCE ≤ 0.2 V

## 2. เคส Cutoff

**ข้อมูลเข้า:** เหมือนข้อ 1 แต่ R2 = 1 kΩ

| ปริมาณ | คำนวณอิสระ | เว็บแสดง |
|---|---|---|
| VTH | `12 × 1k / 101k = 0.118812 V` | 0.119 V |
| VB | 0.118812 V (ตัวแบ่งแรงดันขณะไม่มีโหลด) | 0.119 V |
| IB, IC, IE | 0 A (VTH ≤ VBE) | 0.00 µA / 0.000 mA / 0.000 mA |
| VE | 0 V | 0.000 V |
| VC, VCE | 12 V | 12.000 V |
| Region | Cutoff | **Cutoff** + warning "IB ≈ 0 และแบบจำลอง Forward-Active ใช้ไม่ได้" |

## 3. เคส Saturation

**ข้อมูลเข้า:** เหมือนข้อ 1 แต่ RC = 20 kΩ

| ปริมาณ | คำนวณอิสระ | เว็บแสดง |
|---|---|---|
| VTH, RTH, IB, IC, IE, VE, VB | เท่ากับข้อ 1 | 2.164 V / 18.03 kΩ / 12.30 µA / 1.230 mA / 1.242 mA / 1.242 V / 1.942 V |
| VC | `12 − 1.229858m × 20k = −12.597 V` | −12.597 V |
| VCE | `−12.597 − 1.242157 = −13.839 V` | −13.839 V |
| Region | VCE ≤ 0.2 V → Saturation | **Saturation** + warning |

VC ที่ติดลบเป็นสัญญาณว่าแบบจำลอง Forward-Active ใช้ไม่ได้จริง (กระแส collector ที่คำนวณได้
ทำให้แรงดันตกคร่อม RC เกิน VCC) เว็บจึงต้องเตือนและไม่รายงานว่าเป็นผลที่เชื่อถือได้

## 4. การตรวจ Validation

| อินพุต | ผลที่คาดหวัง | ผลจริง |
|---|---|---|
| R1 = 0 | HTTP 400 + "ค่าความต้านทานต้องมากกว่า 0 Ω" | ตรง |
| β = 0 | HTTP 400 + "β ต้องมากกว่า 0" | ตรง |
| VCC = "abc" | HTTP 400 + "กรุณากรอกตัวเลข" | ตรง |
| ฟอร์มว่าง | HTTP 400 + error ครบทุกช่อง ไม่ crash | ตรง |
| unit_r1 = "megohm" | HTTP 400 + "หน่วยไม่ถูกต้อง" | ตรง |
| VBE = 12 V (= VCC) | HTTP 400 + "VBE ต้องอยู่ระหว่าง 0 ถึง VCC" | ตรง |

## 5. สรุป

- ผลจากเว็บตรงกับการคำนวณอิสระภายในความละเอียดที่แสดง
- ทั้ง Cutoff และ Saturation มี warning ตามที่ออกแบบ
- ไม่มีกรณีอินพุตผิดที่ทำให้หน้าเว็บล้ม (ทุกกรณีที่ทดสอบได้ HTTP 400 พร้อมข้อความ)

## 6. Lab 03 — ตารางตรวจ A1–A5 (browser acceptance)

**วิธีตรวจ:** OpenCode Browser (Chromium ในแอป OpenCode) — เปิด `http://127.0.0.1:5000/`,
เลือกโหมด, กรอกฟอร์มจริงด้วย `fill` และส่งฟอร์มด้วยปุ่ม/Enter, อ่านข้อความจากหน้าเว็บ
และดู HTTP status จาก network log ของแท็บ เครื่องนี้ยังไม่มี Node.js/npx จึงไม่ได้ใช้
Playwright MCP (ใบงานอนุญาตให้ใช้วิธีตรวจผ่าน browser อื่นได้ และให้คะแนนเท่ากัน)
ค่าด้านล่างคำนวณอิสระจากสมการ ไม่ได้คัดลอกจากหน้าเว็บ

| เคส | โหมด / อินพุต | IC คาดหมาย | IC ที่เห็น | VCE คาดหมาย | VCE ที่เห็น | สถานะ | หลักฐาน |
|---|---|---|---|---|---|---|---|
| A1 | Divider: VCC 12 V, R1 100 kΩ, R2 22 kΩ, RC 2.2 kΩ, RE 1 kΩ, β 100, VBE 0.70 V | 1.229858 mA | 1.230 mA | 8.052155 V | 8.052 V | ผ่าน | ผลขึ้น "ผลการคำนวณ — Voltage Divider Bias", Active |
| A2 | Fixed: VCC 12 V, RB 1 MΩ (1000 kΩ), RC 2.2 kΩ, β 100, VBE 0.70 V | 1.130000 mA | 1.130 mA | 9.514000 V | 9.514 V | ผ่าน | ผลขึ้น "ผลการคำนวณ — Fixed Bias", ไม่มี VTH/RTH |
| A3 | Emitter: VCC 12 V, RB 1 MΩ, RC 2.2 kΩ, RE 1 kΩ, β 100, VBE 0.70 V | 1.026340 mA | 1.026 mA | 8.705450 V | 8.705 V | ผ่าน | ผลขึ้น "ผลการคำนวณ — Emitter Bias" |
| A4 | Emitter: เหมือน A3 แต่เปลี่ยน **RE = 2 kΩ** (ค่าอื่นคงเดิม) | 0.940100 mA | 0.940 mA | 8.032779 V | 8.033 V | ผ่าน | [ภาพหน้าจอ](evidence/a4-emitter-bias.jpg) |
| A5 | Fixed: RB = 0 (ค่าอื่นคงเดิม) | HTTP 400 + แจ้งแก้ RB | HTTP **400**, ข้อความ "RB: ค่าความต้านทานต้องมากกว่า 0 Ω", ไม่มีผลเก่าค้าง | — | — | ผ่าน | [ภาพหน้าจอ](evidence/a5-fixed-rb-zero.jpg) |

ความคลาดเคลื่อนที่เห็นเกิดจากการปัดแสดงผล 3 ตำแหน่งทศนิยม (IC ±0.01 mA, VCE ±0.02 V ตามเกณฑ์ใบงาน)

### การคำนวณอิสระสำหรับโหมดใหม่

- **Fixed (A2):** `IB = (12 − 0.70)/1 MΩ = 11.30 µA`, `IC = 100 × IB = 1.130 mA`,
  `VE = 0 V`, `VB = 0.70 V`, `VC = 12 − 1.130m × 2.2k = 9.514 V`, `VCE = 9.514 V`
- **Emitter (A3):** `IB = (12 − 0.70)/(1 MΩ + 101 × 1 kΩ) = 10.2634 µA`,
  `IC = 1.026340 mA`, `IE = 101 × IB = 1.036603 mA`, `VE = IE × 1 kΩ = 1.036603 V`,
  `VB = 1.736603 V`, `VC = 9.742053 V`, `VCE = 8.705450 V`
- **Emitter (A4):** `IB = 11.30/(1 MΩ + 101 × 2 kΩ) = 9.40100 µA`,
  `IC = 0.940100 mA`, `IE = 0.949501 mA`, `VE = 1.899002 V`,
  `VC = 9.931780 V`, `VCE = 8.032779 V`
- **A4 เทียบ A3:** IC ลดลง `1.026340 − 0.940100 = 0.086240 mA` เมื่อเพิ่ม RE จาก 1 kΩ เป็น 2 kΩ
  (สอดคล้องกับสมการ: RE เพิ่ม → ตัวหาร IB เพิ่ม → IB/IC ลดลง)

### การตรวจเพิ่มเติมผ่านเบราว์เซอร์

| รายการ | ผลจริง |
|---|---|
| เปลี่ยนโหมดด้วย dropdown แล้วกด "เปลี่ยนโหมด"/Enter | URL เปลี่ยนเป็น `/?mode=...` และช่องฟอร์ม/แผนภาพเปลี่ยนตามโหมด |
| โหมด Divider แสดงเฉพาะ R1, R2, RC, RE | ตรง; Fixed แสดง RB, RC เท่านั้น; Emitter แสดง RB, RC, RE |
| ผล/ข้อความ error ระบุโหมดที่เลือก | ตรง ("Voltage Divider Bias" / "Fixed Bias" / "Emitter Bias") |
| A5 ไม่แสดงผลของ A4 ค้างอยู่ | ตรง — ไม่มี result card และมี error อยู่ข้างช่อง RB |
| โหมดไม่รู้จัก `?mode=banana` | HTTP 400, หน้า error ขนาดเล็ก ไม่มีฟอร์มคำนวณและไม่มีแผนภาพ |
| `nan`, `inf`, `1e999`, 0, ค่าลบ ในช่องของโหมดใหม่ | HTTP 400 พร้อมข้อความรายฟิลด์ ไม่มี 500 และไม่มี `nan` บนหน้าจอ |
| RB 1000 kΩ เทียบ 1 MΩ ในโหมด Fixed | ผล IC/VCE เท่ากันทุกหลักที่แสดง |

---

## 7. Lab 04 — CE Amplifier Simulator (B1–B8)

**เครื่องมือที่ใช้จริง:** OpenCode Browser (Chromium ในแอป OpenCode) สำหรับ B1–B7 และ desktop B8;
headless Chrome + `puppeteer-core` ตั้ง viewport 390×844 สำหรับ phone B8 เท่านั้น
(Playwright MCP ยังไม่ได้ configure แม้เครื่องจะมี Node.js 26.13.1 แล้ว)
engine ที่รันจริงคือ **`ngspice-47`** ที่
`C:\Users\book1\AppData\Local\ngspice\Spice64\bin\ngspice_con.exe`
model card คงที่ `Q2N3904` (BF = 416.4) ไม่มีการ mock ผลลัพธ์

### 7.1 ข้อมูลอ้างอิงและการแปลงหน่วยที่ตรวจได้จาก netlist

| พารามิเตอร์ | ค่าที่กรอก | ค่าใน netlist | หมายเหตุ |
|---|---|---|---|
| VCC | 12 V | `12` | V |
| R1, R2 | 100 kΩ, 22 kΩ | `100000`, `22000` | kΩ → Ω |
| RC, RE | 2.2 kΩ, 1 kΩ | `2200`, `1000` | kΩ → Ω |
| RL | 10 kΩ | `10000` | kΩ → Ω |
| CIN, COUT | 10 µF, 10 µF | `1e-05`, `1e-05` | µF → F |
| Amplitude | 10 mV peak | `0.01` | mV → V, ใช้เฉพาะ `.tran` |
| Frequency | 1000 Hz | `1000` | ใช้เฉพาะ `.tran`; 10 Hz–20 kHz |
| AC source | 1 V (small-signal) | `AC 1` | ไม่ใช่ amplitude จากฟอร์ม |

### 7.2 ตรวจสมการ/หน่วย/ผลอิสระ (ไม่ได้คัดลอกจากหน้าเว็บ)

- **DC analytical ยังตรงกับข้อ 1 เดิมทุกหลัก** (`dc_bias.py` ไม่ถูกแก้):
  VB 1.942157 V, VE 1.242157 V, VC 9.294312 V, VCE 8.052155 V, IC 1.229858 mA
- **SPICE ต่างจาก analytical อย่างมีเหตุผล:** model ใช้ BF = 416.4 และ VBE เกิดจาก model
  (ไม่ใช่ 0.70 V คงที่) จึงได้ IB 8.89 µA ต่ำกว่า 12.30 µA (−27.7%) และ IC สูงกว่า +7.7%
  ไม่ใช่ bug ของการแปลงหน่วย
- **Small-signal sanity check ที่ RE = 1 kΩ** (ที่ ~300 K, `V_T ≈ 25.85 mV`):
  `g_m = IC/V_T ≈ 1.324 mA / 25.85 mV = 51.2 mS`,
  `r_e = V_T/IE ≈ 25.85 mV / 1.333 mA = 19.4 Ω`,
  `RC ∥ RL = 2.2k ∥ 10k = 1.803 kΩ`
  `|Av| ≈ (RC ∥ RL)/(RE + r_e) = 1803/(1000+19.4) ≈ 1.77 V/V`
  เทียบกับผลจริง 1.756 V/V @ 1 kHz (ต่าง ~0.8% สอดคล้องกับการประมาณ `r_e`)
- **อิมพีแดนซ์ขาเข้า:** `r_π = BF/g_m ≈ 8.13 kΩ`,
  `R1 ∥ R2 = 18.03 kΩ`, `r_π + (BF+1)RE ≈ 425 kΩ`
  → `R_in ≈ 17.3 kΩ`; กับ CIN 10 µF ให้ cutoff ประมาณ 0.9 Hz และ COUT ให้ ~1.3 Hz
  รวมกันใกล้ค่าที่ ngspice รายงาน **≈ 2 Hz** (การประมาณแยก capacitor ไม่ได้ผลรวม exact)
- **Phase:** ที่ 1 kHz ได้ −179.9° และ transient correlation −0.99999746 → CE กลับเฟส 180° จริง
- **Transient gain:** `17.553 mV / 9.996 mV = 1.756` ตรงกับ gain จาก `.ac` ที่ 1 kHz
- **หน่วยของกราฟ:** แกนความถี่เป็น Hz (ลอการิทึม), gain เป็น dB/V·V⁻¹, phase เป็นองศา,
  time เป็น ms, voltage เป็น mV — อ่านจาก label ใน SVG ไม่ใช่เดาจากสีเส้น

### 7.3 ตารางผล B1–B8

| เคส | การกระทำ / อินพุต | สิ่งที่คาดหวัง | สิ่งที่เห็นจริง | สถานะ | หลักฐาน |
|---|---|---|---|---|---|
| **B1** | เปิด `/` เลือก Divider / Fixed / Emitter แล้วกดคำนวณชุด Lab 03 | ผลเดิมไม่เปลี่ยน, สลับโหมดได้ | Divider: VB 1.942 V, VE 1.242 V, VC 9.294 V, VCE 8.052 V, IC 1.230 mA, VTH 2.164 V, RTH 18.03 kΩ · Fixed: IC 1.130 mA, VCE 9.514 V · Emitter: IC 1.026 mA, VCE 8.705 V · Active ทั้ง 3 | ผ่าน | [divider](evidence/b1-divider.jpg) · [fixed](evidence/b1-fixed.jpg) · [emitter](evidence/b1-emitter.jpg) |
| **B2** | `/simulator` → CE Reference → Run DC | ผล `.op` จาก ngspice + engine/model/status | Status `Simulation succeeded — DC Operating Point (.op) ngspice`; Engine `ngspice-47`; Model `2N3904 (Q2N3904)`; region Active; VB 2.004 V, VE 1.333 V, VC 9.087 V, VCE 7.754 V, IC 1.324 mA, IB 8.89 µA, IE 1.333 mA | ผ่าน | [b2-dc.jpg](evidence/b2-dc.jpg) |
| **B3** | เปลี่ยน RE 1 → 2 kΩ แล้วรัน DC และ AC | operating point **และ** gain ต้องเปลี่ยน ไม่ใช่ค่าค้าง | DC: IC 1.324 → 0.705 mA, VCE 7.754 → 9.032 V, IB 8.89 → 5.06 µA · AC: gain @1 kHz 1.756 → 0.879 V/V, midband 1.756 → 1.073; ขึ้น warning “ไม่พบจุดตัด -3 dB ด้านความถี่สูงในช่วง 1 Hz – 1e+09 Hz” | ผ่าน | [DC](evidence/b3-re2.jpg) · [AC](evidence/b3-re2-ac.jpg) |
| **B4** | เลือก AC → Run | Bode magnitude/phase มีแกน/หน่วย/ค่าจริง | 2 SVG (`Bode magnitude`, `Bode phase`); แกน 1–1G Hz, gain dB, phase deg; 181 จุด; midband 1.756 V/V (4.89 dB) @ 8.91 kHz; gain @1 kHz 1.756 / −179.9°; cutoff ≈ 2 Hz / 141 MHz; มีเส้น 1 kHz, −3 dB, −180° | ผ่าน | [b4-ac.jpg](evidence/b4-ac.jpg) |
| **B5** | เลือก Transient, 10 mV peak / 1 kHz → Run | เห็น Vin/Vout ตามเวลา มีหน่วยเวลา/แรงดัน และกลับเฟส | 251 จุด, หน้าต่าง 195.01–200.00 ms, แกน Time (ms)/Voltage (mV); Vin 10.00 mV peak, Vout 17.55 mV peak, gain 1.756, phase `กลับเฟส 180°`, correlation −1.0000 | ผ่าน | [b5-tran.jpg](evidence/b5-tran.jpg) |
| **B6** | เปลี่ยนเป็น 20 mV peak / 2 kHz แล้วรันใหม่ | waveform/หน้าต่างเวลาเปลี่ยน ไม่ hard-code | Vin 19.99 mV, Vout 35.10 mV, หน้าต่าง 197.50–200.00 ms, tick แกนเวลา 197.5–200 ms; gain ยัง 1.756 ตามทฤษฎี small-signal; ไม่มีค่าจาก B5 ค้าง | ผ่าน | [b6-source.jpg](evidence/b6-source.jpg) |
| **B7** | ตั้ง RE = 0 แล้ว Run | แจ้ง error, ไม่ success ปลอม, ไม่มีกราฟ/ผลเก่า | HTTP **400**, banner `Invalid input — ยังไม่มีการเรียก ngspice`, error `RE: ค่าต้องมากกว่า 0`, ไม่มี `Simulation succeeded`, ไม่มี SVG, ไม่มี details netlist | ผ่าน | [b7-invalid.jpg](evidence/b7-invalid.jpg) |
| **B8** | เปิด `/simulator` บน desktop และ viewport 390×844 แล้วรัน AC | อ่านง่าย ไม่มีเนื้อหาสำคัญถูกตัด | desktop: ฟอร์ม/ผล 2 คอลัมน์, กราฟ 2 อัน แสดงครบ · phone: `innerWidth = 390`, `scrollWidth = 390` (ไม่มี horizontal overflow), 2 กราฟและ status success ยังอ่านได้ | ผ่าน | [desktop](evidence/b8-desktop.jpg) · [phone](evidence/b8-phone.png) |

### 7.4 ตรวจเส้นทาง error เพิ่มเติม (Flask test client)

| กรณี | วิธีจำลอง | HTTP | ผลจริง |
|---|---|---|---|
| engine หาย | monkeypatch ทั้ง `app.find_ngspice` และ `spice_engine.find_ngspice` ให้คืน `None` | **503** | ข้อความ `ngspice ไม่พร้อมใช้งาน`, badge `ไม่พบ ngspice`, ไม่มี success/กราฟ/netlist |
| ngspice ล้มเหลว | monkeypatch `run_simulation` ให้ยื่น `SimulationError` | **502** | ข้อความ `ngspice รายงานข้อผิดพลาด`, ไม่มี success/กราฟ |
| อินพุตผิด | RE = 0, VCC = `abc`, frequency = 5 Hz, amplitude = 600 mV | **400** | error รายฟิลด์, ไม่เรียก ngspice, ไม่มี success/กราฟ |

### 7.5 เปรียบเทียบ SPICE กับ Analytical (RE = 1 kΩ)

| ปริมาณ | SPICE (ngspice) | Analytical (Lab 03) | Δ | Δ% |
|---|---|---|---|---|
| VB | 2.004 V | 1.942 V | +0.062 V | +3.2% |
| VE | 1.333 V | 1.242 V | +0.091 V | +7.3% |
| VC | 9.087 V | 9.294 V | −0.207 V | −2.2% |
| VCE | 7.754 V | 8.052 V | −0.298 V | −3.7% |
| IC | 1.324 mA | 1.230 mA | +0.094 mA | +7.7% |
| IB | 8.89 µA | 12.30 µA | −3.41 µA | −27.7% |
| IE | 1.333 mA | 1.242 mA | +0.091 mA | +7.3% |

ความต่างมาจากสมมติฐานของแบบจำลอง (BF จริง 416.4 เทียบ β=100 ที่กำหนดเองใน Lab 03)
ไม่ใช่จากการปัดเศษ; หน้าเว็บระบุชัดว่า analytical เป็น reference และไม่ใช้สร้างกราฟ

### 7.6 บันทึกการตรวจโดย AI และการอนุมัติโดยนิสิต

- **AI ทำ:** เขียนโค้ด/กราฟ/เอกสาร, รัน unittest 25 เทสต์, เรียก ngspice-47 จริง,
  อ่านค่าจาก output, เก็บ screenshot ผ่าน browser tool และทดสอบ HTTP 400/503/502
- **AI ไม่ได้ทำ:** แต่งตัวเลข SPICE, แต่งภาพหน้าจอ, หรือใช้ analytical แทนผลที่ engine ล้มเหลว
- **นิสิตต้องตรวจเองก่อนส่ง:** สมการในข้อ 7.2, หน่วยในข้อ 7.1, ตาราง B1–B8,
  netlist/run log ที่แนบในหน้าเว็บ และยืนยันว่าเข้าใจความต่าง SPICE vs Analytical
- **สถานะการอนุมัติ:** ผู้ให้งานตรวจ equations/units/results และภาพ B1–B8 แล้ว
  อนุมัติให้ commit/push เมื่อ **24/11/2026**
- **Commit SHA ของงาน Lab 04:** ดูจากรายงานการส่งงานหรือ `git log -1` หลัง push
  (เป็น SHA ของ commit ที่บรรจุโค้ด กราฟ เอกสาร และหลักฐานชุดนี้)
