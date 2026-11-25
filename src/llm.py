"""All Gemini calls go through here (D4), so switching provider stays a small change.

- Every answer is cached in data/cache/llm/, keyed on model + prompt + schema,
  so re-running costs nothing.
- Output is JSON that must match a schema; a bad answer is retried once.
- Free-tier rate limits (HTTP 429) wait and retry.
- Failures are appended to data/cache/llm_failures.jsonl.
"""

import hashlib
import json
import time
from datetime import datetime, timezone

from src import config

LLM_CACHE = config.CACHE_DIR / "llm"
FAILURE_LOG = config.CACHE_DIR / "llm_failures.jsonl"

_client = None

# Running totals for this process, printed by callers.
usage = {"calls": 0, "cached": 0, "prompt_tokens": 0, "output_tokens": 0, "failures": 0}


def _get_client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=config.get("GEMINI_API_KEY"))
    return _client


def _cache_file(model: str, prompt: str, schema: dict):
    key = hashlib.sha256(json.dumps([model, prompt, schema], sort_keys=True).encode()).hexdigest()
    return LLM_CACHE / f"{key[:24]}.json"


def log_failure(kind: str, detail: str, prompt: str = "") -> None:
    usage["failures"] += 1
    FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "kind": kind,
                            "detail": detail[:500], "prompt_start": prompt[:200]}) + "\n")


def _call(model: str, prompt: str, schema: dict) -> tuple[str, dict]:
    from google.genai import errors, types
    cfg = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json",
        response_json_schema=schema,
    )
    for attempt in range(6):
        try:
            resp = _get_client().models.generate_content(model=model, contents=prompt, config=cfg)
            u = resp.usage_metadata
            return resp.text or "", {
                "prompt_tokens": (u.prompt_token_count or 0) if u else 0,
                "output_tokens": ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) if u else 0,
            }
        except (errors.ClientError, errors.ServerError) as e:
            code = getattr(e, "code", None)
            if code in (429, 500, 503) and attempt < 5:
                wait = 20 if code == 429 else 5 * (attempt + 1)
                print(f"  Gemini busy ({code}), waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def generate_json(prompt: str, schema: dict, model_setting: str = "MODEL_FAST") -> dict | None:
    """Ask Gemini for JSON matching `schema`. Returns the parsed dict, or None
    after one retry fails (the failure is logged)."""
    model = config.get(model_setting)
    path = _cache_file(model, prompt, schema)
    if path.exists():
        usage["cached"] += 1
        return json.loads(path.read_text(encoding="utf-8"))["data"]

    for attempt in (1, 2):
        try:
            text, u = _call(model, prompt, schema)
            usage["calls"] += 1
            usage["prompt_tokens"] += u["prompt_tokens"]
            usage["output_tokens"] += u["output_tokens"]
            data = json.loads(text)
        except json.JSONDecodeError as e:
            log_failure("bad_json", f"attempt {attempt}: {e}", prompt)
            continue
        except Exception as e:  # API error after its own retries
            log_failure("api_error", f"attempt {attempt}: {type(e).__name__}: {e}", prompt)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": model, "usage": u, "data": data},
                                   ensure_ascii=False), encoding="utf-8")
        return data
    return None
