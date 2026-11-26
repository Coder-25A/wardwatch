"""Add a few realistic sample reports so the demo list is not empty.

Usage (PowerShell):
    python scripts/seed_reports.py https://abc123.execute-api.ap-southeast-2.amazonaws.com/prod/reports
"""

import json
import sys
import urllib.error
import urllib.request

SAMPLES = [
    {"category": "flooded_drain", "description": "Storm drain blocked with plastic, water up to ankle level after 20 minutes of rain.",
     "area": "Gandhi Nagar 2nd Cross", "landmark": "Near Ganesh Temple", "lat": 17.3850, "lng": 78.4867},
    {"category": "pothole", "description": "Deep pothole hidden under rain water, two bikes slipped this morning.",
     "area": "Station Road", "landmark": "Opposite SBI ATM"},
    {"category": "garbage", "description": "Garbage pile not cleared for 4 days, blocking the drain inlet.",
     "area": "Market Lane", "landmark": "Behind vegetable market"},
    {"category": "streetlight", "description": "Three streetlights off on the school road, very dark after 7 pm.",
     "area": "School Road", "landmark": "Govt High School gate"},
]


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    url = sys.argv[1]
    for sample in SAMPLES:
        req = urllib.request.Request(url, data=json.dumps(sample).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(resp.status, json.loads(resp.read())["id"], sample["category"])
        except urllib.error.HTTPError as exc:
            print(exc.code, exc.read().decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
