from __future__ import annotations

from dataclasses import asdict, dataclass
from textwrap import dedent

from nemoslides.pipeline.slidev_reference import TASK_INSTRUCTIONS


@dataclass(frozen=True)
class Choice:
    value: str
    label: str
    guidance: str


AUDIENCE_CHOICES: tuple[Choice, ...] = (
    Choice(
        value="general",
        label="General",
        guidance=(
            "Keep the deck broadly understandable, quick to scan, and useful for a mixed audience."
        ),
    ),
    Choice(
        value="executive",
        label="Executive",
        guidance=(
            "Focus on decisions, clarity, and high-level takeaways instead of too much detail."
        ),
    ),
    Choice(
        value="technical",
        label="Technical",
        guidance=(
            "Allow more technical specificity and structured logic while staying presentation-ready."
        ),
    ),
)

TONE_CHOICES: tuple[Choice, ...] = (
    Choice(
        value="clear",
        label="Clear",
        guidance=(
            "Use short, direct headlines and clean supporting copy with minimal filler."
        ),
    ),
    Choice(
        value="professional",
        label="Professional",
        guidance=(
            "Keep the writing polished, restrained, and credible without sounding stiff."
        ),
    ),
    Choice(
        value="bold",
        label="Bold",
        guidance=(
            "Use stronger framing, higher contrast messaging, and a more assertive presentation style."
        ),
    ),
)

SLIDE_COUNT_CHOICES: tuple[int, ...] = (6, 8, 10)

DEFAULT_AUDIENCE = AUDIENCE_CHOICES[0].value
DEFAULT_TONE = TONE_CHOICES[0].value
DEFAULT_SLIDE_COUNT = 8
DEFAULT_THEME = "geist"

_AUDIENCE_MAP = {choice.value: choice for choice in AUDIENCE_CHOICES}
_TONE_MAP = {choice.value: choice for choice in TONE_CHOICES}


def audience_choice(value: str) -> Choice:
    try:
        return _AUDIENCE_MAP[value]
    except KeyError as exc:
        raise ValueError(f"unsupported audience choice: {value}") from exc


def tone_choice(value: str) -> Choice:
    try:
        return _TONE_MAP[value]
    except KeyError as exc:
        raise ValueError(f"unsupported tone choice: {value}") from exc


def validate_slide_count(value: int) -> int:
    if value not in SLIDE_COUNT_CHOICES:
        raise ValueError(f"unsupported slide count: {value}")
    return value


def template_context() -> dict[str, object]:
    return {
        "audiences": [asdict(choice) for choice in AUDIENCE_CHOICES],
        "tones": [asdict(choice) for choice in TONE_CHOICES],
        "slide_counts": list(SLIDE_COUNT_CHOICES),
        "defaults": {
            "audience": DEFAULT_AUDIENCE,
            "tone": DEFAULT_TONE,
            "slide_count": DEFAULT_SLIDE_COUNT,
        },
    }


def build_system_prompt() -> str:
    return (
        "You are an expert presentation designer. Given the user's deck request,"
        " produce a complete, renderable Slidev markdown file."
    )


def build_user_prompt(
    *,
    prompt: str,
    audience: str,
    tone: str,
    slide_count: int,
) -> str:
    selected_audience = audience_choice(audience)
    selected_tone = tone_choice(tone)
    validated_count = validate_slide_count(slide_count)

    return dedent(
        f"""
        Build a Slidev pitch deck from the request below.

        User request:
        {prompt.strip()}

        Fixed demo controls:
        - Audience: {selected_audience.label}
        - Audience guidance: {selected_audience.guidance}
        - Tone: {selected_tone.label}
        - Tone guidance: {selected_tone.guidance}
        - Target slide count: {validated_count} total slides, including the cover and closing slide
        - Theme: `{DEFAULT_THEME}`

        Content and design expectations:
        - Optimize for an interactive browser presentation rather than a static memo.
        - Prefer concise headlines, visual pacing, and believable specifics.
        - Use images only when they materially improve the deck.
        - If the prompt leaves details open, choose the strongest plausible framing and keep moving.
        """
    ).strip()
