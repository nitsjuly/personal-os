"""
core/normalizer.py — Shared normalization logic

Pulled out of school_agent so evals can test it independently
of any email-sending or API-calling code.
"""

import re
from datetime import date
from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict
import platform

_WIN = platform.system() == "Windows"


def _d(d):
    if isinstance(d, str): d = date.fromisoformat(d)
    return d.strftime("%#d %b") if _WIN else d.strftime("%-d %b")


_ABSENT_RE = [
    r"only\s+if\s+you\s+(don.t|didn.t)\s+present",
    r"only\s+if\s+(you\s+)?(were\s+)?absent",
    r"only\s+submit\s+here\s+if",
    r"only\s+if\s+absent,?\s+you\s+didn.t\s+present",
    r"only\s+if\s+you\s+(didn.t|did\s+not)\s+(present|perform|participate)",
    r"didn.t\s+(present|get\s+a\s+chance)",
]

def is_absent_only(name):
    return any(re.search(p, name.lower()) for p in _ABSENT_RE)


@dataclass
class Assignment:
    id:          str
    title:       str
    course:      str
    source:      str
    due_date:    date
    submitted:   bool
    score:       Optional[float]
    points:      float
    url:         str
    workflow:    str
    absent_only: bool  = False
    optional:    bool  = False
    status:      str   = ""
    days_until:  int   = 0


def normalize_assignments(raw, cutoff):
    today = date.today()
    out   = []
    for a in raw:
        if getattr(a, 'optional', False): continue
        if a.due_date < cutoff: continue
        a.days_until = (a.due_date - today).days
        if a.due_date >= today:
            a.status = "upcoming"
        elif a.score is not None and a.score > 0:
            a.status = "graded"
        elif a.score == 0 and a.submitted:
            a.status = "graded_zero"
        elif a.submitted and a.score is None:
            a.status = "submitted_no_grade"
        else:
            a.status = "not_submitted"
        if a.status == "graded": continue
        out.append(a)
    return out


def track_assignments(assignments):
    buckets = defaultdict(list)
    for a in assignments:
        if a.absent_only:
            buckets["absent_only"].append(a)
        else:
            buckets[a.status].append(a)
    for key in ["not_submitted", "graded_zero", "submitted_no_grade"]:
        buckets[key].sort(key=lambda x: x.due_date, reverse=True)
    buckets["upcoming"].sort(key=lambda x: x.due_date)
    return dict(buckets)
