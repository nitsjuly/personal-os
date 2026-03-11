# Personal OS V2 — End-to-End Setup Guide
# Deploy today: Claude.ai Project + GitHub + Windows Task Scheduler

---

## Step 0 — New Project vs. Extend?

**Create a NEW Claude.ai project. Do not extend the school project.**

Reasons:
- V1 project instructions are tuned for school only. V2 has three domains with different
  data sources, calculation rules, and HITL gates. Mixing them creates ambiguity.
- A clean project gives you a fresh memory scope — no school-only assumptions bleeding
  into finance or health decisions.
- You can keep V1 running for school (it works) while V2 matures.

**What to do with V1:**
- Keep it. It runs school email every morning via Task Scheduler.
- Once V2 school agent is validated, point Task Scheduler at the new code.
- V1 becomes your rollback.

---

## Step 1 — Claude.ai Project Setup (5 minutes)

1. Go to claude.ai → Projects → New Project
2. Name it: `Personal OS V2`
3. Paste the custom instructions (from PROJECT_INSTRUCTIONS.md in this repo)
4. Upload all three reference files:
   - `private/family-constraints.md`
   - `private/account-structure.md`
   - `private/health-roster.md`
5. That's it. The project is live for conversational use immediately.

**What the project gives you right now (before any code runs):**
- Conversational access to all three domains with full context
- Claude knows your FIRE target, scheduling constraints, health roster
- You can ask "what appointments are coming up?" or "what's my FIRE trajectory?"
  and get answers grounded in your actual files
- This is your human-in-the-loop interface — where you review drafts before anything sends

---

## Step 2 — GitHub Repo Setup (15 minutes)

### 2a. Create the repo
```
Name:        personal-os
Visibility:  Public (the code is generic — private data never touches it)
Initialize:  Yes, with README
```

### 2b. Clone and add structure
```bash
git clone https://github.com/YOURUSERNAME/personal-os
cd personal-os
# Copy all files from this scaffold into the repo
```

### 2c. Critical: set up .gitignore BEFORE first commit
```gitignore
# Private family data — never commit
private/
*.env
.env
logs/
data/
*_profile/
__pycache__/
*.pyc
*.log

# Output files that may contain PII
*_output.json
*_report.html
```

### 2d. First commit
```bash
git add .
git commit -m "Initial scaffold: Personal OS V2 architecture"
git push
```

### 2e. Pin the right repos on your GitHub profile
- `personal-os` (this repo — flagship)
- `AI_Transformation_Field_Guide` (if you make it public)
Two pinned repos is the Aakash Gupta recommendation. Don't over-pin.

---

## Step 3 — Local Environment (10 minutes)

```bash
cd personal-os
python -m venv venv

# Windows
venv\Scripts\activate.bat

pip install -r requirements.txt
```

**requirements.txt** (already in repo):
```
playwright==1.42.0
requests==2.31.0
python-dotenv==1.0.0
anthropic==0.25.0
```

After install:
```bash
playwright install chromium
```

### Create your .env file (never commit this)
```
# School
CANVAS_TOKEN=your_token
CANVAS_URL=https://browardschools.instructure.com
CANVAS_CAREER_TECH_ID=1960295
CANVAS_SCIENCE_ID=1959399
SAVVAS_TOKEN=Bearer eyJ...
CLEVER_USERNAME=student@my.browardschools.edu
CLEVER_PASSWORD=yourpassword
SCHOOL_TESTING_RUNS=5

# Email recipients
AK_EMAIL=student@example.com
PARENT1_EMAIL=parent1@example.com
PARENT2_EMAIL=parent2@example.com

# Anthropic (for agent summarization)
ANTHROPIC_API_KEY=sk-ant-...

# Finance (add when ready)
MONARCH_API_KEY=
PLAID_CLIENT_ID=
PLAID_SECRET=
```

---

## Step 4 — Task Scheduler (Windows) — Deploy Today

Four scheduled tasks. All use the same pattern.

### Create batch scripts in your project root:

**refresh_token.bat**
```bat
@echo off
cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python tools\savvas_scraper.py --refresh-token >> logs\refresh.log 2>&1
```

**school_morning.bat**
```bat
@echo off
cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python agents\school_agent.py --mode=morning >> logs\school_morning.log 2>&1
```

**school_evening.bat**
```bat
@echo off
cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python agents\school_agent.py --mode=evening >> logs\school_evening.log 2>&1
```

**finance_weekly.bat**
```bat
@echo off
cd /d "C:\path\to\personal-os"
call venv\Scripts\activate.bat
python agents\finance_agent.py --mode=weekly >> logs\finance.log 2>&1
```

### Task Scheduler settings (for each task):
- Trigger: Daily at specified time
- Settings tab: "Run task as soon as possible after a scheduled start is missed" ✅
- Conditions tab: "Wake the computer to run this task" ✅
- Run whether user is logged on or not ✅

| Task | Time | Script |
|------|------|--------|
| Token Refresh | 6:30 AM | refresh_token.bat |
| School Morning | 7:00 AM | school_morning.bat |
| School Evening | 8:00 PM | school_evening.bat |
| Finance Weekly | Mon 8:00 AM | finance_weekly.bat |

```bash
mkdir logs
```

---

## Step 5 — Validate Everything

### School (works today — carried from V1)
```bash
python agents/school_agent.py --test
```
Expected: mock data email printed to console, no sends.

### Finance (stub — ready for data hookup)
```bash
python agents/finance_agent.py --test
```
Expected: sample anomaly output, no sends.

### Health (stub — ready for health-roster.md hookup)
```bash
python agents/health_agent.py --test
```
Expected: sample reminder output from health-roster.md.

### Run evals
```bash
python evals/school_evals.py
python evals/finance_evals.py
python evals/health_evals.py
```
Expected: scored output — pass/fail per criterion.

---

## Step 6 — What's Live Today vs. What's Coming

| Feature | Status | Notes |
|---------|--------|-------|
| School email digest | ✅ Live | Carried from V1, refactored into agents/ |
| Savvas token refresh | ✅ Live | Playwright automation working |
| Finance anomaly detection | 🔧 Stub | Needs Monarch/Plaid hookup or CSV import |
| Finance monthly report | 🔧 Stub | Math routing to Python ready |
| Health appointment reminders | 🔧 Stub | Needs health-roster.md populated |
| Gmail intake parsing | 🔧 Stub | MCP server hookup next |
| Calendar conflict check | 🔧 Stub | Needs family-constraints.md read |

**Today's goal:** School is live, finance and health are scaffolded with stubs.
**Next session goal:** Wire one real finance data source (Monarch CSV or manual).

---

## Concepts In Play (V2 Architecture Decisions)

**Why separate agents/ from tools/?**
Concept: *Multi-agent orchestration*. Agents have goals and make decisions.
Tools are stateless functions they call. This separation means you can swap out
tools (e.g. replace Playwright with an API) without touching agent logic.

**Why evals/ as a first-class folder?**
Concept: *Eval loops and self-correction*. A system without evals has no way to
know when it regresses. Golden sets defined now means every future change is
testable against known-good outputs.

**Why Python for all math in finance_calc.py?**
Concept: *Deterministic code for math vs. LLM for reasoning*. LLMs hallucinate
numbers under pressure, especially with rounding and multi-step calculations.
Python is auditable. You can add a print() and see exactly what happened.

**Why MCP for external connections?**
Concept: *MCP for credential security*. Credentials never appear in prompts or
agent code. MCP servers handle auth and expose clean tool interfaces. If you
rotate a Gmail password, you update it in one place.
