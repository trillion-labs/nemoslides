"""Generation adapter over the 4 eval models.

Each model is a (route, slug, extra-kwargs) triple. The function accepts
system + user messages and returns raw assistant text. Reasoning tags
(<think>...</think>) are stripped at the parse step, not here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from pipeline.clients import (
    OPENROUTER_EXTRA_HEADERS,
    chat_with_retry,
    openai_client,
    openrouter_client,
)

Route = Literal["openrouter", "openai"]


@dataclass(frozen=True)
class ModelSpec:
    name: str                # short name used in paths + results files
    route: Route
    slug: str                # api model id
    extra: dict[str, Any] = field(default_factory=dict)


MODELS: dict[str, ModelSpec] = {
    "nemotron-nano": ModelSpec(
        name="nemotron-nano",
        route="openrouter",
        slug="nvidia/nemotron-3-nano-30b-a3b",
        extra={"extra_body": {"reasoning": {"effort": "medium"}}},
    ),
    "nemotron-super": ModelSpec(
        name="nemotron-super",
        route="openrouter",
        slug="nvidia/nemotron-3-super-120b-a12b",
        extra={"extra_body": {"reasoning": {"effort": "medium"}}},
    ),
    "glm-5.1": ModelSpec(
        name="glm-5.1",
        route="openrouter",
        slug="z-ai/glm-5.1",
    ),
    "gpt-5.4": ModelSpec(
        name="gpt-5.4",
        route="openai",
        slug="gpt-5.4",
        extra={"reasoning_effort": "medium"},
    ),
}


_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
_FENCE_BLOCK_RE = re.compile(
    r"```(?:markdown|md|slidev)?[ \t]*\n(.*?)```", re.DOTALL
)


def strip_think(text: str) -> str:
    """Remove leading <think>...</think> block(s). Returns the deck body."""
    return _THINK_RE.sub("", text, count=1).lstrip()


def unwrap_fence(text: str) -> str:
    """Unwrap when the model wrapped the deck in a ``` fence.

    A Slidev deck starts its own file with either YAML frontmatter
    (`---\\n...`), a heading (`# ...`), or a slide separator. If the raw
    output's first line is a code fence, strip it; also strip a trailing
    closing fence if present. Handles the common "model forgot to close
    the fence" case.

    If the first line isn't a fence, return as-is — inner ``` blocks
    (Mermaid, code, ASCII) are legitimate deck content.
    """
    stripped = text.lstrip()
    head, _, rest = stripped.partition("\n")

    if head.startswith("---") or head.startswith("#"):
        return text  # already a real deck

    if head.startswith("```"):
        # Drop trailing closing fence if present
        before_close, sep, _tail = rest.rpartition("\n```")
        return (before_close if sep else rest).rstrip()

    # No leading fence. Return original so render surfaces the real error.
    return text


def parse_deck(raw: str) -> str:
    return unwrap_fence(strip_think(raw))


def generate(
    spec: ModelSpec,
    *,
    system: str,
    user: str,
    temperature: float = 1.0,
    top_p: float = 1.0,
    max_tokens: int = 16384,
) -> dict[str, Any]:
    """Return {'raw': str, 'deck_md': str} — deck_md is think-stripped."""
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs: dict[str, Any] = {
        "model": spec.slug,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        **spec.extra,
    }

    if spec.route == "openrouter":
        client = openrouter_client()
        kwargs["extra_headers"] = OPENROUTER_EXTRA_HEADERS
    elif spec.route == "openai":
        client = openai_client()
        # GPT-5.x reasoning models: no temperature/top_p, and max_tokens is renamed
        kwargs.pop("temperature", None)
        kwargs.pop("top_p", None)
        if "max_tokens" in kwargs:
            kwargs["max_completion_tokens"] = kwargs.pop("max_tokens")
    else:
        raise ValueError(f"unknown route {spec.route!r}")

    resp = chat_with_retry(client, **kwargs)
    msg = resp.choices[0].message
    raw = msg.content or ""
    reasoning = getattr(msg, "reasoning", None) or ""
    return {"raw": raw, "deck_md": parse_deck(raw), "reasoning": reasoning}
