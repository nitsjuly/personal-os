# AGENTS.md — Agent Behavior Rules, Tool List, MCP Config

## Agent Roster

| Agent | File | Runs | Model |
|-------|------|------|-------|
| School | agents/school_agent.py | Daily 7am + 8pm | Haiku |
| Finance | agents/finance_agent.py | Mon 8am + 1st of month | Sonnet |
| Health | agents/health_agent.py | 1st of month | Haiku |

## What Each Agent Owns

**school_agent.py**
- Reads: Canvas API, Savvas GraphQL (via Playwright token)
- Writes: Email to student + parents
- Fails loudly: source failures named explicitly in email
- Never: guesses at missing data, combines sources without labeling

**finance_agent.py**
- Reads: Monarch Money (MCP, when configured) or manual CSV
- Computes: via tools/finance_calc.py ONLY — no math in prose
- Writes: Email (weekly alert or monthly draft)
- Monthly: drafts first, waits for human approval before sending
- Never: auto-sends finance reports, combines contributions + growth, reports gross for travel

**health_agent.py**
- Reads: private/health-roster.md (re-read every run)
- Cross-checks: private/family-constraints.md before any scheduling suggestion
- Writes: Email reminder (informational — no calendar writes without confirmation)
- Never: surfaces resolved items, suggests dates without constraint check, writes to calendar

## Cross-Agent Rules
- Agents share tools/ but never share state
- A failure in one agent does not suppress output from others
- All external communications require human approval
- All calendar writes require human confirmation
- All .md reference file updates require human confirmation

## Tool List

| Tool | Purpose | Deterministic? |
|------|---------|----------------|
| canvas_api.py | Fetch Canvas assignments | Yes |
| savvas_scraper.py | Fetch Savvas Math via GraphQL | Yes (Playwright) |
| finance_calc.py | ALL financial math | Yes (Python only) |
| calendar_check.py | Constraint check before scheduling | Yes |
| notifier.py | Email delivery | Yes |
| mock_data.py | Test fixtures | Yes |

## MCP Configuration

```json
{
  "servers": {
    "gmail": {
      "url": "https://gmail.mcp.claude.com/mcp",
      "tools": ["send_email", "read_email", "search_email"]
    },
    "gcal": {
      "url": "https://gcal.mcp.claude.com/mcp",
      "tools": ["list_events", "create_event", "check_availability"]
    }
  }
}
```

Note: Calendar creates are disabled by default. Enable only after confirming HITL gate is in place.
