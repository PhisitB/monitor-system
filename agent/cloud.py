"""Push the latest metrics snapshot to Supabase so other devices can view it.

Enabled when SUPABASE_URL and SUPABASE_SECRET_KEY are set (environment or .env
in the repo root). The secret key bypasses Row Level Security: keep it in .env
on this machine only, never in the repo or the web page.
"""

import http.client
import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PUSH_INTERVAL_SEC = 5
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env(path=ENV_FILE):
    """Minimal .env reader (KEY=VALUE lines); real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class SupabasePusher:
    def __init__(self, collector, url, secret_key, device_id):
        self.collector = collector
        self.endpoint = f"{url.rstrip('/')}/rest/v1/device_metrics?on_conflict=device_id"
        self.headers = {
            "apikey": secret_key,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        }
        if secret_key.startswith("eyJ"):  # legacy service_role JWT also needs Authorization
            self.headers["Authorization"] = f"Bearer {secret_key}"
        self.device_id = device_id
        self._stop = threading.Event()
        self._failing = False

    def push_once(self):
        body = json.dumps({
            "device_id": self.device_id,
            "data": self.collector.collect(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).encode()
        req = urllib.request.Request(self.endpoint, data=body, headers=self.headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()

    def _run(self):
        while not self._stop.wait(PUSH_INTERVAL_SEC):
            try:
                self.push_once()
            except urllib.error.HTTPError as e:
                self._report_failure(f"HTTP {e.code}: {e.read(300).decode(errors='replace')}")
            except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as e:
                self._report_failure(str(e))
            else:
                if self._failing:
                    print("[cloud] push recovered")
                self._failing = False

    def _report_failure(self, msg):
        # Log the first failure and then stay quiet until it recovers (avoid log spam every 5 s).
        if not self._failing:
            print(f"[cloud] push failed, will keep retrying: {msg}")
        self._failing = True

    def start(self):
        threading.Thread(target=self._run, name="supabase-push", daemon=True).start()

    def stop(self):
        self._stop.set()


def pusher_from_env(collector):
    """Return a started pusher if configured, else None."""
    load_env()
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SECRET_KEY")
    if not url or not key:
        print("[cloud] SUPABASE_URL / SUPABASE_SECRET_KEY not set: cloud push disabled (local only)")
        return None
    device_id = os.environ.get("DEVICE_ID") or "notebook"
    pusher = SupabasePusher(collector, url, key, device_id)
    try:
        pusher.push_once()
        print(f"[cloud] pushing to Supabase every {PUSH_INTERVAL_SEC}s as device '{device_id}'")
    except urllib.error.HTTPError as e:
        print(f"[cloud] first push failed: HTTP {e.code}: {e.read(300).decode(errors='replace')}")
        pusher._failing = True
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as e:
        print(f"[cloud] first push failed: {e}")
        pusher._failing = True
    pusher.start()
    return pusher
