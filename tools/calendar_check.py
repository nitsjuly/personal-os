"""tools/calendar_check.py — Cross-reference family-constraints.md before scheduling"""
import os, re
from datetime import date

CONSTRAINTS_PATH = os.getenv("FAMILY_CONSTRAINTS_PATH", "private/family-constraints.md")

def check_constraints(proposed_date: date, duration_hours=1):
    """Returns (ok: bool, reason: str | None)"""
    if not os.path.exists(CONSTRAINTS_PATH):
        return True, "family-constraints.md not found — proceeding without constraint check"
    content = open(CONSTRAINTS_PATH).read()
    ds = proposed_date.strftime("%Y-%m-%d")
    # Simple check: look for explicit block-out dates
    if ds in content:
        return False, f"{ds} appears in family-constraints.md — manual review needed"
    dow = proposed_date.strftime("%A")
    if re.search(rf"no appointments.*{dow}", content, re.IGNORECASE):
        return False, f"{dow}s blocked in family-constraints.md"
    return True, None
