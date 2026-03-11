# v1 Approach Notes — Manual Savvas Login

Before Playwright automation worked, the approach was:
1. User ran a guided script that opened a browser
2. Paused at each login step for manual completion
3. Captured the token after the user navigated to the assignments page

This was replaced by full Playwright automation once the correct CSS selectors
were identified via Chrome DevTools HTML dumps (not guessing).

Key selector discoveries:
- `a.forwardUrl` — district selection link (NOT a button, NOT a click on the dropdown)
- `button#schoolDistrictLogin` — Clever redirect button
- `a.BrowardLogin--submitButton` — Broward Active Directory link on Clever page
- `input#i0116`, `input#i0118`, `input#idSIButton9` — Microsoft SSO selectors (standard)

Lesson: DevTools → Network → XHR tab → find the GraphQL request → inspect request headers
to see the exact Authorization value. This is faster than any amount of selector guessing.
