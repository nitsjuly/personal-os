"""
agents/school_agent.py — School Assignment Agent

Concept: Multi-agent orchestration
This agent owns ONE domain: school. It coordinates two tools
(savvas_scraper, canvas_api) and one output (email). It does not
know about finance or health. That separation means a Savvas failure
cannot corrupt a finance report.

Modes:
  --mode=morning   7am digest
  --mode=evening   8pm nudge (only if urgent)
  --test           mock data, print only

Run:
  python agents/school_agent.py --mode=morning
  python agents/school_agent.py --test
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.savvas_scraper import fetch_savvas, refresh_savvas_token
from tools.canvas_api import fetch_canvas
from tools.notifier import send_email
from tools.school_report import build_report, print_report
from core.normalizer import normalize_assignments, track_assignments
from datetime import date, timedelta
from dotenv import load_dotenv
load_dotenv()

# ── CONFIG ──────────────────────────────────────────────────────────────────
TEST       = "--test" in sys.argv
MODE       = next((a.split("=")[1] for a in sys.argv if a.startswith("--mode=")), "morning")
SCOPE_DAYS = 60
SHOW_BANNER = int(os.getenv("SCHOOL_TESTING_RUNS", "5")) > 0

CANVAS_COURSES = {
    "Career Tech": int(os.getenv("CANVAS_CAREER_TECH_ID", "1960295")),
    "Science":     int(os.getenv("CANVAS_SCIENCE_ID",     "1959399")),
}

# ── PIPELINE ────────────────────────────────────────────────────────────────
def run_pipeline():
    """
    Why this structure?
    Concept: Silent vs. visible failure modes.
    Each source is fetched independently and reports its own health.
    A Savvas failure does not suppress Canvas results — it appears
    explicitly in the email as a labeled gap, not as silence.
    """
    cutoff  = date.today() - timedelta(days=SCOPE_DAYS)
    sources = []
    raw     = []
    alerts  = []  # source-level failures surface here, never silently dropped

    if TEST:
        from tools.mock_data import mock_assignments
        return mock_assignments(), cutoff, ["Mock data"], []

    # Canvas — each course independent
    for cname, cid in CANVAS_COURSES.items():
        result = fetch_canvas(cid, cname)
        if result["ok"]:
            raw += result["assignments"]
            sources.append(f"Canvas ({cname})")
        else:
            # Concept: Scraper fragility and health monitoring
            alerts.append(f"Canvas {cname}: {result['error']}")
            sources.append(f"Canvas ({cname} — FAILED: {result['error']})")

    # Savvas — fragile dependency, treated accordingly
    savvas_result = fetch_savvas()
    if savvas_result["ok"]:
        raw += savvas_result["assignments"]
        sources.append("Savvas (Math)")
    else:
        alerts.append(f"Savvas Math: {savvas_result['error']}")
        sources.append("Savvas (Math — FAILED: check token)")

    normalized = normalize_assignments(raw, cutoff)
    buckets    = track_assignments(normalized)
    return buckets, cutoff, sources, alerts


def run_morning(buckets, cutoff, sources, alerts):
    from platform import system
    from datetime import datetime
    _WIN = system() == "Windows"
    day  = datetime.now().strftime("%A, %B %#d" if _WIN else "%A, %B %-d")

    ak_email  = os.getenv("AK_EMAIL", "")
    parent_emails = [e for e in [
        os.getenv("PARENT1_EMAIL", ""),
        os.getenv("PARENT2_EMAIL", ""),
    ] if e]

    # Concept: Human-in-the-loop interrupt design
    # Student and parent get different data — not a filter, a separate path.
    # This is architecture, not a setting. Changing it requires code.
    ak_html  = build_report(buckets, cutoff, for_ak=True,
                            sources=sources, alerts=alerts, show_banner=SHOW_BANNER)
    par_html = build_report(buckets, cutoff, for_ak=False,
                            sources=sources, alerts=alerts, show_banner=SHOW_BANNER)

    if ak_email:
        send_email(ak_email, f"School — {day}", ak_html)
        print(f"  Sent to student: {ak_email}")
    if parent_emails:
        send_email(parent_emails, f"School — {day}", par_html)
        print(f"  Sent to parents: {parent_emails}")

    # Failure alerts are also sent immediately (separate from digest)
    if alerts:
        _send_failure_alerts(alerts, parent_emails)


def run_evening(buckets, cutoff, sources, alerts):
    not_sub  = buckets.get("not_submitted", [])
    due_tod  = [a for a in buckets.get("upcoming", []) if a.days_until == 0]
    due_tom  = [a for a in buckets.get("upcoming", []) if a.days_until == 1]
    urgent   = not_sub + due_tod + due_tom

    # Concept: Respect for attention — only interrupt when something actually needs it
    if not urgent and not alerts:
        print("  Evening: nothing urgent — no email sent.")
        return

    nudge_buckets = {
        "not_submitted": not_sub,
        "upcoming":      due_tod + due_tom,
    }
    from datetime import date, platform
    from platform import system
    _WIN = system() == "Windows"
    from core.normalizer import _d
    day = _d(date.today())

    parent_emails = [e for e in [
        os.getenv("PARENT1_EMAIL", ""),
        os.getenv("PARENT2_EMAIL", ""),
    ] if e]

    html = build_report(nudge_buckets, cutoff, for_ak=False,
                        sources=sources, alerts=alerts, show_banner=False)
    if parent_emails:
        send_email(parent_emails, f"School reminder — {day}", html)
        print(f"  Evening nudge sent: {len(urgent)} urgent item(s).")


def _send_failure_alerts(alerts, recipients):
    """
    Concept: Silent vs. visible failure modes.
    Alerts go out immediately, separate from the digest.
    Never bury a failure inside a report that looks healthy.
    """
    body = "<h3 style='color:#c00'>⚠️ School OS — Data Source Failures</h3>"
    body += "<p>The following sources failed during this morning's run:</p><ul>"
    for a in alerts:
        body += f"<li><b>{a}</b></li>"
    body += "</ul><p>Last successful data shown in digest. Check logs for details.</p>"
    for r in recipients:
        send_email(r, "⚠️ School OS — Source Failure", body)


# ── MAIN ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    buckets, cutoff, sources, alerts = run_pipeline()

    if TEST:
        print_report(buckets, cutoff)
    elif MODE == "morning":
        run_morning(buckets, cutoff, sources, alerts)
    elif MODE == "evening":
        run_evening(buckets, cutoff, sources, alerts)
    else:
        print(f"Unknown mode: {MODE}")
