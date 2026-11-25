"""The local database: one SQLite file at data/review_radar.db.

SQLite is built into Python, so it needs no extra package (see D11).
Tables:
  places   one row per Google Maps place
  reviews  one row per review (reviewer stored only as a hash, never a name)
"""

import sqlite3
from pathlib import Path

from src.config import DATA_DIR

DB_PATH = DATA_DIR / "review_radar.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS places (
    place_id        TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    category        TEXT,
    address         TEXT,
    city            TEXT,
    total_score     REAL,      -- Google's overall star rating
    reviews_count   INTEGER,   -- total reviews on Google (not just the ones we pulled)
    maps_url        TEXT,
    source_input    TEXT,      -- the link or "name, city" the user typed
    fetched_at      TEXT
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id       TEXT PRIMARY KEY,
    place_id        TEXT NOT NULL REFERENCES places(place_id),
    stars           INTEGER,
    text            TEXT,      -- original wording, may be empty (stars-only review)
    text_translated TEXT,      -- Google's English translation, if the review isn't English
    language        TEXT,
    published_at    TEXT,      -- exact ISO date-time from Google
    owner_reply     TEXT,
    owner_reply_at  TEXT,
    reviewer_hash   TEXT,      -- scrambled reviewer ID; the real name is never stored
    likes           INTEGER,
    has_text        INTEGER    -- 1 if there's text to analyse, 0 if stars only
);

CREATE INDEX IF NOT EXISTS idx_reviews_place_date ON reviews(place_id, published_at);

-- Spec 02: what each review is about. One row per (review, aspect) mention.
CREATE TABLE IF NOT EXISTS aspects (
    review_id   TEXT NOT NULL REFERENCES reviews(review_id),
    aspect      TEXT NOT NULL,   -- a key from src/aspects.py
    sentiment   TEXT NOT NULL,   -- pos / neg / neutral
    quote       TEXT NOT NULL    -- exact phrase from the review (checked in code)
);
CREATE INDEX IF NOT EXISTS idx_aspects_review ON aspects(review_id);

-- Which reviews have been tagged (some have no aspects, e.g. "ok ok").
CREATE TABLE IF NOT EXISTS tagged_reviews (
    review_id   TEXT PRIMARY KEY REFERENCES reviews(review_id),
    model       TEXT,
    tagged_at   TEXT
);

-- Dishes named in reviews (D9). `dish` is the merged name, set per place.
CREATE TABLE IF NOT EXISTS dish_mentions (
    review_id   TEXT NOT NULL REFERENCES reviews(review_id),
    dish_raw    TEXT NOT NULL,   -- as written: "chkn biriyani"
    dish        TEXT,            -- merged: "Chicken biryani"
    sentiment   TEXT NOT NULL,
    aspect      TEXT,
    quote       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dish_review ON dish_mentions(review_id);

-- The spelling-merge mapping per place; edit by hand to fix a merge.
CREATE TABLE IF NOT EXISTS dishes (
    place_id    TEXT NOT NULL,
    dish        TEXT NOT NULL,
    variants    TEXT NOT NULL,   -- JSON list of dish_raw spellings
    PRIMARY KEY (place_id, dish)
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_place(conn: sqlite3.Connection, place: dict) -> None:
    cols = ", ".join(place)
    marks = ", ".join("?" for _ in place)
    conn.execute(f"INSERT OR REPLACE INTO places ({cols}) VALUES ({marks})", list(place.values()))


def save_reviews(conn: sqlite3.Connection, reviews: list[dict]) -> None:
    if not reviews:
        return
    cols = list(reviews[0])
    sql = (f"INSERT OR REPLACE INTO reviews ({', '.join(cols)}) "
           f"VALUES ({', '.join('?' for _ in cols)})")
    conn.executemany(sql, [[r[c] for c in cols] for r in reviews])
