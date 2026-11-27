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
        from google.genai import types
        # 90 s per request: the free tier can hang; better to fail and fall back.
        _client = genai.Client(api_key=config.get("GEMINI_API_KEY"),
                               http_options=types.HttpOptions(timeout=90_000))
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


def _with_retry(fn):
    """Run a Gemini call, waiting and retrying on free-tier 429/5xx errors."""
    from google.genai import errors
    for attempt in range(6):
        try:
            return fn()
        except (errors.ClientError, errors.ServerError) as e:
            code = getattr(e, "code", None)
            if code in (429, 500, 503) and attempt < 5:
                wait = 20 if code == 429 else 5 * (attempt + 1)
                print(f"  Gemini busy ({code}), waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def _low_thinking(model: str):
    """The smart model thinks a lot by default and is slow on the free tier;
    'low' keeps summaries and drafts to seconds (D17). The fast model is left as is."""
    from google.genai import types
    return types.ThinkingConfig(thinking_level="low") if model == config.get("MODEL_SMART") else None


def _usage(resp) -> dict:
    u = resp.usage_metadata
    return {
        "prompt_tokens": (u.prompt_token_count or 0) if u else 0,
        "output_tokens": ((u.candidates_token_count or 0) + (u.thoughts_token_count or 0)) if u else 0,
    }


def _call(model: str, prompt: str, schema: dict) -> tuple[str, dict]:
    from google.genai import types
    cfg = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json",
        response_json_schema=schema,
        thinking_config=_low_thinking(model),
    )
    resp = _with_retry(lambda: _get_client().models.generate_content(model=model, contents=prompt, config=cfg))
    return resp.text or "", _usage(resp)


def generate_raw(model: str, contents: list, cfg) -> tuple[object, dict, bool]:
    """One raw generate_content call (used by the agent loop), cached on the
    full conversation + config, so asking the same question again is free.
    Returns (response, usage, came_from_cache)."""
    from google.genai import types
    key_src = json.dumps([model, [c.model_dump(mode="json", exclude_none=True) for c in contents],
                          cfg.model_dump(mode="json", exclude_none=True)], sort_keys=True)
    path = LLM_CACHE / f"raw_{hashlib.sha256(key_src.encode()).hexdigest()[:24]}.json"
    if path.exists():
        usage["cached"] += 1
        data = json.loads(path.read_text(encoding="utf-8"))
        return types.GenerateContentResponse.model_validate(data["response"]), data["usage"], True
    resp = _with_retry(lambda: _get_client().models.generate_content(model=model, contents=contents, config=cfg))
    u = _usage(resp)
    usage["calls"] += 1
    usage["prompt_tokens"] += u["prompt_tokens"]
    usage["output_tokens"] += u["output_tokens"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": model, "usage": u,
                                "response": resp.model_dump(mode="json", exclude_none=True)},
                               ensure_ascii=False), encoding="utf-8")
    return resp, u, False


def generate_text(prompt: str, model_setting: str = "MODEL_FAST") -> str | None:
    """Plain-text answer (e.g. a reply draft), cached on model + prompt."""
    from google.genai import types
    model = config.get(model_setting)
    path = _cache_file(model, prompt, {"text": True})
    if path.exists():
        usage["cached"] += 1
        return json.loads(path.read_text(encoding="utf-8"))["data"]
    cfg = types.GenerateContentConfig(temperature=0.3, thinking_config=_low_thinking(model))
    try:
        resp = _with_retry(lambda: _get_client().models.generate_content(model=model, contents=prompt, config=cfg))
    except Exception as e:
        log_failure("api_error", f"{type(e).__name__}: {e}", prompt)
        return None
    u = _usage(resp)
    usage["calls"] += 1
    usage["prompt_tokens"] += u["prompt_tokens"]
    usage["output_tokens"] += u["output_tokens"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": model, "usage": u, "data": resp.text}, ensure_ascii=False),
                    encoding="utf-8")
    return resp.text


EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 256


def embed(texts: list[str], task: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed texts (free on the Gemini API); callers cache the vectors."""
    from google.genai import types
    out = []
    for i in range(0, len(texts), 100):
        chunk = texts[i:i + 100]
        resp = _with_retry(lambda: _get_client().models.embed_content(
            model=EMBED_MODEL, contents=chunk,
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=EMBED_DIM)))
        out += [e.values for e in resp.embeddings]
    return out


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
