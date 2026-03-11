# AI Product Sense — Concept Learning Guide
# Personal OS Edition: Every concept grounded in what you actually built

---

## How to use this guide

Each concept below follows the same structure:
1. **Plain English definition** — what it actually is
2. **Where it lives in your code** — not hypothetical
3. **The failure it prevents** — what would happen without it
4. **The interview question it answers** — how to use it in the room
5. **Go deeper** — one question to explore next session

---

## 1. RAG Retrieval Reliability

**Plain English:**
RAG (Retrieval Augmented Generation) means giving an AI model fresh, specific
data at runtime instead of relying on what it learned during training.
"Reliability" is about whether the retrieval actually gets the right data —
and whether you know when it doesn't.

**In your code:**
`health_agent.py` re-reads `health-roster.md` on every run. It doesn't cache
or assume. `canvas_api.py` fetches live data per run. The Savvas scraper checks
whether data is newer than the last run — stale data triggers an alert, not silence.

**Failure it prevents:**
Without reliability checks, your system happily returns yesterday's data and
calls it today's. A student submits work; the system still flags it as missing.
A referral gets resolved; the agent still surfaces it 3 months later.

**Interview question it answers:**
"How do you handle data freshness in an agentic system?"
Answer: "Retrieval reliability means knowing when your source has actually
updated vs. when you're serving stale context. We treat stale data as a failure
mode, not a normal state — it triggers an explicit alert with the last known good
timestamp."

**Go deeper next session:**
What's the difference between RAG and fine-tuning for this use case?
When would you fine-tune instead of retrieve?

---

## 2. Scraper Fragility and Health Monitoring

**Plain English:**
A scraper is code that reads a website's HTML to extract data — because no API
exists. Fragile means it breaks when the website changes. Health monitoring means
building the system to detect and report those breaks, rather than silently failing.

**In your code:**
`tools/savvas_scraper.py` is your fragile dependency. Savvas has no public API.
The scraper knows it's fragile: it checks whether data is newer than the previous
run, reports the specific failure reason (unreachable / empty / unchanged), and
sends an alert with the last known good dataset.

**Failure it prevents:**
Without health monitoring, the scraper fails silently. The morning email says
"no math assignments" — which looks like good news but is actually a broken data
source. The parent doesn't know. The student doesn't know. Assignments get missed.

**Interview question it answers:**
"How do you handle fragile external dependencies in production?"
Answer: "We treat them as first-class failure modes. Every scraper has a health
check: is the data newer than last run? If not, we surface the specific failure
reason immediately — not as a silent gap in the report, but as an explicit alert
with what we last knew."

**Go deeper next session:**
What's the right retry strategy for a scraper? Immediate vs. exponential backoff?
At what point does repeated scraper failure mean you need a different architecture?

---

## 3. Silent vs. Visible Failure Modes

**Plain English:**
A silent failure is when something goes wrong and the system continues without
telling anyone. A visible failure is when the system explicitly says "this broke,
here's what I last knew, here's what to do."
Silent failures are almost always worse than visible ones.

**In your code:**
Every data source in `school_agent.py` has an `alerts` list. If Canvas fails,
it appends to `alerts` and continues — but the email shows "Canvas Career Tech —
FAILED: [reason]" not just fewer assignments. Finance agent returns
`_source_failure_html()` when no data source is available — it does not produce
a report that looks complete when it isn't.

**Failure it prevents:**
Silent failures breed false confidence. A report that says "everything looks fine"
when two data sources are down is more dangerous than no report at all.

**Interview question it answers:**
"Tell me about a time your system gave incorrect data and how you handled it."
Answer: "We architected against silent failures from the start. Every data source
reports its own health. Failure surfaces immediately with the specific reason and
the last known state — never as an empty result that looks like good news."

**Go deeper next session:**
What's the difference between a fail-open and fail-closed system?
When would you want each in a family automation context?

---

## 4. Human-in-the-Loop (HITL) Interrupt Design

**Plain English:**
HITL means designing specific points in an agentic workflow where the system
STOPS and waits for a human decision before continuing. "Interrupt design" is
about choosing those points deliberately — not too many (friction), not too few
(dangerous autonomy).

**In your code:**
Finance monthly report: drafts first, asks "Send? [y/n]" before touching email.
Health scheduling: surfaces dates only after constraint check, never writes to
calendar without confirmation. School alert: failure alerts send immediately
(low stakes, informational), but the digest is review-and-send (high trust).

The interrupt points are:
- Any external communication (appointment requests, emails to providers)
- Any financial action or transfer
- Any permanent update to the reference files
- Any irreversible action

**Failure it prevents:**
Without HITL, the system sends a half-wrong appointment request to a specialist
at 7am before you've had coffee. The trust recovery cost is much higher than the
convenience gain.

**Interview question it answers:**
"How did you decide where to put human approval gates?"
Answer: "We used one rule: if the downstream consequence is hard to reverse,
a human is in the loop. Informational alerts are autonomous. External
communications and data writes always require approval. We also designed the
approval UX to be fast — a single 'y' or a reply to an email — so the gate
doesn't become friction that people learn to skip."

**Go deeper next session:**
How does HITL change as a system matures and builds trust?
What metrics would tell you your HITL gates are in the right places?

---

## 5. Eval Loops and Self-Correction

**Plain English:**
An eval (evaluation) is a test that checks whether your system is producing
the right output. An eval loop is running those tests regularly — especially
after any change — so you know immediately when something regresses.
Self-correction is using eval results to improve the system systematically.

**In your code:**
`evals/school_evals.py` has a golden set: known inputs with known expected outputs.
Run it after any change. If a test fails, you have a regression. The eval
distinguishes between a prompt problem (fix the prompt) and a retrieval
architecture problem (fix the data pipeline).

The weekly "eval check-in" in the Monday email asks the parent: "Did anything
get missed? Was any figure wrong?" This is a human-in-the-loop eval — continuous
feedback that feeds the golden set.

**Failure it prevents:**
Without evals, you fix one bug and create three others without knowing it.
A repeated miss from the same source looks like bad luck. With evals, it looks
like what it is: a retrieval architecture problem.

**Interview question it answers:**
"How do you know your AI system is actually working?"
Answer: "We have two eval layers. Automated: golden sets that run on every
code change. Human: a weekly feedback prompt in the digest — 'did anything get
missed?' Repeated failures from the same source trigger an architecture review,
not a prompt tweak. One tells you what broke. The other tells you how to fix it."

**Go deeper next session:**
What's the difference between an eval and a unit test?
How would you build an eval for something subjective, like tone of the summary email?

---

## 6. MCP for Credential Security

**Plain English:**
MCP (Model Context Protocol) is a standard for connecting AI models to external
services. For credential security, the key idea is: credentials never appear in
prompts, code, or context windows. The MCP server handles authentication and
exposes clean tool interfaces. The model calls the tool; it never sees the password.

**In your code:**
Gmail and Google Calendar are connected via MCP in `config/mcp_config.json`.
The agent calls `gmail.send_email(to=..., subject=..., body=...)` — it never
sees your Gmail password. If you rotate credentials, you update the MCP config
in one place, not in every agent that touches email.

**Failure it prevents:**
Hardcoded credentials in agent code get committed to GitHub by accident.
Or they get echoed back in a Claude response when you're debugging.
Or they need to be updated in 12 places when they rotate.

**Interview question it answers:**
"How do you handle secrets and credentials in an agentic system?"
Answer: "All external connections go through MCP servers. Credentials never
appear in prompts or agent code. This means we can publish the entire codebase
publicly — the private data lives in .env and in the MCP config, both gitignored.
It also means credential rotation is a single-point update."

**Go deeper next session:**
What's the difference between MCP and a regular REST API wrapper?
What would make you choose one over the other?

---

## 7. Deterministic Code for Math vs. LLM for Reasoning

**Plain English:**
Deterministic means the same input always produces the same output, with no
randomness or hallucination. LLMs are probabilistic — they can produce different
(sometimes wrong) outputs for the same input. Math should be deterministic.
Reasoning can be probabilistic.

**In your code:**
`tools/finance_calc.py` is the rule: all math lives here. `finance_agent.py`
calls the functions and narrates the results. It never writes "travel spend was
about $3,200 this month" — it calls `net_by_category()` and uses the returned
`net_display` string. The LLM cannot change the number; it can only describe it.

**Failure it prevents:**
LLMs hallucinate numbers under pressure. They round aggressively. They
mishandle signs (is -$850 a charge or a refund?). They lose track of
multi-step calculations. A finance report with a wrong number is worse than
no report — it builds false confidence about your spending.

**Interview question it answers:**
"Where do you use AI vs. deterministic rules in your system?"
Answer: "We use a simple test: can this be expressed as a rule? If yes, it's code.
If not, it's AI. All financial math is code — it's auditable, testable, and you
can add a print() to see exactly what happened. AI handles the boundary cases:
classifying ambiguous descriptions, generating natural language summaries,
making judgment calls about anomaly severity."

**Go deeper next session:**
What happens when a "rule" needs to be context-dependent?
(e.g., is $3,000 in travel spend anomalous? Depends on the month.)
How would you handle that boundary?

---

## 8. Multi-Agent Orchestration

**Plain English:**
Orchestration means coordinating multiple agents so each one handles its own
domain, they don't interfere with each other, and the overall system produces
a coherent result. Each agent has a specific job, specific tools, and specific
failure modes it owns.

**In your code:**
`school_agent.py` owns school. It does not know about finance.
`finance_agent.py` owns money. It does not know about appointments.
`health_agent.py` owns healthcare. They share tools (notifier, calendar_check)
but do not share state. A Savvas failure cannot corrupt a finance report.

The orchestration layer (currently: Task Scheduler + batch scripts) runs
each agent independently. Future: a coordinator agent that synthesizes
cross-domain insights ("AK has two tests this week AND a dentist appointment —
reschedule the dentist").

**Failure it prevents:**
Without separation, one agent's bug poisons all three reports. With separation,
you can deploy a school fix without touching finance or health.

**Interview question it answers:**
"How did you structure your agents and why?"
Answer: "Each agent owns one domain. They share tools but not state. This means
a scraper failure in school doesn't suppress a finance anomaly. We can update,
test, and deploy each agent independently. The cost of separation is a little
more scaffolding. The benefit is containment: a bug has a blast radius of one domain."

**Go deeper next session:**
What would a coordinator/orchestrator agent look like that reasons across domains?
When does multi-agent add complexity without value?

---

## 9. Model Selection by Task Type and Cost

**Plain English:**
Not all tasks need the same model. Using a Sonnet-class model for a simple
summary email is like using a surgeon to put on a bandage — technically works,
but expensive and slow. Model selection means matching model capability to task
complexity.

**In your code:**
School digest / health reminders → Haiku. Low-complexity, high-frequency,
template-like prose. Fast, cheap, good enough. ~$0.50/month.
Finance anomaly narration → Sonnet. Judgment calls, edge cases, multi-step
reasoning. Worth the cost for high-stakes output. ~$3/month.
Cross-domain scheduling → Sonnet. Multi-constraint reasoning across all three
reference files. ~$2/month. Total: under $10/month.

**Failure it prevents:**
Using the wrong model in either direction. Haiku for complex financial reasoning
produces confident-sounding wrong analysis. Sonnet for simple "here are your
assignments" prose is 10x the cost with no quality gain.

**Interview question it answers:**
"How do you think about model selection in a production system?"
Answer: "We map task complexity to model tier. The signal is: how much does
the model need to reason vs. retrieve and format? Simple retrieval + formatting
→ Haiku. Judgment calls + edge cases → Sonnet. We also track cost per run and
set a monthly budget constraint. Cost discipline isn't frugality — it's a signal
that you understand the system you built."

**Go deeper next session:**
How would you A/B test two models for the same task to know which is actually better?
What metrics would you use beyond cost?
