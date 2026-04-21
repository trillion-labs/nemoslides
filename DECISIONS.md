# Design Decisions

Locked decisions with rationale. Where relevant, the rejected alternatives are listed so later-Scott (or a reviewer) understands the tradeoff space.

## Base model: Nemotron-3-Nano-30B-A3B (MoE), **post-trained variant**

**Picked:** `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16` — the post-trained instruction/reasoning model (MoE, 3B active params, 128K context, text-only, NVIDIA Open Model License).

**Native reasoning format:** `<think>...</think>` tags. Enabled via `apply_chat_template(enable_thinking=True)`, default is ON. For vLLM inference: `chat_template_kwargs: {enable_thinking: true}`. Recommended generation params with reasoning: `temperature=1.0, top_p=1.0`. Supports `reasoning_budget` for trace-length control.

**Why post-trained, not `-Base-BF16`:**
- Post-trained already has chat template + reasoning behavior baked in; SFT specializes it for slide generation rather than teaching chat-format from scratch.
- LoRA SFT preserves the existing alignment and only adds slide-specific adapters.
- Baseline vs finetuned comparison is cleaner: both use the same `enable_thinking=True` inference mode, just the adapter differs.

**Ablation (stretch, if hour budget permits):** compare post-trained + SFT vs. base + SFT to quantify the contribution of post-training alignment. Not required for Track B submission.

**Rejected:** Nemotron-Nano-9B-v2 (dense, older) — less capable starting point; `-Base-BF16` (no post-training) — higher climb in 48h; Nemotron-Nano-12B-v2-VL — multimodal overkill, we generate markdown.

## Training framework: NeMo-RL (SFT)

**Picked:** [NeMo-RL](https://github.com/NVIDIA-NeMo/RL) with `examples/run_sft.py` and the `ResponseDataset` JSONL adapter.

**Why:** SFT is first-class in NeMo-RL (not just RL); satisfies the "NeMo Framework component or Microservice" eligibility gate explicitly. Lets us inherit the published Nano-3 30B-A3B LoRA recipe verbatim.

**Rejected:** TRL/PEFT, Axolotl — simpler, but **fails eligibility rule** (no NeMo component). NeMo 2.0 / Megatron — overkill for ~2,000 samples in 2 days. NeMo-AutoModel — kept as a backup if NeMo-RL install breaks.

## Slide format: Slidev markdown

**Picked:** [Slidev](https://sli.dev) — markdown with YAML frontmatter and named layouts (`cover / two-cols / image-right / quote / center / …`).

**Why:**
- Markdown is the most synthesis-friendly target for a small model (low token count, syntactically forgiving).
- Named `layout:` slots are a natural template-constrained SFT target — model picks layout + fills slots rather than authoring raw HTML.
- High visual ceiling via built-in themes (`seriph`, `shibainu`, etc.).
- Renders to HTML, which keeps the door open for GLM-5-style DOM-geometry eval if we want to add it later.

**Rejected:**
- **reveal.js raw HTML** — too token-heavy, no layout ergonomics.
- **Spectacle (JSX)** — one missing brace kills the entire deck. Hostile to small models.
- **Marp** — kept as a fallback if Slidev render throughput becomes the bottleneck. Same slot-based model.
- **python-pptx code generation (AutoPresent-style)** — possible, but python-pptx is verbose and less visually striking than web slides for a demo gallery.

## Output contract: full Slidev capability surface (revised hour 1.5)

**Picked:** Model emits a full Slidev `.md` file using the **complete Slidev feature surface** — all named layouts (`cover`, `two-cols`, `image-right`/`left`, `quote`, `center`, `section`, `default`, `fact`, `statement`, `intro`, `end`, `iframe`, `full`), shiki code blocks with per-line highlighting, Mermaid diagrams, KaTeX math, `v-click` progressive reveals, `v-motion` animations, transitions, presenter notes, and theme variety.

Enforced by: (a) a teacher prompt that embeds one-shot examples of advanced features, (b) a feature-coverage matrix that ensures the dataset spans the capability surface, (c) a render-validate check that drops malformed decks.

**Why:** Scott's explicit requirement (hour 1.5). A finetuned model that can emit `v-click` reveals, Mermaid diagrams, and code blocks with syntax highlighting is a dramatically stronger demo than one making prettier-but-static decks. This is where the "wow" lives.

**Trade-off accepted:** bigger capability surface is harder to learn from ~2k synthetic samples, and some advanced features (e.g. custom Vue components, `v-motion` fine-tuning) may not transfer reliably. Acceptable — gallery cherry-picks the best output; quantitative eval uses PPTEval which rewards visual quality regardless of feature count.

**Rejected:** template-constrained minimal subset (original plan, rolled back). Would have been safer but ceiling-limited. Free-form HTML still rejected — we want Slidev-markdown specifically because the teacher can generate it cleanly.

**Reference material for teacher prompt:** official Slidev demos at [slidevjs/slidev/tree/main/demo](https://github.com/slidevjs/slidev/tree/main/demo), [sli.dev](https://sli.dev) docs, community theme galleries.

## Training unit: one-shot with native reasoning trace (revised hour 2.5)

**Picked:** each training example is a **single-turn chat JSONL** where the assistant content is `<think>{reasoning}</think>\n\n{Slidev markdown with image-query placeholders}`.

Format exactly:
```jsonl
{"messages": [
  {"role": "system", "content": "<Slidev expert system prompt + knowledge pack>"},
  {"role": "user", "content": "Create a Slidev deck: <domain, topic, style hints>"},
  {"role": "assistant", "content": "<think>\n<reasoning about structure, theme, layouts, visuals>\n</think>\n\n---\ntheme: ...\nlayout: cover\n---\n# ...\n..."}
]}
```

Image URLs are **not** emitted — the model writes `image-query: "<natural language>"` placeholders in slide frontmatter. A deterministic preprocessor (runs before Slidev export) calls `unsplash_search` to resolve each query into a real URL. The model never emits a hash-like Unsplash ID it might hallucinate.

**Why:**
- Matches Nemotron-3-Nano-30B-A3B-BF16's **native `<think>` reasoning format** — zero format-alignment work, the SFT just specializes the model's existing reasoning behavior to slide generation.
- Reasoning-trace SFT distillation is the canonical pattern (s1, DeepSeek-R1, Nemotron's own post-training) — well-understood training dynamics, well-aligned narrative for NVIDIA judges.
- Teacher = **GLM-5.1 via OpenRouter** (`z-ai/glm-5.1`). GLM exposes `reasoning` as a separate structured field in its response; we wrap as `<think>{reasoning}</think>` at training-data build time. OpenAI's reasoning models hide the raw traces — GLM doesn't, which is why we're using it.
- One-shot (vs multi-turn agentic) cuts synthesis time 5–10× and keeps the training data format dead simple.
- Demo narrative survives because the **inference wrapper** (a ~50-line Python that calls the finetuned model → greps image-query lines → calls `unsplash_search` → renders) gives the same "agent with tools" demo feel without needing tool-calling SFT.

**Rejected:**
- Multi-turn agentic SFT with tool-calls in training — 5× slower synthesis, more complex training format, minimal benefit when the outer wrapper can fake agency.
- No reasoning trace — wastes the post-trained model's native reasoning capability and weakens the learning signal.
- Inline `<think>` tags in content (vs using GLM's separate field) — lower-quality reasoning; GLM-5.1 reasons more freely when the field is native.
- OpenCode SDK as runtime — TypeScript-only, session-oriented, misaligned with our Python/uv + NeMo-RL pipeline.

## Agent tools

**Picked (v0):** `unsplash_search(query: str) -> {url, attribution}`. Real Unsplash API.

**v0 fallback:** if no API key is set or quota exhausted, tool returns a photo from a curated `data/image_bank.json` of ~40 known-good Unsplash IDs tagged by theme (tech/team/office/abstract/nature). Keeps the pipeline runnable end-to-end for development.

**Stretch (if hour 5 shows time):** `iconify_search(query) -> svg_url` for cases where an icon is better than a photo, `web_search(query) -> snippets` for factual grounding on real companies/products.

**Rejected (for 48h):** image-generation tools (Flux/DALL-E) — too slow/expensive at 2000-deck scale. Possible for the ~10 hero decks in hour 26–32 demo polish.

## Data: synthetic, teacher-model authored, judge-filtered

**Picked:** ~3,000 generated → ~2,000 after filter.

Pipeline:
1. Seed generator produces diverse `(domain, topic, outline)` triples.
2. Teacher model (**GPT-5-mini by default**, upgrade to GPT-5/Claude if quality floor is low) authors each deck as Slidev markdown.
3. Slidev compile-check validator drops syntactically broken decks.
4. VLM judge scores each rendered deck on **PPTEval rubric** (Content / Design / Coherence, 1–5 each). Top ~65% kept.
5. Format as NeMo-RL `ResponseDataset` JSONL (`input_key: prompt`, `output_key: completion`).

**Why:** No suitable OSS dataset of Slidev/HTML decks with aesthetic quality labels exists (Zenodo10K is .pptx, SciDuet is academic, AutoPresent's 7k is python-pptx). Synthesizing from a strong teacher is faster than collecting and labeling, and lets us design the output distribution directly.

**Rejected:** Zenodo10K conversion — format mismatch, would require PPTX → Slidev transformation pipeline; too much scope for 2 days.

## Eval: PPTEval via VLM-as-judge, with explicit baseline

**Picked:** PPTEval rubric (Content / Design / Coherence, 1–5 each, from PPTAgent EMNLP 2025). Judge = GPT-4o or Claude. Pairwise preference also recorded on the 50-prompt held-out set.

**Baseline is non-negotiable.** We run the **stock `Nemotron-3-Nano-30B-A3B-Base-BF16` model** on the identical 50 held-out prompts at hour 7–8, scored with the identical judge + rubric, *before* training begins. This is the "status quo" measurement. Without it we cannot claim improvement and Track B's "validity of metrics" criterion collapses. The finetuned eval at hour 20–26 uses byte-identical prompts, judge model, and rubric text to ensure the Δ is meaningful and not confounded by protocol drift.

**Why:** PPTEval is canonical, published, has human-correlation numbers (Pearson ~0.71 in PPTAgent paper), and is exactly what the user's "VLM-as-judge" instinct pointed to. Baseline-vs-finetuned on the same protocol is the simplest defensible Track B story.

**Rejected:**
- GLM-5-style DOM-geometry + whitespace reward (L1/L2/L3) — impressive but under-specified in the paper, and the payoff over PPTEval isn't worth the 48h cost.
- SlidesBench (AutoPresent) — benchmark is in python-pptx format; would require format conversion. Stretch goal: port 30 SlidesBench prompts to Slidev format for cross-literature comparison if hour 32 looks healthy.
- Human eval — no budget.
- **Skipping the baseline run** — would be cheaper but invalidates the whole Track B claim.

## Domain: pitch decks + tech talks + product launches

**Picked:** generate seed topics across these three buckets.

**Why:** tech-judge familiar, peer-vote friendly, plentiful reference material online, and Slidev's built-in themes fit the aesthetic.

**Rejected:** lecture/academic slides (Beamer/Keynote norms differ from web-slide aesthetic; harder to show a wow delta), internal business review (boring visuals, low peer-vote appeal).

## Demo format: pre-rendered gallery + reel

**Picked:** static HTML gallery (~10 hero pairs) plus a ~60s comparison reel video.

**Why:** zero live-demo failure surface; we cherry-pick the best side-by-sides honestly; judges can view asynchronously; peer-vote "wow" is transmitted via the reel.

**Rejected:** live generation. Generation latency on 30B-A3B plus a 30% risk of malformed output = catastrophic for a 3-minute pitch.

## What we explicitly are NOT doing

- **No RL stage** (DPO, GRPO, or GLM-5-style reward model). Pure SFT only. 2-day budget.
- **No outline-generation training.** Outlines are produced by a frontier model in the end-to-end demo; the SFT target is `outline → slides`, not `topic → outline`.
- **No multimodal training.** Text-only Nemotron-3-Nano-30B-A3B. Images in slides are referenced by URL (placeholder) or emoji — design language without generative images.
- **No heavier eval than PPTEval.** Track B metric validity is satisfied; more is out of scope.
