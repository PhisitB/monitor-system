import http.client
import json
import os
import threading
import time
import unittest
from unittest import mock

import psutil

import agent


class AgentServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = agent.make_server(0)  # ephemeral port
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, method, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request(method, path, headers=headers or {})
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp, body

    def test_metrics_has_all_sections(self):
        resp, body = self.request("GET", "/api/metrics")
        self.assertEqual(resp.status, 200)
        data = json.loads(body)
        for key in ("cpu", "memory", "disks", "disk_io", "network", "battery", "processes", "system"):
            self.assertIn(key, data)
        self.assertIsInstance(data["cpu"]["per_core"], list)
        self.assertLessEqual(len(data["processes"]["by_cpu"]), agent.TOP_N)

    def test_allowed_origin_gets_cors_header(self):
        origin = "https://phisitb.github.io"
        resp, _ = self.request("GET", "/api/metrics", {"Origin": origin})
        self.assertEqual(resp.status, 200)
        self.assertEqual(resp.getheader("Access-Control-Allow-Origin"), origin)

    def test_foreign_origin_rejected(self):
        resp, _ = self.request("GET", "/api/metrics", {"Origin": "https://evil.example"})
        self.assertEqual(resp.status, 403)
        self.assertIsNone(resp.getheader("Access-Control-Allow-Origin"))

    def test_foreign_host_rejected(self):
        resp, _ = self.request("GET", "/api/metrics", {"Host": "evil.example"})
        self.assertEqual(resp.status, 403)

    def test_private_network_preflight(self):
        resp, _ = self.request("OPTIONS", "/api/metrics", {
            "Origin": "https://phisitb.github.io",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Private-Network": "true",
        })
        self.assertEqual(resp.status, 204)
        self.assertEqual(resp.getheader("Access-Control-Allow-Private-Network"), "true")

    def test_unknown_path_404(self):
        resp, _ = self.request("GET", "/other")
        self.assertEqual(resp.status, 404)

    def test_metrics_with_query_string(self):
        resp, _ = self.request("GET", "/api/metrics?t=1")
        self.assertEqual(resp.status, 200)


class ProcessSnapshotTest(unittest.TestCase):
    def test_own_process_present_with_matching_rss(self):
        snap = agent.process_snapshot()
        me = psutil.Process()
        entries = [v for v in snap.values() if v[0] == me.pid]
        self.assertEqual(len(entries), 1)
        # rss changes slightly between calls; allow 20 MB drift
        self.assertLess(abs(entries[0][3] - me.memory_info().rss), 20 * 1024 * 1024)

    def test_busy_process_shows_cpu(self):
        collector = agent.MetricsCollector()
        end = time.monotonic() + 1.0
        while time.monotonic() < end:
            pass  # burn CPU in this process
        procs = collector.collect()["processes"]["by_cpu"]
        me = [p for p in procs if p["pid"] == os.getpid()]
        self.assertTrue(me, "busy test process should be in top CPU list")
        self.assertGreater(me[0]["cpu_percent"], 0)

    def test_cpu_percent_works_from_new_thread(self):
        # Regression: psutil.cpu_percent(None) state is per-thread and the
        # server handles each request on a new thread, which gave 0% every time.
        collector = agent.MetricsCollector()
        end = time.monotonic() + 1.0
        while time.monotonic() < end:
            pass
        result = []
        t = threading.Thread(target=lambda: result.append(collector.collect()["cpu"]))
        t.start()
        t.join()
        self.assertGreater(result[0]["percent"], 0)
        self.assertEqual(len(result[0]["per_core"]), psutil.cpu_count())

    def test_collect_is_fast(self):
        collector = agent.MetricsCollector()
        start = time.monotonic()
        collector.collect()
        self.assertLess(time.monotonic() - start, 1.0)

    def test_collector_handles_missing_optional_sensors(self):
        with mock.patch.object(agent.psutil, "sensors_battery", return_value=None), \
             mock.patch.object(agent.psutil, "disk_io_counters", return_value=None), \
             mock.patch.object(agent.psutil, "net_io_counters", return_value=None), \
             mock.patch.object(agent.psutil, "cpu_freq", return_value=None):
            data = agent.MetricsCollector().collect()
        self.assertIsNone(data["battery"])
        self.assertIsNone(data["disk_io"])
        self.assertIsNone(data["network"])
        self.assertIsNone(data["cpu"]["freq_mhz"])
        self.assertIsNone(data["cpu"]["freq_max_mhz"])


class OriginTest(unittest.TestCase):
    def test_origin_rules(self):
        self.assertTrue(agent.origin_allowed(None))
        self.assertTrue(agent.origin_allowed("http://localhost:5500"))
        self.assertTrue(agent.origin_allowed("http://127.0.0.1"))
        self.assertFalse(agent.origin_allowed("https://phisitb.github.io.evil.example"))
        self.assertFalse(agent.origin_allowed("http://localhost.evil.example"))
        self.assertFalse(agent.origin_allowed("https://evil.example"))


if __name__ == "__main__":
    unittest.main()
