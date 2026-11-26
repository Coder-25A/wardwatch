"""Send a burst of concurrent requests and report what came back.

Works on Windows, macOS and Linux with plain Python (no extra packages).

It prints:
  * how many answers had each HTTP status code (200 OK, 429 throttled, ...)
  * latency: p50 (typical) and p95 (slow end)
  * CloudFront cache results from the X-Cache header (Hit / Miss), when the URL
    is a CloudFront URL. Each Miss is one request that reached Lambda + DynamoDB.

Examples (PowerShell):
    python scripts\\burst_test.py $api -n 100 -c 8 --label before --save evidence\\burst-before.json
    python scripts\\burst_test.py $cdn -n 100 -c 8 --label after-cdn --save evidence\\burst-after-cdn.json
    python scripts\\burst_test.py $cdn -n 30 -c 8 --post-sample --label post-spam
"""

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

SAMPLE_REPORT = {
    "category": "garbage",
    "description": "Burst test report {n} (safe to ignore)",
    "area": "Test Lane",
}


def percentile(values, pct):
    """Nearest-rank percentile. percentile([...], 95) -> p95."""
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100 * len(ordered)))
    return ordered[rank - 1]


def cache_label(x_cache):
    """Turn an X-Cache header value into hit / miss / other / none."""
    if not x_cache:
        return "none"
    value = x_cache.lower()
    if value.startswith("hit") or value.startswith("refreshhit"):
        return "hit"
    if value.startswith("miss"):
        return "miss"
    return "other"   # for example "Error from cloudfront"


def one_request(url, timeout, index=0, post_sample=False):
    data, headers = None, {"User-Agent": "wardwatch-burst-test"}
    if post_sample:
        body = dict(SAMPLE_REPORT, description=SAMPLE_REPORT["description"].format(n=index))
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    start = time.perf_counter()
    x_cache = None
    try:
        req = urllib.request.Request(url, data=data, headers=headers,
                                     method="POST" if post_sample else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            status = str(resp.status)
            x_cache = resp.headers.get("X-Cache")
    except urllib.error.HTTPError as exc:  # 4xx / 5xx still count as answers
        status = str(exc.code)
        x_cache = exc.headers.get("X-Cache") if exc.headers else None
    except Exception as exc:  # timeouts, DNS problems, connection resets
        status = f"error:{type(exc).__name__}"
    return status, (time.perf_counter() - start) * 1000, cache_label(x_cache)


def run_burst(url, requests_total=100, concurrency=20, timeout=15, post_sample=False):
    start_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda i: one_request(url, timeout, i, post_sample),
                                range(requests_total)))
    wall = time.perf_counter() - started

    counts = Counter(status for status, _, _ in results)
    cache = Counter(label for _, _, label in results)
    latencies = [ms for _, ms, _ in results]
    ok_latencies = [ms for status, ms, _ in results if status.startswith("2")]
    return {
        "url": url,
        "method": "POST" if post_sample else "GET",
        "start_utc": start_utc,
        "time_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": requests_total,
        "concurrency": concurrency,
        "counts": dict(sorted(counts.items())),
        "cache": dict(sorted(cache.items())),
        "p50_ms": round(percentile(latencies, 50), 1),
        "p95_ms": round(percentile(latencies, 95), 1),
        "max_ms": round(max(latencies), 1) if latencies else 0,
        "p50_ok_ms": round(percentile(ok_latencies, 50), 1),
        "wall_seconds": round(wall, 2),
        "requests_per_second": round(requests_total / wall, 1) if wall else 0,
    }


NOTES = {"200": "OK", "201": "Created", "429": "Too Many Requests (throttled)", "500": "server error",
         "502": "bad gateway", "503": "unavailable", "403": "forbidden", "400": "bad request"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Burst test a URL with concurrent requests.")
    parser.add_argument("url", help="Full URL, for example .../prod/reports or https://dxxxx.cloudfront.net/reports")
    parser.add_argument("-n", "--requests", type=int, default=100, help="total requests (default 100)")
    parser.add_argument("-c", "--concurrency", type=int, default=20, help="requests in flight at once (default 20)")
    parser.add_argument("--timeout", type=float, default=15, help="seconds before a request gives up")
    parser.add_argument("--post-sample", action="store_true",
                        help="send POST requests with a small valid test report (spam test) instead of GET")
    parser.add_argument("--label", default="", help="a name for this run, like before or after")
    parser.add_argument("--save", help="write the summary as JSON to this file")
    args = parser.parse_args(argv)

    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be 1 or more")

    method = "POST" if args.post_sample else "GET"
    print(f"Sending {args.requests} {method} requests, {args.concurrency} at a time, to:\n  {args.url}\n")
    summary = run_burst(args.url, args.requests, args.concurrency, args.timeout, args.post_sample)
    summary["label"] = args.label

    print("Status code counts:")
    for status, count in summary["counts"].items():
        print(f"  {status:>6}  {count:>5}   {NOTES.get(status, '')}")
    print()
    cache = summary["cache"]
    if set(cache) != {"none"}:
        print("CloudFront cache (X-Cache header):")
        print(f"  Hit   {cache.get('hit', 0):>5}   served from the edge cache")
        print(f"  Miss  {cache.get('miss', 0):>5}   reached API Gateway -> Lambda -> DynamoDB")
        if cache.get("other") or cache.get("none"):
            print(f"  Other {cache.get('other', 0) + cache.get('none', 0):>5}")
        print()
    else:
        print("No X-Cache header: this URL is not going through CloudFront.\n")
    print(f"Latency p50: {summary['p50_ms']} ms   p95: {summary['p95_ms']} ms   max: {summary['max_ms']} ms")
    print(f"Finished in {summary['wall_seconds']} s  (~{summary['requests_per_second']} requests/second)")

    ok = sum(v for k, v in summary["counts"].items() if k.startswith("2"))
    print()
    print("Row for your evidence table (label | total | 2xx | 429 | cache hits | cache misses | p50 | p95):")
    print(f"| {args.label or 'run'} | {summary['total']} | {ok} | {summary['counts'].get('429', 0)} "
          f"| {cache.get('hit', 0)} | {cache.get('miss', 0)} | {summary['p50_ms']} | {summary['p95_ms']} |")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
        print(f"\nSaved to {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
