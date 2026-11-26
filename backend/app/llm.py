"""The only place that talks to a language model - always through LiteLLM.

Model, key and endpoint come from LLM_MODEL / LLM_API_KEY / LLM_API_BASE.
Every call has a timeout and bounded retries; on any failure (timeout, rate
limit, provider error, no model configured) callers get `None` and fall back to
deterministic behaviour, so the buddy never breaks because the LLM did.
Token usage and latency are tracked for the /api/metrics endpoint.
"""
import json
import logging
import os
import re
import time
from threading import Lock

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")  # no outbound fetch of the cost map

from . import config  # noqa: E402

log = logging.getLogger("llm")
_lock = Lock()
METRICS = {"calls": 0, "failures": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_latency_s": 0.0, "last_error": None}


def _litellm():
    import litellm
    litellm.suppress_debug_info = True
    litellm.drop_params = True  # ignore params a provider does not support instead of erroring
    return litellm


def chat(messages: list[dict], max_tokens: int = 600, temperature: float = 0.3, json_mode: bool = False) -> str | None:
    if not config.llm_enabled():
        return None
    kwargs = {"model": config.LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature,
              "timeout": config.LLM_TIMEOUT, "num_retries": config.LLM_MAX_RETRIES}
    if config.LLM_API_KEY:
        kwargs["api_key"] = config.LLM_API_KEY
    if config.LLM_API_BASE:
        kwargs["api_base"] = config.LLM_API_BASE
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    t0 = time.time()
    try:
        resp = _litellm().completion(**kwargs)
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        with _lock:
            METRICS["calls"] += 1
            METRICS["total_latency_s"] += time.time() - t0
            if usage:
                METRICS["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
                METRICS["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
        return text.strip()
    except Exception as e:  # timeouts, rate limits, auth, provider outages
        with _lock:
            METRICS["failures"] += 1
            METRICS["last_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        log.warning("LLM call failed: %s", METRICS["last_error"])
        return None


def chat_json(messages: list[dict], max_tokens: int = 400) -> dict | None:
    text = chat(messages, max_tokens=max_tokens, temperature=0.0, json_mode=True)
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def metrics() -> dict:
    with _lock:
        m = dict(METRICS)
    m["avg_latency_s"] = round(m["total_latency_s"] / m["calls"], 2) if m["calls"] else None
    m["model"] = config.LLM_MODEL
    return m
