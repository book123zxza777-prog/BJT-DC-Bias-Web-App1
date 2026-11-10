# Pre-flight Checklist — ENG29 2121 Lab 02 (ตรวจเมื่อ 10 พ.ย. 2569)

อ้างอิง: Lab 02 HTML ข้อ 2.4 Checklist ก่อนเริ่มทำงานจริง

## 1. Toolchain

| # | รายการ | คำสั่งตรวจ | ผล | สถานะ |
|---|--------|-----------|-----|--------|
| 1 | Git | `git --version` | 2.56.0.windows.4 (`C:\Users\B6807924\AppData\Local\Programs\Git\cmd\git.exe`) | ✅ |
| 2 | Git identity | `git config --global user.name / user.email` | `Book` / `book123zxza777@gmail.com` | ✅ |
| 3 | Credential helper | `git config --get credential.helper` | `manager` (Git Credential Manager) | ✅ |
| 4 | GitHub Desktop | เปิดแอป / About | v3.6.10 (`C:\Users\B6807924\AppData\Local\GitHubDesktop`) | ⚠️ ติดตั้งแล้ว แต่ **ยังไม่ล็อกอิน** |
| 5 | GitHub network | `https://api.github.com` | HTTP 200 | ✅ |
| 6 | OpenCode Desktop | About / ส่งข้อความ | v2.2.6 | ✅ |
| 7 | Superpowers plugin | `GET /api/plugin` | `superpowers` state = active (commit 22f0b46) | ✅ |
| 8 | Superpowers skills | `GET /api/skill` | 15 skills (brainstorming, writing-plans, ...) | ✅ |
| 9 | Python | `python --version` | 3.15.2 (`...\Programs\Python\Python315\python.exe`) | ✅ (แก้ PATH แล้ว) |
| 10 | pip | `python -m pip --version` | 26.2.2 | ✅ |
| 11 | venv | `python -c "import venv"` | OK | ✅ |
| 12 | Flask | `python -c "import flask"` | ยังไม่ติดตั้ง (ต้องสร้าง venv ก่อน) | ⏳ รอสร้างโปรเจกต์ |
| 13 | Repository | `git status` ในโฟลเดอร์งาน | `git init -b main` แล้วที่ `C:\Users\B6807924\Documents\Default Project` | ✅ (ยังไม่มี commit แรก) |

## 2. สิ่งที่แก้ไประหว่างตรวจ
- **PATH ของ Python**: เดิม `python` ชี้ไปที่ Microsoft Store alias (ขึ้น error) ใช้งานได้แค่ `py`
  → เพิ่ม `...\Programs\Python\Python315` และ `...\Scripts` ไว้หน้าสุดของ User PATH
  → ตอนนี้ `python` และ `python -m pip` ใช้ได้ตามคำสั่งในเอกสาร Lab
- **Repository**: เริ่ม repo ใหม่ที่ branch `main` พร้อม `.gitignore` (Python/Flask/secrets) และ `README.md` ตั้งต้น
  → รอ commit แรกผ่าน GitHub Desktop (ยังไม่ล็อกอิน GitHub Desktop)

## 3. Checklist รับงาน (กรอกก่อนจบ Lab)

- [ ] เปิดเว็บผ่าน `http://127.0.0.1:5000/` ได้ (HTTP 200)
- [ ] กรอก VCC, R1, R2, RC, RE, β, VBE แล้วกด Calculate ได้ผลจาก Python จริง
- [ ] ผลตรงกับการคำนวณอิสระ (VTH, RTH, IB, IC, IE, VE, VB, VC, VCE)
- [ ] กรอกค่าผิด (R≤0, β≤0, ตัวอักษร) แล้วขึ้น Error ไม่พัง
- [ ] นอก Active Region ขึ้น Warning
- [ ] `python -m unittest discover -s tests -v` ผ่านทั้งหมด (≥3 engineering + ≥1 Flask client)
- [ ] Commit/Push ผ่าน GitHub Desktop สำเร็จ เห็น commit SHA
- [ ] README อธิบายวิธีติดตั้ง/รัน/ทดสอบได้จริง
- [ ] ไม่มี `.venv/`, `.env`, API key ถูก commit

## 4. Workflow commit ด้วย GitHub Desktop

1. เปิด GitHub Desktop → **Sign in to GitHub.com** (ทำครั้งเดียว)
2. **File → Add Local Repository** (ถ้ามีโฟลเดอร์อยู่แล้ว) หรือ **File → Clone repository**
   - ถ้ายังไม่มี repo: สร้างโฟลเดอร์โปรเจกต์ → `git init -b main` → แล้ว Add Local Repository
3. ทำงานกับไฟล์ในโปรเจกต์ (ให้ Agent เขียนโค้ดในโฟลเดอร์นี้)
4. เปิด GitHub Desktop → แท็บ **Changes**
   - ตรวจรายการไฟล์ซ้ายมือ (ต้องไม่มี `.venv/`, `__pycache__/`, `.env`)
   - คลิกไฟล์เพื่อดู diff ทีละไฟล์ (แทน `git diff --staged`)
5. ช่อง **Summary** ใส่ commit message เช่น `feat: add voltage divider DC bias calculation`
   ช่อง Description ใส่รายละเอียด/เหตุผลได้
6. กด **Commit to main**
7. กด **Publish repository** (ครั้งแรก, เลือก Private/Public) หรือ **Push origin** (ครั้งต่อไป)
8. คัดลอก commit SHA จากแถบล่าง (คลิกขวา → Copy SHA) ไปส่งใน Moodle
