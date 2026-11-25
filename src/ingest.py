"""Pull a place's Google reviews into the local database (spec 01).

Usage:
    python -m src.ingest "https://maps.app.goo.gl/..."
    python -m src.ingest "Meghana Foods, Bengaluru"
    python -m src.ingest "<link>" --max 500 --refresh

Steps: fetch from Apify (Compass Google Maps Reviews Scraper, see D10) ->
remove reviewer names straight away -> cache -> save to SQLite -> print summary.
Re-running the same input reads the cache, so it costs nothing.
"""

import argparse
import hashlib
import json
import secrets
import sys
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import quote_plus

from src import config, db

ACTOR = "compass/Google-Maps-Reviews-Scraper"
DEFAULT_MAX = 500  # newest 500 per place (D11)

# Fields from the scraper that identify the reviewer. Dropped before anything
# touches disk; only a salted hash of the reviewer ID is kept.
PERSONAL_FIELDS = ["name", "reviewerId", "reviewerUrl", "reviewerPhotoUrl"]

SALT_FILE = config.CACHE_DIR / "reviewer_salt.txt"  # gitignored with the cache


# ---------- input ----------

def to_start_url(query: str) -> str:
    """A Maps link is used as is; 'name, city' becomes a Maps search."""
    q = query.strip()
    if q.startswith("http://") or q.startswith("https://"):
        return q
    return "https://www.google.com/maps/search/" + quote_plus(q)


def build_run_input(query: str, max_reviews: int) -> dict:
    return {
        "startUrls": [{"url": to_start_url(query)}],
        "maxReviews": max_reviews,
        "reviewsSort": "newest",
        "reviewsOrigin": "google",
        "language": "en",
        # Needed only to get a stable reviewer ID to hash; names are removed below.
        "personalData": True,
    }


# ---------- privacy ----------

def get_salt() -> str:
    """A random secret, created once, so reviewer hashes can't be reversed by
    hashing known Google profile IDs."""
    if SALT_FILE.exists():
        return SALT_FILE.read_text().strip()
    SALT_FILE.parent.mkdir(parents=True, exist_ok=True)
    salt = secrets.token_hex(16)
    SALT_FILE.write_text(salt)
    return salt


def hash_reviewer(item: dict, salt: str) -> str | None:
    who = item.get("reviewerId") or item.get("name")
    if not who:
        return None
    return hashlib.sha256((salt + str(who)).encode()).hexdigest()[:16]


def strip_personal(item: dict, salt: str) -> dict:
    """Return a copy with the reviewer hashed and all identifying fields removed."""
    clean = {k: v for k, v in item.items() if k not in PERSONAL_FIELDS}
    clean["reviewerHash"] = hash_reviewer(item, salt)
    return clean


# ---------- fetch + cache ----------

def cache_path(query: str, max_reviews: int):
    key = hashlib.sha256(f"{query.strip()}|{max_reviews}".encode()).hexdigest()[:16]
    return config.CACHE_DIR / f"apify_reviews_{key}.json"


def fetch(query: str, max_reviews: int, refresh: bool = False) -> tuple[list[dict], float, bool]:
    """Return (cleaned items, Apify cost in USD, came_from_cache)."""
    path = cache_path(query, max_reviews)
    if path.exists() and not refresh:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["items"], 0.0, True

    from apify_client import ApifyClient  # imported here so tests don't need it

    client = ApifyClient(config.get("APIFY_TOKEN"))
    print(f"Fetching up to {max_reviews} newest reviews from Apify...")
    run = client.actor(ACTOR).call(run_input=build_run_input(query, max_reviews), logger=None)
    if run is None or run.status != "SUCCEEDED":
        raise RuntimeError(f"Apify run did not succeed (status: {getattr(run, 'status', None)})")
    raw = list(client.dataset(run.default_dataset_id).iterate_items())
    # Per-review charges are added just after the run ends, so re-read the run.
    final = client.run(run.id).get() or run
    cost = float(final.usage_total_usd or run.usage_total_usd or 0)

    salt = get_salt()
    items = [strip_personal(it, salt) for it in raw]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "query": query, "max_reviews": max_reviews, "actor": ACTOR,
        "fetched_at": datetime.now(timezone.utc).isoformat(), "cost_usd": cost,
        "items": items,
    }, ensure_ascii=False), encoding="utf-8")
    return items, cost, False


# ---------- parse ----------

def parse_place(items: list[dict], query: str) -> dict:
    if not items:
        raise RuntimeError("No results. Check the link, or try 'name, city'.")
    it = items[0]
    return {
        "place_id": it.get("placeId"),
        "name": it.get("title"),
        "category": it.get("categoryName"),
        "address": it.get("address"),
        "city": it.get("city"),
        "total_score": it.get("totalScore"),
        "reviews_count": it.get("reviewsCount"),
        "maps_url": it.get("url"),
        "source_input": query,
        "fetched_at": it.get("scrapedAt"),
    }


def parse_reviews(items: list[dict], place_id: str) -> list[dict]:
    reviews = []
    for it in items:
        if not it.get("reviewId"):
            continue  # a place-only row with no review
        text = (it.get("text") or "").strip()
        reviews.append({
            "review_id": it["reviewId"],
            "place_id": place_id,
            "stars": it.get("stars"),
            "text": text or None,
            "text_translated": it.get("textTranslated"),
            "language": it.get("originalLanguage"),
            "published_at": it.get("publishedAtDate"),
            "owner_reply": it.get("responseFromOwnerText"),
            "owner_reply_at": it.get("responseFromOwnerDate"),
            "reviewer_hash": it.get("reviewerHash"),
            "likes": it.get("likesCount"),
            "has_text": 1 if text else 0,
        })
    return reviews


# ---------- summary ----------

def summary(place: dict, reviews: list[dict], cost: float, cached: bool) -> str:
    dates = sorted(r["published_at"] for r in reviews if r["published_at"])
    fmt = lambda d: datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%d %b %Y")
    stars = Counter(r["stars"] for r in reviews)
    with_text = sum(r["has_text"] for r in reviews)
    replied = sum(1 for r in reviews if r["owner_reply"])
    lines = [
        f"{place['name']} ({place['category']}): {place['total_score']}★ "
        f"from {place['reviews_count']:,} Google reviews",
        f"Loaded {len(reviews)} reviews"
        + (f": {fmt(dates[0])} → {fmt(dates[-1])}" if dates else ""),
        "  " + " | ".join(f"{s}★ {stars.get(s, 0)}" for s in (5, 4, 3, 2, 1)),
        f"  {with_text} have text, {len(reviews) - with_text} are stars only; "
        f"owner replied to {replied}",
        f"Apify cost: ${cost:.2f}" + ("  (from cache, no charge)" if cached else ""),
    ]
    return "\n".join(lines)


def ingest(query: str, max_reviews: int = DEFAULT_MAX, refresh: bool = False) -> str:
    items, cost, cached = fetch(query, max_reviews, refresh)
    place = parse_place(items, query)
    reviews = parse_reviews(items, place["place_id"])
    with db.connect() as conn:
        db.save_place(conn, place)
        db.save_reviews(conn, reviews)
    return summary(place, reviews, cost, cached)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # so ★ and → print on Windows
    p = argparse.ArgumentParser(description="Pull a place's Google reviews.")
    p.add_argument("query", help='Google Maps link, or "name, city"')
    p.add_argument("--max", type=int, default=DEFAULT_MAX, help="newest N reviews (default 500)")
    p.add_argument("--refresh", action="store_true", help="ignore the cache and fetch again (costs money)")
    a = p.parse_args()
    print(ingest(a.query, a.max, a.refresh))


if __name__ == "__main__":
    main()
