"""Tag what each review is about, plus the dishes it names (spec 02).

Usage:
    python -m src.tag --place meghana        # name fragment or place_id
    python -m src.tag --all
    python -m src.tag --place meghana --sample 20   # show 20 tagged reviews to hand-check
    python -m src.tag --place meghana --sample-dishes 20

Steps: clean review text -> batches of 20 to MODEL_FAST -> check every quote
really appears in the review -> save aspects + dish mentions -> one call per
place to merge dish spellings -> print counts. All LLM answers are cached.
"""

import argparse
import html
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

from src import config, db, llm
from src.aspects import ASPECTS, LABELS, SENTIMENTS

BATCH = 20
MIN_DISH_MENTIONS = 3  # dashboard shows only dishes with >= 3 mentions

# Safety net if the model still tags a generic word as a dish.
GENERIC_DISH_WORDS = {"food", "meal", "meals", "starter", "starters", "snack", "snacks",
                      "veg", "non-veg", "non veg", "coffee", "tea", "drink", "drinks",
                      "beverage", "beverages", "dessert", "desserts", "main course"}

# ---------- text helpers ----------

def clean_text(text: str | None) -> str:
    """Google review text has <br> tags and HTML entities; make it plain."""
    if not text:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).strip()


def _norm(s: str) -> str:
    s = s.lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip()


def quote_found(quote: str, text: str) -> bool:
    """The anti-hallucination check: the quote must be an exact phrase from the
    review (ignoring case, spacing and curly vs straight quotes)."""
    q = _norm(quote).strip(" .,!\"'")
    return bool(q) and q in _norm(text)


# ---------- prompts + schemas ----------

TAG_SCHEMA = {
    "type": "object",
    "properties": {"reviews": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "aspects": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "aspect": {"type": "string", "enum": list(ASPECTS)},
                    "sentiment": {"type": "string", "enum": SENTIMENTS},
                    "quote": {"type": "string"},
                },
                "required": ["aspect", "sentiment", "quote"]}},
            "dishes": {"type": "array", "items": {
                "type": "object",
                "properties": {
                    "dish_raw": {"type": "string"},
                    "sentiment": {"type": "string", "enum": SENTIMENTS},
                    "aspect": {"type": "string", "enum": list(ASPECTS)},
                    "quote": {"type": "string"},
                },
                "required": ["dish_raw", "sentiment", "aspect", "quote"]}},
        },
        "required": ["id", "aspects", "dishes"]}}},
    "required": ["reviews"],
}


def tag_prompt(batch: list[tuple[str, str]]) -> str:
    aspect_lines = "\n".join(f"- {k}: {v}" for k, v in ASPECTS.items())
    reviews = "\n".join(json.dumps({"id": rid, "text": text}, ensure_ascii=False)
                        for rid, text in batch)
    return f"""You tag customer reviews of restaurants and cafes in India.

For EACH review, list every aspect it talks about, from this fixed list:
{aspect_lines}

Rules for aspects:
- A review can have several aspects with different sentiments ("tasty but slow" =
  food_taste pos + wait_time neg). Use each aspect at most once per review.
- sentiment: pos, neg or neutral.
- quote: copy the EXACT words from the review that support the tag (a short
  phrase, same spelling, no paraphrase, no added words).
- Speed is ALWAYS wait_time, never staff: "quick service", "slow service",
  "took ages", "served fast" -> wait_time. staff is about behaviour,
  attitude or skill (rude, polite, helpful, untrained). Plain "service was
  bad/good/worst" with NO mention of speed or waiting -> staff.
- Worse than before is NEGATIVE: "taste is less compared to earlier", "not like
  before", "quality has dropped" -> neg, not neutral.
- If one aspect gets both praise and a complaint in the same review ("food was
  good, but taste is less than earlier"), tag it neg and quote the complaint:
  the problem is what the owner needs to see.
- Any opinion about the food or a dish counts as food_taste: "good food",
  "tasty", "loved the biryani" -> food_taste pos (and list the dish if named).
- Only praise with no topic at all ("nice place", "good experience", "ok ok",
  "highly recommended", "good as usual") gets NO aspects: return an empty list.
  Do not guess.
- Reviews may be in Hinglish or have typos ("worst servise", "khana accha tha");
  tag them the same way.

Also list DISHES: only specific named dishes or drinks (e.g. "chicken biryani",
"paneer tikka", "filter coffee", "cappuccino", "dal makhani"). Generic words are
NOT dishes: food, meal, starters, snacks, veg, non-veg, coffee, tea, drinks,
beverages, desserts.
For each dish: dish_raw (exactly as written), sentiment about that dish, the
aspect the comment is about, and the exact quote.

Return every review id, even when both lists are empty.

Reviews (one JSON object per line):
{reviews}"""


DISH_SCHEMA = {
    "type": "object",
    "properties": {"groups": {"type": "array", "items": {
        "type": "object",
        "properties": {"dish": {"type": "string"},
                       "variants": {"type": "array", "items": {"type": "string"}}},
        "required": ["dish", "variants"]}}},
    "required": ["groups"],
}


def dish_prompt(place_name: str, raw_names: list[str]) -> str:
    names = "\n".join(f"- {n}" for n in raw_names)
    return f"""These dish names were written by customers in reviews of "{place_name}".
Group spelling variants and shorthand of the SAME dish under one clean canonical
name in sentence case (e.g. "biriyani", "chkn biryani", "chicken biriyani" ->
"Chicken biryani"). Only merge names that are clearly the SAME menu item.
Keep different dishes apart even when they share words: chicken biryani vs
mutton biryani vs veg biryani; fresh lime soda vs mint lime soda; filter coffee
vs cold coffee; tiramisu latte vs tiramisu cold coffee. But names that differ
only by the restaurant's own name or a "special"/"house" label are the house
signature dish and DO belong together (e.g. "special biryani", "{place_name}
special biryani", "{place_name} special chicken biryani"). Otherwise, when
unsure, keep them apart. If a name is too vague to know which variant it is (just "biryani"),
keep it as its own group ("Biryani"). The canonical name must be one of its
own variants, never a name taken from another group.
Every input name must appear in exactly one group's variants, spelled exactly
as given.

Names:
{names}"""


# ---------- validate one batch ----------

def validate(data: dict | None, batch: list[tuple[str, str]]) -> tuple[dict, Counter]:
    """Keep only well-formed tags whose quote is really in the review.
    Returns ({id: {"aspects": [...], "dishes": [...]}}, stats)."""
    stats = Counter()
    texts = dict(batch)
    out: dict[str, dict] = {}
    if not data or not isinstance(data.get("reviews"), list):
        stats["batch_failed"] += 1
        stats["missing_id"] += len(texts)
        return out, stats
    for r in data["reviews"]:
        rid = r.get("id")
        if rid not in texts or rid in out:
            stats["unknown_id"] += 1
            continue
        kept = {"aspects": [], "dishes": []}
        seen = set()
        for a in r.get("aspects") or []:
            if a.get("aspect") not in ASPECTS or a.get("sentiment") not in SENTIMENTS:
                stats["invalid_tag"] += 1
                continue
            stats["quotes_checked"] += 1
            if not quote_found(a.get("quote", ""), texts[rid]):
                stats["quote_not_found"] += 1
                continue
            if a["aspect"] in seen:
                continue
            seen.add(a["aspect"])
            kept["aspects"].append(a)
        for d in r.get("dishes") or []:
            if not d.get("dish_raw") or d.get("sentiment") not in SENTIMENTS:
                stats["invalid_tag"] += 1
                continue
            if d["dish_raw"].strip().lower() in GENERIC_DISH_WORDS:
                stats["generic_dish_dropped"] += 1
                continue
            stats["quotes_checked"] += 1
            if not quote_found(d.get("quote", ""), texts[rid]):
                stats["quote_not_found"] += 1
                continue
            if d.get("aspect") not in ASPECTS:
                d["aspect"] = None
            kept["dishes"].append(d)
        out[rid] = kept
    stats["missing_id"] += len(texts) - len(out)
    return out, stats


# ---------- run ----------

def find_places(conn, query: str | None, all_places: bool) -> list:
    if all_places:
        return conn.execute("SELECT place_id, name FROM places ORDER BY name").fetchall()
    rows = conn.execute("SELECT place_id, name FROM places WHERE place_id = ? OR name LIKE ?",
                        (query, f"%{query}%")).fetchall()
    if not rows:
        sys.exit(f"No place matches '{query}'. Load it first with python -m src.ingest.")
    return rows


def tag_place(conn, place_id: str, name: str) -> Counter:
    rows = conn.execute(
        "SELECT review_id, text, text_translated FROM reviews "
        "WHERE place_id = ? AND has_text = 1 ORDER BY published_at", (place_id,)).fetchall()
    items = [(r["review_id"], clean_text(r["text_translated"] or r["text"])) for r in rows]
    items = [(rid, t) for rid, t in items if t]
    model = config.get("MODEL_FAST")
    total = Counter()
    print(f"\n{name}: tagging {len(items)} reviews with text, {BATCH} per call...")

    for i in range(0, len(items), BATCH):
        chunk = items[i:i + BATCH]
        # Short ids (r1, r2...) save tokens; map back to real review ids after.
        short = [(f"r{j + 1}", t) for j, (_, t) in enumerate(chunk)]
        back = {f"r{j + 1}": rid for j, (rid, _) in enumerate(chunk)}
        data = llm.generate_json(tag_prompt(short), TAG_SCHEMA)
        result, stats = validate(data, short)
        total += stats
        now = datetime.now(timezone.utc).isoformat()
        for sid, tags in result.items():
            rid = back[sid]
            conn.execute("DELETE FROM aspects WHERE review_id = ?", (rid,))
            conn.execute("DELETE FROM dish_mentions WHERE review_id = ?", (rid,))
            conn.executemany("INSERT INTO aspects VALUES (?, ?, ?, ?)",
                             [(rid, a["aspect"], a["sentiment"], a["quote"]) for a in tags["aspects"]])
            conn.executemany(
                "INSERT INTO dish_mentions (review_id, dish_raw, sentiment, aspect, quote) "
                "VALUES (?, ?, ?, ?, ?)",
                [(rid, d["dish_raw"].strip(), d["sentiment"], d["aspect"], d["quote"])
                 for d in tags["dishes"]])
            conn.execute("INSERT OR REPLACE INTO tagged_reviews VALUES (?, ?, ?)", (rid, model, now))
        total["reviews_sent"] += len(chunk)
        total["reviews_tagged"] += len(result)
        conn.commit()
        print(f"  {min(i + BATCH, len(items))}/{len(items)}", end="\r")
    print()
    merge_dishes(conn, place_id, name)
    return total


# Common spelling variants, fixed in code before the AI sees them, so
# "Biriyani", "briyani" and "biryani" can never end up as separate dishes.
SPELLING_FIXES = [
    (r"\bb[ie]r[iy]+a?n[iy]+s?\b|\bbriyani\b|\bbirayani\b|\bbirinay\b", "biryani"),
    (r"\bchiken\b|\bchkn\b", "chicken"),
    (r"\bspl\.?\b", "special"),
    (r"\bmeghna\b", "meghana"),
]


def dish_key(raw: str) -> str:
    """Spelling-insensitive key: 'Meghna Spl Biriyani' -> 'meghana special biryani'."""
    k = raw.lower().replace("’", "'").replace("'s ", " ").replace("&", "and")
    k = re.sub(r"[^\w\s]", " ", k)
    for pattern, fix in SPELLING_FIXES:
        k = re.sub(pattern, fix, k)
    return re.sub(r"\s+", " ", k).strip()


def merge_dishes(conn, place_id: str, name: str) -> None:
    raws = [r[0] for r in conn.execute(
        "SELECT DISTINCT m.dish_raw FROM dish_mentions m JOIN reviews r USING (review_id) "
        "WHERE r.place_id = ? ORDER BY 1", (place_id,))]
    if not raws:
        return
    # Step 1 (code): group spelling and word-order variants
    # ("special meghana biryani" = "meghana special biryani").
    by_words = defaultdict(list)
    for r in raws:
        by_words[" ".join(sorted(dish_key(r).split()))].append(r)
    by_key = {}
    for members in by_words.values():
        # Display the most common spelling in the group.
        top = Counter(dish_key(m) for m in members).most_common(1)[0][0]
        by_key[top] = members
    keys = sorted(by_key)
    # Step 2 (AI): merge the cleaned keys that are the same dish
    # ("meghana special chicken biryani" + "special biryani").
    data = llm.generate_json(dish_prompt(name, keys), DISH_SCHEMA) or {"groups": []}
    key_to_dish: dict[str, str] = {}
    for g in data.get("groups", []):
        for v in g.get("variants", []):
            if v in by_key and v not in key_to_dish and g.get("dish"):
                key_to_dish[v] = dish_key(g["dish"])
    mapping: dict[str, str] = {}
    for k, members in by_key.items():
        canonical = key_to_dish.get(k, k).capitalize()  # sentence case: "Chicken biryani"
        for r in members:
            mapping[r] = canonical
    variants = defaultdict(list)
    for raw, dish in mapping.items():
        variants[dish].append(raw)
    conn.execute("DELETE FROM dishes WHERE place_id = ?", (place_id,))
    conn.executemany("INSERT INTO dishes VALUES (?, ?, ?)",
                     [(place_id, d, json.dumps(v, ensure_ascii=False)) for d, v in variants.items()])
    conn.executemany(
        "UPDATE dish_mentions SET dish = ? WHERE dish_raw = ? AND review_id IN "
        "(SELECT review_id FROM reviews WHERE place_id = ?)",
        [(d, raw, place_id) for raw, d in mapping.items()])
    conn.commit()


# ---------- reports ----------

def report(conn, place_id: str, stats: Counter) -> str:
    sent = stats["reviews_sent"] or 1
    checked = stats["quotes_checked"] or 1
    lines = [
        f"  Tagged {stats['reviews_tagged']}/{stats['reviews_sent']} reviews "
        f"({100 * stats['missing_id'] / sent:.1f}% missing/failed, target < 2%)",
        f"  Quotes found in review: {100 * (1 - stats['quote_not_found'] / checked):.1f}% "
        f"({stats['quote_not_found']} tags dropped for a made-up quote)",
        "",
        f"  {'Aspect':24} {'neg':>5} {'pos':>5} {'neutral':>8}",
    ]
    counts = defaultdict(Counter)
    for a, s, n in conn.execute(
            "SELECT a.aspect, a.sentiment, COUNT(*) FROM aspects a JOIN reviews r USING (review_id) "
            "WHERE r.place_id = ? GROUP BY 1, 2", (place_id,)):
        counts[a][s] = n
    for a in sorted(counts, key=lambda k: -counts[k]["neg"]):
        c = counts[a]
        lines.append(f"  {LABELS[a]:24} {c['neg']:>5} {c['pos']:>5} {c['neutral']:>8}")
    none = conn.execute(
        "SELECT COUNT(*) FROM tagged_reviews t JOIN reviews r USING (review_id) WHERE r.place_id = ? "
        "AND NOT EXISTS (SELECT 1 FROM aspects a WHERE a.review_id = t.review_id)", (place_id,)).fetchone()[0]
    lines.append(f"  (no specific aspect, e.g. 'nice place': {none} reviews)")
    lines += ["", "  Top 10 dishes (praised / criticised / neutral):"]
    for d, n, p, ng, nu in conn.execute(
            "SELECT m.dish, COUNT(*), SUM(sentiment='pos'), SUM(sentiment='neg'), SUM(sentiment='neutral') "
            "FROM dish_mentions m JOIN reviews r USING (review_id) WHERE r.place_id = ? "
            "GROUP BY 1 ORDER BY 2 DESC LIMIT 10", (place_id,)):
        flag = "" if n >= MIN_DISH_MENTIONS else "  (< 3 mentions: hidden on dashboard)"
        lines.append(f"    {d}: {p} / {ng} / {nu}{flag}")
    return "\n".join(lines)


def sample(conn, place_id: str, n: int) -> None:
    rows = conn.execute(
        "SELECT r.review_id, r.stars, r.text, r.text_translated FROM tagged_reviews t "
        "JOIN reviews r USING (review_id) WHERE r.place_id = ?", (place_id,)).fetchall()
    random.seed(42)
    for i, r in enumerate(random.sample(rows, min(n, len(rows))), 1):
        text = clean_text(r["text_translated"] or r["text"]).replace("\n", " ")
        print(f"\n#{i} [{r['stars']}★] {text[:400]}")
        tags = conn.execute("SELECT aspect, sentiment, quote FROM aspects WHERE review_id = ?",
                            (r["review_id"],)).fetchall()
        for a in tags:
            print(f"     {a['sentiment']:>7}  {LABELS[a['aspect']]:22} \"{a['quote']}\"")
        for d in conn.execute("SELECT dish_raw, dish, sentiment FROM dish_mentions WHERE review_id = ?",
                              (r["review_id"],)):
            print(f"     {d['sentiment']:>7}  dish: {d['dish_raw']} -> {d['dish']}")
        if not tags:
            print("     (no aspects)")


def sample_dishes(conn, place_id: str, n: int) -> None:
    rows = conn.execute(
        "SELECT m.dish_raw, m.dish, m.sentiment, m.quote FROM dish_mentions m "
        "JOIN reviews r USING (review_id) WHERE r.place_id = ?", (place_id,)).fetchall()
    random.seed(7)
    for i, d in enumerate(random.sample(rows, min(n, len(rows))), 1):
        print(f"#{i:>2} {d['sentiment']:>7}  {d['dish_raw']!r} -> {d['dish']!r}   \"{d['quote']}\"")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Tag reviews with aspects and dishes.")
    p.add_argument("--place", help="place name fragment or place_id")
    p.add_argument("--all", action="store_true", help="tag every loaded place")
    p.add_argument("--sample", type=int, help="show N random tagged reviews (no tagging)")
    p.add_argument("--sample-dishes", type=int, help="show N random dish mentions (no tagging)")
    a = p.parse_args()
    if not a.place and not a.all:
        p.error("give --place <name> or --all")

    with db.connect() as conn:
        for place_id, name in find_places(conn, a.place, a.all):
            if a.sample:
                print(f"\n=== {name}: {a.sample} random tagged reviews ===")
                sample(conn, place_id, a.sample)
                continue
            if a.sample_dishes:
                print(f"\n=== {name}: {a.sample_dishes} random dish mentions ===")
                sample_dishes(conn, place_id, a.sample_dishes)
                continue
            start = time.time()
            stats = tag_place(conn, place_id, name)
            print(report(conn, place_id, stats))
            print(f"  Took {time.time() - start:.0f}s")

    if not (a.sample or a.sample_dishes):
        u = llm.usage
        print(f"\nGemini: {u['calls']} new calls, {u['cached']} from cache, "
              f"{u['prompt_tokens']:,} input + {u['output_tokens']:,} output tokens, "
              f"{u['failures']} logged failures. Cost: $0.00 on the free tier.")


if __name__ == "__main__":
    main()
