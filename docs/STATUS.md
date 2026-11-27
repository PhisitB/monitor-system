# Status

_Last updated: 2026-11-27_

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
  - Tests: `agent/test_agent.py` (13 tests)
  - CPU model อ่านจาก registry บน Windows (platform.processor() ให้แค่ family/model)
  - Hardening (2026-11-27): แยก `MetricsCollector` ให้ cloud push (ไม่แย่ง delta กับ local poll), รองรับ query string บน `/api/metrics`, ดัก `http.client.HTTPException` และ fallback `DEVICE_ID` ว่างใน `agent/cloud.py`
- Dashboard (`web/`): stat tiles, กราฟ CPU/Memory/Network/Disk I/O ย้อนหลัง 5 นาที (poll ทุก 2 s),
  ราย core, disk usage (เตือน ≥ 90%), system info, top processes, speedtest (Cloudflare), banner เมื่อไม่พบ agent
  - Chart.js 4.6.2 vendored ที่ `web/vendor/` (ตรวจ sha512 กับ npm registry แล้ว)
  - ตรวจด้วย headless Edge screenshot แล้ว (ทั้งสถานะ connected และ offline)
  - Hardening (2026-11-27): กัน `cores_physical`/`freq_max_mhz` เป็น `null`/`0`, เพิ่ม timeout ให้ speedtest, ฟัง `onAuthStateChange` หลัง login magic link
- GitHub Actions workflow deploy `web/` ขึ้น Pages (`.github/workflows/pages.yml`)
- README: วิธีติดตั้ง/รัน (Windows/macOS)

- GitHub Pages เปิดแล้ว (build จาก Actions): https://phisitb.github.io/monitor-system/
- Cloud mode — ใช้งานได้จริงแล้ว (ทดสอบ login magic link + ดูข้อมูลจากมือถือผ่าน 5G สำเร็จ 2026-11-26):
  - Supabase project ตั้งค่าแล้ว (schema + grants + allowed_viewers + URL config); `web/config.js` มี URL + publishable key
  - ตรวจแล้วว่า publishable key โดยไม่ login อ่าน/เขียนตารางไม่ได้ (401)
  - `agent/cloud.py` push snapshot ทุก 5 s เมื่อมี `SUPABASE_URL`/`SUPABASE_SECRET_KEY` ใน `.env` (tests: `agent/test_cloud.py`, 6 tests)
  - `supabase/schema.sql`: `device_metrics` (ค่าล่าสุด/เครื่อง + trigger `updated_at` เวลา server), `allowed_viewers`, RLS
  - Dashboard: ลอง local agent ก่อน → ไม่เจอ → login magic link → อ่านจาก Supabase ทุก 5 s; แสดง "notebook ออฟไลน์" ถ้าข้อมูลเก่ากว่า 30 s
  - supabase-js 2.119.2 vendored (sha512 ตรวจกับ npm แล้ว)

## Decided
- Python + psutil, real-time only, frontend ไม่มี build step
- Architecture แบบ Hybrid: dashboard บน GitHub Pages + local agent ที่ 127.0.0.1:8765
- Agent ใช้ stdlib `http.server` (dependency เดียวคือ `psutil`)
- Speedtest วัดจาก browser กับ Cloudflare (download/upload test) เมื่อกดปุ่ม
- กราฟใช้ Chart.js เก็บไฟล์ไว้ใน repo (ไม่ใช้ CDN)

- ดูจากเครื่องอื่นผ่าน internet: Supabase + magic link + allowlist อีเมล (ทางเลือก Tailscale / Cloudflare Tunnel ถูกปัดตก)

## Remaining
- [ ] รันส่วน trigger `device_metrics_set_updated_at` ใน `supabase/schema.sql` บน Supabase SQL Editor เพื่อให้อัปเดต `updated_at` ด้วยเวลา server
- [ ] ยืนยันว่า dashboard จาก github.io ต่อ local agent ได้ใน browser จริงบน notebook
      (agent log เห็น request เข้ามาทุก ~3 s แต่ยังไม่ได้ยืนยันจากหน้าจอ)
- [ ] ให้ agent เริ่มเองตอนเปิดเครื่อง (ตอนนี้ต้องรัน `python agent/agent.py` เอง)
- [ ] ทดสอบ speedtest ใน browser จริง (endpoint CORS ตรวจด้วย curl แล้ว แต่ยังไม่ได้กดใน browser)
- [ ] ทดสอบ agent บน macOS (ยังไม่ได้ทดสอบ — path ที่ไม่ใช่ Windows ใช้ psutil ล้วน)

## Known limitations
- CPU clock บน Windows: psutil รายงานแค่ base clock (ไม่ใช่ turbo/ปัจจุบันจริง)
- Safari อาจบล็อกการเรียก `http://127.0.0.1` จากหน้า https (ใช้ Chrome/Edge/Firefox) — ไม่กระทบ cloud mode
- Browser ในแอป (เช่นเปิดลิงก์จาก LINE) อาจ cache หน้าเก่า: หลัง deploy ให้เปิดใน Safari/Chrome หรือเติม `?v=<n>`
- Supabase free plan: ส่งอีเมล login ได้ ~2 ฉบับ/ชม.; project ถูกพักถ้าไม่มีการใช้งาน 7 วัน
