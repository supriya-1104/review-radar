# Spec 02: Aspect + sentiment tagging

## Goal
Know WHAT each review is about, not just how many stars it has.

## Key idea: aspects, not one label per review
"Food was amazing but we waited 45 minutes and the waiter was rude" is one
review with three aspects: food (positive), wait time (negative), staff
(negative). Tagging the whole review as "negative" would hide the real story.

## Product decision (yours)
Read 50 reviews across your 3 places and define 8–12 aspects with one-line
definitions in `src/aspects.py`. Example for restaurants: food taste, food
quality/hygiene, portion/value for money, price, wait time, staff behaviour,
order accuracy, cleanliness, ambience/noise, parking/location, delivery,
billing/payment. Decide how non-restaurant places map (e.g. a generic set plus
category-specific ones).

## Requirements
- `MODEL_FAST`, batches of ~20 reviews per call, structured JSON output:
  `review_id`, list of `{aspect, sentiment (pos/neg/neutral), quote}` where
  `quote` is the exact phrase from the review that supports the tag.
- Handle Hinglish and short reviews ("worst service", "ok ok").
- Validate JSON; retry once; log failures. Cache results.
- Code check: every `quote` must actually appear in the review text.
- Store in an `aspects` table.

## Dish tagging (added 2026-11-22, see D9)
Goal: know WHICH dishes people praise or complain about ("biryani was cold",
"naan missing"), using only what the review text says. No bills, no customer
data.

- **Same LLM call, no extra cost per review:** each review's JSON also gets a
  list of `{dish_raw, sentiment (pos/neg/neutral), aspect, quote}`.
  - `dish_raw`: the dish exactly as written ("chkn biriyani", "paneer tikka").
  - `aspect`: which aspect the dish comment is about (e.g. "biryani was cold" →
    food quality/hygiene, negative; "biryani was small for ₹400" → portion/value).
  - `quote`: exact phrase from the review (same code check as aspects).
  - Only named dishes or drinks. Generic words ("food", "starters", "meal")
    are NOT dishes. Include Hinglish/Indian dish names (dal makhani, chole).
- **Normalise names per place:** after tagging, one `MODEL_FAST` call per place
  groups spelling variants into canonical dishes ("biriyani", "chicken biryani",
  "chkn biryani" → "Chicken biryani"). Store the mapping so it can be fixed by
  hand. If the owner later provides a menu, match to menu items instead.
- **Storage:** `dish_mentions` table (`review_id`, `dish_raw`, `dish`,
  `sentiment`, `aspect`, `quote`) plus `dishes` (`place_id`, `dish`, variants).
- **Show only dishes with ≥ 3 mentions** on the dashboard, always as counts
  ("praised in 14 reviews, criticised in 3"). Where dishes appear on the
  dashboard is a separate product decision (to decide on Day 3; likely inside
  Fix first evidence, What's working, and a filter in All reviews).
- **Privacy:** dish tagging uses review text only. Never link a review to a
  bill, order or customer record (D9).

## Acceptance criteria
- [ ] `python -m src.tag --place <id>` tags all reviews
- [ ] < 2% parse failures; 100% of quotes found in their review
- [ ] Prints aspect counts and cost
- [ ] Hand-check 20 reviews; note accuracy in `BUILD_LOG.md`
- [ ] Prints top 10 dishes per place with praised / criticised counts
- [ ] Hand-check 20 dish mentions: right dish, right sentiment, no generic
      words tagged as dishes; spelling variants merged correctly
