# Monitor System

Real-time dashboard for this machine: CPU, memory, disk, network, battery, top processes,
and an on-demand internet speedtest.

- **Dashboard:** https://phisitb.github.io/monitor-system/ (static page on GitHub Pages)
- **Local agent:** a small Python server on your machine at `http://127.0.0.1:8765` that the
  dashboard reads from. Your metrics never leave your machine.

The dashboard needs the agent running on the same machine you open it on.

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

## Security notes

- The agent binds to `127.0.0.1` only and is read-only.
- It answers only requests from `https://phisitb.github.io` and `localhost` origins, and rejects
  non-local `Host` headers (DNS rebinding). Other websites cannot read your metrics or process list.
- The speedtest talks to `speed.cloudflare.com` only when you click the button.

## Layout

| Path | What |
|---|---|
| `agent/` | Python agent (`psutil`); `winprocs.py` = fast Windows process snapshot |
| `web/` | Dashboard (HTML/CSS/JS, Chart.js vendored in `web/vendor/`) |
| `.github/workflows/pages.yml` | Deploys `web/` to GitHub Pages on push to `main` |
| `docs/` | Requirements and status |
