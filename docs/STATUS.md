# Status

_Last updated: 2026-11-26_

## Done
- Requirements ร่างแล้ว (`docs/REQUIREMENTS.md`)
- ติดตั้ง Python 3.12, Git, GitHub CLI แล้ว
- GitHub repo: https://github.com/PhisitB/monitor-system (public)
- Local agent (`agent/agent.py`): `GET /api/metrics` คืน CPU, memory, disk usage, disk I/O,
  network, battery, top processes, system info เป็น JSON
  - CORS อนุญาตเฉพาะ `https://phisitb.github.io` + localhost, ตรวจ Host header, รองรับ Local Network Access preflight
  - Windows: process list ใช้ `agent/winprocs.py` (NtQuerySystemInformation ครั้งเดียว ~15 ms
    แทน psutil ที่ใช้ ~7 s เพราะ process ของ SYSTEM/service)
  - CPU % คำนวณเองจาก `cpu_times` (psutil `cpu_percent(None)` เก็บ state ต่อ thread → ได้ 0% ใน ThreadingHTTPServer)
  - Tests: `agent/test_agent.py` (11 tests)

## Decided
- Python + psutil, real-time only, frontend ไม่มี build step
- Architecture แบบ Hybrid: dashboard บน GitHub Pages + local agent ที่ 127.0.0.1:8765
- Agent ใช้ stdlib `http.server` (dependency เดียวคือ `psutil`)
- Speedtest วัดจาก browser กับ Cloudflare (download/upload test) เมื่อกดปุ่ม
- กราฟใช้ Chart.js เก็บไฟล์ไว้ใน repo (ไม่ใช้ CDN)

## Remaining
- [ ] Frontend: dashboard + กราฟ real-time + สถานะ "agent ไม่ได้รัน"
- [ ] Speedtest (กดปุ่ม)
- [ ] เปิด GitHub Pages
- [ ] README: วิธีติดตั้งและรัน agent (Windows/macOS)
- [ ] ทดสอบ agent บน macOS (ยังไม่ได้ทดสอบ — path ที่ไม่ใช่ Windows ใช้ psutil ล้วน)
