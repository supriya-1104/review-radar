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
- **Decision:** plain Anthropic SDK tool loop.
- **Trade-off:** more code, but every step is visible and explainable in an
  interview. Could port to LangGraph later.
