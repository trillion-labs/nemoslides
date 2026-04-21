"""Gemini 3 Flash judge over rendered slide PNGs.

Judge sees only the user's original request + slide images, never the deck
markdown. Returns a strict JSON score per rubric dimension.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any

from pipeline.clients import (
    OPENROUTER_EXTRA_HEADERS,
    chat_with_retry,
    openrouter_client,
)

from eval.rubric import DIMENSIONS, JUDGE_SYSTEM, format_user_preamble

JUDGE_MODEL = "google/gemini-3-flash-preview"


class JudgeError(RuntimeError):
    pass


def _encode_png(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _image_part(path: Path) -> dict[str, Any]:
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/png;base64,{_encode_png(path)}"},
    }


def _extract_json_object(text: str) -> str:
    """Return the substring from the first '{' to the matching closing '}'.

    Handles models that wrap JSON in ```json fences or trail prose after the
    object. Ignores braces inside string literals.
    """
    s = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```\s*$", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()

    start = s.find("{")
    if start == -1:
        return s  # no object; let json.loads complain

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
    return s[start:]  # unbalanced; let json.loads complain


def _sanitize_invalid_escapes(s: str) -> str:
    """Replace invalid JSON backslash escapes with literal backslashes.

    Judge rationales often contain markdown like `\\*` or `\\-`, which are
    valid markdown but invalid JSON (strict JSON only allows " \\ / b f n r t u).
    """
    return re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)


def _parse_scores(raw: str) -> dict[str, Any]:
    text = _extract_json_object(raw)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = json.loads(_sanitize_invalid_escapes(text))
        except json.JSONDecodeError as e:
            raise JudgeError(f"judge returned non-JSON: {raw[:400]}") from e

    for dim in DIMENSIONS:
        if dim not in parsed:
            raise JudgeError(f"judge JSON missing dimension {dim!r}: {parsed}")
        entry = parsed[dim]
        if not isinstance(entry, dict) or "score" not in entry or "rationale" not in entry:
            raise JudgeError(f"judge JSON malformed at {dim!r}: {entry}")
        score = entry["score"]
        if not isinstance(score, int) or not (1 <= score <= 5):
            raise JudgeError(f"judge score out of range at {dim!r}: {score}")
    return parsed


def judge_deck(
    user_prompt: str,
    slide_pngs: list[Path],
    *,
    model: str = JUDGE_MODEL,
    max_attempts: int = 3,
) -> dict[str, Any]:
    if not slide_pngs:
        raise JudgeError("no slide PNGs provided to judge")

    client = openrouter_client()
    content_parts: list[dict[str, Any]] = [
        {"type": "text", "text": format_user_preamble(user_prompt)}
    ]
    content_parts.extend(_image_part(p) for p in slide_pngs)

    last_err: Exception | None = None
    for attempt in range(max_attempts):
        resp = chat_with_retry(
            client,
            model=model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": content_parts},
            ],
            temperature=0.0,
            extra_headers=OPENROUTER_EXTRA_HEADERS,
        )
        raw = resp.choices[0].message.content or ""
        try:
            return _parse_scores(raw)
        except JudgeError as e:
            last_err = e
            continue
    assert last_err is not None
    raise last_err
