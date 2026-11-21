# Review Radar

Paste any Google Maps place (restaurant, cafe, hotel, clinic, store). Review Radar
pulls its reviews and builds a dashboard showing what bad reviews are about,
whether this month got better or worse, and exactly where the business should
focus, with an AI analyst you can question and that drafts replies to reviews.

I am a product manager learning to build. Explain your reasoning in plain
language before writing code, and explain what you built afterwards.

## How we work
- Each feature has a spec in `docs/specs/`. Read the spec before starting.
- For any change touching more than one file: plan first, wait for my approval.
- Work in small steps. After each working step, tell me what to test, then commit
  with a clear message.
- If you are unsure about a product decision, ask me. Don't guess.
- Log notable decisions in `docs/DECISIONS.md` (context, options, choice, trade-off).

## Tech
- Python 3.11+, virtual env in `.venv/`.
- Reviews come from the Apify Google Maps Reviews scraper via the `apify-client`
  package (`APIFY_TOKEN` in `.env`). The official Google Places API returns only
  5 reviews per place, so it is not used for reviews.
- Google Gemini via the `google-genai` SDK for all LLM work (see D4 in
  `docs/DECISIONS.md`). Model names come from `.env`
  (`MODEL_FAST`, `MODEL_SMART`); check the Gemini docs if a model ID fails.
- Local storage: one DuckDB or SQLite file in `data/` (places, reviews, aspects).
- Streamlit + Plotly for the dashboard.
- Arize Phoenix (local) for tracing LLM calls.
- No agent framework: write the tool-use loop directly so every step is visible.
- Keep dependencies minimal and pinned in `requirements.txt`.

## Rules
- Never hardcode or print API keys or tokens. Read them from `.env`.
- Store reviewer names only as a hash; never display them.
- Never commit raw scraped data. `data/raw/` and `data/cache/` are gitignored.
- Every insight must cite review IDs that exist. Numbers in insights must come
  from database queries, never from the model's memory.
- Show sample size next to every monthly metric; flag months with < 15 reviews
  as "low confidence".
- Posting or saving a reply to a review ALWAYS needs explicit human approval.
- Cache every LLM and scraper result so re-runs cost nothing.

## Structure
- `docs/`   PRD, specs, decisions, error analysis
- `src/`    app code (ingest, analysis, agent, app)
- `evals/`  golden sets, rubric, eval scripts, results
- `data/`   database (gitignored raw + cache)

## Definition of done (whole project)
- Paste a Maps link in the app and get a full dashboard in under 3 minutes
- `python -m evals.run_all` writes a dated report to `evals/results/`
- README shows the demo, architecture, and eval results
