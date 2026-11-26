# WardWatch: step-by-step guide for Abhishek (Windows 11 + PowerShell)

This guide is written for **your exact setup**. Do one step, check that you see what the
guide says you should see, then move on. If something looks different, look in
**Troubleshooting** at the bottom.

| Thing | Your value |
|---|---|
| Project folder | `C:\Users\tella\aws-hackathon\wardwatch` |
| AWS account | `733437129979` (a Free plan **project** account, "My First Project") |
| CLI profile | `wardwatch` |
| Region for **everything you build** | `ap-southeast-2` (Sydney) |
| Region for the **Agent Toolkit** commands only | `us-east-1` |
| Python for this project | 3.12.10 (start it with `py -3.12`; plain `python` is 3.14) |
| Lambda "at once" limit | 10 (so every burst test uses `-c 8`) |
| Other stack in this account | `student-portal` (leave it alone; the review must cover `wardwatch` only) |
| Deadline | Dec 1, 1:29 PM IST |

> **Doing the remaining steps?** Follow `CHECKLIST.md` top to bottom. This guide is the
> detailed reference behind it.

---

## Words you will see (read once)

* **AWS account / project:** your space in Amazon's cloud. You signed up with the newer
  "AWS experience", so your account lives inside a **project**. You sign in with your
  Builder ID (no root user, no IAM user needed). Settings live at https://settings.aws.com.
* **Region:** which AWS data centre city your things run in. Your project is locked to
  **ap-southeast-2 (Sydney)**. AWS picked it from your address (India maps to Sydney).
  Building anything in another Region is blocked by a rule AWS manages for you.
* **IAM (Identity and Access Management):** the part of AWS that decides *who* may do
  *what*. A **role** is a set of permissions that a person or a program can use. A
  **policy** is a list of allowed actions, like "may write to table X".
* **CLI (Command Line Interface):** typing commands instead of clicking. The **AWS CLI** is
  the `aws` command.
* **CLI profile:** a named set of saved login details on your PC. Yours is `wardwatch`.
  Adding `--profile wardwatch` to a command means "use that login".
* **Lambda:** runs a small piece of your Python code only when someone calls it. No server
  to look after.
* **API Gateway:** the front door. It gives you a public web address (URL) and passes each
  request to the right Lambda.
* **DynamoDB:** the database. It stores every report as an item in a table.
* **SAM (Serverless Application Model):** a tool that reads `template.yaml` (a list of
  everything the app needs) and creates all of it in AWS. `sam build` packages the code,
  `sam deploy` sends it to AWS.
* **CloudFormation:** the AWS service SAM uses behind the scenes. One deploy makes one
  **stack** (a named group of resources). Ours is called `wardwatch`.
* **Virtual environment (venv):** a private folder of Python packages just for this project,
  so it always uses Python 3.12, not your default 3.14.
* **Throttling:** limiting how many requests per second are allowed. Extra requests get
  error `429 Too Many Requests`.
* **CloudFront / cache:** Amazon's worldwide network of servers that can keep a short-lived
  copy of an answer and hand it out to many people, so your API doesn't have to answer each
  one. (Used in the fix, Phase 7.)
* **MCP server:** a plug-in that lets the AI agent in Cursor talk to AWS (read docs, check
  your resources). **Skill:** a set of expert instructions the agent follows, like the
  Well-Architected review.

### Will this cost money?
No. You are on the **Free plan**: AWS cannot charge your card on this plan. Usage is taken
from your **$160 of credits**, and this project uses a few cents of them at most. We use
nothing with an hourly fee (no WAF, no NAT, no EC2, no databases that run all day). Two
things to know:
* The Free plan lasts 6 months or until credits run out. Don't upgrade to the Paid plan for
  this hackathon. You don't need to.
* Delete the stack after judging (Phase 9) so nothing keeps using credits.

---

## Phase 0: Check your tools (already done, just confirm)

Open **PowerShell** (Start menu, type "PowerShell"). Run each line. The right-hand column is
what you told me you have.

| Command | What it does | You should see |
|---|---|---|
| `py -3.12 --version` | Asks the Python launcher for Python 3.12 | `Python 3.12.10` |
| `aws --version` | Shows the AWS CLI version | `aws-cli/2.42.4 ...` |
| `sam --version` | Shows the SAM CLI version | `SAM CLI, version 1.174.1` |
| `git --version` | Shows the Git version | `git version 2.52...` |
| `uv --version` | Shows uv (needed by the Agent Toolkit's MCP server) | `uv 0.x.x` |

If `uv` is missing, install it, then **close and reopen PowerShell**:

```powershell
winget install --id astral-sh.uv -e
```

(`winget` is Windows' built-in app installer. `--id` names the exact package, `-e` means
"exact match only".)

Also have **Cursor** installed and signed in with the account linked to your X Premium plan.

---

## Phase 1: AWS CLI login (already done, just confirm)

You already ran `aws login` and answered **y** to switching the profile to `ap-southeast-2`.
That was the right answer: your project can only build in Sydney.

```powershell
aws sts get-caller-identity --profile wardwatch
```

*What it does:* asks AWS "who am I?" using the `wardwatch` login. It changes nothing.

You should see your account and a role, like:

```json
{
    "UserId": "AROA...:...",
    "Account": "733437129979",
    "Arn": "arn:aws:sts::733437129979:assumed-role/AccountFullAccessRole/..."
}
```

```powershell
aws configure get region --profile wardwatch
```

*What it does:* prints the Region saved in your profile. You should see `ap-southeast-2`.

**Your login lasts up to 12 hours.** When a command later says `ExpiredToken` or
`Unable to locate credentials`, log in again:

```powershell
aws login --profile wardwatch
```

*What it does:* opens the browser, you pick "My First Project", and the CLI gets fresh
temporary keys. No passwords or secret keys are saved on your PC.

> You do **not** need to create an IAM user or use access keys. On project accounts AWS
> manages human access for you, and your Builder ID login is the safe, recommended way.

---

## Phase 2: Put the code on your PC, test it, push it to GitHub

### 2.1 Unzip

1. Make the folder `C:\Users\tella\aws-hackathon` if it does not exist.
2. Right-click `wardwatch.zip` > **Extract All...** > choose `C:\Users\tella\aws-hackathon` > Extract.
   The zip already contains a `wardwatch` folder, so you end up with
   `C:\Users\tella\aws-hackathon\wardwatch\template.yaml`. (If you get `wardwatch\wardwatch\`,
   move the inner folder up one level.)

```powershell
cd C:\Users\tella\aws-hackathon\wardwatch
dir
```

*What it does:* `cd` moves PowerShell into the project folder. `dir` lists what is inside.
You should see `template.yaml`, `src`, `tests`, `scripts`, `frontend`, `GUIDE.md`, `FIX.md`.

### 2.2 Make a Python 3.12 virtual environment (important for `sam build`)

`sam build` checks that a Python matching the Lambda runtime (3.12) is the `python` it
finds. Your default `python` is 3.14, so we make a 3.12 venv and switch it on.

```powershell
py -3.12 -m venv .venv
```

*What it does:* creates a hidden folder `.venv` holding a private copy of Python 3.12.

```powershell
.\.venv\Scripts\Activate.ps1
```

*What it does:* switches the venv on for this PowerShell window. Your prompt now starts
with `(.venv)`, and `python` now means 3.12.

If you see "running scripts is disabled on this system", run this once, type `Y`, and
try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

*What it does:* allows scripts you created on your own PC (like `Activate.ps1`) to run.

Check:

```powershell
python --version
```

You should see `Python 3.12.10`. **Every time you open a new PowerShell window for this
project**, run `cd C:\Users\tella\aws-hackathon\wardwatch` and `.\.venv\Scripts\Activate.ps1` first.

### 2.3 Run the unit tests (proves the code works before touching AWS)

```powershell
python -m pip install -r requirements-dev.txt
```

*What it does:* installs the test tools (`pytest`, `moto`, `boto3`) into the venv only.

```powershell
python -m pytest -v
```

*What it does:* runs 33 small automatic checks of the code against a **fake** DynamoDB
(moto), so no AWS is involved. Last line should be `33 passed`.

### 2.4 Push to GitHub (your public code link)

1. Go to https://github.com/new. Name `wardwatch`, choose **Public**, do **not** tick
   "Add a README". Click **Create repository**.
2. Back in PowerShell (replace `YOUR-GITHUB-NAME` and the email):

```powershell
git config --global user.name "Tella Abhishek"
git config --global user.email "you@example.com"
```

*What it does:* tells Git the name and email to put on your commits (one time per PC).

```powershell
git init
git add .
git status
```

*What it does:* `git init` turns the folder into a Git repository. `git add .` stages all
files for saving. `git status` lists them. Check that `.venv`, `.aws-sam` and `private`
are **not** listed (the `.gitignore` file keeps them out).

```powershell
git commit -m "WardWatch: before state (no API throttling)"
git branch -M main
git remote add origin https://github.com/YOUR-GITHUB-NAME/wardwatch.git
git push -u origin main
```

*What it does:* `commit` saves a snapshot. `branch -M main` names the branch `main`.
`remote add` links your folder to the GitHub repo. `push` uploads it. A browser window may
ask you to sign in to GitHub; that is normal.

```powershell
git tag before
git push origin before
```

*What it does:* puts a label called `before` on this exact version, so judges can compare
it with the fixed version later.

---

## Phase 3: Deploy to AWS with SAM

Make sure your prompt shows `(.venv)` (see 2.2).

### 3.1 Check and build

```powershell
sam validate --lint --region ap-southeast-2 --profile wardwatch
```

*What it does:* checks `template.yaml` for mistakes. Changes nothing in AWS.
You should see `...template.yaml is a valid SAM Template`.

```powershell
sam build
```

*What it does:* copies the code in `src\` into a hidden `.aws-sam` folder, ready to upload.
It uses the venv's Python 3.12. You should see `Build Succeeded`.

### 3.2 Deploy (guided, first time only)

```powershell
sam deploy --guided --region ap-southeast-2 --profile wardwatch
```

*What it does:* creates everything in `template.yaml` in your AWS account, asking you a
few questions first. Answer exactly like this:

| SAM asks | You type | Why |
|---|---|---|
| `Stack Name [sam-app]:` | `wardwatch` | The name of this group of resources. |
| `AWS Region [ap-southeast-2]:` | press Enter (it must say `ap-southeast-2`) | Your project can only build in Sydney. |
| `Parameter WardName [Ward 12]:` | press Enter, or type your ward's name | Just a label. |
| `Confirm changes before deploy [y/N]:` | `y` | SAM shows what it will create and waits for your OK. |
| `Allow SAM CLI IAM role creation [Y/n]:` | `Y` | Each Lambda needs its own small role. SAM makes them from the tight policies in the template. |
| `Disable rollback [y/N]:` | `N` | If something fails, AWS cleans up by itself. |
| `CreateReportFunction has no authentication. Is this okay? [y/N]:` (wording may be "may not have authorization defined") | `y` | Residents report without an account. Input checks protect it. |
| `ListReportsFunction has no authentication. Is this okay? [y/N]:` | `y` | The list is public on purpose. This open door is exactly what the review will look at. |
| `Save arguments to configuration file [Y/n]:` | `Y` | Saves your answers in `samconfig.toml`, so next time plain `sam deploy` is enough. |
| `SAM configuration file [samconfig.toml]:` | press Enter | |
| `SAM configuration environment [default]:` | press Enter | |

SAM then makes a small storage bucket for uploads (one time), shows a **changeset** (a list:
1 table, 2 functions, 2 roles, 1 API, 2 log groups and a few small API parts) and asks
`Deploy this changeset? [y/N]:`. Type `y`.

It takes 1 to 3 minutes. At the end you see **Outputs**. The important one is
`ReportsEndpoint`, which looks like:
`https://abc123xyz.execute-api.ap-southeast-2.amazonaws.com/prod/reports`

---

## Phase 4: Test it and record the "before" numbers

### 4.1 Put the URL in a variable

```powershell
$api = aws cloudformation describe-stacks --stack-name wardwatch --region ap-southeast-2 --profile wardwatch --query "Stacks[0].Outputs[?OutputKey=='ReportsEndpoint'].OutputValue" --output text
$api
```

*What it does:* reads the `ReportsEndpoint` output from your stack and keeps it in `$api`,
so you don't have to paste the long URL again. (Re-run it in every new window.)

### 4.2 Create a report (POST)

```powershell
$body = @{
  category    = "flooded_drain"
  description = "Drain near the bus stop is overflowing onto the road"
  area        = "Gandhi Nagar 2nd Cross"
  landmark    = "Opposite Ganesh Temple"
} | ConvertTo-Json

Invoke-RestMethod -Uri $api -Method Post -ContentType "application/json" -Body $body
```

*What it does:* builds a report as JSON and sends it to your API, like a resident pressing
"Submit". You should get the saved report back, with an `id`, `created_at` and `status: open`.

### 4.3 List reports (GET)

```powershell
Invoke-RestMethod -Uri $api | ConvertTo-Json -Depth 5
```

*What it does:* asks the API for the list of reports and prints it neatly.

### 4.4 Check that bad input is rejected

```powershell
$bad = @{ category = "aliens"; description = "test"; area = "x" } | ConvertTo-Json
try { Invoke-RestMethod -Uri $api -Method Post -ContentType "application/json" -Body $bad }
catch { $_.ErrorDetails.Message }
```

*What it does:* sends a report with a made-up category. `try/catch` prints the error
instead of a red wall of text. You should see
`{"error": "Validation failed", "details": {"category": "must be one of: ..."}}`.

### 4.5 Add sample data and open the web page

```powershell
python scripts\seed_reports.py $api
```

*What it does:* posts 4 realistic sample reports so your demo isn't empty.

Now double-click `frontend\index.html`. Paste the `ReportsEndpoint` URL in the box, click
**Save URL**, then **Refresh**. Try submitting a report from the form too.

### 4.6 Burst test: the "before" numbers

Your account may run at most **10 Lambdas at the same time** (you checked:
`aws lambda get-account-settings --region ap-southeast-2 --profile wardwatch --query "AccountLimit.ConcurrentExecutions"`
printed `10`). So every burst test uses `-c 8` (8 at a time). With more than 10, Lambda itself
would refuse some requests and you'd see `500` errors, which would muddy the story. Don't use
the `student-portal` app while testing; it shares the same limit.

```powershell
python scripts\burst_test.py $api -n 10 -c 2
```

*What it does:* a small warm-up (10 requests, 2 at a time) so the first slow "cold start"
doesn't skew your numbers.

```powershell
mkdir evidence -Force
python scripts\burst_test.py $api -n 100 -c 8 --label before --save evidence\burst-before.json
```

*What it does:* fires 100 GET requests, 8 at a time, counts the answers by status code,
measures speed (p50 = typical, p95 = slow end), and saves the summary to a file.
Expected: **all 100 are `200`**, `0` x `429`, and "No X-Cache header" (no CloudFront yet).
Nothing stops a flood of requests. Take a screenshot for the video.

Wait 2 minutes, then ask AWS how many times the "list" Lambda ran during that burst:

```powershell
python scripts\count_lambda_runs.py evidence\burst-before.json
```

*What it does:* reads the burst's start time from the file and asks CloudWatch (AWS's metrics
service) for the Lambda run count in those minutes. Expected: about `100`.

Then the spam test (wait 3 minutes after the last burst so the counts don't mix):

```powershell
python scripts\burst_test.py $api -n 30 -c 8 --post-sample --label post-spam-before --save evidence\post-spam-before.json
```

*What it does:* tries to submit 30 test reports very fast. Before the fix, all 30 get `201`
(saved). Nothing stops spam. The test reports say "Burst test report ... (safe to ignore)";
you'll delete them later with `scripts\delete_test_reports.py`.

---

## Phase 5: Set up the Agent Toolkit in Cursor

The Agent Toolkit has two parts: **skills** (expert instructions saved on your PC) and the
**AWS MCP server** (lets the agent read AWS docs and look at your resources). Important for
your project account:

* The toolkit's own commands always use `--region us-east-1`. That's where the toolkit
  service lives, whatever your project Region is. AWS's setup file says so, and it works
  for project accounts too.
* The MCP server must be told to work in **ap-southeast-2**. Otherwise it defaults to
  us-east-1, where your project is blocked and your app doesn't exist.

### 5.1 Let Cursor's agent run the setup

1. Open Cursor > **File > Open Folder** > `C:\Users\tella\aws-hackathon\wardwatch`.
2. Open the Agent chat (Ctrl+L), make sure it is in **Agent** mode, pick a Grok model, and
   paste this one message (it already answers the setup's questions):

   ```
   Set up Agent Toolkit for AWS by following instructions: https://raw.githubusercontent.com/aws/agent-toolkit-for-aws/refs/heads/main/setup-instructions/setup.md
   My answers: profile name is wardwatch. Yes, I use the new AWS experience (I have a project, "My First Project"). My project Region is ap-southeast-2. I'm on Windows. The AWS CLI 2.42.4 is installed and I'm already logged in with aws login --profile wardwatch, so skip installing the CLI and skip logging in again unless get-caller-identity fails.
   ```

3. Click **Run/Allow** when the agent asks to run a command. What it does, step by step:
   * `aws sts get-caller-identity --profile wardwatch`: checks that your login works.
   * `aws configure agent-toolkit --yes --region us-east-1 --profile wardwatch`: the setup
     wizard. It installs the AWS skills into Cursor (in `%USERPROFILE%\.cursor\skills\`) and
     adds an `aws-mcp` server to `%USERPROFILE%\.cursor\mcp.json`.
     **If it fails with exit code 253 or "requires interactive terminal"**, run that same
     command yourself in PowerShell, answer its questions (choose Cursor), then tell the
     agent "done".
   * Adds your profile to the `aws-mcp` entry (so it doesn't look for a `default` profile).
   * `aws agent-toolkit list-available-skills --region us-east-1 --profile wardwatch`:
     lists the skills, to prove the toolkit works.
   * Saves AWS rules into `.cursor\rules\` (for project accounts, the "starter" rules).

### 5.2 Check the MCP settings yourself (2 small edits)

Open `%USERPROFILE%\.cursor\mcp.json` in Cursor (File > Open File, paste
`C:\Users\tella\.cursor\mcp.json`). Find the `aws-mcp` entry. It should look like this
**after** your edits. Add only the two marked things and leave everything else as the wizard
wrote it:

```json
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
```

* `"AWS_REGION=ap-southeast-2"` (the extra line inside `args`): tells the MCP server to run
  AWS calls in your project Region. Without it, they go to us-east-1 and get denied.
* `"env": { "AWS_MCP_PROXY_PROFILES": "wardwatch" }`: tells it which login to use.
* The `us-east-1` in the URL is fine: it is only where the MCP server itself runs. (AWS also
  runs one in Sydney, `https://aws-mcp.ap-southeast-2.api.aws/mcp`, and you may use that
  URL instead. Either works.)
* Keep the commas exactly as shown. A missing comma breaks the file.

### 5.3 Confirm the review skill is installed

```powershell
aws agent-toolkit list-available-skills --region us-east-1 --profile wardwatch | Select-String "well-architected"
```

*What it does:* lists the toolkit's skills and shows only lines containing
"well-architected". You should see `aws-well-architected-review`.

```powershell
dir $HOME\.cursor\skills
```

*What it does:* lists the skills installed for Cursor. Look for `aws-well-architected-review`.

### 5.4 Restart Cursor and confirm

1. Close Cursor completely (File > Exit) and open it again on the wardwatch folder.
2. Open **Customize** in the left sidebar. Under MCP, `aws-mcp` should be switched **on**
   with no error. If it shows an error: View > Output (Ctrl+Shift+U), choose **MCP Logs** in
   the dropdown, and read the last red line (see Troubleshooting).
3. In the Agent chat, type `/` and start typing `aws-well-architected-review`. If it appears
   in the list, Cursor has loaded the skill.

---

## Phase 6: Run the review (the "before" review)

1. Open a **new** Agent chat in Cursor (with the wardwatch folder open). Paste:

   Type `/aws-well-architected-review`, pick it from the list, then paste this after it:

   ```
   Use the Well-Architected Review skill of Agent Toolkit to review this project. Scope: only this repository and the CloudFormation stack named wardwatch in ap-southeast-2 (AWS profile wardwatch). Do not review any other stack in the account, such as student-portal. Do not change any files or AWS resources; this is a review only.
   ```

   The first sentence is the hackathon's own recommended wording. Picking the skill with `/`
   makes sure Cursor uses the real Agent Toolkit skill, not a lookalike review.

   If it asks which mode or pillars, pick a full review (or Security, Reliability and Cost
   Optimization). Let it read the files and, if it asks, look at your deployed stack. Click
   Allow for read-only AWS calls.
2. The report shows up in the chat. It is marked **CONFIDENTIAL**, so **do not commit it**.
   Make a folder called `private` in the project (Git already ignores it), create
   `private\review-before.md`, and paste the whole report in. Take screenshots of the
   summary, the scores and the throttling finding.
3. Write down:
   * The maturity score (1 to 5) for each pillar.
   * How many Critical / High / Medium / Low findings it found.
   * The findings about the **public GET /reports endpoint**: missing throttling / rate
     limiting (often REL05-BP02), protecting the endpoint, caching, or cost of reads. Note
     each one's ID, status (like "Not Implemented") and risk (like High). Our fix (Phase 7)
     must answer a finding the review really made.
   * What it praised (encryption, least privilege, input validation, logs). Judges like
     seeing that the review gave credit too.
4. If the review doesn't mention the public endpoint at all, ask in the same chat:
   "Which findings relate to the public GET /reports endpoint?". Only implement a fix that
   the review actually recommends. That is the hackathon rule.

---

## Phase 7: Apply the fix, redeploy, measure again

**The idea (read FIX.md for the full story):** the obvious fix, a rate limit on the public
list, would turn residents away during the exact flood they need the app for. So instead:
* **CloudFront** (Amazon's worldwide cache network) sits in front of the API and keeps a copy
  of the report list for 30 seconds. A rush of residents is answered from that copy, so
  there are no `429`s and almost no load on Lambda and DynamoDB.
* **Only new reports (POST)** get a strict limit, to stop spam.
* A backstop limit protects the raw API URL if someone skips CloudFront.

CloudFront is allowed on your Free plan project and free at this size (see FIX.md).

Your prompt must show `(.venv)` for these steps.

### 7.1 Apply the change

```powershell
Copy-Item fix\template-after.yaml template.yaml
git diff --stat
```

*What it does:* replaces `template.yaml` with the ready-made "after" version. `git diff --stat`
shows which files changed and how many lines. (If you'd rather type the change yourself to
learn it, follow the three edits in FIX.md instead.)

### 7.2 Check, build, deploy

```powershell
sam validate --lint --region ap-southeast-2 --profile wardwatch
sam build
sam deploy --profile wardwatch
```

*What it does:* checks the new template, packages the code, and updates your stack. It
reuses your saved answers from `samconfig.toml`. Type `y` at "Deploy this changeset?". The
changeset now also lists a CloudFront **CachePolicy** and **Distribution**.
**Be patient: CloudFront usually takes 5 to 15 minutes to finish.** That's normal.

### 7.3 Save both URLs in variables

```powershell
$api = aws cloudformation describe-stacks --stack-name wardwatch --region ap-southeast-2 --profile wardwatch --query "Stacks[0].Outputs[?OutputKey=='ReportsEndpoint'].OutputValue" --output text
$cdn = aws cloudformation describe-stacks --stack-name wardwatch --region ap-southeast-2 --profile wardwatch --query "Stacks[0].Outputs[?OutputKey=='CloudFrontReportsUrl'].OutputValue" --output text
$cdn
```

*What it does:* `$api` is the raw API Gateway URL (as before). `$cdn` is the new CloudFront
URL, like `https://d1234abcd.cloudfront.net/reports`. **Residents use `$cdn` from now on.**
Paste it into `frontend\index.html` (Save URL) too.

Quick check that it works and is cached (run it twice):

```powershell
(Invoke-WebRequest -Uri $cdn -UseBasicParsing).Headers["X-Cache"]
```

*What it does:* fetches the list through CloudFront and prints the `X-Cache` header. The
first time you'll probably see `Miss from cloudfront`, the second time `Hit from cloudfront`.

### 7.4 The residents' rush: burst test through CloudFront

Use the **same** `-n` and `-c` as your before run:

```powershell
python scripts\burst_test.py $cdn -n 100 -c 8 --label after-cdn --save evidence\burst-after-cdn.json
```

*What it does:* the same 100-request rush as before, but through CloudFront. It also counts
cache **Hits** (answered from the copy) and **Misses** (went all the way to Lambda + DynamoDB).
Expected: **100 x `200`, 0 x `429`**, almost all Hit, about 1 Miss. Run it 3 times.

### 7.5 Proof from AWS itself: how many times did Lambda run?

Wait 2 minutes after the 7.4 burst, then:

```powershell
python scripts\count_lambda_runs.py evidence\burst-after-cdn.json
```

*What it does:* same as in 4.6: asks CloudWatch how many times the "list" Lambda ran during
that burst. Before the fix it was about 100; now expect about 1 to 3 (one per cache miss).
This number comes from AWS itself, so it is strong proof for the judges.

### 7.6 Spam test: POST is limited

```powershell
python scripts\burst_test.py $cdn -n 30 -c 8 --post-sample --label post-spam-after --save evidence\post-spam-after.json
```

*What it does:* tries to submit 30 test reports very fast (8 at a time). Expected: about 5 to
10 x `201` (saved) and the rest `429` (blocked as spam). The test reports say "Burst test
report ... (safe to ignore)".

### 7.7 Bypass test: the raw API URL has a backstop

```powershell
python scripts\burst_test.py $api -n 100 -c 8 --label after-direct --save evidence\burst-after-direct.json
```

*What it does:* the rush again, but skipping CloudFront. Expected: about 20 to 40 `200` and the
rest `429`. Shows that someone who skips the cache still can't hammer the database.

### 7.8 A normal visit and a normal report still work

```powershell
Invoke-RestMethod -Uri $cdn | Select-Object count
Invoke-RestMethod -Uri $cdn -Method Post -ContentType "application/json" -Body $body
```

*What it does:* one ordinary read and one ordinary report through CloudFront (re-create
`$body` as in 4.2 if this is a new window). Both should simply work.

### 7.9 Re-run the review

Open a **new** Cursor Agent chat and use the same `/aws-well-architected-review` + prompt as Phase 6. Save the result as
`private\review-after.md`. Compare the findings about throttling, protecting the public
endpoint and caching, plus the scores. Note what the review says about the trade-offs too.

### 7.10 Save and tag the fix

```powershell
git status
git add template.yaml evidence README.md
git commit -m "Cache public reads at the edge with CloudFront, rate-limit only POST (Well-Architected review)"
git tag after
git push origin main --tags
```

*What it does:* `git status` lets you check that nothing from `private\` is listed. The rest
saves the fix, labels it `after`, and uploads it with both tags.

---

## Phase 8: Evidence, write-up and video

### 8.1 Numbers table (fill in with your real numbers)

| Measure | Before | After |
|---|---|---|
| Residents' rush: 100 GETs, 8 at a time: `200 OK` | 100 (via API) | 100 (via CloudFront) |
| Residents' rush: `429` | 0 | 0 |
| Cache Hit / Miss | n/a | (e.g. 99 / 1) |
| `ListReportsFunction` runs for that rush (CloudWatch) | (about 100) | (about 1) |
| p50 / p95 latency (ms) | | |
| Spam: 30 POSTs, 8 at a time: `201` / `429` | 30 / 0 | (e.g. 7 / 23) |
| Bypass: 100 GETs to raw API URL: `200` / `429` | 100 / 0 | (e.g. 24 / 76) |
| Review findings on throttling / protection / caching | | |
| Maturity score (relevant pillar) | | |
| Cost per million abusive GETs (FIX.md estimate) | ~$4.20 | ~$1.20 (first 10 M/month free) |

Don't round numbers to make them look better. Honest numbers win trust.

### 8.2 Write-up outline (short)

1. **Hook:** "Last monsoon, my ward's drainage WhatsApp group was just photos and rumours."
2. **What I built:** WardWatch, the architecture picture, what is public and why.
3. **What the review found:** scores, top findings, what it praised, and the one I acted on
   (quote the title and ID, not the whole confidential report).
4. **The twist:** "The obvious fix, rate limits, would block residents during the exact flood
   they need the app for." Explain the split: cache the reads, limit the writes.
5. **The fix:** CloudFront with a 30-second cache for `GET /reports`, a strict limit on
   `POST /reports`, and a backstop on the raw API. Link the diff:
   `https://github.com/YOUR-GITHUB-NAME/wardwatch/compare/before...after`
6. **Proof:** the numbers table (no 429s for residents, about 1 Lambda run instead of 100,
   spam blocked) and the re-run review.
7. **Honest trade-offs:** up to 30 seconds stale, the raw API URL still exists (backstop plus
   a planned secret-header check), cache-busting via query strings, and no paid WAF.
8. **Links:** repo and video.

### 8.3 Video plan (3:00 max)

Record with the Windows **Snipping Tool** (Win + Shift + R) or OBS. Upload to YouTube as
**Unlisted**.

| Time | Show | Say |
|---|---|---|
| 0:00 to 0:15 | WhatsApp-style photo chaos (or a slide) | The hook line and the problem |
| 0:15 to 0:35 | `frontend\index.html`: submit and view a report | What WardWatch does, who it helps |
| 0:35 to 1:00 | Cursor running the review: scores and findings | What it found, what it praised |
| 1:00 to 1:20 | Before burst: 100/100 hit Lambda, CloudWatch shows ~100 runs | Nothing protects it, and every visit scans the database |
| 1:20 to 1:40 | Slide: "rate limit = residents get 429 during the flood" | The twist: the obvious fix hurts the people it's for |
| 1:40 to 2:00 | The diff: cache policy + distribution + POST limit, `sam deploy` | Cache the reads, limit the writes |
| 2:00 to 2:30 | After: CloudFront burst 100/100 OK, 99 Hit; CloudWatch ~1 run; POST spam gets 429 | No resident blocked, database calm, spam stopped |
| 2:30 to 2:45 | Re-run review | The agent's view after the fix |
| 2:45 to 3:00 | Numbers table and trade-offs | 30 s staleness, next steps, thanks |

Practise once with a timer. Stay under 3:00.

---

## Phase 9: Clean up (after judging ends)

```powershell
sam delete --stack-name wardwatch --region ap-southeast-2 --profile wardwatch
```

*What it does:* deletes everything the stack created: CloudFront distribution, API,
functions, table (and its data), roles and log groups. Type `y` to both questions. With
CloudFront this can take 10 to 20 minutes, because CloudFront must switch off everywhere
first.

Optional: in the AWS console (Sydney Region), open **CloudFormation** and delete the stack
`aws-sam-cli-managed-default`. That is SAM's upload bucket; empty the bucket first if asked.

---

## Troubleshooting

| You see | What it means | Fix |
|---|---|---|
| `Binary validation failed for python ... runtime: python3.12` during `sam build` | `sam build` found Python 3.14, not 3.12 | Switch the venv on: `.\.venv\Scripts\Activate.ps1`, check `python --version` says 3.12.10, run `sam build` again. |
| `... with an explicit deny in a service control policy` | Something tried to use a Region other than ap-southeast-2 (often us-east-1) | Add `--region ap-southeast-2` to the command. Check `aws configure get region --profile wardwatch`. For the agent, check `AWS_REGION=ap-southeast-2` in `mcp.json` (5.2). |
| `Unable to locate credentials` / `ExpiredToken` / `security token included in the request is expired` | Your 12-hour login ran out, or you forgot `--profile wardwatch` | `aws login --profile wardwatch` |
| `aws: The term 'aws' is not recognized` (same for `sam`, `git`, `uv`) | Window opened before the install, or not installed | Close PowerShell, open a new one. If still missing, install with winget. |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | Windows script policy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, type `Y`. |
| `Stack ... is in ROLLBACK_COMPLETE state and can not be updated` | The first deploy failed | `sam delete --stack-name wardwatch --region ap-southeast-2 --profile wardwatch`, read the first red error in the deploy output, fix it, deploy again. |
| `Error: No changes to deploy` | Nothing changed since the last deploy | Not a problem. |
| Burst "before" shows `500` or `502` | Lambda's at-once limit (often 10 on new accounts) | Use `-c 8` (see 4.6) for every run. Don't use `student-portal` during tests. |
| Bypass burst (raw `$api`) or POST spam still all `200`/`201` after the fix | New limits not live yet, or not deployed | Wait a minute. Check `sam deploy` ended with `UPDATE_COMPLETE`. Check `MethodSettings` sits under `Properties:` of `WardWatchApi` with the same indent as `StageName`. |
| CloudFront URL returns `{"message":"Forbidden"}` or 403 | Usually the Host header was forwarded, or the URL path is wrong | Use `CloudFrontReportsUrl` exactly (ends in `/reports`). Check `OriginRequestPolicyId` is `b689b0a8-53d0-40ab-baf2-68738e2966ac` and `OriginPath` is `/prod`. |
| `sam deploy` sits on `CREATE_IN_PROGRESS AWS::CloudFront::Distribution` for ages | CloudFront takes 5 to 15 minutes to spread worldwide | Wait. Don't press Ctrl+C. |
| Burst through CloudFront shows many `Miss` | The cache was empty or expired, or `limit`/`next` differ | Run it again right away. Same URL, same query string, within 30 s, should be mostly `Hit`. |
| A new report doesn't show in the list | The list is cached for up to 30 s (by design) | Wait 30 s and Refresh. The form already shows your own new report at the top. |
| `{"message":"Missing Authentication Token"}` | Wrong URL (missing `/prod/reports`) | Use the `ReportsEndpoint` output exactly (`$api`). |
| Web page: "Could not reach the API" | Empty or wrong URL in the box | Paste `ReportsEndpoint`, click Save URL. |
| Toolkit wizard: exit code 253 / "requires interactive terminal" | Cursor's terminal can't answer questions | Run `aws configure agent-toolkit --yes --region us-east-1 --profile wardwatch` in your own PowerShell. If `--yes` is "not recognized", leave it out. |
| `list-available-skills` gives `AccessDenied` | The toolkit catalog call was refused | Not a blocker. The skill can still be loaded through the MCP server (`aws___retrieve_skill`). Or install it by hand: download https://github.com/aws/agent-toolkit-for-aws (Code > Download ZIP), copy `skills\core-skills\aws-well-architected-review` into `C:\Users\tella\.cursor\skills\`, restart Cursor. |
| MCP error `-32602: Invalid request parameters("")` or `No AWS credentials available` | `aws-mcp` can't find your login | Check the `env` block in `mcp.json` (5.2). Run `aws login --profile wardwatch`. Restart Cursor. |
| `aws-mcp` shows an error in Cursor's Customize panel | `uv` missing or a typo in `mcp.json` | `uv --version`. Check the commas in `mcp.json`. Restart Cursor. |
| A service suddenly says AccessDenied that worked before | Free plan limits | Run `aws freetier get-account-plan-state --region us-east-1 --profile wardwatch`. Everything WardWatch uses (Lambda, API Gateway, DynamoDB, CloudFormation, CloudWatch Logs, IAM, S3) is on the Free plan list. |
