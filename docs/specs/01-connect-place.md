# Spec 01: Connect a place and pull its reviews

## Goal
Paste a Google Maps link (or "name, city") and get that place's reviews into the
local database.

## Product decisions (yours)
- Pick 3 places to build with. Good mix: one busy restaurant (1,000+ reviews),
  one small cafe (~200 reviews), one non-food place (clinic, salon, gym).
  Record why in `docs/DECISIONS.md`.
- How many reviews to pull by default? (Suggest: newest 500, last 12 months.)

## Requirements
- Create a free Apify account; put `APIFY_TOKEN` in `.env`.
- Use `apify-client` to run a Google Maps reviews actor from the Apify Store
  (pick one with exact review dates, good ratings and pay-per-result pricing;
  compare 2 and record the choice).
- Input: Maps URL or "name, city". Sort by newest. Cap at the default above.
- Save the place: name, category, address, overall rating, total review count.
- Save each review: review_id, rating, text, date (exact), owner_reply (if any),
  reviewer name **hashed**.
- Skip reviews with no text for text analysis, but keep them for rating trends.
- Cache the raw response in `data/cache/` so re-runs cost nothing.

## Acceptance criteria
- [ ] `python -m src.ingest "<maps link>"` loads a place in < 2 minutes
- [ ] Re-running uses the cache (no new Apify charge)
- [ ] No plain reviewer names in the database
- [ ] Printed summary: reviews loaded, date range, rating distribution, Apify cost
