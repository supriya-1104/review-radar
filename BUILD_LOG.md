# Build log

One entry per day. Short and honest. This becomes your "How I PM'd an AI coding
agent" story.

## Day 1: 2026-11-22 to 2026-11-25
- **Goal:** set up the repo, design the dashboard early, and pull real reviews
  for 3 Bengaluru places.
- **Prompts that worked:** "Summarise the product in 5 bullets and list what's
  unclear or risky"; "compare two Apify actors on price, exact dates and
  reliability, then plan the ingest, don't write code yet". Asking for a
  clickable mockup before any dashboard code saved a lot of rework (D5–D8).
- **What broke / surprised me:** my "Anthropic" key was actually a Gemini key,
  so we switched to Gemini (D4). GitHub push hung on a stale saved login, and
  the new repo already had a README commit (merged it). Apify reports the cost
  a moment after the run ends (first run showed $0.01 instead of $0.09). Most
  reviews are stars only: Meghana has 181 text reviews out of 500. Café Coffee
  Day gets almost no new reviews (8 in 6 months).
- **Claude Code feature learned:** CLAUDE.md as the project rulebook; plan
  first, approve, then build; the decision log as a habit.
- **Commit(s):** setup, Gemini switch, dashboard spec iterations (D5–D9),
  ingest (`python -m src.ingest`).
