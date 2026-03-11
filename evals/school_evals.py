"""
evals/school_evals.py — Golden set for school agent

Concept: Eval loops and self-correction

A repeated miss from the same source is a retrieval architecture
problem, not a prompt problem. These evals let you tell the difference.

Run: python evals/school_evals.py
Expected: scored output, pass/fail per criterion
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date, timedelta
from core.normalizer import normalize_assignments, track_assignments

# ── GOLDEN SET ────────────────────────────────────────────────────────────────
# These are the known-good expected behaviors.
# If any test fails after a code change, you have a regression.

GOLDEN_ASSIGNMENTS = [
    # Assignment, expected bucket, expected status
    {"id":"g1","title":"7A-4-3-Homework",   "course":"Math",       "source":"savvas",
     "due_date": date.today()-timedelta(6),  "submitted":False,"score":None,"points":25,"url":"","workflow":"",
     "expected_bucket": "not_submitted"},

    {"id":"g2","title":"Excel Practice Exam","course":"Career Tech","source":"canvas",
     "due_date": date.today()-timedelta(5),  "submitted":True, "score":0,   "points":35,"url":"","workflow":"graded",
     "expected_bucket": "graded_zero"},

    {"id":"g3","title":"Chapter 7 Quiz",     "course":"Science",   "source":"canvas",
     "due_date": date.today(),               "submitted":False,"score":None,"points":20,"url":"","workflow":"",
     "expected_bucket": "upcoming"},

    {"id":"g4","title":"Only if absent",     "course":"Science",   "source":"canvas",
     "due_date": date.today()-timedelta(10), "submitted":False,"score":None,"points":15,"url":"","workflow":"",
     "absent_only": True,
     "expected_bucket": "absent_only"},

    {"id":"g5","title":"Optional extra credit","course":"Math",    "source":"savvas",
     "due_date": date.today()+timedelta(5),  "submitted":False,"score":None,"points":5, "url":"","workflow":"",
     "optional": True,
     "expected_bucket": None},  # None = should be filtered OUT

    {"id":"g6","title":"Lab Report graded",  "course":"Science",   "source":"canvas",
     "due_date": date.today()-timedelta(20), "submitted":True, "score":38, "points":40,"url":"","workflow":"graded",
     "expected_bucket": None},  # Graded with score>0 = filtered OUT of active view
]


class MockAssignment:
    def __init__(self, d):
        for k, v in d.items():
            setattr(self, k, v)
        if not hasattr(self, 'absent_only'): self.absent_only = False
        if not hasattr(self, 'optional'):    self.optional    = False


def run_school_evals():
    print("\n" + "="*60)
    print("SCHOOL AGENT EVALS")
    print("="*60)

    cutoff    = date.today() - timedelta(days=60)
    raw       = [MockAssignment(a) for a in GOLDEN_ASSIGNMENTS]
    normalized = normalize_assignments(raw, cutoff)
    buckets    = track_assignments(normalized)

    all_bucketed = {a.id: bucket for bucket, items in buckets.items() for a in items}

    criteria = [
        ("Captures all non-optional assignments",
         lambda: len([a for a in normalized if not a.optional]) == 5),

        ("Filters optional assignments correctly",
         lambda: "g5" not in all_bucketed),

        ("Filters graded (score>0) assignments correctly",
         lambda: "g6" not in all_bucketed),

        ("Routes not_submitted correctly",
         lambda: all_bucketed.get("g1") == "not_submitted"),

        ("Routes graded_zero correctly",
         lambda: all_bucketed.get("g2") == "graded_zero"),

        ("Routes upcoming correctly (due today)",
         lambda: all_bucketed.get("g3") == "upcoming"),

        ("Routes absent-only to separate bucket",
         lambda: all_bucketed.get("g4") == "absent_only"),

        ("Due today has days_until=0",
         lambda: next((a for a in normalized if a.id=="g3"), None).days_until == 0),

        ("Overdue items have negative days_until",
         lambda: next((a for a in normalized if a.id=="g1"), None).days_until < 0),
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
    print(f"  {'All passing ✅' if passed == len(criteria) else 'REGRESSIONS DETECTED — check before deploying ❌'}")
    return passed == len(criteria)


if __name__ == "__main__":
    ok = run_school_evals()
    sys.exit(0 if ok else 1)
