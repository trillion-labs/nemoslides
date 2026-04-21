"""Objective Slidev-feature scanner.

Counts Slidev-specific capabilities used in a deck.md. The count maps to
a 1-5 visual_craft score — an objective discriminator that isn't subject
to judge drift and that directly measures what SFT teaches.

Features tracked (each contributes 1 point; cap at 5):
    - distinct named layouts used (beyond `default`): 1 pt per layout, max 2
    - shiki code blocks (```<lang>): 1 pt if present
    - Mermaid diagrams: 1 pt if present
    - KaTeX math ($..$ or $$..$$): 1 pt if present
    - v-click / v-clicks progressive reveals: 1 pt if present
    - presenter notes (`notes:` frontmatter or <!-- --> in slides): 1 pt
    - transitions (`transition:` frontmatter): 1 pt
    - non-default Slidev theme: 1 pt

Score mapping: min(5, 1 + total_points). So a deck with 0 features = 1;
a deck with all features = 5.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

# Match YAML frontmatter blocks between --- markers at slide boundaries.
# A Slidev deck has a top frontmatter + per-slide frontmatter blocks.
_SLIDE_FRONTMATTER_RE = re.compile(
    r"(?m)^---\s*\n(.*?)^---\s*$",
    re.DOTALL,
)

# Specifically look for `layout: <name>` and `theme: <name>` inside frontmatter.
_LAYOUT_RE = re.compile(r"(?m)^\s*layout:\s*['\"]?([\w-]+)['\"]?\s*$")
_THEME_RE = re.compile(r"(?m)^\s*theme:\s*['\"]?([\w-]+)['\"]?\s*$")
_TRANSITION_RE = re.compile(r"(?m)^\s*transition:\s*")
_NOTES_FM_RE = re.compile(r"(?m)^\s*notes:\s*")

# Shiki code fences: ```<language> (not just ``` or ```markdown/md/text)
_SHIKI_RE = re.compile(
    r"```(?!markdown\b|md\b|text\b|txt\b|plain\b|\s)([a-zA-Z][a-zA-Z0-9+_-]*)",
)
_MERMAID_RE = re.compile(r"```mermaid\b")
# KaTeX: $inline$ or $$block$$. Require at least one math-syntax character
# inside (^, _, \, {, }, =, +, -) to avoid matching "$147M" or "$12B in Q3".
_KATEX_INLINE_RE = re.compile(r"\$[^\s$][^$]*[\\^_{}=+\-][^$]*[^\s$]\$")
_KATEX_BLOCK_RE = re.compile(r"\$\$.*?\$\$", re.DOTALL)
_VCLICK_RE = re.compile(r"<v-clicks?\b|\bv-click\s*=|^\s*click:\s*", re.MULTILINE)


@dataclass
class FeatureReport:
    distinct_non_default_layouts: int   # count, capped at 2 pts
    has_shiki: bool
    has_mermaid: bool
    has_katex: bool
    has_v_click: bool
    has_notes: bool
    has_transitions: bool
    non_default_theme: bool
    total_points: int
    score: int  # 1-5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _collect_layouts(deck_md: str) -> set[str]:
    layouts: set[str] = set()
    for m in _SLIDE_FRONTMATTER_RE.finditer(deck_md):
        for lm in _LAYOUT_RE.finditer(m.group(1)):
            layouts.add(lm.group(1).lower())
    return layouts


def _theme(deck_md: str) -> str | None:
    for m in _SLIDE_FRONTMATTER_RE.finditer(deck_md):
        tm = _THEME_RE.search(m.group(1))
        if tm:
            return tm.group(1).lower()
    return None


def scan(deck_md: str) -> FeatureReport:
    layouts = _collect_layouts(deck_md)
    non_default_layouts = {l for l in layouts if l and l != "default"}
    distinct_non_default = len(non_default_layouts)

    theme = _theme(deck_md)
    non_default_theme = bool(theme and theme != "default")

    has_shiki = bool(_SHIKI_RE.search(deck_md))
    has_mermaid = bool(_MERMAID_RE.search(deck_md))
    has_katex = bool(_KATEX_INLINE_RE.search(deck_md) or _KATEX_BLOCK_RE.search(deck_md))
    has_v_click = bool(_VCLICK_RE.search(deck_md))

    has_notes = False
    for m in _SLIDE_FRONTMATTER_RE.finditer(deck_md):
        if _NOTES_FM_RE.search(m.group(1)):
            has_notes = True
            break

    has_transitions = False
    for m in _SLIDE_FRONTMATTER_RE.finditer(deck_md):
        if _TRANSITION_RE.search(m.group(1)):
            has_transitions = True
            break

    points = 0
    points += min(2, distinct_non_default)
    points += int(has_shiki)
    points += int(has_mermaid)
    points += int(has_katex)
    points += int(has_v_click)
    points += int(has_notes)
    points += int(has_transitions)
    points += int(non_default_theme)

    score = max(1, min(5, 1 + points))

    return FeatureReport(
        distinct_non_default_layouts=distinct_non_default,
        has_shiki=has_shiki,
        has_mermaid=has_mermaid,
        has_katex=has_katex,
        has_v_click=has_v_click,
        has_notes=has_notes,
        has_transitions=has_transitions,
        non_default_theme=non_default_theme,
        total_points=points,
        score=score,
    )
