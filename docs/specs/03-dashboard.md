# Spec 03: Dashboard + "Fix this first"

## Goal
An owner opens the dashboard and understands in 30 seconds how they're doing and
what to fix.

## Layout (Streamlit + Plotly)
1. **Header cards:** current Google rating, this month's average rating vs last
   month (▲/▼ and by how much), number of reviews this month, % negative.
2. **Monthly trend:** average rating and review volume per month for 12 months.
   Show sample size; grey out months with < 15 reviews ("low confidence").
3. **What bad reviews are about:** aspects ranked by negative mentions in 1–3
   star reviews, this month vs previous 3 months.
4. **Fix this first:** top 3 aspects by the priority score from the PRD, each
   with: one-sentence summary, the score's three parts shown plainly, and 3
   example quotes (clickable to the full review).
5. **What's working:** top 3 positive aspects (owners need to know what to protect).
6. **What changed this month:** biggest rises and falls by aspect.

## Requirements
- All numbers come from SQL queries in `src/metrics.py`, unit-tested.
- The one-sentence summaries are written by `MODEL_SMART` from the computed
  numbers and quotes only; they must cite review IDs.
- Place picker at the top: paste a new Maps link or choose an analysed place.

## Acceptance criteria
- [ ] All 6 blocks render for each of your 3 places
- [ ] Every number on screen traceable to a query
- [ ] Ask 2 friends: "What should this business fix first?" They answer
      correctly within 30 seconds without help
