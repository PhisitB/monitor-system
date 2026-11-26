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
  - CPU model อ่านจาก registry บน Windows (platform.processor() ให้แค่ family/model)
- Dashboard (`web/`): stat tiles, กราฟ CPU/Memory/Network/Disk I/O ย้อนหลัง 5 นาที (poll ทุก 2 s),
  ราย core, disk usage (เตือน ≥ 90%), system info, top processes, speedtest (Cloudflare), banner เมื่อไม่พบ agent
  - Chart.js 4.6.2 vendored ที่ `web/vendor/` (ตรวจ sha512 กับ npm registry แล้ว)
  - ตรวจด้วย headless Edge screenshot แล้ว (ทั้งสถานะ connected และ offline)
- GitHub Actions workflow deploy `web/` ขึ้น Pages (`.github/workflows/pages.yml`)
- README: วิธีติดตั้ง/รัน (Windows/macOS)

## Decided
- Python + psutil, real-time only, frontend ไม่มี build step
- Architecture แบบ Hybrid: dashboard บน GitHub Pages + local agent ที่ 127.0.0.1:8765
- Agent ใช้ stdlib `http.server` (dependency เดียวคือ `psutil`)
- Speedtest วัดจาก browser กับ Cloudflare (download/upload test) เมื่อกดปุ่ม
- กราฟใช้ Chart.js เก็บไฟล์ไว้ใน repo (ไม่ใช้ CDN)

## Remaining
- [ ] เปิด GitHub Pages (Settings → Pages → Source: GitHub Actions) แล้วทดสอบ dashboard จาก github.io กับ agent จริง
- [ ] ทดสอบ speedtest ใน browser จริง (endpoint CORS ตรวจด้วย curl แล้ว แต่ยังไม่ได้กดใน browser)
- [ ] ทดสอบ agent บน macOS (ยังไม่ได้ทดสอบ — path ที่ไม่ใช่ Windows ใช้ psutil ล้วน)

## Known limitations
- CPU clock บน Windows: psutil รายงานแค่ base clock (ไม่ใช่ turbo/ปัจจุบันจริง)
- Safari อาจบล็อกการเรียก `http://127.0.0.1` จากหน้า https (ใช้ Chrome/Edge/Firefox)
