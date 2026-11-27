"""Analyst tools on a hand-made database (no Gemini calls)."""

from datetime import date

import pytest

from src import db, tools

AS_OF = date(2026, 11, 25)


def add(conn, rid, when, stars, neg=(), text="x"):
    conn.execute("INSERT INTO reviews (review_id, place_id, stars, text, published_at, has_text) "
                 "VALUES (?, 'P', ?, ?, ?, 1)", (rid, stars, text, when))
    for a in neg:
        conn.execute("INSERT INTO aspects VALUES (?, ?, 'neg', 'slow')", (rid, a))


@pytest.fixture
def ctx(tmp_path):
    c = db.connect(tmp_path / "t.db")
    c.execute("INSERT INTO places (place_id, name) VALUES ('P', 'Test Cafe')")
    c.execute("INSERT INTO places (place_id, name) VALUES ('Q', 'Other')")
    # 2026-11-21 is a Saturday, 2026-11-18 a Wednesday (times are UTC morning = IST day)
    add(c, "sat1", "2026-11-21T06:00:00Z", 1, ["wait_time"], "Hello, this is KRISHNA. Waited 40 min")
    add(c, "sat2", "2026-11-21T07:00:00Z", 2, ["wait_time"])
    add(c, "wed1", "2026-11-18T06:00:00Z", 5)
    add(c, "oct1", "2026-10-10T06:00:00Z", 4)
    c.execute("INSERT INTO reviews (review_id, place_id, stars, published_at, has_text) "
              "VALUES ('other', 'Q', 1, '2026-11-20T06:00:00Z', 0)")
    c.commit()
    return tools.ToolContext(c, "P", "Test Cafe", AS_OF)


def test_parse_period():
    s, e, label = tools.parse_period("2026-10", AS_OF)
    assert (s, e) == (date(2026, 10, 1), date(2026, 11, 1)) and label == "October 2026"
    s, e, _ = tools.parse_period("2026-11-01..2026-11-07", AS_OF)
    assert e == date(2026, 11, 8)
    with pytest.raises(ValueError):
        tools.parse_period("last week", AS_OF)


def test_get_metrics_with_weekend_and_aspect(ctx):
    m = tools.get_metrics(ctx, "last_30_days")
    assert m["reviews"] == 3 and m["avg_stars"] == 2.67 and m["bad_reviews_1_to_3_stars"] == 2
    assert m["low_confidence"]
    w = tools.get_metrics(ctx, "last_30_days", "wait_time", "weekend")
    assert w["reviews"] == 2 and w["complaints"] == 2 and "posted" in w["note"]
    assert tools.get_metrics(ctx, "last_30_days", days="weekday")["reviews"] == 1


def test_compare_says_too_few_to_tell(ctx):
    c = tools.compare_periods(ctx, "2026-11", "2026-10")
    assert c["avg_stars_change_a_minus_b"] == round(8 / 3 - 4, 2)
    assert c["hint"].startswith("too few reviews to tell")


def test_reviews_by_aspect_use_refs_and_hide_names(ctx):
    r = tools.get_reviews_by_aspect(ctx, "wait_time", "neg", "last_30_days")
    assert r["total_matching"] == 2
    assert {x["ref"] for x in r["reviews"]} == {"R1", "R2"}
    assert all("KRISHNA" not in x["customer_text"] for x in r["reviews"])
    assert ctx.refs["R1"] in ("sat1", "sat2")


def test_save_reply_never_saves(ctx, tmp_path):
    ctx.ref("sat1")
    out = tools.save_reply(ctx, "R1", "Sorry! Your next meal is free.")
    assert out["status"] == "waiting_for_owner_approval"
    assert ctx.pending_saves[0]["review_id"] == "sat1"
    assert any("promise" in f for f in ctx.pending_saves[0]["flags"])


def test_tools_refuse_other_places_reviews(ctx):
    assert tools.run_tool(ctx, "draft_reply", {"review": "other"})["error"].startswith("no review")
    assert "error" in tools.run_tool(ctx, "get_metrics", {"period": "yesterday"})
    assert "error" in tools.run_tool(ctx, "launch_rockets", {})


def test_check_reply_flags():
    assert tools.check_reply("Thanks for visiting, we'll share this with the team.") == []
    assert tools.check_reply("Call us on 98450 12345")
    assert tools.check_reply("That's not true, we were not busy")
