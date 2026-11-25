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
- **Result:** Compass Google Maps Reviews Scraper works (see D10): 1,149
  reviews from 3 places for $0.61, exact dates, owner replies.

## D2: Which 3 places (Day 1, 2026-11-25)
- **Context:** Spec 01 suggests a busy restaurant, a small cafe and one non-food
  place (clinic, salon, gym) to prove "works for any business". Places I know
  are best, because I can judge whether the AI's findings are right.
- **Options:** restaurant + cafe + non-food (spec) · three food places ·
  add a 4th non-food place.
- **Decision:** three food places in Bengaluru:
  Meghana Foods, Residency Road (22,689 reviews: the busy one, biryani-heavy,
  good for dish tagging); Café Coffee Day, Sampige Rd, Malleshwaram (926);
  Sanshu's Coffee Co., RMV 2nd Stage (149: the small one).
- **Trade-off:** focus on restaurants and cafes, where I can judge quality;
  but "works for any place" is untested. Either soften that PRD claim or add a
  non-food place before the demo.
- **Result:** Café Coffee Day gets very few new reviews (8 in the last 6
  months; its newest 500 go back to 2020). Nearly every month will be "low
  confidence". Useful to show the dashboard staying honest, but a weak demo.
  Sanshu's gets 3–19 a month, Meghana 60–109.

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

## D10: Which Apify scraper (Day 1, 2026-11-25)
- **Context:** Spec 01 asks to compare two Google Maps reviews actors on price,
  exact dates and reliability. Tested both on 5 reviews of Sanshu's.
- **Options:** `compass/Google-Maps-Reviews-Scraper` (72k users, $0.0006 per
  review on the free plan) · `kaix/google-maps-reviews-scraper` (2.7k users,
  $0.00004 per review, 15x cheaper).
- **Decision:** Compass. Both give exact dates, review IDs and owner replies,
  but Compass accepts short share links (maps.app.goo.gl) and Maps search URLs
  (so "name, city" works), and returns place details (category, total reviews).
  Kaix rejected short links.
- **Trade-off:** ~$0.30 per 500 reviews vs ~$0.02. Fine for 3 places within
  Apify's $5/month free credit, and the cache means each place is paid once.
  At scale, Kaix (plus our own short-link expansion) would be worth re-testing.
- **Result:** 3 places, 1,149 reviews, $0.61 total, 20–85 s per place
  (spec target < 2 min).

## D11: Storage = SQLite; newest 500 reviews per place (Day 1, 2026-11-25)
- **Context:** CLAUDE.md allows DuckDB or SQLite. Spec 01 suggests newest 500,
  last 12 months; the trend chart shows 12 months.
- **Options:** SQLite (built into Python) · DuckDB (faster analytics, extra
  package). Cap: newest 500 · last 12 months up to 1,000 or 3,000.
- **Decision:** SQLite in `data/review_radar.db` (gitignored: it holds review
  text). Newest 500 per place, no date filter.
- **Trade-off:** no new dependency and plenty fast for thousands of rows. 500
  is cheap and quick to tag, but for Meghana it covers only Jun–Nov 2026
  (~6 months), so its 12-month trend chart will be half empty. Can raise the
  cap just for busy places later (`--max`).
- **Privacy detail:** the scraper's reviewer name, ID, profile link and photo
  are removed in memory before anything is written to disk. Only a salted hash
  of the reviewer ID is kept (to spot repeat reviewers); the salt lives in the
  gitignored cache folder, so the hash can't be reversed by hashing known IDs.
- **Result:** only 36–62% of reviews have text (Meghana: 181 of 500). The
  aspect analysis (Day 2) will work on far fewer reviews than the star counts
  suggest, so "bad reviews this month" numbers will be small. Keep counts
  visible on the dashboard.

## D12: The aspect list (Day 2, 2026-11-25)
- **Context:** Spec 02 asks for 8–12 aspects. Drafted from 60 real reviews of
  the 3 places rather than a generic list.
- **Options:** the spec's 12 examples · a list drawn from our own reviews.
- **Decision:** 11 aspects in `src/aspects.py`: food taste, food quality &
  safety, portion & value, wait time, staff behaviour, order accuracy,
  cleanliness, ambience & comfort, location & parking, billing & policies, and
  a new **hype vs reality** ("overhyped", "not as good as Instagram"), which
  comes up again and again for Meghana and is a different fix from bad taste.
  Delivery left out (few mentions); no non-food list (D2). Vague praise ("nice
  place") gets no aspect rather than a guess.
- **Trade-off:** fits these places well but is food-specific; a clinic or
  salon would need its own list. Tags whose quote isn't word-for-word in the
  review are dropped, so we lose a few real tags to keep zero made-up ones.
- **Result:** 470/470 reviews tagged, 0 parse failures, 98.5–99.7% of quotes
  found (the rest dropped), $0 on the free tier, ~1.5–2.5 min per place.
  Top problems: Meghana wait time (17 neg) and hype (12 neg); Café Coffee Day
  staff behaviour (20 neg) and billing & policies (14 neg); Sanshu's portion &
  value (11 neg).
