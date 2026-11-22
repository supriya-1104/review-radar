# Decision log

One entry per meaningful decision. These become the decision-log cards in your
portfolio.

## D1: Where reviews come from (Day 1)
- **Context:** Google Places API (official) returns only 5 reviews per place.
  Google Business Profile API returns all reviews but only for businesses you own.
- **Options:** Places API (5 reviews) · Business Profile API (owner only) ·
  third-party scraper APIs (Apify, SerpApi, Outscraper).
- **Decision:** Apify reviews actor for the prototype.
- **Trade-off:** full review history and low cost, but relies on a third party
  and Google's terms; for a real product, owners would connect their Business
  Profile instead (the right long-term path).
- **Result:**

## D2: Which 3 places (Day 1)
- **Context:**
- **Options:**
- **Decision:**
- **Trade-off:**
- **Result:**

## D3: No agent framework (Day 1)
- **Decision:** plain Gemini SDK tool loop (was Anthropic; see D4).
- **Trade-off:** more code, but every step is visible and explainable in an
  interview. Could port to LangGraph later.

## D4: LLM provider = Google Gemini, free tier (Day 1, 2026-11-22)
- **Context:** The kit assumed the Anthropic API, which is paid only. I have a
  free Gemini API key and want to keep prototype costs near zero (PRD target:
  < $0.50 per place).
- **Options:** Anthropic API (paid, original plan) · Gemini API free tier ·
  a switch supporting both (more code than we need now).
- **Decision:** Gemini via the `google-genai` SDK. Tested on my key:
  `MODEL_FAST=gemini-3.5-flash-lite` (~1.5 s per call) for tagging,
  `MODEL_SMART=gemini-3.6-flash` (~4 s) for summaries and the analyst.
  Pinned versions, not `-latest` aliases, so eval results don't shift silently.
  Pro models weren't available on my free key.
- **Trade-off:** Free, and supports tool use, so the hand-written agent loop
  and Phoenix tracing still work. But free-tier rate limits may make tagging
  1,000 reviews slower than the < 3 min target (check on Day 2), and on the free
  tier Google may use submitted data to improve its products (reviews are
  public, so low risk; re-check terms before real owners use it). Keeping all
  LLM calls in one module so switching back is a small change.
- **Result:**

## D5: Dashboard order: answer first, proof after (2026-11-22)
- **Context:** Spec 03 opened with number cards and a trend chart. The owner
  checks the dashboard on a phone between services with ~10 minutes a week,
  and the PRD's first job (J1) is a 30-second summary, which the spec lacked.
- **Options:** numbers first (spec as written) · answer first: summary →
  Fix this first → What's working → numbers and charts as proof.
- **Decision:** answer first, plus a new summary card ending in "What to do
  next". Agreed from a clickable phone mockup:
  https://claude.ai/artifact/HSA5Z4xTQ5arGfruuXAcfK
- **Trade-off:** owners who like to see the trend first must scroll; the
  summary is LLM-written, so it carries the most hallucination risk and must
  cite review IDs and use only SQL numbers.
- **Result:**

## D6: "This month" = last 30 days (2026-11-22)
- **Context:** "This month" drives the header cards, "what bad reviews are
  about" and "what changed". A calendar month is nearly empty early on.
- **Options:** last 30 days · calendar month so far · last full calendar month.
- **Decision:** last 30 days, compared with the previous 30 days ("last
  month") and the average of the previous 3 × 30 days ("usual"). The 12-month
  trend chart still uses calendar months, which owners read more easily.
- **Trade-off:** always a full window of reviews and never out of date, but
  "the last 30 days" doesn't match how owners say "November", so the dashboard
  must show the exact date range. Two time definitions on one screen (30-day
  cards, calendar-month chart) could confuse; check in owner interviews.
- **Result:**

## D7: One screen with tabs, black/white + a little yellow (2026-11-22)
- **Context:** The long-scroll mockup (D5) was too much scrolling; an owner
  checking between services won't scroll through 7 blocks.
- **Options:** long scroll (D5) · one screen: summary always on top, the rest
  in tabs ordered by importance.
- **Decision:** one 390 × 844 screen. Summary + "Do this next" always visible;
  tabs Fix first (default) → Working → Trends → Issues. "What bad reviews are
  about" and "What changed" merged into Issues. Palette first black/white +
  yellow, then changed to a warm pastel set (teal, coral, yellow, cream) from
  a reference I liked; black/white felt flat.
- **Trade-off:** far less scrolling and a clearer priority, but anything not in
  the default tab is one tap away and may go unseen; reviews behind a problem
  are shown one at a time. Check in owner interviews whether they open the other tabs.
- **Result:**

## D8: Scroll or tap, and explicit numbers (2026-11-22)
- **Context:** Reviewing the tabbed mockup (D7): numbers like "3.9 ▼0.4" and
  "27%" were vague (of what? compared with what?), and hiding sections behind
  tabs forced tapping when sometimes scrolling is more natural.
- **Options:** tabs only (D7) · long scroll only (D5) · one scrolling page with
  a sticky tab bar that jumps to sections and follows the scroll.
- **Decision:** scroll + sticky tabs, kept in sync. Every number states what,
  how many, compared with what, and over which period, with counts next to
  percentages (rules in spec 03).
- **Trade-off:** longer labels take more space and the page is longer again,
  but owners can trust and act on what they read. Streamlit has no built-in
  scroll-synced tabs; needs a small custom component or anchor links (Day 3).
- **Result:**

## D9: Dishes from review text, not from bills (2026-11-22)
- **Context:** Owners want to know which dishes people talk about. Idea: link
  each review to the customer's bill and read the items they ordered.
- **Options:** link reviews to bills (POS data) · extract dish names from the
  review text · later, use aggregate sales per dish (no customer data).
- **Decision:** v1 extracts dish names from review text in the same tagging
  call (spec 02). Bill linking is out of scope. Aggregate sales per dish is a v2
  idea to normalise complaints ("3 complaints per 1,000 biryanis sold").
- **Why not bills:** a Google review has only a display name, so matching to a
  bill is guesswork (group bills, walk-ins, reviews posted days later); linking
  a public review to a private purchase record identifies customers, needs
  consent (e.g. India's DPDP Act) and breaks our rule of hashing reviewer names;
  it also needs an integration per billing system, far beyond 2 weeks.
- **Trade-off:** we only see dishes reviewers chose to name, so quiet dishes are
  invisible and popular dishes get more mentions. Aggregate sales data in v2
  would correct for popularity.
- **Result:**
