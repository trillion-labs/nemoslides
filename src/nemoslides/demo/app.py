from __future__ import annotations

import json
import os
import subprocess
from textwrap import dedent
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from pydantic import BaseModel, Field

from nemoslides._paths import REPO_ROOT, RENDERER
from nemoslides.eval.generate import parse_deck
from nemoslides.pipeline.clients import chat_with_retry

from .prompting import (
    DEFAULT_AUDIENCE,
    DEFAULT_SLIDE_COUNT,
    DEFAULT_TONE,
    build_system_prompt,
    build_user_prompt,
    audience_choice,
    template_context,
    tone_choice,
    validate_slide_count,
)

APP_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))
GENERATED_ROOT = Path(
    os.environ.get("DEMO_OUTPUT_DIR", str(REPO_ROOT / "results" / "demo-presentations"))
).resolve()
GENERATED_ROOT.mkdir(parents=True, exist_ok=True)

MAX_PROMPT_CHARS = 4_000
MAX_COMPLETION_TOKENS = 8_192

app = FastAPI(title="NemoSlides demo", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
app.mount("/generated", StaticFiles(directory=str(GENERATED_ROOT)), name="generated")


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=12, max_length=MAX_PROMPT_CHARS)
    audience: str = Field(default=DEFAULT_AUDIENCE)
    tone: str = Field(default=DEFAULT_TONE)
    slide_count: int = Field(default=DEFAULT_SLIDE_COUNT)


def _generation_client() -> tuple[OpenAI, str, bool]:
    base_url = os.environ.get("DEMO_OPENAI_BASE_URL") or None
    api_key = (
        os.environ.get("DEMO_OPENAI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ("EMPTY" if base_url else None)
    )
    if not api_key:
        raise RuntimeError(
            "missing API key: set DEMO_OPENAI_API_KEY or OPENAI_API_KEY for the demo app"
        )

    model = os.environ.get("DEMO_MODEL", "gpt-5.4")
    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    is_openai_reasoning = base_url is None and model.startswith("gpt-5")
    return client, model, is_openai_reasoning


def _trim_log(text: str, limit: int = 1_600) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def _fake_deck_markdown(payload: GenerateRequest) -> str:
    prompt = payload.prompt.strip()
    audience = audience_choice(payload.audience).label
    tone = tone_choice(payload.tone).label
    slide_count = payload.slide_count
    return dedent(
        f"""
        ---
        theme: geist
        title: Demo deck
        layout: cover
        class: text-center
        mdc: true
        ---

        # Demo deck

        ### {prompt[:90]}

        ---
        layout: statement
        ---

        # Audience

        ### {audience}

        ---
        layout: two-cols
        ---

        # Demo controls

        - Tone: {tone}
        - Target slides: {slide_count}
        - Flow: prompt to interactive Slidev

        ::right::

        # What this proves

        - Local generation route works
        - Slidev build path works
        - Browser viewer loads the built deck

        ---
        layout: end
        ---

        # Ready

        ### This is a fake local deck for smoke testing.
        """
    ).strip() + "\n"


def _generate_deck_markdown(payload: GenerateRequest) -> str:
    if os.environ.get("DEMO_FAKE_GENERATION") == "1":
        return _fake_deck_markdown(payload)

    client, model, is_openai_reasoning = _generation_client()
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {
            "role": "user",
            "content": build_user_prompt(
                prompt=payload.prompt,
                audience=payload.audience,
                tone=payload.tone,
                slide_count=payload.slide_count,
            ),
        },
    ]
    kwargs: dict[str, object] = {"model": model, "messages": messages}
    if is_openai_reasoning:
        kwargs["reasoning_effort"] = os.environ.get("DEMO_REASONING_EFFORT", "medium")
        kwargs["max_completion_tokens"] = MAX_COMPLETION_TOKENS
    else:
        kwargs["max_tokens"] = MAX_COMPLETION_TOKENS

    response = chat_with_retry(client, **kwargs)
    raw = response.choices[0].message.content or ""
    deck = parse_deck(raw).strip()
    if not deck:
        raise RuntimeError("model returned an empty deck")
    return deck + "\n"


def _build_slidev_site(deck_path: Path, output_dir: Path, base_path: str) -> None:
    cmd = [str(RENDERER / "build.sh"), str(deck_path), str(output_dir), base_path]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        return
    detail = _trim_log(proc.stderr or proc.stdout or "slidev build failed")
    raise RuntimeError(detail)


def _write_manifest(presentation_dir: Path, payload: GenerateRequest, deck_md: str) -> None:
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt": payload.prompt,
        "audience": payload.audience,
        "tone": payload.tone,
        "slide_count": payload.slide_count,
        "deck_preview": deck_md[:500],
    }
    (presentation_dir / "meta.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "page_title": "NemoSlides demo",
            **template_context(),
        },
    )


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/generate")
def generate_deck(payload: GenerateRequest) -> dict[str, str]:
    prompt = payload.prompt.strip()
    if len(prompt) < 12:
        raise HTTPException(status_code=422, detail="prompt must be at least 12 characters")

    try:
        audience_choice(payload.audience)
        tone_choice(payload.tone)
        validate_slide_count(payload.slide_count)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    presentation_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
    presentation_dir = GENERATED_ROOT / presentation_id
    source_dir = presentation_dir / "_source"
    site_dir = presentation_dir / "site"
    source_dir.mkdir(parents=True, exist_ok=True)

    try:
        deck_md = _generate_deck_markdown(payload)
        deck_path = source_dir / "deck.md"
        deck_path.write_text(deck_md, encoding="utf-8")
        _write_manifest(presentation_dir, payload, deck_md)
        _build_slidev_site(deck_path, site_dir, f"/generated/{presentation_id}/site/")
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "id": presentation_id,
        "presentation_url": f"/generated/{presentation_id}/site/index.html",
        "deck_url": f"/generated/{presentation_id}/_source/deck.md",
    }
