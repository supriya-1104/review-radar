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

## Acceptance criteria
- [ ] `python -m src.tag --place <id>` tags all reviews
- [ ] < 2% parse failures; 100% of quotes found in their review
- [ ] Prints aspect counts and cost
- [ ] Hand-check 20 reviews; note accuracy in `BUILD_LOG.md`
