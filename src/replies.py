"""Approved replies, saved to data/replies.json (gitignored).

Only the app's Approve button calls save_approved(): the agent's save_reply
tool can only queue a reply for approval (spec 04, D17). Nothing is ever
posted to Google.
"""

import json
from datetime import datetime, timezone

from src.config import DATA_DIR

PATH = DATA_DIR / "replies.json"


def load() -> list[dict]:
    if not PATH.exists():
        return []
    return json.loads(PATH.read_text(encoding="utf-8"))


def save_approved(place_id: str, review_id: str, text: str, source: str, flags: list[str]) -> dict:
    """Called only after the owner clicks Approve."""
    items = [r for r in load() if r["review_id"] != review_id]  # one reply per review
    entry = {"place_id": place_id, "review_id": review_id, "text": text.strip(),
             "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "source": source, "flags_at_approval": flags, "posted_to_google": False}
    items.append(entry)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return entry


def for_place(place_id: str) -> dict[str, dict]:
    return {r["review_id"]: r for r in load() if r["place_id"] == place_id}
