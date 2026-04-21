# 02 — Data pipeline

!!! quote "The corpus is the product"
    Training recipe is hard-to-screw-up. Data is where projects of this shape actually live or die. Everything else in this doc set is in service of getting the corpus right.

This doc covers what gets into the training JSONL, how, and why each shape choice holds up.

## What a training sample looks like

*Chat JSONL with a `<think>` reasoning trace in the assistant turn. The reasoning isn't a demo prop — it's the primary training signal.*

One chat-format JSONL row. Assistant content is `<think>{reasoning}</think>\n\n{Slidev markdown}`.

```jsonl
{"messages": [
  {"role": "system", "content": "<Slidev expert system prompt + knowledge pack>"},
  {"role": "user", "content": "Create a Slidev deck: <topic, audience, constraints>"},
  {"role": "assistant", "content": "<think>\n<reasoning>\n</think>\n\n---\ntheme: seriph\nlayout: cover\n---\n# ..."}
]}
```

Published as [`trillionlabs/slides-sft-v0`](https://huggingface.co/datasets/trillionlabs/slides-sft-v0) — 705 train / 30 test rows, `reasoning_content` carried as a separate field on the assistant turn so the training loop can handle the `<think>` block explicitly.

The reasoning trace is not a demo prop. It's the primary training signal. The finetuned model inherits a design-teaching habit: read the user prompt, pick a theme, plan the narrative arc, map content to layouts, self-review, *then* write slides. That's the only way a one-shot model produces coherent decks without iteration.

## Why Slidev (and not the alternatives)

*Markdown is the highest-density format a language model can author. Slidev layers a named-layout system and a theme ceiling on top of it, and exports to HTML via Playwright so the render target stays inspectable.*

| Format | Why we didn't pick it |
|---|---|
| **reveal.js raw HTML** | Token-heavy. No layout ergonomics. A small model spends all its budget on div-soup. |
| **Spectacle (JSX)** | One missing brace kills the deck. Hostile to small-model generation. |
| **Marp** | Viable fallback (same slot-based model), kept as an option if Slidev render throughput blew up. Didn't. |
| **python-pptx codegen** | AutoPresent's corpus shape. Verbose programmatic API, low visual ceiling, "auto-generated" aesthetic. |

Slidev won on four axes: markdown is the highest-density format a language model can author, named layouts (`cover`, `two-cols`, `image-right`, `quote`, `center`, `section`, `fact`, `statement`, `intro`, `end`) are a natural template-constrained target, the theme system raises the visual ceiling, and the Playwright export path leaves room for DOM-geometry eval later.

## Why full Slidev surface, not a whitelisted subset

*Narrower scope would have been easier to learn, but the delta that matters lives in the advanced features. A "better default Slidev deck" is not the wow gap; code blocks, Mermaid, KaTeX, and `v-click` reveals are.*

An earlier version of this plan trained on 7 layouts and nothing else. That would have been easier — narrower distribution, fewer format failures, tighter loss curves. It was abandoned within two hours of the project starting.

**The "safer default" model is not the delta that matters.** The baseline already produces those, weakly.

The visible capability gap is in the advanced features — shiki-highlighted code with per-line ranges, Mermaid diagrams with readable graph structure, KaTeX math in correct positions, `v-click` progressive reveals that pace a narrative, theme-appropriate transitions, presenter notes that hold up in a real presentation.

That gap is why the evaluation includes an objective `visual_craft` scanner (see [04-evaluation.md](04-evaluation.md)) — it counts Slidev primitives directly, independent of the judge model. The SFT signal is designed to move that number.

## Why Codex as corpus author (not single-shot LLM calls)

*A single LLM call produces a monologue, not a design process. We needed an agent with file access, iteration, and validation — per-seed.*

The obvious approach is: call a strong model with a prompt, get a deck back, validate, keep or drop. That's what the first pipeline tried. Two problems surfaced quickly.

**Problem one: reasoning traces from a hidden-CoT model are junk.** OpenAI's reasoning models produce the best decks in one-shot, but the raw reasoning is hidden behind a summary.

GLM-5.1 exposes a raw `reasoning` field via OpenRouter, which is why it appears in `pipeline/clients.py` as an eligible teacher. But distilled reasoning from an inference call is still a monologue — no file access, no iteration, no self-review loop, no validation.

**Problem two: one-shot quality caps out.** A strong model making a 700-word reasoning trace and a 30-slide deck in a single response over-compresses both. The reasoning is sketchy; the deck cuts corners on the slides the model planned to get to and then ran out of room for.

The solution: use **Codex CLI** (`codex-manual` in `pipeline/clients.py`, `TEACHER_MODEL = "codex-manual"`) as the corpus author. Per-seed workflow:

1. `scripts.codex_pipeline init` materializes a workspace directory. Every seed gets its own folder with `seed.json`, `INSTRUCTIONS.md`, `HERO_EXAMPLE.md` (a gold few-shot from `reference/gold_examples/`), and stub files for `PROMPT.md` / `think.md` / `deck.md`.
2. Codex is invoked per-folder in parallel (`scripts/run_codex_batch.sh`, tmux-driven, 6-way default parallelism). For each seed, Codex reads the seed and instructions, produces the user-side `PROMPT.md`, writes a design-teaching `think.md` (3–8 sentences per section, 350–900 words, self-review mandatory per [`scripts/codex_templates/header.md`](https://github.com/trillion-labs/slides-sft/blob/main/scripts/codex_templates/header.md)), then authors the final `deck.md`.
3. `scripts.codex_pipeline status` and `pack` validate each folder: prompt substance, think substance, deck substance + syntactic checks. Bad folders are dropped.
4. `scripts.push_hf_dataset` packs kept folders into chat-JSONL and pushes to HF Hub.

This gets us per-seed file access, per-seed validation, per-seed retry, per-seed parallelism, and — crucially — a reasoning trace written explicitly as a *design-teaching artifact*, not a monologue incidental to the deck.

## Slidev feature coverage

*Breadth comes from diverse seeds plus a vendored Slidev knowledge pack injected at both synthesis and training time — not from hand-labeled feature requirements.*

The seed generator does not hand-label required features. The breadth comes from two sources.

**Diverse seeds.** `data/seeds.json` spans pitch decks, tech talks, product launches, internal reviews, conference overviews, educational content — each with domain, audience, tone, and slide-count hints. Feature use follows naturally: a tech talk benefits from code blocks and Mermaid diagrams; a pitch deck wants `fact` layouts and `v-click` reveals; a product launch needs `image-right` and `cover` with strong visuals.

**Injected knowledge pack.** `pipeline/slidev_reference.py` compiles a ~45KB / ~11K-token reference from the vendored `reference/slidev_docs/` (sparse-cloned from [`slidevjs/slidev`](https://github.com/slidevjs/slidev/tree/main/docs)). It covers: syntax, named layouts, animations (`v-click`, `v-motion`), Mermaid, KaTeX, shiki line-highlighting, icons, components, a curated themes catalog. This pack is prepended to the Codex instructions *and* to the training-time system prompt. The finetuned model learns against prompts that already carry the same Slidev idioms the training decks use.

Themes are restricted to `default`, `seriph`, and `apple-basic`. Earlier iterations included `bricks` and `shibainu`, but both render with placeholder graphic assets that make the decks look unfinished. Cutting them raised the dataset's visual floor without narrowing the useful capability surface.

## The image-query placeholder trick

*The model never emits an image URL. It emits a natural-language query. A render-time preprocessor resolves queries to real Unsplash URLs. Hallucinated IDs stop being a failure mode.*

Base Nemotron-Nano hallucinates Unsplash IDs — the URL format is correct but the IDs don't exist. Every image-right slide renders with an empty panel. This was the single most visible failure mode in the hour-1 qualitative check (see [qualitative evidence](qualitative/notes.md)).

The fix: the model never emits an image URL. It emits a natural-language query.

```yaml
---
layout: image-right
image-query: "modern office workspace with natural lighting"
---
```

A deterministic preprocessor (`pipeline/image_resolver.py`) runs before `renderer/render.sh` calls Slidev. For each `image-query:` line in the deck, it calls `pipeline/tools/image_search.py::unsplash_search(query)` and rewrites the line as `image: <resolved URL>`. On API failure or missing key, it falls back to a curated `data/image_bank.json` of ~40 hand-chosen Unsplash IDs tagged by theme (tech, team, office, abstract, nature).

Two reasons this is better than training the model to emit real URLs:

1. **Hallucination stops being a failure mode.** The model never has to invent an ID. Its worst-case output is a bad query, not a broken image.
2. **Images stay current.** Unsplash content rotates; a frozen URL in a 2026-trained checkpoint would silently go stale. Queries resolve at render time.

This also keeps image resolution out of the training loop. The dataset has placeholder queries; the preprocessor is the one thing that touches Unsplash. Swap it for Pexels or an internal image bank and the model is unchanged.

## What's rejected and why

*Every alternative we considered and why it didn't ship.*

- **Multi-turn agentic SFT with tool calls in training.** Considered and rolled back. 5–10× synthesis wall-clock, more complex training format, and the outer inference wrapper (finetuned model → grep image-query → resolve → render) delivers the same "agent with tools" feel without tool-calling SFT. Keeping the training format dead simple was worth more than the agentic signal.
- **Zenodo10K, SciDuet, AutoPresent's 7k.** Format mismatch (PPTX / academic / python-pptx). Would require a transform pipeline with no short path to Slidev. Out of scope for 48h.
- **Inline `<think>` tags concatenated into the assistant content from a hidden-CoT model.** Produces lower-quality reasoning than a model that exposes its raw trace. Was briefly planned with GLM-5.1 before the switch to Codex authoring.
- **Human-curated decks.** No budget. The synthetic-first route with per-seed validation is what a 48h solo project can actually ship.

## Current state

*What's shipped as of writing.*

- Seeds locked at `data/seeds.json` (plus batched archives in `data/seeds.d/`).
- Codex pipeline produced 651 validated rows at last pack; dataset published as 705 train / 30 test after dedup and quality pass.
- Image resolver + curated bank ship alongside the dataset.
- Full Slidev knowledge pack injected at both synthesis time and training time.
