# Hour 1–2 qualitative check — notes

## Setup
- Teacher: `gpt-5-mini` via OpenAI.
- Base model under study: `nvidia/nemotron-3-nano-30b-a3b` via OpenRouter (free tier, DeepInfra-backed).
- 3 prompts: AI-coding-startup pitch deck, 10-min tech talk on attention, Apple AR glasses launch.
- Shared system prompt requiring Slidev markdown + named-layout whitelist (cover/two-cols/image-right/image-left/quote/center/section/default).

## Results summary

| Prompt | Teacher (GPT-5-mini) | Base (Nemotron-3-Nano-30B-A3B) |
|---|---|---|
| Pitch deck (Corvid) | 3818 chars, 11 slides rendered, 7 layout types used | 1259 chars, 8 slides, 5 layout types, **hallucinated image URLs → blank image-right panels** |
| Tech talk (attention) | 2753 chars, 10 slides, 8 layout types | 1708 chars, 9 slides, 6 layout types, frontmatter placement issues |
| AR glasses launch | 2297 chars | **429 rate-limit (DeepInfra upstream)** — retry deferred |

## Qualitative observations

### Teacher (GPT-5-mini) — usable with minor fixes
- Generally produces valid Slidev. Contentful, layout-diverse, real Unsplash IDs.
- **Minor formatting bug:** occasionally inserts a blank line between the slide separator `---` and the frontmatter `layout: X`, which some Slidev parsers misread as content. Observed in the tech-talk output but not the pitch-deck output.
- **Mitigation:** tighten the system prompt with an explicit format exemplar. Not worth upgrading to GPT-5 (cost ~3x) yet — iterate prompt first, reassess at hour 2–3.

### Base (Nemotron-3-Nano-30B-A3B) — baseline is weak in predictable ways
- Understands the Slidev format at a surface level — emits `---`-separated slides with `layout:` fields.
- **Defaults heavily to `layout: default`** (5/8 slides on the pitch deck) → flat, bullet-only visuals.
- **Hallucinates Unsplash image IDs.** Format is right (`https://images.unsplash.com/photo-<id>?w=1200`) but IDs are made up → 404 on render → empty image panels. This produces visually broken slides — a *perfect* "before" case for the hackathon demo.
- Shorter outputs overall (~1.5k vs 2.8k chars) → thinner content per slide.
- Has some non-ASCII artifacts (en-dashes, smart quotes, backticks around `don't`) that are fine visually but noisy for tokenization.

### What SFT must close
1. **Layout diversity.** Push the model off the `default` layout; exercise the full named-layout whitelist + advanced layouts (fact, statement, intro, end).
2. **Image URLs that actually resolve.** Either train on real Unsplash IDs (pulled from the teacher), provide a curated ID library, or adopt an emoji/illustration strategy.
3. **Content density per slide.** Teacher averages ~4 focused bullets; base averages ~3 sparser ones.
4. **Structural reliability.** No blank lines inside the frontmatter; no trailing `---` after the last slide.

## Direction shift (user, hour 1.5)

**Training target is the full Slidev capability surface**, not just a template-constrained subset of named layouts. The dataset must also cover:
- Code blocks with shiki highlighting (`\`\`\`ts {2|3-5|*}` style per-line highlighting)
- Mermaid diagrams (` ```mermaid ... ``` `)
- KaTeX / LaTeX math (`$...$`, `$$...$$`)
- `v-click` progressive reveals, `v-motion` animations
- Transitions (`transition: slide-left`)
- Presenter notes (`<!-- note content -->`)
- Theme variety (seriph/default/apple-basic/bricks/shibainu)
- Advanced two-column slots (`::right::`, custom slots)
- Embedded components (custom Vue components — maybe out of scope for 2-day hackathon)

This shifts hour 2–5 from "diverse topic × layouts" to "diverse topic × layouts × advanced-feature coverage buckets." Use the official Slidev docs (sli.dev), sample decks in the [slidevjs/slidev](https://github.com/slidevjs/slidev/tree/main/demo) repo, and community theme galleries as one-shot references in the teacher prompt.

## Decisions taken this block
- Teacher model: **GPT-5-mini locked** (with prompt iteration in hour 2). Revisit if hour 2–3 synthesis quality is insufficient.
- Base model inference path: **OpenRouter (`nvidia/nemotron-3-nano-30b-a3b:free`)** for all qualitative + baseline eval queries. Free tier has rate limits — expect occasional 429s; add retry-with-backoff to the eval harness.
- Rendering: **canonical renderer at `renderer/`** with all common themes pre-installed. Usage: `./renderer/render.sh <input.md> <output_dir>` — copies deck into renderer dir and renders from there (Slidev resolves themes relative to deck location, not cwd).
- **Training target expanded to full Slidev capability** per user feedback (see section above).

## Next (hour 2–5)
Build data synthesis pipeline:
1. Pull Slidev demo decks + docs excerpts as reference material for the teacher prompt.
2. Design a feature-coverage matrix: layouts × advanced features × domains × theme.
3. Seed prompt generator emits (domain, topic, outline, required_features) tuples.
4. Teacher authors each deck with required features embedded.
5. Render-validate each deck; drop any that fail to render.
6. Output ~2500 valid `.md` files into `data/raw/`.
