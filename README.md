# Review Radar

**Paste any Google Maps place. See what bad reviews are really about, whether
this month got better or worse, and what to fix first, with evidence.**

Built by <Your Name>, product manager, as a hands-on project in LLM agents,
aspect-based analysis and evals. Built with Claude Code.

[Live demo](#) · [2-min video](#) · [PRD](docs/PRD.md) · [Decision log](docs/DECISIONS.md) · [What owners said](docs/user-feedback.md)

<!-- Add a GIF of: paste link → dashboard → "Fix this first" → ask a question -->

## The problem
A local business lives on its Google rating, but owners can't read hundreds of
reviews. They see the stars drop and don't know why, so they fix the wrong thing.

## What it does
- **Connect any place** with a Google Maps link
- **Tags every review by aspect** (food, wait time, staff, price, cleanliness...),
  because one review can praise the food and slam the service
- **Monthly trend:** did we get better or worse, and why
- **Fix this first:** aspects ranked by how often they drive bad reviews, how
  much they pull the rating down, and whether they're rising
- **AI analyst:** ask questions in plain words; every answer cites real reviews
- **Reply drafts** for angry reviews, saved only after the owner approves

## Results
<!-- Paste from evals/results/<latest>.md -->
| Metric | Baseline | After fixes | Target |
|---|---|---|---|
| Aspect tagging accuracy | | | ≥ 85% |
| Insight groundedness (LLM judge) | | | ≥ 90% |
| Judge agreement with my labels | | | ≥ 80% |
| Numbers matching the database | | | 100% |
| Replies saved without approval | | | 0 |
| Cost per place analysed | | | < $0.50 |
| Link → dashboard time | | | < 3 min |

## How I evaluated it
1. Hand-labelled 100 reviews for aspect tagging.
2. Wrote 30 realistic owner questions, read every trace, built a failure
   taxonomy ([error analysis](docs/error-analysis.md)).
3. Built an LLM judge from a written [rubric](evals/rubric.md) and checked it
   against my labels before trusting it.
4. Fixed the top two failure modes and measured before/after.
5. Red-teamed it with a prompt-injection review.
6. Showed it to 3 real business owners.

## Key product decisions
<!-- 3 one-liners linking to DECISIONS.md, e.g. why aspects not star ratings,
why the "Fix this first" formula, why the data source -->

## Architecture
<!-- Ask Claude Code for a Mermaid diagram -->
Maps link → Apify reviews actor → database → aspect tagging (Claude) → metrics
(SQL) → dashboard (Streamlit) + analyst agent (Claude tool use, approval gate).
Traced with Arize Phoenix.

## What I'd do next
<!-- e.g. owners connect their Google Business Profile, weekly WhatsApp digest,
multi-outlet comparison for chains -->

## Run it locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add Anthropic key + Apify token
streamlit run src/app.py
python -m evals.run_all
```
