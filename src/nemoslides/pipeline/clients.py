"""Shared API clients. OpenAI for the judge; OpenRouter for GLM-5.1 teacher and
Nemotron-3-Nano-30B-A3B baseline inference."""

from __future__ import annotations

import os
import time
from typing import Any

from dotenv import load_dotenv
from openai import APIError, OpenAI, RateLimitError

load_dotenv()

_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/trillion-labs/nemoslides",
    "X-Title": "NemoSlides",
}

TEACHER_MODEL = "z-ai/glm-5.1"
STUDENT_BASELINE_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
JUDGE_MODEL = "google/gemini-3-flash-preview"  # PPTEval VLM judge (via OpenRouter)


def openrouter_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )


def openai_client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def chat_with_retry(
    client: OpenAI,
    *,
    model: str,
    messages: list[dict[str, Any]],
    max_retries: int = 5,
    backoff_base: float = 2.0,
    **kwargs: Any,
) -> Any:
    """Chat-completion call with exponential backoff on rate limits + transient errors.

    OpenRouter uses the OpenAI SDK — pass extra headers as `extra_headers=_OPENROUTER_HEADERS`
    when calling via `openrouter_client()`.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )
        except RateLimitError as e:
            last_err = e
            sleep = backoff_base**attempt
            time.sleep(sleep)
        except APIError as e:
            last_err = e
            # retry on 429/5xx; give up on 4xx client errors
            status = getattr(e, "status_code", 0)
            if status == 429 or (isinstance(status, int) and status >= 500):
                sleep = backoff_base**attempt
                time.sleep(sleep)
            else:
                raise
    assert last_err is not None
    raise last_err


OPENROUTER_EXTRA_HEADERS = _OPENROUTER_HEADERS
