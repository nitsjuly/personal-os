"""tools/school_report.py — HTML report builder (moved from run_school.py)"""
import os
from collections import defaultdict
from datetime import date
from core.normalizer import _d
import platform
_WIN = platform.system() == "Windows"

_TS = "border-collapse:collapse;width:100%;font-family:Calibri,Arial,sans-serif;font-size:13px;margin-bottom:18px"
_TH = "background:#1a2a4a;color:white;padding:6px 10px;text-align:left;white-space:nowrap"
_TD = "padding:5px 10px;border-bottom:1px solid #e0e0e0;vertical-align:top"

def _table(headers, rows):
    head = "<tr>" + "".join(f"<th style='{_TH}'>{h}</th>" for h in headers) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td style='{_TD}'>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table style='{_TS}'>{head}{body}</table>"

def _h(text, color="#1a2a4a"):
    return f"<h3 style='color:{color};margin:20px 0 5px 0;border-bottom:2px solid {color};padding-bottom:3px'>{text}</h3>"

def _when(a):
    d = a.days_until
    if d == 0:  return "<b style='color:#c00'>TODAY</b>"
    if d == 1:  return "<b style='color:#c87000'>Tomorrow</b>"
    if d < 0:   return f"<span style='color:#c00'>{abs(d)}d overdue</span>"
    if d <= 3:  return f"<span style='color:#c87000'>in {d}d</span>"
    return f"in {d}d"

def _section(items, title, color):
    if not items: return ""
    by_course = defaultdict(list)
    for a in items: by_course[a.course].append(a)
    html = _h(f"{title} ({len(items)})", color=color)
    for course in sorted(by_course):
        html += f"<p style='font-weight:bold;color:#0a5a6a;margin:8px 0 3px'>{course}</p>"
        rows = [[_d(a.due_date), _when(a), a.title[:55], f"{a.points:.0f}pts"] for a in by_course[course]]
        html += _table(["Due","When","Assignment","Pts"], rows)
    return html

def _alerts_html(alerts):
    if not alerts: return ""
    html = "<div style='background:#fce4ec;border:2px solid #c62828;border-radius:4px;padding:10px;margin-bottom:12px'>"
    html += "<b>⚠️ Data source issues:</b><ul style='margin:4px 0'>"
    for a in alerts: html += f"<li>{a}</li>"
    html += "</ul></div>"
    return html

def _testing_banner():
    email = os.getenv("PARENT1_EMAIL","parent@example.com")
    return (
        f"<div style='background:#fff3cd;border:2px solid #ffc107;border-radius:6px;"
        f"padding:12px 16px;margin-bottom:16px;font-size:12px;color:#333'>"
        f"<b>🧪 TESTING MODE</b> — Please send feedback to "
        f"<a href='mailto:{email}'>{email}</a>.<br>"
        f"Covers: Canvas (Career Tech, Science) + Savvas (Math) · 60-day scope.<br>"
        f"Does NOT cover: ELA, World History, Chess, French. Check Canvas weekly to verify."
        f"</div>"
    )

def build_report(buckets, cutoff, for_ak=False, sources=None, alerts=None, show_banner=False):
    html = ""
    if show_banner: html += _testing_banner()
    if alerts:      html += _alerts_html(alerts)

    upcoming  = buckets.get("upcoming",[])
    due_now   = [a for a in upcoming if a.days_until <= 1]
    due_later = [a for a in upcoming if a.days_until > 1]
    not_sub   = buckets.get("not_submitted",[])
    zeros     = buckets.get("graded_zero",[])

    if due_now:   html += _section(due_now,  "📌 Due Today / Tomorrow", "#8B0000")
    if not_sub:   html += _section(not_sub,  "🔴 Overdue — Not Submitted", "#8B0000")
    if zeros:
        label = "📖 Complete for Mastery — grades will follow" if for_ak else "🟠 Graded Zero"
        html += _section(zeros, label, "#5a4000")
    if due_later: html += _section(due_later,"📅 Upcoming This Week", "#1a2a4a")

    absent = buckets.get("absent_only",[])
    if absent and not for_ak:
        html += _h(f"📋 Absent-Only ({len(absent)}) — likely not required","#aaa")
        rows = [[_d(a.due_date), a.course, a.title[:55]] for a in absent]
        html += _table(["Due","Course","Assignment"], rows)

    src_str = ", ".join(sources) if sources else "Unknown"
    html += (f"<p style='font-size:11px;color:#888;margin-top:12px'>"
             f"Sources: {src_str} · Scope: {_d(cutoff)} onward · "
             f"Not tracked: ELA, World History, Chess, French</p>")
    return f"<div style='font-family:Calibri,Arial,sans-serif;max-width:740px;color:#222'>{html}</div>"

def print_report(buckets, cutoff):
    today = date.today()
    total = sum(len(v) for v in buckets.values())
    print(f"\n{'='*60}\nSchool OS V2 — {today} | {total} items\n{'='*60}")
    for key, label in [("not_submitted","🔴 NOT SUBMITTED"),("graded_zero","🟠 GRADED ZERO"),
                       ("upcoming","📅 UPCOMING"),("absent_only","📋 ABSENT-ONLY")]:
        items = buckets.get(key,[])
        if not items: continue
        print(f"\n{label} ({len(items)}):")
        for a in items:
            tag = f"+{a.days_until}d" if a.days_until >= 0 else f"{a.days_until}d"
            print(f"  {a.due_date} ({tag:>6})  {a.course:<15}  {a.title[:45]}")
