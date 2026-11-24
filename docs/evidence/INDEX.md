# หลักฐานภาพหน้าจอ Lab 04 — แยกตามเคส B1–B8

รันตรวจรับใหม่บนเว็บที่เปิดอยู่เมื่อ **24/11/2026**

- **เครื่องมือ:** OpenCode Browser (Chromium ในแอป OpenCode) สำหรับ B1–B7 และ desktop B8;
  headless Chrome + `puppeteer-core` ตั้ง viewport 390×844 สำหรับ phone B8
- **Engine:** ngspice-47 · **Model:** 2N3904 (`Q2N3904`, BF=416.4)
- **วิธีรัน:** เปิด `/` หรือ `/simulator`, กรอก/เลือกค่าจริงในฟอร์ม, กดปุ่มส่งฟอร์ม,
  อ่านข้อความบนหน้าเว็บ แล้วจึงแคปหน้าจอ (ไม่ได้ตัดต่อภาพหรือแต่งตัวเลข)
- รายละเอียดการคำนวณอิสระและเกณฑ์อยู่ใน [`../validation.md`](../validation.md) ข้อ 7

## รายการไฟล์แยกตามข้อ

| ข้อ | ไฟล์ภาพ | สิ่งที่เห็นในภาพ | ผล |
|---|---|---|---|
| **B1** | [`b1-divider.jpg`](b1-divider.jpg) | Lab 03 Divider — IC 1.230 mA, VCE 8.052 V, VTH 2.164 V, RTH 18.03 kΩ, Active | PASS |
| **B1** | [`b1-fixed.jpg`](b1-fixed.jpg) | Lab 03 Fixed — IC 1.130 mA, VCE 9.514 V, Active | PASS |
| **B1** | [`b1-emitter.jpg`](b1-emitter.jpg) | Lab 03 Emitter — IC 1.026 mA, VCE 8.705 V, Active | PASS |
| **B2** | [`b2-dc.jpg`](b2-dc.jpg) | Run DC `.op` — status `Simulation succeeded`, Engine `ngspice-47`, Model `2N3904 (Q2N3904)`, VB 2.004 V · VE 1.333 V · VC 9.087 V · VCE 7.754 V · IC 1.324 mA · IB 8.89 µA · IE 1.333 mA, ตารางเทียบ Analytical | PASS |
| **B3** | [`b3-re2.jpg`](b3-re2.jpg) | เปลี่ยน RE = 2 kΩ แล้วรัน DC — IC 1.324 → 0.705 mA, VCE 7.754 → 9.032 V, IB 8.89 → 5.06 µA (ไม่ใช่ค่าค้าง) | PASS |
| **B3** | [`b3-re2-ac.jpg`](b3-re2-ac.jpg) | RE = 2 kΩ แล้วรัน AC — gain @1 kHz 1.756 → 0.879 V/V, midband 1.073, low cutoff 3.16 Hz, มี warning หา high cutoff ไม่พบ | PASS |
| **B4** | [`b4-ac.jpg`](b4-ac.jpg) | AC Bode — 2 กราฟ (magnitude/phase), แกน Hz/dB/องศา, 181 จุด, gain @1 kHz 1.756 V/V (4.89 dB), phase −179.9°, cutoff ≈2 Hz / 141 MHz | PASS |
| **B5** | [`b5-tran.jpg`](b5-tran.jpg) | Transient 10 mV/1 kHz — 251 จุด, 195.01–200.00 ms, Vin 10.00 mV, Vout 17.55 mV, gain 1.756, correlation −1.0000, กลับเฟส 180° | PASS |
| **B6** | [`b6-source.jpg`](b6-source.jpg) | เปลี่ยนเป็น 20 mV/2 kHz — Vin 19.99 mV, Vout 35.10 mV, หน้าต่าง 197.50–200.00 ms, tick แกนเวลาเปลี่ยน ไม่ hard-code | PASS |
| **B7** | [`b7-invalid.jpg`](b7-invalid.jpg) | ตั้ง RE = 0 แล้ว Run — `Invalid input · ยังไม่มีการเรียก ngspice`, error `RE: ค่าต้องมากกว่า 0`, ไม่มี success/กราฟ/netlist | PASS |
| **B8** | [`b8-desktop.jpg`](b8-desktop.jpg) | Desktop: ฟอร์ม + ผล 2 คอลัมน์, กราฟ AC 2 อัน แสดงครบ, status success | PASS |
| **B8** | [`b8-phone.png`](b8-phone.png) | Phone 390×844: `innerWidth = 390`, `scrollWidth = 390` (ไม่มี horizontal overflow), กราฟ 2 อันยังอ่านได้ | PASS |

## ไฟล์เพิ่มเติมจาก Lab 03

| เคส | ไฟล์ | สิ่งที่เห็น |
|---|---|---|
| A4 | [`a4-emitter-bias.jpg`](a4-emitter-bias.jpg) | Emitter bias เปลี่ยน RE = 2 kΩ → IC 0.940 mA, VCE 8.033 V |
| A5 | [`a5-fixed-rb-zero.jpg`](a5-fixed-rb-zero.jpg) | Fixed bias RB = 0 → HTTP 400 + แจ้งแก้ RB |

ทุกไฟล์เป็นภาพที่ได้จาก browser tool จริง (full-page capture) ไม่ใช่ภาพที่วาดหรือสร้างขึ้นใหม่
