# Iteration Log — School Assignment Tracker

Each version includes: what changed, why, and what it prevented.

---

## v1 — Canvas only, forward-looking
**What:** Fetched Canvas assignments due in the next 7 days. Simple list email.
**Why it failed:** Completely missed overdue work. "Nothing due" was wrong.
**Failure mode:** Forward-only scope = false confidence.

## v2 — Added missing + low grades
**What:** Added `missing=True` flag from Canvas API. Showed low scores.
**Why it failed:** Canvas `missing=True` is unreliable — teachers rarely set it.
**Failure mode:** Trusting a platform signal without verifying it against ground truth.

## v3 — Absent-only bucket, optional filter, 60-day scope
**What:** Regex-detected absent-only assignments, filtered optional items, widened scope to 60 days.
**Why:** v2 was too noisy. Students were ignoring emails with irrelevant items.
**Concept:** Precision over recall for attention-scarce recipients.

## v4 — Savvas GraphQL integration
**What:** Reverse-engineered Savvas Realize GraphQL endpoint via Chrome DevTools.
Built `savvas_connector.py`. Math assignments now visible.
**Why:** Math was entirely invisible. The platform has no public API.
**Concept:** Scraper fragility. Treat this as a dependency with no contract.
**Key learning:** Dumping exact HTML from DevTools is the reliable path.
Guessing CSS selectors wastes iteration cycles.

## v5 — Playwright token automation
**What:** Automated the Savvas login via Playwright. Persistent browser profile
for fast path (~5s). Full login fallback when profile is stale.
**Why:** Manual token refresh was the single point of human friction in the system.
**Key learning:** `a.forwardUrl` selector (found in HTML dump) was the breakthrough.
Previous attempts used guessed selectors and all failed.

## v6 — All PII to .env
**What:** Moved all names, emails, course IDs, student IDs to environment variables.
**Why:** Code was not safe to share publicly with hardcoded family data.
**Concept:** Privacy by architecture.

## v7 — Due-date status display fix
**What:** `_when_cell()` now correctly shows TODAY / Tomorrow / "in Nd" instead of
repeating the due date.
**Why:** Parents reported the "when" column was confusing.

## v8 — Graded zero reframe + testing banner
**What:** Graded zeros shown to student as "Complete for Mastery." Testing banner
on first 5 runs with coverage caveats. `SCHOOL_TESTING_RUNS` decrements in `.env`.
**Why:** A zero shown without context causes anxiety. Reframe as a learning opportunity.
Testing banner sets honest expectations about what the system doesn't cover.
**Concept:** Responsible AI — emotional safety and honest uncertainty.
