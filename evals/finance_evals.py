"""
evals/finance_evals.py — Golden set for finance agent

Concept: Deterministic code for math vs. LLM for reasoning
These tests verify the math layer independently of the LLM.
If finance_calc.py gets the numbers wrong, this catches it.

Run: python evals/finance_evals.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tools.finance_calc import net_by_category, detect_anomalies, check_double_counting


GOLDEN_TRANSACTIONS = [
    # Travel: charge + refund → should net to $70
    {"date": "2026-03-03", "amount": -850,  "category": "Travel",    "merchant": "Delta",        "account": "AmEx"},
    {"date": "2026-03-05", "amount": +780,  "category": "Travel",    "merchant": "Delta Refund", "account": "AmEx"},
    # Travel anomaly: big new charge → 3x baseline
    {"date": "2026-03-12", "amount": -3200, "category": "Travel",    "merchant": "United",       "account": "AmEx"},
    # Groceries: normal
    {"date": "2026-03-07", "amount": -120,  "category": "Groceries", "merchant": "Publix",       "account": "Checking"},
    {"date": "2026-03-08", "amount": -95,   "category": "Groceries", "merchant": "Whole Foods",  "account": "Checking"},
    # Double-count candidate: same amount, same date, two accounts
    {"date": "2026-03-10", "amount": -2800, "category": "Transfer",  "merchant": "Savings xfer", "account": "Checking"},
    {"date": "2026-03-10", "amount": -2800, "category": "Transfer",  "merchant": "Savings xfer", "account": "Savings"},
]


def run_finance_evals():
    print("\n" + "="*60)
    print("FINANCE AGENT EVALS")
    print("="*60)

    net_cats   = net_by_category(GOLDEN_TRANSACTIONS)
    anomalies  = detect_anomalies(GOLDEN_TRANSACTIONS)
    dc_flags   = check_double_counting(GOLDEN_TRANSACTIONS)

    travel_cat = next((c for c in net_cats if c["name"] == "Travel"), None)
    travel_net = travel_cat["net"] if travel_cat else None
    # Expected: -850 + 780 + -3200 = -3270
    expected_travel_net = -3270.0

    grocery_cat = next((c for c in net_cats if c["name"] == "Groceries"), None)
    grocery_net = grocery_cat["net"] if grocery_cat else None
    expected_grocery_net = -215.0

    travel_anomaly = next((a for a in anomalies if a["category"] == "Travel"), None)

    criteria = [
        ("Travel NET is -$3,270 (charge + refund + new charge — not gross)",
         lambda: travel_net == expected_travel_net),

        ("Groceries NET is -$215 (two purchases, no refunds)",
         lambda: grocery_net == expected_grocery_net),

        ("Travel flagged as anomaly (>2x baseline of $400)",
         lambda: travel_anomaly is not None),

        ("Travel anomaly multiple is ~8x",
         lambda: travel_anomaly and travel_anomaly["multiple"] >= 7.0),

        ("Groceries NOT flagged as anomaly ($215 vs $600 baseline)",
         lambda: not any(a["category"] == "Groceries" for a in anomalies)),

        ("Double-count detected for Savings xfer",
         lambda: len(dc_flags) >= 1),

        ("Double-count identifies both accounts",
         lambda: dc_flags and len({dc_flags[0]["account_a"], dc_flags[0]["account_b"]}) == 2),

        ("NET figures are negative for expenses (sign convention correct)",
         lambda: all(c["net"] < 0 for c in net_cats if c["name"] in ["Travel","Groceries"])),
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
    ok = run_finance_evals()
    sys.exit(0 if ok else 1)
