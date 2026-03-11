# Personal OS — AI-Powered Family Intelligence System

> A production-grade agentic system for a dual-income household.
> Built by a Senior PM to solve a real problem — and to learn by building.

---

## What It Does

Three school platforms. A FIRE savings goal. Family healthcare across four people.
All of it landing in different apps, with no unified view.

**Personal OS** pulls it together into one morning email, one weekly finance check,
and one monthly health reminder — fully automated, with explicit human-in-the-loop
gates before anything consequential happens.

| Domain | What it does | Runs |
|--------|-------------|------|
| **School** | Canvas + Savvas Realize → 7am digest for student + parents | Daily |
| **Finance** | Transaction anomaly detection, NET category reporting, FIRE progress | Weekly + Monthly |
| **Health** | Appointment reminders, referral tracking, scheduling conflict check | Monthly |

---

## Why This Exists (The Real Problem)

My 7th grader was across three school platforms. I was opening three apps every morning.
The student was opening zero.

The job-to-be-done: know at a glance what needs attention today, in one email, without
manual checking — so the 7am conversation is useful instead of reactive.

Savvas Realize had no public API. I reverse-engineered the GraphQL endpoint from
Chrome DevTools, automated token refresh via Playwright, and wired it into a
Canvas-normalized pipeline. Math was dark. Now it isn't.

---

## Key Architectural Decisions

**1. Deterministic core, probabilistic edge**

~80% of this system is pure Python: due date math, scope windows, API calls, email
formatting, financial calculations. AI handles ~20%: ambiguous classification (absent-only
assignment detection), plain-English summary generation, and model routing.

This is deliberate. Deterministic systems are debuggable. When the email is wrong,
there's a line of code to point at.

**2. Math never in the LLM**

All financial calculations live in `tools/finance_calc.py`. The agent narrates results.
It never adds, subtracts, or computes percentages in prose. This prevents the most
common failure mode in AI finance tools: confident wrong numbers.

**3. Silent failures are unacceptable**

Every data source reports its own health independently. A Savvas failure appears
explicitly in the email as a labeled gap — not as silence, and not as "no assignments."
The parent email shows exactly what failed and when it last worked.

**4. Privacy is architecture**

Student email and parent email are separate data paths — not the same data filtered.
No family names, emails, or IDs in code. Everything in `.env`. Safe to publish the repo.

**5. Human-in-the-loop is a design constraint, not a feature**

Finance monthly reports draft first — you review before they send.
Health reminders surface dates only after checking `family-constraints.md`.
Calendar writes require explicit confirmation. Irreversible actions always stop for a human.

---

## What I Learned

- **Canvas `missing=True` is unreliable.** Teachers rarely set it. `score=None` is
  the real signal for "no grade yet." This was the v1 → v2 bug.

- **Absent-only assignment detection needs regex, not AI.** The pattern is consistent
  enough that 15 regex patterns cover 95%+ of cases at zero cost. AI for the last 5%.

- **The correction loop is the product.** Getting classification from 78% to 83%
  accurate took a week. Building a 10-second correction experience took two hours and
  made the 78% system more useful. Reframe: the question was never "how do I reach 100%?"

- **Persistent browser profile is the fast path.** Full Playwright login takes ~30s.
  With a cached session profile, it's ~5s. The full login is the fallback, not the default.

- **Net vs. gross is a design decision, not a display choice.** A travel charge and
  refund in the same period net to zero. Reporting gross overstates spend by 10x
  and triggers false anomalies. This has to be decided at the data model layer.

---

## Architecture

```
personal-os/
├── agents/
│   ├── school_agent.py      ← daily digest, Savvas + Canvas
│   ├── finance_agent.py     ← weekly anomaly check, monthly report
│   └── health_agent.py      ← appointment reminders, referral tracking
├── tools/
│   ├── savvas_scraper.py    ← Playwright token refresh + GraphQL fetch
│   ├── canvas_api.py        ← Canvas REST API wrapper
│   ├── finance_calc.py      ← ALL math lives here — never in the LLM
│   ├── calendar_check.py    ← constraint checking before scheduling
│   └── notifier.py          ← email delivery
├── core/
│   └── normalizer.py        ← shared assignment normalization
├── evals/
│   ├── school_evals.py      ← golden set: routing, scope, absent-only
│   ├── finance_evals.py     ← golden set: NET vs gross, double-count
│   └── health_evals.py      ← golden set: cadence inference, referral tracking
├── config/
│   └── mcp_config.json      ← MCP server config (Gmail, Calendar)
└── private/                 ← .gitignored — never committed
    ├── family-constraints.md
    ├── account-structure.md
    └── health-roster.md
```

---

## Model Routing & Cost

| Task | Model | Why | Est. cost |
|------|-------|-----|-----------|
| School summary prose | Haiku | Low-stakes, high-frequency | ~$0.50/mo |
| Finance anomaly narration | Sonnet | Judgment calls, edge cases | ~$3/mo |
| Health reminders | Haiku | Template-like, low complexity | ~$0.50/mo |
| Cross-domain scheduling | Sonnet | Multi-constraint reasoning | ~$2/mo |
| **Total** | | | **< $10/mo** |

All financial math routes to Python (`finance_calc.py`). Model cost is for
reasoning and narration only — never for computation.

---

## Iteration Log

| Version | What changed | Why |
|---------|-------------|-----|
| v1 | Canvas only, forward-looking | Baseline |
| v2 | Added missing/low grades | v1 missed overdue work |
| v3 | Absent-only bucket, optional filter, 60-day scope | Too much noise |
| v4 | Savvas GraphQL integration, Playwright token automation | Math was dark |
| v5 | Finance + health stubs, V2 architecture | Full Personal OS |
| v6 | All PII to .env, testing banner, graded-zero reframe | Production-ready |

---

## Setup

See [V2_SETUP_GUIDE.md](V2_SETUP_GUIDE.md) for full deployment instructions.

```bash
python -m venv venv && venv\Scripts\activate.bat   # Windows
pip install -r requirements.txt
playwright install chromium
python agents/school_agent.py --test               # validate before deploying
python evals/school_evals.py                       # run golden set
```

---

## Concepts In Play

This project was built as a learning exercise in production AI design.
At every non-trivial decision, the architectural reasoning is documented here.

`RAG retrieval reliability` · `Scraper fragility and health monitoring` ·
`Silent vs. visible failure modes` · `Human-in-the-loop interrupt design` ·
`Eval loops and self-correction` · `MCP for credential security` ·
`Deterministic code for math vs. LLM for reasoning` · `Multi-agent orchestration` ·
`Model selection by task type and cost`

---

*Built by a Senior PM learning AI architecture through production builds.*
*Started as a school tracker. Became a family operating system.*
