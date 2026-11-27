# Monitor System — Requirements

## เป้าหมาย
เว็บ dashboard สำหรับทดสอบการ monitor ทรัพยากรของ notebook เครื่องนี้ (local machine) แบบ real-time
และเครื่องของตัวเองอื่น ๆ ที่รัน agent เดียวกัน (เช่น VPS Windows Server) ผ่าน cloud mode

## ผู้ใช้
- เจ้าของเครื่อง ดูได้ทั้งบน notebook เอง และจากเครื่องอื่น (เช่นมือถือ) ผ่าน internet
- ผู้ดูจากเครื่องอื่นต้อง login (magic link ทางอีเมล) และอีเมลต้องอยู่ใน allowlist

## Architecture (Hybrid)
- **Dashboard (frontend):** host บน GitHub Pages ที่ `https://<username>.github.io/<repo>/`
- **Local agent (backend):** Python รันบน notebook ที่ `http://127.0.0.1:<port>` คืนค่า metrics เป็น JSON
- บน notebook: dashboard ดึงข้อมูลจาก local agent โดยตรงทุก 2 s
- **Cloud mode (เครื่องอื่น):** agent ส่ง snapshot ล่าสุดขึ้น Supabase ทุก 5 s (เก็บแค่ค่าล่าสุด 1 แถวต่อเครื่อง
  ไม่เก็บประวัติ) dashboard บนเครื่องอื่นอ่านจาก Supabase หลัง login
  - เปิดเมื่อมี `SUPABASE_URL` + `SUPABASE_SECRET_KEY` ใน `.env` เท่านั้น ไม่มี = local only
  - ข้อมูลที่ขึ้น cloud: metrics ทั้งหมดรวมรายชื่อ process, ชื่อ CPU/OS, disk
  - หลายเครื่อง: แต่ละเครื่องตั้ง `DEVICE_ID` ไม่ซ้ำกัน; dashboard มีตัวเลือกเครื่อง
    ("อัตโนมัติ" = local agent ก่อน แล้วค่อยเครื่องแรกใน cloud)
  - Server ที่ไม่มีคน logon (VPS): agent เริ่มตอน boot ผ่าน Task Scheduler (`register-autostart-server.ps1`)
- ต้องเปิด agent ไว้ตอนใช้งาน ถ้า agent ไม่ทำงาน dashboard ต้องแสดงข้อความบอกชัดเจน
  (cloud mode: ข้อมูลเก่ากว่า 30 s = แสดงว่า notebook ออฟไลน์)
- Code ทั้งหมด backup ไว้ใน GitHub repo (public — จำเป็นสำหรับ GitHub Pages แบบฟรี)

## Metrics ที่ต้องแสดง
| หมวด | รายละเอียด |
|---|---|
| CPU | % การใช้งานรวม และราย core, clock ปัจจุบัน (GHz) |
| Memory | ใช้ไป / ทั้งหมด / %, swap |
| Disk usage | พื้นที่ใช้ไป / เหลือ ของแต่ละไดรฟ์ |
| Disk I/O | ความเร็วอ่าน/เขียน (MB/s) |
| Network | ความเร็ว upload/download ปัจจุบัน (KB/s, MB/s) |
| Internet speedtest | ทดสอบเมื่อกดปุ่มเท่านั้น (ไม่รันอัตโนมัติ) |
| Battery | % และสถานะการชาร์จ |
| Top processes | โปรแกรมที่ใช้ CPU / RAM สูงสุด (เช่น 10 อันดับ) |
| System info | OS, รุ่น CPU, uptime |

## พฤติกรรม
- อัปเดตอัตโนมัติทุก ~1–2 วินาที
- กราฟแสดงย้อนหลังไม่กี่นาที เก็บใน memory ของหน้าเว็บเท่านั้น
- อ่านข้อมูลอย่างเดียว ไม่แก้ไขอะไรในระบบ (ไม่ kill process ฯลฯ)

## Tech stack
- **Backend:** Python 3 + `psutil` (อ่านค่าระบบ ใช้ได้ทั้ง Windows/macOS)
- **Web server (agent):** stdlib `http.server`
- **Cloud:** Supabase (Postgres + Auth magic link); agent ใช้ `urllib` (ไม่มี dependency เพิ่ม),
  dashboard ใช้ supabase-js (vendored)
- **Frontend:** HTML/CSS/JavaScript ล้วน ไม่มี build step, deploy เป็น static files บน GitHub Pages
- **Platform:** ต้องรันได้บน Windows (หลัก) และ macOS

## ข้อกำหนดด้าน security
- Agent bind ที่ `127.0.0.1` เท่านั้น ไม่เปิดให้เครื่องอื่นในเครือข่ายเข้าถึง
- Agent อนุญาต CORS เฉพาะ origin ของ GitHub Pages ของเรา (และ localhost สำหรับ dev) — ป้องกันเว็บอื่นอ่านข้อมูลเครื่อง/รายชื่อ process
- รองรับ Private/Local Network Access ของ Chrome/Edge (preflight header ที่จำเป็น)
- Repo เป็น public: ห้ามมี secret, IP, hostname, อีเมลผู้ดู หรือข้อมูลเครื่องใน code/commit
- Supabase: Row Level Security เปิดทุกตาราง; อ่าน `device_metrics` ได้เฉพาะอีเมลใน `allowed_viewers`;
  client เขียนไม่ได้ (เขียนได้เฉพาะ agent ด้วย secret key ที่อยู่ใน `.env` บนเครื่องที่รัน agent เท่านั้น)
  - ความเสี่ยงที่ยอมรับ: secret key ข้าม RLS ได้ทั้งหมด ถ้าเครื่องใดที่มี key ถูกเจาะ (เช่น VPS) ข้อมูลใน project นี้ทั้งหมดจะถูกอ่าน/เขียนได้
- Publishable/anon key อยู่ใน `web/config.js` ได้ (เป็น public key โดยออกแบบ)
- Speedtest เป็นการเชื่อมต่อ server ภายนอก — ทำเฉพาะเมื่อผู้ใช้กดปุ่ม และไม่ส่งข้อมูลส่วนตัวใด ๆ

## Out of scope
- ไม่เก็บประวัติลงไฟล์หรือ database (cloud เก็บแค่ snapshot ล่าสุด)
- ไม่ monitor เครื่องที่ไม่ได้รัน agent นี้ (agentless, SNMP) / อุปกรณ์เครือข่าย
- ไม่มีระบบจัดการผู้ใช้ในหน้าเว็บ (เพิ่ม/ลบผู้ดูทำใน Supabase Dashboard)
- ไม่มีการแจ้งเตือน (LINE, Email ฯลฯ)
- ไม่มีการสั่งงานหรือแก้ไขระบบจาก dashboard
