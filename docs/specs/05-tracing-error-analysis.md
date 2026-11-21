# Spec 05: Tracing + error analysis

## Goal
See exactly what the AI does, find where it fails, count the failures. This is
the skill AI PM job descriptions ask for most.

## Requirements
- Add Arize Phoenix (local, free) with OpenInference instrumentation for the
  Anthropic SDK so every LLM call and tool call is traced.
- Write 30 realistic owner questions in `evals/questions.jsonl`, spread across
  your 3 places. Mix simple, multi-step, vague, and 5 with no good answer.
- Run all 30.

## Your job (not Claude's): read every trace
For each run, one line in `docs/error-analysis.md`: pass/fail and what went
wrong in your words. Then group failures into 4–6 categories, e.g.:
- wrong aspect assigned (e.g. "cold food" tagged as ambience)
- missed Hinglish or sarcasm
- insight not supported by cited reviews
- number in answer doesn't match the database
- generic advice ("improve service") instead of specific
- overconfident on a low-data month

## Acceptance criteria
- [ ] Traces visible in Phoenix
- [ ] 30 rows + failure category table with counts
- [ ] Top 2 failure modes chosen as Day 7 fix targets
