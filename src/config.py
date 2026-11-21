"""Settings for Review Radar, read from the .env file.

Keys and tokens are never printed. Run `python -m src.config` to check that
everything is filled in: it shows only whether each value is set.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"      # gitignored: raw scraped reviews
CACHE_DIR = DATA_DIR / "cache"  # gitignored: cached LLM + scraper results

load_dotenv(ROOT / ".env")

SECRET_KEYS = ["GEMINI_API_KEY", "APIFY_TOKEN"]
SETTING_KEYS = ["MODEL_FAST", "MODEL_SMART"]


def get(name: str) -> str:
    """Return a setting from .env, or stop with a clear message if it's missing."""
    value = os.getenv(name, "").strip()
    if not value or value.startswith("your-"):
        raise RuntimeError(f"{name} is not set. Fill it in your .env file.")
    return value


def is_set(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value) and not value.startswith("your-")


def main() -> None:
    all_ok = True
    for name in SECRET_KEYS:
        ok = is_set(name)
        all_ok &= ok
        print(f"{'OK     ' if ok else 'MISSING'}  {name}")
    for name in SETTING_KEYS:
        ok = is_set(name)
        all_ok &= ok
        # Model names aren't secret, so it's fine to show them.
        shown = os.getenv(name) if ok else ""
        print(f"{'OK     ' if ok else 'MISSING'}  {name} {shown}")
    print("\nAll set." if all_ok else "\nSome values are missing. Edit .env and run again.")


if __name__ == "__main__":
    main()
