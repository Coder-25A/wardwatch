# FIX.md: the "after" change (do NOT apply until after the first review)

## The story in one line

> The obvious fix (a rate limit on the public API) would block residents during the exact
> flood they need the app for. So reads are **cached at the edge** and only **writes** are
> rate-limited.

## What the review is expected to flag

`GET /reports` is public, needs no login, and runs a DynamoDB **Scan** on every call. The
API has **no throttling** of its own. Only the account-wide default applies (thousands of
requests per second), which does nothing to stop a bot or a spam script.

So every call to the open endpoint:

1. is billed by API Gateway,
2. starts a Lambda run, and
3. reads the whole table page (Scan), which is billed per read.

In the Well-Architected Framework this usually shows up as "throttle requests"
(Reliability, often REL05-BP02), "protect network resources / limit exposure" (Security),
and sometimes "use caching" (Performance) or "manage demand" (Cost). The IDs may differ
after the Nov 16, 2026 framework update, so copy the ones **your** review prints, and make
sure your write-up ties the fix to a finding the review actually made. That is the
hackathon rule.

## Why not just add a rate limit to GET?

A simple stage-wide limit (say 10 requests/second) is the textbook fix, and it is free. But
picture the real moment WardWatch exists for: heavy rain, the WhatsApp group shares the
link, 300 residents open it within a minute. A limit sized to stop bots would answer many of
those residents with `429 Too Many Requests`, exactly when they need the list most.

So the fix splits the traffic by what it is:

| Traffic | Before | After |
|---|---|---|
| Residents reading the list (`GET /reports`) | every request hits Lambda + DynamoDB | served from the **CloudFront cache** (30 s). A whole flood rush costs about one Lambda run per 30 s per edge location. **No 429s.** |
| New reports (`POST /reports`) | unlimited | strict API Gateway limit: **2/s, burst 5** (spam protection). Never cached. |
| Anyone skipping CloudFront and calling the API URL directly | unlimited | backstop limit **10/s, burst 20** |

## Is this allowed and free on your Free plan project? Yes.

* CloudFront is on the Free plan's supported services list (Lambda@Edge is the exception,
  and we don't use it). It is a global service, called through us-east-1, which the
  project's Region rule allows for CloudFront. CloudFormation in ap-southeast-2 can create
  it like any other resource.
* We use the free default `*.cloudfront.net` certificate, so **no ACM certificate, no
  custom domain, no WAF, no logging**, and nothing is created in us-east-1.
* CloudFront's always-free allowance (pay-as-you-go) is **1 TB of data out and 10 million
  requests per month**. Our demo uses a few hundred requests.
* API Gateway stage throttling (MethodSettings) is free. Requests that API Gateway throttles
  never reach Lambda or DynamoDB.

## The change

The complete "after" template is in `fix/template-after.yaml` (checked with
`sam validate --lint`, `cfn-lint` and `sam build`). Two ways to apply it:

* **Easy:** `Copy-Item fix\template-after.yaml template.yaml` (this replaces the file; Git
  keeps the old version, so you can always see the difference with `git diff`).
* **By hand** (better for understanding): make the three edits below.

### Edit 1: throttling in `WardWatchApi` (under `StageName: prod`)

```yaml
      StageName: prod
      # AFTER (part 1): throttling at API Gateway.
      MethodSettings:
        # Backstop for anyone who skips CloudFront and calls the API URL directly.
        # Residents go through CloudFront, whose cache absorbs reads, so they never reach this.
        - ResourcePath: "/*"
          HttpMethod: "*"
          ThrottlingRateLimit: 10
          ThrottlingBurstLimit: 20
        # Strict limit on new reports, to stop spam. "/~1reports" means "/reports".
        - ResourcePath: "/~1reports"
          HttpMethod: "POST"
          ThrottlingRateLimit: 2
          ThrottlingBurstLimit: 5
```

### Edit 2: add CloudFront (paste just above the `Outputs:` line)

```yaml
  # -------------------------------------------------------------------------
  # AFTER (part 2): CloudFront in front of the API.
  # GET /reports is cached for 30 seconds at the edge, so a flood rush of
  # residents is served from the cache instead of hitting Lambda + DynamoDB.
  # POST is never cached; it passes through to API Gateway (strict limit above).
  # Uses the default *.cloudfront.net certificate: no ACM, no custom domain,
  # nothing created in us-east-1.
  # -------------------------------------------------------------------------
  ReportsCachePolicy:
    Type: AWS::CloudFront::CachePolicy
    Properties:
      CachePolicyConfig:
        Name: !Sub "${AWS::StackName}-reports-30s"
        Comment: Cache GET /reports for 30 seconds, keyed on limit and next only
        MinTTL: 0
        DefaultTTL: 30          # used because the API sends no Cache-Control header
        MaxTTL: 30
        ParametersInCacheKeyAndForwardedToOrigin:
          EnableAcceptEncodingGzip: true
          EnableAcceptEncodingBrotli: true
          QueryStringsConfig:
            QueryStringBehavior: whitelist
            QueryStrings:
              - limit
              - next
          HeadersConfig:
            HeaderBehavior: none
          CookiesConfig:
            CookieBehavior: none

  WardWatchCdn:
    Type: AWS::CloudFront::Distribution
    Properties:
      DistributionConfig:
        Enabled: true
        Comment: !Sub "WardWatch (${AWS::StackName}) - cached reads, protected API"
        HttpVersion: http2and3
        PriceClass: PriceClass_200      # includes edge locations in India
        Origins:
          - Id: wardwatch-api
            DomainName: !Sub "${WardWatchApi}.execute-api.${AWS::Region}.amazonaws.com"
            OriginPath: /prod
            CustomOriginConfig:
              OriginProtocolPolicy: https-only
              OriginSSLProtocols:
                - TLSv1.2
        DefaultCacheBehavior:
          TargetOriginId: wardwatch-api
          ViewerProtocolPolicy: https-only
          AllowedMethods: [GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE]
          CachedMethods: [GET, HEAD]    # POST is never cached
          Compress: true
          CachePolicyId: !Ref ReportsCachePolicy
          # Managed policy "AllViewerExceptHostHeader": forwards everything except
          # the Host header, which API Gateway needs to be its own domain.
          OriginRequestPolicyId: b689b0a8-53d0-40ab-baf2-68738e2966ac
```

What each part means:

* **`ReportsCachePolicy`**: how long to keep a copy (30 s), and what makes two requests
  "the same": only the `limit` and `next` query strings. Headers and cookies are ignored, so
  every resident shares one cached copy.
* **`Origins`**: where CloudFront fetches from: your API Gateway URL, stage `/prod`. So
  `https://dxxxx.cloudfront.net/reports` maps to `.../prod/reports`.
* **`AllowedMethods` / `CachedMethods`**: all methods pass through (so POST works), but only
  GET and HEAD are ever cached.
* **`OriginRequestPolicyId: b689b0a8-...`**: the AWS-managed policy
  "AllViewerExceptHostHeader". It forwards the body, `Content-Type` and query strings, but
  not the `Host` header. API Gateway rejects requests whose Host isn't its own domain.
* **`PriceClass_200`**: uses edge locations in India (and most of the world) without the
  most expensive ones.

### Edit 3: add outputs (at the end of the `Outputs:` section)

```yaml
  CloudFrontReportsUrl:
    Description: AFTER - public URL residents should use (cached GET, protected POST)
    Value: !Sub "https://${WardWatchCdn.DomainName}/reports"
  CloudFrontDistributionId:
    Description: CloudFront distribution id
    Value: !Ref WardWatchCdn
```

## Deploy it

```powershell
# with the Python 3.12 venv active: .\.venv\Scripts\Activate.ps1
sam validate --lint --region ap-southeast-2 --profile wardwatch
sam build
sam deploy --profile wardwatch
```

Type `y` at "Deploy this changeset?". **CloudFront takes a while: usually 5 to 15 minutes.**
That's normal. When it finishes, the Outputs show `CloudFrontReportsUrl`, like
`https://d1234abcd.cloudfront.net/reports`.

## Measure it (same `-n` and `-c 8` as your before run; your Lambda limit is 10)

See GUIDE.md Phase 7 for the full steps. In short:

1. **Residents' path (CloudFront):** `python scripts\burst_test.py $cdn -n 100 -c 8 --label after-cdn`
   Expect **100 x 200, 0 x 429**, and X-Cache showing mostly **Hit** with about 1 **Miss**.
2. **Origin load proof:** `python scripts\count_lambda_runs.py evidence\burst-after-cdn.json`
   counts `ListReportsFunction` runs during that burst. Before: about 100. After: about 1 to 3.
3. **Spam path (POST):** `python scripts\burst_test.py $cdn -n 30 -c 8 --post-sample --label post-spam-after`
   Expect a handful of `201` and the rest `429`.
4. **Bypass path (direct API URL):** `python scripts\burst_test.py $api -n 100 -c 8 --label after-direct`
   Expect about 20 to 40 `200` and the rest `429`: the backstop works.

## Honest trade-offs and limitations (put these in the write-up)

* **Up to 30 seconds stale.** A new report can take up to 30 s to appear in the public list.
  For drain and pothole reports that's fine; for a life-safety alert it wouldn't be. The web
  page shows the resident's own new report immediately and says "the public list updates
  within about 30 seconds".
* **POST limit during a real rush.** 2/s with a burst of 5 is about 120 reports a minute. A
  real ward won't get near that, but a spammer is cut off fast. If many people report at the
  very same second, a few may see "please wait a few seconds and submit again" (the page
  handles 429 politely).
* **The API URL is still public.** Someone can skip CloudFront and call API Gateway directly.
  The backstop limit caps what they can do, but it is shared, so it could make the direct URL
  return 429s. Residents use the CloudFront URL, so they aren't affected. Next step (free):
  CloudFront adds a secret header and the Lambda rejects requests without it.
* **Cache-busting.** A bot can add different `limit` or `next` values to dodge the cache. Each
  distinct value is one origin request per 30 s per edge, and the backstop limit still
  applies, so the damage is bounded, but it isn't zero. Per-client blocking would need AWS
  WAF, which is paid and, on project accounts, not available for CloudFront.
* **Per-edge caches.** Each CloudFront location keeps its own copy, so a rush spread across
  Mumbai, Chennai and Hyderabad costs one origin request per location per 30 s, not one in
  total. Still tiny.

## Cost of abuse: before vs after (rough estimate)

Rough list prices before free allowances. Check the current pricing pages (API Gateway,
Lambda and DynamoDB in Sydney; CloudFront for India) before you publish numbers.

| Per 1 million GET requests | Before (straight to API) | After (through CloudFront) |
|---|---|---|
| API Gateway REST requests | ~$3.50 | ~$0 (only cache misses reach it) |
| Lambda + DynamoDB Scan | ~$0.70 | ~$0 |
| CloudFront HTTPS requests (India, ~$0.012 per 10,000) | n/a | ~$1.20 |
| **Total** | **~$4.20** | **~$1.20**, and the first 10 M requests/month are free |

* A bot sending 100 requests/second all day is 8.64 million requests. Before: about
  **$36/day**, and the database is scanned 8.64 million times. After: about **$10/day** of
  CloudFront requests, beyond the free 10 M per month, with **near-zero load on Lambda and
  DynamoDB**, and residents still get fast answers.
* The real win isn't only money. The database and Lambda stay healthy during the rush, and
  no resident is turned away.
