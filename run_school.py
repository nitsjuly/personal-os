"""
run_school.py v8 — Integrated Canvas + Savvas + Weekly/Daily Planning

Sources:
  Canvas  → Career Tech, Science
  Savvas  → Math (via GraphQL)

Modes:
  --mode=morning   7am digest — AK gets daily plan, parents get full view
  --mode=evening   8pm gentle nudge — only if urgent items exist
  --test           mock data, print only, no emails

TESTING MODE: First N runs include an informational banner and request for
feedback to parent email.
"""

import sys, os, re, requests, platform
from datetime import datetime, date, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, List
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

try:
    from config import FAMILY
    from core.notify import send
except ImportError:
    FAMILY = {
        "ak":      {"email": os.getenv("AK_EMAIL",""),
                    "canvas_token": os.getenv("CANVAS_TOKEN",""),
                    "canvas_url":   os.getenv("CANVAS_URL","")},
        "parent1": {"email": os.getenv("PARENT1_EMAIL","")},
        "parent2": {"email": os.getenv("PARENT2_EMAIL","")},
    }
    def send(to, subject, html):
        print(f"\n[EMAIL] To: {to}\n[EMAIL] Subject: {subject}\n[EMAIL] ({len(html)} chars)")

# ── CONFIG (all sensitive values from .env) ────────────────────────────────
TEST       = "--test" in sys.argv
MODE       = next((a.split("=")[1] for a in sys.argv if a.startswith("--mode=")), "morning")
_WIN       = platform.system() == "Windows"
SCOPE_DAYS = 60

# How many runs to show the "TESTING MODE" banner (tracked via .env)
TESTING_RUNS_REMAINING = int(os.getenv("SCHOOL_TESTING_RUNS", "5"))

CANVAS_COURSES = {
    "Career Tech": int(os.getenv("CANVAS_CAREER_TECH_ID", "1960295")),
    "Science":     int(os.getenv("CANVAS_SCIENCE_ID",     "1959399")),
}

def _d(d):
    if isinstance(d, str): d = date.fromisoformat(d)
    return d.strftime("%#d %b") if _WIN else d.strftime("%-d %b")

# ── DATA MODEL ─────────────────────────────────────────────────────────────
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

    @property
    def pct(self):
        if self.score is not None and self.points > 0:
            return round(self.score / self.points * 100)
        return None

_ABSENT_RE = [
    r"only\s+if\s+you\s+(don.t|didn.t)\s+present",
    r"only\s+if\s+(you\s+)?(were\s+)?absent",
    r"only\s+submit\s+here\s+if",
    r"only\s+if\s+absent,?\s+you\s+didn.t\s+present",
    r"only\s+if\s+you\s+(didn.t|did\s+not)\s+(present|perform|participate)",
    r"didn.t\s+(present|get\s+a\s+chance)",
    r"if\s+you\s+(presented|performed)\s+in\s+class",
    r"want\s+an\s+a\+",
]
def _is_absent_only(name):
    return any(re.search(p, name.lower()) for p in _ABSENT_RE)

# ── CANVAS CONNECTOR ───────────────────────────────────────────────────────
def canvas_fetch(course_id: int, course_name: str) -> List[Assignment]:
    token = FAMILY["ak"]["canvas_token"]
    base  = FAMILY["ak"]["canvas_url"]
    try:
        r = requests.get(
            f"{base}/api/v1/courses/{course_id}/assignments"
            f"?include[]=submission&per_page=100",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        raw = r.json() if r.status_code == 200 else []
    except Exception as e:
        print(f"  Canvas error ({course_name}): {e}")
        return []
    out = []
    for a in raw:
        if not isinstance(a, dict): continue
        due_str = a.get("due_at")
        if not due_str: continue
        try:
            due_d = datetime.fromisoformat(due_str.replace("Z", "+00:00")).date()
        except Exception:
            continue
        sub  = a.get("submission") or {}
        name = a.get("name", "")
        out.append(Assignment(
            id          = str(a.get("id","")),
            title       = name,
            course      = course_name,
            source      = "canvas",
            due_date    = due_d,
            submitted   = sub.get("submitted_at") is not None,
            score       = sub.get("score"),
            points      = a.get("points_possible") or 0,
            url         = a.get("html_url",""),
            workflow    = sub.get("workflow_state",""),
            absent_only = _is_absent_only(name),
            optional    = "optional" in name.lower(),
        ))
    return out

# ── SAVVAS CONNECTOR ───────────────────────────────────────────────────────
def savvas_fetch() -> List[Assignment]:
    try:
        from savvas_connector import fetch_savvas_assignments, normalize_savvas
    except ImportError:
        print("  savvas_connector.py not found — skipping Math")
        return []
    token = os.getenv("SAVVAS_TOKEN","")
    if not token:
        print("  SAVVAS_TOKEN not set — skipping Math")
        return []
    try:
        raw  = fetch_savvas_assignments(page_size=50)
        norm = normalize_savvas(raw)
    except Exception as e:
        print(f"  Savvas error: {e}")
        return []
    out = []
    for a in norm:
        name = a.get("title","")
        out.append(Assignment(
            id          = str(a.get("id","")),
            title       = name,
            course      = "Math",
            source      = "savvas",
            due_date    = a["due_date"],
            submitted   = a.get("submitted", False),
            score       = a.get("score"),
            points      = a.get("points", 0),
            url         = a.get("url",""),
            workflow    = a.get("workflow",""),
            absent_only = False,
            optional    = "optional" in name.lower(),
        ))
    return out

# ── MOCK DATA ──────────────────────────────────────────────────────────────
def mock_fetch() -> List[Assignment]:
    today = date.today()
    return [
        Assignment("m001","7A-4-3-Homework1",        "Math","savvas",today-timedelta(6), False,None,25,"","in_progress"),
        Assignment("m002","7A-3-7-Quiz",             "Math","savvas",today-timedelta(14),False,None,20,"","in_progress"),
        Assignment("m003","7A-Topic4-HW",            "Math","savvas",today+timedelta(4), False,None,25,"","not_started"),
        Assignment("c001","Domain 6 Lesson 1",       "Career Tech","canvas",today+timedelta(3), False,None,15,"","unsubmitted"),
        Assignment("c002","Excel Practice Exam 2",   "Career Tech","canvas",today-timedelta(5), True, 0,  35,"","graded"),
        Assignment("s001","Project 1 - 3rd MP",      "Science","canvas",today-timedelta(22),False,None,48,"","unsubmitted"),
        Assignment("s002","Activity - only if absent","Science","canvas",today-timedelta(35),False,None,15,"","unsubmitted",absent_only=True),
        Assignment("s003","Earth 2 Final Reflection","Science","canvas",today+timedelta(8), False,None,30,"","unsubmitted"),
        Assignment("s004","Lab Report Ch9",          "Science","canvas",today+timedelta(1), False,None,40,"","unsubmitted"),
        Assignment("s005","Chapter 7 Quiz",          "Science","canvas",today,             False,None,20,"","unsubmitted"),
    ]

# ── NORMALIZER ─────────────────────────────────────────────────────────────
def normalize(assignments: List[Assignment], cutoff: date) -> List[Assignment]:
    today = date.today()
    out   = []
    for a in assignments:
        if a.optional: continue
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

# ── TRACKER ────────────────────────────────────────────────────────────────
def track(assignments: List[Assignment]) -> dict:
    buckets = defaultdict(list)
    for a in assignments:
        if a.absent_only:
            buckets["absent_only"].append(a)
        else:
            buckets[a.status].append(a)
    for key in ["not_submitted","graded_zero","submitted_no_grade"]:
        buckets[key].sort(key=lambda x: x.due_date, reverse=True)
    buckets["upcoming"].sort(key=lambda x: x.due_date)
    return dict(buckets)

# ── TESTING MODE BANNER ────────────────────────────────────────────────────
def _testing_banner():
    feedback_email = FAMILY.get("parent1",{}).get("email","") or os.getenv("PARENT1_EMAIL","")
    return (
        f"<div style='background:#fff3cd;border:2px solid #ffc107;border-radius:6px;"
        f"padding:12px 16px;margin-bottom:16px;font-size:12px;color:#333'>"
        f"<b>🧪 TESTING MODE — This is an automated preview.</b><br>"
        f"Please review and send feedback to "
        f"<a href='mailto:{feedback_email}'>{feedback_email}</a>.<br><br>"
        f"<b>What this covers:</b> Canvas (Career Tech &amp; Science) + Savvas Realize (Math). "
        f"Scope: last {SCOPE_DAYS} days + upcoming only.<br>"
        f"<b>What it does NOT cover:</b> ELA, World History, Chess, French, or any tests "
        f"not entered in Canvas/Savvas. Optional and absent-only assignments are filtered out.<br>"
        f"<b>Recommendation:</b> Check Canvas directly once a week to catch anything missed. "
        f"This tool is a supplement, not a replacement."
        f"</div>"
    )

# ── PLAIN ENGLISH SUMMARY ──────────────────────────────────────────────────
def build_summary(buckets: dict) -> str:
    not_sub  = buckets.get("not_submitted", [])
    zeros    = buckets.get("graded_zero", [])
    pending  = buckets.get("submitted_no_grade", [])
    upcoming = buckets.get("upcoming", [])

    due_today = [a for a in upcoming if a.days_until == 0]
    due_tom   = [a for a in upcoming if a.days_until == 1]
    due_week  = [a for a in upcoming if 2 <= a.days_until <= 7]

    lines = []

    urgent = not_sub + zeros
    if urgent:
        by_course = defaultdict(list)
        for a in urgent: by_course[a.course].append(a)
        course_strs = []
        for c, items in sorted(by_course.items()):
            names = ", ".join(f"<b>{a.title[:35]}</b>" for a in items[:2])
            extra = f" +{len(items)-2} more" if len(items) > 2 else ""
            course_strs.append(f"{c}: {names}{extra}")
        lines.append(
            f"<span style='color:#c00;font-size:15px;font-weight:bold'>"
            f"⚠️ {len(urgent)} item{'s' if len(urgent)!=1 else ''} need immediate attention</span> — "
            + " · ".join(course_strs)
        )
    else:
        lines.append("<span style='color:green;font-weight:bold'>✅ Nothing overdue — great work!</span>")

    if due_today:
        names = ", ".join(f"<b>{a.title[:30]}</b> ({a.course})" for a in due_today)
        lines.append(f"📌 <b>Due TODAY:</b> {names}")
    if due_tom:
        names = ", ".join(f"<b>{a.title[:30]}</b> ({a.course})" for a in due_tom)
        lines.append(f"📌 <b>Due TOMORROW:</b> {names}")
    if due_week:
        names = ", ".join(f"{a.title[:28]} ({a.course}, {_d(a.due_date)})" for a in due_week[:4])
        extra = f" and {len(due_week)-4} more" if len(due_week) > 4 else ""
        lines.append(f"📅 <b>This week:</b> {names}{extra}")
    if pending:
        lines.append(
            f"🟡 <b>{len(pending)} submitted</b> and waiting for a grade "
            f"({', '.join(set(a.course for a in pending))})"
        )

    total_open = len(not_sub) + len(zeros) + len(due_week)
    if total_open >= 5:
        lines.append(
            "💡 <b>Weekly plan suggestion:</b> Block 30 min tonight to triage — "
            "tackle the oldest overdue item first, then prep for what's due this week."
        )
    elif total_open >= 2:
        lines.append("💡 <b>Daily plan:</b> Pick one overdue item and one upcoming item to start early today.")
    elif not urgent and not due_today and not due_tom:
        lines.append("👍 Light week ahead — great time to get ahead on upcoming work.")

    html  = "<div style='background:#f5f7ff;border-left:4px solid #1a2a4a;padding:12px 16px;"
    html += "margin-bottom:18px;border-radius:0 6px 6px 0'>"
    html += "".join(f"<span style='display:block;margin:4px 0'>{l}</span>" for l in lines)
    html += "</div>"
    return html

# ── HTML HELPERS ───────────────────────────────────────────────────────────
_TS  = "border-collapse:collapse;width:100%;font-family:Calibri,Arial,sans-serif;font-size:13px;margin-bottom:18px"
_TH  = "background:#1a2a4a;color:white;padding:6px 10px;text-align:left;white-space:nowrap"
_TD  = "padding:5px 10px;border-bottom:1px solid #e0e0e0;vertical-align:top"
_TDA = "padding:5px 10px;border-bottom:1px solid #e0e0e0;background:#f8f9fa;vertical-align:top"

def _table(headers, rows):
    head = "<tr>" + "".join(f"<th style='{_TH}'>{h}</th>" for h in headers) + "</tr>"
    body = "".join(
        "<tr>" + "".join(f"<td style='{_TDA if i%2 else _TD}'>{c}</td>" for c in row) + "</tr>"
        for i, row in enumerate(rows)
    )
    return f"<table style='{_TS}'>{head}{body}</table>"

def _h(text, color="#1a2a4a"):
    return (f"<h3 style='color:{color};margin:20px 0 5px 0;"
            f"border-bottom:2px solid {color};padding-bottom:3px'>{text}</h3>")

def _name_cell(a):
    return f"<a href='{a.url}' style='color:#1a2a4a;text-decoration:none'>{a.title}</a>" if a.url else a.title

def _when_cell(a):
    """Shows when relative to today — used for upcoming items."""
    d = a.days_until
    if d == 0:  return "<b style='color:#c00'>TODAY</b>"
    if d == 1:  return "<b style='color:#c87000'>Tomorrow</b>"
    if d < 0:   return f"<span style='color:#c00'>{abs(d)}d overdue</span>"
    if d <= 3:  return f"<span style='color:#c87000'>in {d}d</span>"
    return f"in {d}d"

def _status_badge(a):
    if a.status == "not_submitted":
        return "<span style='color:#c00;font-weight:bold'>🔴 Not submitted</span>"
    if a.status == "graded_zero":
        return "<span style='color:#c00;font-weight:bold'>🔴 Graded 0</span>"
    if a.status == "submitted_no_grade":
        return "<span style='color:#c87000'>🟡 Awaiting grade</span>"
    if a.status == "upcoming":
        return _when_cell(a)
    return a.status

def _section(items, title, color):
    if not items: return ""
    by_course = defaultdict(list)
    for a in items: by_course[a.course].append(a)
    html = _h(f"{title} ({len(items)})", color=color)
    for course in sorted(by_course):
        html += f"<p style='font-weight:bold;color:#0a5a6a;margin:10px 0 3px 0'>📚 {course}</p>"
        rows = [
            [_d(a.due_date), _when_cell(a), _name_cell(a),
             f"{a.points:.0f}pts", _status_badge(a)]
            for a in by_course[course]
        ]
        html += _table(["Due","When","Assignment","Pts","Status"], rows)
    return html

def _footer(cutoff, sources):
    return (
        f"<div style='background:#f0f4ff;border:1px solid #c0c8e8;border-radius:4px;"
        f"padding:8px 14px;margin-top:14px;font-size:11px;color:#666'>"
        f"Connected: {', '.join(sources)} · Scope: {_d(cutoff)} onward · "
        f"Not tracked: ELA, World History, Chess, French"
        f"</div>"
    )

def _wrap(title, body):
    return (
        f"<div style='font-family:Calibri,Arial,sans-serif;max-width:740px;color:#222'>"
        f"<div style='background:#1a2a4a;padding:14px 20px;border-radius:6px 6px 0 0'>"
        f"<h2 style='color:white;margin:0;font-size:18px'>{title}</h2></div>"
        f"<div style='padding:16px 20px;background:#fff'>{body}</div></div>"
    )

# ── REPORT BUILDER ─────────────────────────────────────────────────────────
def build_report(buckets: dict, cutoff: date, for_ak=False,
                 sources=None, show_testing_banner=False) -> str:
    sources = sources or ["Canvas (Career Tech, Science)", "Savvas (Math)"]
    html    = ""

    if show_testing_banner:
        html += _testing_banner()

    html += build_summary(buckets)

    # Due today/tomorrow first — most urgent action
    upcoming  = buckets.get("upcoming", [])
    due_now   = [a for a in upcoming if a.days_until <= 1]
    due_later = [a for a in upcoming if a.days_until > 1]

    if due_now:
        html += _section(due_now, "📌 Due Today / Tomorrow — Do These First", "#8B0000")

    not_sub = buckets.get("not_submitted", [])
    if not_sub:
        html += _section(not_sub, "🔴 Overdue — Not Submitted", "#8B0000")
        html += ("<p style='font-size:12px;color:#888;margin:-12px 0 12px 0'>"
                 "Most recent first — better chance of late credit.</p>")

    # Graded zero: show to everyone but reframe for AK as a learning opportunity
    zeros = buckets.get("graded_zero", [])
    if zeros:
        if for_ak:
            html += _section(zeros,
                "📖 Graded 0 — Complete These for Mastery (grades will follow)", "#5a4000")
            html += ("<p style='font-size:12px;color:#666;margin:-12px 0 12px 0'>"
                     "Understanding the concept matters more than the grade. "
                     "Revisiting these builds real knowledge.</p>")
        else:
            html += _section(zeros, "🟠 Graded Zero", "#8B2000")

    pending = buckets.get("submitted_no_grade", [])
    if pending:
        html += _section(pending, "🟡 Submitted — Awaiting Grade", "#884400")

    if due_later:
        html += _section(due_later, "📅 Upcoming This Week & Beyond", "#1a2a4a")

    absent = buckets.get("absent_only", [])
    if absent and not for_ak:
        html += _h(f"📋 Absent-Only ({len(absent)}) — likely not required", "#aaa")
        rows = [[_d(a.due_date), a.course, a.title[:55], f"{a.points:.0f}pts"] for a in absent]
        html += _table(["Due","Course","Assignment","Pts"], rows)

    if not any(v for v in buckets.values()):
        html += "<p style='color:green;font-size:14px'>✅ All clear — nothing pending!</p>"

    html += _footer(cutoff, sources)
    return html

# ── CONSOLE PRINT ──────────────────────────────────────────────────────────
def print_report(buckets: dict, cutoff: date):
    today = date.today()
    total = sum(len(v) for v in buckets.values())
    print(f"\n{'='*70}")
    print(f"School OS v8 — {today}  |  Scope: {cutoff} onward")
    print(f"Sources: Canvas (Career Tech, Science) + Savvas (Math)")
    print(f"Total items: {total}")
    print(f"{'='*70}")

    not_sub  = buckets.get("not_submitted",[])
    zeros    = buckets.get("graded_zero",[])
    upcoming = buckets.get("upcoming",[])
    due_tod  = [a for a in upcoming if a.days_until == 0]
    due_tom  = [a for a in upcoming if a.days_until == 1]
    due_week = [a for a in upcoming if 2 <= a.days_until <= 7]

    print("\n── SUMMARY ──")
    urgent = not_sub + zeros
    if urgent:
        print(f"  ⚠️  {len(urgent)} item(s) need immediate attention:")
        for a in urgent:
            print(f"       {a.course}: {a.title[:50]}  ({abs(a.days_until)}d overdue)")
    else:
        print("  ✅ Nothing overdue")
    if due_tod:  print(f"  📌 Due TODAY:     " + ", ".join(f"{a.title[:30]} ({a.course})" for a in due_tod))
    if due_tom:  print(f"  📌 Due TOMORROW:  " + ", ".join(f"{a.title[:30]} ({a.course})" for a in due_tom))
    if due_week: print(f"  📅 This week:     {len(due_week)} item(s)")

    sections = [
        ("not_submitted",      "🔴 NOT SUBMITTED"),
        ("graded_zero",        "🟠 GRADED ZERO (complete for mastery)"),
        ("submitted_no_grade", "🟡 SUBMITTED — AWAITING GRADE"),
        ("upcoming",           "📅 UPCOMING"),
        ("absent_only",        "📋 ABSENT-ONLY"),
    ]
    for key, label in sections:
        items = buckets.get(key, [])
        if not items: continue
        print(f"\n{label} ({len(items)}):")
        by_c = defaultdict(list)
        for a in items: by_c[a.course].append(a)
        for course in sorted(by_c):
            print(f"  ── {course}")
            for a in by_c[course]:
                tag = f"+{a.days_until}d" if a.days_until >= 0 else f"{a.days_until}d"
                sub = "✓" if a.submitted else "✗"
                scr = str(a.score) if a.score is not None else "NG"
                print(f"    {a.due_date} ({tag:>6})  {sub}  {a.title[:48]:<48}  {a.points:.0f}pts  score={scr}")

# ── PIPELINE ───────────────────────────────────────────────────────────────
def run_pipeline():
    cutoff  = date.today() - timedelta(days=SCOPE_DAYS)
    sources = []
    raw     = []

    if TEST:
        print("[TEST MODE — using mock data]")
        raw     = mock_fetch()
        sources = ["Mock data"]
    else:
        for cname, cid in CANVAS_COURSES.items():
            print(f"  Fetching Canvas: {cname}...")
            raw += canvas_fetch(cid, cname)
        sources.append("Canvas (Career Tech, Science)")

        print("  Fetching Savvas: Math...")
        math = savvas_fetch()
        if math:
            raw += math
            sources.append("Savvas (Math)")
        else:
            sources.append("Savvas (Math — unavailable)")

    normalized = normalize(raw, cutoff)
    buckets    = track(normalized)
    return buckets, cutoff, sources

def _decrement_testing_runs():
    """Reduce the testing run counter in .env."""
    if TESTING_RUNS_REMAINING <= 0:
        return
    env_file = ".env"
    if not os.path.exists(env_file):
        return
    lines = open(env_file).readlines()
    new_lines = []
    for line in lines:
        if line.startswith("SCHOOL_TESTING_RUNS="):
            new_lines.append(f"SCHOOL_TESTING_RUNS={max(0, TESTING_RUNS_REMAINING-1)}\n")
        else:
            new_lines.append(line)
    open(env_file,"w").writelines(new_lines)

# ── MODES ──────────────────────────────────────────────────────────────────
def run_morning():
    buckets, cutoff, sources = run_pipeline()
    show_banner = TESTING_RUNS_REMAINING > 0

    if TEST:
        print_report(buckets, cutoff)
        return

    day = datetime.now().strftime("%A, %B %#d" if _WIN else "%A, %B %-d")

    # AK view: include graded_zero (reframed), no absent-only
    ak_buckets = {k: v for k, v in buckets.items() if k != "absent_only"}
    ak_html    = build_report(ak_buckets, cutoff, for_ak=True,
                              sources=sources, show_testing_banner=show_banner)

    # Parent view: full picture
    par_html   = build_report(buckets, cutoff, for_ak=False,
                              sources=sources, show_testing_banner=show_banner)

    ak_email  = FAMILY["ak"]["email"]
    parents   = [e for e in [
        FAMILY.get("parent1",{}).get("email",""),
        FAMILY.get("parent2",{}).get("email","")
    ] if e]

    if ak_email:
        send(ak_email, f"School — {day}", _wrap(f"Good morning 👋 — {day}", ak_html))
        print(f"  Sent to student: {ak_email}")
    if parents:
        send(parents, f"School — {day}", _wrap(f"School — {day}", par_html))
        print(f"  Sent to parents: {parents}")

    if show_banner:
        _decrement_testing_runs()

def run_evening():
    buckets, cutoff, sources = run_pipeline()
    not_sub = buckets.get("not_submitted", [])
    due_tod = [a for a in buckets.get("upcoming",[]) if a.days_until == 0]
    due_tom = [a for a in buckets.get("upcoming",[]) if a.days_until == 1]
    urgent  = not_sub + due_tod + due_tom

    if TEST:
        print_report(buckets, cutoff)
        return

    if not urgent:
        print("  Evening: nothing urgent — no email sent.")
        return

    nudge_buckets = {
        "not_submitted": not_sub,
        "upcoming":      due_tod + due_tom,
    }
    html    = build_report(nudge_buckets, cutoff, for_ak=False, sources=sources)
    day     = _d(date.today())
    parents = [e for e in [
        FAMILY.get("parent1",{}).get("email",""),
        FAMILY.get("parent2",{}).get("email","")
    ] if e]
    if parents:
        send(parents, f"School reminder — {day}",
             _wrap(f"School — evening reminder {day}", html))
        print(f"  Evening nudge sent: {len(urgent)} urgent items.")

# ── MAIN ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    modes = {"morning": run_morning, "evening": run_evening}
    fn = modes.get(MODE)
    if fn:
        fn()
    else:
        print(f"Unknown mode: {MODE}. Use --mode=morning|evening")
