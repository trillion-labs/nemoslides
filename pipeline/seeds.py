"""Seed generator for synthetic training data.

Asks GLM-5.1 to produce highly diverse slide-deck seeds spanning tech, business,
consumer, creative, academic, and everyday-life domains. A fraction of seeds
come pre-baked with an outline (the synthesis model just styles slides from it);
the rest are topic-only (the synthesis model plans its own structure).

Each seed dict keys:
  id                (assigned at merge)
  domain            (one of DOMAINS)
  topic             (concrete, specific, 1-2 sentences)
  audience          (1 short phrase)
  style_hints       (1 short phrase)
  theme_hint        (one of THEMES)
  feature_hints     (subset of FEATURE_BUCKETS)
  n_slides_target   (6..14)
  outline_hint      (optional: structured list of per-slide bullets)

Resumable per-batch. Usage:
    uv run python -m pipeline.seeds --n 50 --batches 200 --concurrency 4 --out data/seeds.json
"""

from __future__ import annotations

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from tqdm import tqdm

from pipeline.clients import (
    OPENROUTER_EXTRA_HEADERS,
    TEACHER_MODEL,
    chat_with_retry,
    openrouter_client,
)

DOMAINS = [
    # technical / engineering
    "startup pitch deck",
    "conference tech talk",
    "product launch keynote",
    "academic lecture / research talk",
    "internal business review / quarterly update",
    "workshop tutorial / hands-on lab",
    "public explainer for a technical audience",
    # general professional
    "investor update for a non-tech business",
    "board meeting strategy briefing",
    "company all-hands town hall",
    "marketing campaign brief",
    "sales kickoff deck",
    "customer success case study",
    "partnership proposal",
    "annual report visual summary",
    "nonprofit fundraising pitch",
    "policy briefing for government officials",
    "design review presentation",
    "hiring / recruiting pitch deck",
    # creative / lifestyle / everyday
    "personal finance primer",
    "travel trip-planning guide",
    "cooking or food workshop",
    "fitness / wellness programme overview",
    "history mini-lecture",
    "book club discussion guide",
    "art or design retrospective",
    "wedding toast / life event recap",
    "parenting or family-life guide",
    "hobby tutorial (music, photography, gardening, pottery, etc.)",
    "local community project update",
    "school or classroom lesson slides",
    "culture & language explainer",
    "film or tv essay / analysis",
    "sports analytics or fan presentation",
    "self-improvement / productivity talk",
]

THEMES = [
    # official
    "default",
    "seriph",
    "apple-basic",
    # community (professional)
    "geist",
    "academic",
    "the-unnamed",
    "nord",
    "penguin",
    "dracula",
    "frankfurt",
    "scholarly",
    "takahashi",
]

FEATURE_BUCKETS = [
    "heavy-on-code-blocks-with-shiki-line-highlighting",
    "includes-mermaid-diagrams",
    "includes-KaTeX-math-equations",
    "uses-v-click-progressive-reveals",
    "image-forward-with-multiple-image-right-image-left-layouts",
    "quote-heavy-with-layout-quote-and-layout-fact",
    "minimal-text-layout-center-and-layout-statement",
    "two-column-comparison-with-layout-two-cols",
    "narrative-driven-mixed-layouts",
    "data-dense-with-tables-and-charts",
    "timeline-or-journey-structure",
    "before-and-after-comparison",
    "problem-solution-ask-format",
]

OUTLINE_FRACTION = 0.35  # ~35% of seeds include a pre-baked outline_hint


# Each theme has a natural topic/audience/vibe profile. Batches are
# pre-assigned a theme and the generator is told to produce topics that
# ACTUALLY FIT that theme — guaranteeing topic-theme alignment instead of
# hoping the LLM matches them correctly in a free-pick setup.
THEME_PROFILES: dict[str, dict[str, str]] = {
    "default": {
        "vibe": "neutral, clean, minimal blue — safe business default",
        "topic_fit": "generic business updates, internal reviews, company all-hands, partnership proposals, cross-functional status reports, quarterly OKR readouts, generic explainers",
        "tone": "professional, neutral, corporate",
    },
    "seriph": {
        "vibe": "elegant serif, editorial — reads like a longform essay",
        "topic_fit": "editorial essays, long-form keynotes, book-club discussions, culture/history explainers, film/tv analysis, philosophy talks, journalism briefings, museum talks",
        "tone": "thoughtful, literary, considered",
    },
    "apple-basic": {
        "vibe": "Apple-keynote minimalism, oversized type, tons of whitespace",
        "topic_fit": "consumer product launches, flagship feature reveals, design-review keynotes, brand-forward marketing, aesthetic product demos, fashion/beauty launches, premium-lifestyle pitches",
        "tone": "crisp, confident, minimal",
    },
    "geist": {
        "vibe": "Vercel-clean, monospace accents, developer-product energy",
        "topic_fit": "startup pitch decks, dev-tool launches, SaaS pitches, API/platform rollouts, infra-product explainers, investor updates for a dev-tool company, developer-conference tech talks",
        "tone": "confident, technical, crisp",
    },
    "academic": {
        "vibe": "formal serif, figure-heavy, traditional academic",
        "topic_fit": "research talks, conference paper walkthroughs, university lectures, thesis defenses, literature reviews, lab meeting updates, policy briefings grounded in research, higher-ed teaching",
        "tone": "formal, rigorous, evidentiary",
    },
    "the-unnamed": {
        "vibe": "VS Code dark, purple accents, IDE-native",
        "topic_fit": "engineering deep-dives, backend internals, compiler/language implementation talks, performance-optimization talks, open-source project tours, debugging war stories, security/red-team talks",
        "tone": "technical, detailed, hacker-friendly",
    },
    "nord": {
        "vibe": "cool blue-gray Nord palette, understated dev aesthetic",
        "topic_fit": "infra/DevOps talks, observability & SRE talks, cloud-architecture walkthroughs, networking/protocol explainers, terminal-tooling talks, systems programming",
        "tone": "calm, technical, polished",
    },
    "penguin": {
        "vibe": "warm modern gradients, Vue/JS ecosystem energy",
        "topic_fit": "Vue/JS/frontend meetup talks, product demos, component-library walkthroughs, design-system talks, hackathon recaps, community workshop kickoffs, developer-advocate presentations",
        "tone": "approachable, modern, energetic",
    },
    "dracula": {
        "vibe": "classic Dracula dark palette, high contrast, popular dev aesthetic",
        "topic_fit": "dev-tool tutorials, code-walkthrough talks, CLI tool showcases, terminal-workflow talks, hackathon pitches for developers, night-mode-forward tech talks",
        "tone": "playful-technical, developer-insider",
    },
    "frankfurt": {
        "vibe": "Beamer-inspired navy + cream, structured and formal",
        "topic_fit": "mathematics lectures, physics talks, economics seminars, structured academic lectures, grant-proposal presentations, formal conference presentations",
        "tone": "formal, structured, old-school academic",
    },
    "scholarly": {
        "vibe": "traditional academic (oxford/cambridge/princeton color variants)",
        "topic_fit": "humanities lectures, history talks, literature seminars, philosophy talks, classics/ancient-studies talks, liberal-arts college lectures, thesis presentations",
        "tone": "erudite, institutional, reflective",
    },
    "takahashi": {
        "vibe": "oversized type, one-idea-per-slide, extreme minimalism",
        "topic_fit": "lightning talks, single-idea manifestos, motivational talks, bold-opinion essays, short ignition-style talks, keynote closers, inspirational community talks",
        "tone": "punchy, declarative, high-impact",
    },
}


# Base prompt template. `{with_outline_clause}` is swapped per batch so the
# generator produces the right mix.
SEED_GENERATOR_PROMPT = """You are a creative strategist helping build a training corpus for a slide-generation model.

Generate {n} DIVERSE, REALISTIC slide-deck seeds — **all for the same Slidev theme: `{theme}`**. Every seed in this batch MUST be a topic that naturally belongs on this theme.

Theme profile for `{theme}`:
- Vibe: {theme_vibe}
- Topic fit: {theme_topic_fit}
- Tone: {theme_tone}

Each seed must feel like a presentation a real presenter would deliver using THIS theme. Topics outside the theme's natural fit are NOT acceptable (e.g., for `apple-basic` don't generate an engineering backend deep-dive; for `the-unnamed` don't generate a consumer fashion launch).

Return a JSON array of objects with this shape:

```json
[
  {{
    "domain": "<one of the domains listed>",
    "topic": "<1-2 sentence concrete topic description; specific and varied, MUST fit the theme profile>",
    "audience": "<1 short phrase describing the audience>",
    "style_hints": "<1 short phrase of style/tone — should align with theme tone>",
    "theme_hint": "{theme}",
    "feature_hints": ["<0-3 items from the feature bucket list>"],
    "n_slides_target": <integer between 6 and 14>{outline_field_shape}
  }},
  ...
]
```

{with_outline_clause}

Requirements:
- ALL {n} seeds must match the `{theme}` theme profile — no off-theme topics.
- The `theme_hint` field is always the literal string `{theme}`.
- Topics are CONCRETE and SPECIFIC with named (possibly fictional) products, people, places, or projects.
- Vary audiences, industries, n_slides_target, and feature_hints within the theme's natural range.
- Domains may repeat across seeds if multiple domains fit this theme; that is fine.
- Do NOT copy literal example phrasings from these instructions — invent new topics.
- Each seed unique.

Domain allowed list: {domains}

Feature hint guidance:
- code tutorials → code blocks
- research talks → KaTeX + mermaid
- pitch decks → two-col comparison or problem-solution-ask
- data/finance → data-dense tables
- travel/cooking/lifestyle → image-forward

Return ONLY the JSON array, no prose, no markdown fences.
"""

OUTLINE_CLAUSE_WITH = """For roughly half of the seeds in this batch, INCLUDE an `outline_hint` field — a list of 6–12 per-slide summaries the presenter wants on each slide. Each outline entry is a short string describing that slide's content (title or topic + 1–2 key points). The outline MUST be realistic and detailed enough that a slide designer could style it without inventing new content. For the OTHER half, OMIT the `outline_hint` field entirely (topic-only seed). This variety is important — don't include outlines for all seeds."""

OUTLINE_CLAUSE_WITHOUT = """Do NOT include an `outline_hint` field on any seed in this batch. These are topic-only seeds."""


def _parse_seeds(raw: str) -> list[dict[str, Any]]:
    raw = raw.strip()
    if raw.startswith("```"):
        nl = raw.find("\n")
        raw = raw[nl + 1 :] if nl != -1 else raw
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")].rstrip()
    return json.loads(raw)


def generate_seeds(n: int, theme: str, with_outline: bool) -> list[dict[str, Any]]:
    if theme not in THEME_PROFILES:
        raise ValueError(f"unknown theme '{theme}'. Must be one of {list(THEME_PROFILES)}")
    profile = THEME_PROFILES[theme]
    client = openrouter_client()
    prompt = SEED_GENERATOR_PROMPT.format(
        n=n,
        theme=theme,
        theme_vibe=profile["vibe"],
        theme_topic_fit=profile["topic_fit"],
        theme_tone=profile["tone"],
        domains=" | ".join(DOMAINS),
        outline_field_shape=',\n    "outline_hint": ["<slide 1 summary>", "<slide 2 summary>", ...]  // optional — include on ~half of seeds' if with_outline else '',
        with_outline_clause=OUTLINE_CLAUSE_WITH if with_outline else OUTLINE_CLAUSE_WITHOUT,
    )
    resp = chat_with_retry(
        client,
        model=TEACHER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers=OPENROUTER_EXTRA_HEADERS,
        temperature=1.0,
        top_p=1.0,
    )
    content = resp.choices[0].message.content or ""
    seeds = _parse_seeds(content)
    for s in seeds:
        # force the assigned theme — if the LLM drifted, correct it
        s["theme_hint"] = theme
        s.setdefault("feature_hints", [])
        s.setdefault("n_slides_target", random.randint(8, 12))
        if "outline_hint" in s and not isinstance(s["outline_hint"], list):
            del s["outline_hint"]
    return seeds


def _batch_file(batch_dir: Path, idx: int) -> Path:
    return batch_dir / f"batch_{idx:04d}.json"


def _batch_done(batch_dir: Path, idx: int) -> bool:
    f = _batch_file(batch_dir, idx)
    if not f.exists():
        return False
    try:
        d = json.loads(f.read_text())
        return isinstance(d, list) and len(d) > 0
    except (json.JSONDecodeError, OSError):
        return False


def _gen_one_batch(n: int, batch_dir: Path, idx: int, theme: str, with_outline: bool) -> tuple[int, int]:
    batch = generate_seeds(n, theme=theme, with_outline=with_outline)
    _batch_file(batch_dir, idx).write_text(
        json.dumps(batch, indent=2, ensure_ascii=False)
    )
    return idx, len(batch)


def _merge_all(batch_dir: Path, out_path: Path) -> int:
    batches = sorted(batch_dir.glob("batch_*.json"))
    merged: list[dict[str, Any]] = []
    for bf in batches:
        try:
            for s in json.loads(bf.read_text()):
                s["id"] = f"seed_{len(merged):05d}"
                merged.append(s)
        except (json.JSONDecodeError, OSError):
            continue
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    return len(merged)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=50, help="seeds per batch")
    p.add_argument("--batches", type=int, default=200, help="number of batches (target 10K at 50/batch)")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--outline-fraction", type=float, default=OUTLINE_FRACTION)
    p.add_argument("--out", type=Path, default=Path("data/seeds.json"))
    args = p.parse_args()

    batch_dir = args.out.with_suffix(".d")
    batch_dir.mkdir(parents=True, exist_ok=True)

    # deterministic per-batch assignments so resumes don't drift
    rng = random.Random(42)
    batch_asks_outline = [rng.random() < args.outline_fraction for _ in range(args.batches)]
    # round-robin themes across batches, shuffled deterministically so each
    # theme gets ~equal share; batch idx directly maps to theme
    theme_rng = random.Random(2026)
    theme_cycle = list(THEMES)
    theme_rng.shuffle(theme_cycle)
    batch_themes = [theme_cycle[i % len(theme_cycle)] for i in range(args.batches)]

    todo = [i for i in range(args.batches) if not _batch_done(batch_dir, i)]
    done = args.batches - len(todo)
    n_outline_batches = sum(batch_asks_outline[i] for i in todo)
    # theme distribution preview in remaining todo
    from collections import Counter
    todo_theme_hist = Counter(batch_themes[i] for i in todo)
    print(
        f"batches total: {args.batches} | already done: {done} | running: {len(todo)}\n"
        f"concurrency: {args.concurrency} | outline batches in remaining todo: {n_outline_batches}\n"
        f"theme distribution (remaining): {dict(todo_theme_hist)}"
    )

    if todo:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {
                pool.submit(
                    _gen_one_batch,
                    args.n,
                    batch_dir,
                    idx,
                    batch_themes[idx],
                    batch_asks_outline[idx],
                ): idx
                for idx in todo
            }
            for fut in tqdm(as_completed(futures), total=len(futures), desc="seed batches"):
                idx = futures[fut]
                try:
                    _, got = fut.result()
                    tqdm.write(
                        f"  + batch {idx:04d}: {got} seeds "
                        f"(theme={batch_themes[idx]}, outline={batch_asks_outline[idx]})"
                    )
                except Exception as e:
                    tqdm.write(f"  ! batch {idx:04d} failed: {type(e).__name__}: {e}")

    total = _merge_all(batch_dir, args.out)
    print(f"\nmerged {total} seeds → {args.out}")
    print(f"per-batch shards at      {batch_dir}/  ({args.batches} target)")


if __name__ == "__main__":
    main()
