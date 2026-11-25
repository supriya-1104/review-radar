"""Every number on the dashboard comes from a function here (spec 03).

Only SQL over the local database: no LLM, no made-up numbers. All functions
take `as_of` (a date) so tests can freeze time.

Time windows (D6, D13):
- "Last 30 days" = the 30 days up to as_of; "previous 30 days" = the 30 before.
- "A normal month" = average per 30 days over the 90 days before the window.
- Complaint sections use the last 30 days if they hold >= MIN_COMPLAINTS
  complaints, else widen to 90 days, else 12 months, and say so.
- A complaint = any negative aspect tag, in any review (D13).
"""

import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from src.aspects import PRAISE_LABELS, PROBLEM_LABELS

MIN_COMPLAINTS = 10   # below this, widen the window
LOW_CONFIDENCE = 15   # months with fewer reviews are "low confidence" (CLAUDE.md)
MIN_FIX_MENTIONS = 2  # an aspect needs >= 2 complaints to be ranked in Fix first
WINDOWS = [(30, "Last 30 days"), (90, "Last 90 days"), (365, "Last 12 months")]


def today() -> date:
    return datetime.now(timezone.utc).date()


def _ts(d: date) -> str:
    """Date -> ISO string comparable with published_at ('2026-11-22T15:48:45Z')."""
    return d.isoformat() + "T00:00:00"


def _between(start: date, end: date) -> tuple[str, str]:
    """Half-open [start, end) in timestamp form; end is exclusive."""
    return _ts(start), _ts(end)


def fmt_range(start: date, end_exclusive: date) -> str:
    """'24 Oct – 22 Nov' (end shown inclusive)."""
    last = end_exclusive - timedelta(days=1)
    if start.year != last.year:
        return f"{start.day} {start:%b %Y} – {last.day} {last:%b %Y}"
    return f"{start.day} {start:%b} – {last.day} {last:%b}"


# ---------- header + summary ----------

def place_header(conn: sqlite3.Connection, place_id: str) -> dict:
    r = conn.execute("SELECT name, category, total_score, reviews_count, address "
                     "FROM places WHERE place_id = ?", (place_id,)).fetchone()
    return dict(r) if r else {}


def _rating_stats(conn, place_id, start: date, end: date) -> dict:
    lo, hi = _between(start, end)
    n, avg, bad = conn.execute(
        "SELECT COUNT(*), AVG(stars), SUM(stars <= 3) FROM reviews "
        "WHERE place_id = ? AND published_at >= ? AND published_at < ?",
        (place_id, lo, hi)).fetchone()
    return {"n": n, "avg": round(avg, 2) if avg is not None else None, "bad": bad or 0,
            "start": start, "end": end}


@dataclass
class Summary:
    last: dict            # last 30 days: n, avg, bad, start, end
    prev: dict            # previous 30 days
    normal_bad_share: float | None   # bad share over the 90 days before (a normal month)
    normal_n: int                    # reviews behind that normal share

    @property
    def bad_share(self) -> float | None:
        return self.last["bad"] / self.last["n"] if self.last["n"] else None

    @property
    def change(self) -> float | None:
        if self.last["avg"] is None or self.prev["avg"] is None:
            return None
        return round(self.last["avg"] - self.prev["avg"], 2)


def summary(conn, place_id: str, as_of: date | None = None) -> Summary:
    end = (as_of or today()) + timedelta(days=1)  # include as_of itself
    last = _rating_stats(conn, place_id, end - timedelta(days=30), end)
    prev = _rating_stats(conn, place_id, end - timedelta(days=60), end - timedelta(days=30))
    base = _rating_stats(conn, place_id, end - timedelta(days=120), end - timedelta(days=30))
    share = base["bad"] / base["n"] if base["n"] else None
    return Summary(last, prev, share, base["n"])


# ---------- monthly trend ----------

def monthly_trend(conn, place_id: str, as_of: date | None = None, months: int = 12) -> list[dict]:
    """Average rating per calendar month for the last `months` months."""
    as_of = as_of or today()
    first = date(as_of.year, as_of.month, 1)
    for _ in range(months - 1):
        first = (first - timedelta(days=1)).replace(day=1)
    rows = conn.execute(
        "SELECT substr(published_at, 1, 7) m, COUNT(*), AVG(stars) FROM reviews "
        "WHERE place_id = ? AND published_at >= ? GROUP BY 1", (place_id, _ts(first))).fetchall()
    by_month = {m: (n, a) for m, n, a in rows}
    out, d = [], first
    while d <= as_of:
        key = f"{d.year}-{d.month:02d}"
        n, a = by_month.get(key, (0, None))
        out.append({
            "month": key, "label": d.strftime("%b"), "year": d.year,
            "n": n, "avg": round(a, 2) if a is not None else None,
            "low_confidence": n < LOW_CONFIDENCE,
            "partial": d.year == as_of.year and d.month == as_of.month,
            "through_day": as_of.day if (d.year, d.month) == (as_of.year, as_of.month) else None,
        })
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


# ---------- complaint window ----------

@dataclass
class Window:
    days: int
    label: str
    start: date
    end: date                       # exclusive
    widened: bool                   # True if 30 days had too few complaints
    baseline_start: date | None     # None = not enough history for "a normal month"
    baseline_periods: float = 0.0   # how many window-lengths the baseline covers
    reason: str = ""

    @property
    def range_text(self) -> str:
        return fmt_range(self.start, self.end)

    @property
    def baseline_text(self) -> str:
        if not self.baseline_start:
            return ""
        return fmt_range(self.baseline_start, self.start)


def _complaint_count(conn, place_id, start: date, end: date) -> int:
    lo, hi = _between(start, end)
    return conn.execute(
        "SELECT COUNT(*) FROM aspects a JOIN reviews r USING (review_id) "
        "WHERE r.place_id = ? AND a.sentiment = 'neg' AND r.published_at >= ? AND r.published_at < ?",
        (place_id, lo, hi)).fetchone()[0]


def _data_start(conn, place_id) -> date | None:
    r = conn.execute("SELECT MIN(published_at) FROM reviews WHERE place_id = ?", (place_id,)).fetchone()[0]
    return date.fromisoformat(r[:10]) if r else None


def choose_window(conn, place_id: str, as_of: date | None = None) -> Window:
    end = (as_of or today()) + timedelta(days=1)
    chosen = None
    for days, label in WINDOWS:
        start = end - timedelta(days=days)
        if _complaint_count(conn, place_id, start, end) >= MIN_COMPLAINTS:
            chosen = (days, label, start)
            break
    if chosen is None:
        days, label = WINDOWS[-1]
        chosen = (days, label, end - timedelta(days=days))
    days, label, start = chosen
    widened = days != 30
    reason = (f"Too few recent complaints for a 30-day view (fewer than {MIN_COMPLAINTS}), "
              f"so this uses the {label.lower()}.") if widened else ""

    # "A normal month": up to 3 window-lengths before, but only where we have data.
    data_start = _data_start(conn, place_id)
    want = start - timedelta(days=3 * days)
    b_start = max(want, data_start) if data_start else None
    periods = (start - b_start).days / days if b_start and b_start < start else 0.0
    if periods < 1:  # less than one full window of history: no fair comparison
        b_start, periods = None, 0.0
    return Window(days, label, start, end, widened, b_start, periods, reason)


# ---------- complaints + praise ----------

def _aspect_rows(conn, place_id, start: date, end: date, sentiment: str):
    lo, hi = _between(start, end)
    return conn.execute(
        "SELECT a.aspect, a.review_id, a.quote, r.stars, r.published_at FROM aspects a "
        "JOIN reviews r USING (review_id) WHERE r.place_id = ? AND a.sentiment = ? "
        "AND r.published_at >= ? AND r.published_at < ?",
        (place_id, sentiment, lo, hi)).fetchall()


def complaints(conn, place_id: str, w: Window) -> list[dict]:
    """Each aspect's complaints in the window vs a normal period of the same length."""
    now = defaultdict(list)
    for a, rid, q, stars, at in _aspect_rows(conn, place_id, w.start, w.end, "neg"):
        now[a].append({"review_id": rid, "quote": q, "stars": stars, "published_at": at})
    base = defaultdict(int)
    if w.baseline_start:
        for a, *_ in _aspect_rows(conn, place_id, w.baseline_start, w.start, "neg"):
            base[a] += 1
    out = []
    for a in set(now) | set(base):
        n = len(now[a])
        normal = round(base[a] / w.baseline_periods, 1) if w.baseline_start else None
        out.append({
            "aspect": a, "label": PROBLEM_LABELS[a], "n": n,
            "n_bad_reviews": sum(1 for x in now[a] if x["stars"] <= 3),
            "normal": normal,
            "delta": round(n - normal, 1) if normal is not None else None,
            "mentions": now[a],
        })
    return sorted(out, key=lambda x: (-x["n"], x["label"]))


def complaint_review_count(conn, place_id: str, w: Window) -> int:
    """Reviews in the window with at least one complaint."""
    lo, hi = _between(w.start, w.end)
    return conn.execute(
        "SELECT COUNT(DISTINCT a.review_id) FROM aspects a JOIN reviews r USING (review_id) "
        "WHERE r.place_id = ? AND a.sentiment = 'neg' AND r.published_at >= ? AND r.published_at < ?",
        (place_id, lo, hi)).fetchone()[0]


def strengths(conn, place_id: str, w: Window, top: int = 3) -> dict:
    """What good (4–5★) reviews with text praise, in the same window."""
    lo, hi = _between(w.start, w.end)
    good = conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE place_id = ? AND stars >= 4 AND has_text = 1 "
        "AND published_at >= ? AND published_at < ?", (place_id, lo, hi)).fetchone()[0]
    by = defaultdict(list)
    for a, rid, q, stars, at in _aspect_rows(conn, place_id, w.start, w.end, "pos"):
        if stars >= 4:
            by[a].append({"review_id": rid, "quote": q, "stars": stars, "published_at": at})
    items = sorted(by.items(), key=lambda kv: -len(kv[1]))[:top]
    return {"good_with_text": good, "items": [
        {"aspect": a, "label": PRAISE_LABELS[a], "n": len(m),
         "share": len(m) / good if good else 0,
         # the longest quote is usually the most telling
         "quote": max(m, key=lambda x: len(x["quote"]))}
        for a, m in items]}


# ---------- Fix first ----------

@dataclass
class Priority:
    aspect: str
    label: str
    n: int                 # complaints in the window
    n_bad_reviews: int     # of which in 1–3★ reviews
    share: float           # n / reviews with any complaint
    drag: float            # avg rating in window minus avg rating of these reviews
    trend: float           # (n + 1) / (normal + 1), 1.0 when no baseline
    normal: float | None
    stars_lost: float      # formula B
    score_a: float = 0.0
    evidence: list = field(default_factory=list)


def priorities(conn, place_id: str, w: Window, formula: str = "B") -> list[Priority]:
    """Rank problems. A = PRD formula (share x rating drag x trend).
    B = stars lost: each complaining review's (5 - stars), split across the
    aspects it complains about."""
    comps = complaints(conn, place_id, w)
    total_reviews = complaint_review_count(conn, place_id, w) or 1
    lo, hi = _between(w.start, w.end)
    avg_all = conn.execute(
        "SELECT AVG(stars) FROM reviews WHERE place_id = ? AND published_at >= ? AND published_at < ?",
        (place_id, lo, hi)).fetchone()[0] or 0
    # how many aspects each review complains about (to split stars lost fairly)
    per_review = defaultdict(int)
    for c in comps:
        for m in c["mentions"]:
            per_review[m["review_id"]] += 1

    out = []
    for c in comps:
        if c["n"] < MIN_FIX_MENTIONS:
            continue
        stars = [m["stars"] for m in c["mentions"]]
        drag = max(avg_all - sum(stars) / len(stars), 0.1)
        trend = (c["n"] + 1) / (c["normal"] + 1) if c["normal"] is not None else 1.0
        trend = min(max(trend, 0.5), 3.0)
        lost = sum((5 - m["stars"]) / per_review[m["review_id"]] for m in c["mentions"])
        p = Priority(c["aspect"], c["label"], c["n"], c["n_bad_reviews"], c["n"] / total_reviews,
                     round(drag, 2), round(trend, 2), c["normal"], round(lost, 1))
        p.score_a = round(p.share * p.drag * p.trend, 3)
        p.evidence = sorted(c["mentions"], key=lambda m: (m["stars"], m["published_at"]))
        out.append(p)
    key = (lambda p: -p.score_a) if formula == "A" else (lambda p: -p.stars_lost)
    return sorted(out, key=key)


def review_text(conn, review_id: str) -> dict | None:
    r = conn.execute("SELECT review_id, stars, text, text_translated, published_at, owner_reply "
                     "FROM reviews WHERE review_id = ?", (review_id,)).fetchone()
    return dict(r) if r else None


def unreplied_bad(conn, place_id: str) -> int:
    """Bad reviews (1–3★) with text and no owner reply: the Replies badge."""
    return conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE place_id = ? AND stars <= 3 AND has_text = 1 "
        "AND (owner_reply IS NULL OR owner_reply = '')", (place_id,)).fetchone()[0]
