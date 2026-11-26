# WardWatch: remaining steps to submission (in order)

Where you are: stack `wardwatch` is deployed in ap-southeast-2 with 5 reports. Your folder is
`C:\Users\tella\aws-hackathon\wardwatch`. Your Lambda limit is 10, so every burst test uses
`-c 8`. Deadline: **Dec 1, 1:29 PM IST** (Nov 30, 11:59 PM PST).

Do the steps in order. Each one says what to type, what it does, and what you should see.
⚠ marks something I could not test for you, so read the output carefully there.
`GUIDE.md` has longer explanations; `FIX.md` explains the fix.

---

## A. Get ready (every time you open a new PowerShell window: steps 2 to 4)

**1. Update your project files.** Right-click the new `wardwatch.zip` > Extract All > choose
`C:\Users\tella\aws-hackathon` > Extract. When Windows asks, choose **Replace the files in the
destination**.
*What it does:* brings in the new scripts and guides. Your `.venv`, `samconfig.toml` and
`.aws-sam` folders are not in the zip, so they are kept. `template.yaml` is unchanged.
Expected: `scripts\count_lambda_runs.py`, `scripts\delete_test_reports.py`, `CHECKLIST.md` and
`fix\template-after.yaml` now exist.
⚠ If you edited any file yourself, Windows will overwrite it. Tell me first if you did.

**2. Go to the folder and switch on Python 3.12**
```powershell
cd C:\Users\tella\aws-hackathon\wardwatch
.\.venv\Scripts\Activate.ps1
python --version
```
*What it does:* moves into the project and switches on the private Python 3.12 for it.
Expected: prompt starts with `(.venv)`, then `Python 3.12.10`.

**3. Check your AWS login**
```powershell
aws sts get-caller-identity --profile wardwatch
```
*What it does:* asks AWS "who am I?". Changes nothing.
Expected: `"Account": "733437129979"` and an Arn with `assumed-role/AccountFullAccessRole`.
If it says `ExpiredToken` or `Unable to locate credentials`: run `aws login --profile wardwatch`,
pick "My First Project" in the browser, and try again.

**4. Put the API address in a variable**
```powershell
$api = aws cloudformation describe-stacks --stack-name wardwatch --region ap-southeast-2 --profile wardwatch --query "Stacks[0].Outputs[?OutputKey=='ReportsEndpoint'].OutputValue" --output text
$api
```
*What it does:* reads your API address from the stack, so you don't paste it by hand.
Expected: `https://y7ndi37hbc.execute-api.ap-southeast-2.amazonaws.com/prod/reports`

**5. Update test tools and run the tests**
```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```
*What it does:* installs or updates pytest, moto and boto3 (1.41 or newer understands your
`aws login` session), then runs the automatic checks against a fake database.
Expected: `33 passed`.

**6. Quick live check**
```powershell
Invoke-RestMethod -Uri $api | Select-Object count
```
*What it does:* reads the report list once, like a resident opening the page.
Expected: `count` is `5`.

---

## B. Save the "before" code on GitHub

**7. Check what Git would upload**
```powershell
git status
```
*What it does:* shows which files Git sees.
* If it says `not a git repository`, run `git init` first, then `git status` again.
* Expected: you see `template.yaml`, `src/`, `tests/`, `scripts/`, `GUIDE.md` etc. You must
  **not** see `.venv`, `.aws-sam`, `samconfig.toml` or `private` (`.gitignore` hides them).

**8. Look inside samconfig.toml (optional, for peace of mind)**
```powershell
Get-Content samconfig.toml
```
*What it does:* prints the answers SAM saved during `sam deploy --guided`.
Expected: stack name, region, profile name, `confirm_changeset`, `capabilities` and maybe an S3
bucket name. No passwords or keys. It's still kept out of GitHub because it's personal to your PC.

**9. Make the public repo.** In the browser go to https://github.com/new. Name it `wardwatch`,
choose **Public**, and leave "Add a README", ".gitignore" and "license" **unticked**. Click
**Create repository**.
*What it does:* makes an empty public repo. Judges need to open the code link.

**10. Upload the "before" version**
```powershell
git config --global user.name "Tella Abhishek"
git config --global user.email "YOUR-EMAIL"
git add .
git commit -m "WardWatch: before state (no throttling, no caching)"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-NAME/wardwatch.git
git push -u origin main
git tag before
git push origin before
```
*What it does:* saves a snapshot, links it to GitHub, uploads it, and labels it `before`.
Expected: `push` ends with `main -> main` and `before -> before`. A GitHub sign-in window may
pop up the first time.
If `remote origin already exists`: run `git remote set-url origin https://github.com/YOUR-GITHUB-NAME/wardwatch.git`.

---

## C. Measure the "before" (do this BEFORE the fix)

**11. Warm up**
```powershell
python scripts\burst_test.py $api -n 10 -c 2
```
*What it does:* 10 gentle requests so slow first-time "cold starts" don't skew the numbers.
Expected: `200` x 10.

**12. The residents' rush, before**
```powershell
mkdir evidence -Force
python scripts\burst_test.py $api -n 100 -c 8 --label before --save evidence\burst-before.json
```
*What it does:* 100 GET requests, 8 at a time, straight to the API. It counts status codes,
measures speed, and saves the result.
Expected: `200` x 100, no `429`, "No X-Cache header". **Screenshot or screen-record this.**
⚠ If you see `500` or `502`, tell me (it would mean the Lambda limit was hit).

**13. Count Lambda runs for that rush** (wait 2 minutes first)
```powershell
python scripts\count_lambda_runs.py evidence\burst-before.json
```
*What it does:* asks CloudWatch (AWS's metrics service) how many times the list Lambda ran
during step 12.
Expected: about `100` (a few more is fine; warm-up requests in the same minute count too).
⚠ If it shows `0`, wait 2 more minutes and run it again; metrics can be slow.

**14. Spam test, before** (wait 3 minutes after step 12)
```powershell
python scripts\burst_test.py $api -n 30 -c 8 --post-sample --label post-spam-before --save evidence\post-spam-before.json
```
*What it does:* tries to post 30 test reports quickly, like a spammer.
Expected: `201` x 30. Nothing stops spam.

**15. Record "before" video clips now.** Use Win + Shift + R (Snipping Tool) to record:
`frontend\index.html` working, step 12's output, and step 13's count.
*Why:* after the fix you can't go back to film the "before" state.

---

## D. Set up the Agent Toolkit in Cursor

**16. Open the project in Cursor:** File > Open Folder > `C:\Users\tella\aws-hackathon\wardwatch`.

**17. Let the agent run the official setup.** Open the Agent chat (Ctrl+L), make sure it is in
**Agent** mode with a Grok model, and paste:
```
Set up Agent Toolkit for AWS by following instructions: https://raw.githubusercontent.com/aws/agent-toolkit-for-aws/refs/heads/main/setup-instructions/setup.md
My answers: profile name is wardwatch. Yes, I use the new AWS experience (my project is "My First Project"). My project Region is ap-southeast-2. I'm on Windows. AWS CLI 2.42.4 is installed and I'm already logged in with aws login --profile wardwatch, so skip installing the CLI and skip logging in again unless get-caller-identity fails.
```
*What it does:* the agent follows AWS's official setup steps. Click **Run/Allow** for each
command. Key commands it runs:
* `aws sts get-caller-identity --profile wardwatch`: checks your login.
* `aws configure agent-toolkit --yes --region us-east-1 --profile wardwatch`: installs the AWS
  skills into `C:\Users\tella\.cursor\skills\` and adds an `aws-mcp` entry to
  `C:\Users\tella\.cursor\mcp.json`. The toolkit service only lives in us-east-1, which is why
  this one command uses us-east-1.
* `aws agent-toolkit list-available-skills --region us-east-1 --profile wardwatch`: lists skills.
* It saves AWS "starter" rules into `.cursor\rules\` in your project.
If the wizard fails with exit code `253` or "requires interactive terminal", run that
`aws configure agent-toolkit ...` command yourself in PowerShell, then tell the agent "done".
⚠ If `list-available-skills` says AccessDenied, see Troubleshooting in GUIDE.md (fallback included).

**18. Fix the MCP settings file.** In Cursor: File > Open File >
`C:\Users\tella\.cursor\mcp.json` (that's the global file the toolkit writes, not one inside the
project). The `aws-mcp` part must look exactly like this. Leave any other servers in the
file alone:
```json
{
  "mcpServers": {
    "aws-mcp": {
      "command": "uvx",
      "args": [
        "mcp-proxy-for-aws@latest",
        "https://aws-mcp.us-east-1.api.aws/mcp",
        "--metadata",
        "INSTALL_SOURCE=aws-cli",
        "AWS_REGION=ap-southeast-2"
      ],
      "env": {
        "AWS_MCP_PROXY_PROFILES": "wardwatch"
      }
    }
  }
}
```
*What it does:* `AWS_REGION=ap-southeast-2` makes the agent's AWS calls go to your project's
Region (otherwise they default to us-east-1 and get denied). `AWS_MCP_PROXY_PROFILES` tells it
to use your `wardwatch` login. The us-east-1 address is only where the MCP server runs, and
that's fine. Save with Ctrl+S.
⚠ If the agent already added the `env` part, don't add it twice. If your file looks different
from this, send me a screenshot before changing it.

**19. Restart Cursor and confirm.** File > Exit, then open Cursor on the wardwatch folder again.
* Open **Customize** in the left sidebar: `aws-mcp` should be **on** with no error.
* In the Agent chat, type `/aws-well` : `aws-well-architected-review` should appear in the list.
* Optional double-check in PowerShell:
```powershell
dir $HOME\.cursor\skills
```
Expected: a folder named `aws-well-architected-review` (among others).

---

## E. Run the review ("before")

**20. Run the skill.** Open a **new** Agent chat. Type `/aws-well-architected-review`, select it,
then paste:
```
Use the Well-Architected Review skill of Agent Toolkit to review this project. Scope: only this repository and the CloudFormation stack named wardwatch in ap-southeast-2 (AWS profile wardwatch). Do not review any other stack in the account, such as student-portal. Do not change any files or AWS resources; this is a review only.
```
*What it does:* runs the real Agent Toolkit review, limited to WardWatch. The first sentence is
the hackathon's own suggested wording. Allow read-only AWS calls if it asks. If it asks for a
mode or pillars, choose a full review.
Expected: a report with pillar scores (1 to 5), findings with risk levels (Critical/High/Medium/Low),
things it says are already done well, and a priority list.

**21. Save it privately and take notes.** Create the folder `private` in the project, then the
file `private\review-before.md`, and paste the whole report in. Screenshot the summary, the
scores and the findings about the public `GET /reports` endpoint.
*Why:* the report is marked confidential, so it stays out of GitHub (`private\` is ignored).
Write down each finding's ID, title, status and risk, especially any about throttling or
rate limiting, protecting the public endpoint, caching, or the cost of reads.

**22. Decision point: check the review supports our fix.** The rules say: *"Pick one
recommendation from the review, implement it."* Our fix (cache reads with CloudFront and limit
POST) answers a finding about throttling or protecting the public endpoint.
⚠ If the review recommends neither, **stop and send me the findings list** before going on.

---

## F. Apply the fix

**23. Swap in the "after" template**
```powershell
Copy-Item fix\template-after.yaml template.yaml
git diff --stat
```
*What it does:* replaces `template.yaml` with the version that adds CloudFront and the POST limit.
Expected: `template.yaml | 76 +` (76 lines added, none removed).

**24. Check, build, deploy**
```powershell
sam validate --lint --region ap-southeast-2 --profile wardwatch
sam build
sam deploy --profile wardwatch
```
*What it does:* checks the template, packages the code with Python 3.12, and updates the live stack.
Expected: `valid SAM Template`, `Build Succeeded`, then a change list that adds
`ReportsCachePolicy` and `WardWatchCdn` and modifies the API stage. Type `y` at
"Deploy this changeset?". **CloudFront takes 5 to 15 minutes**, so don't press Ctrl+C. Finishes
with `Successfully created/updated stack - wardwatch`.

**25. Save the CloudFront address**
```powershell
$cdn = aws cloudformation describe-stacks --stack-name wardwatch --region ap-southeast-2 --profile wardwatch --query "Stacks[0].Outputs[?OutputKey=='CloudFrontReportsUrl'].OutputValue" --output text
$cdn
(Invoke-WebRequest -Uri $cdn -UseBasicParsing).Headers["X-Cache"]
(Invoke-WebRequest -Uri $cdn -UseBasicParsing).Headers["X-Cache"]
```
*What it does:* gets the new public address and fetches it twice, showing whether CloudFront
answered from its cache.
Expected: `https://dxxxxxxxx.cloudfront.net/reports`, then `Miss from cloudfront`, then
`Hit from cloudfront`.
⚠ A `403`/`Forbidden` here means a CloudFront setting problem. Send me the output.

---

## G. Measure the "after"

**26. Residents' rush through CloudFront**
```powershell
python scripts\burst_test.py $cdn -n 100 -c 8 --label after-cdn --save evidence\burst-after-cdn.json
```
Expected: `200` x 100, **no `429`**, cache **Hit** about 99 and **Miss** about 1.

**27. Lambda runs for that rush** (wait 2 minutes)
```powershell
python scripts\count_lambda_runs.py evidence\burst-after-cdn.json
```
Expected: about `1` to `3` (before it was about 100).

**28. Spam test, after** (wait 3 minutes after step 26)
```powershell
python scripts\burst_test.py $cdn -n 30 -c 8 --post-sample --label post-spam-after --save evidence\post-spam-after.json
```
Expected: roughly `201` x 5 to 10 and the rest `429`. Spam is stopped.
⚠ The exact split varies per run; report what you get.

**29. Someone skipping CloudFront** (wait 1 minute)
```powershell
python scripts\burst_test.py $api -n 100 -c 8 --label after-direct --save evidence\burst-after-direct.json
```
Expected: roughly 20 to 40 `200` and the rest `429`. The backstop protects the raw API URL.

**30. Normal use still works**
```powershell
Invoke-RestMethod -Uri $cdn | Select-Object count
```
Expected: a number (your reports plus the test ones). Then open `frontend\index.html`, paste
`$cdn`'s address, Save URL, Refresh, and submit one real report. It should say "Report saved".
**Record steps 26 to 30 for the video.**

**31. Re-run the review ("after").** Open a **new** Agent chat, use the same
`/aws-well-architected-review` + prompt as step 20, and save the result as `private\review-after.md`.
Compare the findings from step 21: what changed in status, risk and score. Screenshot it.

**32. Remove the test reports**
```powershell
python scripts\delete_test_reports.py --profile wardwatch --region ap-southeast-2
```
*What it does:* finds only reports whose text starts with "Burst test report" and asks before
deleting them. Real reports are never touched.
Expected: `found NN test report(s)`, type `y`, then `Deleted NN test report(s)`.

---

## H. Save, write, record, submit

**33. Fill the results table** in `README.md` ("Results" section) with your real numbers from
the `evidence\*.json` files and the review notes. Don't paste the whole review report.

**34. Upload the "after" version**
```powershell
git status
git add template.yaml evidence README.md
git commit -m "Cache public reads with CloudFront, rate-limit only POST (Well-Architected review)"
git tag after
git push origin main --tags
```
*What it does:* saves the fix, labels it `after`, and uploads it.
Expected: nothing from `private` listed in `git status`, and the push ends with `after -> after`.
Your diff link for the write-up:
`https://github.com/YOUR-GITHUB-NAME/wardwatch/compare/before...after`

**35. Write the write-up** following GUIDE.md 8.2. Required by the rules: what you built, the
recommendation the skill surfaced, why you chose it, and what you changed.

**36. Make the video (3:00 or less)** following GUIDE.md 8.3. Required by the rules: show the
state the review flagged, the change, and the improved result. Upload to YouTube as Unlisted.

**37. Submit** on the hackathon page
(https://builder.aws.com/build/hackathons/7a94862a-95ea-37c2-9644-710d158a1316/let-the-agent-review-you):
join the hackathon if you haven't, then create your project post with the write-up, the video
link and the GitHub link. Before **Dec 1, 1:29 PM IST**.
⚠ I couldn't see the logged-in submission form. Follow the page's "Create post" / project flow,
and check that the video and repo links open in a private browser window.

**38. After judging:** delete everything (CloudFront makes this take 10 to 20 minutes):
```powershell
sam delete --stack-name wardwatch --region ap-southeast-2 --profile wardwatch
```
