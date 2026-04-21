"""Rubric v5 — weighted, visual-axis-heavy, hybrid subjective + objective.

v5 corrects two structural problems in v4:

1. **Overlap/redundancy**: v4's Prompt Fidelity duplicated Content's
   completeness axis. Dropped; Content's 5-anchor now includes completeness.

2. **Subjective visual score was noisy**: Visual Craft as a judge score
   was the exact axis we most needed signal on, but the judge couldn't
   discriminate reliably between "uses 2 layouts" and "uses 5." v5 moves
   Visual Craft to an **objective feature scan** (see eval/features.py):
   count actual Slidev feature usage in deck.md and map to 1–5.

4 dimensions:
    content      — substance, specificity, completeness (judge, 1-5)
    design       — typography, hierarchy, whitespace, polish (judge, 1-5)
    coherence    — narrative architecture, pacing (judge, 1-5)
    visual_craft — objective count of Slidev features used (auto, 1-5)

Overall is weighted, not equal:
    0.40 visual_craft + 0.25 design + 0.20 content + 0.15 coherence

Weighting rationale: the SFT delta lives in the visual axis. Content and
coherence are hygiene — already near-ceiling on capable base models, won't
move much with SFT, so low weight. Design and visual_craft are where SFT
teaches new behavior, so they carry the signal.

Judge sees: user prompt + slide PNGs only. Never the deck markdown.
"""

from __future__ import annotations

from textwrap import dedent

# All dimensions (for aggregation/storage).
DIMENSIONS = ("content", "design", "coherence", "visual_craft")

# Only these are scored by the judge. visual_craft is set by features.scan().
JUDGE_DIMENSIONS = ("content", "design", "coherence")

# Weights for the Overall composite.
WEIGHTS = {
    "visual_craft": 0.40,
    "design":       0.25,
    "content":      0.20,
    "coherence":    0.15,
}


JUDGE_SYSTEM = dedent(
    """\
    You are a STRICT presentation reviewer. You see the user's deck request
    and the rendered slides (one image per slide). Score three dimensions
    1-5. A **3** is the typical plausible output; most decks should land
    in 2-3. A **5** is reserved for work that would be accepted as-is by
    a demanding professional audience.

    ### Global hard caps (apply BEFORE individual-dim scoring)

    - Any slide is **visually empty, truncated, shows raw markdown/YAML/
      code fences as content, or is broken** → cap ALL dims at 2.
    - Fewer than **3 substantive slides** → cap ALL dims at 2.
    - Deck uses a **single layout across every slide** → cap Design at 3.
    - Deck is **all text**, no diagrams / tables / images / code / icons,
      when the prompt warrants them → cap Design at 3.
    - Any dim scored 4 or 5 MUST be justified with **specific cited
      evidence** in the rationale (quote a slide title, cite a layout by
      name, quote a number). A 4+ without evidence is a protocol violation
      — rescale it to 3.

    ### 1. Content (1-5) — substance, specificity, completeness

    Anchor: **McKinsey client-briefing / expert-panel quality**. The deck
    reads like it was written by a practitioner who knows the domain.
    Content 5 requires BOTH specificity (numbers, names, examples) AND
    completeness (addresses every explicit ask in the user's prompt).

    Blacklist phrases (heavy use → cap Content at 3):
      "best practices", "synergies", "leverage X", "stakeholder alignment",
      "move the needle", "paradigm shift", "world-class", "journey",
      "optimize", "enable", "empower", "robust", "seamless"

    - 1: empty, off-topic, placeholder strings, near-zero information.
    - 2: on-topic but generic; mostly platitudes; few specifics; misses
         major asks.
    - 3: covers the ask with some specifics; most slides feel templated or
         could apply to any company in the sector.
    - 4: concrete, grounded detail in most slides; addresses all major
         asks. Cite ≥3 specific examples.
    - 5: every slide carries audience-aware, non-obvious detail; every
         explicit ask is addressed. Cite ≥5 examples and explain why
         they're non-obvious.

    ### 2. Design (1-5) — typography, hierarchy, whitespace, polish

    Anchor: **Apple keynote / top-tier tech-conference slide quality**.
    Not "clean and readable" — visually crafted.

    - 1: broken rendering, overflow, unreadable.
    - 2: monotone; bullet walls; dead whitespace or cramped text; no
         hierarchy. **Hard ceiling for bullet-only decks.**
    - 3: readable, some hierarchy, formulaic; typography passable but not
         chosen; whitespace not intentional.
    - 4: polished typography, hierarchy reads cleanly, whitespace breathes,
         consistent visual system. Cite ≥2 specific slides.
    - 5: every slide looks designed. Typographic rhythm, intentional
         negative space, cohesive visual system. Cite ≥3 specific design
         choices.

    ### 3. Coherence (1-5) — narrative architecture

    Anchor: **a keynote a speaker would open a conference with**.

    - 1: random order, no open/close, no through-line.
    - 2: topical grouping only; no arc; generic "Thanks / Questions?"
         close; uniform slide density.
    - 3: clear opening and close; flow predictable; sequential not
         architectural.
    - 4: real arc — setup, tension/insight, payoff. Pacing varies
         intentionally. Cite the three structural beats.
    - 5: architecture is undeniable; every slide earns its place; reordering
         would break the argument. Cite the through-line and ≥3 slides
         advancing it.

    ### Output

    Return ONLY this JSON (no prose, no markdown fences):

    {
      "content":   {"score": <int 1-5>, "rationale": "<cite evidence if 4+>"},
      "design":    {"score": <int 1-5>, "rationale": "<cite evidence if 4+>"},
      "coherence": {"score": <int 1-5>, "rationale": "<cite evidence if 4+>"}
    }
    """
).strip()


USER_PREAMBLE = dedent(
    """\
    Original deck request:
    ---
    {user_prompt}
    ---

    The rendered slides follow, in order. Apply the rubric strictly:
    - Global caps FIRST (empty slides, <3 substantive, single layout, all text).
    - Evidence required in rationale for any 4 or 5 score.
    - 3 is typical plausible output.
    """
).strip()


def format_user_preamble(user_prompt: str) -> str:
    return USER_PREAMBLE.format(user_prompt=user_prompt.strip())
