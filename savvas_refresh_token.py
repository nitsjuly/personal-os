"""
savvas_refresh_token.py — Automated Playwright login for Savvas Realize

Login chain (discovered via Chrome DevTools HTML dumps):
  savvasrealize.com → type "Broward" slowly → click a.forwardUrl
  → click button#schoolDistrictLogin → Clever
  → click a.BrowardLogin--submitButton → Microsoft SSO
  → input#i0116 (email) → idSIButton9 (Next)
  → input#i0118 (password) → idSIButton9 (Sign in)
  → idSIButton9 (Yes, stay signed in)
  → Savvas dashboard loads → GraphQL requests fire → token captured

Fast path: persistent browser profile (~5s vs ~30s for full login)
Trigger full login: delete data/savvas_browser_profile/ folder

Run:
  python savvas_refresh_token.py

Force full re-login (Windows):
  rmdir /s /q data\\savvas_browser_profile
  python savvas_refresh_token.py
"""

import asyncio, os
from pathlib import Path
from dotenv import load_dotenv, set_key
load_dotenv()

USERNAME   = os.getenv("CLEVER_USERNAME", "")
PASSWORD   = os.getenv("CLEVER_PASSWORD", "")
CLASS_ID   = os.getenv("SAVVAS_CLASS_ID", "")
STUDENT_ID = os.getenv("SAVVAS_STUDENT_ID", "")
PROFILE_DIR = Path("data/savvas_browser_profile")

# Target URL that triggers the GraphQL request we need the token from
ASSIGNMENTS_URL = (
    f"https://www.savvasrealize.com/community/api/programs/{CLASS_ID}/"
    f"classes/{CLASS_ID}/students/{STUDENT_ID}/assignments"
)

captured_token = None


async def run():
    global captured_token
    from playwright.async_api import async_playwright

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Intercept all requests to capture Bearer token
        def on_request(req):
            global captured_token
            auth = req.headers.get("authorization", "")
            if auth.startswith("Bearer ") and "savvasrealize" in req.url:
                captured_token = auth

        page.on("request", on_request)

        print("  Navigating to Savvas...")
        await page.goto(
            "https://www.savvasrealize.com/dashboard/viewer",
            wait_until="networkidle",
            timeout=30000,
        )

        # Fast path: already logged in via persistent profile
        if "dashboard" in page.url and "login" not in page.url:
            print("  Session active — triggering assignment fetch...")
            await page.goto(ASSIGNMENTS_URL, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            if captured_token:
                print("  ✅ Token captured (fast path — ~5s)")
                await ctx.close()
                return

        # Full login flow
        print("  Full login required...")

        # 1. Type district name slowly (autocomplete is timing-sensitive)
        await page.wait_for_selector("input[placeholder*='district' i]", timeout=10000)
        await page.type("input[placeholder*='district' i]", "Broward", delay=200)
        await page.wait_for_timeout(1500)

        # 2. Click district link (a.forwardUrl — discovered via DevTools HTML dump)
        await page.click("a.forwardUrl", timeout=8000)
        await page.wait_for_load_state("networkidle")

        # 3. District login button → Clever
        await page.click("button#schoolDistrictLogin", timeout=8000)
        await page.wait_for_load_state("networkidle")

        # 4. Clever → Broward Active Directory
        await page.click("a.BrowardLogin--submitButton", timeout=10000)
        await page.wait_for_load_state("networkidle")

        # 5. Microsoft SSO — email
        await page.fill("input#i0116", USERNAME)
        await page.click("input#idSIButton9")
        await page.wait_for_load_state("networkidle")

        # 6. Microsoft SSO — password
        await page.fill("input#i0118", PASSWORD)
        await page.click("input#idSIButton9")
        await page.wait_for_load_state("networkidle")

        # 7. Stay signed in
        try:
            await page.click("input#idSIButton9", timeout=5000)
            await page.wait_for_load_state("networkidle")
        except Exception:
            pass  # KMSI page may not appear on every login

        # 8. Wait for Savvas to load, then trigger assignment fetch
        await page.wait_for_url("**/savvasrealize.com/**", timeout=20000)
        await page.wait_for_timeout(3000)
        await page.goto(ASSIGNMENTS_URL, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        await ctx.close()

    if captured_token:
        print("  ✅ Token captured (full login)")
    else:
        print("  ⚠️  Login completed but no token captured")
        print("     Check: CLEVER_USERNAME/PASSWORD correct? Savvas still uses same login chain?")
        print("     Debug: delete data/savvas_browser_profile/ and rerun to see full browser")


def save_token():
    if not captured_token:
        print("  ❌ Nothing to save")
        return False
    env_path = ".env"
    if os.path.exists(env_path):
        set_key(env_path, "SAVVAS_TOKEN", captured_token)
    else:
        with open(env_path, "a") as f:
            f.write(f"\nSAVVAS_TOKEN={captured_token}\n")
    preview = captured_token[:40] + "..."
    print(f"  Saved to .env: {preview}")
    return True


if __name__ == "__main__":
    if not USERNAME or not PASSWORD:
        print("ERROR: Set CLEVER_USERNAME and CLEVER_PASSWORD in .env first")
        exit(1)
    asyncio.run(run())
    success = save_token()
    exit(0 if success else 1)
