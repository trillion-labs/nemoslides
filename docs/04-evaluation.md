# 04 — Evaluation

Everything the project claims — every number, every "better," every Δ — traces back to the protocol in this doc. It's the longest doc on purpose. If you read one file in `docs/`, read this one.

## What PPTEval is

*Three-dimension VLM-as-judge rubric from the PPTAgent paper (EMNLP 2025), ~0.71 Pearson with human judgment. We use the three dimensions and the 1–5 scale as published.*

PPTEval is the rubric proposed in [**PPTAgent** (EMNLP 2025, arXiv 2501.03936)](https://arxiv.org/abs/2501.03936). It scores slide decks on three subjective dimensions, 1–5 each:

- **Content** — completeness, informativeness, factual sanity.
- **Design** — visual quality: layout, typography, spacing, color.
- **Coherence** — cross-slide narrative and structural consistency.

The authors report Pearson correlation with human judgment around 0.71 — strong for a VLM-as-judge rubric, which is the property that makes it worth adopting.

We use the three dimensions and the 1–5 scale as-published. We changed two things — see "Our adaptation" below — and we document both changes openly because a locked-but-modified protocol only works if the modifications are legible to a reviewer.

## Our adaptation: rubric v5

*Two changes to the published rubric, both documented openly. A locked-but-modified protocol only works if the modifications are legible to a reviewer.*

Rubric v5 is what every number in this repo is scored against. It makes two changes to the PPTEval rubric.

### Change 1: dropped `prompt_fidelity`, kept its intent inside `content`

**`prompt_fidelity` got dropped because it was noise.** Earlier rubric iterations (v3, v4) carried it as a fourth subjective dimension — how well the deck answered the user's request.

In practice it was almost perfectly correlated with `content`: the judge almost never gave a deck high content and low prompt fidelity, or vice versa. The dimension was carrying no new signal; we were paying for a second subjective axis that told us the same thing.

We absorbed the intent into the `content` rubric's 5-point anchor text: "Content completeness is scored *relative to the user's prompt*, not in the abstract." This keeps the signal without paying for an extra judge call per row.

### Change 2: added an objective `visual_craft` dimension

**A subjective visual score alone has a problem for this project specifically.** The SFT target is advanced Slidev features — shiki code blocks, Mermaid diagrams, KaTeX math, `v-click` reveals, transitions, non-default themes, presenter notes.

A VLM judge can *see* those features in a rendered screenshot, but its weighting of them against general "looks nice" is a latent parameter. A deck with visual polish and no advanced features might out-score a deck with correct Mermaid and ugly typography — and the "advanced features" axis is exactly what we're training.

The fix is an independent, objective scanner: [`eval/features.py`](https://github.com/trillion-labs/slides-sft/blob/main/eval/features.py). It scans raw deck markdown (not renders) and counts:

- Named layouts used (distinct non-default layouts).
- Shiki code blocks (and whether line-highlighting syntax is used).
- Mermaid diagrams.
- KaTeX math spans and blocks.
- `v-click` progressive reveals.
- Presenter notes (`<!-- -->` after slide content).
- Transitions (`transition:` in frontmatter).
- Non-default theme selection.

The feature counts are mapped to a 1–5 Visual Craft score by thresholds documented in the scanner. The mapping is the same for every model, every run.

!!! quote "The anchor claim"
    **This score cannot be biased by the judge.** It reads markdown directly. It is, by construction, un-gameable by any change to the judge model, judge prompt, or render pipeline.

    It's the single most defensible number in the project.

### Weighted Overall

*VisCraft at 0.40 on purpose — that's where the SFT delta is expected to land. Intermediate per-dimension numbers are preserved in `comparison.json` for anyone who wants to re-aggregate.*

```
Overall = 0.40·VisCraft + 0.25·Design + 0.20·Content + 0.15·Coherence
```

The visual axis over-weights on purpose. That's where the SFT delta is expected to land, and the project's defensibility rests on being up-front about what we're optimizing.

A reviewer who disagrees with the weighting has every intermediate number in the tables to re-aggregate against a different scheme — they're all in [`eval/comparison.json`](https://github.com/trillion-labs/slides-sft/blob/main/eval/comparison.json).

## Judge: Gemini 3 Flash

*Vision-native, cheap enough to iterate, not in the training-data path. Sees the user prompt and the rendered PNGs — never the markdown.*

`google/gemini-3-flash-preview`, vision-enabled, invoked via OpenRouter. The judge receives the **user prompt** (what the deck was supposed to be) and the **rendered per-slide PNGs** (what the model actually produced).

It does not see the markdown. That's intentional — the judge should score what a human viewer experiences, not the underlying representation.

Why Gemini 3 Flash specifically:

- **Vision native.** A deck is a visual artifact; a text-only judge reading markdown would over-weight structural correctness and miss aesthetics.
- **Cheap enough for the baseline matrix.** The 4-model × 30-row baseline requires 120 judge calls per rubric iteration; vision calls against Gemini 3 Flash are ~$0.002 each. We could iterate the rubric cheaply.
- **Not in the training-data path.** The judge is not the teacher. Codex authors the corpus; Gemini 3 Flash scores it. No circular distillation.

The judge prompt is in [`eval/rubric.py`](https://github.com/trillion-labs/slides-sft/blob/main/eval/rubric.py). It has explicit 5-point anchor text per dimension, a generic-phrase blacklist (the rubric penalizes "the deck looks nice" style rationales and requires evidence from the actual slides), and forces JSON output that is validated and re-tried on malformed responses.

## Floor-scoring: the headline number

*Unrenderable decks score 1 across all dimensions. Counting only renderable rows would be charitable to the weakest models, whose invalid outputs would silently vanish from the average.*

!!! info "Strict by design"
    **Unrenderable decks score 1 across all dimensions.** That's the project's published number. A model that emits invalid Slidev and fails to render is not producing a slide deck; the rubric should not reward it for failing quietly.

A model that emits invalid Slidev and fails to render is not producing a slide deck. Counting only renderable rows would be charitable to the strongest models and unusually charitable to the weakest (whose invalid outputs would silently vanish from the average).

Floor-scoring penalizes invalidity directly and keeps the rubric comparable across models with different render rates.

The alternative number — mean-over-renderable — is also in the comparison table for completeness. It tells you "when the deck renders, how good is it." Both views are in [`eval/comparison_table.md`](https://github.com/trillion-labs/slides-sft/blob/main/eval/comparison_table.md). The Overall number quoted everywhere is floor-scored.

One footnote in the base-model row: `nemotron-nano`'s 87% render rate is about 15pp inflated by cache-reuse of Vue-error PNGs (the render completed but with compile-error slides that the feature scanner and judge correctly score low, so the ranking is unaffected). The final pitch number will re-render fresh. We'd rather flag this honestly than silently correct.

## The four-model baseline

*Not one reference point, four. A Δ that only exists relative to the stock nano but collapses relative to its larger sibling would be a weaker claim than the one this structure lets us make.*

The Track B "Δ vs. baseline" claim depends on the baseline being *meaningful*, not just the model the SFT starts from. We ran the full protocol against four reference points:

| Model | Role |
|---|---|
| `nvidia/nemotron-3-nano-30b-a3b` | SFT target. The "stock" number the finetuned model must beat. |
| `nvidia/nemotron-3-super-120b-a12b` | Same family, 4× larger active params. Clearing this proves the SFT produces real capability, not just parameter-count-for-free. |
| `z-ai/glm-5.1` | Strong open-weight reasoning model, similar vintage. The "can a targeted SFT match a generalist open model" ceiling. |
| `gpt-5.4` | Frontier closed reference. Upper bound for context, not a target. |

Headline table, floor-scored, 30 rows, rubric v5:

| Model | Render | Content | Design | Coherence | VisCraft | **Overall** |
|---|---|---|---|---|---|---|
| `gpt-5.4` | 100% | 4.27 | 3.17 | 4.07 | 3.40 | **3.62** |
| `glm-5.1` | 100% | 3.83 | 3.03 | 3.83 | 2.90 | **3.26** |
| `nemotron-super` | 100% | 4.13 | 2.63 | 3.73 | 1.97 | **2.83** |
| `nemotron-nano` | 87% | 3.50 | 2.30 | 3.37 | 1.80 | **2.50** |

Several things worth flagging from this table:

1. **`nemotron-super` beats `nemotron-nano` on content (4.13 vs. 3.50) but ties on visual craft (1.97 vs. 1.80).** Parameter count helps with content, but the advanced-feature gap is a training-data gap, not a capability gap. This is exactly the region SFT can address.
2. **`glm-5.1` (open reasoning model) beats both Nemotrons on visual craft (2.90 vs. 1.97 / 1.80).** The VisCraft dim is tractable for a model that knows to reach for advanced features. The nano's score is a starting point, not a ceiling.
3. **`gpt-5.4` scores 3.40 on VisCraft, not 5.0.** The advanced-feature surface is actually hard even for frontier models — there's headroom for a domain-specific SFT to compete.

## The render pipeline (and three bugs we caught)

*The eval is only as good as the render. Three bugs had to be fixed before the baseline numbers were load-bearing; all three would have silently inflated or deflated scores had they gone unnoticed.*

The eval is only as good as the render. `renderer/render.sh` takes a deck, resolves image queries, exports per-slide PNGs via Slidev + Playwright, and hands the PNGs to the judge and the markdown to the feature scanner. Three bugs had to be fixed before the baseline numbers were trustworthy:

1. **Port race.** `slidev export` uses `getPort(12445)` as its dev-server port; parallel invocations race for the same port and occasionally produce broken renders. Serialized with `fcntl.flock` around the export call. Benchmark throughput drops, but correctness is non-negotiable for eval.
2. **Silent Vue compile errors.** `slidev export` exits 0 even when Vue raises a compile error mid-render — the resulting PNGs are garbled fragments that *look* valid at the filesystem level. Fix: scan stdout for error signatures (`[vite] Internal server error`, `Element is missing end tag`, `YAMLParseError`, `ReferenceError: Unresolved alias`) and fail the render explicitly if any fire.
3. **Fence-wrap single-slide renders.** Some decks from weaker models wrap the entire output in a `\`\`\`markdown` fence — Slidev parses that as one big code-block slide and exports a single PNG. We were briefly counting this as a successful 1-slide "render." Fix: minimum-slide guard (3 PNGs) to flag these as failures, plus `parse_deck` logic that unwraps leading `\`\`\`markdown` fences (closed or unclosed) without touching inner code blocks in real decks.

Catching these pre-baseline is what makes the baseline numbers load-bearing. A rubric iteration or a model swap cannot expose render-pipeline bugs that were there the whole time.

## Rubric iteration: v1 → v5

*Five versions, each moving in one direction — cheaper, more defensible, harder to game. The trail itself is evidence that the scoring was taken seriously.*

The rubric went through five versions. Each shift is documented in [`PROGRESS.md`](https://github.com/trillion-labs/slides-sft/blob/main/PROGRESS.md) and replayable from the code history. The short version:

- **v1 / v2** — Canonical PPTEval: Content, Design, Coherence, 1–5, no objective cross-check.
- **v3** — Added `visual_richness` and `prompt_fidelity` as extra subjective dimensions with hard 5-point caps. Motivation: the three base dimensions under-weighted the advanced-feature signal the SFT was targeting.
- **v4** — Tightened v3 with benchmark 5-point anchors, a generic-phrase blacklist (the judge was producing "the slides are well-designed" rationales with no evidence), and an evidence-required rubric ("cite a slide number when making a claim").
- **v5 (current)** — Dropped `prompt_fidelity` (redundant with content completeness, see "Our adaptation"). Replaced subjective `visual_richness` with the objective `features.py` scanner ("Visual Craft"). Weighted Overall aggregates the four remaining dimensions with VisCraft at 0.40.

Each change moved the rubric in one direction — toward being cheaper, more defensible, and harder for any single model (including the judge) to game. The five-iteration trail is itself evidence that the scoring was taken seriously.

## Why this is trustworthy

*Six properties together. Any one of them would be weak on its own; the argument for the Δ rests on the full set.*

Six properties together:

1. **Baseline locked before training.** `nemotron-nano`'s 2.50 is the number every finetuned claim will be compared against. It was produced before SFT started.
2. **Protocol identity.** The finetuned eval reuses: the same 30 prompts, the same judge model and judge prompt, the same render pipeline, the same weighted-Overall formula.
3. **Cross-check between subjective and objective.** The Visual Craft scanner runs on markdown directly, independent of the judge. A large Δ on `visual_craft` without a matching shift in the judge's Design score would be a red flag; the converse would too.
4. **Floor-scoring is strict.** Invalid outputs count as 1s, not as omissions. A model that games the rubric by failing to render gets no hiding place.
5. **Four-model baseline, not one.** The SFT target is bracketed by a same-family larger sibling, an open reasoning peer, and a frontier reference. A Δ that only exists relative to the nano but collapses relative to the super is a weaker claim than the one the baseline structure lets us make.
6. **Rubric and render-pipeline bugs caught *pre*-baseline.** The scoring is locked against a pipeline that has already been stress-tested.

## Rejected alternatives

*What we considered for scoring and why each didn't make it in.*

- **Human eval.** No budget. The PPTEval authors' 0.71 Pearson with human judgment is what makes VLM-as-judge acceptable here.
- **GLM-5-style DOM-geometry + whitespace reward (L1/L2/L3).** Impressive on paper, under-specified in the paper, and payoff over PPTEval is not worth the 48h cost.
- **SlidesBench (AutoPresent).** Benchmark is python-pptx format. Porting 30 prompts to Slidev is a stretch item for the writeup stage; not part of the core protocol.
- **Mean-over-renderable as the headline.** Would be charitable to weaker models. Kept as a secondary view for context.
