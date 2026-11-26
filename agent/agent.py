"""Local monitoring agent.

Serves this machine's metrics as JSON at http://127.0.0.1:<port>/api/metrics
for the dashboard hosted on GitHub Pages. Read-only; binds to localhost only.
"""

import argparse
import json
import platform
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psutil

if psutil.WINDOWS:
    import winprocs

DEFAULT_PORT = 8765
ALLOWED_ORIGINS = {"https://phisitb.github.io"}
LOCAL_ORIGIN_RE = re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$")
ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
TOP_N = 10


def origin_allowed(origin):
    """No Origin (curl, same-origin GET) is allowed; otherwise it must be ours."""
    if origin is None:
        return True
    return origin in ALLOWED_ORIGINS or bool(LOCAL_ORIGIN_RE.match(origin))


def process_snapshot():
    """Return {(pid, create_time): (pid, name, cpu_seconds, rss_bytes)}."""
    if psutil.WINDOWS:
        return winprocs.snapshot()
    procs = {}
    for p in psutil.process_iter(["name", "cpu_times", "memory_info", "create_time"]):
        info = p.info
        if info["cpu_times"] is None or info["memory_info"] is None:
            continue  # AccessDenied (e.g. other users' processes on macOS)
        cpu = info["cpu_times"].user + info["cpu_times"].system
        procs[(p.pid, info["create_time"])] = (p.pid, info["name"], cpu, info["memory_info"].rss)
    return procs


class MetricsCollector:
    """Collects metrics; keeps previous counters to turn totals into rates."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last_time = time.monotonic()
        self._last_disk = psutil.disk_io_counters()
        self._last_net = psutil.net_io_counters()
        self._last_procs = process_snapshot()
        # Track cpu_times ourselves: psutil.cpu_percent(interval=None) keeps its
        # state per thread, and ThreadingHTTPServer uses a new thread per request.
        self._last_cpu = psutil.cpu_times()
        self._last_percpu = psutil.cpu_times(percpu=True)

    def collect(self):
        with self._lock:
            now = time.monotonic()
            elapsed = max(now - self._last_time, 1e-6)
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()
            procs = process_snapshot()
            cpu_times = psutil.cpu_times()
            percpu_times = psutil.cpu_times(percpu=True)
            data = {
                "timestamp": time.time(),
                "cpu": self._cpu(self._last_cpu, cpu_times, self._last_percpu, percpu_times),
                "memory": self._memory(),
                "disks": self._disks(),
                "disk_io": self._rate(self._last_disk, disk_io, elapsed, "read_bytes", "write_bytes"),
                "network": self._rate(self._last_net, net_io, elapsed, "bytes_recv", "bytes_sent"),
                "battery": self._battery(),
                "processes": self._processes(self._last_procs, procs, elapsed),
                "system": self._system(),
            }
            self._last_time, self._last_disk, self._last_net, self._last_procs = now, disk_io, net_io, procs
            self._last_cpu, self._last_percpu = cpu_times, percpu_times
            return data

    @staticmethod
    def _busy_percent(prev, cur):
        """Busy % between two cpu_times snapshots (idle + iowait count as idle)."""
        def idle(t):
            return t.idle + getattr(t, "iowait", 0)
        total = sum(cur) - sum(prev)
        if total <= 0:
            return 0.0
        busy = total - (idle(cur) - idle(prev))
        return round(min(max(busy / total * 100, 0.0), 100.0), 1)

    @classmethod
    def _cpu(cls, prev, cur, prev_percpu, cur_percpu):
        freq = psutil.cpu_freq()
        return {
            "percent": cls._busy_percent(prev, cur),
            "per_core": [cls._busy_percent(p, c) for p, c in zip(prev_percpu, cur_percpu)],
            "freq_mhz": freq.current if freq else None,
            "freq_max_mhz": freq.max if freq else None,
            "cores_logical": psutil.cpu_count(logical=True),
            "cores_physical": psutil.cpu_count(logical=False),
        }

    @staticmethod
    def _memory():
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
        return {
            "total": vm.total, "used": vm.total - vm.available, "percent": vm.percent,
            "swap_total": sw.total, "swap_used": sw.used, "swap_percent": sw.percent,
        }

    @staticmethod
    def _disks():
        disks = []
        for part in psutil.disk_partitions(all=False):
            if not part.fstype or "cdrom" in part.opts:
                continue
            try:
                u = psutil.disk_usage(part.mountpoint)
            except OSError as e:
                disks.append({"mount": part.mountpoint, "error": str(e)})
                continue
            disks.append({
                "mount": part.mountpoint, "fstype": part.fstype,
                "total": u.total, "used": u.used, "free": u.free, "percent": u.percent,
            })
        return disks

    @staticmethod
    def _rate(prev, cur, elapsed, in_field, out_field):
        """Bytes/sec between two counter snapshots; None if unavailable."""
        if prev is None or cur is None:
            return None
        return {
            f"{in_field}_per_sec": max(getattr(cur, in_field) - getattr(prev, in_field), 0) / elapsed,
            f"{out_field}_per_sec": max(getattr(cur, out_field) - getattr(prev, out_field), 0) / elapsed,
        }

    @staticmethod
    def _battery():
        b = psutil.sensors_battery()
        if b is None:
            return None
        secs = b.secsleft if b.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) else None
        return {"percent": b.percent, "plugged": b.power_plugged, "secs_left": secs}

    @staticmethod
    def _processes(prev, cur, elapsed):
        """CPU % (of whole machine) from CPU-time delta between two snapshots."""
        ncpu = psutil.cpu_count() or 1
        procs = []
        for key, (pid, name, cpu_sec, rss) in cur.items():
            prev_entry = prev.get(key)
            cpu = 0.0
            if prev_entry is not None:
                cpu = max(cpu_sec - prev_entry[2], 0) / elapsed / ncpu * 100
            procs.append({"pid": pid, "name": name, "cpu_percent": min(cpu, 100.0), "memory_rss": rss})
        return {
            "by_cpu": sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:TOP_N],
            "by_memory": sorted(procs, key=lambda x: x["memory_rss"], reverse=True)[:TOP_N],
        }

    @staticmethod
    def _system():
        boot = psutil.boot_time()
        return {
            "os": f"{platform.system()} {platform.release()}",
            "os_version": platform.version(),
            "cpu_model": platform.processor(),
            "boot_time": boot,
            "uptime_sec": time.time() - boot,
        }


class Handler(BaseHTTPRequestHandler):
    collector = None  # set in main()

    def _cors_headers(self, origin):
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _reject_if_bad_request(self):
        """Reject foreign origins and non-local Host headers (DNS rebinding)."""
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host not in ALLOWED_HOSTS:
            self.send_error(403, "Host not allowed")
            return True
        if not origin_allowed(self.headers.get("Origin")):
            self.send_error(403, "Origin not allowed")
            return True
        return False

    def do_OPTIONS(self):
        if self._reject_if_bad_request():
            return
        self.send_response(204)
        self._cors_headers(self.headers.get("Origin"))
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Max-Age", "600")
        # Chrome/Edge Private (Local) Network Access preflight
        if self.headers.get("Access-Control-Request-Private-Network") == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_GET(self):
        if self._reject_if_bad_request():
            return
        if self.path != "/api/metrics":
            self.send_error(404, "Not found")
            return
        body = json.dumps(self.collector.collect()).encode()
        self.send_response(200)
        self._cors_headers(self.headers.get("Origin"))
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def make_server(port):
    Handler.collector = MetricsCollector()
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Local metrics agent for Monitor System dashboard")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default {DEFAULT_PORT})")
    args = parser.parse_args()
    server = make_server(args.port)
    print(f"Agent running at http://127.0.0.1:{args.port}/api/metrics  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
