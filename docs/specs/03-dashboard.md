# Spec 03: Dashboard + "Fix this first"

## Goal
An owner opens the dashboard and understands in 30 seconds how they're doing and
what to fix.

## Definitions
- **"This month"** = the last 30 days, compared with the 30 days before it
  ("last month") or the average of the previous 3 × 30 days ("usual").
  The 12-month trend chart uses calendar months. See D6 in DECISIONS.md.

## Layout (Streamlit + Plotly): one phone screen, scroll OR tap
Agreed from the clickable mockup (D5, D7, D8):
https://claude.ai/artifact/HSA5Z4xTQ5arGfruuXAcfK

All sections sit on ONE normal scrolling page, so an owner can just keep
scrolling and see everything (no hidden tab content). A tab bar sticks to the
top once you scroll past the summary, and the bottom bar sticks to the bottom.
Owners choose: scroll, or tap a tab to jump. Both stay in sync: tapping a tab
scrolls to that section; scrolling highlights the tab of the section on screen.

0. **Header:** place name with a ▾ chevron (tap to switch between analysed
   restaurants), "All-time Google rating 4.2★ · 1,012 reviews" (labelled so it
   isn't confused with the 30-day number), and an "+ Add place" button (paste a
   Google Maps link). Entry point for choosing a restaurant.
1. **Summary card (J1):** "LAST 30 DAYS" + exact dates; big average rating with
   "from 41 new reviews" under it; two comparison tiles that show BOTH sides:
   "Previous 30 days 4.3★ · 33 reviews ▼ down 0.4 stars" and "Bad reviews
   (1–3★) 13 of 41 · 32% ▲ usually 16%"; one sentence with counts ("9 of the
   13 bad reviews complain about slow service, 7 of them on Fri–Sun
   evenings"); "Do this next" with a button that jumps to the evidence.
2. **Sticky tabs:** Fix first · Working · Trend · Complaints.
3. **1 · Fix first (J2):** top 3 by the PRD priority score as #1/#2/#3 rows:
   plain name ("Slow service", not "Wait time"), "In 9 of 13 bad reviews ·
   4.5× more than usual", and a % ring. The selected row opens a "Why #1 is on
   this list" card with the score's 3 parts as numbered sentences, then the
   reviews one at a time ("Review 1 of 3") and "Draft reply" (approval needed).
4. **2 · What's working (J3):** "What the 28 good reviews (4–5★) praise", as
   "18 of 28 good reviews (64%)" plus a quote, for the top 3 strengths.
5. **3 · Rating trend (J4):** average rating per calendar month, y-axis
   labelled in stars; tap a dot for "November (1–22 Nov, so far): 3.9★ from 34
   reviews. Down 0.4★ from Oct (4.3★)". < 15 reviews = hollow dashed dot plus
   a "low confidence" sentence explaining why.
6. **4 · All complaints:** what the 13 bad reviews mention, toggle "This month
   (24 Oct – 22 Nov) / A normal month (avg of 3 months before)", badges
   "↑ 7 more / same / ↓ 1 fewer", and a footnote with exact date ranges. Use
   "a normal month" (not "usual") everywhere in the UI.
7. **Bottom bar (sticky), every icon has a text label:** Dashboard · All
   reviews (full list, filterable) · Ask analyst (chat with the agent, spec 04) ·
   Replies (reply drafts waiting for approval; badge = bad reviews with no reply
   yet).

## Clarity rules for every number (think like a Google PM)
- Say **what it is, how many, compared with what, over which period**:
  "13 of 41 reviews were 1–3★ (32%), usually 16%", never just "27% ▲".
- Show both sides of a comparison (4.3★ → 3.9★), not only the change.
- Use counts with percentages ("9 of 13"), so small samples are visible.
- Use the owner's words for aspects ("Slow service", "Price vs portion size").
- Label anything that could be confused (all-time Google rating vs last 30 days;
  calendar month vs last 30 days).
- Every section has a one-line subtitle saying what it shows.
- Chart axes are readable without guessing: months as 3 letters (Jan, Jun,
  Jul, never J/J/J), with the year shown where it changes; y-axis in stars.

Design rules: warm pastel palette on cream (#FBF3E4): teal #2F7F6E (summary
card, good), coral #EE7B8E (problems, rising), yellow #F6B73C (Do this next,
selection, Ask), lavender #B3A8F2 and peach #F7CBA4 as extra card colours,
near-black #1F1D1B for text, the review card and the bottom bar. Elements: big
rounded colourful cards, a decorative curve on the summary card, ranked #1 #2 #3
rows with % rings, a line chart with a tooltip bubble, rounded vertical bars
with values in white circles, pill toggles, round arrow buttons. Text on teal is
white; text on coral, yellow, lavender and peach is near-black (for contrast).
Never colour alone (arrows, words and dashed outlines carry the meaning); touch
targets ≥ 44 px; phone frame 390 × 844 with the middle scrolling. Streamlit can't match every detail;
custom CSS + Plotly get close, and any gaps are noted in DECISIONS.md when we
build (Day 3).

## Requirements
- All numbers come from SQL queries in `src/metrics.py`, unit-tested.
- The one-sentence summaries are written by `MODEL_SMART` from the computed
  numbers and quotes only; they must cite review IDs.
- Place picker at the top: paste a new Maps link or choose an analysed place.

## Acceptance criteria
- [ ] Header, summary and all 4 sections render for each of your 3 places, on a phone;
      tabs and scrolling stay in sync
- [ ] Every number on screen follows the clarity rules above
- [ ] Every number on screen traceable to a query
- [ ] Ask 2 friends: "What should this business fix first?" They answer
      correctly within 30 seconds without help
