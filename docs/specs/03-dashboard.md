# Spec 03: Dashboard + "Fix this first"

## Goal
An owner opens the dashboard and understands in 30 seconds how they're doing and
what to fix.

## Definitions
- **"This month"** = the last 30 days, compared with the 30 days before it
  ("last month") or the average of the previous 3 × 30 days ("usual").
  The 12-month trend chart uses calendar months. See D6 in DECISIONS.md.

## Layout (Streamlit + Plotly): one phone screen, no long scroll
Agreed from the clickable mockup (D5, D7):
https://claude.ai/artifact/HSA5Z4xTQ5arGfruuXAcfK

Always visible, most important first:
0. **Place header:** place name, Google rating, reviews analysed, "Change place".
1. **Summary card (J1):** big average rating for the last 30 days with ▲/▼ vs
   the previous 30 days, % bad reviews vs usual, review count (sample size),
   1–2 plain sentences, and one "Do this next" action. Cites review IDs.
2. **Tabs** (one shown at a time, "Fix first" open by default):
   - **Fix first (J2):** top 3 aspects by the PRD priority score as 3 tappable
     pills. The selected one shows the score's three parts in plain words
     ("46% of bad reviews", "−1.6★ vs your average", "×2.4 vs usual"), a
     rising/steady tag, and one review at a time with ‹ › to step through 3,
     plus "Draft reply" (saved only after approval).
   - **Working (J3):** top 3 positive aspects with % of good reviews praising each.
   - **Trends (J4):** 12 calendar-month rating bars; tap a month to see its
     rating, review count and "low confidence" if < 15 reviews (dashed bar).
   - **Issues:** what bad reviews are about (old blocks 5 + 6 merged): aspects
     by mentions in 1–3★ reviews, toggle "Last 30 days / Usual", with a change
     badge (↑ 11 / ↓ 2 / same) that replaces the separate "What changed" block.
3. **Bottom bar:** Home, All reviews, **Ask analyst** (spec 04), Reply drafts
   (badge = unanswered bad reviews).

Design rules: black and white with a little yellow (#FFD43B). Yellow only
marks what matters most: "Do this next", the selected item, big rises, the Ask
button. Never yellow text on white. Never colour alone (arrows, words and
dashed outlines carry the meaning); touch targets ≥ 44 px; fits a 390 × 844
screen. Streamlit can't match every detail; custom CSS + Plotly get close, and
any gaps are noted in DECISIONS.md when we build (Day 3).

## Requirements
- All numbers come from SQL queries in `src/metrics.py`, unit-tested.
- The one-sentence summaries are written by `MODEL_SMART` from the computed
  numbers and quotes only; they must cite review IDs.
- Place picker at the top: paste a new Maps link or choose an analysed place.

## Acceptance criteria
- [ ] Header, summary and all 4 tabs render for each of your 3 places, on a phone,
      without scrolling the main screen
- [ ] Every number on screen traceable to a query
- [ ] Ask 2 friends: "What should this business fix first?" They answer
      correctly within 30 seconds without help
