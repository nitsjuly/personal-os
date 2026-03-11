"""
agents/finance_agent.py — Finance Agent

Concept: Deterministic code for math vs. LLM for reasoning
ALL numbers flow through tools/finance_calc.py (Python).
This agent only reads results and writes narrative. It never
adds, subtracts, or computes percentages in prose.

Concept: Human-in-the-loop interrupt design
Monthly report is DRAFTED first. User reviews before it sends.
Anomaly alerts are immediate — but framed as questions, not alerts.

Modes:
  --mode=weekly    anomaly check only
  --mode=monthly   full report (draft → review → send)
  --test           sample data, no sends, no review gate
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.finance_calc import (
    net_by_category,
    separate_contributions_from_growth,
    detect_anomalies,
    compute_fire_progress,
    check_double_counting,
)
from tools.notifier import send_email
from dotenv import load_dotenv
load_dotenv()

TEST  = "--test" in sys.argv
MODE  = next((a.split("=")[1] for a in sys.argv if a.startswith("--mode=")), "weekly")

FINANCE_RECIPIENT = os.getenv("PARENT1_EMAIL", "")  # finance email goes to primary parent


# ── DATA LOADING ─────────────────────────────────────────────────────────────
def load_transactions():
    """
    Concept: RAG retrieval reliability
    Data source priority:
    1. Monarch Money API (when connected via MCP)
    2. Manual CSV export (fallback — always works)
    3. Test fixture (--test mode)

    If source 1 fails, we don't silently fall to source 3.
    We surface the gap: "Using manual CSV from [date] — Monarch unavailable."
    """
    if TEST:
        return _test_transactions()

    # Attempt Monarch API (MCP — stub for now)
    monarch_result = _try_monarch_api()
    if monarch_result["ok"]:
        return monarch_result["data"], "Monarch Money (live)"

    # Fallback: manual CSV
    csv_path = os.getenv("FINANCE_CSV_PATH", "private/transactions.csv")
    if os.path.exists(csv_path):
        import csv
        from datetime import datetime
        rows = []
        with open(csv_path) as f:
            for row in csv.DictReader(f):
                rows.append({
                    "date":     row.get("Date", ""),
                    "amount":   float(row.get("Amount", 0)),
                    "category": row.get("Category", "Uncategorized"),
                    "merchant": row.get("Merchant", ""),
                    "account":  row.get("Account", ""),
                })
        mtime = os.path.getmtime(csv_path)
        from datetime import datetime
        age   = (datetime.now() - datetime.fromtimestamp(mtime)).days
        return rows, f"Manual CSV (exported {age} day(s) ago — Monarch unavailable)"

    # Neither worked — explicit failure
    return None, "NO DATA SOURCE AVAILABLE — Monarch failed, no CSV found"


def _try_monarch_api():
    """Stub: replace with actual MCP call when Monarch MCP is connected."""
    return {"ok": False, "error": "Monarch MCP not yet configured"}


def _test_transactions():
    """Golden test fixture — used for evals and --test mode."""
    return [
        {"date": "2026-03-01", "amount": -4200, "category": "Housing",    "merchant": "Mortgage",      "account": "Checking"},
        {"date": "2026-03-03", "amount": -850,  "category": "Travel",     "merchant": "Delta",         "account": "AmEx"},
        {"date": "2026-03-05", "amount": +780,  "category": "Travel",     "merchant": "Delta Refund",  "account": "AmEx"},
        {"date": "2026-03-07", "amount": -120,  "category": "Groceries",  "merchant": "Publix",        "account": "Checking"},
        {"date": "2026-03-08", "amount": -95,   "category": "Groceries",  "merchant": "Whole Foods",   "account": "Checking"},
        {"date": "2026-03-10", "amount": +2800, "category": "Income",     "merchant": "Rental",        "account": "Checking"},
        {"date": "2026-03-10", "amount": -2800, "category": "Income",     "merchant": "Rental",        "account": "Savings"},  # flag: double count?
        {"date": "2026-03-12", "amount": -3200, "category": "Travel",     "merchant": "United",        "account": "AmEx"},  # anomaly: 3x avg
        {"date": "2026-03-15", "amount": -500,  "category": "Investments","merchant": "Fidelity 401k", "account": "Fidelity"},
    ], "Test fixture"


# ── REPORT BUILDER ────────────────────────────────────────────────────────────
def build_weekly_alert(transactions, source_note):
    """
    Concept: Anomaly alerts as questions, not warnings.
    "Flight spend is 3x last month — expected?" is better than
    "WARNING: Unusual flight spend detected."
    The former invites a response. The latter creates anxiety.
    """
    if transactions is None:
        return _source_failure_html(source_note), True

    # All math in Python — not in this function
    anomalies = detect_anomalies(transactions)
    double_count_flags = check_double_counting(transactions)

    if not anomalies and not double_count_flags:
        return None, False  # Nothing to surface this week

    html  = f"<div style='font-family:Calibri,Arial,sans-serif;max-width:700px'>"
    html += f"<div style='background:#1a2a4a;padding:12px 20px;border-radius:6px 6px 0 0'>"
    html += f"<h2 style='color:white;margin:0;font-size:16px'>Finance — Weekly Check</h2></div>"
    html += f"<div style='padding:16px;background:#fff'>"
    html += f"<p style='font-size:12px;color:#888'>Source: {source_note}</p>"

    for a in anomalies:
        # Frame as a question — Concept: HITL interrupt design
        html += (
            f"<div style='background:#fff8e1;border-left:4px solid #f9a825;"
            f"padding:10px 14px;margin:8px 0;border-radius:0 4px 4px 0'>"
            f"<b>{a['category']}</b> spend is {a['multiple']}x last month "
            f"({a['currency_display']}) — expected?<br>"
            f"<span style='font-size:11px;color:#888'>Largest item: {a['top_merchant']} ({a['top_amount']})</span>"
            f"</div>"
        )

    for dc in double_count_flags:
        html += (
            f"<div style='background:#fce4ec;border-left:4px solid #c62828;"
            f"padding:10px 14px;margin:8px 0;border-radius:0 4px 4px 0'>"
            f"⚠️ Possible double-count: <b>{dc['merchant']}</b> appears in both "
            f"{dc['account_a']} and {dc['account_b']} on {dc['date']} — same amount: {dc['amount_display']}"
            f"</div>"
        )

    html += "</div></div>"
    return html, True


def build_monthly_report(transactions, source_note):
    """
    Concept: Deterministic code for math vs. LLM for reasoning
    All numbers computed in finance_calc.py. This function only
    assembles the narrative around Python-confirmed figures.
    """
    if transactions is None:
        return _source_failure_html(source_note)

    net_cats     = net_by_category(transactions)
    portfolio    = separate_contributions_from_growth()
    fire         = compute_fire_progress()
    anomalies    = detect_anomalies(transactions)
    double_count = check_double_counting(transactions)

    html  = "<div style='font-family:Calibri,Arial,sans-serif;max-width:700px'>"
    html += "<div style='background:#1a2a4a;padding:12px 20px;border-radius:6px 6px 0 0'>"
    html += "<h2 style='color:white;margin:0'>Finance — Monthly Report</h2></div>"
    html += "<div style='padding:16px;background:#fff'>"
    html += f"<p style='font-size:12px;color:#888'>Source: {source_note}</p>"

    # Section 1: Anomalies first (what needs attention)
    if anomalies:
        html += "<h3 style='color:#1a2a4a;border-bottom:2px solid #1a2a4a;padding-bottom:3px'>Questions for Review</h3>"
        for a in anomalies:
            html += (
                f"<div style='background:#fff8e1;border-left:4px solid #f9a825;"
                f"padding:10px 14px;margin:8px 0'>"
                f"<b>{a['category']}</b>: {a['multiple']}x last month — expected?"
                f"</div>"
            )

    # Section 2: Spending by category (net)
    html += "<h3 style='color:#1a2a4a;border-bottom:2px solid #1a2a4a;padding-bottom:3px'>Spending by Category (NET)</h3>"
    html += "<table style='border-collapse:collapse;width:100%;font-size:13px'>"
    html += "<tr><th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:left'>Category</th>"
    html += "<th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:right'>This Month</th>"
    html += "<th style='background:#1a2a4a;color:white;padding:6px 10px;text-align:right'>Delta</th></tr>"
    for cat in net_cats:
        delta_color = "#c00" if cat.get("delta_pct", 0) > 20 else "#2a7a2a" if cat.get("delta_pct", 0) < -10 else "#333"
        html += (
            f"<tr><td style='padding:5px 10px;border-bottom:1px solid #eee'>{cat['name']}</td>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee;text-align:right'>{cat['net_display']}</td>"
            f"<td style='padding:5px 10px;border-bottom:1px solid #eee;text-align:right;color:{delta_color}'>{cat.get('delta_display','—')}</td></tr>"
        )
    html += "</table>"

    # Section 3: Portfolio (contributions SEPARATE from growth — always)
    html += "<h3 style='color:#1a2a4a;border-bottom:2px solid #1a2a4a;padding-bottom:3px;margin-top:20px'>Portfolio</h3>"
    html += "<div style='background:#f0f4ff;border:1px solid #c0c8e8;border-radius:4px;padding:12px'>"
    html += f"<b>Total Value:</b> {portfolio.get('total_display','[needs data]')}<br>"
    html += f"<b>Your contributions:</b> {portfolio.get('contributions_display','[needs data]')} "
    html += f"— <span style='font-size:11px;color:#888'>this is money you put in</span><br>"
    html += f"<b>Market growth:</b> {portfolio.get('growth_display','[needs data]')} "
    html += f"— <span style='font-size:11px;color:#888'>this is the market's work, not yours</span><br>"
    html += f"<span style='font-size:11px;color:#c00'>⚠️ Retirement projections require human review — not shown automatically.</span>"
    html += "</div>"

    # Section 4: FIRE progress
    html += "<h3 style='color:#1a2a4a;border-bottom:2px solid #1a2a4a;padding-bottom:3px;margin-top:20px'>FIRE Progress</h3>"
    if fire.get("incomplete"):
        html += f"<div style='background:#fff3cd;padding:10px;border-radius:4px'>{fire['incomplete']}</div>"
    else:
        html += f"<p>Savings rate: <b>{fire.get('savings_rate','—')}</b> (target: {fire.get('target_rate','—')})<br>"
        html += f"Trajectory: <b>{fire.get('trajectory','—')}</b></p>"

    # Source footnote
    html += f"<p style='font-size:11px;color:#888;margin-top:16px'>All figures are NET. Contributions and market growth are always shown separately. Data: {source_note}</p>"
    html += "</div></div>"
    return html


def _source_failure_html(note):
    return (
        "<div style='background:#fce4ec;border:2px solid #c62828;border-radius:6px;padding:14px'>"
        "<b>⚠️ Finance report could not run — data source unavailable.</b><br>"
        f"Reason: {note}<br>"
        "No figures are shown. Do not interpret absence of data as 'no issues.'"
        "</div>"
    )


# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    transactions, source_note = load_transactions()

    if MODE == "weekly" or TEST:
        html, has_alerts = build_weekly_alert(transactions, source_note)
        if TEST:
            print(f"[TEST] Weekly alert generated. Has alerts: {has_alerts}")
            if html: print(html[:400], "...")
        elif has_alerts and html:
            send_email(FINANCE_RECIPIENT, "Finance — Weekly Check", html)
            print(f"  Weekly alert sent to {FINANCE_RECIPIENT}")
        else:
            print("  No anomalies this week — no email sent.")

    elif MODE == "monthly":
        html = build_monthly_report(transactions, source_note)
        if TEST:
            print("[TEST] Monthly report generated.")
            print(html[:400], "...")
        else:
            # Concept: Human-in-the-loop — draft first, review before send
            print("\n── MONTHLY FINANCE REPORT DRAFT ──")
            print("Review the draft. Send? [y/n]: ", end="")
            answer = input().strip().lower()
            if answer == "y":
                send_email(FINANCE_RECIPIENT, "Finance — Monthly Report", html)
                print(f"  Monthly report sent to {FINANCE_RECIPIENT}")
            else:
                print("  Cancelled. Draft saved to logs/finance_draft.html")
                os.makedirs("logs", exist_ok=True)
                with open("logs/finance_draft.html", "w") as f:
                    f.write(html)
