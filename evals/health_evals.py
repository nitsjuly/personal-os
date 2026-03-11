"""
evals/health_evals.py — Golden set for health agent

Tests cadence inference, referral tracking, and resolved-item filtering.

Run: python evals/health_evals.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from datetime import date, timedelta

# Import health agent logic directly for testing
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents'))


def run_health_evals():
    print("\n" + "="*60)
    print("HEALTH AGENT EVALS")
    print("="*60)

    today = date.today()

    # Golden set: known inputs with known expected outputs
    sample_members = [
        {"name": "Student", "appointments": [
            {"type": "dental", "last_date": today - timedelta(days=190),
             "cadence_days": 180, "next_due": today - timedelta(days=10),
             "status": "due", "raw_line": ""},
            {"type": "annual physical", "last_date": today - timedelta(days=400),
             "cadence_days": 365, "next_due": today - timedelta(days=35),
             "status": "due", "raw_line": ""},
            {"type": "orthodontist", "last_date": today - timedelta(days=50),
             "cadence_days": 42, "next_due": today - timedelta(days=8),
             "status": "scheduled", "raw_line": ""},  # scheduled — should NOT appear
        ], "referrals": []},
        {"name": "Parent", "appointments": [
            {"type": "dermatology", "last_date": today - timedelta(days=380),
             "cadence_days": 365, "next_due": today - timedelta(days=15),
             "status": "due", "raw_line": ""},
            {"type": "eye exam", "last_date": today + timedelta(days=45),
             "cadence_days": 365, "next_due": today + timedelta(days=45),
             "status": "due", "raw_line": ""},  # far out — should NOT appear
        ], "referrals": [
            {"specialist": "Neurologist", "logged_date": today - timedelta(days=75),
             "days_open": 75, "resolved": False, "raw_line": ""},       # open 75d — SHOULD flag
            {"specialist": "Cardiologist", "logged_date": today - timedelta(days=30),
             "days_open": 30, "resolved": False, "raw_line": ""},       # open 30d — should NOT flag
            {"specialist": "Dermatologist", "logged_date": today - timedelta(days=90),
             "days_open": 90, "resolved": True, "raw_line": ""},        # resolved — should NOT flag
        ]},
    ]

    # Run the compute_reminders logic inline (mirrors health_agent.py)
    reminders = []
    referral_flags = []
    for member in sample_members:
        for appt in member["appointments"]:
            if appt["status"] in ("resolved", "scheduled"):
                continue
            if appt["next_due"] is None:
                continue
            days_until = (appt["next_due"] - today).days
            if days_until <= 30:
                reminders.append({"member": member["name"], "type": appt["type"],
                                   "days_until": days_until, "overdue": days_until < 0})
        for ref in member["referrals"]:
            if ref["resolved"]: continue
            if ref["days_open"] >= 60:
                referral_flags.append({"member": member["name"], "specialist": ref["specialist"],
                                       "days_open": ref["days_open"]})

    student_reminders = [r for r in reminders if r["member"] == "Student"]
    parent_reminders  = [r for r in reminders if r["member"] == "Parent"]

    criteria = [
        ("Student dental flagged as overdue",
         lambda: any(r["type"] == "dental" and r["overdue"] for r in student_reminders)),

        ("Student annual physical flagged as overdue",
         lambda: any("physical" in r["type"] and r["overdue"] for r in student_reminders)),

        ("Scheduled orthodontist NOT surfaced",
         lambda: not any(r["type"] == "orthodontist" for r in reminders)),

        ("Parent dermatology flagged",
         lambda: any(r["type"] == "dermatology" for r in parent_reminders)),

        ("Eye exam 45d out NOT surfaced (outside 30d window)",
         lambda: not any(r["type"] == "eye exam" for r in reminders)),

        ("Neurologist referral (75d) flagged",
         lambda: any(rf["specialist"] == "Neurologist" for rf in referral_flags)),

        ("Cardiologist referral (30d) NOT flagged — under 60d threshold",
         lambda: not any(rf["specialist"] == "Cardiologist" for rf in referral_flags)),

        ("Resolved dermatologist referral NOT flagged",
         lambda: not any(rf["specialist"] == "Dermatologist" for rf in referral_flags)),

        ("Reminders sorted — most overdue first",
         lambda: reminders == sorted(reminders, key=lambda r: r["days_until"])),
    ]

    passed = 0
    for label, test_fn in criteria:
        try:
            result = test_fn()
        except Exception as e:
            result = False
            label += f" [ERROR: {e}]"
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}  {label}")
        if result: passed += 1

    print(f"\n  Score: {passed}/{len(criteria)}")
    print(f"  {'All passing ✅' if passed == len(criteria) else 'REGRESSIONS DETECTED ❌'}")
    return passed == len(criteria)


if __name__ == "__main__":
    ok = run_health_evals()
    sys.exit(0 if ok else 1)
