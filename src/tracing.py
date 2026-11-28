"""Tracing to Arize Phoenix (spec 05). Local and free.

Start Phoenix first (python -m phoenix.server.main serve, opens on
http://localhost:6006). If it isn't running, tracing quietly switches off,
so the app and scripts work the same either way. TRACING=0 in .env turns it off.

What gets traced:
- every real Gemini call: automatically, by the OpenInference plug-in
- each analyst question (AGENT span) and each tool call (TOOL span): by us
- LLM answers served from our cache: a small "cached" span, so steps don't
  silently disappear from the timeline
"""

import json
import os
import socket
from contextlib import contextmanager

PHOENIX = ("127.0.0.1", 6006)
_tracer = None
_ready = False


def _phoenix_running() -> bool:
    try:
        with socket.create_connection(PHOENIX, timeout=0.3):
            return True
    except OSError:
        return False


def setup(project: str = "review-radar") -> bool:
    """Turn tracing on if Phoenix is running. Safe to call many times."""
    global _tracer, _ready
    if _ready:
        return _tracer is not None
    _ready = True
    if os.getenv("TRACING", "1") == "0" or not _phoenix_running():
        return False
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
    from phoenix.otel import register
    provider = register(project_name=project, endpoint=f"http://{PHOENIX[0]}:{PHOENIX[1]}/v1/traces",
                        verbose=False)
    GoogleGenAIInstrumentor().instrument(tracer_provider=provider)
    _tracer = provider.get_tracer("review-radar")
    return True


def _text(x) -> str:
    return x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)


class _Span:
    def __init__(self, span):
        self.span = span

    def output(self, value) -> None:
        if self.span is not None:
            self.span.set_attribute("output.value", _text(value)[:20000])

    def attr(self, key: str, value) -> None:
        if self.span is not None:
            self.span.set_attribute(key, value if isinstance(value, (str, int, float, bool)) else _text(value))


@contextmanager
def span(name: str, kind: str, input_value=None, **attrs):
    """kind: AGENT, TOOL, LLM, CHAIN... (OpenInference span kinds)."""
    if _tracer is None:
        yield _Span(None)
        return
    with _tracer.start_as_current_span(name) as s:
        s.set_attribute("openinference.span.kind", kind)
        if input_value is not None:
            s.set_attribute("input.value", _text(input_value)[:20000])
        for k, v in attrs.items():
            s.set_attribute(k.replace("__", "."), v if isinstance(v, (str, int, float, bool)) else _text(v))
        yield _Span(s)
