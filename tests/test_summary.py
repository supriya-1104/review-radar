"""The summary's grounding checks, on fake AI answers (no Gemini calls)."""

from src import summary

FACTS = "Last 30 days: 88 reviews, average 4.1 stars.\nSlow service: 5 complaints, cost 9.8 stars."
EVIDENCE = {"E1": {"review_id": "real-1"}, "E2": {"review_id": "real-2"}}


def test_grounded_answer_passes():
    ok = {"headline": "4.1 stars from 88 reviews; slow service had 5 complaints.",
          "do_next": "Add a second order-taker on weekends.", "cited": ["E1"]}
    assert summary.check(ok, FACTS, EVIDENCE) is None


def test_made_up_number_fails():
    bad = {"headline": "Slow service is up 40% this month.", "do_next": "Hire staff.", "cited": ["E1"]}
    assert "40" in summary.check(bad, FACTS, EVIDENCE)


def test_widened_period_must_be_named():
    ans = {"headline": "4.1 stars from 88 reviews; slow service had 5 complaints.",
           "do_next": "Add staff.", "cited": ["E1"]}
    facts = FACTS + "\nBiggest problem (last 12 months): slow service."
    assert "12 months" in summary.check(ans, facts, EVIDENCE, period="12 months")
    ans["headline"] = "4.1 stars from 88 reviews; 5 complaints over the last 12 months."
    assert summary.check(ans, facts, EVIDENCE, period="12 months") is None


def test_unknown_or_missing_citation_fails():
    assert summary.check({"headline": "ok", "do_next": "x", "cited": ["E9"]}, FACTS, EVIDENCE)
    assert summary.check({"headline": "ok", "do_next": "x", "cited": []}, FACTS, EVIDENCE)
    assert summary.check(None, FACTS, EVIDENCE) == "no answer"
