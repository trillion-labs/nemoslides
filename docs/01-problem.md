# 01 — Problem and thesis

## The gap

*Slide generation is a universal pain point with no usable open-weight answer. The good tools are all closed-source subscriptions; the OSS alternatives don't look like decks a real person would willingly present.*

Slide generation is one of those problems that sounds easy and isn't. Every knowledge worker makes decks. Every manager has watched a direct report spend half a day wrestling with alignment, layout, image search, and "does this section flow."

The pain is universal, the output is low-information, and the tools that work best — Gamma, Beautiful.ai, Canva Magic Design — are all closed-source subscription products with proprietary models behind them.

The OSS side has three shapes of answer, none of them close to useful:

- **Template engines** (reveal.js presets, remark, plain Markdown slide tools). Text in, bland template out. No layout judgment, no visual hierarchy, no coherence across slides.
- **Python-pptx codegen** (AutoPresent and similar). Technically open, but python-pptx is a verbose programmatic API, the visual ceiling is low, and the aesthetic reads as "auto-generated."
- **Research prototypes** (PPTAgent, SciDuet-style academic tools). Benchmark-driven, not product-driven. Zero velocity to a polished deck a real person would willingly present.

Gamma-style generation is the shape the market wants. The SOTA-on-paper research prototypes are not that shape. That gap is the one we're trying to shrink.

## Why it's hard for a language model

*Four layered decisions — layout, hierarchy, coherence, imagery. A small model typically collapses at least one, and the failure modes are structural rather than stylistic, which is what makes them addressable with SFT.*

Slide design has four decisions stacked on each other, and a small model tends to collapse at least one:

1. **Layout selection.** Given a topic and some content, which slide shape? A cover? A two-column with image? A quote? A progressive-reveal list? Base Nemotron-Nano defaults to `layout: default` 5 times out of 8 — because when you're unsure, the unlabeled default is safe. The result is a bullet-soup deck.
2. **Visual hierarchy inside the slide.** Headline vs. sub vs. body vs. footnote. Three bullets beats six. Base models run long and flat.
3. **Coherence across the deck.** Theme continuity, color discipline, repeated structural beats. Small models re-litigate choices slide-by-slide and drift.
4. **Grounded imagery.** "Put a relevant image here" is a generative failure mode. Base Nemotron-Nano hallucinates Unsplash photo IDs (correct URL format, nonexistent photo) — every image panel renders empty. The deck *looks* broken even when the markdown compiles.

These failure modes are exactly what people complain about online: "AI decks all look the same," "the images are obviously AI," "the layout is always boring." They're structural, not stylistic. That's encouraging — structural failures respond well to SFT on a good corpus.

## The thesis

*Open weights on the NVIDIA stack, Slidev markdown as the output format, the full feature surface as the training target, and a locked protocol with a cross-checked metric.*

Four commitments, defended in the docs that follow:

**1. Open weights, NVIDIA stack.** `Nemotron-3-Nano-30B-A3B` (post-trained, MoE, 3B active) under a permissive model license, fine-tuned with NeMo-RL's SFT recipe, LoRA + FSDP2. Runs on a single node and drops into the NVIDIA microservice deployment path without re-architecting. Details in [03-training.md](03-training.md).

**2. Slidev as the output format.** Text-only markdown with YAML frontmatter and a rich named-layout system. Low token count. Forgiving syntax. High visual ceiling via themes. Diff-able in git. Renders to HTML via Playwright, which keeps the door open to DOM-geometry eval later. Rationale in [02-data-pipeline.md](02-data-pipeline.md).

**3. Full Slidev capability surface, not a template-constrained subset.** An early version of the plan trained on a whitelisted set of 7 layouts. That was safer to learn, but ceiling-limited — the finetuned model would be a "better default Slidev deck" generator, which is not the wow delta. The current scope trains all named layouts plus shiki code blocks, Mermaid diagrams, KaTeX math, `v-click` progressive reveals, `v-motion` animations, presenter notes, transitions, and non-default themes. This is where the visible delta lives. Details in [02-data-pipeline.md](02-data-pipeline.md).

**4. Locked protocol, cross-checked metric.** One judge, one rubric, one test split, baseline numbers produced before training. The judge (Gemini 3 Flash, vision) handles the subjective axes — Content, Design, Coherence. An independent objective feature scanner (`eval/features.py`) counts Slidev primitives directly and produces a Visual Craft score the judge cannot bias. The weighted Overall over-weights Visual Craft because that's the axis where SFT delta is *expected* to land. Every detail in [04-evaluation.md](04-evaluation.md).

## What a good outcome looks like

*Clearing `nemotron-super` is the must-have; approaching `glm-5.1` is the stretch. Both are defensible without cherry-picking because the Visual Craft gap is objective and large.*

The baseline table (see [docs overview](index.md)) anchors expectations. `nemotron-nano` floor-scored Overall: **2.50**. `nemotron-super` (its 4×-larger sibling): **2.83**. `glm-5.1` (a strong open-weight reasoning model of similar vintage): **3.26**. `gpt-5.4` (frontier): **3.62**.

- **Must-have** outcome: finetuned nano ≥ `nemotron-super`. A 30B-A3B model (3B active) clearing a 120B-A12B sibling on a visual-craft-weighted rubric is a clean, defensible narrative.
- **Stretch** outcome: finetuned nano approaches or clears `glm-5.1`. This would be a small open model matching a much larger open reasoning model on a domain-specific task — exactly the value proposition of targeted SFT.

Neither outcome requires cherry-picking. The gap on objective Visual Craft (nano 1.80, gpt-5.4 3.40) is large, measurable, and the teaching signal the synthetic corpus is designed around.
