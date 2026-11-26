# Monitor System — Requirements

## เป้าหมาย
เว็บ dashboard สำหรับทดสอบการ monitor ทรัพยากรของ notebook เครื่องนี้ (local machine) แบบ real-time

## ผู้ใช้
- ใช้คนเดียว บนเครื่องตัวเอง

## Architecture (Hybrid)
- **Dashboard (frontend):** host บน GitHub Pages ที่ `https://<username>.github.io/<repo>/`
- **Local agent (backend):** Python รันบน notebook ที่ `http://127.0.0.1:<port>` คืนค่า metrics เป็น JSON
- หน้า dashboard ดึงข้อมูลจาก local agent ผ่าน browser — ข้อมูลเครื่องไม่ถูกส่งขึ้น GitHub หรือ server ใด
- ต้องเปิด agent ไว้ตอนใช้งาน ถ้า agent ไม่ทำงาน dashboard ต้องแสดงข้อความบอกชัดเจน
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
- **Web server (agent):** ตัดสินใจตอนเริ่ม implement (stdlib `http.server` vs FastAPI) — ดู STATUS.md
- **Frontend:** HTML/CSS/JavaScript ล้วน ไม่มี build step, deploy เป็น static files บน GitHub Pages
- **Platform:** ต้องรันได้บน Windows (หลัก) และ macOS

## ข้อกำหนดด้าน security
- Agent bind ที่ `127.0.0.1` เท่านั้น ไม่เปิดให้เครื่องอื่นในเครือข่ายเข้าถึง
- Agent อนุญาต CORS เฉพาะ origin ของ GitHub Pages ของเรา (และ localhost สำหรับ dev) — ป้องกันเว็บอื่นอ่านข้อมูลเครื่อง/รายชื่อ process
- รองรับ Private/Local Network Access ของ Chrome/Edge (preflight header ที่จำเป็น)
- Repo เป็น public: ห้ามมี secret, IP, hostname หรือข้อมูลเครื่องใน code/commit
- Speedtest เป็นการเชื่อมต่อ server ภายนอก — ทำเฉพาะเมื่อผู้ใช้กดปุ่ม และไม่ส่งข้อมูลส่วนตัวใด ๆ

## Out of scope
- ไม่เก็บประวัติลงไฟล์หรือ database
- ไม่ monitor เครื่องอื่น / อุปกรณ์เครือข่าย
- ไม่มีระบบ login / ผู้ใช้หลายคน
- ไม่มีการแจ้งเตือน (LINE, Email ฯลฯ)
- ไม่มีการสั่งงานหรือแก้ไขระบบจาก dashboard
