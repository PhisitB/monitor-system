import json
import os
import tempfile
import threading
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cloud


class FakeSupabase(BaseHTTPRequestHandler):
    requests = []
    status = 201

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        # self.headers is case-insensitive, like HTTP (urllib sends "Apikey")
        FakeSupabase.requests.append({"path": self.path, "headers": self.headers, "body": json.loads(body)})
        self.send_response(FakeSupabase.status)
        self.end_headers()
        if FakeSupabase.status >= 400:
            self.wfile.write(b'{"message":"bad key"}')

    def log_message(self, *args):
        pass


class FakeCollector:
    def collect(self):
        return {"timestamp": 123.0, "cpu": {"percent": 5.0}}


class PusherTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeSupabase)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeSupabase.requests = []
        FakeSupabase.status = 201

    def test_push_upserts_snapshot(self):
        cloud.SupabasePusher(FakeCollector(), self.url + "/", "sb_secret_x", "nb1").push_once()
        req = FakeSupabase.requests[0]
        self.assertEqual(req["path"], "/rest/v1/device_metrics?on_conflict=device_id")
        self.assertEqual(req["headers"]["apikey"], "sb_secret_x")
        self.assertNotIn("Authorization", req["headers"])  # new-style keys are not JWTs
        self.assertIn("resolution=merge-duplicates", req["headers"]["Prefer"])
        self.assertEqual(req["body"]["device_id"], "nb1")
        self.assertEqual(req["body"]["data"]["cpu"]["percent"], 5.0)
        self.assertIn("updated_at", req["body"])

    def test_legacy_jwt_key_sends_authorization(self):
        cloud.SupabasePusher(FakeCollector(), self.url, "eyJhbGciOi.fake", "nb1").push_once()
        self.assertEqual(FakeSupabase.requests[0]["headers"]["Authorization"], "Bearer eyJhbGciOi.fake")

    def test_http_error_raises(self):
        FakeSupabase.status = 401
        with self.assertRaises(urllib.error.HTTPError):
            cloud.SupabasePusher(FakeCollector(), self.url, "bad", "nb1").push_once()


class LoadEnvTest(unittest.TestCase):
    def test_reads_file_without_overriding_real_env(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / ".env"
            p.write_text('# comment\nMON_TEST_A="from file"\nMON_TEST_B=file\n\n', encoding="utf-8")
            os.environ["MON_TEST_B"] = "real"
            try:
                cloud.load_env(p)
                self.assertEqual(os.environ["MON_TEST_A"], "from file")
                self.assertEqual(os.environ["MON_TEST_B"], "real")
            finally:
                os.environ.pop("MON_TEST_A", None)
                os.environ.pop("MON_TEST_B", None)


if __name__ == "__main__":
    unittest.main()
