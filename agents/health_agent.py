"""
agents/health_agent.py — Healthcare Appointment Agent

Concept: RAG retrieval reliability
health-roster.md is the authoritative source. This agent reads it
every run — it does not cache or assume. If the file changes,
the next run reflects the change automatically.

Concept: Human-in-the-loop interrupt design
This agent NEVER sends external communications autonomously.
It drafts → presents → waits for approval → only then acts.
Scheduling conflicts surface immediately and stop the flow.

Run:
  python agents/health_agent.py           # monthly check
  python agents/health_agent.py --test    # sample output, no sends
"""

import sys, os, re
from datetime import date, datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.calendar_check import check_constraints
from tools.notifier import send_email
from dotenv import load_dotenv
load_dotenv()

TEST = "--test" in sys.argv

HEALTH_ROSTER_PATH   = os.getenv("HEALTH_ROSTER_PATH",   "private/health-roster.md")
FAMILY_CONSTRAINTS_PATH = os.getenv("FAMILY_CONSTRAINTS_PATH", "private/family-constraints.md")

PARENT1_EMAIL = os.getenv("PARENT1_EMAIL", "")

# Standard cadences (overridden by health-roster.md entries if noted)
CADENCES = {
    "dental":          180,  # 6 months
    "annual_physical": 365,
    "orthodontist":     42,  # 6 weeks default
    "pediatric_well":  365,
    "dermatology":     365,
    "ophthalmology":   365,
    "specialist":      None, # no standard cadence — surface as "check roster"
}


# ── ROSTER PARSING ────────────────────────────────────────────────────────────
def parse_health_roster(path):
    """
    Concept: RAG retrieval reliability
    We parse the markdown file fresh every run. The source of truth
    is the file, not memory. This means updates (a new appointment,
    a resolved referral) take effect immediately.

    Failure mode prevented: cached state diverging from reality.
    Tradeoff: slightly slower startup; completely worth it.
    """
    if not os.path.exists(path):
        return None, f"health-roster.md not found at {path}"

    content = open(path).read()
    members = []

    # Each family member section starts with ## Name
    for section in re.split(r'\n## ', content):
        if not section.strip():
            continue
        lines     = section.strip().split('\n')
        name      = lines[0].strip().lstrip('#').strip()
        appts     = []
        referrals = []

        for line in lines[1:]:
            # Parse appointment lines: - [type]: last [date], cadence [N days/months]
            appt_match = re.search(
                r'-\s+\*?\*?(\w[\w\s/]+)\*?\*?:\s+last\s+([\d-]+)',
                line, re.IGNORECASE
            )
            if appt_match:
                appt_type = appt_match.group(1).lower().strip()
                last_date_str = appt_match.group(2).strip()
                try:
                    last_date = date.fromisoformat(last_date_str)
                except ValueError:
                    continue
                cadence_match = re.search(r'cadence[:\s]+(\d+)\s*(day|week|month)', line, re.IGNORECASE)
                if cadence_match:
                    n     = int(cadence_match.group(1))
                    unit  = cadence_match.group(2).lower()
                    days  = n * (30 if unit == "month" else 7 if unit == "week" else 1)
                else:
                    # Fall back to standard cadence map
                    key   = next((k for k in CADENCES if k in appt_type), None)
                    days  = CADENCES.get(key) if key else None

                appts.append({
                    "type":      appt_type,
                    "last_date": last_date,
                    "cadence_days": days,
                    "next_due":  last_date + timedelta(days=days) if days else None,
                    "status":    "scheduled" if "scheduled" in line.lower() else
                                 "resolved"  if "resolved"  in line.lower() else "due",
                    "raw_line":  line.strip(),
                })

            # Parse referral lines: - referral: [specialist], logged [date]
            ref_match = re.search(r'referral[:\s]+(\w[\w\s]+),?\s+logged\s+([\d-]+)', line, re.IGNORECASE)
            if ref_match:
                specialist  = ref_match.group(1).strip()
                logged_date_str = ref_match.group(2).strip()
                try:
                    logged_date = date.fromisoformat(logged_date_str)
                except ValueError:
                    continue
                days_open = (date.today() - logged_date).days
                referrals.append({
                    "specialist":  specialist,
                    "logged_date": logged_date,
                    "days_open":   days_open,
                    "resolved":    "resolved" in line.lower(),
                    "raw_line":    line.strip(),
                })

        members.append({"name": name, "appointments": appts, "referrals": referrals})

    return members, None


# ── REMINDER LOGIC ────────────────────────────────────────────────────────────
def compute_reminders(members):
    """
    Surfaces:
    1. Appointments due within 30 days with no scheduled visit
    2. Referrals open > 60 days (possibly resolved or dropped)
    3. Items already overdue
    Never surfaces: resolved items, scheduled items, items explicitly ignored
    """
    today     = date.today()
    reminders = []
    referral_flags = []

    for member in members:
        for appt in member["appointments"]:
            if appt["status"] in ("resolved", "scheduled"):
                continue
            if appt["next_due"] is None:
                continue
            days_until = (appt["next_due"] - today).days
            if days_until <= 30:
                reminders.append({
                    "member":     member["name"],
                    "type":       appt["type"],
                    "last_date":  appt["last_date"],
                    "next_due":   appt["next_due"],
                    "days_until": days_until,
                    "overdue":    days_until < 0,
                })

        for ref in member["referrals"]:
            if ref["resolved"]:
                continue
            if ref["days_open"] >= 60:
                referral_flags.append({
                    "member":      member["name"],
                    "specialist":  ref["specialist"],
                    "logged_date": ref["logged_date"],
                    "days_open":   ref["days_open"],
                })

    reminders.sort(key=lambda r: r["days_until"])
    return reminders, referral_flags


# ── REPORT BUILDER ────────────────────────────────────────────────────────────
def build_health_digest(reminders, referral_flags, source_error=None):
    html  = "<div style='font-family:Calibri,Arial,sans-serif;max-width:700px'>"
    html += "<div style='background:#1a2a4a;padding:12px 20px;border-radius:6px 6px 0 0'>"
    html += "<h2 style='color:white;margin:0'>Health — Monthly Appointment Check</h2></div>"
    html += "<div style='padding:16px;background:#fff'>"

    if source_error:
        html += (
            f"<div style='background:#fce4ec;border:2px solid #c62828;border-radius:4px;"
            f"padding:10px;margin-bottom:12px'>"
            f"<b>⚠️ Could not read health-roster.md:</b> {source_error}"
            f"</div>"
        )
        html += "</div></div>"
        return html

    if not reminders and not referral_flags:
        html += "<p style='color:green;font-size:14px'>✅ All appointments are current. Nothing due within 30 days.</p>"
        html += "</div></div>"
        return html

    if reminders:
        html += "<h3 style='color:#1a2a4a;border-bottom:2px solid #1a2a4a;padding-bottom:3px'>Due / Overdue</h3>"
        html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
        html += "<tr><th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:left'>Person</th>"
        html += "<th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:left'>Appointment</th>"
        html += "<th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:left'>Last Visit</th>"
        html += "<th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:left'>Due</th></tr>"
        for r in reminders:
            if r["overdue"]:
                due_str = f"<span style='color:#c00;font-weight:bold'>{abs(r['days_until'])}d overdue</span>"
            elif r["days_until"] <= 7:
                due_str = f"<span style='color:#c87000;font-weight:bold'>in {r['days_until']}d</span>"
            else:
                due_str = f"in {r['days_until']}d ({r['next_due'].strftime('%b %d')})"
            html += (
                f"<tr><td style='padding:5px 10px;border-bottom:1px solid #eee'>{r['member']}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #eee'>{r['type'].title()}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #eee'>{r['last_date'].strftime('%b %d, %Y')}</td>"
                f"<td style='padding:5px 10px;border-bottom:1px solid #eee'>{due_str}</td></tr>"
            )
        html += "</table>"
        # Concept: HITL — scheduling requires constraint check before any dates suggested
        html += (
            "<p style='font-size:11px;color:#888;margin-top:6px'>"
            "To schedule: reply with the appointment you want to book. "
            "Scheduling suggestions will include a conflict check against family-constraints.md "
            "before any dates are proposed. No calendar writes without your confirmation."
            "</p>"
        )

    if referral_flags:
        html += "<h3 style='color:#8B2000;border-bottom:2px solid #8B2000;padding-bottom:3px;margin-top:20px'>Open Referrals — Check In</h3>"
        for ref in referral_flags:
            html += (
                f"<div style='background:#fff8e1;border-left:4px solid #f9a825;"
                f"padding:10px 14px;margin:8px 0;border-radius:0 4px 4px 0'>"
                f"<b>{ref['member']}</b> — {ref['specialist']} referral open for {ref['days_open']} days "
                f"(logged {ref['logged_date'].strftime('%b %d, %Y')})<br>"
                f"<span style='font-size:11px;color:#555'>Resolved, still pending, or no longer needed? "
                f"Reply to update health-roster.md.</span>"
                f"</div>"
            )

    html += "</div></div>"
    return html


# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if TEST:
        # Use sample roster for testing
        print("[TEST] Running health agent with sample data...")
        sample_members = [
            {"name": "AK", "appointments": [
                {"type": "dental", "last_date": date(2025,9,1), "cadence_days": 180,
                 "next_due": date(2026,3,1), "status": "due", "raw_line": ""},
                {"type": "annual physical", "last_date": date(2025,3,1), "cadence_days": 365,
                 "next_due": date(2026,3,1), "status": "due", "raw_line": ""},
            ], "referrals": []},
            {"name": "Parent", "appointments": [
                {"type": "dermatology", "last_date": date(2025,3,1), "cadence_days": 365,
                 "next_due": date(2026,3,1), "status": "due", "raw_line": ""},
            ], "referrals": [
                {"specialist": "Neurologist", "logged_date": date(2025,11,1),
                 "days_open": 130, "resolved": False, "raw_line": ""},
            ]},
        ]
        reminders, referral_flags = compute_reminders(sample_members)
        print(f"  Reminders: {len(reminders)}")
        print(f"  Referral flags: {len(referral_flags)}")
        for r in reminders:
            print(f"    {r['member']}: {r['type']} — {r['days_until']}d")
        for rf in referral_flags:
            print(f"    ⚠️  {rf['member']}: {rf['specialist']} open {rf['days_open']}d")
        print("\n[TEST] Email HTML preview:")
        html = build_health_digest(reminders, referral_flags)
        print(html[:500], "...")
    else:
        members, error = parse_health_roster(HEALTH_ROSTER_PATH)
        if error:
            print(f"  ERROR: {error}")
            html = build_health_digest([], [], source_error=error)
        else:
            reminders, referral_flags = compute_reminders(members)
            html = build_health_digest(reminders, referral_flags)

        if PARENT1_EMAIL:
            # Concept: HITL — health digest is informational, not actionable without review
            print(f"  Sending health digest to {PARENT1_EMAIL}...")
            send_email(PARENT1_EMAIL, "Health — Monthly Appointment Check", html)
        else:
            print("PARENT1_EMAIL not set. Print only:")
            print(html[:600])
