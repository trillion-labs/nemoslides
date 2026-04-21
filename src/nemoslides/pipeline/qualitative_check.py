"""Hour 1-2 qualitative gate.

Call GPT-5-mini (candidate teacher) and Nemotron-3-Nano-30B-A3B (base model under study)
on 3 diverse slide-generation prompts. Save outputs side by side so we can (a) validate the
teacher produces usable Slidev markdown, and (b) measure the 'distance to cover' for the
base model before SFT.

Run: `uv run python -m nemoslides.pipeline.qualitative_check`
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from nemoslides._paths import RESULTS

load_dotenv()

TEACHER_MODEL = "gpt-5-mini"
BASE_MODEL = "nvidia/nemotron-3-nano-30b-a3b"
OUT_DIR = RESULTS / "qualitative"

SYSTEM_PROMPT = """You are an expert slide designer. Generate a complete Slidev markdown presentation for the topic the user provides.

Hard requirements (strictly follow all):
- Slidev markdown format: `---` separators between slides, each slide's YAML frontmatter declared with `---\\n<yaml>\\n---` at the top of the slide.
- Every slide MUST declare a `layout:` field. Allowed layouts ONLY: cover, two-cols, image-right, image-left, quote, center, section, default.
- Global frontmatter on the first slide must include: `theme: seriph`, `class: text-center` (for cover only), `title: <deck title>`, `mdc: true`.
- 8-12 slides total. Start with `layout: cover`, end with a `layout: center` or `layout: default` conclusion.
- For image-right / image-left layouts, include an `image:` field with an Unsplash URL: `https://images.unsplash.com/photo-<id>?w=1200`. Use real, common Unsplash photo IDs.
- For two-cols, use `::right::` to separate left and right column content.
- Keep text concise — bullet points, short sentences. No paragraphs > 2 lines.
- No code blocks unless the topic is explicitly technical.

Output ONLY the raw Slidev markdown, no commentary, no surrounding markdown fences.
"""

PROMPTS = {
    "pitch_deck_ai_coding_startup": (
        "A $2M seed-round pitch deck for 'Corvid' — an AI coding assistant that uses agentic "
        "RL-fine-tuned models to autonomously fix production bugs. Audience: tier-1 Silicon Valley "
        "VCs. Cover problem, solution, demo results, market size, team, traction, ask."
    ),
    "tech_talk_attention": (
        "A 10-minute conference tech talk titled 'Attention Is All You Need — for Junior Engineers'. "
        "Explain the transformer attention mechanism intuitively, covering: motivation, Q/K/V intuition, "
        "multi-head attention, why it beat RNNs, and one practical code-level gotcha. Junior-engineer "
        "audience, visual-heavy, minimal math notation."
    ),
    "product_launch_ar_glasses": (
        "A consumer product launch deck for 'Apple Glass' — Apple's AR glasses, shipping March 2027. "
        "Cover design philosophy, three hero features (navigation, messaging, ambient computing), "
        "developer story, privacy posture, price, availability. Apple-style minimalism."
    ),
}


def call_openai(prompt: str) -> str:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=TEACHER_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def call_openrouter(prompt: str) -> str:
    client = OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )
    resp = client.chat.completions.create(
        model=BASE_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        extra_headers={
            "HTTP-Referer": "https://github.com/trillion-labs/nemoslides",
            "X-Title": "NemoSlides",
        },
    )
    return resp.choices[0].message.content or ""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for slug, prompt in PROMPTS.items():
        print(f"\n=== {slug} ===")
        (OUT_DIR / f"{slug}__prompt.txt").write_text(prompt + "\n")

        print(f"  calling {TEACHER_MODEL}...", flush=True)
        try:
            teacher_out = call_openai(prompt)
            (OUT_DIR / f"{slug}__teacher_{TEACHER_MODEL}.md").write_text(teacher_out)
            print(f"  teacher ok — {len(teacher_out)} chars")
        except Exception as e:
            print(f"  teacher FAILED: {e}", file=sys.stderr)
            (OUT_DIR / f"{slug}__teacher_{TEACHER_MODEL}.md").write_text(f"ERROR: {e}\n")

        print(f"  calling {BASE_MODEL}...", flush=True)
        try:
            base_out = call_openrouter(prompt)
            base_slug = BASE_MODEL.replace("/", "__")
            (OUT_DIR / f"{slug}__base_{base_slug}.md").write_text(base_out)
            print(f"  base ok — {len(base_out)} chars")
        except Exception as e:
            print(f"  base FAILED: {e}", file=sys.stderr)
            (OUT_DIR / f"{slug}__base_FAILED.md").write_text(f"ERROR: {e}\n")


if __name__ == "__main__":
    main()
