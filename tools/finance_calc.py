"""
tools/finance_calc.py — ALL financial math lives here

Concept: Deterministic code for math vs. LLM for reasoning

This file is the single place where numbers are computed. The LLM
(finance_agent.py) calls these functions and narrates the results.
It never does math in prose. This means:
- Every calculation is auditable (add a print() to see exactly what happened)
- Rounding and edge cases are handled once, not scattered across prompts
- A test suite can verify numbers independently of any LLM

Nothing in this file calls an LLM. Nothing in this file sends email.
It takes data in, returns structured results out.
"""

from collections import defaultdict
from datetime import date, datetime
import os


# ── PRIOR MONTH BASELINE (loaded from file or hardcoded for now) ──────────────
def _load_prior_month_baselines():
    """
    Baseline for anomaly detection. Replace with DB/file lookup as system matures.
    Values represent typical monthly spend per category.
    """
    return {
        "Housing":     4200,
        "Groceries":   600,
        "Travel":      400,
        "Dining":      300,
        "Utilities":   200,
        "Investments": 2000,
        "Income":      -10000,   # negative = inflow
    }


# ── NET BY CATEGORY ───────────────────────────────────────────────────────────
def net_by_category(transactions):
    """
    Compute NET spend per category.

    Why NET and not gross?
    A flight charge of $850 and a refund of $780 in the same period
    nets to $70 — not $850 spend. Reporting gross would overstate
    travel spend by 10x and trigger a false anomaly.

    Returns list of dicts sorted by absolute net spend descending.
    """
    category_totals = defaultdict(float)
    for t in transactions:
        category_totals[t["category"]] += t["amount"]

    baselines = _load_prior_month_baselines()
    result    = []
    for cat, net in sorted(category_totals.items(), key=lambda x: abs(x[1]), reverse=True):
        baseline = baselines.get(cat, 0)
        delta    = net - baseline
        delta_pct = round((delta / abs(baseline)) * 100) if baseline != 0 else None

        result.append({
            "name":          cat,
            "net":           round(net, 2),
            "net_display":   f"${abs(net):,.2f}" + (" (refund net)" if net > 0 and cat not in ["Income","Rental"] else ""),
            "baseline":      baseline,
            "delta":         round(delta, 2),
            "delta_display": f"+${delta:,.2f}" if delta > 0 else f"-${abs(delta):,.2f}",
            "delta_pct":     delta_pct,
        })
    return result


# ── ANOMALY DETECTION ─────────────────────────────────────────────────────────
def detect_anomalies(transactions, threshold_multiple=2.0):
    """
    Flag categories where NET spend is > threshold_multiple of baseline.

    Why threshold_multiple=2.0?
    2x is large enough to be meaningful, small enough to catch real drift.
    Configurable via account-structure.md when that's wired up.

    Returns list of anomaly dicts — never raises, never silently drops.
    """
    baselines = _load_prior_month_baselines()
    net_cats  = net_by_category(transactions)
    anomalies = []

    for cat in net_cats:
        baseline = baselines.get(cat["name"])
        if not baseline or baseline <= 0:
            continue   # Skip income categories and unknowns
        multiple = abs(cat["net"]) / baseline
        if multiple >= threshold_multiple:
            # Find top merchant in this category
            cat_txns = [t for t in transactions if t["category"] == cat["name"] and t["amount"] < 0]
            top_txn  = max(cat_txns, key=lambda t: abs(t["amount"])) if cat_txns else None
            anomalies.append({
                "category":        cat["name"],
                "net":             cat["net"],
                "currency_display": cat["net_display"],
                "baseline":        baseline,
                "multiple":        round(multiple, 1),
                "top_merchant":    top_txn["merchant"] if top_txn else "—",
                "top_amount":      f"${abs(top_txn['amount']):,.2f}" if top_txn else "—",
            })

    return anomalies


# ── DOUBLE-COUNT DETECTION ────────────────────────────────────────────────────
def check_double_counting(transactions):
    """
    Detect the same transaction appearing in two accounts on the same date.

    This is a real failure mode: Plaid sometimes returns a transfer
    as an expense in both the source AND destination account.
    Net effect: spending is overstated by the transfer amount.

    Returns list of suspected double-counts for human review.
    Never auto-removes — always surfaces for confirmation.
    """
    flags = []
    # Group by (date, abs_amount)
    by_key = defaultdict(list)
    for t in transactions:
        key = (t["date"], round(abs(t["amount"]), 2))
        by_key[key].append(t)

    for (date_str, amount), group in by_key.items():
        if len(group) >= 2:
            accounts = list({t["account"] for t in group})
            if len(accounts) >= 2:
                flags.append({
                    "date":           date_str,
                    "amount":         amount,
                    "amount_display": f"${amount:,.2f}",
                    "account_a":      accounts[0],
                    "account_b":      accounts[1],
                    "merchant":       group[0].get("merchant", "Unknown"),
                    "transactions":   group,
                })
    return flags


# ── PORTFOLIO (stub — replace with real data source) ─────────────────────────
def separate_contributions_from_growth():
    """
    Concept: Contributions and market growth are NEVER combined.

    A $500 deposit and $500 in market gains are not the same thing.
    One reflects your behavior. The other reflects market behavior.
    Combining them masks your actual savings rate.

    This function returns a dict with both, always separately.
    If data is incomplete, it says so explicitly — does not estimate.
    """
    # TODO: wire to Fidelity/Robinhood export or manual CSV
    total_value   = _read_portfolio_value()
    contributions = _read_contributions_ytd()
    growth        = (total_value - contributions) if (total_value and contributions) else None

    return {
        "total":               total_value,
        "total_display":       f"${total_value:,.2f}" if total_value else "[needs data — connect brokerage export]",
        "contributions":       contributions,
        "contributions_display": f"${contributions:,.2f}" if contributions else "[needs data]",
        "growth":              growth,
        "growth_display":      f"${growth:,.2f}" if growth is not None else "[derived from total − contributions]",
        "incomplete":          not (total_value and contributions),
    }


def _read_portfolio_value():
    """Read from manual export file. Returns None if not available."""
    path = os.getenv("PORTFOLIO_VALUE_PATH", "private/portfolio_value.txt")
    if os.path.exists(path):
        try:
            return float(open(path).read().strip().replace("$", "").replace(",", ""))
        except Exception:
            return None
    return None


def _read_contributions_ytd():
    """Read YTD contributions from file. Returns None if not available."""
    path = os.getenv("CONTRIBUTIONS_PATH", "private/contributions_ytd.txt")
    if os.path.exists(path):
        try:
            return float(open(path).read().strip().replace("$", "").replace(",", ""))
        except Exception:
            return None
    return None


# ── FIRE PROGRESS ─────────────────────────────────────────────────────────────
def compute_fire_progress():
    """
    FIRE metric is savings rate + trajectory — NOT just net worth.

    Net worth can go up due to market returns while savings rate
    drops. The leading indicator is savings rate. Always show both.

    Retirement projections always require human review —
    never presented automatically as a confident number.
    """
    # TODO: wire to account-structure.md FIRE targets
    monthly_income   = _get_env_float("MONTHLY_INCOME_NET")
    monthly_savings  = _get_env_float("MONTHLY_SAVINGS")
    fire_target      = _get_env_float("FIRE_TARGET")
    current_nw       = _read_portfolio_value()

    if not all([monthly_income, monthly_savings, fire_target, current_nw]):
        missing = [k for k, v in {
            "MONTHLY_INCOME_NET": monthly_income,
            "MONTHLY_SAVINGS": monthly_savings,
            "FIRE_TARGET": fire_target,
            "portfolio value": current_nw,
        }.items() if not v]
        return {
            "incomplete": f"FIRE calculation incomplete — missing: {', '.join(missing)}. "
                          f"Add to .env or account-structure.md."
        }

    savings_rate     = round(monthly_savings / monthly_income * 100, 1)
    target_rate      = float(os.getenv("FIRE_TARGET_SAVINGS_RATE", "40"))
    pct_to_fire      = round(current_nw / fire_target * 100, 1)
    on_track         = savings_rate >= target_rate

    return {
        "savings_rate":   f"{savings_rate}%",
        "target_rate":    f"{target_rate}%",
        "pct_to_fire":    f"{pct_to_fire}%",
        "trajectory":     f"{'On track' if on_track else 'Behind'} — {pct_to_fire}% to FIRE target",
        "note":           "Projection requires human review — not shown automatically.",
        "incomplete":     None,
    }


def _get_env_float(key):
    val = os.getenv(key)
    if val:
        try:
            return float(val.replace("$", "").replace(",", ""))
        except Exception:
            return None
    return None
