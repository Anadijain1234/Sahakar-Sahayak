"""
Triple-fallback AI engine:  Sarvam  ->  Groq  ->  Cloudflare

Every AI call in the app (translating the question to English, writing the
answer) goes through `chat()`. It tries the AIs in order and moves to the next
one as soon as one fails (error, timeout, empty reply). If all three fail, the
caller switches to "search-only" mode (see rag_service.py).

Every step is printed to the Render logs with the question's request ID, e.g.

    [REQ a3f9c2] [LLM] ▶ sarvam (answer) model=sarvam-105b
    [REQ a3f9c2] [LLM] ❌ sarvam failed after 30.02s: HTTP 429 rate limit  -> switching to groq
    [REQ a3f9c2] [LLM] ▶ groq (answer) model=openai/gpt-oss-120b
    [REQ a3f9c2] [LLM] ✅ groq answered in 1.84s (412 chars, provider id=req_01k...)

Environment variables (Render -> Environment, and your .env):
    SARVAM_API_KEY                         main AI
    GROQ_API_KEY                           1st backup (free: console.groq.com)
    CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN   2nd backup (same as meaning search)
Optional:
    GROQ_MODEL            default openai/gpt-oss-120b
    CLOUDFLARE_LLM_MODEL  default @cf/meta/llama-3.3-70b-instruct-fp8-fast
    LLM_ORDER             default sarvam,groq,cloudflare
    LLM_TIMEOUT           seconds per AI call, default 30
    LLM_COOLDOWN          seconds to skip an AI after it failed, default 60
"""

import os
import re
import time
import threading

import requests
from dotenv import load_dotenv

from backend.services.reqlog import log

load_dotenv()

SARVAM_MODEL = "sarvam-105b"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
CF_LLM_MODEL = os.getenv("CLOUDFLARE_LLM_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast").strip()
TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
COOLDOWN = float(os.getenv("LLM_COOLDOWN", "60"))
DEFAULT_ORDER = [p.strip() for p in os.getenv("LLM_ORDER", "sarvam,groq,cloudflare").split(",") if p.strip()]

PROVIDER_NAMES = {
    "sarvam": "Sarvam AI",
    "groq": "Groq (backup)",
    "cloudflare": "Cloudflare (backup)",
    "search_only": "Search only (AI unavailable)",
}

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
_sarvam = None
try:
    from sarvamai import SarvamAI
    _key = os.getenv("SARVAM_API_KEY", "").strip()
    if _key:
        try:
            _sarvam = SarvamAI(api_subscription_key=_key, timeout=TIMEOUT)
        except TypeError:          # older SDK without a timeout option
            _sarvam = SarvamAI(api_subscription_key=_key)
except Exception as e:             # SDK missing or broken -> just skip Sarvam
    print(f"[LLM] ⚠️ Sarvam SDK not available: {e}")

_GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()
_CF_ACCOUNT = os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
_CF_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()

_http = requests.Session()
# Tokens used per provider since the server started (the benchmark uses this to stay
# inside the free daily limits). {"groq": {"in": 0, "out": 0, "calls": 0}, ...}
USAGE = {}
_failed_at = {}                    # provider -> time of last failure (for the cool-down)
_lock = threading.Lock()


def configured() -> dict:
    return {"sarvam": _sarvam is not None, "groq": bool(_GROQ_KEY), "cloudflare": bool(_CF_ACCOUNT and _CF_TOKEN)}


print("=======================================================")
print("🧠 AI ENGINE: triple fallback  " + "  ->  ".join(
    f"{p} {'✅' if configured().get(p) else '❌ (no key)'}" for p in DEFAULT_ORDER))
print(f"   groq model: {GROQ_MODEL} | cloudflare model: {CF_LLM_MODEL} | timeout {TIMEOUT:.0f}s | cool-down {COOLDOWN:.0f}s")
print("=======================================================")


def _count(provider, usage, messages, text):
    """Add one call's token use (from the provider's own numbers, or a rough estimate)."""
    u = usage or {}
    tin = u.get("prompt_tokens") or u.get("input_tokens")
    tout = u.get("completion_tokens") or u.get("output_tokens")
    if tin is None:
        tin = sum(len(m.get("content") or "") for m in messages) // 3
    if tout is None:
        tout = len(text or "") // 3
    with _lock:
        d = USAGE.setdefault(provider, {"in": 0, "out": 0, "calls": 0})
        d["in"] += int(tin)
        d["out"] += int(tout)
        d["calls"] += 1


class ProviderError(Exception):
    def __init__(self, message, cool_down=True):
        super().__init__(message)
        self.cool_down = cool_down


def _clean(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def _http_error(resp) -> ProviderError:
    body = (resp.text or "")[:300].replace("\n", " ")
    # 400 = something in THIS request (e.g. safety filter); the AI itself is fine,
    # so don't put it on cool-down. 401/403/429/5xx = the AI is unusable right now.
    return ProviderError(f"HTTP {resp.status_code}: {body}", cool_down=resp.status_code != 400)


# ---------------------------------------------------------------------------
# One call per provider. Each returns (text, provider_request_id) or raises.
# ---------------------------------------------------------------------------
def _call_sarvam(messages, temperature, max_tokens):
    if _sarvam is None:
        raise ProviderError("no SARVAM_API_KEY", cool_down=False)
    resp = _sarvam.chat.completions(model=SARVAM_MODEL, messages=messages, temperature=temperature,
                                    max_tokens=max_tokens, reasoning_effort=None)
    msg = resp.choices[0].message if getattr(resp, "choices", None) else None
    text = _clean(getattr(msg, "content", "") or "")
    u = getattr(resp, "usage", None)
    _count("sarvam", {"prompt_tokens": getattr(u, "prompt_tokens", None),
                      "completion_tokens": getattr(u, "completion_tokens", None)} if u else None, messages, text)
    return text, getattr(resp, "id", None)


def _call_groq(messages, temperature, max_tokens):
    if not _GROQ_KEY:
        raise ProviderError("no GROQ_API_KEY", cool_down=False)
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": temperature,
               "max_completion_tokens": max_tokens + 800}   # gpt-oss also spends tokens on thinking
    if "gpt-oss" in GROQ_MODEL:
        payload.update({"reasoning_effort": "low", "include_reasoning": False})
    resp = _http.post("https://api.groq.com/openai/v1/chat/completions", json=payload, timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {_GROQ_KEY}"})
    if resp.status_code != 200:
        raise _http_error(resp)
    data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    _count("groq", data.get("usage"), messages, text)
    return _clean(text), data.get("id") or resp.headers.get("x-request-id")


def _call_cloudflare(messages, temperature, max_tokens):
    if not (_CF_ACCOUNT and _CF_TOKEN):
        raise ProviderError("no CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN", cool_down=False)
    url = f"https://api.cloudflare.com/client/v4/accounts/{_CF_ACCOUNT}/ai/run/{CF_LLM_MODEL}"
    resp = _http.post(url, json={"messages": messages, "temperature": temperature, "max_tokens": max_tokens},
                      timeout=TIMEOUT, headers={"Authorization": f"Bearer {_CF_TOKEN}"})
    if resp.status_code != 200:
        raise _http_error(resp)
    result = resp.json().get("result") or {}
    text = result.get("response")
    if text is None and result.get("choices"):                     # OpenAI-style models
        text = (result["choices"][0].get("message") or {}).get("content")
    text = text if isinstance(text, str) else ""
    _count("cloudflare", result.get("usage"), messages, text)
    return _clean(text), resp.headers.get("cf-ray")


_CALLS = {"sarvam": _call_sarvam, "groq": _call_groq, "cloudflare": _call_cloudflare}


def _model_of(provider):
    return {"sarvam": SARVAM_MODEL, "groq": GROQ_MODEL, "cloudflare": CF_LLM_MODEL}.get(provider, "?")


# ---------------------------------------------------------------------------
def chat(messages, purpose="answer", temperature=0.3, max_tokens=1024, order=None, _ignore_cooldown=False):
    """Ask the AIs in order until one gives a non-empty reply.

    Returns (text, provider) -- provider is "sarvam" / "groq" / "cloudflare",
    or (None, None) if every AI failed. Never raises.
    """
    order = order or DEFAULT_ORDER
    attempts = []
    for i, provider in enumerate(order):
        nxt = order[i + 1] if i + 1 < len(order) else "search-only mode"
        call = _CALLS.get(provider)
        if call is None:
            continue
        with _lock:
            failed = _failed_at.get(provider)
        if failed and time.time() - failed < COOLDOWN and not _ignore_cooldown:
            log("LLM", f"⏭ skipping {provider} ({purpose}): failed {time.time() - failed:.0f}s ago, "
                       f"cooling down {COOLDOWN:.0f}s -> {nxt}")
            attempts.append(f"{provider}:cooldown")
            continue

        log("LLM", f"▶ {provider} ({purpose}) model={_model_of(provider)}")
        t0 = time.perf_counter()
        try:
            text, provider_id = call(messages, temperature, max_tokens)
            secs = time.perf_counter() - t0
            if not text:
                raise ProviderError("empty reply", cool_down=False)
            with _lock:
                _failed_at.pop(provider, None)
            log("LLM", f"✅ {provider} answered {purpose} in {secs:.2f}s ({len(text)} chars"
                       f"{', provider id=' + str(provider_id) if provider_id else ''})")
            return text, provider
        except Exception as e:
            secs = time.perf_counter() - t0
            cool = getattr(e, "cool_down", True) and getattr(e, "status_code", None) != 400
            if isinstance(e, requests.Timeout):
                reason = f"timed out after {TIMEOUT:.0f}s"
            else:
                reason = str(e)[:300].replace("\n", " ")
            if cool:
                with _lock:
                    _failed_at[provider] = time.time()
            log("LLM", f"❌ {provider} failed {purpose} after {secs:.2f}s: {reason}  -> switching to {nxt}")
            attempts.append(f"{provider}:fail")

    if attempts and all(a.endswith(":cooldown") for a in attempts):
        # Every AI was only resting after an earlier failure -- give them one real try.
        log("LLM", f"🔁 all AIs were cooling down -- trying them once anyway for {purpose}")
        return chat(messages, purpose, temperature, max_tokens, order, _ignore_cooldown=True)
    log("LLM", f"🛑 all AIs failed for {purpose} ({', '.join(attempts) or 'none configured'})")
    return None, None
