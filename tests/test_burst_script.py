"""Checks the burst test script against a tiny local web server."""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import burst_test  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    hits = 0
    posts = []
    lock = threading.Lock()

    def _count(self):
        with _Handler.lock:
            _Handler.hits += 1
            return _Handler.hits

    def do_GET(self):
        n = self._count()
        if self.path.startswith("/cdn"):
            # Pretend to be CloudFront: first request misses, the rest hit.
            self.send_response(200)
            self.send_header("X-Cache", "Miss from cloudfront" if n == 1 else "Hit from cloudfront")
        else:
            self.send_response(200 if n <= 20 else 429)
        self.end_headers()
        self.wfile.write(b"{}")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        with _Handler.lock:
            _Handler.posts.append(body)
        self.send_response(201)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


def _serve():
    _Handler.hits = 0
    _Handler.posts = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_counts_and_percentiles():
    server, base = _serve()
    try:
        summary = burst_test.run_burst(base + "/reports", requests_total=50, concurrency=10, timeout=5)
    finally:
        server.shutdown()
    assert summary["total"] == 50
    assert summary["counts"] == {"200": 20, "429": 30}
    assert summary["cache"] == {"none": 50}
    assert summary["p50_ms"] <= summary["p95_ms"]


def test_cloudfront_cache_counts():
    server, base = _serve()
    try:
        summary = burst_test.run_burst(base + "/cdn/reports", requests_total=30, concurrency=1, timeout=5)
    finally:
        server.shutdown()
    assert summary["counts"] == {"200": 30}
    assert summary["cache"] == {"hit": 29, "miss": 1}


def test_post_sample_sends_valid_reports():
    server, base = _serve()
    try:
        summary = burst_test.run_burst(base + "/reports", requests_total=5, concurrency=2,
                                       timeout=5, post_sample=True)
    finally:
        server.shutdown()
    assert summary["method"] == "POST"
    assert summary["counts"] == {"201": 5}
    assert all(p["category"] == "garbage" and p["area"] for p in _Handler.posts)
    assert len({p["description"] for p in _Handler.posts}) == 5


def test_cache_label():
    assert burst_test.cache_label("Hit from cloudfront") == "hit"
    assert burst_test.cache_label("RefreshHit from cloudfront") == "hit"
    assert burst_test.cache_label("Miss from cloudfront") == "miss"
    assert burst_test.cache_label("Error from cloudfront") == "other"
    assert burst_test.cache_label(None) == "none"


def test_percentile_helper():
    assert burst_test.percentile([1, 2, 3, 4], 50) == 2
    assert burst_test.percentile([10], 95) == 10
    assert burst_test.percentile([], 50) == 0


def test_summary_has_start_time():
    server, base = _serve()
    try:
        summary = burst_test.run_burst(base + "/reports", requests_total=2, concurrency=1, timeout=5)
    finally:
        server.shutdown()
    assert summary["start_utc"] <= summary["time_utc"]


def test_count_window():
    import count_lambda_runs
    start, end = count_lambda_runs.burst_window(
        {"start_utc": "2026-11-27T06:30:42+00:00", "wall_seconds": 12.5})
    assert start.isoformat() == "2026-11-27T06:30:00+00:00"
    assert (end - start).total_seconds() == 12.5 + 120
