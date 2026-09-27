"""
Request IDs for the Render logs.

Every question gets a short ID (e.g. "a3f9c2") at the start of /query. Every log
line printed while answering that question starts with it:

    [REQ a3f9c2] [LLM] ▶ sarvam  (answer) ...
    [REQ a3f9c2] [LLM] ❌ sarvam failed ... -> switching to groq

so in Render -> Logs you can search the ID and see the full story of one question.
"""

import contextvars
import uuid

_request_id = contextvars.ContextVar("request_id", default="-")


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:6]
    _request_id.set(rid)
    return rid


def set_request_id(rid: str) -> None:
    _request_id.set(rid or "-")


def current_request_id() -> str:
    return _request_id.get()


def log(tag: str, message: str) -> None:
    """Print one log line with the current request ID, e.g. log("LLM", "✅ sarvam ok")."""
    print(f"[REQ {_request_id.get()}] [{tag}] {message}", flush=True)
