# PRD: Review Radar

> Draft. Keep editing it in your own words. This document is where your PM
> thinking shows.

## 1. Problem
An independent restaurant lives on its Google rating, but the owner can't read
hundreds of reviews to spot patterns. They see the stars move and don't know
why. Was it the new chef? Slow weekend service? A price hike? They fix the
wrong thing, or nothing, and the rating keeps sliding. Problems are noticed
weeks late, and nobody knows whether a fix worked.

## 2. Target user
**Primary persona: the independent restaurant owner.**
- Runs one outlet in a metro city; 300+ Google reviews.
- Not technical; lives on their phone, checks it between services.
- Has about 10 minutes a week for this.
- Doesn't fix problems personally: acts through the kitchen and floor staff.
- Feels anxious about public reviews and has no clear way to act on them.

**Secondary (not designed for in v1):** the ops manager of a multi-outlet chain.

Why this persona: rating-sensitive, high review volume, clear causes (food,
wait, staff), and no analyst on the team. Restaurants also have enough reviews
per month for trends to mean something.

## 3. Jobs to be done
Format: **When** [situation], **I want to** [goal], **so I can** [outcome].

### Functional jobs

| # | Job | Priority |
|---|---|---|
| J1 | **When** I don't have time to read every review, **I want to** see what customers are saying in one short summary, **so I can** stay on top of my reputation in minutes a week. | v1 |
| J2 | **When** customers keep complaining, **I want to** see the most common problems ranked by impact on my rating, **so I can** spend limited time and money on the one that matters most. | v1 (core) |
| J3 | **When** I make changes to the menu, staff or prices, **I want to** know what customers love most, **so I can** protect it and not break what's working. | v1 |
| J4 | **When** my rating moves, **I want to** see whether this month is better or worse than usual and what drove the change, **so I can** react to the cause instead of guessing. | v1 |
| J5 | **When** an insight tells me to change something, **I want to** see the actual reviews behind it, **so I can** trust it enough to act. | v1 |
| J6 | **When** a specific problem is rising, **I want to** know where it happens (time of day, dish, dine-in vs delivery), **so I can** fix the root cause, not the symptom. | v1.5 |
| J7 | **When** someone leaves an angry review, **I want to** reply quickly and well, **so I can** win them back and show future customers that I care. | v1.5 |
| J8 | **When** something starts going wrong, **I want to** hear about it within days without opening a dashboard, **so I can** fix it before it shows up in my rating. | v2 |
| J9 | **When** I've made a change to fix a problem, **I want to** see whether reviews improved afterwards, **so I can** decide whether to keep it. | v2 |
| J10 | **When** I brief my team, **I want to** share specific complaints and praise (including staff named in reviews), **so I can** coach them and keep them motivated. | v2 |
| J11 | **When** my rating changes, **I want to** compare with similar places nearby, **so I can** tell whether the problem is mine or the whole market's. | v2 |

### Emotional job
**When** I think about my online reviews, **I want to** feel in control instead
of anxious, **so I can** focus on running the restaurant.
→ Design implication: calm, specific, plain-language insights; always end with
"what to do next"; never alarmist.

### What the user originally asked for (my first draft)
I started with five user stories (know what customers think, find common
problems, protect what's working, track monthly progress, get deeper insights).
Reframing them as jobs exposed what was missing: prioritizing which problem to
fix, finding the cause behind a problem, trusting the evidence, early alerts,
and checking whether a fix worked.

## 4. v1 solution (covers J1–J5, plus J6–J7 if time allows)
Paste a Google Maps link. Review Radar:
- pulls up to ~1,000 recent reviews,
- tags every review by **aspect** (one review can praise the food and slam the
  service) and sentiment,
- shows a phone-first dashboard:
  - **Summary card** (J1): the 30-second version, ending in "what to do next"
  - **Fix this first** (J2): top 3 problems ranked by impact, with quotes
  - **What's working** (J3): top 3 strengths to protect
  - **This month vs usual** (J4): rating and volume trend, biggest changes and why
  - **Evidence everywhere** (J5): every insight links to the reviews behind it
- AI analyst for follow-up questions; slices by time, dish and channel (J6)
- Reply drafts for negative reviews, saved only after approval (J7)

## 5. The "Fix this first" score (product decision)
For each aspect:
`priority = share of negative mentions × rating drag × trend`
- **share of negative mentions:** how often it comes up in 1–3 star reviews
- **rating drag:** average rating of reviews that mention it negatively vs the
  overall average
- **trend:** rising this month compared with the previous 3 months?
Document why this formula, and what it gets wrong (e.g. it ignores how costly a
fix is, which the owner knows better than we do).

## 6. Out of scope (and why)
| Not doing | Why |
|---|---|
| Getting more reviews / review requests | Different job; crowded market |
| Zomato, Swiggy, TripAdvisor reviews | Google first; prove value on one source |
| Multi-outlet chains | Different persona and needs; v3 |
| Posting replies directly to Google | Needs owner's Business Profile access; v1 drafts only |
| Live sync and user accounts | Not needed to prove the value |
| Languages beyond English and Hinglish | Scope for 2 weeks |

## 7. Success metrics
| Job | Metric | Target | How measured |
|---|---|---|---|
| J1 | Owner can state the top issue after reading the summary | 3 of 3 owners, < 30 s | usability test |
| J2 | Aspect tagging accuracy | ≥ 85% | vs 100 hand-labelled reviews |
| J2 | "Fix this first" matches a human reviewer's top 3 | ≥ 2 of 3 | I rank 3 places by hand |
| J4 | Numbers in insights match the database | 100% | code check |
| J5 | Insight groundedness | ≥ 90% | LLM judge on 30 insights, judge checked against my labels |
| J5 | Invalid citations | 0% | code check |
| J7 | Replies saved without approval | 0 (hard rule) | agent scenarios |
| All | Owners who say "I'd act on this" | 3 of 3 | owner interviews |
| All | Cost per place analysed | < $0.50 | logged |
| All | Link → dashboard | < 3 min | logged |

## 8. Validation plan
Before building past Day 3, interview 3–5 restaurant owners (see
`docs/owner-interviews.md`). Confirm or change the jobs and their priority.
After Day 7, show them the product and record what they'd do differently.

## 9. Risks and mitigations
- **Few reviews per month at small places** → show sample size; mark months with
  < 15 reviews as low confidence; offer a quarter view.
- **Hallucinated insights** → numbers from SQL only; cite IDs; judge grounding.
- **Prompt injection inside a review** → reviews are data; approval on actions;
  red-team test.
- **Privacy** → hash reviewer names; never display them.
- **Data source terms** → third-party scraper for the prototype; analysis and
  demo only, no republishing. Long-term: owners connect their Google Business
  Profile.
- **Cost of a public demo** → spend limits, per-session limits, demo mode with 3
  pre-analysed places.

## 10. Milestones
| Day | Milestone |
|---|---|
| 1 | Setup, PRD, reviews pulled for 1 place |
| 2 | Aspect + sentiment tagging; book owner interviews |
| 3 | Dashboard: J1–J5 |
| 4 | AI analyst + reply drafts with approval (J6–J7) |
| 5 | Tracing + error analysis |
| 6 | Eval suite + baseline |
| 7 | Fix top failures, polish, deploy |
| 8 | README, demo video, show to owners |
