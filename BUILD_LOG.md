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

## Day 2: 2026-11-25
- **Goal:** tag what every review is about (11 aspects, D12) plus the dishes it
  names (D9), and check the AI's accuracy by hand.
- **Prompts that worked:** drafting the aspect list from 60 real reviews instead
  of a generic list; "show me 20 random tagged reviews with their quotes".
  Re-checking the SAME 20 reviews after each prompt change (fixed random seed),
  so before/after is a fair comparison.
- **What broke / surprised me:**
  - First pass (Claude's hand-check of 20 Meghana reviews): ~17/20 right.
    Misses: "very quick service" tagged as staff (should be wait time); "taste
    is less than earlier" tagged neutral (should be negative); "Good food" got
    no tag. Dish merges wrong: fresh lime soda -> Mint lime soda, filter coffee
    -> Coffee.
  - Fix 1 ("speed is always wait time") over-corrected: plain "service is
    worst" became wait time. Fix 2 added "plain 'service' with no speed ->
    staff" and "praise + complaint on one aspect -> negative". Lesson: every
    prompt rule can break something else, so re-check the same sample.
  - Dish merging was fixed in code, not the prompt: spelling variants
    (biriyani/briyani/biryani) and word order are merged by a rule first; the
    AI only judges the harder cases. Before that, "Biryani" and "Biriyani"
    showed as two dishes.
  - After both fixes, same 20 reviews: aspects 20/20 right, 1 dish missed
    ("Good Biryani" not listed as a dish). 98–99.7% of quotes found word for
    word; the rest are dropped automatically.
  - Gemini's free tier often returns "503 busy": a full re-tag took 3–5 min per
    place instead of 1–2. Fine for now; watch against the < 3 min target.
- **My own hand-check:** (to fill in: run `python -m src.tag --place meghana
  --sample 20` and count how many I agree with)
- **Claude Code feature learned:** plan -> approve -> build; background runs
  for slow jobs; before/after diffs to judge a prompt change.
- **Commit(s):** tagging (spec 02); prompt + dish-merge fixes.

## Day 3: 2026-11-25
- **Goal:** real dashboard from the mockup: metrics first (tested), then
  Streamlit.
- **Prompts that worked:** "check the real data against each dashboard section
  before building" found that the mockup's 30-day view would be empty for both
  cafes (0 bad reviews with text in 30 days), which led to D13. Comparing two
  Fix-first formulas side by side on real places (D14).
- **What broke / surprised me:** the AI summary said "12 complaints" next to
  "last 30 days" when the 12 were from 12 months: added a code check that the
  period is named. "A normal month 100%" was based on 1 review: now shows the
  sample size. Streamlit stacks columns on phones and hid a button icon behind
  my font override; fixed with CSS.
- **Claude Code feature learned:** checking the app in the browser pane at
  phone size; the playbook's "rewind" to compare A vs B (we compared both in
  one table instead).
- **Commit(s):** metrics + A vs B; AI summary with checks; dashboard.
