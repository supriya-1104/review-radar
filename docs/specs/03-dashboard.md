# Spec 03: Dashboard + "Fix this first"

## Goal
An owner opens the dashboard and understands in 30 seconds how they're doing and
what to fix.

## Definitions
- **"This month"** = the last 30 days, compared with the 30 days before it
  ("last month") or the average of the previous 3 × 30 days ("usual").
  The 12-month trend chart uses calendar months. See D6 in DECISIONS.md.

## Layout (Streamlit + Plotly), phone-first, answer first and proof after
Order agreed from the clickable mockup (D5):
https://claude.ai/artifact/HSA5Z4xTQ5arGfruuXAcfK

0. **Place header:** place name, current Google rating, number of reviews
   analysed, the date range "this month" covers, and a "Change place" button.
1. **Summary card (J1):** 2–3 plain sentences on how this month went, ending in
   one "What to do next" action. Shows sample size and cites review IDs.
2. **Fix this first (J2):** top 3 aspects by the priority score from the PRD,
   each with: name, one-sentence summary, and (tap to expand) the score's three
   parts in plain words ("46% of bad reviews mention it", "1.6★ below your
   average", "×2.4 more than usual") plus 3 example quotes linking to the
   full review. The first one is open by default.
3. **What's working (J3):** top 3 positive aspects, each with how often it is
   praised (owners need to know what to protect).
4. **This month vs usual (J4):** two headline cards (average rating vs last
   month; % of 1–3★ reviews vs usual), then a 12-month chart of average rating
   with review count (n) under every month. Grey out months with < 15 reviews
   ("low confidence"); highlight the current period.
5. **What bad reviews are about:** aspects ranked by mentions in 1–3★ reviews,
   this month vs usual.
6. **What changed this month:** biggest rises and falls by aspect.
7. **"Ask the analyst" button** (opens the agent, spec 04).

Design rules: orange = problem, blue = good, never colour alone (arrows and
words carry the meaning); touch targets ≥ 44 px; works at 390 px wide.

## Requirements
- All numbers come from SQL queries in `src/metrics.py`, unit-tested.
- The one-sentence summaries are written by `MODEL_SMART` from the computed
  numbers and quotes only; they must cite review IDs.
- Place picker at the top: paste a new Maps link or choose an analysed place.

## Acceptance criteria
- [ ] All blocks (0–7) render for each of your 3 places, on a phone
- [ ] Every number on screen traceable to a query
- [ ] Ask 2 friends: "What should this business fix first?" They answer
      correctly within 30 seconds without help
