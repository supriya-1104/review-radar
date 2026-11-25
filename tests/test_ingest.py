"""Ingest tests on fake scraper data: no network, no Apify cost.

Run: .venv\\Scripts\\python.exe -m pytest -q
"""

import json

from src import db, ingest


def fake_item(review_id="r1", stars=5, text="Biryani was great", name="Asha Rao", reviewer_id="111"):
    return {
        "reviewId": review_id, "stars": stars, "text": text, "textTranslated": None,
        "originalLanguage": "en", "publishedAtDate": "2026-11-22T15:48:45.187Z",
        "responseFromOwnerText": None, "responseFromOwnerDate": None, "likesCount": 0,
        "name": name, "reviewerId": reviewer_id,
        "reviewerUrl": f"https://maps.google.com/contrib/{reviewer_id}",
        "reviewerPhotoUrl": "https://lh3.googleusercontent.com/x",
        "placeId": "P1", "title": "Test Cafe", "categoryName": "Cafe",
        "address": "1 Main Rd", "city": "Bengaluru", "totalScore": 4.4,
        "reviewsCount": 149, "url": "https://maps.google.com/?cid=1",
        "scrapedAt": "2026-11-25T06:44:08Z",
    }


def test_name_city_becomes_search_and_links_pass_through():
    assert ingest.to_start_url("Meghana Foods, Bengaluru").startswith(
        "https://www.google.com/maps/search/Meghana+Foods")
    assert ingest.to_start_url(" https://maps.app.goo.gl/abc ") == "https://maps.app.goo.gl/abc"


def test_personal_fields_removed_and_hash_is_stable():
    a = ingest.strip_personal(fake_item(), "salt")
    b = ingest.strip_personal(fake_item(review_id="r2"), "salt")
    for field in ingest.PERSONAL_FIELDS:
        assert field not in a
    assert "Asha" not in json.dumps(a)
    assert a["reviewerHash"] == b["reviewerHash"]          # same person, same hash
    assert a["reviewerHash"] != ingest.strip_personal(fake_item(), "other")["reviewerHash"]


def test_stars_only_review_kept_but_marked():
    items = [ingest.strip_personal(fake_item(), "s"),
             ingest.strip_personal(fake_item(review_id="r2", text="  ", stars=3), "s")]
    reviews = ingest.parse_reviews(items, "P1")
    assert [r["has_text"] for r in reviews] == [1, 0]
    assert reviews[1]["text"] is None


def test_cache_means_second_run_is_free(tmp_path, monkeypatch):
    monkeypatch.setattr(ingest.config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    path = ingest.cache_path("q", 5)
    path.write_text(json.dumps({"items": [ingest.strip_personal(fake_item(), "s")]}),
                    encoding="utf-8")
    items, cost, cached = ingest.fetch("q", 5)   # would need Apify if the cache missed
    assert cached and cost == 0.0 and len(items) == 1


def test_database_has_no_plain_names(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    items = [ingest.strip_personal(fake_item(), "s")]
    place = ingest.parse_place(items, "q")
    db.save_place(conn, place)
    db.save_reviews(conn, ingest.parse_reviews(items, place["place_id"]))
    conn.commit()
    dump = "\n".join(conn.iterdump())
    assert "Asha" not in dump and "contrib/111" not in dump
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1
