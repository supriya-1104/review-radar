"""Metric tests on a small hand-made database, so every number is checkable by hand."""

from datetime import date, timedelta

import pytest

from src import db, metrics

AS_OF = date(2026, 11, 25)


def add(conn, rid, days_ago, stars, neg=(), pos=(), text=True):
    when = (AS_OF - timedelta(days=days_ago)).isoformat() + "T12:00:00.000Z"
    conn.execute("INSERT INTO reviews (review_id, place_id, stars, text, published_at, has_text) "
                 "VALUES (?, 'P', ?, ?, ?, ?)", (rid, stars, "x" if text else None, when, int(text)))
    for a in neg:
        conn.execute("INSERT INTO aspects VALUES (?, ?, 'neg', 'q')", (rid, a))
    for a in pos:
        conn.execute("INSERT INTO aspects VALUES (?, ?, 'pos', 'q')", (rid, a))


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "m.db")
    c.execute("INSERT INTO places (place_id, name, total_score, reviews_count) VALUES ('P', 'Test', 4.2, 999)")
    # Last 30 days: 6 reviews, avg (5+5+4+2+1+3)/6 = 3.33, 3 bad (1–3★)
    add(c, "a1", 1, 5, pos=["food_taste"])
    add(c, "a2", 2, 5, pos=["food_taste", "staff"])
    add(c, "a3", 3, 4, neg=["wait_time"], pos=["food_taste"])
    add(c, "a4", 5, 2, neg=["wait_time", "staff"])
    add(c, "a5", 8, 1, neg=["wait_time"])
    add(c, "a6", 10, 3, neg=["portion_value"])
    # Previous 30 days: 2 reviews, avg 4.5
    add(c, "b1", 35, 5)
    add(c, "b2", 40, 4, neg=["staff"])
    # Baseline 90 days before the window (days 30–119): b1, b2 + 2 more
    add(c, "c1", 80, 5)
    add(c, "c2", 110, 2, neg=["wait_time"])
    c.commit()
    return c


def test_summary_numbers(conn):
    s = metrics.summary(conn, "P", AS_OF)
    assert s.last["n"] == 6 and s.last["avg"] == 3.33 and s.last["bad"] == 3
    assert s.prev["n"] == 2 and s.prev["avg"] == 4.5
    assert s.change == pytest.approx(-1.17)
    assert s.bad_share == 0.5
    assert s.normal_n == 4 and s.normal_bad_share == 0.25   # 1 bad of 4 (c2)


def test_window_widens_when_few_complaints(conn):
    w = metrics.choose_window(conn, "P", AS_OF)
    # only 5 complaints in 30 days (< 10), 7 in 90 days, 7 in 12 months -> falls back to 12 months
    assert w.days == 365 and w.widened and "fewer than 10" in w.reason


def test_window_stays_30_days_when_enough(conn, monkeypatch):
    monkeypatch.setattr(metrics, "MIN_COMPLAINTS", 5)
    w = metrics.choose_window(conn, "P", AS_OF)
    assert w.days == 30 and not w.widened
    # window starts 29 days ago (today included); data starts 110 days ago: 81 days of baseline
    assert w.baseline_start == AS_OF - timedelta(days=110)
    assert w.baseline_periods == pytest.approx(81 / 30)


def test_complaints_and_normal_month(conn, monkeypatch):
    monkeypatch.setattr(metrics, "MIN_COMPLAINTS", 5)
    w = metrics.choose_window(conn, "P", AS_OF)
    c = {x["aspect"]: x for x in metrics.complaints(conn, "P", w)}
    assert c["wait_time"]["n"] == 3 and c["wait_time"]["n_bad_reviews"] == 2
    assert c["wait_time"]["normal"] == round(1 / (81 / 30), 1)   # 1 complaint over 81 days
    assert c["staff"]["n"] == 1


def test_priorities_formula_a_and_b(conn, monkeypatch):
    monkeypatch.setattr(metrics, "MIN_COMPLAINTS", 5)
    w = metrics.choose_window(conn, "P", AS_OF)
    a = metrics.priorities(conn, "P", w, "A")
    assert [p.aspect for p in a] == ["wait_time"]          # only aspect with >= 2 complaints
    p = a[0]
    assert p.share == 3 / 4                                  # 3 of 4 complaining reviews
    assert p.drag == round(3.33 - (4 + 2 + 1) / 3, 2)
    # stars lost: a3 (5-4)/1 + a4 (5-2)/2 + a5 (5-1)/1 = 1 + 1.5 + 4
    assert p.stars_lost == 6.5
    assert p.evidence[0]["review_id"] == "a5"               # worst review first


def test_strengths_count_good_reviews_with_text(conn):
    w = metrics.choose_window(conn, "P", AS_OF)
    s = metrics.strengths(conn, "P", w)
    assert s["good_with_text"] == 6                         # a1 a2 a3 b1 b2 c1 (12-month window)
    assert s["items"][0]["aspect"] == "food_taste" and s["items"][0]["n"] == 3


def test_monthly_trend_flags_low_confidence(conn):
    t = metrics.monthly_trend(conn, "P", AS_OF)
    assert len(t) == 12 and t[-1]["month"] == "2026-11" and t[-1]["partial"]
    assert all(m["low_confidence"] for m in t)              # every month < 15 reviews
    assert t[-1]["label"] == "Nov"


def test_fmt_range():
    assert metrics.fmt_range(date(2026, 10, 27), date(2026, 11, 26)) == "27 Oct – 25 Nov"
    assert metrics.fmt_range(date(2025, 12, 1), date(2026, 1, 2)) == "1 Dec 2025 – 1 Jan 2026"
