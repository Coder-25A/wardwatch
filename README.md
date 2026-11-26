# WardWatch

**Monsoon and civic issue reporting for one city ward in India.**

> Last monsoon, my ward's drainage WhatsApp group was just photos and rumours.
> Which drain was blocked? Was it already reported? Nobody knew.

WardWatch gives a ward one shared, simple list. Any resident can report a
**flooded drain, pothole, uncleared garbage or broken streetlight** with a short
description, the area or a landmark, and an optional GPS point. Anyone can open the list
and see what is already reported, so the ward office and volunteers see one clean
picture instead of 300 forwarded photos.

Built for the AWS Builder Center hackathon **"Let the Agent Review you"**: I ran the
Agent Toolkit `aws-well-architected-review` skill on this project, implemented one of
its recommendations, and measured the before and after.

## Architecture

```
 Browser (frontend/index.html)
        |
        v
 Amazon API Gateway (REST API, stage "prod", CORS on)
   |                         |
 POST /reports            GET /reports  (public)
   |                         |
 Lambda create_report     Lambda list_reports
 (Python 3.12, arm64)     (Python 3.12, arm64)
 write-only IAM policy    read-only IAM policy
   \                         /
    v                       v
  Amazon DynamoDB table (on-demand, encrypted at rest)
```

Everything is defined in `template.yaml` (AWS SAM). It runs in **ap-southeast-2 (Sydney)**,
the Region of my AWS Free plan project, and costs a few cents of free credits at most.

### What is already done well
* **Encryption at rest** on the DynamoDB table (SSE with the AWS managed key).
* **Least privilege:** the POST function can only write to this one table, the GET
  function can only read it. No wildcards on data.
* **Input validation:** fixed category list, 500 character description limit, length
  limits on area and landmark, lat/lng range checks, 4 KB body limit. Text in Indian
  scripts (Hindi, Telugu...) is kept intact; only control characters are stripped.
* **Structured JSON logs** with request ids, and **7 day log retention**.
* **Infrastructure as code** plus **unit tests** that run without AWS (`moto`).

### The weak spot (the "before")
`GET /reports` is public and runs a table Scan on every call, and the API has **no
throttling**. One script can hammer it, and every call costs API Gateway, Lambda and
DynamoDB money. Anyone can also spam `POST /reports`.

### The fix (the "after"): cache the reads, limit the writes
> The obvious fix (rate limits) would block residents during the exact flood they need
> the app for.

So instead of a rate limit on the public list:

```
 Residents --> CloudFront (30 s cache for GET /reports, *.cloudfront.net, no WAF/ACM)
                   |  cache miss / POST
                   v
              API Gateway  (POST /reports: 2 req/s, burst 5 | backstop on raw URL: 10/s, burst 20)
                   v
              Lambda --> DynamoDB
```

* A flood rush of readers is served from the CloudFront cache: **no 429s for residents**
  and about one Lambda run per 30 seconds per edge location instead of one per visit.
* Spam on `POST /reports` is cut off by a strict API Gateway limit.
* Trade-off: the public list can be **up to 30 seconds old** (the form shows your own new
  report immediately). Full details, measurements and other limitations: `FIX.md`.

## API

| Method | Path | Body / query | Returns |
|---|---|---|---|
| POST | `/reports` | `{"category","description","area","landmark?","lat?","lng?"}` | `201` + saved report |
| GET | `/reports` | `?limit=1..100&next=<token>` | `200` + `{"items","count","next?"}` (each page sorted newest first) |

Categories: `flooded_drain`, `pothole`, `garbage`, `streetlight`.

## Project layout

```
template.yaml          SAM template (all AWS resources)
src/                   Lambda code
  create_report.py     POST /reports
  list_reports.py      GET /reports (Scan + pagination)
  wardwatch_common.py  shared helpers (responses, CORS, table, limits)
tests/                 pytest unit tests (moto, no AWS needed)
scripts/burst_test.py  concurrent GET/POST burst test: status counts, p50/p95, CloudFront Hit/Miss
scripts/seed_reports.py  adds 4 sample reports
scripts/count_lambda_runs.py  counts Lambda runs during a saved burst (CloudWatch)
scripts/delete_test_reports.py  removes the "Burst test report" items after spam tests
CHECKLIST.md           ordered remaining steps to submission
frontend/index.html    simple page to view and submit reports
fix/template-after.yaml  the complete "after" template (CloudFront + throttling)
evidence/              burst test results (safe to commit)
GUIDE.md               step-by-step beginner guide (Windows PowerShell)
FIX.md                 the "after" change, story, trade-offs and cost estimate
```

## Run the tests

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -v
```

## Deploy

See **GUIDE.md**. Short version (with the Python 3.12 venv active): `sam build`, then
`sam deploy --guided --region ap-southeast-2`.

## Results (fill in after the review)

| Measure | Before | After |
|---|---|---|
| Residents' rush: 100 GETs, 8 at a time: 200 / 429 | | |
| CloudFront cache Hit / Miss | n/a | |
| List-Lambda runs for that rush (CloudWatch) | | |
| p50 / p95 latency (ms) | | |
| Spam: 30 POSTs, 8 at a time: 201 / 429 | | |
| Raw API URL rush: 200 / 429 | | |
| Review: findings on the public endpoint (status / risk) | | |
| Review: maturity score | | |

## Clean up

`sam delete --stack-name wardwatch --region ap-southeast-2 --profile wardwatch`
