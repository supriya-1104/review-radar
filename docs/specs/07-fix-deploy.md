# Spec 07: Fix, polish, deploy

## Fix
- Take the top 2 failure modes from `docs/error-analysis.md`.
- For each: hypothesis → ONE change (prompt, aspect definitions, retrieval, tool
  description) → rerun evals → keep only if it improves without breaking safety.
- Record before/after numbers in `docs/DECISIONS.md`.

## Polish
- Mobile-friendly layout; plain language everywhere (owners aren't analysts).
- "How this is calculated" expander under every score.
- Download a one-page monthly report (PDF or Markdown) for the owner.

## Deploy
- Streamlit Community Cloud (free) from the GitHub repo; keys in app secrets.
- Protect your money: Anthropic Console spend limit, Apify spend limit,
  max 1 new place per visitor session, and **Demo mode** with your 3
  pre-analysed places so most visitors cost nothing.

## Validate with real users
- Show it to 3 real business owners or managers (a local cafe, a friend's
  family business). Ask: "What would you do differently after seeing this?"
  Write their answers in `docs/user-feedback.md`. This is gold in interviews.

## Acceptance criteria
- [ ] Before/after eval table for both fixes
- [ ] Public link works on mobile; demo mode works with no keys used
- [ ] Feedback from 3 owners recorded
