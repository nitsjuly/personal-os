# DEPLOY_WINDOWS.md — Personal OS Deployment Guide
# Windows Task Scheduler + Local Python Environment

---

## What this repo runs automatically

| Script | When | What it does |
|--------|------|-------------|
| `savvas_refresh_token.py` | 6:30 AM daily | Playwright login → captures fresh Bearer token → saves to .env |
| `run_school.py --mode=morning` | 7:00 AM daily | Fetches Canvas + Savvas → sends email digest to student + parents |
| `run_school.py --mode=evening` | 8:00 PM daily | Sends nudge ONLY if something urgent (overdue or due today/tomorrow) |
| `agents/finance_agent.py --mode=weekly` | Monday 8:00 AM | Anomaly check → sends alert if anything above threshold |

Finance monthly report and health reminders are not yet scheduled
(they require data hookup first — see V2_SETUP_GUIDE.md).

---

## Prerequisites

Before starting:
- Python 3.11+ installed and on PATH
- Git installed (optional but recommended)
- A Gmail account with App Passwords enabled (for sending email)
- Your Canvas API token (Settings → New Access Token in Canvas)
- Your Savvas/Clever login credentials

---

## Step 1 — Download and unzip the repo

Unzip `personal-os-github.zip` to a folder you'll keep permanently.
Example: `C:\Users\YourName\personal-os`

**Important:** Do not put it in a folder that syncs to cloud (OneDrive, Google Drive).
The Playwright browser profile in `data/` is large and should stay local.

---

## Step 2 — Create your Python virtual environment

Open Command Prompt (`cmd`) as a regular user (not Admin).

```bat
cd C:\Users\YourName\personal-os
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
playwright install chromium
```

Verify it works:
```bat
python run_school.py --test
```

Expected output: a console report with mock data. No emails sent.

---

## Step 3 — Create the private/ folder and add your reference files

This is where your personal family data lives — it is **gitignored** and will
never be committed to GitHub, but the agents read from it at runtime.

```bat
cd C:\Users\YourName\personal-os
mkdir private
echo. > private\.gitkeep
```

Your folder should now look like this:
```
personal-os\
├── private\
│   └── .gitkeep        ← placeholder so the folder exists; contents are gitignored
├── agents\
├── tools\
├── docs\
...
```

Now copy your three reference files from `personal-os-private.zip` into `private\`:

```
personal-os\
└── private\
    ├── .gitkeep
    ├── account-structure.md     ← copy from personal-os-private.zip
    ├── family-constraints.md    ← copy from personal-os-private.zip, fill in your rules
    └── health-roster.md         ← copy from personal-os-private.zip, fill in your data
```

Open each `.md` file in Notepad and fill in your real information.
The templates have comments explaining every field.

Then add the paths to your `.env` (next step):
```
HEALTH_ROSTER_PATH=private\health-roster.md
FAMILY_CONSTRAINTS_PATH=private\family-constraints.md
```

**Verify gitignore is protecting private/:**
```bat
git status
```
You should NOT see the `.md` files inside `private\` listed.
If you do, stop — check that `.gitignore` contains the line `private/` before continuing.

---

## Step 4 — Create your .env file

Copy the template:
```bat
copy .env.template .env
```

Open `.env` in Notepad and fill in **all** values:

```
CANVAS_TOKEN=your_canvas_api_token
CANVAS_URL=https://browardschools.instructure.com
CANVAS_CAREER_TECH_ID=1960295
CANVAS_SCIENCE_ID=1959399

CLEVER_USERNAME=studentid@my.browardschools.edu
CLEVER_PASSWORD=yourpassword

AK_EMAIL=student@gmail.com
PARENT1_EMAIL=you@gmail.com
PARENT2_EMAIL=spouse@gmail.com

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=xxxx xxxx xxxx xxxx    ← Gmail App Password (16 chars, 4 groups)
FROM_EMAIL=you@gmail.com

SCHOOL_TESTING_RUNS=5
```

**Getting a Gmail App Password:**
1. Go to myaccount.google.com → Security → 2-Step Verification (must be ON)
2. Search "App passwords" → Create one named "Personal OS"
3. Copy the 16-character password into SMTP_PASS

**Getting your Canvas API token:**
1. Log into Canvas as the student
2. Account → Settings → scroll to "Approved Integrations"
3. Click "+ New Access Token" → copy the token

---

## Step 5 — Run the first Savvas token refresh

```bat
cd C:\Users\YourName\personal-os
venv\Scripts\activate.bat
python savvas_refresh_token.py
```

Expected output:
```
  Navigating to Savvas...
  Full login required...
  ✅ Token captured (full login)
  Saved to .env: Bearer eyJ...
```

If it hangs or fails, see Troubleshooting below.
After success, `SAVVAS_TOKEN=Bearer eyJ...` will appear in your `.env`.

---

## Step 6 — Test the full morning run

```bat
python run_school.py --mode=morning
```

This sends a real email. Check your inbox.
If you see `[EMAIL] To: ...` printed instead of "Sent", SMTP is not configured —
check SMTP_USER, SMTP_PASS, and that Gmail App Password is correct.

---

## Step 7 — Edit the batch scripts

Open each file in `scripts/` and replace `C:\path\to\personal-os` with your actual path:

**scripts\refresh_token.bat:**
```bat
@echo off
cd /d "C:\Users\YourName\personal-os"
call venv\Scripts\activate.bat
python savvas_refresh_token.py >> logs\refresh.log 2>&1
```

**scripts\school_morning.bat:**
```bat
@echo off
cd /d "C:\Users\YourName\personal-os"
call venv\Scripts\activate.bat
python run_school.py --mode=morning >> logs\school_morning.log 2>&1
```

**scripts\school_evening.bat:**
```bat
@echo off
cd /d "C:\Users\YourName\personal-os"
call venv\Scripts\activate.bat
python run_school.py --mode=evening >> logs\school_evening.log 2>&1
```

Create the logs folder:
```bat
mkdir logs
```

---

## Step 8 — Create Task Scheduler tasks

Open Task Scheduler: Start menu → search "Task Scheduler"

Create **3 tasks** (one at a time). For each, use **"Create Task"** (not Basic Task —
you need the full settings).

---

### Task 1: Savvas Token Refresh — 6:30 AM

**General tab:**
- Name: `PersonalOS - Refresh Token`
- Run whether user is logged on or not: ✅
- Run with highest privileges: ✅ (needed for network access)
- Configure for: Windows 10

**Triggers tab → New:**
- Begin the task: On a schedule
- Daily, start 6:30:00 AM
- Recur every 1 days ✅

**Actions tab → New:**
- Action: Start a program
- Program/script: `C:\Users\YourName\personal-os\scripts\refresh_token.bat`
- Start in: `C:\Users\YourName\personal-os`

**Settings tab:**
- Run task as soon as possible after a scheduled start is missed ✅
- Stop the task if it runs longer than: 10 minutes

**Conditions tab:**
- Start the task only if the computer is on AC power: ❌ uncheck this
- Wake the computer to run this task: ✅

---

### Task 2: Morning School Digest — 7:00 AM

Same settings as above, except:
- Name: `PersonalOS - Morning School`
- Trigger: 7:00 AM daily
- Program: `C:\Users\YourName\personal-os\scripts\school_morning.bat`

---

### Task 3: Evening School Nudge — 8:00 PM

Same settings as above, except:
- Name: `PersonalOS - Evening School`
- Trigger: 8:00 PM daily
- Program: `C:\Users\YourName\personal-os\scripts\school_evening.bat`
- Wake the computer: ❌ (not needed for evening — you're awake)

---

## Step 9 — Verify the tasks work

Right-click each task → **Run** → then check the log:
```bat
type logs\refresh.log
type logs\school_morning.log
```

If a task runs but produces no log, the `cd` path in the batch script is wrong.

---

## Step 10 — Run the evals

```bat
python evals\school_evals.py
python evals\finance_evals.py
```

All tests should pass before you rely on the system.
If any fail, check that `core\normalizer.py` is intact.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Savvas token refresh hangs at login | Credentials wrong or login flow changed | Run with `headless=False` (edit `savvas_refresh_token.py`, change `headless=True` → `False`) to see browser |
| Token captured but empty in .env | `.env` not writable | Run cmd as same user who owns the project folder |
| Email prints `[EMAIL] To:` but doesn't send | SMTP not configured | Check SMTP_PASS is a Gmail App Password (16 chars), not your Gmail password |
| Task Scheduler task "Ready" but never ran | "Run only if AC power" checked | Uncheck it in Conditions tab |
| Task ran but log is empty | Wrong `cd` path in batch script | Check your actual project path in the .bat file |
| Canvas returns 401 | Token expired | Log into Canvas → Settings → new access token |
| `ModuleNotFoundError: playwright` | Ran outside venv | Add `call venv\Scripts\activate.bat` before `python` in batch script |
| `SAVVAS_TOKEN not set` in morning run | Token refresh failed | Check `logs\refresh.log`, run `python savvas_refresh_token.py` manually |

---

## Resetting the Savvas browser profile

If the token refresh stops working (login flow changes, session corrupted):

```bat
rmdir /s /q data\savvas_browser_profile
python savvas_refresh_token.py
```

This forces a full login. Takes ~30 seconds instead of ~5.
After success, subsequent runs use the profile again (~5 seconds).

---

## Cloud alternative (if laptop is often off)

GitHub Actions runs for free and works even when your machine is off.
Limitation: Playwright in headless mode on Linux works, but the Savvas
login has only been tested on Windows. Use local Task Scheduler until the
system is stable, then migrate.

Basic GitHub Actions workflow (`.github/workflows/school.yml`):

```yaml
name: School OS
on:
  schedule:
    - cron: '30 11 * * 1-5'   # 6:30 AM EST (UTC-5) = 11:30 UTC, Mon-Fri
    - cron: '0 12 * * 1-5'    # 7:00 AM EST = 12:00 UTC
    - cron: '0 1 * * 1-5'     # 8:00 PM EST = 01:00 UTC next day
  workflow_dispatch:           # manual run button in GitHub UI

jobs:
  school:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt && playwright install chromium
      - run: python savvas_refresh_token.py
        env:
          CLEVER_USERNAME: ${{ secrets.CLEVER_USERNAME }}
          CLEVER_PASSWORD: ${{ secrets.CLEVER_PASSWORD }}
          SAVVAS_CLASS_ID: ${{ secrets.SAVVAS_CLASS_ID }}
          SAVVAS_STUDENT_ID: ${{ secrets.SAVVAS_STUDENT_ID }}
      - run: python run_school.py --mode=morning
        env:
          CANVAS_TOKEN: ${{ secrets.CANVAS_TOKEN }}
          CANVAS_URL: ${{ secrets.CANVAS_URL }}
          AK_EMAIL: ${{ secrets.AK_EMAIL }}
          PARENT1_EMAIL: ${{ secrets.PARENT1_EMAIL }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          SAVVAS_TOKEN: ${{ secrets.SAVVAS_TOKEN }}
```

Store all secrets in: GitHub repo → Settings → Secrets and variables → Actions.
Use a **private** repo if you go this route.
