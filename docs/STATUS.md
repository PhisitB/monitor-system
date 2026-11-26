# Status

_Last updated: 2026-11-26_

## Done
- Requirements ร่างแล้ว (`docs/REQUIREMENTS.md`)
- ติดตั้ง Python 3.12, Git, GitHub CLI แล้ว
- `git init` + commit แรก

## Decided
- Python + psutil, real-time only, frontend ไม่มี build step
- Architecture แบบ Hybrid: dashboard บน GitHub Pages + local agent ที่ 127.0.0.1
- Backup code ขึ้น GitHub: repo `monitor-system` (public)
- Agent ใช้ stdlib `http.server` (dependency เดียวคือ `psutil`)
- Speedtest วัดจาก browser กับ Cloudflare (download/upload test) เมื่อกดปุ่ม
- กราฟใช้ Chart.js เก็บไฟล์ไว้ใน repo (ไม่ใช้ CDN)

## Remaining
- [ ] สร้าง GitHub repo + push ครั้งแรก
- [ ] Agent: API endpoint คืนค่า metrics เป็น JSON + CORS/Local Network Access
- [ ] Frontend: dashboard + กราฟ real-time + สถานะ "agent ไม่ได้รัน"
- [ ] Speedtest (กดปุ่ม)
- [ ] เปิด GitHub Pages
- [ ] README: วิธีติดตั้งและรัน agent (Windows/macOS)
