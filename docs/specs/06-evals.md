# Spec 06: Eval suite

## Goal
One command tells us how good Review Radar is, so every change can be measured.

## Four eval sets
1. **Aspect tagging:** 100 reviews you hand-label (aspects + sentiment) in
   `evals/golden_aspects.jsonl`. Metrics: precision and recall per aspect.
2. **Insight quality:** the 30 questions from Spec 05, labelled pass/fail by you
   with `evals/rubric.md`. An LLM judge scores the same answers with the same
   rubric. **Judge check:** % agreement with your labels; if < 80%, fix the
   rubric or judge prompt before trusting it.
3. **Reply drafts:** 15 real negative reviews; you and the judge rate drafts on
   empathy, specificity, no false promises, no arguing.
4. **Agent safety:** 10 scenarios incl. the prompt-injection review. Metric:
   replies saved without approval (must be 0).

## Code checks (no LLM)
- Every cited review ID exists
- Every number in an answer matches a tool result
- Every aspect quote appears in its review

## Requirements
- `python -m evals.run_all` runs all of it and writes
  `evals/results/YYYY-MM-DD.md` with a summary table and cost.
- Save the baseline; compare every later change to it.

## Acceptance criteria
- [ ] Baseline report committed
- [ ] Judge agreement reported
- [ ] README results table copied from the report
