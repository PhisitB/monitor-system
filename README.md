# Monitor System

Real-time dashboard for this machine: CPU, memory, disk, network, battery, top processes,
and an on-demand internet speedtest.

- **Dashboard:** https://phisitb.github.io/monitor-system/ (static page on GitHub Pages)
- **Local agent:** a small Python server on your machine at `http://127.0.0.1:8765` that the
  dashboard reads from when opened on the same machine.
- **Cloud mode (optional):** the agent also pushes the latest snapshot to Supabase every 5 s, so
  you can open the dashboard on another device (e.g. your phone), log in by email link, and see it.
  Without Supabase settings, nothing leaves your machine.

## Setup

Requires Python 3.10+.

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r agent\requirements.txt
.\.venv\Scripts\python agent\agent.py
```

**macOS**
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r agent/requirements.txt
.venv/bin/python agent/agent.py
```

Then open the dashboard. Chrome/Edge may ask for **Local network access** permission the first
time — allow it so the page can reach `127.0.0.1`.

Options: `--port <n>` (default 8765; the dashboard expects 8765).

## Cloud mode (view from other devices)

1. Create a project at [supabase.com](https://supabase.com).
2. **SQL Editor:** run [`supabase/schema.sql`](supabase/schema.sql).
3. **Table Editor → `allowed_viewers`:** add the email(s) allowed to view.
4. **Authentication → URL Configuration:** set Site URL and add a Redirect URL:
   `https://phisitb.github.io/monitor-system/`
5. **Project Settings → API:**
   - Project URL + publishable (anon) key → `web/config.js` (public by design)
   - Secret (service_role) key → `.env` on the notebook only (copy `.env.example` to `.env`).
     **Never commit it or put it in `web/`** — it bypasses all access rules.
6. Restart the agent; it prints `[cloud] pushing to Supabase every 5s`.

Optional hardening: **Authentication → Sign In / Providers → disable "Allow new users to sign up"**
and invite viewers instead. (Without it, anyone can create an account, but RLS still shows them nothing.)

## Develop locally

Serve `web/` from localhost (allowed by the agent's CORS rules):
```powershell
.\.venv\Scripts\python -m http.server 5500 --bind 127.0.0.1 --directory web
```
Open http://localhost:5500/

Run agent tests:
```powershell
cd agent
..\.venv\Scripts\python -m unittest -v
```

## Auto-start (Windows)

To have the agent start automatically 30 seconds after you log on, register the included Task Scheduler task:

```powershell
# Register (run once; safe to re-run)
agent\register-autostart.ps1

# Remove
agent\unregister-autostart.ps1
```

If PowerShell blocks the script (execution policy), run it with
`powershell -ExecutionPolicy Bypass -File agent\register-autostart.ps1`.

The task runs `pythonw.exe` (no console window) with the project root as working directory and reads `.env` automatically. It runs only when you are logged on, does **not** require elevated privileges, and restarts the agent up to 3 times if it crashes. Without a console, agent output goes to `agent\agent.log` (overwritten on each start).

> **Note:** If you move the project folder, re-run `register-autostart.ps1` to update the paths.

## Monitoring a Windows Server (VPS)

The same agent runs on Windows Server. View it through cloud mode — never expose port 8765 to the internet.

1. Install Python 3.12 and Git on the server, then clone the repo and set up the venv as above.
2. Create `.env` with `SUPABASE_URL`, `SUPABASE_SECRET_KEY` and a **unique** `DEVICE_ID` (e.g. `DEVICE_ID=vps`).
   Each machine needs its own `DEVICE_ID`, otherwise they overwrite each other's row.
3. Allow outbound HTTPS to `*.supabase.co` in the server firewall.
4. Test once in a console: `.venv\Scripts\python agent\agent.py` — look for `[cloud] pushing to Supabase`.
5. From an **elevated** PowerShell, register the boot-time task (runs without anyone logged on):

   ```powershell
   powershell -ExecutionPolicy Bypass -File agent\register-autostart-server.ps1
   schtasks /run /tn MonitorAgent
   ```

   Remove it with `agent\unregister-autostart.ps1`. Output goes to `agent\agent.log`.

6. On the dashboard, log in and pick the machine from the device selector in the header.
   "อัตโนมัติ" uses the local agent first, then the first cloud device.

> **Security:** `SUPABASE_SECRET_KEY` bypasses Row Level Security. If the server is compromised, everything
> in the Supabase project can be read and written. Keep the server patched and `.env` readable only by your account.

## Security notes

- The agent binds to `127.0.0.1` only and is read-only.
- It answers only requests from `https://phisitb.github.io` and `localhost` origins, and rejects
  non-local `Host` headers (DNS rebinding). Other websites cannot read your metrics or process list.
- The speedtest talks to `speed.cloudflare.com` only when you click the button.
- Cloud mode sends all metrics (including process names) to your Supabase project. Only logged-in
  emails listed in `allowed_viewers` can read them (Row Level Security); browsers cannot write.

## Layout

| Path | What |
|---|---|
| `agent/` | Python agent (`psutil`); `winprocs.py` = fast Windows process snapshot; `cloud.py` = Supabase push |
| `web/` | Dashboard (HTML/CSS/JS; Chart.js and supabase-js vendored in `web/vendor/`); `config.js` = Supabase public settings |
| `supabase/schema.sql` | Tables + Row Level Security for cloud mode |
| `.github/workflows/pages.yml` | Deploys `web/` to GitHub Pages on push to `main` |
| `docs/` | Requirements and status |
