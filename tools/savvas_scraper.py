"""tools/savvas_scraper.py — Playwright scraper + token refresh for Savvas Realize"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.normalizer import Assignment, is_absent_only
from datetime import date, datetime
import requests

# For full Playwright login implementation, see savvas_refresh_token.py (V1)
# This wrapper calls it and provides the normalized interface

def refresh_savvas_token():
    """Run the Playwright login to get a fresh token. Saves to .env."""
    try:
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "tools/savvas_refresh_token.py"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("  Token refreshed successfully")
            return True
        else:
            print(f"  Token refresh failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"  Token refresh error: {e}")
        return False


def fetch_savvas():
    token = os.getenv("SAVVAS_TOKEN","")
    if not token:
        return {"ok": False, "error": "SAVVAS_TOKEN not set — run refresh first", "assignments": []}
    try:
        from savvas_connector import fetch_savvas_assignments, normalize_savvas
        raw  = fetch_savvas_assignments(page_size=50)
        norm = normalize_savvas(raw)
    except ImportError:
        return {"ok": False, "error": "savvas_connector.py not found", "assignments": []}
    except Exception as e:
        return {"ok": False, "error": str(e), "assignments": []}

    out = []
    for a in norm:
        name = a.get("title","")
        out.append(Assignment(
            id=str(a.get("id","")), title=name, course="Math", source="savvas",
            due_date=a["due_date"], submitted=a.get("submitted",False),
            score=a.get("score"), points=a.get("points",0),
            url=a.get("url",""), workflow=a.get("workflow",""),
            absent_only=False, optional="optional" in name.lower()
        ))
    return {"ok": True, "assignments": out, "error": None}
