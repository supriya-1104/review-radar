"""Search reviews by meaning + keywords (spec 04, search_reviews).

Each review with text gets a 256-number "meaning vector" from Gemini's free
embedding model, stored once in the review_embeddings table. A question is
turned into a vector too; reviews pointing the same way score highest.
Exact keyword matches get a small boost. Plain Python, no extra package:
a few hundred reviews per place is tiny.
"""

import json
import math
import re

from src import llm
from src.tag import clean_text


def ensure_embeddings(conn, place_id: str) -> int:
    """Embed any of this place's text reviews that don't have a vector yet."""
    rows = conn.execute(
        "SELECT r.review_id, r.text, r.text_translated FROM reviews r "
        "LEFT JOIN review_embeddings e ON e.review_id = r.review_id AND e.model = ? "
        "WHERE r.place_id = ? AND r.has_text = 1 AND e.review_id IS NULL",
        (llm.EMBED_MODEL, place_id)).fetchall()
    if not rows:
        return 0
    texts = [clean_text(r["text_translated"] or r["text"])[:2000] for r in rows]
    vectors = llm.embed(texts, "RETRIEVAL_DOCUMENT")
    conn.executemany("INSERT OR REPLACE INTO review_embeddings VALUES (?, ?, ?)",
                     [(r["review_id"], llm.EMBED_MODEL, json.dumps(v)) for r, v in zip(rows, vectors)])
    conn.commit()
    return len(rows)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def search(conn, place_id: str, query: str, start_ts: str, end_ts: str,
           stars: list[int] | None = None, limit: int = 8) -> list[dict]:
    ensure_embeddings(conn, place_id)
    qv = llm.embed([query], "RETRIEVAL_QUERY")[0]
    words = [w for w in re.findall(r"[a-z]{3,}", query.lower())]
    sql = ("SELECT r.review_id, r.stars, r.text, r.text_translated, r.published_at, e.vector "
           "FROM reviews r JOIN review_embeddings e USING (review_id) "
           "WHERE r.place_id = ? AND r.published_at >= ? AND r.published_at < ?")
    args: list = [place_id, start_ts, end_ts]
    if stars:
        sql += f" AND r.stars IN ({','.join('?' for _ in stars)})"
        args += stars
    scored = []
    for r in conn.execute(sql, args):
        text = clean_text(r["text_translated"] or r["text"])
        score = _cosine(qv, json.loads(r["vector"]))
        if words and any(w in text.lower() for w in words):
            score += 0.05  # small boost for an exact keyword match
        scored.append((score, r, text))
    scored.sort(key=lambda x: -x[0])
    return [{"review_id": r["review_id"], "stars": r["stars"], "published_at": r["published_at"],
             "text": text, "score": round(s, 3)} for s, r, text in scored[:limit]]
