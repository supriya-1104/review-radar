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
